# Onboarding Gap Fixes Applied

This document records fixes applied for the comprehensive gap analysis (STEP 1–4, orchestration, and nice-to-have items).

---

## STEP 1: `/api/onboarding/complete`

| Gap | Fix |
|-----|-----|
| **1.1 Config creation timing** | Config is committed in the same transaction as Customer/User/Accounts before CSV generation. Comment added: "Config MUST be committed BEFORE CSV generation so the generator can load CustomerConfig via ConfigLoader." |
| **1.2 Generator not fully config-aware** | In `scripts/generate_synthetic_customer_data.py`, KPI target now uses `dc2s_kpi_overrides` from ConfigLoader: `override = kpi_overrides.get(kpi_code, {}); target_value = override.get('target', ...)`. |
| **1.3 KPI code mismatch (AI/CH/DV/EX/OS vs P1–P5)** | In `verticals/dc2_s/api_routes.py`, `calculate_kpi_health` now normalizes kpi codes: `_normalize_kpi_code_for_health()` maps AI-KPI1→P3-KPI1, CH→P4, DV→P1, EX→P5, OS→P2 so catalog lookup works. |
| **1.4 No idempotency** | Request can send `idempotent: true`. If customer with same `customer_id` already exists, returns 200 with existing customer (idempotent). Otherwise returns 400 with hint to use `idempotent=true`. |
| **1.5 No rollback on partial failure** | When CSV generation fails, response still returns `success: true` with `csv_files_generated: false` and `warnings` indicating upload/process-data can be used. No DB rollback (already committed). |
| **1.6 No validation of custom weights** | Added `validate_dc2s_pillar_weights(weights)`: sum to 1.0, all pillars AI/CH/DV/EX/OS present, non-negative. Called when `weights` is provided in `/complete`; returns 400 with message if invalid. |

---

## STEP 2: `/api/onboarding/upload`

| Gap | Fix |
|-----|-----|
| **2.1 Upload doesn't validate against config** | For `file_type === 'kpis'`, after saving temp file: `filter_kpi_csv_by_config(df, customer_id, strict_mode)` filters by `dc2s_enabled_kpis`. If `strict_mode=true` (form param), rejects when disabled KPIs present; otherwise filters and adds warnings to response. |
| **2.2 No CSV schema validation** | Added `validate_kpi_csv_schema(df)`: required columns (account_id, kpi_code, value, date col, target col), numeric value/target, valid date. For KPI uploads, schema is validated before config filter; 400 returned with error list if invalid. |

---

## STEP 3: `/api/onboarding/process-data`

| Gap | Fix |
|-----|-----|
| **3.1 Data loading not config-aware** | Step 1 (data loading) now filters KPI DataFrame by `ConfigLoader(customer_id).get_enabled_kpis()` before `to_sql('dc2s_kpis')`. Disabled KPIs are not loaded. |
| **3.2 Embedding config-awareness** | Not changed (script behavior). Documented that embedding script should use same enabled_kpis; Step 1 ensures only enabled KPIs are in DB. |
| **3.3 Journey config-awareness** | Not changed (script behavior). Documented. |
| **3.4 Wizard C – no side effects** | After Wizard C updates CustomerConfig: (1) Logging added. (2) **Response payload**: when pillar weights are updated, response includes `config_changes` (`pillar_weights_updated`, `old_weights`, `new_weights`), `action_required` (recalculate health / refresh dashboards), and a `warnings` entry with `type: 'config_changed'`, `message`, `action_required` so the user knows scores may be stale. No automatic cache invalidation (no shared cache implemented). |
| **3.5 No transaction isolation** | Response now includes `execution_state`: `data_loaded`, `embeddings_created`, `validation_run`, `journey_generated`, `weight_calibrated`. Caller can see partial state. |
| **3.6 No cleanup on failure** | No automatic rollback/cleanup (complex; would require tracking inserts and Qdrant state). Left for future enhancement. |
| **3.7 Script not found – silent failure** | Critical steps: `data_loading`, `embeddings`. If either is missing from `steps_completed`, response is 500 with message "Critical step(s) failed or skipped". Optional steps: validation, pattern_analysis, weight_calibration; response includes `optional_steps_skipped` when applicable. |
| **3.8 No progress tracking** | Added `GET /api/onboarding/status/<customer_id>`. Returns `in_progress`, `current_step`, `steps_completed`, `started_at` when process-data is running. In-memory per process; `_onboarding_progress` updated at step start and cleared on completion/error. |

---

## Orchestration / Cross-cutting

| Issue | Fix |
|-------|-----|
| **Config → Generator timing** | Confirmed: commit happens before subprocess run; generator runs in new process and sees committed config. |
| **CSV → Loader filtering** | Step 1 (process-data) and upload (for KPI files) both filter by `dc2s_enabled_kpis`. |
| **Loader → Embeddings consistency** | Only enabled KPIs are loaded into DB; embedding script reads from DB (same filter implicitly). |
| **Health calculation code mismatch** | Health uses normalized codes (AI/CH/DV/EX/OS → P1–P5) in `calculate_kpi_health`. |
| **Wizard C → Cache invalidation** | Logged; no automatic invalidation (no shared cache). |

