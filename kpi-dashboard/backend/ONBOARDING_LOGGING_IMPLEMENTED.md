# Onboarding Verbose Logging - Implemented ✅
**Date:** January 19, 2026

---

## ✅ Verbose Log File Created

### Log File Location
```
backend/logs/onboarding/onboarding_customer{N}_{timestamp}.log
```

**Example:**
```
backend/logs/onboarding/onboarding_customer18_20260119_143022.log
```

---

## 📋 Log File Format

### Format
```
YYYY-MM-DD HH:MM:SS.ffffff | LEVEL     | STEP_NAME                  | MESSAGE
```

### Example Log Entry
```
2026-01-19 14:30:22.123456 | INFO      | SESSION_START              | ═══════════════════════════════════════════════════════════════
2026-01-19 14:30:22.123789 | INFO      | SESSION_START              | ONBOARDING SESSION STARTED
2026-01-19 14:30:22.124012 | INFO      | SESSION_START              | Customer ID: 18 | Name: Acme Corp
2026-01-19 14:30:22.124234 | INFO      | PROVISION_START            | Starting customer directory provisioning
2026-01-19 14:30:22.124456 | INFO      | PROVISION_START            | Details:
{
  "customer_name": "Acme Corp",
  "vertical": "dc2_s"
}
2026-01-19 14:30:25.567890 | INFO      | PROVISION_COMPLETE         | ✅ Customer directory provisioned successfully
2026-01-19 14:30:25.568123 | INFO      | UPLOAD_ACCOUNTS            | ✅ File uploaded: accounts.csv
2026-01-19 14:30:25.568345 | INFO      | SCRIPT_START_02_load_data  | Executing script: 02_load_data
2026-01-19 14:32:10.123456 | INFO      | SCRIPT_SUCCESS_02_load_data | ✅ Script completed successfully: 02_load_data
```

---

## 🔍 Tracked Steps

### 1. Session Management
- `SESSION_START` - Onboarding session started
- `SESSION_END` - Onboarding session ended with summary

### 2. Provisioning
- `PROVISION_START` - Directory provisioning started
- `PROVISION_COMPLETE` - Directory provisioned successfully
- `PROVISION_ERROR` - Provisioning failed
- `PROVISION_SKIP` - Directory already exists

### 3. Onboarding Completion
- `COMPLETE_START` - Onboarding completion started
- `COMPLETE_SUCCESS` - Customer/User/Config created
- `COMPLETE_CONFIG` - CustomerConfig with pillar weights

### 4. File Uploads
- `UPLOAD_ACCOUNTS` - Accounts file uploaded
- `UPLOAD_KPIS` - KPIs file uploaded
- `UPLOAD_SIGNALS` - Signals file uploaded
- `UPLOAD_PRODUCTS` - Products file uploaded
- `UPLOAD_PROFILES` - Profiles file uploaded
- `UPLOAD_{TYPE}_ERROR` - Upload error for specific type

### 5. Data Processing
- `PROCESS_DATA_START` - Data processing pipeline started
- `SCRIPT_START_{name}` - Script execution started
- `SCRIPT_SUCCESS_{name}` - Script completed successfully
- `SCRIPT_ERROR_{name}` - Script execution failed
- `PROCESS_DATA_COMPLETE` - All scripts completed

### 6. Journey API
- `JOURNEY_API_REGISTER` - Journey API registration (success/error)

### 7. Rollback
- `ROLLBACK` - Rollback triggered with actions needed

---

## 📊 Log Details Include

### File Uploads
- File type, filename, file path
- File size in bytes
- Upload timestamp

### Script Execution
- Script name and path
- Execution duration (seconds)
- stdout/stderr preview (first 500 chars)
- Success/error status

### Processing Pipeline
- Steps completed
- Errors encountered
- Total steps count
- Skip flags (validation, wizard_b)

### Session Summary
- Overall status (SUCCESS/ERROR/WARNING)
- Complete step list
- Error summary
- Log file path

---

## 🔧 Usage

### Automatic Logging
Logging is **automatic** - no code changes needed in endpoints. The logger is initialized when:
1. Provision endpoint is called
2. Complete endpoint is called
3. Upload endpoint is called
4. Process-data endpoint is called

### Log File Returned in API Responses
All endpoints now return `log_file` path in response:
```json
{
  "status": "success",
  "customer_id": 18,
  "log_file": "logs/onboarding/onboarding_customer18_20260119_143022.log"
}
```

### Manual Access
```python
from onboarding_logger import get_onboarding_logger

# Get logger for customer
logger = get_onboarding_logger(customer_id=18, customer_name="Acme Corp")

# Log custom step
logger.log_step('CUSTOM_STEP', 'Custom message', 'INFO', {'key': 'value'})

# Close session
from onboarding_logger import close_onboarding_session
close_onboarding_session(customer_id=18, overall_status='SUCCESS', summary={...})
```

---

## 📁 Log File Management

### Rotation
- **Max size:** 50MB per file
- **Backups:** 10 rotated files kept
- **Encoding:** UTF-8

### Directory Structure
```
backend/
  logs/
    onboarding/
      onboarding_customer18_20260119_143022.log
      onboarding_customer18_20260119_143022.log.1
      onboarding_customer18_20260119_143022.log.2
      ...
      onboarding_customer19_20260119_150000.log
      ...
```

---

## ✅ Integration Status

### Endpoints with Logging
- ✅ `POST /api/onboarding/provision`
- ✅ `POST /api/onboarding/complete`
- ✅ `POST /api/onboarding/upload`
- ✅ `POST /api/onboarding/process-data`
- ✅ `POST /api/onboarding/register-journey-api`

### Logged Operations
- ✅ Directory provisioning
- ✅ Customer/User/Config creation
- ✅ Team member creation
- ✅ File uploads (all types)
- ✅ Script execution (all 5 scripts)
- ✅ Journey API registration
- ✅ Rollback operations

---

## 🎯 Benefits

1. **Complete Audit Trail** - Every step logged with timestamp
2. **Error Debugging** - Detailed error messages with context
3. **Performance Tracking** - Script execution durations
4. **Troubleshooting** - Easy to identify where process failed
5. **Compliance** - Full record of onboarding operations

---

**Status:** ✅ **VERBOSE LOGGING FULLY IMPLEMENTED**
