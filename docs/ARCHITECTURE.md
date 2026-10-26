# FinnancialSystem: Implementation Architecture

Reference document that guides development. It defines the product, the domain rules, the stack, the repository layout and the implementation phases, in order.

> Decisions made during development refine this plan and live in [`docs/DECISIONS.md`](DECISIONS.md). When the two disagree, `DECISIONS.md` wins.

**How to use it with Claude Code:** ask for **one phase at a time**, for example: "Implement Phase 2 of docs/ARCHITECTURE.md, meeting its acceptance criteria". Do not move to the next phase until the criteria are met and the tests pass.

---

## 1. Product vision

A personal finance platform. The user works **month by month** (one "sheet" per month) and distributes money across **labels** (Rent, Food, Investments, Savings...). Data is **entered manually** (no bots, no voice, no bank connections).

The app answers questions such as "how much did I spend on water in the last 6 months?" or "how much did I invest this year?", and shows everything visually and immediately.

## 2. Domain rules (invariants)

These rules are the most important part of the project. They must be covered by automated tests and can never be broken by any endpoint, task or consumer.

### 2.1 Labels and kind

- Every label has a `kind`: `expense`, `saving` or `investment`.
- The kind is asked when the label is created and sets the **semantic color of amounts**: expense in soft red, saving in green, investment in blue.
- The **label color** (chosen by the user) is independent and acts as its identity in donuts, icons and chart lines.
- Color is never the only signal: always pair it with an icon and text (accessibility).
- Changing a label's `kind` is allowed, but it retroactively changes reports; the UI must warn about it.
- Default labels are created at sign-up, already with the right kind. Every label has a name, a color and an icon.
- A label with entries is not deleted: it is either archived or its entries are reassigned to another label.

### 2.2 Movements (entries)

A label always shows the **sum of everything put into it**. There is no "budget consumption": if Food had €200 and €12 more were added, it shows €212.

Every movement has a date (`occurred_on`), a positive amount and a `movement_type`:

| Type | Meaning | Effect on the label |
|---|---|---|
| `allocation` | Initial distribution of the month | adds |
| `addition` | Amount added later, coming from outside the app | adds |
| `transfer_in` | Amount coming in from another label | adds |
| `transfer_out` | Amount going out to another label | subtracts |

**Label total = allocation + addition + transfer_in − transfer_out.**

Invariants:

1. `amount` is always `NUMERIC(14,2)` and strictly positive. The sign comes from the type. Never use `float`.
2. An `addition` also creates an income record (`incomes`) linked by `income_id`, so the month's income goes up by the same amount.
3. A transfer is **always a pair** of entries (`transfer_out` + `transfer_in`) with the same `transfer_id`, same amount, same date and different labels, created in a single database transaction.
4. Deleting or editing one leg of a transfer affects both (atomically).
5. Taking money out of a label is always a transfer to another label. Money never disappears without a destination. Mistakes are fixed by editing or deleting the entry (with undo).
6. The month total is invariant to transfers: the sum of `transfer_in` and `transfer_out` in a month is always equal.
7. **Unallocated** = total month income − sum of (`allocation` + `addition`). Additions raise both sides by the same amount, so they do not change the unallocated amount.
8. A saving or investment label may end a month with a negative balance (it means accumulated money was used). Net worth evolution uses balances **accumulated** across months.
9. Every entry shows its origin (initial distribution, external income, transferred from X) and its date, so the changes during the month are visible.

### 2.3 Months

- One month per user per year/month (`UNIQUE(user_id, year, month)`).
- On creation: option to copy the previous month's structure (same labels, blank or copied amounts).
- A **closed** month rejects any write (entries, incomes, transfers) until it is reopened.
- Optional note on the month and on each entry.
- Several incomes per month (salary, extra...).

### 2.4 Cross-cutting

