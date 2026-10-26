# FinnancialSystem — frontend

Angular 22 (standalone, Signals, zoneless, novo control flow), Angular Material M3,
Transloco (PT/EN) e ECharts via ngx-echarts. Ver `../docs/ARCHITECTURE.md` e `../docs/DECISIONS.md`.

## Requisitos

Node `^22.22.3 || ^24.15.0` (ver `.nvmrc`).

## Comandos

| Comando | O quê |
|---|---|
| `npm start` | Dev server em http://localhost:4200, com proxy de `/api` para http://localhost:8000 (`proxy.conf.json`) |
| `npm run lint` | ESLint (angular-eslint) |
| `npm test` / `npm run test:ci` | Testes unitários (Vitest), em watch / uma vez |
| `npm run build` | Build de produção em `dist/` |
| `docker build -t finnancial-frontend .` | Imagem nginx; `API_UPSTREAM` (padrão `http://api:8000`) define para onde vai `/api` |

## Estrutura

```
src/app/
├── core/       # auth (API, store, interceptor, guards), i18n, tema, layout
├── shared/     # design tokens, MoneyAmount, utilitários de formulários e layout
└── features/   # auth (login, registo), home
```

- **Design tokens** em `shared/design-tokens/_tokens.scss`: `--kind-expense`, `--kind-saving`,
  `--kind-investment` (versões `-light`/`-dark`, escolhidas por `light-dark()` conforme o tema).
- **Valores monetários** chegam como strings decimais e são formatados sem passar por `float`
  (`shared/money/format-money.ts`).
- **Sessão**: o access token fica só em memória; ao recarregar, a sessão é retomada pelo cookie
  `refresh_token` (HttpOnly). O interceptor faz refresh uma vez em 401 e repete o pedido.
