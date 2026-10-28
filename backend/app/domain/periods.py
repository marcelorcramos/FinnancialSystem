"""Report time windows (see "Report filters" in docs/DECISIONS.md).

Windows are rolling and counted back from the current month, which is included:
last month = the current month, last 6 months = the current month and the 5 before it.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class Period(StrEnum):
    LAST_MONTH = "last_month"
    LAST_6_MONTHS = "last_6_months"
    LAST_12_MONTHS = "last_12_months"
    ALL = "all"


WINDOW_SIZE: dict[Period, int] = {
    Period.LAST_MONTH: 1,
    Period.LAST_6_MONTHS: 6,
    Period.LAST_12_MONTHS: 12,
}


@dataclass(frozen=True, order=True, slots=True)
class MonthKey:
    year: int
    month: int

    @classmethod
    def of(cls, day: date) -> "MonthKey":
        return cls(day.year, day.month)

    @property
    def index(self) -> int:
        """Months since year 0, so consecutive months differ by one."""
        return self.year * 12 + self.month - 1

    @classmethod
    def from_index(cls, index: int) -> "MonthKey":
        return cls(index // 12, index % 12 + 1)

    def __str__(self) -> str:
        return f"{self.year}-{self.month:02d}"


def months_back(end: MonthKey, count: int) -> list[MonthKey]:
    """`count` consecutive months ending at `end` (inclusive), oldest first."""
    if count < 1:
        raise ValueError("count must be at least 1")
    return [MonthKey.from_index(i) for i in range(end.index - count + 1, end.index + 1)]


def months_between(first: MonthKey, last: MonthKey) -> list[MonthKey]:
    """Every month from `first` to `last` (inclusive), oldest first."""
    return months_back(last, last.index - first.index + 1)


def months_in(period: Period, today: date) -> list[MonthKey] | None:
    """The months covered by `period`, oldest first; None means no time limit."""
    if period is Period.ALL:
        return None
    return months_back(MonthKey.of(today), WINDOW_SIZE[period])
