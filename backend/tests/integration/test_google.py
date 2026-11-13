"""Sign in with Google (Phase 10), against a fake Google OpenID provider."""

import json
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pyotp
import pytest
from httpx import AsyncClient
from joserfc import jwt
from joserfc.jwk import RSAKey
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import REFRESH_COOKIE
from app.core.config import settings
from app.core.google import GoogleOAuth, get_google
from app.main import app
from app.models import Label, User
from tests.integration.helpers import PASSWORD, bearer, new_user, register

ISSUER = "https://accounts.google.com"
CLIENT_ID = "test-client.apps.googleusercontent.com"
DISCOVERY = "https://fake-google.test/.well-known/openid-configuration"


@dataclass
class FakeGoogle:
    """Discovery, token and keys endpoints; the ID token says what `claims` holds."""

    key: RSAKey = field(default_factory=lambda: RSAKey.generate_key(2048, parameters={"kid": "k1"}))
    claims: dict[str, Any] = field(default_factory=dict)
    nonce: str = ""
    token_requests: list[dict[str, list[str]]] = field(default_factory=list)

    def handle(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == DISCOVERY:
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": "https://fake-google.test/auth",
                    "token_endpoint": "https://fake-google.test/token",
                    "jwks_uri": "https://fake-google.test/keys",
                },
            )
        if url == "https://fake-google.test/keys":
            return httpx.Response(200, json={"keys": [self.key.as_dict(private=False)]})
        if url == "https://fake-google.test/token":
            self.token_requests.append(parse_qs(request.content.decode()))
            now = int(time.time())
            claims = {
                "iss": ISSUER,
                "aud": CLIENT_ID,
                "sub": "google-123",
                "email": "ana.google@example.com",
                "email_verified": True,
                "name": "Ana Google",
                "picture": "https://example.com/ana.png",
                "nonce": self.nonce,
                "iat": now,
                "exp": now + 600,
                **self.claims,
            }
            token = jwt.encode({"alg": "RS256", "kid": "k1"}, claims, self.key)
            return httpx.Response(
                200,
                json={
                    "access_token": "at",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "id_token": token,
                },
            )
        return httpx.Response(404)


@pytest.fixture
def google() -> Iterator[FakeGoogle]:
    fake = FakeGoogle()
    client = GoogleOAuth(CLIENT_ID, "secret", DISCOVERY, transport=httpx.MockTransport(fake.handle))
    app.dependency_overrides[get_google] = lambda: client
    yield fake
    app.dependency_overrides.pop(get_google, None)


async def go_to_google(client: AsyncClient, google: FakeGoogle) -> dict[str, list[str]]:
    response = await client.get("/api/v1/auth/google/login")
    assert response.status_code == 303, response.text
    location = urlparse(response.headers["location"])
    assert location.netloc == "fake-google.test"
    query = parse_qs(location.query)
    google.nonce = query["nonce"][0]
    return query


async def come_back(
    client: AsyncClient, query: dict[str, list[str]], **extra: str
) -> httpx.Response:
    params = {"code": "auth-code", "state": query["state"][0], **extra}
    return await client.get("/api/v1/auth/google/callback", params=params)


def assert_failed(response: httpx.Response) -> None:
    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:4200/auth/login?error=google"


