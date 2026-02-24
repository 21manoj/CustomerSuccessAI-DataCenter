# Customer Onboarding Guide — CS Pulse Platform (DC2_S Vertical)

## From Zero to First Dashboard in 5 Steps

**Audience:** Platform administrators, DevOps, load testers
**Vertical:** DC2_S (Data Center Hardware Infrastructure)
**Backend:** Flask + PostgreSQL + Qdrant

---

## Prerequisites

### Environment Variables (must be set before starting)

```bash
# CRITICAL — Required
export DATABASE_URL="postgresql://cspulse:cspulse@localhost:5432/cspulse"
export SECRET_KEY="your-secret-key-at-least-32-characters-long"

# RECOMMENDED — Needed for RAG + embeddings
export OPENAI_API_KEY="sk-..."
export QDRANT_URL="http://localhost:6333"
export QDRANT_API_KEY=""  # Empty for local, set for cloud

# OPTIONAL — Feature flags
export FLASK_ENV="development"
export LOG_LEVEL="INFO"
```

### Services Running

| Service | Port | Verify |
|---------|------|--------|
| CS Pulse backend | 5059 | `curl http://localhost:5059/api/health` |
| PostgreSQL | 5432 | `psql $DATABASE_URL -c "SELECT 1"` |
| Qdrant (for RAG) | 6333 | `curl http://localhost:6333/dashboard` |

---

## Step 1: Register the Customer

### API Call

```bash
curl -X POST http://localhost:5059/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Nexus Data Centers",
    "admin_name": "Sarah Chen",
    "email": "sarah.chen@nexusdc.com",
    "password": "NexusDC2026!",
    "phone": "+1-555-0100",
    "vertical": "dc2_s"
  }'
```

### Expected Response

```json
{
  "status": "success",
  "message": "Registration successful",
  "customer_id": 300,
  "customer_uuid": "dc2_s_cust_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "vertical": "dc2_s",
  "user_id": 450,
  "user_uuid": "dc2_s_user_f9e8d7c6-b5a4-3210-fedc-ba0987654321",
  "email": "sarah.chen@nexusdc.com",
  "company_name": "Nexus Data Centers"
}
```

### What Gets Created (5 records across 3 tables)

**File:** `backend/registration_api.py:32-218`

| Table | Record | Key Fields |
|-------|--------|------------|
| `customers` | 1 row | `customer_id=300`, `customer_name='Nexus Data Centers'`, `domain='nexusdc.com'`, `uuid='dc2_s_cust_...'`, `vertical='dc2_s'` |
| `users` | 1 row | `user_id=450`, `customer_id=300`, `email='sarah.chen@nexusdc.com'`, `password_hash=pbkdf2:sha256:...` |
| `customer_configs` | 1 row | `customer_id=300`, `kpi_upload_mode='account_rollup'`, `category_weights={...}` |
| `playbook_triggers` | 5 rows | voc, activation, sla, renewal, expansion — all `auto_trigger_enabled=True` |

### Validation Rules

- Company name: must be unique across platform
- Email domain: must be unique (one company per domain)
- Email: globally unique across all users
- Password: minimum 6 characters
- Vertical: must be one of: `saas`, `dc2_s`, `fintech`, `healthcare`, etc.

### SQL to Verify Registration

```sql
-- Check customer was created
SELECT customer_id, customer_name, email, domain, uuid, vertical, created_at
FROM customers
WHERE customer_name = 'Nexus Data Centers';

-- Check admin user was created
SELECT user_id, customer_id, user_name, email, uuid, created_at
FROM users
WHERE customer_id = 300;

-- Check config was created with default weights
SELECT config_id, customer_id, kpi_upload_mode, category_weights
FROM customer_configs
WHERE customer_id = 300;

-- Check 5 playbook triggers were created
SELECT trigger_id, customer_id, playbook_type, auto_trigger_enabled,
       trigger_config::text
FROM playbook_triggers
WHERE customer_id = 300
ORDER BY playbook_type;
```

### Add Additional Users (Optional)

```bash
curl -X POST http://localhost:5059/api/register/add-user \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "nexusdc.com",
    "user_name": "Mike Johnson",
    "email": "mike.johnson@nexusdc.com",
    "password": "MikeNexus2026!"
  }'
```

**File:** `backend/registration_api.py:220-295`

---

## Step 2: Complete Onboarding (Create Accounts + Generate CSVs)

### Option A: Demo Mode (Auto-Generates Everything)

