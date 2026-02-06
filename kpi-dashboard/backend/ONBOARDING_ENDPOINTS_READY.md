# Onboarding Endpoints - Ready for Testing
**Date:** January 19, 2026  
**Status:** ✅ **ALL ENDPOINTS IMPLEMENTED**

---

## ✅ Complete Endpoint List

### 1. POST /api/onboarding/provision ✅
**Purpose:** Provision customer directory structure  
**Timing:** Separate endpoint (called before or after complete)  
**Implementation:** Calls `provision_dc_customer.py` programmatically

### 2. POST /api/onboarding/complete ✅
**Purpose:** Create customer, user, config, and team members  
**Features:**
- Creates Customer/User/Config in DB
- Creates team member Users (if provided)
- Normalizes pillar weights
- Rollback on error

### 3. POST /api/onboarding/upload ✅
**Purpose:** Save files to customer directory  
**Behavior:** Files saved ONLY to directory (scripts handle DB)  
**Location:** `customer{N}-dc2_s/data/`

### 4. POST /api/onboarding/process-data ✅
**Purpose:** Execute all scripts synchronously  
**Scripts Executed:**
1. `02_load_customer{N}_data_SMART.py` (CSV → PostgreSQL)
2. `03_embed_customer{N}_OPENAI.py` (PostgreSQL → Qdrant)
3. `04_validate_data_integrity.py` (validation)
4. `wizard_a_journey_generator.py` (journey JSON files)
5. `wizard_b_pattern_analyzer.py` (optional)

**Features:**
- Synchronous execution (blocking)
- Rollback on failure
- Error tracking

### 5. GET /api/onboarding/processing-status ✅
**Purpose:** Check script execution status

### 6. POST /api/onboarding/register-journey-api ✅
**Purpose:** Dynamically register journey API blueprint

### 7. GET /api/onboarding/upload-status ✅
**Purpose:** Check which files are in customer directory  
**Updated:** Now checks directory files, not database

### 8. POST /api/onboarding/validate-excel ✅
**Purpose:** Validate Excel file structure

### 9. POST /api/onboarding/validate ✅
**Purpose:** Validate CSV files

---

## 🔄 Recommended Flow

```
1. POST /api/onboarding/provision
   → Creates customer18-dc2_s/

2. POST /api/onboarding/complete
   → Creates Customer/User/Config + Team

3. POST /api/onboarding/upload (×5 files)
   → Saves to customer18-dc2_s/data/

4. POST /api/onboarding/process-data
   → Executes all scripts synchronously

5. POST /api/onboarding/register-journey-api
   → Registers journey API blueprint

6. GET /api/onboarding/processing-status
   → Verify everything completed
```

---

## ✅ All Requirements Met

1. ✅ **Separate provisioning endpoint** - `/api/onboarding/provision`
2. ✅ **Files saved to directory only** - No DB upload in upload endpoint
3. ✅ **Synchronous script execution** - All scripts run in sequence
4. ✅ **Rollback support** - Tracks and logs rollback actions
5. ✅ **Team data integration** - Complete endpoint creates team Users
6. ✅ **Journey API registration** - Dynamic blueprint registration
7. ✅ **Validation script** - Executed in process-data endpoint

---

**Status:** ✅ **ALL ENDPOINTS READY FOR API TESTING**
