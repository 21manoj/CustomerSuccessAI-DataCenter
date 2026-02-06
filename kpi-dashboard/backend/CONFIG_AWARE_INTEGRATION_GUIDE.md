# Config-Aware CSV Upload System - Integration Guide

## 📋 Overview

Complete guide to integrating config-aware CSV upload functionality into your existing system.

### What You're Getting

✅ **Config-Aware Data Loader** - Template script that respects CustomerConfig  
✅ **Updated Onboarding API** - Validates CSVs against config before processing  
✅ **Updated Upload API** - Runtime uploads with config filtering  
✅ **Migration Script** - Updates existing customer loaders  
✅ **V3 Test** - Generates config-aware test data  

---

## 📦 Files Provided

### 1. **02_load_customer_data_SMART_V2_CONFIG_AWARE.py**
   - Template for config-aware data loaders
   - Filters KPIs based on CustomerConfig
   - Use for all new customers

### 2. **onboarding_api_v2_config_aware.py**
   - Updated onboarding API with validation
   - Checks CSVs against config before loading
   - Provides warnings for disabled KPIs

### 3. **upload_api_v2_config_aware.py**
   - Runtime upload API with config filtering
   - Supports incremental and replace modes
   - Auto-filters disabled KPIs

### 4. **migrate_loaders_to_config_aware.py**
   - Migration script for existing customers
   - Backs up original loaders
   - Creates config-aware versions

### 5. **test_onboarding_complete_e2e_api_v3.py**
   - Test script that generates config-aware CSVs
   - Tests complete upload flow
   - Validates config integration

### 6. **generate_csv_from_config.py**
   - Helper module for CSV generation
   - Reads CustomerConfig to determine KPIs
   - Reusable across tests

---

## 🚀 Quick Start

### Step 1: Copy Files to Backend

```bash
cd /path/to/backend

# Copy core files
cp 02_load_customer_data_SMART_V2_CONFIG_AWARE.py scripts/
cp onboarding_api_v2_config_aware.py .
cp upload_api_v2_config_aware.py .
cp migrate_loaders_to_config_aware.py scripts/

# Copy test files
cp test_onboarding_complete_e2e_api_v3.py .
cp generate_csv_from_config.py .
```

### Step 2: Register New APIs

```bash
# Edit app_v3_minimal.py

# Add imports (replace old versions if they exist)
from onboarding_api_v2_config_aware import onboarding_api
from upload_api_v2_config_aware import upload_api

# Register blueprints
app.register_blueprint(onboarding_api)
app.register_blueprint(upload_api)

print("✅ Registered Config-Aware APIs")
```

### Step 3: Migrate Existing Customer Loaders

```bash
cd backend

# Dry run first (see what will change)
python3 scripts/migrate_loaders_to_config_aware.py --dry-run

# Migrate all customers
python3 scripts/migrate_loaders_to_config_aware.py

# Or migrate specific customer
python3 scripts/migrate_loaders_to_config_aware.py --customer-id 9
```

### Step 4: Test

```bash
# Test V3 CSV generation
python3 test_onboarding_complete_e2e_api_v3.py

# Test a migrated loader
python3 verticals/customer9-dc2_s/scripts/02_load_customer9_data_SMART.py
```

---

## 📊 How It Works

### Flow 1: Initial Onboarding

```
┌─────────────────────────────────────────────────────────────┐
│ 1. POST /api/onboarding/complete                            │
│    • Creates Customer                                       │
│    • Creates CustomerConfig (15 default enabled KPIs)       │
│    • Creates 3 sample accounts                              │
│    • Calls generate_synthetic_dc2s_data.py                  │
│      (reads CustomerConfig, generates only enabled KPIs)    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CSVs Generated                                            │
│    • Location: verticals/customer{ID}-dc2_s/data/           │
│    • kpi_measurements.csv contains ONLY enabled KPIs        │
│    • Config-aware from the start                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. POST /api/onboarding/process-data                        │
│    • Validates CSV against CustomerConfig                   │
│    • Executes 02_load_customer{ID}_data_SMART.py           │
│      (V2 version filters any disabled KPIs)                 │
│    • Loads to database                                      │
└─────────────────────────────────────────────────────────────┘
```

### Flow 2: Runtime Incremental Upload

