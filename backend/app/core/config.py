from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "dev"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql+asyncpg://finance:finance_dev@localhost:5544/finance"
    REDIS_URL: str = "redis://localhost:6379/0"
    RABBITMQ_URL: str = "amqp://finance:finance_dev@localhost:5672/"

    SECRET_KEY: str = Field(min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    CORS_ORIGINS: str = "http://localhost:4200"
    # Links in emails point here (verify email, reset password).
    FRONTEND_URL: str = "http://localhost:4200"

    # Google sign-in (OpenID Connect). Off until both are set; see docs/GOOGLE_SIGN_IN.md.
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GOOGLE_DISCOVERY_URL: str = "https://accounts.google.com/.well-known/openid-configuration"

    # Outgoing email (Mailpit in dev: http://localhost:8025).
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_STARTTLS: bool = False
    MAIL_FROM: str = "FinnancialSystem <no-reply@finnancial.local>"

    # S3-compatible file storage (SeaweedFS in dev). Signed links use the public URL,
    # the address the browser reaches; the API talks to S3_ENDPOINT_URL.
    S3_ENDPOINT_URL: str = "http://localhost:8333"
    S3_PUBLIC_URL: str | None = None
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: str = "finance"
    S3_SECRET_KEY: str = "finance_dev_secret"  # noqa: S105  (dev default, like the DB password)
    S3_BUCKET: str = "finnancial"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @cached_property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def google_enabled(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    @property
    def google_redirect_uri(self) -> str:
        """Google returns to the app's own origin, which proxies /api, so the session
        cookie is first-party (register this exact URI in Google Cloud)."""
        return f"{self.FRONTEND_URL.rstrip('/')}/api/v1/auth/google/callback"

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT in {"dev", "test"}


settings = Settings()
