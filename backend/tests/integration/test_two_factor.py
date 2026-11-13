"""Optional TOTP two-factor sign-in (Phase 10)."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pyotp
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import REFRESH_COOKIE
from app.core import security
from app.models import User
from tests.integration.helpers import PASSWORD, ApiUser, bearer, new_user


async def turn_on(client: AsyncClient, user: ApiUser) -> tuple[str, list[str]]:
    """Set up and confirm 2FA; returns the secret and the recovery codes."""
    setup = await client.post("/api/v1/users/me/2fa/setup", headers=user.headers)
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_uri"].startswith("otpauth://totp/FinnancialSystem:")
    assert setup.json()["qr_code"].startswith("data:image/svg+xml")
    enable = await client.post(
        "/api/v1/users/me/2fa/enable",
        headers=user.headers,
        json={"code": pyotp.TOTP(secret).now()},
    )
    assert enable.status_code == 200, enable.text
    return secret, enable.json()["codes"]


def later_code(secret: str, steps: int = 1) -> str:
    """A code of a following step, so it was not used yet."""
    return pyotp.TOTP(secret).at(datetime.now(UTC) + timedelta(seconds=30 * steps))


async def password_login(client: AsyncClient, user: ApiUser) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def test_turning_it_on_needs_a_code_from_the_app(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await new_user(client)
    await client.post("/api/v1/users/me/2fa/setup", headers=user.headers)
    wrong = await client.post(
        "/api/v1/users/me/2fa/enable", headers=user.headers, json={"code": "000000"}
    )
    assert wrong.status_code == 401
    status = await client.get("/api/v1/users/me/2fa", headers=user.headers)
    assert status.json() == {"enabled": False, "recovery_codes_left": 0}

    secret, codes = await turn_on(client, user)
    assert len(codes) == 10
    status = await client.get("/api/v1/users/me/2fa", headers=user.headers)
    assert status.json() == {"enabled": True, "recovery_codes_left": 10}
    me = await client.get("/api/v1/users/me", headers=user.headers)
    assert me.json()["two_factor_enabled"] is True
    # The secret is stored encrypted.
    row = await session.scalar(select(User).where(User.id == user.id))
    assert row is not None and row.totp_secret and secret not in row.totp_secret


async def test_sign_in_asks_for_a_code_and_each_code_works_once(
    client: AsyncClient,
) -> None:
    user = await new_user(client)
    secret, _ = await turn_on(client, user)
    client.cookies.clear()

    first = await password_login(client, user)
    assert first["two_factor_required"] is True
    assert first["expires_in"] == 300
    assert "access_token" not in first
    assert client.cookies.get(REFRESH_COOKIE) is None

    code = later_code(secret)
    done = await client.post(
        "/api/v1/auth/login/2fa", json={"ticket": first["ticket"], "code": code}
    )
    assert done.status_code == 200, done.text
    assert client.cookies.get(REFRESH_COOKIE)
    me = await client.get("/api/v1/users/me", headers=bearer(done.json()["access_token"]))
    assert me.status_code == 200

    again = await password_login(client, user)
    replay = await client.post(
        "/api/v1/auth/login/2fa", json={"ticket": again["ticket"], "code": code}
    )
    assert replay.status_code == 401
    assert replay.json()["detail"] == "That code is not valid"


async def test_a_recovery_code_signs_in_once(client: AsyncClient) -> None:
    user = await new_user(client)
    _, codes = await turn_on(client, user)
    ticket = (await password_login(client, user))["ticket"]
    used = await client.post(
        "/api/v1/auth/login/2fa", json={"ticket": ticket, "code": codes[0].upper()}
    )
    assert used.status_code == 200
    ticket = (await password_login(client, user))["ticket"]
    reused = await client.post("/api/v1/auth/login/2fa", json={"ticket": ticket, "code": codes[0]})
    assert reused.status_code == 401
    status = await client.get("/api/v1/users/me/2fa", headers=user.headers)
    assert status.json()["recovery_codes_left"] == 9


async def test_tickets_expire_and_cannot_be_forged(client: AsyncClient) -> None:
    user = await new_user(client)
    secret, _ = await turn_on(client, user)
    old = security.create_two_factor_ticket(user.id, datetime.now(UTC) - timedelta(minutes=6))
    expired = await client.post(
        "/api/v1/auth/login/2fa", json={"ticket": old, "code": later_code(secret)}
    )
    assert expired.status_code == 401
    assert expired.json()["detail"] == "The sign-in expired. Start again."
    # An access token is not a ticket.
    forged = await client.post(
        "/api/v1/auth/login/2fa", json={"ticket": user.token, "code": later_code(secret)}
    )
    assert forged.status_code == 401


async def test_turning_it_off_or_new_codes_need_a_code(client: AsyncClient) -> None:
    user = await new_user(client)
    secret, codes = await turn_on(client, user)

    renewed = await client.post(
        "/api/v1/users/me/2fa/recovery-codes", headers=user.headers, json={"code": codes[1]}
    )
    assert renewed.status_code == 200
    new_codes = renewed.json()["codes"]
    assert set(new_codes).isdisjoint(codes)

    refused = await client.post(
        "/api/v1/users/me/2fa/disable", headers=user.headers, json={"code": "123456"}
    )
    assert refused.status_code == 401
    off = await client.post(
        "/api/v1/users/me/2fa/disable", headers=user.headers, json={"code": later_code(secret)}
    )
    assert off.status_code == 204
    assert "access_token" in await password_login(client, user)
    again = await client.post(
        "/api/v1/users/me/2fa/disable", headers=user.headers, json={"code": new_codes[0]}
    )
    assert again.status_code == 409


async def test_setup_twice_is_refused_once_it_is_on(client: AsyncClient) -> None:
    user = await new_user(client)
    await turn_on(client, user)
    response = await client.post("/api/v1/users/me/2fa/setup", headers=user.headers)
    assert response.status_code == 409
    enable = await client.post(
        "/api/v1/users/me/2fa/enable", headers=user.headers, json={"code": "123456"}
    )
    assert enable.status_code == 409


async def test_enable_needs_a_setup_first(client: AsyncClient) -> None:
    user = await new_user(client)
    response = await client.post(
        "/api/v1/users/me/2fa/enable", headers=user.headers, json={"code": "123456"}
    )
    assert response.status_code == 409


async def test_the_docs_form_refuses_two_factor_accounts(client: AsyncClient) -> None:
    user = await new_user(client)
    await turn_on(client, user)
    response = await client.post(
        "/api/v1/auth/token", data={"username": user.email, "password": PASSWORD}
    )
    assert response.status_code == 401


async def test_two_factor_routes_need_a_signed_in_user(client: AsyncClient) -> None:
    for method, path in (
        ("GET", "/api/v1/users/me/2fa"),
        ("POST", "/api/v1/users/me/2fa/setup"),
        ("POST", "/api/v1/users/me/2fa/enable"),
        ("POST", "/api/v1/users/me/2fa/disable"),
        ("POST", "/api/v1/users/me/2fa/recovery-codes"),
    ):
        response = await client.request(method, path, json={"code": "123456"})
        assert response.status_code == 401, path
