"""Receipts: photos and PDFs of a month or one of its entries, kept in S3 (Phase 9).

Each file lives under the owner's prefix with a random key, and the API only hands
out short-lived signed links after checking ownership, so a guessed URL opens
nothing. Deletes are soft (the file stays for Undo) until the account is deleted.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import SIGNED_URL_SECONDS, Storage
from app.domain import attachments as rules
from app.domain.enums import AuditAction
from app.domain.errors import NotFoundError, ValidationError
from app.models import Attachment, User
from app.repositories import attachments as attachments_repo
from app.repositories import entries as entries_repo
from app.schemas.attachment import SignedUrl
from app.services import audit, months

ENTITY = "attachment"


def storage_key(user_id: uuid.UUID, attachment_id: uuid.UUID) -> str:
    return f"users/{user_id}/attachments/{attachment_id}"


async def upload(
    session: AsyncSession,
    storage: Storage,
    user: User,
    month_id: uuid.UUID,
    data: bytes,
    filename: str | None,
    entry_id: uuid.UUID | None = None,
) -> Attachment:
    await months.get_open(session, user, month_id)
    if entry_id is not None:
        entry = await entries_repo.get_for_user(session, user.id, entry_id)
        if entry is None:
            raise NotFoundError("Entry not found")
        if entry.month_id != month_id:
            raise ValidationError("The entry belongs to another month")
    mime = rules.validate(data)
    attachment_id = uuid.uuid4()
    attachment = Attachment(
        id=attachment_id,
        user_id=user.id,
        month_id=month_id,
        entry_id=entry_id,
        storage_key=storage_key(user.id, attachment_id),
        filename=rules.clean_filename(filename, mime),
        mime=mime,
        size=len(data),
    )
    # The file is stored first: if the database write fails, an orphan object is
    # harmless; a row without its file would not be.
    await storage.put(attachment.storage_key, data, mime)
    session.add(attachment)
    await session.flush()
    _log(session, user, attachment, AuditAction.CREATE)
    await session.commit()
    return attachment


async def list_for_month(
    session: AsyncSession, user: User, month_id: uuid.UUID, entry_id: uuid.UUID | None = None
) -> list[Attachment]:
    await months.get(session, user, month_id)
    return await attachments_repo.list_for_month(session, user.id, month_id, entry_id)


async def signed_url(
    session: AsyncSession, storage: Storage, user: User, attachment_id: uuid.UUID, download: bool
) -> SignedUrl:
    attachment = await _get(session, user, attachment_id)
    url = storage.signed_url(attachment.storage_key, attachment.filename, download=download)
    return SignedUrl(url=url, expires_in=SIGNED_URL_SECONDS)


async def delete(session: AsyncSession, user: User, attachment_id: uuid.UUID) -> None:
    attachment = await _get(session, user, attachment_id)
    await months.get_open(session, user, attachment.month_id)
    before = audit.snapshot(attachment)
    attachment.deleted_at = datetime.now(UTC)
    await session.flush()
    _log(session, user, attachment, AuditAction.DELETE, before)
    await session.commit()


async def restore(session: AsyncSession, user: User, attachment_id: uuid.UUID) -> Attachment:
    attachment = await attachments_repo.get_for_user(session, user.id, attachment_id, deleted=True)
    if attachment is None:
        raise NotFoundError("Receipt not found")
    await months.get_open(session, user, attachment.month_id)
    attachment.deleted_at = None
    await session.flush()
    _log(session, user, attachment, AuditAction.RESTORE)
    await session.commit()
    return attachment


async def _get(session: AsyncSession, user: User, attachment_id: uuid.UUID) -> Attachment:
    attachment = await attachments_repo.get_for_user(session, user.id, attachment_id)
    if attachment is None:
        raise NotFoundError("Receipt not found")
    return attachment


def _log(
    session: AsyncSession,
    user: User,
    attachment: Attachment,
    action: AuditAction,
    before: dict[str, object] | None = None,
) -> None:
    audit.log(session, user_id=user.id, entity=ENTITY, obj=attachment, action=action, before=before)
