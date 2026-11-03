from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, RateLimiterDep, SessionDep, client_ip
from app.core.config import settings
from app.core.rate_limit import LOGIN_PER_EMAIL, LOGIN_PER_IP, REFRESH_PER_IP, REGISTER_PER_IP
from app.schemas.auth import AccessToken
from app.schemas.user import LoginRequest, UserCreate, UserRead
from app.services import auth
from app.services.auth import IssuedTokens

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


def _respond_with_tokens(response: Response, tokens: IssuedTokens) -> AccessToken:
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=not settings.is_dev,
        samesite="lax",
    )
    return AccessToken(access_token=tokens.access_token, expires_in=tokens.expires_in)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate, session: SessionDep, request: Request, limiter: RateLimiterDep
) -> UserRead:
    await limiter.hit(REGISTER_PER_IP, client_ip(request))
    user = await auth.register(session, data)
    return UserRead.model_validate(user)


@router.post("/login")
async def login(
    data: LoginRequest,
    session: SessionDep,
    response: Response,
    request: Request,
    limiter: RateLimiterDep,
) -> AccessToken:
    await limiter.hit(LOGIN_PER_IP, client_ip(request))
    await limiter.hit(LOGIN_PER_EMAIL, data.email)
    tokens = await auth.login(session, data.email, data.password)
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
    tokens = await auth.login(session, form.username.strip().lower(), form.password)
    return AccessToken(access_token=tokens.access_token, expires_in=tokens.expires_in)


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
