"""Celery tasks. Celery is synchronous, so each task runs its async work with a
fresh event loop and an engine that does not outlive it."""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core import mail
from app.core.config import settings
from app.core.storage import get_storage
from app.services import demo, exports, recurring
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


@celery_app.task(
    name="app.workers.tasks.send_email",
    autoretry_for=(OSError,),  # SMTP down or refusing: try again later
    retry_backoff=True,
    max_retries=5,
)
def send_email(to: str, subject: str, body: str) -> None:
    mail.send(to, subject, body)


@celery_app.task(name="app.workers.tasks.run_export")
def run_export(export_id: str) -> str:
    """Build an export's file (see services/exports.py); returns its final status."""
    status = _run_with_session(
        lambda session: exports.build(session, get_storage(), uuid.UUID(export_id))
    )
    return status.value


@celery_app.task(name="app.workers.tasks.remove_expired_exports")
def remove_expired_exports() -> int:
    return _run_with_session(
        lambda session: exports.remove_expired(session, get_storage(), datetime.now(UTC))
    )


@celery_app.task(
    name="app.workers.tasks.delete_user_files",
    autoretry_for=(Exception,),  # storage down: the files must still go
    retry_backoff=True,
    max_retries=10,
)
def delete_user_files(user_id: str) -> int:
    """Remove every stored file of a deleted account (receipts and exports)."""
    return asyncio.run(get_storage().delete_prefix(f"users/{uuid.UUID(user_id)}/"))


@celery_app.task(name="app.workers.tasks.remove_expired_demos")
def remove_expired_demos() -> int:
    """Delete demo accounts older than 24 hours (see services/demo.py)."""
    return _run_with_session(
        lambda session: demo.remove_expired(session, get_storage(), datetime.now(UTC))
    )
