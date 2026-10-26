"""Section 2.2 invariants of ARCHITECTURE.md, tested without database or HTTP."""

import uuid
from decimal import Decimal

import pytest

from app.domain import ledger
from app.domain.enums import LabelKind, MovementType
from app.domain.errors import ValidationError
from app.domain.ledger import Movement
from app.domain.money import money, positive_money
from app.domain.transfers import plan_transfer

FOOD, SAVINGS, INVEST = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
D = Decimal


def mv(label: uuid.UUID, kind: MovementType, amount: str) -> Movement:
    return Movement(label, kind, D(amount))


def test_food_200_plus_12_shows_212() -> None:
    movements = [
        mv(FOOD, MovementType.ALLOCATION, "200.00"),
        mv(FOOD, MovementType.ADDITION, "12.00"),
    ]
    assert ledger.label_totals(movements)[FOOD] == D("212.00")


def test_food_plus_12_from_another_label_also_shows_212() -> None:
    plan = plan_transfer(SAVINGS, FOOD, "12.00")
    movements = [mv(FOOD, MovementType.ALLOCATION, "200.00"), plan.out_leg, plan.in_leg]
    totals = ledger.label_totals(movements)
    assert totals[FOOD] == D("212.00")
    assert totals[SAVINGS] == D("-12.00")


def test_label_total_formula() -> None:
    movements = [
        mv(FOOD, MovementType.ALLOCATION, "100.00"),
        mv(FOOD, MovementType.ADDITION, "20.00"),
        mv(FOOD, MovementType.TRANSFER_IN, "30.00"),
        mv(FOOD, MovementType.TRANSFER_OUT, "15.50"),
    ]
    breakdown = ledger.breakdown_by_label(movements)[FOOD]
    assert (breakdown.allocation, breakdown.addition) == (D("100.00"), D("20.00"))
    assert (breakdown.transfer_in, breakdown.transfer_out) == (D("30.00"), D("15.50"))
    assert breakdown.total == D("134.50")


def test_month_total_is_invariant_to_transfers() -> None:
    base = [
        mv(FOOD, MovementType.ALLOCATION, "200.00"),
        mv(SAVINGS, MovementType.ALLOCATION, "300.00"),
    ]
    before = ledger.month_total(base)
    t1 = plan_transfer(SAVINGS, FOOD, "50.00")
    t2 = plan_transfer(FOOD, INVEST, "70.25")
    after = ledger.month_total([*base, t1.out_leg, t1.in_leg, t2.out_leg, t2.in_leg])
    assert before == after == D("500.00")


def test_transfer_legs_sum_to_zero_in_month() -> None:
    plan = plan_transfer(SAVINGS, FOOD, "33.33")
    legs = [plan.out_leg, plan.in_leg]
    ins = sum(m.amount for m in legs if m.movement_type is MovementType.TRANSFER_IN)
    outs = sum(m.amount for m in legs if m.movement_type is MovementType.TRANSFER_OUT)
    assert ins == outs


def test_transfer_is_always_a_pair_with_same_amount_and_distinct_labels() -> None:
    plan = plan_transfer(SAVINGS, FOOD, "10")
    assert plan.out_leg.movement_type is MovementType.TRANSFER_OUT
    assert plan.in_leg.movement_type is MovementType.TRANSFER_IN
    assert plan.out_leg.amount == plan.in_leg.amount == D("10.00")
    assert plan.out_leg.label_id != plan.in_leg.label_id


def test_transfer_to_same_label_is_rejected() -> None:
    with pytest.raises(ValidationError):
        plan_transfer(FOOD, FOOD, "10.00")


@pytest.mark.parametrize("amount", ["0", "-5.00"])
def test_transfer_requires_positive_amount(amount: str) -> None:
    with pytest.raises(ValidationError):
        plan_transfer(SAVINGS, FOOD, amount)


def test_unallocated_is_income_minus_allocations() -> None:
    movements = [
        mv(FOOD, MovementType.ALLOCATION, "200.00"),
        mv(SAVINGS, MovementType.ALLOCATION, "300.00"),
    ]
    assert ledger.unallocated(D("1000.00"), movements) == D("500.00")


def test_unallocated_is_unchanged_by_addition() -> None:
    """An addition raises income and allocated money by the same amount."""
    income, movements = D("1000.00"), [mv(FOOD, MovementType.ALLOCATION, "200.00")]
    before = ledger.unallocated(income, movements)
    after = ledger.unallocated(
        income + D("50.00"), [*movements, mv(FOOD, MovementType.ADDITION, "50.00")]
    )
    assert before == after == D("800.00")


def test_unallocated_is_unchanged_by_transfers() -> None:
    movements = [mv(FOOD, MovementType.ALLOCATION, "200.00")]
    plan = plan_transfer(FOOD, SAVINGS, "80.00")
    assert ledger.unallocated(D("1000.00"), movements) == ledger.unallocated(
        D("1000.00"), [*movements, plan.out_leg, plan.in_leg]
    )


def test_saving_label_can_go_negative_in_a_month() -> None:
    plan = plan_transfer(SAVINGS, FOOD, "150.00")
    assert ledger.label_totals([plan.out_leg, plan.in_leg])[SAVINGS] == D("-150.00")


def test_totals_by_kind() -> None:
    totals = {FOOD: D("212.00"), SAVINGS: D("100.00"), INVEST: D("50.00")}
    kinds = {
        FOOD: LabelKind.EXPENSE,
        SAVINGS: LabelKind.SAVING,
        INVEST: LabelKind.INVESTMENT,
    }
    assert ledger.totals_by_kind(totals, kinds) == {
        LabelKind.EXPENSE: D("212.00"),
        LabelKind.SAVING: D("100.00"),
        LabelKind.INVESTMENT: D("50.00"),
    }


def test_money_never_accepts_float() -> None:
    with pytest.raises(TypeError):
        money(0.1)  # type: ignore[arg-type]


def test_money_rounds_half_up_to_cents() -> None:
    assert money("10.005") == D("10.01")
    assert money("10.004") == D("10.00")
    assert money(7) == D("7.00")


@pytest.mark.parametrize("value", ["abc", "1e20"])
def test_money_rejects_invalid_or_huge(value: str) -> None:
    with pytest.raises(ValidationError):
        money(value)


def test_positive_money_rejects_zero() -> None:
    with pytest.raises(ValidationError):
        positive_money("0.004")
