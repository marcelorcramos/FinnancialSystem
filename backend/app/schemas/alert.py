import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.enums import AlertLevel


class AlertRead(BaseModel):
    id: uuid.UUID
    level: AlertLevel
    label_id: uuid.UUID
    label_name: str
    color: str
    month_id: uuid.UUID
    year: int
    month: int
    limit_amount: Decimal = Field(description="The limit when the alert was raised")
    total: Decimal = Field(description="The label's month total when the alert was raised")
    seen_at: datetime | None
    created_at: datetime
