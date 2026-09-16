# Implementation phases

## Phase 1 – MVP (complete in this repo)

| Week | Deliverable | Status in repo |
|------|-------------|----------------|
| 1 | Schema, roles, manual ingest | Django models + seed_demo + Observation API |
| 2 | Web/feed adapters, runs, health | Source + Run models, Source health UI |
| 3 | AI extraction stub, scoring, review flags | `apps.scoring.engine`, AI prompt, review_reasons |
| 4 | Queue, detail, assignment, stages | OpportunityViewSet, LeadDetail, Pipeline |
| 5 | CSV export, outbox, cost tracking fields | Safe CSV, SyncJob, OutboxEvent |
| 6 | Pilot tuning, permissions, handover | README, acceptance checklist, n8n templates |

## Phase 2 – Second release (scaffolded)

- X / Reddit connector access states in Source model
- Contact enrichment model (`apps.contacts`)
- Cloud Excel sync outbox + n8n-sync.json
- Draft endpoint for reviewed leads
- Assignment via owner field + activity log

## Phase 3 – Later product (architecture hooks)

- Tenant isolation: add `tenant_id` to Opportunity / Source when needed
- CRM webhooks: outbox destination types
- SaaS packaging: separate auth gateway, billing

## How to extend for live collection

1. Implement Brave Search adapter calling `GET https://api.search.brave.com/res/v1/web/search`
2. Normalize into Observation with ON CONFLICT
3. Call AI extraction (replace stub) → validate evidence quotes
4. Run `compute_score` → create/link Opportunity
5. Emit OutboxEvent inside the same transaction
