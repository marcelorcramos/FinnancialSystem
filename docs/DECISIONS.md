# Project decisions

Decisions about what `docs/ARCHITECTURE.md` leaves open or adjusts. When they disagree, this file wins.

## Language (2026-10-26)

Everything in the repository is in **English**: code, identifiers, comments, docstrings, API error messages, commit messages, documentation and seed data (default label names).

## Data and domain (2026-10-26)

| Topic | Decision |
|---|---|
| IDs | UUID on every table (generated in Python, `uuid.uuid4`), so they cannot be guessed in URLs or attachment links. |
| Migrations | There is no real data yet: the initial migration was recreated from scratch with the full section 6 model. |
| Default labels | Every user gets their own copy at sign-up (`labels.user_id` is never null). The user can change name, color and icon. |
| Movement date | `occurred_on` must fall within the year/month of the entry's month (validated in the domain). The day is informative: filters and reports aggregate by month, semester or year. |
| Allocation | At most one `allocation` per label and month, editable (partial unique index). |
| Refresh tokens | `refresh_tokens` table (token hash, family, `expires_at`, `revoked_at`, `replaced_by_id`). Rotated on every refresh; reusing an already rotated token revokes the whole family. |
| Admin | Later. There are no routes that list or edit other users. |
| Accounts | No email verification for now (it only has to be a valid email). New passwords: at least 8 characters with a lowercase letter, an uppercase letter, a digit and a special character. |
| Currency and locale | EUR only in the MVP (the `currency` field exists to change it later). Default time zone `Europe/Lisbon`. |

## Months, entries and reports (2026-10-26)

| Topic | Decision |
|---|---|
| Copy previous month | Optional on creation: copies the allocations and/or the incomes of the latest existing month. Copies are regular entries, editable afterwards (e.g. Food goes from €200 to €220). One-off "add money" incomes are not copied. |
| Closed month | Blocks every write, including the note. It can always be reopened, edited and closed again. |
| Delete month | Soft delete of the month; its entries are hidden with it and come back with "undo". |
| Add money | Money that arrives mid-month (e.g. +€50 to Investments) is an `addition`: it adds to the label and to the month's income. |
| Negative unallocated | Allowed; the UI only warns. |
| Report filters | Two independent, optional filters: **category** (one or more labels and/or kinds) and **time**. Time is a rolling window counted back from the current month, which is included: **last month** (the current month), **last 6 months**, **last 12 months**. No time filter = since the first record. No category filter = all labels together. Custom ranges come later (see `FUTURE_IMPLEMENTATIONS.md`). |
| Multi-category filter | The category filter accepts several labels and/or kinds in one query (e.g. Food + Investments over the last 6 months), returning the combined total and the per-label split. |
| Report entries | The report lists the entries behind its totals, newest first, with the same filters and the same origin fields as the month's entry list, plus the month. Paginated with `limit` (default 50, at most 200) and `offset`; the total and count always cover every page. Query plans are recorded in `QUERY_PLANS.md` (added 2026-10-29). |
| Charts | **Donut** (pie with an empty center) for the overview: how the money was distributed, as a share (%) per kind (expense / saving / investment) and per label, for the selected period and categories. It shows the distribution only; it does not judge positive or negative balances. A label whose net total in the period is zero or below (money moved out of it) gets no slice but is still listed with its amount. **Line chart** for the evolution of one label across months (e.g. Food €200 three months ago vs €250 now). Both read from the Phase 3 report endpoints. |

### Default labels

| Name | Kind | Color | Icon |
|---|---|---|---|
| Investments | investment | `#42A5F5` | `trending_up` |
| Savings | saving | `#66BB6A` | `savings` |
| Emergency Fund | saving | `#26A69A` | `health_and_safety` |
| Food | expense | `#FFB74D` | `restaurant` |
| Housing | expense | `#E57373` | `home` |
| Electricity | expense | `#FFD54F` | `bolt` |
| Water | expense | `#4FC3F7` | `water_drop` |
| Transport | expense | `#9575CD` | `directions_bus` |
| Health | expense | `#F06292` | `medical_services` |
| Phone & Internet | expense | `#7986CB` | `wifi` |
| Subscriptions | expense | `#BA68C8` | `subscriptions` |

