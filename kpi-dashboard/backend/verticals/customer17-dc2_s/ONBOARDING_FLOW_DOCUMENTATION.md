# Customer 17 Onboarding Flow - Complete Documentation

**Last Updated:** January 19, 2026  
**Vertical:** DC2_S (Customer 17)

---

## 📋 Overview

This document traces the **complete onboarding flow** from CSV file uploads through all processing steps to final journey generation outputs.

---

## 🔄 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 0: CUSTOMER PROVISIONING                │
│                    provision_dc_customer.py                    │
│                    (Creates customer directory from _template) │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 1: CSV FILE UPLOADS                    │
│                    (6 Distinct Files from User)                │
└─────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────────────────┼─────────────────────────┐
    │                         │                         │
    ▼                         ▼                         ▼
┌──────────┐           ┌──────────────┐          ┌──────────┐
│customers │           │accounts      │          │account_  │
│.csv      │           │.csv          │          │profiles  │
│          │           │              │          │.csv      │
└──────────┘           └──────────────┘          └──────────┘
    │                         │                         │
    │                         ▼                         │
    │                 ┌──────────────┐                 │
    │                 │kpi_          │                 │
    │                 │measurements  │                 │
    │                 │.csv          │                 │
    │                 └──────────────┘                 │
    │                         │                         │
    │                         ▼                         │
    │                 ┌──────────────┐                 │
    │                 │qualitative_  │                 │
    │                 │signals.csv   │                 │
    │                 └──────────────┘                 │
    │                         │                         │
    │                         ▼                         │
    │                 ┌──────────────┐                 │
    │                 │products.csv  │                 │
    │                 └──────────────┘                 │
    │                         │                         │
    └─────────────────────────┼─────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 2: DATA LOADING SCRIPT                       │
│              02_load_customer17_data_SMART.py                  │
│                                                                 │
│  Actions:                                                       │
│  1. Check database connection                                  │
│  2. Delete existing Customer 17 data (if exists)              │
│  3. Load CSV files into PostgreSQL tables:                    │
│     - customers.csv → customers table                          │
│     - accounts.csv → accounts table                            │
│     - account_profiles.csv → account_profiles table            │
│     - kpi_measurements.csv → kpi_measurements table           │
│     - qualitative_signals.csv → qualitative_signals table      │
│     - products.csv → products table                            │
│  4. Validate data integrity                                    │
│  5. Report load summary                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 3: EMBEDDING GENERATION                 │
│                    03_embed_customer17_OPENAI.py               │
│                                                                 │
│  Actions:                                                       │
│  1. Connect to PostgreSQL (read data)                          │
│  2. Connect to Qdrant Cloud (write embeddings)                │
│  3. Create/recreate collection:                                │
│     - Collection: kpi_dashboard_vectors_customer_17           │
│     - Model: text-embedding-3-large (3072 dimensions)          │
│  4. Generate embeddings for:                                   │
│     - KPI measurements (from kpi_measurements table)           │
│     - Qualitative signals (from qualitative_signals table)     │
│  5. Batch upload to Qdrant (batch size: 50)                    │
│  6. Create metadata payloads with:                             │
│     - account_id, customer_id, kpi_code, date, etc.            │
│  7. Report embedding summary                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 4: DATA STORAGE                         │
│              PostgreSQL + Qdrant (Ready for Analysis)         │
│                                                                 │
│  PostgreSQL Tables:                                            │
│  ├── customers (customer metadata)                             │
│  ├── accounts (account master data)                             │
│  ├── account_profiles (detailed profiles, 100+ attributes)     │
│  ├── kpi_measurements (time-series KPI data)                  │
│  ├── qualitative_signals (signals/events)                     │
│  └── products (product catalog)                                │
│                                                                 │
│  Qdrant Collections:                                           │
│  └── kpi_dashboard_vectors_customer_17                         │
│      ├── KPI embeddings (3072-dim vectors)                    │
│      └── Signal embeddings (3072-dim vectors)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 5: WIZARD A - JOURNEY GENERATOR               │
│              wizard_a/wizard_journey_generator.py              │
│                                                                 │
│  Actions:                                                       │
│  1. Read account data from PostgreSQL                           │
│  2. Generate journey patterns for each account:                │
│     - crisis_recovery (crisis → recovery)                      │
│     - ignored_churn (decline → churn)                          │
│     - proactive_growth (stable → expansion)                    │
│     - strategic_expansion (growth → expansion)                 │
│  3. Create weekly journey data (52 weeks)                      │
│  4. Generate events based on patterns                          │
│  5. Calculate health scores over time                         │
│  6. Export outputs to test_run_*/data/ directory               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 6: GENERATED OUTPUTS                    │
│                                                                 │
│  Location: wizard_a/test_run_YYYYMMDD_HHMMSS/data/              │
│                                                                 │
│  Per-Account Files:                                             │
│  ├── account_90001_journey.json                                │
│  │   └── Full journey data (52 weeks, events, health scores)    │
│  ├── account_90001_events.csv                                  │
│  │   └── Event timeline (week_number, event_type, dates)       │
│  ├── account_90001_kpis.csv                                    │
│  │   └── KPI snapshots by week                                 │
│  └── account_90001_report.md                                   │
│      └── Human-readable journey summary                        │
│                                                                 │
│  Aggregated Files:                                              │
│  ├── all_accounts_kpis.csv                                     │
│  ├── kpi_metadata.json                                         │
│  └── processed/                                                │
│      ├── account_90001_milestones.csv                         │
│      └── all_accounts_milestones.csv                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Step 0: Customer Provisioning (Create Directory Structure)

