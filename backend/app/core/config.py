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

    # Outgoing email (Mailpit in dev: http://localhost:8025).
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_STARTTLS: bool = False
    MAIL_FROM: str = "FinnancialSystem <no-reply@finnancial.local>"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @cached_property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT in {"dev", "test"}


settings = Settings()
