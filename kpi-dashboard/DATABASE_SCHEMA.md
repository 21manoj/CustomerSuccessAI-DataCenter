# KPI Dashboard Database Schema

## Overview

The KPI Dashboard uses SQLite database with 14 tables organized into the following groups:
- **Core Entities**: Customers, Users, Accounts
- **KPI Management**: KPIs, KPI Uploads, KPI Reference Ranges, KPI Time Series
- **Health Tracking**: Health Trends
- **Playbooks**: Playbook Triggers, Playbook Executions, Playbook Reports
- **Configuration**: Customer Configs

---

## Tables Summary

| Table | Purpose | Row Count (V2) |
|-------|---------|----------------|
| customers | Customer organizations | 2 |
| users | User accounts | 2 |
| accounts | Customer accounts | 35 |
| customer_configs | Customer-specific settings | 2 |
| kpi_uploads | Upload tracking | 210 |
| kpis | KPI definitions | 14,070 |
| kpi_reference_ranges | KPI scoring rules | ~40 |
| kpi_time_series | Historical KPI values | ~5,000 |
| health_trends | Monthly health scores | ~245 |
| playbook_triggers | Playbook automation config | ~10 |
| playbook_executions | Playbook run history | ~15 |
| playbook_reports | Playbook RACI reports | ~15 |

---

## Detailed Schema

### 1. customers

**Purpose:** Stores customer organizations (tenants in multi-tenant system)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| customer_id | INTEGER | PRIMARY KEY | Auto-increment ID |
| customer_name | VARCHAR | NOT NULL | Organization name |
| email | VARCHAR | UNIQUE | Contact email |
| phone | VARCHAR | - | Contact phone |

**Relationships:**
- One-to-Many: users, accounts, kpi_uploads, health_trends
- One-to-One: customer_configs

**Example Data:**
```sql
customer_id=1, customer_name="Test Company", email="test@test.com"
customer_id=2, customer_name="ACME", email="acme@acme.com"
```

---

### 2. users

**Purpose:** User authentication and tracking

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| user_id | INTEGER | PRIMARY KEY | Auto-increment ID |
| customer_id | INTEGER | FK → customers | Tenant isolation |
| user_name | VARCHAR | NOT NULL | Display name |
| email | VARCHAR | - | Login email |
| password_hash | VARCHAR(128) | - | Hashed password |

**Relationships:**
- Many-to-One: customers
- One-to-Many: kpi_uploads

**Example Data:**
```sql
user_id=1, customer_id=1, email="test@test.com", user_name="Test User"
user_id=2, customer_id=2, email="acme@acme.com", user_name="ACME User"
```

---

### 3. accounts

**Purpose:** Individual customer accounts managed within each customer organization

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| account_id | INTEGER | PRIMARY KEY | Auto-increment ID |
| customer_id | INTEGER | FK → customers | Tenant isolation |
| account_name | VARCHAR | NOT NULL | Account name |
| revenue | NUMERIC(15,2) | DEFAULT 0 | Annual revenue |
| account_status | VARCHAR | DEFAULT 'active' | active/inactive |
| industry | VARCHAR | - | Industry vertical |
| region | VARCHAR | - | Geographic region |
| created_at | DATETIME | AUTO | Creation timestamp |
| updated_at | DATETIME | AUTO | Last update timestamp |

**Relationships:**
- Many-to-One: customers
- One-to-Many: kpis, kpi_uploads, health_trends, kpi_time_series

**Example Data:**
```sql
account_id=1, customer_id=1, account_name="TechCorp Solutions", 
  revenue=1200000, industry="Technology", region="North America"
```

---

### 4. customer_configs

**Purpose:** Customer-specific configuration and settings

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| config_id | INTEGER | PRIMARY KEY | Auto-increment ID |
| customer_id | INTEGER | FK → customers, UNIQUE | One config per customer |
| kpi_upload_mode | VARCHAR | DEFAULT 'corporate' | 'corporate' or 'account_rollup' |
| category_weights | TEXT | - | JSON: category weight percentages |
| master_file_name | VARCHAR | - | Uploaded master file name |
| created_at | DATETIME | AUTO | Creation timestamp |
| updated_at | DATETIME | AUTO | Last update timestamp |

