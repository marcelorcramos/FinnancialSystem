import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.common import Note, PositiveMoney


class MonthCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    note: Note | None = None
    copy_allocations: bool = Field(
        default=False, description="Copia a distribuição inicial do último mês existente"
    )
    copy_incomes: bool = Field(
        default=False, description="Copia os rendimentos do último mês existente"
    )


class MonthUpdate(BaseModel):
    note: Note | None = None


class MonthRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    year: int
    month: int
    note: str | None
    closed_at: datetime | None


Source = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class IncomeCreate(BaseModel):
    source: Source
    amount: PositiveMoney
    received_on: date
    note: Note | None = None


class IncomeUpdate(BaseModel):
    source: Source | None = None
    amount: PositiveMoney | None = None
    received_on: date | None = None
    note: Note | None = None


class IncomeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    month_id: uuid.UUID
    source: str
    amount: Decimal
    received_on: date
    note: str | None
    from_addition: bool = Field(
        default=False, description="Criado por 'acrescentar dinheiro'; edita-se pela entrada"
    )
