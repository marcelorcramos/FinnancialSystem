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
| Report filters | Two independent, optional filters: **category** (one or more labels, or a kind) and **time**. Time is one month, a "semester" = the last 6 months up to the reference month (rolling window, not Jan–Jun/Jul–Dec), or a calendar year ("how much did I invest this year?"). No time filter = since the first record. No category filter = all labels together. |

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

## Frontend: visual identity (2026-10-26)

The current look (Angular Material, Roboto, Material Symbols) feels like Google/Gmail and **will be redesigned**. Requirements: a FinnancialSystem identity of its own, without copying templates, layouts or the look of other products, and without Google Fonts. The visual direction will be agreed before building the screens.

## Structure and tooling

- Monorepo: `backend/`, `frontend/`, `deploy/`, `docs/`, `.github/workflows/`.
- Backend in `backend/app/` with the layers `core`, `db`, `domain`, `models`, `schemas`, `repositories`, `services`, `api/v1` (plus `events` and `workers` from Phase 7).
- Python dependencies in `requirements.txt` (runtime) and `requirements-dev.txt` (tests and lint). `pyproject.toml` only holds Ruff, mypy and pytest configuration.
- SQLAlchemy 2.0 async with `asyncpg`.
- Integration tests with testcontainers (real PostgreSQL); Docker must be running.
- Frontend: Angular (latest stable), standalone components, Signals, zoneless, new control flow, ECharts via ngx-echarts.
- Dev file storage: SeaweedFS (S3-compatible) instead of MinIO, because MinIO Docker images are no longer public. The code speaks S3, so production can still use Azure Blob (through an S3 gateway or its own SDK, decided in Phase 9).
- CI split by area: `.github/workflows/backend.yml` and `frontend.yml`.
- Node 24 for the frontend (Angular 22 needs Node ≥ 22.22).

## Authentication API contract

Prefix `/api/v1`. The access token is returned in the response body and sent as `Authorization: Bearer`. The refresh token lives in a `refresh_token` cookie (HttpOnly, SameSite=Lax, `Path=/api/v1/auth`, `Secure` outside dev).

| Method | Route | Body | Response |
|---|---|---|---|
| POST | `/auth/register` | `{email, password, name}` | 201 `UserRead` |
| POST | `/auth/login` | `{email, password}` | 200 `{access_token, token_type, expires_in}` + cookie |
| POST | `/auth/refresh` | (cookie) | 200 `{access_token, token_type, expires_in}` + new cookie |
| POST | `/auth/logout` | (cookie) | 204, cookie cleared |
| GET | `/users/me` | | 200 `UserRead` |
| PATCH | `/users/me` | `{name?, currency?, locale?, timezone?}` | 200 `UserRead` |
| POST | `/users/me/password` | `{current_password, new_password}` | 204 |

`UserRead` = `{id, email, name, avatar_url, currency, locale, timezone, email_verified_at}`.

`POST /auth/token` (form, hidden from the schema) exists only for the Swagger Authorize button.

## Ways of working

- One branch per area: `backend`, `frontend` and later `infra` (cloud/Kubernetes). Merged into `main` through pull requests.
- Commit after every finished feature, on the area branch, with tests passing.
