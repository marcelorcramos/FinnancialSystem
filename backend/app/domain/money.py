"""Money: always Decimal with 2 decimal places. Never float."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.domain.errors import ValidationError

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
MAX_AMOUNT = Decimal("999999999999.99")  # NUMERIC(14,2) limit


def money(value: Decimal | int | str) -> Decimal:
    if isinstance(value, float):
        raise TypeError("Money cannot be a float; use Decimal or str")
    try:
        result = Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValidationError(f"Invalid amount: {value!r}") from exc
    if abs(result) > MAX_AMOUNT:
        raise ValidationError("Amount is too large")
    return result


def positive_money(value: Decimal | int | str) -> Decimal:
    result = money(value)
    if result <= ZERO:
        raise ValidationError("Amount must be greater than zero")
    return result
