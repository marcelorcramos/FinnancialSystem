"""Exports (Phase 9): report CSV/PDF and the account's data, built by the Celery worker.

The API records a pending export and hands its id to the worker after committing.
The worker builds the file, stores it under the user's prefix and marks it ready;
the user downloads it through a signed link. Files are removed after 7 days.
"""

import re
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import RUN_EXPORT, JobQueue
from app.core.storage import SIGNED_URL_SECONDS, Storage
from app.db.base import Base
from app.domain.enums import AuditAction, ExportFormat, ExportKind, ExportStatus, LabelKind
from app.domain.errors import ConflictError, NotFoundError, ValidationError
from app.domain.filters import CategoryFilter
from app.domain.periods import Period
from app.models import (
    Alert,
    Attachment,
    Entry,
    Export,
    Goal,
    Income,
    Label,
    Limit,
    Month,
    User,
)
from app.repositories import attachments as attachments_repo
from app.repositories import exports as exports_repo
from app.repositories import labels as labels_repo
from app.repositories import users
from app.schemas.attachment import SignedUrl
from app.schemas.export import ReportExportCreate
from app.schemas.report import ReportEntry
from app.services import audit, export_files, reports
from app.services.export_files import LabelInfo

log = structlog.get_logger(__name__)

ENTITY = "export"
RETENTION = timedelta(days=7)
MAX_PENDING = 3
PAGE = 200
CONTENT_TYPES = {
    ExportFormat.CSV: "text/csv; charset=utf-8",
    ExportFormat.PDF: "application/pdf",
    ExportFormat.ZIP: "application/zip",
}
# Every table with the user's records, in the order they appear in data.json.
ACCOUNT_TABLES: dict[str, type[Base]] = {
    "labels": Label,
    "months": Month,
    "incomes": Income,
    "entries": Entry,
    "limits": Limit,
    "alerts": Alert,
    "goals": Goal,
    "receipts": Attachment,
}


async def request_report(
    session: AsyncSession, user: User, data: ReportExportCreate, today: date, jobs: JobQueue
) -> Export:
    if data.format is ExportFormat.ZIP:
        raise ValidationError("Reports export as csv or pdf")
    categories = CategoryFilter(frozenset(data.label_ids), frozenset(data.kinds))
    await reports.ensure_own_labels(session, user, categories)
    return await _request(
        session,
        user,
        jobs,
        Export(
            user_id=user.id,
            kind=ExportKind.REPORT,
            format=data.format,
            period=data.period,
            label_ids=sorted(str(i) for i in data.label_ids),
            kinds=sorted(k.value for k in data.kinds),
            reference_date=today,
        ),
    )


async def request_account(session: AsyncSession, user: User, today: date, jobs: JobQueue) -> Export:
    return await _request(
        session,
        user,
        jobs,
        Export(
            user_id=user.id,
            kind=ExportKind.ACCOUNT,
            format=ExportFormat.ZIP,
            reference_date=today,
        ),
    )


async def _request(session: AsyncSession, user: User, jobs: JobQueue, export: Export) -> Export:
    if await exports_repo.count_pending(session, user.id) >= MAX_PENDING:
        raise ConflictError("Wait for the exports in progress to finish")
    session.add(export)
    await session.flush()
    audit.log(session, user_id=user.id, entity=ENTITY, obj=export, action=AuditAction.CREATE)
    await session.commit()
    await jobs.enqueue(RUN_EXPORT, export_id=str(export.id))
    return export


async def list_recent(session: AsyncSession, user: User) -> list[Export]:
    return await exports_repo.recent_for_user(session, user.id, limit=20)


async def get(session: AsyncSession, user: User, export_id: uuid.UUID) -> Export:
    export = await exports_repo.get_for_user(session, user.id, export_id)
    if export is None:
        raise NotFoundError("Export not found")
    return export


async def signed_url(
    session: AsyncSession, storage: Storage, user: User, export_id: uuid.UUID
) -> SignedUrl:
    export = await get(session, user, export_id)
    if export.status is not ExportStatus.READY or not export.storage_key or not export.filename:
        raise ConflictError(f"The export is {export.status.value}, not ready to download")
    url = storage.signed_url(export.storage_key, export.filename, download=True)
    return SignedUrl(url=url, expires_in=SIGNED_URL_SECONDS)


