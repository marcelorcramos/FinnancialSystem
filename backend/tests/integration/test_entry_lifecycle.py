"""Listing, editing, deleting and undoing entries."""

import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Entry, Income
from tests.integration.helpers import ApiUser, create_month, label_id, new_user


class Ctx:
    def __init__(self, user: ApiUser, month: dict[str, Any], labels: dict[str, uuid.UUID]):
        self.user, self.month, self.labels = user, month, labels

    @property
    def month_url(self) -> str:
        return f"/api/v1/months/{self.month['id']}"


async def setup(client: AsyncClient) -> Ctx:
    user = await new_user(client)
    month = await create_month(client, user)
    labels = {n: await label_id(client, user, n) for n in ("Food", "Savings", "Investments")}
    return Ctx(user, month, labels)


async def allocate(client: AsyncClient, ctx: Ctx, label: str, amount: str) -> dict[str, Any]:
    response = await client.put(
        f"{ctx.month_url}/allocations/{ctx.labels[label]}",
        headers=ctx.user.headers,
        json={"amount": amount},
    )
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


async def add_money(client: AsyncClient, ctx: Ctx, label: str, **extra: Any) -> dict[str, Any]:
    payload = {"label_id": str(ctx.labels[label]), "amount": "50.00", "occurred_on": "2026-10-15"}
    response = await client.post(
        f"{ctx.month_url}/additions", headers=ctx.user.headers, json={**payload, **extra}
    )
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


async def transfer(client: AsyncClient, ctx: Ctx, source: str, target: str) -> dict[str, Any]:
    response = await client.post(
        f"{ctx.month_url}/transfers",
        headers=ctx.user.headers,
        json={
            "from_label_id": str(ctx.labels[source]),
            "to_label_id": str(ctx.labels[target]),
            "amount": "30.00",
            "occurred_on": "2026-10-20",
        },
    )
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


async def entries(client: AsyncClient, ctx: Ctx) -> list[dict[str, Any]]:
    response = await client.get(f"{ctx.month_url}/entries", headers=ctx.user.headers)
    assert response.status_code == 200
    body: list[dict[str, Any]] = response.json()
    return body


async def incomes(client: AsyncClient, ctx: Ctx) -> list[dict[str, Any]]:
    body: list[dict[str, Any]] = (
        await client.get(f"{ctx.month_url}/incomes", headers=ctx.user.headers)
    ).json()
    return body


# --- listing -----------------------------------------------------------------


async def test_list_shows_entries_by_date_with_their_origin(client: AsyncClient) -> None:
    ctx = await setup(client)
    await transfer(client, ctx, "Savings", "Food")  # 20th
    await add_money(client, ctx, "Investments", source="Freelance")  # 15th
    await allocate(client, ctx, "Food", "200.00")  # 1st

    listed = await entries(client, ctx)
    assert [e["occurred_on"] for e in listed] == [
        "2026-10-01",
        "2026-10-15",
        "2026-10-20",
        "2026-10-20",
    ]
    by_origin = {e["origin"]: e for e in listed}
    assert by_origin["initial_distribution"]["label_id"] == str(ctx.labels["Food"])
    assert by_origin["external_income"]["source"] == "Freelance"
    assert by_origin["transfer_out"]["counterpart_label_id"] == str(ctx.labels["Food"])
    assert by_origin["transfer_in"]["counterpart_label_id"] == str(ctx.labels["Savings"])


async def test_list_of_empty_month_and_other_users_month(client: AsyncClient) -> None:
    ctx, other = await setup(client), await setup(client)
    assert await entries(client, ctx) == []
    response = await client.get(f"{ctx.month_url}/entries", headers=other.user.headers)
    assert response.status_code == 404


# --- editing -----------------------------------------------------------------


async def test_edit_allocation_amount_and_note(client: AsyncClient) -> None:
    ctx = await setup(client)
    allocation = await allocate(client, ctx, "Food", "200.00")
    response = await client.patch(
        f"/api/v1/entries/{allocation['id']}",
        headers=ctx.user.headers,
        json={"amount": "220.00", "note": "More guests"},
    )
    assert (response.json()["amount"], response.json()["note"]) == ("220.00", "More guests")