**category_weights JSON Structure:**
```json
{
  "Relationship Strength": 0.20,
  "Adoption & Engagement": 0.25,
  "Support & Experience": 0.20,
  "Product Value": 0.20,
  "Business Outcomes": 0.15
}
```

---

### 5. kpi_uploads

**Purpose:** Tracks each KPI data file upload

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| upload_id | INTEGER | PRIMARY KEY | Auto-increment ID |
| customer_id | INTEGER | FK → customers | Tenant isolation |
| account_id | INTEGER | FK → accounts | Associated account |
| user_id | INTEGER | FK → users | Who uploaded |
| uploaded_at | DATETIME | AUTO | Upload timestamp |
| version | INTEGER | NOT NULL | Version number |
| original_filename | VARCHAR | - | Original file name |
| raw_excel | BLOB | - | Binary Excel file |
| parsed_json | JSON | - | Parsed structure |

**Relationships:**
- Many-to-One: customers, accounts, users
- One-to-Many: kpis

---

### 6. kpis

**Purpose:** Individual KPI definitions and current values

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| kpi_id | INTEGER | PRIMARY KEY | Auto-increment ID |
| upload_id | INTEGER | FK → kpi_uploads | Source upload |
| account_id | INTEGER | FK → accounts | Associated account |
| category | VARCHAR | - | Tab/category name |
| row_index | INTEGER | - | Row in Excel |
| health_score_component | VARCHAR | - | Health category |
| weight | VARCHAR | - | Importance weight |
| data | VARCHAR | - | Current value |
| source_review | VARCHAR | - | Data source |
| kpi_parameter | VARCHAR | - | KPI name/metric |
| impact_level | VARCHAR | - | Critical/High/Medium/Low |
| measurement_frequency | VARCHAR | - | Monthly/Quarterly/etc |
| last_edited_by | INTEGER | FK → users | Last editor |
| last_edited_at | DATETIME | - | Last edit time |

**Relationships:**
- Many-to-One: kpi_uploads, accounts, users
- One-to-Many: kpi_time_series

**Example Data:**
```sql
kpi_id=1, account_id=1, category="Relationship Strength",
  kpi_parameter="NPS Score", data="45", impact_level="Critical"
```

---

### 7. kpi_reference_ranges

**Purpose:** Defines scoring thresholds for each KPI metric

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| range_id | INTEGER | PRIMARY KEY | Auto-increment ID |
| kpi_name | VARCHAR | NOT NULL, UNIQUE | KPI metric name |
| unit | VARCHAR | NOT NULL | Measurement unit |
| higher_is_better | BOOLEAN | NOT NULL, DEFAULT TRUE | Scoring direction |
| critical_min | NUMERIC(10,2) | NOT NULL | Critical range min |
| critical_max | NUMERIC(10,2) | NOT NULL | Critical range max |
| risk_min | NUMERIC(10,2) | NOT NULL | Risk range min |
| risk_max | NUMERIC(10,2) | NOT NULL | Risk range max |
| healthy_min | NUMERIC(10,2) | NOT NULL | Healthy range min |
| healthy_max | NUMERIC(10,2) | NOT NULL | Healthy range max |
| created_at | DATETIME | AUTO | Creation timestamp |
| updated_at | DATETIME | AUTO | Last update timestamp |
| created_by | INTEGER | FK → users | Creator |
| updated_by | INTEGER | FK → users | Last updater |

**Example Data:**
```sql
kpi_name="NPS Score", unit="score", higher_is_better=TRUE,
  critical_min=-100, critical_max=10,
  risk_min=10, risk_max=30,
  healthy_min=30, healthy_max=100
```

---

### 8. kpi_time_series

**Purpose:** Historical KPI values by month/year for trend analysis

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| kpi_id | INTEGER | FK → kpis, NOT NULL | Associated KPI |
| account_id | INTEGER | FK → accounts, NOT NULL | Associated account |
| customer_id | INTEGER | FK → customers, NOT NULL | Tenant isolation |
| month | INTEGER | NOT NULL | Month (1-12) |
| year | INTEGER | NOT NULL | Year (YYYY) |
| value | NUMERIC(10,2) | - | KPI value |
| health_status | VARCHAR(20) | - | Healthy/Risk/Critical |
| health_score | NUMERIC(5,2) | - | 0.00-100.00 |
| created_at | DATETIME | AUTO | Creation timestamp |
| updated_at | DATETIME | AUTO | Last update timestamp |

