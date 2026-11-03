import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Limit


async def list_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[Limit]:
    stmt = select(Limit).where(Limit.user_id == user_id, Limit.deleted_at.is_(None))
    return list(await session.scalars(stmt.order_by(Limit.created_at)))


async def find(
    session: AsyncSession, user_id: uuid.UUID, label_id: uuid.UUID, month_id: uuid.UUID | None
) -> Limit | None:
    """The active default limit (month_id None) or month limit of a label."""
    stmt = select(Limit).where(
        Limit.user_id == user_id,
        Limit.label_id == label_id,
        Limit.month_id.is_(None) if month_id is None else Limit.month_id == month_id,
        Limit.deleted_at.is_(None),
    )
    return await session.scalar(stmt.with_for_update())


async def effective_for_month(
    session: AsyncSession, user_id: uuid.UUID, month_id: uuid.UUID
) -> dict[uuid.UUID, Limit]:
    """Per label, the month's own limit or else the default one."""
    stmt = select(Limit).where(
        Limit.user_id == user_id,
        Limit.deleted_at.is_(None),
        (Limit.month_id.is_(None)) | (Limit.month_id == month_id),
    )
    result: dict[uuid.UUID, Limit] = {}
    for limit in await session.scalars(stmt):
        if limit.month_id is not None or limit.label_id not in result:
            result[limit.label_id] = limit
    return result
