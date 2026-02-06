# Onboarding Wizard - Gap Analysis & Testing Checklist
**Date:** January 19, 2026  
**Reference:** CS_PULSE_DC2_S_STRUCTURE (1).md

---

## 🔍 Gap Analysis

### ✅ Implemented vs Documentation

| Requirement | Documentation | Implementation | Status |
|------------|---------------|----------------|--------|
| **STEP 3: Complete Endpoint** | Creates Customer, User, CustomerConfig, **Processes uploaded files** | Creates Customer, User, CustomerConfig, **Does NOT process files** | ⚠️ **GAP** |
| **File Upload** | Part of STEP 3 | Separate endpoint (`/api/onboarding/upload`) | ⚠️ **DESIGN DIFFERENCE** |
| **Excel Validation** | Not explicitly mentioned | Added `POST /api/onboarding/validate-excel` | ✅ **ENHANCEMENT** |
| **Pillar Weights** | Should be configurable | Implemented with defaults | ✅ **COMPLETE** |
| **Rankings → Weights** | Not explicitly mentioned | Implemented | ✅ **ENHANCEMENT** |

---

## ⚠️ Identified Gaps

### Gap 1: File Processing in Complete Endpoint
**Documentation Says:**
> STEP 3: POST /api/onboarding/complete
> - Processes uploaded files (CSV or Excel)

**Current Implementation:**
- `/api/onboarding/complete` only creates Customer/User/Config
- Files must be uploaded separately via `/api/onboarding/upload`

**Question:** Should files be processed during completion, or is separate upload acceptable?

**Options:**
1. **Keep Separate (Current):** Files uploaded before completion, completion just finalizes setup
2. **Process in Complete:** Complete endpoint processes any files uploaded during wizard
3. **Hybrid:** Complete endpoint can optionally process files if provided

---

## 📋 Endpoint Testing Checklist

### All Endpoints Ready for Testing

#### 1. POST /api/onboarding/complete ✅
**Purpose:** Create customer, user, and config records

**Test Cases:**
- [ ] Create new customer with all required fields
- [ ] Verify customer_id is returned
- [ ] Verify user_id is returned
- [ ] Verify CustomerConfig is created with pillar weights
- [ ] Test with custom pillar weights
- [ ] Test with default pillar weights
- [ ] Test duplicate email detection
- [ ] Test duplicate domain detection
- [ ] Test missing required fields (should fail)
- [ ] Test invalid email format (should fail)

**Request Body:**
```json
{
  "company_name": "Acme Corp",
  "company_email": "info@acme.com",
  "admin_name": "John Doe",
  "admin_email": "john@acme.com",
  "admin_password": "SecurePass123!",
  "phone": "+1-555-1234",
  "vertical": "dc2_s",
  "weights": {
    "P1_deployment_velocity": 0.10,
    "P2_operational_stability": 0.30,
    "P3_ai_workload_performance": 0.30,
    "P4_channel_partner_health": 0.05,
    "P5_expansion_revenue": 0.25
  }
}
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Onboarding completed successfully",
  "customer_id": 18,
  "user_id": 45,
  "customer_name": "Acme Corp",
  "admin_email": "john@acme.com"
}
```

---

#### 2. POST /api/onboarding/upload ✅
**Purpose:** Upload CSV or Excel files

**Test Cases:**
- [ ] Upload CSV file (accounts.csv)
- [ ] Upload CSV file (kpi_measurements.csv)
- [ ] Upload CSV file (qualitative_signals.csv)
- [ ] Upload CSV file (products.csv)
- [ ] Upload CSV file (profiles.csv)
- [ ] Upload Excel file (.xlsx) - should use full pipeline
- [ ] Upload Excel file (.xls) - should use full pipeline
- [ ] Test with invalid file type (should fail)
- [ ] Test with empty file (should fail)
- [ ] Test with malformed CSV (should fail)
- [ ] Verify data appears in PostgreSQL
- [ ] Verify Excel files trigger normalization pipeline
- [ ] Test authentication (should require customer_id)

**Request (FormData):**
```
file: <file>
file_type: accounts|kpis|signals|products|profiles
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Successfully uploaded accounts data",
  "file_type": "accounts",
  "table": "accounts",
  "rows_uploaded": 10,
  "total_rows": 10,
  "columns": 15
}
```

---

#### 3. GET /api/onboarding/upload-status ✅
**Purpose:** Check which files have been uploaded

**Test Cases:**
- [ ] Check status with no files uploaded
- [ ] Check status after uploading accounts.csv
- [ ] Check status after uploading all 5 CSV files
- [ ] Verify counts are accurate
- [ ] Test authentication (should require customer_id)

**Expected Response:**
```json
{
  "status": "success",
  "upload_status": {
    "accounts": { "uploaded": true, "count": 10 },
    "kpis": { "uploaded": true, "count": 150 },
    "signals": { "uploaded": false, "count": 0 },
    "products": { "uploaded": true, "count": 5 },
    "profiles": { "uploaded": true, "count": 10 }
  }
}
```

---

#### 4. POST /api/onboarding/validate ✅
**Purpose:** Validate CSV files before upload

