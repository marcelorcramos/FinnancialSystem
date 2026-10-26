"""Regras de validação do domínio. Funções puras: recebem valores, levantam DomainError."""

import uuid
from datetime import date, datetime

from app.domain.errors import MonthClosedError, ValidationError


def ensure_month_open(closed_at: datetime | None) -> None:
    if closed_at is not None:
        raise MonthClosedError()


def ensure_date_in_month(occurred_on: date, year: int, month: int) -> None:
    if (occurred_on.year, occurred_on.month) != (year, month):
        raise ValidationError(f"A data tem de pertencer ao mês {month:02d}/{year}")


def ensure_distinct_labels(from_label_id: uuid.UUID, to_label_id: uuid.UUID) -> None:
    if from_label_id == to_label_id:
        raise ValidationError("Uma transferência tem de ser entre etiquetas diferentes")


def ensure_label_usable(archived_at: datetime | None) -> None:
    if archived_at is not None:
        raise ValidationError("A etiqueta está arquivada; desarquiva-a para a usar")


def previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def semester_of(month: int) -> int:
    return 1 if month <= 6 else 2
