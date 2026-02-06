# Blueprint Registration Complete

## Changes Made

### 1. Updated Route Definitions ✅

**upload_api_v2_config_aware.py:**
- Changed `/api/upload` → `/upload`
- Changed `/api/upload/recalculate-scores` → `/upload/recalculate-scores`
- Changed `/api/upload/validate` → `/upload/validate`
- Changed `/api/upload/health` → `/upload/health`
- Removed duplicate `/api/onboarding/upload` (handled by onboarding_api_v2)

**onboarding_api_v2_config_aware.py:**
- Changed `/api/onboarding/complete` → `/complete`
- Changed `/api/onboarding/process-data` → `/process-data`
- Changed `/api/onboarding/validate-csv` → `/validate-csv`
- Changed `/api/onboarding/upload` → `/upload`
- Changed `/api/onboarding/health` → `/health`

### 2. Updated Blueprint Registration ✅

**app_v3_minimal.py:**

```python
# Register upload API (V2 config-aware takes precedence)
if UPLOAD_API_V2_AVAILABLE:
    app.register_blueprint(upload_api_v2, url_prefix='/api')
    print("✅ Registered Config-Aware Upload API V2: /api/upload/*")

# Register Onboarding API (V2 config-aware takes precedence)
if ONBOARDING_API_V2_AVAILABLE:
    app.register_blueprint(onboarding_api_v2, url_prefix='/api/onboarding')
    print("✅ Registered Config-Aware Onboarding API V2: /api/onboarding/*")
```

## Resulting Endpoints

### Upload API (`/api` prefix):
- `POST /api/upload` - Upload KPI CSV
- `POST /api/upload/recalculate-scores` - Recalculate scores
- `POST /api/upload/validate` - Validate upload
- `GET /api/upload/health` - Health check

### Onboarding API (`/api/onboarding` prefix):
- `POST /api/onboarding/complete` - Complete onboarding
- `POST /api/onboarding/process-data` - Process data
- `POST /api/onboarding/validate-csv` - Validate CSV
- `POST /api/onboarding/upload` - Upload file (for UI)
- `GET /api/onboarding/health` - Health check

## Benefits

✅ **Better Design:** Upload and onboarding are now separate concerns  
✅ **Cleaner URLs:** Consistent prefix structure  
✅ **Easier Maintenance:** Clear separation of responsibilities  
✅ **No Duplication:** Removed duplicate `/api/onboarding/upload` from upload_api_v2

## Next Steps

1. **Restart Flask server** to load new route registrations
2. **Test endpoints** to verify they work correctly
3. **Update frontend** if any endpoint URLs changed

## Verification

After server restart, verify routes are registered:

```python
from app_v3_minimal import app
for rule in app.url_map.iter_rules():
    if 'upload' in rule.rule or 'onboarding' in rule.rule:
        print(f'{rule.rule} [{rule.methods}]')
```
