"""Request id, access log and HTTP metrics (Phase 12)."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from prometheus_client import REGISTRY

from app.api.middleware import RequestContextMiddleware, route_of
from app.main import app


def requests_seen(method: str, route: str, status: str) -> float:
    value = REGISTRY.get_sample_value(
        "http_requests_total", {"method": method, "route": route, "status": status}
    )
    return value or 0.0


async def get(path: str, **headers: str) -> tuple[int, dict[str, str], str]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(path, headers=headers)
    return response.status_code, dict(response.headers), response.text


async def test_every_response_carries_a_request_id() -> None:
    _, headers, _ = await get("/api/v1/labels")
    assert len(headers["x-request-id"]) == 32


async def test_a_safe_request_id_from_the_caller_is_kept() -> None:
    _, headers, _ = await get("/api/v1/labels", **{"X-Request-ID": "nginx-4f2a.9"})
    assert headers["x-request-id"] == "nginx-4f2a.9"


async def test_an_unsafe_request_id_is_replaced() -> None:
    _, headers, _ = await get("/api/v1/labels", **{"X-Request-ID": 'a b"<script>'})
    assert headers["x-request-id"] != 'a b"<script>'
    assert len(headers["x-request-id"]) == 32


async def test_requests_are_counted_by_route_template_not_by_path() -> None:
    route = "/api/v1/months/{month_id}"
    before = requests_seen("GET", route, "401")
    await get("/api/v1/months/0b6f8a7e-0000-4000-8000-000000000001")
    await get("/api/v1/months/0b6f8a7e-0000-4000-8000-000000000002")
    assert requests_seen("GET", route, "401") == before + 2


async def test_unknown_paths_share_one_label() -> None:
    before = requests_seen("GET", "unmatched", "404")
    await get("/wp-admin/setup.php")
    await get("/.env")
    assert requests_seen("GET", "unmatched", "404") == before + 2


async def test_probes_and_scrapes_are_not_counted() -> None:
    await get("/health")
    _, _, body = await get("/metrics")
    assert 'route="/health"' not in body
    assert 'route="/metrics"' not in body


async def test_metrics_are_served_in_the_prometheus_format() -> None:
    status, headers, body = await get("/metrics")
    assert status == 200
    assert headers["content-type"].startswith("text/plain")
    assert "# TYPE http_request_duration_seconds histogram" in body


async def test_an_unhandled_error_is_counted_as_500() -> None:
    broken = FastAPI()
    broken.add_middleware(RequestContextMiddleware)

    @broken.get("/boom")
    async def boom() -> None:
        raise RuntimeError("bug")

    before = requests_seen("GET", "/boom", "500")
    transport = ASGITransport(app=broken, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom")
    assert response.status_code == 500
    assert requests_seen("GET", "/boom", "500") == before + 1


@pytest.mark.parametrize(
    ("path", "template", "params", "expected"),
    [
        (
            "/api/v1/months/abc",
            "/months/{month_id}",
            {"month_id": "abc"},
            "/api/v1/months/{month_id}",
        ),
        ("/api/v1/auth/login", "/auth/login", {}, "/api/v1/auth/login"),
        ("/health", "/health", {}, "/health"),
    ],
)
def test_route_template_includes_the_router_prefix(
    path: str, template: str, params: dict[str, str], expected: str
) -> None:
    class Route:
        path_format = template

    assert route_of({"path": path, "route": Route(), "path_params": params}) == expected


def test_no_route_means_unmatched() -> None:
    assert route_of({"path": "/x", "path_params": {}}) == "unmatched"