There is a single investment label on purpose: users create their own labels for specific investments (ETFs, pension plan...). Other categories (leisure, travel funds...) are left to the user.

Icon names are Material Symbols for now; they will change with the frontend redesign.

### Label colors

- Two labels of the same user never share the exact same color (case-insensitive); similar colors are fine. Archived labels keep their color reserved; deleted labels free it.
- Colors are stored uppercase (`#AB47BC`).
- `GET /labels/color-suggestions` returns 8 colors not used by any of the user's labels: a curated palette first, then generated hues.
- Color picker (frontend): when creating or editing a label, a small pop-up shows the 8 suggestions as square swatches, plus a field to type any `#RRGGBB` code. A full-spectrum picker may come later.

## Cache, events and tasks (2026-11-03)

| Topic | Decision |
|---|---|
| Read cache | Redis caches the month summary and the three report routes per user, keyed by the request's parameters (the report key includes today, so a new day is a new key), for one hour. Each user has a version number in the key: invalidating is one `INCR`, old keys just expire. If Redis is down, reads go to PostgreSQL and nothing fails. |
| Invalidation | Every successful write on months, incomes, entries, transfers and labels invalidates the user's cache before the response is sent, so the next read is already fresh. The `cache` consumer (outbox events) also invalidates, for writes that do not come through the API, such as Celery tasks. |
| Auth rate limits | Fixed windows in Redis: login 20 per minute per IP and 10 per 5 minutes per email, sign-up 30 per hour per IP, refresh 60 per minute per IP. Over the limit: 429 `rate_limited` with `Retry-After`. Emails are hashed in the keys. Without Redis there is no limit (fail open), like the cache. |
| Outbox | Every audited write also adds an `outbox_events` row in the same transaction (`audit.record`), so a change and its event are saved together or not at all. Type `<entity>.<action>` (e.g. `entry.create`, `month.close`); payload: `user_id`, `entity`, `entity_id`, `action`, `month_id`. |
| Relay and topology | `python -m app.events.relay` publishes pending events oldest first with publisher confirms, locking rows with `SKIP LOCKED` so several relays can run. Topic exchange `finance.events` (routing key = event type) with quorum queues `cache` (entries, incomes, months, labels), `limits` and `goals` (entries). Publishing twice is possible after a crash; consumers are idempotent. |
| Consumers | One process per queue (`python -m app.events.consumers cache`). Each stores `(consumer, event_id)` in `processed_events` in the same transaction as its own work, so a repeated message is acknowledged without repeating its effect. A failure publishes the message again to the same queue with an `x-attempts` header; on the 5th failure it is rejected to `finance.events.dead`. (RabbitMQ 4 does not count a requeueing nack towards `x-delivery-limit`, so that limit, 10, only catches consumers that crash.) Malformed messages go straight to the dead-letter queue. `cache` invalidates the user's read cache; `limits` and `goals` are wired and deduplicated now and get their work in Phase 8. |
| Recurring entries | Opt-in per user (`auto_new_month`, off by default: a month appearing on its own could surprise). Celery beat runs `create_due_months` every hour; for each opted-in user whose own month (in their time zone) has no sheet yet, it creates it copying the previous month's allocations and recurring incomes (rent, salary), like **New month** with both copies ticked. The first month is always created by hand, and running it again changes nothing. Celery uses RabbitMQ as broker, late acks, and no result backend. |
| Processes | Compose runs the API image as separate processes: `api`, `relay`, `consumer-cache`, `consumer-limits`, `consumer-goals`, `worker` and `beat`; the background ones start once the API is healthy (migrations done). RabbitMQ 4 refuses transient non-exclusive queues, so the Celery worker runs without remote control, mingle, gossip and event heartbeats. Queue arguments cannot change once a queue exists: changing them means deleting and recreating the queue. |

## Limits, alerts and goals (2026-11-03)