- **Isolation:** each user only accesses their own data. Every query filters by `user_id`; dedicated tests try to access another user's data.
- **Soft delete** on entries, months, labels and goals (`deleted_at`). Deleting shows a toast with "undo". Double confirmation only for truly destructive actions (delete account, delete a label with entries).
- **Audit log** of creation, update and deletion of entries, months and labels.
- **One currency per user** in the MVP. Multi-currency is out of scope.
- Amounts rounded and formatted consistently (backend and frontend).

## 3. Scope: MVP and V2

**MVP:** users and profile; labels with kind; months; incomes; entries and transfers; home with donut and month picker; filters and totals by label and period; limits with alerts (fixed 80% and 100% thresholds); goals and emergency fund; receipts; closed month; demo mode.

**V2:** configurable limit thresholds; chart customization; investments by type (ETF, pension plan...) with entry splitting; month-over-month and year-over-year comparisons; net worth evolution; advanced CSV/PDF export; text search in notes; email alerts; bank statement CSV import.

## 4. Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| Frontend | Angular (recent stable), standalone components, Signals, new control flow (`@if`, `@for`), ECharts (ngx-echarts) |
| Database | PostgreSQL |
| Cache and rate limiting | Redis |
| Messaging | RabbitMQ (domain events and Celery broker) |
| Tasks | Celery + Celery beat |
| Auth | JWT with refresh token in an HttpOnly cookie; Google OAuth (Authlib) |
| Files | S3-compatible storage locally, Azure Blob Storage in production (signed URLs) |
| Email | Mailpit in dev, Azure Communication Services or Resend in production |
| AI | Claude API (financial chat and insights, with tool use over the report queries) |
| Real time | WebSockets or SSE (alerts) |
| Tests | pytest, pytest-asyncio, testcontainers, Ruff, mypy; Vitest; Playwright |
| Observability | Prometheus, Grafana, structlog, OpenTelemetry, Application Insights |
| Infra | Docker, Docker Compose, Kubernetes (Helm), Terraform, Azure (AKS, ACR, Key Vault, PostgreSQL Flexible Server, Blob Storage) |
| CI/CD | GitHub Actions (Azure login via OIDC) |

## 5. Repository layout (monorepo)

```
finnancial-system/
├── CLAUDE.md
├── README.md
├── docs/
│   ├── ARCHITECTURE.md        # this document
│   ├── DECISIONS.md           # decisions that refine this plan
│   ├── adr/                   # Architecture Decision Records
│   └── diagrams/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/              # config, security, logging
│   │   ├── db/                # session, base, column types
│   │   ├── domain/            # pure business rules (no FastAPI, no database)
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic
│   │   ├── repositories/      # data access
│   │   ├── services/          # use cases
│   │   ├── api/v1/            # routers
│   │   ├── events/            # publishers, consumers, outbox
│   │   └── workers/           # Celery tasks
│   ├── alembic/               # migrations
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/app/
│   │   ├── core/              # auth, interceptors, guards
│   │   ├── shared/            # components, design tokens, pipes
│   │   ├── features/          # auth, months, labels, dashboard, goals...
│   │   └── app.routes.ts
│   ├── e2e/                   # Playwright
│   └── Dockerfile
├── deploy/
│   ├── docker-compose.yml
│   ├── helm/                  # charts: api, worker, consumers, frontend
│   └── terraform/             # azure
└── .github/workflows/         # backend.yml, frontend.yml, cd.yml
```

Architecture principle: **business rules live in `domain/` and `services/`**, not in routers or models. That makes them testable without HTTP or a database.

## 6. Data model (summary)

