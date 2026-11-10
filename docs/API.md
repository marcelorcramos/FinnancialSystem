# FinnancialSystem API (v1)

The contract the frontend builds on. The interactive version, always in sync with the code, is at `http://localhost:8000/docs` (Swagger) and `/redoc`; the machine-readable schema is `/openapi.json`.

## Conventions

| Topic | Rule |
|---|---|
| Base path | `/api/v1` (only `GET /health` lives outside it) |
| Auth | `Authorization: Bearer <access_token>` on every route except `/auth/*` and `/health` |
| IDs | UUID strings |
| Money | **Decimal strings** with 2 decimal places, both ways: send `"212.50"`, receive `"212.50"`. Never parse into a float. Input must be positive (allocations accept `"0"` to remove), at most 2 decimal places and fit `NUMERIC(14,2)` |
| Dates | `YYYY-MM-DD`; timestamps are ISO 8601 in UTC |
| Isolation | A resource of another user always answers **404**, never 403 |
| Soft delete | `DELETE` hides a resource; `POST .../restore` brings it back (the "undo" toast) |

### Errors

Domain errors share one shape:

```json
{ "detail": "The month is closed. Reopen it to make changes.", "code": "month_closed" }
```

| Status | `code` | When |
|---|---|---|
| 401 | `authentication_failed` | Wrong credentials or invalid session on `/auth/*` |
| 401 | *(no `code`)* | Missing, invalid or expired access token on a protected route: `{"detail": "Invalid credentials"}` with `WWW-Authenticate: Bearer` → refresh and retry |
| 404 | `not_found` | The resource does not exist or belongs to someone else |
| 409 | `conflict` | Duplicates (email, label name or color, month), restores that would clash |
| 409 | `month_closed` | Any write to a closed month |
| 422 | `validation_failed` | A domain rule failed (date outside the month, same label on both sides of a transfer, archived label...) |
| 422 | *(FastAPI shape)* | Request body/query does not match the schema: `{"detail": [{"loc": [...], "msg": "..."}]}` |
| 429 | `rate_limited` | Too many attempts on `/auth/register`, `/auth/login` or `/auth/refresh`; the `Retry-After` header says how many seconds to wait |

## Auth and profile

The access token lasts 15 minutes and comes in the response body. The refresh token lives in an HttpOnly cookie `refresh_token` (`Path=/api/v1/auth`, SameSite=Lax); it rotates on every refresh, and reusing an old one revokes the whole session family. Send refresh/logout requests with credentials.

| Method | Route | Body | Response |
|---|---|---|---|
| POST | `/auth/register` | `{email, password, name}` | 201 `User` |
| POST | `/auth/login` | `{email, password}` | 200 `Token` + cookie |
| POST | `/auth/refresh` | cookie | 200 `Token` + new cookie |
| POST | `/auth/logout` | cookie | 204, cookie cleared |
| POST | `/auth/logout-others` | Bearer + cookie | 204, ends every other session; this one stays signed in |
| GET | `/users/me` | | 200 `User` |
| PATCH | `/users/me` | `{name?, currency?: "EUR", locale?, timezone?, auto_new_month?}` | 200 `User` |
| POST | `/users/me/password` | `{current_password, new_password}` | 204, ends every session |
| DELETE | `/users/me` | `{password}` | 204, deletes the account and all of its data for good; cookie cleared |
| POST | `/users/me/verification-email` | | 202, emails a new confirmation link; 409 if already confirmed |
| POST | `/auth/verify-email` | `{token}` | 204, confirms the email (no sign-in needed) |
| POST | `/auth/password-reset` | `{email}` | 202, emails a reset link if the email has an account |
| POST | `/auth/password-reset/confirm` | `{token, new_password}` | 204, sets the password and ends every session |

- `Token` = `{access_token, token_type: "bearer", expires_in}` (seconds).
- `User` = `{id, email, name, avatar_url, currency, locale, timezone, email_verified_at}`.
- New passwords: at least 8 characters with a lowercase letter, an uppercase letter, a digit and a special character.
- Sign-up creates the default labels listed in `DECISIONS.md` and emails a link to confirm the address (`{FRONTEND_URL}/verify-email?token=…`). Signing in does not wait for it: `email_verified_at` stays null until the link is opened.
- Reset links (`{FRONTEND_URL}/reset-password?token=…`) last 1 hour, confirmation links 48 hours; both work once, and a new link replaces the previous one of the same kind. A used, expired or unknown token gives 422 `invalid_token`. Resetting the password also confirms the email.
- `DELETE /users/me` needs the current password (401 otherwise; 10 tries per hour). Every record goes at once, audit log included; receipts and export files are removed by the worker right after, and a goodbye email confirms it. The email can sign up again.
- `/auth/password-reset` answers 202 whether or not the email has an account, so it cannot be used to find accounts. Rate limits: 20 per hour per IP and 5 per hour per email; resending the confirmation, 5 per hour per user.