```bash
curl -X POST http://localhost:5059/api/onboarding/complete \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 300,
    "customer_name": "Nexus Data Centers",
    "domain": "nexusdc.com",
    "industry": "Data Center Infrastructure",
    "vertical": "dc2_s",
    "email": "sarah.chen@nexusdc.com",
    "username": "sarah_chen",
    "password": "NexusDC2026!",
    "num_accounts": 10,
    "weights": {
      "AI": 0.25,
      "CH": 0.20,
      "DV": 0.15,
      "EX": 0.20,
      "OS": 0.20
    },
    "onboarding_mode": "demo"
  }'
```

**File:** `backend/onboarding_api_v2_config_aware.py:506-1045`

### Expected Response

```json
{
  "success": true,
  "customer_id": 300,
  "customer_name": "Nexus Data Centers",
  "domain": "nexusdc.com",
  "accounts": 10,
  "account_details": [
    {"account_id": 300001, "account_name": "Nexus Data Centers - Production"},
    {"account_id": 300002, "account_name": "Nexus Data Centers - Staging"},
    {"account_id": 300003, "account_name": "Nexus Data Centers - Development"},
    {"account_id": 300004, "account_name": "Nexus Data Centers - QA"},
    {"account_id": 300005, "account_name": "Nexus Data Centers - UAT"},
    {"account_id": 300006, "account_name": "Nexus Data Centers - DR"},
    {"account_id": 300007, "account_name": "Nexus Data Centers - Sandbox"},
    {"account_id": 300008, "account_name": "Nexus Data Centers - Integration"},
    {"account_id": 300009, "account_name": "Nexus Data Centers - Performance"},
    {"account_id": 300010, "account_name": "Nexus Data Centers - Edge"}
  ],
  "account_id_range": "300001 - 300010",
  "user": {
    "user_id": 450,
    "email": "sarah.chen@nexusdc.com",
    "username": "sarah_chen",
    "role": "admin"
  },
  "config": {
    "enabled_kpis": 15,
    "pillars": 5,
    "weights": {"AI": 0.25, "CH": 0.20, "DV": 0.15, "EX": 0.20, "OS": 0.20},
    "vertical": "dc2_s"
  },
  "directory_provisioned": true,
  "csv_files_generated": true,
  "message": "Onboarding complete!"
}
```

### Account ID Convention

```
account_id = customer_id × 1000 + sequence

Customer 300 → accounts 300001 through 300010
Customer 301 → accounts 301001 through 301010
```

### What Gets Created

| Table | Records | Key Fields |
|-------|---------|------------|
| `accounts` | 10 rows | `account_id=300001-300010`, `customer_id=300`, environment names |
| `customer_configs` | Updated | `dc2s_pillar_weights`, `dc2s_enabled_kpis` set |

### Directory Provisioned

```
backend/verticals/customer300-dc2_s/
├── data/
│   ├── accounts.csv          ← 10 accounts with full profile metadata
│   ├── kpi_measurements.csv  ← 15 KPIs × 10 accounts × 12 months = 1,800 rows
│   ├── qualitative_signals.csv ← Signals per account (meeting notes, emails, etc.)
│   ├── products.csv          ← Products per customer
│   └── customers.csv         ← Customer master record
```

### Option B: Custom Mode (Upload Your Own CSVs)

If you have real data, skip demo mode and upload your own files:

```bash
# Step 2a: Create accounts without CSV generation
curl -X POST http://localhost:5059/api/onboarding/complete \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 300,
    "customer_name": "Nexus Data Centers",
    "vertical": "dc2_s",
    "num_accounts": 10,
    "onboarding_mode": "custom"
  }'

# Step 2b: Upload your CSV files
curl -X POST http://localhost:5059/api/onboarding/upload \
  -F "customer_id=300" \
  -F "accounts=@/path/to/accounts.csv" \
  -F "kpi_measurements=@/path/to/kpi_measurements.csv" \
  -F "qualitative_signals=@/path/to/qualitative_signals.csv" \
  -F "products=@/path/to/products.csv"
```

**File:** `backend/onboarding_api_v2_config_aware.py:1818-2013`

### SQL to Verify Accounts