```
users              id, email, password_hash, name, avatar_url, currency, locale, timezone,
                   email_verified_at, google_id, deleted_at
refresh_tokens     id, user_id, family_id, token_hash, expires_at, revoked_at, replaced_by_id
labels             id, user_id, name, kind (expense|saving|investment), color, icon,
                   is_default, archived_at, deleted_at
months             id, user_id, year, month, note, closed_at, deleted_at   UNIQUE(user_id, year, month)
incomes            id, user_id, month_id, source, amount, received_on, note, deleted_at
entries            id, user_id, month_id, label_id, amount, movement_type, transfer_id (nullable),
                   income_id (nullable), occurred_on, note, deleted_at
attachments        id, user_id, entry_id (nullable), month_id, storage_key, filename, mime, size
limits             id, user_id, label_id, month_id (nullable = default), amount
alerts             id, user_id, limit_id, level (warning|exceeded), seen_at, created_at
goals              id, user_id, label_id, target_amount, deadline, type (normal|emergency_fund),
                   manual_progress (nullable), completed_at, deleted_at
chart_preferences  id, user_id, chart_type, label_ids
audit_log          id, user_id, entity, entity_id, action, before (jsonb), after (jsonb), created_at
outbox_events      id, type, payload (jsonb), created_at, published_at
# V2: investment_types, entry_investments
```

Essential indexes: `entries(user_id, occurred_on)`, `entries(user_id, label_id, occurred_on)`, `entries(transfer_id)`, `months(user_id, year, month)`. Constraints: `CHECK (amount > 0)`, `CHECK` for consistency between `movement_type` and `transfer_id`.

## 7. Event flow (target)

```
Angular → FastAPI → writes to PostgreSQL + writes an event to the outbox table (same transaction)
                       │
                  relay publishes to RabbitMQ
                       ├─ consumer "limits" : recomputes limits and creates alerts
                       ├─ consumer "cache"  : invalidates the dashboard cache (Redis)
                       ├─ consumer "goals"  : updates goal progress
                       └─ consumer "emails" : sends email alerts (V2)

Celery beat / CronJob → creates recurring entries at the start of each month
Celery workers        → PDF/CSV exports, GDPR, emails
```

Events: `EntryCreated`, `EntryUpdated`, `EntryDeleted`, `TransferCreated`, `MonthClosed`, `MonthReopened`. Consumers are **idempotent** (the same message processed twice cannot duplicate effects). Messages that fail repeatedly go to a dead-letter queue.

---

## 8. Implementation phases

General rule: every phase ends with **code, tests and minimal documentation**, and a green CI. Do not start the next phase before that.

### Phase 0: Repository foundation

**Goal:** reproducible environment and a minimal pipeline.

**Deliverables**

- Monorepo layout (section 5), `README.md` and `CLAUDE.md`
- `docker-compose.yml` with PostgreSQL, Redis, RabbitMQ (with management UI), S3-compatible storage and Mailpit; healthchecks on all of them
- Minimal FastAPI backend with `/health`, configuration through environment variables (pydantic-settings), structured logging
- Generated Angular frontend serving a home page
- Ruff, mypy, pre-commit; pytest configured
- GitHub Actions: lint, type-check and backend tests; frontend lint/build
- Backend and frontend Dockerfiles

**Acceptance criteria**

- `docker compose up` starts the whole stack with no manual steps
- `GET /health` answers 200 and CI passes on push

### Phase 1: Database and authentication

**Goal:** real users and the base model migrated.

**Deliverables**

- Async SQLAlchemy + Alembic; initial migration with `users`, `labels`, `months`, `incomes`, `entries`, `audit_log` and the constraints/indexes from section 6
- Sign-up with email and password (argon2 or bcrypt hash), login, logout, refresh token (HttpOnly cookie), refresh rotation
- `get_current_user` dependency used by every protected router
- Profile editing (name, currency, language, time zone) and password change
- Creation of the default labels (with kind) at sign-up
- Integration tests with testcontainers (real PostgreSQL)

**Acceptance criteria**

- Sign-up → login → refresh → logout flow tested
- A test proving a user cannot access another user's resources
- Migrations upgrade and downgrade without errors

### Phase 2: Domain core (labels, months, entries)

**Goal:** implement the rules from section 2. This is the most important phase.

**Deliverables**

- Labels CRUD (kind, color, icon, archive, reassign on delete)
- Months CRUD, with copy from the previous month and close/reopen
- Incomes CRUD per month
- Initial distribution (`allocation`) per label
- Create `addition` (with its income) and transfers (atomic pair with `transfer_id`)
- Soft delete with a restore endpoint (for "undo")
- Audit log on every write
- Pure `domain/` layer with the rules and the computation of totals and "unallocated"

