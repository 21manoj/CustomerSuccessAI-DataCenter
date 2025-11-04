# Database Entity-Relationship Diagram

## Visual Schema Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CUSTOMER (Multi-Tenant Root)                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ customers                                                             │   │
│  │ • customer_id (PK)                                                    │   │
│  │ • customer_name                                                       │   │
│  │ • email (UNIQUE)                                                      │   │
│  │ • phone                                                               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│         │                 │                │              │                  │
│         │                 │                │              │                  │
│    ┌────▼────┐     ┌─────▼─────┐    ┌────▼────┐   ┌─────▼──────┐          │
│    │  users  │     │ accounts  │    │ uploads │   │   config   │          │
│    └─────────┘     └───────────┘    └─────────┘   └────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              CORE ENTITIES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────┐       ┌────────────────────┐                       │
│  │ users              │       │ accounts           │                       │
│  ├────────────────────┤       ├────────────────────┤                       │
│  │ user_id (PK)       │       │ account_id (PK)    │                       │
│  │ customer_id (FK)   │       │ customer_id (FK)   │                       │
│  │ user_name          │       │ account_name       │                       │
│  │ email              │       │ revenue            │                       │
│  │ password_hash      │       │ account_status     │                       │
│  └────────────────────┘       │ industry           │                       │
│                               │ region             │                       │
│                               │ created_at         │                       │
│                               │ updated_at         │                       │
│                               └────────────────────┘                       │
│                                        │                                    │
│                    ┌───────────────────┼───────────────────┐               │
│                    │                   │                   │               │
│              ┌─────▼─────┐      ┌─────▼─────┐      ┌─────▼─────┐         │
│              │   KPIs    │      │  Health   │      │ Playbook  │         │
│              │           │      │  Trends   │      │   Execs   │         │
│              └───────────┘      └───────────┘      └───────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          KPI DATA MANAGEMENT                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────┐                                                     │
│  │ kpi_uploads        │                                                     │
│  ├────────────────────┤                                                     │
│  │ upload_id (PK)     │                                                     │
│  │ customer_id (FK)   │                                                     │
│  │ account_id (FK)    │                                                     │
│  │ user_id (FK)       │                                                     │
│  │ uploaded_at        │                                                     │
│  │ version            │                                                     │
│  │ original_filename  │                                                     │
│  │ raw_excel (BLOB)   │                                                     │
│  │ parsed_json (JSON) │                                                     │
│  └────────────────────┘                                                     │
│           │                                                                  │
│           │ 1:M                                                              │
│           │                                                                  │
│  ┌────────▼────────────┐          ┌────────────────────┐                   │
│  │ kpis                │          │ kpi_reference_ranges│                   │
│  ├─────────────────────┤          ├────────────────────┤                   │
│  │ kpi_id (PK)         │          │ range_id (PK)      │                   │
│  │ upload_id (FK)      │          │ kpi_name (UNIQUE)  │                   │
│  │ account_id (FK)     │          │ unit               │                   │
│  │ category            │          │ higher_is_better   │                   │
│  │ row_index           │          │ critical_min/max   │                   │
│  │ health_score_comp   │          │ risk_min/max       │                   │
│  │ weight              │          │ healthy_min/max    │                   │
│  │ data                │          │ created_at         │                   │
│  │ source_review       │          │ updated_at         │                   │
│  │ kpi_parameter       │          │ created_by (FK)    │                   │
│  │ impact_level        │          │ updated_by (FK)    │                   │
│  │ measurement_freq    │          └────────────────────┘                   │
│  │ last_edited_by (FK) │                                                    │
│  │ last_edited_at      │                                                    │
│  └─────────────────────┘                                                    │
│           │                                                                  │
│           │ 1:M                                                              │
│           │                                                                  │
│  ┌────────▼────────────┐                                                    │
│  │ kpi_time_series     │                                                    │
│  ├─────────────────────┤                                                    │
│  │ id (PK)             │                                                    │
│  │ kpi_id (FK)         │                                                    │
│  │ account_id (FK)     │                                                    │
│  │ customer_id (FK)    │                                                    │
│  │ month               │                                                    │
│  │ year                │                                                    │
│  │ value               │                                                    │
│  │ health_status       │                                                    │
│  │ health_score        │                                                    │
│  │ created_at          │                                                    │
│  │ updated_at          │                                                    │
│  │ UNIQUE(kpi,mo,yr)   │                                                    │
│  └─────────────────────┘                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         HEALTH SCORE TRACKING                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │ health_trends                                                     │       │
│  ├──────────────────────────────────────────────────────────────────┤       │
│  │ trend_id (PK)                                                     │       │
│  │ account_id (FK)                                                   │       │
│  │ customer_id (FK)                                                  │       │
│  │ month, year                                                       │       │
│  │ overall_health_score                                              │       │
│  │ product_usage_score                                               │       │
│  │ support_score                                                     │       │
│  │ customer_sentiment_score                                          │       │
│  │ business_outcomes_score                                           │       │
│  │ relationship_strength_score                                       │       │
│  │ total_kpis, valid_kpis                                            │       │
│  │ created_at, updated_at                                            │       │
│  │ UNIQUE(account_id, month, year)                                   │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        PLAYBOOK SYSTEM                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────┐                                                 │
│  │ playbook_triggers      │                                                 │
│  ├────────────────────────┤                                                 │
│  │ trigger_id (PK)        │                                                 │
│  │ customer_id (FK)       │                                                 │
│  │ playbook_type          │  (voc, activation, sla, renewal, expansion)    │
│  │ trigger_config (JSON)  │                                                 │
│  │ auto_trigger_enabled   │                                                 │
│  │ last_evaluated         │                                                 │
│  │ last_triggered         │                                                 │
│  │ trigger_count          │                                                 │
│  │ created_at, updated_at │                                                 │
│  │ UNIQUE(cust,playbook)  │                                                 │
│  └────────────────────────┘                                                 │
│                                                                              │
│  ┌────────────────────────┐                                                 │
│  │ playbook_executions    │                                                 │
│  ├────────────────────────┤                                                 │
│  │ id (PK)                │                                                 │
│  │ execution_id (UUID)    │  ← UNIQUE, INDEXED                             │
│  │ customer_id (FK)       │                                                 │
│  │ account_id (FK)        │                                                 │
│  │ playbook_id            │                                                 │
│  │ status                 │  (in-progress, completed, failed, cancelled)   │
│  │ current_step           │                                                 │
│  │ execution_data (JSON)  │  ← Full execution object                       │
│  │ started_at             │                                                 │
│  │ completed_at           │                                                 │
│  │ created_at, updated_at │                                                 │
│  └────────────────────────┘                                                 │
│           │                                                                  │
│           │ 1:1 CASCADE DELETE                                               │
│           │                                                                  │
│  ┌────────▼────────────────────────────────────────────────────┐            │
│  │ playbook_reports                                             │            │
│  ├──────────────────────────────────────────────────────────────┤            │
│  │ report_id (PK)                                               │            │
│  │ execution_id (FK → playbook_executions ON DELETE CASCADE)    │            │
│  │ customer_id (FK)                                             │            │
│  │ account_id (FK)                                              │            │
│  │ playbook_id                                                  │            │
│  │ playbook_name                                                │            │
│  │ account_name                                                 │            │
│  │ status                                                       │            │
│  │ report_data (JSON)      ← RACI, outcomes, exit criteria     │            │
│  │ duration                                                     │            │
│  │ steps_completed                                              │            │
│  │ total_steps                                                  │            │
│  │ started_at, completed_at                                     │            │
│  │ report_generated_at                                          │            │
│  │ created_at, updated_at                                       │            │
│  └──────────────────────────────────────────────────────────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONFIGURATION                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────┐                 │
│  │ customer_configs                                        │                 │
│  ├────────────────────────────────────────────────────────┤                 │
│  │ config_id (PK)                                          │                 │
│  │ customer_id (FK, UNIQUE)                                │                 │
│  │ kpi_upload_mode  ('corporate' or 'account_rollup')      │                 │
│  │ category_weights (JSON)                                 │                 │
│  │   {                                                     │                 │
│  │     "Relationship Strength": 0.20,                      │                 │
│  │     "Adoption & Engagement": 0.25,                      │                 │
│  │     "Support & Experience": 0.20,                       │                 │
│  │     "Product Value": 0.20,                              │                 │
│  │     "Business Outcomes": 0.15                           │                 │
│  │   }                                                     │                 │
│  │ master_file_name                                        │                 │
│  │ created_at, updated_at                                  │                 │
│  └────────────────────────────────────────────────────────┘                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Relationships

