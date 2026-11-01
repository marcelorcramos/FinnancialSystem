# FinnancialSystem — frontend

Angular 22 (standalone, Signals, zoneless, new control flow), Angular Material M3,
Transloco (i18n) and ECharts via ngx-echarts. See `../docs/ARCHITECTURE.md` and `../docs/DECISIONS.md`.

> The current visual design is a placeholder and will be redesigned (see "Frontend: visual identity" in `DECISIONS.md`).

## Requirements

Node `^22.22.3 || ^24.15.0` (see `.nvmrc`).

## Commands

| Command | What it does |
|---|---|
| `npm start` | Dev server on http://localhost:4200, proxying `/api` to http://localhost:8000 (`proxy.conf.json`) |
| `npm run lint` | ESLint (angular-eslint) |
| `npm test` / `npm run test:ci` | Unit tests (Vitest), watch mode / single run |
| `npm run build` | Production build into `dist/` |
| `npm run e2e` | Playwright end-to-end tests (`e2e/`, desktop and phone) against the Compose stack on http://localhost:8080; `E2E_BASE_URL=http://localhost:4200` runs them against the dev server. First time: `npx playwright install chromium` |
| `docker build -t finnancial-frontend .` | nginx image; `API_UPSTREAM` (default `http://api:8000`) sets where `/api` goes |

## Structure

```
src/app/
├── core/       # auth (API, store, interceptor, guards), i18n, theme, layout
├── shared/     # design tokens, MoneyAmount, form and layout utilities
└── features/   # auth (login, sign-up), home
```

- **Design tokens** in `shared/design-tokens/_tokens.scss`: `--kind-expense`, `--kind-saving`,
  `--kind-investment` (`-light`/`-dark` variants, picked by `light-dark()` from the theme).
- **Money** arrives as decimal strings and is formatted without going through `float`
  (`shared/money/format-money.ts`).
- **Session**: the access token lives in memory only; on reload the session is restored through the
  `refresh_token` cookie (HttpOnly). The interceptor refreshes once on a 401 and retries the request.
