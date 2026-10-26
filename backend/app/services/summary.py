"""Month summary: totals per label and kind, income and unallocated (section 2.2)."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import ledger
from app.domain.enums import LabelKind
from app.domain.ledger import LabelBreakdown, Movement
from app.domain.money import ZERO
from app.models import Label, User
from app.repositories import entries as entries_repo
from app.repositories import incomes as incomes_repo
from app.repositories import labels as labels_repo
from app.schemas.summary import LabelSummary, MonthSummary
from app.services import months

_KIND_ORDER = {LabelKind.EXPENSE: 0, LabelKind.SAVING: 1, LabelKind.INVESTMENT: 2}


async def month_summary(session: AsyncSession, user: User, month_id: uuid.UUID) -> MonthSummary:
    month = await months.get(session, user, month_id)
    entries = await entries_repo.list_active_for_month(session, month.id)
    movements = [Movement(e.label_id, e.movement_type, e.amount) for e in entries]
    income_total = sum(
        (i.amount for i in await incomes_repo.list_for_month(session, month.id)), ZERO
    )

    breakdowns = ledger.breakdown_by_label(movements)
    # Every usable label is shown (even at zero); archived ones only when they have movements.
    labels: dict[uuid.UUID, Label] = {
        label.id: label
        for label in await labels_repo.list_for_user(session, user.id, include_archived=True)
        if label.archived_at is None or label.id in breakdowns
    }
    for label_id in breakdowns.keys() - labels.keys():  # e.g. a label deleted after reassignment
        if (label := await session.get(Label, label_id)) is not None:
            labels[label_id] = label

    rows = sorted(
        (
            _label_summary(label, breakdowns.get(label.id, LabelBreakdown()))
            for label in labels.values()
        ),
        key=lambda r: (_KIND_ORDER[r.kind], r.name.lower()),
    )
    totals = {row.label_id: row.total for row in rows}
    unallocated = ledger.unallocated(income_total, movements)
    return MonthSummary(
        month_id=month.id,
        year=month.year,
        month=month.month,
        closed_at=month.closed_at,
        income_total=income_total,
        distributed=ledger.distributed(movements),
        unallocated=unallocated,
        over_allocated=unallocated < ZERO,
        month_total=ledger.month_total(movements),
        by_kind=ledger.totals_by_kind(totals, {r.label_id: r.kind for r in rows}),
        labels=rows,
    )


def _label_summary(label: Label, breakdown: LabelBreakdown) -> LabelSummary:
    return LabelSummary(
        label_id=label.id,
        name=label.name,
        kind=label.kind,
        color=label.color,
        icon=label.icon,
        archived=label.archived_at is not None,
        allocation=breakdown.allocation,
        addition=breakdown.addition,
        transfer_in=breakdown.transfer_in,
        transfer_out=breakdown.transfer_out,
        total=breakdown.total,
    )
