# FinnancialSystem: Arquitetura de Implementação

Documento de referência para guiar o desenvolvimento com o Claude Code. Define o produto, as regras de domínio, a stack, a estrutura do repositório e as fases de implementação, por ordem.

**Como usar com o Claude Code:** guarda este documento como `docs/ARCHITECTURE.md` no repositório, cria um `CLAUDE.md` na raiz a apontar para ele (ver secção 9) e pede **uma fase de cada vez**, por exemplo: "Implementa a Fase 2 do docs/ARCHITECTURE.md, cumprindo os critérios de aceitação". Não avances de fase sem os critérios cumpridos e os testes a passar.

---

## 1. Visão do produto

Plataforma de controlo financeiro pessoal. O utilizador trabalha por **mês** (uma "planilha" por mês) e distribui o dinheiro por **etiquetas** (Aluguel, Comida, Investimento, Poupança...). Os dados são **introduzidos manualmente** (sem bots, sem áudio, sem ligação a bancos).

A app responde a perguntas como "quanto gastei em água nos últimos 6 meses?" ou "quanto investi este ano?", e mostra tudo de forma visual e imediata.

## 2. Regras de domínio (invariantes)

Estas regras são a parte mais importante do projeto. Devem estar cobertas por testes automáticos e nunca podem ser violadas por nenhum endpoint, tarefa ou consumer.

### 2.1 Etiquetas e tipo

- Cada etiqueta tem um `kind`: `expense` (gasto), `saving` (poupança) ou `investment` (investimento).
- O tipo é perguntado na criação da etiqueta e determina a **cor semântica dos valores**: gasto em vermelho suave, poupança em verde, investimento em azul.
- A **cor da etiqueta** (escolhida pelo utilizador) é independente e serve de identidade em donuts, ícones e linhas de gráficos.
- A cor nunca é o único sinal: acompanhar sempre de ícone e texto (acessibilidade).
- Mudar o `kind` de uma etiqueta é permitido, mas altera retroativamente os relatórios; a UI deve avisar.
- Etiquetas padrão são criadas no registo, já com o tipo certo. Todas têm nome, cor e ícone.
- Etiqueta com entradas não se elimina: ou se arquiva, ou se reatribuem as entradas a outra etiqueta.

### 2.2 Movimentos (entradas)

Uma etiqueta mostra sempre a **soma de tudo o que foi posto nela**. Não há "consumo de orçamento": se Mercado tinha 200 € e se gastaram mais 12 €, mostra 212 €.

Cada movimento tem data (`occurred_on`), valor positivo e um `movement_type`:

| Tipo | Significado | Efeito na etiqueta |
|---|---|---|
| `allocation` | Distribuição inicial do mês | soma |
| `addition` | Valor acrescentado depois, vindo de fora da app | soma |
| `transfer_in` | Valor que entra vindo de outra etiqueta | soma |
| `transfer_out` | Valor que sai para outra etiqueta | subtrai |

**Total da etiqueta = allocation + addition + transfer_in − transfer_out.**

Invariantes:

1. `amount` é sempre `NUMERIC(14,2)` e estritamente positivo. O sinal vem do tipo. Nunca usar `float`.
2. Um `addition` cria também um registo de rendimento (`incomes`) ligado por `income_id`, para o rendimento do mês subir o mesmo valor.
3. Uma transferência é **sempre um par** de entradas (`transfer_out` + `transfer_in`) com o mesmo `transfer_id`, mesmo valor, mesma data, etiquetas diferentes, criado numa única transação de base de dados.
4. Apagar ou editar uma perna da transferência afeta as duas (atomicamente).
5. Tirar dinheiro de uma etiqueta é sempre uma transferência para outra. O dinheiro nunca desaparece sem destino. Corrigir enganos faz-se editando ou apagando a entrada (com desfazer).
6. O total do mês é invariante a transferências: a soma de `transfer_in` e `transfer_out` num mês é sempre igual.
7. **Por distribuir** = rendimento total do mês − soma de (`allocation` + `addition`). Os `addition` sobem as duas parcelas por igual, por isso não alteram o por distribuir.
8. Uma etiqueta de poupança ou investimento pode ficar com saldo mensal negativo (significa que se usou dinheiro acumulado). A evolução do património usa saldos **acumulados** entre meses.
9. Cada entrada mostra a sua origem (distribuição inicial, rendimento externo, transferido de X) e a data, para se ver a diferença ao longo do mês.

