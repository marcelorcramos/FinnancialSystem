import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import MovementType
from app.models import AuditLog, Entry
from tests.integration.helpers import ApiUser, create_month, label_id, new_user


def allocation_url(month_id: str, label: uuid.UUID) -> str:
    return f"/api/v1/months/{month_id}/allocations/{label}"


async def active_allocations(session: AsyncSession, month_id: str) -> list[Entry]:
    stmt = select(Entry).where(
        Entry.month_id == uuid.UUID(month_id),
        Entry.movement_type == MovementType.ALLOCATION,
        Entry.deleted_at.is_(None),
    )
    return list((await session.scalars(stmt)).all())


async def setup(client: AsyncClient) -> tuple[ApiUser, dict[str, str], uuid.UUID]:
    user = await new_user(client)
    month = await create_month(client, user)
    return user, month, await label_id(client, user, "Food")


async def test_set_creates_allocation_on_first_day(client: AsyncClient) -> None:
    user, month, food = await setup(client)
    response = await client.put(
        allocation_url(month["id"], food),
        headers=user.headers,
        json={"amount": "200.00", "note": "Weekly shopping"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["amount"], body["movement_type"]) == ("200.00", "allocation")
    assert (body["occurred_on"], body["note"]) == ("2026-10-01", "Weekly shopping")


async def test_set_again_updates_the_same_allocation(
    client: AsyncClient, session: AsyncSession
) -> None:
    user, month, food = await setup(client)
    url = allocation_url(month["id"], food)
    first = await client.put(url, headers=user.headers, json={"amount": "200.00"})
    second = await client.put(url, headers=user.headers, json={"amount": "220.00"})
    assert first.json()["id"] == second.json()["id"]

    allocations = await active_allocations(session, month["id"])
    assert [str(a.amount) for a in allocations] == ["220.00"]
    actions = (
        await session.scalars(
            select(AuditLog.action).where(AuditLog.entity_id == uuid.UUID(first.json()["id"]))
        )
    ).all()
    assert actions == ["create", "update"]


async def test_amount_zero_removes_allocation(client: AsyncClient, session: AsyncSession) -> None:
    user, month, food = await setup(client)
    url = allocation_url(month["id"], food)
    await client.put(url, headers=user.headers, json={"amount": "200.00"})

    removed = await client.put(url, headers=user.headers, json={"amount": "0"})
    assert removed.status_code == 204
    assert await active_allocations(session, month["id"]) == []

    # Setting 0 when there is nothing is a no-op, and a new value creates a fresh allocation.
    assert (await client.put(url, headers=user.headers, json={"amount": "0"})).status_code == 204
    recreated = await client.put(url, headers=user.headers, json={"amount": "50.00"})
    assert recreated.status_code == 200


async def test_delete_removes_allocation(client: AsyncClient, session: AsyncSession) -> None:
    user, month, food = await setup(client)
    url = allocation_url(month["id"], food)
    await client.put(url, headers=user.headers, json={"amount": "200.00"})

    assert (await client.delete(url, headers=user.headers)).status_code == 204
    assert await active_allocations(session, month["id"]) == []
    assert (await client.delete(url, headers=user.headers)).status_code == 404


async def test_allocations_are_independent_per_label(
    client: AsyncClient, session: AsyncSession
) -> None:
    user, month, food = await setup(client)
    savings = await label_id(client, user, "Savings")
    await client.put(
        allocation_url(month["id"], food), headers=user.headers, json={"amount": "200"}
    )
    await client.put(
        allocation_url(month["id"], savings), headers=user.headers, json={"amount": "300"}
    )
    amounts = sorted(str(a.amount) for a in await active_allocations(session, month["id"]))
    assert amounts == ["200.00", "300.00"]


async def test_allocation_amount_validation(client: AsyncClient) -> None:
    user, month, food = await setup(client)
    url = allocation_url(month["id"], food)
    for amount in ("-1.00", "10.555", "abc", "1000000000000.00"):
        response = await client.put(url, headers=user.headers, json={"amount": amount})
        assert response.status_code == 422, amount


async def test_archived_label_cannot_get_a_new_allocation(client: AsyncClient) -> None:
    user, month, food = await setup(client)
    url = allocation_url(month["id"], food)
    await client.put(url, headers=user.headers, json={"amount": "200.00"})
    await client.post(f"/api/v1/labels/{food}/archive", headers=user.headers)

    assert (await client.put(url, headers=user.headers, json={"amount": "250"})).status_code == 422
    # Removing an existing allocation of an archived label is still allowed.
    assert (await client.delete(url, headers=user.headers)).status_code == 204


async def test_closed_month_rejects_allocation_changes(client: AsyncClient) -> None:
    user, month, food = await setup(client)
    url = allocation_url(month["id"], food)
    await client.put(url, headers=user.headers, json={"amount": "200.00"})
    await client.post(f"/api/v1/months/{month['id']}/close", headers=user.headers)

    attempts = [
        await client.put(url, headers=user.headers, json={"amount": "250.00"}),
        await client.put(url, headers=user.headers, json={"amount": "0"}),
        await client.delete(url, headers=user.headers),
    ]
    assert [r.status_code for r in attempts] == [409, 409, 409]
    assert all(r.json()["code"] == "month_closed" for r in attempts)


async def test_users_cannot_allocate_on_each_others_months_or_labels(
    client: AsyncClient,
) -> None:
    _, alice_month, alice_food = await setup(client)
    bob, bob_month, bob_food = await setup(client)
    attempts = [
        # Bob on Alice's month with his own label, and on his month with Alice's label.
        await client.put(
            allocation_url(alice_month["id"], bob_food), headers=bob.headers, json={"amount": "1"}
        ),
        await client.put(
            allocation_url(bob_month["id"], alice_food), headers=bob.headers, json={"amount": "1"}
        ),
        await client.delete(allocation_url(alice_month["id"], alice_food), headers=bob.headers),
    ]
    assert [r.status_code for r in attempts] == [404, 404, 404]
