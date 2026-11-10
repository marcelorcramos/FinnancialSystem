"""Receipts in S3 (Phase 9). Acceptance criterion: a user cannot reach another user's
attachments, not even with a guessed URL."""

import urllib.error
import urllib.request
import uuid
from typing import Any

from httpx import AsyncClient

from app.core.storage import Storage
from tests.integration.helpers import ApiUser, create_month, label_id, new_user

PDF = b"%PDF-1.7\n1 0 obj << >> endobj\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def fetch(url: str) -> tuple[int, bytes, dict[str, str]]:
    """GET straight from storage, like a browser opening the link."""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310 (test S3)
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, b"", {}


async def upload(
    client: AsyncClient,
    user: ApiUser,
    month_id: str,
    data: bytes = PDF,
    name: str = "groceries.pdf",
    **form: str,
) -> Any:
    return await client.post(
        f"/api/v1/months/{month_id}/attachments",
        headers=user.headers,
        files={"file": (name, data, "application/octet-stream")},
        data=form,
    )


async def allocation(client: AsyncClient, user: ApiUser, month_id: str) -> str:
    food = await label_id(client, user, "Food")
    response = await client.put(
        f"/api/v1/months/{month_id}/allocations/{food}", headers=user.headers, json={"amount": "50"}
    )
    entry_id: str = response.json()["id"]
    return entry_id


async def test_upload_list_and_open_a_receipt(client: AsyncClient, storage: Storage) -> None:
    user = await new_user(client)
    month = (await create_month(client, user))["id"]
    entry = await allocation(client, user, month)

    response = await upload(client, user, month, entry_id=entry)
    assert response.status_code == 201, response.text
    receipt = response.json()
    assert receipt["filename"] == "groceries.pdf"
    assert receipt["mime"] == "application/pdf"  # from the bytes, not the browser's claim
    assert receipt["size"] == len(PDF)
    assert receipt["entry_id"] == entry

    listed = await client.get(f"/api/v1/months/{month}/attachments", headers=user.headers)
    assert [a["id"] for a in listed.json()] == [receipt["id"]]
    for_entry = await client.get(
        f"/api/v1/months/{month}/attachments",
        headers=user.headers,
        params={"entry_id": str(uuid.uuid4())},
    )
    assert for_entry.json() == []

    link = await client.get(f"/api/v1/attachments/{receipt['id']}/url", headers=user.headers)
    assert link.json()["expires_in"] == 300
    status, body, headers = fetch(link.json()["url"])
    assert (status, body) == (200, PDF)
    assert headers["Content-Disposition"].startswith("inline")

    download = await client.get(
        f"/api/v1/attachments/{receipt['id']}/url",
        headers=user.headers,
        params={"download": "true"},
    )
    _, _, headers = fetch(download.json()["url"])
    assert headers["Content-Disposition"] == "attachment; filename*=UTF-8''groceries.pdf"


async def test_another_user_cannot_reach_a_receipt(client: AsyncClient, storage: Storage) -> None:
    alice, bob = await new_user(client), await new_user(client)
    month = (await create_month(client, alice))["id"]
    entry = await allocation(client, alice, month)
    receipt = (await upload(client, alice, month, entry_id=entry)).json()
    bob_month = (await create_month(client, bob))["id"]

    assert (
        await client.get(f"/api/v1/attachments/{receipt['id']}/url", headers=bob.headers)
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/attachments/{receipt['id']}", headers=bob.headers)
    ).status_code == 404
    assert (
        await client.post(f"/api/v1/attachments/{receipt['id']}/restore", headers=bob.headers)
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/months/{month}/attachments", headers=bob.headers)
    ).status_code == 404
    assert (await upload(client, bob, month)).status_code == 404
    # Bob cannot hang his file on Alice's entry from his own month either.
    assert (await upload(client, bob, bob_month, entry_id=entry)).status_code == 404


async def test_a_guessed_or_altered_url_opens_nothing(
    client: AsyncClient, storage: Storage
) -> None:
    alice, bob = await new_user(client), await new_user(client)
    alice_receipt = (await upload(client, alice, (await create_month(client, alice))["id"])).json()
    bob_receipt = (await upload(client, bob, (await create_month(client, bob))["id"])).json()
    alice_link = (
        await client.get(f"/api/v1/attachments/{alice_receipt['id']}/url", headers=alice.headers)
    ).json()["url"]
    bob_link = (
        await client.get(f"/api/v1/attachments/{bob_receipt['id']}/url", headers=bob.headers)
    ).json()["url"]
    assert fetch(alice_link)[0] == 200

    # The object's plain address, without a signature: private.
    plain = alice_link.split("?")[0]
    assert fetch(plain)[0] == 403
    # Bob reuses his own signature on Alice's object: the signature covers the key.
    bob_query = bob_link.split("?")[1]
    assert fetch(f"{plain}?{bob_query}")[0] == 403
    # Keys hold no names or numbers to guess.
    assert alice_link.split("?")[0].endswith(f"/attachments/{alice_receipt['id']}")


