"""Aggregations for reports. Only active entries of active months count."""

import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import MovementType
from app.domain.filters import CategoryFilter
from app.domain.periods import MonthKey
from app.models import Entry, Label, Month


def _scoped[S: Select[*tuple[Any, ...]]](
    stmt: S,
    user_id: uuid.UUID,
    months: Sequence[MonthKey] | None,
    categories: CategoryFilter,
) -> S:
    stmt = (
        stmt.join(Month, Month.id == Entry.month_id)
        .join(Label, Label.id == Entry.label_id)
        .where(
            Entry.user_id == user_id,
            Entry.deleted_at.is_(None),
            Month.deleted_at.is_(None),
        )
    )
    if months is not None:
        index = Month.year * 12 + Month.month - 1
        stmt = stmt.where(index.between(months[0].index, months[-1].index))
    if not categories.is_empty:
        stmt = stmt.where(or_(Label.id.in_(categories.label_ids), Label.kind.in_(categories.kinds)))
    return stmt


async def totals_by_label_and_type(
    session: AsyncSession,
    user_id: uuid.UUID,
    months: Sequence[MonthKey] | None,
    categories: CategoryFilter,
) -> list[tuple[uuid.UUID, MovementType, Decimal]]:
    """Sum of amounts per (label, movement type) in the window."""
    stmt = select(Entry.label_id, Entry.movement_type, func.sum(Entry.amount)).group_by(
        Entry.label_id, Entry.movement_type
    )
    result = await session.execute(_scoped(stmt, user_id, months, categories))
    return [(row[0], row[1], row[2]) for row in result]


async def labels_for_report(
    session: AsyncSession, user_id: uuid.UUID, label_ids: set[uuid.UUID]
) -> list[Label]:
    """The user's labels by id, including archived or deleted ones that still have history."""
    if not label_ids:
        return []
    stmt = select(Label).where(Label.user_id == user_id, Label.id.in_(label_ids))
    return list(await session.scalars(stmt))


async def missing_label_ids(
    session: AsyncSession, user_id: uuid.UUID, label_ids: frozenset[uuid.UUID]
) -> set[uuid.UUID]:
    """Ids in the filter that are not labels of this user."""
    if not label_ids:
        return set()
    stmt = select(Label.id).where(Label.user_id == user_id, Label.id.in_(label_ids))
    return set(label_ids) - set(await session.scalars(stmt))


async def usable_labels_matching(
    session: AsyncSession, user_id: uuid.UUID, categories: CategoryFilter
) -> list[Label]:
    """Active, unarchived labels selected by the filter (listed even with no money)."""
    stmt = select(Label).where(
        Label.user_id == user_id, Label.deleted_at.is_(None), Label.archived_at.is_(None)
    )
    if not categories.is_empty:
        stmt = stmt.where(or_(Label.id.in_(categories.label_ids), Label.kind.in_(categories.kinds)))
    return list(await session.scalars(stmt))
