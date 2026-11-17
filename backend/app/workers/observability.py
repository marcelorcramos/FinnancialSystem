"""Metrics, traces and error reports for the Celery worker (Phase 12).

Imported by celery_app, so the signal handlers below are connected wherever the app
is loaded; they only fire in a worker. The worker forks its pool processes: the
metrics server and error reporting start in the main process, traces in each pool
process (the exporter's thread does not survive a fork).
"""

import os
import time
from typing import Any

from celery import signals

from app.core import metrics, telemetry
from app.core.config import settings
from app.core.logging import configure_logging

_OUTCOMES = {"SUCCESS": "succeeded", "FAILURE": "failed", "RETRY": "retried"}
_started: dict[str, float] = {}


@signals.worker_init.connect
def start_worker_observability(**_: Any) -> None:
    configure_logging()
    telemetry.setup_error_reporting("worker")
    metrics.serve(settings.METRICS_PORT)


@signals.beat_init.connect
def start_beat_observability(**_: Any) -> None:
    configure_logging()
    telemetry.setup_error_reporting("beat")


@signals.worker_process_init.connect
def start_pool_process_tracing(**_: Any) -> None:
    configure_logging()
    if telemetry.setup_tracing("worker"):
        telemetry.instrument_celery()


@signals.worker_process_shutdown.connect
def forget_pool_process(**_: Any) -> None:
    metrics.mark_process_dead(os.getpid())


@signals.task_prerun.connect
def task_started(task_id: str | None = None, **_: Any) -> None:
    if task_id:
        _started[task_id] = time.perf_counter()


@signals.task_postrun.connect
def task_finished(
    task_id: str | None = None, task: Any = None, state: str | None = None, **_: Any
) -> None:
    name = metrics.short_task_name(getattr(task, "name", None) or "unknown")
    start = _started.pop(task_id, None) if task_id else None
    if start is not None:
        metrics.TASK_DURATION.labels(name).observe(time.perf_counter() - start)
    outcome = _OUTCOMES.get(state or "")
    if outcome:
        metrics.TASKS.labels(name, outcome).inc()
