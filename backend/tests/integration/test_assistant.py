"""The assistant (Phase 11), with a scripted client in place of the Claude API."""

from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import anthropic
import httpx2
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.assistant_client import get_assistant_client
from app.main import app
from app.models import AssistantMessage
from app.services import assistant
from app.services.assistant_tools import TOOLS
from tests.integration.assistant_fakes import (
    FakeClient,
    last_tool_result,
    text,
    tool_call,
    tool_output,
)
from tests.integration.helpers import ApiUser, new_user
from tests.integration.test_reports import fixed_today, make_book

__all__ = ["fixed_today"]


@pytest.fixture
def use_client() -> Iterator[Any]:
    def install(client: FakeClient) -> FakeClient:
        app.dependency_overrides[get_assistant_client] = lambda: client
        return client

    yield install
    app.dependency_overrides.pop(get_assistant_client, None)


async def ask(
    client: AsyncClient, user: ApiUser, question: str, conversation: str | None = None
) -> Any:
    body: dict[str, Any] = {"text": question}
    if conversation:
        body["conversation_id"] = conversation
    return await client.post("/api/v1/assistant/questions", headers=user.headers, json=body)


async def test_the_assistant_is_off_without_an_api_key(client: AsyncClient) -> None:
    user = await new_user(client)
    assert (await client.get("/api/v1/assistant/status")).json() == {"enabled": False}
    response = await ask(client, user, "How much did I spend?")
    assert response.status_code == 503
    assert response.json()["code"] == "assistant_unavailable"


async def test_how_much_did_i_invest_in_the_last_2_months(
    client: AsyncClient, use_client: Any
) -> None:
    """Acceptance criterion: the answer has the same amount as the Phase 3 report."""
    book = await make_book(client)  # today is 26 October 2026
    series = (
        await client.get(
            "/api/v1/reports/series",
            headers=book.user.headers,
            params={"period": "last_6_months", "kinds": "investment"},
        )
    ).json()
    report_total = sum(Decimal(p["total"]) for p in series["totals"] if p["month"] >= "2026-09")
    assert report_total == Decimal("50.00")  # the €50 added in September

    fake = use_client(
        FakeClient(
            tool_call(
                "totals",
                {
                    "start_month": "2026-09",
                    "end_month": "2026-10",
                    "labels": [],
                    "kinds": ["investment"],
                },
            ),
            lambda messages: text(
                f"You invested €{tool_output(messages)['total']} in the last 2 months."
            ),
        )
    )
    response = await ask(client, book.user, "How much did I invest in the last 2 months?")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"]["text"] == f"You invested €{report_total} in the last 2 months."
    assert body["conversation"]["title"] == "How much did I invest in the last 2 months?"

    # What the model received: the frozen system prompt and tools, and the date in the question.
    first = fake.requests[0]
    assert first["system"] == assistant.SYSTEM
    assert first["tools"] == TOOLS
    assert (
        first["messages"][0]["content"][0]["text"]
        == "Today is Monday, 26 October 2026 (2026-10-26)."
    )
    assert (
        first["messages"][0]["content"][1]["text"] == "How much did I invest in the last 2 months?"
    )


async def test_a_conversation_replays_every_earlier_turn_unchanged(
    client: AsyncClient, session: AsyncSession, use_client: Any
) -> None:
    book = await make_book(client)
    fake = use_client(
        FakeClient(
            tool_call("list_labels", {}),
            text("You have 11 labels."),
            text("Food got €212.00 this month."),
        )
    )
    first = (await ask(client, book.user, "What labels do I have?")).json()
    conversation = first["conversation"]["id"]
    second = await ask(client, book.user, "And Food?", conversation)
    assert second.json()["answer"]["text"] == "Food got €212.00 this month."

    sent_before = fake.requests[1]["messages"] + [
        {
            "role": "assistant",
            "content": [
                {"signature": "sig", "thinking": "", "type": "thinking"},
                {"text": "You have 11 labels.", "type": "text"},
            ],
        }
    ]
    replayed = fake.requests[2]["messages"]
    assert replayed[: len(sent_before)] == sent_before  # append-only, thinking blocks included
    assert fake.requests[2]["system"] == fake.requests[0]["system"]
    assert fake.requests[2]["tools"] == fake.requests[0]["tools"]

    shown = (
        await client.get(
            f"/api/v1/assistant/conversations/{conversation}", headers=book.user.headers
        )
    ).json()
    assert [(m["kind"], m["text"]) for m in shown] == [
        ("question", "What labels do I have?"),
        ("answer", "You have 11 labels."),
        ("question", "And Food?"),
        ("answer", "Food got €212.00 this month."),
    ]
    stored = await session.scalar(
        select(func.count())
        .select_from(AssistantMessage)
        .where(AssistantMessage.user_id == book.user.id)
    )
    assert stored == 6  # question, tool step, tool results, answer, question, answer


