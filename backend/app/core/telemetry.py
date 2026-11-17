"""Traces (OpenTelemetry) and error reports (GlitchTip, through the Sentry SDK). Phase 12.

Both are off until their setting is given (OTEL_EXPORTER_OTLP_ENDPOINT, SENTRY_DSN),
so tests and a plain `docker compose up` send nothing anywhere.

A trace follows a request across processes: the API stores the trace context with
each outbox event, the relay publishes it in the message headers and the consumer
continues the same trace. Celery tasks carry it in their own headers.
"""

from collections.abc import Mapping
from typing import Any

import sentry_sdk
import structlog
from opentelemetry import propagate, trace
from opentelemetry.context import Context
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

from app.core.config import settings

log = structlog.get_logger(__name__)

tracer = trace.get_tracer("app")


def tracing_enabled() -> bool:
    return bool(settings.OTEL_EXPORTER_OTLP_ENDPOINT)


def setup_tracing(service: str, exporter: SpanExporter | None = None) -> bool:
    """Send this process's spans to the collector; returns whether tracing is on.

    Instruments SQLAlchemy and Redis here; Celery is instrumented apart
    (instrument_celery). FastAPI needs nothing: it traces its requests by itself
    with the provider set here (its native OpenTelemetry support).
    """
    if exporter is None:
        if not tracing_enabled():
            return False
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        endpoint = str(settings.OTEL_EXPORTER_OTLP_ENDPOINT).rstrip("/")
        exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
    resource = Resource.create(
        {"service.name": service, "deployment.environment.name": settings.ENVIRONMENT}
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    from app.db.session import engine

    # The instrumentation declares SQLAlchemy < 2.1, but the engine events it hooks are
    # unchanged in 2.1 (tests/integration/test_tracing.py checks the spans).
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, skip_dep_check=True)
    RedisInstrumentor().instrument()
    log.info("telemetry.tracing_on", service=service)
    return True


def instrument_celery() -> None:
    """Producer side in the API (trace context in the task headers), consumer side in
    the worker. In the worker, call it in each pool process (after the fork)."""
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    CeleryInstrumentor().instrument()  # type: ignore[no-untyped-call]


def current_carrier() -> dict[str, str] | None:
    """The current trace context as headers (traceparent), or None outside a trace."""
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    return carrier or None


def context_from(headers: Mapping[str, Any] | None) -> Context:
    """The trace context carried in message headers (an empty one if there is none)."""
    carrier = {k: v for k, v in (headers or {}).items() if isinstance(v, str)}
    return propagate.extract(carrier)


def setup_error_reporting(service: str) -> bool:
    """Report unhandled errors to GlitchTip; returns whether it is on.

    Request bodies are never sent (they hold amounts and descriptions) and the SDK's
    scrubber drops cookies, tokens and passwords from what is sent.
    """
    if not settings.SENTRY_DSN:
        return False
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        server_name=service,
        send_default_pii=False,
        max_request_body_size="never",
    )
    sentry_sdk.set_tag("service", service)
    log.info("telemetry.errors_on", service=service)
    return True


def report_exception(error: BaseException) -> None:
    """Report an error the code caught and handled (a no-op when reporting is off)."""
    sentry_sdk.capture_exception(error)
