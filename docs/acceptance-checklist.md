# Acceptance checks (Handover §15)

| Check | Expected result | Covered by |
|-------|-----------------|------------|
| Buyer versus seller | Supplier promotion rejected; explicit partner request becomes a lead | seed demo-4 / demo-1 + scoring engine |
| Hiring versus outsourcing | Employment-only stays review | seed demo-3 |
| Unsupported facts | Absent budgets/contacts stay null | Opportunity model defaults |
| Dates and urgency | Expired tender closed | seed demo-5 |
| Replay and duplicates | Unique constraint on source+external_id | Observation model |
| Scoring consistency | Factors sum to score; review rules override | `apps.scoring.engine` |
| Role isolation | Executive cannot change credentials | DRF permissions |
| Formula injection | Leading `=+-@` neutralized in CSV | `exports.csv_utils.safe_cell` |
| Partial failure | One failed connector does not stop others | Run model design |
| Prompt injection | Extraction prompt ignores embedded instructions | `docs/ai-extraction-prompt.txt` |
| Recovery | Revision field + outbox event keys | Opportunity.revision, OutboxEvent.event_key |
