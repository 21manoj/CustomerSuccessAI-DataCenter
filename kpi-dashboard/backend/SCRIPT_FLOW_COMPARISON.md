# Script Flow Comparison: provision_dc_customer.py vs generate_customer17_seed_data.py

## Overview

This document shows the execution flow and dependencies for both scripts.

---

## 1. provision_dc_customer.py Flow

### Purpose
Creates a new customer directory structure by copying from `_template` and replacing placeholders.

### Execution Flow

```
provision_dc_customer.py
│
├─ main()
│   ├─ Parse arguments (--customer-id, --customer-name, --dry-run, --force)
│   └─ provision_customer()
│
├─ provision_customer()
│   ├─ validate_template()
│   │   ├─ Check TEMPLATE_DIR exists
│   │   ├─ Check expected directories: ['data', 'scripts', 'services']
│   │   └─ Return (is_valid, issues)
│   │
│   ├─ calculate_account_id_start(customer_id)
│   │   └─ Return: 10000 + customer_id * 1000
│   │
│   ├─ Check if customer_dir exists → Delete if force=True
│   │
│   └─ Copy directory structure (os.walk TEMPLATE_DIR)
│       ├─ For each file:
│       │   ├─ should_process_file() → Skip binary/cache files
│       │   ├─ copy_and_replace_file()
│       │   │   ├─ is_text_file() → Check if .py, .md, .csv, etc.
│       │   │   ├─ If text: replace_placeholders()
│       │   │   │   ├─ Replace {CUSTOMER_ID}, {CUSTOMER_NAME}, etc.
│       │   │   │   ├─ Replace customer9 → customerN
│       │   │   │   └─ Replace account IDs (90001 → 18001, etc.)
│       │   │   └─ Write to destination
│       │   └─ If binary: shutil.copy2()
│       └─ Collect stats (files_copied, replacements, etc.)
│
└─ Print "Next Steps" (manual instructions):
    ├─ 1. Upload 5 CSV files to customer_dir/data/
    ├─ 2. Run: 02_load_customer{customer_id}_data_SMART.py
    ├─ 3. Run: 03_embed_customer{customer_id}_OPENAI.py
    ├─ 4. Run: journey/wizard_a/wizard_a_journey_generator.py
    └─ 5. Run: create_customer{customer_id}_user.py
```

### Key Functions Called

| Function | Purpose |
|---------|---------|
| `calculate_account_id_start()` | Formula: `10000 + customer_id * 1000` |
| `map_account_id()` | Maps old account ID to new (90001 → 18001) |
| `replace_placeholders()` | Replaces {CUSTOMER_ID}, customer9, account IDs in files |
| `should_process_file()` | Filters out binary/cache files |
| `copy_and_replace_file()` | Copies file and replaces placeholders |

### What It Creates

- **Directory Structure**: `backend/verticals/customer{N}-dc2_s/`
  - `data/` (empty, expects CSV files)
  - `scripts/` (with placeholder replacements)
  - `services/` (with placeholder replacements)
  - `journey/` (with placeholder replacements)
  - `agents/`, `api/`, `tests/`, etc.

- **File Transformations**:
  - `02_load_customer9_data_SMART.py` → `02_load_customer18_data_SMART.py`
  - `customer9` → `customer18` (in all files)
  - `90001` → `18001` (account ID mapping)
  - `{CUSTOMER_ID}` → `18` (placeholder replacement)

### Dependencies

- **Input**: `_template/` directory must exist
- **Output**: Customer directory structure (no CSV files generated)
- **Manual Step Required**: User must upload 5 CSV files to `data/` directory

---

## 2. generate_customer17_seed_data.py Flow

### Purpose
Generates 5 CSV files with synthetic seed data for a data center customer.

### Execution Flow

