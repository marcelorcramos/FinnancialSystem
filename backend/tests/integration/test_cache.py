"""Redis read cache for summaries and reports (Phase 7)."""

from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from testcontainers.community.redis import RedisContainer

from app.core.cache import Cache, get_cache
from app.main import app
from tests.integration.helpers import ApiUser, create_month, label_id, new_user


@pytest.fixture(scope="module")
def redis_url() -> Iterator[str]:
    with RedisContainer("redis:7-alpine") as container:
        host, port = container.get_container_host_ip(), container.get_exposed_port(6379)
        yield f"redis://{host}:{port}/0"


@pytest.fixture
async def redis(redis_url: str) -> AsyncIterator[Redis]:
    client = Redis.from_url(redis_url)
    await client.flushdb()
    app.dependency_overrides[get_cache] = lambda: Cache(client)
    yield client
    app.dependency_overrides.pop(get_cache, None)
    await client.aclose()


async def version(redis: Redis, user: ApiUser) -> int:
    return int(await redis.get(f"cache:{user.id}:version") or 0)


async def keys(redis: Redis, pattern: str) -> list[str]:
    return sorted(k.decode() for k in await redis.keys(pattern))


async def summary(client: AsyncClient, user: ApiUser, month_id: str) -> dict[str, Any]:
    response = await client.get(f"/api/v1/months/{month_id}/summary", headers=user.headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_creating_an_entry_invalidates_the_cache(client: AsyncClient, redis: Redis) -> None:
    """Acceptance criterion: the next read after a write returns the updated value."""
    user = await new_user(client)
    month = (await create_month(client, user))["id"]
    food = await label_id(client, user, "Food")

    before = await version(redis, user)  # creating the month was already a write
    assert (await summary(client, user, month))["distributed"] == "0.00"
    assert len(await keys(redis, f"cache:{user.id}:v{before}:month_summary:*")) == 1
    assert (await summary(client, user, month))["distributed"] == "0.00"  # served from Redis

    response = await client.put(
        f"/api/v1/months/{month}/allocations/{food}", headers=user.headers, json={"amount": "200"}
    )
    assert response.status_code == 200
    assert await version(redis, user) == before + 1
    assert (await summary(client, user, month))["distributed"] == "200.00"


async def test_reports_are_cached_per_user_and_filter(client: AsyncClient, redis: Redis) -> None:
    alice, bob = await new_user(client), await new_user(client)
    for user in (alice, bob):
        for params in ({"period": "last_month"}, {"period": "all"}):
            response = await client.get(
                "/api/v1/reports/summary", headers=user.headers, params=params
            )
            assert response.status_code == 200
    assert len(await keys(redis, f"cache:{alice.id}:*:report_summary:*")) == 2
    assert len(await keys(redis, f"cache:{bob.id}:*:report_summary:*")) == 2


async def test_failed_writes_and_reads_keep_the_cache(client: AsyncClient, redis: Redis) -> None:
    user = await new_user(client)
    month = (await create_month(client, user))["id"]
    await summary(client, user, month)
    before = await version(redis, user)
    response = await client.put(
        f"/api/v1/months/{month}/allocations/{await label_id(client, user, 'Food')}",
        headers=user.headers,
        json={"amount": "-5"},
    )
    assert response.status_code == 422
    assert await version(redis, user) == before
    assert len(await keys(redis, f"cache:{user.id}:v{before}:month_summary:*")) == 1


async def test_reads_work_without_redis(client: AsyncClient) -> None:
    app.dependency_overrides[get_cache] = lambda: Cache(Redis.from_url("redis://127.0.0.1:1/0"))
    try:
        user = await new_user(client)
        month = (await create_month(client, user))["id"]
        assert (await summary(client, user, month))["distributed"] == "0.00"
        response = await client.post(f"/api/v1/months/{month}/close", headers=user.headers)
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_cache, None)
