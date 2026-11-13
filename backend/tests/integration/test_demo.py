"""Demo accounts behind "Try it" (Phase 10)."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import REFRESH_COOKIE
from app.core.rate_limit import Limit, RateLimiter, get_rate_limiter
from app.core.storage import Storage
from app.main import app
from app.models import Month, User
from app.services import demo
from tests.integration.helpers import bearer, new_user


async def try_it(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/api/v1/auth/demo")
    assert response.status_code == 201, response.text
    headers = bearer(response.json()["access_token"])
    return headers


async def get(client: AsyncClient, headers: dict[str, str], path: str) -> Any:
    response = await client.get(f"/api/v1{path}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_try_it_signs_into_a_fresh_account_full_of_data(client: AsyncClient) -> None:
    headers = await try_it(client)
    assert client.cookies.get(REFRESH_COOKIE)
    me = await get(client, headers, "/users/me")
    assert me["email"].endswith("@demo.example.com")
    assert me["has_password"] is False
    expires = datetime.fromisoformat(me["demo_expires_at"])
    assert timedelta(hours=23) < expires - datetime.now(UTC) <= timedelta(hours=24)

    months = await get(client, headers, "/months")
    assert len(months) == 6
    assert sum(1 for m in months if m["closed_at"]) == 5
    current = next(m for m in months if not m["closed_at"])
    summary = await get(client, headers, f"/months/{current['id']}/summary")
    assert summary["income_total"] in ("2400.00", "2520.00")  # salary, maybe the bike money
    assert len([lb for lb in summary["labels"] if lb["total"] != "0.00"]) == 11

    report = await get(client, headers, "/reports/entries?period=all&limit=200")
    origins = {e["origin"] for e in report["entries"]}
    assert {"initial_distribution", "transfer_in", "transfer_out", "external_income"} <= origins

    goal_list = await get(client, headers, "/goals")
    assert {g["type"] for g in goal_list["active"]} == {"normal", "emergency_fund"}
    assert len(await get(client, headers, "/limits")) == 2


async def test_every_click_gets_its_own_account(client: AsyncClient) -> None:
    first = await get(client, await try_it(client), "/users/me")
    second = await get(client, await try_it(client), "/users/me")
    assert first["id"] != second["id"]


async def test_demo_accounts_cannot_add_a_password_or_two_factor(client: AsyncClient) -> None:
    headers = await try_it(client)
    password = await client.post(
        "/api/v1/users/me/password",
        headers=headers,
        json={"current_password": "x", "new_password": "Another-password-1"},
    )
    assert password.status_code == 409
    setup = await client.post("/api/v1/users/me/2fa/setup", headers=headers)
    assert setup.status_code == 409


async def test_a_demo_account_can_delete_itself_by_typing_its_email(client: AsyncClient) -> None:
    headers = await try_it(client)
    me = await get(client, headers, "/users/me")
    response = await client.request(
        "DELETE", "/api/v1/users/me", headers=headers, json={"confirm_email": me["email"]}
    )
    assert response.status_code == 204


async def test_expired_demos_are_removed_and_real_accounts_stay(
    client: AsyncClient, session: AsyncSession, storage: Storage
) -> None:
    real = await new_user(client)
    old = await demo.create(session, datetime.now(UTC) - timedelta(hours=25))
    fresh = await demo.create(session)
    await storage.put(f"users/{old.id}/attachments/x", b"%PDF-1.7", "application/pdf")

    assert await demo.remove_expired(session, storage, datetime.now(UTC)) == 1
    assert await session.get(User, old.id) is None
    assert await session.scalar(select(Month).where(Month.user_id == old.id)) is None
    assert await session.get(User, fresh.id) is not None
    assert await session.get(User, real.id) is not None
    assert await storage.delete_prefix(f"users/{old.id}/") == 0
    assert await demo.remove_expired(session, storage, datetime.now(UTC)) == 0


@pytest.fixture
async def limited(redis_url: str) -> AsyncIterator[None]:
    client = Redis.from_url(redis_url)
    await client.flushdb()
    app.dependency_overrides[get_rate_limiter] = lambda: RateLimiter(client)
    yield
    app.dependency_overrides.pop(get_rate_limiter, None)
    await client.aclose()


async def test_try_it_is_rate_limited_per_address(
    client: AsyncClient, limited: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.v1.auth.DEMO_PER_IP", Limit("demo-ip", 1, 3600))
    assert (await client.post("/api/v1/auth/demo")).status_code == 201
    assert (await client.post("/api/v1/auth/demo")).status_code == 429


def test_beat_removes_expired_demos_every_hour() -> None:
    from app.workers import tasks
    from app.workers.celery_app import celery_app

    schedule = celery_app.conf.beat_schedule["remove-expired-demos"]
    assert schedule["task"] == tasks.remove_expired_demos.name
