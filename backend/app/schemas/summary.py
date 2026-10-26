import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.enums import LabelKind


class LabelSummary(BaseModel):
    """A label's total in the month, split into "base + adjustments"."""

    label_id: uuid.UUID
    name: str
    kind: LabelKind
    color: str
    icon: str
    archived: bool
    allocation: Decimal = Field(description="Initial distribution (base)")
    addition: Decimal = Field(description="Money added from outside the app")
    transfer_in: Decimal
    transfer_out: Decimal
    total: Decimal = Field(description="allocation + addition + transfer_in - transfer_out")


class MonthSummary(BaseModel):
    month_id: uuid.UUID
    year: int
    month: int
    closed_at: datetime | None
    income_total: Decimal
    distributed: Decimal = Field(description="Sum of allocations and additions")
    unallocated: Decimal = Field(description="income_total - distributed; may be negative")
    over_allocated: bool = Field(description="True when more was distributed than earned")
    month_total: Decimal = Field(description="Sum of every label total (transfers cancel out)")
    by_kind: dict[LabelKind, Decimal]
    labels: list[LabelSummary]
