"""Entry use cases: allocations, additions and transfers (section 2.2)."""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction, MovementType
from app.domain.errors import ConflictError, NotFoundError, ValidationError
from app.domain.money import ZERO
from app.domain.rules import ensure_date_in_month, ensure_distinct_labels
from app.domain.transfers import plan_transfer
from app.models import Entry, Income, Label, Month, User
from app.repositories import entries as entries_repo
from app.repositories import incomes as incomes_repo
from app.repositories import labels as labels_repo
from app.schemas.entry import (
    DEFAULT_ADDITION_SOURCE,
    AdditionCreate,
    AllocationSet,
    EntryListItem,
    EntryRead,
    EntryUpdate,
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


async def list_for_month(
    session: AsyncSession, user: User, month_id: uuid.UUID
) -> list[EntryListItem]:
    """The month's entries by date, each with its origin (invariant 2.2.9)."""
    month = await months.get(session, user, month_id)
    rows = await entries_repo.list_active_for_month(session, month.id)
    sources = {i.id: i.source for i in await incomes_repo.list_for_month(session, month.id)}
    legs: dict[uuid.UUID, dict[MovementType, uuid.UUID]] = {}
    for row in rows:
        if row.transfer_id is not None:
            legs.setdefault(row.transfer_id, {})[row.movement_type] = row.label_id
    return [list_item(row, sources, legs) for row in rows]


def list_item(
    row: Entry,
    sources: dict[uuid.UUID, str],
    legs: dict[uuid.UUID, dict[MovementType, uuid.UUID]],
) -> EntryListItem:
    """An entry with its origin: income source of an addition, other label of a transfer."""
    base = EntryRead.model_validate(row).model_dump()
    if row.movement_type is MovementType.ALLOCATION:
        return EntryListItem(**base, origin="initial_distribution")
    if row.movement_type is MovementType.ADDITION:
        source = sources.get(row.income_id) if row.income_id else None
        return EntryListItem(**base, origin="external_income", source=source)
    assert row.transfer_id is not None
    other = (
        MovementType.TRANSFER_OUT
        if row.movement_type is MovementType.TRANSFER_IN
        else MovementType.TRANSFER_IN
    )
    return EntryListItem(
        **base,
        origin=row.movement_type.value,
        counterpart_label_id=legs.get(row.transfer_id, {}).get(other),
    )


async def update_entry(
    session: AsyncSession, user: User, entry_id: uuid.UUID, data: EntryUpdate
) -> Entry:
    """Edit an allocation or an addition; an addition keeps its income in sync."""
    entry = await _get_entry(session, user, entry_id)
    month = await months.get_open(session, user, entry.month_id)
    changes = data.model_dump(exclude_unset=True)

    if entry.transfer_id is not None:
        raise ValidationError("Transfers are edited through /transfers/{transfer_id}")
    if entry.movement_type is MovementType.ALLOCATION:
        not_allowed = changes.keys() - {"amount", "note"}
        if not_allowed:
            raise ValidationError(
                f"An allocation only accepts amount and note (got {', '.join(sorted(not_allowed))})"
            )

    before = audit.snapshot(entry)
    if changes.get("amount") is not None:
        entry.amount = changes["amount"]
    if "note" in changes:
        entry.note = changes["note"]
    if changes.get("occurred_on") is not None:
        ensure_date_in_month(changes["occurred_on"], month.year, month.month)
        entry.occurred_on = changes["occurred_on"]
    if changes.get("label_id") is not None and changes["label_id"] != entry.label_id:
        entry.label_id = (await labels.get_usable(session, user, changes["label_id"])).id

    if entry.movement_type is MovementType.ADDITION:
        await _sync_income(session, user, entry, changes.get("source"))
    await session.flush()
    _log(session, user, entry, AuditAction.UPDATE, before)
    await session.commit()
    return entry


async def delete_entry(session: AsyncSession, user: User, entry_id: uuid.UUID) -> None:
    """Soft delete. A transfer leg takes the other leg along; an addition takes its income."""
    entry = await _get_entry(session, user, entry_id)
    await months.get_open(session, user, entry.month_id)
    now = datetime.now(UTC)
    for item in await _linked_entries(session, user, entry, deleted=False):
        before = audit.snapshot(item)
        item.deleted_at = now
        await session.flush()
        _log(session, user, item, AuditAction.DELETE, before)
    if entry.income_id is not None:
        income = await incomes_repo.get_for_user(session, user.id, entry.income_id)
        if income is not None:
            income_before = audit.snapshot(income)
            income.deleted_at = now
            await session.flush()
            audit.log(
                session,
                user_id=user.id,
                entity="income",
                obj=income,
                action=AuditAction.DELETE,
                before=income_before,
            )
    await session.commit()


async def restore_entry(session: AsyncSession, user: User, entry_id: uuid.UUID) -> Entry:
    """Undo a delete, bringing back the other transfer leg or the addition's income too."""
    entry = await entries_repo.get_for_user(session, user.id, entry_id, deleted=True)
    if entry is None:
        raise NotFoundError("Entry not found")
    month = await months.get_open(session, user, entry.month_id)
    restored = await _linked_entries(session, user, entry, deleted=True)
    for item in restored:
        await _ensure_restorable(session, user, month, item)
    for item in restored:
        item.deleted_at = None
        await session.flush()
        _log(session, user, item, AuditAction.RESTORE)
    if entry.income_id is not None:
        income = await incomes_repo.get_for_user(session, user.id, entry.income_id, deleted=True)
        if income is not None:
            income.deleted_at = None
            await session.flush()
            audit.log(
                session, user_id=user.id, entity="income", obj=income, action=AuditAction.RESTORE
            )
    await session.commit()
    return entry


async def delete_transfer(session: AsyncSession, user: User, transfer_id: uuid.UUID) -> None:
    out_leg, _ = await _transfer_legs(session, user, transfer_id)
    await delete_entry(session, user, out_leg.id)


async def restore_transfer(
    session: AsyncSession, user: User, transfer_id: uuid.UUID
) -> TransferRead:
    legs = await entries_repo.transfer_legs(session, transfer_id)
    deleted = [leg for leg in legs if leg.user_id == user.id and leg.deleted_at is not None]
    if len(deleted) != 2:
        raise NotFoundError("Transfer not found")
    await restore_entry(session, user, deleted[0].id)
    return _transfer_read(*await _transfer_legs(session, user, transfer_id))


async def _get_entry(session: AsyncSession, user: User, entry_id: uuid.UUID) -> Entry:
    entry = await entries_repo.get_for_user(session, user.id, entry_id)
    if entry is None:
        raise NotFoundError("Entry not found")
    return entry


async def _linked_entries(
    session: AsyncSession, user: User, entry: Entry, *, deleted: bool
) -> list[Entry]:
    """The entry plus, for a transfer, its other leg in the same state."""
    if entry.transfer_id is None:
        return [entry]
    legs = await entries_repo.transfer_legs(session, entry.transfer_id)
    return [
        leg for leg in legs if leg.user_id == user.id and (leg.deleted_at is not None) == deleted
    ]


async def _ensure_restorable(session: AsyncSession, user: User, month: Month, entry: Entry) -> None:
    label: Label | None = await labels_repo.get_for_user(session, user.id, entry.label_id)
    if label is None:
        raise ConflictError("The entry's label was deleted; restore the label first")
    if entry.movement_type is MovementType.ALLOCATION and await entries_repo.active_allocation(
        session, month.id, entry.label_id
    ):
        raise ConflictError("This label already has another allocation in this month")


async def _sync_income(session: AsyncSession, user: User, entry: Entry, source: str | None) -> None:
    assert entry.income_id is not None
    income = await incomes_repo.get_for_user(session, user.id, entry.income_id)
    if income is None:
        return
    before = audit.snapshot(income)
    income.amount, income.received_on, income.note = entry.amount, entry.occurred_on, entry.note
    if source is not None:
        income.source = source
    await session.flush()
    audit.log(
        session,
        user_id=user.id,
        entity="income",
        obj=income,
        action=AuditAction.UPDATE,
        before=before,
    )


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
