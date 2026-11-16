"""Month insights (Phase 11): a short reading of a month, written when it closes.

The `insights` consumer calls generate() on month events. The model gets the
month's numbers (from the same services as the screens) and the month before
for comparison, and answers in a fixed JSON shape. One insight per month;
closing it again after changes writes a new one.
"""

import json
import uuid
from typing import Any

import anthropic
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.assistant_client import AssistantClient
from app.domain.errors import NotFoundError
from app.models import Month, MonthInsight, User
from app.repositories import months as months_repo
from app.repositories import users
from app.services import limits, months, summary

log = structlog.get_logger(__name__)

MAX_TOKENS = 4000

SYSTEM = """You write a short, friendly reading of one month of a personal budget, from \
the numbers you are given. The user planned the month by hand: income split across labels \
(expense, saving or investment), plus money added or moved during the month.

Point out what stands out: where most of the money went, labels near or over their limit, \
how saving and investing compare with the month before, and unallocated money. Use only \
the numbers given; amounts are euros, written like €1,234.50. Never give investment advice. \
The headline is one sentence; give two to four highlights of one sentence each, and at most \
one practical suggestion for next month (empty when there is nothing useful to say)."""

FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "headline": {"type": "string"},
            "highlights": {"type": "array", "items": {"type": "string"}},
            "suggestion": {"type": "string"},
        },
        "required": ["headline", "highlights", "suggestion"],
        "additionalProperties": False,
    },
}


async def get(session: AsyncSession, user: User, month_id: uuid.UUID) -> MonthInsight:
    month = await months.get(session, user, month_id)
    insight = await session.scalar(
        select(MonthInsight).where(
            MonthInsight.month_id == month.id, MonthInsight.user_id == user.id
        )
    )
    if insight is None or month.closed_at is None:
        raise NotFoundError("No insight for this month yet")
    return insight


async def generate(
    session: AsyncSession, client: AssistantClient, user_id: uuid.UUID, month_id: uuid.UUID
) -> MonthInsight | None:
    """Write the insight of a closed month, unless one exists for this close already."""
    user = await users.get_active_by_id(session, user_id)
    month = await months_repo.get_for_user(session, user_id, month_id) if user else None
    if user is None or month is None or month.closed_at is None:
        return None
    insight = await session.scalar(select(MonthInsight).where(MonthInsight.month_id == month.id))
    if insight is not None and insight.closed_at == month.closed_at:
        return insight

    try:
        response = await client.create(
            system=SYSTEM,
            messages=[{"role": "user", "content": json.dumps(await _facts(session, user, month))}],
            max_tokens=MAX_TOKENS,
            output_format=FORMAT,
        )
    except anthropic.APIError:
        log.warning("insight.failed", month_id=str(month.id))
        raise  # the consumer retries, then dead-letters
    if response.stop_reason == "refusal":
        log.info("insight.refused", month_id=str(month.id))
        return None
    text = next((b.text for b in response.content if b.type == "text"), "")
    data = json.loads(text)
    if insight is None:
        insight = MonthInsight(user_id=user.id, month_id=month.id)
        session.add(insight)
    insight.closed_at = month.closed_at
    insight.headline = str(data["headline"])[:300]
    insight.highlights = [str(h)[:300] for h in data["highlights"]][:4]
    insight.suggestion = str(data["suggestion"])[:600] or None
    await session.flush()
    log.info("insight.written", month_id=str(month.id))
    return insight


async def _facts(session: AsyncSession, user: User, month: Month) -> dict[str, Any]:
    current = await _sheet(session, user, month)
    previous_month = await months_repo.latest_before(session, user.id, month.year, month.month)
    return {
        "month": current,
        "previous_month": await _sheet(session, user, previous_month) if previous_month else None,
        "limits": [
            {
                "label": status.name,
                "limit": f"{status.limit:.2f}",
                "total": f"{status.total:.2f}",
                "percent": f"{status.percent}",
            }
            for status in await limits.month_status(session, user, month.id)
        ],
    }


async def _sheet(session: AsyncSession, user: User, month: Month) -> dict[str, Any]:
    sheet = await summary.month_summary(session, user, month.id)
    return {
        "month": f"{month.year}-{month.month:02d}",
        "income": f"{sheet.income_total:.2f}",
        "unallocated": f"{sheet.unallocated:.2f}",
        "by_kind": {kind.value: f"{amount:.2f}" for kind, amount in sheet.by_kind.items()},
        "labels": [
            {"name": lb.name, "kind": lb.kind.value, "total": f"{lb.total:.2f}"}
            for lb in sheet.labels
            if lb.total != 0
        ],
    }
