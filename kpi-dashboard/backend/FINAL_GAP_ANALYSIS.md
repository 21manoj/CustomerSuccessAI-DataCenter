# Final Comprehensive Gap Analysis
**Date:** January 19, 2026  
**Reference:** CS_PULSE_DC2_S_STRUCTURE (1).md

---

## 🔴 CRITICAL GAPS (Must Fix)

### 1. Provisioning Customer Directory ❌
**Documentation:** STEP 1 - Must run `provision_dc_customer.py` before wizard
**Current:** No provisioning call in API
**Impact:** Customer directory structure not created
**Fix:** Call `provision_dc_customer.py` programmatically in `/api/onboarding/complete`

---

### 2. File Storage to Customer Directory ❌
**Documentation:** Files must be in `customer{N}-dc2_s/data/` for scripts
**Current:** Files uploaded directly to DB, NOT saved to directory
**Impact:** Loading scripts can't find files
**Fix:** Save uploaded files to `customer{N}-dc2_s/data/` directory

---

### 3. Data Loading Script Execution ❌
**Documentation:** STEP 3 - Run `02_load_customer{N}_data_SMART.py`
**Current:** No script execution
**Impact:** CSV files not loaded to PostgreSQL
**Fix:** Execute script after files are saved

---

### 4. Embedding Script Execution ❌
**Documentation:** STEP 4 - Run `03_embed_customer{N}_OPENAI.py`
**Current:** No script execution
**Impact:** No embeddings in Qdrant
**Fix:** Execute script after data loading

---

### 5. Journey Generator Execution ❌
**Documentation:** STEP 5 - Run `wizard_a_journey_generator.py`
**Current:** No script execution
**Impact:** No journey JSON files created
**Fix:** Execute script after embeddings

---

## 🟡 HIGH PRIORITY GAPS

### 6. Team Data Collection ⚠️
**Documentation:** STEP 2 mentions "team" data collection
**Current:** 
- `OnboardingWizard.main.tsx` has Step7Team
- `OnboardingWizard.tsx` (used in App.tsx) does NOT have Step7Team
- Team data not sent to `/api/onboarding/complete`
**Impact:** Team members not created as User records
**Fix:** 
1. Integrate Step7Team into OnboardingWizard.tsx OR use OnboardingWizard.main.tsx
2. Send team data to complete endpoint
3. Create User records for team members

---

### 7. Journey API Registration ⚠️
**Documentation:** Each customer needs `customer{N}_journey_api.py` registered
**Current:** 
- `customer17_journey_api.py` is hardcoded in `app_v3_minimal.py`
- New customers won't have journey API registered
**Impact:** Journey endpoints won't work for new customers
**Fix:** Dynamic registration of journey API blueprints

---

### 8. Data Validation Script ⚠️
**Documentation:** STEP 5 - Run `04_validate_data_integrity.py`
**Current:** No execution
**Impact:** No data quality validation
**Fix:** Execute validation script after data loading

---

## 🟢 MEDIUM/LOW PRIORITY

### 9. Wizard B (Pattern Analysis) 🟢
**Documentation:** STEP 7 - Run `wizard_b_pattern_analyzer.py`
**Current:** No execution
**Impact:** No pattern analysis (optional feature)
**Fix:** Optional endpoint for pattern analysis

---

### 10. Account ID Mapping Validation 🟢
**Documentation:** Account IDs must follow formula: `10000 + customer_id * 1000`
**Current:** No validation in complete endpoint
**Impact:** Potential ID conflicts
**Fix:** Validate account IDs match expected range

---

## 📊 Complete Missing Flow

### What Should Happen (Per Documentation):

```
1. Admin provisions customer (manual OR via API)
   └─ provision_dc_customer.py creates customer{N}-dc2_s/

2. Customer completes wizard
   └─ Collects: company, pillars, events, criteria, sources, **team**
   └─ Uploads files (CSV or Excel)

3. POST /api/onboarding/complete
   ├─ Creates Customer/User/Config in DB
   ├─ **CALLS:** provision_dc_customer.py (if not done)
   ├─ **SAVES:** Files to customer{N}-dc2_s/data/
   └─ **PROCESSES:** Files (CSV direct or Excel pipeline)

4. POST /api/onboarding/process-data (NEW)
   ├─ **EXECUTES:** 02_load_customer{N}_data_SMART.py
   ├─ **EXECUTES:** 03_embed_customer{N}_OPENAI.py
   ├─ **EXECUTES:** 04_validate_data_integrity.py
   └─ **EXECUTES:** wizard_a_journey_generator.py

5. Dynamic API Registration (NEW)
   └─ **REGISTERS:** customer{N}_journey_api.py blueprint

6. Customer logs in
   └─ Sees dashboard with journey data
```

---

## 🔧 Required Implementation

### New/Updated Endpoints:

1. **UPDATE:** `POST /api/onboarding/complete`
   - Add provisioning call
   - Add file saving to directory
   - Add team member creation

2. **UPDATE:** `POST /api/onboarding/upload`
   - Save files to `customer{N}-dc2_s/data/`
   - Keep DB upload for immediate access

3. **NEW:** `POST /api/onboarding/process-data`
   - Execute all scripts in sequence
   - Return progress/status

4. **NEW:** `GET /api/onboarding/processing-status`
   - Check script execution status
   - Return progress for each step

5. **NEW:** `POST /api/onboarding/register-journey-api`
   - Dynamically register journey API blueprint
   - Or auto-register in process-data endpoint

---

## 📋 Implementation Checklist

### Phase 1: Critical (Must Have)
- [ ] Add provisioning call to complete endpoint
- [ ] Update upload endpoint to save files to directory
- [ ] Create process-data endpoint
- [ ] Add script execution helpers (subprocess)
- [ ] Add error handling and rollback

### Phase 2: High Priority
- [ ] Integrate Step7Team into wizard
- [ ] Create User records for team members
- [ ] Add data validation script execution
- [ ] Add dynamic journey API registration

### Phase 3: Nice to Have
- [ ] Add Wizard B execution (optional)
- [ ] Add account ID validation
- [ ] Add progress tracking UI
- [ ] Add retry mechanism for failed scripts

---

## 🎯 Summary

### Total Gaps Identified: **10**

| Priority | Count | Items |
|----------|-------|-------|
| 🔴 **CRITICAL** | 5 | Provisioning, File Storage, Data Loading, Embeddings, Journey Gen |
| 🟡 **HIGH** | 3 | Team Data, Journey API Registration, Validation |
| 🟢 **MEDIUM/LOW** | 2 | Wizard B, Account ID Validation |

### Endpoints Status:
- ✅ **5 endpoints** implemented (complete, upload, status, validate, validate-excel)
- ❌ **3 endpoints** missing (process-data, processing-status, register-journey-api)
- ⚠️ **2 endpoints** need updates (complete, upload)

---

**Status:** ⚠️ **CRITICAL GAPS IDENTIFIED - COMPREHENSIVE IMPLEMENTATION REQUIRED**

**Next Step:** Implement Phase 1 (Critical) gaps before UI testing