**Test Cases:**
- [ ] Validate valid CSV file
- [ ] Validate CSV with missing required columns
- [ ] Validate CSV with invalid data types
- [ ] Validate CSV with duplicate account_ids
- [ ] Validate empty CSV (should fail)
- [ ] Validate malformed CSV (should fail)

**Request (FormData):**
```
file: <file>
file_type: accounts|kpis|signals|products|profiles
```

**Expected Response:**
```json
{
  "status": "success",
  "valid": true,
  "rows": 10,
  "columns": 15,
  "errors": [],
  "warnings": []
}
```

---

#### 5. POST /api/onboarding/validate-excel ✅
**Purpose:** Validate Excel file structure before upload

**Test Cases:**
- [ ] Validate Excel with all required sheets
- [ ] Validate Excel with missing required sheet (should fail)
- [ ] Validate Excel with missing optional sheet (should warn)
- [ ] Validate Excel with missing required columns (should fail)
- [ ] Validate Excel with correct structure (should pass)
- [ ] Test with .xlsx file
- [ ] Test with .xls file
- [ ] Test with invalid file type (should fail)

**Request (FormData):**
```
file: <excel_file>
```

**Expected Response:**
```json
{
  "status": "success",
  "valid": true,
  "issues": [],
  "warnings": ["Optional sheet 'Events' not found"],
  "sheet_info": {
    "Customer Profile": { "rows": 10, "columns": 15, "exists": true },
    "KPI Coverage Detail": { "rows": 50, "columns": 8, "exists": true }
  },
  "filename": "customer_data.xlsx"
}
```

---

## 🧪 End-to-End Testing Flow

### Test Scenario 1: Complete Onboarding with CSV Files
```
1. POST /api/onboarding/complete
   → Creates customer_id=18, user_id=45

2. POST /api/onboarding/upload (accounts.csv)
   → Uploads 10 accounts

3. POST /api/onboarding/upload (kpi_measurements.csv)
   → Uploads 150 KPI measurements

4. POST /api/onboarding/upload (qualitative_signals.csv)
   → Uploads 25 signals

5. POST /api/onboarding/upload (products.csv)
   → Uploads 5 products

6. POST /api/onboarding/upload (profiles.csv)
   → Uploads 10 profiles

7. GET /api/onboarding/upload-status
   → Verify all files uploaded

8. Verify in PostgreSQL:
   → SELECT * FROM accounts WHERE customer_id = 18;
   → SELECT * FROM kpi_measurements WHERE account_id IN (...);
```

### Test Scenario 2: Complete Onboarding with Excel File
```
1. POST /api/onboarding/validate-excel
   → Validate Excel structure

2. POST /api/onboarding/complete
   → Creates customer_id=18, user_id=45

3. POST /api/onboarding/upload (customer_data.xlsx)
   → Should trigger Excel import pipeline
   → Should normalize KPIs
   → Should create embeddings in Qdrant

4. GET /api/onboarding/upload-status
   → Verify data loaded

5. Verify in PostgreSQL:
   → Check accounts, kpi_measurements, etc.

6. Verify in Qdrant:
   → Check embeddings created
```

---

## 🔧 Missing Features / Gaps to Address

### Gap 1: File Processing in Complete Endpoint
**Decision Needed:** Should `/api/onboarding/complete` process files, or keep separate?

**Recommendation:** Keep separate for now (current design is cleaner), but document the flow clearly.

### Gap 2: Team Data Collection
**Current:** Using placeholder admin email/password
**Needed:** Collect from wizard Step 7 (Team) or add to Step 1

### Gap 3: Company Email Collection
**Current:** Generated from company name
**Needed:** Add to Step 1 (Business Context)

### Gap 4: Phone Number Collection
**Current:** Empty string
**Needed:** Add to Step 1 (Business Context)

---

## ✅ Ready for Testing

All endpoints are implemented and ready for testing:

1. ✅ `POST /api/onboarding/complete` - Creates customer/user/config
2. ✅ `POST /api/onboarding/upload` - Uploads CSV/Excel files
3. ✅ `GET /api/onboarding/upload-status` - Checks upload status
4. ✅ `POST /api/onboarding/validate` - Validates CSV files
5. ✅ `POST /api/onboarding/validate-excel` - Validates Excel files

**All endpoints are functional and ready for API testing before UI integration!**

---

## 📝 Testing Commands

### Test Complete Endpoint:
```bash
curl -X POST http://localhost:5000/api/onboarding/complete \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Corp",
    "company_email": "info@test.com",
    "admin_name": "Admin User",
    "admin_email": "admin@test.com",
    "admin_password": "Test123!",
    "vertical": "dc2_s"
  }'
```

### Test Upload Status:
```bash
curl -X GET http://localhost:5000/api/onboarding/upload-status \
  -H "X-Customer-ID: 18"
```

### Test Excel Validation:
```bash
curl -X POST http://localhost:5000/api/onboarding/validate-excel \
  -F "file=@customer_data.xlsx"
```

---

**Status:** ✅ **ALL ENDPOINTS READY FOR TESTING**
