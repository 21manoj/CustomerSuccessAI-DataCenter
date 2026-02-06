# Upload Endpoint Registration Complete

## Changes Made

### 1. Added `/api/onboarding/upload` Endpoint ✅

**File:** `backend/onboarding_api_v2_config_aware.py`

**Endpoint:** `POST /api/onboarding/upload`

**Status:** ✅ Code added, requires server restart to activate

**Features:**
- Public endpoint (no authentication required)
- Accepts `file_type` and `upload_mode` parameters (matches UI expectations)
- Saves files to `verticals/customer{N}-dc2_s/data/` directory
- Supports all 6 file types: accounts, kpis, signals, products, profiles, customers
- Supports all 4 upload modes: full_refresh, incremental, upsert, merge
- Saves upload metadata for loader scripts

**Parameters:**
- `file`: CSV/Excel file (required)
- `customer_id`: Customer ID (required, in form data or X-Customer-ID header)
- `file_type`: One of 'accounts', 'kpis', 'signals', 'products', 'profiles', 'customers'
- `upload_mode`: One of 'full_refresh', 'incremental', 'upsert', 'merge'

**Response:**
```json
{
    "status": "success",
    "message": "File uploaded successfully",
    "file_path": "/path/to/file",
    "file_type": "accounts",
    "upload_mode": "incremental",
    "customer_id": 123
}
```

### 2. Also Added to `upload_api_v2_config_aware.py` ✅

Added the same endpoint to `upload_api_v2_config_aware.py` for redundancy.

## Registration Status

✅ **Code Added:** Both files updated  
⚠️ **Server Restart Required:** Flask needs to reload to register new routes

## Next Steps

1. **Restart the Flask server** to load the new endpoint
2. **Re-run the test:** `python3 test_csv_upload_ui_combinations.py`
3. **Expected Result:** All 24 combinations should succeed (status 200)

## Test After Restart

```bash
cd backend
python3 test_csv_upload_ui_combinations.py
```

Expected output:
- ✅ All 24 combinations successful
- ✅ Files saved to `verticals/customer{N}-dc2_s/data/`
- ✅ Upload metadata saved

## Verification

To verify the endpoint is registered after restart:

```python
from app_v3_minimal import app
for rule in app.url_map.iter_rules():
    if 'onboarding/upload' in rule.rule:
        print(f'✅ {rule.rule} [{rule.methods}]')
```