```sql
-- Check all 10 accounts created with correct customer_id
SELECT account_id, customer_id, account_name, industry, vertical,
       region, account_status, revenue, arr
FROM accounts
WHERE customer_id = 300
ORDER BY account_id;

-- Check account ID range follows convention
SELECT MIN(account_id) AS first_account,
       MAX(account_id) AS last_account,
       COUNT(*) AS total_accounts
FROM accounts
WHERE customer_id = 300;
-- Expected: first=300001, last=300010, total=10
```

---

## Step 3: Process Data (Load CSVs → Database + Embeddings)

### API Call

```bash
curl -X POST http://localhost:5059/api/onboarding/process-data \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 300,
    "vertical": "dc2_s",
    "skip_wizard_b": true,
    "skip_wizard_c": false
  }'
```

**File:** `backend/onboarding_api_v2_config_aware.py:1047-1795`

### Processing Pipeline (6 Steps)

```
Step 1: Data Loading (CSV → Database)
  ├── accounts.csv       → accounts table (UPDATE/INSERT)
  ├── kpi_measurements.csv → dc2s_kpis table (1,800 rows)
  ├── qualitative_signals.csv → qualitative_signals table
  ├── products.csv       → products table
  └── profiles.csv       → accounts.profile_metadata (JSON)

Step 2: Embedding Generation (Qdrant)
  └── Runs 03_embed_customer300_OPENAI.py
      └── Creates vector embeddings for RAG queries

Step 3: Data Validation
  └── Runs 04_validate_data_integrity.py
      └── Checks referential integrity, null values, ranges

Step 4: Journey Generation (Wizard A)
  └── Runs wizard_a_journey_generator.py
      └── Creates customer journey phases per account

Step 5: Pattern Analysis (Wizard B) — SKIPPED if skip_wizard_b=true
Step 6: Weight Calibration (Wizard C) — Runs if skip_wizard_c=false
  └── Adjusts pillar weights based on data patterns
```

### Tables Populated After Processing

| Table | Records Created | Source |
|-------|----------------|--------|
| `dc2s_kpis` | ~1,800 rows (15 KPIs × 10 accounts × 12 months) | kpi_measurements.csv |
| `qualitative_signals` | ~90 rows (9 per account) | qualitative_signals.csv |
| `products` | 2 rows (DC2_S Platform + Monitoring Suite) | products.csv |

### SQL to Verify Data Load

```sql
-- Check KPI data loaded (should be ~1,800 rows)
SELECT COUNT(*) AS total_kpis,
       COUNT(DISTINCT account_id) AS accounts,
       COUNT(DISTINCT kpi_code) AS kpi_codes,
       COUNT(DISTINCT measured_at) AS months,
       MIN(measured_at) AS earliest,
       MAX(measured_at) AS latest
FROM dc2s_kpis
WHERE account_id BETWEEN 300001 AND 300010;
-- Expected: ~1800, 10, 15, 12, 2024-01-01, 2024-12-01

-- Check distribution of KPIs per pillar
SELECT LEFT(kpi_code, 2) AS pillar,
       COUNT(DISTINCT kpi_code) AS kpis_per_pillar,
       ROUND(AVG(value), 2) AS avg_value
FROM dc2s_kpis
WHERE account_id BETWEEN 300001 AND 300010
GROUP BY LEFT(kpi_code, 2)
ORDER BY pillar;
-- Expected: AI=3, CH=3, DV=3, EX=3, OS=3

-- Check qualitative signals loaded
SELECT COUNT(*) AS total_signals,
       COUNT(DISTINCT account_id) AS accounts,
       COUNT(DISTINCT signal_type) AS signal_types
FROM qualitative_signals
WHERE account_id BETWEEN 300001 AND 300010;

-- Check products loaded
SELECT product_id, customer_id, product_name, category, license_type
FROM products
WHERE customer_id = 300;
```

---

## Step 4: Calculate Health Scores

### API Call

```bash
# Login first to get session cookie
curl -X POST http://localhost:5059/api/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "email": "sarah.chen@nexusdc.com",
    "password": "NexusDC2026!"
  }'

# Calculate scores for all accounts
curl -X POST http://localhost:5059/api/dc2s/scores/calculate \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "customer_id": 300,
    "measurement_month": "2024-12-01"
  }'
```

**File:** `backend/dc2s_scores_api.py:139-196`

### Score Calculation Logic (3 Levels)

