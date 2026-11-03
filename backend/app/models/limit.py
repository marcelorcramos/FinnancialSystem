import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey
from app.db.types import Money, str_enum
from app.domain.enums import AlertLevel

_ACTIVE = "deleted_at IS NULL"


class Limit(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    """A maximum for a label: the default (month_id null) or for one month."""

    __tablename__ = "limits"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        Index(
            "uq_limits_label_default",
            "label_id",
            unique=True,
            postgresql_where=text(f"month_id IS NULL AND {_ACTIVE}"),
        ),
        Index(
            "uq_limits_label_month",
            "label_id",
            "month_id",
            unique=True,
            postgresql_where=text(f"month_id IS NOT NULL AND {_ACTIVE}"),
        ),
        Index("ix_limits_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    label_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("labels.id", ondelete="CASCADE"))
    month_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("months.id", ondelete="CASCADE"))
    amount: Mapped[Decimal] = mapped_column(Money)


class Alert(UUIDPrimaryKey, Base):
    """A limit reached in a month. Each level is raised at most once per label and month."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("uq_alerts_label_month_level", "label_id", "month_id", "level", unique=True),
        Index("ix_alerts_user_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    limit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("limits.id", ondelete="CASCADE"))
    label_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("labels.id", ondelete="CASCADE"))
    month_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("months.id", ondelete="CASCADE"))
    level: Mapped[AlertLevel] = mapped_column(str_enum(AlertLevel, "alert_level"))
    limit_amount: Mapped[Decimal] = mapped_column(Money)
    total: Mapped[Decimal] = mapped_column(Money)
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
