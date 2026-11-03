import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, PrimaryKeyConstraint, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKey


class OutboxEvent(UUIDPrimaryKey, Base):
    """A domain event, written in the same transaction as the change it describes.

    The relay (app/events/relay.py) publishes it to RabbitMQ and sets published_at.
    """

    __tablename__ = "outbox_events"
    __table_args__ = (
        # The relay only reads what is still waiting, oldest first.
        Index(
            "ix_outbox_events_pending",
            "created_at",
            postgresql_where=text("published_at IS NULL"),
        ),
    )

    type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProcessedEvent(Base):
    """An event a consumer already handled: reprocessing it is a no-op (idempotency)."""

    __tablename__ = "processed_events"
    __table_args__ = (PrimaryKeyConstraint("consumer", "event_id"),)

    consumer: Mapped[str] = mapped_column(String(50))
    event_id: Mapped[uuid.UUID]
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
