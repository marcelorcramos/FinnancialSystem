import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import LabelKind, MovementType
from app.models import Entry, Income, Label, Month, User


async def _user_with_month_and_label(session: AsyncSession) -> tuple[User, Month, Label]:
    user = User(email=f"{uuid.uuid4()}@example.com", name="Alice", password_hash="x")
    session.add(user)
    await session.flush()
    month = Month(user_id=user.id, year=2026, month=10)
    label = Label(user_id=user.id, name="Food", kind=LabelKind.EXPENSE, color="#FFB74D", icon="x")
    session.add_all([month, label])
    await session.flush()
    return user, month, label


def _entry(user: User, month: Month, label: Label, **overrides: object) -> Entry:
    values: dict[str, object] = {
        "user_id": user.id,
        "month_id": month.id,
        "label_id": label.id,
        "amount": Decimal("10.00"),
        "movement_type": MovementType.ALLOCATION,
        "occurred_on": date(2026, 10, 1),
    }
    values.update(overrides)
    return Entry(**values)


async def _assert_rejected(session: AsyncSession, obj: object) -> None:
    session.add(obj)
    with pytest.raises(IntegrityError):
        await session.flush()
    await session.rollback()


async def test_amount_must_be_positive(session: AsyncSession) -> None:
    user, month, label = await _user_with_month_and_label(session)
    await _assert_rejected(session, _entry(user, month, label, amount=Decimal("0.00")))


async def test_transfer_leg_requires_transfer_id(session: AsyncSession) -> None:
    user, month, label = await _user_with_month_and_label(session)
    await _assert_rejected(
        session, _entry(user, month, label, movement_type=MovementType.TRANSFER_OUT)
    )


async def test_allocation_cannot_have_transfer_id(session: AsyncSession) -> None:
    user, month, label = await _user_with_month_and_label(session)
    await _assert_rejected(session, _entry(user, month, label, transfer_id=uuid.uuid4()))


async def test_addition_requires_income(session: AsyncSession) -> None:
    user, month, label = await _user_with_month_and_label(session)
    await _assert_rejected(session, _entry(user, month, label, movement_type=MovementType.ADDITION))


async def test_addition_with_income_is_accepted(session: AsyncSession) -> None:
    user, month, label = await _user_with_month_and_label(session)
    income = Income(
        user_id=user.id,
        month_id=month.id,
        source="Extra",
        amount=Decimal("12.00"),
        received_on=date(2026, 10, 5),
    )
    session.add(income)
    await session.flush()
    session.add(
        _entry(user, month, label, movement_type=MovementType.ADDITION, income_id=income.id)
    )
    await session.flush()


async def test_only_one_allocation_per_label_and_month(session: AsyncSession) -> None:
    user, month, label = await _user_with_month_and_label(session)
    session.add(_entry(user, month, label))
    await session.flush()
    await _assert_rejected(session, _entry(user, month, label))


async def test_transfer_has_at_most_one_leg_of_each_type(session: AsyncSession) -> None:
    user, month, label = await _user_with_month_and_label(session)
    transfer_id = uuid.uuid4()
    leg = {"movement_type": MovementType.TRANSFER_OUT, "transfer_id": transfer_id}
    session.add(_entry(user, month, label, **leg))
    await session.flush()
    await _assert_rejected(session, _entry(user, month, label, **leg))


async def test_one_active_month_per_year_month(session: AsyncSession) -> None:
    user, month, _ = await _user_with_month_and_label(session)
    await _assert_rejected(session, Month(user_id=user.id, year=month.year, month=month.month))


async def test_soft_deleted_month_frees_its_year_month(session: AsyncSession) -> None:
    user, month, _ = await _user_with_month_and_label(session)
    month.deleted_at = month.created_at
    await session.flush()
    session.add(Month(user_id=user.id, year=month.year, month=month.month))
    await session.flush()


async def test_month_number_must_be_valid(session: AsyncSession) -> None:
    user, _, _ = await _user_with_month_and_label(session)
    await _assert_rejected(session, Month(user_id=user.id, year=2026, month=13))


async def test_label_kind_is_restricted(session: AsyncSession) -> None:
    from sqlalchemy import text

    user, _, _ = await _user_with_month_and_label(session)
    with pytest.raises(IntegrityError):
        await session.execute(
            text(
                "INSERT INTO labels (id, user_id, name, kind, color, icon) "
                "VALUES (:id, :user_id, 'X', 'gift', '#000000', 'x')"
            ),
            {"id": uuid.uuid4(), "user_id": user.id},
        )
