from datetime import date
from decimal import Decimal

from app.domain import demo
from app.domain.periods import MonthKey


def test_six_months_up_to_today_with_only_the_current_one_open() -> None:
    plans = demo.plan(date(2026, 11, 13))
    assert [str(p.month) for p in plans] == [
        "2026-06",
        "2026-07",
        "2026-08",
        "2026-09",
        "2026-10",
        "2026-11",
    ]
    assert [p.closed for p in plans] == [True] * 5 + [False]


def test_each_month_distributes_less_than_the_salary() -> None:
    for month_plan in demo.plan(date(2026, 11, 13)):
        assert Decimal("2000") < demo.total_allocated(month_plan) < demo.SALARY


def test_transfers_and_extra_income_vary_across_months() -> None:
    plans = demo.plan(date(2026, 3, 28))
    transfers = [m for p in plans for m in p.movements if m.from_label]
    additions = [m for p in plans for m in p.movements if not m.from_label]
    assert len(transfers) >= 3 and len(additions) == 2
    assert all(m.from_label != m.to_label for m in transfers)


def test_nothing_in_the_current_month_is_dated_after_today() -> None:
    early = demo.plan(date(2026, 1, 5))[-1]  # month index 5 would have a transfer on the 18th
    assert early.month == MonthKey(2026, 1)
    assert all(m.day <= 5 for m in early.movements)
    late = demo.plan(date(2026, 1, 25))[-1]
    assert any(m.day == 18 for m in late.movements)
