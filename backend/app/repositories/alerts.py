import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AlertLevel
from app.models import Alert, Label, Month


async def create_once(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit_id: uuid.UUID,
    label_id: uuid.UUID,
    month_id: uuid.UUID,
    level: AlertLevel,
    limit_amount: Decimal,
    total: Decimal,
) -> uuid.UUID | None:
    """Insert the alert unless that level was already raised; returns the new id."""
    stmt = (
        insert(Alert)
        .values(
            id=uuid.uuid4(),
            user_id=user_id,
            limit_id=limit_id,
            label_id=label_id,
            month_id=month_id,
            level=level,
            limit_amount=limit_amount,
            total=total,
            # The real time, not the transaction's start: keeps alerts in the order raised.
            created_at=datetime.now(UTC),
        )
        .on_conflict_do_nothing(index_elements=["label_id", "month_id", "level"])
        .returning(Alert.id)
    )
    return await session.scalar(stmt)


async def list_with_details(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    ids: list[uuid.UUID] | None = None,
    unseen: bool = False,
    limit: int = 50,
) -> list[tuple[Alert, Label, Month]]:
    stmt = (
        select(Alert, Label, Month)
        .join(Label, Label.id == Alert.label_id)
        .join(Month, Month.id == Alert.month_id)
        .where(Alert.user_id == user_id, Month.deleted_at.is_(None))
        .order_by(Alert.created_at.desc())
        .limit(limit)
    )
    if ids is not None:
        stmt = stmt.where(Alert.id.in_(ids))
    if unseen:
        stmt = stmt.where(Alert.seen_at.is_(None))
    return [(row[0], row[1], row[2]) for row in await session.execute(stmt)]


async def mark_seen(
    session: AsyncSession, user_id: uuid.UUID, now: datetime, alert_id: uuid.UUID | None = None
) -> int:
    stmt = update(Alert).where(Alert.user_id == user_id, Alert.seen_at.is_(None))
    if alert_id is not None:
        stmt = stmt.where(Alert.id == alert_id)
    result = await session.execute(stmt.values(seen_at=now))
    return int(getattr(result, "rowcount", 0) or 0)
