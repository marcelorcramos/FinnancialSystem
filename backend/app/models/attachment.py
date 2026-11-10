import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey


class Attachment(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    """A receipt (photo or PDF) of a month, optionally tied to one of its entries."""

    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint("size > 0", name="size_positive"),
        Index("ix_attachments_user_month", "user_id", "month_id"),
        Index("ix_attachments_entry_id", "entry_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    month_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("months.id", ondelete="CASCADE"))
    entry_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("entries.id", ondelete="CASCADE"))
    storage_key: Mapped[str] = mapped_column(String(300), unique=True)
    filename: Mapped[str] = mapped_column(String(200))
    mime: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