**Constraints:**
- UNIQUE(kpi_id, month, year)

**Example Data:**
```sql
kpi_id=1, account_id=1, month=9, year=2025, value=45.50,
  health_status="Critical", health_score=25.00
```

---

### 9. health_trends

**Purpose:** Monthly aggregated health scores per account

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| trend_id | INTEGER | PRIMARY KEY | Auto-increment ID |
| account_id | INTEGER | FK → accounts, NOT NULL | Associated account |
| customer_id | INTEGER | FK → customers, NOT NULL | Tenant isolation |
| month | INTEGER | NOT NULL | Month (1-12) |
| year | INTEGER | NOT NULL | Year (YYYY) |
| overall_health_score | NUMERIC(5,2) | NOT NULL | 0.00-100.00 |
| product_usage_score | NUMERIC(5,2) | - | Category score |
| support_score | NUMERIC(5,2) | - | Category score |
| customer_sentiment_score | NUMERIC(5,2) | - | Category score |
| business_outcomes_score | NUMERIC(5,2) | - | Category score |
| relationship_strength_score | NUMERIC(5,2) | - | Category score |
| total_kpis | INTEGER | DEFAULT 0 | KPI count |
| valid_kpis | INTEGER | DEFAULT 0 | Valid KPI count |
| created_at | DATETIME | AUTO | Creation timestamp |
| updated_at | DATETIME | AUTO | Last update timestamp |

**Constraints:**
- UNIQUE(account_id, month, year)

**Example Data:**
```sql
account_id=1, month=9, year=2025, overall_health_score=68.50,
  product_usage_score=72.00, support_score=65.00
```

---

### 10. playbook_triggers

**Purpose:** Configuration for automated playbook triggering

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| trigger_id | INTEGER | PRIMARY KEY | Auto-increment ID |
| customer_id | INTEGER | FK → customers, NOT NULL | Tenant isolation |
| playbook_type | VARCHAR(50) | NOT NULL | voc/activation/sla/renewal/expansion |
| trigger_config | TEXT | - | JSON: threshold configuration |
| auto_trigger_enabled | BOOLEAN | DEFAULT FALSE | Enable auto-trigger |
| last_evaluated | DATETIME | - | Last evaluation time |
| last_triggered | DATETIME | - | Last trigger time |
| trigger_count | INTEGER | DEFAULT 0 | Trigger count |
| created_at | DATETIME | AUTO | Creation timestamp |
| updated_at | DATETIME | AUTO | Last update timestamp |

**Constraints:**
- UNIQUE(customer_id, playbook_type)

**trigger_config JSON Example (VoC Sprint):**
```json
{
  "nps_threshold": 10,
  "csat_threshold": 3.6,
  "churn_risk_threshold": 30,
  "health_drop_threshold": 10
}
```

---

### 11. playbook_executions

**Purpose:** Tracks each playbook execution instance

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-increment ID |
| execution_id | VARCHAR(36) | NOT NULL, UNIQUE, INDEXED | UUID |
| customer_id | INTEGER | FK → customers, NOT NULL, INDEXED | Tenant isolation |
| account_id | INTEGER | FK → accounts, INDEXED | Target account |
| playbook_id | VARCHAR(50) | NOT NULL, INDEXED | Playbook type ID |
| status | VARCHAR(20) | DEFAULT 'in-progress' | in-progress/completed/failed/cancelled |
| current_step | VARCHAR(100) | - | Current step ID |
| execution_data | JSON | NOT NULL | Full execution object |
| started_at | DATETIME | NOT NULL | Start timestamp |
| completed_at | DATETIME | - | Completion timestamp |
| created_at | DATETIME | AUTO | Creation timestamp |
| updated_at | DATETIME | AUTO | Last update timestamp |

**Relationships:**
- Many-to-One: customers, accounts
- One-to-One: playbook_reports (CASCADE DELETE)

**Indexes:**
- idx_customer_playbook_exec (customer_id, playbook_id)
- idx_account_playbook_exec (account_id, playbook_id)
- idx_status (status)

