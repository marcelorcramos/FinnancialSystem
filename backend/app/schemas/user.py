import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Password = Field(min_length=8, max_length=128)
SupportedCurrency = Literal["EUR"]  # só EUR no MVP (docs/DECISIONS.md)
SupportedLocale = Literal["pt-PT", "en"]


def _normalize_email(value: str) -> str:
    return value.strip().lower()


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Password
    name: str = Field(min_length=1, max_length=100)

    _email = field_validator("email")(_normalize_email)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    _email = field_validator("email")(_normalize_email)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: str
    avatar_url: str | None
    currency: str
    locale: str
    timezone: str
    email_verified_at: datetime | None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    currency: SupportedCurrency | None = None
    locale: SupportedLocale | None = None
    timezone: str | None = None

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str | None) -> str | None:
        if value is not None and value not in available_timezones():
            raise ValueError("Fuso horário desconhecido")
        return value


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Password
