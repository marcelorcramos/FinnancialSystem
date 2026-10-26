"""Month totals computed from movements (section 2.2 of ARCHITECTURE.md).

Label total = allocation + addition + transfer_in - transfer_out.
Unallocated = month income - (allocation + addition).
"""

import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.enums import LabelKind, MovementType
from app.domain.money import ZERO


@dataclass(frozen=True, slots=True)
class Movement:
    label_id: uuid.UUID
    movement_type: MovementType
    amount: Decimal  # always positive; the sign comes from the type


@dataclass(slots=True)
class LabelBreakdown:
    """A label total split by origin ("base + adjustments")."""

    allocation: Decimal = field(default=ZERO)
    addition: Decimal = field(default=ZERO)
    transfer_in: Decimal = field(default=ZERO)
    transfer_out: Decimal = field(default=ZERO)

    @property
    def total(self) -> Decimal:
        return self.allocation + self.addition + self.transfer_in - self.transfer_out

    def add(self, movement: Movement) -> None:
        name = movement.movement_type.value
        setattr(self, name, getattr(self, name) + movement.amount)


def signed_amount(movement: Movement) -> Decimal:
    if movement.movement_type is MovementType.TRANSFER_OUT:
        return -movement.amount
    return movement.amount


def breakdown_by_label(movements: Iterable[Movement]) -> dict[uuid.UUID, LabelBreakdown]:
    result: dict[uuid.UUID, LabelBreakdown] = defaultdict(LabelBreakdown)
    for movement in movements:
        result[movement.label_id].add(movement)
    return dict(result)


def label_totals(movements: Iterable[Movement]) -> dict[uuid.UUID, Decimal]:
    return {label: b.total for label, b in breakdown_by_label(movements).items()}


def month_total(movements: Iterable[Movement]) -> Decimal:
    """Sum of all labels. Transfers cancel out, so they do not change it."""
    return sum((signed_amount(m) for m in movements), ZERO)


def distributed(movements: Iterable[Movement]) -> Decimal:
    return sum(
        (
            m.amount
            for m in movements
            if m.movement_type in (MovementType.ALLOCATION, MovementType.ADDITION)
        ),
        ZERO,
    )


def unallocated(income_total: Decimal, movements: Iterable[Movement]) -> Decimal:
    return income_total - distributed(movements)


def totals_by_kind(
    totals: Mapping[uuid.UUID, Decimal], kinds: Mapping[uuid.UUID, LabelKind]
) -> dict[LabelKind, Decimal]:
    result = dict.fromkeys(LabelKind, ZERO)
    for label_id, total in totals.items():
        result[kinds[label_id]] += total
    return result
