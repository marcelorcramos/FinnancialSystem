"""Traces, error reports and worker metrics (Phase 12)."""

from types import SimpleNamespace

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from prometheus_client import REGISTRY

from app.core import metrics, telemetry
from app.core.config import settings
from app.core.logging import add_trace_ids
from app.workers import observability
from tests.tracing import spans  # noqa: F401  (fixture)


def test_everything_is_off_without_settings() -> None:
    assert settings.OTEL_EXPORTER_OTLP_ENDPOINT is None
    assert settings.SENTRY_DSN is None
    assert telemetry.setup_tracing("test") is False
    assert telemetry.setup_error_reporting("test") is False


def test_no_trace_context_outside_a_span() -> None:
    assert telemetry.current_carrier() is None
    assert add_trace_ids(None, "info", {"event": "x"}) == {"event": "x"}


def test_the_trace_context_survives_a_round_trip(spans: InMemorySpanExporter) -> None:  # noqa: F811
    with telemetry.tracer.start_as_current_span("request") as request:
        carrier = telemetry.current_carrier()
        line = add_trace_ids(None, "info", {"event": "x"})
    assert carrier is not None and "traceparent" in carrier
    trace_id = request.get_span_context().trace_id
    assert line["trace_id"] == format(trace_id, "032x")

    with telemetry.tracer.start_as_current_span(
        "later", context=telemetry.context_from(carrier)
    ) as later:
        assert later.get_span_context().trace_id == trace_id
    assert [s.name for s in spans.get_finished_spans()] == ["request", "later"]


def test_headers_that_are_not_text_are_ignored() -> None:
    context = telemetry.context_from({"x-attempts": 2, "traceparent": b"bytes"})
    assert not trace.get_current_span(context).get_span_context().is_valid


def test_error_reports_never_include_request_bodies(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(settings, "SENTRY_DSN", "http://key@glitchtip:8000/1")
    monkeypatch.setattr(telemetry.sentry_sdk, "init", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(telemetry.sentry_sdk, "set_tag", lambda *_: None)
    assert telemetry.setup_error_reporting("api") is True
    assert calls[0]["max_request_body_size"] == "never"
    assert calls[0]["send_default_pii"] is False


def tasks_seen(task: str, outcome: str) -> float:
    value = REGISTRY.get_sample_value("celery_tasks_total", {"task": task, "outcome": outcome})
    return value or 0.0


@pytest.mark.parametrize(("state", "outcome"), [("SUCCESS", "succeeded"), ("FAILURE", "failed")])
def test_worker_counts_tasks_by_outcome(state: str, outcome: str) -> None:
    task = SimpleNamespace(name="app.workers.tasks.send_email")
    before = tasks_seen("send_email", outcome)
    observability.task_started(task_id="t1")
    observability.task_finished(task_id="t1", task=task, state=state)
    assert tasks_seen("send_email", outcome) == before + 1
    count = REGISTRY.get_sample_value("celery_task_duration_seconds_count", {"task": "send_email"})
    assert count and count >= 1


def test_task_names_are_shortened() -> None:
    assert metrics.short_task_name("app.workers.tasks.run_export") == "run_export"
