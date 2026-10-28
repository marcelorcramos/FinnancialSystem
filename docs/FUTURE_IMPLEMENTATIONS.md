# Future implementations

Ideas agreed during development and left for later. They are **not in scope now**: the current goal is a simple, working backend and frontend to test end to end.

**When:** after the frontend is structured (Phases 4–5) and before message brokers or any cloud infrastructure (Phases 7+), once the system is robust enough to take the next step.

When an idea moves into scope, record the decision in `DECISIONS.md` and remove it from here.

## Reports and filters

| Idea | Notes |
|---|---|
| Custom time ranges | User-editable report periods: last N days (e.g. 60 or 40 days), a specific year (only 2024, only 2023), any start/end range. Today only last month, last 6 months, last 12 months and all time exist. |
| Evolution of the current month by day | "Last month" on the evolution chart as one point per day or week inside the month (e.g. Oct 1, 8, 15, 22, 31), as in the mockup. Needs a daily series from the API; today `/reports/series` aggregates by month, so the chart offers only last 6 / 12 months and all time. |

## Limits and alerts

| Idea | Notes |
|---|---|
| Category limits set by the user | When signing up or editing the profile, the user sets a maximum per category (e.g. Food at most €300/month). When a month reaches it, the app **warns but never blocks**: the user is free to distribute money however they want (they may put €3000 into Food if they decide so). Related to Phase 8. |

## Labels

| Idea | Notes |
|---|---|
| Full-spectrum color picker | Beyond the 8 suggested swatches and the `#RRGGBB` field. |

## Accounts and settings

| Idea | Notes |
|---|---|
| Email verification | Accounts work without it for now; planned with password recovery (Phase 9). |
| Admin panel | No admin routes exist yet. |
| Multiple currencies | EUR only for now; the `currency` field is already on the user. |
