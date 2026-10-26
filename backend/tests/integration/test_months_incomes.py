import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from httpx import AsyncClient
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import MovementType
from app.models import Entry, Income
from tests.integration.helpers import ApiUser, new_user


async def create_month(
    client: AsyncClient, user: ApiUser, year: int = 2026, month: int = 10, **extra: Any
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/months", headers=user.headers, json={"year": year, "month": month, **extra}
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def add_income(
    client: AsyncClient, user: ApiUser, month_id: str, **overrides: Any
) -> dict[str, Any]:
    payload = {"source": "Salary", "amount": "1500.00", "received_on": "2026-10-05"}
    response = await client.post(
        f"/api/v1/months/{month_id}/incomes", headers=user.headers, json={**payload, **overrides}
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def label_id(client: AsyncClient, user: ApiUser, name: str) -> uuid.UUID:
    labels = (await client.get("/api/v1/labels", headers=user.headers)).json()
    return uuid.UUID(next(lb["id"] for lb in labels if lb["name"] == name))


# --- meses -------------------------------------------------------------------


async def test_create_list_and_get_month(client: AsyncClient) -> None:
    user = await new_user(client)
    october = await create_month(client, user, note="Holiday month")
    await create_month(client, user, month=9)
    await create_month(client, user, year=2025, month=12)

    listed = (await client.get("/api/v1/months", headers=user.headers)).json()
    assert [(m["year"], m["month"]) for m in listed] == [(2026, 10), (2026, 9), (2025, 12)]
    only_2026 = (await client.get("/api/v1/months?year=2026", headers=user.headers)).json()
    assert len(only_2026) == 2

    got = await client.get(f"/api/v1/months/{october['id']}", headers=user.headers)
    assert got.json()["note"] == "Holiday month"
    assert got.json()["closed_at"] is None


async def test_month_is_unique_per_user(client: AsyncClient) -> None:
    alice, bob = await new_user(client), await new_user(client)
    await create_month(client, alice)
    duplicate = await client.post(
        "/api/v1/months", headers=alice.headers, json={"year": 2026, "month": 10}
    )
    assert duplicate.status_code == 409
    await create_month(client, bob)  # another user has their own October


async def test_month_validation(client: AsyncClient) -> None:
    user = await new_user(client)
    for payload in ({"year": 2026, "month": 13}, {"year": 1999, "month": 1}):
        response = await client.post("/api/v1/months", headers=user.headers, json=payload)
        assert response.status_code == 422


async def test_copy_previous_month_allocations_and_incomes(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await new_user(client)
    food = await label_id(client, user, "Food")
    september = await create_month(client, user, month=9)
    await add_income(client, user, september["id"], received_on="2026-09-30")
    session.add(
        Entry(
            user_id=user.id,
            month_id=uuid.UUID(september["id"]),
            label_id=food,
            amount=Decimal("200.00"),
            movement_type=MovementType.ALLOCATION,
            occurred_on=date(2026, 9, 1),
        )
    )
    # An "add money" income is a one-off and must not be copied.
    extra = Income(
        user_id=user.id,
        month_id=uuid.UUID(september["id"]),
        source="Extra",
        amount=Decimal("50.00"),
        received_on=date(2026, 9, 15),
    )
    session.add(extra)
    await session.flush()
    session.add(
        Entry(
            user_id=user.id,
            month_id=uuid.UUID(september["id"]),
            label_id=food,
            amount=Decimal("50.00"),
            movement_type=MovementType.ADDITION,
            income_id=extra.id,
            occurred_on=date(2026, 9, 15),
        )
    )
    await session.flush()

    october = await create_month(client, user, copy_allocations=True, copy_incomes=True)

    incomes = (
        await client.get(f"/api/v1/months/{october['id']}/incomes", headers=user.headers)
    ).json()
    assert [(i["source"], i["amount"], i["received_on"]) for i in incomes] == [
        ("Salary", "1500.00", "2026-10-30")
    ]
    allocations = [
        e
        for e in (await session.scalars(_entries_of(october["id"]))).all()
        if e.movement_type is MovementType.ALLOCATION
    ]
    assert [(a.label_id, a.amount, a.occurred_on) for a in allocations] == [
        (food, Decimal("200.00"), date(2026, 10, 1))
    ]


async def test_copy_is_a_no_op_without_previous_month(client: AsyncClient) -> None:
    user = await new_user(client)
    month = await create_month(client, user, copy_allocations=True, copy_incomes=True)
    incomes = await client.get(f"/api/v1/months/{month['id']}/incomes", headers=user.headers)
    assert incomes.json() == []


async def test_closed_month_blocks_writes_until_reopened(client: AsyncClient) -> None:
    user = await new_user(client)
    month = await create_month(client, user)
    income = await add_income(client, user, month["id"])
    url = f"/api/v1/months/{month['id']}"

    closed = await client.post(f"{url}/close", headers=user.headers)
    assert closed.json()["closed_at"] is not None

    blocked = [
        await client.patch(url, headers=user.headers, json={"note": "x"}),
        await client.post(
            f"{url}/incomes",
            headers=user.headers,
            json={"source": "Extra", "amount": "10.00", "received_on": "2026-10-10"},
        ),
        await client.patch(
            f"/api/v1/incomes/{income['id']}", headers=user.headers, json={"amount": "1.00"}
        ),
        await client.delete(f"/api/v1/incomes/{income['id']}", headers=user.headers),
        await client.delete(url, headers=user.headers),
    ]
    assert [r.status_code for r in blocked] == [409] * 5
    assert all(r.json()["code"] == "month_closed" for r in blocked)

    await client.post(f"{url}/reopen", headers=user.headers)
    edited = await client.patch(url, headers=user.headers, json={"note": "Reviewed"})
    assert edited.status_code == 200
    assert edited.json()["note"] == "Reviewed"


async def test_delete_and_restore_month(client: AsyncClient) -> None:
    user = await new_user(client)
    month = await create_month(client, user)
    url = f"/api/v1/months/{month['id']}"
    assert (await client.delete(url, headers=user.headers)).status_code == 204
    assert (await client.get(url, headers=user.headers)).status_code == 404

    restored = await client.post(f"{url}/restore", headers=user.headers)
    assert restored.status_code == 200
    assert (await client.get(url, headers=user.headers)).status_code == 200


async def test_restore_conflicts_when_month_was_recreated(client: AsyncClient) -> None:
    user = await new_user(client)
    month = await create_month(client, user)
    await client.delete(f"/api/v1/months/{month['id']}", headers=user.headers)
    await create_month(client, user)
    restored = await client.post(f"/api/v1/months/{month['id']}/restore", headers=user.headers)
    assert restored.status_code == 409


# --- rendimentos -------------------------------------------------------------


async def test_income_crud_and_restore(client: AsyncClient) -> None:
    user = await new_user(client)
    month = await create_month(client, user)
    income = await add_income(client, user, month["id"])
    assert (income["amount"], income["from_addition"]) == ("1500.00", False)

    updated = await client.patch(
        f"/api/v1/incomes/{income['id']}",
        headers=user.headers,
        json={"amount": "1550.50", "source": "Salary + bonus"},
    )
    assert updated.json()["amount"] == "1550.50"

    assert (
        await client.delete(f"/api/v1/incomes/{income['id']}", headers=user.headers)
    ).status_code == 204
    listed = await client.get(f"/api/v1/months/{month['id']}/incomes", headers=user.headers)
    assert listed.json() == []

    await client.post(f"/api/v1/incomes/{income['id']}/restore", headers=user.headers)
    listed = await client.get(f"/api/v1/months/{month['id']}/incomes", headers=user.headers)
    assert [i["amount"] for i in listed.json()] == ["1550.50"]


async def test_income_validation(client: AsyncClient) -> None:
    user = await new_user(client)
    month = await create_month(client, user)
    url = f"/api/v1/months/{month['id']}/incomes"
    base = {"source": "Salary", "amount": "10.00", "received_on": "2026-10-05"}
    cases = [
        ({"amount": "0"}, 422),
        ({"amount": "-5.00"}, 422),
        ({"amount": "10.555"}, 422),
        ({"source": ""}, 422),
        ({"received_on": "2026-11-01"}, 422),  # outside the month
    ]
    for override, expected in cases:
        response = await client.post(url, headers=user.headers, json={**base, **override})
        assert response.status_code == expected, override


async def test_income_from_addition_is_read_only(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await new_user(client)
    month = await create_month(client, user)
    income = Income(
        user_id=user.id,
        month_id=uuid.UUID(month["id"]),
        source="Extra",
        amount=Decimal("50.00"),
        received_on=date(2026, 10, 15),
    )
    session.add(income)
    await session.flush()
    session.add(
        Entry(
            user_id=user.id,
            month_id=uuid.UUID(month["id"]),
            label_id=await label_id(client, user, "Investments"),
            amount=Decimal("50.00"),
            movement_type=MovementType.ADDITION,
            income_id=income.id,
            occurred_on=date(2026, 10, 15),
        )
    )
    await session.flush()

    listed = await client.get(f"/api/v1/months/{month['id']}/incomes", headers=user.headers)
    assert listed.json()[0]["from_addition"] is True
    edit = await client.patch(
        f"/api/v1/incomes/{income.id}", headers=user.headers, json={"amount": "1.00"}
    )
    delete = await client.delete(f"/api/v1/incomes/{income.id}", headers=user.headers)
    assert (edit.status_code, delete.status_code) == (409, 409)


# --- isolamento --------------------------------------------------------------


async def test_users_cannot_touch_each_others_months_and_incomes(client: AsyncClient) -> None:
    alice, bob = await new_user(client), await new_user(client)
    month = await create_month(client, alice)
    income = await add_income(client, alice, month["id"])
    m_url, i_url = f"/api/v1/months/{month['id']}", f"/api/v1/incomes/{income['id']}"
    attempts = [
        await client.get(m_url, headers=bob.headers),
        await client.patch(m_url, headers=bob.headers, json={"note": "x"}),
        await client.post(f"{m_url}/close", headers=bob.headers),
        await client.post(f"{m_url}/restore", headers=bob.headers),
        await client.delete(m_url, headers=bob.headers),
        await client.get(f"{m_url}/incomes", headers=bob.headers),
        await client.post(
            f"{m_url}/incomes",
            headers=bob.headers,
            json={"source": "x", "amount": "1.00", "received_on": "2026-10-01"},
        ),
        await client.patch(i_url, headers=bob.headers, json={"amount": "1.00"}),
        await client.delete(i_url, headers=bob.headers),
        await client.post(f"{i_url}/restore", headers=bob.headers),
    ]
    assert [r.status_code for r in attempts] == [404] * 10
    assert (await client.get("/api/v1/months", headers=bob.headers)).json() == []


def _entries_of(month_id: str) -> Select[tuple[Entry]]:
    return select(Entry).where(Entry.month_id == uuid.UUID(month_id), Entry.deleted_at.is_(None))
