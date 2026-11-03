"""RabbitMQ topology: one topic exchange, a queue per consumer and a dead-letter queue.

Routing keys are the event types ("entry.create", "month.close", ...). Queues are
quorum queues with a dead-letter exchange. Consumers retry a failed message up to
MAX_ATTEMPTS times (an `x-attempts` header, see consumers.py) and then reject it
to the dead-letter queue. RabbitMQ 4 does not count a requeueing nack towards
x-delivery-limit, so that limit only catches consumers that crash mid-message.
"""

from aio_pika import ExchangeType
from aio_pika.abc import AbstractChannel, AbstractExchange

EXCHANGE = "finance.events"
DEAD_LETTER_EXCHANGE = "finance.events.dead"
DEAD_LETTER_QUEUE = "finance.events.dead"
MAX_ATTEMPTS = 5
DELIVERY_LIMIT = 10

# Consumer queue -> event types it receives.
BINDINGS: dict[str, tuple[str, ...]] = {
    "cache": ("entry.*", "income.*", "month.*", "label.*"),
    "limits": ("entry.*", "limit.*"),
    "goals": ("entry.*", "goal.*"),
}


async def declare(channel: AbstractChannel) -> AbstractExchange:
    """Declare everything (idempotent); returns the events exchange."""
    exchange = await channel.declare_exchange(EXCHANGE, ExchangeType.TOPIC, durable=True)
    dead = await channel.declare_exchange(DEAD_LETTER_EXCHANGE, ExchangeType.FANOUT, durable=True)
    dead_queue = await channel.declare_queue(
        DEAD_LETTER_QUEUE, durable=True, arguments={"x-queue-type": "quorum"}
    )
    await dead_queue.bind(dead)
    for name, patterns in BINDINGS.items():
        queue = await channel.declare_queue(
            name,
            durable=True,
            arguments={
                "x-queue-type": "quorum",
                "x-delivery-limit": DELIVERY_LIMIT,
                "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE,
            },
        )
        for pattern in patterns:
            await queue.bind(exchange, routing_key=pattern)
    return exchange
