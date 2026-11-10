"""Report and account exports built by the worker (Phase 9)."""

import csv
import io
import json
import uuid
import zipfile
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from pypdf import PdfReader
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jobs import RUN_EXPORT
from app.core.storage import Storage
from app.domain.enums import ExportStatus
from app.models import Export
from app.services import exports
from tests.integration.conftest import RecordedJobs
from tests.integration.helpers import ApiUser, create_month, new_user
from tests.integration.test_attachments import PDF, fetch, upload
from tests.integration.test_reports import TODAY, fixed_today, make_book

__all__ = ["fixed_today"]


async def request(client: AsyncClient, user: ApiUser, **body: Any) -> dict[str, Any]:
    response = await client.post("/api/v1/exports", headers=user.headers, json=body)
    assert response.status_code == 202, response.text
    result: dict[str, Any] = response.json()
    return result


async def build_and_download(
    client: AsyncClient, session: AsyncSession, storage: Storage, user: ApiUser, export_id: str
) -> tuple[dict[str, Any], bytes]:
    """Run the worker's job, then fetch the file as the browser would."""
    assert await exports.build(session, storage, uuid.UUID(export_id)) is ExportStatus.READY
    export = (await client.get(f"/api/v1/exports/{export_id}", headers=user.headers)).json()
    link = (await client.get(f"/api/v1/exports/{export_id}/url", headers=user.headers)).json()
    status, body, _ = fetch(link["url"])
    assert status == 200
    return export, body


async def test_a_report_csv_has_every_entry_of_the_window(
    client: AsyncClient, session: AsyncSession, storage: Storage, jobs: RecordedJobs
) -> None:
    book = await make_book(client)
    pending = await request(
        client, book.user, format="csv", period="last_month", kinds=["expense", "saving"]
    )
    assert pending["status"] == "pending"
    assert pending["reference_date"] == TODAY.isoformat()
    assert jobs.of(RUN_EXPORT) == [{"export_id": pending["id"]}]

    export, content = await build_and_download(client, session, storage, book.user, pending["id"])
    assert export["status"] == "ready"
    assert export["filename"] == f"finnancial-report-last-month-{TODAY.isoformat()}.csv"
    assert export["size"] == len(content)
    assert export["expires_at"] is not None
    assert content.startswith("﻿".encode())

    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    found = {
        (r["Label"], r["Movement"], r["Amount"], r["Signed amount"], r["Other label"]) for r in rows
    }
    assert found == {
        ("Water", "Allocation", "30.00", "30.00", ""),
        ("Food", "Allocation", "200.00", "200.00", ""),
        ("Savings", "Allocation", "300.00", "300.00", ""),
        ("Food", "Transfer in", "12.00", "12.00", "Savings"),
        ("Savings", "Transfer out", "12.00", "-12.00", "Food"),
    }
    assert {r["Month"] for r in rows} == {"2026-10"}


async def test_a_report_pdf_shows_totals_labels_and_entries(
    client: AsyncClient, session: AsyncSession, storage: Storage
) -> None:
    book = await make_book(client)
    pending = await request(
        client,
        book.user,
        format="pdf",
        period="last_6_months",
        label_ids=[str(book.labels["Water"])],
    )
    export, content = await build_and_download(client, session, storage, book.user, pending["id"])
    assert export["filename"].endswith(".pdf")
    text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(content)).pages)
    assert "FinnancialSystem report" in text
    assert "Last 6 months (2026-05 to 2026-10)" in text
    assert "€180.00" in text  # six months of €30 water
    assert "Entries (6)" in text


async def test_the_account_export_holds_every_record_and_receipt(
    client: AsyncClient, session: AsyncSession, storage: Storage
) -> None:
    user = await new_user(client)
    month = (await create_month(client, user))["id"]
    receipt = (await upload(client, user, month)).json()
    response = await client.post("/api/v1/users/me/export", headers=user.headers)
    assert response.status_code == 202
    pending = response.json()
    assert (pending["kind"], pending["format"]) == ("account", "zip")

    export, content = await build_and_download(client, session, storage, user, pending["id"])
    assert export["filename"] == f"finnancial-data-{TODAY.isoformat()}.zip"
    archive = zipfile.ZipFile(io.BytesIO(content))
    data = json.loads(archive.read("data.json"))
    assert data["profile"]["email"] == user.email
    assert "password_hash" not in data["profile"]
    assert len(data["labels"]) == 11
    assert [m["id"] for m in data["months"]] == [month]
    assert [r["id"] for r in data["receipts"]] == [receipt["id"]]
    assert set(data) >= {"incomes", "entries", "limits", "alerts", "goals"}
    assert archive.read(f"receipts/{receipt['id']}-groceries.pdf") == PDF
    assert "README.txt" in archive.namelist()


