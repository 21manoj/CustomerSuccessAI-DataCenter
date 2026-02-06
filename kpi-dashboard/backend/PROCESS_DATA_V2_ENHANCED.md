# `/api/onboarding/process-data` - Enhanced V2 Implementation

## ✅ Enhancement Complete

The V2 implementation has been enhanced to include **all 7 steps** from the full workflow.

**Gap fixes applied:** Data loading is config-aware (filters by `dc2s_enabled_kpis`). Critical steps are `data_loading` and `embeddings`; if either is missing, the endpoint returns 500. Optional steps (validation, pattern_analysis, weight_calibration) are tracked in `optional_steps_skipped`. Wizard C config changes are logged for cache invalidation. Progress: `GET /api/onboarding/status/<customer_id>`. See **ONBOARDING_GAP_FIXES_APPLIED.md** for full list.

---

## Enhanced Scope

### Step 1: Data Loading ✅
- **Mechanism:** Direct load from saved CSVs (no 02_load/02_upload scripts). CSVs are uploaded via `/api/onboarding/upload`; process-data reads from customer data dir and loads into PostgreSQL.
- **Purpose:** Load CSV files → PostgreSQL (dc2s_kpis, qualitative_signals)
- **Features:**
  - Config-aware validation of kpi_measurements against CustomerConfig
  - Loads kpi_measurements.csv → dc2s_kpis, qualitative_signals.csv → qualitative_signals
- **Status:** ✅ Implemented

### Step 2: Embedding Generation ✅ (NEW)
- **Script:** `03_embed_customer{N}_OPENAI.py` (if exists)
- **Fallback:** Uses `enhanced_rag_qdrant.build_knowledge_base()` API if script not found
- **Purpose:** Create embeddings from database → Qdrant Cloud
- **Features:**
  - Uses OpenAI `text-embedding-3-large` (3072 dimensions)
  - Builds knowledge base in Qdrant
  - Per-customer collection: `kpi_dashboard_vectors_customer_{N}`
- **Status:** ✅ Implemented (with API fallback)

### Step 3: Data Validation ✅ (NEW - Optional)
- **Script:** `04_validate_data_integrity.py`
- **Purpose:** Validate data integrity after loading
- **Features:**
  - Checks data completeness
  - Validates relationships
  - Reports data quality issues
- **Status:** ✅ Implemented (optional, can be skipped)
- **Skip:** Set `skip_validation: true` in request

### Step 4: Journey Generation (Wizard A) ✅ (NEW)
- **Script:** `wizard_a_journey_generator.py` or `wizard_journey_generator.py`
- **Purpose:** Generate journey JSON files for visualization
- **Features:**
  - Creates journey timeline data
  - Generates health score progression
  - Creates milestone events
  - Outputs to `verticals/customer{N}-dc2_s/journey/wizard_a/outputs/`
- **Status:** ✅ Implemented (gracefully skips if script not found)

### Step 5: Pattern Analysis (Wizard B) ✅ (NEW - Optional)
- **Script:** `wizard_b_pattern_analyzer.py`
- **Purpose:** Analyze patterns in customer data
- **Features:**
  - Identifies trends
  - Detects anomalies
  - Generates insights
- **Status:** ✅ Implemented (optional, default: skipped)
- **Skip:** Set `skip_wizard_b: true` in request (default)

### Step 6: Weight Calibration (Wizard C) ✅ (NEW - Optional)
- **Script:** `wizard_c_weight_calibrator.py` or `weight_calibrator.py`
- **Purpose:** Calibrate pillar/KPI weights based on data
- **Features:**
  - Learns optimal weights from historical data
  - Updates `CustomerConfig.dc2s_pillar_weights` and `dc2s_kpi_weights`
  - Self-learning system
- **Status:** ✅ Implemented (optional, default: runs)
- **Skip:** Set `skip_wizard_c: true` in request

### Step 7: Journey API Ready ✅ (NEW)
- **Purpose:** Mark journey API as ready
- **Features:**
  - Dynamic journey API automatically discovers journey files
  - No manual registration needed
- **Status:** ✅ Implemented

---

## Request Format

```json
{
  "customer_id": 123,
  "skip_validation": false,    // Optional: skip validation script
  "skip_wizard_b": true,       // Optional: skip Wizard B (default: true)
  "skip_wizard_c": false,      // Optional: skip Wizard C (default: false - runs it)
  "upload_mode": "incremental" // Optional: full_refresh, incremental, upsert, merge
}
```

---

## Response Format

```json
{
  "status": "success",  // or "warning" if errors but completed
  "message": "Data processing completed successfully",
  "customer_id": 123,
  "steps_completed": [
    "data_loading",
    "embeddings",
    "validation",
    "journey_generation",
    "weight_calibration",
    "journey_api_ready"
  ],
  "errors": [],  // Warnings/non-critical errors
  "validation": {
    "valid": true,
    "enabled_kpis": 15,
    "csv_kpis": 35,
    "disabled_kpis": [...],
    "warnings": [...]
  },
  "total_steps": 6
}
```

---

## Key Features

### ✅ Graceful Degradation
- If embedding script not found → Uses API fallback
- If validation script not found → Skips (optional step)
- If journey generator not found → Logs warning, continues
- If Wizard B/C not found → Logs warning, continues

### ✅ Error Handling
- Tracks execution state
- Continues with remaining steps even if one fails (non-critical)
- Returns comprehensive error list
- Logs all steps with timing

### ✅ Config-Aware
- Validates CSV against CustomerConfig before processing
- Filters disabled KPIs automatically
- Provides detailed validation warnings

### ✅ Flexible Execution
- Optional steps can be skipped
- Upload mode support
- Timeout protection (600s for data/embedding, 300s for others)

---

## Execution Flow

```
1. Validate CSV against CustomerConfig
   ↓
2. Load CSVs directly from customer data dir → PostgreSQL (no 02_load/02_upload scripts)
   ↓
3. Execute embedding script (03_embed_*.py) OR use API fallback
   ↓
4. Execute validation script (04_validate_*.py) [if not skipped]
   ↓
5. Execute journey generator (wizard_a_*.py)
   ↓
6. Execute pattern analyzer (wizard_b_*.py) [if not skipped]
   ↓
7. Execute weight calibrator (wizard_c_*.py) [if not skipped]
   ↓
8. Mark journey API as ready
```

---

## Helper Functions Added

1. **`get_customer_directory(customer_id, vertical_slug='dc2_s')`**
   - Returns Path to customer directory
   - Location: `backend/verticals/customer{N}-dc2_s/`

2. **`execute_script(script_path, customer_id, timeout, additional_args, env)`**
   - Executes Python scripts synchronously
   - Sets `CUSTOMER_ID` environment variable
   - Supports additional arguments and environment variables
   - Returns `(success, stdout, stderr)`

---

## Next Steps

The enhanced V2 implementation is now ready. For creating the new customer account, we can:

1. **Use the enhanced process-data endpoint** (requires CSV files + scripts)
2. **Use direct database seeding** (faster, more control, no CSV files needed)

Which approach would you prefer for creating the new reference customer account?