```
┌─────────────────────────────────────────────────────────────┐
│ Customer uploads new month's KPI data                        │
│ POST /api/upload                                             │
│ - file: december_kpis.csv                                    │
│ - customer_id: 123                                           │
│ - mode: incremental                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ upload_api_v2_config_aware.py                                │
│ 1. Reads CustomerConfig                                      │
│ 2. Gets enabled KPIs (e.g., 15 KPIs)                        │
│ 3. Filters CSV to only enabled KPIs                         │
│ 4. For each record:                                          │
│    - If exists: UPDATE                                       │
│    - If not exists: INSERT                                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Response                                                      │
│ {                                                             │
│   "records_in_csv": 500,        // Total uploaded           │
│   "records_filtered": 150,      // Disabled KPIs removed    │
│   "records_processed": 350,     // Actually loaded           │
│   "disabled_kpis": [...]        // Which KPIs were filtered │
│ }                                                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ POST /api/upload/recalculate-scores                          │
│ - Recalculates health scores with new data                  │
│ - Updates dashboard                                          │
└─────────────────────────────────────────────────────────────┘
```

### Flow 3: Runtime Complete Refresh

```
┌─────────────────────────────────────────────────────────────┐
│ Customer uploads corrected November data                     │
│ POST /api/upload                                             │
│ - file: november_corrected.csv                               │
│ - customer_id: 123                                           │
│ - mode: replace                                              │
│ - date_range: 2024-11-01,2024-11-30                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ upload_api_v2_config_aware.py                                │
│ 1. Reads CustomerConfig                                      │
│ 2. Filters CSV to enabled KPIs                              │
│ 3. DELETE existing November data                            │
│ 4. INSERT all new November data                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Configuration Examples

### Example 1: Customer with 15 KPIs

**CustomerConfig:**
```python
{
  "customer_id": 123,
  "vertical": "dc2_s",
  "dc2s_enabled_kpis": [
    "AI-KPI1", "AI-KPI2", "AI-KPI3",
    "CH-KPI1", "CH-KPI2", "CH-KPI3",
    "DV-KPI1", "DV-KPI2", "DV-KPI3",
    "EX-KPI1", "EX-KPI2", "EX-KPI3",
    "OS-KPI1", "OS-KPI2", "OS-KPI3"
  ]
}
```

**CSV Upload Result:**
- CSV contains 35 KPIs (all possible)
- System filters to 15 enabled KPIs
- 20 KPIs rejected
- Only 15 KPIs loaded to database

### Example 2: Customer Adds Custom KPI

**Before:**
```python
"dc2s_enabled_kpis": ["AI-KPI1", "AI-KPI2", "AI-KPI3", ...]  # 15 KPIs
```

**After (via Settings UI):**
```python
"dc2s_enabled_kpis": [
  "AI-KPI1", "AI-KPI2", "AI-KPI3", ...,
  "CUSTOM-GPU-TEMP"  # New custom KPI added
]  # 16 KPIs
```

**Next CSV Upload:**
- Customer includes "CUSTOM-GPU-TEMP" in CSV
- System recognizes it's enabled
- Loads the custom KPI data
- Calculates scores including custom KPI

---

## 🧪 Testing

### Test 1: Config-Aware CSV Generation

```bash
cd backend

# Generate test CSVs (config-aware)
python3 test_onboarding_complete_e2e_api_v3.py

# Check output
cat /tmp/test_customer_*/data/kpi_measurements.csv | cut -d',' -f2 | sort -u
# Should show ONLY enabled KPIs (e.g., 15), not all 35
```

### Test 2: Upload Filtering

```bash
# Create CSV with 35 KPIs
# Upload to customer with 15 enabled KPIs

curl -X POST http://localhost:5059/api/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@all_kpis.csv" \
  -F "customer_id=123" \
  -F "mode=incremental"

# Response should show:
# {
#   "records_in_csv": 5400,      // 35 KPIs × 10 accounts × 12 months
#   "records_filtered": 3086,    // 20 disabled KPIs filtered
#   "records_processed": 2314,   // 15 enabled KPIs loaded
#   "disabled_kpis": [...20 KPIs...]
# }
```

### Test 3: Loader Script

```bash
# Test migrated loader
cd backend

python3 verticals/customer9-dc2_s/scripts/02_load_customer9_data_SMART.py

