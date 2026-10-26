import uuid
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.domain.enums import AuditAction
from app.models import AuditLog

_EXCLUDED = {"password_hash"}


def snapshot(obj: Base) -> dict[str, Any]:
    """Estado das colunas de um modelo, serializável para JSONB."""
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
