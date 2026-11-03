import uuid
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.domain.enums import AuditAction
from app.models import AuditLog, OutboxEvent

_EXCLUDED = {"password_hash"}


def snapshot(obj: Base) -> dict[str, Any]:
    """Column state of a model, serializable to JSONB."""
    state = inspect(obj)
    data: dict[str, Any] = {}
    for column in state.mapper.column_attrs:
        if column.key in _EXCLUDED or column.key in state.unloaded:
            continue
        value = getattr(obj, column.key)
        data[column.key] = value if isinstance(value, bool | int | str | None) else str(value)
    return data


def record(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    entity: str,
    entity_id: uuid.UUID,
    action: AuditAction,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    """Audit a write and emit its domain event (outbox), both in the caller's transaction."""
    session.add(
        AuditLog(
            user_id=user_id,
            entity=entity,
            entity_id=entity_id,
            action=action,
            before=before,
            after=after,
        )
    )
    month_id = (after or before or {}).get("month_id")
    session.add(
        OutboxEvent(
            type=f"{entity}.{action.value}",
            payload={
                "user_id": str(user_id),
                "entity": entity,
                "entity_id": str(entity_id),
                "action": action.value,
                "month_id": str(month_id) if month_id else None,
            },
        )
    )


def log(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    entity: str,
    obj: Base,
    action: AuditAction,
    before: dict[str, Any] | None = None,
) -> None:
    """Record a write; the "after" state is taken from the object (except on DELETE)."""
    after = None if action is AuditAction.DELETE else snapshot(obj)
    entity_id = getattr(obj, "id")  # noqa: B009  (every audited model has an id)
    record(
        session,
        user_id=user_id,
        entity=entity,
        entity_id=entity_id,
        action=action,
        before=before,
        after=after,
    )
