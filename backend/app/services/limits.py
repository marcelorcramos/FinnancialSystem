"""Limits per label: a default amount and optional per-month amounts (Phase 8).

Limits only warn (alerts, see the limits consumer); they never block a write.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import limits as rules
from app.domain.enums import AuditAction
from app.domain.errors import NotFoundError
from app.models import Limit, User
from app.repositories import limits as limits_repo
from app.schemas.limit import LimitStatus
from app.services import audit, labels, months, summary

ENTITY = "limit"


async def list_limits(session: AsyncSession, user: User) -> list[Limit]:
    return await limits_repo.list_for_user(session, user.id)


async def set_limit(
    session: AsyncSession,
    user: User,
    label_id: uuid.UUID,
    amount: Decimal,
    month_id: uuid.UUID | None = None,
) -> Limit:
    """Create or change the default limit of a label, or its limit for one (open) month."""
    await labels.get(session, user, label_id)
    if month_id is not None:
        await months.get_open(session, user, month_id)
    limit = await limits_repo.find(session, user.id, label_id, month_id)
    if limit is None:
        limit = Limit(user_id=user.id, label_id=label_id, month_id=month_id, amount=amount)
        session.add(limit)
        await session.flush()
        _log(session, user, limit, AuditAction.CREATE)
    elif limit.amount != amount:
        before = audit.snapshot(limit)
        limit.amount = amount
        await session.flush()
        _log(session, user, limit, AuditAction.UPDATE, before)
    await session.commit()
    return limit


async def remove_limit(
    session: AsyncSession, user: User, label_id: uuid.UUID, month_id: uuid.UUID | None = None
) -> None:
    await labels.get(session, user, label_id)
    if month_id is not None:
        await months.get_open(session, user, month_id)
    limit = await limits_repo.find(session, user.id, label_id, month_id)
    if limit is None:
        raise NotFoundError("Limit not found")
    before = audit.snapshot(limit)
    limit.deleted_at = datetime.now(UTC)
    await session.flush()
    _log(session, user, limit, AuditAction.DELETE, before)
    await session.commit()


async def month_status(session: AsyncSession, user: User, month_id: uuid.UUID) -> list[LimitStatus]:
    """Every label with a limit in the month: its total against the limit."""
    sheet = await summary.month_summary(session, user, month_id)
    effective = await limits_repo.effective_for_month(session, user.id, month_id)
    rows = []
    for label in sheet.labels:
        limit = effective.get(label.label_id)
        if limit is None:
            continue
        rows.append(
            LimitStatus(
                label_id=label.label_id,
                name=label.name,
                color=label.color,
                limit_id=limit.id,
                limit=limit.amount,
                source="month" if limit.month_id else "default",
                total=label.total,
                remaining=limit.amount - label.total,
                percent=rules.usage_percent(label.total, limit.amount),
                level=rules.level(label.total, limit.amount),
            )
        )
    rows.sort(key=lambda r: (-r.percent, r.name.lower()))
    return rows


def _log(
    session: AsyncSession,
    user: User,
    limit: Limit,
    action: AuditAction,
    before: dict[str, object] | None = None,
) -> None:
    audit.log(session, user_id=user.id, entity=ENTITY, obj=limit, action=action, before=before)
