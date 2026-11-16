import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, RateLimiterDep, SessionDep, Today
from app.core.assistant_client import AssistantClient, get_assistant_client
from app.core.rate_limit import ASSISTANT_PER_USER
from app.domain.errors import AssistantUnavailableError
from app.schemas.assistant import (
    AssistantAnswer,
    AssistantQuestion,
    AssistantStatus,
    ChatMessage,
    ConversationRead,
    InsightRead,
)
from app.services import assistant, insights

router = APIRouter(tags=["assistant"])

ClientDep = Annotated[AssistantClient | None, Depends(get_assistant_client)]


@router.get("/assistant/status")
async def assistant_status(client: ClientDep) -> AssistantStatus:
    """Whether the assistant is set up on this server (the app hides it otherwise)."""
    return AssistantStatus(enabled=client is not None)


@router.post("/assistant/questions")
async def ask(
    data: AssistantQuestion,
    user: CurrentUser,
    session: SessionDep,
    today: Today,
    client: ClientDep,
    limiter: RateLimiterDep,
) -> AssistantAnswer:
    """Ask about your money; the answer comes from your own reports."""
    if client is None:
        raise AssistantUnavailableError("The assistant is not set up on this server")
    await limiter.hit(ASSISTANT_PER_USER, str(user.id))
    conversation, answer = await assistant.ask(
        session, client, user, data.text.strip(), today, data.conversation_id
    )
    return AssistantAnswer(
        conversation=ConversationRead.model_validate(conversation),
        answer=ChatMessage.model_validate(answer),
    )


@router.get("/assistant/conversations")
async def list_conversations(user: CurrentUser, session: SessionDep) -> list[ConversationRead]:
    """The latest 30 conversations, most recent first."""
    items = await assistant.list_conversations(session, user)
    return [ConversationRead.model_validate(c) for c in items]


@router.get("/assistant/conversations/{conversation_id}")
async def conversation_messages(
    conversation_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[ChatMessage]:
    """The questions and answers of a conversation, in order."""
    items = await assistant.visible_messages(session, user, conversation_id)
    return [ChatMessage.model_validate(m) for m in items]


@router.delete("/assistant/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> None:
    await assistant.delete_conversation(session, user, conversation_id)


@router.get("/months/{month_id}/insight")
async def month_insight(month_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> InsightRead:
    """The reading written when the month was closed; 404 until there is one."""
    return InsightRead.model_validate(await insights.get(session, user, month_id))
