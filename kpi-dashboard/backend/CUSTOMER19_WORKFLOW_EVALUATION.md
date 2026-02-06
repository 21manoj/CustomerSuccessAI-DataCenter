# Customer 19 Workflow Evaluation & Open Questions

## Workflow Overview

The proposed workflow has **3 phases**:
1. **PHASE 1: PREPARATION** - Scripts to provision directory and generate CSV files
2. **PHASE 2: PRODUCTION API FLOW** - API endpoints for customer creation, upload, processing
3. **PHASE 3: VERIFICATION** - Validation and testing

---

## ✅ What Exists

### Phase 1 Scripts
- ✅ **`provision_dc_customer.py`** - **EXISTS** (`verticals/provision_dc_customer.py`)
  - **What it does:** Creates customer directory structure from `_template`
  - **Account ID formula:** `10000 + customer_id * 1000` (so customer 19 = 29000)
  - **Usage:** `python3 provision_dc_customer.py --customer-id 19 --customer-name "DC2_S Demo Enterprise"`
  - **Status:** ✅ Ready to use

- ⚠️ **`generate_synthetic_customer_data.py`** - **NOT FOUND**
  - **Found instead:** `scripts/generate_synthetic_dc2s_data.py`
  - **Gap:** Script name mismatch, and doesn't support `--journey-patterns DEMO_MANIFEST`
  - **Current capabilities:** Generates accounts, KPIs, signals, products (simple synthetic data)
  - **Question:** Should we:
    - Use `generate_synthetic_dc2s_data.py` as-is?
    - Rename/alias it?
    - Enhance it to support `--journey-patterns DEMO_MANIFEST`?

### Phase 2 API Endpoints

1. ✅ **`/api/onboarding/complete`** - **EXISTS** (V2)
   - **Current signature:** `customer_name`, `email`, `industry`, `vertical`
   - **Workflow expects:** `customer_id`, `customer_name`, `domain`, `industry`, `vertical`, `email`, `username`, `weights`
   - **Gap:** V2 doesn't accept `customer_id` (auto-generated), `domain`, `username`, `weights` in request
   - **Question:** Should we enhance V2 to accept these fields, or use a different endpoint?

2. ⚠️ **`/api/onboarding/upload`** - **EXISTS IN DEPRECATED ONLY**
   - **Found in:** `scripts/onboarding_api_DEPRICATED.py` (line 800) ✅
   - **NOT found in:** `onboarding_api_v2_config_aware.py` (current V2) ❌
   - **Capabilities:** Uploads CSV/Excel files to `customer{N}-dc2_s/data/` directory
   - **Question:** Should we:
     - **Option A:** Add upload endpoint to V2 (recommended for production)
     - **Option B:** Use deprecated endpoint (works but not ideal)
     - **Option C:** Skip upload (files already in directory from Phase 1)

3. ✅ **`/api/onboarding/process-data`** - **EXISTS** (V2 Enhanced)
   - **Status:** ✅ Just enhanced with all 7 steps
   - **Signature matches:** ✅ Accepts `customer_id`, `skip_validation`, `skip_wizard_b`, `skip_wizard_c`
   - **Ready to use:** ✅

4. ❓ **`/api/onboarding/register-journey-api`** - **STATUS UNCLEAR**
   - **Found in:** `scripts/onboarding_api_DEPRICATED.py` (line 2548)
   - **NOT found in:** `onboarding_api_v2_config_aware.py` (current V2)
   - **Note:** Enhanced V2 `process-data` marks journey API as ready automatically
   - **Question:** Is this endpoint still needed, or is it redundant with enhanced V2?

### Phase 3 Verification
- ✅ **`04_validate_data_integrity.py`** - **EXISTS** (referenced in workflow)
- ✅ **Executive Dashboard** - **EXISTS** (UI route)
- ✅ **Journey Visualizer** - **EXISTS** (UI route)
- ✅ **Signal Analyst API** - **EXISTS** (`/api/signal-analyst/analyze`)

---

## ❌ Issues Found

### Issue 1: Account ID Formula Discrepancy ⚠️ **CRITICAL**
- **Workflow shows:** `account_id: 29001` in verification step
- **Provision script formula:** `10000 + customer_id * 1000 = 10000 + 19000 = 29000` ✅ **MATCHES**
- **V2 `/complete` formula:** `customer_id * 1000 = 19000` ❌ **DOESN'T MATCH**
- **Gap:** Two different account ID formulas in use!
  - Provision script: `10000 + customer_id * 1000` → Customer 19 = 29000-29999
  - V2 complete endpoint: `customer_id * 1000` → Customer 19 = 19000-19999
