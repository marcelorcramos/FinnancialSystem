import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey
from app.db.types import str_enum
from app.domain.enums import AssistantMessageKind


class AssistantConversation(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    __tablename__ = "assistant_conversations"
    __table_args__ = (Index("ix_assistant_conversations_user_updated", "user_id", "updated_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(120))


class AssistantMessage(UUIDPrimaryKey, Base):
    """One message of the transcript sent to the model, kept exactly as sent (append-only):
    the model checks that earlier turns are unchanged when they come back."""

    __tablename__ = "assistant_messages"
    __table_args__ = (
        Index("uq_assistant_messages_position", "conversation_id", "position", unique=True),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assistant_conversations.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(16))  # "user" or "assistant", as the API sees it
    kind: Mapped[AssistantMessageKind] = mapped_column(
        str_enum(AssistantMessageKind, "assistant_message_kind")
    )
    content: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    # What the user sees: the question, or the answer's text (empty for tool steps).
    text: Mapped[str] = mapped_column(String(20000), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sql_text("now()")
    )


class MonthInsight(UUIDPrimaryKey, Base):
    """A short reading of a closed month, written when the month closes."""

    __tablename__ = "month_insights"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    month_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("months.id", ondelete="CASCADE"), unique=True
    )
    # The close it was written for: closing again after changes writes a new one.
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    headline: Mapped[str] = mapped_column(String(300))
    highlights: Mapped[list[str]] = mapped_column(JSONB)
    suggestion: Mapped[str | None] = mapped_column(String(600))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sql_text("now()")
    )
