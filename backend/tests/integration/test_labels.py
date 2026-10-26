import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import MovementType
from app.models import AuditLog, Entry, Month
from tests.integration.helpers import ApiUser, new_user

NEW_LABEL = {"name": "Gym", "kind": "expense", "color": "#AB47BC", "icon": "fitness_center"}


async def create_label(client: AsyncClient, user: ApiUser, **overrides: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/labels", headers=user.headers, json={**NEW_LABEL, **overrides}
    )
    assert response.status_code == 201, response.text
    body: dict[str, str] = response.json()
    return body


async def labels_by_name(client: AsyncClient, user: ApiUser, **params: str) -> dict[str, dict]:  # type: ignore[type-arg]
    response = await client.get("/api/v1/labels", headers=user.headers, params=params)
    assert response.status_code == 200
    return {lb["name"]: lb for lb in response.json()}


async def test_list_starts_with_default_labels(client: AsyncClient) -> None:
    user = await new_user(client)
    labels = await labels_by_name(client, user)
    assert len(labels) == 7
    assert labels["Food"]["kind"] == "expense"
    assert labels["Investments"]["kind"] == "investment"


async def test_create_update_and_change_kind(client: AsyncClient, session: AsyncSession) -> None:
    user = await new_user(client)
    label = await create_label(client, user)
    assert label["is_default"] is False

    response = await client.patch(
        f"/api/v1/labels/{label['id']}",
        headers=user.headers,
        json={"name": "Sports", "kind": "investment", "color": "#000000"},
    )
    assert response.status_code == 200
    assert (response.json()["name"], response.json()["kind"]) == ("Sports", "investment")

    actions = (
        await session.scalars(
            select(AuditLog.action).where(AuditLog.entity_id == uuid.UUID(label["id"]))
        )
    ).all()
    assert actions == ["create", "update"]


async def test_label_validation(client: AsyncClient) -> None:
    user = await new_user(client)
    for bad in ({"color": "red"}, {"kind": "gift"}, {"name": "  "}, {"icon": ""}):
        response = await client.post(
            "/api/v1/labels", headers=user.headers, json={**NEW_LABEL, **bad}
        )
        assert response.status_code == 422, bad


async def test_label_names_are_unique_per_user_case_insensitive(client: AsyncClient) -> None:
    alice, bob = await new_user(client), await new_user(client)
    await create_label(client, alice)
    duplicate = await client.post(
        "/api/v1/labels", headers=alice.headers, json={**NEW_LABEL, "name": "GYM"}
    )
    assert duplicate.status_code == 409
    await create_label(client, bob)  # another user may use the same name


async def test_archive_hides_label_until_unarchived(client: AsyncClient) -> None:
    user = await new_user(client)
    label = await create_label(client, user)
    await client.post(f"/api/v1/labels/{label['id']}/archive", headers=user.headers)
    assert "Gym" not in await labels_by_name(client, user)
    assert "Gym" in await labels_by_name(client, user, include_archived="true")
    await client.post(f"/api/v1/labels/{label['id']}/unarchive", headers=user.headers)
    assert "Gym" in await labels_by_name(client, user)


async def test_delete_without_entries_and_restore(client: AsyncClient) -> None:
    user = await new_user(client)
    label = await create_label(client, user)
    response = await client.delete(f"/api/v1/labels/{label['id']}", headers=user.headers)
    assert response.status_code == 204
    assert "Gym" not in await labels_by_name(client, user, include_archived="true")

    restored = await client.post(f"/api/v1/labels/{label['id']}/restore", headers=user.headers)
    assert restored.status_code == 200
    assert "Gym" in await labels_by_name(client, user)


async def _month(session: AsyncSession, user: ApiUser, *, closed: bool = False) -> Month:
    month = Month(user_id=user.id, year=2026, month=10)
    if closed:
        month.closed_at = datetime.now(UTC)
    session.add(month)
    await session.flush()
    return month


