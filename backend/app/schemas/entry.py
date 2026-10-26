import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import MovementType
from app.schemas.common import NonNegativeMoney, Note


class AllocationSet(BaseModel):
    amount: NonNegativeMoney = Field(description="Setting 0 removes the allocation")
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
