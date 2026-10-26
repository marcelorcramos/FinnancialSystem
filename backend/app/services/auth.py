"""Authentication use cases: sign-up, login, refresh with rotation and logout."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.domain.default_labels import DEFAULT_LABELS
from app.domain.enums import AuditAction
from app.domain.errors import AuthenticationError, ConflictError
from app.models import Label, RefreshToken, User
from app.repositories import refresh_tokens, users
from app.schemas.user import UserCreate
from app.services import audit

INVALID_CREDENTIALS = "Incorrect email or password"
INVALID_SESSION = "Invalid or expired session"


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    expires_in: int
    refresh_token: str


async def register(session: AsyncSession, data: UserCreate) -> User:
    if await users.get_active_by_email(session, data.email):
        raise ConflictError("This email is already registered")

    user = User(
        email=data.email, name=data.name, password_hash=security.hash_password(data.password)
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:  # race between two sign-ups with the same email
        await session.rollback()
        raise ConflictError("This email is already registered") from exc

    labels = [
        Label(
            user_id=user.id,
            name=t.name,
            kind=t.kind,
            color=t.color,
            icon=t.icon,
            is_default=True,
        )
        for t in DEFAULT_LABELS
    ]
    session.add_all(labels)
    await session.flush()
    for label in labels:
        audit.record(
            session,
            user_id=user.id,
            entity="label",
            entity_id=label.id,
            action=AuditAction.CREATE,
            after=audit.snapshot(label),
        )
    await session.commit()
    return user


async def login(session: AsyncSession, email: str, password: str) -> IssuedTokens:
    user = await users.get_active_by_email(session, email)
    if not security.verify_password(password, user.password_hash if user else None):
        raise AuthenticationError(INVALID_CREDENTIALS)
    assert user is not None
    tokens, _ = await _issue(session, user.id, family_id=uuid.uuid4())
    await session.commit()
    return tokens


async def refresh(session: AsyncSession, raw_token: str | None) -> IssuedTokens:
    if not raw_token:
        raise AuthenticationError(INVALID_SESSION)
    now = datetime.now(UTC)
    current = await refresh_tokens.get_by_hash_for_update(
        session, security.hash_refresh_token(raw_token)
    )
    if current is None:
        raise AuthenticationError(INVALID_SESSION)

    if current.revoked_at is not None:
        # An already rotated token was used again: likely theft. Revoke the whole family.
        await refresh_tokens.revoke_family(session, current.family_id, now)
        await session.commit()
        raise AuthenticationError(INVALID_SESSION)

    if current.expires_at <= now or await users.get_active_by_id(session, current.user_id) is None:
        raise AuthenticationError(INVALID_SESSION)

    tokens, replacement = await _issue(session, current.user_id, family_id=current.family_id)
    current.revoked_at = now
    current.replaced_by_id = replacement.id
    await session.commit()
    return tokens


async def logout(session: AsyncSession, raw_token: str | None) -> None:
    if not raw_token:
        return
    current = await refresh_tokens.get_by_hash_for_update(
        session, security.hash_refresh_token(raw_token)
    )
    if current is not None:
        await refresh_tokens.revoke_family(session, current.family_id, datetime.now(UTC))
        await session.commit()


async def change_password(
    session: AsyncSession, user: User, current_password: str, new_password: str
) -> None:
    if not security.verify_password(current_password, user.password_hash):
        raise AuthenticationError("Current password is incorrect")
    user.password_hash = security.hash_password(new_password)
    # End every open session on other devices.
    await refresh_tokens.revoke_all_for_user(session, user.id, datetime.now(UTC))
    await session.commit()


async def _issue(
    session: AsyncSession, user_id: uuid.UUID, family_id: uuid.UUID
) -> tuple[IssuedTokens, RefreshToken]:
    access_token, expires_in = security.create_access_token(user_id)
    raw_refresh = security.generate_refresh_token()
    row = RefreshToken(
        user_id=user_id,
        family_id=family_id,
        token_hash=security.hash_refresh_token(raw_refresh),
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    session.add(row)
    await session.flush()
    return IssuedTokens(access_token, expires_in, raw_refresh), row
