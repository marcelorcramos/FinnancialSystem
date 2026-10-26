"""Casos de uso das etiquetas (secção 2.1)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction, MovementType
from app.domain.errors import ConflictError, NotFoundError, ValidationError
from app.domain.rules import ensure_label_usable
from app.models import Entry, Label, User
from app.repositories import entries as entries_repo
from app.repositories import labels as labels_repo
from app.schemas.label import LabelCreate, LabelUpdate
from app.services import audit

ENTITY = "label"


async def get(session: AsyncSession, user: User, label_id: uuid.UUID) -> Label:
    label = await labels_repo.get_for_user(session, user.id, label_id)
    if label is None:
        raise NotFoundError("Etiqueta não encontrada")
    return label


async def get_usable(session: AsyncSession, user: User, label_id: uuid.UUID) -> Label:
    label = await get(session, user, label_id)
    ensure_label_usable(label.archived_at)
    return label


async def create(session: AsyncSession, user: User, data: LabelCreate) -> Label:
    await _ensure_name_free(session, user, data.name)
    label = Label(user_id=user.id, **data.model_dump())
    session.add(label)
    await session.flush()
    _audit(session, user, label, AuditAction.CREATE, after=audit.snapshot(label))
    await session.commit()
    return label


async def update(
    session: AsyncSession, user: User, label_id: uuid.UUID, data: LabelUpdate
) -> Label:
    label = await get(session, user, label_id)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if "name" in changes:
        await _ensure_name_free(session, user, changes["name"], exclude_id=label.id)
    before = audit.snapshot(label)
    for field, value in changes.items():
        setattr(label, field, value)
    await session.flush()
    _audit(session, user, label, AuditAction.UPDATE, before=before, after=audit.snapshot(label))
    await session.commit()
    return label


async def set_archived(
    session: AsyncSession, user: User, label_id: uuid.UUID, *, archived: bool
) -> Label:
    label = await get(session, user, label_id)
    before = audit.snapshot(label)
    label.archived_at = datetime.now(UTC) if archived else None
    await session.flush()
    _audit(session, user, label, AuditAction.UPDATE, before=before, after=audit.snapshot(label))
    await session.commit()
    return label


async def delete(
    session: AsyncSession, user: User, label_id: uuid.UUID, reassign_to: uuid.UUID | None
) -> None:
    """Etiqueta com entradas não se elimina sem reatribuir as entradas a outra etiqueta."""
    label = await get(session, user, label_id)
    if await labels_repo.count_active_entries(session, label.id):
        if reassign_to is None:
            raise ConflictError(
                "A etiqueta tem entradas: arquiva-a ou reatribui as entradas a outra etiqueta"
            )
        target = await get_usable(session, user, reassign_to)
        if target.id == label.id:
            raise ValidationError("Escolhe outra etiqueta para receber as entradas")
        await _reassign_entries(session, user, label, target)

    before = audit.snapshot(label)
    label.deleted_at = datetime.now(UTC)
    await session.flush()
    _audit(session, user, label, AuditAction.DELETE, before=before)
    await session.commit()


async def restore(session: AsyncSession, user: User, label_id: uuid.UUID) -> Label:
    label = await labels_repo.get_for_user(session, user.id, label_id, deleted=True)
    if label is None:
        raise NotFoundError("Etiqueta não encontrada")
    await _ensure_name_free(session, user, label.name)
    label.deleted_at = None
    await session.flush()
    _audit(session, user, label, AuditAction.RESTORE, after=audit.snapshot(label))
    await session.commit()
    return label


async def _reassign_entries(
    session: AsyncSession, user: User, source: Label, target: Label
) -> None:
    if await entries_repo.closed_months_with_label_entries(session, source.id):
        raise ConflictError(
            "A etiqueta tem entradas em meses fechados: reabre esses meses para reatribuir"
        )
    now = datetime.now(UTC)
    for entry in await entries_repo.list_active_for_label(session, source.id):
        before = audit.snapshot(entry)
        if entry.movement_type is MovementType.ALLOCATION:
            existing = await entries_repo.active_allocation(session, entry.month_id, target.id)
            if existing is not None:
                # O destino já tem distribuição neste mês: somam-se as duas.
                existing_before = audit.snapshot(existing)
                existing.amount += entry.amount
                entry.deleted_at = now
                _audit_entry(session, user, existing, AuditAction.UPDATE, existing_before)
                _audit_entry(session, user, entry, AuditAction.DELETE, before)
                continue
        elif entry.transfer_id is not None:
            legs = await entries_repo.transfer_legs(session, entry.transfer_id)
            if any(leg.label_id == target.id for leg in legs if leg.id != entry.id):
                # Transferência entre origem e destino: passaria a ser da etiqueta para ela
                # própria e o efeito líquido é zero, por isso desaparece.
                for leg in legs:
                    leg_before = audit.snapshot(leg)
                    leg.deleted_at = now
                    _audit_entry(session, user, leg, AuditAction.DELETE, leg_before)
                continue
        entry.label_id = target.id
        _audit_entry(session, user, entry, AuditAction.UPDATE, before)
    await session.flush()


async def _ensure_name_free(
    session: AsyncSession, user: User, name: str, *, exclude_id: uuid.UUID | None = None
) -> None:
    if await labels_repo.name_taken(session, user.id, name, exclude_id=exclude_id):
        raise ConflictError(f"Já existe uma etiqueta chamada {name!r}")


def _audit(
    session: AsyncSession,
    user: User,
    label: Label,
    action: AuditAction,
    *,
    before: dict[str, object] | None = None,
    after: dict[str, object] | None = None,
) -> None:
    audit.record(
        session,
        user_id=user.id,
        entity=ENTITY,
        entity_id=label.id,
        action=action,
        before=before,
        after=after,
    )


def _audit_entry(
    session: AsyncSession, user: User, entry: Entry, action: AuditAction, before: dict[str, object]
) -> None:
    after = None if action is AuditAction.DELETE else audit.snapshot(entry)
    audit.record(
        session,
        user_id=user.id,
        entity="entry",
        entity_id=entry.id,
        action=action,
        before=before,
        after=after,
    )