---

## STEP 4: Verification

| Gap | Fix |
|-----|-----|
| **4.1 No automated verification** | Not implemented. Can be added as post–process-data smoke tests (e.g. GET health, journey API). |

---

## Who loads onboarding CSVs into the DB

**Canonical loader: `/api/onboarding/process-data` (Step 1).** No 02_load scripts in the workflow.

| CSV (onboarding or upload) | Loaded into DB by process-data | Purpose |
|----------------------------|---------------------------------|---------|
| **accounts.csv** | **accounts** (upsert by account_id) | Account list, revenue (ARR), industry, region; extra columns → `profile_metadata` JSON. |
| **kpi_measurements.csv** | **dc2s_kpis** (filtered by enabled_kpis) | KPI time series for health. |
| **qualitative_signals.csv** | **qualitative_signals** | Signals for RAG/analytics. |
| **products.csv** | **products** | Product catalog; if no account_id in CSV, assigned to first account of customer. |
| **profiles.csv** or **account_profiles.csv** | **account_profiles** (if table exists) or **accounts.profile_metadata** | ARR, CSM name, Champion name, and other profile attributes. |

So ARR, CSM name, Champion name, etc. are populated from **accounts.csv** (extra columns → `profile_metadata`) and/or **profiles.csv** / **account_profiles.csv** when you run process-data after upload or onboarding.

---

## Files Modified

- `onboarding_api_v2_config_aware.py`: weight validation, idempotency, partial success, upload config/schema validation, process-data filter, **accounts/products/profiles loading**, critical/optional steps, progress tracking, status endpoint, Wizard C logging.
- `scripts/generate_synthetic_customer_data.py`: use `dc2s_kpi_overrides` for target per KPI.
- `verticals/dc2_s/api_routes.py`: KPI code normalization (AI/CH/DV/EX/OS → P1–P5) in `calculate_kpi_health`.

---

## Verification: Check all tables populated

Use these SQL checks after **/complete** and after **/process-data** (replace `19` with your `customer_id`; account range = `customer_id * 1000 + 1` to `customer_id * 1000 + 10` for 10 accounts).

### After `/complete` (basic accounts only; no products/KPIs/signals from CSV yet)

```sql
-- Accounts: created by /complete
SELECT COUNT(*) FROM accounts WHERE customer_id = 19;
-- Expected: 10

-- Products: not loaded by /complete (only by process-data from products.csv)
SELECT COUNT(*) FROM products WHERE customer_id = 19;
-- Expected: 0
```

### After `/process-data` (CSVs loaded into DB)

```sql
-- Accounts: same count, rows updated from accounts.csv if present
SELECT COUNT(*) FROM accounts WHERE customer_id = 19;
-- Expected: 10

-- Products: loaded from products.csv
SELECT COUNT(*) FROM products WHERE customer_id = 19;
-- Expected: > 0 (e.g. 2 if using generator's products.csv)

-- KPIs: loaded from kpi_measurements.csv (enabled KPIs only), account range 19001–19010
SELECT COUNT(*) FROM dc2s_kpis WHERE account_id BETWEEN 19001 AND 19010;
-- Expected: ~1800 (e.g. 10 accounts × 15 KPIs × 12 months = 1800)

-- Signals: loaded from qualitative_signals.csv
SELECT COUNT(*) FROM qualitative_signals WHERE account_id BETWEEN 19001 AND 19010;
-- Expected: ~303
```

**Sample account rows (revenue/ARR, industry, region, profile_metadata populated from accounts.csv):**

```sql
SELECT
    account_id,
    account_name,
    revenue AS arr,   -- Should be populated from accounts.csv
    industry,         -- Should be populated
    region,           -- Should be populated
    profile_metadata -- Should have JSON (extra CSV columns or from profiles)
FROM accounts
WHERE customer_id = 19
LIMIT 5;
```

Optional one-liner for customer 19:

```sql
SELECT
  (SELECT COUNT(*) FROM accounts WHERE customer_id = 19) AS accounts,
  (SELECT COUNT(*) FROM products WHERE customer_id = 19) AS products,
  (SELECT COUNT(*) FROM dc2s_kpis WHERE account_id BETWEEN 19001 AND 19010) AS dc2s_kpis,
  (SELECT COUNT(*) FROM qualitative_signals WHERE account_id BETWEEN 19001 AND 19010) AS qualitative_signals;
-- After process-data expect: accounts=10, products>0, dc2s_kpis~1800, qualitative_signals~300+
```

---

## New Helpers / Endpoints

- `validate_dc2s_pillar_weights(weights)` → (bool, error_message)
- `validate_kpi_csv_schema(df)` → (bool, list of errors)
- `filter_kpi_csv_by_config(df, customer_id, strict_mode)` → (filtered_df, warnings)
- `GET /api/onboarding/status/<customer_id>` → progress for process-data
