# Signal Engine — Sprints 2 & 3

## Context

Sprint 1 shipped (Session 4): async enrichment worker, Voyage AI embeddings, Qdrant→Claude RAG enrichment, collision dedup, raw signal generator (88% recall). Pipeline 1 (extraction) and Pipeline 2 (reasoning) are cleanly separated.

**What Sprint 1 delivered:**
- Ingestion API: `/api/signals/ingest/{slack|email|transcript|manual}` → 202 Accepted
- Claude Sonnet enrichment: sentiment, intent, stakeholder roles, escalation probability
- Rate limiting: 200 calls/customer/day, 50 calls/account/day
- DB schema: 22 enrichment columns on `qualitative_signals` table
- Feature toggle: `FEATURE_SIGNAL_ENGINE=true` (enabled on EC2)
- Raw signal generator: `generate_raw_signals.py` — 30/30 test signals, 88% recall

**What's NOT built yet:**
- Deduplication not integrated into ingestion flow (code exists, not wired)
- Alert routing & dispatch (table created, no routing logic)
- Tier-1 pre-emption (champion_loss, exec_escalation) not firing immediate alerts
- Health score fusion (composite score computation defined, not connected)
- No async background queue (enrichment is sync-only or daemon thread)

---

## Sprint 2: Deduplication + Alert Dispatch (1.5 weeks)

### Goal
Signals are deduplicated across channels and routed to CSM via alerts. A champion loss signal in Slack that's also in email becomes ONE enriched signal, not two.

### Phase 2A: Deduplication Integration (4 days)

1. **Wire SignalDeduplicator into ingestion flow**
   - After enrichment completes, call `signal_deduplicator.check_duplicates(signal)`
   - Window-based matching: same account + similar intent within configurable window (48h-168h per intent type)
   - Merge strategy: keep highest-confidence enrichment, combine source metadata
   - File: `signal_engine/ingest_api.py` → call `signal_deduplicator.py` post-enrichment

2. **Composite signal creation**
   - When dedup confidence ≥ 0.7: merge into single `composite_signal_id`
   - When dedup confidence < 0.7: queue for manual review (`requires_review=true`)
   - Update `qualitative_signals.composite_signal_id` and `dedup_confidence` columns

3. **CG collision check integration**
   - After dedup, call `collision.check_existing_nodes(signal, account_id)`
   - If signal matches existing ContextNode: link via `cg_node_id`, don't create duplicate
   - If new: create SIGNAL node in context graph with proper edges

4. **Dedup dashboard API**
   - `GET /api/signals/dedup-stats` — merge rate, confidence distribution, review queue size
   - `GET /api/signals/review-queue?status=pending` — signals needing manual review

### Phase 2B: Alert Routing & Dispatch (3 days)

5. **Alert routing engine**
   - New file: `signal_engine/alert_router.py`
   - Route rules: urgency ≥ 0.8 → immediate, 0.5-0.8 → daily digest, < 0.5 → weekly summary
   - CSM assignment lookup: account → CSM via `profile_metadata` or `allowed_account_ids`
   - Write to `alert_records` table with delivery_status tracking

6. **Dispatch channels**
   - Slack webhook: POST to CSM's Slack channel (uses existing `slack_provider.py`)
   - Email alert: send via `email_provider.py` with signal summary + recommended action
   - In-app: write to notification queue (consumed by CSM dashboard NotificationBell)

7. **Tier-1 pre-emption**
   - Champion loss, executive escalation, churn risk signals bypass normal queue
   - Fire within 5-minute SLA of ingestion
   - Create alert_record with `priority='tier_1'`, `sla_target=300s`
   - Track SLA compliance: `alert_records.dispatched_at - signal.created_at`

### Sprint 2 Acceptance Criteria
- Two Slack messages about same topic merge into one enriched signal
- CSM receives Slack alert within 5 minutes of champion_loss signal ingestion
- Review queue shows signals with dedup confidence < 0.7
- Alert dispatch tracks delivery status (sent/delivered/acknowledged)

---

## Sprint 3: Health Fusion + Feedback Loop (1.5 weeks)

### Goal
Signal intelligence feeds back into health scores. CSM feedback improves extraction quality over time.

