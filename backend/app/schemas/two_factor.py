from pydantic import BaseModel, Field


class TwoFactorSetup(BaseModel):
    secret: str = Field(description="Base32 secret, for apps that cannot scan the QR code")
    otpauth_uri: str
    qr_code: str = Field(description="The otpauth URI as a QR code: an SVG data: URI for an <img>")


class TwoFactorCode(BaseModel):
    code: str = Field(min_length=6, max_length=20, description="6-digit code or a recovery code")


class RecoveryCodes(BaseModel):
    codes: list[str] = Field(description="Shown once: each works a single time instead of a code")


class TwoFactorStatus(BaseModel):
    enabled: bool
    recovery_codes_left: int


class TwoFactorLogin(BaseModel):
    ticket: str = Field(min_length=1, max_length=1000)
    code: str = Field(min_length=6, max_length=20)


class TwoFactorRequired(BaseModel):
    """Login answer when the account has 2FA: send the ticket and a code to /auth/login/2fa."""

    two_factor_required: bool = True
    ticket: str
    expires_in: int = Field(description="Seconds left to send the code")
