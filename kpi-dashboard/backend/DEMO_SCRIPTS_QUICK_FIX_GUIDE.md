# 🚀 Demo Scripts Quick Fix Guide

## Overview

You have comprehensive demo scripts, but they need minor fixes to work with your codebase.

---

## ⚡ Quick Fixes (1 Hour Total)

### Fix 1: Copy Scripts to Backend (2 minutes)

```bash
cd /Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard/backend
cp /Users/manojgupta/Downloads/demo-narrations/demo_*.py .
```

### Fix 2: Update Path References (15 minutes)

**File:** `demo_testing.py`

**Line 20:** Change base path
```python
# BEFORE:
def __init__(self, base_path='backend/verticals/customer17-dc2_s/journey/wizard_a/test_10_accounts'):

# AFTER (Option 1 - Use customer120):
def __init__(self, base_path='backend/verticals/customer120-dc2_s/journey/wizard_a/test_10_accounts'):

# AFTER (Option 2 - Dynamic discovery - RECOMMENDED):
def __init__(self, base_path=None):
    if base_path is None:
        # Auto-discover path
        from pathlib import Path
        for customer_dir in Path('backend/verticals').glob('customer*-dc2_s'):
            test_dir = customer_dir / 'journey/wizard_a/test_10_accounts'
            if test_dir.exists():
                base_path = str(test_dir)
                break
        if base_path is None:
            raise ValueError("Could not find journey test_10_accounts directory")
    self.base_path = base_path
```

**Line 309:** Update milestone file path
```python
# BEFORE:
kpi_file = f"backend/verticals/customer17-dc2_s/journey/wizard_a/test_10_accounts/account_{account_id}_kpis.csv"

# AFTER:
kpi_file = f"{self.base_path}/account_{account_id}_kpis.csv"  # Use self.base_path
```

**File:** `demo_journeys.py`

**Line 590:** Update journey file path
```python
# BEFORE:
journey_file = f"backend/verticals/customer17-dc2_s/journey/wizard_a/test_10_accounts/account_{account_id}_journey.json"

# AFTER (Use dynamic discovery):
from pathlib import Path
journey_file = None
for customer_dir in Path('backend/verticals').glob('customer*-dc2_s'):
    test_file = customer_dir / f'journey/wizard_a/test_10_accounts/account_{account_id}_journey.json'
    if test_file.exists():
        journey_file = str(test_file)
        break
```

### Fix 3: Add Frontend Route (5 minutes)

**File:** `src/App.tsx`

**Add after line 198:**
```typescript
{/* Journey Visualizer Route */}
<Route
  path="/journey/:accountId"
  element={
    <PrivateRoute>
      <JourneyDashboardV3 />
    </PrivateRoute>
  }
/>
```

### Fix 4: Verify Account IDs (10 minutes)

**Run this check:**
```bash
cd kpi-dashboard/backend
python3 -c "
from app_v3_minimal import app, db
from models import Account
from pathlib import Path

with app.app_context():
    print('Checking Account IDs...\n')
    
    # Check database
    for aid in [10001, 10003, 10007, 120001, 120003, 120007]:
        acc = Account.query.filter_by(account_id=aid).first()
        if acc:
            print(f'✅ Account {aid}: Customer {acc.customer_id}, Name: {acc.account_name}')
    
    # Check journey files
    print('\nChecking Journey Files...\n')
    for customer_dir in Path('verticals').glob('customer*-dc2_s'):
        test_dir = customer_dir / 'journey/wizard_a/test_10_accounts'
        if test_dir.exists():
            for aid in [10001, 10003, 10007]:
                journey_file = test_dir / f'account_{aid}_journey.json'
                if journey_file.exists():
                    print(f'✅ Found: {journey_file} (Account {aid})')
"
```

**Based on results:**
- If accounts 10001, 10003, 10007 exist in DB → Keep as-is
- If accounts 120001, 120003, 120007 exist → Update scripts
- If files in customer120 but accounts are 10001 → Update file paths only

### Fix 5: Install Dependencies (2 minutes)

