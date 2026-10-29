import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep, Today
from app.domain.enums import LabelKind
from app.domain.filters import CategoryFilter
from app.domain.periods import Period
from app.schemas.report import ReportEntries, ReportSeries, ReportSummary
from app.services import reports

router = APIRouter(prefix="/reports", tags=["reports"])

LabelIds = Annotated[
    list[uuid.UUID] | None,
    Query(description="Labels to include (repeat the parameter for several)"),
]
Kinds = Annotated[
    list[LabelKind] | None,
    Query(description="Label kinds to include; combined with label_ids as a union"),
]


@router.get("/summary")
async def report_summary(
    user: CurrentUser,
    session: SessionDep,
    today: Today,
    period: Period = Period.ALL,
    label_ids: LabelIds = None,
    kinds: Kinds = None,
) -> ReportSummary:
    """Totals by label and kind for a time window and category filter (donut chart data)."""
    categories = CategoryFilter(frozenset(label_ids or ()), frozenset(kinds or ()))
    return await reports.summary(session, user, period=period, categories=categories, today=today)


@router.get("/series")
async def report_series(
    user: CurrentUser,
    session: SessionDep,
    today: Today,
    period: Period = Period.ALL,
    label_ids: LabelIds = None,
    kinds: Kinds = None,
) -> ReportSeries:
    """Net total per label and month for a time window and category filter (line chart data)."""
    categories = CategoryFilter(frozenset(label_ids or ()), frozenset(kinds or ()))
    return await reports.series(session, user, period=period, categories=categories, today=today)


@router.get("/entries")
async def report_entries(
    user: CurrentUser,
    session: SessionDep,
    today: Today,
    period: Period = Period.ALL,
    label_ids: LabelIds = None,
    kinds: Kinds = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReportEntries:
    """The entries behind a summary, newest first, with their origin (report list)."""
    categories = CategoryFilter(frozenset(label_ids or ()), frozenset(kinds or ()))
    return await reports.entries(
        session,
        user,
        period=period,
        categories=categories,
        today=today,
        limit=limit,
        offset=offset,
    )
