"""The assistant (Phase 11): questions about the user's money, answered from their
reports through read-only tools (services/assistant_tools.py).

Conversations are stored exactly as sent to the model and only ever appended to:
the model checks that earlier turns come back unchanged. The system prompt and
the tools never change; today's date travels inside each question instead.
A turn is saved only once it is complete, so a failed call leaves no trace.
"""

import uuid
from datetime import date
from typing import Any

import anthropic
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.assistant_client import AssistantClient
from app.domain.enums import AssistantMessageKind
from app.domain.errors import AssistantUnavailableError, ConflictError, NotFoundError
from app.models import AssistantConversation, AssistantMessage, User
from app.services import assistant_tools

log = structlog.get_logger(__name__)

MAX_TOKENS = 16000
MAX_TOOL_ROUNDS = 6
MAX_MESSAGES = 80
TITLE_LENGTH = 80
NO_ANSWER = "Sorry, I could not answer that. Please try asking in another way."
REFUSED = "Sorry, I can't help with that request."

SYSTEM = """You are the assistant of FinnancialSystem, a personal finance app where people \
plan each month by hand: they record their income and split it across labels (expense, \
saving or investment), then add money or move it between labels during the month.

Answer questions about the user's own money using the tools, which read their reports. \
Never guess numbers: get every amount from a tool, and say so when the data does not \
cover what was asked (for example, a month without a sheet). Label names must match \
list_labels exactly, so call it when unsure.

Amounts are euros. Write them like €1,234.50. Months in tool calls are YYYY-MM; "the \
last N months" means the current month and the N-1 before it. Keep answers short and \
plain: a sentence or two with the numbers, and a short list only when it helps. You \
cannot change anything in the app, give investment advice, or see other people's data; \
say so if asked."""


async def list_conversations(session: AsyncSession, user: User) -> list[AssistantConversation]:
    stmt = (
        select(AssistantConversation)
        .where(AssistantConversation.user_id == user.id, AssistantConversation.deleted_at.is_(None))
        .order_by(AssistantConversation.updated_at.desc())
        .limit(30)
    )
    return list(await session.scalars(stmt))


async def get_conversation(
    session: AsyncSession, user: User, conversation_id: uuid.UUID, *, lock: bool = False
) -> AssistantConversation:
    stmt = select(AssistantConversation).where(
        AssistantConversation.id == conversation_id,
        AssistantConversation.user_id == user.id,
        AssistantConversation.deleted_at.is_(None),
    )
    conversation = await session.scalar(stmt.with_for_update() if lock else stmt)
    if conversation is None:
        raise NotFoundError("Conversation not found")
    return conversation


async def visible_messages(
    session: AsyncSession, user: User, conversation_id: uuid.UUID
) -> list[AssistantMessage]:
    """The questions and answers, in order (tool steps are left out)."""
    await get_conversation(session, user, conversation_id)
    stmt = (
        select(AssistantMessage)
        .where(
            AssistantMessage.conversation_id == conversation_id,
            AssistantMessage.user_id == user.id,
            AssistantMessage.kind != AssistantMessageKind.TOOL_RESULTS,
            AssistantMessage.text != "",
        )
        .order_by(AssistantMessage.position)
    )
    return list(await session.scalars(stmt))


async def delete_conversation(
    session: AsyncSession, user: User, conversation_id: uuid.UUID
) -> None:
    conversation = await get_conversation(session, user, conversation_id)
    conversation.deleted_at = func.now()
    await session.commit()


