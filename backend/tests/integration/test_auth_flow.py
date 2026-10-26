import uuid

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import REFRESH_COOKIE
from app.domain.default_labels import DEFAULT_LABELS
from app.models import AuditLog, Label, User

PASSWORD = "password-segura-123"


async def register(client: AsyncClient, email: str | None = None) -> dict[str, str]:
    email = email or f"{uuid.uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": PASSWORD, "name": "Ana"}
    )
    assert response.status_code == 201, response.text
    body: dict[str, str] = response.json()
    return body


async def login(client: AsyncClient, email: str, password: str = PASSWORD) -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_register_login_refresh_logout(client: AsyncClient) -> None:
    user = await register(client)
    access = await login(client, user["email"])
    assert client.cookies.get(REFRESH_COOKIE)

    me = await client.get("/api/v1/users/me", headers=bearer(access))
    assert me.status_code == 200
    assert me.json()["email"] == user["email"]

    old_refresh = client.cookies.get(REFRESH_COOKIE)
    refreshed = await client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    assert client.cookies.get(REFRESH_COOKIE) != old_refresh
    new_access = refreshed.json()["access_token"]
    assert (await client.get("/api/v1/users/me", headers=bearer(new_access))).status_code == 200

    assert (await client.post("/api/v1/auth/logout")).status_code == 204
    assert client.cookies.get(REFRESH_COOKIE) is None


async def test_register_normalizes_email_and_hides_password(client: AsyncClient) -> None:
    user = await register(client, email="  Ana.Silva@Example.COM ")
    assert user["email"] == "ana.silva@example.com"
    assert "password_hash" not in user
    assert user["currency"] == "EUR"
    assert user["locale"] == "pt-PT"


async def test_register_creates_default_labels_with_audit(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await register(client)
    user_id = uuid.UUID(user["id"])
    labels = (await session.scalars(select(Label).where(Label.user_id == user_id))).all()
    assert {(lb.name, lb.kind) for lb in labels} == {(t.name, t.kind) for t in DEFAULT_LABELS}
    assert all(lb.is_default for lb in labels)
    audits = await session.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.user_id == user_id)
    )
    assert audits == len(DEFAULT_LABELS)


async def test_register_duplicate_email_conflicts(client: AsyncClient) -> None:
    user = await register(client)
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": user["email"].upper(), "password": PASSWORD, "name": "Outra"},
    )
    assert response.status_code == 409


async def test_register_rejects_short_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register", json={"email": "a@example.com", "password": "123", "name": "A"}
    )
    assert response.status_code == 422


async def test_login_wrong_password_and_unknown_email_look_the_same(client: AsyncClient) -> None:
    user = await register(client)
    wrong = await client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": "errada-123"}
    )
    unknown = await client.post(
        "/api/v1/auth/login", json={"email": "ninguem@example.com", "password": PASSWORD}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


async def test_login_rejects_soft_deleted_user(client: AsyncClient, session: AsyncSession) -> None:
    user = await register(client)
    db_user = await session.get(User, uuid.UUID(user["id"]))
    assert db_user is not None
    db_user.deleted_at = db_user.created_at
    await session.flush()
    response = await client.post(
        "/api/v1/auth/login", json={"email": user["email"], "password": PASSWORD}
    )
    assert response.status_code == 401


async def test_protected_route_requires_valid_token(client: AsyncClient) -> None:
    no_token = await client.get("/api/v1/users/me")
    garbage = await client.get("/api/v1/users/me", headers=bearer("not-a-jwt"))
    basic = await client.get("/api/v1/users/me", headers={"Authorization": "Basic abc"})
    for response in (no_token, garbage, basic):
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"


async def test_token_of_deleted_user_is_rejected(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await register(client)
    access = await login(client, user["email"])
    db_user = await session.get(User, uuid.UUID(user["id"]))
    assert db_user is not None
    db_user.deleted_at = db_user.created_at
    await session.flush()
    assert (await client.get("/api/v1/users/me", headers=bearer(access))).status_code == 401


async def test_refresh_without_cookie_is_rejected(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_reused_refresh_token_revokes_the_whole_family(client: AsyncClient) -> None:
    user = await register(client)
    await login(client, user["email"])
    stolen = client.cookies.get(REFRESH_COOKIE)
    assert stolen

    assert (await client.post("/api/v1/auth/refresh")).status_code == 200
    legit = client.cookies.get(REFRESH_COOKIE)

    # O atacante usa o token antigo: é rejeitado e a família é revogada.
    client.cookies.set(REFRESH_COOKIE, stolen, path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401

    # O token legítimo mais recente também deixa de funcionar.
    assert legit
    client.cookies.set(REFRESH_COOKIE, legit, path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    user = await register(client)
    await login(client, user["email"])
    token = client.cookies.get(REFRESH_COOKIE)
    assert token
    await client.post("/api/v1/auth/logout")
    client.cookies.set(REFRESH_COOKIE, token, path="/api/v1/auth")
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_update_profile(client: AsyncClient) -> None:
    user = await register(client)
    access = await login(client, user["email"])
    response = await client.patch(
        "/api/v1/users/me",
        headers=bearer(access),
        json={"name": "Ana Silva", "locale": "en", "timezone": "Europe/Madrid"},
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["locale"], body["timezone"]) == ("Ana Silva", "en", "Europe/Madrid")


async def test_update_profile_rejects_unsupported_values(client: AsyncClient) -> None:
    user = await register(client)
    access = await login(client, user["email"])
    for payload in ({"currency": "USD"}, {"timezone": "Mars/Base"}, {"locale": "fr"}):
        response = await client.patch("/api/v1/users/me", headers=bearer(access), json=payload)
        assert response.status_code == 422, payload


async def test_change_password_revokes_sessions(client: AsyncClient) -> None:
    user = await register(client)
    access = await login(client, user["email"])
    old_refresh = client.cookies.get(REFRESH_COOKIE)
    assert old_refresh

    wrong = await client.post(
        "/api/v1/users/me/password",
        headers=bearer(access),
        json={"current_password": "errada-123", "new_password": "nova-password-456"},
    )
    assert wrong.status_code == 401

    ok = await client.post(
        "/api/v1/users/me/password",
        headers=bearer(access),
        json={"current_password": PASSWORD, "new_password": "nova-password-456"},
    )
    assert ok.status_code == 204
    assert (await client.post("/api/v1/auth/refresh")).status_code == 401
    await login(client, user["email"], "nova-password-456")


async def test_user_only_sees_own_profile_and_cannot_reach_others(client: AsyncClient) -> None:
    alice = await register(client)
    bob = await register(client)
    alice_token = await login(client, alice["email"])

    me = await client.get("/api/v1/users/me", headers=bearer(alice_token))
    assert me.json()["id"] == alice["id"]

    # Não existem rotas para ler ou editar outro utilizador.
    for method, path in (
        ("GET", f"/api/v1/users/{bob['id']}"),
        ("PATCH", f"/api/v1/users/{bob['id']}"),
        ("GET", "/api/v1/users"),
        ("GET", f"/api/v1/users/search?email={bob['email']}"),
    ):
        response = await client.request(method, path, headers=bearer(alice_token), json={})
        assert response.status_code in (404, 405), (method, path)
