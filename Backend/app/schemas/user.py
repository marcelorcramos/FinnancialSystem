import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class UserBase(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=125)
    name: str = Field(min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return v.lower().strip()


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: str
    currency: str
    timezone: str
    language: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str 

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower().strip()

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"