### 2.3 Meses

- Um mês por utilizador por ano/mês (`UNIQUE(user_id, year, month)`).
- Ao criar: opção de copiar a estrutura do mês anterior (mesmas etiquetas, valores em branco ou copiados).
- Um mês **fechado** rejeita qualquer escrita (entradas, rendimentos, transferências) até ser reaberto.
- Observação opcional no mês e em cada entrada.
- Vários rendimentos por mês (salário, extra...).

### 2.4 Transversais

- **Isolamento:** cada utilizador só acede aos seus dados. Toda a query filtra por `user_id`; há testes dedicados a tentar aceder a dados de outro utilizador.
- **Soft delete** em entradas, meses, etiquetas e metas (`deleted_at`). Eliminar mostra um toast com "desfazer". Dupla confirmação só em ações destrutivas a sério (apagar conta, apagar etiqueta com entradas).
- **Audit log** de criação, edição e eliminação de entradas, meses e etiquetas.
- **Uma moeda por utilizador** no MVP. Multi-moeda fica fora do âmbito.
- Valores arredondados e formatados de forma consistente (backend e frontend).

## 3. Âmbito: MVP e V2

**MVP:** utilizadores e perfil; etiquetas com tipo; meses; rendimentos; entradas e transferências; home com donut e seletor de mês; filtros e totais por etiqueta e período; limites com alertas (faixas fixas 80% e 100%); metas e fundo de emergência; comprovativos; mês fechado; modo demo.

**V2:** faixas de limite configuráveis; personalização de gráficos; investimentos por tipo (ETF, PPR...) com divisão de uma entrada; comparações mês a mês e ano a ano; evolução do património; exportação CSV/PDF avançada; pesquisa por texto em observações; alertas por email; importação de extrato CSV.

## 4. Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| Frontend | Angular (versão estável recente), standalone components, Signals, novo control flow (`@if`, `@for`), ECharts (ngx-echarts) |
| Base de dados | PostgreSQL |
| Cache e rate limiting | Redis |
| Mensageria | RabbitMQ (eventos de domínio e broker do Celery) |
| Tarefas | Celery + Celery beat |
| Auth | JWT com refresh token em cookie HttpOnly; OAuth Google (Authlib) |
| Ficheiros | MinIO em local, Azure Blob Storage em produção (URLs assinadas) |
| Emails | Mailpit em dev, Azure Communication Services ou Resend em produção |
| IA | Claude API (chat financeiro e insights, com tool use sobre as queries de relatórios) |
| Tempo real | WebSockets ou SSE (alertas) |
| Testes | pytest, pytest-asyncio, testcontainers, Ruff, mypy; Vitest ou Jest; Playwright |
| Observabilidade | Prometheus, Grafana, structlog, OpenTelemetry, Application Insights |
| Infra | Docker, Docker Compose, Kubernetes (Helm), Terraform, Azure (AKS, ACR, Key Vault, PostgreSQL Flexible Server, Blob Storage) |
| CI/CD | GitHub Actions (login Azure por OIDC) |

## 5. Estrutura do repositório (monorepo)

```
finnancial-system/
├── CLAUDE.md
├── README.md
├── docs/
│   ├── ARCHITECTURE.md        # este documento
│   ├── adr/                   # Architecture Decision Records
│   └── diagrams/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/              # config, segurança, logging, dependências
│   │   ├── db/                # sessão, base, migrações (alembic)
│   │   ├── domain/            # regras de negócio puras (sem FastAPI)
│   │   ├── models/            # modelos SQLAlchemy
│   │   ├── schemas/           # Pydantic
│   │   ├── repositories/      # acesso a dados
│   │   ├── services/          # casos de uso
│   │   ├── api/v1/            # routers
│   │   ├── events/            # publishers, consumers, outbox
│   │   └── workers/           # tarefas Celery
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/app/
│   │   ├── core/              # auth, interceptors, guards
│   │   ├── shared/            # componentes, design tokens, pipes
│   │   ├── features/          # auth, months, labels, dashboard, goals...
│   │   └── app.routes.ts
│   ├── e2e/                   # Playwright
│   └── Dockerfile
├── deploy/
│   ├── docker-compose.yml
│   ├── docker-compose.override.yml
│   ├── helm/                  # charts: api, worker, consumers, frontend
│   └── terraform/             # azure
└── .github/workflows/         # ci.yml, cd.yml
```