**execution_data JSON Structure:**
```json
{
  "id": "exec_1760487926017_e954mwgcv",
  "playbookId": "voc-sprint",
  "customerId": 1,
  "accountId": 1,
  "status": "in-progress",
  "currentStep": "voc-week1-survey",
  "startedAt": "2025-10-15T00:25:26.017Z",
  "results": [
    {
      "stepId": "voc-week1-survey",
      "completedAt": "2025-10-15T00:30:15.123Z",
      "status": "completed",
      "result": { "responses": 45, "nps": 42 }
    }
  ],
  "context": {
    "customerId": 1,
    "accountId": 1,
    "accountName": "TechCorp Solutions",
    "userId": 1,
    "userName": "Test User"
  },
  "metadata": {
    "priority": "high",
    "triggeredBy": "manual"
  }
}
```

---

### 12. playbook_reports

**Purpose:** Comprehensive RACI reports for playbook executions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| report_id | INTEGER | PRIMARY KEY | Auto-increment ID |
| execution_id | VARCHAR(36) | FK → playbook_executions (CASCADE), UNIQUE, INDEXED | Execution UUID |
| customer_id | INTEGER | FK → customers, NOT NULL, INDEXED | Tenant isolation |
| account_id | INTEGER | FK → accounts, INDEXED | Target account |
| playbook_id | VARCHAR(50) | NOT NULL, INDEXED | Playbook type ID |
| playbook_name | VARCHAR(100) | NOT NULL | Playbook display name |
| account_name | VARCHAR(200) | - | Account name |
| status | VARCHAR(20) | DEFAULT 'in-progress' | in-progress/completed/failed |
| report_data | JSON | NOT NULL | Full RACI report |
| duration | VARCHAR(50) | - | Playbook duration |
| steps_completed | INTEGER | DEFAULT 0 | Completed step count |
| total_steps | INTEGER | - | Total step count |
| started_at | DATETIME | NOT NULL | Start timestamp |
| completed_at | DATETIME | - | Completion timestamp |
| report_generated_at | DATETIME | AUTO | Report generation time |
| created_at | DATETIME | AUTO | Creation timestamp |
| updated_at | DATETIME | AUTO | Last update timestamp |

**Relationships:**
- One-to-One: playbook_executions (with CASCADE DELETE)
- Many-to-One: customers, accounts

**Indexes:**
- idx_customer_playbook (customer_id, playbook_id)
- idx_account_playbook (account_id, playbook_id)

**report_data JSON Structure:**
```json
{
  "execution_id": "exec_1760487926017_e954mwgcv",
  "playbook_id": "voc-sprint",
  "playbook_name": "VoC Sprint",
  "account_name": "TechCorp Solutions",
  "duration": "30 days",
  "executive_summary": "Executed 4-week VoC sprint...",
  "raci_breakdown": {
    "responsible": ["CSM", "Product Manager"],
    "accountable": ["VP Customer Success"],
    "consulted": ["Engineering Lead"],
    "informed": ["Account Executive", "CEO"]
  },
  "outcomes_achieved": {
    "nps_improvement": {
      "baseline": 42,
      "current": 58,
      "improvement": "+16 points",
      "status": "Achieved"
    },
    "csat_improvement": {
      "baseline": 3.2,
      "current": 4.1,
      "improvement": "+0.9 points",
      "status": "Achieved"
    }
  },
  "exit_criteria_met": {
    "nps_above_50": true,
    "action_items_created": true,
    "executive_sponsor_identified": true
  },
  "next_steps": [
    "Schedule quarterly NPS tracking",
    "Implement top 3 feature requests",
    "Conduct executive business review"
  ],
  "report_generated_at": "2025-10-15T00:25:30.145880"
}
```

---

## Database Relationships

```
customers (1) ──< (M) users
customers (1) ──< (M) accounts
customers (1) ──< (M) kpi_uploads
customers (1) ──< (M) health_trends
customers (1) ──< (M) kpi_time_series
customers (1) ──< (M) playbook_triggers
customers (1) ──< (M) playbook_executions
customers (1) ──< (M) playbook_reports
customers (1) ──── (1) customer_configs

accounts (1) ──< (M) kpis
accounts (1) ──< (M) kpi_uploads
accounts (1) ──< (M) health_trends
accounts (1) ──< (M) kpi_time_series
accounts (1) ──< (M) playbook_executions
accounts (1) ──< (M) playbook_reports

kpi_uploads (1) ──< (M) kpis

kpis (1) ──< (M) kpi_time_series

playbook_executions (1) ──── (1) playbook_reports (CASCADE DELETE)
```

