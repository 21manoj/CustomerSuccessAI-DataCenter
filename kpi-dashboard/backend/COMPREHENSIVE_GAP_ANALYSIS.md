# Comprehensive Gap Analysis - Onboarding Wizard
**Date:** January 19, 2026  
**Reference:** CS_PULSE_DC2_S_STRUCTURE (1).md

---

## 📋 Documentation vs Implementation Comparison

### STEP 1: Provision Customer Directory
**Documentation (Line 227-230):**
```
STEP 1: Provision Customer Directory
$ python3 provision_dc_customer.py --customer-id 18
Creates: customer18-dc2_s/ from _template/
```

**Current Implementation:**
- ❌ **MISSING:** No provisioning call in `/api/onboarding/complete`
- ❌ **MISSING:** Directory structure not created automatically
- ✅ **EXISTS:** `provision_dc_customer.py` script exists and works

**Gap:** Need to call provisioning script programmatically after creating customer in DB

---

### STEP 2: Customer Completes Onboarding Wizard
**Documentation (Line 234-237):**
```
STEP 2: Customer Completes Onboarding Wizard (React)
- Company info, pillars, data sources, **team**
- Uploads data files (CSV or Excel)
```

**Current Implementation:**
- ✅ **EXISTS:** OnboardingWizard.tsx component
- ✅ **EXISTS:** Steps 1-6 implemented
- ⚠️ **PARTIAL:** Step 7 (Team) exists but not integrated into complete endpoint
- ✅ **EXISTS:** File upload functionality

**Gap:** Team data (Step7Team) not sent to `/api/onboarding/complete`

---

### STEP 3: POST /api/onboarding/complete
**Documentation (Line 241-246):**
```
STEP 3: POST /api/onboarding/complete
- Creates Customer record in DB
- Creates User record
- Saves CustomerConfig (pillars, weights, etc.)
- **Processes uploaded files (CSV or Excel)**
```

**Current Implementation:**
- ✅ **EXISTS:** Creates Customer/User/Config
- ❌ **MISSING:** Does NOT process uploaded files
- ❌ **MISSING:** Does NOT call provisioning script
- ❌ **MISSING:** Does NOT save files to customer directory

**Gap:** Complete endpoint should:
1. Call `provision_dc_customer.py` after creating customer
2. Save uploaded files to `customer{N}-dc2_s/data/`
3. Process files (CSV direct or Excel pipeline)

---

### STEP 4: Data Loading
**Documentation (Line 267-271):**
```
STEP 4: Data Loading
- KPIs loaded to PostgreSQL
- Embeddings created in Qdrant
- Health scores calculated
```

**Documentation Commands (Line 565-578):**
```bash
# STEP 3: Load data to database
cd customer18-dc2_s/scripts
python3 02_load_customer18_data_SMART.py

# STEP 4: Create embeddings
python3 03_embed_customer18_OPENAI.py

# STEP 5: Validate data
python3 04_validate_data_integrity.py
```

**Current Implementation:**
- ❌ **MISSING:** No script execution for `02_load_customer{N}_data_SMART.py`
- ❌ **MISSING:** No script execution for `03_embed_customer{N}_OPENAI.py`
- ❌ **MISSING:** No script execution for `04_validate_data_integrity.py`
- ✅ **EXISTS:** Scripts exist in customer directories

**Gap:** Need endpoint to execute these scripts programmatically

---

### STEP 5: Journey Generation (Wizard A)
**Documentation (Line 274-278):**
```
STEP 5: Journey Generation (Wizard A)
- Creates account_*_journey.json
- Creates milestones, events
```

**Documentation Commands (Line 580-584):**
```bash
# STEP 6: Generate journey data (Wizard A)
cd ../journey/wizard_a
python3 wizard_a_journey_generator.py
```

**Current Implementation:**
- ❌ **MISSING:** No script execution for `wizard_a_journey_generator.py`
- ✅ **EXISTS:** Script exists in `customer{N}-dc2_s/journey/wizard_a/`
- ✅ **EXISTS:** Journey API adapter exists (`customer{N}_journey_api.py`)

**Gap:** Need to execute journey generator script after data loading

---

### STEP 6: Customer Logs In
**Documentation (Line 281-286):**
```
STEP 6: Customer Logs In
- Sees DC2_S Dashboard
- Journey Visualizer available
- Signal Analyst available
```

**Current Implementation:**
- ✅ **EXISTS:** Dashboard_dc.tsx
- ✅ **EXISTS:** JourneyDashboardV3.tsx
- ✅ **EXISTS:** SignalAnalyst.tsx
- ✅ **EXISTS:** Journey API endpoints

**Gap:** None - this is the end result

---

## 🔍 Additional Missing Pieces

### 1. File Storage Location
**Documentation (Line 114-119):**
```
customer18-dc2_s/
├── 📂 data/                            # ⭐ INPUT DATA (5 CSV files required)
│   ├── accounts.csv
│   ├── kpi_measurements.csv
│   ├── qualitative_signals.csv
│   ├── products.csv
│   └── profiles.csv
```

**Current Implementation:**
- ❌ **MISSING:** Files uploaded via API go directly to DB, NOT to `customer{N}-dc2_s/data/`
- ❌ **MISSING:** Loading scripts expect files in `data/` directory

