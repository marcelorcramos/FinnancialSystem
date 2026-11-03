from decimal import Decimal

import pytest

from app.domain.enums import AlertLevel
from app.domain.limits import level, levels_reached, usage_percent

D = Decimal


@pytest.mark.parametrize(
    ("total", "limit", "percent"),
    [
        ("212.00", "300.00", "70.67"),
        ("0.00", "300.00", "0.00"),
        ("300.00", "300.00", "100.00"),
        ("450.00", "300.00", "150.00"),
        ("-20.00", "300.00", "0.00"),  # money moved out: nothing used
        ("0.01", "3.00", "0.33"),
    ],
)
def test_usage_percent(total: str, limit: str, percent: str) -> None:
    assert usage_percent(D(total), D(limit)) == D(percent)


def test_a_limit_is_never_zero() -> None:
    with pytest.raises(ValueError):
        usage_percent(D("10"), D("0"))


@pytest.mark.parametrize(
    ("total", "expected"),
    [
        ("239.99", None),  # 79.997%: shown as 80.00% but not yet 80%
        ("240.00", AlertLevel.WARNING),
        ("299.99", AlertLevel.WARNING),
        ("300.00", AlertLevel.EXCEEDED),
        ("900.00", AlertLevel.EXCEEDED),
    ],
)
def test_levels_at_80_and_100_percent(total: str, expected: AlertLevel | None) -> None:
    assert level(D(total), D("300.00")) is expected


def test_jumping_past_100_percent_reaches_both_levels() -> None:
    assert levels_reached(D("350"), D("300")) == [AlertLevel.WARNING, AlertLevel.EXCEEDED]
    assert levels_reached(D("250"), D("300")) == [AlertLevel.WARNING]
    assert levels_reached(D("100"), D("300")) == []
