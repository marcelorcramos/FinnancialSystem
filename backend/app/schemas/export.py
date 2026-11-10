import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ExportFormat, ExportKind, ExportStatus, LabelKind
from app.domain.periods import Period


class ReportExportCreate(BaseModel):
    format: ExportFormat = Field(description="csv or pdf")
    period: Period = Period.ALL
    label_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    kinds: list[LabelKind] = Field(default_factory=list)


class ExportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: ExportKind
    format: ExportFormat
    status: ExportStatus
    period: Period | None
    label_ids: list[uuid.UUID]
    kinds: list[LabelKind]
    reference_date: date
    filename: str | None
    size: int | None = Field(description="Bytes, once ready")
    error: str | None
    created_at: datetime
    completed_at: datetime | None
    expires_at: datetime | None = Field(description="The file is removed after this moment")
