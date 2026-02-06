# Missing Steps in Onboarding Flow
**Date:** January 19, 2026

## ❌ What I Was Missing

You're absolutely correct! I was missing these critical steps:

### 1. **Provisioning Customer Directory** ❌
- After creating customer in DB, need to call `provision_dc_customer.py`
- Creates `customer{N}-dc2_s/` directory structure
- Sets up scripts, services, journey directories

### 2. **Saving CSV Files to Customer Directory** ❌
- Uploaded files need to be saved to `customer{N}-dc2_s/data/`
- Files must be accessible to loading scripts
- Currently files go directly to DB, but scripts expect them in `data/` folder

### 3. **Running Data Loading Script** ❌
- Need to execute `02_load_customer{N}_data_SMART.py`
- Loads CSV files from `data/` → PostgreSQL
- Script expects files in `customer{N}-dc2_s/data/`

### 4. **Running Embedding Script** ❌
- Need to execute `03_embed_customer{N}_OPENAI.py`
- Creates embeddings in Qdrant
- Reads from PostgreSQL, writes to Qdrant

### 5. **Running Journey Generator** ❌
- Need to execute `wizard_a_journey_generator.py`
- Creates journey JSON files
- Generates `account_*_journey.json` files in `wizard_a/test_run_*/`

---

## ✅ Complete Flow (What Should Happen)

```
1. POST /api/onboarding/complete
   ├─ Creates Customer/User/Config in DB
   ├─ Calls provision_dc_customer.py (creates directory)
   └─ Returns customer_id

2. POST /api/onboarding/upload (for each file)
   ├─ Saves file to customer{N}-dc2_s/data/
   └─ Optionally: Also uploads to DB directly

3. POST /api/onboarding/process-data (NEW ENDPOINT)
   ├─ Runs 02_load_customer{N}_data_SMART.py
   ├─ Runs 03_embed_customer{N}_OPENAI.py
   └─ Runs wizard_a_journey_generator.py

4. GET /api/onboarding/status
   └─ Returns processing status
```

---

## 🔧 Implementation Required

### Option 1: All-in-One Complete Endpoint
- Complete endpoint does everything
- Pros: Simple
- Cons: Long-running, hard to debug

### Option 2: Separate Processing Endpoint (RECOMMENDED)
- Complete → creates customer + provisions directory
- Upload → saves files to directory
- Process → runs all scripts
- Pros: Better error handling, can retry
- Cons: Multiple API calls

### Option 3: Background Jobs
- Use Celery/Redis for async processing
- Pros: Non-blocking, better UX
- Cons: More complex setup

---

## 📋 Next Steps

1. **Add provisioning call** to `/api/onboarding/complete`
2. **Update upload endpoint** to save files to customer directory
3. **Create `/api/onboarding/process-data`** endpoint
4. **Add script execution helpers** (subprocess calls)
5. **Add error handling** and progress tracking

---

**Status:** ⚠️ **NEEDS IMPLEMENTATION - CRITICAL GAPS IDENTIFIED**
