import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entry, Label


async def list_for_user(
    session: AsyncSession, user_id: uuid.UUID, *, include_archived: bool
) -> list[Label]:
    stmt = select(Label).where(Label.user_id == user_id, Label.deleted_at.is_(None))
    if not include_archived:
        stmt = stmt.where(Label.archived_at.is_(None))
    return list(await session.scalars(stmt.order_by(Label.kind, Label.name)))


async def get_for_user(
    session: AsyncSession, user_id: uuid.UUID, label_id: uuid.UUID, *, deleted: bool = False
) -> Label | None:
    stmt = select(Label).where(Label.id == label_id, Label.user_id == user_id)
    stmt = stmt.where(Label.deleted_at.is_not(None) if deleted else Label.deleted_at.is_(None))
    return await session.scalar(stmt)


async def name_taken(
    session: AsyncSession, user_id: uuid.UUID, name: str, *, exclude_id: uuid.UUID | None = None
) -> bool:
    stmt = select(Label.id).where(
        Label.user_id == user_id,
        func.lower(Label.name) == name.lower(),
        Label.deleted_at.is_(None),
    )
    if exclude_id is not None:
        stmt = stmt.where(Label.id != exclude_id)
    return await session.scalar(stmt.limit(1)) is not None


async def count_active_entries(session: AsyncSession, label_id: uuid.UUID) -> int:
    stmt = select(func.count()).where(Entry.label_id == label_id, Entry.deleted_at.is_(None))
    return await session.scalar(stmt) or 0
