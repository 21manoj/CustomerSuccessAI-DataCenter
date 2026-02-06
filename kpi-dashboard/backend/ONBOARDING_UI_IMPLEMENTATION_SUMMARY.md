# Onboarding Wizard UI Implementation Summary

## ✅ Implementation Complete

All changes have been implemented based on your requirements. Here's what was done:

---

## 1. Backend API Endpoints Added

### ✅ `GET /api/onboarding/next-customer-id`
- Returns next available customer ID
- Returns account ID range for that customer
- Used to auto-populate customer_id field

### ✅ `GET /api/onboarding/validate-customer-id/<id>`
- Validates if customer ID exists
- Returns suggested ID if exists
- Returns account ID range if available
- Used for real-time validation in UI

### ✅ Updated `POST /api/onboarding/generate-sample-files`
- Now accepts: `customer_id`, `industry`, `company_name`
- Validates customer_id before generation
- Passes parameters to `generate_synthetic_customer_data.py`
- Fixed `num_months` to 12 (was 6)

---

## 2. Backend Generator Updates

### ✅ `generate_synthetic_customer_data.py`
**Updated Functions:**
- `generate_accounts()` - Now accepts `industry` and `company_name` parameters
  - Uses `industry` for all accounts (no randomness)
  - Uses `company_name` to create account name variations (e.g., "Acme Healthcare - Datacenter East")
- `generate_customers_csv()` - Now accepts `company_name` and `industry`
  - Uses `company_name` in customer_name field
  - Generates domain from company_name
- `generate_demo_manifest()` - Now accepts `company_name`
  - Includes company name in manifest header
  - Shows industry in manifest description

**Key Changes:**
- All accounts use the same industry (from user selection)
- Account names derived from company_name with variations
- DEMO_MANIFEST.md includes company context

---

## 3. Frontend UI Updates (Step5Sources.tsx)

### ✅ New State Variables
- `customerId` - Current customer ID value
- `suggestedCustomerId` - System-suggested ID
- `customerIdError` - Validation error message
- `showConfirmation` - Confirmation dialog state
- `accountIdRange` - Calculated account ID range
- `validatingCustomerId` - Loading state for validation

### ✅ New Features

**1. Sample Data Configuration Section**
- Read-only fields:
  - Company Name (from Step 1)
  - Industry (from Step 1)
  - Vertical: "DC2_S (Data Center)" (read-only)
  - Time Period: "12 months (fixed)" (read-only)
  - Number of Accounts: "10 accounts" (read-only)
- Editable field:
  - Customer ID (with validation)
  - Shows account ID range when valid
  - Shows suggested ID if current ID exists

**2. Customer ID Validation**
- Auto-fetches next available ID on mount
- Real-time validation (debounced 500ms)
- Shows error if ID exists with "Use Suggested ID" button
- Shows account ID range when valid

**3. Confirmation Dialog**
- Shows before generation:
  - Company name
  - Industry
  - Customer ID
  - Account ID range
  - Number of accounts
  - Time period
  - Note about default weights

**4. Updated API Call**
- Sends: `customer_id`, `industry`, `company_name`
- Fixed: `num_months: 12` (was 6)
- Fixed: `vertical: 'dc2_s'` (was dynamic)

---

## 4. CustomerConfig with Default Weights

### ✅ Already Implemented
The `complete_onboarding` endpoint already:
- Uses `get_default_pillar_weights('dc2_s')` for DC2_S vertical
- Saves default weights to `CustomerConfig.category_weights`:
  ```json
  {
    "P1_deployment_velocity": 0.15,
    "P2_operational_stability": 0.20,
    "P3_ai_workload_performance": 0.25,
    "P4_channel_partner_health": 0.15,
    "P5_expansion_readiness": 0.25
  }
  ```
- Normalizes weights to sum to 1.0
- Creates/updates CustomerConfig during onboarding completion

**Note:** KPI-level weights (L1) are loaded from `bootstrap_weights_config.json` files in customer directories, not stored in CustomerConfig. This is handled by the bootstrap weights loader system.

---

## 5. Demo Manifest and Journeys

### ✅ Preplanned Journeys (Health Scenarios)
The `generate_synthetic_customer_data.py` includes 8 predefined health scenarios:

1. **improving**: Critical → At-Risk → Healthy (55 → 88)
2. **declining**: Healthy → At-Risk → Critical (90 → 60)
3. **stable_healthy**: Consistently Healthy (88 → 92)
4. **stable_at_risk**: Persistently At-Risk (68 → 72)
5. **volatile**: Unpredictable swings
6. **plateau_breakthrough**: Plateau → Breakthrough (70 → 86)
7. **high_churn_risk**: Critical with declining engagement (58 → 45)
8. **new_onboarding**: Recently onboarded, improving (62 → 82)

