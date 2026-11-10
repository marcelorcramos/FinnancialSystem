import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ExportStatus
from app.models import Export


async def get_for_user(
    session: AsyncSession, user_id: uuid.UUID, export_id: uuid.UUID
) -> Export | None:
    stmt = select(Export).where(Export.id == export_id, Export.user_id == user_id)
    return await session.scalar(stmt)


async def get_for_update(session: AsyncSession, export_id: uuid.UUID) -> Export | None:
    """The worker's read: by id only, from the task it was handed."""
    stmt = select(Export).where(Export.id == export_id).with_for_update()
    return await session.scalar(stmt)


async def recent_for_user(session: AsyncSession, user_id: uuid.UUID, limit: int) -> list[Export]:
    stmt = (
        select(Export)
        .where(Export.user_id == user_id)
        .order_by(Export.created_at.desc(), Export.id)
        .limit(limit)
    )
    return list(await session.scalars(stmt))


async def count_pending(session: AsyncSession, user_id: uuid.UUID) -> int:
    stmt = select(func.count()).where(
        Export.user_id == user_id, Export.status == ExportStatus.PENDING
    )
    return int(await session.scalar(stmt) or 0)


async def expired_ready(session: AsyncSession, now: datetime) -> list[Export]:
    stmt = (
        select(Export)
        .where(Export.status == ExportStatus.READY, Export.expires_at <= now)
        .with_for_update(skip_locked=True)
    )
    return list(await session.scalars(stmt))