### Script: `provision_dc_customer.py`

**Location:** `backend/verticals/provision_dc_customer.py`

**Purpose:** Creates a new customer directory structure by copying from `_template` and replacing placeholders.

**Execution:**
```bash
cd backend/verticals
python3 provision_dc_customer.py --customer-id 18 --vertical-slug dc2_s
```

**Process:**
1. **Copy Template Structure**
   - Copies entire `_template/` directory structure
   - Creates `customer{CUSTOMER_ID}-{VERTICAL_SLUG}/` directory
   - Example: `customer18-dc2_s/`

2. **Replace Placeholders**
   - `{CUSTOMER_ID}` → Customer ID (e.g., 18)
   - `{VERTICAL_SLUG}` → Vertical slug (e.g., dc2_s)
   - `{ACCOUNT_ID_START}` → Calculated as `10000 + customer_id * 1000`
   - `customer9` → `customer{CUSTOMER_ID}` (in file names and content)
   - `Customer 9` → `Customer {CUSTOMER_ID}` (in text)

3. **File Processing**
   - Processes text files (.py, .md, .txt, .sh, .sql, .json, .yaml, .csv)
   - Replaces placeholders in content
   - Copies binary files as-is
   - Skips cache directories (__pycache__, .git, etc.)

4. **Output**
   - Creates complete directory structure:
     ```
     customer18-dc2_s/
     ├── agents/
     ├── api/
     ├── data/          # Empty - ready for CSV uploads
     ├── journey/
     ├── scripts/       # With customer-specific IDs
     ├── services/
     └── tests/
     ```