**Gap:** Upload endpoint should save files to customer directory

---

### 2. Team Data Collection
**Documentation (Line 235):**
```
- Company info, pillars, data sources, **team**
```

**Current Implementation:**
- ✅ **EXISTS:** `Step7Team.tsx` component exists
- ❌ **MISSING:** Team data not sent to `/api/onboarding/complete`
- ❌ **MISSING:** Team members not created as User records

**Gap:** Need to:
1. Collect team data in wizard
2. Send to complete endpoint
3. Create User records for each team member

---

### 3. Excel File Processing Flow
**Documentation (Line 252-262):**
```
Excel (.xlsx/.xls)
  ExcelImportService (parse sheets)
         ↓
  ImportIntegrationAdapter (map to schema)
         ↓
  KPINormalizationService (raw → 0-100)
         ↓
  PostgreSQL + Qdrant
```

**Current Implementation:**
- ✅ **EXISTS:** Excel import services loaded from `_template/services/`
- ✅ **EXISTS:** `handle_excel_upload()` function
- ❌ **MISSING:** Excel files not saved to `customer{N}-dc2_s/data/`
- ⚠️ **PARTIAL:** Excel pipeline works but files need to be in directory for scripts

**Gap:** Excel files should be saved to directory AND processed through pipeline

---

### 4. Data Validation Step
**Documentation (Line 575-578):**
```bash
# STEP 5: Validate data
python3 04_validate_data_integrity.py
```

**Current Implementation:**
- ❌ **MISSING:** No execution of validation script
- ✅ **EXISTS:** Script exists in customer directories

**Gap:** Should execute validation script after data loading

---

### 5. Wizard B (Pattern Analysis)
**Documentation (Line 586-590):**
```bash
# STEP 7: Run pattern analysis (Wizard B)
cd ../wizard_b
python3 wizard_b_pattern_analyzer.py
```

**Current Implementation:**
- ❌ **MISSING:** No execution of Wizard B script
- ✅ **EXISTS:** Script exists in customer directories

**Gap:** Optional but should be available

---

## 📊 Complete Missing Items Summary

| Step | Component | Status | Priority |
|------|-----------|--------|----------|
| **1** | Provision directory | ❌ Missing | 🔴 **CRITICAL** |
| **2** | Save files to directory | ❌ Missing | 🔴 **CRITICAL** |
| **3** | Team data collection | ⚠️ Partial | 🟡 **HIGH** |
| **4** | Execute data loading script | ❌ Missing | 🔴 **CRITICAL** |
| **5** | Execute embedding script | ❌ Missing | 🔴 **CRITICAL** |
| **6** | Execute journey generator | ❌ Missing | 🔴 **CRITICAL** |
| **7** | Execute validation script | ❌ Missing | 🟡 **MEDIUM** |
| **8** | Execute Wizard B (optional) | ❌ Missing | 🟢 **LOW** |

---

## 🎯 Required Endpoints

### Current Endpoints (✅ Implemented):
1. `POST /api/onboarding/complete` - Creates customer/user/config
2. `POST /api/onboarding/upload` - Uploads files to DB
3. `GET /api/onboarding/upload-status` - Checks upload status
4. `POST /api/onboarding/validate` - Validates CSV
5. `POST /api/onboarding/validate-excel` - Validates Excel

### Missing Endpoints (❌ Need Implementation):
1. `POST /api/onboarding/provision` - Provisions customer directory
2. `POST /api/onboarding/process-data` - Executes all scripts
3. `GET /api/onboarding/processing-status` - Checks script execution status

---

## 🔧 Implementation Plan

### Phase 1: Critical Gaps (Must Have)
1. **Add provisioning to complete endpoint**
   - Call `provision_dc_customer.py` after creating customer
   - Use subprocess or import function directly

2. **Update upload endpoint**
   - Save files to `customer{N}-dc2_s/data/` directory
   - Keep DB upload for immediate access
   - Ensure files are accessible to scripts

3. **Create process-data endpoint**
   - Execute `02_load_customer{N}_data_SMART.py`
   - Execute `03_embed_customer{N}_OPENAI.py`
   - Execute `wizard_a_journey_generator.py`
   - Return status/progress

### Phase 2: High Priority
4. **Integrate team data**
   - Collect from Step7Team in wizard
   - Send to complete endpoint
   - Create User records for team members

5. **Add validation step**
   - Execute `04_validate_data_integrity.py`
   - Return validation results

### Phase 3: Nice to Have
6. **Add Wizard B execution**
   - Optional pattern analysis
   - Can be triggered separately

---

## 📝 Key Questions

1. **Provisioning Timing:**
   - Should provisioning happen in `/api/onboarding/complete`?
   - Or should it be a separate endpoint called first?

2. **File Storage:**
   - Should files be saved to directory AND uploaded to DB?
   - Or just to directory (scripts handle DB)?

3. **Script Execution:**
   - Synchronous (blocking) or asynchronous (background jobs)?
   - How to handle long-running operations?

4. **Error Handling:**
   - What happens if provisioning fails?
   - What happens if script execution fails?
   - How to rollback partial operations?

---

**Status:** ⚠️ **CRITICAL GAPS IDENTIFIED - NEEDS COMPREHENSIVE IMPLEMENTATION**
