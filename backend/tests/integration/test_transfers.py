import uuid
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import ledger
from app.domain.enums import MovementType
from app.domain.ledger import Movement
from app.models import Entry
from tests.integration.helpers import ApiUser, create_month, label_id, new_user


class Ctx:
    def __init__(self, user: ApiUser, month: dict[str, Any], labels: dict[str, uuid.UUID]):
        self.user, self.month, self.labels = user, month, labels


async def setup(client: AsyncClient) -> Ctx:
    user = await new_user(client)
    month = await create_month(client, user)
    names = ("Food", "Savings", "Investments", "Housing")
    labels = {name: await label_id(client, user, name) for name in names}
    return Ctx(user, month, labels)


async def transfer(
    client: AsyncClient, ctx: Ctx, source: str, target: str, amount: str = "12.00", **extra: Any
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/months/{ctx.month['id']}/transfers",
        headers=ctx.user.headers,
        json={
            "from_label_id": str(ctx.labels[source]),
            "to_label_id": str(ctx.labels[target]),
            "amount": amount,
            "occurred_on": "2026-10-20",
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def allocate(client: AsyncClient, ctx: Ctx, label: str, amount: str) -> None:
    response = await client.put(
        f"/api/v1/months/{ctx.month['id']}/allocations/{ctx.labels[label]}",
        headers=ctx.user.headers,
        json={"amount": amount},
    )
    assert response.status_code == 200


async def legs(session: AsyncSession, transfer_id: str) -> list[Entry]:
    stmt = (
        select(Entry)
        .where(Entry.transfer_id == uuid.UUID(transfer_id), Entry.deleted_at.is_(None))
        .order_by(Entry.movement_type)
    )
    return list((await session.scalars(stmt)).all())


async def movements(session: AsyncSession, month_id: str) -> list[Movement]:
    rows = await session.scalars(
        select(Entry).where(Entry.month_id == uuid.UUID(month_id), Entry.deleted_at.is_(None))
    )
    return [Movement(e.label_id, e.movement_type, e.amount) for e in rows]


async def test_transfer_creates_a_pair_of_legs(client: AsyncClient, session: AsyncSession) -> None:
    ctx = await setup(client)
    body = await transfer(client, ctx, "Savings", "Food", "30.00", note="Dinner out")
    assert (body["amount"], body["occurred_on"], body["note"]) == (
        "30.00",
        "2026-10-20",
        "Dinner out",
    )

    pair = await legs(session, body["transfer_id"])
    assert [leg.movement_type for leg in pair] == [
        MovementType.TRANSFER_IN,
        MovementType.TRANSFER_OUT,
    ]
    by_type = {leg.movement_type: leg for leg in pair}
    assert by_type[MovementType.TRANSFER_OUT].label_id == ctx.labels["Savings"]
    assert by_type[MovementType.TRANSFER_IN].label_id == ctx.labels["Food"]
    assert {leg.amount for leg in pair} == {Decimal("30.00")}
    assert {leg.occurred_on.isoformat() for leg in pair} == {"2026-10-20"}
    assert str(by_type[MovementType.TRANSFER_OUT].id) == body["out_entry_id"]


async def test_food_200_plus_12_from_savings_is_212(
    client: AsyncClient, session: AsyncSession
) -> None:
    ctx = await setup(client)
    await allocate(client, ctx, "Food", "200.00")
    await allocate(client, ctx, "Savings", "300.00")
    await transfer(client, ctx, "Savings", "Food", "12.00")

    totals = ledger.label_totals(await movements(session, ctx.month["id"]))
    assert totals[ctx.labels["Food"]] == Decimal("212.00")
    assert totals[ctx.labels["Savings"]] == Decimal("288.00")


async def test_month_total_is_invariant_to_transfers(
    client: AsyncClient, session: AsyncSession
) -> None:
    ctx = await setup(client)
    await allocate(client, ctx, "Food", "200.00")
    await allocate(client, ctx, "Savings", "300.00")
    before = ledger.month_total(await movements(session, ctx.month["id"]))

    await transfer(client, ctx, "Savings", "Food", "50.00")
    await transfer(client, ctx, "Food", "Investments", "70.25")
    after = await movements(session, ctx.month["id"])

    assert before == ledger.month_total(after) == Decimal("500.00")
    ins = sum(m.amount for m in after if m.movement_type is MovementType.TRANSFER_IN)
    outs = sum(m.amount for m in after if m.movement_type is MovementType.TRANSFER_OUT)
    assert ins == outs


async def test_saving_label_can_go_negative(client: AsyncClient, session: AsyncSession) -> None:
    ctx = await setup(client)
    await transfer(client, ctx, "Savings", "Housing", "150.00")
    totals = ledger.label_totals(await movements(session, ctx.month["id"]))
    assert totals[ctx.labels["Savings"]] == Decimal("-150.00")


async def test_transfer_validation(client: AsyncClient) -> None:
    ctx = await setup(client)
    url = f"/api/v1/months/{ctx.month['id']}/transfers"
    base = {
        "from_label_id": str(ctx.labels["Savings"]),
        "to_label_id": str(ctx.labels["Food"]),
        "amount": "10.00",
        "occurred_on": "2026-10-10",
    }
    cases = [
        {"to_label_id": str(ctx.labels["Savings"])},  # same label
        {"amount": "0"},
        {"amount": "-3.00"},
        {"amount": "3.333"},
        {"occurred_on": "2026-11-01"},
    ]
    for override in cases:
        response = await client.post(url, headers=ctx.user.headers, json={**base, **override})
        assert response.status_code == 422, override


async def test_archived_labels_cannot_be_used(client: AsyncClient) -> None:
    ctx = await setup(client)
    await client.post(f"/api/v1/labels/{ctx.labels['Food']}/archive", headers=ctx.user.headers)
    for source, target in (("Food", "Savings"), ("Savings", "Food")):
        response = await client.post(
            f"/api/v1/months/{ctx.month['id']}/transfers",
            headers=ctx.user.headers,
            json={
                "from_label_id": str(ctx.labels[source]),
                "to_label_id": str(ctx.labels[target]),
                "amount": "1.00",
                "occurred_on": "2026-10-10",
            },
        )
        assert response.status_code == 422


async def test_update_changes_both_legs(client: AsyncClient, session: AsyncSession) -> None:
    ctx = await setup(client)
    body = await transfer(client, ctx, "Savings", "Food", "30.00")
    url = f"/api/v1/transfers/{body['transfer_id']}"

    updated = await client.patch(
        url,
        headers=ctx.user.headers,
        json={"amount": "40.00", "occurred_on": "2026-10-25", "note": "Fixed"},
    )
    assert updated.status_code == 200, updated.text
    pair = await legs(session, body["transfer_id"])
    assert {leg.amount for leg in pair} == {Decimal("40.00")}
    assert {leg.occurred_on.isoformat() for leg in pair} == {"2026-10-25"}
    assert {leg.note for leg in pair} == {"Fixed"}
    assert updated.json()["out_entry_id"] == body["out_entry_id"]


async def test_update_can_change_labels_and_swap_direction(
    client: AsyncClient, session: AsyncSession
) -> None:
    ctx = await setup(client)
    body = await transfer(client, ctx, "Savings", "Food")
    url = f"/api/v1/transfers/{body['transfer_id']}"

    moved = await client.patch(
        url, headers=ctx.user.headers, json={"to_label_id": str(ctx.labels["Investments"])}
    )
    assert moved.json()["to_label_id"] == str(ctx.labels["Investments"])

    swapped = await client.patch(
        url,
        headers=ctx.user.headers,
        json={
            "from_label_id": str(ctx.labels["Investments"]),
            "to_label_id": str(ctx.labels["Savings"]),
        },
    )
    assert swapped.status_code == 200
    by_type = {leg.movement_type: leg for leg in await legs(session, body["transfer_id"])}
    assert by_type[MovementType.TRANSFER_OUT].label_id == ctx.labels["Investments"]
    assert by_type[MovementType.TRANSFER_IN].label_id == ctx.labels["Savings"]


async def test_update_rejects_invalid_changes(client: AsyncClient) -> None:
    ctx = await setup(client)
    body = await transfer(client, ctx, "Savings", "Food")
    url = f"/api/v1/transfers/{body['transfer_id']}"
    cases = [
        {"to_label_id": str(ctx.labels["Savings"])},  # would become Savings -> Savings
        {"occurred_on": "2026-09-30"},
        {"amount": "0"},
    ]
    for payload in cases:
        response = await client.patch(url, headers=ctx.user.headers, json=payload)
        assert response.status_code == 422, payload
    missing = await client.patch(
        f"/api/v1/transfers/{uuid.uuid4()}", headers=ctx.user.headers, json={"amount": "1"}
    )
    assert missing.status_code == 404


async def test_closed_month_rejects_transfers(client: AsyncClient) -> None:
    ctx = await setup(client)
    body = await transfer(client, ctx, "Savings", "Food")
    await client.post(f"/api/v1/months/{ctx.month['id']}/close", headers=ctx.user.headers)

    created = await client.post(
        f"/api/v1/months/{ctx.month['id']}/transfers",
        headers=ctx.user.headers,
        json={
            "from_label_id": str(ctx.labels["Savings"]),
            "to_label_id": str(ctx.labels["Food"]),
            "amount": "1.00",
            "occurred_on": "2026-10-10",
        },
    )
    updated = await client.patch(
        f"/api/v1/transfers/{body['transfer_id']}",
        headers=ctx.user.headers,
        json={"amount": "1.00"},
    )
    assert [created.status_code, updated.status_code] == [409, 409]


async def test_users_cannot_touch_each_others_transfers(client: AsyncClient) -> None:
    alice, bob = await setup(client), await setup(client)
    body = await transfer(client, alice, "Savings", "Food")
    attempts = [
        # Bob edits Alice's transfer, uses Alice's labels on his month, or her month.
        await client.patch(
            f"/api/v1/transfers/{body['transfer_id']}",
            headers=bob.user.headers,
            json={"amount": "1.00"},
        ),
        await client.post(
            f"/api/v1/months/{bob.month['id']}/transfers",
            headers=bob.user.headers,
            json={
                "from_label_id": str(alice.labels["Savings"]),
                "to_label_id": str(bob.labels["Food"]),
                "amount": "1.00",
                "occurred_on": "2026-10-10",
            },
        ),
        await client.post(
            f"/api/v1/months/{alice.month['id']}/transfers",
            headers=bob.user.headers,
            json={
                "from_label_id": str(bob.labels["Savings"]),
                "to_label_id": str(bob.labels["Food"]),
                "amount": "1.00",
                "occurred_on": "2026-10-10",
            },
        ),
    ]
    assert [r.status_code for r in attempts] == [404, 404, 404]
    # Alice cannot point her transfer at Bob's label either.
    hijack = await client.patch(
        f"/api/v1/transfers/{body['transfer_id']}",
        headers=alice.user.headers,
        json={"to_label_id": str(bob.labels["Food"])},
    )
    assert hijack.status_code == 404
