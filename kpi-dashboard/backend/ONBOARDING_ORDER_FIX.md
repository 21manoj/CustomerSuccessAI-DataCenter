# Onboarding Order Fix

## Problem Identified

The test script was generating synthetic data **before** provisioning the customer directory, then copying files. This is inefficient and error-prone.

## Correct Order

### ✅ **CORRECT FLOW:**

1. **Provision customer directory** (creates `customer19-dc2_s/` structure from `_template`)
2. **Generate synthetic data directly** into `customer19-dc2_s/data/` using `--output-dir` flag
3. **Load data** using `02_load_customer19_data_SMART.py`
4. **Embed data** using `03_embed_customer19_OPENAI.py`
5. **Validate data** using `04_validate_data_integrity.py`
6. **Generate journey data** using `wizard_a_journey_generator.py`

### ❌ **OLD FLOW (WRONG):**

1. Generate synthetic data to `customer19_synthetic_data/`
2. Provision customer directory
3. Copy synthetic data to provisioned directory
4. Load data...

## Changes Made

### 1. Updated `test_customer19_e2e_onboarding.py`:
- **Step 0:** Provision customer directory FIRST
- **Step 0.5:** Generate synthetic data directly into `customer19-dc2_s/data/` using `--output-dir` flag
- Removed manual file copying step

### 2. Updated `execute_script()` function:
- Added support for `additional_args` parameter
- Added support for custom `env` parameter
- Allows passing command-line arguments to scripts (e.g., for journey generator)

## Benefits

1. **No file copying needed** - data generated directly where it's needed
2. **Cleaner workflow** - fewer steps, less error-prone
3. **Better organization** - data is in the right place from the start
4. **Easier to debug** - single source of truth for data location

## Usage

```bash
# Run the corrected test
python3 test_customer19_e2e_onboarding.py
```

The test will:
1. Provision `customer19-dc2_s/` directory
2. Generate synthetic data directly to `customer19-dc2_s/data/`
3. Execute all processing scripts
4. Verify results

## Code Example

```python
# Step 0: Provision
subprocess.run([
    sys.executable, "provision_dc_customer.py",
    "--customer-id", "19",
    "--customer-name", "Synthetic Data Corp",
    "--force"
])

# Step 0.5: Generate data directly into provisioned directory
subprocess.run([
    sys.executable, "generate_synthetic_customer_data.py",
    "--customer-id", "19",
    "--num-accounts", "20",
    "--output-dir", "verticals/customer19-dc2_s/data"  # <-- Direct output
])
```

## Status

✅ **Fixed:** Test script now provisions first, then generates data directly into provisioned directory  
✅ **Fixed:** `execute_script()` now supports additional arguments for journey generator