Princípio de arquitetura: **as regras de negócio vivem em `domain/` e `services/`**, não nos routers nem nos modelos. Isso permite testá-las sem HTTP nem base de dados.

## 6. Modelo de dados (resumo)

```
users              id, email, password_hash, name, avatar_url, currency, locale, timezone,
                   email_verified_at, google_id, deleted_at
labels             id, user_id, name, kind (expense|saving|investment), color, icon,
                   is_default, archived_at, deleted_at
months             id, user_id, year, month, note, closed_at, deleted_at   UNIQUE(user_id, year, month)
incomes            id, user_id, month_id, source, amount, received_on, note, deleted_at
entries            id, user_id, month_id, label_id, amount, movement_type, transfer_id (nullable),
                   income_id (nullable), occurred_on, note, deleted_at
attachments        id, user_id, entry_id (nullable), month_id, storage_key, filename, mime, size
limits             id, user_id, label_id, month_id (nullable = padrão), amount
alerts             id, user_id, limit_id, level (warning|exceeded), seen_at, created_at
goals              id, user_id, label_id, target_amount, deadline, type (normal|emergency_fund),
                   manual_progress (nullable), completed_at, deleted_at
chart_preferences  id, user_id, chart_type, label_ids
audit_log          id, user_id, entity, entity_id, action, before (jsonb), after (jsonb), created_at
outbox_events      id, type, payload (jsonb), created_at, published_at
# V2: investment_types, entry_investments
```

Índices essenciais: `entries(user_id, occurred_on)`, `entries(user_id, label_id, occurred_on)`, `entries(transfer_id)`, `months(user_id, year, month)`. Constraints: `CHECK (amount > 0)`, `CHECK` de coerência entre `movement_type` e `transfer_id`.

## 7. Fluxo de eventos (alvo)

```
Angular → FastAPI → grava no PostgreSQL + escreve evento na tabela outbox (mesma transação)
                       │
                  relay publica no RabbitMQ
                       ├─ consumer "limits" : recalcula limites e cria alertas
                       ├─ consumer "cache"  : invalida o cache do dashboard (Redis)
                       ├─ consumer "goals"  : atualiza progresso de metas
                       └─ consumer "emails" : envia alertas por email (V2)

Celery beat / CronJob → cria entradas recorrentes no início de cada mês
Celery workers        → exportações PDF/CSV, RGPD, emails
```

Eventos: `EntryCreated`, `EntryUpdated`, `EntryDeleted`, `TransferCreated`, `MonthClosed`, `MonthReopened`. Consumers são **idempotentes** (a mesma mensagem processada duas vezes não pode duplicar efeitos). Mensagens que falham várias vezes vão para uma dead-letter queue.

---

## 8. Fases de implementação

Regra geral: cada fase termina com **código, testes e documentação mínima**, e o CI verde. Não começar a fase seguinte antes.

### Fase 0: Fundação do repositório

**Objetivo:** ambiente reprodutível e pipeline mínimo.

**Entregáveis**

- Estrutura do monorepo (secção 5), `README.md` e `CLAUDE.md`
- `docker-compose.yml` com PostgreSQL, Redis, RabbitMQ (com management UI), MinIO e Mailpit; healthchecks em todos
- Backend FastAPI mínimo com `/health`, configuração por variáveis de ambiente (pydantic-settings), logging estruturado
- Frontend Angular gerado e a servir uma página inicial
- Ruff, mypy, pre-commit; pytest configurado
- GitHub Actions `ci.yml`: lint, type-check e testes do backend e lint/build do frontend
- Dockerfiles do backend e do frontend

