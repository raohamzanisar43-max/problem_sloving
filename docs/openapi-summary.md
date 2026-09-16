# API contract summary

Base path: `/api/v1/`. All endpoints require authentication except
`GET /health/`.

## Authentication

| Method | Path | Notes |
|--------|------|-------|
| POST | `/auth/token/` | `{username, password}` → `{access, refresh}` |
| POST | `/auth/token/refresh/` | `{refresh}` → `{access, refresh}` (tokens rotate) |

Send the access token as `Authorization: Bearer <token>`. Session auth also
works, which is what the Django admin and the browsable API use.

Access tokens last 8 hours, refresh tokens 7 days.

## Roles

| Role | Can |
|------|-----|
| `sales_executive` | Read the queue (own, unassigned, new and review records), update status/owner/notes on what they can see, prepare drafts, capture observations, export CSV |
| `sales_manager` | Everything above, plus create opportunities, trigger collection runs, resolve duplicates, run workbook sync, read the outbox |
| `admin` | Everything above, plus delete opportunities, change source configuration, and edit operating settings |

A request that exceeds the caller's role returns `403`, never a silently
filtered result.

## Pagination

Most list endpoints use page-number pagination:

```json
{ "count": 132, "next": "…?page=2", "previous": null, "results": [ … ] }
```

`GET /opportunities/` uses keyset (cursor) pagination for stable paging under
concurrent writes, and also reports `count`:

```json
{ "count": 132, "next": "…?cursor=cD0yMDI2…", "previous": null, "results": [ … ] }
```

Both accept `page_size` (max 100).

## Opportunities

| Method | Path | Notes |
|--------|------|-------|
| GET | `/opportunities/` | Filters: `service`, `status`, `intent`, `owner`, `band`, `search`, `ordering` |
| POST | `/opportunities/` | Manager/admin only |
| GET | `/opportunities/{id}/` | Includes `score_breakdown` and `revision` |
| PATCH | `/opportunities/{id}/` | `{status, owner, notes, expected_revision}` |
| DELETE | `/opportunities/{id}/` | Admin only |
| GET | `/opportunities/stats/` | Overview counters |
| GET | `/opportunities/pipeline/` | Reviewed → won lanes |
| GET | `/opportunities/{id}/activities/` | Status, assignment and note history |
| POST | `/opportunities/{id}/drafts/` | Prepare an outreach draft; requires status `reviewed`+ |
| GET | `/opportunities/{id}/draft-list/` | Previously prepared drafts |

### Optimistic concurrency

`PATCH` accepts `expected_revision`. If it does not match the stored
`revision`, the write is rejected with `400` and
`{"expected_revision": ["Revision conflict – record was modified by another user."]}`.
Every accepted change increments `revision` and writes an `Activity` row.

## Duplicates

| Method | Path | Notes |
|--------|------|-------|
| GET | `/duplicates/` | Filter by `decision` (`pending`, `accepted`, `rejected`) |
| POST | `/duplicates/{id}/resolve/` | `{decision}`; manager/admin only |

Accepting a pair closes the lower-scored record and notes which record it was
merged into. A pair can only be resolved once — a second attempt returns `409`.

## Sources, terms and runs

| Method | Path | Notes |
|--------|------|-------|
| GET | `/sources/` | Connector readiness and access state |
| PATCH | `/sources/{id}/` | Admin only |
| GET | `/search-terms/` | Starter query groups |
| GET | `/runs/` | Run history with counters; filter by `source`, `state`, `trigger` |
| POST | `/runs/` | `{source_id, trigger}` → `202`; manager/admin only |

`POST /runs/` creates exactly one `Run` and dispatches the collection task to
it. If no broker is reachable the run stays `queued` with a `dispatch_error`
counter, and an operator can pick it up with `python manage.py run_collection`.

Run counters: `fetched`, `new`, `duplicates`, `errors`, `qualified`.

## Observations

| Method | Path | Notes |
|--------|------|-------|
| GET | `/observations/` | Filter by `source`, `is_manual` |
| POST | `/observations/` | Manual capture |

Manual capture body:

```json
{ "url": "https://…", "title": "…", "company": "…", "text": "permitted excerpt", "qualify": true }
```

With `qualify: true` (the default) the excerpt is extracted and scored
immediately and the response carries an `opportunity` object. If extraction
fails the evidence is still stored and the response carries
`qualification_error`.

## Contacts

| Method | Path | Notes |
|--------|------|-------|
| GET | `/contacts/` | Filter by `opportunity`, `verification`, `is_primary` |
| POST | `/contacts/` | Create from evidence |
| PATCH | `/contacts/{id}/` | Correct a record |
| POST | `/contacts/{id}/suppress/` | Honour a do-not-contact request; manager/admin only |

Suppressed contacts are hidden from every listing but retained for audit.

## Exports and sync

| Method | Path | Notes |
|--------|------|-------|
| GET | `/exports/opportunities.csv` | Role-filtered CSV; accepts `service`, `status`, `search` |
| GET | `/sync/jobs/` | Sync history |
| POST | `/sync/jobs/` | `{target_id?}` → `202`; manager/admin only |
| GET | `/sync/targets/` | Configured workbook destinations |
| GET | `/outbox/` | Delivery ledger; manager/admin only |

CSV is UTF-8 with a BOM for Excel. Cells beginning `=`, `+`, `-` or `@` are
prefixed with an apostrophe so a spreadsheet cannot execute them.

A sync job returns state `completed`, `skipped` or `failed`. `skipped` means
Microsoft Graph is not configured, and `error` says which variables are missing.

## Outbox semantics

Every collected lead and every status, owner or note change writes an
`OutboxEvent` in the same transaction as the change. The key is
`destination:opportunity:revision`, so replaying a revision delivers nothing
twice. Destinations: `csv` (audit marker) and `email` (internal alert, only
when `alert_email` is set and the score clears `alert_min_score`).

## Operating settings

| Method | Path | Notes |
|--------|------|-------|
| GET | `/settings/` | Resolved operating values plus extraction-provider status |
| PATCH | `/settings/` | Admin only; partial update of editable keys |

Editable: `qualification_confidence`, `collection_interval_minutes`,
`duplicate_similarity_threshold`, `alert_min_score`, `alert_email`,
`excerpt_retention_days`. Everything else is reported read-only because it is
owned by the deployment environment. Credentials are never returned.

Out-of-range values return `400` with a per-key `errors` object.

## Users

| Method | Path | Notes |
|--------|------|-------|
| GET | `/me/` | Current user and role |
| GET | `/users/` | Assignment list; executives see only themselves |

## Health

`GET /health/` is unauthenticated and returns
`{"status": "ok", "service": "novu-opportunity-radar", "version": "1.0.0"}`.
It backs the container health check.
