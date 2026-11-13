"""Optional TOTP two-factor sign-in (Phase 10): set up, confirm, check and turn off.

Turning it on, off and getting new recovery codes all need a current code, so
someone holding only a signed-in session cannot change it. Demo accounts cannot
use it.
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import two_factor as totp
from app.domain.errors import AuthenticationError, ConflictError
from app.models import User
from app.repositories import recovery_codes
from app.schemas.two_factor import RecoveryCodes, TwoFactorSetup, TwoFactorStatus

INVALID_CODE = "That code is not valid"


async def status(session: AsyncSession, user: User) -> TwoFactorStatus:
    left = await recovery_codes.count_unused(session, user.id) if user.two_factor_enabled else 0
    return TwoFactorStatus(enabled=user.two_factor_enabled, recovery_codes_left=left)


async def start_setup(session: AsyncSession, user: User) -> TwoFactorSetup:
    """A new secret to scan; it only counts once a code from it is confirmed."""
    if user.is_demo:
        raise ConflictError("Demo accounts cannot use two-factor sign-in")
    if user.two_factor_enabled:
        raise ConflictError("Two-factor sign-in is already on")
    secret = totp.new_secret()
    user.totp_secret = totp.encrypt(secret)
    user.totp_last_step = None
    await session.commit()
    uri = totp.provisioning_uri(secret, user.email)
    return TwoFactorSetup(secret=secret, otpauth_uri=uri, qr_svg=totp.qr_svg(uri))


async def enable(session: AsyncSession, user: User, code: str) -> RecoveryCodes:
    if user.two_factor_enabled:
        raise ConflictError("Two-factor sign-in is already on")
    secret = totp.decrypt(user.totp_secret) if user.totp_secret else None
    if secret is None:
        raise ConflictError("Start the setup first")
    accepted = totp.verify(secret, code, user.totp_last_step, datetime.now(UTC))
    if accepted is None:
        raise AuthenticationError(INVALID_CODE)
    user.totp_last_step = accepted.step
    user.totp_enabled_at = datetime.now(UTC)
    codes = await _new_recovery_codes(session, user)
    await session.commit()
    return codes


async def disable(session: AsyncSession, user: User, code: str) -> None:
    if not user.two_factor_enabled:
        raise ConflictError("Two-factor sign-in is already off")
    await _require_code(session, user, code)
    user.totp_secret = None
    user.totp_enabled_at = None
    user.totp_last_step = None
    await recovery_codes.delete_all(session, user.id)
    await session.commit()


async def regenerate_recovery_codes(session: AsyncSession, user: User, code: str) -> RecoveryCodes:
    if not user.two_factor_enabled:
        raise ConflictError("Two-factor sign-in is off")
    await _require_code(session, user, code)
    codes = await _new_recovery_codes(session, user)
    await session.commit()
    return codes


async def check(session: AsyncSession, user: User, code: str) -> bool:
    """True for a fresh TOTP code or an unused recovery code (which is then spent).

    The caller commits, so the step or the recovery code is saved as used.
    """
    now = datetime.now(UTC)
    secret = totp.decrypt(user.totp_secret) if user.totp_secret else None
    if secret is not None:
        accepted = totp.verify(secret, code, user.totp_last_step, now)
        if accepted is not None:
            user.totp_last_step = accepted.step
            return True
    return await recovery_codes.use(session, user.id, totp.hash_recovery_code(code), now)


async def _require_code(session: AsyncSession, user: User, code: str) -> None:
    if not await check(session, user, code):
        raise AuthenticationError(INVALID_CODE)


async def _new_recovery_codes(session: AsyncSession, user: User) -> RecoveryCodes:
    codes = totp.new_recovery_codes()
    await recovery_codes.replace_all(session, user.id, [totp.hash_recovery_code(c) for c in codes])
    return RecoveryCodes(codes=codes)
