# `/api/onboarding/process-data` Endpoint - Complete Scope

## Overview

The `/api/onboarding/process-data` endpoint is a **critical orchestration endpoint** that processes uploaded customer data files and executes a series of scripts to transform raw CSV/Excel files into a fully functional customer instance in the platform.

## Current Implementation Status

**Active Version:** `onboarding_api_v2_config_aware.py` (V2 - Config-Aware)  
**Location:** Registered in `app_v3_minimal.py` as `/api/onboarding/*`

**Note:** There's also a deprecated version (`scripts/onboarding_api_DEPRICATED.py`) that has a more complete implementation with multiple script executions. The current V2 version is simpler.

---

## Current V2 Implementation Scope

### What It Does Now:

1. **CSV Validation (Config-Aware)**
   - Validates `kpi_measurements.csv` against `CustomerConfig`
   - Checks if KPIs in CSV are enabled in config
   - Provides warnings for disabled KPIs
   - Calculates filter statistics

2. **Data Loading (direct from saved CSVs)**
   - Reads CSVs from `verticals/customer{N}-dc2_s/data/` (files saved by the upload endpoint)
   - Loads directly into PostgreSQL (dc2s_kpis, qualitative_signals). No 02_load or 02_upload scripts.
   - Config-aware validation of kpi_measurements against CustomerConfig before loading

### What It Returns:

```json
{
  "success": true,
  "message": "Data loaded successfully (config-aware)",
  "validation": {
    "valid": true,
    "enabled_kpis": 15,
    "csv_kpis": 35,
    "disabled_kpis": [...],
    "warnings": [...],
    "details": {
      "total_records": 5400,
      "enabled_records": 1800,
      "filtered_records": 3600
    }
  },
  "loader_output": "..."
}
```

---

## Full Intended Scope (From Deprecated Version)

Based on the deprecated implementation and documentation, the **complete intended scope** includes:

### Step 1: Data Loading ✅ (Currently Implemented)
- **Mechanism:** Direct load from saved CSVs (no 02_load/02_upload scripts). CSVs are uploaded via `/api/onboarding/upload` and saved to customer data dir; process-data reads them and loads into PostgreSQL.
- **Purpose:** Load CSV files → PostgreSQL (dc2s_kpis, qualitative_signals)
- **Features:**
  - Config-aware validation of kpi_measurements against CustomerConfig
  - Loads kpi_measurements.csv → dc2s_kpis, qualitative_signals.csv → qualitative_signals
- **Status:** ✅ Implemented in V2

### Step 2: Embedding Generation ⚠️ (Not in V2)
- **Script:** `03_embed_customer{N}_OPENAI.py`
- **Purpose:** Create embeddings from database → Qdrant Cloud
- **Features:**
  - Uses OpenAI `text-embedding-3-large` (3072 dimensions)
  - Builds knowledge base in Qdrant
  - Per-customer collection: `kpi_dashboard_vectors_customer_{N}`
- **Status:** ⚠️ **NOT in current V2 implementation**
- **Location:** Should be in `verticals/customer{N}-dc2_s/scripts/`

### Step 3: Data Validation ⚠️ (Not in V2)
- **Script:** `04_validate_data_integrity.py`
- **Purpose:** Validate data integrity after loading
- **Features:**
  - Checks data completeness
  - Validates relationships
  - Reports data quality issues
- **Status:** ⚠️ **NOT in current V2 implementation** (optional, can be skipped)
- **Location:** Should be in `verticals/customer{N}-dc2_s/scripts/`

### Step 4: Journey Generation (Wizard A) ⚠️ (Not in V2)
- **Script:** `wizard_a_journey_generator.py` or `wizard_journey_generator.py`
- **Purpose:** Generate journey JSON files for visualization
- **Features:**
  - Creates journey timeline data
  - Generates health score progression
  - Creates milestone events
  - Outputs to `verticals/customer{N}-dc2_s/journey/wizard_a/outputs/`
- **Status:** ⚠️ **NOT in current V2 implementation**
- **Location:** Should be in `verticals/customer{N}-dc2_s/journey/wizard_a/`

### Step 5: Pattern Analysis (Wizard B) ⚠️ (Not in V2)
- **Script:** `wizard_b_pattern_analyzer.py`
- **Purpose:** Analyze patterns in customer data
- **Features:**
  - Identifies trends
  - Detects anomalies
  - Generates insights
- **Status:** ⚠️ **NOT in current V2 implementation** (optional)
- **Location:** Should be in `verticals/customer{N}-dc2_s/journey/wizard_b/`

### Step 6: Weight Calibration (Wizard C) ⚠️ (Not in V2)
- **Script:** `wizard_c_weight_calibrator.py` or `weight_calibrator.py`
- **Purpose:** Calibrate pillar/KPI weights based on data
- **Features:**
  - Learns optimal weights from historical data
  - Updates `CustomerConfig.dc2s_pillar_weights` and `dc2s_kpi_weights`
  - Self-learning system
- **Status:** ⚠️ **NOT in current V2 implementation** (optional but recommended)
- **Location:** Should be in `verticals/customer{N}-dc2_s/journey/wizard_c/`

---

## Request Format

### Current V2:
```json
{
  "customer_id": 123
}
```

