# Why Scripts Aren't Generated - Root Cause Analysis

## 🔍 Problem

When Customer 19 is provisioned via `/api/onboarding/complete`, the provision script reports:
```
📁 Copying directory structure...
   ✅ Copied 0 files
   ✅ 0 files with placeholder replacements
   ✅ 0 total replacements made
   ⏭️  Skipped 19 files (binary/cache)
```

But when the provision script is run directly, it works perfectly:
```
📁 Copying directory structure...
   ✅ Copied 411 files
   ✅ 72 files with placeholder replacements
   ✅ 603 total replacements made
   ⏭️  Skipped 3 files (binary/cache)
```

## 🔎 Root Cause

The issue is likely related to **path resolution** when the provision script is called from the API context vs. direct execution.

### When Run Directly:
- `BASE_DIR = Path(__file__).parent` resolves to: `/Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/verticals`
- `TEMPLATE_DIR = BASE_DIR / "_template"` resolves correctly
- Files are found and copied successfully

### When Called from API:
- The `__file__` path might resolve differently
- Or the working directory might be different
- Or there's an exception being silently caught

## 🔧 Investigation Steps

1. **Check path resolution in API context:**
   ```python
   # In onboarding_api_v2_config_aware.py, before calling provision_customer:
   from verticals.provision_dc_customer import TEMPLATE_DIR, BASE_DIR
   current_app.logger.info(f"BASE_DIR: {BASE_DIR}")
   current_app.logger.info(f"TEMPLATE_DIR: {TEMPLATE_DIR}")
   current_app.logger.info(f"TEMPLATE_DIR exists: {TEMPLATE_DIR.exists()}")
   ```

2. **Check if exception is being caught:**
   ```python
   # The current code catches exceptions silently:
   except Exception as e:
       current_app.logger.warning(f"⚠️  Could not provision directory: {e}")
   ```
   This might be hiding the real error!

3. **Check working directory:**
   ```python
   import os
   current_app.logger.info(f"Working directory: {os.getcwd()}")
   ```

## ✅ Solution

### Option 1: Fix Path Resolution (Recommended)

Update `provision_dc_customer.py` to use absolute paths:

```python
# Instead of:
BASE_DIR = Path(__file__).parent

# Use:
BASE_DIR = Path(__file__).resolve().parent
```

### Option 2: Add Better Error Handling

Update `onboarding_api_v2_config_aware.py` to log the actual error:

```python
except Exception as e:
    import traceback
    current_app.logger.error(f"❌ Could not provision directory: {e}")
    current_app.logger.error(traceback.format_exc())
    # Don't fail silently - raise or return error
```

### Option 3: Use Absolute Paths in API Call

Pass absolute paths explicitly:

```python
from pathlib import Path
template_dir = Path(__file__).parent.parent / "verticals" / "_template"
provision_customer(..., template_dir=template_dir)
```

## 🎯 Immediate Fix

The most likely issue is that exceptions are being silently caught. Let's add better error logging:

```python
try:
    from verticals.provision_dc_customer import provision_customer, TEMPLATE_DIR, BASE_DIR
    
    # Debug logging
    current_app.logger.info(f"Provisioning customer {customer_id}")
    current_app.logger.info(f"BASE_DIR: {BASE_DIR}")
    current_app.logger.info(f"TEMPLATE_DIR: {TEMPLATE_DIR}")
    current_app.logger.info(f"TEMPLATE_DIR exists: {TEMPLATE_DIR.exists()}")
    
    provision_success = provision_customer(
        customer_id=customer_id,
        customer_name=customer_name,
        vertical_slug=vertical,
        force=True
    )
    
    if provision_success:
        directory_provisioned = True
        current_app.logger.info(f"✅ Provisioned directory for customer {customer_id}")
    else:
        current_app.logger.warning(f"⚠️  Directory provisioning returned False for customer {customer_id}")
        
except Exception as e:
    import traceback
    current_app.logger.error(f"❌ Could not provision directory: {e}")
    current_app.logger.error(traceback.format_exc())
    # Don't fail silently - this is a critical step
    raise  # Or return error response
```

## 📊 Expected Behavior

After fix, when Customer 19 is provisioned, you should see:
```
📁 Copying directory structure...
   ✅ Copied 411 files
   ✅ 72 files with placeholder replacements
   ✅ 603 total replacements made
   ⏭️  Skipped 3 files (binary/cache)
```

And the scripts directory should contain:
- `02_load_customer19_data_SMART.py`
- `03_embed_customer19_OPENAI.py`
- `04_validate_data_integrity.py`
- And other scripts...

## ✅ Verification

After applying the fix, verify:
1. Scripts directory exists: `verticals/customer19-dc2_s/scripts/`
2. Scripts are present: `ls verticals/customer19-dc2_s/scripts/*.py`
3. Scripts have correct customer ID: `grep -l "customer19" verticals/customer19-dc2_s/scripts/*.py`

---

**Status:** 🔴 **ISSUE IDENTIFIED** - Path resolution or exception handling issue  
**Priority:** 🔴 **HIGH** - Scripts are critical for data processing  
**Fix:** Add better error logging and ensure absolute paths
