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
| Contas | Email sem verificação por agora (só tem de ser um email válido). Passwords novas: mínimo 8 caracteres, com minúscula, maiúscula, número e caractere especial. |
| Moeda e locale | Só EUR no MVP (o campo `currency` existe para mudar mais tarde). Locale padrão `pt-PT`, fuso `Europe/Lisbon`. |

## Meses, entradas e relatórios (2026-10-26)

| Tema | Decisão |
|---|---|
| Copiar mês anterior | Opcional ao criar: copia a distribuição inicial e/ou os rendimentos do último mês existente. O que é copiado são entradas normais, editáveis depois (ex.: Mercado passa de 200 € para 220 €). |
| Mês fechado | Bloqueia todas as escritas, incluindo a nota. Pode sempre ser reaberto, editado e fechado outra vez. |
| Eliminar mês | Soft delete do mês; as entradas ficam escondidas com ele e voltam com o "desfazer". |
| Acrescentar dinheiro | Valor que chega a meio do mês (ex.: +50 € para Investimento) é um `addition`: soma à etiqueta e ao rendimento do mês. |
| Por distribuir negativo | Permitido; a UI só avisa. |
| Filtros de relatório | Período (mês, semestre, ano) combinado opcionalmente com etiquetas ou tipos. Sem filtro de etiqueta, mostra todas juntas. |

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

## Frontend: identidade visual (2026-10-26)

O visual atual (Angular Material, Roboto, Material Symbols) parece Google/Gmail e **vai ser repaginado**. Requisitos: identidade própria do FinnancialSystem, sem copiar templates, layouts nem o aspeto de outros produtos, e sem Google Fonts. A direção visual será definida em conjunto antes de avançar com os ecrãs.

## Estrutura e ferramentas

- Monorepo: `backend/`, `frontend/`, `deploy/`, `docs/`, `.github/workflows/`.
- Backend em `backend/app/` com as camadas `core`, `db`, `domain`, `models`, `schemas`, `repositories`, `services`, `api/v1` (e `events`, `workers` a partir da Fase 7).
- Dependências Python em `requirements.txt` (runtime) e `requirements-dev.txt` (testes e lint). O `pyproject.toml` só guarda a configuração de Ruff, mypy e pytest.
- SQLAlchemy 2.0 async com `asyncpg`.
- Testes de integração com testcontainers (PostgreSQL real); precisam do Docker a correr.
- Frontend: Angular (última versão estável), standalone components, Signals, zoneless, novo control flow, Angular Material (M3) com design tokens em variáveis CSS, ECharts via ngx-echarts.
- Armazenamento de ficheiros em dev: SeaweedFS (S3 compatível) em vez de MinIO, porque as imagens Docker do MinIO deixaram de ser públicas. O código fala S3, por isso produção continua em Azure Blob (via gateway S3 ou SDK próprio, a decidir na Fase 9).
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
