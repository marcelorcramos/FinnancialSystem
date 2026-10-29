"""Report queries scope every joined table by user (see docs/QUERY_PLANS.md)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql

from app.domain.filters import CategoryFilter
from app.models import Entry
from app.repositories.reports import _scoped


def test_joined_months_and_labels_are_filtered_by_user() -> None:
    stmt = _scoped(select(func.count(Entry.id)), uuid.uuid4(), None, CategoryFilter())
    sql = str(stmt.compile(dialect=postgresql.dialect()))
    for column in ("entries.user_id", "months.user_id", "labels.user_id"):
        assert f"{column} = " in sql, column