**Acceptance criteria**

- Unit tests for every invariant in sections 2.2 and 2.3, including: a closed month rejects writes; a transfer is always a pair; deleting one leg deletes both; the month total is invariant to transfers; Food 200 + 12 = 212; unallocated is correct after an addition
- No calculation uses float

### Phase 3: Reports and aggregations

**Goal:** answer questions by period.

**Deliverables**

- Month summary endpoint: total per label, total per kind, origin of each part (base + adjustments), unallocated
- Report endpoint with optional filters: by label, by kind and by period, with a total and the list of entries
- Time series per label (evolution across months)
- Optimized queries and indexes validated with `EXPLAIN`
- A single `ReportService`, later reused by the Claude chat

**Acceptance criteria**

- Tests with fixed data proving the totals, including labels with transfers
- "Water spending in the last 6 months" returns the right amount

### Phase 4: Frontend foundation

**Goal:** a navigable app with authentication and data entry.

**Deliverables**

- Responsive layout (phone, tablet, desktop), dark mode, i18n
- Design tokens as CSS variables: `--kind-expense`, `--kind-saving`, `--kind-investment` (with dark variants) and a `MoneyAmount` component that applies color, icon and text per kind
- Auth: sign-up, login, interceptor with refresh, guards
- Label management (create with the kind question, color, icon)
- Month screen: initial distribution, list of entries by date with origin, quick entry form, "add money" flow that asks for the origin (external source or another label)
- Toast with "undo" after deleting
- Typed HTTP client generated from the backend OpenAPI

**Acceptance criteria**

- Sign up, create a month, distribute €1000 and add €50 from an external source and €50 from Savings, with everything reflected correctly
- Usable on a phone screen

### Phase 5: Dashboard and charts

**Goal:** the overview that gives the product its identity.

**Deliverables**

- Home with the latest month by default and a month picker
- Three totals at the top (spent, saved, invested) and unallocated
- Donut by kind and, on click, by label; sorted bars; evolution line for one label
- Filters by label and period with an updated total and list
- "Base + adjustments" view per label (stacked bar or timeline)
- Text alternative (table) for every chart

**Acceptance criteria**

- Dashboard values match the Phase 3 endpoints
- Contrast and keyboard navigation checked on the charts

### Phase 6: E2E tests and full CI

**Deliverables**

- Playwright: sign up, log in, create a month, distribute, add money, transfer, close the month, view the dashboard
- CI with testcontainers, coverage badge in the README and Playwright running against the Docker Compose stack
- Pre-commit and protection of the main branch

**Acceptance criteria:** full pipeline green on a pull request.

### Phase 7: Redis, RabbitMQ, Celery and outbox

**Goal:** event-driven architecture.

**Deliverables**

- Redis cache for summaries and reports, keyed by user and period; rate limiting on auth endpoints
- `outbox_events` table written in the same transaction as entries; relay that publishes to RabbitMQ
- Exchange with separate queues and a dead-letter queue; idempotent `cache`, `limits` and `goals` consumers
- Celery + beat: recurring entries (rent, salary) created at the start of the month; base async tasks
- Separate processes in Compose: api, worker, beat, consumers

**Acceptance criteria**

- Creating an entry invalidates the cache and the next read returns the updated value
- Reprocessing the same message does not duplicate effects (test)
- If a consumer fails, the entry stays saved and the message is reprocessed

### Phase 8: Limits, alerts, goals and emergency fund

**Deliverables**

- Limits per label and month, with warnings at 80% and 100% (fixed in the MVP)
- Alerts created by the `limits` consumer and pushed to the UI via WebSocket or SSE
- Goals (label, target amount, deadline) with progress, time left and "you need to save €X/month"
- Emergency fund as a special goal: target in "N months of expenses", computed from average spending (expense labels)
- Completed goals kept in history

