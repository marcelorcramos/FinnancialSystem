"""What a demo account ("Try it") starts with: six months of a believable budget.

Plain data, so it can be read and tested on its own; services/demo.py writes it
through the normal services, with every rule applied.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.domain.periods import MonthKey, months_back

MONTHS = 6
SALARY = Decimal("2400.00")
LIFETIME_HOURS = 24


@dataclass(frozen=True, slots=True)
class Movement:
    """A transfer (from_label set) or money from outside the app (from_label None)."""

    to_label: str
    amount: Decimal
    day: int
    note: str
    from_label: str | None = None


@dataclass(frozen=True, slots=True)
class MonthPlan:
    month: MonthKey
    allocations: dict[str, Decimal]
    movements: list[Movement] = field(default_factory=list)
    closed: bool = True


def _money(value: str | int) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def plan(today: date) -> list[MonthPlan]:
    """The six months up to and including today's, oldest first; all but the last closed."""
    months = months_back(MonthKey.of(today), MONTHS)
    plans = []
    for i, month in enumerate(months):
        current = i == MONTHS - 1
        allocations = {
            "Housing": _money(850),
            "Food": _money(300 + (i % 3) * 15),
            "Electricity": _money(48 + (i * 7) % 20),
            "Water": _money(26 + (i % 2) * 4),
            "Transport": _money(60),
            "Phone & Internet": _money(35),
            "Subscriptions": _money(25),
            "Health": _money(40),
            "Savings": _money(400),
            "Emergency Fund": _money(200),
            "Investments": _money(300),
        }
        movements = []
        if i % 2 == 1:
            movements.append(Movement("Food", _money(35), 18, "Dinner with friends", "Savings"))
        if i == 2:
            movements.append(Movement("Investments", _money(300), 20, "Year-end bonus"))
        if i == 3:
            movements.append(
                Movement("Investments", _money(20), 28, "Left over from groceries", "Food")
            )
        if i == 4:
            movements.append(Movement("Savings", _money(120), 12, "Sold my old bike"))
        if current:
            # Only what already happened: nothing dated after today.
            movements = [m for m in movements if m.day <= today.day]
        plans.append(MonthPlan(month, allocations, movements, closed=not current))
    return plans


def total_allocated(month_plan: MonthPlan) -> Decimal:
    return sum(month_plan.allocations.values(), Decimal("0.00"))