# Look for in output:
# "CONFIG-AWARE KPI LOADING"
# "Enabled KPIs in config: 33"
# "Filtered out X records with disabled KPIs"
```

---

## 📝 API Reference

### POST /api/onboarding/complete

Creates customer with default config.

**Request:**
```json
{
  "customer_name": "Acme Corp",
  "industry": "Technology"
}
```

**Response:**
```json
{
  "success": true,
  "customer_id": 123,
  "config": {
    "enabled_kpis": 15,
    "pillars": 5
  }
}
```

### POST /api/onboarding/process-data

Processes uploaded CSVs (config-aware).

**Request:**
```json
{
  "customer_id": 123
}
```

**Response:**
```json
{
  "success": true,
  "validation": {
    "enabled_kpis": 15,
    "csv_kpis": 35,
    "disabled_kpis": [...],
    "warnings": [...]
  }
}
```

### POST /api/upload

Runtime CSV upload (config-aware).

**Request:**
```
Content-Type: multipart/form-data

file: kpi_measurements.csv
customer_id: 123
mode: incremental | replace
date_range: 2024-12-01,2024-12-31 (optional, for replace mode)
```

**Response:**
```json
{
  "success": true,
  "mode": "incremental",
  "records_in_csv": 500,
  "records_filtered": 150,
  "records_processed": 350,
  "enabled_kpis": 15,
  "disabled_kpis": [...]
}
```

### POST /api/upload/validate

Validate CSV before uploading.

**Request:**
```
Content-Type: multipart/form-data

file: kpi_measurements.csv
customer_id: 123
```

**Response:**
```json
{
  "valid": true,
  "enabled_kpis": 15,
  "csv_kpis": 35,
  "disabled_kpis": [...],
  "records_will_filter": 3600,
  "warnings": [...]
}
```

### POST /api/upload/recalculate-scores

Recalculate after upload.

**Request:**
```json
{
  "customer_id": 123,
  "month": "2024-12-01"  // optional
}
```

**Response:**
```json
{
  "success": true,
  "accounts_scored": 3,
  "results": [...]
}
```

---

## 🔍 Troubleshooting

### Issue: "No enabled KPIs found"

**Cause:** Customer doesn't have CustomerConfig entry.

**Solution:**
```bash
# Create config via API
curl -X POST http://localhost:5059/api/onboarding/complete \
  -d '{"customer_name": "Test", "industry": "Tech"}'
```

### Issue: "All records filtered out"

**Cause:** CSV contains only disabled KPIs.

**Solution:**
1. Check what's enabled: `SELECT dc2s_enabled_kpis FROM customer_configs WHERE customer_id = 123`
2. Enable more KPIs via Settings UI
3. Or upload CSV with enabled KPIs

### Issue: "Loader script still loads all KPIs"

**Cause:** Old loader version still in use.

**Solution:**
```bash
# Re-run migration
python3 scripts/migrate_loaders_to_config_aware.py --customer-id 123

# Verify it's the V2 version
grep "CONFIG-AWARE" verticals/customer123-dc2_s/scripts/02_load_customer123_data_SMART.py
```

---

## ✅ Verification Checklist

After integration, verify:

- [ ] New customers get CustomerConfig automatically
- [ ] CSV generation creates only enabled KPIs
- [ ] Onboarding API validates CSVs against config
- [ ] Upload API filters disabled KPIs
- [ ] Loader scripts show "CONFIG-AWARE" in logs
- [ ] Disabled KPIs in CSV are filtered out
- [ ] Only enabled KPIs appear in database
- [ ] Health scores calculate correctly
- [ ] Settings UI can modify enabled KPIs
- [ ] Changes to config affect future uploads

---

## 🎯 Next Steps

1. **Copy files to backend**
2. **Register new APIs in app_v3_minimal.py**
3. **Migrate existing customer loaders**
4. **Test with V3 test script**
5. **Update documentation**
6. **Deploy to staging**

---

## 📚 Related Documentation

- CustomerConfig model: `models.py`
- ConfigLoader utility: `utils/config_loader.py`
- Settings UI: `frontend/src/components/Settings/`
- Onboarding flow: `docs/ONBOARDING.md`

---

## 🆘 Support

If you encounter issues:

1. Check logs for "CONFIG-AWARE" messages
2. Verify CustomerConfig exists in database
3. Test with V3 test script first
4. Check API responses for filtering stats

---

**System is now fully config-aware!** 🎉
