# Onboarding Wizard API Updates

## Summary

The onboarding wizard API has been updated to handle **ALL** database fields, fixing the previous limitations where only a few fields were updated and most data was stored in JSON metadata.

## What Was Fixed

### Previous Limitations (Old APIs)
- ❌ Only updated 4-5 fields on `accounts` table
- ❌ Stored most data in `profile_metadata` JSON (not queryable)
- ❌ Did NOT populate `account_profiles` table
- ❌ Did NOT handle `kpi_measurements`
- ❌ Did NOT handle `qualitative_signals`
- ❌ Did NOT handle `account_products`

### New Onboarding API (`/api/onboarding/*`)
- ✅ Populates **ALL** `accounts` table fields:
  - `account_status` = 'active'
  - `external_account_id` = account_id as string
  - `revenue` = final_arr (or initial_arr)
  - `region` = extracted from datacenter_location
  - `vertical` = 'DC2_S' (default)
  - `created_at`, `updated_at` = timestamps
- ✅ Populates **ALL** `account_profiles` table columns (121 fields)
- ✅ Populates `kpi_measurements` table (with proper date column mapping)
- ✅ Populates `qualitative_signals` table
- ✅ Populates `account_products` table
- ✅ Handles boolean/integer type conversions correctly
- ✅ All data in proper database columns (fully queryable)

## API Endpoints

### 1. Upload CSV File
**POST** `/api/onboarding/upload`

**Form Data:**
- `file`: CSV file
- `file_type`: One of `'accounts'`, `'kpis'`, `'signals'`, `'products'`, `'profiles'`

**Response:**
```json
{
  "status": "success",
  "message": "Successfully uploaded accounts data",
  "file_type": "accounts",
  "table": "accounts",
  "rows_uploaded": 10,
  "total_rows": 10,
  "columns": 20
}
```

### 2. Get Upload Status
**GET** `/api/onboarding/upload-status`

**Response:**
```json
{
  "status": "success",
  "upload_status": {
    "accounts": {"uploaded": true, "count": 10},
    "kpis": {"uploaded": true, "count": 3960},
    "signals": {"uploaded": true, "count": 217},
    "products": {"uploaded": true, "count": 18},
    "profiles": {"uploaded": true, "count": 10}
  }
}
```

### 3. Validate CSV File
**POST** `/api/onboarding/validate`

**Form Data:**
- `file`: CSV file
- `file_type`: One of `'accounts'`, `'kpis'`, `'signals'`, `'products'`, `'profiles'`

**Response:**
```json
{
  "status": "success",
  "valid": true,
  "rows": 10,
  "columns": 20,
  "errors": [],
  "warnings": []
}
```

## File Type Mappings

| File Type | Database Table | Description |
|-----------|---------------|-------------|
| `accounts` | `accounts` | Account list (required) |
| `kpis` | `kpi_measurements` | Historical KPI measurements |
| `signals` | `qualitative_signals` | Qualitative signals |
| `products` | `account_products` | Account-product associations |
| `profiles` | `account_profiles` | Detailed account profiles (121 columns) |

## Data Preparation

The API automatically handles:

1. **Accounts CSV:**
   - Sets `account_status` = 'active'
   - Sets `external_account_id` = account_id as string
   - Sets `revenue` = final_arr (or initial_arr)
   - Extracts `region` from datacenter_location
   - Sets `vertical` = 'DC2_S'
   - Sets `created_at`, `updated_at` timestamps

2. **Profiles CSV:**
   - Converts boolean columns (strategic_account, reference_customer, etc.)
   - Converts `co_marketing_opportunities` to integer (not boolean)

3. **KPIs CSV:**
   - Renames `date` → `measurement_month`
   - Converts `threshold_breached` to boolean

4. **Signals CSV:**
   - Converts `is_narrative_signal` to boolean

5. **Products CSV:**
   - Converts `primary_product` to boolean

## Updated APIs

### 1. `onboarding_api.py` (NEW)
- Comprehensive onboarding API with all field support
- Endpoints: `/api/onboarding/upload`, `/api/onboarding/upload-status`, `/api/onboarding/validate`

### 2. `corporate_api.py` (UPDATED)
- Now sets `account_status`, `external_account_id`, `vertical` when creating accounts

### 3. `upload_api.py` (UPDATED)
- Now sets `vertical` when creating accounts

## Usage Example

```python
import requests

# Upload accounts CSV
with open('accounts.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:5059/api/onboarding/upload',
        files={'file': f},
        data={'file_type': 'accounts'},
        headers={'X-Customer-ID': '17', 'X-User-ID': '1'}
    )
    print(response.json())

# Upload KPIs CSV
with open('kpis.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:5059/api/onboarding/upload',
        files={'file': f},
        data={'file_type': 'kpis'},
        headers={'X-Customer-ID': '17', 'X-User-ID': '1'}
    )
    print(response.json())

# Check upload status
response = requests.get(
    'http://localhost:5059/api/onboarding/upload-status',
    headers={'X-Customer-ID': '17'}
)
print(response.json())
```

## Frontend Integration

The onboarding wizard frontend should call these endpoints:

```typescript
// Upload file
const formData = new FormData();
formData.append('file', file);
formData.append('file_type', 'accounts'); // or 'kpis', 'signals', 'products', 'profiles'

const response = await fetch('/api/onboarding/upload', {
  method: 'POST',
  headers: {
    'X-Customer-ID': customerId,
    'X-User-ID': userId
  },
  body: formData
});

// Check status
const statusResponse = await fetch('/api/onboarding/upload-status', {
  headers: {
    'X-Customer-ID': customerId
  }
});
```

## Testing

All fields are now properly populated:
- ✅ `accounts` table: All 28 columns
- ✅ `account_profiles` table: All 121 columns
- ✅ `kpi_measurements` table: All columns
- ✅ `qualitative_signals` table: All columns
- ✅ `account_products` table: All columns

No data is stored in JSON metadata - everything goes to proper database columns for full queryability.
