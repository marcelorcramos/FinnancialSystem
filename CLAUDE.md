# FinnancialSystem

Ler docs/ARCHITECTURE.md e docs/DECISIONS.md antes de qualquer tarefa. O DECISIONS.md prevalece em caso de conflito. Implementar uma fase de cada vez.

## Regras
- Valores monetários: NUMERIC(14,2) na BD e Decimal em Python. Nunca float.
- IDs são UUID.
- Regras de negócio em backend/app/domain e services, nunca em routers ou modelos.
- Toda query filtra por user_id. Cada endpoint novo precisa de teste de isolamento.
- Soft delete (deleted_at) em vez de DELETE. Escritas geram audit_log.
- Transferências são sempre pares atómicos com o mesmo transfer_id.
- Mês fechado rejeita escritas.
- Consumers RabbitMQ têm de ser idempotentes.
- Escrever testes antes de dar a tarefa por concluída.
- Commit a cada funcionalidade concluída, no branch da área (backend, frontend, infra).

## Comandos
- Subir stack: docker compose -f deploy/docker-compose.yml up
- Testes backend: cd backend && pytest
- Lint backend: cd backend && ruff check . && ruff format --check . && mypy app
- Migrações: cd backend && alembic upgrade head
- Testes E2E: cd frontend && npx playwright test
