# FinnancialSystem

Read docs/ARCHITECTURE.md and docs/DECISIONS.md before any task; docs/API.md is the API contract. DECISIONS.md wins when they disagree. Implement one phase at a time.

## Rules
- Everything in the repository is in English: code, comments, docs, API messages, seed data, commits.
- Money: NUMERIC(14,2) in the database and Decimal in Python. Never float.
- IDs are UUIDs.
- Business rules live in backend/app/domain and services, never in routers or models.
- Every query filters by user_id. Every new endpoint needs an isolation test.
- Soft delete (deleted_at) instead of DELETE. Writes produce audit_log rows.
- Transfers are always atomic pairs sharing the same transfer_id.
- A closed month rejects writes.
- RabbitMQ consumers must be idempotent.
- Write tests before calling a task done.
- Commit after every finished feature, on the area branch (backend, frontend, infra).

## Commands
- Start the stack: docker compose -f deploy/docker-compose.yml up
- Backend tests: cd backend && pytest
- Backend lint: cd backend && ruff check . && ruff format --check . && mypy app
- Migrations: cd backend && alembic upgrade head
- E2E tests: cd frontend && npx playwright test