def _entry(user: ApiUser, month: Month, label_id: str, **kw: object) -> Entry:
    values: dict[str, object] = {
        "user_id": user.id,
        "month_id": month.id,
        "label_id": uuid.UUID(label_id),
        "amount": Decimal("100.00"),
        "movement_type": MovementType.ALLOCATION,
        "occurred_on": date(2026, 10, 1),
    }
    values.update(kw)
    return Entry(**values)


async def test_label_with_entries_needs_reassignment(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await new_user(client)
    label = await create_label(client, user)
    month = await _month(session, user)
    session.add(_entry(user, month, label["id"]))
    await session.flush()

    response = await client.delete(f"/api/v1/labels/{label['id']}", headers=user.headers)
    assert response.status_code == 409


async def test_reassign_moves_entries_and_merges_allocations(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await new_user(client)
    labels = await labels_by_name(client, user)
    source = await create_label(client, user)
    target_id = labels["Food"]["id"]
    month = await _month(session, user)
    session.add_all(
        [
            _entry(user, month, source["id"], amount=Decimal("30.00")),
            _entry(user, month, target_id, amount=Decimal("200.00")),
        ]
    )
    await session.flush()

    response = await client.delete(
        f"/api/v1/labels/{source['id']}",
        headers=user.headers,
        params={"reassign_to": target_id},
    )
    assert response.status_code == 204

    active = (
        await session.scalars(
            select(Entry).where(Entry.month_id == month.id, Entry.deleted_at.is_(None))
        )
    ).all()
    assert [(str(e.label_id), e.amount) for e in active] == [(target_id, Decimal("230.00"))]


async def test_reassign_drops_transfers_between_source_and_target(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await new_user(client)
    labels = await labels_by_name(client, user)
    source = await create_label(client, user)
    target_id = labels["Savings"]["id"]
    month = await _month(session, user)
    transfer_id = uuid.uuid4()
    session.add_all(
        [
            _entry(user, month, source["id"], movement_type=MovementType.TRANSFER_OUT,
                   transfer_id=transfer_id, amount=Decimal("10.00")),
            _entry(user, month, target_id, movement_type=MovementType.TRANSFER_IN,
                   transfer_id=transfer_id, amount=Decimal("10.00")),
        ]
    )  # fmt: skip
    await session.flush()

    response = await client.delete(
        f"/api/v1/labels/{source['id']}", headers=user.headers, params={"reassign_to": target_id}
    )
    assert response.status_code == 204
    legs = (await session.scalars(select(Entry).where(Entry.transfer_id == transfer_id))).all()
    assert all(leg.deleted_at is not None for leg in legs)


async def test_reassign_is_blocked_by_closed_months(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await new_user(client)
    labels = await labels_by_name(client, user)
    source = await create_label(client, user)
    month = await _month(session, user, closed=True)
    session.add(_entry(user, month, source["id"]))
    await session.flush()
    response = await client.delete(
        f"/api/v1/labels/{source['id']}",
        headers=user.headers,
        params={"reassign_to": labels["Food"]["id"]},
    )
    assert response.status_code == 409


async def test_users_cannot_touch_each_others_labels(
    client: AsyncClient, session: AsyncSession
) -> None:
    alice, bob = await new_user(client), await new_user(client)
    label = await create_label(client, alice)
    url = f"/api/v1/labels/{label['id']}"
    attempts = [
        await client.get(url, headers=bob.headers),
        await client.patch(url, headers=bob.headers, json={"name": "Stolen"}),
        await client.post(f"{url}/archive", headers=bob.headers),
        await client.post(f"{url}/restore", headers=bob.headers),
        await client.delete(url, headers=bob.headers),
    ]
    assert [r.status_code for r in attempts] == [404] * 5
    assert "Gym" not in await labels_by_name(client, bob)

    # Nor can they reassign their entries to someone else's label.
    own = await create_label(client, bob, name="Bob")
    session.add(_entry(bob, await _month(session, bob), own["id"]))
    await session.flush()
    response = await client.delete(
        f"/api/v1/labels/{own['id']}", headers=bob.headers, params={"reassign_to": label["id"]}
    )
    assert response.status_code == 404
