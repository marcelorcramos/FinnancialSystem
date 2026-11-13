"""Demo accounts behind the "Try it" button (Phase 10).

Each click creates its own temporary account, filled through the normal services
from domain/demo.py, so visitors never see each other's changes. Celery beat
removes demo accounts once they expire (24 hours).
"""

import secrets
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import Storage
from app.domain import demo as rules
from app.domain.enums import GoalType
from app.models import Label, User
from app.schemas.entry import AdditionCreate, AllocationSet, TransferCreate
from app.schemas.goal import GoalCreate
from app.schemas.month import IncomeCreate, MonthCreate
from app.services import auth, entries, goals, incomes, limits, months

log = structlog.get_logger(__name__)

DEMO_DOMAIN = "demo.example.com"  # reserved for examples: never a real inbox


async def create(session: AsyncSession, now: datetime | None = None) -> User:
    now = now or datetime.now(UTC)
    user = await auth.create_user(
        session,
        User(
            email=f"demo-{secrets.token_hex(6)}@{DEMO_DOMAIN}",
            name="Demo",
            email_verified_at=now,
            demo_expires_at=now + timedelta(hours=rules.LIFETIME_HOURS),
        ),
    )
    await session.commit()
    await _fill(session, user, now.date())
    log.info("demo.created", user_id=str(user.id))
    return user


async def _fill(session: AsyncSession, user: User, today: date) -> None:
    labels = {
        label.name: label.id
        for label in await session.scalars(select(Label).where(Label.user_id == user.id))
    }
    plans = rules.plan(today)
    for month_plan in plans:
        key = month_plan.month
        month = await months.create(session, user, MonthCreate(year=key.year, month=key.month))
        await incomes.create(
            session,
            user,
            month.id,
            IncomeCreate(
                source="Salary", amount=rules.SALARY, received_on=date(key.year, key.month, 1)
            ),
        )
        for name, amount in month_plan.allocations.items():
            await entries.set_allocation(
                session, user, month.id, labels[name], AllocationSet(amount=amount)
            )
        for movement in month_plan.movements:
            day = date(key.year, key.month, movement.day)
            if movement.from_label is None:
                await entries.add_money(
                    session,
                    user,
                    month.id,
                    AdditionCreate(
                        label_id=labels[movement.to_label],
                        amount=movement.amount,
                        occurred_on=day,
                        source=movement.note,
                    ),
                )
            else:
                await entries.create_transfer(
                    session,
                    user,
                    month.id,
                    TransferCreate(
                        from_label_id=labels[movement.from_label],
                        to_label_id=labels[movement.to_label],
                        amount=movement.amount,
                        occurred_on=day,
                        note=movement.note,
                    ),
                )
        if month_plan.closed:
            await months.set_closed(session, user, month.id, closed=True)

    await limits.set_limit(session, user, labels["Food"], Decimal("350.00"))
    await limits.set_limit(session, user, labels["Transport"], Decimal("70.00"))
    first = plans[-1].month
    await goals.create(
        session,
        user,
        GoalCreate(
            label_id=labels["Savings"],
            target_amount=Decimal("6000.00"),
            deadline=date(first.year + 1, first.month, 1),
        ),
    )
    await goals.create(
        session,
        user,
        GoalCreate(
            label_id=labels["Emergency Fund"], type=GoalType.EMERGENCY_FUND, months_of_expenses=6
        ),
    )


async def remove_expired(session: AsyncSession, storage: Storage, now: datetime) -> int:
    """Delete demo accounts past their 24 hours, with their files (Celery beat, hourly)."""
    expired = list(
        await session.scalars(
            select(User.id).where(User.demo_expires_at.is_not(None), User.demo_expires_at <= now)
        )
    )
    for user_id in expired:
        await auth.erase_user(session, user_id)
        await session.commit()
        await storage.delete_prefix(f"users/{user_id}/")
    if expired:
        log.info("demo.removed", count=len(expired))
    return len(expired)