```
L1: KPI Scores (individual)
    Each KPI normalized to 0-100 using target ranges
    Stored in: kpi_scores table
    ↓
L2: Pillar Scores (5 pillars, weighted average of L1)
    AI (25%) + CH (20%) + DV (15%) + EX (20%) + OS (20%)
    Stored in: pillar_scores table
    ↓
L3: Health Score (single number, weighted average of L2)
    P1-Deployment (15%) + P2-Operational (20%) + P3-AI Workload (25%)
    + P4-Channel (15%) + P5-Expansion (25%)
    Stored in: health_scores table
```

**File:** `backend/utils/score_calculator.py`

### Tables Populated After Score Calculation

| Table | Records Created | Content |
|-------|----------------|---------|
| `kpi_scores` | 150 rows (15 KPIs × 10 accounts) | Individual KPI score 0-100, status |
| `pillar_scores` | 50 rows (5 pillars × 10 accounts) | Pillar weighted score 0-100 |
| `health_scores` | 10 rows (1 per account) | Overall health 0-100 |

### SQL to Verify Scores

```sql
-- Check health scores exist for all 10 accounts
SELECT hs.account_id, a.account_name,
       hs.overall_health_score,
       hs.measurement_month,
       CASE
         WHEN hs.overall_health_score >= 80 THEN 'Healthy'
         WHEN hs.overall_health_score >= 60 THEN 'At Risk'
         ELSE 'Critical'
       END AS health_tier
FROM health_scores hs
JOIN accounts a ON a.account_id = hs.account_id
WHERE a.customer_id = 300
ORDER BY hs.overall_health_score DESC;

-- Check pillar scores breakdown for one account
SELECT ps.pillar_code, ps.pillar_score, ps.pillar_status,
       ps.contributing_kpis, ps.kpi_weights
FROM pillar_scores ps
WHERE ps.account_id = 300001
  AND ps.measurement_month = '2024-12-01'
ORDER BY ps.pillar_code;

-- Check individual KPI scores
SELECT ks.kpi_code, ks.kpi_value, ks.kpi_target,
       ks.kpi_score, ks.kpi_status
FROM kpi_scores ks
WHERE ks.account_id = 300001
  AND ks.measurement_month = '2024-12-01'
ORDER BY ks.kpi_code;

-- Customer-wide health distribution
SELECT
  COUNT(CASE WHEN overall_health_score >= 80 THEN 1 END) AS healthy,
  COUNT(CASE WHEN overall_health_score >= 60 AND overall_health_score < 80 THEN 1 END) AS at_risk,
  COUNT(CASE WHEN overall_health_score < 60 THEN 1 END) AS critical,
  ROUND(AVG(overall_health_score), 1) AS avg_health
FROM health_scores hs
JOIN accounts a ON a.account_id = hs.account_id
WHERE a.customer_id = 300;
```

---

## Step 5: Access the Dashboard

### API Calls (All require auth cookie from Step 4 login)

```bash
# 5a. List all accounts with health overview
curl -b cookies.txt http://localhost:5059/api/dc2s/accounts

# 5b. Get detailed scores for one account
curl -b cookies.txt http://localhost:5059/api/dc2s/scores/account/300001/latest

# 5c. Get customer-wide summary
curl -b cookies.txt http://localhost:5059/api/dc2s/scores/customer/summary

# 5d. Run a RAG query (requires OPENAI_API_KEY)
curl -X POST http://localhost:5059/api/direct-rag/query \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "query": "Which accounts have the lowest health scores and why?",
    "customer_id": 300
  }'
```

---

## CSV File Formats (Reference)

### accounts.csv

```csv
account_id,customer_id,account_name,industry,vertical,region,account_status,account_tier,assigned_csm,csm_manager,executive_sponsor,strategic_account,products_used,contract_start_date,contract_end_date,renewal_date,revenue,arr,mrr,primary_champion_name,champion_title,champion_email,champion_status,champion_tenure_months,champion_influence_level,economic_buyer_name,economic_buyer_title,executive_sponsor_name,executive_sponsor_title,technical_champion_name,number_active_champions,created_at,last_updated
300001,300,Nexus DC - Production,Data Center Infrastructure,dc2_s,us-east-1,active,Enterprise,Jane Smith,Bob Director,CTO,Yes,"DC2_S Platform, Monitoring Suite",2025-01-01,2027-01-01,2027-01-01,1500000.0,1500000.0,125000.0,Alice Champion,VP Infrastructure,alice@nexusdc.com,Active,18,Executive,Bob Buyer,CFO,Carol Exec,CTO,Dave Tech,3,2026-02-24,2026-02-24
```

