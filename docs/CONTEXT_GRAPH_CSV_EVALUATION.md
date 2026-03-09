# Context Graph CSV Evaluation: Time/Date Stamp and Completeness

This doc evaluates the 9 context graph CSVs (schema in `kpi-dashboard/backend/config/csv_schemas.json`, generator in `kpi-dashboard/backend/scripts/generate_context_graph_data.py`, ingestion in `onboarding_api_v2_config_aware.py` → `ingest_context_graph_csvs`).

## Summary

| CSV | Has date/timestamp? | Used for `occurred_at`? | Gap / recommendation |
|-----|---------------------|--------------------------|----------------------|
| **stakeholders.csv** | No | No (ingestion passes none) | Add optional `first_observed_at` or `as_of_date` |
| **engagement_events.csv** | Yes (`event_date`) | Yes | Consider adding time (e.g. `event_time`) for ordering within day |
| **account_business_profiles.csv** | No | No | Add optional `profile_date` / `as_of_date` |
| **decisions.csv** | Yes (`decision_date`) | Yes | Consider adding time for ordering |
| **outcomes.csv** | Yes (`outcome_date`) | Yes | OK |
| **signal_edges.csv** | Optional `lag_days` only | No (edges have optional `occurred_at` in DB) | Optional: add `observed_at` for when the edge was inferred |
| **decision_evidence.csv** | Yes (optional `timestamp`) | Not mapped to node (evidence → edges) | OK |
| **industry_benchmarks.csv** | Yes (optional `benchmark_date`) | No (ingestion doesn’t pass it) | Use `benchmark_date` for `occurred_at` in ingestion |
| **enhanced_qualitative_signals.csv** | Yes (`signal_date`) | Yes | Consider adding time |

---

## 1. What the DB expects

- **context_nodes**: `occurred_at` is **required** (NOT NULL). Used for time ordering, “since” filters, and causal ordering in validation.
- **context_edges**: `occurred_at` is optional; used for when the relationship was observed.

Ingestion maps CSV columns into `_insert_node(..., event_time=...)`; that value is written to `context_nodes.occurred_at`.

---

## 2. File-by-file

### 2.1 stakeholders.csv

- **Schema**: No date column (required or optional).
- **Generator**: No date column written.
- **Ingestion**: Calls `_insert_node(..., )` with **no** `event_time`, so `occurred_at` would be NULL and the insert can fail (column is NOT NULL) unless the DB has a default.

**Recommendation:**

- Add an **optional** column, e.g. `first_observed_at` or `as_of_date` (date or datetime).
- In ingestion: set `event_time` from that column when present; otherwise use a safe default (e.g. `datetime.utcnow()` or arc start date) so `occurred_at` is never NULL.

---

### 2.2 engagement_events.csv

- **Schema**: Required `event_date`.
- **Generator**: Writes `event_date` as `%Y-%m-%d`.
- **Ingestion**: Uses `event_date` for `event_time` → `occurred_at`. OK.

**Recommendation:**

- Optional: add `event_time` (e.g. `HH:MM` or ISO time) if you need ordering within a day (e.g. meeting at 10:00 vs decision at 14:00). Not required for current story-arc semantics.

---

### 2.3 account_business_profiles.csv

- **Schema**: No date column.
- **Generator**: No date column.
- **Ingestion**: No `event_time` → same risk as stakeholders for `occurred_at`.

**Recommendation:**

- Add optional `profile_date` or `as_of_date`.
- In ingestion: pass it as `event_time` when present; otherwise use a default (e.g. “today” or arc start) so `occurred_at` is always set.

---

### 2.4 decisions.csv

- **Schema**: Required `decision_date`.
- **Generator**: Writes `decision_date` as `%Y-%m-%d`.
- **Ingestion**: Uses `decision_date` for `event_time`. OK.

Optional: add time if you need sub-day ordering.

---

### 2.5 outcomes.csv

- **Schema**: Required `outcome_date`.
- **Generator**: Writes `outcome_date` as `%Y-%m-%d`.
- **Ingestion**: Uses `outcome_date` for `event_time`. OK.

---

### 2.6 signal_edges.csv

- **Schema**: Optional `lag_days`; no `occurred_at` / `observed_at`.
- **Generator**: Writes `lag_days` (weeks → days); no date column.
- **Ingestion**: Edges are inserted with optional `occurred_at`; current code doesn’t set it from CSV.

**Recommendation:**

- Optional: add `observed_at` (or `edge_date`) if you want “when this causal link was inferred” for analytics or decay. Not required for basic causal graph behavior.

---

### 2.7 decision_evidence.csv

- **Schema**: Optional `timestamp`.
- **Generator**: Writes evidence date as `%Y-%m-%d` in the `timestamp` column.
- **Ingestion**: Evidence is used to build edges (SOURCED_FROM, etc.); the timestamp is stored in properties or similar, not as `context_nodes.occurred_at`. OK for current design.

---

### 2.8 industry_benchmarks.csv

- **Schema**: Optional `benchmark_date`.
- **Generator**: Writes `benchmark_date` as `datetime.now().strftime('%Y-%m-%d')`.
- **Ingestion**: Calls `_insert_node(..., )` with **no** `event_time` for benchmark nodes, so `occurred_at` is again NULL unless the DB has a default.

**Recommendation:**

- In ingestion: pass `row.get('benchmark_date')` as `event_time` when inserting EXTERNAL_CONTEXT nodes so benchmarks get a valid `occurred_at` (and use the CSV value instead of “now” when provided).

---

### 2.9 enhanced_qualitative_signals.csv

- **Schema**: Required `signal_date`.
- **Generator**: Writes `signal_date` as `%Y-%m-%d`.
- **Ingestion**: Uses `signal_date` for `event_time`. OK.

Optional: add time for sub-day ordering.

---

## 3. Date format and timezone

- All current date columns are **date-only** (`YYYY-MM-DD`). The DB `occurred_at` is a timestamp; ingestion/PostgreSQL will interpret a date string as midnight (server TZ or UTC depending on config).
- **Recommendation**: Document that date columns are UTC or “date only, time assumed 00:00:00 UTC.” If you add time later, use ISO 8601 (e.g. `YYYY-MM-DDTHH:MM:SSZ`).

---

## 4. What’s not missing (already covered)

- **engagement_events**, **decisions**, **outcomes**, **enhanced_qualitative_signals**: Have required/optional dates and ingestion maps them to `occurred_at`. Good.
- **decision_evidence**: Optional `timestamp` is generated and stored; sufficient for evidence lifecycle.
- **Causal ordering**: Story arcs drive event_date / decision_date / outcome_date from phase weeks; ordering is consistent. Optional time would only refine within-day order.

---

## 5. Priority fixes

1. **Stakeholders**: Add optional `first_observed_at` (or `as_of_date`); in ingestion, set `event_time` from it or default to a safe value so `occurred_at` is never NULL.
2. **Account business profiles**: Add optional `profile_date` (or `as_of_date`); same ingestion fallback for `event_time`.
3. **Industry benchmarks**: In ingestion, pass `benchmark_date` as `event_time` when inserting benchmark nodes; optionally add/generate `benchmark_date` in CSV when missing.

After that, all 9 context graph CSVs will support correct and consistent time/date stamping for `context_nodes.occurred_at`, with optional improvements (time-of-day, edge `observed_at`) as needed later.