- **Impact:** If using provision script, accounts will be 29000+, but V2 creates 19000+
- **Question:** Which formula should be standard? Should we:
  - **Option A:** Use provision script formula everywhere (`10000 + customer_id * 1000`)
  - **Option B:** Use V2 formula everywhere (`customer_id * 1000`)
  - **Option C:** Make V2 accept explicit account IDs

### Issue 2: Vertical Naming Inconsistency
- **Workflow uses:** `"vertical": "DC2_S"` (uppercase with underscore)
- **V2 expects:** `"vertical": "dc2_s"` (lowercase)
- **Question:** Which format is correct? Should we normalize?

### Issue 3: Missing Upload Endpoint in V2
- **Workflow requires:** `/api/onboarding/upload` for CSV files
- **V2 status:** Endpoint not found in `onboarding_api_v2_config_aware.py`
- **Impact:** Cannot upload CSV files via V2 API
- **Question:** Should we:
  - Add upload endpoint to V2?
  - Use deprecated endpoint?
  - Skip upload step and use pre-generated files?

### Issue 4: `/api/onboarding/complete` Field Mismatch
- **Workflow expects:**
  ```json
  {
    "customer_id": 19,  // ❌ V2 auto-generates this
    "customer_name": "...",
    "domain": "...",    // ❌ Not in V2
    "username": "...",  // ❌ Not in V2
    "weights": {...}    // ❌ Not in V2
  }
  ```
- **V2 accepts:**
  ```json
  {
    "customer_name": "...",
    "email": "...",
    "industry": "...",
    "vertical": "dc2_s"
  }
  ```
- **Question:** Should we enhance V2 to accept these fields?

### Issue 5: Journey API Registration Redundancy
- **Enhanced V2 `process-data`:** Automatically marks journey API as ready (Step 7)
- **Workflow step 6:** Calls `/api/onboarding/register-journey-api` separately
- **Question:** Is step 6 redundant, or does it do something additional?

---

## 🔍 Open Questions

### Q1: Script Availability ✅ **RESOLVED**
**Answer:** Scripts exist but with differences:
- ✅ `provision_dc_customer.py` - **EXISTS** at `verticals/provision_dc_customer.py`
- ⚠️ `generate_synthetic_customer_data.py` - **NOT FOUND**
  - **Found instead:** `scripts/generate_synthetic_dc2s_data.py`
  - **Gap:** Doesn't support `--journey-patterns DEMO_MANIFEST`

**Action Needed:** 
- Use `generate_synthetic_dc2s_data.py` as-is, OR
- Enhance it to support `--journey-patterns DEMO_MANIFEST` for demo manifest-based data generation

### Q2: Upload Endpoint Strategy
**Question:** How should CSV files be uploaded?
- **Option A:** Add `/api/onboarding/upload` to V2
- **Option B:** Use deprecated endpoint from `onboarding_api_DEPRICATED.py`
- **Option C:** Skip upload (files already in directory from Phase 1)

**Recommendation:** Option C (skip upload) if files are pre-generated in Phase 1.

### Q3: Customer Creation Endpoint Enhancement
**Question:** Should we enhance `/api/onboarding/complete` to accept:
- `customer_id` (optional, for explicit ID assignment)
- `domain`
- `username` (for initial user creation)
- `weights` (for pillar/KPI weights)

**Recommendation:** Yes, for production alignment.

### Q4: Account ID Formula Standardization ⚠️ **CRITICAL**
**Question:** Which account ID formula should be standard?
- **Provision script:** `10000 + customer_id * 1000` → Customer 19 = 29000-29999
- **V2 complete endpoint:** `customer_id * 1000` → Customer 19 = 19000-19999
- **Workflow shows:** `29001` (matches provision script)

**Impact:** If using provision script + V2, accounts will be in different ranges!

**Recommendation:** 
- **Option A (Recommended):** Standardize on provision script formula (`10000 + customer_id * 1000`)
  - Update V2 `/complete` to use same formula
  - Customer 19 accounts: 29000-29999
- **Option B:** Standardize on V2 formula (`customer_id * 1000`)
  - Update provision script to use same formula
  - Customer 19 accounts: 19000-19999