### Full Intended (Deprecated Version):
```json
{
  "customer_id": 123,
  "skip_validation": false,    // Optional: skip validation script
  "skip_wizard_b": true,       // Optional: skip Wizard B
  "skip_wizard_c": false,      // Optional: skip Wizard C (default: run it)
  "upload_mode": "incremental" // Optional: full_refresh, incremental, upsert, merge
}
```

---

## Response Format

### Current V2:
```json
{
  "success": true,
  "message": "Data loaded successfully (config-aware)",
  "validation": {...},
  "loader_output": "..."
}
```

### Full Intended (Deprecated Version):
```json
{
  "status": "success",
  "message": "Data processing completed successfully",
  "customer_id": 123,
  "steps_completed": [
    "data_loading",
    "embeddings",
    "validation",
    "journey_generation",
    "pattern_analysis",      // Optional
    "weight_calibration",    // Optional
    "journey_api_ready"
  ],
  "errors": [],
  "log_file": "path/to/log"
}
```

---

## Prerequisites

### Files Required:
1. **Customer Directory:** `verticals/customer{N}-dc2_s/`
2. **Data Files:** `verticals/customer{N}-dc2_s/data/` (saved by upload endpoint)
   - `accounts.csv` (required)
   - `kpi_measurements.csv` (required)
   - `qualitative_signals.csv` (optional)
   - `account_notes.csv` (optional)
   - Data is loaded directly from these CSVs by process-data; no 02_load/02_upload scripts.

### Database Requirements:
- Customer must exist in `customers` table
- `CustomerConfig` must exist with `vertical='dc2_s'`
- Enabled KPIs must be configured

---

## Execution Flow

### Current V2 Flow:
```
1. Validate CSV against CustomerConfig
   ↓
2. Load CSVs directly from customer data dir → PostgreSQL (no 02_load/02_upload scripts)
   ↓
3. Return results
```

### Full Intended Flow:
```
1. Validate CSV against CustomerConfig
   ↓
2. Load CSVs directly from saved files → PostgreSQL (dc2s_kpis, qualitative_signals)
   ↓
3. Execute embedding script (03_embed_*.py)
   ↓
4. Execute validation script (04_validate_*.py) [optional]
   ↓
5. Execute journey generator (wizard_a_*.py)
   ↓
6. Execute pattern analyzer (wizard_b_*.py) [optional]
   ↓
7. Execute weight calibrator (wizard_c_*.py) [optional]
   ↓
8. Mark journey API as ready
```

---

## Key Features

### ✅ Currently Available:
1. **Config-Aware Validation** - Validates KPIs against enabled KPIs in config
2. **CSV Filtering** - Automatically filters disabled KPIs
3. **Warning System** - Provides detailed warnings about filtered data
4. **Data Loading** - Loads validated data to PostgreSQL

### ⚠️ Missing (But Intended):
1. **Embedding Generation** - Qdrant knowledge base creation
2. **Data Validation** - Post-load integrity checks
3. **Journey Generation** - Timeline JSON file creation
4. **Pattern Analysis** - Trend detection and insights
5. **Weight Calibration** - Self-learning weight optimization
6. **Rollback Support** - Transaction rollback on failure
7. **Progress Logging** - Detailed execution logs
8. **Error Tracking** - Comprehensive error reporting

---

## Comparison: V2 vs Deprecated

| Feature | V2 (Current) | Deprecated (Full) |
|---------|--------------|-------------------|
| CSV Validation | ✅ | ✅ |
| Config-Aware Filtering | ✅ | ✅ |
| Data Loading | ✅ | ✅ |
| Embedding Generation | ❌ | ✅ |
| Data Validation | ❌ | ✅ |
| Journey Generation | ❌ | ✅ |
| Pattern Analysis | ❌ | ✅ |
| Weight Calibration | ❌ | ✅ |
| Rollback Support | ❌ | ✅ |
| Progress Logging | ❌ | ✅ |
| Error Tracking | ❌ | ✅ |

---

## Recommendations

### For New Customer Creation:

**Option A: Use Current V2 + Manual Steps**
1. Call `/api/onboarding/process-data` (loads data)
2. Manually build Qdrant knowledge base (via API or script)
3. Manually calculate health scores (L1/L2/L3)
4. Manually generate journey files (if needed)

**Option B: Enhance V2 to Match Deprecated Version**
- Add embedding script execution
- Add validation script execution
- Add journey generation
- Add rollback support
- Add comprehensive logging

**Option C: Use Direct Database Seeding**
- Skip onboarding API entirely
- Seed data directly via Python scripts
- Build knowledge base via API
- Calculate health scores automatically

---

## Open Questions

1. **Which version should we use?**
   - Current V2 (simpler, only data loading)
   - Enhanced V2 (add missing steps)
   - Deprecated version (full featured, but deprecated)

2. **For new customer creation, should we:**
   - Use onboarding API flow (requires CSV files + scripts)
   - Use direct database seeding (faster, more control)

3. **Are the missing scripts available?**
   - `03_embed_customer{N}_OPENAI.py` - Does it exist?
   - `wizard_a_journey_generator.py` - Does it exist?
   - `wizard_c_weight_calibrator.py` - Does it exist?

4. **Should we create a unified onboarding script?**
   - That combines customer creation + data seeding + knowledge base building
   - Without requiring CSV files and separate scripts
