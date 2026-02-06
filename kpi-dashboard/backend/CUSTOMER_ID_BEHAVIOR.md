# Customer ID Behavior in Onboarding

## Question: When onboarding customer with ID 23, which customer_id will be used?

**Answer:** The database auto-generated ID (current sequence value), **NOT** the provided ID 23.

---

## Current Behavior

### What Happens:

1. **Provisioning Step** (`POST /api/onboarding/provision` with `customer_id: 23`):
   - ✅ Creates directory: `customer23-dc2_s/`
   - ✅ Creates scripts: `02_load_customer23_data_SMART.py`
   - ✅ Uses customer_id=23 for **directory structure and scripts**

2. **Complete Step** (`POST /api/onboarding/complete` with `customer_id: 23`):
   - ⚠️  Attempts to set sequence to 22 (so next is 23)
   - ⚠️  PostgreSQL creates customer with **auto-generated ID** (current sequence value)
   - ⚠️  If sequence is at 17, customer gets ID 18
   - ⚠️  If sequence is at 22, customer gets ID 23 (coincidence)
   - ⚠️  **Result:** Database customer_id may **NOT** match provided ID

3. **Data Loading Step** (`POST /api/onboarding/process-data`):
   - ✅ CSV files have `customer_id=23` (from provisioning)
   - ✅ Script **auto-corrects** customer_id in CSV to match database
   - ✅ Accounts are linked to **actual database customer_id**

---

## Test Results

```
Current max customer_id: 17
Next auto-increment would be: 18

Attempted: Set sequence to 22 (so next would be 23)
Result: Customer created with ID: 22 (not 23!)
```

**Why?** The `setval()` call with `false` parameter doesn't work as expected. The sequence value is set, but the next insert uses the sequence value, not sequence+1.

---

## Root Cause

PostgreSQL auto-increment sequences:
- `customer_id` is defined as `PRIMARY KEY` with auto-increment
- Cannot directly set `customer_id` when creating a new record
- Can only manipulate the sequence, but it's unreliable

---

## Solutions

### Option 1: **Accept Auto-Generated IDs** (Current Implementation)
- ✅ Provision with desired customer_id for directory structure
- ✅ Accept database auto-generates its own customer_id
- ✅ Data loading script auto-corrects customer_id mismatch
- ✅ **This is what we have now - it works!**

**Pros:**
- Simple and reliable
- No database conflicts
- Auto-correction handles mismatches

**Cons:**
- Directory customer_id ≠ Database customer_id
- Requires customer_id mapping logic

---

### Option 2: **Pre-Create Customer Record** (Better Approach)
Create the customer record **first** with the desired ID:

```python
# In provisioning step:
# 1. Create customer record with explicit ID (if sequence allows)
# 2. Then create directory structure
# 3. Then generate data

# If sequence is at 17, and we want 23:
# - Need to advance sequence to 22 (next is 23)
# - Create customer (gets 23)
# - Provision directory (uses 23)
```

**Pros:**
- Directory customer_id = Database customer_id
- No mismatches to correct

**Cons:**
- More complex
- Sequence manipulation can fail
- May conflict with existing IDs

---

### Option 3: **Use UUID Instead of Integer IDs** (Best Long-Term)
```python
customer_id = db.Column(db.String, primary_key=True)  # UUID
```

**Pros:**
- No sequence conflicts
- Can set explicit IDs
- Better for distributed systems

**Cons:**
- Requires schema change
- Breaking change for existing data

---

## Recommendation for Customer 23

**Use Option 1** (current implementation):

1. **Provision** with `customer_id: 23`:
   ```bash
   POST /api/onboarding/provision
   {"customer_id": 23, "customer_name": "Customer 23"}
   ```
   - Creates `customer23-dc2_s/` directory
   - Creates scripts with customer_id=23

2. **Complete** onboarding:
   ```bash
   POST /api/onboarding/complete
   {"customer_id": 23, ...}
   ```
   - Database creates customer with auto-generated ID (e.g., 18, 19, 20...)
   - May or may not be 23

3. **Process data**:
   ```bash
   POST /api/onboarding/process-data
   {"customer_id": 23}
   ```
   - CSV files have customer_id=23
   - Script auto-corrects to actual database customer_id
   - Accounts linked correctly

---

## Summary

| Step | Provided ID | Actual ID Used | Status |
|------|-------------|----------------|--------|
| Provision | 23 | 23 (directory) | ✅ Works |
| Complete | 23 | 18-23 (DB) | ⚠️  May differ |
| Load Data | 23 (CSV) | 18-23 (DB) | ✅ Auto-corrected |

**Bottom Line:** 
- **Directory structure** will use customer_id **23**
- **Database customer_id** will be **auto-generated** (likely 18, 19, 20, etc.)
- **Data loading** will **auto-correct** the mismatch

This works, but customer_id **23 in directory ≠ customer_id in database**.
