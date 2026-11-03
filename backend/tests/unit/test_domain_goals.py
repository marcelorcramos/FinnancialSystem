from datetime import date
from decimal import Decimal

from app.domain.goals import (
    average_monthly_expenses,
    emergency_fund_months,
    emergency_fund_target,
    months_left,
    pace,
    percent_of,
)
from app.domain.periods import MonthKey

D = Decimal
TODAY = date(2026, 11, 3)


def test_percent_of_the_target() -> None:
    assert percent_of(D("1250"), D("5000")) == D("25.00")
    assert percent_of(D("5200"), D("5000")) == D("104.00")
    assert percent_of(D("-50"), D("5000")) == D("0.00")
    assert percent_of(D("10"), D("0")) == D("0.00")


def test_months_left_count_the_current_and_the_deadline_month() -> None:
    assert months_left(TODAY, date(2026, 11, 30)) == 1
    assert months_left(TODAY, date(2027, 3, 31)) == 5  # Nov, Dec, Jan, Feb, Mar
    assert months_left(TODAY, date(2026, 10, 31)) == 0


def test_what_to_save_each_month_rounds_up_to_the_cent() -> None:
    p = pace(D("1000"), D("2000"), TODAY, date(2027, 1, 15))  # 3 months: 333.333...
    assert (p.remaining, p.months_left, p.per_month) == (D("1000"), 3, D("333.34"))
    assert p.per_month * 3 >= p.remaining
    assert (p.reached, p.overdue) == (False, False)
    assert p.days_left == 73


def test_a_reached_goal_needs_nothing_more() -> None:
    p = pace(D("2100"), D("2000"), TODAY, date(2027, 1, 15))
    assert (p.reached, p.remaining, p.per_month, p.percent) == (True, D("0"), D("0"), D("105.00"))


def test_a_passed_deadline_is_overdue_with_no_monthly_amount() -> None:
    p = pace(D("500"), D("2000"), TODAY, date(2026, 9, 30))
    assert (p.overdue, p.months_left, p.days_left, p.per_month) == (True, 0, 0, None)


def test_without_a_deadline_there_is_no_pace() -> None:
    p = pace(D("500"), D("2000"), TODAY, None)
    assert (p.months_left, p.days_left, p.per_month, p.overdue) == (None, None, None, False)


def test_emergency_fund_target_from_average_expenses() -> None:
    average = average_monthly_expenses([D("1100"), D("1300"), D("1200.01")])
    assert average == D("1200.00")
    assert emergency_fund_target(average, 6) == D("7200.00")
    assert average_monthly_expenses([]) is None
    assert emergency_fund_target(None, 6) is None


def test_emergency_fund_averages_the_six_complete_months() -> None:
    assert emergency_fund_months(TODAY) == [
        MonthKey(2026, 5),
        MonthKey(2026, 6),
        MonthKey(2026, 7),
        MonthKey(2026, 8),
        MonthKey(2026, 9),
        MonthKey(2026, 10),
    ]
    assert emergency_fund_months(date(2026, 2, 1))[-1] == MonthKey(2026, 1)
