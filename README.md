# Novu Opportunity Radar

**Find the requirement. Keep the evidence. Give sales a clear next step.**

Full-stack implementation of the Novu Labs Opportunity Radar system using **Django (backend)** + **React (frontend)** + **PostgreSQL**.

Version 1.0 · 15 September 2026  
Based on the official Developer Handover and interactive prototype.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 5.x + Django REST Framework |
| Database | PostgreSQL 16 |
| Auth | Django sessions + JWT (simplejwt) |
| AI Extraction | Pluggable: offline stub (default), OpenAI/Azure, or Gemini |
| Task queue | Celery + Redis (optional for production) |
| Frontend | React 18 + Vite + React Router |
| Styling | CSS matching the official prototype |
| Export | UTF-8 CSV with formula-injection protection |
| Orchestration | n8n workflow templates (included) |

---

## Project Structure

```
novu-opportunity-radar/
├── backend/                 # Django project
│   ├── config/              # Settings, URLs, ASGI/WSGI
│   ├── apps/
│   │   ├── accounts/        # Users & roles (Admin, Sales Manager, Sales Executive)
│   │   ├── sources/         # Connectors, search terms, runs, health
│   │   ├── observations/    # Raw source observations
│   │   ├── opportunities/   # Qualified leads, status, assignment
│   │   ├── contacts/        # Business contacts with provenance
│   │   ├── scoring/         # Deterministic 100-point scoring engine
│   │   ├── exports/         # CSV, outbox, cloud workbook sync
│   │   └── core/            # Pagination, permissions, operating settings
│   ├── apps/*/tests/        # Test suites (88 tests)
│   ├── manage.py
│   └── requirements.txt
├── frontend/                # React + Vite SPA
│   ├── src/
│   │   ├── pages/           # Overview, Queue, Capture, Sources, Rules, Pipeline, Duplicates, Exports, Settings
│   │   ├── components/      # LeadDetail, Stats, Tables, Pipeline lanes
│   │   ├── api/             # Axios client
│   │   └── styles/          # Prototype-matched CSS
│   └── package.json
├── n8n/                     # Inactive collection & sync workflow templates
├── docs/                    # Schema notes, AI prompt, acceptance checklist
├── scripts/                 # dev_setup + demo_run helpers (sh and ps1)
└── README.md
```

---

## Quick Start (Development)

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16 (or use SQLite for pure local demo)
- Redis (optional, for Celery)

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy env and edit if needed
# Windows:  copy .env.example .env
cp .env.example .env

# IMPORTANT — create tables FIRST, then seed
python manage.py migrate
python manage.py seed_demo         # loads example leads from the prototype
# seed_demo already creates admin / manager / executive users

python manage.py runserver 0.0.0.0:8000
```

If you see `no such table: accounts_user`, you skipped `migrate`. Run it, then seed again.

API base: `http://localhost:8000/api/v1/`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: `http://localhost:5173`

The frontend proxies `/api` to the Django server (see `vite.config.js`).

### 3. Demo credentials (after seed)

| Role              | Username          | Password   |
|-------------------|-------------------|------------|
| Administrator     | admin             | admin123   |
| Sales Manager     | manager           | manager123 |
| Sales Executive   | executive         | exec123    |

---

## Running collection

Sources ship disabled. Enable one in Django admin and supply its credentials in
the environment first — a run against a disabled source is refused.

**With Celery** (Redis reachable):

```bash
celery -A celery_app worker --loglevel=info
celery -A celery_app beat --loglevel=info --schedule /tmp/celerybeat-schedule
```

Beat reads `CELERY_BEAT_SCHEDULE` from Django settings and runs three jobs:
collection every `COLLECTION_INTERVAL_MINUTES`, the duplicate scan at twice that
interval, and outbox delivery every 5 minutes.

**Without Celery** — the whole pipeline runs in-process:

```bash
python manage.py run_collection              # every enabled source
python manage.py run_collection --source X   # one source
python manage.py run_collection --duplicates # duplicate scan only
```

`scripts/dev_setup.sh` and `scripts/demo_run.sh` (`.ps1` on Windows) wrap the
common steps.

---

## Docker

```bash
cp .env.example .env     # set DJANGO_SECRET_KEY at minimum
docker compose up --build
```

The stack runs Postgres, Redis, the API, a Celery worker, beat, and nginx
serving the built UI on port 80. `DJANGO_DEBUG` defaults to `false`; secrets
come from the environment and are never copied into the images.

---

## Implemented Phases

### Phase 1 – MVP (Weeks 1-6)

- [x] PostgreSQL schema (sources, observations, opportunities, contacts, runs, outbox…)
- [x] Role-based access (Admin / Sales Manager / Sales Executive)
- [x] Manual observation capture
- [x] Deterministic scoring engine (Buying intent 30 + Service match 25 + Recency 15 + Evidence 15 + Contact 10 + Deadline 5)
- [x] Review flags & status workflow (new → review → reviewed → contacted → meeting → proposal → won / rejected / closed)
- [x] Opportunity queue with filters (service, status, search)
- [x] Lead detail with evidence, score breakdown, assignment, notes
- [x] Sales pipeline board
- [x] Safe CSV export (formula injection neutralised)
- [x] Source health screen + collection run history
- [x] Search rules & qualification policy UI
- [x] Settings screen backed by live, admin-editable operating settings
- [x] Duplicate review with soft merge
- [x] Sales draft writer (prepared for human review; never auto-sent)

