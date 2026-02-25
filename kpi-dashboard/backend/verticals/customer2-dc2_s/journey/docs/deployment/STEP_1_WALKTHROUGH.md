# 🚶 STEP 1 WALKTHROUGH - Copy & Paste Commands
## Organize Files → Deploy to PostgreSQL

**Time:** 45-60 minutes  
**Goal:** Organized directory + Data loaded to PostgreSQL

---

## ⏸️ PREREQUISITES

Before starting, ensure you have:
- [ ] PostgreSQL database accessible
- [ ] Python 3.8+ installed
- [ ] Phase 4 scripts downloaded from Claude
- [ ] Phase 1-3 data files ready

---

## 📍 STEP-BY-STEP COMMANDS

### **PART 1: ORGANIZE FILES (15 minutes)**

#### **1.1 Create Directory Structure**

```bash
# Navigate to your project
cd ~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer2-dc2_s/

# Create organized structure
mkdir -p journey/{scripts/{phase1,phase3,phase4,phase5},data/{raw/{phase1,phase2,phase3},processed,bootstrap},docs/deployment,logs,config}

# Verify structure
ls -R journey/
```

**✅ Expected:** Directory tree created with multiple subdirectories

---

#### **1.2 Move Phase 1-3 Data Files**

**Important:** Replace `/path/to/your/files/` with actual location of your uploaded files

```bash
# Set base directory
BASE_DIR=~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer2-dc2_s
JOURNEY_DIR=$BASE_DIR/journey

# Where are your files currently?
# Example: cd ~/Downloads  (wherever you have the uploaded files)
cd /path/to/your/files/

# Move Phase 1 (Account 10007)
mv *account_10007_events.csv $JOURNEY_DIR/data/raw/phase1/account_10007_events.csv
mv *account_10007_journey.json $JOURNEY_DIR/data/raw/phase1/account_10007_journey.json
mv *account_10007_report.md $JOURNEY_DIR/data/raw/phase1/account_10007_report.md

# Move Phase 2 (Account 12000)
mv *account_10001_events.csv $JOURNEY_DIR/data/raw/phase2/account_10001_events.csv
mv *account_10001_journey.json $JOURNEY_DIR/data/raw/phase2/account_10001_journey.json
mv *account_10001_report.md $JOURNEY_DIR/data/raw/phase2/account_10001_report.md

# Move Phase 2 (Account {ACCOUNT_ID_START+2})
mv *account_10003_events.csv $JOURNEY_DIR/data/raw/phase2/account_10003_events.csv
mv *account_10003_journey.json $JOURNEY_DIR/data/raw/phase2/account_10003_journey.json
mv *account_10003_report.md $JOURNEY_DIR/data/raw/phase2/account_10003_report.md

# Move Phase 3 KPIs
mv all_accounts_kpis.csv $JOURNEY_DIR/data/raw/phase3/
mv kpi_metadata.json $JOURNEY_DIR/data/raw/phase3/

# Move scripts
mv journey_pattern_generator.py $JOURNEY_DIR/scripts/phase1/
mv kpi_generator_phase3.py $JOURNEY_DIR/scripts/phase3/

# Move documentation
mv PHASE_*_COMPLETE_SUMMARY.md $JOURNEY_DIR/docs/
mv THREE_ACCOUNT_COMPARISON.md $JOURNEY_DIR/docs/ 2>/dev/null || true
```

**✅ Expected:** All files moved to organized locations

---

#### **1.3 Add Phase 4 Scripts**

**Important:** Replace `/path/to/downloads/` with where you saved Phase 4 scripts from Claude

