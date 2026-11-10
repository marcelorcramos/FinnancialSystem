import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.deps import CurrentUser, SessionDep, StorageDep
from app.domain.attachments import MAX_SIZE
from app.schemas.attachment import AttachmentRead, SignedUrl
from app.services import attachments

router = APIRouter(tags=["attachments"])


@router.post("/months/{month_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    month_id: uuid.UUID,
    file: Annotated[UploadFile, File(description="JPEG, PNG, WebP or PDF, up to 10 MB")],
    user: CurrentUser,
    session: SessionDep,
    storage: StorageDep,
    entry_id: Annotated[uuid.UUID | None, Form()] = None,
) -> AttachmentRead:
    """Attach a receipt to an open month, optionally to one of its entries."""
    data = await file.read(MAX_SIZE + 1)  # one byte more is enough to know it is too big
    attachment = await attachments.upload(
        session, storage, user, month_id, data, file.filename, entry_id
    )
    return AttachmentRead.model_validate(attachment)


@router.get("/months/{month_id}/attachments")
async def list_attachments(
    month_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    entry_id: uuid.UUID | None = None,
) -> list[AttachmentRead]:
    """Receipts of the month (or of one entry), oldest first."""
    items = await attachments.list_for_month(session, user, month_id, entry_id)
    return [AttachmentRead.model_validate(a) for a in items]


@router.get("/attachments/{attachment_id}/url")
async def attachment_url(
    attachment_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    storage: StorageDep,
    download: bool = False,
) -> SignedUrl:
    """A signed link to view (or, with download=true, save) the file; it expires in minutes."""
    return await attachments.signed_url(session, storage, user, attachment_id, download)


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> None:
    await attachments.delete(session, user, attachment_id)


@router.post("/attachments/{attachment_id}/restore")
async def restore_attachment(
    attachment_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> AttachmentRead:
    return AttachmentRead.model_validate(await attachments.restore(session, user, attachment_id))