## Labels

| Method | Route | Body / query | Response |
|---|---|---|---|
| GET | `/labels` | `?include_archived=false` | 200 `Label[]`, ordered by kind then name |
| POST | `/labels` | `{name, kind, color, icon}` | 201 `Label` |
| GET | `/labels/color-suggestions` | | 200 `{colors: string[8]}`, none used by the user's labels |
| GET | `/labels/{id}` | | 200 `Label` |
| PATCH | `/labels/{id}` | `{name?, kind?, color?, icon?}` | 200 `Label` (changing `kind` changes past reports: warn the user) |
| POST | `/labels/{id}/archive` · `/unarchive` | | 200 `Label` |
| DELETE | `/labels/{id}` | `?reassign_to={label_id}` (required when the label has entries) | 204 |
| POST | `/labels/{id}/restore` | | 200 `Label` |

- `Label` = `{id, name, kind, color, icon, is_default, archived_at}`.
- `kind` is `expense`, `saving` or `investment`. `color` is `#RRGGBB`, stored uppercase, unique per user.
- Archived labels cannot receive new money but keep their history and their color.

## Months

| Method | Route | Body / query | Response |
|---|---|---|---|
| GET | `/months` | `?year=2026` | 200 `Month[]`, newest first |
| POST | `/months` | `{year, month, note?, copy_allocations?, copy_incomes?}` | 201 `Month` |
| GET | `/months/{id}` | | 200 `Month` |
| PATCH | `/months/{id}` | `{note}` | 200 `Month` |
| POST | `/months/{id}/close` · `/reopen` | | 200 `Month` |
| DELETE | `/months/{id}` | | 204 |
| POST | `/months/{id}/restore` | | 200 `Month` |
| GET | `/months/{id}/summary` | | 200 `MonthSummary` |

- `Month` = `{id, year, month, note, closed_at}`.
- `copy_allocations` / `copy_incomes` copy from the latest existing earlier month; copies are normal, editable records.
- A closed month answers `409 month_closed` to every write, including the note, until it is reopened.

### Month summary

```json
{
  "month_id": "…", "year": 2026, "month": 10, "closed_at": null,
  "income_total": "1050.00",
  "distributed": "650.00",
  "unallocated": "400.00",
  "over_allocated": false,
  "month_total": "650.00",
  "by_kind": { "expense": "212.00", "saving": "288.00", "investment": "150.00" },
  "labels": [
    { "label_id": "…", "name": "Food", "kind": "expense", "color": "#FFB74D", "icon": "restaurant",
      "archived": false, "allocation": "200.00", "addition": "0.00",
      "transfer_in": "12.00", "transfer_out": "0.00", "total": "212.00" }
  ]
}
```

- `total` = allocation + addition + transfer_in − transfer_out ("base + adjustments").
- `unallocated` = income_total − distributed; it may be negative, and `over_allocated` tells the UI to warn.
- Every usable label is listed (even at zero); archived labels only when they moved money that month.

## Incomes

| Method | Route | Body | Response |
|---|---|---|---|
| GET | `/months/{id}/incomes` | | 200 `Income[]` |
| POST | `/months/{id}/incomes` | `{source, amount, received_on, note?}` | 201 `Income` |
| PATCH | `/incomes/{id}` | `{source?, amount?, received_on?, note?}` | 200 `Income` |
| DELETE | `/incomes/{id}` | | 204 |
| POST | `/incomes/{id}/restore` | | 200 `Income` |

- `Income` = `{id, month_id, source, amount, received_on, note, from_addition}`.
- `received_on` must fall within the month.
- Incomes with `from_addition: true` were created by "add money": edit or delete them through their entry (direct writes answer 409).

## Entries

Every movement is an entry with a `movement_type`: `allocation`, `addition`, `transfer_in` or `transfer_out`.