| Topic | Decision |
|---|---|
| Limits | Per label: a default amount for every month (`month_id` null) and optional amounts for single months that replace it. They are compared with the label's month total (the same total the month screen shows) and only warn, never block. Thresholds are fixed: `warning` from 80%, `exceeded` from 100%, compared exactly. A closed month's limits cannot change. |
| Alerts | Raised by the `limits` consumer on `entry.*` and `limit.*` events (a default limit change checks every open month). One row per label, month and level (`warning`, `exceeded`), never repeated, with the limit and total at that moment. Pushed live with Server-Sent Events: the consumer publishes to Redis channel `alerts:<user>` only after its transaction commits, and `GET /alerts/stream` relays it. SSE over WebSocket: one-way is all alerts need, and it goes through nginx and plain HTTP. The stream gives its database connection back before streaming. |
| Goals | A goal gathers money in a label: progress is the label's balance over all months (or a manual amount). One active goal per label. "You need to save €X/month" = remaining / months left, counting the current month and the deadline's month, rounded up to the cent so following it always reaches the target. A passed deadline without the target is `overdue`. The `goals` consumer (on `entry.*` and `goal.*` events) marks reached goals as completed; they stay in the history even if the balance drops later. |
| Emergency fund | A goal of type `emergency_fund`: target = N months (1–24) of average expenses, averaged over the 6 complete months before the current one that have a sheet (months without a sheet do not pull the average down). Recomputed on every read, so it follows spending. |

## Future ideas

Ideas left for later live in [`docs/FUTURE_IMPLEMENTATIONS.md`](FUTURE_IMPLEMENTATIONS.md).

## Frontend: visual identity (2026-10-26)

The current look (Angular Material, Roboto, Material Symbols) feels like Google/Gmail and **will be redesigned**. Requirements: a FinnancialSystem identity of its own, without copying templates, layouts or the look of other products, and without Google Fonts.

**Chosen direction: "Vault"** (out of three proposals). Mockups of every screen live in the design canvas https://claude.ai/artifact/MpLuzgGrY9DWYLY2RUdSbp.

| Topic | Decision |
|---|---|
| Mood | Dark-first and precise, like a control panel for your money. Light theme and "system" are options. |
| Colors | Ground `#111417`, panels `#1A1F24`, borders `#2A3138`, text `#E6EAEE` / `#B9C1C9`, one accent "signal" lime `#D4F06A`. Kinds: expense `#FF8A73`, saving `#5FD39A`, investment `#7AB3FF`. |
| Type | System fonts only: system sans for words, system monospace for money and dates. No web fonts. |
| Shapes | 4–6px corners, thin borders, no glows or heavy shadows; touch targets ≥ 44px. |
| Components | Angular Material is removed; own components built on Angular CDK (focus, overlays, a11y), no Material look. |
| Language | The UI is **English only**; the PT translations go away. |
| Motion | Subtle transitions (hover on rows, donut slices grow, chart points enlarge); all off with "Reduce motion". |
| Accessibility | Color is never the only signal (text, icons, optional chart patterns); text size, high contrast and reduce-motion preferences. Checked on 2026-11-01: the token colours pass WCAG AA in both themes (text at least 4.7:1, kind slices at least 5.3:1 against the surface); every chart value is reachable by keyboard (donut legend, line chart points) and as text (`aria-label`s, the Reports **Table** view). Label colours are user-picked and may be faint in the light theme, so their values are always written next to them. |

Screens agreed in the mockups:

