import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey
from app.db.types import Money, str_enum
from app.domain.enums import MovementType

_ACTIVE = "deleted_at IS NULL"


class Entry(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    __tablename__ = "entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        # transfer_id is set if and only if the entry is a transfer leg.
        CheckConstraint(
            "(movement_type IN ('transfer_in', 'transfer_out')) = (transfer_id IS NOT NULL)",
            name="transfer_id_matches_type",
        ),
        # income_id is set if and only if the entry is an addition.
        CheckConstraint(
            "(movement_type = 'addition') = (income_id IS NOT NULL)",
            name="income_id_matches_type",
        ),
        Index("ix_entries_user_occurred_on", "user_id", "occurred_on"),
        Index("ix_entries_user_label_occurred_on", "user_id", "label_id", "occurred_on"),
        Index("ix_entries_transfer_id", "transfer_id"),
        Index("ix_entries_month_id", "month_id"),
        # At most one allocation per label and month.
        Index(
            "uq_entries_allocation_per_label_month",
            "month_id",
            "label_id",
            unique=True,
            postgresql_where=text(f"movement_type = 'allocation' AND {_ACTIVE}"),
        ),
        # Each transfer has at most one leg of each type.
        Index(
            "uq_entries_transfer_leg",
            "transfer_id",
            "movement_type",
            unique=True,
            postgresql_where=text(f"transfer_id IS NOT NULL AND {_ACTIVE}"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    month_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("months.id", ondelete="CASCADE"))
    label_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("labels.id", ondelete="RESTRICT"))
    amount: Mapped[Decimal] = mapped_column(Money)
    movement_type: Mapped[MovementType] = mapped_column(str_enum(MovementType, "movement_type"))
    transfer_id: Mapped[uuid.UUID | None]
    income_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("incomes.id", ondelete="RESTRICT")
    )
    occurred_on: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(String(1000))
