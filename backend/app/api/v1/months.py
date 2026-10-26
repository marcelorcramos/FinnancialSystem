import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, SessionDep
from app.repositories import months as months_repo
from app.schemas.month import (
    IncomeCreate,
    IncomeRead,
    IncomeUpdate,
    MonthCreate,
    MonthRead,
    MonthUpdate,
)
from app.schemas.summary import MonthSummary
from app.services import incomes, months, summary

router = APIRouter(tags=["months"])


@router.get("/months")
async def list_months(
    user: CurrentUser, session: SessionDep, year: int | None = None
) -> list[MonthRead]:
    rows = await months_repo.list_for_user(session, user.id, year)
    return [MonthRead.model_validate(m) for m in rows]


@router.post("/months", status_code=status.HTTP_201_CREATED)
async def create_month(data: MonthCreate, user: CurrentUser, session: SessionDep) -> MonthRead:
    return MonthRead.model_validate(await months.create(session, user, data))


@router.get("/months/{month_id}")
async def get_month(month_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> MonthRead:
    return MonthRead.model_validate(await months.get(session, user, month_id))


@router.get("/months/{month_id}/summary")
async def month_summary(
    month_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> MonthSummary:
    """Totals per label ("base + adjustments") and per kind, income and unallocated."""
    return await summary.month_summary(session, user, month_id)


@router.patch("/months/{month_id}")
async def update_month(
    month_id: uuid.UUID, data: MonthUpdate, user: CurrentUser, session: SessionDep
) -> MonthRead:
    return MonthRead.model_validate(await months.update(session, user, month_id, data))


@router.post("/months/{month_id}/close")
async def close_month(month_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> MonthRead:
    month = await months.set_closed(session, user, month_id, closed=True)
    return MonthRead.model_validate(month)


@router.post("/months/{month_id}/reopen")
async def reopen_month(month_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> MonthRead:
    month = await months.set_closed(session, user, month_id, closed=False)
    return MonthRead.model_validate(month)


@router.delete("/months/{month_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_month(month_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    await months.delete(session, user, month_id)


@router.post("/months/{month_id}/restore")
async def restore_month(month_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> MonthRead:
    return MonthRead.model_validate(await months.restore(session, user, month_id))


@router.get("/months/{month_id}/incomes")
async def list_incomes(
    month_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[IncomeRead]:
    return await incomes.list_for_month(session, user, month_id)


@router.post("/months/{month_id}/incomes", status_code=status.HTTP_201_CREATED)
async def create_income(
    month_id: uuid.UUID, data: IncomeCreate, user: CurrentUser, session: SessionDep
) -> IncomeRead:
    return IncomeRead.model_validate(await incomes.create(session, user, month_id, data))


@router.patch("/incomes/{income_id}")
async def update_income(
    income_id: uuid.UUID, data: IncomeUpdate, user: CurrentUser, session: SessionDep
) -> IncomeRead:
    return IncomeRead.model_validate(await incomes.update(session, user, income_id, data))


@router.delete("/incomes/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_income(income_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    await incomes.delete(session, user, income_id)


@router.post("/incomes/{income_id}/restore")
async def restore_income(
    income_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> IncomeRead:
    return IncomeRead.model_validate(await incomes.restore(session, user, income_id))
