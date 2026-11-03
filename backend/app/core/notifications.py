"""Live notifications through Redis pub/sub (Phase 8).

Consumers run in their own processes, so they publish to a per-user channel and
the API process that holds the user's SSE connection relays it to the browser.
"""

import json
import uuid
from typing import Any

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

log = structlog.get_logger(__name__)


_subscriber: Redis | None = None


def subscriber_client() -> Redis:
    """Pool for long-lived subscriptions: no socket timeout (the cache pool has a short one)."""
    global _subscriber
    if _subscriber is None:
        _subscriber = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5)
    return _subscriber


def get_subscriber() -> Redis | None:
    return subscriber_client()


def alerts_channel(user_id: uuid.UUID) -> str:
    return f"alerts:{user_id}"


async def publish(redis: Redis | None, channel: str, message: dict[str, Any]) -> None:
    """Best effort: an alert is already saved, so a missed push only means a later refresh."""
    if redis is None:
        return
    try:
        await redis.publish(channel, json.dumps(message, default=str))
    except RedisError as error:
        log.warning("notifications.publish_failed", channel=channel, error=str(error))
