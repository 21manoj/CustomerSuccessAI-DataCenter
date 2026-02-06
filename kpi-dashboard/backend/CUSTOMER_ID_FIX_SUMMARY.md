# Customer ID Override Fix Summary

## Problem Identified

The onboarding wizard was generating a new `customer_id` via database auto-increment instead of using the `customer_id` provided during provisioning.

### Root Cause:
- `/api/onboarding/complete` endpoint creates a new `Customer` record without accepting a `customer_id` parameter
- Database auto-increments the `customer_id` (e.g., 16) instead of using the provided ID (e.g., 19)
- CSV files have `customer_id=19` hardcoded
- Data loading script uses `customer_id=19` 
- Result: **0 accounts** because customer record is 16, but data is loaded with 19

## Solution Applied

### 1. Updated `/api/onboarding/complete` endpoint:
- Now accepts `customer_id` in request body
- Checks if customer with provided `customer_id` already exists
- If exists, uses existing customer
- If not, attempts to set the sequence to use provided `customer_id`
- Falls back to auto-increment if database doesn't allow manual ID assignment

### 2. Updated data loading script:
- Automatically detects customer_id mismatch between CSV and database
- Updates CSV data to use actual database customer_id before loading
- This ensures accounts are linked to the correct customer record

## Code Changes

### `onboarding_api.py` - `/api/onboarding/complete`:
```python
# Check if customer_id is provided (from provisioning step)
provided_customer_id = data.get('customer_id')

# Check if customer already exists (by customer_id, domain, or email)
existing_customer = None
if provided_customer_id:
    existing_customer = Customer.query.filter_by(customer_id=provided_customer_id).first()
# ... rest of logic
```

### `02_load_customer19_data_SMART.py`:
```python
# Fix customer_id mismatch: CSV has customer_id=19, but DB customer is 16
if 'customer_id' in df.columns:
    # Find actual customer_id from database
    # Update CSV data to match database customer_id
    df['customer_id'] = actual_customer_id
```

## Testing

1. **Provision customer 19:**
   ```bash
   POST /api/onboarding/provision
   {"customer_id": 19, "customer_name": "Synthetic Data Corp"}
   ```

2. **Complete onboarding with customer_id:**
   ```bash
   POST /api/onboarding/complete
   {
     "customer_id": 19,  # <-- Now accepts this!
     "company_name": "Synthetic Data Corp",
     "company_email": "admin@synthetic-data.com",
     ...
   }
   ```

3. **Verify customer_id matches:**
   - Customer record in DB should have `customer_id=19` (or the provided ID)
   - CSV files can have `customer_id=19`
   - Data loading script will auto-correct if mismatch occurs

## Next Steps

1. **Frontend Update:** Update `OnboardingWizard.tsx` to pass `customer_id` to `/api/onboarding/complete` if it was provided during provisioning
2. **Alternative:** Make provisioning step create the customer record in DB with the specified ID
3. **Database Schema:** Consider allowing manual `customer_id` assignment if not already supported

## Status

✅ **Fixed:** Endpoint now accepts `customer_id` parameter  
✅ **Fixed:** Data loading script auto-corrects customer_id mismatch  
⚠️ **Pending:** Frontend integration to pass `customer_id` from provisioning to complete
