# 🚀 STEP 1: DEPLOY JOURNEY DATA (Phase 4)
## Load Phase 2/3 Files to PostgreSQL & Qdrant

**Goal:** Deploy your 3 accounts (187 events, 3,220 KPIs) to databases  
**Time:** 30-45 minutes  
**Prerequisites:** PostgreSQL database, Phase 4 scripts

---

## 📋 PRE-DEPLOYMENT CHECKLIST

### **1. Verify You Have Phase 2/3 Files:**
```bash
# Check your files exist:
ls -la | grep -E "(events.csv|kpis.csv|journey.json)"

# Should see:
# ✅ 1767800625203_account_10001_events.csv
# ✅ 1767800625205_account_10003_events.csv  
# ✅ 1767800625205_account_10007_events.csv
# ✅ all_accounts_kpis.csv
# ✅ kpi_metadata.json
# ✅ 1767800625204_account_10001_journey.json
# ✅ 1767800625205_account_10003_journey.json
# ✅ 1767800625205_account_10007_journey.json
```

### **2. Verify You Have Phase 4 Scripts:**
```bash
# Check Phase 4 scripts downloaded:
ls -la | grep phase4

# Should see:
# ✅ migration_journey_phase4.py (creates 8 tables)
# ✅ load_journey_data_phase4.py (loads data)
# ✅ generate_milestones_phase4.py (creates training labels)
# ✅ load_journey_to_qdrant_phase4.py (Qdrant loader)
# ✅ verify_production_safety.py (safety checker)
```

### **3. Database Credentials:**
```bash
# PostgreSQL connection string format:
# postgresql://username:password@host:port/database

# Example:
# postgresql://csm_user:password123@localhost:5432/csm_dev

# Verify connection works:
psql "postgresql://username:password@host:port/database" -c "SELECT version();"
```

### **4. Python Environment:**
```bash
# Check Python version (3.8+)
python --version

# Install required packages:
pip install sqlalchemy psycopg2-binary pandas alembic --break-system-packages

# For Qdrant (optional, can do later):
pip install qdrant-client openai --break-system-packages
```

---

## 🔄 DEPLOYMENT STEPS

### **STEP 1A: Generate Milestones (5 minutes)**

**What it does:** Creates 6 training labels (ground truth outcomes) from your 3 accounts

```bash
cd /path/to/your/phase2-3/files

python generate_milestones_phase4.py

# Output (creates 4 CSV files):
# ✅ account_10007_milestones.csv (3 milestones - crisis recovery)
# ✅ account_10003_milestones.csv (2 milestones - churn)
# ✅ account_10001_milestones.csv (1 milestone - expansion)
# ✅ all_accounts_milestones.csv (6 total)

# Verify files created:
ls -la *milestones.csv
```

**Example milestone:**
```csv
account_id,week_number,date,milestone_type,description,arr_impact,...
10007,30,2024-07-22,expansion_decision_approved,"$400K expansion...",400000,...
```

---

### **STEP 1B: Create PostgreSQL Tables (5 minutes)**