**Assignment:** Accounts are assigned scenarios cyclically (Account 1 = improving, Account 2 = declining, etc.)

**DEMO_MANIFEST.md** includes:
- Quick reference for which account to use for each demo scenario
- Demo flow instructions
- Health score legend
- KPI structure (5 pillars)

---

## 6. Wizard A and Wizard B Integration

### ✅ Background Processing
- Wizard A runs automatically after data is loaded into database
- Wizard B runs after Wizard A completes
- Both run in background (not shown in UI)
- Results appear in:
  - Executive Dashboard (Wizard B insights)
  - Journey View (Wizard A narratives)
  - AI Insights Tab (Wizard B patterns)

**Implementation Note:** The onboarding wizard doesn't show Wizard A/B status. They run automatically after CSV upload and data loading completes.

---

## 7. Account ID Formula

### ✅ Formula Implementation
```
account_id_start = 10000 + customer_id * 1000
account_ids = range(account_id_start + 1, account_id_start + num_accounts + 1)
```

**Examples:**
- Customer 18 → Accounts 28001-28010
- Customer 19 → Accounts 29001-29010
- Customer 20 → Accounts 30001-30010

**UI Shows:** Account ID range updates automatically when customer_id changes

---

## 8. Industry Usage

### ✅ Implementation
- **All accounts use the same industry** (from Step 1 selection)
- No randomness in industry assignment
- Industry appears in:
  - `accounts.csv` (all accounts)
  - `customers.csv` (customer record)
  - `DEMO_MANIFEST.md` (description)

**Future Enhancement:** Industry-specific KPI ranges (Phase 2)

---

## 9. Company Name Usage

### ✅ Implementation
- **In `customers.csv`:**
  - `customer_name` = company_name
  - `domain` = generated from company_name (lowercase, hyphenated)

- **In `accounts.csv`:**
  - Account names = `"{company_name} - {suffix}"`
  - Suffixes: "Datacenter East", "Cloud Ops", "AI Lab", etc.

- **In `DEMO_MANIFEST.md`:**
  - Header: `"# Demo Data for {company_name}"`
  - Description includes company name

- **In Customer Record:**
  - `customer_name` = company_name (when customer is created)

---

## Files Modified

### Backend:
1. ✅ `backend/onboarding_api.py`
   - Added `GET /api/onboarding/next-customer-id`
   - Added `GET /api/onboarding/validate-customer-id/<id>`
   - Updated `POST /api/onboarding/generate-sample-files`
   - CustomerConfig already saves default weights (no changes needed)

2. ✅ `backend/generate_synthetic_customer_data.py`
   - Updated `generate_accounts()` to accept `industry`, `company_name`
   - Updated `generate_customers_csv()` to accept `company_name`, `industry`
   - Updated `generate_demo_manifest()` to accept `company_name`
   - Updated `main()` to pass parameters

### Frontend:
3. ✅ `src/components/onboarding/Step5Sources.tsx`
   - Added state management for customer_id validation
   - Added Sample Data Configuration section
   - Added read-only fields display
   - Added customer_id input with validation
   - Added confirmation dialog
   - Updated API call with new parameters
   - Added useEffect for debounced validation

---

## Testing Checklist

- [ ] Test customer ID auto-generation (should fetch next available)
- [ ] Test customer ID validation (existing ID should show error)
- [ ] Test customer ID override (should recalculate account IDs)
- [ ] Test industry usage (all accounts should have same industry)
- [ ] Test company name usage (should appear in customers.csv and account names)
- [ ] Test confirmation dialog (should show before generation)
- [ ] Test file generation (should include DEMO_MANIFEST.md)
- [ ] Test ZIP download (should contain all 6 CSV files + manifest)
- [ ] Test account ID range calculation (should match formula)

---

## Next Steps

1. **Test the implementation** with a real onboarding flow
2. **Verify** that generated files match expected format
3. **Check** that CustomerConfig is created with default weights
4. **Confirm** that Wizard A/B run automatically after data upload

---

## Summary

✅ All requirements implemented:
- ✅ Read-only fields (company, industry, vertical, time period)
- ✅ Customer ID with validation and override
- ✅ Industry used for all accounts
- ✅ Company name in generated files
- ✅ Default weights saved to CustomerConfig
- ✅ Demo manifest with preplanned journeys
- ✅ Confirmation dialog before generation
- ✅ Account ID formula implementation

The onboarding wizard is now fully aligned with `provision_dc_customer.py` and `generate_synthetic_customer_data.py`! 🎉
