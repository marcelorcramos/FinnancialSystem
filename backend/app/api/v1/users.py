from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, JobsDep, RateLimiterDep, SessionDep
from app.api.v1.auth import REFRESH_COOKIE, REFRESH_COOKIE_PATH
from app.core.rate_limit import DELETE_PER_USER, TWO_FACTOR_PER_USER, VERIFY_PER_USER
from app.schemas.two_factor import RecoveryCodes, TwoFactorCode, TwoFactorSetup, TwoFactorStatus
from app.schemas.user import AccountDeletion, PasswordChange, UserRead, UserUpdate
from app.services import auth, two_factor

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me")
async def update_me(data: UserUpdate, user: CurrentUser, session: SessionDep) -> UserRead:
    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(user, field, value)
    await session.commit()
    return UserRead.model_validate(user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(data: PasswordChange, user: CurrentUser, session: SessionDep) -> None:
    await auth.change_password(session, user, data.current_password, data.new_password)


@router.post("/me/verification-email", status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(
    user: CurrentUser, session: SessionDep, limiter: RateLimiterDep, jobs: JobsDep
) -> None:
    """Send the confirmation link again (the previous links stop working)."""
    await limiter.hit(VERIFY_PER_USER, str(user.id))
    await auth.resend_verification(session, user, jobs)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    data: AccountDeletion,
    user: CurrentUser,
    session: SessionDep,
    response: Response,
    limiter: RateLimiterDep,
    jobs: JobsDep,
) -> None:
    """Delete the account and all of its data for good, after checking the password
    (or, for accounts without one, the typed email)."""
    await limiter.hit(DELETE_PER_USER, str(user.id))
    await auth.delete_account(
        session, user, jobs, password=data.password, confirm_email=data.confirm_email
    )
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.get("/me/2fa")
async def two_factor_status(user: CurrentUser, session: SessionDep) -> TwoFactorStatus:
    return await two_factor.status(session, user)


@router.post("/me/2fa/setup")
async def two_factor_setup(user: CurrentUser, session: SessionDep) -> TwoFactorSetup:
    """A new secret and its QR code; nothing changes until a code is confirmed."""
    return await two_factor.start_setup(session, user)


@router.post("/me/2fa/enable")
async def two_factor_enable(
    data: TwoFactorCode, user: CurrentUser, session: SessionDep, limiter: RateLimiterDep
) -> RecoveryCodes:
    """Turn 2FA on with a code from the app; returns the recovery codes (shown once)."""
    await limiter.hit(TWO_FACTOR_PER_USER, str(user.id))
    return await two_factor.enable(session, user, data.code)


@router.post("/me/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def two_factor_disable(
    data: TwoFactorCode, user: CurrentUser, session: SessionDep, limiter: RateLimiterDep
) -> None:
    await limiter.hit(TWO_FACTOR_PER_USER, str(user.id))
    await two_factor.disable(session, user, data.code)


@router.post("/me/2fa/recovery-codes")
async def two_factor_recovery_codes(
    data: TwoFactorCode, user: CurrentUser, session: SessionDep, limiter: RateLimiterDep
) -> RecoveryCodes:
    """New recovery codes; the old ones stop working."""
    await limiter.hit(TWO_FACTOR_PER_USER, str(user.id))
    return await two_factor.regenerate_recovery_codes(session, user, data.code)
