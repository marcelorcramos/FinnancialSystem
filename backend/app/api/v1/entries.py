import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.entry import (
    AdditionCreate,
    AdditionRead,
    AllocationSet,
    EntryRead,
    TransferCreate,
    TransferRead,
    TransferUpdate,
)
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


@router.post("/months/{month_id}/additions", status_code=status.HTTP_201_CREATED)
async def add_money(
    month_id: uuid.UUID, data: AdditionCreate, user: CurrentUser, session: SessionDep
) -> AdditionRead:
    entry, income = await entries.add_money(session, user, month_id, data)
    return AdditionRead.model_validate(
        {**EntryRead.model_validate(entry).model_dump(), "source": income.source}
    )


@router.post("/months/{month_id}/transfers", status_code=status.HTTP_201_CREATED)
async def create_transfer(
    month_id: uuid.UUID, data: TransferCreate, user: CurrentUser, session: SessionDep
) -> TransferRead:
    return await entries.create_transfer(session, user, month_id, data)


@router.patch("/transfers/{transfer_id}")
async def update_transfer(
    transfer_id: uuid.UUID, data: TransferUpdate, user: CurrentUser, session: SessionDep
) -> TransferRead:
    return await entries.update_transfer(session, user, transfer_id, data)