### Q5: Journey API Registration
**Question:** Is `/api/onboarding/register-journey-api` still needed?
- **Enhanced V2:** Automatically marks journey API ready
- **Deprecated version:** Has separate registration step

**Recommendation:** Remove step 6 if using enhanced V2, or keep if it does additional setup.

### Q6: Vertical Format
**Question:** Which vertical format is correct?
- `"DC2_S"` (uppercase, underscore)
- `"dc2_s"` (lowercase, underscore)

**Recommendation:** Use `"dc2_s"` (lowercase) to match V2 expectations.

### Q7: User Creation
**Question:** When should the initial user be created?
- **Workflow step 3:** `/api/onboarding/complete` expects `username` and `email`
- **V2 current:** Only creates customer, not user
- **Gap:** No user creation in V2 `/complete` endpoint

**Recommendation:** Enhance V2 to create initial admin user.

### Q8: Weight Configuration
**Question:** How should pillar weights be set?
- **Workflow expects:** `weights` object in `/complete` request
- **V2 current:** Uses default weights (AI: 0.25, CH: 0.20, etc.)
- **Gap:** Cannot set custom weights via API

**Recommendation:** Enhance V2 to accept and apply custom weights.

---

## 📋 Recommended Workflow Corrections

### Corrected Phase 2 (Production API Flow)

```bash
# 3. Create customer via API (ENHANCED V2)
curl -X POST http://localhost:5000/api/onboarding/complete \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "DC2_S Demo Enterprise",
    "email": "admin@dc2s-demo.example.com",
    "industry": "Data Center Infrastructure",
    "vertical": "dc2_s",
    "username": "dc2s_admin",
    "password": "TestPass123!",
    "weights": {
      "AI": 0.10,
      "CH": 0.30,
      "DV": 0.30,
      "EX": 0.05,
      "OS": 0.25
    }
  }'

# Note: customer_id will be auto-generated (or accept it if provided)

# 4. Upload CSV files (IF upload endpoint exists, OR skip if files already in directory)
# Option A: If upload endpoint exists
for file in accounts kpis signals products profiles; do
  curl -X POST http://localhost:5000/api/onboarding/upload \
    -F "file=@customer19-dc2_s/data/${file}.csv" \
    -F "customer_id=19" \
    -F "file_type=${file}"
done

# Option B: Skip upload (files already in directory from Phase 1)

# 5. Process uploaded data (ENHANCED V2 - includes all steps)
curl -X POST http://localhost:5000/api/onboarding/process-data \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 19,
    "skip_validation": false,
    "skip_wizard_b": false,
    "skip_wizard_c": false
  }'

# 6. Register journey API (OPTIONAL - may be redundant with enhanced V2)
# Skip if enhanced V2 process-data already marks it ready
```

### Corrected Phase 3 (Verification)

```bash
# 7. Verify data loaded
python3 scripts/04_validate_data_integrity.py --customer-id 19

# 8. Check executive dashboard
open http://localhost:3000/executive-dashboard?customer=19

# 9. Test journey visualizer (USE CORRECT ACCOUNT ID)
# Expected: account_id = 29001 (first account for customer 19, using provision script formula)
# NOTE: If using V2 /complete endpoint, account_id would be 19001 instead
open http://localhost:3000/journey-v3/29001

# 10. Test Signal Analyst (USE CORRECT ACCOUNT ID)
curl -X POST http://localhost:5000/api/signal-analyst/analyze \
  -H "Content-Type: application/json" \
  -d '{"account_id": 29001}'
```

---

## 🎯 Action Items

### High Priority
1. ✅ **Verify script existence:** `provision_dc_customer.py`, `generate_synthetic_customer_data.py`
2. ✅ **Decide on upload strategy:** Add to V2, use deprecated, or skip
3. ✅ **Enhance `/api/onboarding/complete`:** Add `username`, `password`, `weights` support
4. ✅ **Fix account ID:** Use `19001` instead of `29001`

### Medium Priority
5. ✅ **Clarify journey API registration:** Is step 6 needed with enhanced V2?
6. ✅ **Standardize vertical format:** Use `dc2_s` (lowercase)

### Low Priority
7. ✅ **Add user creation to `/complete`:** Create initial admin user
8. ✅ **Document workflow:** Create final corrected workflow document

---

## 📝 Next Steps

1. **Answer open questions** (Q1-Q8 above)
2. **Create missing scripts** (if needed)
3. **Enhance V2 endpoints** (if needed)
4. **Test corrected workflow** end-to-end
5. **Document final workflow** for Customer 19