### Allocation (initial distribution)

| Method | Route | Body | Response |
|---|---|---|---|
| PUT | `/months/{id}/allocations/{label_id}` | `{amount, note?}` | 200 `Entry`; **204** when `amount` is `"0"` (removed) |
| DELETE | `/months/{id}/allocations/{label_id}` | | 204 |

One allocation per label and month, dated on the 1st.

### Add money (addition)

| Method | Route | Body | Response |
|---|---|---|---|
| POST | `/months/{id}/additions` | `{label_id, amount, occurred_on, source?, note?}` | 201 `Entry` + `source` |

Creates the entry and an income in one transaction, so the label and the month income rise together. `source` defaults to `"Extra income"`.

### Transfers

| Method | Route | Body | Response |
|---|---|---|---|
| POST | `/months/{id}/transfers` | `{from_label_id, to_label_id, amount, occurred_on, note?}` | 201 `Transfer` |
| PATCH | `/transfers/{transfer_id}` | `{from_label_id?, to_label_id?, amount?, occurred_on?, note?}` | 200 `Transfer` |
| DELETE | `/transfers/{transfer_id}` | | 204 |
| POST | `/transfers/{transfer_id}/restore` | | 200 `Transfer` |

- `Transfer` = `{transfer_id, month_id, from_label_id, to_label_id, amount, occurred_on, note, out_entry_id, in_entry_id}`.
- Stored as two entries (`transfer_out` and `transfer_in`) that are always created, edited, deleted and restored together. The labels must differ.

### Listing, editing and undo

| Method | Route | Body | Response |
|---|---|---|---|
| GET | `/months/{id}/entries` | | 200 `EntryListItem[]`, by date |
| PATCH | `/entries/{id}` | allocation: `{amount?, note?}` · addition: `{amount?, occurred_on?, label_id?, source?, note?}` | 200 `Entry` |
| DELETE | `/entries/{id}` | | 204 |
| POST | `/entries/{id}/restore` | | 200 `Entry` |

- `Entry` = `{id, month_id, label_id, amount, movement_type, transfer_id, income_id, occurred_on, note, created_at}`.
- `EntryListItem` = `Entry` + `origin` (`initial_distribution`, `external_income`, `transfer_in`, `transfer_out`) + `source` (additions) + `counterpart_label_id` (transfers).
- Deleting or restoring a transfer leg affects both legs; an addition takes its income along. Transfer legs are edited through `/transfers`.
- `occurred_on` must fall within the month; labels must not be archived.

## Reports

Every report route takes the same optional query filters:

| Parameter | Values | Default |
|---|---|---|
| `period` | `last_month` (the current month), `last_6_months`, `last_12_months`, `all` | `all` |
| `label_ids` | Label UUID; repeat the parameter for several | every label |
| `kinds` | `expense`, `saving`, `investment`; repeat for several. Combined with `label_ids` as a union | every kind |