**Required columns:** `account_id`, `customer_id`, `account_name`
**All other columns are optional** (stored in `profile_metadata` JSON if extra)

### kpi_measurements.csv

```csv
account_id,kpi_code,measured_at,value,target,pillar,weight,status
300001,AI-KPI1,2024-01-01,82.22,85.0,AI,0.25,healthy
300001,AI-KPI2,2024-01-01,79.25,85.0,AI,0.25,healthy
300001,AI-KPI3,2024-01-01,79.38,85.0,AI,0.25,healthy
300001,CH-KPI1,2024-01-01,79.97,85.0,CH,0.25,healthy
300001,CH-KPI2,2024-01-01,83.58,85.0,CH,0.25,healthy
300001,CH-KPI3,2024-01-01,78.91,85.0,CH,0.25,healthy
300001,DV-KPI1,2024-01-01,84.77,85.0,DV,0.25,healthy
300001,DV-KPI2,2024-01-01,82.33,85.0,DV,0.25,healthy
300001,DV-KPI3,2024-01-01,78.78,85.0,DV,0.25,healthy
300001,EX-KPI1,2024-01-01,82.75,85.0,EX,0.25,healthy
300001,EX-KPI2,2024-01-01,83.46,85.0,EX,0.25,healthy
300001,EX-KPI3,2024-01-01,76.31,85.0,EX,0.25,healthy
300001,OS-KPI1,2024-01-01,83.81,85.0,OS,0.25,healthy
300001,OS-KPI2,2024-01-01,77.69,85.0,OS,0.25,healthy
300001,OS-KPI3,2024-01-01,82.50,85.0,OS,0.25,healthy
```

**Required columns:** `account_id`, `kpi_code`, `measured_at`, `value`, `target`
**Optional columns:** `pillar`, `weight`, `status`

### 15 Default KPI Codes (3 per pillar)

| Pillar | Code | Description |
|--------|------|-------------|
| AI (AI Workload) | `AI-KPI1` | GPU Utilization Rate |
| AI | `AI-KPI2` | AI Job Completion Rate |
| AI | `AI-KPI3` | AI Workload Performance Index |
| CH (Channel) | `CH-KPI1` | Partner Engagement Score |
| CH | `CH-KPI2` | Channel Revenue Contribution |
| CH | `CH-KPI3` | Partner Satisfaction Index |
| DV (Deployment) | `DV-KPI1` | Deployment Velocity |
| DV | `DV-KPI2` | Configuration Accuracy |
| DV | `DV-KPI3` | Time-to-First-Workload |
| EX (Expansion) | `EX-KPI1` | Capacity Utilization |
| EX | `EX-KPI2` | Expansion Pipeline Score |
| EX | `EX-KPI3` | Upsell Readiness Index |
| OS (Operational) | `OS-KPI1` | Uptime SLA Compliance |
| OS | `OS-KPI2` | Mean Time to Recovery |
| OS | `OS-KPI3` | Incident Frequency Rate |

### qualitative_signals.csv

```csv
signal_id,account_id,signal_date,signal_type,content,sentiment,sentiment_score
sig_300001_0001,300001,2024-01-08,customer_feedback,"Champion expressed concern about GPU underutilization in Q1 planning call",negative,-0.45
sig_300001_0002,300001,2024-01-15,meeting,"QBR showed strong adoption of monitoring suite across 3 environments",positive,0.72
sig_300001_0003,300001,2024-02-10,incident,"P1 outage: 4-hour downtime on production cluster, RCA pending",negative,-0.80
sig_300001_0004,300001,2024-03-05,milestone,"Successfully completed Phase 2 GPU expansion ahead of schedule",positive,0.85
```

**Required columns:** `account_id`, `signal_date`, `signal_type`, `content`, `sentiment`
**Signal types:** `customer_feedback`, `meeting`, `incident`, `milestone`, `health_check`, `email`, `ticket`, `survey`

### products.csv

```csv
customer_id,product_id,product_name,category,license_type
300,1,DC2_S Platform,Infrastructure,Enterprise
300,2,Monitoring Suite,Operations,Professional
```

---

## Quick Reference: Python Files Involved

