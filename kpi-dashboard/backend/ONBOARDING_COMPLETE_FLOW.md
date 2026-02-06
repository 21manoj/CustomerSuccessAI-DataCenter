# Complete Onboarding Flow - Missing Steps Identified
**Date:** January 19, 2026

## ❌ Missing Steps in Current Implementation

You're absolutely right! I was missing critical steps:

### Current Implementation (INCOMPLETE):
1. ✅ `POST /api/onboarding/complete` - Creates Customer/User/Config in DB
2. ✅ `POST /api/onboarding/upload` - Uploads CSV/Excel files to DB
3. ❌ **MISSING:** Provision customer directory structure
4. ❌ **MISSING:** Save CSV files to customer directory
5. ❌ **MISSING:** Run data loading script (`02_load_customer{N}_data_SMART.py`)
6. ❌ **MISSING:** Run embedding script (`03_embed_customer{N}_OPENAI.py`)
7. ❌ **MISSING:** Run journey generator (`wizard_a_journey_generator.py`)

---

## ✅ Complete Flow (As Per Documentation)

### STEP 1: Provision Customer Directory
**Script:** `provision_dc_customer.py`
**Action:** Creates `customer{N}-dc2_s/` directory structure from `_template/`

### STEP 2: Customer Completes Wizard
**Frontend:** OnboardingWizard.tsx
**Action:** Customer uploads CSV/Excel files

### STEP 3: Complete Onboarding
**Endpoint:** `POST /api/onboarding/complete`
**Actions:**
1. Creates Customer/User/Config in DB
2. **CALLS:** `provision_dc_customer.py` to create directory
3. **SAVES:** Uploaded files to `customer{N}-dc2_s/data/`
4. **RUNS:** `02_load_customer{N}_data_SMART.py` (loads CSV → PostgreSQL)
5. **RUNS:** `03_embed_customer{N}_OPENAI.py` (creates embeddings → Qdrant)
6. **RUNS:** `wizard_a_journey_generator.py` (creates journey JSON files)

### STEP 4: Data Loading (Automated in STEP 3)
- KPIs loaded to PostgreSQL ✅
- Embeddings created in Qdrant ✅

### STEP 5: Journey Generation (Automated in STEP 3)
- Journey JSON files created ✅
- Available for JourneyDashboardV3 ✅

---

## 🔧 Required Changes

### 1. Update `/api/onboarding/complete` to:
- Call `provision_dc_customer.py` programmatically
- Save uploaded CSV files to customer directory
- Execute data loading script
- Execute embedding script
- Execute journey generator script

### 2. New Endpoint: `/api/onboarding/process-files`
- Alternative: Separate endpoint to process files after upload
- Runs all scripts in sequence

### 3. File Storage:
- Save uploaded files to `customer{N}-dc2_s/data/` before processing
- Ensure files are accessible to loading scripts

---

## 📋 Implementation Plan

### Option A: All-in-One Complete Endpoint
**Pros:** Single API call, simpler frontend
**Cons:** Long-running operation, harder to debug

### Option B: Separate Processing Endpoint
**Pros:** Better error handling, can retry individual steps
**Cons:** Two API calls needed

### Option C: Background Job Queue
**Pros:** Non-blocking, better UX
**Cons:** More complex, requires job queue (Celery/Redis)

**Recommendation:** Option B (Separate endpoint) for now, can upgrade to Option C later.

---

## 🚀 Next Steps

1. **Add provisioning call** to `/api/onboarding/complete`
2. **Add file saving** to customer directory
3. **Add script execution** functions
4. **Create `/api/onboarding/process-files`** endpoint
5. **Add error handling** and progress tracking

---

**Status:** ⚠️ **MISSING CRITICAL STEPS - NEEDS IMPLEMENTATION**
