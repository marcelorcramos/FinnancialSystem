import uuid
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import ledger
from app.domain.ledger import Movement
from app.models import AuditLog, Entry, Income
from tests.integration.helpers import ApiUser, create_month, label_id, new_user


async def add_money(
    client: AsyncClient, user: ApiUser, month_id: str, **payload: Any
) -> dict[str, Any]:
    body = {"amount": "12.00", "occurred_on": "2026-10-15", **payload}
    body["label_id"] = str(body["label_id"])
    response = await client.post(
        f"/api/v1/months/{month_id}/additions", headers=user.headers, json=body
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def month_movements(session: AsyncSession, month_id: str) -> list[Movement]:
    rows = await session.scalars(
        select(Entry).where(Entry.month_id == uuid.UUID(month_id), Entry.deleted_at.is_(None))
    )
    return [Movement(e.label_id, e.movement_type, e.amount) for e in rows]


async def month_income(session: AsyncSession, month_id: str) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(Income.amount), 0)).where(
            Income.month_id == uuid.UUID(month_id), Income.deleted_at.is_(None)
        )
    )
    return Decimal(total)


async def test_addition_creates_linked_entry_and_income(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await new_user(client)
    month = await create_month(client, user)
    investments = await label_id(client, user, "Investments")

    body = await add_money(
        client, user, month["id"], label_id=investments, amount="50.00", source="Freelance"
    )
    assert (body["movement_type"], body["amount"], body["source"]) == (
        "addition",
        "50.00",
        "Freelance",
    )
    assert body["income_id"] is not None

    incomes = (
        await client.get(f"/api/v1/months/{month['id']}/incomes", headers=user.headers)
    ).json()
    fields = ("id", "source", "amount", "received_on", "from_addition")
    assert [tuple(i[f] for f in fields) for i in incomes] == [
        (body["income_id"], "Freelance", "50.00", "2026-10-15", True)
    ]

    audited = (
        await session.scalars(
            select(AuditLog.entity).where(
                AuditLog.entity_id.in_([uuid.UUID(body["id"]), uuid.UUID(body["income_id"])])
            )
        )
    ).all()
    assert sorted(audited) == ["entry", "income"]


async def test_addition_without_source_is_extra_income(client: AsyncClient) -> None:
    user = await new_user(client)
    month = await create_month(client, user)
    body = await add_money(client, user, month["id"], label_id=await label_id(client, user, "Food"))
    assert body["source"] == "Extra income"


async def test_food_200_plus_12_is_212(client: AsyncClient, session: AsyncSession) -> None:
    user = await new_user(client)
    month = await create_month(client, user)
    food = await label_id(client, user, "Food")
    await client.put(
        f"/api/v1/months/{month['id']}/allocations/{food}",
        headers=user.headers,
        json={"amount": "200.00"},
    )
    await add_money(client, user, month["id"], label_id=food, amount="12.00")

    totals = ledger.label_totals(await month_movements(session, month["id"]))
    assert totals[food] == Decimal("212.00")


async def test_addition_does_not_change_unallocated(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await new_user(client)
    month = await create_month(client, user)
    food = await label_id(client, user, "Food")
    await client.post(
        f"/api/v1/months/{month['id']}/incomes",
        headers=user.headers,
        json={"source": "Salary", "amount": "1000.00", "received_on": "2026-10-01"},
    )
    await client.put(
        f"/api/v1/months/{month['id']}/allocations/{food}",
        headers=user.headers,
        json={"amount": "200.00"},
    )

    async def unallocated() -> Decimal:
        movements = await month_movements(session, month["id"])
        return ledger.unallocated(await month_income(session, month["id"]), movements)

    before = await unallocated()
    await add_money(client, user, month["id"], label_id=food, amount="50.00")
    assert before == await unallocated() == Decimal("800.00")
    assert await month_income(session, month["id"]) == Decimal("1050.00")


async def test_addition_validation(client: AsyncClient) -> None:
    user = await new_user(client)
    month = await create_month(client, user)
    food = str(await label_id(client, user, "Food"))
    url = f"/api/v1/months/{month['id']}/additions"
    base = {"label_id": food, "amount": "10.00", "occurred_on": "2026-10-10"}
    cases = [
        {"amount": "0"},
        {"amount": "-1.00"},
        {"amount": "1.001"},
        {"occurred_on": "2026-09-30"},  # outside the month
        {"source": ""},
        {"label_id": "not-a-uuid"},
    ]
    for override in cases:
        response = await client.post(url, headers=user.headers, json={**base, **override})
        assert response.status_code == 422, override


async def test_archived_label_cannot_receive_money(client: AsyncClient) -> None:
    user = await new_user(client)
    month = await create_month(client, user)
    food = await label_id(client, user, "Food")
    await client.post(f"/api/v1/labels/{food}/archive", headers=user.headers)
    response = await client.post(
        f"/api/v1/months/{month['id']}/additions",
        headers=user.headers,
        json={"label_id": str(food), "amount": "10.00", "occurred_on": "2026-10-10"},
    )
    assert response.status_code == 422


async def test_closed_month_rejects_additions(client: AsyncClient, session: AsyncSession) -> None:
    user = await new_user(client)
    month = await create_month(client, user)
    await client.post(f"/api/v1/months/{month['id']}/close", headers=user.headers)
    response = await client.post(
        f"/api/v1/months/{month['id']}/additions",
        headers=user.headers,
        json={
            "label_id": str(await label_id(client, user, "Food")),
            "amount": "10.00",
            "occurred_on": "2026-10-10",
        },
    )
    assert (response.status_code, response.json()["code"]) == (409, "month_closed")
    assert await month_income(session, month["id"]) == Decimal("0")


async def test_users_cannot_add_money_to_each_others_months_or_labels(
    client: AsyncClient,
) -> None:
    alice, bob = await new_user(client), await new_user(client)
    alice_month, bob_month = await create_month(client, alice), await create_month(client, bob)
    alice_food, bob_food = (
        await label_id(client, alice, "Food"),
        await label_id(client, bob, "Food"),
    )
    payload = {"amount": "10.00", "occurred_on": "2026-10-10"}
    attempts = [
        await client.post(
            f"/api/v1/months/{alice_month['id']}/additions",
            headers=bob.headers,
            json={**payload, "label_id": str(bob_food)},
        ),
        await client.post(
            f"/api/v1/months/{bob_month['id']}/additions",
            headers=bob.headers,
            json={**payload, "label_id": str(alice_food)},
        ),
    ]
    assert [r.status_code for r in attempts] == [404, 404]
