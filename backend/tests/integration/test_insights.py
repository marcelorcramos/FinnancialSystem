"""Month insights written when a month closes (Phase 11)."""

import json
import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.events.consumers import Event, handle_once, insights_handler
from app.models import MonthInsight
from app.services import insights
from tests.integration.assistant_fakes import FakeClient, text
from tests.integration.helpers import ApiUser, create_month, label_id, new_user

INSIGHT = {
    "headline": "Housing took most of October.",
    "highlights": ["Food stayed under its limit.", "You saved €300.00."],
    "suggestion": "Move the unallocated €50.00 to Savings.",
}


async def closed_month(client: AsyncClient, user: ApiUser) -> str:
    month = (await create_month(client, user))["id"]
    food = await label_id(client, user, "Food")
    await client.put(
        f"/api/v1/months/{month}/allocations/{food}", headers=user.headers, json={"amount": "200"}
    )
    await client.post(f"/api/v1/months/{month}/close", headers=user.headers)
    return str(month)


async def test_closing_a_month_writes_its_insight(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await new_user(client)
    month = await closed_month(client, user)
    fake = FakeClient(text(json.dumps(INSIGHT)))
    handler = insights_handler(fake)
    event = Event(
        uuid.uuid4(),
        "month.update",
        {"user_id": str(user.id), "entity_id": month, "month_id": month},
    )
    sessions = async_sessionmaker(
        bind=session.bind, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    async with sessions() as consumer_session:
        assert await handle_once(consumer_session, "insights", event, handler) is True

    # The model got the month's numbers and a fixed JSON shape to answer in.
    request: dict[str, Any] = fake.requests[0]
    facts = json.loads(request["messages"][0]["content"])
    assert facts["month"]["labels"] == [{"name": "Food", "kind": "expense", "total": "200.00"}]
    assert facts["previous_month"] is None
    assert request["output_format"]["schema"]["required"] == [
        "headline",
        "highlights",
        "suggestion",
    ]

    response = await client.get(f"/api/v1/months/{month}/insight", headers=user.headers)
    assert response.status_code == 200
    assert response.json()["headline"] == INSIGHT["headline"]
    assert response.json()["highlights"] == INSIGHT["highlights"]
    assert response.json()["suggestion"] == INSIGHT["suggestion"]


async def test_one_insight_per_close(client: AsyncClient, session: AsyncSession) -> None:
    user = await new_user(client)
    month = uuid.UUID(await closed_month(client, user))
    fake = FakeClient(
        text(json.dumps(INSIGHT)), text(json.dumps({**INSIGHT, "headline": "Second close."}))
    )
    await insights.generate(session, fake, user.id, month)
    await insights.generate(session, fake, user.id, month)  # the same close: nothing new
    assert len(fake.requests) == 1

    await client.post(f"/api/v1/months/{month}/reopen", headers=user.headers)
    await client.post(f"/api/v1/months/{month}/close", headers=user.headers)
    insight = await insights.generate(session, fake, user.id, month)
    assert insight is not None and insight.headline == "Second close."
    rows = await session.scalars(select(MonthInsight).where(MonthInsight.month_id == month))
    assert len(list(rows)) == 1


async def test_open_months_and_other_users_have_no_insight(
    client: AsyncClient, session: AsyncSession
) -> None:
    alice, bob = await new_user(client), await new_user(client)
    open_month = (await create_month(client, alice, month=11))["id"]
    fake = FakeClient()
    assert await insights.generate(session, fake, alice.id, uuid.UUID(open_month)) is None
    assert fake.requests == []

    month = await closed_month(client, alice)
    await insights.generate(
        session, FakeClient(text(json.dumps(INSIGHT))), alice.id, uuid.UUID(month)
    )
    assert (
        await client.get(f"/api/v1/months/{month}/insight", headers=bob.headers)
    ).status_code == 404
    # Bob's id with Alice's month writes nothing.
    assert await insights.generate(session, FakeClient(), bob.id, uuid.UUID(month)) is None
    # Reopened: the old reading no longer applies.
    await client.post(f"/api/v1/months/{month}/reopen", headers=alice.headers)
    assert (
        await client.get(f"/api/v1/months/{month}/insight", headers=alice.headers)
    ).status_code == 404


async def test_without_the_assistant_the_consumer_does_nothing(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await new_user(client)
    month = await closed_month(client, user)
    handler = insights_handler(None)
    await handler(
        session, Event(uuid.uuid4(), "month.update", {"user_id": str(user.id), "month_id": month})
    )
    assert await session.scalar(select(MonthInsight).where(MonthInsight.user_id == user.id)) is None


async def test_a_refused_insight_is_skipped(client: AsyncClient, session: AsyncSession) -> None:
    user = await new_user(client)
    month = uuid.UUID(await closed_month(client, user))
    refusal = text("")
    refusal.stop_reason = "refusal"
    assert await insights.generate(session, FakeClient(refusal), user.id, month) is None
