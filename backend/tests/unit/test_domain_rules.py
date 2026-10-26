import uuid
from datetime import UTC, date, datetime

import pytest

from app.domain import rules
from app.domain.errors import MonthClosedError, ValidationError


def test_closed_month_rejects_writes() -> None:
    with pytest.raises(MonthClosedError):
        rules.ensure_month_open(datetime.now(UTC))


def test_open_month_accepts_writes() -> None:
    rules.ensure_month_open(None)


def test_date_must_belong_to_the_month() -> None:
    rules.ensure_date_in_month(date(2026, 10, 31), 2026, 10)
    with pytest.raises(ValidationError):
        rules.ensure_date_in_month(date(2026, 11, 1), 2026, 10)
    with pytest.raises(ValidationError):
        rules.ensure_date_in_month(date(2025, 10, 15), 2026, 10)


def test_transfer_labels_must_differ() -> None:
    label = uuid.uuid4()
    with pytest.raises(ValidationError):
        rules.ensure_distinct_labels(label, label)


def test_archived_label_cannot_receive_entries() -> None:
    with pytest.raises(ValidationError):
        rules.ensure_label_usable(datetime.now(UTC))


@pytest.mark.parametrize(
    ("year", "month", "expected"), [(2026, 10, (2026, 9)), (2026, 1, (2025, 12))]
)
def test_previous_month(year: int, month: int, expected: tuple[int, int]) -> None:
    assert rules.previous_month(year, month) == expected


def test_semester() -> None:
    assert [rules.semester_of(m) for m in (1, 6, 7, 12)] == [1, 1, 2, 2]
