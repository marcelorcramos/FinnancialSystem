"""Rate limiting of the auth routes in Redis (Phase 7): fixed windows per IP and per email.

Like the cache, it fails open: without Redis, requests are not limited.
"""

import hashlib
from dataclasses import dataclass

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.cache import redis_client
from app.domain.errors import RateLimitedError

log = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Limit:
    name: str
    requests: int
    window_seconds: int


LOGIN_PER_IP = Limit("login-ip", 20, 60)
LOGIN_PER_EMAIL = Limit("login-email", 10, 300)
REGISTER_PER_IP = Limit("register-ip", 30, 3600)
REFRESH_PER_IP = Limit("refresh-ip", 60, 60)


class RateLimiter:
    def __init__(self, redis: Redis | None) -> None:
        self.redis = redis

    async def hit(self, limit: Limit, subject: str) -> None:
        """Count one request; raise RateLimitedError when the window is full."""
        if self.redis is None:
            return
        # Emails are hashed so the keys do not store personal data.
        digest = hashlib.sha256(subject.lower().encode()).hexdigest()[:24]
        key = f"ratelimit:{limit.name}:{digest}"
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, limit.window_seconds, nx=True)
                pipe.ttl(key)
                count, _, ttl = await pipe.execute()
        except RedisError as error:
            log.warning("rate_limit.unavailable", error=str(error))
            return
        if count > limit.requests:
            raise RateLimitedError(retry_after=max(int(ttl), 1))


def get_rate_limiter() -> RateLimiter:
    return RateLimiter(redis_client())
