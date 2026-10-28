"""ReportService: answers questions by period and category (Phase 3).

This is the single entry point for reports; the Claude chat (Phase 11) will reuse it.
"""

import uuid
from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import ledger
from app.domain.errors import NotFoundError
from app.domain.filters import CategoryFilter
from app.domain.ledger import LabelBreakdown
from app.domain.periods import MonthKey, Period, months_between, months_in
from app.models import Label, User
from app.repositories import reports as reports_repo
from app.schemas.report import (
    ReportLabel,
    ReportSeries,
    ReportSummary,
    SeriesLabel,
    SeriesPoint,
)


async def summary(
    session: AsyncSession,
    user: User,
    *,
    period: Period,
    categories: CategoryFilter,
    today: date,
) -> ReportSummary:
    await _ensure_own_labels(session, user, categories)
    months = months_in(period, today)

    breakdowns: dict[uuid.UUID, LabelBreakdown] = {}
    for label_id, movement_type, amount in await reports_repo.totals_by_label_and_type(
        session, user.id, months, categories
    ):
        breakdown = breakdowns.setdefault(label_id, LabelBreakdown())
        name = movement_type.value
        setattr(breakdown, name, getattr(breakdown, name) + amount)

    labels = await _selected_labels(session, user, categories, breakdowns.keys())
    totals = {label_id: breakdowns.get(label_id, LabelBreakdown()).total for label_id in labels}
    kinds = {label_id: label.kind for label_id, label in labels.items()}
    by_kind = ledger.totals_by_kind(totals, kinds)
    shares = ledger.distribution_shares(totals)

    rows = [
        _report_label(label, breakdowns.get(label.id, LabelBreakdown()), shares[label.id])
        for label in labels.values()
    ]
    rows.sort(key=lambda r: (-r.total, r.name.lower()))
    return ReportSummary(
        period=period,
        start_month=str(months[0]) if months else None,
        end_month=str(months[-1]) if months else None,
        reference_date=today,
        total=sum(totals.values(), Decimal("0.00")),
        by_kind=by_kind,
        kind_shares=ledger.distribution_shares(by_kind),
        labels=rows,
    )


async def series(
    session: AsyncSession,
    user: User,
    *,
    period: Period,
    categories: CategoryFilter,
    today: date,
) -> ReportSeries:
    """Net total per label and month (line chart data). Months without money count as zero."""
    await _ensure_own_labels(session, user, categories)
    window = months_in(period, today)

    breakdowns: dict[tuple[uuid.UUID, MonthKey], LabelBreakdown] = {}
    for label_id, month, movement_type, amount in await reports_repo.totals_by_label_month_and_type(
        session, user.id, window, categories
    ):
        breakdown = breakdowns.setdefault((label_id, month), LabelBreakdown())
        name = movement_type.value
        setattr(breakdown, name, getattr(breakdown, name) + amount)

    if window is not None:
        months = window
    elif breakdowns:
        # All time: from the first month with money up to the current month (or a later sheet).
        seen = [month for _, month in breakdowns]
        months = months_between(min(seen), max(*seen, MonthKey.of(today)))
    else:
        months = []

    labels = await _selected_labels(
        session, user, categories, {label_id for label_id, _ in breakdowns}
    )
    rows = []
    for label in labels.values():
        totals = [breakdowns.get((label.id, m), LabelBreakdown()).total for m in months]
        rows.append(
            SeriesLabel(
                label_id=label.id,
                name=label.name,
                kind=label.kind,
                color=label.color,
                icon=label.icon,
                archived=label.archived_at is not None,
                total=sum(totals, Decimal("0.00")),
                points=[
                    SeriesPoint(month=str(m), total=t) for m, t in zip(months, totals, strict=True)
                ],
            )
        )
    rows.sort(key=lambda r: (-r.total, r.name.lower()))
    return ReportSeries(
        period=period,
        start_month=str(months[0]) if months else None,
        end_month=str(months[-1]) if months else None,
        reference_date=today,
        months=[str(m) for m in months],
        totals=[
            SeriesPoint(month=str(m), total=sum((r.points[i].total for r in rows), Decimal("0.00")))
            for i, m in enumerate(months)
        ],
        labels=rows,
    )


async def _selected_labels(
    session: AsyncSession,
    user: User,
    categories: CategoryFilter,
    with_history: Iterable[uuid.UUID],
) -> dict[uuid.UUID, Label]:
    """Usable labels matching the filter, plus archived or deleted ones that have money."""
    labels: dict[uuid.UUID, Label] = {
        label.id: label
        for label in await reports_repo.usable_labels_matching(session, user.id, categories)
    }
    for label in await reports_repo.labels_for_report(
        session, user.id, set(with_history) - labels.keys()
    ):
        labels[label.id] = label
    return labels


async def _ensure_own_labels(session: AsyncSession, user: User, categories: CategoryFilter) -> None:
    if await reports_repo.missing_label_ids(session, user.id, categories.label_ids):
        raise NotFoundError("Label not found")


def _report_label(label: Label, breakdown: LabelBreakdown, share: Decimal) -> ReportLabel:
    return ReportLabel(
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
        share=share,
    )
