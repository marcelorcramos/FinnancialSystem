import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, InvalidatesCache, SessionDep
from app.schemas.limit import LimitRead, LimitSet, LimitStatus
from app.services import limits

router = APIRouter(tags=["limits"], dependencies=[InvalidatesCache])


@router.get("/limits")
async def list_limits(user: CurrentUser, session: SessionDep) -> list[LimitRead]:
    """Every default and per-month limit of the user."""
    return [LimitRead.model_validate(row) for row in await limits.list_limits(session, user)]


@router.put("/labels/{label_id}/limit")
async def set_default_limit(
    label_id: uuid.UUID, data: LimitSet, user: CurrentUser, session: SessionDep
) -> LimitRead:
    """The label's limit for every month that has none of its own."""
    return LimitRead.model_validate(await limits.set_limit(session, user, label_id, data.amount))


@router.delete("/labels/{label_id}/limit", status_code=status.HTTP_204_NO_CONTENT)
async def remove_default_limit(label_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    await limits.remove_limit(session, user, label_id)


@router.put("/months/{month_id}/limits/{label_id}")
async def set_month_limit(
    month_id: uuid.UUID,
    label_id: uuid.UUID,
    data: LimitSet,
    user: CurrentUser,
    session: SessionDep,
) -> LimitRead:
    """A limit for this month only, replacing the default one."""
    limit = await limits.set_limit(session, user, label_id, data.amount, month_id)
    return LimitRead.model_validate(limit)


@router.delete("/months/{month_id}/limits/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_month_limit(
    month_id: uuid.UUID, label_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> None:
    await limits.remove_limit(session, user, label_id, month_id)


@router.get("/months/{month_id}/limits")
async def month_limits(
    month_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[LimitStatus]:
    """Labels with a limit this month, most used first."""
    return await limits.month_status(session, user, month_id)
