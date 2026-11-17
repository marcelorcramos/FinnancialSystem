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
from opentelemetry import propagate
from opentelemetry.trace import SpanKind
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import metrics, telemetry
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
        # Continue the trace of the request that wrote the event; the consumer picks
        # it up from the message headers.
        with telemetry.tracer.start_as_current_span(
            f"{event.type} publish",
            context=telemetry.context_from(event.trace_context),
            kind=SpanKind.PRODUCER,
            attributes={"messaging.system": "rabbitmq", "messaging.message.id": str(event.id)},
        ):
            headers: dict[str, str] = {}
            propagate.inject(headers)
            await exchange.publish(
                aio_pika.Message(
                    json.dumps(body).encode(),
                    headers=dict(headers),
                    message_id=str(event.id),
                    type=event.type,
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=event.type,
            )
        event.published_at = datetime.now(UTC)
    await session.commit()
    metrics.OUTBOX_PUBLISHED.inc(len(events))
    return len(events)


async def count_pending(session: AsyncSession) -> int:
    """Events still waiting (the relay's backlog), read with the partial index."""
    stmt = select(func.count()).select_from(OutboxEvent).where(OutboxEvent.published_at.is_(None))
    return int(await session.scalar(stmt) or 0)


async def run() -> None:
    configure_logging()
    telemetry.setup_error_reporting("relay")
    telemetry.setup_tracing("relay")
    metrics.serve(settings.METRICS_PORT)
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    async with connection:
        channel = await connection.channel(publisher_confirms=True)
        exchange = await topology.declare(channel)
        log.info("relay.started")
        while True:
            async with SessionLocal() as session:
                published = await publish_pending(session, exchange)
                metrics.OUTBOX_PENDING.set(await count_pending(session))
            if published:
                log.info("relay.published", count=published)
            else:
                await asyncio.sleep(IDLE_SECONDS)


if __name__ == "__main__":
    asyncio.run(run())
