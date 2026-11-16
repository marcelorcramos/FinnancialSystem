import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AssistantStatus(BaseModel):
    enabled: bool


class AssistantQuestion(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    conversation_id: uuid.UUID | None = Field(
        default=None, description="Continue this conversation; omit to start a new one"
    )


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str = Field(description='"question" or "answer"')
    text: str
    created_at: datetime


class AssistantAnswer(BaseModel):
    conversation: ConversationRead
    answer: ChatMessage


class InsightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    month_id: uuid.UUID
    headline: str
    highlights: list[str]
    suggestion: str | None
    created_at: datetime
