from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Enum, Numeric

# Money: always NUMERIC(14,2) in the database and Decimal in Python.
Money = Numeric(14, 2, asdecimal=True)
MONEY_ZERO = Decimal("0.00")


def str_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """VARCHAR + CHECK instead of a native PostgreSQL ENUM (easier to evolve)."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
    )
