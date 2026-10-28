import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.enums import LabelKind
from app.domain.periods import Period


class ReportLabel(BaseModel):
    label_id: uuid.UUID
    name: str
    kind: LabelKind
    color: str
    icon: str
    archived: bool
    allocation: Decimal
    addition: Decimal
    transfer_in: Decimal
    transfer_out: Decimal
    total: Decimal = Field(description="allocation + addition + transfer_in - transfer_out")
    share: Decimal = Field(description="Percentage of the distributed money (donut slice)")


class ReportSummary(BaseModel):
    period: Period
    start_month: str | None = Field(description="First month of the window (YYYY-MM); null = all")
    end_month: str | None = Field(description="Last month of the window (YYYY-MM); null = all")
    reference_date: date = Field(description="Today in the user's time zone")
    total: Decimal = Field(description="Sum of the selected labels")
    by_kind: dict[LabelKind, Decimal]
    kind_shares: dict[LabelKind, Decimal] = Field(description="Percentages per kind (donut)")
    labels: list[ReportLabel] = Field(description="Selected labels, largest total first")


class SeriesPoint(BaseModel):
    month: str = Field(description="YYYY-MM")
    total: Decimal = Field(description="Net total of the label in that month")


class SeriesLabel(BaseModel):
    label_id: uuid.UUID
    name: str
    kind: LabelKind
    color: str
    icon: str
    archived: bool
    total: Decimal = Field(description="Net total over the whole window")
    points: list[SeriesPoint] = Field(description="One point per month of the window")


class ReportSeries(BaseModel):
    period: Period
    start_month: str | None = Field(description="First month of the series (YYYY-MM)")
    end_month: str | None = Field(description="Last month of the series (YYYY-MM)")
    reference_date: date = Field(description="Today in the user's time zone")
    months: list[str] = Field(description="Every month of the series, oldest first, gaps included")
    totals: list[SeriesPoint] = Field(description="Selected labels combined, per month")
    labels: list[SeriesLabel] = Field(description="Selected labels, largest window total first")