async def test_allocation_rejects_date_and_label_changes(client: AsyncClient) -> None:
    ctx = await setup(client)
    allocation = await allocate(client, ctx, "Food", "200.00")
    for payload in ({"occurred_on": "2026-10-05"}, {"label_id": str(ctx.labels["Savings"])}):
        response = await client.patch(
            f"/api/v1/entries/{allocation['id']}", headers=ctx.user.headers, json=payload
        )
        assert response.status_code == 422, payload


async def test_edit_addition_keeps_income_in_sync(client: AsyncClient) -> None:
    ctx = await setup(client)
    addition = await add_money(client, ctx, "Investments")
    response = await client.patch(
        f"/api/v1/entries/{addition['id']}",
        headers=ctx.user.headers,
        json={
            "amount": "75.00",
            "occurred_on": "2026-10-18",
            "label_id": str(ctx.labels["Savings"]),
            "source": "Bonus",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["label_id"] == str(ctx.labels["Savings"])
    [income] = await incomes(client, ctx)
    assert (income["amount"], income["received_on"], income["source"]) == (
        "75.00",
        "2026-10-18",
        "Bonus",
    )


async def test_transfer_legs_are_edited_through_transfers(client: AsyncClient) -> None:
    ctx = await setup(client)
    body = await transfer(client, ctx, "Savings", "Food")
    response = await client.patch(
        f"/api/v1/entries/{body['out_entry_id']}",
        headers=ctx.user.headers,
        json={"amount": "1.00"},
    )
    assert response.status_code == 422


async def test_edit_validation(client: AsyncClient) -> None:
    ctx = await setup(client)
    addition = await add_money(client, ctx, "Food")
    for payload in ({"amount": "0"}, {"occurred_on": "2026-11-02"}):
        response = await client.patch(
            f"/api/v1/entries/{addition['id']}", headers=ctx.user.headers, json=payload
        )
        assert response.status_code == 422, payload


# --- deleting and undo -------------------------------------------------------


async def test_deleting_one_transfer_leg_deletes_both(
    client: AsyncClient, session: AsyncSession
) -> None:
    ctx = await setup(client)
    body = await transfer(client, ctx, "Savings", "Food")

    response = await client.delete(
        f"/api/v1/entries/{body['in_entry_id']}", headers=ctx.user.headers
    )
    assert response.status_code == 204
    legs = (
        await session.scalars(
            select(Entry).where(Entry.transfer_id == uuid.UUID(body["transfer_id"]))
        )
    ).all()
    assert len(legs) == 2
    assert all(leg.deleted_at is not None for leg in legs)
    assert await entries(client, ctx) == []


async def test_undo_restores_both_transfer_legs(client: AsyncClient) -> None:
    ctx = await setup(client)
    body = await transfer(client, ctx, "Savings", "Food")
    await client.delete(f"/api/v1/entries/{body['out_entry_id']}", headers=ctx.user.headers)

    restored = await client.post(
        f"/api/v1/entries/{body['out_entry_id']}/restore", headers=ctx.user.headers
    )
    assert restored.status_code == 200
    assert {e["origin"] for e in await entries(client, ctx)} == {"transfer_in", "transfer_out"}


async def test_delete_and_restore_transfer_by_transfer_id(client: AsyncClient) -> None:
    ctx = await setup(client)
    body = await transfer(client, ctx, "Savings", "Food")
    url = f"/api/v1/transfers/{body['transfer_id']}"
    assert (await client.delete(url, headers=ctx.user.headers)).status_code == 204
    assert await entries(client, ctx) == []
    restored = await client.post(f"{url}/restore", headers=ctx.user.headers)
    assert restored.json()["amount"] == "30.00"
    assert len(await entries(client, ctx)) == 2


async def test_deleting_addition_deletes_its_income_and_undo_brings_both(
    client: AsyncClient, session: AsyncSession
) -> None:
    ctx = await setup(client)
    addition = await add_money(client, ctx, "Food")
    url = f"/api/v1/entries/{addition['id']}"

    assert (await client.delete(url, headers=ctx.user.headers)).status_code == 204
    assert await incomes(client, ctx) == []
    income = await session.get(Income, uuid.UUID(addition["income_id"]))
    assert income is not None and income.deleted_at is not None

    await client.post(f"{url}/restore", headers=ctx.user.headers)
    assert [i["amount"] for i in await incomes(client, ctx)] == ["50.00"]
    assert [e["origin"] for e in await entries(client, ctx)] == ["external_income"]


async def test_delete_and_restore_allocation(client: AsyncClient) -> None:
    ctx = await setup(client)
    allocation = await allocate(client, ctx, "Food", "200.00")
    url = f"/api/v1/entries/{allocation['id']}"
    await client.delete(url, headers=ctx.user.headers)
    assert await entries(client, ctx) == []
    assert (await client.post(f"{url}/restore", headers=ctx.user.headers)).status_code == 200
    assert [e["amount"] for e in await entries(client, ctx)] == ["200.00"]


async def test_restore_allocation_conflicts_with_a_newer_one(client: AsyncClient) -> None:
    ctx = await setup(client)
    old = await allocate(client, ctx, "Food", "200.00")
    await client.delete(f"/api/v1/entries/{old['id']}", headers=ctx.user.headers)
    await allocate(client, ctx, "Food", "250.00")
    response = await client.post(f"/api/v1/entries/{old['id']}/restore", headers=ctx.user.headers)
    assert response.status_code == 409


async def test_delete_and_restore_unknown_entries(client: AsyncClient) -> None:
    ctx = await setup(client)
    allocation = await allocate(client, ctx, "Food", "200.00")
    missing = uuid.uuid4()
    attempts = [
        await client.delete(f"/api/v1/entries/{missing}", headers=ctx.user.headers),
        await client.post(f"/api/v1/entries/{missing}/restore", headers=ctx.user.headers),
        # Restoring an entry that is not deleted.
        await client.post(f"/api/v1/entries/{allocation['id']}/restore", headers=ctx.user.headers),
        await client.delete(f"/api/v1/transfers/{missing}", headers=ctx.user.headers),
        await client.post(f"/api/v1/transfers/{missing}/restore", headers=ctx.user.headers),
    ]
    assert [r.status_code for r in attempts] == [404] * 5


# --- closed month and isolation ----------------------------------------------


async def test_closed_month_rejects_edit_delete_and_undo(client: AsyncClient) -> None:
    ctx = await setup(client)
    allocation = await allocate(client, ctx, "Food", "200.00")
    addition = await add_money(client, ctx, "Food")
    await client.delete(f"/api/v1/entries/{addition['id']}", headers=ctx.user.headers)
    await client.post(f"{ctx.month_url}/close", headers=ctx.user.headers)

    attempts = [
        await client.patch(
            f"/api/v1/entries/{allocation['id']}",
            headers=ctx.user.headers,
            json={"amount": "1.00"},
        ),
        await client.delete(f"/api/v1/entries/{allocation['id']}", headers=ctx.user.headers),
        await client.post(f"/api/v1/entries/{addition['id']}/restore", headers=ctx.user.headers),
    ]
    assert [r.status_code for r in attempts] == [409, 409, 409]
    assert all(r.json()["code"] == "month_closed" for r in attempts)


async def test_users_cannot_touch_each_others_entries(client: AsyncClient) -> None:
    alice, bob = await setup(client), await setup(client)
    allocation = await allocate(client, alice, "Food", "200.00")
    body = await transfer(client, alice, "Savings", "Food")
    url = f"/api/v1/entries/{allocation['id']}"
    attempts = [
        await client.patch(url, headers=bob.user.headers, json={"amount": "1.00"}),
        await client.delete(url, headers=bob.user.headers),
        await client.delete(f"/api/v1/transfers/{body['transfer_id']}", headers=bob.user.headers),
    ]
    assert [r.status_code for r in attempts] == [404, 404, 404]

    await client.delete(url, headers=alice.user.headers)
    restore = await client.post(f"{url}/restore", headers=bob.user.headers)
    assert restore.status_code == 404
    assert [e["amount"] for e in await entries(client, alice)] == ["30.00", "30.00"]
