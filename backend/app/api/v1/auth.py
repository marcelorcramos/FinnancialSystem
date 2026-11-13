from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, JobsDep, RateLimiterDep, SessionDep, client_ip
from app.core.config import settings
from app.core.rate_limit import (
    LOGIN_PER_EMAIL,
    LOGIN_PER_IP,
    REFRESH_PER_IP,
    REGISTER_PER_IP,
    RESET_PER_EMAIL,
    RESET_PER_IP,
    TWO_FACTOR_PER_USER,
)
from app.core.security import decode_two_factor_ticket
from app.domain.errors import AuthenticationError
from app.schemas.auth import AccessToken
from app.schemas.two_factor import TwoFactorLogin, TwoFactorRequired
from app.schemas.user import (
    LoginRequest,
    PasswordReset,
    PasswordResetRequest,
    TokenRequest,
    UserCreate,
    UserRead,
)
from app.services import auth
from app.services.auth import IssuedTokens, TwoFactorTicket

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=not settings.is_dev,
        samesite="lax",
    )


def _respond_with_tokens(response: Response, tokens: IssuedTokens) -> AccessToken:
    set_refresh_cookie(response, tokens.refresh_token)
    return AccessToken(access_token=tokens.access_token, expires_in=tokens.expires_in)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    session: SessionDep,
    request: Request,
    limiter: RateLimiterDep,
    jobs: JobsDep,
) -> UserRead:
    """Create the account and email a link to confirm the address (signing in does not wait)."""
    await limiter.hit(REGISTER_PER_IP, client_ip(request))
    user = await auth.register(session, data, jobs)
    return UserRead.model_validate(user)


def _respond_with_result(
    response: Response, result: IssuedTokens | TwoFactorTicket
) -> AccessToken | TwoFactorRequired:
    if isinstance(result, TwoFactorTicket):
        return TwoFactorRequired(ticket=result.ticket, expires_in=result.expires_in)
    return _respond_with_tokens(response, result)


@router.post("/login")
async def login(
    data: LoginRequest,
    session: SessionDep,
    response: Response,
    request: Request,
    limiter: RateLimiterDep,
) -> AccessToken | TwoFactorRequired:
    """Tokens, or `two_factor_required` with a ticket when the account has 2FA on."""
    await limiter.hit(LOGIN_PER_IP, client_ip(request))
    await limiter.hit(LOGIN_PER_EMAIL, data.email)
    result = await auth.login(session, data.email, data.password)
    return _respond_with_result(response, result)


@router.post("/login/2fa")
async def login_two_factor(
    data: TwoFactorLogin,
    session: SessionDep,
    response: Response,
    request: Request,
    limiter: RateLimiterDep,
) -> AccessToken:
    """Second step: the ticket from /login and a code from the app (or a recovery code)."""
    await limiter.hit(LOGIN_PER_IP, client_ip(request))
    user_id = decode_two_factor_ticket(data.ticket)
    if user_id is not None:
        await limiter.hit(TWO_FACTOR_PER_USER, str(user_id))
    tokens = await auth.complete_two_factor(session, data.ticket, data.code)
    return _respond_with_tokens(response, tokens)


@router.post("/token", include_in_schema=False)
async def token_for_docs(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
    request: Request,
    limiter: RateLimiterDep,
) -> AccessToken:
    """Form login used by the Swagger Authorize button. The username is the email."""
    await limiter.hit(LOGIN_PER_IP, client_ip(request))
    await limiter.hit(LOGIN_PER_EMAIL, form.username.strip())
    result = await auth.login(session, form.username.strip().lower(), form.password)
    if isinstance(result, TwoFactorTicket):
        raise AuthenticationError("Accounts with two-factor sign-in use the app to sign in")
    return AccessToken(access_token=result.access_token, expires_in=result.expires_in)


@router.post("/refresh")
async def refresh(
    session: SessionDep,
    response: Response,
    request: Request,
    limiter: RateLimiterDep,
    refresh_token: RefreshCookie = None,
) -> AccessToken:
    await limiter.hit(REFRESH_PER_IP, client_ip(request))
    tokens = await auth.refresh(session, refresh_token)
    return _respond_with_tokens(response, tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    session: SessionDep, response: Response, refresh_token: RefreshCookie = None
) -> None:
    await auth.logout(session, refresh_token)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.post("/logout-others", status_code=status.HTTP_204_NO_CONTENT)
async def logout_others(
    user: CurrentUser, session: SessionDep, refresh_token: RefreshCookie = None
) -> None:
    """Sign out every other device; this session (its refresh cookie) stays signed in."""
    await auth.logout_others(session, user, refresh_token)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
async def verify_email(data: TokenRequest, session: SessionDep) -> None:
    """Confirm the email with the token from the link (works without signing in)."""
    await auth.verify_email(session, data.token)


@router.post("/password-reset", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    data: PasswordResetRequest,
    session: SessionDep,
    request: Request,
    limiter: RateLimiterDep,
    jobs: JobsDep,
) -> None:
    """Email a reset link. The answer is the same whether the email has an account or not."""
    await limiter.hit(RESET_PER_IP, client_ip(request))
    await limiter.hit(RESET_PER_EMAIL, data.email)
    await auth.request_password_reset(session, data.email, jobs)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(data: PasswordReset, session: SessionDep) -> None:
    """Set a new password with the token from the link; every session ends."""
    await auth.reset_password(session, data.token, data.new_password)
