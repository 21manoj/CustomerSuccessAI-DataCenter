# 📁 JOURNEY DATA ORGANIZATION GUIDE
## Clean Directory Structure for Phase 1-4

**Base Path:** `~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer9-dc2_s/`

---

## 🎯 RECOMMENDED STRUCTURE

```
customer9-dc2_s/
├── journey/
│   ├── scripts/                    # All executable scripts
│   │   ├── phase1/
│   │   │   └── journey_pattern_generator.py
│   │   ├── phase3/
│   │   │   └── kpi_generator_phase3.py
│   │   ├── phase4/
│   │   │   ├── migration_journey_phase4.py
│   │   │   ├── load_journey_data_phase4.py
│   │   │   ├── generate_milestones_phase4.py
│   │   │   ├── load_journey_to_qdrant_phase4.py
│   │   │   ├── journey_schema_phase4.py
│   │   │   └── verify_production_safety.py
│   │   └── phase5/                 # Future: Bootstrap integration
│   │
│   ├── data/                       # All data files
│   │   ├── raw/                    # Original generated data (Phase 1-3)
│   │   │   ├── phase1/
│   │   │   │   ├── account_10007_events.csv
│   │   │   │   ├── account_10007_journey.json
│   │   │   │   └── account_10007_report.md
│   │   │   ├── phase2/
│   │   │   │   ├── account_10001_events.csv
│   │   │   │   ├── account_10001_journey.json
│   │   │   │   ├── account_10001_report.md
│   │   │   │   ├── account_10003_events.csv
│   │   │   │   ├── account_10003_journey.json
│   │   │   │   └── account_10003_report.md
│   │   │   └── phase3/
│   │   │       ├── all_accounts_kpis.csv
│   │   │       ├── kpi_metadata.json
│   │   │       └── account_*_kpis.csv (individual files)
│   │   │
│   │   ├── processed/              # Phase 4 generated files
│   │   │   ├── account_10001_milestones.csv
│   │   │   ├── account_10003_milestones.csv
│   │   │   ├── account_10007_milestones.csv
│   │   │   └── all_accounts_milestones.csv
│   │   │
│   │   └── bootstrap/              # Phase 5: Bootstrap weights
│   │       └── bootstrap_weights_supermicro.json
│   │
│   ├── docs/                       # All documentation
│   │   ├── PHASE_1_COMPLETE_SUMMARY.md
│   │   ├── PHASE_2_COMPLETE_SUMMARY.md
│   │   ├── PHASE_3_COMPLETE_SUMMARY.md
│   │   ├── PHASE_4_FINAL_SUMMARY.md
│   │   ├── THREE_ACCOUNT_COMPARISON.md
│   │   └── deployment/
│   │       ├── STEP_1_DEPLOY_JOURNEY_DATA.md
│   │       ├── STEP_1_QUICK_START.txt
│   │       └── PHASE_2_3_4_ALIGNMENT_VERIFICATION.md
│   │
│   ├── logs/                       # Deployment logs and verification
│   │   ├── step1_verification.json
│   │   └── deployment_YYYYMMDD.log
│   │
│   └── config/                     # Configuration files
│       ├── database.yaml           # DB connection configs
│       └── qdrant.yaml             # Qdrant configs
│
└── [existing project structure...]
```

---

## 🔧 SETUP COMMANDS

### **Step 1: Create Directory Structure**

```bash
# Navigate to base directory
cd ~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer9-dc2_s/

# Create directory structure
mkdir -p journey/{scripts/{phase1,phase3,phase4,phase5},data/{raw/{phase1,phase2,phase3},processed,bootstrap},docs/deployment,logs,config}

# Verify structure created
tree journey -L 3
```

---

### **Step 2: Organize Phase 1-3 Files**

**From your current location (wherever files are now):**

