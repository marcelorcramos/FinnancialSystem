import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"  # noqa: S105  (tipo de token, não é um segredo)

_hasher = PasswordHasher()
# Usado quando o email não existe, para o login demorar o mesmo e não revelar contas.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def _verify(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError):
        return False


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _verify(_DUMMY_HASH, password)
        return False
    return _verify(password_hash, password)


def create_access_token(user_id: uuid.UUID, now: datetime | None = None) -> tuple[str, int]:
    """Devolve (token, segundos até expirar)."""
    now = now or datetime.now(UTC)
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM), expires_in


def decode_access_token(token: str) -> uuid.UUID | None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["sub", "exp", "type"]},
        )
        if payload["type"] != ACCESS_TOKEN_TYPE:
            return None
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        return None


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
