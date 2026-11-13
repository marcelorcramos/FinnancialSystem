import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey
from app.db.types import str_enum
from app.domain.enums import TokenPurpose


class User(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "uq_users_email_active",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_users_google_id",
            "google_id",
            unique=True,
            postgresql_where=text("google_id IS NOT NULL"),
        ),
    )

    email: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255))  # null for Google-only accounts
    name: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    currency: Mapped[str] = mapped_column(String(3), default="EUR", server_default="EUR")
    locale: Mapped[str] = mapped_column(String(10), default="pt-PT", server_default="pt-PT")
    timezone: Mapped[str] = mapped_column(
        String(50), default="Europe/Lisbon", server_default="Europe/Lisbon"
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Create each new month automatically, copying the previous one (Celery beat).
    auto_new_month: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    google_id: Mapped[str | None] = mapped_column(String(255))
    # TOTP 2FA: the secret is encrypted (core/two_factor.py); enabled once a code was confirmed.
    totp_secret: Mapped[str | None] = mapped_column(String(255))
    totp_enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Last 30-second step accepted, so a code cannot be used twice.
    totp_last_step: Mapped[int | None] = mapped_column(Integer)
    # Demo accounts ("Try it") are deleted after this moment; null for real accounts.
    demo_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None

    @property
    def google_linked(self) -> bool:
        return self.google_id is not None

    @property
    def two_factor_enabled(self) -> bool:
        return self.totp_enabled_at is not None

    @property
    def is_demo(self) -> bool:
        return self.demo_expires_at is not None


class RefreshToken(UUIDPrimaryKey, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    family_id: Mapped[uuid.UUID] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)  # sha256 hex
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class UserToken(UUIDPrimaryKey, Base):
    """One-time token sent by email (verify the address, reset the password)."""

    __tablename__ = "user_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[TokenPurpose] = mapped_column(str_enum(TokenPurpose, "token_purpose"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)  # sha256 hex
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class RecoveryCode(UUIDPrimaryKey, Base):
    """One-time code that replaces a TOTP code when the phone is lost (stored hashed)."""

    __tablename__ = "recovery_codes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    code_hash: Mapped[str] = mapped_column(String(64))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
