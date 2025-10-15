# Data Persistence Status Report

## Overview
**YES - Your customer data IS persisted!** ✅

All customer data is stored in the SQLite database and survives server restarts.

---

## Database Location

**Development:**
```
/Users/manojgupta/kpi-dashboard/instance/kpi_dashboard.db
```

**Docker/Production:**
```
/app/instance/kpi_dashboard.db
```

---

## What's Persisted (18 Tables)

### ✅ **Core Customer Data**

#### 1. **Customers** (`customers` table)
- Customer ID
- Customer name
- Email, phone
- **Current Data:** 1 customer (Test Company)

#### 2. **Users** (`users` table)
- User ID
- Customer ID (foreign key)
- Name, email
- Password hash
- **Current Data:** 1 user (test@test.com)

#### 3. **Customer Configs** (`customer_configs` table)
- KPI upload mode (corporate vs account_rollup)
- Category weights (JSON)
- Master file name
- **Persisted:** Yes ✅

---

### ✅ **Account & KPI Data**

#### 4. **Accounts** (`accounts` table)
- Account ID
- Customer ID (foreign key)
- Account name
- Revenue, industry, region
- Account status
- Created/Updated timestamps
- **Current Data:** 25 accounts

#### 5. **KPIs** (`kpis` table)
- KPI ID
- Account ID (foreign key)
- KPI parameter, category
- Data value
- Impact level, weight
- Measurement frequency
- **Current Data:** 625 KPIs (25 KPIs × 25 accounts)

#### 6. **KPI Uploads** (`kpi_uploads` table)
- Upload ID
- Customer ID, Account ID
- User ID, uploaded timestamp
- Version number
- Original filename
- Raw Excel file (LargeBinary)
- Parsed JSON
- **Current Data:** 25 uploads

#### 7. **KPI Time Series** (`kpi_time_series` table)
- Time series data by month/year
- KPI values over time
- Health status and scores
- **Persisted:** Yes ✅

---

### ✅ **Health & Analytics Data**

#### 8. **Health Trends** (`health_trends` table)
- Account health trends over time
- **Persisted:** Yes ✅

#### 9. **KPI Reference Ranges** (`kpi_reference_ranges` table)
- KPI thresholds (critical, risk, healthy)
- Impact scoring rules
- **Persisted:** Yes ✅

#### 10. **Customer Insights** (`customer_insights` table)
- Generated insights
- **Persisted:** Yes ✅

#### 11. **Financial Projections** (`financial_projections` table)
- Revenue forecasts
- **Persisted:** Yes ✅

#### 12. **Industry Benchmarks** (`industry_benchmarks` table)
- Industry comparison data
- **Persisted:** Yes ✅

#### 13. **KPI Best Practices** (`kpi_best_practices` table)
- Best practice recommendations
- **Persisted:** Yes ✅

---

### ✅ **Playbook Data**

#### 14. **Playbook Executions** (`playbook_executions` table)
- Execution ID (UUID)
- Customer ID, Account ID
- Playbook ID, status
- Current step
- Full execution data (JSON)
- Started/Completed timestamps
- **Current Data:** 3 executions (VoC Sprint, Expansion Timing, Renewal Safeguard)
- **Persisted:** Yes ✅

#### 15. **Playbook Reports** (`playbook_reports` table)
- Report ID
- Execution ID (foreign key with CASCADE DELETE)
- Customer ID, Account ID
- Playbook ID, name
- Full report data (JSON) with RACI, outcomes, exit criteria
- Steps completed
- Started/Completed/Generated timestamps
- **Current Data:** 3 reports (VoC Sprint, Expansion Timing, Renewal Safeguard)
- **Persisted:** Yes ✅
- **Cascade Delete:** Yes (deletes when execution deleted)

#### 16. **Playbook Triggers** (`playbook_triggers` table)
- Trigger configurations for each playbook type
- Auto-trigger settings
- Last evaluated/triggered timestamps
- **Persisted:** Yes ✅

---

### ✅ **RAG System Data**

#### 17. **RAG Knowledge Base** (`rag_knowledge_base` table)
- Indexed documents for RAG
- **Persisted:** Yes ✅

#### 18. **RAG Query Log** (`rag_query_log` table)
- Query history and responses
- **Persisted:** Yes ✅

---

## What's NOT Persisted (In-Memory Only)

### ⚠️ **Temporary/Cache Data**

1. **RAG Query Cache** (`query_cache.py`)
   - In-memory cache of RAG query results
   - **Cleared on server restart**
   - **Purpose:** Performance optimization
   - **Impact:** Minimal (cache rebuilds on first query)

2. **FAISS Index** (`enhanced_rag_openai.py`)
   - Vector embeddings for semantic search
   - **Rebuilt on first query**
   - **Purpose:** Fast similarity search
   - **Impact:** ~5 seconds to rebuild on first query

3. **Session Data**
   - User login sessions
   - **Cleared on browser close/logout**
   - **Purpose:** Security
   - **Impact:** Users need to re-login

---

## Current Database Contents

**As of last check:**

