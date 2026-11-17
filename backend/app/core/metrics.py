"""Prometheus metrics (Phase 12).

The API serves them on GET /metrics. The background processes (relay, consumers,
Celery worker) have no HTTP server of their own, so each one starts a small one on
settings.METRICS_PORT; Prometheus scrapes every process (deploy/observability).

The Celery worker forks its pool processes, so it runs prometheus_client in
multiprocess mode (PROMETHEUS_MULTIPROC_DIR set in Compose): each process writes its
samples to that directory and the worker's main process serves them all.

Label values are always bounded (route templates, consumer and task names, a fixed
set of outcomes): never a user id, an entry id or a raw path.
"""

import os

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
    start_http_server,
)

# --- API ---------------------------------------------------------------------

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests answered by the API.",
    ["method", "route", "status"],
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "Time to answer an HTTP request, by route template.",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
HTTP_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests being answered right now.",
    multiprocess_mode="livesum",
)
UNMATCHED_ROUTE = "unmatched"  # 404s for paths no route matches: one label, not one per path

# --- Outbox relay ------------------------------------------------------------

OUTBOX_PUBLISHED = Counter("outbox_events_published_total", "Outbox events sent to RabbitMQ.")
OUTBOX_PENDING = Gauge(
    "outbox_events_pending",
    "Outbox events written but not yet published.",
    multiprocess_mode="max",
)

# --- Event consumers ---------------------------------------------------------

EVENT_OUTCOMES = ("handled", "duplicate", "retried", "dead_lettered", "malformed")
EVENTS = Counter(
    "events_consumed_total",
    "Domain events a consumer took off its queue, by outcome.",
    ["consumer", "outcome"],
)
EVENT_DURATION = Histogram(
    "event_handle_duration_seconds",
    "Time a consumer spent on one event (handled, duplicate or failed).",
    ["consumer"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)

# --- Celery tasks ------------------------------------------------------------

TASK_OUTCOMES = ("succeeded", "failed", "retried")
TASKS = Counter(
    "celery_tasks_total",
    "Background tasks the worker ran, by outcome.",
    ["task", "outcome"],
)
TASK_DURATION = Histogram(
    "celery_task_duration_seconds",
    "Time a background task ran.",
    ["task"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)


def short_task_name(name: str) -> str:
    """app.workers.tasks.send_email -> send_email (task names are a fixed set)."""
    return name.rsplit(".", 1)[-1]


def _registry() -> CollectorRegistry | None:
    """Multiprocess mode collects from the samples directory; otherwise the default."""
    if not os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        return None
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)  # type: ignore[no-untyped-call]
    return registry


def latest() -> tuple[bytes, str]:
    """The current samples in the text format, and its content type."""
    registry = _registry()
    data = generate_latest(registry) if registry is not None else generate_latest()
    return data, CONTENT_TYPE_LATEST


def serve(port: int) -> None:
    """Expose /metrics from a background thread (processes without an HTTP server)."""
    registry = _registry()
    if registry is not None:
        start_http_server(port, registry=registry)
    else:
        start_http_server(port)


def mark_process_dead(pid: int) -> None:
    """Drop a finished pool process's live gauges (multiprocess mode only)."""
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        multiprocess.mark_process_dead(pid)  # type: ignore[no-untyped-call]