```bash
# Copy Phase 4 scripts
cp /path/to/downloads/migration_journey_phase4.py $JOURNEY_DIR/scripts/phase4/
cp /path/to/downloads/load_journey_data_phase4.py $JOURNEY_DIR/scripts/phase4/
cp /path/to/downloads/generate_milestones_phase4.py $JOURNEY_DIR/scripts/phase4/
cp /path/to/downloads/load_journey_to_qdrant_phase4.py $JOURNEY_DIR/scripts/phase4/
cp /path/to/downloads/journey_schema_phase4.py $JOURNEY_DIR/scripts/phase4/
cp /path/to/downloads/verify_production_safety.py $JOURNEY_DIR/scripts/phase4/

# Copy deployment guides
cp /path/to/downloads/STEP_1_DEPLOY_JOURNEY_DATA.md $JOURNEY_DIR/docs/deployment/
cp /path/to/downloads/PHASE_4_FINAL_SUMMARY.md $JOURNEY_DIR/docs/
```

**✅ Expected:** Phase 4 scripts in journey/scripts/phase4/

---

#### **1.4 Verify Organization**

```bash
cd $JOURNEY_DIR

# Check all files in place
echo "=== Phase 1 Data ==="
ls data/raw/phase1/

echo "=== Phase 2 Data ==="
ls data/raw/phase2/

echo "=== Phase 3 Data ==="
ls data/raw/phase3/

echo "=== Phase 4 Scripts ==="
ls scripts/phase4/
```

**✅ Expected Output:**
```
=== Phase 1 Data ===
account_10007_events.csv
account_10007_journey.json
account_10007_report.md

=== Phase 2 Data ===
account_10001_events.csv
account_10001_journey.json
account_10001_report.md
account_10003_events.csv
account_10003_journey.json
account_10003_report.md

=== Phase 3 Data ===
all_accounts_kpis.csv
kpi_metadata.json

=== Phase 4 Scripts ===
generate_milestones_phase4.py
load_journey_data_phase4.py
load_journey_to_qdrant_phase4.py
migration_journey_phase4.py
verify_production_safety.py
journey_schema_phase4.py
```

**✅ Checkpoint:** Files organized! Ready for deployment.

---

### **PART 2: INSTALL DEPENDENCIES (5 minutes)**

```bash
# Install required Python packages
pip install sqlalchemy psycopg2-binary pandas alembic --break-system-packages

# For Qdrant (optional, can skip for now)
# pip install qdrant-client openai --break-system-packages

# Verify installations
python -c "import sqlalchemy, psycopg2, pandas; print('✅ All packages installed')"
```

**✅ Expected:** "✅ All packages installed"

---

### **PART 3: GENERATE MILESTONES (5 minutes)**

```bash
cd $JOURNEY_DIR

# Generate 6 milestone training labels
python scripts/phase4/generate_milestones_phase4.py

# Expected output:
# ✅ Generating milestones for 3 accounts...
# ✅ Account 10007: 3 milestones generated
# ✅ Account {ACCOUNT_ID_START+2}: 2 milestones generated
# ✅ Account 12000: 1 milestone generated
# ✅ Total: 6 milestones

# Verify files created
ls -lh data/processed/
```

**✅ Expected:** 4 new CSV files in data/processed/:
- account_10001_milestones.csv
- account_10003_milestones.csv
- account_10007_milestones.csv
- all_accounts_milestones.csv

---

### **PART 4: CREATE DATABASE TABLES (5 minutes)**

**⚠️ IMPORTANT:** Update with your actual PostgreSQL connection details:
- Replace `YOUR_USER`
- Replace `YOUR_PASSWORD`
- Replace `YOUR_HOST` (usually `localhost`)
- Replace `YOUR_DATABASE` (e.g., `csm_dev`)

```bash
cd $JOURNEY_DIR

# Set your database URL
export DB_URL="postgresql://YOUR_USER:YOUR_PASSWORD@YOUR_HOST:5432/YOUR_DATABASE"

# Test connection first
psql "$DB_URL" -c "SELECT version();"
```

**✅ Expected:** PostgreSQL version info displayed

---

**Now create tables:**

```bash
# Run migration to create 8 journey_* tables
python scripts/phase4/migration_journey_phase4.py

# Verify tables created
psql "$DB_URL" -c "\dt journey_*"
```