### Phase 3A: Composite Health Fusion (4 days)

8. **Wire fusion into health recalculation**
   - After signal enrichment + dedup, call `fusion.compute_composite_score(account_id)`
   - Composite = `(kpi_score × kpi_weight) + (signal_score × signal_weight)`
   - Default signal_weight: 0.15 (KPI weight: 0.85) — configurable per customer via CustomerConfig
   - Cold-start ramp: signal_weight starts at 0.05, increases by 0.025/month up to max

9. **Pillar-level signal attribution**
   - Map signal intents to pillars: `champion_loss` → P2 (Stakeholder), `feature_request` → P1 (Adoption)
   - Signal modifies pillar score, not overall score directly
   - Mapping defined in `signal_engine/pillar_mapping.py` (new file)

10. **Health score recalc trigger**
    - After fusion computes new composite: trigger incremental health recalc for affected account
    - Respect immutability: only update current month's score, never rewrite historical
    - Publish `HEALTH_SCORES_UPDATED` event for downstream consumers

11. **Signal impact visualization**
    - API: `GET /api/accounts/<id>/signal-impact` — shows signal contribution to each pillar
    - Returns: `{ "P1": { "kpi_score": 72, "signal_modifier": -3, "composite": 69 }, ... }`

### Phase 3B: CSM Feedback Loop (3 days)

12. **Signal accuracy feedback**
    - CSM can mark signal as: accurate, inaccurate, partially_accurate
    - API: `POST /api/signals/<id>/feedback` with `{ accuracy, corrected_intent, notes }`
    - Feedback stored on `qualitative_signals.csm_feedback` (new JSON column)

13. **Extraction quality tracking**
    - Per-customer accuracy score: `correct_signals / total_reviewed_signals`
    - Dashboard: `GET /api/signals/quality-metrics?customer_id=<id>`
    - Returns: accuracy_rate, most_common_misclassifications, signals_reviewed_count

14. **Confidence threshold auto-tuning**
    - If accuracy < 85%: lower confidence gate (more signals go to review queue)
    - If accuracy > 95%: raise confidence gate (fewer manual reviews needed)
    - Threshold stored in CustomerConfig: `signal_confidence_threshold` (default 0.7)

15. **Enrichment prompt refinement**
    - Collect misclassified signals per customer
    - Add customer-specific examples to enrichment prompt (few-shot learning)
    - Store in `CustomerConfig.signal_extraction_examples` (JSON, max 10 examples)

### Sprint 3 Acceptance Criteria
- Health score for account changes when high-urgency signal is ingested
- Signal impact visible per-pillar in account detail view
- CSM can mark signal as inaccurate → goes into customer's quality metrics
- Confidence threshold adjusts based on accumulated feedback (85% → lower gate)

---

## Key Files

| Component | File |
|-----------|------|
| Signal Ingestion API | `backend/signal_engine/ingest_api.py` |
| Signal Enrichment | `backend/signal_engine/enrichment.py` |
| Signal Deduplicator | `backend/agents/signal_deduplicator.py` |
| CG Collision Check | `backend/signal_engine/collision.py` |
| Composite Fusion | `backend/signal_engine/fusion.py` |
| Structural Urgency | `backend/signal_engine/urgency.py` |
| Alert Router (NEW) | `backend/signal_engine/alert_router.py` |
| Pillar Mapping (NEW) | `backend/signal_engine/pillar_mapping.py` |
| Slack Provider | `backend/providers/slack_provider.py` |
| Email Provider | `backend/providers/email_provider.py` |
| Signal Analyst API | `backend/agents/signal_analyst_api.py` |

## Dependencies
- Sprint 1 complete (enrichment worker, Qdrant, Voyage embeddings) ✓
- `FEATURE_SIGNAL_ENGINE=true` enabled ✓
- Slack webhook URL configured per customer (for alert dispatch)
- CSM assignment data in `profile_metadata` or `allowed_account_ids`

## Risks
- **P0**: Signal-to-health fusion changes scores — need "signal contribution" audit trail before design partner
- **P1**: Dedup across channels needs semantic similarity (Voyage embeddings), not just intent matching
- **P2**: Feedback loop needs 50+ reviewed signals per customer to be statistically meaningful
