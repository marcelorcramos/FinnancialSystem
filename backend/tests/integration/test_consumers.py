"""Idempotent consumers, retries and the dead-letter queue (Phase 7 acceptance criteria)."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator

import aio_pika
import pytest
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage, AbstractQueue
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.cache import Cache
from app.events import relay, topology
from app.events.consumers import Event, cache_handler, handle_once, process_message
from app.models import Entry, ProcessedEvent
from tests.integration.helpers import ApiUser, create_month, label_id, new_user


@pytest.fixture
async def channel(rabbitmq_url: str) -> AsyncIterator[AbstractChannel]:
    connection = await aio_pika.connect(rabbitmq_url)
    async with connection:
        channel = await connection.channel(publisher_confirms=True)
        await topology.declare(channel)
        for name in (*topology.BINDINGS, topology.DEAD_LETTER_QUEUE):
            await (await channel.get_queue(name)).purge()
        yield channel


@pytest.fixture
def sessions(session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    """Consumer sessions inside the test transaction (rolled back at the end)."""
    return async_sessionmaker(
        bind=session.bind, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )


@pytest.fixture
async def redis(redis_url: str) -> AsyncIterator[Redis]:
    client = Redis.from_url(redis_url)
    await client.flushdb()
    yield client
    await client.aclose()


async def allocate(client: AsyncClient, user: ApiUser) -> str:
    month = (await create_month(client, user))["id"]
    food = await label_id(client, user, "Food")
    response = await client.put(
        f"/api/v1/months/{month}/allocations/{food}", headers=user.headers, json={"amount": "200"}
    )
    assert response.status_code == 200
    entry_id: str = response.json()["id"]
    return entry_id


async def next_message(queue: AbstractQueue, user: ApiUser) -> AbstractIncomingMessage:
    """The next message of this user's events (other tests' events are acknowledged)."""
    for _ in range(100):
        message = await queue.get(fail=False)
        if message is None:
            await asyncio.sleep(0.05)
            continue
        if json.loads(message.body)["payload"]["user_id"] == str(user.id):
            return message
        await message.ack()
    raise AssertionError("no message for this user")


async def test_reprocessing_an_event_does_not_repeat_its_effect(
    sessions: async_sessionmaker[AsyncSession], redis: Redis
) -> None:
    event = Event(uuid.uuid4(), "entry.create", {"user_id": str(uuid.uuid4())})
    handler = cache_handler(Cache(redis))
    async with sessions() as session:
        assert await handle_once(session, "cache", event, handler) is True
    async with sessions() as session:
        assert await handle_once(session, "cache", event, handler) is False
    assert await redis.get(f"cache:{event.user_id}:version") == b"1"
    async with sessions() as session:
        count = await session.scalar(
            select(func.count()).where(ProcessedEvent.event_id == event.id)
        )
    assert count == 1


async def test_a_failing_consumer_keeps_the_entry_and_gets_the_message_again(
    client: AsyncClient,
    session: AsyncSession,
    sessions: async_sessionmaker[AsyncSession],
    channel: AbstractChannel,
) -> None:
    user = await new_user(client)
    entry_id = await allocate(client, user)
    await relay.publish_pending(session, await channel.get_exchange(topology.EXCHANGE))
    queue = await channel.get_queue("limits")

    async def broken(_: AsyncSession, __: Event) -> None:
        raise RuntimeError("limits service is down")

    retry = channel.default_exchange
    message = await next_message(queue, user)
    await process_message(message, "limits", broken, retry, sessions)
    assert await session.get(Entry, uuid.UUID(entry_id)) is not None  # the write stays saved

    handled: list[str] = []

    async def working(_: AsyncSession, event: Event) -> None:
        handled.append(event.type)

    redelivered = await next_message(queue, user)
    assert redelivered.message_id == message.message_id
    assert redelivered.headers["x-attempts"] == 1
    await process_message(redelivered, "limits", working, retry, sessions)
    assert handled == ["entry.create"]


async def test_a_message_that_keeps_failing_goes_to_the_dead_letter_queue(
    client: AsyncClient,
    session: AsyncSession,
    sessions: async_sessionmaker[AsyncSession],
    channel: AbstractChannel,
) -> None:
    user = await new_user(client)
    await allocate(client, user)
    await relay.publish_pending(session, await channel.get_exchange(topology.EXCHANGE))
    queue = await channel.get_queue("goals")

    async def broken(_: AsyncSession, __: Event) -> None:
        raise RuntimeError("always fails")

    retry = channel.default_exchange
    first = await next_message(queue, user)
    await process_message(first, "goals", broken, retry, sessions)
    for _ in range(topology.MAX_ATTEMPTS - 1):
        retried = await next_message(queue, user)
        assert retried.message_id == first.message_id
        await process_message(retried, "goals", broken, retry, sessions)

    dead_queue = await channel.get_queue(topology.DEAD_LETTER_QUEUE)
    dead = await next_message(dead_queue, user)
    assert dead.message_id == first.message_id
    await dead.ack()
    assert await queue.get(fail=False) is None


async def test_a_malformed_message_goes_straight_to_the_dead_letter_queue(
    sessions: async_sessionmaker[AsyncSession], channel: AbstractChannel
) -> None:
    exchange = await channel.get_exchange(topology.EXCHANGE)
    await exchange.publish(
        aio_pika.Message(b"not json", message_id="bad"), routing_key="entry.create"
    )
    queue = await channel.get_queue("goals")
    message = await queue.get(timeout=5)
    retry = channel.default_exchange

    async def never(_: AsyncSession, __: Event) -> None:
        raise AssertionError("must not run")

    await process_message(message, "goals", never, retry, sessions)
    dead_queue = await channel.get_queue(topology.DEAD_LETTER_QUEUE)
    for _ in range(100):
        dead = await dead_queue.get(fail=False)
        if dead is not None:
            break
        await asyncio.sleep(0.05)
    assert dead is not None and dead.message_id == "bad"
    await dead.ack()