- **Month**: income, spent, saved, invested and unallocated totals; a thick donut with hover details and two views chosen with **Overview / Detailed** buttons (Overview = one slice per kind: Spent, Saved, Invested; Detailed = one slice per label in its own colour; the choice is remembered per browser); labels list ("base + adjustments"); a large evolution chart with a **category** and a **period** selector (last 6 / 12 months, all time; rolling from the current month, months without money count as zero; "last month by day" waits for daily data, see `FUTURE_IMPLEMENTATIONS.md`) showing this month, the monthly average and the change since the first month; entries by date with delete + Undo (the latest 6, or all of them with **Show all**) and a one-line **quick entry** (amount, to, from: outside the app or another label; dated today, or the 1st when the month is not the current one); **Close month** (with Undo) and **Reopen**.
- **Reports** (added 2026-10-29, no mockup; follows the Vault month screen): a period toggle (this month, last 6 / 12 months, all time) and kind and label chips that combine as a union, all kept in the URL so a report can be bookmarked; totals; the donut (Overview / Detailed); labels as **sorted bars** that show base + adjustments (base, extra income and moved in as parts of the bar, moved out striped at its end) with a **Table** view as the text alternative; a month-by-month line of the selection; and the entries behind the totals, 50 at a time with **Show more**.
- **Limits, alerts and goals** (added 2026-11-03, no mockups; Vault style): on the month screen each label with a limit shows its usage bar and a warning from 80% and when passed, and a gauge button sets the limit for every month or only this one; a **bell** in the header counts unseen alerts and lists them, and new alerts arrive live (Server-Sent Events read with `fetch`) as a toast; the **Goals** page shows active goals as cards (progress, what to save each month to meet the deadline or that it passed, the emergency fund's average expenses) and the completed ones, with create/edit in a dialog and delete with Undo.
- **Sign in / create account** with live password rules; **Account** (name, email, EUR, time zone, password, sign out other devices; changing the password ends every session on the API and this browser signs in again, so only the other devices are signed out); **Preferences & accessibility**, kept per browser: theme, text size, reduce motion, high contrast and chart patterns (on by default: stripes for saving, dots for investment), plus the month screen shortcuts (N new entry, T transfer, ←/→ months, ⌘/Ctrl+Z undo the last delete).
- **Labels** grouped by kind, archive, and delete with reassignment of entries; **Create label** with the kind question, the 8 suggested colors plus a `#RRGGBB` field, and icons.
- **Add money**: from outside the app (raises income) or from another label (a transfer), showing the effect before confirming.
- **New month** copying from the previous month, with **Review amounts**: every label shows its previous-month value and the new value, editable with −/+ (€10), typed, removed or reset; the salary is editable too. The month is created with the reviewed values (no backend change: create the month, then set each allocation).
- **Plan** (on the month screen, open months only): edit the recurring incomes (add a salary, change, rename or remove one) and the initial distribution of every usable label with −/+ (€10) or typed values. Extra income from Add money is shown as one total and edited through its entry. Totals update live and saving sends only what changed.

## Structure and tooling

- Monorepo: `backend/`, `frontend/`, `deploy/`, `docs/`, `.github/workflows/`.
- Backend in `backend/app/` with the layers `core`, `db`, `domain`, `models`, `schemas`, `repositories`, `services`, `api/v1` (plus `events` and `workers` from Phase 7).
- Python dependencies in `requirements.txt` (runtime) and `requirements-dev.txt` (tests and lint). `pyproject.toml` only holds Ruff, mypy and pytest configuration.
- SQLAlchemy 2.0 async with `asyncpg`.
- Integration tests with testcontainers (real PostgreSQL); Docker must be running.
- Frontend: Angular (latest stable), standalone components, Signals, zoneless, new control flow, own components on Angular CDK (no Angular Material), charts as own SVG components (donut, line) instead of ECharts.
- Dev file storage: SeaweedFS (S3-compatible) instead of MinIO, because MinIO Docker images are no longer public. The code speaks S3, so production can still use Azure Blob (through an S3 gateway or its own SDK, decided in Phase 9).
- CI split by area: `.github/workflows/backend.yml` and `frontend.yml`.
- Node 24 for the frontend (Angular 22 needs Node ≥ 22.22).

## API contract

The full API contract (auth, labels, months, incomes, entries, transfers, summary, errors and money format) lives in [`docs/API.md`](API.md).

## Ways of working

- One branch per area: `backend`, `frontend` and later `infra` (cloud/Kubernetes). Merged into `main` through pull requests.
- Commit after every finished feature, on the area branch, with tests passing.
