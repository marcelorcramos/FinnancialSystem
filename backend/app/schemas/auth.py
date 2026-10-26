from pydantic import BaseModel


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105  (tipo OAuth2, não é um segredo)
    expires_in: int