**Critérios de aceitação**

- `docker compose up` sobe toda a stack sem passos manuais
- `GET /health` responde 200 e o CI passa num push

### Fase 1: Base de dados e autenticação

**Objetivo:** utilizadores reais e modelo base migrado.

**Entregáveis**

- SQLAlchemy async + Alembic; migração inicial com `users`, `labels`, `months`, `incomes`, `entries`, `audit_log` e constraints/índices da secção 6
- Registo com email e password (hash com argon2 ou bcrypt), login, logout, refresh token (cookie HttpOnly), rotação de refresh
- Dependência `get_current_user` usada em todos os routers protegidos
- Edição de perfil (nome, moeda, idioma, fuso horário) e alteração de password
- Criação das etiquetas padrão (com `kind`) no registo
- Testes de integração com testcontainers (PostgreSQL real)

**Critérios de aceitação**

- Fluxo registo → login → refresh → logout testado
- Teste que prova que um utilizador não acede a recursos de outro
- Migrações sobem e descem sem erros

### Fase 2: Núcleo de domínio (etiquetas, meses, entradas)

**Objetivo:** implementar as regras da secção 2. É a fase mais importante.

**Entregáveis**

- CRUD de etiquetas (com `kind`, cor, ícone, arquivar, reatribuir ao eliminar)
- CRUD de meses, com cópia do mês anterior e fecho/reabertura
- CRUD de rendimentos por mês
- Distribuição inicial (`allocation`) por etiqueta
- Criar `addition` (com `income` associado) e transferências (par atómico com `transfer_id`)
- Soft delete com endpoint de restauro (para o "desfazer")
- Audit log em todas as escritas
- Camada `domain/` pura com as regras e cálculo de totais e "por distribuir"

**Critérios de aceitação**

- Testes unitários para cada invariante da secção 2.2 e 2.3, incluindo: mês fechado rejeita escritas; transferência é sempre par; apagar uma perna apaga as duas; total do mês invariante a transferências; Mercado 200 + 12 = 212; por distribuir correto após `addition`
- Nenhum cálculo usa `float`

### Fase 3: Relatórios e agregações

**Objetivo:** responder a perguntas por período.

**Entregáveis**

- Endpoint de resumo do mês: total por etiqueta, total por `kind`, origem de cada parte (base + ajustes), por distribuir
- Endpoint de relatório por intervalo livre: filtro por etiqueta, por `kind` e por período (3, 6, 12 meses, ano, intervalo), com total e lista de entradas
- Série temporal por etiqueta (evolução ao longo dos meses)
- Queries otimizadas e índices validados com `EXPLAIN`
- Serviço único `ReportService`, que será depois reutilizado pelo chat com Claude

**Critérios de aceitação**

- Testes com dados fixos que comprovam os totais, incluindo etiquetas com transferências
- "Gasto em água nos últimos 6 meses" devolve o valor certo

### Fase 4: Frontend base

**Objetivo:** app navegável com autenticação e lançamento de dados.

**Entregáveis**

- Layout responsivo (telemóvel, tablet, desktop), dark mode, i18n PT/EN
- **Design tokens** em variáveis CSS: `--kind-expense`, `--kind-saving`, `--kind-investment` (com versão dark) e componente `MoneyAmount` que aplica cor, ícone e texto por `kind`
- Auth: registo, login, interceptor com refresh, guards
- Gestão de etiquetas (criar com pergunta do tipo, cor, ícone)
- Ecrã do mês: distribuição inicial, lista de entradas por data com origem, formulário rápido de entrada, fluxo "acrescentar dinheiro" que pergunta a origem (fonte externa ou outra etiqueta)
- Toast com "desfazer" após eliminar
- Cliente HTTP tipado, gerado a partir do OpenAPI do backend

**Critérios de aceitação**

- Registar-se, criar um mês, distribuir 1000 € e acrescentar 50 € vindos de fonte externa e 50 € vindos de Poupança, vendo tudo refletido corretamente
- Utilizável em ecrã de telemóvel

### Fase 5: Dashboard e gráficos

**Objetivo:** a visão geral que dá identidade ao produto.

**Entregáveis**

