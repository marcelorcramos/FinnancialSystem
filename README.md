# FinnancialSystem

[![backend](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/backend.yml/badge.svg?branch=main)](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/backend.yml)
[![frontend](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/frontend.yml/badge.svg?branch=main)](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/frontend.yml)
[![e2e](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/e2e.yml/badge.svg?branch=main)](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/e2e.yml)
![backend coverage](https://github.com/marcelorcramos/FinnancialSystem/blob/badges/coverage.svg?raw=true)

A personal finance app that works month by month: each month's income is distributed across labels (Food, Housing, Savings, Investments…), money can be added or moved between labels, and reports answer questions such as "how much did I spend on water in the last 6 months?".

## Stack

- **Backend:** FastAPI (async), SQLAlchemy 2, PostgreSQL, Alembic. Money is `NUMERIC(14,2)` / `Decimal`, never float.
- **Frontend:** Angular (zoneless, signals), own SVG charts, Vitest, Playwright.
- **Infrastructure:** Docker Compose; Redis, RabbitMQ and Celery come in Phase 7.

## Run it

```sh
docker compose -f deploy/docker-compose.yml up --build
```

The app is on http://localhost:8080 and the API docs on http://localhost:8000/docs.

## Tests

| What | Command |
|---|---|
| Backend tests (PostgreSQL via testcontainers, 95% coverage floor) | `cd backend && pytest --cov=app` |
| Backend lint | `cd backend && ruff check . && ruff format --check . && mypy app` |
| Frontend unit tests and lint | `cd frontend && npm run test:ci && npm run lint` |
| End-to-end, against the running stack | `cd frontend && npx playwright test` |

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): product, domain rules and the implementation phases.
- [`docs/DECISIONS.md`](docs/DECISIONS.md): decisions made along the way; they win over the architecture document.
- [`docs/API.md`](docs/API.md): the API contract.
- [`docs/QUERY_PLANS.md`](docs/QUERY_PLANS.md): how the report queries were validated with `EXPLAIN`.
- [`docs/FUTURE_IMPLEMENTATIONS.md`](docs/FUTURE_IMPLEMENTATIONS.md): ideas left for later.
