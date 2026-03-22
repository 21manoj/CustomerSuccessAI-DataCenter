# QSIM Signal Data Architecture

**Status:** Approved design — implement post-demo (March 23+)
**Date:** March 22, 2026
**Author:** Manoj / Claude

## Problem

QSIM signals written directly to `qualitative_signals` table create phantom data when toggle is OFF — no enrichment pipeline, no oversight, no review queue. Nobody sees them, but they pollute the source-of-truth table.

## Design Principle

**If nobody's watching, nothing should be there.**

QSIM signals live in a separate table. They are joined with qualitative signals ONLY when the toggle is ON, via a query-time UNION — never a write-time merge.

## Architecture

```
CSV / regular ingestion → qualitative_signals (untouched, source of truth)
QSIM ingestion         → qsim_signals (isolated table, same time-series schema)

Toggle OFF → qsim_signals exists but is NEVER queried by any API/dashboard
Toggle ON  → UNION view joins both tables chronologically
```

## Table: `qsim_signals`

### Core columns (shared schema with qualitative_signals)

| Column | Type | Description |
|--------|------|-------------|
| signal_id | VARCHAR(60) PK | UUID format |
| account_id | INTEGER FK | Links to accounts table |
| customer_id | INTEGER FK | Tenant isolation |
| signal_date | TIMESTAMP | When the signal occurred |
| signal_type | VARCHAR(50) | e.g. slack, email, transcript, manual |
| content | TEXT | Raw signal text |
| sentiment | VARCHAR(20) | positive/negative/neutral |

### QSIM-only columns

| Column | Type | Description |
|--------|------|-------------|
| source_channel | VARCHAR(30) | slack / email / transcript / webhook / manual |
| structural_urgency | VARCHAR(10) | tier1 (immediate) / tier2 (composite) |
| enrichment_status | VARCHAR(20) | raw / enriched / reviewed |
| enriched_intent | TEXT | LLM-extracted intent (Phase 2) |
| enriched_summary | TEXT | LLM-generated summary (Phase 2) |
| enriched_urgency | INTEGER | LLM-scored urgency 1-10 (Phase 2) |
| cg_collision_id | INTEGER FK | Linked context graph node (if collision detected) |
| review_status | VARCHAR(20) | pending / approved / rejected |
| reviewed_by | VARCHAR(100) | Who approved/rejected |
| reviewed_at | TIMESTAMP | When reviewed |
| raw_metadata | JSONB | Original payload (participants, thread_id, etc.) |
| created_at | TIMESTAMP | Ingestion timestamp |

## Query-Time Join (Toggle ON)

```sql
-- Unified view used by APIs and dashboards when toggle is ON
CREATE VIEW unified_signals AS
  SELECT signal_id, account_id, signal_date, signal_type,
         content, sentiment, 'csv' as source, NULL as enrichment_status
  FROM qualitative_signals
  UNION ALL
  SELECT signal_id, account_id, signal_date, signal_type,
         content, sentiment, 'qsim' as source, enrichment_status
  FROM qsim_signals
  WHERE enrichment_status != 'rejected'  -- only show approved/enriched
  ORDER BY signal_date DESC;
```

## Toggle Behavior

| State | qualitative_signals | qsim_signals | APIs/Dashboards query |
|-------|--------------------|--------------|-----------------------|
| Toggle OFF | Normal (CSV source of truth) | Exists but ignored | qualitative_signals only |
| Toggle ON | Normal (unchanged) | Queried via UNION | unified_signals view |

## Benefits

1. **Toggle OFF = zero impact** — qualitative_signals never touched, no cleanup needed
2. **Toggle ON = time-series join** — unified chronological view, each row tagged with source
3. **Rollback is free** — DROP TABLE qsim_signals restores baseline
4. **Independent lifecycle** — CSV refresh doesn't clobber QSIM data, QSIM enrichment doesn't block CSV ingestion
5. **Audit trail** — always know which signals came from CSV vs QSIM
6. **Review gate** — QSIM signals must be approved before surfacing in dashboards

## Implementation Steps (Post-Demo)

1. Create `qsim_signals` table (Alembic migration)
2. Update Signal Engine ingestion to write to `qsim_signals` instead of `qualitative_signals`
3. Create `unified_signals` SQL view
4. Update all signal-reading APIs to use view when toggle ON, base table when OFF
5. Add review queue UI for QSIM signals (CS Ops dashboard)
6. Wire LLM enrichment pipeline (Phase 2)
