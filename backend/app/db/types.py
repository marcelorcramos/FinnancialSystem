from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Enum, Numeric

# Valores monetários: sempre NUMERIC(14,2) e Decimal em Python.
Money = Numeric(14, 2, asdecimal=True)
MONEY_ZERO = Decimal("0.00")


def str_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """VARCHAR + CHECK em vez de ENUM nativo do PostgreSQL (mais fácil de evoluir)."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
    )