```
TENANT ISOLATION (All tables):
  customers (1) ──< (M) All other tables via customer_id

ACCOUNT HIERARCHY:
  customers (1) ──< (M) accounts
  accounts (1) ──< (M) kpis, health_trends, kpi_time_series

KPI DATA FLOW:
  kpi_uploads (1) ──< (M) kpis
  kpis (1) ──< (M) kpi_time_series

PLAYBOOK CASCADE:
  playbook_executions (1) ──── (1) playbook_reports
    └─> ON DELETE CASCADE (delete report when execution deleted)

CONFIGURATION:
  customers (1) ──── (1) customer_configs
```

## Data Flow Examples

### 1. KPI Upload Flow
```
User uploads Excel file
    ↓
kpi_uploads (stores file + metadata)
    ↓
kpis (individual KPI records extracted)
    ↓
kpi_time_series (monthly values for trends)
    ↓
health_trends (aggregated monthly health scores)
```

### 2. Playbook Execution Flow
```
User starts playbook
    ↓
playbook_executions (tracks execution state)
    ↓
User completes steps
    ↓
execution_data updated (JSON in playbook_executions)
    ↓
playbook_reports (comprehensive RACI report generated)
    ↓
User deletes execution
    ↓
playbook_reports automatically deleted (CASCADE)
```

### 3. Health Score Calculation
```
KPI values from kpis table
    ↓
Reference ranges from kpi_reference_ranges
    ↓
Calculate health_score for each KPI
    ↓
Store in kpi_time_series
    ↓
Aggregate by category
    ↓
Store in health_trends (monthly)
```

---

**Legend:**
- `(PK)` = Primary Key
- `(FK)` = Foreign Key
- `(M)` = Many
- `(1)` = One
- `──<` = One-to-Many
- `────` = One-to-One
- `(JSON)` = JSON data type
- `(BLOB)` = Binary large object
- `UNIQUE` = Unique constraint
- `INDEXED` = Has index

---

Created: October 15, 2025
