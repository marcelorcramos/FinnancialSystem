import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.domain.enums import LabelKind

LabelName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
# Accepts any case and stores uppercase, so "#ab47bc" and "#AB47BC" are the same color.
HexColor = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^#[0-9A-Fa-f]{6}$"),
    AfterValidator(str.upper),
]
IconName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class LabelCreate(BaseModel):
    name: LabelName
    kind: LabelKind
    color: HexColor
    icon: IconName


class LabelUpdate(BaseModel):
    name: LabelName | None = None
    kind: LabelKind | None = Field(
        default=None, description="Changing the kind retroactively changes reports."
    )
    color: HexColor | None = None
    icon: IconName | None = None


class LabelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    kind: LabelKind
    color: str
    icon: str
    is_default: bool
    archived_at: datetime | None


class ColorSuggestions(BaseModel):
    colors: list[str] = Field(description="Colors not used by any of the user's labels")
