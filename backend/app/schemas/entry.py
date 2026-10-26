import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import MovementType
from app.schemas.common import NonNegativeMoney, Note, PositiveMoney
from app.schemas.month import Source

DEFAULT_ADDITION_SOURCE = "Extra income"


class AllocationSet(BaseModel):
    amount: NonNegativeMoney = Field(description="Setting 0 removes the allocation")
    note: Note | None = None


class AdditionCreate(BaseModel):
    """Money that arrives mid-month for a label; it also raises the month's income."""

    label_id: uuid.UUID
    amount: PositiveMoney
    occurred_on: date
    source: Source | None = Field(
        default=None,
        description=f"Where the money came from (default: {DEFAULT_ADDITION_SOURCE!r})",
    )
    note: Note | None = None


class EntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    month_id: uuid.UUID
    label_id: uuid.UUID
    amount: Decimal
    movement_type: MovementType
    transfer_id: uuid.UUID | None
    income_id: uuid.UUID | None
    occurred_on: date
    note: str | None
    created_at: datetime


class AdditionRead(EntryRead):
    source: str
