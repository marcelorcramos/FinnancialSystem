from collections.abc import AsyncIterator
from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import Cache, get_cache
from app.core.jobs import JobQueue, get_job_queue
from app.core.rate_limit import RateLimiter, get_rate_limiter
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import User
from app.repositories import users

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# OAuth2 password flow only so the Swagger (/docs) Authorize button asks for email and password.
# The app uses POST /auth/login (JSON); both return the same access token.
_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


async def get_current_user(
    session: SessionDep, token: Annotated[str | None, Depends(_oauth2)]
) -> User:
    user_id = decode_access_token(token) if token else None
    user = await users.get_active_by_id(session, user_id) if user_id else None
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_today(user: CurrentUser) -> date:
    """Today in the user's time zone: the reference for rolling report windows."""
    return datetime.now(ZoneInfo(user.timezone)).date()


Today = Annotated[date, Depends(get_today)]


CacheDep = Annotated[Cache, Depends(get_cache)]

_READS = {"GET", "HEAD", "OPTIONS"}


async def _invalidate_cache_after_writes(
    request: Request, user: CurrentUser, cache: CacheDep
) -> AsyncIterator[None]:
    yield
    # Only reached when the handler succeeded; runs before the response is sent,
    # so the client's next read already misses the stale cache.
    if request.method not in _READS:
        await cache.invalidate(user.id)


InvalidatesCache = Depends(_invalidate_cache_after_writes, scope="function")
"""Router dependency for routes that change a user's money: clears their read cache."""


RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]
JobsDep = Annotated[JobQueue, Depends(get_job_queue)]


def client_ip(request: Request) -> str:
    """The caller's address (Uvicorn resolves X-Forwarded-For from trusted proxies)."""
    return request.client.host if request.client else "unknown"
