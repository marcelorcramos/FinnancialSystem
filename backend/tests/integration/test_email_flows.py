"""Email verification and password reset (Phase 9)."""

import re
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import REFRESH_COOKIE
from app.core.jobs import SEND_EMAIL
from app.models import UserToken
from tests.integration.conftest import RecordedJobs
from tests.integration.helpers import PASSWORD, bearer, login, new_user, register

NEW_PASSWORD = "Another-password-456"


def link_token(email: dict[str, str]) -> str:
    match = re.search(r"\?token=([\w\-%]+)", email["body"])
    assert match, email["body"]
    return match.group(1)


async def test_sign_up_emails_a_link_that_confirms_the_address(
    client: AsyncClient, jobs: RecordedJobs
) -> None:
    user = await register(client)
    assert user["email_verified_at"] is None
    [email] = jobs.of(SEND_EMAIL)
    assert email["to"] == user["email"]
    assert email["subject"] == "Confirm your email"
    assert "http://localhost:4200/verify-email?token=" in email["body"]

    response = await client.post("/api/v1/auth/verify-email", json={"token": link_token(email)})
    assert response.status_code == 204
    me = await client.get("/api/v1/users/me", headers=bearer(await login(client, user["email"])))
    assert me.json()["email_verified_at"] is not None


async def test_a_verification_link_works_once(client: AsyncClient, jobs: RecordedJobs) -> None:
    await register(client)
    token = link_token(jobs.of(SEND_EMAIL)[0])
    first = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert first.status_code == 204
    again = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert again.status_code == 422
    assert again.json()["code"] == "invalid_token"


async def test_an_unknown_or_expired_token_is_refused(
    client: AsyncClient, session: AsyncSession, jobs: RecordedJobs
) -> None:
    unknown = await client.post("/api/v1/auth/verify-email", json={"token": "made-up"})
    assert unknown.json()["code"] == "invalid_token"

    await register(client)
    await session.execute(
        update(UserToken).values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    )
    expired = await client.post(
        "/api/v1/auth/verify-email", json={"token": link_token(jobs.of(SEND_EMAIL)[0])}
    )
    assert expired.status_code == 422


async def test_resending_replaces_the_previous_link(
    client: AsyncClient, jobs: RecordedJobs
) -> None:
    user = await new_user(client)
    response = await client.post("/api/v1/users/me/verification-email", headers=user.headers)
    assert response.status_code == 202
    first, second = (link_token(e) for e in jobs.of(SEND_EMAIL))
    old = await client.post("/api/v1/auth/verify-email", json={"token": first})
    assert old.status_code == 422
    new = await client.post("/api/v1/auth/verify-email", json={"token": second})
    assert new.status_code == 204

    verified = await client.post("/api/v1/users/me/verification-email", headers=user.headers)
    assert verified.status_code == 409


async def test_resending_needs_a_signed_in_user(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/users/me/verification-email")).status_code == 401


async def test_password_reset_sets_a_new_password_and_ends_every_session(
    client: AsyncClient, jobs: RecordedJobs
) -> None:
    user = await new_user(client)
    response = await client.post("/api/v1/auth/password-reset", json={"email": user.email})
    assert response.status_code == 202
    email = jobs.of(SEND_EMAIL)[-1]
    assert email["subject"] == "Reset your password"
    assert "/reset-password?token=" in email["body"]

    confirm = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": link_token(email), "new_password": NEW_PASSWORD},
    )
    assert confirm.status_code == 204
    # The session opened before the reset is gone.
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401
    old = await client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD})
    assert old.status_code == 401
    token = await login(client, user.email, NEW_PASSWORD)
    assert client.cookies.get(REFRESH_COOKIE)
    me = await client.get("/api/v1/users/me", headers=bearer(token))
    # Opening the link proved the address.
    assert me.json()["email_verified_at"] is not None


async def test_password_reset_answers_the_same_for_unknown_emails(
    client: AsyncClient, jobs: RecordedJobs
) -> None:
    response = await client.post(
        "/api/v1/auth/password-reset", json={"email": "Nobody@Example.com"}
    )
    assert response.status_code == 202
    assert jobs.of(SEND_EMAIL) == []


async def test_a_reset_link_works_once_and_only_for_resets(
    client: AsyncClient, jobs: RecordedJobs
) -> None:
    user = await new_user(client)
    verification = link_token(jobs.of(SEND_EMAIL)[0])
    wrong_purpose = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": verification, "new_password": NEW_PASSWORD},
    )
    assert wrong_purpose.json()["code"] == "invalid_token"

    await client.post("/api/v1/auth/password-reset", json={"email": user.email})
    token = link_token(jobs.of(SEND_EMAIL)[-1])
    body = {"token": token, "new_password": NEW_PASSWORD}
    assert (await client.post("/api/v1/auth/password-reset/confirm", json=body)).status_code == 204
    again = await client.post("/api/v1/auth/password-reset/confirm", json=body)
    assert again.status_code == 422


async def test_password_reset_still_needs_a_strong_password(
    client: AsyncClient, jobs: RecordedJobs
) -> None:
    user = await new_user(client)
    await client.post("/api/v1/auth/password-reset", json={"email": user.email})
    weak = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": link_token(jobs.of(SEND_EMAIL)[-1]), "new_password": "short"},
    )
    assert weak.status_code == 422
