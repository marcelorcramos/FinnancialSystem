import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.entry import AllocationSet, EntryRead
from app.services import entries

router = APIRouter(tags=["entries"])


@router.put(
    "/months/{month_id}/allocations/{label_id}",
    response_model=EntryRead,
    responses={204: {"description": "Amount was 0: the allocation was removed"}},
)
async def set_allocation(
    month_id: uuid.UUID,
    label_id: uuid.UUID,
    data: AllocationSet,
    user: CurrentUser,
    session: SessionDep,
) -> EntryRead | Response:
    allocation = await entries.set_allocation(session, user, month_id, label_id, data)
    if allocation is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return EntryRead.model_validate(allocation)


@router.delete("/months/{month_id}/allocations/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_allocation(
    month_id: uuid.UUID, label_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> None:
    await entries.remove_allocation(session, user, month_id, label_id)
