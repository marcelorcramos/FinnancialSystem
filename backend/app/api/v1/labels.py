import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, InvalidatesCache, SessionDep
from app.repositories import labels as labels_repo
from app.schemas.label import ColorSuggestions, LabelCreate, LabelRead, LabelUpdate
from app.services import labels

router = APIRouter(prefix="/labels", tags=["labels"], dependencies=[InvalidatesCache])


@router.get("")
async def list_labels(
    user: CurrentUser, session: SessionDep, include_archived: bool = False
) -> list[LabelRead]:
    rows = await labels_repo.list_for_user(session, user.id, include_archived=include_archived)
    return [LabelRead.model_validate(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_label(data: LabelCreate, user: CurrentUser, session: SessionDep) -> LabelRead:
    return LabelRead.model_validate(await labels.create(session, user, data))


@router.get("/color-suggestions")
async def color_suggestions(user: CurrentUser, session: SessionDep) -> ColorSuggestions:
    """Eight colors for the picker, none of them already used by the user's labels."""
    return ColorSuggestions(colors=await labels.color_suggestions(session, user))


@router.get("/{label_id}")
async def get_label(label_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> LabelRead:
    return LabelRead.model_validate(await labels.get(session, user, label_id))


@router.patch("/{label_id}")
async def update_label(
    label_id: uuid.UUID, data: LabelUpdate, user: CurrentUser, session: SessionDep
) -> LabelRead:
    return LabelRead.model_validate(await labels.update(session, user, label_id, data))


@router.post("/{label_id}/archive")
async def archive_label(label_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> LabelRead:
    label = await labels.set_archived(session, user, label_id, archived=True)
    return LabelRead.model_validate(label)


@router.post("/{label_id}/unarchive")
async def unarchive_label(label_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> LabelRead:
    label = await labels.set_archived(session, user, label_id, archived=False)
    return LabelRead.model_validate(label)


@router.delete("/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label(
    label_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    reassign_to: Annotated[
        uuid.UUID | None,
        Query(description="Label that receives the entries of the deleted label"),
    ] = None,
) -> None:
    await labels.delete(session, user, label_id, reassign_to)


@router.post("/{label_id}/restore")
async def restore_label(label_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> LabelRead:
    return LabelRead.model_validate(await labels.restore(session, user, label_id))
