"""Recurring entries: each new month starts from the previous one (Phase 7).

For users with auto_new_month on, when their own month changes (in their time
zone) and the new month has no sheet yet, it is created copying the previous
month's allocations and recurring incomes (rent, salary...), exactly like
"New month" with both copies ticked. Run by Celery beat every hour; running it
again changes nothing, since a month that exists is skipped.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.periods import MonthKey
from app.repositories import months as months_repo
from app.repositories import users as users_repo
from app.schemas.month import MonthCreate
from app.services import months

log = structlog.get_logger(__name__)


async def create_due_months(session: AsyncSession, now: datetime) -> int:
    """Create the current month for every opted-in user who has none; returns how many."""
    created = 0
    for user in await users_repo.with_auto_new_month(session):
        today = now.astimezone(ZoneInfo(user.timezone)).date()
        current = MonthKey.of(today)
        if await months_repo.find_active(session, user.id, current.year, current.month):
            continue
        # Only continue an existing history: the first month is always created by hand.
        if not await months_repo.latest_before(session, user.id, current.year, current.month):
            continue
        await months.create(
            session,
            user,
            MonthCreate(
                year=current.year,
                month=current.month,
                copy_allocations=True,
                copy_incomes=True,
            ),
        )
        log.info("recurring.month_created", user_id=str(user.id), month=str(current))
        created += 1
    return created
