import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Attachment, Entry


async def list_for_month(
    session: AsyncSession, user_id: uuid.UUID, month_id: uuid.UUID, entry_id: uuid.UUID | None
) -> list[Attachment]:
    """Active receipts of a month, oldest first; those of deleted entries are hidden."""
    stmt = (
        select(Attachment)
        .outerjoin(Entry, Entry.id == Attachment.entry_id)
        .where(
            Attachment.user_id == user_id,
            Attachment.month_id == month_id,
            Attachment.deleted_at.is_(None),
            or_(Attachment.entry_id.is_(None), Entry.deleted_at.is_(None)),
        )
        .order_by(Attachment.created_at, Attachment.id)
    )
    if entry_id is not None:
        stmt = stmt.where(Attachment.entry_id == entry_id)
    return list(await session.scalars(stmt))


async def get_for_user(
    session: AsyncSession, user_id: uuid.UUID, attachment_id: uuid.UUID, *, deleted: bool = False
) -> Attachment | None:
    stmt = select(Attachment).where(Attachment.id == attachment_id, Attachment.user_id == user_id)
    stmt = stmt.where(
        Attachment.deleted_at.is_not(None) if deleted else Attachment.deleted_at.is_(None)
    )
    return await session.scalar(stmt)


async def list_all_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[Attachment]:
    """Every receipt of the user, deleted ones included (data export)."""
    stmt = select(Attachment).where(Attachment.user_id == user_id).order_by(Attachment.created_at)
    return list(await session.scalars(stmt))
