"""Deleting the account (GDPR): every record and file goes, for good."""

from typing import Any

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import REFRESH_COOKIE
from app.core.jobs import DELETE_USER_FILES, SEND_EMAIL
from app.core.storage import Storage
from app.models import (
    Attachment,
    AuditLog,
    Entry,
    Export,
    Goal,
    Income,
    Label,
    Limit,
    Month,
    RefreshToken,
    User,
    UserToken,
)
from tests.integration.conftest import RecordedJobs
from tests.integration.helpers import PASSWORD, ApiUser, create_month, label_id, new_user
from tests.integration.test_attachments import upload

USER_TABLES = (
    Attachment,
    AuditLog,
    Entry,
    Export,
    Goal,
    Income,
    Label,
    Limit,
    Month,
    RefreshToken,
    UserToken,
)


async def delete_account(client: AsyncClient, user: ApiUser, password: str = PASSWORD) -> Any:
    return await client.request(
        "DELETE", "/api/v1/users/me", headers=user.headers, json={"password": password}
    )


async def rows_of(session: AsyncSession, user: ApiUser) -> dict[str, int]:
    counts = {}
    for model in USER_TABLES:
        counts[model.__tablename__] = await session.scalar(
            select(func.count()).select_from(model).where(model.user_id == user.id)
        )
    return counts


async def busy_account(client: AsyncClient, storage: Storage) -> ApiUser:
    """A user with entries, a transfer, an income, a limit, a goal, a receipt and an export."""
    user = await new_user(client)
    month = (await create_month(client, user))["id"]
    food, savings = await label_id(client, user, "Food"), await label_id(client, user, "Savings")
    h = user.headers
    await client.put(
        f"/api/v1/months/{month}/allocations/{food}", headers=h, json={"amount": "200"}
    )
    await client.put(
        f"/api/v1/months/{month}/allocations/{savings}", headers=h, json={"amount": "100"}
    )
    await client.post(
        f"/api/v1/months/{month}/transfers",
        headers=h,
        json={
            "from_label_id": str(savings),
            "to_label_id": str(food),
            "amount": "10",
            "occurred_on": "2026-10-05",
        },
    )
    await client.post(
        f"/api/v1/months/{month}/incomes",
        headers=h,
        json={"source": "Salary", "amount": "1500", "received_on": "2026-10-01"},
    )
    await client.post(
        f"/api/v1/months/{month}/additions",
        headers=h,
        json={"label_id": str(food), "amount": "20", "occurred_on": "2026-10-03"},
    )
    await client.put(f"/api/v1/labels/{food}/limit", headers=h, json={"amount": "150"})
    await client.post(
        "/api/v1/goals", headers=h, json={"label_id": str(savings), "target_amount": "500"}
    )
    await upload(client, user, month)
    await client.post("/api/v1/exports", headers=h, json={"format": "csv"})
    return user


async def test_deleting_the_account_erases_every_record(
    client: AsyncClient, session: AsyncSession, storage: Storage, jobs: RecordedJobs
) -> None:
    user = await busy_account(client, storage)
    before = await rows_of(session, user)
    assert all(
        before[t] > 0 for t in ("entries", "incomes", "limits", "goals", "attachments", "exports")
    )

    response = await delete_account(client, user)
    assert response.status_code == 204, response.text
    assert client.cookies.get(REFRESH_COOKIE) is None

    assert await session.get(User, user.id) is None
    assert set((await rows_of(session, user)).values()) == {0}
    assert jobs.of(DELETE_USER_FILES) == [{"user_id": str(user.id)}]
    goodbye = jobs.of(SEND_EMAIL)[-1]
    assert (goodbye["to"], goodbye["subject"]) == (user.email, "Your account was deleted")

    # The old token and session no longer work, and the email is free again.
    assert (await client.get("/api/v1/users/me", headers=user.headers)).status_code == 401
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401
    again = await client.post(
        "/api/v1/auth/register", json={"email": user.email, "password": PASSWORD, "name": "New"}
    )
    assert again.status_code == 201


async def test_the_password_is_required(
    client: AsyncClient, session: AsyncSession, jobs: RecordedJobs
) -> None:
    user = await new_user(client)
    response = await delete_account(client, user, "Wrong-password-1")
    assert response.status_code == 401
    assert response.json()["detail"] == "Password is incorrect"
    assert await session.get(User, user.id) is not None
    assert jobs.of(DELETE_USER_FILES) == []
    assert (
        await client.request("DELETE", "/api/v1/users/me", json={"password": PASSWORD})
    ).status_code == 401


async def test_deleting_one_account_leaves_the_others(
    client: AsyncClient, session: AsyncSession, storage: Storage
) -> None:
    alice = await busy_account(client, storage)
    bob = await busy_account(client, storage)
    bob_before = await rows_of(session, bob)
    await delete_account(client, alice)
    assert await rows_of(session, bob) == bob_before
    assert (await client.get("/api/v1/users/me", headers=bob.headers)).status_code == 200
