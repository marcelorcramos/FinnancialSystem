"""Google sign-in with OpenID Connect: authorization code flow with PKCE (Authlib's
OAuth client) and the ID token checked with joserfc.

The ID token is checked against Google's published keys: issuer, audience
(our client id), expiry and the nonce we sent. Endpoints come from the
discovery document, so tests point GOOGLE_DISCOVERY_URL at a fake server.
"""

import secrets
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx
from authlib.common.security import generate_token
from authlib.integrations.httpx_client import AsyncOAuth2Client
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet

from app.core.config import settings

SCOPE = "openid email profile"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")


class GoogleError(Exception):
    """Google refused, or answered with something we cannot trust."""


@dataclass(frozen=True, slots=True)
class GoogleUser:
    sub: str
    email: str
    email_verified: bool
    name: str
    picture: str | None


@dataclass(frozen=True, slots=True)
class Authorization:
    url: str
    state: str
    nonce: str
    code_verifier: str


class GoogleOAuth:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        discovery_url: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.discovery_url = discovery_url
        self.transport = transport
        self._metadata: dict[str, Any] | None = None

    def _client(self) -> AsyncOAuth2Client:
        return AsyncOAuth2Client(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope=SCOPE,
            redirect_uri=settings.google_redirect_uri,
            code_challenge_method="S256",
            transport=self.transport,
            timeout=10,
        )

    async def _get_json(self, url: str) -> Any:
        """Public documents (discovery, keys): a plain client, no OAuth token involved."""
        async with httpx.AsyncClient(transport=self.transport, timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def metadata(self) -> dict[str, Any]:
        if self._metadata is None:
            self._metadata = await self._get_json(self.discovery_url)
        return self._metadata

    async def authorize(self) -> Authorization:
        """Where to send the browser, and what to remember until it comes back."""
        meta = await self.metadata()
        state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
        verifier = generate_token(64)
        async with self._client() as client:
            url, _ = client.create_authorization_url(
                meta["authorization_endpoint"],
                state=state,
                nonce=nonce,
                code_verifier=verifier,
                prompt="select_account",
            )
        return Authorization(url, state, nonce, verifier)

    async def exchange(self, code: str, code_verifier: str, nonce: str) -> GoogleUser:
        meta = await self.metadata()
        try:
            async with self._client() as client:
                token = await client.fetch_token(
                    meta["token_endpoint"], code=code, code_verifier=code_verifier
                )
            keys = await self._get_json(meta["jwks_uri"])
        except Exception as error:
            raise GoogleError(f"token exchange failed: {type(error).__name__}") from error
        id_token = token.get("id_token")
        if not id_token:
            raise GoogleError("no id_token")
        try:
            token_data = jwt.decode(id_token, KeySet.import_key_set(keys), algorithms=["RS256"])
            jwt.JWTClaimsRegistry(
                iss={"essential": True, "values": list(ISSUERS)},
                aud={"essential": True, "value": self.client_id},
                sub={"essential": True},
                nonce={"essential": True, "value": nonce},
            ).validate(token_data.claims)
        except (JoseError, ValueError) as error:
            raise GoogleError(f"invalid id_token: {error}") from error
        claims = token_data.claims
        email = claims.get("email")
        if not email:
            raise GoogleError("no email")
        return GoogleUser(
            sub=str(claims["sub"]),
            email=str(email).strip().lower(),
            email_verified=claims.get("email_verified") is True,
            name=str(claims.get("name") or email.split("@")[0])[:100],
            picture=claims.get("picture"),
        )


@lru_cache
def get_google() -> GoogleOAuth | None:
    """The Google client, or None while sign-in with Google is not configured."""
    if not settings.google_enabled:
        return None
    assert settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET
    return GoogleOAuth(
        settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET, settings.GOOGLE_DISCOVERY_URL
    )
