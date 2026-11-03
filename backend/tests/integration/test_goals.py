"""Goals and the emergency fund (Phase 8)."""

import uuid
from datetime import date
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_today
from app.events.consumers import Event, goals_handler, handle_once
from app.main import app
from app.services import goals as goals_service
from tests.integration.helpers import ApiUser, create_month, label_id, new_user

TODAY = date(2026, 11, 3)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(goals_service, "today_for", lambda _user: TODAY)
    app.dependency_overrides[get_today] = lambda: TODAY


@pytest.fixture
def sessions(session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=session.bind, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )


async def allocate(
    client: AsyncClient, user: ApiUser, year: int, month: int, label: str, amount: str
) -> None:
    sheet = await create_month(client, user, year, month)
    response = await client.put(
        f"/api/v1/months/{sheet['id']}/allocations/{await label_id(client, user, label)}",
        headers=user.headers,
        json={"amount": amount},
    )
    assert response.status_code == 200, response.text


async def create_goal(client: AsyncClient, user: ApiUser, **body: Any) -> dict[str, Any]:
    response = await client.post("/api/v1/goals", headers=user.headers, json=body)
    assert response.status_code == 201, response.text
    goal: dict[str, Any] = response.json()
    return goal


async def goals(client: AsyncClient, user: ApiUser) -> dict[str, list[dict[str, Any]]]:
    response = await client.get("/api/v1/goals", headers=user.headers)
    assert response.status_code == 200
    body: dict[str, list[dict[str, Any]]] = response.json()
    return body


async def test_progress_comes_from_the_label_balance(client: AsyncClient) -> None:
    user = await new_user(client)
    await allocate(client, user, 2026, 9, "Savings", "300")
    await allocate(client, user, 2026, 10, "Savings", "200")
    savings = await label_id(client, user, "Savings")

    goal = await create_goal(
        client, user, label_id=str(savings), target_amount="2000", deadline="2027-01-31"
    )
    assert (goal["progress"], goal["remaining"], goal["percent"]) == ("500.00", "1500.00", "25.00")
    # November, December and January to go: 1500 / 3.
    assert (goal["months_left"], goal["per_month"], goal["days_left"]) == (3, "500.00", 89)
    assert (goal["reached"], goal["overdue"], goal["label_name"]) == (False, False, "Savings")

    updated = await client.patch(
        f"/api/v1/goals/{goal['id']}", headers=user.headers, json={"manual_progress": "1900"}
    )
    assert updated.json()["progress"] == "1900.00"
    cleared = await client.patch(
        f"/api/v1/goals/{goal['id']}", headers=user.headers, json={"manual_progress": None}
    )
    assert cleared.json()["progress"] == "500.00"


async def test_emergency_fund_is_months_of_average_expenses(client: AsyncClient) -> None:
    user = await new_user(client)
    # Complete months May..October: only September and October have a sheet.
    await allocate(client, user, 2026, 9, "Housing", "1000")
    await allocate(client, user, 2026, 10, "Housing", "1100")
    await allocate(client, user, 2026, 11, "Housing", "5000")  # current month: not averaged
    await allocate(client, user, 2026, 4, "Housing", "9000")  # outside the 6 months
    fund = await label_id(client, user, "Emergency Fund")

    goal = await create_goal(
        client, user, label_id=str(fund), type="emergency_fund", months_of_expenses=6
    )
    assert (goal["average_expenses"], goal["target_amount"]) == ("1050.00", "6300.00")
    assert (goal["deadline"], goal["per_month"], goal["months_left"]) == (None, None, None)


async def test_emergency_fund_without_history_has_no_target_yet(client: AsyncClient) -> None:
    user = await new_user(client)
    fund = await label_id(client, user, "Emergency Fund")
    goal = await create_goal(
        client, user, label_id=str(fund), type="emergency_fund", months_of_expenses=3
    )
    assert (goal["average_expenses"], goal["target_amount"], goal["reached"]) == (None, None, False)


async def test_reached_goals_move_to_the_history(
    client: AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    user = await new_user(client)
    savings = await label_id(client, user, "Savings")
    goal = await create_goal(client, user, label_id=str(savings), target_amount="400")
    await allocate(client, user, 2026, 10, "Savings", "450")

    event = Event(uuid.uuid4(), "entry.create", {"user_id": str(user.id)})
    async with sessions() as session:
        await handle_once(session, "goals", event, goals_handler)

    listed = await goals(client, user)
    assert listed["active"] == []
    [done] = listed["completed"]
    assert (done["id"], done["reached"], done["completed_at"] is not None) == (
        goal["id"],
        True,
        True,
    )
    # The label is free for a new goal.
    await create_goal(client, user, label_id=str(savings), target_amount="1000")


async def test_goal_rules(client: AsyncClient) -> None:
    user = await new_user(client)
    savings = str(await label_id(client, user, "Savings"))
    bad = [
        {"label_id": savings},  # no target
        {"label_id": savings, "type": "emergency_fund"},  # no months
        {"label_id": savings, "target_amount": "100", "deadline": "2026-10-31"},  # past
        {"label_id": savings, "type": "emergency_fund", "months_of_expenses": 30},
    ]
    for body in bad:
        response = await client.post("/api/v1/goals", headers=user.headers, json=body)
        assert response.status_code == 422, body
    goal = await create_goal(client, user, label_id=savings, target_amount="100")
    second = await client.post(
        "/api/v1/goals", headers=user.headers, json={"label_id": savings, "target_amount": "5"}
    )
    assert second.status_code == 409
    response = await client.patch(
        f"/api/v1/goals/{goal['id']}", headers=user.headers, json={"months_of_expenses": 3}
    )
    assert response.status_code == 422


async def test_delete_and_restore_a_goal(client: AsyncClient) -> None:
    user = await new_user(client)
    savings = str(await label_id(client, user, "Savings"))
    goal = await create_goal(client, user, label_id=savings, target_amount="100")
    assert (
        await client.delete(f"/api/v1/goals/{goal['id']}", headers=user.headers)
    ).status_code == 204
    assert (await goals(client, user))["active"] == []
    restored = await client.post(f"/api/v1/goals/{goal['id']}/restore", headers=user.headers)
    assert restored.status_code == 200
    assert [g["id"] for g in (await goals(client, user))["active"]] == [goal["id"]]


async def test_goals_are_isolated(client: AsyncClient) -> None:
    alice, bob = await new_user(client), await new_user(client)
    goal = await create_goal(
        client, alice, label_id=str(await label_id(client, alice, "Savings")), target_amount="100"
    )
    assert await goals(client, bob) == {"active": [], "completed": []}
    for method, url in (
        ("PATCH", f"/api/v1/goals/{goal['id']}"),
        ("DELETE", f"/api/v1/goals/{goal['id']}"),
        ("POST", f"/api/v1/goals/{goal['id']}/restore"),
    ):
        response = await client.request(method, url, headers=bob.headers, json={})
        assert response.status_code == 404, (method, url)
    alice_label = await label_id(client, alice, "Savings")
    response = await client.post(
        "/api/v1/goals",
        headers=bob.headers,
        json={"label_id": str(alice_label), "target_amount": "1"},
    )
    assert response.status_code == 404