async def test_exports_are_private(client: AsyncClient, storage: Storage) -> None:
    alice, bob = await new_user(client), await new_user(client)
    export = await request(client, alice, format="csv")
    for path in (f"/api/v1/exports/{export['id']}", f"/api/v1/exports/{export['id']}/url"):
        assert (await client.get(path, headers=bob.headers)).status_code == 404
    assert (await client.get("/api/v1/exports", headers=bob.headers)).json() == []
    assert [
        e["id"] for e in (await client.get("/api/v1/exports", headers=alice.headers)).json()
    ] == [export["id"]]
    # Bob cannot export a report of Alice's labels.
    labels = (await client.get("/api/v1/labels", headers=alice.headers)).json()
    stolen = await client.post(
        "/api/v1/exports",
        headers=bob.headers,
        json={"format": "csv", "label_ids": [labels[0]["id"]]},
    )
    assert stolen.status_code == 404


async def test_downloading_waits_for_the_file(client: AsyncClient, storage: Storage) -> None:
    user = await new_user(client)
    export = await request(client, user, format="pdf")
    response = await client.get(f"/api/v1/exports/{export['id']}/url", headers=user.headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "The export is pending, not ready to download"


async def test_reports_export_only_as_csv_or_pdf(client: AsyncClient) -> None:
    user = await new_user(client)
    response = await client.post("/api/v1/exports", headers=user.headers, json={"format": "zip"})
    assert response.status_code == 422


async def test_only_three_exports_can_wait_at_once(client: AsyncClient) -> None:
    user = await new_user(client)
    for _ in range(3):
        await request(client, user, format="csv")
    response = await client.post("/api/v1/exports", headers=user.headers, json={"format": "csv"})
    assert response.status_code == 409


async def test_building_twice_changes_nothing(
    client: AsyncClient, session: AsyncSession, storage: Storage
) -> None:
    user = await new_user(client)
    export_id = uuid.UUID((await request(client, user, format="csv"))["id"])
    assert await exports.build(session, storage, export_id) is ExportStatus.READY
    first = await session.get(Export, export_id)
    assert first is not None
    completed = first.completed_at
    assert await exports.build(session, storage, export_id) is ExportStatus.READY
    assert first.completed_at == completed
    assert await exports.build(session, storage, uuid.uuid4()) is ExportStatus.FAILED


async def test_a_failure_marks_the_export_failed(
    client: AsyncClient, session: AsyncSession, storage: Storage, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = await new_user(client)
    export = await request(client, user, format="csv")

    async def broken(*_: Any) -> None:
        raise ConnectionError("storage down")

    monkeypatch.setattr(storage, "put", broken)
    assert await exports.build(session, storage, uuid.UUID(export["id"])) is ExportStatus.FAILED
    failed = (await client.get(f"/api/v1/exports/{export['id']}", headers=user.headers)).json()
    assert failed["status"] == "failed"
    assert failed["error"] == "The file could not be built (ConnectionError)"


async def test_expired_files_are_removed(
    client: AsyncClient, session: AsyncSession, storage: Storage
) -> None:
    user = await new_user(client)
    export = await request(client, user, format="csv")
    export_id = uuid.UUID(export["id"])
    await exports.build(session, storage, export_id)
    now = datetime.now(UTC)
    assert await exports.remove_expired(session, storage, now) == 0

    await session.execute(
        update(Export).where(Export.id == export_id).values(expires_at=now - timedelta(seconds=1))
    )
    row = await session.get(Export, export_id)
    assert row is not None
    key = row.storage_key
    assert key is not None
    assert await exports.remove_expired(session, storage, now) == 1
    await session.refresh(row)
    assert (row.status, row.storage_key) == (ExportStatus.EXPIRED, None)
    assert await storage.delete_prefix(key) == 0  # the file is gone
    gone = await client.get(f"/api/v1/exports/{export['id']}/url", headers=user.headers)
    assert gone.status_code == 409