- Home com último mês por defeito e seletor de mês
- Três totais no topo (gasto, poupado, investido) e por distribuir
- Donut por `kind` e, ao clicar, por etiqueta; barras ordenadas; linha de evolução de uma etiqueta
- Filtros por etiqueta e período com total atualizado e lista
- Vista "base + ajustes" por etiqueta (barra empilhada ou linha do tempo)
- Alternativa textual (tabela) para cada gráfico

**Critérios de aceitação**

- Os valores do dashboard coincidem com os endpoints da Fase 3
- Contraste e navegação por teclado verificados nos gráficos

### Fase 6: Testes E2E e CI completo

**Entregáveis**

- Playwright: registo, login, criar mês, distribuir, acrescentar valor, transferir, fechar mês, ver dashboard
- CI com testcontainers, cobertura com badge no README e Playwright a correr contra a stack em Docker Compose
- Pre-commit e proteção do ramo principal

**Critérios de aceitação:** pipeline completo verde num pull request.

### Fase 7: Redis, RabbitMQ, Celery e outbox

**Objetivo:** arquitetura orientada a eventos.

**Entregáveis**

- Cache Redis dos resumos e relatórios, com chaves por utilizador e período; rate limiting nos endpoints de auth
- Tabela `outbox_events` escrita na mesma transação das entradas; relay que publica no RabbitMQ
- Exchange com filas separadas e dead-letter queue; consumers `cache`, `limits`, `goals` idempotentes
- Celery + beat: **entradas recorrentes** (aluguel, salário) criadas no início do mês; tarefas assíncronas base
- Processos separados no Compose: `api`, `worker`, `beat`, `consumers`

**Critérios de aceitação**

- Criar uma entrada invalida o cache e a próxima leitura devolve o valor atualizado
- Reprocessar a mesma mensagem não duplica efeitos (teste)
- Se um consumer falhar, a entrada continua gravada e a mensagem é reprocessada

### Fase 8: Limites, alertas, metas e fundo de emergência

**Entregáveis**

- Limites por etiqueta e mês, com avisos aos 80% e 100% (fixos no MVP)
- Alertas criados pelo consumer `limits` e empurrados para a UI por WebSocket ou SSE
- Metas (etiqueta, valor-alvo, prazo) com progresso, tempo restante e "precisas de guardar X €/mês"
- Fundo de emergência como meta especial: alvo em "N meses de despesas", calculado com a média dos gastos (etiquetas `expense`)
- Metas concluídas guardadas no histórico

**Critérios de aceitação:** testes unitários dos cálculos (percentagens, ritmo, média de despesas) e alerta a aparecer na UI sem recarregar.

### Fase 9: Comprovativos, exportação, RGPD e emails

**Entregáveis**

- Upload de foto/PDF ligado a entrada e mês, guardado em MinIO com URLs assinadas e validação de tipo e tamanho; ver, descarregar e remover
- Exportação CSV e PDF por período e etiquetas (tarefa Celery, ficheiro no storage, link para download)
- Exportação de dados e eliminação de conta (RGPD)
- Verificação de email e recuperação de password (Mailpit em dev)

**Critérios de aceitação:** um utilizador não consegue aceder a anexos de outro, nem com URL adivinhada.

### Fase 10: OAuth Google e modo demo

**Entregáveis**

- Login com Google (Authlib), com ligação a conta existente pelo email verificado
- 2FA TOTP (opcional)
- **Conta demo** com dados realistas pré-carregados (vários meses, transferências, metas), reposta por tarefa agendada, acessível por um botão "Experimentar"

### Fase 11: IA com Claude

**Objetivo:** camada de leitura e análise. A introdução de dados continua manual.

**Entregáveis**

- **Chat financeiro** com tool use sobre o `ReportService` (ferramentas: resumo do mês, relatório por etiqueta e período, evolução, metas). O modelo nunca recebe SQL livre nem dados de outros utilizadores
- **Insights do mês** gerados ao fechar o mês (consumer do evento `MonthClosed`)
- **Sugestão de etiqueta** ao escrever a descrição de uma entrada (opcional)
- Chave da API em segredo, limite de pedidos por utilizador, timeout e tratamento de erros
- Testes com o cliente da API simulado (mock)

