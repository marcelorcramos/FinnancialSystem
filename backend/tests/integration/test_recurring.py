"""Recurring entries: the new month starts from the previous one (Phase 7)."""

from datetime import UTC, datetime
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutboxEvent
from app.services.recurring import create_due_months
from app.workers import tasks
from app.workers.celery_app import celery_app
from tests.integration.helpers import ApiUser, create_month, label_id, new_user

FIRST_OF_NOVEMBER = datetime(2026, 11, 1, 0, 30, tzinfo=UTC)  # 00:30 in Lisbon


async def october_with_rent_and_salary(client: AsyncClient, user: ApiUser) -> None:
    month = (await create_month(client, user, 2026, 10))["id"]
    housing = await label_id(client, user, "Housing")
    response = await client.put(
        f"/api/v1/months/{month}/allocations/{housing}",
        headers=user.headers,
        json={"amount": "650"},
    )
    assert response.status_code == 200
    response = await client.post(
        f"/api/v1/months/{month}/incomes",
        headers=user.headers,
        json={"source": "Salary", "amount": "2000", "received_on": "2026-10-01"},
    )
    assert response.status_code == 201, response.text


async def opt_in(client: AsyncClient, user: ApiUser, **extra: Any) -> None:
    response = await client.patch(
        "/api/v1/users/me", headers=user.headers, json={"auto_new_month": True, **extra}
    )
    assert response.status_code == 200
    assert response.json()["auto_new_month"] is True


async def november(client: AsyncClient, user: ApiUser) -> dict[str, Any] | None:
    response = await client.get("/api/v1/months", headers=user.headers, params={"year": 2026})
    found = [m for m in response.json() if m["month"] == 11]
    return found[0] if found else None


async def test_the_new_month_copies_rent_and_salary_once(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await new_user(client)
    await october_with_rent_and_salary(client, user)
    await opt_in(client, user)

    assert await create_due_months(session, FIRST_OF_NOVEMBER) >= 1
    sheet = await november(client, user)
    assert sheet is not None
    summary = (
        await client.get(f"/api/v1/months/{sheet['id']}/summary", headers=user.headers)
    ).json()
    assert (summary["income_total"], summary["distributed"]) == ("2000.00", "650.00")

    # Running again (beat runs hourly) changes nothing.
    await create_due_months(session, FIRST_OF_NOVEMBER)
    response = await client.get("/api/v1/months", headers=user.headers, params={"year": 2026})
    assert [m["month"] for m in response.json()].count(11) == 1

    # Like any write, it leaves events for the consumers (cache invalidation...).
    events = await session.scalars(
        select(OutboxEvent.type).where(OutboxEvent.payload["month_id"].astext == sheet["id"])
    )
    assert "entry.create" in set(events)


async def test_only_opted_in_users_with_history_get_a_month(
    client: AsyncClient, session: AsyncSession
) -> None:
    not_opted = await new_user(client)
    await october_with_rent_and_salary(client, not_opted)
    no_history = await new_user(client)
    await opt_in(client, no_history)

    await create_due_months(session, FIRST_OF_NOVEMBER)
    assert await november(client, not_opted) is None
    assert await november(client, no_history) is None


async def test_each_user_starts_the_month_in_their_own_time_zone(
    client: AsyncClient, session: AsyncSession
) -> None:
    lisbon, tokyo = await new_user(client), await new_user(client)
    for user in (lisbon, tokyo):
        await october_with_rent_and_salary(client, user)
    await opt_in(client, lisbon)
    await opt_in(client, tokyo, timezone="Asia/Tokyo")

    # 23:30 UTC on 31 October: still October in Lisbon, already 1 November in Tokyo.
    await create_due_months(session, datetime(2026, 10, 31, 23, 30, tzinfo=UTC))
    assert await november(client, lisbon) is None
    assert await november(client, tokyo) is not None


def test_beat_runs_the_task_every_hour() -> None:
    schedule = celery_app.conf.beat_schedule["create-due-months"]
    assert schedule["task"] == "app.workers.tasks.create_due_months"
    assert tasks.create_due_months.name in celery_app.tasks
