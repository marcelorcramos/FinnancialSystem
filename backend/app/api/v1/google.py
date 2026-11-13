"""Sign in with Google: the browser goes to Google and comes back to the callback,
which starts the session (refresh cookie) and returns to the app."""

from typing import Annotated
from urllib.parse import urlencode

import structlog
from fastapi import APIRouter, Cookie, Depends, Request
from fastapi.responses import RedirectResponse

from app.api.deps import RateLimiterDep, SessionDep, client_ip
from app.api.v1.auth import set_refresh_cookie
from app.core import security
from app.core.config import settings
from app.core.google import GoogleError, GoogleOAuth, get_google
from app.core.rate_limit import LOGIN_PER_IP
from app.domain.errors import DomainError, NotFoundError
from app.schemas.auth import Providers
from app.services import auth
from app.services.auth import TwoFactorTicket

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

STATE_COOKIE = "google_oauth"
STATE_COOKIE_PATH = "/api/v1/auth/google"

GoogleDep = Annotated[GoogleOAuth | None, Depends(get_google)]


def _app_url(path: str, **params: str) -> str:
    query = f"?{urlencode(params)}" if params else ""
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}{query}"


def _fail(reason: str) -> RedirectResponse:
    log.info("google.failed", reason=reason)
    response = RedirectResponse(_app_url("/auth/login", error="google"), status_code=303)
    response.delete_cookie(STATE_COOKIE, path=STATE_COOKIE_PATH)
    return response


@router.get("/providers")
async def providers(google: GoogleDep) -> Providers:
    """Which sign-in options this server offers (the Google button shows only when set up)."""
    return Providers(google=google is not None)


@router.get("/google/login")
async def google_login(
    google: GoogleDep, request: Request, limiter: RateLimiterDep
) -> RedirectResponse:
    """Send the browser to Google's account chooser."""
    if google is None:
        raise NotFoundError("Sign-in with Google is not set up")
    await limiter.hit(LOGIN_PER_IP, client_ip(request))
    try:
        authorization = await google.authorize()
    except Exception as error:
        log.warning("google.unreachable", error=str(error))
        return _fail("unreachable")
    response = RedirectResponse(authorization.url, status_code=303)
    response.set_cookie(
        STATE_COOKIE,
        security.encode_google_state(
            authorization.state, authorization.nonce, authorization.code_verifier
        ),
        max_age=security.GOOGLE_STATE_SECONDS,
        path=STATE_COOKIE_PATH,
        httponly=True,
        secure=not settings.is_dev,
        samesite="lax",  # sent on the top-level redirect back from Google
    )
    return response


@router.get("/google/callback")
async def google_callback(
    google: GoogleDep,
    session: SessionDep,
    request: Request,
    limiter: RateLimiterDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    google_oauth: Annotated[str | None, Cookie(alias=STATE_COOKIE)] = None,
) -> RedirectResponse:
    """Google sends the browser here. Success goes to the app's /auth/google page, which
    picks up the session; with 2FA on, to the code page with a ticket."""
    if google is None:
        raise NotFoundError("Sign-in with Google is not set up")
    await limiter.hit(LOGIN_PER_IP, client_ip(request))
    if error or not code or not state:
        return _fail(error or "missing code")
    remembered = security.decode_google_state(google_oauth) if google_oauth else None
    if remembered is None or remembered.get("state") != state:
        return _fail("state mismatch")
    try:
        google_user = await google.exchange(code, remembered["verifier"], remembered["nonce"])
        user = await auth.google_sign_in(session, google_user)
        result = await auth.start_session(session, user)
    except GoogleError as problem:
        await session.rollback()
        return _fail(str(problem))
    except DomainError as problem:
        await session.rollback()
        return _fail(problem.code)
    await session.commit()

    if isinstance(result, TwoFactorTicket):
        # The ticket rides in the fragment, which never reaches a server log.
        target = _app_url("/auth/two-factor") + f"#ticket={result.ticket}"
        response = RedirectResponse(target, status_code=303)
    else:
        response = RedirectResponse(_app_url("/auth/google"), status_code=303)
        set_refresh_cookie(response, result.refresh_token)
    response.delete_cookie(STATE_COOKIE, path=STATE_COOKIE_PATH)
    return response
