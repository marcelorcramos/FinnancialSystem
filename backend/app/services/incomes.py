"""Month incomes. Those created by an `addition` are managed only through their entry."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import AuditAction
from app.domain.errors import ConflictError, NotFoundError
from app.domain.rules import ensure_date_in_month, ensure_month_open
from app.models import Income, Month, User
from app.repositories import incomes as incomes_repo
from app.repositories import months as months_repo
from app.schemas.month import IncomeCreate, IncomeRead, IncomeUpdate
from app.services import audit, months

ENTITY = "income"


async def list_for_month(
    session: AsyncSession, user: User, month_id: uuid.UUID
) -> list[IncomeRead]:
    month = await months.get(session, user, month_id)
    from_additions = await incomes_repo.ids_backing_additions(session, month.id)
    return [
        IncomeRead.model_validate(i).model_copy(update={"from_addition": i.id in from_additions})
        for i in await incomes_repo.list_for_month(session, month.id)
    ]


async def create(
    session: AsyncSession, user: User, month_id: uuid.UUID, data: IncomeCreate
) -> Income:
    month = await months.get_open(session, user, month_id)
    ensure_date_in_month(data.received_on, month.year, month.month)
    income = Income(user_id=user.id, month_id=month.id, **data.model_dump())
    session.add(income)
    await session.flush()
    audit.log(session, user_id=user.id, entity=ENTITY, obj=income, action=AuditAction.CREATE)
    await session.commit()
    return income


async def update(
    session: AsyncSession, user: User, income_id: uuid.UUID, data: IncomeUpdate
) -> Income:
    income, month = await _get_editable(session, user, income_id)
    changes = data.model_dump(exclude_unset=True)
    for required in ("source", "amount", "received_on"):
        if required in changes and changes[required] is None:
            del changes[required]
    if "received_on" in changes:
        ensure_date_in_month(changes["received_on"], month.year, month.month)
    before = audit.snapshot(income)
    for field, value in changes.items():
        setattr(income, field, value)
    await session.flush()
    audit.log(
        session,
        user_id=user.id,
        entity=ENTITY,
        obj=income,
        action=AuditAction.UPDATE,
        before=before,
    )
    await session.commit()
    return income


async def delete(session: AsyncSession, user: User, income_id: uuid.UUID) -> None:
    income, _ = await _get_editable(session, user, income_id)
    before = audit.snapshot(income)
    income.deleted_at = datetime.now(UTC)
    await session.flush()
    audit.log(
        session,
        user_id=user.id,
        entity=ENTITY,
        obj=income,
        action=AuditAction.DELETE,
        before=before,
    )
    await session.commit()


async def restore(session: AsyncSession, user: User, income_id: uuid.UUID) -> Income:
    income = await incomes_repo.get_for_user(session, user.id, income_id, deleted=True)
    if income is None:
        raise NotFoundError("Income not found")
    await _ensure_writable(session, user, income)
    income.deleted_at = None
    await session.flush()
    audit.log(session, user_id=user.id, entity=ENTITY, obj=income, action=AuditAction.RESTORE)
    await session.commit()
    return income


async def _get_editable(
    session: AsyncSession, user: User, income_id: uuid.UUID
) -> tuple[Income, Month]:
    income = await incomes_repo.get_for_user(session, user.id, income_id)
    if income is None:
        raise NotFoundError("Income not found")
    return income, await _ensure_writable(session, user, income)


async def _ensure_writable(session: AsyncSession, user: User, income: Income) -> Month:
    month = await months_repo.get_for_user(session, user.id, income.month_id)
    if month is None:
        raise NotFoundError("Income not found")
    ensure_month_open(month.closed_at)
    if income.id in await incomes_repo.ids_backing_additions(session, month.id):
        raise ConflictError("This income came from 'add money': edit it through its entry")
    return month
