import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKey
from app.db.types import str_enum
from app.domain.enums import ExportFormat, ExportKind, ExportStatus
from app.domain.periods import Period


class Export(UUIDPrimaryKey, Base):
    """A file the worker builds on request (report CSV/PDF or the account's data)."""

    __tablename__ = "exports"
    __table_args__ = (Index("ix_exports_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[ExportKind] = mapped_column(str_enum(ExportKind, "export_kind"))
    format: Mapped[ExportFormat] = mapped_column(str_enum(ExportFormat, "export_format"))
    status: Mapped[ExportStatus] = mapped_column(
        str_enum(ExportStatus, "export_status"), default=ExportStatus.PENDING
    )
    # Report filters, fixed when asked for: the window ends at that day's month.
    period: Mapped[Period | None] = mapped_column(str_enum(Period, "export_period"))
    label_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    kinds: Mapped[list[str]] = mapped_column(JSONB, default=list)
    reference_date: Mapped[date] = mapped_column(Date)
    storage_key: Mapped[str | None] = mapped_column(String(300))
    filename: Mapped[str | None] = mapped_column(String(200))
    size: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
