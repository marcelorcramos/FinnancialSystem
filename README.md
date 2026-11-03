# FinnancialSystem

[![backend](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/backend.yml/badge.svg?branch=main)](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/backend.yml)
[![frontend](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/frontend.yml/badge.svg?branch=main)](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/frontend.yml)
[![e2e](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/e2e.yml/badge.svg?branch=main)](https://github.com/marcelorcramos/FinnancialSystem/actions/workflows/e2e.yml)
![backend coverage](https://github.com/marcelorcramos/FinnancialSystem/blob/badges/coverage.svg?raw=true)

A personal finance app that works month by month: each month's income is distributed across labels (Food, Housing, Savings, Investments…), money can be added or moved between labels, and reports answer questions such as "how much did I spend on water in the last 6 months?".

## Technologies

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.162-009688?logo=fastapi&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-FF4438?logo=redis&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-4-FF6600?logo=rabbitmq&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.6-37814A?logo=celery&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Angular](https://img.shields.io/badge/Angular-22-DD0031?logo=angular&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?logo=typescript&logoColor=white)
![Docker](https://img.shields.io/badge/Docker_Compose-2496ED?logo=docker&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.64-2EAD33?logo=playwright&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=githubactions&logoColor=white)

### Backend

| Technology | Version | What it does here |
|---|---|---|
| Python | 3.12 | Language of the API |
| FastAPI + Uvicorn | 0.162 / 0.54 | Async REST API, OpenAPI docs at `/docs` |
| SQLAlchemy (async) + asyncpg | 2.1 / 0.32 | ORM and PostgreSQL driver; layered as api → services → domain → repositories |
| Alembic | 1.20 | Database migrations, applied when the API starts |
| Pydantic + pydantic-settings | 2.14 / 2.16 | Request and response schemas (money as `Decimal`), configuration from the environment |
| PyJWT + argon2-cffi | 2.15 / 25.1 | Short-lived access tokens, rotating refresh tokens in an HttpOnly cookie, Argon2 password hashes |
| structlog | 26.1 | Structured logs (JSON outside development) |
| aio-pika | 10.1 | Outbox relay and idempotent event consumers (`cache`, `limits`, `goals`) |
| Celery + Celery beat | 5.6 | Background tasks; beat starts each new month from the previous one (opt-in) |
| redis-py | 8.1 | Async Redis client for the cache and the rate limits |

### Frontend

| Technology | Version | What it does here |
|---|---|---|
| Angular | 22 | Standalone components, zoneless change detection and signals |
| Angular CDK | 22 | Accessible dialogs and menus |
| TypeScript | 6.0 | Strict typing; API types generated from the backend OpenAPI with openapi-typescript |
| RxJS | 7.8 | HTTP and the auth refresh flow |
| Own SVG charts | | Donut, line and bar charts with keyboard access and text alternatives |
| nginx | 1.29 | Serves the built app and proxies `/api` in the container |

### Data and infrastructure

| Technology | Version | What it does here |
|---|---|---|
| PostgreSQL | 16 | Main database: `NUMERIC(14,2)` money, UUID keys, soft delete, audit log |
| Docker + Docker Compose | | The whole stack locally (`deploy/docker-compose.yml`): API, web, outbox relay, one process per consumer, Celery worker and beat, with healthchecks on the services |
| Redis | 7 | Per-user cache of summaries and reports, and rate limits on the auth routes (both fail open) |
| RabbitMQ | 4 | Domain events from the transactional outbox (topic exchange, quorum queues, dead-letter queue) and the Celery broker |
| SeaweedFS (S3-compatible) | 4.50 | In the stack for file exports (Phase 9) |
| Mailpit | 1.32 | Catches outgoing email in development |

### Quality and tests

| Technology | Version | What it does here |
|---|---|---|
| pytest + pytest-asyncio + httpx | | Backend unit and integration tests through the real ASGI app |
| testcontainers | 4.15 | Real PostgreSQL, Redis and RabbitMQ in the tests, locally and in CI |
| pytest-cov | | Coverage, with a 95% floor (99% today) |
| Ruff + mypy | | Python lint, formatting and strict type checks |
| Vitest + jsdom | 5 / 30 | Frontend unit tests |
| ESLint (angular-eslint) + Prettier | 10 / 3.8 | Frontend lint and formatting |
| Playwright | 1.64 | End-to-end tests on desktop and phone against the Compose stack |
| GitHub Actions | | `backend`, `frontend` and `e2e` workflows on every pull request, required to merge into `main` |
| pre-commit | | Ruff and file checks before each commit |

### Planned

Limits, alerts and goals on top of the event consumers (Phase 8), Kubernetes with Helm (Phase 13) and an AI chat over the reports with the Claude API (Phase 11). See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full plan.

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
