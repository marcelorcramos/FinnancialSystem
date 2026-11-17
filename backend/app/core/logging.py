import logging

import structlog
from opentelemetry import trace

from app.core.config import settings


def add_trace_ids(
    _: object, __: str, event_dict: structlog.typing.EventDict
) -> structlog.typing.EventDict:
    """Put the current trace and span ids on the line, so a log opens its trace."""
    context = trace.get_current_span().get_span_context()
    if context.is_valid:
        event_dict["trace_id"] = format(context.trace_id, "032x")
        event_dict["span_id"] = format(context.span_id, "016x")
    return event_dict


def configure_logging() -> None:
    level = logging.getLevelName(settings.LOG_LEVEL.upper())
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if settings.json_logs
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            # request_id (and anything else bound for the current request or event).
            structlog.contextvars.merge_contextvars,
            add_trace_ids,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
