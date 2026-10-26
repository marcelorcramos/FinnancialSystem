import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

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


class TransferCreate(BaseModel):
    """Move money from one label to another. Stored as two linked entries (the "legs")."""

    from_label_id: uuid.UUID
    to_label_id: uuid.UUID
    amount: PositiveMoney
    occurred_on: date
    note: Note | None = None


class TransferUpdate(BaseModel):
    from_label_id: uuid.UUID | None = None
    to_label_id: uuid.UUID | None = None
    amount: PositiveMoney | None = None
    occurred_on: date | None = None
    note: Note | None = None


class TransferRead(BaseModel):
    transfer_id: uuid.UUID
    month_id: uuid.UUID
    from_label_id: uuid.UUID
    to_label_id: uuid.UUID
    amount: Decimal
    occurred_on: date
    note: str | None
    out_entry_id: uuid.UUID
    in_entry_id: uuid.UUID


EntryOrigin = Literal["initial_distribution", "external_income", "transfer_in", "transfer_out"]


class EntryListItem(EntryRead):
    """An entry with where its money came from, for the month's entry list."""

    origin: EntryOrigin
    source: str | None = Field(default=None, description="Income source of an addition")
    counterpart_label_id: uuid.UUID | None = Field(
        default=None, description="The other label of a transfer"
    )


class EntryUpdate(BaseModel):
    """Edit an allocation (amount, note) or an addition (all fields). Transfers use /transfers."""

    amount: PositiveMoney | None = None
    occurred_on: date | None = None
    label_id: uuid.UUID | None = None
    source: Source | None = None
    note: Note | None = None
