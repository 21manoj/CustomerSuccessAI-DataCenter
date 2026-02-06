# Config Parameters for Customer 19 (DB)

## Canonical data flow (no 02_upload / 02_load)

- **Upload:** CSVs are uploaded via **POST /api/onboarding/upload** and saved to `verticals/customer{N}-dc2_s/data/`.
- **Load:** **POST /api/onboarding/process-data** reads those saved CSVs and loads them directly into PostgreSQL (dc2s_kpis, qualitative_signals). No 02_upload or 02_load scripts are used in this workflow.

## Where config is stored

- **Table:** `customer_configs`
- **Key:** `customer_id = 19` (one row per customer)

## Schema: `customer_configs` (CustomerConfig model)

| Column | Type | Description |
|--------|------|-------------|
| `config_id` | int | Primary key |
| `customer_id` | int | FK to customers (unique) |
| **SaaS (legacy)** | | |
| `kpi_upload_mode` | string | `'corporate'` or `'account_rollup'` |
| `category_weights` | text | JSON string of category weights |
| `master_file_name` | string | Name of uploaded master file |
| `openai_api_key_encrypted` | text | Encrypted OpenAI API key |
| `openai_api_key_updated_at` | datetime | When key was last updated |
| **DC2_S** | | |
| `vertical` | string | `'saas'` or `'dc2_s'` |
| `dc2s_pillar_weights` | JSON | `{"AI": 0.25, "CH": 0.20, "DV": 0.15, "EX": 0.20, "OS": 0.20}` |
| `dc2s_enabled_kpis` | JSON | List of KPI codes enabled for upload/validation, e.g. `["AI-KPI1", "AI-KPI2", ...]` |
| `dc2s_kpi_overrides` | JSON | Per-KPI overrides, e.g. `{"AI-KPI1": {"target": 90}}` |
| `dc2s_kpi_weights` | JSON | Per-pillar KPI weights |
| `dc2s_kpi_definitions` | JSON | Custom KPI definitions |
| **Meta** | | |
| `config_version` | string | e.g. `'1.0'` |
| `customized_by` | string | Who last updated |
| `created_at` | datetime | |
| `updated_at` | datetime | |

## What is set for Customer 19 when created via onboarding

When customer 19 is created via **POST /api/onboarding/complete** (e.g. `complete_onboarding()` in `onboarding_api_v2_config_aware.py`), the following are set:

- **vertical:** `'dc2_s'`
- **dc2s_enabled_kpis:** default 15 KPIs (3 per pillar), e.g.  
  `['AI-KPI1','AI-KPI2','AI-KPI3','CH-KPI1','CH-KPI2','CH-KPI3','DV-KPI1','DV-KPI2','DV-KPI3','EX-KPI1','EX-KPI2','EX-KPI3','OS-KPI1','OS-KPI2','OS-KPI3']`
- **dc2s_pillar_weights:** default or request body `weights`, e.g.  
  `{'AI': 0.25, 'CH': 0.20, 'DV': 0.15, 'EX': 0.20, 'OS': 0.20}`

Other DC2_S columns (`dc2s_kpi_overrides`, `dc2s_kpi_weights`, `dc2s_kpi_definitions`) are left null/empty unless provided.

## How to query config for customer 19

```sql
SELECT config_id, customer_id, vertical,
       dc2s_pillar_weights, dc2s_enabled_kpis, dc2s_kpi_overrides,
       dc2s_kpi_weights, config_version, updated_at
FROM customer_configs
WHERE customer_id = 19;
```

Or use the API (as a user belonging to customer 19):

- **GET /api/dc2s/config** — returns DC2_S config for the current customer (pillar_weights, enabled_kpis, kpi_overrides, kpi_weights, kpi_definitions).

## Config-aware logic in the codebase

- **Onboarding CSV validation:** `validate_csv_against_config(customer_id, csv_file)` uses `ConfigLoader(customer_id)` and **CustomerConfig** (`dc2s_enabled_kpis`, pillar weights) to validate/filter KPIs. **Config-aware.**
- **DC2_S config API:** **GET/PUT /api/dc2s/config** read/write **CustomerConfig** (dc2s_*). **Config-aware.**
- **Health score from dc2s_kpis:** DC2_S health uses `verticals.dc2_s.api_routes.calculate_kpi_health(kpi_values, customer_id=...)`. When `customer_id` is provided, **`get_weights_for_customer(customer_id)`** loads **CustomerConfig.dc2s_pillar_weights** from the DB and uses those L2 weights; otherwise it falls back to code default weights. Fallback is logged explicitly: `"FALLBACK: Using code default L2 weights (no CustomerConfig or vertical != dc2_s)"` or similar. **Config-aware.**

## KPI code conventions

- **Customer 19 CSV / dc2s_kpis:** Use pillar prefix in KPI code: `AI-KPI1`, `CH-KPI1`, `DV-KPI1`, `EX-KPI1`, `OS-KPI1`, etc.
- **Vertical catalog (kpi_definitions.py):** Uses `P1-KPI1`, `P2-KPI1`, … (P1–P5).  
  Health calculation currently uses the vertical catalog; if only `AI-KPI1`-style codes exist in `dc2s_kpis`, ensure either the catalog or the health logic recognizes both naming schemes (or normalizes them) so onboarding data is included in health.
