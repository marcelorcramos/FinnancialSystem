import uuid
from dataclasses import dataclass
from typing import Any

from httpx import AsyncClient

PASSWORD = "Secure-password-123"


@dataclass
class ApiUser:
    id: uuid.UUID
    email: str
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return bearer(self.token)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register(client: AsyncClient, email: str | None = None) -> dict[str, str]:
    email = email or f"{uuid.uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": PASSWORD, "name": "Alice"}
    )
    assert response.status_code == 201, response.text
    body: dict[str, str] = response.json()
    return body


async def login(client: AsyncClient, email: str, password: str = PASSWORD) -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token


async def new_user(client: AsyncClient) -> ApiUser:
    data = await register(client)
    return ApiUser(uuid.UUID(data["id"]), data["email"], await login(client, data["email"]))


async def create_month(
    client: AsyncClient, user: ApiUser, year: int = 2026, month: int = 10, **extra: Any
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/months", headers=user.headers, json={"year": year, "month": month, **extra}
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def label_id(client: AsyncClient, user: ApiUser, name: str) -> uuid.UUID:
    labels = (await client.get("/api/v1/labels", headers=user.headers)).json()
    return uuid.UUID(next(lb["id"] for lb in labels if lb["name"] == name))