```
generate_customer17_seed_data.py
│
├─ main()
│   ├─ Parse arguments (--output-dir, --create-customer)
│   ├─ Create output directory
│   │
│   ├─ [Optional] create_customer_17()
│   │   ├─ app.app_context()
│   │   ├─ Check if Customer.query.filter_by(customer_id=17).first()
│   │   ├─ If not exists: Create Customer record
│   │   ├─ Check if User.query.filter_by(email=...).first()
│   │   └─ If not exists: Create User record
│   │
│   └─ Generate CSV files (sequential):
│       ├─ generate_accounts_csv(output_dir)
│       │   ├─ Loop NUM_ACCOUNTS (default: 10)
│       │   ├─ Generate account data:
│       │   │   ├─ account_id = BASE_ACCOUNT_ID + i (17001, 17002, ...)
│       │   │   ├─ account_name, account_type, industry, tier
│       │   │   ├─ initial_arr, final_arr (with growth logic)
│       │   │   ├─ contract dates, partner info
│       │   │   ├─ gpu_count, datacenter_location, csm_assigned
│       │   │   └─ journey_type, outcome
│       │   └─ Write accounts.csv
│       │
│       ├─ generate_kpis_csv(accounts, output_dir)
│       │   ├─ For each account:
│       │   │   ├─ For each month (NUM_MONTHS_HISTORICAL = 12):
│       │   │   │   ├─ For each KPI_CODE (33 KPIs):
│       │   │   │   │   ├─ Generate value based on KPI category:
│       │   │   │   │   │   ├─ DV-* (Data Velocity): 5.0-20.0
│       │   │   │   │   │   ├─ OS-* (Operational Stability): 99.0-100.0
│       │   │   │   │   │   ├─ AI-* (AI Performance): 50.0-85.0
│       │   │   │   │   │   ├─ CH-* (Customer Health): 70.0-95.0
│       │   │   │   │   │   └─ EX-* (Expansion): 50.0-120.0
│       │   │   │   │   ├─ Apply recovery_modifier (if recovery account)
│       │   │   │   │   ├─ Determine health_state (optimal/healthy/at_risk/critical)
│       │   │   │   │   └─ Create measurement record
│       │   │   └─ Write kpis.csv
│       │
│       ├─ generate_signals_csv(accounts, output_dir)
│       │   ├─ For each account:
│       │   │   ├─ Determine num_signals (15-30 per account)
│       │   │   ├─ For each signal:
│       │   │   │   ├─ Random date within year
│       │   │   │   ├─ signal_type (email/call/meeting/slack)
│       │   │   │   ├─ stakeholder_level, stakeholder_title
│       │   │   │   ├─ sentiment (positive/neutral/negative)
│       │   │   │   │   └─ Recovery accounts: sentiment varies by crisis period
│       │   │   │   ├─ content (templates based on sentiment)
│       │   │   │   └─ keywords, sentiment_score
│       │   │   └─ Write signals.csv
│       │
│       ├─ generate_products_csv(accounts, output_dir)
│       │   ├─ For each account:
│       │   │   ├─ Select 1-3 products from PRODUCT_IDS
│       │   │   ├─ For each product:
│       │   │   │   ├─ quantity, utilization_percent, monthly_spend
│       │   │   │   ├─ adoption_date (recovery accounts: during crisis)
│       │   │   │   ├─ satisfaction_score (lower for recovery accounts)
│       │   │   │   └─ expansion_potential, churn_risk
│       │   │   └─ Write products.csv
│       │
│       └─ generate_profiles_csv(accounts, output_dir)
│           ├─ For each account:
│           │   ├─ Calculate derived fields:
│           │   │   ├─ arr_growth_amount, arr_growth_percent
│           │   │   └─ expansion_count, contraction_count
│           │   ├─ Generate 100+ profile attributes:
│           │   │   ├─ Basic: account_name, industry, tier, company_size
│           │   │   ├─ Financial: initial_arr, current_arr, arr_growth, LTV
│           │   │   ├─ Contract: contract_start, contract_end, renewal_likelihood
│           │   │   ├─ Health: overall_health_score, nps_score, csat_score
│           │   │   ├─ Engagement: executive_engagement, champion_strength
│           │   │   ├─ Technical: gpu_count, datacenter_location, utilization
│           │   │   ├─ Journey: journey_type, journey_phase, customer_maturity
│           │   │   ├─ Risk: churn_risk_level, competitive_risk, budget_risk
│           │   │   └─ Strategic: strategic_account, reference_customer, etc.
│           │   └─ Write profiles.csv
│
└─ Print summary (file counts, account ID range)
```

### Key Functions Called

| Function | Purpose |
|---------|---------|
| `create_customer_17()` | Creates Customer and User records in database (optional) |
| `generate_accounts_csv()` | Generates accounts.csv (10 accounts by default) |
| `generate_kpis_csv()` | Generates kpis.csv (12 months × 33 KPIs × 10 accounts = ~3,960 rows) |
| `generate_signals_csv()` | Generates signals.csv (~15-30 signals per account = ~200 rows) |
| `generate_products_csv()` | Generates products.csv (1-3 products per account = ~20 rows) |
| `generate_profiles_csv()` | Generates profiles.csv (1 profile per account = 10 rows) |

### What It Generates

- **CSV Files** (5 files):
  1. `accounts.csv` - 10 accounts with metadata
  2. `kpis.csv` - ~3,960 KPI measurements (time series)
  3. `signals.csv` - ~200 qualitative signals
  4. `products.csv` - ~20 product associations
  5. `profiles.csv` - 10 comprehensive account profiles (100+ columns)

