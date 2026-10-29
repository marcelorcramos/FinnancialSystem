"""EXPLAIN ANALYZE the report queries against a large database (see docs/QUERY_PLANS.md).

Usage, from backend/:  PYTHONPATH=. python scripts/query_plans/explain.py [--plans]
"""

import asyncio
import sys
import uuid
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.domain.enums import LabelKind
from app.domain.filters import CategoryFilter
from app.domain.periods import Period, months_in
from app.models import Entry, Label, User
from app.repositories import reports as repo

URL = "postgresql+asyncpg://finance:finance_dev@localhost:5544/explain_lab"
TODAY = date(2026, 10, 28)


async def main(show_plans: bool) -> None:
    engine = create_async_engine(URL)
    statements: list[tuple[str, Any]] = []

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def capture(_conn: Any, _cursor: Any, statement: str, params: Any, *_: Any) -> None:
        statements.append((statement, params))

    async with AsyncSession(engine) as session:
        user = await session.scalar(select(User).order_by(User.email).limit(1))
        assert user is not None, "Seed explain_lab first (scripts/query_plans/seed.sql)"
        label_id = await session.scalar(select(Label.id).where(Label.user_id == user.id))
        assert label_id is not None
        transfer_ids = set(
            await session.scalars(
                select(Entry.transfer_id)
                .where(Entry.user_id == user.id, Entry.transfer_id.is_not(None))
                .limit(20)
            )
        )
        income_ids = set(
            await session.scalars(
                select(Entry.income_id)
                .where(Entry.user_id == user.id, Entry.income_id.is_not(None))
                .limit(20)
            )
        )

        windows = {
            "one label, 6 months": (
                months_in(Period.LAST_6_MONTHS, TODAY),
                CategoryFilter(frozenset({label_id})),
            ),
            "investments, 12 months": (
                months_in(Period.LAST_12_MONTHS, TODAY),
                CategoryFilter(kinds=frozenset({LabelKind.INVESTMENT})),
            ),
            "everything, all time": (None, CategoryFilter()),
        }
        queries: dict[str, Callable[[], Awaitable[object]]] = {}
        for name, (months, cats) in windows.items():
            queries |= {
                f"{name} / summary": lambda m=months, c=cats: repo.totals_by_label_and_type(
                    session, user.id, m, c
                ),
                f"{name} / series": lambda m=months, c=cats: repo.totals_by_label_month_and_type(
                    session, user.id, m, c
                ),
                f"{name} / entries page": lambda m=months, c=cats: repo.entries_in_window(
                    session, user.id, m, c, limit=50, offset=0
                ),
                f"{name} / entries count": lambda m=months, c=cats: repo.count_entries(
                    session, user.id, m, c
                ),
            }
        queries["transfer legs"] = lambda: repo.transfer_leg_labels(
            session, user.id, {t for t in transfer_ids if isinstance(t, uuid.UUID)}
        )
        queries["income sources"] = lambda: repo.income_sources(
            session, user.id, {i for i in income_ids if isinstance(i, uuid.UUID)}
        )
        queries["usable labels"] = lambda: repo.usable_labels_matching(
            session, user.id, CategoryFilter()
        )

        conn = await session.connection()
        for title, run in queries.items():
            statements.clear()
            await run()
            statement, params = statements[-1]
            result = await conn.exec_driver_sql("EXPLAIN (ANALYZE, BUFFERS) " + statement, params)
            plan = [row[0] for row in result]
            elapsed = next(line for line in plan if line.startswith("Execution Time"))
            seq_scans = [
                line.split("Seq Scan on ")[1].split()[0] for line in plan if "Seq Scan" in line
            ]
            print(f"{title:40} {elapsed:30} seq scans: {', '.join(seq_scans) or 'none'}")
            if show_plans:
                print("\n".join(plan), "\n")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main("--plans" in sys.argv))
