import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, SmallInteger, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey
from app.db.types import Money, str_enum
from app.domain.enums import GoalType


class Goal(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    """Money to gather in a label, optionally by a deadline (Phase 8).

    A normal goal has a fixed target; the emergency fund's target is N months of
    average expenses. Progress is the label's balance unless set by hand.
    """

    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint(
            "(type = 'normal' AND target_amount > 0 AND months_of_expenses IS NULL)"
            " OR (type = 'emergency_fund' AND target_amount IS NULL"
            " AND months_of_expenses BETWEEN 1 AND 24)",
            name="target_matches_type",
        ),
        # One goal at a time per label: they would count the same money.
        Index(
            "uq_goals_label_active",
            "label_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND completed_at IS NULL"),
        ),
        Index("ix_goals_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    label_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("labels.id", ondelete="CASCADE"))
    type: Mapped[GoalType] = mapped_column(str_enum(GoalType, "goal_type"))
    target_amount: Mapped[Decimal | None] = mapped_column(Money)
    months_of_expenses: Mapped[int | None] = mapped_column(SmallInteger)
    deadline: Mapped[date | None] = mapped_column(Date)
    manual_progress: Mapped[Decimal | None] = mapped_column(Money)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
