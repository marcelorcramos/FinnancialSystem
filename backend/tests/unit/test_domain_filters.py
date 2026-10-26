import uuid

from app.domain.enums import LabelKind
from app.domain.filters import CategoryFilter

FOOD, WATER, BROKER = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def test_empty_filter_selects_everything() -> None:
    everything = CategoryFilter()
    assert everything.is_empty
    assert everything.matches(FOOD, LabelKind.EXPENSE)
    assert everything.matches(BROKER, LabelKind.INVESTMENT)


def test_several_labels() -> None:
    chosen = CategoryFilter(label_ids=frozenset({FOOD, WATER}))
    assert chosen.matches(FOOD, LabelKind.EXPENSE)
    assert chosen.matches(WATER, LabelKind.EXPENSE)
    assert not chosen.matches(BROKER, LabelKind.INVESTMENT)


def test_kinds() -> None:
    investments = CategoryFilter(kinds=frozenset({LabelKind.INVESTMENT}))
    assert investments.matches(BROKER, LabelKind.INVESTMENT)
    assert not investments.matches(FOOD, LabelKind.EXPENSE)


def test_labels_and_kinds_combine_as_a_union() -> None:
    food_and_investments = CategoryFilter(
        label_ids=frozenset({FOOD}), kinds=frozenset({LabelKind.INVESTMENT})
    )
    assert food_and_investments.matches(FOOD, LabelKind.EXPENSE)
    assert food_and_investments.matches(BROKER, LabelKind.INVESTMENT)
    assert not food_and_investments.matches(WATER, LabelKind.EXPENSE)
