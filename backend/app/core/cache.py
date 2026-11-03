"""Read cache for summaries and reports in Redis, keyed by user (Phase 7).

Each user has a version number; cached keys include it, so invalidating a
user's cache is one INCR and the old keys simply expire. Redis is a
convenience: when it is down, reads go to PostgreSQL and nothing fails.
"""

import hashlib
import json
import uuid
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import structlog
from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

log = structlog.get_logger(__name__)

TTL_SECONDS = 3600


def _version_key(user_id: uuid.UUID) -> str:
    return f"cache:{user_id}:version"


def _key(user_id: uuid.UUID, version: int, name: str, params: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[
        :16
    ]
    return f"cache:{user_id}:v{version}:{name}:{digest}"


class Cache:
    """Per-user JSON cache of Pydantic responses. `redis=None` disables it."""

    def __init__(self, redis: Redis | None) -> None:
        self.redis = redis

    async def get_or_set[M: BaseModel](
        self,
        user_id: uuid.UUID,
        name: str,
        params: Mapping[str, Any],
        model: type[M],
        compute: Callable[[], Awaitable[M]],
    ) -> M:
        if self.redis is None:
            return await compute()
        try:
            version = int(await self.redis.get(_version_key(user_id)) or 0)
            key = _key(user_id, version, name, params)
            cached = await self.redis.get(key)
            if cached is not None:
                return model.model_validate_json(cached)
        except RedisError as error:
            log.warning("cache.read_failed", error=str(error))
            return await compute()

        value = await compute()
        try:
            await self.redis.set(key, value.model_dump_json(), ex=TTL_SECONDS)
        except RedisError as error:
            log.warning("cache.write_failed", error=str(error))
        return value

    async def invalidate(self, user_id: uuid.UUID) -> None:
        """Make every cached read of this user stale (idempotent in effect)."""
        if self.redis is None:
            return
        try:
            await self.redis.incr(_version_key(user_id))
        except RedisError as error:
            log.warning("cache.invalidate_failed", error=str(error))


_redis: Redis | None = None


def redis_client() -> Redis:
    """One connection pool per process, created on first use."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
    return _redis


def get_cache() -> Cache:
    return Cache(redis_client())