**✅ Expected Output:**
```
           List of relations
 Schema |          Name              | Type  | Owner
--------+---------------------------+-------+-------
 public | journey_accounts          | table | user
 public | journey_events            | table | user
 public | journey_health            | table | user
 public | journey_kpis              | table | user
 public | journey_metadata          | table | user
 public | journey_milestones        | table | user
 public | prediction_explanations   | table | user
 public | signal_predictions        | table | user
(8 rows)
```

**✅ Checkpoint:** 8 tables created!

---

### **PART 5: LOAD JOURNEY DATA (15 minutes)**

```bash
cd $JOURNEY_DIR

# Load all data to PostgreSQL
python scripts/phase4/load_journey_data_phase4.py \
    --db-url "$DB_URL" \
    --data-dir data/raw \
    --processed-dir data/processed

# This will:
# 1. Read your Phase 2/3 CSV/JSON files
# 2. Transform data (wide→long, column mapping)
# 3. Calculate health snapshots
# 4. Generate sample predictions
# 5. Load everything to PostgreSQL
```

**Expected Output (will take a few minutes):**
```
🔄 Loading Journey Data to PostgreSQL
═══════════════════════════════════════

📊 Reading source files...
✅ Found 3 account events files
✅ Found 1 KPI file (3,220 data points)
✅ Found 3 journey JSON files
✅ Found 4 milestone files

📦 Loading journey_accounts...
✅ Loaded 3 accounts

📦 Loading journey_events...
✅ Loaded 187 events

📦 Loading journey_kpis...
✅ Transforming wide→long format (92 rows → 3,220 rows)
✅ Loaded 3,220 KPI data points

📦 Calculating journey_health snapshots...
✅ Calculated 92 weekly health snapshots

📦 Loading journey_milestones...
✅ Loaded 6 milestones

📦 Generating signal_predictions...
✅ Generated 3 sample predictions

📦 Generating prediction_explanations...
✅ Generated 3 explanations

📦 Loading journey_metadata...
✅ Loaded 1 metadata record

═══════════════════════════════════════
✅ Phase 4 Deployment Complete!
═══════════════════════════════════════

Summary:
- 3 accounts loaded
- 187 events loaded
- 3,220 KPI data points loaded
- 92 health snapshots calculated
- 6 milestones loaded
- 3 predictions generated
- Total: 3,512 database rows
```

**✅ Checkpoint:** Data loaded!

---

### **PART 6: VERIFY DATA (5 minutes)**

```bash
# Quick verification queries
psql "$DB_URL" << EOF

-- Check accounts
SELECT 'Accounts' as table_name, COUNT(*) as rows FROM journey_accounts
UNION ALL
SELECT 'Events', COUNT(*) FROM journey_events
UNION ALL
SELECT 'KPIs', COUNT(*) FROM journey_kpis
UNION ALL
SELECT 'Health', COUNT(*) FROM journey_health
UNION ALL
SELECT 'Milestones', COUNT(*) FROM journey_milestones
UNION ALL
SELECT 'Predictions', COUNT(*) FROM signal_predictions
UNION ALL
SELECT 'Explanations', COUNT(*) FROM prediction_explanations
UNION ALL
SELECT 'Metadata', COUNT(*) FROM journey_metadata;

EOF
```

**✅ Expected Output:**
```
  table_name   | rows
---------------+------
 Accounts      |    3
 Events        |  187
 KPIs          | 3220
 Health        |   92
 Milestones    |    6
 Predictions   |    3
 Explanations  |    3
 Metadata      |    1
(8 rows)
```

---

**More detailed verification:**

```bash
psql "$DB_URL" << EOF

-- Verify event counts per account
SELECT 
    journey_account_id,
    COUNT(*) as event_count
FROM journey_events
GROUP BY journey_account_id
ORDER BY journey_account_id;

-- Should show:
-- 1 (12000) | 34
-- 2 ({ACCOUNT_ID_START+2}) | 54
-- 3 (10007) | 99

EOF
```