| Step | File | Line Range | What It Does |
|------|------|-----------|--------------|
| 1 | `backend/registration_api.py` | 32-218 | Register customer + user + config + triggers |
| 1 | `backend/id_generator.py` | — | UUID generation (`dc2_s_cust_...`) |
| 2 | `backend/onboarding_api_v2_config_aware.py` | 506-1045 | Create accounts + provision directory + generate CSVs |
| 2 | `backend/onboarding_api_v2_config_aware.py` | 1818-2013 | Upload custom CSVs |
| 3 | `backend/onboarding_api_v2_config_aware.py` | 1047-1795 | Process data pipeline (6 steps) |
| 3 | `backend/verticals/dc2_s/kpi_definitions.py` | — | 38 KPI definitions, 5 pillars |
| 4 | `backend/dc2s_scores_api.py` | 139-196 | Calculate L1/L2/L3 scores |
| 4 | `backend/utils/score_calculator.py` | — | Score normalization + weighting |
| 5 | `backend/dc2s_scores_api.py` | 23-59 | Get latest scores for account |
| 5 | `backend/dc2s_scores_api.py` | 88-132 | Get customer-wide summary |
| 5 | `backend/direct_rag_api.py` | — | RAG queries against Qdrant |
| — | `backend/auth_middleware.py` | 40-113 | Authentication + tenant isolation |
| — | `backend/models.py` | — | All table definitions |

---

## SQL: Complete State After Onboarding

Run this query after all 5 steps to verify everything is in place:

```sql
-- ============================================================
-- ONBOARDING VERIFICATION REPORT
-- Replace 300 with your actual customer_id
-- ============================================================

-- 1. Customer record
SELECT '1. CUSTOMER' AS section, customer_id, customer_name, email, domain, uuid, vertical
FROM customers WHERE customer_id = 300;

-- 2. User(s)
SELECT '2. USERS' AS section, user_id, customer_id, user_name, email, uuid
FROM users WHERE customer_id = 300;

-- 3. Config
SELECT '3. CONFIG' AS section, config_id, customer_id, kpi_upload_mode,
       dc2s_pillar_weights::text, dc2s_enabled_kpis::text
FROM customer_configs WHERE customer_id = 300;

-- 4. Playbook triggers
SELECT '4. TRIGGERS' AS section, trigger_id, playbook_type, auto_trigger_enabled,
       LEFT(trigger_config::text, 80) AS config_preview
FROM playbook_triggers WHERE customer_id = 300 ORDER BY playbook_type;

-- 5. Accounts
SELECT '5. ACCOUNTS' AS section, account_id, account_name, account_status,
       revenue, region
FROM accounts WHERE customer_id = 300 ORDER BY account_id;

-- 6. KPI data volume
SELECT '6. KPI DATA' AS section,
       COUNT(*) AS total_kpi_rows,
       COUNT(DISTINCT account_id) AS accounts_with_data,
       COUNT(DISTINCT kpi_code) AS distinct_kpis,
       COUNT(DISTINCT measured_at) AS months_of_data
FROM dc2s_kpis WHERE account_id BETWEEN 300001 AND 300010;

-- 7. Qualitative signals
SELECT '7. SIGNALS' AS section,
       COUNT(*) AS total_signals,
       COUNT(DISTINCT signal_type) AS signal_types
FROM qualitative_signals WHERE account_id BETWEEN 300001 AND 300010;

-- 8. Products
SELECT '8. PRODUCTS' AS section, product_id, product_name, category
FROM products WHERE customer_id = 300;

-- 9. Health scores
SELECT '9. HEALTH SCORES' AS section,
       hs.account_id, a.account_name,
       hs.overall_health_score,
       CASE
         WHEN hs.overall_health_score >= 80 THEN 'HEALTHY'
         WHEN hs.overall_health_score >= 60 THEN 'AT RISK'
         ELSE 'CRITICAL'
       END AS tier
FROM health_scores hs
JOIN accounts a ON a.account_id = hs.account_id
WHERE a.customer_id = 300
ORDER BY hs.overall_health_score DESC;

-- 10. Pillar scores (one account sample)
SELECT '10. PILLAR DETAIL' AS section,
       pillar_code, pillar_score, pillar_status
FROM pillar_scores
WHERE account_id = 300001
ORDER BY pillar_code;
```

### Expected Row Counts After Complete Onboarding

| Table | Expected Rows | Formula |
|-------|--------------|---------|
| `customers` | 1 | 1 per customer |
| `users` | 1+ | 1 admin + any added users |
| `customer_configs` | 1 | 1 per customer |
| `playbook_triggers` | 5 | voc, activation, sla, renewal, expansion |
| `accounts` | 10 | `num_accounts` parameter |
| `dc2s_kpis` | ~1,800 | 15 KPIs × 10 accounts × 12 months |
| `qualitative_signals` | ~90 | ~9 signals per account |
| `products` | 2 | DC2_S Platform + Monitoring Suite |
| `kpi_scores` | 150 | 15 KPIs × 10 accounts (latest month) |
| `pillar_scores` | 50 | 5 pillars × 10 accounts |
| `health_scores` | 10 | 1 per account |
| **Total** | **~2,119** | |

