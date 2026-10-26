"""Valores monetários: sempre Decimal com 2 casas. Nunca float."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.domain.errors import ValidationError

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
MAX_AMOUNT = Decimal("999999999999.99")  # limite de NUMERIC(14,2)


def money(value: Decimal | int | str) -> Decimal:
    if isinstance(value, float):
        raise TypeError("Valores monetários não podem ser float; usar Decimal ou str")
    try:
        result = Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValidationError(f"Valor monetário inválido: {value!r}") from exc
    if abs(result) > MAX_AMOUNT:
        raise ValidationError("Valor monetário demasiado grande")
    return result


def positive_money(value: Decimal | int | str) -> Decimal:
    result = money(value)
    if result <= ZERO:
        raise ValidationError("O valor tem de ser maior que zero")
    return result
