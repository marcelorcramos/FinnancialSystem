"""Entry use cases: allocations, additions and transfers (section 2.2)."""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction, MovementType
from app.domain.errors import NotFoundError
from app.domain.money import ZERO
from app.domain.rules import ensure_date_in_month, ensure_distinct_labels
from app.domain.transfers import plan_transfer
from app.models import Entry, Income, User
from app.repositories import entries as entries_repo
from app.schemas.entry import (
    DEFAULT_ADDITION_SOURCE,
    AdditionCreate,
    AllocationSet,
    TransferCreate,
    TransferRead,
    TransferUpdate,
)
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


async def create_transfer(
    session: AsyncSession, user: User, month_id: uuid.UUID, data: TransferCreate
) -> TransferRead:
    """Create both legs of a transfer in one transaction (invariant 2.2.3)."""
    month = await months.get_open(session, user, month_id)
    source = await labels.get_usable(session, user, data.from_label_id)
    target = await labels.get_usable(session, user, data.to_label_id)
    plan = plan_transfer(source.id, target.id, data.amount)
    ensure_date_in_month(data.occurred_on, month.year, month.month)

    transfer_id = uuid.uuid4()
    legs = [
        Entry(
            user_id=user.id,
            month_id=month.id,
            label_id=leg.label_id,
            amount=leg.amount,
            movement_type=leg.movement_type,
            transfer_id=transfer_id,
            occurred_on=data.occurred_on,
            note=data.note,
        )
        for leg in (plan.out_leg, plan.in_leg)
    ]
    session.add_all(legs)
    await session.flush()
    for leg in legs:
        _log(session, user, leg, AuditAction.CREATE)
    await session.commit()
    return _transfer_read(legs[0], legs[1])


async def update_transfer(
    session: AsyncSession, user: User, transfer_id: uuid.UUID, data: TransferUpdate
) -> TransferRead:
    """Edit a transfer: amount, date and note change on both legs (invariant 2.2.4)."""
    out_leg, in_leg = await _transfer_legs(session, user, transfer_id)
    month = await months.get_open(session, user, out_leg.month_id)
    changes = data.model_dump(exclude_unset=True)

    from_label_id = changes.get("from_label_id") or out_leg.label_id
    to_label_id = changes.get("to_label_id") or in_leg.label_id
    if from_label_id != out_leg.label_id:
        from_label_id = (await labels.get_usable(session, user, from_label_id)).id
    if to_label_id != in_leg.label_id:
        to_label_id = (await labels.get_usable(session, user, to_label_id)).id
    ensure_distinct_labels(from_label_id, to_label_id)

    occurred_on = changes.get("occurred_on") or out_leg.occurred_on
    ensure_date_in_month(occurred_on, month.year, month.month)
    amount = changes.get("amount") or out_leg.amount
    note = changes.get("note", out_leg.note)

    for leg, label_id in ((out_leg, from_label_id), (in_leg, to_label_id)):
        before = audit.snapshot(leg)
        leg.label_id, leg.amount, leg.occurred_on, leg.note = label_id, amount, occurred_on, note
        await session.flush()
        _log(session, user, leg, AuditAction.UPDATE, before)
    await session.commit()
    return _transfer_read(out_leg, in_leg)


async def _transfer_legs(
    session: AsyncSession, user: User, transfer_id: uuid.UUID
) -> tuple[Entry, Entry]:
    legs = await entries_repo.active_transfer_legs(session, user.id, transfer_id)
    out_leg = legs.get(MovementType.TRANSFER_OUT)
    in_leg = legs.get(MovementType.TRANSFER_IN)
    if out_leg is None or in_leg is None:
        raise NotFoundError("Transfer not found")
    return out_leg, in_leg


def _transfer_read(out_leg: Entry, in_leg: Entry) -> TransferRead:
    assert out_leg.transfer_id is not None
    return TransferRead(
        transfer_id=out_leg.transfer_id,
        month_id=out_leg.month_id,
        from_label_id=out_leg.label_id,
        to_label_id=in_leg.label_id,
        amount=out_leg.amount,
        occurred_on=out_leg.occurred_on,
        note=out_leg.note,
        out_entry_id=out_leg.id,
        in_entry_id=in_leg.id,
    )


def _log(
    session: AsyncSession,
    user: User,
    entry: Entry,
    action: AuditAction,
    before: dict[str, object] | None = None,
) -> None:
    audit.log(session, user_id=user.id, entity=ENTITY, obj=entry, action=action, before=before)
