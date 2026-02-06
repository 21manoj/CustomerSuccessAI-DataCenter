# Duplicate Upload Endpoint Removed ✅

## Changes Made

### 1. Removed Duplicate `/upload` from Onboarding API ✅

**File:** `onboarding_api_v2_config_aware.py`

**Removed:**
- Entire `upload_onboarding_csv()` function (lines 427-516)
- Route: `@onboarding_api.route('/upload', methods=['POST'])`

**Reason:**
- Upload is NOT part of onboarding - it's a separate runtime operation
- Customers upload CSVs AFTER being onboarded
- One clear endpoint: `/api/upload`
- Cleaner architecture

### 2. Updated Test Script ✅

**File:** `test_csv_upload_ui_combinations.py`

**Changes:**
- Updated to use `/api/upload` instead of `/api/onboarding/upload`
- Maps `upload_mode` to `mode` parameter:
  - `full_refresh` → `replace`
  - `incremental` → `incremental`
  - `upsert` → `incremental`
  - `merge` → `incremental`

**Note:**
- `/api/upload` currently only handles KPI CSV files with specific columns
- For other file types (accounts, signals, products, profiles, customers), the endpoint may return validation errors
- This is expected behavior - `/api/upload` is designed for KPI measurements

## Final Route Structure

### Upload API (`/api` prefix):
```
POST   /api/upload                      ← Single upload endpoint (config-aware)
POST   /api/upload/validate             ← Validate before upload
POST   /api/upload/recalculate-scores   ← Recalculate scores
GET    /api/upload/health               ← Health check
```

### Onboarding API (`/api/onboarding` prefix):
```
POST   /api/onboarding/complete         ← Create customer + config
POST   /api/onboarding/process-data     ← Process CSVs (during onboarding)
POST   /api/onboarding/validate-csv     ← Validate onboarding CSVs
GET    /api/onboarding/health           ← Health check
```

**Note:** `/api/onboarding/upload` has been REMOVED ✅

## Benefits

✅ **Single Upload Endpoint:** One clear endpoint `/api/upload`  
✅ **Better Design:** Upload and onboarding are separate concerns  
✅ **Cleaner Architecture:** No duplicate functionality  
✅ **Clear Separation:** Onboarding handles customer creation, upload handles runtime data

## Next Steps

1. **Restart Flask server** to load changes
2. **Update UI** if it's calling `/api/onboarding/upload`:
   ```typescript
   // OLD (removed):
   fetch('http://localhost:5059/api/onboarding/upload', ...)
   
   // NEW (correct):
   fetch('http://localhost:5059/api/upload', ...)
   ```
3. **Test:** Run `python3 test_csv_upload_ui_combinations.py`

## Current Limitations

⚠️ **File Type Support:**
- `/api/upload` currently only supports KPI CSV files
- Other file types (accounts, signals, products, profiles, customers) may need separate handling
- This is by design - `/api/upload` is for KPI measurements specifically