Windows are rolling and include the current month (in the user's time zone). Deleted entries and months never count. A `label_ids` value that is not one of the user's labels answers 404.

| Method | Route | Response |
|---|---|---|
| GET | `/reports/summary` | 200 `ReportSummary`: totals by label and kind (donut) |
| GET | `/reports/series` | 200 `ReportSeries`: net total per label and month (line chart) |
| GET | `/reports/entries` | 200 `ReportEntries`: the entries behind the totals, newest first (`limit` 1–200, default 50; `offset` ≥ 0) |

### Report summary

```json
{
  "period": "last_6_months", "start_month": "2026-05", "end_month": "2026-10",
  "reference_date": "2026-10-28",
  "total": "362.00",
  "by_kind": { "expense": "212.00", "saving": "0.00", "investment": "150.00" },
  "kind_shares": { "expense": "58.56", "saving": "0.00", "investment": "41.44" },
  "labels": [
    { "label_id": "…", "name": "Food", "kind": "expense", "color": "#FFB74D", "icon": "restaurant",
      "archived": false, "allocation": "200.00", "addition": "0.00",
      "transfer_in": "12.00", "transfer_out": "0.00", "total": "212.00", "share": "58.56" }
  ]
}
```

- `share` and `kind_shares` are percentages of the distributed money. A label whose total is zero or below gets `"0.00"` (no slice) but is still listed.
- With `period=all`, `start_month` and `end_month` are `null`.

### Report series

```json
{
  "period": "last_6_months", "start_month": "2026-05", "end_month": "2026-10",
  "reference_date": "2026-10-28",
  "months": ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"],
  "totals": [ { "month": "2026-05", "total": "30.00" }, "…" ],
  "labels": [
    { "label_id": "…", "name": "Water", "kind": "expense", "color": "#4FC3F7", "icon": "water_drop",
      "archived": false, "total": "180.00",
      "points": [ { "month": "2026-05", "total": "30.00" }, "…" ] }
  ]
}
```

- Every month of the window has a point, so lines have no gaps: a month without money (or without a sheet) is `"0.00"`.
- `totals` adds up the selected labels per month; `labels[].total` is the label's total over the window and matches `/reports/summary`.
- With `period=all`, the series starts at the first month with money and ends at the current month (or a later sheet). An account without money returns empty `months`.
- Labels are listed the same way as in the summary, largest window total first.

### Report entries

```json
{
  "period": "last_month", "start_month": "2026-10", "end_month": "2026-10",
  "reference_date": "2026-10-28",
  "total": "212.00", "count": 2, "limit": 50, "offset": 0,
  "entries": [
    { "id": "…", "month_id": "…", "month": "2026-10", "label_id": "…", "amount": "12.00",
      "movement_type": "transfer_in", "transfer_id": "…", "income_id": null,
      "occurred_on": "2026-10-10", "note": null, "created_at": "…",
      "origin": "transfer_in", "source": null, "counterpart_label_id": "…" },
    { "id": "…", "month": "2026-10", "amount": "200.00", "movement_type": "allocation",
      "origin": "initial_distribution", "…": "…" }
  ]
}
```

- Each entry has the same fields as the month's entry list, plus `month` (YYYY-MM).
- `total` is the net sum of every matching entry (transfers out subtract), not just this page, and equals the `/reports/summary` total. `count` is the number of matching entries across all pages.
- `counterpart_label_id` names the other label of a transfer even when that label is outside the filter.
- Sorted by `occurred_on`, newest first; ties keep creation order, newest first.

## Receipts

Photos and PDFs of a month, optionally tied to one of its entries. Files live in private S3 storage; the browser opens them through short-lived signed links that the API makes only for the owner.

| Method | Route | Body | Response |
|---|---|---|---|
| POST | `/months/{month_id}/attachments` | multipart: `file`, `entry_id?` | 201 `Attachment`; 409 `month_closed` |
| GET | `/months/{month_id}/attachments` | `?entry_id=` | 200 `Attachment[]`, oldest first |
| GET | `/attachments/{id}/url` | `?download=true` | 200 `{url, expires_in}` |
| DELETE | `/attachments/{id}` | | 204 (soft delete); 409 on a closed month |
| POST | `/attachments/{id}/restore` | | 200 `Attachment` |

- `Attachment` = `{id, month_id, entry_id, filename, mime, size, created_at}`.
- Accepted: JPEG, PNG, WebP and PDF up to 10 MB, recognized by the file's first bytes (not its name or declared type). Anything else gives 422. The stored name drops folders and control characters and gets the extension of the real type.
- `url` works for 5 minutes and opens the file inline, or as a download with `download=true`. Another user's receipt is a 404, and storage refuses unsigned or altered links.
- Receipts of a deleted entry are hidden from the list and come back with the entry.

## Exports

Files built in the background by the Celery worker: a report's entries as CSV or PDF, or all of the account's data (GDPR) as a ZIP. Ask for one, poll it until `status` is `ready`, then download it through a signed link.

| Method | Route | Body | Response |
|---|---|---|---|
| POST | `/exports` | `{format: "csv" \| "pdf", period?, label_ids?, kinds?}` | 202 `Export` (pending) |
| POST | `/users/me/export` | | 202 `Export` (pending ZIP of the whole account) |
| GET | `/exports` | | 200 `Export[]`, latest 20, newest first |
| GET | `/exports/{id}` | | 200 `Export` |
| GET | `/exports/{id}/url` | | 200 `{url, expires_in}`; 409 until ready (or once failed or expired) |

- `Export` = `{id, kind: "report" | "account", format, status: "pending" | "ready" | "failed" | "expired", period, label_ids, kinds, reference_date, filename, size, error, created_at, completed_at, expires_at}`.
- Report filters work like `/reports/*`; the window is fixed on the day of the request (`reference_date`). Someone else's label is a 404.
- CSV: one row per entry, newest first, with month, date, label, kind, movement, amount, signed amount (money moved out is negative), the other label of a transfer, the income source and the note. UTF-8 with a BOM; notes that start like a formula get a leading `'`.
- PDF: totals by kind, the labels with total and share, and the entries.
- ZIP: `data.json` with the profile and every label, month, income, entry, limit, alert, goal and receipt record (deleted ones too), plus the receipt files under `receipts/`.
- At most 3 exports can wait at once (409). Files are removed 7 days after they are ready (`status` becomes `expired`).

## Limits

A limit is a maximum for a label: a default for every month, or one for a single month that replaces the default. Limits only warn, never block a write.

| Method | Route | Body | Response |
|---|---|---|---|
| GET | `/limits` | | 200 `Limit[]` (defaults have `month_id: null`) |
| PUT | `/labels/{label_id}/limit` | `{amount}` | 200 `Limit`: creates or changes the default |
| DELETE | `/labels/{label_id}/limit` | | 204 |
| PUT | `/months/{month_id}/limits/{label_id}` | `{amount}` | 200 `Limit`; 409 `month_closed` on a closed month |
| DELETE | `/months/{month_id}/limits/{label_id}` | | 204: the default applies again |
| GET | `/months/{month_id}/limits` | | 200 `LimitStatus[]`, most used first |

```json
{ "label_id": "…", "name": "Food", "color": "#FFB74D", "limit_id": "…",
  "limit": "300.00", "source": "default", "total": "250.00", "remaining": "50.00",
  "percent": "83.33", "level": "warning" }
```

- `level` is `warning` from 80% and `exceeded` from 100%, compared exactly (`percent` is rounded for display), otherwise `null`.
- `total` is the label's month total, as in the month summary.

## Alerts

The `limits` consumer raises an alert when a label reaches a level of its limit in a month: `warning` (80%) and `exceeded` (100%), each at most once per label and month. Jumping straight past 100% raises both.

| Method | Route | Response |
|---|---|---|
| GET | `/alerts?unseen=` | 200 `Alert[]`, the 50 newest (`unseen=true`: only those not seen yet) |
| POST | `/alerts/{id}/seen` | 204 (seen already is fine; someone else's or unknown: 404) |
| POST | `/alerts/seen` | 204: every alert seen |
| GET | `/alerts/stream` | `text/event-stream`: `event: alert` with an `Alert` as `data` each time one is raised; a `: ping` comment line every 15 s |

```json
{ "id": "…", "level": "exceeded", "label_id": "…", "label_name": "Food", "color": "#FFB74D",
  "month_id": "…", "year": 2026, "month": 11, "limit_amount": "300.00", "total": "320.00",
  "seen_at": null, "created_at": "2026-11-03T20:15:02Z" }
```

The stream needs the Bearer header, so read it with `fetch` (the browser's `EventSource` cannot send headers). Alerts raised while it was closed are in `GET /alerts`.

## Goals

A goal gathers money in a label, optionally by a deadline. One active goal per label (they would count the same money). Progress is the label's balance over all months, unless `manual_progress` is set.

| Method | Route | Body | Response |
|---|---|---|---|
| GET | `/goals` | | 200 `{active: Goal[], completed: Goal[]}` (completed newest first) |
| POST | `/goals` | `{label_id, type?, target_amount?, months_of_expenses?, deadline?, manual_progress?}` | 201 `Goal`; 409 if the label has an active goal |
| PATCH | `/goals/{id}` | `{target_amount?, months_of_expenses?, deadline?, manual_progress?}` (null clears deadline or manual_progress) | 200 `Goal` |
| DELETE | `/goals/{id}` | | 204 (soft delete) |
| POST | `/goals/{id}/restore` | | 200 `Goal` |

- `type`: `normal` needs `target_amount`; `emergency_fund` needs `months_of_expenses` (1–24) and its target is that many months of average expenses (expense labels, the 6 complete months before the current one that have a sheet). Without such a month the target is `null`.
- Computed fields: `progress`, `remaining`, `percent`, `months_left` (the current month and the deadline's month included), `days_left`, `per_month` (what to save each month to finish on time, rounded up to the cent), `reached`, `overdue`.
- The `goals` consumer moves a goal to `completed` when its progress reaches the target.

