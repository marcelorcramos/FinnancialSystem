"""Outbox relay: publishes pending outbox_events to RabbitMQ (Phase 7).

Run it as its own process: `python -m app.events.relay`. Several relays can run
at once (rows are locked with SKIP LOCKED). A crash after publishing but before
marking the row means the event is published again: consumers are idempotent.
"""

import asyncio
import json
from datetime import UTC, datetime

import aio_pika
import structlog
from aio_pika.abc import AbstractExchange
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.events import topology
from app.models import OutboxEvent

log = structlog.get_logger(__name__)

BATCH_SIZE = 100
IDLE_SECONDS = 1.0


async def publish_pending(
    session: AsyncSession, exchange: AbstractExchange, batch_size: int = BATCH_SIZE
) -> int:
    """Publish one batch of pending events, oldest first; returns how many."""
    stmt = (
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.created_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    events = list(await session.scalars(stmt))
    for event in events:
        body = {"id": str(event.id), "type": event.type, "payload": event.payload}
        await exchange.publish(
            aio_pika.Message(
                json.dumps(body).encode(),
                message_id=str(event.id),
                type=event.type,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=event.type,
        )
        event.published_at = datetime.now(UTC)
    await session.commit()
    return len(events)


async def run() -> None:
    configure_logging()
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    async with connection:
        channel = await connection.channel(publisher_confirms=True)
        exchange = await topology.declare(channel)
        log.info("relay.started")
        while True:
            async with SessionLocal() as session:
                published = await publish_pending(session, exchange)
            if published:
                log.info("relay.published", count=published)
            else:
                await asyncio.sleep(IDLE_SECONDS)


if __name__ == "__main__":
    asyncio.run(run())
