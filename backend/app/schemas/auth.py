from pydantic import BaseModel


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105  (OAuth2 token type, not a secret)
    expires_in: int


class Providers(BaseModel):
    google: bool