async def test_a_wrong_label_comes_back_as_a_tool_error(
    client: AsyncClient, use_client: Any
) -> None:
    user = await new_user(client)

    def answer(messages: list[dict[str, Any]]) -> Any:
        result = last_tool_result(messages)
        assert result["is_error"] is True
        assert "There is no label called 'Holidays'" in result["content"]
        return text("You have no label called Holidays.")

    use_client(
        FakeClient(
            tool_call(
                "totals",
                {
                    "start_month": "2026-10",
                    "end_month": "2026-10",
                    "labels": ["Holidays"],
                    "kinds": [],
                },
            ),
            answer,
        )
    )
    response = await ask(client, user, "How much went to Holidays?")
    assert response.json()["answer"]["text"] == "You have no label called Holidays."


async def test_tools_only_see_the_signed_in_users_money(
    client: AsyncClient, use_client: Any
) -> None:
    alice = await make_book(client)
    bob = await new_user(client)
    use_client(
        FakeClient(
            tool_call(
                "totals",
                {"start_month": "2026-05", "end_month": "2026-10", "labels": [], "kinds": []},
            ),
            lambda messages: text(f"Total: {tool_output(messages)['total']}"),
        )
    )
    assert (await ask(client, bob, "How much have I spent?")).json()["answer"][
        "text"
    ] == "Total: 0.00"

    # Alice's conversations are not Bob's.
    use_client(FakeClient(text("Hello.")))
    conversation = (await ask(client, alice.user, "Hi")).json()["conversation"]["id"]
    url = f"/api/v1/assistant/conversations/{conversation}"
    assert (await client.get(url, headers=bob.headers)).status_code == 404
    assert (await client.delete(url, headers=bob.headers)).status_code == 404
    assert (await ask(client, bob, "Hi", conversation)).status_code == 404
    listed = (await client.get("/api/v1/assistant/conversations", headers=bob.headers)).json()
    assert all(c["id"] != conversation for c in listed)


async def test_a_failed_call_saves_nothing(
    client: AsyncClient, session: AsyncSession, use_client: Any
) -> None:
    user = await new_user(client)
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    use_client(FakeClient(anthropic.APIConnectionError(request=request)))
    response = await ask(client, user, "How much did I spend?")
    assert response.status_code == 503
    assert response.json()["detail"] == "The assistant could not answer right now."
    count = await session.scalar(
        select(func.count())
        .select_from(AssistantMessage)
        .where(AssistantMessage.user_id == user.id)
    )
    assert count == 0


async def test_refusals_and_endless_tool_calls_get_a_plain_reply(
    client: AsyncClient, use_client: Any
) -> None:
    user = await new_user(client)
    refusal = text("")
    refusal.stop_reason = "refusal"
    refusal.content = refusal.content[:1]
    use_client(FakeClient(refusal))
    assert (await ask(client, user, "...")).json()["answer"]["text"] == assistant.REFUSED

    use_client(
        FakeClient(
            *[tool_call("list_labels", {}, f"toolu_{i}") for i in range(assistant.MAX_TOOL_ROUNDS)]
        )
    )
    assert (await ask(client, user, "Loop")).json()["answer"]["text"] == assistant.NO_ANSWER


async def test_long_conversations_must_start_again(
    client: AsyncClient, use_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assistant, "MAX_MESSAGES", 2)
    user = await new_user(client)
    use_client(FakeClient(text("One."), text("Two.")))
    conversation = (await ask(client, user, "First")).json()["conversation"]["id"]
    response = await ask(client, user, "Second", conversation)
    assert response.status_code == 409


async def test_conversations_list_and_delete(client: AsyncClient, use_client: Any) -> None:
    user = await new_user(client)
    use_client(FakeClient(text("A."), text("B.")))
    first = (await ask(client, user, "First question")).json()["conversation"]["id"]
    second = (await ask(client, user, "Second question")).json()["conversation"]["id"]
    listed = (await client.get("/api/v1/assistant/conversations", headers=user.headers)).json()
    assert [c["id"] for c in listed] == [second, first]
    deleted = await client.delete(f"/api/v1/assistant/conversations/{first}", headers=user.headers)
    assert deleted.status_code == 204
    listed = (await client.get("/api/v1/assistant/conversations", headers=user.headers)).json()
    assert [c["id"] for c in listed] == [second]


async def test_assistant_routes_need_a_signed_in_user(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/assistant/questions", json={"text": "x"})).status_code == 401
    assert (await client.get("/api/v1/assistant/conversations")).status_code == 401
