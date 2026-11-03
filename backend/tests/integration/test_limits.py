"""Limits per label: default and per month, and the month status (Phase 8)."""

from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutboxEvent
from tests.integration.helpers import ApiUser, create_month, label_id, new_user


async def allocate(client: AsyncClient, user: ApiUser, month: str, label: str, amount: str) -> None:
    response = await client.put(
        f"/api/v1/months/{month}/allocations/{await label_id(client, user, label)}",
        headers=user.headers,
        json={"amount": amount},
    )
    assert response.status_code == 200, response.text


async def status(client: AsyncClient, user: ApiUser, month: str) -> list[dict[str, Any]]:
    response = await client.get(f"/api/v1/months/{month}/limits", headers=user.headers)
    assert response.status_code == 200, response.text
    body: list[dict[str, Any]] = response.json()
    return body


async def test_default_limit_and_month_override(client: AsyncClient) -> None:
    user = await new_user(client)
    october = (await create_month(client, user, 2026, 10))["id"]
    november = (await create_month(client, user, 2026, 11))["id"]
    food = await label_id(client, user, "Food")
    await allocate(client, user, october, "Food", "250")
    await allocate(client, user, november, "Food", "250")

    response = await client.put(
        f"/api/v1/labels/{food}/limit", headers=user.headers, json={"amount": "300"}
    )
    assert response.status_code == 200
    assert response.json()["month_id"] is None

    response = await client.put(
        f"/api/v1/months/{november}/limits/{food}", headers=user.headers, json={"amount": "200"}
    )
    assert response.status_code == 200

    [oct_food] = await status(client, user, october)
    assert (oct_food["source"], oct_food["limit"], oct_food["percent"], oct_food["level"]) == (
        "default",
        "300.00",
        "83.33",
        "warning",
    )
    assert oct_food["remaining"] == "50.00"
    [nov_food] = await status(client, user, november)
    assert (nov_food["source"], nov_food["level"], nov_food["remaining"]) == (
        "month",
        "exceeded",
        "-50.00",
    )

    # Changing the default amount updates the same limit; removing the override falls back.
    await client.put(f"/api/v1/labels/{food}/limit", headers=user.headers, json={"amount": "500"})
    response = await client.delete(f"/api/v1/months/{november}/limits/{food}", headers=user.headers)
    assert response.status_code == 204
    [nov_food] = await status(client, user, november)
    assert (nov_food["source"], nov_food["limit"], nov_food["level"]) == ("default", "500.00", None)
    limits = (await client.get("/api/v1/limits", headers=user.headers)).json()
    assert [(row["month_id"], row["amount"]) for row in limits] == [(None, "500.00")]


async def test_limits_only_warn_and_closed_months_keep_theirs(client: AsyncClient) -> None:
    user = await new_user(client)
    month = (await create_month(client, user))["id"]
    food = await label_id(client, user, "Food")
    await client.put(f"/api/v1/labels/{food}/limit", headers=user.headers, json={"amount": "10"})
    await allocate(client, user, month, "Food", "3000")  # far over the limit: still saved

    await client.post(f"/api/v1/months/{month}/close", headers=user.headers)
    response = await client.put(
        f"/api/v1/months/{month}/limits/{food}", headers=user.headers, json={"amount": "50"}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "month_closed"


async def test_invalid_amounts_and_missing_limits(client: AsyncClient) -> None:
    user = await new_user(client)
    food = await label_id(client, user, "Food")
    for amount in ("0", "-5", "1.234"):
        response = await client.put(
            f"/api/v1/labels/{food}/limit", headers=user.headers, json={"amount": amount}
        )
        assert response.status_code == 422, amount
    response = await client.delete(f"/api/v1/labels/{food}/limit", headers=user.headers)
    assert response.status_code == 404


async def test_limit_writes_are_audited_events(client: AsyncClient, session: AsyncSession) -> None:
    user = await new_user(client)
    food = await label_id(client, user, "Food")
    await client.put(f"/api/v1/labels/{food}/limit", headers=user.headers, json={"amount": "300"})
    await client.delete(f"/api/v1/labels/{food}/limit", headers=user.headers)
    types = list(
        await session.scalars(
            select(OutboxEvent.type)
            .where(OutboxEvent.payload["user_id"].astext == str(user.id))
            .where(OutboxEvent.type.like("limit.%"))
            .order_by(OutboxEvent.created_at)
        )
    )
    assert types == ["limit.create", "limit.delete"]


async def test_limits_are_isolated(client: AsyncClient) -> None:
    alice, bob = await new_user(client), await new_user(client)
    alice_food = await label_id(client, alice, "Food")
    alice_month = (await create_month(client, alice))["id"]
    bob_food = await label_id(client, bob, "Food")
    await client.put(
        f"/api/v1/labels/{alice_food}/limit", headers=alice.headers, json={"amount": "300"}
    )

    for method, url in (
        ("PUT", f"/api/v1/labels/{alice_food}/limit"),
        ("DELETE", f"/api/v1/labels/{alice_food}/limit"),
        ("PUT", f"/api/v1/months/{alice_month}/limits/{bob_food}"),
        ("GET", f"/api/v1/months/{alice_month}/limits"),
    ):
        response = await client.request(method, url, headers=bob.headers, json={"amount": "1"})
        assert response.status_code == 404, (method, url)
    assert (await client.get("/api/v1/limits", headers=bob.headers)).json() == []
