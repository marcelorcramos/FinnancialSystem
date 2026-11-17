"""A trace follows a write from the API, through the outbox, to the consumer (Phase 12)."""

import json
from collections.abc import AsyncIterator

import aio_pika
import pytest
from aio_pika.abc import AbstractChannel
from httpx import AsyncClient
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind
from prometheus_client import REGISTRY
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.events import relay, topology
from app.events.consumers import Event, process_message
from app.models import OutboxEvent
from tests.integration.helpers import create_month, new_user
from tests.tracing import spans  # noqa: F401  (fixture)


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
    return async_sessionmaker(
        bind=session.bind, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )


def consumed(consumer: str, outcome: str) -> float:
    value = REGISTRY.get_sample_value(
        "events_consumed_total", {"consumer": consumer, "outcome": outcome}
    )
    return value or 0.0


async def test_the_consumer_continues_the_trace_of_the_request(
    client: AsyncClient,
    session: AsyncSession,
    sessions: async_sessionmaker[AsyncSession],
    channel: AbstractChannel,
    spans: InMemorySpanExporter,  # noqa: F811
) -> None:
    user = await new_user(client)
    spans.clear()
    month = await create_month(client, user)
    # FastAPI's own server span for the request.
    (request_span,) = [s for s in spans.get_finished_spans() if s.kind is SpanKind.SERVER]
    assert request_span.attributes is not None
    assert request_span.attributes["http.route"] == "/api/v1/months"
    trace_id = request_span.context.trace_id

    event = await session.scalar(
        select(OutboxEvent).where(
            OutboxEvent.type == "month.create",
            OutboxEvent.payload["entity_id"].astext == month["id"],
        )
    )
    assert event is not None and event.trace_context is not None
    assert "traceparent" in event.trace_context

    published_before = REGISTRY.get_sample_value("outbox_events_published_total") or 0.0
    await relay.publish_pending(session, await channel.get_exchange(topology.EXCHANGE))
    assert (REGISTRY.get_sample_value("outbox_events_published_total") or 0) > published_before
    assert await relay.count_pending(session) == 0

    queue = await channel.get_queue("cache")
    message = None
    for _ in range(50):
        candidate = await queue.get(timeout=5)
        if json.loads(candidate.body)["id"] == str(event.id):
            message = candidate
            break
        await candidate.ack()
    assert message is not None and "traceparent" in (message.headers or {})

    handled_before = consumed("cache", "handled")

    async def handler(_: AsyncSession, __: Event) -> None:
        return None

    await process_message(message, "cache", handler, channel.default_exchange, sessions)
    assert consumed("cache", "handled") == handled_before + 1

    by_name = {s.name: s for s in spans.get_finished_spans()}
    publish = by_name["month.create publish"]
    process = by_name["month.create process"]
    assert publish.kind is SpanKind.PRODUCER and process.kind is SpanKind.CONSUMER
    assert publish.context.trace_id == trace_id
    assert process.context.trace_id == trace_id
    assert process.parent is not None and process.parent.span_id == publish.context.span_id


async def test_queries_become_spans_with_sqlalchemy_2_1(
    engine: AsyncEngine,
    spans: InMemorySpanExporter,  # noqa: F811
) -> None:
    """The instrumentation declares SQLAlchemy < 2.1; telemetry.setup_tracing skips that
    check, so this makes sure the spans still come, with placeholders instead of values."""
    instrumentor = SQLAlchemyInstrumentor()
    instrumentor.instrument(engine=engine.sync_engine, skip_dep_check=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(
                text("SELECT count(*) FROM users WHERE email = :email"), {"email": "a@b.c"}
            )
    finally:
        instrumentor.uninstrument()
    (query,) = [s for s in spans.get_finished_spans() if s.name == "SELECT"]
    assert query.attributes is not None
    statement = str(query.attributes["db.statement"])
    assert "users" in statement and "a@b.c" not in statement
