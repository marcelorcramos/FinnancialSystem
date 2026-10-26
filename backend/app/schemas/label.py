import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.enums import LabelKind

LabelName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]
IconName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class LabelCreate(BaseModel):
    name: LabelName
    kind: LabelKind
    color: HexColor
    icon: IconName


class LabelUpdate(BaseModel):
    name: LabelName | None = None
    kind: LabelKind | None = Field(
        default=None, description="Mudar o tipo altera retroativamente os relatórios."
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