```bash
# Set variables for clarity
BASE_DIR=~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer9-dc2_s
JOURNEY_DIR=$BASE_DIR/journey

# Move Phase 1 data files
mv 1767800625205_account_10007_events.csv $JOURNEY_DIR/data/raw/phase1/account_10007_events.csv
mv 1767800625205_account_10007_journey.json $JOURNEY_DIR/data/raw/phase1/account_10007_journey.json
mv 1767800625205_account_10007_report.md $JOURNEY_DIR/data/raw/phase1/account_10007_report.md

# Move Phase 1 script
mv journey_pattern_generator.py $JOURNEY_DIR/scripts/phase1/

# Move Phase 2 data files (account 10001)
mv 1767800625203_account_10001_events.csv $JOURNEY_DIR/data/raw/phase2/account_10001_events.csv
mv 1767800625204_account_10001_journey.json $JOURNEY_DIR/data/raw/phase2/account_10001_journey.json
mv 1767800625204_account_10001_report.md $JOURNEY_DIR/data/raw/phase2/account_10001_report.md

# Move Phase 2 data files (account 10003)
mv 1767800625205_account_10003_events.csv $JOURNEY_DIR/data/raw/phase2/account_10003_events.csv
mv 1767800625205_account_10003_journey.json $JOURNEY_DIR/data/raw/phase2/account_10003_journey.json
mv 1767800625205_account_10003_report.md $JOURNEY_DIR/data/raw/phase2/account_10003_report.md

# Move Phase 3 data files
mv all_accounts_kpis.csv $JOURNEY_DIR/data/raw/phase3/
mv kpi_metadata.json $JOURNEY_DIR/data/raw/phase3/
mv account_*_kpis.csv $JOURNEY_DIR/data/raw/phase3/ 2>/dev/null || true

# Move Phase 3 script
mv kpi_generator_phase3.py $JOURNEY_DIR/scripts/phase3/

# Move documentation
mv PHASE_1_COMPLETE_SUMMARY.md $JOURNEY_DIR/docs/
mv PHASE_2_COMPLETE_SUMMARY.md $JOURNEY_DIR/docs/ 2>/dev/null || true
mv PHASE_3_COMPLETE_SUMMARY.md $JOURNEY_DIR/docs/
mv THREE_ACCOUNT_COMPARISON.md $JOURNEY_DIR/docs/ 2>/dev/null || true
```

---

### **Step 3: Add Phase 4 Scripts**

**Download Phase 4 scripts from Claude outputs and place them:**

```bash
# Copy Phase 4 scripts you downloaded
cp /path/to/downloads/migration_journey_phase4.py $JOURNEY_DIR/scripts/phase4/
cp /path/to/downloads/load_journey_data_phase4.py $JOURNEY_DIR/scripts/phase4/
cp /path/to/downloads/generate_milestones_phase4.py $JOURNEY_DIR/scripts/phase4/
cp /path/to/downloads/load_journey_to_qdrant_phase4.py $JOURNEY_DIR/scripts/phase4/
cp /path/to/downloads/journey_schema_phase4.py $JOURNEY_DIR/scripts/phase4/
cp /path/to/downloads/verify_production_safety.py $JOURNEY_DIR/scripts/phase4/

# Copy deployment docs
cp /path/to/downloads/STEP_1_DEPLOY_JOURNEY_DATA.md $JOURNEY_DIR/docs/deployment/
cp /path/to/downloads/STEP_1_QUICK_START.txt $JOURNEY_DIR/docs/deployment/
cp /path/to/downloads/PHASE_4_FINAL_SUMMARY.md $JOURNEY_DIR/docs/
cp /path/to/downloads/PHASE_2_3_4_ALIGNMENT_VERIFICATION.md $JOURNEY_DIR/docs/deployment/
```

---

### **Step 4: Verify Organization**

```bash
cd $JOURNEY_DIR

# Check structure
ls -R

# Expected output:
# scripts/phase1:    journey_pattern_generator.py
# scripts/phase3:    kpi_generator_phase3.py
# scripts/phase4:    migration_journey_phase4.py, load_journey_data_phase4.py, ...
# data/raw/phase1:   account_10007_*.csv/json/md
# data/raw/phase2:   account_10001_*, account_10003_*
# data/raw/phase3:   all_accounts_kpis.csv, kpi_metadata.json
# docs:              PHASE_*_COMPLETE_SUMMARY.md
```

---

## 🚀 STEP 1 DEPLOYMENT (Updated Paths)

**Now that files are organized, run Step 1:**

### **A. Generate Milestones**

```bash
cd ~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer9-dc2_s/journey

# Run from journey directory
python scripts/phase4/generate_milestones_phase4.py \
    --data-dir data/raw \
    --output-dir data/processed

# Expected output in data/processed/:
# - account_10001_milestones.csv
# - account_10003_milestones.csv
# - account_10007_milestones.csv
# - all_accounts_milestones.csv
```

---

### **B. Create PostgreSQL Tables**

```bash
# Option 1: Using Alembic (if you have migrations)
cd ~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend
alembic upgrade head

# Option 2: Direct execution
cd ~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer9-dc2_s/journey
python scripts/phase4/migration_journey_phase4.py

# Verify tables created
psql "postgresql://user:pass@localhost/csm_dev" -c "\dt journey_*"
```

