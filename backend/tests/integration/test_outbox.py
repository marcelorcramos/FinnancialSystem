"""Outbox events and the relay (Phase 7)."""

import json
from collections.abc import AsyncIterator

import aio_pika
import pytest
from aio_pika.abc import AbstractChannel
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events import relay, topology
from app.models import OutboxEvent
from tests.integration.helpers import create_month, label_id, new_user


@pytest.fixture
async def channel(rabbitmq_url: str) -> AsyncIterator[AbstractChannel]:
    connection = await aio_pika.connect(rabbitmq_url)
    async with connection:
        channel = await connection.channel(publisher_confirms=True)
        await topology.declare(channel)
        for name in (*topology.BINDINGS, topology.DEAD_LETTER_QUEUE):
            await (await channel.get_queue(name)).purge()
        yield channel


async def pending(session: AsyncSession) -> list[OutboxEvent]:
    stmt = select(OutboxEvent).where(OutboxEvent.published_at.is_(None))
    return list(await session.scalars(stmt.order_by(OutboxEvent.created_at)))


async def test_a_write_and_its_event_share_the_transaction(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await new_user(client)
    month = (await create_month(client, user))["id"]
    food = await label_id(client, user, "Food")
    response = await client.put(
        f"/api/v1/months/{month}/allocations/{food}", headers=user.headers, json={"amount": "200"}
    )
    assert response.status_code == 200

    events = [e for e in await pending(session) if e.payload["user_id"] == str(user.id)]
    assert [e.type for e in events][-2:] == ["month.create", "entry.create"]
    assert events[-1].payload == {
        "user_id": str(user.id),
        "entity": "entry",
        "entity_id": response.json()["id"],
        "action": "create",
        "month_id": month,
    }


async def test_a_failed_write_leaves_no_event(client: AsyncClient, session: AsyncSession) -> None:
    user = await new_user(client)
    month = (await create_month(client, user))["id"]
    before = len(await pending(session))
    response = await client.put(
        f"/api/v1/months/{month}/allocations/{await label_id(client, user, 'Food')}",
        headers=user.headers,
        json={"amount": "-1"},
    )
    assert response.status_code == 422
    assert len(await pending(session)) == before


async def test_the_relay_publishes_pending_events_once(
    client: AsyncClient, session: AsyncSession, channel: AbstractChannel
) -> None:
    user = await new_user(client)
    await create_month(client, user)
    exchange = await channel.get_exchange(topology.EXCHANGE)

    assert await relay.publish_pending(session, exchange) >= 1
    assert await pending(session) == []
    assert await relay.publish_pending(session, exchange) == 0  # nothing left

    cache = await channel.get_queue("cache")
    goals = await channel.get_queue("goals")
    messages = []
    while (message := await cache.get(fail=False)) is not None:
        await message.ack()
        messages.append(json.loads(message.body))
    mine = [m for m in messages if m["payload"]["user_id"] == str(user.id)]
    types = [m["type"] for m in mine]
    # Sign-up creates the default labels, then the month: one message each, in order.
    assert types[-1] == "month.create"
    assert set(types[:-1]) == {"label.create"} and len(types) == len(set(m["id"] for m in mine))
    assert await goals.get(fail=False) is None  # goals only listens to entries
