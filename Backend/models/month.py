from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base

class Month(Base):
    __tablename__ = "months"
    __table_args__ = (UniqueConstraint("user_id", "year", "month",name = "uq_user_year_month"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    income: Mapped[int | None] = mapped_column(Nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_closed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())