async def test_providers_say_whether_google_is_set_up(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/providers")).json() == {"google": False}
    assert (await client.get("/api/v1/auth/google/login")).status_code == 404
    assert (await client.get("/api/v1/auth/google/callback")).status_code == 404


async def test_a_new_google_user_gets_an_account_and_a_session(
    client: AsyncClient, session: AsyncSession, google: FakeGoogle
) -> None:
    assert (await client.get("/api/v1/auth/providers")).json() == {"google": True}
    query = await go_to_google(client, google)
    assert query["client_id"] == [CLIENT_ID]
    assert query["redirect_uri"] == [settings.google_redirect_uri]
    assert query["scope"] == ["openid email profile"]
    assert query["code_challenge_method"] == ["S256"]

    response = await come_back(client, query)
    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:4200/auth/google"
    assert client.cookies.get(REFRESH_COOKIE)
    # PKCE: the token request proves it started the flow.
    assert google.token_requests[0]["code_verifier"]

    refreshed = await client.post("/api/v1/auth/refresh")
    me = (
        await client.get("/api/v1/users/me", headers=bearer(refreshed.json()["access_token"]))
    ).json()
    assert (me["email"], me["name"]) == ("ana.google@example.com", "Ana Google")
    assert me["google_linked"] is True
    assert me["has_password"] is False
    assert me["email_verified_at"] is not None
    assert me["avatar_url"] == "https://example.com/ana.png"
    labels = await session.scalar(
        select(func.count()).select_from(Label).where(Label.user_id == uuid.UUID(me["id"]))
    )
    assert labels == 11

    # The same Google account signs into the same user next time.
    client.cookies.clear()
    await come_back(client, await go_to_google(client, google))
    users = await session.scalar(
        select(func.count()).select_from(User).where(User.email == "ana.google@example.com")
    )
    assert users == 1


async def test_an_existing_account_is_linked_by_its_email(
    client: AsyncClient, session: AsyncSession, google: FakeGoogle
) -> None:
    existing = await register(client, "ana.google@example.com")
    response = await come_back(client, await go_to_google(client, google))
    assert response.headers["location"] == "http://localhost:4200/auth/google"
    user = await session.get(User, uuid.UUID(existing["id"]))
    assert user is not None
    await session.refresh(user)
    assert user.google_id == "google-123"
    assert user.email_verified_at is not None
    # The password still works too.
    login = await client.post(
        "/api/v1/auth/login", json={"email": "ana.google@example.com", "password": PASSWORD}
    )
    assert login.status_code == 200


async def test_an_email_google_did_not_verify_is_refused(
    client: AsyncClient, session: AsyncSession, google: FakeGoogle
) -> None:
    google.claims = {"email_verified": False}
    assert_failed(await come_back(client, await go_to_google(client, google)))
    assert await session.scalar(select(User).where(User.email == "ana.google@example.com")) is None
    assert client.cookies.get(REFRESH_COOKIE) is None


@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "someone-else"},
        {"iss": "https://evil.example"},
        {"nonce": "replayed"},
        {"exp": int(time.time()) - 60},
    ],
)
async def test_untrustworthy_id_tokens_are_refused(
    client: AsyncClient, google: FakeGoogle, claims: dict[str, Any]
) -> None:
    google.claims = claims
    assert_failed(await come_back(client, await go_to_google(client, google)))


async def test_a_token_signed_by_another_key_is_refused(
    client: AsyncClient, google: FakeGoogle
) -> None:
    query = await go_to_google(client, google)
    google.key = RSAKey.generate_key(2048, parameters={"kid": "k1"})
    published = google.key
    signer = RSAKey.generate_key(2048, parameters={"kid": "k1"})
    original = google.handle

    def handle(request: httpx.Request) -> httpx.Response:
        google.key = signer if request.url.path == "/token" else published
        return original(request)

    google.handle = handle  # type: ignore[method-assign]
    app.dependency_overrides[get_google] = lambda: GoogleOAuth(
        CLIENT_ID, "secret", DISCOVERY, transport=httpx.MockTransport(handle)
    )
    assert_failed(await come_back(client, query))


async def test_a_wrong_state_or_a_google_error_goes_back_to_sign_in(
    client: AsyncClient, google: FakeGoogle
) -> None:
    query = await go_to_google(client, google)
    assert_failed(await come_back(client, {"state": ["forged"]}))
    assert_failed(await come_back(client, query, error="access_denied"))
    client.cookies.clear()  # no state cookie at all
    assert_failed(await come_back(client, query))


async def test_two_factor_still_applies_after_google(
    client: AsyncClient, session: AsyncSession, google: FakeGoogle
) -> None:
    user = await new_user(client)
    await session.execute(
        User.__table__.update().where(User.id == user.id).values(email="ana.google@example.com")
    )
    setup = await client.post("/api/v1/users/me/2fa/setup", headers=user.headers)
    secret = setup.json()["secret"]
    await client.post(
        "/api/v1/users/me/2fa/enable", headers=user.headers, json={"code": pyotp.TOTP(secret).now()}
    )
    client.cookies.clear()

    response = await come_back(client, await go_to_google(client, google))
    location = response.headers["location"]
    assert location.startswith("http://localhost:4200/auth/two-factor#ticket=")
    assert client.cookies.get(REFRESH_COOKIE) is None


async def test_google_only_accounts_have_no_password_and_delete_by_email(
    client: AsyncClient, google: FakeGoogle
) -> None:
    await come_back(client, await go_to_google(client, google))
    token = (await client.post("/api/v1/auth/refresh")).json()["access_token"]
    login = await client.post(
        "/api/v1/auth/login", json={"email": "ana.google@example.com", "password": "anything"}
    )
    assert login.status_code == 401

    wrong = await client.request(
        "DELETE", "/api/v1/users/me", headers=bearer(token), json={"confirm_email": "x@example.com"}
    )
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "Type your email to confirm"
    deleted = await client.request(
        "DELETE",
        "/api/v1/users/me",
        headers=bearer(token),
        json={"confirm_email": " Ana.Google@example.com "},
    )
    assert deleted.status_code == 204


def test_the_state_cookie_cannot_be_forged() -> None:
    from app.core import security

    value = security.encode_google_state("s", "n", "v")
    assert security.decode_google_state(value) == {"state": "s", "nonce": "n", "verifier": "v"}
    assert security.decode_google_state(value + "x") is None
    assert security.decode_google_state(json.dumps({"state": "s"})) is None
