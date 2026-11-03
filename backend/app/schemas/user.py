import uuid
from datetime import datetime
from typing import Annotated, Literal
from zoneinfo import available_timezones

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.domain.passwords import MAX_LENGTH, password_problems


def _strong_password(value: str) -> str:
    if problems := password_problems(value):
        raise ValueError("Password needs " + ", ".join(problems))
    return value


# The policy applies only to new passwords (sign-up and change); login accepts any password.
NewPassword = Annotated[str, Field(max_length=MAX_LENGTH), AfterValidator(_strong_password)]
SupportedCurrency = Literal["EUR"]  # EUR only in the MVP (docs/DECISIONS.md)
SupportedLocale = Literal["pt-PT", "en"]


def _normalize_email(value: str) -> str:
    return value.strip().lower()


class UserCreate(BaseModel):
    email: EmailStr
    password: NewPassword
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
    auto_new_month: bool = Field(
        description="Create each month automatically from the previous one (rent, salary...)"
    )


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    currency: SupportedCurrency | None = None
    locale: SupportedLocale | None = None
    timezone: str | None = None
    auto_new_month: bool | None = None

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str | None) -> str | None:
        if value is not None and value not in available_timezones():
            raise ValueError("Unknown time zone")
        return value


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: NewPassword