**Prerequisites:**
- `_template/` directory must exist
- Customer ID must be unique (directory shouldn't exist)

**Next Steps After Provisioning:**
1. Upload CSV files to `data/` directory
2. Update scripts if needed (customer ID already replaced)
3. Proceed to Step 1 (CSV uploads)

---

## 📁 Step 1: CSV File Uploads (6 Distinct Files)

### Required CSV Files:

| # | File Name | Description | Table Destination | Required? |
|---|-----------|-------------|-------------------|-----------|
| 1 | `customers.csv` | Customer profile/metadata | `customers` | ✅ Yes |
| 2 | `accounts.csv` | Account master data | `accounts` | ✅ Yes |
| 3 | `account_profiles.csv` | Detailed account profiles (100+ attributes) | `account_profiles` | ✅ Yes |
| 4 | `kpi_measurements.csv` | Time-series KPI measurements | `kpi_measurements` | ✅ Yes |
| 5 | `qualitative_signals.csv` | Qualitative signals/events | `qualitative_signals` | ✅ Yes |
| 6 | `products.csv` | Product catalog | `products` | ✅ Yes |

### File Locations:
- **Input:** User uploads via onboarding wizard or direct file placement
- **Processing Location:** `backend/verticals/customer17-dc2_s/data/`

### Key Differences from Current Onboarding Wizard:
- **Current Wizard expects:** `accounts`, `kpis`, `signals`, `products`, `profiles` (5 files)
- **Actual Flow requires:** `customers.csv`, `accounts.csv`, `account_profiles.csv`, `kpi_measurements.csv`, `qualitative_signals.csv`, `products.csv` (6 files)
- **Missing:** `customers.csv` is not in current onboarding wizard
- **Name mismatch:** Wizard uses `kpis` but flow expects `kpi_measurements.csv`
- **Name mismatch:** Wizard uses `signals` but flow expects `qualitative_signals.csv`
- **Name mismatch:** Wizard uses `profiles` but flow expects `account_profiles.csv`

---

## 🔧 Step 2: Data Loading Script

### Script: `02_load_customer17_data_SMART.py`

**Location:** `backend/verticals/customer17-dc2_s/scripts/`

**Execution:**
```bash
cd backend/verticals/customer17-dc2_s/scripts
python3 02_load_customer17_data_SMART.py
```

**Process:**
1. **Check Database Connection**
   - Validates `DATABASE_URL` environment variable
   - Tests PostgreSQL connection

2. **Check for Existing Data**
   - Queries for existing Customer 17 data
   - Prompts user if data exists

3. **Delete Existing Data (if found)**
   - Deletes in dependency order:
     - `playbook_executions`
     - `expansion_readiness_scores`
     - `account_health_history`
     - `qualitative_signals`
     - `kpi_measurements`
     - `account_products`
     - `account_profiles`
     - `accounts`
     - `products`
     - `kpi_definitions`
     - `partner_definitions`
     - `customers`

4. **Load CSV Files**
   - Reads each CSV from `../data/` directory
   - Validates file existence
   - Loads into PostgreSQL using `pandas.to_sql()`
   - Handles data type conversions
   - Sets `customer_id = 17` for all records

5. **Report Summary**
   - Shows success/failure count
   - Displays rows loaded per table

**Output:** Data loaded into PostgreSQL tables

---

## 🧠 Step 3: Embedding Generation

### Script: `03_embed_customer17_OPENAI.py`

**Location:** `backend/verticals/customer17-dc2_s/scripts/`

**Prerequisites:**
```bash
export OPENAI_API_KEY="your-key-here"
export QDRANT_URL="https://your-qdrant-url"
export QDRANT_API_KEY="your-qdrant-key"
```

**Execution:**
```bash
cd backend/verticals/customer17-dc2_s/scripts
python3 03_embed_customer17_OPENAI.py
```

**Process:**
1. **Initialize Connections**
   - PostgreSQL connection (read data)
   - Qdrant Cloud connection (write embeddings)
   - OpenAI client (generate embeddings)

2. **Create/Recreate Collection**
   - Collection name: `kpi_dashboard_vectors_customer_17`
   - Model: `text-embedding-3-large`
   - Dimensions: 3072
   - Distance: Cosine

3. **Generate Embeddings**
   - **KPI Measurements:**
     - Reads from `kpi_measurements` table
     - Creates text representation: `"{kpi_code}: {value} {unit} on {date}"`
     - Generates embedding using OpenAI API
     - Creates payload with metadata (account_id, customer_id, kpi_code, date, etc.)
   
   - **Qualitative Signals:**
     - Reads from `qualitative_signals` table
     - Creates text representation: `"{signal_type}: {summary} on {date}"`
     - Generates embedding using OpenAI API
     - Creates payload with metadata (account_id, customer_id, signal_type, date, etc.)

4. **Batch Upload to Qdrant**
   - Batch size: 50 vectors
   - Uploads with retry logic
   - Reports progress

5. **Report Summary**
   - Total embeddings created
   - Success/failure counts

**Output:** Embeddings stored in Qdrant Cloud collection

---

## 💾 Step 4: Data Storage (PostgreSQL + Qdrant)

### PostgreSQL Tables (Structured Data):

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `customers` | Customer metadata | customer_id, company_name, industry |
| `accounts` | Account master data | account_id, customer_id, account_name, account_tier |
| `account_profiles` | Detailed profiles (100+ attributes) | account_id, overall_health_score, nps_score, etc. |
| `kpi_measurements` | Time-series KPI data | account_id, kpi_code, value, date, unit |
| `qualitative_signals` | Signals/events | account_id, signal_type, summary, date, sentiment |
| `products` | Product catalog | product_id, product_name, product_category |

### Qdrant Collection (Vector Embeddings):

- **Collection:** `kpi_dashboard_vectors_customer_17`
- **Model:** `text-embedding-3-large`
- **Dimensions:** 3072
- **Content:** KPI and signal embeddings with metadata

---

## 🧙 Step 5: Wizard A - Journey Generator

### Script: `wizard_a/wizard_journey_generator.py`

**Location:** `backend/verticals/customer17-dc2_s/journey/wizard_a/`

**Execution:**
```bash
cd backend/verticals/customer17-dc2_s/journey/wizard_a
python3 wizard_journey_generator.py \
    --accounts 10 \
    --start-id 90001 \
    --pattern-mix '{"crisis":0.2,"churn":0.15,"stable":0.4,"expansion":0.25}' \
    --output-dir test_run_20260108_191444
```

**Process:**
1. **Read Account Data**
   - Queries PostgreSQL for Customer 17 accounts
   - Loads account profiles and KPI data

2. **Generate Journey Patterns**
   - **crisis_recovery:** Crisis → Recovery journey
   - **ignored_churn:** Decline → Churn journey
   - **proactive_growth:** Stable → Expansion journey
   - **strategic_expansion:** Growth → Expansion journey

3. **Create Weekly Journey Data**
   - Generates 52 weeks of journey data
   - Calculates health scores over time
   - Creates events based on pattern
   - Assigns phases (onboarding, growth, crisis, recovery, etc.)

4. **Export Outputs**
   - Creates `test_run_YYYYMMDD_HHMMSS/data/` directory
   - Exports per-account JSON files
   - Exports CSV files (events, KPIs)
   - Generates markdown reports

**Output:** Journey JSON files in `test_run_*/data/` directory

---

## 📊 Step 6: Generated Outputs

### Output Location:
`backend/verticals/customer17-dc2_s/journey/wizard_a/test_run_YYYYMMDD_HHMMSS/data/`

### Per-Account Files:

1. **`account_90001_journey.json`**
   - Full journey data structure
   - 52 weeks of data
   - Events, health scores, phases
   - Pattern type, milestones

2. **`account_90001_events.csv`**
   - Event timeline
   - Columns: week_number, date, event_type, description, sentiment, health_impact

3. **`account_90001_kpis.csv`**
   - KPI snapshots by week
   - Columns: week_number, kpi_code, value, unit

4. **`account_90001_report.md`**
   - Human-readable summary
   - Journey overview, key events, health trends

### Aggregated Files:

- **`all_accounts_kpis.csv`** - All accounts' KPI data
- **`kpi_metadata.json`** - KPI definitions and metadata
- **`processed/account_90001_milestones.csv`** - Key milestones
- **`processed/all_accounts_milestones.csv`** - All milestones

---

## 🔄 Current State vs. Expected Flow

### ❌ Current Onboarding Wizard Flow:
```
Onboarding Wizard → Upload CSV → Direct PostgreSQL Insert → STOP
```

### ✅ Expected Complete Flow:
```
CSV Uploads → 02_load Script → PostgreSQL → 03_embed Script → Qdrant → 
Wizard A → Journey JSON Files
```

### 🔧 Gap Analysis:

| Step | Current State | Expected State | Status |
|------|--------------|----------------|--------|
| CSV Upload | ✅ Onboarding wizard uploads directly | ✅ CSV files in `data/` directory | ⚠️ Name mismatch |
| Data Loading | ❌ Not triggered automatically | ✅ `02_load_customer17_data_SMART.py` | ❌ Missing |
| Embedding Generation | ❌ Not triggered automatically | ✅ `03_embed_customer17_OPENAI.py` | ❌ Missing |
| Journey Generation | ❌ Not triggered automatically | ✅ `wizard_journey_generator.py` | ❌ Missing |

---

## 🚀 Complete Onboarding Flow Summary

### Step-by-Step Process:

**Step 0: Provision Customer** (One-time setup)
```bash
cd backend/verticals
python3 provision_dc_customer.py --customer-id 18 --vertical-slug dc2_s
```

**Step 1: Upload CSV Files** (6 files)
- Place CSV files in `customer18-dc2_s/data/`
- Files: customers.csv, accounts.csv, account_profiles.csv, kpi_measurements.csv, qualitative_signals.csv, products.csv

**Step 2: Load Data**
```bash
cd customer18-dc2_s/scripts
python3 02_load_customer18_data_SMART.py
```

**Step 3: Generate Embeddings**
```bash
python3 03_embed_customer18_OPENAI.py
```

**Step 4: Generate Journeys**
```bash
cd ../journey/wizard_a
python3 wizard_journey_generator.py --accounts 10 --start-id 18001 --pattern-mix '{"crisis":0.2,"churn":0.15,"stable":0.4,"expansion":0.25}' --output-dir test_run_YYYYMMDD_HHMMSS
```

---

## 🚀 Recommended Implementation

To align onboarding with the expected flow:

1. **Add Step 0 to Onboarding Wizard** - Provision customer directory first

2. **Update Onboarding Wizard** to accept 6 files with correct names:
   - `customers.csv`
   - `accounts.csv`
   - `account_profiles.csv`
   - `kpi_measurements.csv`
   - `qualitative_signals.csv`
   - `products.csv`

2. **Add Post-Upload Pipeline** that automatically triggers:
   - `02_load_customer17_data_SMART.py`
   - `03_embed_customer17_OPENAI.py`
   - `wizard_journey_generator.py`

3. **Add Progress Tracking** for each step

4. **Add Error Handling** and rollback capabilities

---

*Document generated for Customer 17 onboarding flow documentation.*