---

### **C. Load Journey Data**

```bash
cd ~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer9-dc2_s/journey

python scripts/phase4/load_journey_data_phase4.py \
    --db-url "postgresql://user:pass@localhost:5432/csm_dev" \
    --data-dir data/raw \
    --processed-dir data/processed

# Expected output:
# ✅ Loading journey accounts... (3 accounts)
# ✅ Loading journey events... (187 events)
# ✅ Loading journey KPIs... (3,220 data points)
# ✅ Loading milestones... (6 milestones)
# ✅ Complete!
```

---

### **D. Verify Safety**

```bash
python scripts/phase4/verify_production_safety.py \
    --db-url "postgresql://user:pass@localhost:5432/csm_dev" \
    --output logs/step1_verification.json

# Check verification
cat logs/step1_verification.json
```

---

### **E. Load to Qdrant (Optional)**

```bash
python scripts/phase4/load_journey_to_qdrant_phase4.py \
    --qdrant-url https://your-cluster.qdrant.io:6333 \
    --qdrant-api-key YOUR_QDRANT_KEY \
    --openai-api-key YOUR_OPENAI_KEY \
    --data-dir data/raw
```

---

## 📝 CONFIGURATION FILES (Optional but Recommended)

### **config/database.yaml**

```yaml
# Database configuration
development:
  postgresql:
    host: localhost
    port: 5432
    database: csm_dev
    user: csm_user
    password: ${DB_PASSWORD}  # Use env var
    
production:
  postgresql:
    host: prod-db.example.com
    port: 5432
    database: csm_prod
    user: csm_prod_user
    password: ${DB_PASSWORD}
```

### **config/qdrant.yaml**

```yaml
# Qdrant configuration
development:
  url: http://localhost:6333
  api_key: ${QDRANT_API_KEY}
  collection_prefix: dev_

production:
  url: https://prod-cluster.qdrant.io:6333
  api_key: ${QDRANT_API_KEY}
  collection_prefix: prod_
```

### **.env file (in journey/ directory)**

```bash
# Database
DB_PASSWORD=your_secure_password

# Qdrant
QDRANT_API_KEY=your_qdrant_key

# OpenAI (for embeddings)
OPENAI_API_KEY=your_openai_key
```

---

## ✅ BENEFITS OF THIS STRUCTURE

### **1. Clean Separation**
- Scripts separate from data
- Raw data vs processed data
- Documentation in one place

### **2. Easy Navigation**
```bash
# Find Phase 4 scripts
cd journey/scripts/phase4

# Check raw data
cd journey/data/raw/phase3

# Read documentation
cd journey/docs
```

### **3. Git-Friendly**
```gitignore
# Add to .gitignore
journey/data/raw/
journey/data/processed/
journey/logs/
journey/config/.env
```

### **4. Scalable**
- Easy to add Phase 5, 6, etc.
- Clear where new files go
- Simple to find things

### **5. Deployment-Ready**
- All paths relative to journey/
- Scripts know where to find data
- Configuration centralized

---

## 🎯 QUICK REFERENCE

**After organization, your commands will be:**

```bash
# Always start from journey directory
cd ~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer9-dc2_s/journey

# Run any Phase 4 script
python scripts/phase4/SCRIPT_NAME.py --data-dir data/raw

# Check logs
cat logs/step1_verification.json

# Read docs
less docs/PHASE_4_FINAL_SUMMARY.md
```

---

## 📊 FILE COUNT VERIFICATION

After organization, verify counts:

```bash
cd ~/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals/customer9-dc2_s/journey

echo "Phase 1 files:"
ls -1 data/raw/phase1/ | wc -l
# Should show: 3 files (events, journey, report for account 10007)

echo "Phase 2 files:"
ls -1 data/raw/phase2/ | wc -l
# Should show: 6 files (3 files × 2 accounts: 10001, 10003)

echo "Phase 3 files:"
ls -1 data/raw/phase3/ | wc -l
# Should show: 2+ files (all_accounts_kpis.csv, kpi_metadata.json, plus individual KPI files)

echo "Phase 4 scripts:"
ls -1 scripts/phase4/ | wc -l
# Should show: 6 scripts

echo "Documentation:"
ls -1 docs/*.md | wc -l
# Should show: 4+ documentation files
```

---

## 🚀 READY TO PROCEED!

**Once organized, proceed with Step 1 deployment using the commands above.**

---

**Next:** After Step 1 complete, we'll add Phase 5 (Bootstrap Integration) to `scripts/phase5/`