---

## Optional Post-Onboarding Setup

### Configure n8n Workflow Integration

```bash
curl -X POST http://localhost:5059/api/workflow/config \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "workflow_system": "n8n",
    "n8n_instance_type": "cloud",
    "n8n_base_url": "https://your-n8n.app.n8n.cloud",
    "n8n_webhook_url": "https://your-n8n.app.n8n.cloud/webhook/playbook-trigger",
    "n8n_api_key": "your-n8n-api-key",
    "webhook_secret": "your-webhook-secret-min-32-chars",
    "enabled_playbooks": ["voc", "activation", "sla", "renewal", "expansion"]
  }'
```

**File:** `backend/workflow_config_api.py`
**Table:** `customer_workflow_configs`

### Enable Feature Toggles

```bash
# Enable revenue intelligence (Power of 1 ROI engine)
curl -X POST http://localhost:5059/api/feature-toggles \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "feature_name": "revenue_intelligence",
    "enabled": true
  }'
```

**Table:** `feature_toggles`

### Build RAG Knowledge Base (if not done in Step 3)

```bash
curl -X POST http://localhost:5059/api/enhanced-rag/build-knowledge-base \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "customer_id": 300
  }'
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `409 Company name already registered` | Duplicate company_name | Use unique name or delete existing customer |
| `409 Email already registered` | Duplicate email | Use different email |
| `No scores calculated yet` | Step 4 not run | Run `POST /api/dc2s/scores/calculate` |
| `Account not found (404)` | Wrong customer_id in session | Login with correct user, check `X-Customer-ID` header |
| `Empty RAG response` | Qdrant embeddings not built | Re-run Step 3 or call `/api/enhanced-rag/build-knowledge-base` |
| `KPI data missing` | CSV parsing error | Check `kpi_measurements.csv` column names match exactly |
| `Process-data timeout` | Embedding generation slow | Set `OPENAI_API_KEY`, increase timeout, or skip with `skip_embeddings: true` |

---

## Cleanup: Delete a Customer Completely

There is no single API endpoint for this yet (see GAP-LD-30). Use this SQL in the correct FK-safe order:

```sql
-- ============================================================
-- COMPLETE CUSTOMER DELETION (FK-safe order)
-- Replace 300 with your customer_id
-- Replace 300001-300010 with your account_id range
-- ============================================================

BEGIN;

-- Leaf tables first (no dependents)
DELETE FROM query_audits       WHERE customer_id = 300;
DELETE FROM account_notes      WHERE customer_id = 300;
DELETE FROM account_snapshots  WHERE customer_id = 300;
DELETE FROM action_economics   WHERE customer_id = 300;

-- Playbook chain (reports → executions → triggers)
DELETE FROM playbook_reports    WHERE customer_id = 300;
DELETE FROM playbook_executions WHERE customer_id = 300;
DELETE FROM playbook_triggers   WHERE customer_id = 300;

-- Config and features
DELETE FROM customer_workflow_configs WHERE customer_id = 300;
DELETE FROM feature_toggles          WHERE customer_id = 300;
DELETE FROM kpi_reference_ranges     WHERE customer_id = 300;

-- Score tables (no customer_id FK — must use account_ids)
DELETE FROM health_scores       WHERE account_id BETWEEN 300001 AND 300010;
DELETE FROM pillar_scores       WHERE account_id BETWEEN 300001 AND 300010;
DELETE FROM kpi_scores          WHERE account_id BETWEEN 300001 AND 300010;
DELETE FROM qualitative_signals WHERE account_id BETWEEN 300001 AND 300010;
DELETE FROM dc2s_kpis           WHERE account_id BETWEEN 300001 AND 300010;

-- Health trends and KPI records
DELETE FROM health_trends WHERE customer_id = 300;
DELETE FROM kpis          WHERE account_id BETWEEN 300001 AND 300010;
DELETE FROM kpi_uploads   WHERE customer_id = 300;

-- Products and accounts
DELETE FROM products       WHERE customer_id = 300;
DELETE FROM accounts       WHERE customer_id = 300;

