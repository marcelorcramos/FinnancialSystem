import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entry, Income


async def list_for_month(session: AsyncSession, month_id: uuid.UUID) -> list[Income]:
    stmt = select(Income).where(Income.month_id == month_id, Income.deleted_at.is_(None))
    return list(await session.scalars(stmt.order_by(Income.received_on, Income.created_at)))


async def get_for_user(
    session: AsyncSession, user_id: uuid.UUID, income_id: uuid.UUID, *, deleted: bool = False
) -> Income | None:
    stmt = select(Income).where(Income.id == income_id, Income.user_id == user_id)
    stmt = stmt.where(Income.deleted_at.is_not(None) if deleted else Income.deleted_at.is_(None))
    return await session.scalar(stmt.with_for_update())


async def ids_backing_additions(session: AsyncSession, month_id: uuid.UUID) -> set[uuid.UUID]:
    """Rendimentos criados por um `addition`: só se gerem através da entrada."""
    stmt = select(Entry.income_id).where(Entry.month_id == month_id, Entry.income_id.is_not(None))
    return {i for i in await session.scalars(stmt) if i is not None}