async def ask(
    session: AsyncSession,
    client: AssistantClient,
    user: User,
    question: str,
    today: date,
    conversation_id: uuid.UUID | None = None,
) -> tuple[AssistantConversation, AssistantMessage]:
    """Answer one question, calling tools as the model asks; returns the answer."""
    if conversation_id is None:
        conversation = AssistantConversation(user_id=user.id, title=_title(question))
        session.add(conversation)
        await session.flush()
        transcript: list[AssistantMessage] = []
    else:
        conversation = await get_conversation(session, user, conversation_id, lock=True)
        transcript = await _transcript(session, conversation.id)
    if len(transcript) >= MAX_MESSAGES:
        raise ConflictError("This conversation is long. Start a new one to keep going.")

    new: list[AssistantMessage] = []

    def add(
        role: str, kind: AssistantMessageKind, content: list[dict[str, Any]], text: str
    ) -> AssistantMessage:
        message = AssistantMessage(
            conversation_id=conversation.id,
            user_id=user.id,
            position=len(transcript) + len(new),
            role=role,
            kind=kind,
            content=content,
            text=text,
        )
        new.append(message)
        return message

    add(
        "user",
        AssistantMessageKind.QUESTION,
        [
            {"type": "text", "text": f"Today is {today:%A, %d %B %Y} ({today:%Y-%m-%d})."},
            {"type": "text", "text": question},
        ],
        question,
    )
    answer: AssistantMessage | None = None
    for _ in range(MAX_TOOL_ROUNDS):
        response = await _call(client, [*transcript, *new])
        content = [block.model_dump(mode="json", exclude_none=True) for block in response.content]
        text = "\n\n".join(b.text for b in response.content if b.type == "text").strip()
        if response.stop_reason == "refusal":
            text = text or REFUSED
        if response.stop_reason != "tool_use":
            answer = add("assistant", AssistantMessageKind.ANSWER, content, text or NO_ANSWER)
            break
        # A step towards the answer: kept for the model, not shown in the chat.
        add("assistant", AssistantMessageKind.ANSWER, content, "")
        results = [
            await _run_tool(session, user, today, block)
            for block in response.content
            if block.type == "tool_use"
        ]
        add("user", AssistantMessageKind.TOOL_RESULTS, results, "")
    if answer is None:
        # Still asking for tools after every round: close the turn with a plain reply.
        answer = add(
            "assistant",
            AssistantMessageKind.ANSWER,
            [{"type": "text", "text": NO_ANSWER}],
            NO_ANSWER,
        )
    session.add_all(new)
    conversation.updated_at = func.now()
    await session.commit()
    return conversation, answer


async def _transcript(session: AsyncSession, conversation_id: uuid.UUID) -> list[AssistantMessage]:
    stmt = (
        select(AssistantMessage)
        .where(AssistantMessage.conversation_id == conversation_id)
        .order_by(AssistantMessage.position)
    )
    return list(await session.scalars(stmt))


async def _call(client: AssistantClient, messages: list[AssistantMessage]) -> Any:
    try:
        response = await client.create(
            system=SYSTEM,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            max_tokens=MAX_TOKENS,
            tools=assistant_tools.TOOLS,
        )
    except anthropic.RateLimitError as error:
        log.warning("assistant.rate_limited", request_id=getattr(error, "request_id", None))
        raise AssistantUnavailableError("The assistant is busy. Try again in a minute.") from error
    except (anthropic.APIConnectionError, anthropic.APIStatusError) as error:
        log.warning("assistant.failed", error=type(error).__name__)
        raise AssistantUnavailableError("The assistant could not answer right now.") from error
    log.info(
        "assistant.usage",
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        stop_reason=response.stop_reason,
    )
    return response


async def _run_tool(session: AsyncSession, user: User, today: date, block: Any) -> dict[str, Any]:
    try:
        output = await assistant_tools.run(session, user, today, block.name, dict(block.input))
        return {"type": "tool_result", "tool_use_id": block.id, "content": output}
    except assistant_tools.ToolError as error:
        return {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": str(error),
            "is_error": True,
        }


def _title(question: str) -> str:
    line = " ".join(question.split())
    return line if len(line) <= TITLE_LENGTH else line[: TITLE_LENGTH - 1].rstrip() + "…"