-- Activity log (CASCADE but explicit)
DELETE FROM activity_logs  WHERE customer_id = 300;

-- User and config
DELETE FROM users            WHERE customer_id = 300;
DELETE FROM customer_configs WHERE customer_id = 300;

-- Customer record last
DELETE FROM customers WHERE customer_id = 300;

COMMIT;

-- Verify cleanup
SELECT 'Remaining rows' AS check,
  (SELECT COUNT(*) FROM accounts WHERE customer_id = 300) AS accounts,
  (SELECT COUNT(*) FROM dc2s_kpis WHERE account_id BETWEEN 300001 AND 300010) AS kpis,
  (SELECT COUNT(*) FROM health_scores WHERE account_id BETWEEN 300001 AND 300010) AS health,
  (SELECT COUNT(*) FROM users WHERE customer_id = 300) AS users;
-- All should be 0
```

---

## Quick-Start Script (All 5 Steps in One)

Save this as `onboard_new_customer.sh`:

```bash
#!/bin/bash
# Usage: ./onboard_new_customer.sh <company_name> <email> <password> <num_accounts>

BASE_URL="${CS_PULSE_URL:-http://localhost:5059}"
COMPANY="$1"
EMAIL="$2"
PASSWORD="$3"
NUM_ACCOUNTS="${4:-10}"

echo "=== Step 1: Register ==="
REGISTER=$(curl -s -X POST "$BASE_URL/api/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"company_name\": \"$COMPANY\",
    \"admin_name\": \"Admin\",
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\",
    \"vertical\": \"dc2_s\"
  }")
echo "$REGISTER" | python3 -m json.tool
CUSTOMER_ID=$(echo "$REGISTER" | python3 -c "import sys,json; print(json.load(sys.stdin)['customer_id'])")
echo "Customer ID: $CUSTOMER_ID"

echo ""
echo "=== Step 2: Complete Onboarding ==="
curl -s -X POST "$BASE_URL/api/onboarding/complete" \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_id\": $CUSTOMER_ID,
    \"customer_name\": \"$COMPANY\",
    \"vertical\": \"dc2_s\",
    \"industry\": \"Data Center Infrastructure\",
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\",
    \"num_accounts\": $NUM_ACCOUNTS,
    \"onboarding_mode\": \"demo\"
  }" | python3 -m json.tool

echo ""
echo "=== Step 3: Process Data ==="
curl -s -X POST "$BASE_URL/api/onboarding/process-data" \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_id\": $CUSTOMER_ID,
    \"vertical\": \"dc2_s\",
    \"skip_wizard_b\": true,
    \"skip_wizard_c\": false
  }" | python3 -m json.tool

echo ""
echo "=== Step 4: Login + Calculate Scores ==="
curl -s -X POST "$BASE_URL/api/login" \
  -H "Content-Type: application/json" \
  -c /tmp/cs_cookies.txt \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}" | python3 -m json.tool

curl -s -X POST "$BASE_URL/api/dc2s/scores/calculate" \
  -H "Content-Type: application/json" \
  -b /tmp/cs_cookies.txt \
  -d "{\"customer_id\": $CUSTOMER_ID, \"measurement_month\": \"2024-12-01\"}" | python3 -m json.tool

echo ""
echo "=== Step 5: Verify Dashboard ==="
curl -s -b /tmp/cs_cookies.txt "$BASE_URL/api/dc2s/scores/customer/summary" | python3 -m json.tool

FIRST_ACCOUNT=$((CUSTOMER_ID * 1000 + 1))
echo ""
echo "=== Account $FIRST_ACCOUNT Detail ==="
curl -s -b /tmp/cs_cookies.txt "$BASE_URL/api/dc2s/scores/account/$FIRST_ACCOUNT/latest" | python3 -m json.tool

echo ""
echo "=== ONBOARDING COMPLETE ==="
echo "Customer ID: $CUSTOMER_ID"
echo "Accounts: ${FIRST_ACCOUNT} - $((CUSTOMER_ID * 1000 + NUM_ACCOUNTS))"
echo "Login: $EMAIL / $PASSWORD"
echo "Dashboard: $BASE_URL"

rm -f /tmp/cs_cookies.txt
```

```bash
# Run it
chmod +x onboard_new_customer.sh
./onboard_new_customer.sh "Nexus Data Centers" "sarah@nexusdc.com" "NexusDC2026!" 10
```
