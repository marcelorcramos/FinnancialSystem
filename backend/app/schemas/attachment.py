import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    month_id: uuid.UUID
    entry_id: uuid.UUID | None
    filename: str
    mime: str = Field(description="image/jpeg, image/png, image/webp or application/pdf")
    size: int = Field(description="Bytes")
    created_at: datetime


class SignedUrl(BaseModel):
    url: str = Field(description="Opens the file directly from storage; works only briefly")
    expires_in: int = Field(description="Seconds")