**Acceptance criteria:** unit tests for the calculations (percentages, pace, average expenses) and an alert showing in the UI without reloading.

### Phase 9: Receipts, export, GDPR and email

**Deliverables**

- Photo/PDF upload linked to an entry and a month, stored in S3 with signed URLs and type/size validation; view, download and remove
- CSV and PDF export by period and labels (Celery task, file in storage, download link)
- Data export and account deletion (GDPR)
- Email verification and password recovery (Mailpit in dev)

**Acceptance criteria:** a user cannot access another user's attachments, not even with a guessed URL.

### Phase 10: Google OAuth and demo mode

**Deliverables**

- Google login (Authlib), linking to an existing account by verified email
- TOTP 2FA (optional)
- Demo account with realistic preloaded data (several months, transfers, goals), reset by a scheduled task, reachable through a "Try it" button

### Phase 11: AI with Claude

**Goal:** a read and analysis layer. Data entry stays manual.

**Deliverables**

- Financial chat with tool use over the `ReportService` (tools: month summary, report by label and period, evolution, goals). The model never receives free SQL nor other users' data
- Month insights generated when the month is closed (consumer of the `MonthClosed` event)
- Label suggestion while typing an entry description (optional)
- API key as a secret, per-user rate limit, timeout and error handling
- Tests with a mocked API client

**Acceptance criteria:** "how much did I invest in the last 2 months?" returns the same amount as the Phase 3 report.

### Phase 12: Observability

**Deliverables**

- Prometheus metrics on the API (requests, latency, errors) and on the queues (size, failures)
- Grafana dashboards in the repository (provisioning)
- OpenTelemetry and Sentry; structured logs with `request_id`
- Prometheus and Grafana in Compose

### Phase 13: Local Kubernetes

**Deliverables**

- Local cluster with kind or k3d
- Helm charts: api, worker, consumers, frontend; RabbitMQ and Redis via existing charts
- Separate deployments, liveness and readiness probes, resource limits, ConfigMaps and Secrets
- CronJob for recurring entries, HPA on the workers, NGINX Ingress
- kube-prometheus-stack for metrics

**Acceptance criteria:** `helm install` brings up the full application on the local cluster.

### Phase 14: Azure, Terraform and CD

**Deliverables**

- Terraform: resource group, ACR, AKS, PostgreSQL Flexible Server, Key Vault, Storage Account, network
- Workload Identity so pods read secrets from Key Vault
- `cd.yml`: build images, push to ACR and `helm upgrade` on AKS, with Azure login via OIDC (no static secrets)
- Ingress with HTTPS (cert-manager) and a domain
- Environment that can be destroyed and recreated with Terraform (cost control)

**Acceptance criteria:** a merge into the main branch deploys automatically and the public URL answers over HTTPS.

### Phase 15: Portfolio polish

**Deliverables**

- Landing page with a demo and a security overview
- README with an architecture diagram (C4), GIFs, run instructions and badges (CI, coverage)
- ADRs for the main decisions (outbox, RabbitMQ vs Redis, Kubernetes, movement model)
- Security review (CORS, headers, rate limiting, dependencies)
- Accessibility and performance checked (Lighthouse)

### V2 phase (later)

Investments by type with entry splitting; month-over-month and year-over-year comparisons; net worth evolution; configurable limit thresholds; chart customization; text search; email alerts; bank statement CSV import.

---

## 9. Summary of the order

| Block | Phases | Result |
|---|---|---|
| Working product | 0 to 5 | Complete app running locally |
| Quality | 6 | Serious E2E tests and CI |
| Advanced architecture | 7 to 9 | Events, cache, limits, goals, attachments, exports |
| Differentiators | 10 to 11 | Google, demo mode, AI |
| Platform | 12 to 14 | Observability, Kubernetes, Azure, CD |
| Presentation | 15 | Landing page, README, ADRs |

The application is usable at the end of Phase 5; everything after that adds technical depth without blocking the product.