async def build(session: AsyncSession, storage: Storage, export_id: uuid.UUID) -> ExportStatus:
    """The worker's job: build the file, store it and mark the export ready (or failed).

    Running it again for a finished export changes nothing.
    """
    export = await exports_repo.get_for_update(session, export_id)
    if export is None or export.status is not ExportStatus.PENDING:
        return export.status if export else ExportStatus.FAILED
    user = await users.get_active_by_id(session, export.user_id)
    if user is None:
        export.status = ExportStatus.FAILED
        export.error = "The account no longer exists"
        await session.commit()
        return export.status
    try:
        content = await _content(session, storage, user, export)
        filename = _filename(export)
        key = f"users/{user.id}/exports/{export.id}.{export.format.value}"
        await storage.put(key, content, CONTENT_TYPES[export.format])
    except Exception as error:
        log.exception("export.failed", export_id=str(export.id))
        export.status = ExportStatus.FAILED
        export.error = f"The file could not be built ({type(error).__name__})"
    else:
        now = datetime.now(UTC)
        export.status = ExportStatus.READY
        export.storage_key = key
        export.filename = filename
        export.size = len(content)
        export.completed_at = now
        export.expires_at = now + RETENTION
    await session.commit()
    return export.status


async def remove_expired(session: AsyncSession, storage: Storage, now: datetime) -> int:
    """Delete the files of exports past their retention (Celery beat, daily)."""
    expired = await exports_repo.expired_ready(session, now)
    for export in expired:
        if export.storage_key:
            await storage.delete_prefix(export.storage_key)
        export.status = ExportStatus.EXPIRED
        export.storage_key = None
    await session.commit()
    return len(expired)


def _filename(export: Export) -> str:
    stamp = export.reference_date.isoformat()
    if export.kind is ExportKind.ACCOUNT:
        return f"finnancial-data-{stamp}.zip"
    period = re.sub(r"_", "-", (export.period or Period.ALL).value)
    return f"finnancial-report-{period}-{stamp}.{export.format.value}"


async def _content(session: AsyncSession, storage: Storage, user: User, export: Export) -> bytes:
    if export.kind is ExportKind.ACCOUNT:
        return await _account_zip(session, storage, user)
    categories = CategoryFilter(
        frozenset(uuid.UUID(i) for i in export.label_ids),
        frozenset(LabelKind(k) for k in export.kinds),
    )
    period = export.period or Period.ALL
    today = export.reference_date
    entries = await _all_entries(session, user, period, categories, today)
    labels = {
        label.id: LabelInfo(label.name, label.kind)
        for label in await labels_repo.all_for_user(session, user.id)
    }
    if export.format is ExportFormat.CSV:
        return export_files.report_csv(entries, labels)
    summary = await reports.summary(
        session, user, period=period, categories=categories, today=today
    )
    return export_files.report_pdf(summary, entries, labels)


async def _all_entries(
    session: AsyncSession, user: User, period: Period, categories: CategoryFilter, today: date
) -> list[ReportEntry]:
    entries: list[ReportEntry] = []
    while True:
        page = await reports.entries(
            session,
            user,
            period=period,
            categories=categories,
            today=today,
            limit=PAGE,
            offset=len(entries),
        )
        entries.extend(page.entries)
        if not page.entries or len(entries) >= page.count:
            return entries


async def _account_zip(session: AsyncSession, storage: Storage, user: User) -> bytes:
    data: dict[str, Any] = {
        "exported_at": datetime.now(UTC).isoformat(),
        "profile": audit.snapshot(user),
    }
    for name, model in ACCOUNT_TABLES.items():
        rows = await session.scalars(
            select(model).where(model.user_id == user.id)  # type: ignore[attr-defined]
        )
        data[name] = [audit.snapshot(row) for row in rows]
    files = [
        (f"{attachment.id}-{attachment.filename}", await storage.get(attachment.storage_key))
        for attachment in await attachments_repo.list_all_for_user(session, user.id)
    ]
    return export_files.account_zip(data, files)
