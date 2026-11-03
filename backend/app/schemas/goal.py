import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.enums import GoalType
from app.schemas.common import NonNegativeMoney, PositiveMoney


class GoalCreate(BaseModel):
    label_id: uuid.UUID
    type: GoalType = GoalType.NORMAL
    target_amount: PositiveMoney | None = Field(default=None, description="Required for normal")
    months_of_expenses: int | None = Field(
        default=None, ge=1, le=24, description="Required for emergency_fund (e.g. 6)"
    )
    deadline: date | None = None
    manual_progress: NonNegativeMoney | None = Field(
        default=None, description="Set to track progress by hand instead of the label balance"
    )


class GoalUpdate(BaseModel):
    """Only the fields sent change; send null to clear deadline or manual_progress."""

    target_amount: PositiveMoney | None = None
    months_of_expenses: int | None = Field(default=None, ge=1, le=24)
    deadline: date | None = None
    manual_progress: NonNegativeMoney | None = None


class GoalRead(BaseModel):
    id: uuid.UUID
    label_id: uuid.UUID
    label_name: str
    color: str
    icon: str
    type: GoalType
    target_amount: Decimal | None = Field(
        description="The fixed target, or for the emergency fund N months of average expenses"
        " (null until there is a complete month to average)"
    )
    months_of_expenses: int | None
    average_expenses: Decimal | None = Field(description="Emergency fund: monthly average used")
    deadline: date | None
    manual_progress: Decimal | None
    progress: Decimal = Field(description="manual_progress, or the label's balance over all months")
    remaining: Decimal
    percent: Decimal
    months_left: int | None = Field(description="Months to save in, the current one included")
    days_left: int | None
    per_month: Decimal | None = Field(description="What to save each month to finish on time")
    reached: bool
    overdue: bool
    completed_at: datetime | None
    created_at: datetime


class GoalList(BaseModel):
    active: list[GoalRead]
    completed: list[GoalRead] = Field(description="History of reached goals, newest first")
