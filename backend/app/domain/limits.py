"""Spending limits per label and month (Phase 8).

A limit only warns: it never blocks a write. Thresholds are fixed in the MVP.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import AlertLevel

WARNING_AT = Decimal("80")
EXCEEDED_AT = Decimal("100")
_PERCENT = Decimal("0.01")


def usage_percent(total: Decimal, limit: Decimal) -> Decimal:
    """Share of the limit used, in percent with 2 decimals ("212 of 300" -> 70.67)."""
    if limit <= 0:
        raise ValueError("A limit is always greater than zero")
    used = max(total, Decimal("0")) / limit * 100
    return used.quantize(_PERCENT, rounding=ROUND_HALF_UP)


def level(total: Decimal, limit: Decimal) -> AlertLevel | None:
    """The alert level a label total reaches, or None below 80%.

    Compared exactly (not on the rounded percent): 239.99 of 300 is not yet 80%.
    """
    if limit <= 0:
        raise ValueError("A limit is always greater than zero")
    if total * 100 >= limit * EXCEEDED_AT:
        return AlertLevel.EXCEEDED
    if total * 100 >= limit * WARNING_AT:
        return AlertLevel.WARNING
    return None


def levels_reached(total: Decimal, limit: Decimal) -> list[AlertLevel]:
    """Every level at or below the current one: jumping past 100% also counts as 80%."""
    current = level(total, limit)
    if current is AlertLevel.EXCEEDED:
        return [AlertLevel.WARNING, AlertLevel.EXCEEDED]
    return [current] if current else []
