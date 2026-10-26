# Decisões do projeto

Decisões tomadas sobre o que o `docs/ARCHITECTURE.md` deixa em aberto ou que o ajustam. Em caso de conflito, este ficheiro prevalece.

## Dados e domínio (2026-10-26)

| Tema | Decisão |
|---|---|
| IDs | UUID em todas as tabelas (gerados no Python, `uuid.uuid4`). Não ficam adivinháveis em URLs e anexos. |
| Migrações | Não há dados reais: a migração inicial é recriada do zero com o modelo completo da secção 6. |
| Etiquetas padrão | Cada utilizador recebe a sua própria cópia no registo (`labels.user_id` nunca é nulo). O utilizador pode mudar nome, cor e ícone. |
| Data do movimento | `occurred_on` tem de cair dentro do ano/mês do mês a que a entrada pertence (validado no domínio). A data do dia é informativa: os filtros e relatórios agregam sempre por **mês, semestre ou ano**. |
| Distribuição inicial | No máximo uma `allocation` por etiqueta e mês, editável (índice único parcial). |
| Refresh tokens | Tabela `refresh_tokens` (hash do token, família, `expires_at`, `revoked_at`, `replaced_by_id`). Rotação a cada refresh; reutilizar um token já rodado revoga a família inteira. |
| Admin | Fica para mais tarde. Não há rotas que listem ou editem outros utilizadores. |
| Moeda e locale | Só EUR no MVP (o campo `currency` existe para mudar mais tarde). Locale padrão `pt-PT`, fuso `Europe/Lisbon`. |

### Etiquetas padrão

| Nome | Tipo | Cor | Ícone (Material Symbols) |
|---|---|---|---|
| Aluguel | expense | `#E57373` | `home` |
| Mercado | expense | `#FFB74D` | `shopping_cart` |
| Água | expense | `#4FC3F7` | `water_drop` |
| Luz | expense | `#FFD54F` | `bolt` |
| Transporte | expense | `#9575CD` | `directions_bus` |
| Poupança | saving | `#66BB6A` | `savings` |
| Fundo de emergência | saving | `#26A69A` | `health_and_safety` |
| Investimento | investment | `#42A5F5` | `trending_up` |

## Estrutura e ferramentas

- Monorepo: `backend/`, `frontend/`, `deploy/`, `docs/`, `.github/workflows/`.
- Backend em `backend/app/` com as camadas `core`, `db`, `domain`, `models`, `schemas`, `repositories`, `services`, `api/v1` (e `events`, `workers` a partir da Fase 7).
- Dependências Python em `requirements.txt` (runtime) e `requirements-dev.txt` (testes e lint). O `pyproject.toml` só guarda a configuração de Ruff, mypy e pytest.
- SQLAlchemy 2.0 async com `asyncpg`.
- Testes de integração com testcontainers (PostgreSQL real); precisam do Docker a correr.
- Frontend: Angular (última versão estável), standalone components, Signals, zoneless, novo control flow, Angular Material (M3) com design tokens em variáveis CSS, ECharts via ngx-echarts.
- CI separado por área: `.github/workflows/backend.yml` e `frontend.yml`.

## Contrato da API de autenticação

Prefixo `/api/v1`. O access token vai no corpo da resposta e é enviado em `Authorization: Bearer`. O refresh token vai num cookie `refresh_token` (HttpOnly, SameSite=Lax, `Path=/api/v1/auth`, `Secure` fora de dev).

| Método | Rota | Corpo | Resposta |
|---|---|---|---|
| POST | `/auth/register` | `{email, password, name}` | 201 `UserRead` |
| POST | `/auth/login` | `{email, password}` | 200 `{access_token, token_type, expires_in}` + cookie |
| POST | `/auth/refresh` | (cookie) | 200 `{access_token, token_type, expires_in}` + cookie novo |
| POST | `/auth/logout` | (cookie) | 204, cookie apagado |
| GET | `/users/me` | | 200 `UserRead` |
| PATCH | `/users/me` | `{name?, currency?, locale?, timezone?}` | 200 `UserRead` |
| POST | `/users/me/password` | `{current_password, new_password}` | 204 |

`UserRead` = `{id, email, name, avatar_url, currency, locale, timezone, email_verified_at}`.

## Forma de trabalhar

- Branches por área: `backend`, `frontend` e mais tarde `infra` (cloud/Kubernetes). Merge para `main` por pull request.
- Commit a cada funcionalidade concluída, no branch da área, com testes a passar.
