import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, JobsDep, SessionDep, StorageDep, Today
from app.schemas.attachment import SignedUrl
from app.schemas.export import ExportRead, ReportExportCreate
from app.services import exports

router = APIRouter(tags=["exports"])


@router.post("/exports", status_code=status.HTTP_202_ACCEPTED)
async def export_report(
    data: ReportExportCreate, user: CurrentUser, session: SessionDep, today: Today, jobs: JobsDep
) -> ExportRead:
    """Build a report's entries as CSV or PDF in the background; poll the export until ready."""
    return ExportRead.model_validate(await exports.request_report(session, user, data, today, jobs))


@router.post("/users/me/export", status_code=status.HTTP_202_ACCEPTED)
async def export_account(
    user: CurrentUser, session: SessionDep, today: Today, jobs: JobsDep
) -> ExportRead:
    """Every piece of the account's data and its receipts, as a ZIP (GDPR)."""
    return ExportRead.model_validate(await exports.request_account(session, user, today, jobs))


@router.get("/exports")
async def list_exports(user: CurrentUser, session: SessionDep) -> list[ExportRead]:
    """The latest 20 exports, newest first."""
    return [ExportRead.model_validate(e) for e in await exports.list_recent(session, user)]


@router.get("/exports/{export_id}")
async def get_export(export_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> ExportRead:
    return ExportRead.model_validate(await exports.get(session, user, export_id))


@router.get("/exports/{export_id}/url")
async def export_url(
    export_id: uuid.UUID, user: CurrentUser, session: SessionDep, storage: StorageDep
) -> SignedUrl:
    """A signed download link (5 minutes); 409 until the export is ready."""
    return await exports.signed_url(session, storage, user, export_id)