- **Database Records** (if `--create-customer` flag):
  - Customer record (customer_id=17)
  - User record (admin user)

### Dependencies

- **Imports**: 
  - `app_v3_minimal` (Flask app context)
  - `models` (Customer, User)
  - Standard library: `csv`, `random`, `datetime`, `pathlib`

- **Configuration Constants**:
  - `CUSTOMER_ID = 17`
  - `NUM_ACCOUNTS = 10`
  - `BASE_ACCOUNT_ID = 17001`
  - `NUM_MONTHS_HISTORICAL = 12`
  - `KPI_CODES` (33 KPIs)
  - `PRODUCT_IDS`, `PRODUCT_NAMES` (7 products)

---

## 3. Complete Onboarding Flow (After provision_dc_customer.py)

### Manual Steps (from provision_dc_customer.py output)

```
1. Upload CSV files to customer_dir/data/
   ├─ accounts.csv
   ├─ kpi_measurements.csv (or kpis.csv)
   ├─ qualitative_signals.csv (or signals.csv)
   ├─ products.csv
   └─ profiles.csv (or account_profiles.csv)

2. Load data into database:
   └─ python3 02_load_customer{customer_id}_data_SMART.py
      ├─ check_database() → Verify DATABASE_URL
      ├─ check_existing_data() → Check if customer data exists
      ├─ delete_customer{customer_id}_data() → Delete existing data
      ├─ For each CSV file:
      │   ├─ Read CSV with pandas
      │   ├─ Transform columns (if needed)
      │   └─ Insert into database table
      └─ Print summary

3. Create embeddings:
   └─ python3 03_embed_customer{customer_id}_OPENAI.py
      ├─ Load data from database
      ├─ Generate embeddings (OpenAI API)
      └─ Store in Qdrant/vector DB

4. Generate journey data (Wizard A):
   └─ journey/wizard_a/wizard_a_journey_generator.py
      ├─ Load account data
      ├─ Generate journey narratives
      └─ Create journey JSON files

5. Create user in database:
   └─ create_customer{customer_id}_user.py
      ├─ Create Customer record
      └─ Create User record
```

---

## 4. Key Differences

| Aspect | provision_dc_customer.py | generate_customer17_seed_data.py |
|--------|--------------------------|----------------------------------|
| **Purpose** | Create directory structure from template | Generate CSV seed data files |
| **Input** | `_template/` directory | Configuration constants |
| **Output** | Customer directory (no data) | 5 CSV files |
| **Account ID Formula** | `10000 + customer_id * 1000` | Hardcoded `BASE_ACCOUNT_ID = 17001` |
| **Customer ID** | Parameter (--customer-id) | Hardcoded `CUSTOMER_ID = 17` |
| **Data Generation** | None (expects manual upload) | Full synthetic data generation |
| **Database Operations** | None | Optional (--create-customer flag) |
| **Dependencies** | File system operations | Flask app, models, database |
| **Use Case** | Provision new customer structure | Generate demo/test data |

---

## 5. Integration Points

### How They Work Together

1. **provision_dc_customer.py** creates the structure:
   ```
   backend/verticals/customer18-dc2_s/
   ├─ data/          (empty, expects CSV files)
   ├─ scripts/       (with customer18 placeholders)
   └─ services/      (with customer18 placeholders)
   ```

2. **generate_customer17_seed_data.py** (or similar) generates CSV files:
   ```
   backend/verticals/customer18-dc2_s/data/
   ├─ accounts.csv
   ├─ kpis.csv
   ├─ signals.csv
   ├─ products.csv
   └─ profiles.csv
   ```

3. **02_load_customer18_data_SMART.py** loads CSVs into database

4. **03_embed_customer18_OPENAI.py** creates embeddings

5. **wizard_a_journey_generator.py** generates journey data

---

## 6. Recommendations for Onboarding Wizard Integration

### Current Onboarding API Approach
- Uses `generate_customer17_seed_data.py` functions directly
- Dynamically overrides constants (NUM_ACCOUNTS, etc.)
- Transforms CSV output to match expected format

### Potential Improvements

1. **Use Account ID Formula from provision_dc_customer.py**:
   ```python
   account_id_start = 10000 + customer_id * 1000
   ```
   - But: Customer ID not known during onboarding wizard
   - Solution: Use temporary ID, update after customer creation

2. **Align with Template Services**:
   - Consider using `realistic_kpi_generator.py` from `_template/services/`
   - More aligned with production data format

3. **Generate Files in Correct Format**:
   - Match exactly what `02_load_customer{customer_id}_data_SMART.py` expects
   - No transformation needed in onboarding API

4. **Parameterize Customer ID**:
   - Make `generate_customer17_seed_data.py` accept customer_id as parameter
   - Or create a generic version that works for any customer
