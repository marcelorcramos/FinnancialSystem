"""Month use cases (section 2.3)."""

import calendar
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction, MovementType
from app.domain.errors import ConflictError, NotFoundError
from app.domain.rules import ensure_month_open
from app.models import Entry, Income, Label, Month, User
from app.repositories import incomes as incomes_repo
from app.repositories import months as months_repo
from app.schemas.month import MonthCreate, MonthUpdate
from app.services import audit

ENTITY = "month"


async def get(session: AsyncSession, user: User, month_id: uuid.UUID) -> Month:
    month = await months_repo.get_for_user(session, user.id, month_id)
    if month is None:
        raise NotFoundError("Month not found")
    return month


async def get_open(session: AsyncSession, user: User, month_id: uuid.UUID) -> Month:
    month = await get(session, user, month_id)
    ensure_month_open(month.closed_at)
    return month


async def create(session: AsyncSession, user: User, data: MonthCreate) -> Month:
    await _ensure_free(session, user, data.year, data.month)
    month = Month(user_id=user.id, year=data.year, month=data.month, note=data.note)
    session.add(month)
    await session.flush()
    _log(session, user, month, AuditAction.CREATE)

    if data.copy_allocations or data.copy_incomes:
        previous = await months_repo.latest_before(session, user.id, data.year, data.month)
        if previous is not None:
            if data.copy_allocations:
                await _copy_allocations(session, user, previous, month)
            if data.copy_incomes:
                await _copy_incomes(session, user, previous, month)
    await session.commit()
    return month


async def update(
    session: AsyncSession, user: User, month_id: uuid.UUID, data: MonthUpdate
) -> Month:
    month = await get_open(session, user, month_id)
    before = audit.snapshot(month)
    if "note" in data.model_fields_set:
        month.note = data.note or None
    await session.flush()
    _log(session, user, month, AuditAction.UPDATE, before)
    await session.commit()
    return month


async def set_closed(
    session: AsyncSession, user: User, month_id: uuid.UUID, *, closed: bool
) -> Month:
    month = await get(session, user, month_id)
    if (month.closed_at is not None) == closed:
        return month
    before = audit.snapshot(month)
    month.closed_at = datetime.now(UTC) if closed else None
    await session.flush()
    _log(session, user, month, AuditAction.UPDATE, before)
    await session.commit()
    return month


async def delete(session: AsyncSession, user: User, month_id: uuid.UUID) -> None:
    """Soft delete: entries and incomes are hidden with the month and come back on restore."""
    month = await get_open(session, user, month_id)
    before = audit.snapshot(month)
    month.deleted_at = datetime.now(UTC)
    await session.flush()
    _log(session, user, month, AuditAction.DELETE, before)
    await session.commit()


async def restore(session: AsyncSession, user: User, month_id: uuid.UUID) -> Month:
    month = await months_repo.get_for_user(session, user.id, month_id, deleted=True)
    if month is None:
        raise NotFoundError("Month not found")
    await _ensure_free(session, user, month.year, month.month)
    month.deleted_at = None
    await session.flush()
    _log(session, user, month, AuditAction.RESTORE)
    await session.commit()
    return month


async def _copy_allocations(
    session: AsyncSession, user: User, source: Month, target: Month
) -> None:
    stmt = (
        select(Entry)
        .join(Label, Label.id == Entry.label_id)
        .where(
            Entry.month_id == source.id,
            Entry.movement_type == MovementType.ALLOCATION,
            Entry.deleted_at.is_(None),
            Label.deleted_at.is_(None),
            Label.archived_at.is_(None),
        )
    )
    for previous in await session.scalars(stmt):
        entry = Entry(
            user_id=user.id,
            month_id=target.id,
            label_id=previous.label_id,
            amount=previous.amount,
            movement_type=MovementType.ALLOCATION,
            occurred_on=date(target.year, target.month, 1),
            note=previous.note,
        )
        session.add(entry)
        await session.flush()
        audit.log(session, user_id=user.id, entity="entry", obj=entry, action=AuditAction.CREATE)


async def _copy_incomes(session: AsyncSession, user: User, source: Month, target: Month) -> None:
    # Incomes from "add money" are one-offs: they are not copied.
    from_additions = await incomes_repo.ids_backing_additions(session, source.id)
    last_day = calendar.monthrange(target.year, target.month)[1]
    for previous in await incomes_repo.list_for_month(session, source.id):
        if previous.id in from_additions:
            continue
        income = Income(
            user_id=user.id,
            month_id=target.id,
            source=previous.source,
            amount=previous.amount,
            received_on=date(target.year, target.month, min(previous.received_on.day, last_day)),
            note=previous.note,
        )
        session.add(income)
        await session.flush()
        audit.log(session, user_id=user.id, entity="income", obj=income, action=AuditAction.CREATE)


async def _ensure_free(session: AsyncSession, user: User, year: int, month: int) -> None:
    if await months_repo.find_active(session, user.id, year, month):
        raise ConflictError(f"Month {year}-{month:02d} already exists")


def _log(
    session: AsyncSession,
    user: User,
    month: Month,
    action: AuditAction,
    before: dict[str, object] | None = None,
) -> None:
    audit.log(session, user_id=user.id, entity=ENTITY, obj=month, action=action, before=before)
