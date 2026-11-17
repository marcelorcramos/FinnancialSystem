from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.middleware import QUIET_PATHS, RequestContextMiddleware
from app.api.v1.router import api_router
from app.core import metrics, telemetry
from app.core.config import settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    telemetry.setup_error_reporting("api")
    app = FastAPI(
        title="FinnancialSystem API",
        version="0.1.0",
        # FastAPI's own OpenTelemetry spans, sent once telemetry.setup_tracing sets a
        # provider. Metrics come from Prometheus and logs from structlog instead.
        telemetry={
            "metrics": False,
            "logs": False,
            "exclude": lambda scope: scope.get("path") in QUIET_PATHS,
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    # Added last, so it runs first: preflights and CORS rejections are logged too.
    app.add_middleware(RequestContextMiddleware)

    register_error_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Scraped by Prometheus on the internal network; nginx only proxies /api/.
    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics() -> Response:
        data, content_type = metrics.latest()
        return Response(data, media_type=content_type)

    if telemetry.setup_tracing("api"):
        telemetry.instrument_celery()  # the trace continues in the tasks the API sends

    return app


app = create_app()