**What it does:** Creates 8 new tables with `journey_` prefix (safe, doesn't touch production)

```bash
# Option A: Using Alembic (if you have migrations set up)
alembic upgrade head

# Option B: Direct SQL execution
psql "postgresql://username:password@host:port/database" -f migration_journey_phase4.py

# Option C: Using Python directly
python << EOF
from migration_journey_phase4 import upgrade
from sqlalchemy import create_engine

engine = create_engine("postgresql://username:password@host:port/database")
upgrade()
EOF

# Verify tables created:
psql "postgresql://username:password@host:port/database" -c "\dt journey_*"

# Should show 8 tables:
# ✅ journey_accounts
# ✅ journey_events
# ✅ journey_kpis
# ✅ journey_health
# ✅ journey_metadata
# ✅ journey_milestones
# ✅ signal_predictions
# ✅ prediction_explanations
```

---

### **STEP 1C: Load Journey Data to PostgreSQL (10-15 minutes)**

**What it does:** Loads all Phase 2/3 data + generates sample predictions

```bash
python load_journey_data_phase4.py \
    --db-url "postgresql://username:password@host:port/database" \
    --data-dir /path/to/your/phase2-3/files

# Expected output:
# ✅ Loading journey accounts... (3 accounts)
# ✅ Loading journey events... (187 events)
# ✅ Loading journey KPIs... (3,220 KPI data points)
# ✅ Calculating health snapshots... (92 weekly snapshots)
# ✅ Loading milestones... (6 milestones)
# ✅ Generating sample predictions... (3 predictions)
# ✅ Generating explanations... (3 explanations)
# ✅ Loading metadata... (1 record)
# 
# Phase 4 deployment complete! ✅
```

**What the script does automatically:**
1. Reads your Phase 2/3 CSV files ✅
2. Parses your JSON files ✅
3. Maps column names (sentiment → sentiment_level, etc.) ✅
4. Transforms KPIs from wide→long format (92 rows → 3,220 rows) ✅
5. Calculates pillar scores (P1-P5 from 35 KPIs) ✅
6. Aggregates health snapshots per week ✅
7. Loads milestones ✅
8. Generates 3 sample predictions (baseline examples) ✅
9. Creates explanations (why predictions were made) ✅

---

### **STEP 1D: Verify PostgreSQL Data (5 minutes)**

```bash
# Connect to database
psql "postgresql://username:password@host:port/database"

# Check accounts loaded
SELECT * FROM journey_accounts;
-- Should show 3 accounts: 307000, {ACCOUNT_ID_START+2}, 10007

# Check events count
SELECT journey_account_id, COUNT(*) as event_count
FROM journey_events 
GROUP BY journey_account_id
ORDER BY journey_account_id;
-- Should show: 1→34, 2→54, 3→99 events

# Check KPIs count
SELECT journey_account_id, COUNT(*) as kpi_count
FROM journey_kpis 
GROUP BY journey_account_id
ORDER BY journey_account_id;
-- Should show: 1→735, 2→770, 3→1,715 KPIs

# Check health snapshots
SELECT journey_account_id, COUNT(*) as week_count
FROM journey_health 
GROUP BY journey_account_id
ORDER BY journey_account_id;
-- Should show: 1→21, 2→22, 3→49 weeks

# Check milestones
SELECT * FROM journey_milestones ORDER BY week_number;
-- Should show 6 milestones

# Check predictions
SELECT * FROM signal_predictions;
-- Should show 3 sample predictions

# Exit
\q
```

**Expected counts:**
```
journey_accounts:              3 rows
journey_events:              187 rows
journey_kpis:              3,220 rows
journey_health:               92 rows
journey_metadata:              1 row
journey_milestones:            6 rows
signal_predictions:            3 rows
prediction_explanations:       3 rows
─────────────────────────────────
TOTAL:                     3,512 rows
```

---

### **STEP 1E: Load to Qdrant (Optional - 10 minutes)**

**What it does:** Creates separate training collection with embedded events

**Note:** Can skip this for now and do later. PostgreSQL is enough to proceed to Step 2.

```bash
# Only if you want to test Qdrant-based retrieval:
python load_journey_to_qdrant_phase4.py \
    --qdrant-url https://your-cluster.qdrant.io:6333 \
    --qdrant-api-key YOUR_QDRANT_API_KEY \
    --openai-api-key YOUR_OPENAI_API_KEY \
    --data-dir /path/to/your/phase2-3/files

# Expected output:
# ✅ Creating collection: journey_training_vectors_customer_297
# ✅ Embedding 187 events with OpenAI...
# ✅ Uploading to Qdrant...
# ✅ Collection created with 187 vectors
# 
# Qdrant deployment complete! ✅
```

**Qdrant collection details:**
```
Collection: journey_training_vectors_customer_297
Vectors: 187 (one per event)
Dimensions: 1536 (OpenAI text-embedding-3-small)
Metadata: account_id, week_number, event_type, phase, sentiment, etc.
Flag: is_training_data: true (isolated from production)
```

---

### **STEP 1F: Run Safety Verification (5 minutes)**

**What it does:** Confirms production tables are untouched

```bash
python verify_production_safety.py \
    --db-url "postgresql://username:password@host:port/database" \
    --output step1_verification.json

# Expected output:
# ═══════════════════════════════════════════════
# PRODUCTION SAFETY VERIFICATION
# ═══════════════════════════════════════════════
# 
# 🔡 Connecting to database...
# ✅ Connected!
# 
# 🔍 Checking production tables...
#   ✅ accounts              10 rows (UNTOUCHED)
#   ✅ kpis                  450 rows (UNTOUCHED)
#   ✅ health_trends         120 rows (UNTOUCHED)
#   ✅ dc2s_kpis            800 rows (UNTOUCHED)
#   ... (all production tables)
# 
# 🔍 Checking for journey tables...
#   Found 8 journey tables:
#     - journey_accounts
#     - journey_events
#     - journey_kpis
#     - journey_health
#     - journey_metadata
#     - journey_milestones
#     - signal_predictions
#     - prediction_explanations
# 
# 💾 Results saved to: step1_verification.json
# 
# ═══════════════════════════════════════════════
# ✅ Verification Complete!
# ═══════════════════════════════════════════════
```

**Check the verification file:**
```bash
cat step1_verification.json

# Should show:
# {
#   "production_tables": {
#     "accounts": {"row_count": 10, "modified": false},
#     "kpis": {"row_count": 450, "modified": false},
#     ...
#   },
#   "journey_tables": [
#     "journey_accounts",
#     "journey_events",
#     ...
#   ],
#   "safety_status": "PASS"
# }
```

---

## ✅ STEP 1 COMPLETE CHECKLIST

After running all steps, verify:

- [x] **Milestones generated:** 4 CSV files created
- [x] **PostgreSQL tables created:** 8 tables with `journey_` prefix
- [x] **Data loaded:** 3,512 total rows across 8 tables
- [x] **Accounts:** 3 accounts (307000, {ACCOUNT_ID_START+2}, 10007)
- [x] **Events:** 187 events loaded
- [x] **KPIs:** 3,220 KPI data points loaded
- [x] **Health:** 92 weekly snapshots calculated
- [x] **Milestones:** 6 training labels loaded
- [x] **Predictions:** 3 sample predictions generated
- [x] **Safety verified:** Production tables untouched
- [x] **Optional - Qdrant:** Training collection created (skip if not ready)

---

## 🎯 WHAT YOU NOW HAVE

### **Database State:**
```
PostgreSQL Database: csm_dev
├─ Production Tables (UNTOUCHED) ✅
│  ├─ accounts (10 rows)
│  ├─ kpis (450 rows)
│  └─ ... (all existing tables)
│
└─ Journey Tables (NEW) ✅
   ├─ journey_accounts (3 rows)
   ├─ journey_events (187 rows)
   ├─ journey_kpis (3,220 rows)
   ├─ journey_health (92 rows)
   ├─ journey_metadata (1 row)
   ├─ journey_milestones (6 rows) 🆕
   ├─ signal_predictions (3 rows) 🆕
   └─ prediction_explanations (3 rows) 🆕
```

### **Training Data Summary:**
```
3 Accounts:
├─ Account 307000 (CloudScale AI Labs)
│  ├─ Pattern: Proactive Growth
│  ├─ Duration: 21 weeks
│  ├─ Events: 34
│  ├─ KPIs: 735
│  ├─ Outcome: $5M expansion ✅
│  └─ Milestone: Expansion approved (Week 15)
│
├─ Account {ACCOUNT_ID_START+2} (Quantum Computing Corp)
│  ├─ Pattern: Ignored → Churn
│  ├─ Duration: 22 weeks
│  ├─ Events: 54
│  ├─ KPIs: 770
│  ├─ Outcome: $3.8M lost ❌
│  └─ Milestones: Warning signals (Week 1), Final churn (Week 22)
│
└─ Account 10007 (Legacy Manufacturing Corp)
   ├─ Pattern: Crisis → Recovery
   ├─ Duration: 49 weeks
   ├─ Events: 99
   ├─ KPIs: 1,715
   ├─ Outcome: 40% expansion ✅
   └─ Milestones: Crisis (Week 5), Recovery (Week 20), Expansion (Week 30)
```

---

## 🚨 TROUBLESHOOTING

### **Error: "psycopg2 not found"**
```bash
pip install psycopg2-binary --break-system-packages
```

### **Error: "Permission denied on table"**
```bash
# Grant permissions:
psql "postgresql://..." -c "GRANT ALL ON SCHEMA public TO your_user;"
```

### **Error: "Table already exists"**
```bash
# Drop journey tables and retry:
psql "postgresql://..." << EOF
DROP TABLE IF EXISTS prediction_explanations CASCADE;
DROP TABLE IF EXISTS signal_predictions CASCADE;
DROP TABLE IF EXISTS journey_milestones CASCADE;
DROP TABLE IF EXISTS journey_metadata CASCADE;
DROP TABLE IF EXISTS journey_health CASCADE;
DROP TABLE IF EXISTS journey_kpis CASCADE;
DROP TABLE IF EXISTS journey_events CASCADE;
DROP TABLE IF EXISTS journey_accounts CASCADE;
EOF

# Then re-run migration
```

### **Error: "Cannot find CSV files"**
```bash
# Make sure you're in the right directory:
cd /path/to/your/phase2-3/files
ls -la *.csv

# If files have different names, update --data-dir parameter
```

---

## ➡️ NEXT STEPS

**After Step 1 is complete:**

### **STEP 2: Bootstrap Weights** (30 min)
- Load Supermicro simulation weights (32 KPIs)
- Document weight structure
- File: `bootstrap_weights_supermicro.json`

### **STEP 3: Mapping Layer** (30 min)
- Map 32 bootstrap KPIs → 35 journey KPIs
- Semantic alignment
- Test mapping accuracy

### **STEP 4: Test Signal Analyst** (15 min)
- Run predictions on journey data
- Compare vs milestones
- Measure baseline accuracy (target: 55-65%)

---

## 📞 SUPPORT

If you encounter issues:

1. **Check logs:** Look at script output for specific errors
2. **Verify database:** Ensure PostgreSQL is accessible
3. **Check file paths:** Verify all CSV/JSON files are in correct location
4. **Review verification:** Check `step1_verification.json` for details

---

**Ready to deploy? Let's go!** 🚀
