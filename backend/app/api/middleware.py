"""Request id, access log and HTTP metrics for every API request (Phase 12).

Each request gets an id: the caller's X-Request-ID when it looks safe (nginx sends
one), otherwise a new one. It is bound to every log line written while the request
runs and returned in the X-Request-ID response header, so an error a person sees can
be found in the logs.
"""

import re
import time
import uuid

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core import metrics

log = structlog.get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
# Probes and scrapes: no access log, no metrics (they would drown the real traffic).
QUIET_PATHS = frozenset({"/health", "/metrics"})
_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})


def request_id_from(scope: Scope) -> str:
    for name, value in scope.get("headers", []):
        if name == b"x-request-id":
            candidate = str(value.decode("latin-1"))
            if _SAFE_REQUEST_ID.fullmatch(candidate):
                return candidate
            break
    return uuid.uuid4().hex


def route_of(scope: Scope) -> str:
    """The matched route's template (/api/v1/months/{month_id}), never the raw path.

    A route of an included router only knows its own part (/months/{month_id}); the
    prefix is what the concrete path has before that part.
    """
    route = scope.get("route")
    template = getattr(route, "path_format", None)
    if not isinstance(template, str) or not template:
        return metrics.UNMATCHED_ROUTE
    path: str = scope["path"]
    params = {k: str(v) for k, v in scope.get("path_params", {}).items()}
    try:
        own_part = template.format(**params)
    except (KeyError, IndexError, ValueError):
        return template
    prefix = path[: len(path) - len(own_part)] if path.endswith(own_part) else ""
    return prefix + template


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in QUIET_PATHS:
            await self.app(scope, receive, send)
            return

        request_id = request_id_from(scope)
        method = scope["method"] if scope["method"] in _METHODS else "OTHER"
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message.setdefault("headers", [])
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        start = time.perf_counter()
        metrics.HTTP_IN_PROGRESS.inc()
        with structlog.contextvars.bound_contextvars(request_id=request_id):
            try:
                await self.app(scope, receive, send_with_id)
            except Exception:
                status = 500
                log.exception("http.unhandled_error", method=method, path=scope["path"])
                raise
            finally:
                metrics.HTTP_IN_PROGRESS.dec()
                elapsed = time.perf_counter() - start
                route = route_of(scope)
                metrics.HTTP_REQUESTS.labels(method, route, str(status)).inc()
                metrics.HTTP_DURATION.labels(method, route).observe(elapsed)
                log.info(
                    "http.request",
                    method=method,
                    route=route,
                    status=status,
                    duration_ms=round(elapsed * 1000, 1),
                )