---

### **PART 7: RUN SAFETY VERIFICATION (5 minutes)**

```bash
cd $JOURNEY_DIR

# Run safety verification
python scripts/phase4/verify_production_safety.py \
    --db-url "$DB_URL" \
    --output logs/step1_verification.json

# Check verification results
cat logs/step1_verification.json
```

**✅ Expected:** JSON file showing:
- All production tables UNTOUCHED
- 8 journey tables CREATED
- Safety status: PASS

---

### **PART 8: OPTIONAL - LOAD TO QDRANT (10 minutes)**

**Skip this if you don't have Qdrant set up yet. Can do later.**

```bash
# Only run if you have Qdrant instance + OpenAI API key
python scripts/phase4/load_journey_to_qdrant_phase4.py \
    --qdrant-url "https://your-cluster.qdrant.io:6333" \
    --qdrant-api-key "YOUR_QDRANT_KEY" \
    --openai-api-key "YOUR_OPENAI_KEY" \
    --data-dir data/raw
```

---

## ✅ STEP 1 COMPLETE CHECKLIST

After running all commands, verify:

- [x] **Files organized:** journey/ directory structure created
- [x] **Dependencies installed:** sqlalchemy, psycopg2, pandas
- [x] **Milestones generated:** 4 CSV files in data/processed/
- [x] **Tables created:** 8 journey_* tables in PostgreSQL
- [x] **Data loaded:** 3,512 total rows across 8 tables
- [x] **Verified:** All counts match expected (3 accounts, 187 events, etc.)
- [x] **Safety checked:** Production tables untouched
- [x] **Optional - Qdrant:** Training collection created (skip if not ready)

---

## 🎯 WHAT YOU NOW HAVE

```
✅ Clean organized directory structure
✅ 3 customer accounts in PostgreSQL:
   - Account 12000: Proactive growth (34 events)
   - Account {ACCOUNT_ID_START+2}: Ignored churn (54 events)
   - Account 10007: Crisis recovery (99 events)
✅ 3,220 KPI data points (35 KPIs × 92 weeks)
✅ 6 milestone training labels
✅ 3 sample predictions with explanations
✅ Production data: SAFE (untouched)
```

---

## ➡️ NEXT STEPS

**STEP 2: Bootstrap Weights**
- Load Supermicro simulation weights
- Document 32-KPI structure
- Prepare for mapping

**STEP 3: Mapping Layer**
- Map 32 bootstrap KPIs → 35 journey KPIs
- Test mapping accuracy

**STEP 4: Test Signal Analyst**
- Run predictions on journey data
- Measure baseline accuracy (target: 55-65%)

---

## 🆘 TROUBLESHOOTING

### Issue: "pip packages not installing"
```bash
pip install --upgrade pip
pip install sqlalchemy psycopg2-binary pandas alembic --break-system-packages --user
```

### Issue: "Cannot connect to PostgreSQL"
```bash
# Test connection
psql "postgresql://user:pass@host:5432/database" -c "\conninfo"

# Check if PostgreSQL is running
pg_isready -h localhost -p 5432
```

### Issue: "Files not found"
```bash
# Check where you are
pwd

# Check files exist
ls -la data/raw/phase1/
ls -la data/raw/phase2/
ls -la data/raw/phase3/
```

### Issue: "Permission denied on database"
```bash
# Grant permissions
psql "postgresql://..." -c "GRANT ALL ON SCHEMA public TO your_user;"
```

---

## 📞 READY FOR HELP?

If you encounter issues:
1. Check which step failed
2. Review error message
3. Check logs/step1_verification.json
4. Verify file paths are correct
5. Ask for help with specific error

---

**🎉 Congratulations on completing Step 1!** 🎉

You now have a fully deployed journey training dataset ready for bootstrap integration!
