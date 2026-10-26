import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Month


async def list_for_user(session: AsyncSession, user_id: uuid.UUID, year: int | None) -> list[Month]:
    stmt = select(Month).where(Month.user_id == user_id, Month.deleted_at.is_(None))
    if year is not None:
        stmt = stmt.where(Month.year == year)
    return list(await session.scalars(stmt.order_by(Month.year.desc(), Month.month.desc())))


async def get_for_user(
    session: AsyncSession, user_id: uuid.UUID, month_id: uuid.UUID, *, deleted: bool = False
) -> Month | None:
    stmt = select(Month).where(Month.id == month_id, Month.user_id == user_id)
    stmt = stmt.where(Month.deleted_at.is_not(None) if deleted else Month.deleted_at.is_(None))
    return await session.scalar(stmt.with_for_update())


async def find_active(
    session: AsyncSession, user_id: uuid.UUID, year: int, month: int
) -> Month | None:
    stmt = select(Month).where(
        Month.user_id == user_id,
        Month.year == year,
        Month.month == month,
        Month.deleted_at.is_(None),
    )
    return await session.scalar(stmt)


async def latest_before(
    session: AsyncSession, user_id: uuid.UUID, year: int, month: int
) -> Month | None:
    stmt = (
        select(Month)
        .where(
            Month.user_id == user_id,
            Month.deleted_at.is_(None),
            Month.year * 12 + Month.month < year * 12 + month,
        )
        .order_by(Month.year.desc(), Month.month.desc())
        .limit(1)
    )
    return await session.scalar(stmt)