### Phase 2 – Second Release

- [x] X / Reddit / Brave / RSS collectors + access-state model
- [x] Contact records with provenance, verification state and suppression
- [x] Cloud Excel / Microsoft Graph sync with job history
- [x] Transactional outbox with idempotent event keys + internal email alerts
- [x] Duplicate detection (tf-idf cosine, no heavyweight dependencies)
- [x] n8n collection & sync workflow templates

**Not yet done in Phase 2:** contact *enrichment* — contacts are recorded from
evidence already present in the source text; there is no third-party lookup
service. Live collection also needs real credentials before any connector can
be enabled.

### Phase 3 – Later Product (architecture ready)

- Tenant isolation hooks
- CRM integration points
- Commercial SaaS packaging notes in docs/

---

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/api/v1/runs/` | Queue a collection run |
| GET    | `/api/v1/runs/{id}/` | Run status & counters |
| POST   | `/api/v1/observations/` | Manual / connector observation |
| GET    | `/api/v1/opportunities/` | Filtered queue (cursor pagination) |
| PATCH  | `/api/v1/opportunities/{id}/` | Assign, status, notes (optimistic revision) |
| POST   | `/api/v1/opportunities/{id}/drafts/` | Create sales draft |
| GET    | `/api/v1/exports/opportunities.csv` | Permission-filtered CSV |
| GET    | `/api/v1/opportunities/{id}/activities/` | Status, assignment and note history |
| GET    | `/api/v1/duplicates/` · POST `{id}/resolve/` | Duplicate review and merge |
| GET    | `/api/v1/contacts/` | Published contacts with provenance |
| POST   | `/api/v1/sync/jobs/` | Run cloud workbook sync |
| GET    | `/api/v1/outbox/` | Delivery ledger (manager/admin) |
| GET    | `/api/v1/sources/` | Source health |
| GET    | `/api/v1/search-terms/` | Query groups |
| GET/PATCH | `/api/v1/settings/` | Operating settings (PATCH is admin only) |

Full contract, including roles, pagination and outbox semantics, lives in
[`docs/openapi-summary.md`](docs/openapi-summary.md).

---

## Scoring Policy (Deterministic)

| Factor            | Max | Rules |
|-------------------|-----|-------|
| Buying intent     | 30  | Explicit / RFP 30 · Agency 24 · Indirect 10 · Hiring 5 · Non-buyer 0 |
| Service match     | 25  | Supported category 25 · else 0 |
| Recency           | 15  | ≤2d 15 · ≤7d 10 · ≤30d 5 · older/missing 0 |
| Evidence quality  | 15  | Quote 10 + full source text 5 |
| Contact path      | 10  | Published email/phone 10 · original URL 3 |
| Deadline urgency  | 5   | Explicit future deadline ≤7d 5 |

**Bands:** 80–100 Hot · 60–79 High potential · 40–59 Review · <40 Archive  
Non-buyer → rejected · Expired deadline → closed · Hiring / uncertain → review.

---

## Safety & Compliance Highlights

- Every opportunity keeps the original source URL + excerpt.
- No automatic external messaging in MVP.
- Formula-injection protection on CSV cells.
- Prompt-injection resistance instructions in AI extraction prompt.
- Credentials never stored in JSON settings; use environment / secret store.
- Role isolation enforced at API level.

---

## Acceptance Checklist (from Handover)

See `docs/acceptance-checklist.md`. Each check is covered by the seed data and
the test suites under `backend/apps/*/tests/`:

```
cd backend
python manage.py test apps      # 88 tests
```

---

## Production Notes

1. Set `DJANGO_SECRET_KEY` and leave `DJANGO_DEBUG=false`; configure `ALLOWED_HOSTS`, PostgreSQL and Redis.
2. For a real extraction provider, set `LLM_PROVIDER` and `LLM_API_KEY` and install its SDK (`openai` or `google-genai`). If the SDK is missing the pipeline falls back to the offline stub and logs an error — the Settings screen reports this as **Degraded**.
3. Attach Brave Search / X / Reddit credentials only after commercial agreements.
4. Configure daily spend caps before enabling live collection.
5. n8n workflows are intentionally inactive – import, replace base URL, attach Header Auth, then activate.
6. Microsoft Graph table-row sync requires delegated sign-in (application permissions are not supported for that endpoint).
7. Set `ALERT_EMAIL` and SMTP credentials to turn on internal alerts; leaving it blank disables alert events entirely.

---

## License & Usage

Internal Novu Labs project.  
n8n Sustainable Use License applies to the included workflow templates – internal business use only.

---

Prepared for Novu Labs development and sales teams.  
Interface prototype behaviour is faithfully reproduced in the React application.