async def test_only_receipt_types_up_to_10_mb_are_accepted(
    client: AsyncClient, storage: Storage
) -> None:
    user = await new_user(client)
    month = (await create_month(client, user))["id"]

    disguised = await upload(client, user, month, b"MZ\x90\x00 not a pdf", "invoice.pdf")
    assert disguised.status_code == 422
    assert disguised.json()["detail"] == "Only JPEG, PNG, WebP images and PDF files are accepted"
    too_big = await upload(client, user, month, PDF + b"\x00" * (10 * 1024 * 1024))
    assert too_big.status_code == 422
    assert too_big.json()["detail"] == "The file is larger than 10 MB"
    empty = await upload(client, user, month, b"")
    assert empty.status_code == 422

    photo = await upload(client, user, month, PNG, "../photo.exe")
    assert photo.json()["filename"] == "photo.png"
    assert photo.json()["mime"] == "image/png"


async def test_the_entry_must_belong_to_the_month(client: AsyncClient, storage: Storage) -> None:
    user = await new_user(client)
    october = (await create_month(client, user))["id"]
    november = (await create_month(client, user, month=11))["id"]
    entry = await allocation(client, user, october)
    response = await upload(client, user, november, entry_id=entry)
    assert response.status_code == 422
    assert response.json()["detail"] == "The entry belongs to another month"


async def test_delete_and_undo(client: AsyncClient, storage: Storage) -> None:
    user = await new_user(client)
    month = (await create_month(client, user))["id"]
    receipt = (await upload(client, user, month)).json()
    url = f"/api/v1/attachments/{receipt['id']}"

    assert (await client.delete(url, headers=user.headers)).status_code == 204
    assert (
        await client.get(f"/api/v1/months/{month}/attachments", headers=user.headers)
    ).json() == []
    assert (await client.get(f"{url}/url", headers=user.headers)).status_code == 404
    assert (await client.delete(url, headers=user.headers)).status_code == 404

    restored = await client.post(f"{url}/restore", headers=user.headers)
    assert restored.status_code == 200
    assert restored.json()["id"] == receipt["id"]
    assert (await client.post(f"{url}/restore", headers=user.headers)).status_code == 404


async def test_receipts_of_a_deleted_entry_are_hidden(
    client: AsyncClient, storage: Storage
) -> None:
    user = await new_user(client)
    month = (await create_month(client, user))["id"]
    entry = await allocation(client, user, month)
    await upload(client, user, month, entry_id=entry)
    loose = (await upload(client, user, month)).json()

    await client.delete(f"/api/v1/entries/{entry}", headers=user.headers)
    listed = await client.get(f"/api/v1/months/{month}/attachments", headers=user.headers)
    assert [a["id"] for a in listed.json()] == [loose["id"]]

    await client.post(f"/api/v1/entries/{entry}/restore", headers=user.headers)
    listed = await client.get(f"/api/v1/months/{month}/attachments", headers=user.headers)
    assert len(listed.json()) == 2


async def test_a_closed_month_rejects_receipt_changes(
    client: AsyncClient, storage: Storage
) -> None:
    user = await new_user(client)
    month = (await create_month(client, user))["id"]
    receipt = (await upload(client, user, month)).json()
    await client.post(f"/api/v1/months/{month}/close", headers=user.headers)

    assert (await upload(client, user, month)).json()["code"] == "month_closed"
    deleted = await client.delete(f"/api/v1/attachments/{receipt['id']}", headers=user.headers)
    assert deleted.status_code == 409
    # Reading still works.
    link = await client.get(f"/api/v1/attachments/{receipt['id']}/url", headers=user.headers)
    assert link.status_code == 200

    await client.post(f"/api/v1/months/{month}/reopen", headers=user.headers)
    await client.delete(f"/api/v1/attachments/{receipt['id']}", headers=user.headers)
    await client.post(f"/api/v1/months/{month}/close", headers=user.headers)
    restore = await client.post(
        f"/api/v1/attachments/{receipt['id']}/restore", headers=user.headers
    )
    assert restore.status_code == 409


async def test_deleting_a_users_files_empties_their_prefix(storage: Storage) -> None:
    user_id = uuid.uuid4()
    await storage.put(f"users/{user_id}/attachments/a", PDF, "application/pdf")
    await storage.put(f"users/{user_id}/exports/b", b"x", "text/csv")
    await storage.put(f"users/{uuid.uuid4()}/attachments/c", PDF, "application/pdf")
    assert await storage.get(f"users/{user_id}/attachments/a") == PDF
    assert await storage.delete_prefix(f"users/{user_id}/") == 2
    assert await storage.delete_prefix(f"users/{user_id}/") == 0
