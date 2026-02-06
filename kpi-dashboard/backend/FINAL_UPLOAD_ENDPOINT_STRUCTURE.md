# Final Upload Endpoint Structure ✅

## Summary

✅ **Duplicate endpoint removed** - `/api/onboarding/upload` has been removed  
✅ **Single upload endpoint** - `/api/upload` is now the only upload endpoint  
✅ **Test script updated** - Now uses `/api/upload`  
✅ **Clean architecture** - Upload and onboarding are properly separated

## Final Route Structure

### Upload API (`/api` prefix):
```
POST   /api/upload                      ← Single upload endpoint (config-aware)
POST   /api/upload/recalculate-scores   ← Recalculate scores
POST   /api/upload/validate             ← Validate before upload
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

## Changes Made

### 1. Removed from `onboarding_api_v2_config_aware.py`:
- ❌ `@onboarding_api.route('/upload', methods=['POST'])`
- ❌ `def upload_onboarding_csv():` function (entire function removed)

### 2. Updated `test_csv_upload_ui_combinations.py`:
- ✅ Changed endpoint from `/api/onboarding/upload` to `/api/upload`
- ✅ Maps `upload_mode` to `mode` parameter:
  - `full_refresh` → `replace`
  - `incremental` → `incremental`
  - `upsert` → `incremental`
  - `merge` → `incremental`

## API Usage

### `/api/upload` Endpoint

**Request:**
```python
POST /api/upload
Content-Type: multipart/form-data

{
    "file": <CSV file>,
    "customer_id": 123,
    "mode": "incremental" | "replace"
}
```

**Response:**
```json
{
    "success": true,
    "mode": "incremental",
    "records_in_csv": 5400,
    "records_filtered": 3600,
    "records_processed": 1800,
    "enabled_kpis": 15,
    "csv_kpis": 35,
    "disabled_kpis": [...],
    "details": {
        "added": 1500,
        "updated": 300,
        "deleted": 0
    }
}
```

## Important Notes

⚠️ **File Type Support:**
- `/api/upload` currently only supports **KPI CSV files** with specific columns:
  - `account_id`, `kpi_code`, `measured_at`, `value`, `target`, `pillar`
- Other file types (accounts, signals, products, profiles, customers) may return validation errors
- This is by design - `/api/upload` is specifically for KPI measurements

⚠️ **Authentication:**
- `/api/upload` requires authentication (unlike the removed `/api/onboarding/upload` which was public)
- Test script includes authentication flow

## Next Steps

1. **Restart Flask server** to load changes
2. **Update UI** if it references `/api/onboarding/upload`:
   ```typescript
   // OLD (removed):
   fetch('/api/onboarding/upload', ...)
   
   // NEW (correct):
   fetch('/api/upload', ...)
   ```
3. **Test:** Run `python3 test_csv_upload_ui_combinations.py`

## Benefits

✅ **Single Source of Truth:** One clear upload endpoint  
✅ **Better Design:** Upload and onboarding are separate concerns  
✅ **Cleaner Architecture:** No duplicate functionality  
✅ **Config-Aware:** `/api/upload` respects CustomerConfig settings  
✅ **Clear Separation:** Onboarding handles customer creation, upload handles runtime data
