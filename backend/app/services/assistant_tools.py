"""The tools the assistant may call: read-only questions to the report services.

They run as the signed-in user, through the same services as the screens, so
the model sees only that user's numbers and never writes or queries anything
else. Results are JSON text; a bad request (an unknown label, a malformed
month) comes back as a tool error the model can correct.
"""

import json
import re
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import LabelKind
from app.domain.filters import CategoryFilter
from app.domain.periods import MonthKey
from app.models import User
from app.repositories import labels as labels_repo
from app.repositories import months as months_repo
from app.services import goals, reports, summary

MAX_MONTHS = 36
_MONTH = re.compile(r"^(\d{4})-(\d{2})$")

_CATEGORY_PROPERTIES: dict[str, Any] = {
    "start_month": {"type": "string", "description": "First month, YYYY-MM"},
    "end_month": {"type": "string", "description": "Last month, YYYY-MM (inclusive)"},
    "labels": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Label names to include (exact names from list_labels). Empty: all.",
    },
    "kinds": {
        "type": "array",
        "items": {"type": "string", "enum": [k.value for k in LabelKind]},
        "description": "Label kinds to include, combined with labels as a union. Empty: all.",
    },
}


def _tool(name: str, description: str, properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
    }


# Declared once, in a fixed order: the same tools on every request of a conversation.
TOOLS: list[dict[str, Any]] = [
    _tool(
        "list_labels",
        "The user's labels (categories of money) with their kind: expense, saving or "
        "investment. Call it before using label names in other tools.",
        {},
    ),
    _tool(
        "month_summary",
        "One month's sheet: income, what was distributed, unallocated money, totals by "
        "kind and the total of every label (allocations + extra income + transfers).",
        {"month": {"type": "string", "description": "The month, YYYY-MM"}},
    ),
    _tool(
        "totals",
        "Net totals over a run of months for the chosen labels and kinds: per kind, per "
        "label and overall. Use it for questions like 'how much did I invest in the last "
        "2 months' or 'what did I spend on food this year'.",
        _CATEGORY_PROPERTIES,
    ),
    _tool(
        "monthly_totals",
        "The same selection month by month, to see how it changed over time.",
        _CATEGORY_PROPERTIES,
    ),
    _tool(
        "goals",
        "The user's active savings goals: target, progress, deadline and what to save "
        "each month to reach them.",
        {},
    ),
]


class ToolError(Exception):
    """A request the model can fix (shown to it as an error result)."""


def _json(data: Any) -> str:
    def default(value: Any) -> str:
        if isinstance(value, Decimal):
            return f"{value:.2f}"
        return str(value)

    return json.dumps(data, default=default, ensure_ascii=False)


def _month(value: str) -> MonthKey:
    match = _MONTH.match(value or "")
    if not match or not 1 <= int(match.group(2)) <= 12:
        raise ToolError(f"Months are written YYYY-MM, got {value!r}")
    return MonthKey(int(match.group(1)), int(match.group(2)))


def _range(data: dict[str, Any]) -> tuple[MonthKey, MonthKey]:
    first, last = _month(data["start_month"]), _month(data["end_month"])
    if first > last:
        raise ToolError("start_month must not be after end_month")
    if last.index - first.index + 1 > MAX_MONTHS:
        raise ToolError(f"Ask for at most {MAX_MONTHS} months at a time")
    return first, last


async def _categories(session: AsyncSession, user: User, data: dict[str, Any]) -> CategoryFilter:
    names = {label.name.lower(): label for label in await _labels(session, user)}
    chosen = []
    for name in data.get("labels") or []:
        label = names.get(str(name).strip().lower())
        if label is None:
            known = ", ".join(sorted(label.name for label in names.values()))
            raise ToolError(f"There is no label called {name!r}. Labels: {known}")
        chosen.append(label.id)
    kinds = [LabelKind(kind) for kind in data.get("kinds") or []]
    return CategoryFilter(frozenset(chosen), frozenset(kinds))


async def _labels(session: AsyncSession, user: User) -> list[Any]:
    return await labels_repo.list_for_user(session, user.id, include_archived=True)


async def run(
    session: AsyncSession, user: User, today: date, name: str, data: dict[str, Any]
) -> str:
    """Run one tool call for this user; raises ToolError for a request to correct."""
    if name == "list_labels":
        return _json(
            [
                {"name": lb.name, "kind": lb.kind.value, "archived": lb.archived_at is not None}
                for lb in await _labels(session, user)
            ]
        )
    if name == "month_summary":
        key = _month(data["month"])
        month = await months_repo.find_active(session, user.id, key.year, key.month)
        if month is None:
            return _json({"month": str(key), "exists": False})
        sheet = await summary.month_summary(session, user, month.id)
        return _json(
            {
                "month": str(key),
                "exists": True,
                "closed": sheet.closed_at is not None,
                "income": sheet.income_total,
                "distributed": sheet.distributed,
                "unallocated": sheet.unallocated,
                "by_kind": sheet.by_kind,
                "labels": [
                    {"name": lb.name, "kind": lb.kind.value, "total": lb.total}
                    for lb in sheet.labels
                    if lb.total != 0
                ],
            }
        )
    if name == "totals":
        first, last = _range(data)
        result = await reports.summary_between(
            session,
            user,
            first=first,
            last=last,
            categories=await _categories(session, user, data),
            today=today,
        )
        return _json(
            {
                "from": str(first),
                "to": str(last),
                "total": result.total,
                "by_kind": result.by_kind,
                "labels": [
                    {"name": row.name, "kind": row.kind.value, "total": row.total}
                    for row in result.labels
                ],
            }
        )
    if name == "monthly_totals":
        first, last = _range(data)
        series = await reports.series_between(
            session,
            user,
            first=first,
            last=last,
            categories=await _categories(session, user, data),
            today=today,
        )
        return _json(
            {
                "months": [{"month": p.month, "total": p.total} for p in series.totals],
                "labels": [
                    {
                        "name": lb.name,
                        "points": [{"month": p.month, "total": p.total} for p in lb.points],
                    }
                    for lb in series.labels
                ],
            }
        )
    if name == "goals":
        listing = await goals.list_goals(session, user)
        return _json(
            [
                {
                    "label": goal.label_name,
                    "type": goal.type.value,
                    "target": goal.target_amount,
                    "progress": goal.progress,
                    "percent": goal.percent,
                    "deadline": goal.deadline,
                    "per_month": goal.per_month,
                    "overdue": goal.overdue,
                }
                for goal in listing.active
            ]
        )
    raise ToolError(f"Unknown tool {name!r}")
