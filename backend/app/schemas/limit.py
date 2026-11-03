import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AlertLevel
from app.schemas.common import PositiveMoney


class LimitSet(BaseModel):
    amount: PositiveMoney


class LimitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label_id: uuid.UUID
    month_id: uuid.UUID | None = Field(description="null = the label's default limit")
    amount: Decimal


class LimitStatus(BaseModel):
    """How much of its limit a label used in a month."""

    label_id: uuid.UUID
    name: str
    color: str
    limit_id: uuid.UUID
    limit: Decimal
    source: str = Field(description='"month" (set for this month) or "default"')
    total: Decimal = Field(description="The label's total in the month")
    remaining: Decimal = Field(description="limit - total; negative when exceeded")
    percent: Decimal = Field(description="Share of the limit used (2 decimals)")
    level: AlertLevel | None = Field(description="warning from 80%, exceeded from 100%")
