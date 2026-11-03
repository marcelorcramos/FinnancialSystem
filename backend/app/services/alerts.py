"""Alerts: limits reached in a month (Phase 8).

The limits consumer calls `raise_alerts` after entries or limits change. Each
level (warning at 80%, exceeded at 100%) is raised once per label and month.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import limits as rules
from app.domain.errors import NotFoundError
from app.models import Alert, Label, Month, User
from app.repositories import alerts as alerts_repo
from app.repositories import months as months_repo
from app.schemas.alert import AlertRead
from app.services import limits


async def raise_alerts(session: AsyncSession, user: User, month_id: uuid.UUID) -> list[uuid.UUID]:
    """Create the alerts the month's limits now reach; returns only the new ones."""
    created = []
    for row in await limits.month_status(session, user, month_id):
        for level in rules.levels_reached(row.total, row.limit):
            alert_id = await alerts_repo.create_once(
                session,
                user_id=user.id,
                limit_id=row.limit_id,
                label_id=row.label_id,
                month_id=month_id,
                level=level,
                limit_amount=row.limit,
                total=row.total,
            )
            if alert_id is not None:
                created.append(alert_id)
    return created


async def months_to_check(
    session: AsyncSession, user: User, month_id: uuid.UUID | None
) -> list[uuid.UUID]:
    """The month an event touched; a default limit applies to every open month."""
    if month_id is not None:
        month = await months_repo.get_for_user(session, user.id, month_id)
        return [month.id] if month is not None else []
    return [
        m.id for m in await months_repo.list_for_user(session, user.id, None) if not m.closed_at
    ]


async def list_alerts(session: AsyncSession, user: User, *, unseen: bool) -> list[AlertRead]:
    rows = await alerts_repo.list_with_details(session, user.id, unseen=unseen)
    return [to_read(*row) for row in rows]


async def get_many(session: AsyncSession, user: User, ids: list[uuid.UUID]) -> list[AlertRead]:
    rows = await alerts_repo.list_with_details(session, user.id, ids=ids)
    return [to_read(*row) for row in rows]


async def mark_seen(session: AsyncSession, user: User, alert_id: uuid.UUID | None = None) -> None:
    changed = await alerts_repo.mark_seen(session, user.id, datetime.now(UTC), alert_id)
    # Nothing changed: unknown, someone else's (both 404) or already seen (fine).
    if (
        alert_id is not None
        and changed == 0
        and not await alerts_repo.list_with_details(session, user.id, ids=[alert_id])
    ):
        raise NotFoundError("Alert not found")
    await session.commit()


def to_read(alert: Alert, label: Label, month: Month) -> AlertRead:
    return AlertRead(
        id=alert.id,
        level=alert.level,
        label_id=label.id,
        label_name=label.name,
        color=label.color,
        month_id=month.id,
        year=month.year,
        month=month.month,
        limit_amount=alert.limit_amount,
        total=alert.total,
        seen_at=alert.seen_at,
        created_at=alert.created_at,
    )