---

## Key Design Patterns

### 1. Multi-Tenancy
- All tables have `customer_id` foreign key
- Ensures data isolation between customers
- API queries automatically filter by customer_id from session

### 2. Cascade Deletion
- `playbook_executions` → `playbook_reports`: ON DELETE CASCADE
- When execution is deleted, report is automatically deleted

### 3. Soft vs Hard Delete
- Accounts: Soft delete via `account_status = 'inactive'`
- Playbooks: Hard delete (CASCADE)

### 4. Versioning
- `kpi_uploads.version`: Track multiple uploads per account
- Latest version always used for current data

### 5. Time Series Data
- `kpi_time_series`: Monthly KPI values for trends
- `health_trends`: Monthly aggregated health scores
- Unique constraints on (entity_id, month, year)

### 6. JSON Storage
- Flexible schema for complex data (execution_data, report_data, trigger_config)
- Easy to extend without schema migrations
- Full-text searchable in SQLite

---

## Indexes

Performance indexes on frequently queried columns:

```sql
-- playbook_executions
CREATE INDEX idx_customer_playbook_exec ON playbook_executions(customer_id, playbook_id);
CREATE INDEX idx_account_playbook_exec ON playbook_executions(account_id, playbook_id);
CREATE INDEX idx_status ON playbook_executions(status);

-- playbook_reports
CREATE INDEX idx_customer_playbook ON playbook_reports(customer_id, playbook_id);
CREATE INDEX idx_account_playbook ON playbook_reports(account_id, playbook_id);

-- Unique indexes
CREATE UNIQUE INDEX ON kpi_time_series(kpi_id, month, year);
CREATE UNIQUE INDEX ON health_trends(account_id, month, year);
CREATE UNIQUE INDEX ON playbook_triggers(customer_id, playbook_type);
```

---

## Sample Queries

### Get all accounts with low health scores
```sql
SELECT a.account_name, h.overall_health_score
FROM accounts a
JOIN health_trends h ON a.account_id = h.account_id
WHERE a.customer_id = 1
  AND h.month = 9 AND h.year = 2025
  AND h.overall_health_score < 70
ORDER BY h.overall_health_score ASC;
```

### Get playbook execution history for an account
```sql
SELECT pe.execution_id, pe.playbook_id, pe.status,
       pe.started_at, pe.completed_at
FROM playbook_executions pe
WHERE pe.customer_id = 1 AND pe.account_id = 1
ORDER BY pe.started_at DESC;
```

### Get KPI trends for last 6 months
```sql
SELECT kts.month, kts.year, kts.value, kts.health_status
FROM kpi_time_series kts
JOIN kpis k ON kts.kpi_id = k.kpi_id
WHERE k.kpi_parameter = 'NPS Score'
  AND kts.account_id = 1
ORDER BY kts.year DESC, kts.month DESC
LIMIT 6;
```

---

## Migration History

Migrations managed via Flask-Migrate (Alembic):

```
migrations/versions/
├── xxxx_initial_schema.py
├── xxxx_add_kpi_time_series.py
├── xxxx_add_playbook_tables.py
├── xxxx_add_cascade_delete.py
└── xxxx_add_indexes.py
```

Current schema version: **Latest (October 2025)**

---

## Database Location

**V1 (Production):**
- Path: `/app/instance/kpi_dashboard.db` (Docker)
- Backup: Automatic daily backups

**V2 (New Production):**
- Path: `/app/instance/kpi_dashboard.db` (Docker)
- Separate database from V1
- Contains: Test Company (25 accounts) + ACME (10 accounts)

**Local Development:**
- Path: `/Users/manojgupta/kpi-dashboard/instance/kpi_dashboard.db`
- Shared with development server

---

## Performance Considerations

1. **Indexes**: All foreign keys and frequently queried columns
2. **JSON Storage**: Efficient for complex nested data
3. **Batch Operations**: Use bulk inserts for KPI uploads
4. **Connection Pooling**: SQLAlchemy manages connections
5. **Query Optimization**: Use JOINs instead of N+1 queries

---

**Last Updated:** October 15, 2025  
**Schema Version:** V2 Production  
**Total Tables:** 12  
**Total Relationships:** 20+

