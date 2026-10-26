import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep, Today
from app.domain.enums import LabelKind
from app.domain.filters import CategoryFilter
from app.domain.periods import Period
from app.schemas.report import ReportSummary
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
