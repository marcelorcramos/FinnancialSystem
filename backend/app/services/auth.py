"""Authentication use cases: sign-up, login, refresh with rotation, logout, email
verification and password reset."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.google import GoogleUser
from app.core.jobs import DELETE_USER_FILES, JobQueue
from app.domain.default_labels import DEFAULT_LABELS
from app.domain.enums import AuditAction, TokenPurpose
from app.domain.errors import AuthenticationError, ConflictError, InvalidTokenError
from app.models import Entry, Label, RefreshToken, User, UserToken
from app.repositories import refresh_tokens, user_tokens, users
from app.schemas.user import UserCreate
from app.services import audit, emails, two_factor

log = structlog.get_logger(__name__)

INVALID_CREDENTIALS = "Incorrect email or password"
INVALID_SESSION = "Invalid or expired session"

TOKEN_LIFETIME = {
    TokenPurpose.VERIFY_EMAIL: timedelta(hours=48),
    TokenPurpose.RESET_PASSWORD: timedelta(hours=1),
}


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    expires_in: int
    refresh_token: str


@dataclass(frozen=True, slots=True)
class TwoFactorTicket:
    """The first step passed; a TOTP or recovery code must follow."""

    ticket: str
    expires_in: int = security.TWO_FACTOR_TICKET_SECONDS


async def register(session: AsyncSession, data: UserCreate, jobs: JobQueue) -> User:
    if await users.get_active_by_email(session, data.email):
        raise ConflictError("This email is already registered")
    user = await create_user(
        session,
        User(email=data.email, name=data.name, password_hash=security.hash_password(data.password)),
    )
    token = await _new_token(session, user.id, TokenPurpose.VERIFY_EMAIL)
    await session.commit()
    await emails.send(jobs, emails.verification(user.email, user.name, token))
    return user


async def create_user(session: AsyncSession, user: User) -> User:
    """Add a new user with their own copy of the default labels (not committed)."""
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
    return user


async def google_sign_in(session: AsyncSession, google_user: GoogleUser) -> User:
    """The account for this Google identity: already linked, linked now by its verified
    email, or created. Google only counts when it vouches for the email."""
    if not google_user.email_verified:
        raise AuthenticationError("Google did not confirm this email")
    user = await users.get_active_by_google_id(session, google_user.sub)
    if user is None:
        user = await users.get_active_by_email(session, google_user.email)
        if user is not None:
            if user.google_id is not None or user.is_demo:
                raise ConflictError("This email is linked to another Google account")
            user.google_id = google_user.sub
            user.email_verified_at = user.email_verified_at or datetime.now(UTC)
            user.avatar_url = user.avatar_url or google_user.picture
            log.info("google.linked", user_id=str(user.id))
        else:
            user = await create_user(
                session,
                User(
                    email=google_user.email,
                    name=google_user.name,
                    google_id=google_user.sub,
                    avatar_url=google_user.picture,
                    email_verified_at=datetime.now(UTC),
                ),
            )
            log.info("google.signed_up", user_id=str(user.id))
    await session.flush()
    return user


async def login(session: AsyncSession, email: str, password: str) -> IssuedTokens | TwoFactorTicket:
    user = await users.get_active_by_email(session, email)
    if not security.verify_password(password, user.password_hash if user else None):
        raise AuthenticationError(INVALID_CREDENTIALS)
    assert user is not None
    return await start_session(session, user)


async def start_session(session: AsyncSession, user: User) -> IssuedTokens | TwoFactorTicket:
    """After the first step (password or Google): a session, or the 2FA ticket."""
    if user.two_factor_enabled:
        return TwoFactorTicket(security.create_two_factor_ticket(user.id))
    tokens, _ = await _issue(session, user.id, family_id=uuid.uuid4())
    await session.commit()
    return tokens


async def complete_two_factor(session: AsyncSession, ticket: str, code: str) -> IssuedTokens:
    user_id = security.decode_two_factor_ticket(ticket)
    user = await users.get_active_by_id(session, user_id) if user_id else None
    if user is None or not user.two_factor_enabled:
        raise AuthenticationError("The sign-in expired. Start again.")
    if not await two_factor.check(session, user, code):
        raise AuthenticationError(two_factor.INVALID_CODE)
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


async def logout_others(session: AsyncSession, user: User, raw_token: str | None) -> None:
    """End every session of the user except the one holding this refresh token."""
    current = (
        await refresh_tokens.get_by_hash_for_update(session, security.hash_refresh_token(raw_token))
        if raw_token
        else None
    )
    if current is None or current.user_id != user.id or current.revoked_at is not None:
        raise AuthenticationError(INVALID_SESSION)
    await refresh_tokens.revoke_other_families(
        session, user.id, current.family_id, datetime.now(UTC)
    )
    await session.commit()


async def change_password(
    session: AsyncSession, user: User, current_password: str, new_password: str
) -> None:
    if user.is_demo:
        raise ConflictError("Demo accounts have no password")
    if not security.verify_password(current_password, user.password_hash):
        raise AuthenticationError("Current password is incorrect")
    user.password_hash = security.hash_password(new_password)
    # End every open session on other devices.
    await refresh_tokens.revoke_all_for_user(session, user.id, datetime.now(UTC))
    await session.commit()


async def resend_verification(session: AsyncSession, user: User, jobs: JobQueue) -> None:
    if user.email_verified_at is not None:
        raise ConflictError("This email is already confirmed")
    token = await _new_token(session, user.id, TokenPurpose.VERIFY_EMAIL)
    await session.commit()
    await emails.send(jobs, emails.verification(user.email, user.name, token))


async def verify_email(session: AsyncSession, raw_token: str) -> None:
    now = datetime.now(UTC)
    user = await _spend_token(session, raw_token, TokenPurpose.VERIFY_EMAIL, now)
    if user.email_verified_at is None:
        user.email_verified_at = now
    await session.commit()


async def request_password_reset(session: AsyncSession, email: str, jobs: JobQueue) -> None:
    """Email a reset link. Unknown emails get no email and the same answer (no leaks)."""
    user = await users.get_active_by_email(session, email)
    if user is None:
        return
    token = await _new_token(session, user.id, TokenPurpose.RESET_PASSWORD)
    await session.commit()
    await emails.send(jobs, emails.password_reset(user.email, user.name, token))


async def reset_password(session: AsyncSession, raw_token: str, new_password: str) -> None:
    now = datetime.now(UTC)
    user = await _spend_token(session, raw_token, TokenPurpose.RESET_PASSWORD, now)
    user.password_hash = security.hash_password(new_password)
    # Opening the link proves the address is theirs.
    if user.email_verified_at is None:
        user.email_verified_at = now
    await refresh_tokens.revoke_all_for_user(session, user.id, now)
    await session.commit()


async def delete_account(
    session: AsyncSession,
    user: User,
    jobs: JobQueue,
    *,
    password: str | None,
    confirm_email: str | None,
) -> None:
    """Erase the account for good (GDPR): every record now, the stored files right after.

    The one exception to soft delete: nothing of the user is kept, audit log included.
    Accounts with a password confirm with it; Google-only and demo accounts type their email.
    """
    if user.has_password:
        if not security.verify_password(password or "", user.password_hash):
            raise AuthenticationError("Password is incorrect")
    elif (confirm_email or "").strip().lower() != user.email:
        raise AuthenticationError("Type your email to confirm")
    user_id, email, name, is_demo = user.id, user.email, user.name, user.is_demo
    await erase_user(session, user_id)
    await session.commit()
    await jobs.enqueue(DELETE_USER_FILES, user_id=str(user_id))
    if not is_demo:
        await emails.send(jobs, emails.account_deleted(email, name))
    log.info("account.deleted", user_id=str(user_id))


async def erase_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Every record of the user (not committed; their stored files are the caller's job)."""
    # Entries first: they hold RESTRICT keys to labels and incomes; the rest cascades.
    await session.execute(delete(Entry).where(Entry.user_id == user_id))
    await session.execute(delete(User).where(User.id == user_id))


async def _new_token(session: AsyncSession, user_id: uuid.UUID, purpose: TokenPurpose) -> str:
    """Create a one-time token, replacing the open ones of the same purpose."""
    now = datetime.now(UTC)
    await user_tokens.use_all(session, user_id, purpose, now)
    raw = security.generate_email_token()
    session.add(
        UserToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=security.hash_email_token(raw),
            expires_at=now + TOKEN_LIFETIME[purpose],
        )
    )
    await session.flush()
    return raw


async def _spend_token(
    session: AsyncSession, raw_token: str, purpose: TokenPurpose, now: datetime
) -> User:
    token = await user_tokens.get_usable_for_update(
        session, security.hash_email_token(raw_token), purpose, now
    )
    user = await users.get_active_by_id(session, token.user_id) if token else None
    if token is None or user is None:
        raise InvalidTokenError()
    token.used_at = now
    return user


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
