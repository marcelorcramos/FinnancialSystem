"""Goals and the emergency fund (Phase 8). Calculations live in app/domain/goals.py."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import goals as rules
from app.domain.enums import AuditAction, GoalType, LabelKind
from app.domain.errors import ConflictError, NotFoundError, ValidationError
from app.domain.filters import CategoryFilter
from app.domain.ledger import LabelBreakdown
from app.domain.money import ZERO, money
from app.domain.periods import MonthKey
from app.models import Goal, Label, User
from app.repositories import goals as goals_repo
from app.repositories import months as months_repo
from app.repositories import reports as reports_repo
from app.schemas.goal import GoalCreate, GoalList, GoalRead, GoalUpdate
from app.services import audit, labels

ENTITY = "goal"


def today_for(user: User) -> date:
    return datetime.now(ZoneInfo(user.timezone)).date()


async def label_balance(session: AsyncSession, user: User, label_id: uuid.UUID) -> Decimal:
    """Everything the label holds over all months (allocations, additions, transfers)."""
    breakdown = LabelBreakdown()
    for _, movement_type, amount in await reports_repo.totals_by_label_and_type(
        session, user.id, None, CategoryFilter(frozenset({label_id}))
    ):
        name = movement_type.value
        setattr(breakdown, name, getattr(breakdown, name) + amount)
    return breakdown.total


async def average_expenses(session: AsyncSession, user: User, today: date) -> Decimal | None:
    """Monthly average of expense labels over the 6 complete months that have a sheet."""
    window = rules.emergency_fund_months(today)
    sheets = {
        MonthKey(m.year, m.month)
        for m in await months_repo.list_for_user(session, user.id, None)
        if window[0] <= MonthKey(m.year, m.month) <= window[-1]
    }
    totals = dict.fromkeys(sheets, ZERO)
    rows = await reports_repo.totals_by_label_month_and_type(
        session, user.id, window, CategoryFilter(kinds=frozenset({LabelKind.EXPENSE}))
    )
    for _, month, movement_type, amount in rows:
        if month in totals:
            signed = -amount if movement_type.value == "transfer_out" else amount
            totals[month] += signed
    return rules.average_monthly_expenses([totals[m] for m in sorted(totals)])


async def view(
    session: AsyncSession, user: User, goal: Goal, label: Label, today: date
) -> GoalRead:
    average = None
    if goal.type is GoalType.EMERGENCY_FUND:
        average = await average_expenses(session, user, today)
        assert goal.months_of_expenses is not None
        target = rules.emergency_fund_target(average, goal.months_of_expenses)
    else:
        target = goal.target_amount
    progress = (
        goal.manual_progress
        if goal.manual_progress is not None
        else await label_balance(session, user, goal.label_id)
    )
    pace = rules.pace(progress, target or ZERO, today, goal.deadline)
    return GoalRead(
        id=goal.id,
        label_id=label.id,
        label_name=label.name,
        color=label.color,
        icon=label.icon,
        type=goal.type,
        target_amount=target,
        months_of_expenses=goal.months_of_expenses,
        average_expenses=average,
        deadline=goal.deadline,
        manual_progress=goal.manual_progress,
        progress=progress,
        remaining=pace.remaining if target else ZERO,
        percent=pace.percent,
        months_left=pace.months_left,
        days_left=pace.days_left,
        per_month=pace.per_month if target else None,
        reached=pace.reached,
        overdue=pace.overdue,
        completed_at=goal.completed_at,
        created_at=goal.created_at,
    )


async def list_goals(session: AsyncSession, user: User) -> GoalList:
    today = today_for(user)
    active: list[GoalRead] = []
    completed: list[GoalRead] = []
    for goal, label in await goals_repo.list_with_labels(session, user.id):
        row = await view(session, user, goal, label, today)
        (completed if goal.completed_at else active).append(row)
    completed.sort(key=lambda g: g.completed_at or g.created_at, reverse=True)
    return GoalList(active=active, completed=completed)


async def get_view(session: AsyncSession, user: User, goal: Goal) -> GoalRead:
    label = await labels.get(session, user, goal.label_id)
    return await view(session, user, goal, label, today_for(user))


async def create(session: AsyncSession, user: User, data: GoalCreate) -> Goal:
    await labels.get_usable(session, user, data.label_id)
    _check_target(data.type, data.target_amount, data.months_of_expenses)
    _check_deadline(data.deadline, user)
    if await goals_repo.active_for_label(session, user.id, data.label_id):
        raise ConflictError("This label already has an active goal")
    goal = Goal(
        user_id=user.id,
        label_id=data.label_id,
        type=data.type,
        target_amount=_money(data.target_amount) if data.type is GoalType.NORMAL else None,
        months_of_expenses=data.months_of_expenses
        if data.type is GoalType.EMERGENCY_FUND
        else None,
        deadline=data.deadline,
        manual_progress=_money(data.manual_progress),
    )
    session.add(goal)
    await session.flush()
    _log(session, user, goal, AuditAction.CREATE)
    await session.commit()
    return goal


async def update(session: AsyncSession, user: User, goal_id: uuid.UUID, data: GoalUpdate) -> Goal:
    goal = await _get(session, user, goal_id)
    changes = data.model_dump(exclude_unset=True)
    if "target_amount" in changes and goal.type is not GoalType.NORMAL:
        raise ValidationError("The emergency fund target comes from months_of_expenses")
    if "months_of_expenses" in changes and goal.type is not GoalType.EMERGENCY_FUND:
        raise ValidationError("Only the emergency fund has months_of_expenses")
    if changes.get("target_amount", 1) is None or changes.get("months_of_expenses", 1) is None:
        raise ValidationError("A goal always has a target")
    if "deadline" in changes:
        _check_deadline(changes["deadline"], user)
    before = audit.snapshot(goal)
    for field, value in changes.items():
        setattr(goal, field, _money(value) if field in _MONEY_FIELDS else value)
    await session.flush()
    _log(session, user, goal, AuditAction.UPDATE, before)
    await session.commit()
    return goal


async def delete(session: AsyncSession, user: User, goal_id: uuid.UUID) -> None:
    goal = await _get(session, user, goal_id)
    before = audit.snapshot(goal)
    goal.deleted_at = datetime.now(UTC)
    await session.flush()
    _log(session, user, goal, AuditAction.DELETE, before)
    await session.commit()


async def restore(session: AsyncSession, user: User, goal_id: uuid.UUID) -> Goal:
    goal = await goals_repo.get_for_user(session, user.id, goal_id, deleted=True)
    if goal is None:
        raise NotFoundError("Goal not found")
    before = audit.snapshot(goal)
    goal.deleted_at = None
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("This label already has an active goal") from exc
    _log(session, user, goal, AuditAction.RESTORE, before)
    await session.commit()
    return goal


async def complete_reached(session: AsyncSession, user: User) -> list[uuid.UUID]:
    """Mark active goals whose target is reached as completed (kept in history)."""
    today = today_for(user)
    completed = []
    for goal, label in await goals_repo.list_with_labels(session, user.id):
        if goal.completed_at is not None:
            continue
        row = await view(session, user, goal, label, today)
        if row.reached:
            before = audit.snapshot(goal)
            goal.completed_at = datetime.now(UTC)
            await session.flush()
            _log(session, user, goal, AuditAction.UPDATE, before)
            completed.append(goal.id)
    return completed


_MONEY_FIELDS = {"target_amount", "manual_progress"}


def _money(value: Decimal | None) -> Decimal | None:
    return money(value) if value is not None else None


def _check_target(kind: GoalType, target: Decimal | None, months: int | None) -> None:
    if kind is GoalType.NORMAL and target is None:
        raise ValidationError("A goal needs target_amount")
    if kind is GoalType.EMERGENCY_FUND and months is None:
        raise ValidationError("The emergency fund needs months_of_expenses")


def _check_deadline(deadline: date | None, user: User) -> None:
    if deadline is not None and deadline < today_for(user):
        raise ValidationError("The deadline cannot be in the past")


async def _get(session: AsyncSession, user: User, goal_id: uuid.UUID) -> Goal:
    goal = await goals_repo.get_for_user(session, user.id, goal_id)
    if goal is None:
        raise NotFoundError("Goal not found")
    return goal


def _log(
    session: AsyncSession,
    user: User,
    goal: Goal,
    action: AuditAction,
    before: dict[str, object] | None = None,
) -> None:
    audit.log(session, user_id=user.id, entity=ENTITY, obj=goal, action=action, before=before)