**Critérios de aceitação:** "quanto investi nos últimos 2 meses?" devolve o mesmo valor que o relatório da Fase 3.

### Fase 12: Observabilidade

**Entregáveis**

- Métricas Prometheus na API (pedidos, latência, erros) e nas filas (tamanho, falhas)
- Dashboards Grafana no repositório (provisioning)
- OpenTelemetry e Sentry; logs estruturados com `request_id`
- Prometheus e Grafana no Compose

### Fase 13: Kubernetes local

**Entregáveis**

- Cluster local com kind ou k3d
- Helm charts: `api`, `worker`, `consumers`, `frontend`; RabbitMQ e Redis via charts existentes
- Deployments separados, probes de liveness e readiness, resource limits, ConfigMaps e Secrets
- CronJob para as recorrências, HPA nos workers, Ingress NGINX
- `kube-prometheus-stack` para métricas

**Critérios de aceitação:** `helm install` sobe a aplicação completa no cluster local.

### Fase 14: Azure, Terraform e CD

**Entregáveis**

- Terraform: resource group, ACR, AKS, PostgreSQL Flexible Server, Key Vault, Storage Account, rede
- Workload Identity para os pods lerem segredos do Key Vault
- `cd.yml`: build das imagens, push para ACR e `helm upgrade` no AKS, com login Azure por OIDC (sem segredos estáticos)
- Ingress com HTTPS (cert-manager) e domínio
- Ambiente destruível e recriável por Terraform (controlo de custos)

**Critérios de aceitação:** um merge no ramo principal faz deploy automático e a URL pública responde com HTTPS.

### Fase 15: Polimento para o portfólio

**Entregáveis**

- Landing page com demo e explicação de segurança
- README com diagrama de arquitetura (C4), GIFs, instruções de execução e badges (CI, cobertura)
- ADRs para as decisões principais (outbox, RabbitMQ vs Redis, Kubernetes, modelo de movimentos)
- Revisão de segurança (CORS, headers, rate limiting, dependências)
- Acessibilidade e performance verificadas (Lighthouse)

### Fase V2 (depois)

Investimentos por tipo com divisão de entradas; comparações mês a mês e ano a ano; evolução do património; faixas de limite configuráveis; personalização de gráficos; pesquisa por texto; alertas por email; importação de extrato CSV.

---

## 9. Ficheiro `CLAUDE.md` sugerido (raiz do repositório)

```
# FinnancialSystem

Ler docs/ARCHITECTURE.md antes de qualquer tarefa. Implementar uma fase de cada vez.

## Regras
- Valores monetários: NUMERIC(14,2) na BD e Decimal em Python. Nunca float.
- Regras de negócio em backend/app/domain e services, nunca em routers ou modelos.
- Toda query filtra por user_id. Cada endpoint novo precisa de teste de isolamento.
- Soft delete (deleted_at) em vez de DELETE. Escritas geram audit_log.
- Transferências são sempre pares atómicos com o mesmo transfer_id.
- Mês fechado rejeita escritas.
- Consumers RabbitMQ têm de ser idempotentes.
- Escrever testes antes de dar a tarefa por concluída.

## Comandos
- Subir stack: docker compose -f deploy/docker-compose.yml up
- Testes backend: cd backend && pytest
- Lint: ruff check . && mypy app
- Testes E2E: cd frontend && npx playwright test
```

## 10. Ordem resumida

| Bloco | Fases | Resultado |
|---|---|---|
| Produto funcional | 0 a 5 | App completa a funcionar em local |
| Qualidade | 6 | Testes E2E e CI sérios |
| Arquitetura avançada | 7 a 9 | Eventos, cache, limites, metas, anexos, exportações |
| Diferenciais | 10 a 11 | Google, modo demo, IA |
| Plataforma | 12 a 14 | Observabilidade, Kubernetes, Azure, CD |
| Apresentação | 15 | Landing, README, ADRs |

A aplicação fica utilizável ao fim da Fase 5, e tudo o que vem depois acrescenta profundidade técnica sem bloquear o produto.

