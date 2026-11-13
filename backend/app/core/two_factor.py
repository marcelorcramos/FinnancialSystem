"""TOTP (RFC 6238) for two-factor sign-in, and the recovery codes that back it up.

Secrets are encrypted at rest with a key derived from SECRET_KEY, so a database
dump alone cannot generate codes. A code is accepted once: the last accepted
30-second step is remembered.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime

import pyotp
import segno
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

ISSUER = "FinnancialSystem"
RECOVERY_CODES = 10
# One step before and after the current one, for clocks that drift a little.
VALID_WINDOW = 1


def _fernet() -> Fernet:
    key = hashlib.sha256(b"totp:" + settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def new_secret() -> str:
    return pyotp.random_base32()


def encrypt(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None


def provisioning_uri(secret: str, email: str) -> str:
    """The otpauth:// link authenticator apps read from the QR code."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=ISSUER)


def qr_data_uri(uri: str) -> str:
    """The QR code as a standalone SVG image (data: URI), safe to show in an <img>."""
    return str(segno.make(uri, error="m").svg_data_uri(scale=4, border=2))


@dataclass(frozen=True, slots=True)
class Accepted:
    step: int


def verify(secret: str, code: str, last_step: int | None, now: datetime) -> Accepted | None:
    """The step of a valid code that was not used before, or None."""
    code = code.replace(" ", "")
    if not (len(code) == 6 and code.isdigit()):
        return None
    totp = pyotp.TOTP(secret)
    current = totp.timecode(now)
    for step in range(current - VALID_WINDOW, current + VALID_WINDOW + 1):
        if last_step is not None and step <= last_step:
            continue
        if secrets.compare_digest(totp.generate_otp(step), code):
            return Accepted(step)
    return None


def new_recovery_codes() -> list[str]:
    """Codes like "k7q2-m9xd": easy to copy, about 50 bits each."""
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    codes = []
    for _ in range(RECOVERY_CODES):
        raw = "".join(secrets.choice(alphabet) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def hash_recovery_code(code: str) -> str:
    normalized = code.strip().lower().replace(" ", "").replace("-", "")
    return hashlib.sha256(normalized.encode()).hexdigest()
