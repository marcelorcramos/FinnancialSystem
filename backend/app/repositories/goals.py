import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Goal, Label


async def list_with_labels(session: AsyncSession, user_id: uuid.UUID) -> list[tuple[Goal, Label]]:
    stmt = (
        select(Goal, Label)
        .join(Label, Label.id == Goal.label_id)
        .where(Goal.user_id == user_id, Goal.deleted_at.is_(None))
        .order_by(Goal.created_at)
    )
    return [(row[0], row[1]) for row in await session.execute(stmt)]


async def get_for_user(
    session: AsyncSession, user_id: uuid.UUID, goal_id: uuid.UUID, *, deleted: bool = False
) -> Goal | None:
    stmt = select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
    stmt = stmt.where(Goal.deleted_at.is_not(None) if deleted else Goal.deleted_at.is_(None))
    return await session.scalar(stmt.with_for_update())


async def active_for_label(
    session: AsyncSession, user_id: uuid.UUID, label_id: uuid.UUID
) -> Goal | None:
    stmt = select(Goal).where(
        Goal.user_id == user_id,
        Goal.label_id == label_id,
        Goal.deleted_at.is_(None),
        Goal.completed_at.is_(None),
    )
    return await session.scalar(stmt)
