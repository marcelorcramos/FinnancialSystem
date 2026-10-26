import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey
from app.db.types import str_enum
from app.domain.enums import LabelKind


class Label(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    __tablename__ = "labels"
    __table_args__ = (
        Index(
            "uq_labels_user_name_active",
            "user_id",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(50))
    kind: Mapped[LabelKind] = mapped_column(str_enum(LabelKind, "label_kind"))
    color: Mapped[str] = mapped_column(String(7))  # #RRGGBB
    icon: Mapped[str] = mapped_column(String(50))
    is_default: Mapped[bool] = mapped_column(default=False, server_default=text("false"))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
