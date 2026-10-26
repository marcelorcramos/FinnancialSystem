import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.domain.enums import MovementType
from app.domain.ledger import Movement
from app.domain.money import positive_money
from app.domain.rules import ensure_distinct_labels


@dataclass(frozen=True, slots=True)
class TransferPlan:
    """As duas pernas de uma transferência: mesmo valor, etiquetas diferentes."""

    out_leg: Movement
    in_leg: Movement


def plan_transfer(
    from_label_id: uuid.UUID, to_label_id: uuid.UUID, amount: Decimal | str
) -> TransferPlan:
    ensure_distinct_labels(from_label_id, to_label_id)
    value = positive_money(amount)
    return TransferPlan(
        out_leg=Movement(from_label_id, MovementType.TRANSFER_OUT, value),
        in_leg=Movement(to_label_id, MovementType.TRANSFER_IN, value),
    )
