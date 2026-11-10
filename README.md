# FinnancialSystem

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.162-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.1-D71F00?logo=sqlalchemy&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Angular](https://img.shields.io/badge/Angular-22-DD0031?logo=angular&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?logo=typescript&logoColor=white)
![RxJS](https://img.shields.io/badge/RxJS-7.8-B7178C?logo=reactivex&logoColor=white)
![nginx](https://img.shields.io/badge/nginx-1.29-009639?logo=nginx&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-FF4438?logo=redis&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-4-FF6600?logo=rabbitmq&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.6-37814A?logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker_Compose-2496ED?logo=docker&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.64-2EAD33?logo=playwright&logoColor=white)
![Vitest](https://img.shields.io/badge/Vitest-5-6E9F18?logo=vitest&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white)

[![backend](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/backend.yml/badge.svg?branch=main)](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/backend.yml)
[![frontend](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/frontend.yml/badge.svg?branch=main)](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/frontend.yml)
[![e2e](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/e2e.yml/badge.svg?branch=main)](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/e2e.yml)
![backend coverage](https://github.com/marcelorcramos/FinnancialSystem/blob/badges/coverage.svg?raw=true)

A personal finance app built around one simple habit: **plan each month, then see where the money really went.**

Every month is a sheet. You record what came in, split it across labels such as Food, Housing, Savings or Investments, and log what changes along the way. The app keeps every euro accounted for and answers questions like *"how much did I spend on water in the last 6 months?"* or *"how much did I invest this year?"* in a couple of clicks.

Everything is entered by hand: no bank connections, no bots, no guessing.

## How it works

### Months

Each month has its incomes (salary, extras…) and an initial distribution of that money across your labels. A new month can copy the previous one, so you only review what changed: every label shows last month's value next to the new one, adjustable with −/+ or by typing. If you prefer, the app can start each month on its own, at midnight in your time zone, with the same distribution and recurring incomes (rent, salary).

Whatever you have not distributed yet shows up as **unallocated**. When the month is over you **close** it, and a closed month accepts no more changes until you reopen it.

### Labels and kinds

Every label belongs to one of three kinds, and the kind gives its amounts their meaning and color:

| Kind | Color | Examples |
|---|---|---|
| Expense | soft red | Food, Housing, Water, Transport |
| Saving | green | Savings, Emergency Fund |
| Investment | blue | Investments, an ETF, a pension plan |

New accounts start with a sensible set of default labels; you can rename them, recolor them, pick icons, create your own, archive them, or delete one and move its entries to another label.

### Money always has a destination

A label shows the sum of everything put into it. If Food got €200 and later €12 more, it shows €212. Money moves in exactly four ways:

| Movement | What it means |
|---|---|
| Allocation | The initial distribution of the month |
| Addition | Money that arrived from outside the app mid-month; it raises the month's income too |
| Transfer in / out | Money moved from one label to another, always recorded as a matched pair |

Money never simply disappears: taking it out of a label means sending it somewhere else. Mistakes are fixed by editing or deleting an entry, and every delete can be undone.

### Reports

The month screen and the Reports page show the same picture from different angles:

- **Totals** for income, spent, saved, invested and unallocated.
- **Donut** of the distribution, by kind (Overview) or by label (Detailed).
- **Sorted bars** per label, showing the base amount plus what was added, moved in and moved out.
- **Evolution line** of a label or a selection across months, with the monthly average and the change since the start.
- **Entries behind the totals**, each with its date and origin.

Filters combine freely: pick labels and/or kinds and a period (this month, last 6 or 12 months, all time). The filters live in the URL, so a report can be bookmarked.

### Accessible by design

Color is never the only signal: amounts always carry an icon and text, charts can use patterns, and every chart has a table view and keyboard access. Theme (dark, light or system), text size, high contrast and reduced motion are all preferences. Keyboard shortcuts cover the month screen (new entry, transfer, previous/next month, undo).

### Safe by default

Each user sees only their own data, and tests try to break that on every endpoint. Amounts are exact decimals, never floating point. Nothing is hard-deleted, and every change is written to an audit log. Sessions use short-lived access tokens with rotating refresh tokens, and repeated sign-in attempts are slowed down.

## Status

The core product works end to end: accounts, labels, months, entries, transfers, reports and the dashboard, covered by unit, integration and end-to-end tests. Behind it, summaries and reports are cached in Redis, every change is published as an event through RabbitMQ (transactional outbox, idempotent consumers), and Celery starts new months for those who opt in. Limits raise live alerts, goals track their pace, and the emergency fund follows your spending. Receipts are kept privately in S3-compatible storage, reports export as CSV or PDF, your whole account downloads as a ZIP or is deleted for good, and emails confirm addresses and recover passwords.

Next on the roadmap: Google sign-in with a demo mode, an AI chat over your reports, observability, and deployment to Kubernetes and Azure. The full plan is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Run it

You only need Docker:

```sh
docker compose -f deploy/docker-compose.yml up --build
```

Then open the app at http://localhost:8080. The API and its interactive docs are at http://localhost:8000/docs.

## Tests

| What | Command |
|---|---|
| Backend tests (real PostgreSQL, Redis and RabbitMQ via testcontainers) | `cd backend && pytest --cov=app` |
| Backend lint and types | `cd backend && ruff check . && ruff format --check . && mypy app` |
| Frontend unit tests and lint | `cd frontend && npm run test:ci && npm run lint` |
| End-to-end, against the running stack | `cd frontend && npx playwright test` |

## Project layout

```
backend/    FastAPI API: domain rules, services, repositories, migrations, tests
frontend/   Angular app and Playwright end-to-end tests
deploy/     Docker Compose stack
docs/       Architecture, decisions, API contract
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): product, domain rules and the implementation phases.
- [`docs/DECISIONS.md`](docs/DECISIONS.md): decisions made along the way; they win over the architecture document.
- [`docs/API.md`](docs/API.md): the API contract.
- [`docs/QUERY_PLANS.md`](docs/QUERY_PLANS.md): how the report queries were validated with `EXPLAIN`.
- [`docs/FUTURE_IMPLEMENTATIONS.md`](docs/FUTURE_IMPLEMENTATIONS.md): ideas left for later.

## License

[MIT](LICENSE)
