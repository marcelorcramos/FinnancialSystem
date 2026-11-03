"""Alerts raised by the limits consumer and pushed live (Phase 8)."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.v1.alerts import alert_events
from app.core.notifications import alerts_channel
from app.events.consumers import Event, handle_once, limits_handler
from tests.integration.helpers import ApiUser, create_month, label_id, new_user


@pytest.fixture
def sessions(session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=session.bind, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )


@pytest.fixture
async def redis(redis_url: str) -> AsyncIterator[Redis]:
    client = Redis.from_url(redis_url)
    yield client
    await client.aclose()


async def food_month(client: AsyncClient, user: ApiUser, limit: str) -> tuple[str, uuid.UUID]:
    month = (await create_month(client, user))["id"]
    food = await label_id(client, user, "Food")
    response = await client.put(
        f"/api/v1/labels/{food}/limit", headers=user.headers, json={"amount": limit}
    )
    assert response.status_code == 200
    return month, food


async def allocate(
    client: AsyncClient, user: ApiUser, month: str, food: uuid.UUID, amount: str
) -> None:
    response = await client.put(
        f"/api/v1/months/{month}/allocations/{food}", headers=user.headers, json={"amount": amount}
    )
    assert response.status_code == 200


def entry_event(user: ApiUser, month: str) -> Event:
    return Event(uuid.uuid4(), "entry.create", {"user_id": str(user.id), "month_id": month})


async def alerts_of(client: AsyncClient, user: ApiUser, **params: Any) -> list[dict[str, Any]]:
    response = await client.get("/api/v1/alerts", headers=user.headers, params=params)
    assert response.status_code == 200, response.text
    body: list[dict[str, Any]] = response.json()
    return body


async def test_each_level_is_raised_once_and_pushed_after_commit(
    client: AsyncClient, sessions: async_sessionmaker[AsyncSession], redis: Redis
) -> None:
    user = await new_user(client)
    month, food = await food_month(client, user, "300")
    pubsub = redis.pubsub()
    await pubsub.subscribe(alerts_channel(user.id))
    handler = limits_handler(redis, sessions)

    await allocate(client, user, month, food, "100")  # 33%: nothing yet
    async with sessions() as session:
        await handle_once(session, "limits", entry_event(user, month), handler)
    assert await alerts_of(client, user) == []

    await allocate(client, user, month, food, "250")  # 83%: warning
    async with sessions() as session:
        await handle_once(session, "limits", entry_event(user, month), handler)
    await allocate(client, user, month, food, "320")  # 107%: exceeded, warning not repeated
    for _ in range(2):
        async with sessions() as session:
            await handle_once(session, "limits", entry_event(user, month), handler)

    alerts = await alerts_of(client, user)
    assert [(a["level"], a["label_name"], a["total"], a["limit_amount"]) for a in alerts] == [
        ("exceeded", "Food", "320.00", "300.00"),
        ("warning", "Food", "250.00", "300.00"),
    ]

    pushed = []
    for _ in range(20):
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.2)
        if message:
            pushed.append(json.loads(message["data"])["level"])
    assert pushed == ["warning", "exceeded"]
    await pubsub.aclose()


async def test_lowering_a_limit_raises_alerts_for_open_months(
    client: AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    user = await new_user(client)
    month, food = await food_month(client, user, "1000")
    await allocate(client, user, month, food, "200")
    await client.put(f"/api/v1/labels/{food}/limit", headers=user.headers, json={"amount": "150"})
    event = Event(uuid.uuid4(), "limit.update", {"user_id": str(user.id), "month_id": None})
    async with sessions() as session:
        await handle_once(session, "limits", event, limits_handler(None, sessions))
    assert {a["level"] for a in await alerts_of(client, user)} == {"warning", "exceeded"}


async def test_alerts_can_be_marked_seen(
    client: AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    user = await new_user(client)
    month, food = await food_month(client, user, "100")
    await allocate(client, user, month, food, "150")
    async with sessions() as session:
        await handle_once(
            session, "limits", entry_event(user, month), limits_handler(None, sessions)
        )

    first, second = await alerts_of(client, user, unseen=True)
    response = await client.post(f"/api/v1/alerts/{first['id']}/seen", headers=user.headers)
    assert response.status_code == 204
    assert [a["id"] for a in await alerts_of(client, user, unseen=True)] == [second["id"]]
    assert (await client.post("/api/v1/alerts/seen", headers=user.headers)).status_code == 204
    assert await alerts_of(client, user, unseen=True) == []
    assert len(await alerts_of(client, user)) == 2  # still listed, as seen

    # Marking again is fine; an unknown id is not.
    assert (
        await client.post(f"/api/v1/alerts/{first['id']}/seen", headers=user.headers)
    ).status_code == 204
    missing = await client.post(f"/api/v1/alerts/{uuid.uuid4()}/seen", headers=user.headers)
    assert missing.status_code == 404


async def test_alerts_are_isolated(
    client: AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    alice, bob = await new_user(client), await new_user(client)
    month, food = await food_month(client, alice, "100")
    await allocate(client, alice, month, food, "150")
    async with sessions() as session:
        await handle_once(
            session, "limits", entry_event(alice, month), limits_handler(None, sessions)
        )
    alert = (await alerts_of(client, alice))[0]

    assert await alerts_of(client, bob) == []
    response = await client.post(f"/api/v1/alerts/{alert['id']}/seen", headers=bob.headers)
    assert response.status_code == 404
    assert (await alerts_of(client, alice, unseen=True))[0]["id"] == alert["id"]


async def test_the_stream_sends_alerts_and_heartbeats(redis: Redis, redis_url: str) -> None:
    user_id = uuid.uuid4()
    stop = asyncio.Event()

    async def disconnected() -> bool:
        return stop.is_set()

    subscriber = Redis.from_url(redis_url)
    stream = alert_events(subscriber, user_id, disconnected, heartbeat=0.2)
    assert await anext(stream) == ": connected\n\n"
    assert await anext(stream) == ": ping\n\n"
    await redis.publish(alerts_channel(user_id), json.dumps({"level": "warning"}))
    lines = [await anext(stream) for _ in range(3)]
    assert 'event: alert\ndata: {"level": "warning"}\n\n' in lines
    stop.set()
    await stream.aclose()
    await subscriber.aclose()
