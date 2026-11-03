"""Idempotent consumers of the domain events (Phase 7).

Run one process per consumer: `python -m app.events.consumers cache`.

Each event is handled at most once per consumer: the (consumer, event id) pair
is stored in processed_events in the same transaction as the consumer's own
database work, so a redelivered message is acknowledged without repeating its
effects. If the handler fails nothing is stored and the message is published
again to the same queue with its attempt count; after topology.MAX_ATTEMPTS
failures it is rejected to the dead-letter queue. The write that produced the
event is never affected.
"""

import asyncio
import json
import sys
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import aio_pika
import structlog
from aio_pika.abc import AbstractExchange, AbstractIncomingMessage
from redis.asyncio import Redis
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core import notifications
from app.core.cache import Cache, get_cache
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.events import topology
from app.models import ProcessedEvent
from app.repositories import users as users_repo
from app.services import alerts

log = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Event:
    id: uuid.UUID
    type: str
    payload: dict[str, Any]

    @property
    def user_id(self) -> uuid.UUID:
        return uuid.UUID(self.payload["user_id"])

    @classmethod
    def from_body(cls, body: bytes) -> "Event":
        data = json.loads(body)
        return cls(uuid.UUID(data["id"]), str(data["type"]), dict(data["payload"]))


AfterCommit = Callable[[], Awaitable[None]]
# A handler does its database work in the given session and may return what to do
# once that work is committed (e.g. push a notification): never before it is saved.
Handler = Callable[[AsyncSession, Event], Awaitable[AfterCommit | None]]


def cache_handler(cache: Cache) -> Handler:
    """Invalidate the user's read cache (writes that did not come through the API)."""

    async def handle(_: AsyncSession, event: Event) -> None:
        await cache.invalidate(event.user_id)

    return handle


def limits_handler(
    redis: Redis | None, sessions: async_sessionmaker[AsyncSession] = SessionLocal
) -> Handler:
    """Raise the alerts the touched month's limits reach, then push them live."""

    async def handle(session: AsyncSession, event: Event) -> AfterCommit | None:
        user = await users_repo.get_active_by_id(session, event.user_id)
        if user is None:
            return None
        month_id = event.payload.get("month_id")
        created: list[uuid.UUID] = []
        for month in await alerts.months_to_check(
            session, user, uuid.UUID(month_id) if month_id else None
        ):
            created += await alerts.raise_alerts(session, user, month)
        if not created:
            return None

        async def push() -> None:
            async with sessions() as fresh:
                # Oldest first, so a jump past 100% reads "warning" then "exceeded".
                for alert in reversed(await alerts.get_many(fresh, user, created)):
                    await notifications.publish(
                        redis, notifications.alerts_channel(user.id), alert.model_dump(mode="json")
                    )

        return push

    return handle


async def _waits_for_goals(_: AsyncSession, event: Event) -> None:
    # Goal progress is computed when read (services/goals.py); completed goals are
    # recorded by the goals consumer in the next step of Phase 8.
    log.debug("event.no_action_yet", type=event.type)


def handlers(cache: Cache) -> dict[str, Handler]:
    return {
        "cache": cache_handler(cache),
        "limits": limits_handler(cache.redis),
        "goals": _waits_for_goals,
    }


async def handle_once(session: AsyncSession, consumer: str, event: Event, handler: Handler) -> bool:
    """Run the handler unless this consumer already processed the event.

    Returns whether it ran. On error the transaction is rolled back and re-raised.
    """
    claimed = await session.execute(
        insert(ProcessedEvent)
        .values(consumer=consumer, event_id=event.id)
        .on_conflict_do_nothing()
        .returning(ProcessedEvent.event_id)
    )
    if claimed.first() is None:
        await session.rollback()
        return False
    try:
        after_commit = await handler(session, event)
    except BaseException:
        await session.rollback()
        raise
    await session.commit()
    if after_commit is not None:
        try:
            await after_commit()
        except Exception:
            # The work is saved and marked processed; a failed side effect is logged only.
            log.exception("event.after_commit_failed", consumer=consumer, type=event.type)
    return True


ATTEMPTS_HEADER = "x-attempts"


async def _retry_or_dead_letter(
    message: AbstractIncomingMessage, consumer: str, retry_exchange: AbstractExchange
) -> None:
    headers: dict[str, Any] = dict(message.headers or {})
    previous = headers.get(ATTEMPTS_HEADER)
    attempts = (previous if isinstance(previous, int) else 0) + 1
    if attempts >= topology.MAX_ATTEMPTS:
        log.error("event.dead_lettered", consumer=consumer, message_id=message.message_id)
        await message.reject(requeue=False)
        return
    # Publish a copy with the new count, then drop the original. A crash in between
    # only means one extra delivery, which the idempotency check absorbs.
    await retry_exchange.publish(
        aio_pika.Message(
            message.body,
            headers={**headers, ATTEMPTS_HEADER: attempts},
            message_id=message.message_id,
            type=message.type,
            content_type=message.content_type,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=consumer,
    )
    await message.ack()


async def process_message(
    message: AbstractIncomingMessage,
    consumer: str,
    handler: Handler,
    retry_exchange: AbstractExchange,
    sessions: async_sessionmaker[AsyncSession] = SessionLocal,
) -> None:
    """Acknowledge a handled (or already handled) message; retry it on failure.

    `retry_exchange` is the default exchange, which routes by queue name, so a
    retried message only goes back to this consumer's queue.
    """
    try:
        event = Event.from_body(message.body)
    except (ValueError, KeyError, TypeError):
        log.error("event.malformed", consumer=consumer, message_id=message.message_id)
        await message.reject(requeue=False)  # straight to the dead-letter queue
        return
    try:
        async with sessions() as session:
            ran = await handle_once(session, consumer, event, handler)
    except Exception:
        log.exception("event.failed", consumer=consumer, type=event.type, id=str(event.id))
        await _retry_or_dead_letter(message, consumer, retry_exchange)
        return
    log.info("event.handled" if ran else "event.duplicate", consumer=consumer, type=event.type)
    await message.ack()


async def run(consumer: str) -> None:
    configure_logging()
    handler = handlers(get_cache())[consumer]
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    async with connection:
        channel = await connection.channel(publisher_confirms=True)
        await channel.set_qos(prefetch_count=10)
        await topology.declare(channel)
        queue = await channel.get_queue(consumer)
        log.info("consumer.started", consumer=consumer)
        async with queue.iterator() as messages:
            async for message in messages:
                await process_message(message, consumer, handler, channel.default_exchange)


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in topology.BINDINGS:
        sys.exit(f"Usage: python -m app.events.consumers {{{','.join(topology.BINDINGS)}}}")
    asyncio.run(run(name))