```
Customers: 1
  - Test Company (ID: 1)

Users: 1
  - test@test.com (Customer ID: 1)

Accounts: 25
  - TechCorp Solutions, Acme Corp, etc.

KPIs: 625
  - 25 KPIs per account across 5 categories

Playbook Executions: 3
  - VoC Sprint for TechCorp Solutions (in-progress)
  - Expansion Timing for TechCorp Solutions (in-progress)
  - Renewal Safeguard for TechCorp Solutions (in-progress)

Playbook Reports: 3
  - VoC Sprint - TechCorp Solutions (in-progress)
  - Expansion Timing - TechCorp Solutions (in-progress)
  - Renewal Safeguard - TechCorp Solutions (in-progress)
```

---

## Data Lifecycle

### Creating Data
1. **Customer/User:** Created via API or seeding
2. **Accounts:** Created via KPI upload
3. **KPIs:** Created via Excel upload
4. **Playbook Executions:** Created when starting playbook
5. **Playbook Reports:** Generated when viewing report

All saved to database immediately ✅

### Reading Data
1. **On Server Startup:**
   - Playbook executions loaded into memory
   - Playbook reports loaded into memory
   - RAG knowledge base rebuilt on first query

2. **On User Login:**
   - Customer data queried
   - Account data queried
   - KPI data queried

### Updating Data
1. **KPI Updates:** Via Excel re-upload
2. **Playbook Progress:** Each step saves to DB
3. **Trigger Settings:** Saved to `playbook_triggers` table

### Deleting Data
1. **Playbook Execution:** CASCADE deletes associated report
2. **Account:** Would cascade delete KPIs (if configured)
3. **Customer:** Would cascade delete all related data (if configured)

---

## Database Backup

### Manual Backup
```bash
# Copy the database file
cp /Users/manojgupta/kpi-dashboard/instance/kpi_dashboard.db \
   /Users/manojgupta/kpi-dashboard/backups/kpi_dashboard_$(date +%Y%m%d_%H%M%S).db
```

### Automated Backup (Recommended)
Add to cron or scheduled task:
```bash
# Daily backup at 2 AM
0 2 * * * cp /Users/manojgupta/kpi-dashboard/instance/kpi_dashboard.db \
            /Users/manojgupta/kpi-dashboard/backups/kpi_dashboard_$(date +\%Y\%m\%d).db
```

---

## Data Recovery

### Restore from Backup
```bash
# Stop server first
lsof -ti:5059 | xargs kill -9

# Restore database
cp /Users/manojgupta/kpi-dashboard/backups/kpi_dashboard_20251014.db \
   /Users/manojgupta/kpi-dashboard/instance/kpi_dashboard.db

# Restart server
cd /Users/manojgupta/kpi-dashboard && ./venv/bin/python backend/run_server.py
```

---

## Persistence Verification

### Test 1: Check Database File
```bash
ls -lh /Users/manojgupta/kpi-dashboard/instance/kpi_dashboard.db
```

**Expected:** File exists with size > 100KB

### Test 2: Query Data After Restart
```bash
# Restart server
lsof -ti:5059 | xargs kill -9
cd /Users/manojgupta/kpi-dashboard && ./venv/bin/python backend/run_server.py &

# Wait 5 seconds, then query
sleep 5
curl -s http://localhost:5059/api/accounts -H "X-Customer-ID: 1" | python3 -m json.tool | head -20
```

**Expected:** Your 25 accounts returned

### Test 3: Verify Playbook Persistence
```bash
cd /Users/manojgupta/kpi-dashboard/backend
../venv/bin/python -c "
from app import app, db
from models import PlaybookExecution, PlaybookReport

with app.app_context():
    execs = PlaybookExecution.query.count()
    reports = PlaybookReport.query.count()
    print(f'Playbook Executions: {execs}')
    print(f'Playbook Reports: {reports}')
"
```

**Expected:** 
```
Playbook Executions: 3
Playbook Reports: 3
```

---

## Summary

### ✅ **PERSISTED (Survives Server Restart):**
1. ✅ Customers & Users
2. ✅ Accounts (all 25)
3. ✅ KPIs (all 625)
4. ✅ KPI Uploads (Excel files + metadata)
5. ✅ KPI Time Series data
6. ✅ Health trends & reference ranges
7. ✅ **Playbook Executions** (with full state)
8. ✅ **Playbook Reports** (with RACI, outcomes, exit criteria)
9. ✅ Playbook Trigger Settings
10. ✅ Customer configs (upload mode, category weights)
11. ✅ Financial projections
12. ✅ Best practices
13. ✅ Industry benchmarks
14. ✅ RAG knowledge base entries

### ⚠️ **NOT PERSISTED (Rebuilds on Restart):**
1. ⚠️ RAG query cache (in-memory only)
2. ⚠️ FAISS vector index (rebuilds on first query)
3. ⚠️ User sessions (logout on browser close)

---

## Database File

**Location:** `/Users/manojgupta/kpi-dashboard/instance/kpi_dashboard.db`

**Check it:**
```bash
ls -lh /Users/manojgupta/kpi-dashboard/instance/kpi_dashboard.db
```

**Backup it:**
```bash
cp /Users/manojgupta/kpi-dashboard/instance/kpi_dashboard.db \
   ~/Desktop/kpi_dashboard_backup_$(date +%Y%m%d).db
```

---

## Conclusion

**YES - All your customer data is persisted!** ✅

- 1 Customer (Test Company)
- 1 User (test@test.com)
- 25 Accounts
- 625 KPIs
- 25 KPI Uploads
- 3 Playbook Executions
- 3 Playbook Reports

Everything is in the SQLite database and will be there when you restart the server! 🎉

**Your data is safe!** 💾

