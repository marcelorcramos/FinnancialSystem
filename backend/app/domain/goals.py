"""Goal calculations (Phase 8): progress, pace and the emergency fund target.

All money is Decimal; "per month" amounts round up to the cent, so following the
advice always reaches the target.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from app.domain.money import CENT, ZERO
from app.domain.periods import MonthKey

EMERGENCY_FUND_WINDOW = 6  # complete months averaged for the emergency fund


@dataclass(frozen=True, slots=True)
class Pace:
    progress: Decimal
    remaining: Decimal  # never negative
    percent: Decimal  # 2 decimals, may pass 100
    months_left: int | None  # months still to save in, the current one included
    days_left: int | None
    per_month: Decimal | None  # what to save each month to finish on time
    reached: bool
    overdue: bool  # deadline passed without reaching the target


def percent_of(progress: Decimal, target: Decimal) -> Decimal:
    if target <= 0:
        return ZERO
    return (max(progress, ZERO) / target * 100).quantize(CENT, rounding=ROUND_HALF_UP)


def months_left(today: date, deadline: date) -> int:
    """Months to save in from today's month to the deadline's month, both included."""
    return max(MonthKey.of(deadline).index - MonthKey.of(today).index + 1, 0)


def pace(progress: Decimal, target: Decimal, today: date, deadline: date | None) -> Pace:
    remaining = max(target - progress, ZERO)
    reached = target > 0 and progress >= target
    if deadline is None:
        left = days = None
        per_month = None
        overdue = False
    else:
        left = months_left(today, deadline) if deadline >= today else 0
        days = max((deadline - today).days, 0)
        overdue = deadline < today and not reached
        per_month = (
            None
            if reached or left == 0
            else (remaining / left).quantize(CENT, rounding=ROUND_CEILING)
        )
    return Pace(
        progress=progress,
        remaining=remaining,
        percent=percent_of(progress, target),
        months_left=left,
        days_left=days,
        per_month=ZERO if reached else per_month,
        reached=reached,
        overdue=overdue,
    )


def average_monthly_expenses(month_totals: Sequence[Decimal]) -> Decimal | None:
    """Average of the given months' expense totals; None without any month."""
    if not month_totals:
        return None
    return (sum(month_totals, ZERO) / len(month_totals)).quantize(CENT, rounding=ROUND_HALF_UP)


def emergency_fund_target(average_expenses: Decimal | None, months: int) -> Decimal | None:
    """N months of average expenses (e.g. 6 x €1,200 = €7,200)."""
    if average_expenses is None:
        return None
    return (average_expenses * months).quantize(CENT, rounding=ROUND_HALF_UP)


def emergency_fund_months(today: date) -> list[MonthKey]:
    """The complete months averaged for the emergency fund: the 6 before the current one."""
    previous = MonthKey.from_index(MonthKey.of(today).index - 1)
    return [
        MonthKey.from_index(i)
        for i in range(previous.index - EMERGENCY_FUND_WINDOW + 1, previous.index + 1)
    ]
