"""Celery tasks. Celery is synchronous, so each task runs its async work with a
fresh event loop and an engine that does not outlive it."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.services import recurring
from app.workers.celery_app import celery_app


def _run_with_session[T](work: Callable[[AsyncSession], Awaitable[T]]) -> T:
    async def main() -> T:
        engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                return await work(session)
        finally:
            await engine.dispose()

    return asyncio.run(main())


@celery_app.task(name="app.workers.tasks.create_due_months")
def create_due_months() -> int:
    """Start the new month for users with auto_new_month on (see services/recurring.py)."""
    return _run_with_session(
        lambda session: recurring.create_due_months(session, datetime.now(UTC))
    )
