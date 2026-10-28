from datetime import date

import pytest

from app.domain.periods import MonthKey, Period, months_back, months_between, months_in

TODAY = date(2026, 10, 26)


def keys(*pairs: tuple[int, int]) -> list[MonthKey]:
    return [MonthKey(y, m) for y, m in pairs]


def test_last_month_is_the_current_month() -> None:
    assert months_in(Period.LAST_MONTH, TODAY) == keys((2026, 10))


def test_last_6_months_includes_current_month() -> None:
    assert months_in(Period.LAST_6_MONTHS, TODAY) == keys(
        (2026, 5), (2026, 6), (2026, 7), (2026, 8), (2026, 9), (2026, 10)
    )


def test_last_12_months_crosses_the_year() -> None:
    months = months_in(Period.LAST_12_MONTHS, TODAY)
    assert months is not None
    assert (months[0], months[-1], len(months)) == (MonthKey(2025, 11), MonthKey(2026, 10), 12)


def test_window_in_january_reaches_back_into_last_year() -> None:
    assert months_in(Period.LAST_6_MONTHS, date(2027, 1, 3)) == keys(
        (2026, 8), (2026, 9), (2026, 10), (2026, 11), (2026, 12), (2027, 1)
    )


def test_all_has_no_time_limit() -> None:
    assert months_in(Period.ALL, TODAY) is None


def test_month_key_order_index_and_text() -> None:
    assert MonthKey(2025, 12) < MonthKey(2026, 1)
    assert MonthKey.from_index(MonthKey(2026, 3).index) == MonthKey(2026, 3)
    assert str(MonthKey(2026, 3)) == "2026-03"


def test_months_back_requires_a_positive_count() -> None:
    with pytest.raises(ValueError):
        months_back(MonthKey(2026, 1), 0)


def test_months_between_includes_both_ends_and_crosses_the_year() -> None:
    assert months_between(MonthKey(2025, 11), MonthKey(2026, 2)) == keys(
        (2025, 11), (2025, 12), (2026, 1), (2026, 2)
    )
    assert months_between(MonthKey(2026, 3), MonthKey(2026, 3)) == keys((2026, 3))
