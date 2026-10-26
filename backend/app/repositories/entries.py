import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import MovementType
from app.models import Entry, Month


async def list_active_for_label(session: AsyncSession, label_id: uuid.UUID) -> list[Entry]:
    stmt = select(Entry).where(Entry.label_id == label_id, Entry.deleted_at.is_(None))
    return list(await session.scalars(stmt.with_for_update()))


async def active_allocation(
    session: AsyncSession, month_id: uuid.UUID, label_id: uuid.UUID
) -> Entry | None:
    stmt = select(Entry).where(
        Entry.month_id == month_id,
        Entry.label_id == label_id,
        Entry.movement_type == MovementType.ALLOCATION,
        Entry.deleted_at.is_(None),
    )
    return await session.scalar(stmt.with_for_update())


async def transfer_legs(session: AsyncSession, transfer_id: uuid.UUID) -> list[Entry]:
    stmt = select(Entry).where(Entry.transfer_id == transfer_id).order_by(Entry.movement_type)
    return list(await session.scalars(stmt.with_for_update()))


async def active_transfer_legs(
    session: AsyncSession, user_id: uuid.UUID, transfer_id: uuid.UUID
) -> dict[MovementType, Entry]:
    """The active legs of a user's transfer, keyed by movement type."""
    stmt = select(Entry).where(
        Entry.transfer_id == transfer_id,
        Entry.user_id == user_id,
        Entry.deleted_at.is_(None),
    )
    return {leg.movement_type: leg for leg in await session.scalars(stmt.with_for_update())}


async def get_for_user(
    session: AsyncSession, user_id: uuid.UUID, entry_id: uuid.UUID, *, deleted: bool = False
) -> Entry | None:
    stmt = select(Entry).where(Entry.id == entry_id, Entry.user_id == user_id)
    stmt = stmt.where(Entry.deleted_at.is_not(None) if deleted else Entry.deleted_at.is_(None))
    return await session.scalar(stmt.with_for_update())


async def list_active_for_month(session: AsyncSession, month_id: uuid.UUID) -> list[Entry]:
    stmt = (
        select(Entry)
        .where(Entry.month_id == month_id, Entry.deleted_at.is_(None))
        .order_by(Entry.occurred_on, Entry.created_at, Entry.movement_type)
    )
    return list(await session.scalars(stmt))


async def closed_months_with_label_entries(
    session: AsyncSession, label_id: uuid.UUID
) -> list[Month]:
    stmt = (
        select(Month)
        .join(Entry, Entry.month_id == Month.id)
        .where(
            Entry.label_id == label_id,
            Entry.deleted_at.is_(None),
            Month.closed_at.is_not(None),
        )
        .distinct()
    )
    return list(await session.scalars(stmt))
