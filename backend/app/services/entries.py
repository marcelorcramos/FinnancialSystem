"""Entry use cases: allocations, additions and transfers (section 2.2)."""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction, MovementType
from app.domain.errors import NotFoundError
from app.domain.money import ZERO
from app.domain.rules import ensure_date_in_month
from app.models import Entry, Income, User
from app.repositories import entries as entries_repo
from app.schemas.entry import DEFAULT_ADDITION_SOURCE, AdditionCreate, AllocationSet
from app.services import audit, labels, months

ENTITY = "entry"


async def set_allocation(
    session: AsyncSession,
    user: User,
    month_id: uuid.UUID,
    label_id: uuid.UUID,
    data: AllocationSet,
) -> Entry | None:
    """Create or update the label's allocation for the month. An amount of 0 removes it."""
    month = await months.get_open(session, user, month_id)
    if data.amount == ZERO:
        label = await labels.get(session, user, label_id)
        await _remove_allocation(session, user, month.id, label.id, missing_ok=True)
        await session.commit()
        return None

    label = await labels.get_usable(session, user, label_id)
    allocation = await entries_repo.active_allocation(session, month.id, label.id)
    if allocation is None:
        allocation = Entry(
            user_id=user.id,
            month_id=month.id,
            label_id=label.id,
            amount=data.amount,
            movement_type=MovementType.ALLOCATION,
            occurred_on=date(month.year, month.month, 1),
            note=data.note,
        )
        session.add(allocation)
        await session.flush()
        _log(session, user, allocation, AuditAction.CREATE)
    else:
        before = audit.snapshot(allocation)
        allocation.amount = data.amount
        allocation.note = data.note
        await session.flush()
        _log(session, user, allocation, AuditAction.UPDATE, before)
    await session.commit()
    return allocation


async def remove_allocation(
    session: AsyncSession, user: User, month_id: uuid.UUID, label_id: uuid.UUID
) -> None:
    month = await months.get_open(session, user, month_id)
    label = await labels.get(session, user, label_id)
    await _remove_allocation(session, user, month.id, label.id, missing_ok=False)
    await session.commit()


async def _remove_allocation(
    session: AsyncSession,
    user: User,
    month_id: uuid.UUID,
    label_id: uuid.UUID,
    *,
    missing_ok: bool,
) -> None:
    allocation = await entries_repo.active_allocation(session, month_id, label_id)
    if allocation is None:
        if missing_ok:
            return
        raise NotFoundError("This label has no allocation in this month")
    before = audit.snapshot(allocation)
    allocation.deleted_at = datetime.now(UTC)
    await session.flush()
    _log(session, user, allocation, AuditAction.DELETE, before)


async def add_money(
    session: AsyncSession, user: User, month_id: uuid.UUID, data: AdditionCreate
) -> tuple[Entry, Income]:
    """Create an `addition` and its income in one transaction (invariant 2.2.2)."""
    month = await months.get_open(session, user, month_id)
    label = await labels.get_usable(session, user, data.label_id)
    ensure_date_in_month(data.occurred_on, month.year, month.month)

    income = Income(
        user_id=user.id,
        month_id=month.id,
        source=data.source or DEFAULT_ADDITION_SOURCE,
        amount=data.amount,
        received_on=data.occurred_on,
        note=data.note,
    )
    session.add(income)
    await session.flush()
    entry = Entry(
        user_id=user.id,
        month_id=month.id,
        label_id=label.id,
        amount=data.amount,
        movement_type=MovementType.ADDITION,
        income_id=income.id,
        occurred_on=data.occurred_on,
        note=data.note,
    )
    session.add(entry)
    await session.flush()
    audit.log(session, user_id=user.id, entity="income", obj=income, action=AuditAction.CREATE)
    _log(session, user, entry, AuditAction.CREATE)
    await session.commit()
    return entry, income


def _log(
    session: AsyncSession,
    user: User,
    entry: Entry,
    action: AuditAction,
    before: dict[str, object] | None = None,
) -> None:
    audit.log(session, user_id=user.id, entity=ENTITY, obj=entry, action=action, before=before)
