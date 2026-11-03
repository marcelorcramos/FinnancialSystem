"""Rate limiting of the auth routes (Phase 7)."""

from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis

from app.core.rate_limit import Limit, RateLimiter, get_rate_limiter
from app.main import app
from tests.integration.helpers import PASSWORD, register


@pytest.fixture
async def redis(redis_url: str) -> AsyncIterator[Redis]:
    client = Redis.from_url(redis_url)
    await client.flushdb()
    app.dependency_overrides[get_rate_limiter] = lambda: RateLimiter(client)
    yield client
    app.dependency_overrides.pop(get_rate_limiter, None)
    await client.aclose()


async def test_too_many_logins_for_one_email_get_429(
    client: AsyncClient, redis: Redis, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.v1.auth.LOGIN_PER_EMAIL", Limit("login-email", 3, 300))
    user = await register(client)
    body = {"email": user["email"], "password": "wrong-123"}
    statuses = [(await client.post("/api/v1/auth/login", json=body)).status_code for _ in range(3)]
    assert statuses == [401, 401, 401]

    blocked = await client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": PASSWORD}
    )
    assert blocked.status_code == 429
    assert blocked.json() == {
        "detail": "Too many attempts. Try again later.",
        "code": "rate_limited",
    }
    assert 0 < int(blocked.headers["Retry-After"]) <= 300
    # The key holds a hash, never the email itself.
    assert all(user["email"] not in k.decode() for k in await redis.keys("ratelimit:*"))


async def test_other_emails_are_not_affected(
    client: AsyncClient, redis: Redis, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.v1.auth.LOGIN_PER_EMAIL", Limit("login-email", 1, 300))
    alice, bob = await register(client), await register(client)
    for user in (alice, alice):
        await client.post("/api/v1/auth/login", json={"email": user["email"], "password": "x"})
    ok = await client.post("/api/v1/auth/login", json={"email": bob["email"], "password": PASSWORD})
    assert ok.status_code == 200


async def test_registrations_are_limited_per_ip(
    client: AsyncClient, redis: Redis, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.v1.auth.REGISTER_PER_IP", Limit("register-ip", 2, 3600))
    await register(client)
    await register(client)
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "third@example.com", "password": PASSWORD, "name": "Third"},
    )
    assert response.status_code == 429


async def test_without_redis_nothing_is_limited(client: AsyncClient) -> None:
    app.dependency_overrides[get_rate_limiter] = lambda: RateLimiter(
        Redis.from_url("redis://127.0.0.1:1/0")
    )
    try:
        user = await register(client)
        for _ in range(3):
            response = await client.post(
                "/api/v1/auth/login", json={"email": user["email"], "password": PASSWORD}
            )
            assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_rate_limiter, None)