```bash
cd kpi-dashboard/backend
pip install pandas requests
```

### Fix 6: Fix Import in demo_testing.py (2 minutes)

**File:** `demo_testing.py` line 382

**BEFORE:**
```python
from demo_script import DEMO_SCRIPTS
```

**AFTER:**
```python
try:
    from demo_script import DEMO_SCRIPTS
except ImportError:
    # Handle case where demo_script.py not in same directory
    import sys
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    from demo_script import DEMO_SCRIPTS
```

### Fix 7: Update URLs in demo_journeys.py (5 minutes)

**File:** `demo_journeys.py` line 528-534

**BEFORE:**
```python
'urls': {
    'dashboard': f'http://localhost:5059/dashboard?account={account_id}',
    'journey': f'http://localhost:5059/journey/{account_id}',
    'health': f'http://localhost:5059/health?account={account_id}',
    'signals': f'http://localhost:5059/signals?account={account_id}',
    'playbooks': f'http://localhost:5059/playbooks?account={account_id}'
}
```

**AFTER:**
```python
'urls': {
    'dashboard': f'http://localhost:5059/dc-dashboard',
    'journey': f'http://localhost:5059/journey/{account_id}',  # After route added
    'tenant_details': f'http://localhost:5059/dc-dashboard/tenants/{account_id}',
    'api_journey': f'http://localhost:5059/api/journey/{account_id}',
    'api_health': f'http://localhost:5059/api/health',
}
```

---

## 🧪 Testing After Fixes

### Test 1: Readiness Check
```bash
cd kpi-dashboard/backend
python3 demo_testing.py check
```

**Expected:** All checks pass (after path fixes)

### Test 2: List Journeys
```bash
python3 demo_journeys.py list
```

**Expected:** Shows 3 journeys (turnaround_success, churn_prevention, proactive_growth)

### Test 3: Setup Demo
```bash
python3 demo_journeys.py setup turnaround_success
```

**Expected:** Shows account info, URLs, features

### Test 4: Test Journey
```bash
python3 demo_journeys.py test turnaround_success
```

**Expected:** Validates journey data exists

### Test 5: Demo Script
```bash
python3 demo_script.py script 15min
```

**Expected:** Shows timed 15-minute script

### Test 6: Persona Demo
```bash
python3 demo_script.py persona vp_customer_success 15min
```

**Expected:** Shows customized demo for VP CS

### Test 7: Rehearsal
```bash
python3 demo_testing.py rehearse 15min
```

**Expected:** Interactive timer for practice

---

## ✅ Verification Checklist

After fixes, verify:

- [ ] Scripts copied to `backend/` directory
- [ ] Paths updated (customer17 → customer120 or dynamic)
- [ ] Frontend route `/journey/:accountId` added
- [ ] Account IDs verified in database
- [ ] Dependencies installed (pandas, requests)
- [ ] Import fixed in demo_testing.py
- [ ] URLs updated in demo_journeys.py
- [ ] `demo_testing.py check` passes
- [ ] `demo_journeys.py list` works
- [ ] `demo_script.py script 15min` works
- [ ] Frontend route accessible in browser

---

## 🎯 Expected Final State

After all fixes:

```bash
# 1. Check readiness
python3 demo_testing.py check
# ✅ All checks pass

# 2. Setup demo
python3 demo_journeys.py setup turnaround_success
# ✅ Shows account 10001, URLs, features

# 3. Practice demo
python3 demo_testing.py rehearse 15min
# ✅ Interactive timer works

# 4. Run demo
# Browser: http://localhost:5059/journey/10001
# ✅ Journey visualizer loads
```

---

## 📋 Summary

**Time Required:** ~1 hour  
**Complexity:** Low (mostly find/replace)  
**Risk:** Low (scripts are separate from core code)

**After fixes, you'll have:**
- ✅ Complete demo automation
- ✅ All features from proposal
- ✅ Working readiness checks
- ✅ Rehearsal tools
- ✅ Persona customization

**You're 75% ready - just need these path/route fixes!** 🚀
