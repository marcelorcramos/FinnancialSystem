# Query plans

Phase 3 asks for the report queries and indexes to be validated with `EXPLAIN`. This file records how it was measured and what came out, so it can be repeated when the queries change.

## How to repeat

With the Compose stack running (Postgres on port 5544):

```sh
cd backend
docker compose -f ../deploy/docker-compose.yml exec -T postgres psql -U finance finance \
  -c "DROP DATABASE IF EXISTS explain_lab" -c "CREATE DATABASE explain_lab"
DATABASE_URL=postgresql+asyncpg://finance:finance_dev@localhost:5544/explain_lab alembic upgrade head
docker compose -f ../deploy/docker-compose.yml exec -T postgres psql -q -U finance explain_lab \
  < scripts/query_plans/seed.sql
PYTHONPATH=. python scripts/query_plans/explain.py           # one line per query
PYTHONPATH=. python scripts/query_plans/explain.py --plans   # full plans
```

`seed.sql` creates 1,000 users with 15 labels and 60 months each (November 2021 to October 2026): one allocation per label and month, two transfers and one addition per month. That is 1.2 million entries, about 1,200 per user. `explain.py` runs the real repository functions for the first user and sends the SQL they produce to `EXPLAIN (ANALYZE, BUFFERS)`.

## Results (2026-10-29, Postgres 16)

| Query | Before | After |
|---|---|---|
| One label, last 6 months (summary, series, entries, count) | 0.2–0.3 ms | 0.3–0.5 ms |
| Investment kind, last 12 months | 1.7–2.1 ms, seq scan on `labels` | 0.4–0.9 ms |
| Everything, all time | 10–12 ms, seq scan on `months` | 1.2–2.2 ms |
| Transfer legs, income sources, usable labels | < 0.1 ms | < 0.1 ms |

**What changed.** The report queries filtered `entries` by `user_id` but joined `months` and `labels` only by id. For wide filters, the planner then hashed every user's months (60,000 rows) or every investment label (5,000 rows), a cost that grows with the number of users, not with the user's own data. `_scoped` in `app/repositories/reports.py` now also filters `months.user_id` and `labels.user_id`, so no plan has a seq scan left. `tests/unit/test_report_queries.py` guards this.

**Indexes.** The existing ones are enough, so there is no new migration:

- `ix_entries_user_label_occurred_on` serves every entry scan (by user, by user and label).
- `pk_months` and `pk_labels` serve the joins.
- `uq_entries_transfer_leg` serves the transfer counterpart lookup; `ix_incomes_user_id` and `pk_incomes` serve income sources.

The all-time entries page sorts the user's matching entries before taking 50. That cost is bounded by one user's history (about 1,200 rows here, 1.5 ms). If it grows, cache the reports in Redis (Phase 7) or switch to keyset pagination.
