# 🧪 End-to-End Testing Guide: Demo Manifest-Based Journeys

## Overview

This guide provides best practices for testing end-to-end demo manifest-based journeys in the DC2_S platform. Demo manifests define specific account journey patterns for demonstration purposes.

## 📋 Table of Contents

1. [Understanding Demo Manifests](#understanding-demo-manifests)
2. [Test Strategy](#test-strategy)
3. [Test Setup](#test-setup)
4. [E2E Test Scripts](#e2e-test-scripts)
5. [Verification Checklist](#verification-checklist)
6. [Common Issues & Solutions](#common-issues--solutions)

---

## Understanding Demo Manifests

### What is a Demo Manifest?

A demo manifest (`DEMO_MANIFEST.md`) is a structured document that defines:
- **Account IDs** for specific demo scenarios
- **Journey patterns** (e.g., Critical → At-Risk → Healthy)
- **Health score ranges** over time
- **Use cases** for each account
- **Demo flow** steps

### Example Manifest Structure

```markdown
## 🎯 Quick Reference: Which Account for Which Demo?

### Critical → At-Risk → Healthy
**Use Case:** Demo turnaround success story
**Pattern:** Account starts in crisis, receives intervention, improves steadily
**Health Range:** 55 → 88

- **Account 29001** - CloudScale AI Labs
  - ARR: $1,900,199
  - Industry: Healthcare
  - CSM: Emily Watson
  - Region: US-West
```

### Journey Patterns

1. **Critical → At-Risk → Healthy** (Turnaround success)
2. **Healthy → At-Risk → Critical** (Early warning detection)
3. **Consistently Healthy** (Best practices)
4. **Persistently At-Risk** (Strategic intervention needed)
5. **Volatile / Unpredictable** (Signal detection)
6. **Plateau → Breakthrough** (QBR impact)
7. **High Churn Risk** (Churn prevention)
8. **New Customer Onboarding** (Onboarding success)

---

## Test Strategy

### Three-Tier Testing Approach

#### Tier 1: Data Generation & Validation
- ✅ Verify manifest accounts exist in database
- ✅ Verify journey data files are generated
- ✅ Validate health score progression matches manifest
- ✅ Check KPI data aligns with journey pattern

#### Tier 2: API & Backend Testing
- ✅ Test journey API endpoints return correct data
- ✅ Verify journey visualization data format
- ✅ Test health score calculations
- ✅ Validate milestone detection

#### Tier 3: Frontend & User Experience
- ✅ Test journey visualizer renders correctly
- ✅ Verify timeline progression
- ✅ Test interactive features
- ✅ Validate demo flow matches manifest description

---

## Test Setup

### Prerequisites

```bash
# 1. Ensure backend is running
cd kpi-dashboard/backend
python3 app_v3_minimal.py

# 2. Verify database connection
psql -U your_user -d your_database -c "SELECT COUNT(*) FROM accounts;"

# 3. Check journey data files exist
ls -la verticals/customer*/journey/wizard_a/outputs/*.json
```

### Environment Variables

```bash
export CUSTOMER_ID=19  # Or your demo customer ID
export OPENAI_API_KEY="your-key"  # For RAG/embeddings if needed
export DATABASE_URL="postgresql://user:pass@localhost/db"
```

---

## E2E Test Scripts

### Script 1: Manifest Validation Test

**File:** `test_manifest_validation.py`

```python
#!/usr/bin/env python3
"""
Validate Demo Manifest Accounts
Checks that all accounts in manifest exist and have correct data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app_v3_minimal import app, db
from models import Account, DC2SKPI, Customer
from datetime import datetime, timedelta
import json
from pathlib import Path

def get_customer_from_account(account_id):
    """Extract customer ID from account ID"""
    return int(account_id) // 1000

def find_journey_file(customer_id, account_id):
    """Find journey JSON file for account"""
    verticals_dir = Path(__file__).parent / "verticals"
    account_id_str = str(account_id)
    
    possible_dirs = [
        verticals_dir / f"customer{customer_id}-dc2_s",
        verticals_dir / f"customer{customer_id}-DC2_S",
    ]
    
    for customer_dir in possible_dirs:
        if not customer_dir.exists():
            continue
        
        outputs_dir = customer_dir / "journey" / "wizard_a" / "outputs"
        journey_file = outputs_dir / f"account_{account_id_str}_journey.json"
        
        if journey_file.exists():
            return journey_file
    
    return None

def validate_manifest_account(account_id, expected_pattern, expected_health_range):
    """Validate a single manifest account"""
    with app.app_context():
        account = Account.query.filter_by(account_id=account_id).first()
        
        if not account:
            return {
                'account_id': account_id,
                'status': 'FAIL',
                'error': 'Account not found in database'
            }
        
        # Check journey file exists
        customer_id = get_customer_from_account(account_id)
        journey_file = find_journey_file(customer_id, account_id)
        
        if not journey_file:
            return {
                'account_id': account_id,
                'status': 'FAIL',
                'error': 'Journey file not found'
            }
        
        # Load and validate journey data
        with open(journey_file, 'r') as f:
            journey_data = json.load(f)
        
        # Validate health score progression
        health_scores = []
        for event in journey_data.get('events', []):
            if 'health_score' in event:
                health_scores.append(event['health_score'])
        
        if not health_scores:
            return {
                'account_id': account_id,
                'status': 'FAIL',
                'error': 'No health scores in journey data'
            }
        
        min_health = min(health_scores)
        max_health = max(health_scores)
        
        # Check if health range matches expected
        expected_min, expected_max = expected_health_range
        health_match = (min_health <= expected_max and max_health >= expected_min)
        
        return {
            'account_id': account_id,
            'account_name': account.account_name,
            'status': 'PASS' if health_match else 'WARN',
            'health_range': (min_health, max_health),
            'expected_range': expected_health_range,
            'journey_file': str(journey_file),
            'events_count': len(journey_data.get('events', [])),
            'health_match': health_match
        }

def main():
    """Test all manifest accounts"""
    print("=" * 70)
    print("DEMO MANIFEST VALIDATION TEST")
    print("=" * 70)
    
    # Define manifest accounts (from DEMO_MANIFEST.md)
    manifest_accounts = [
        # Critical → At-Risk → Healthy
        (29001, "Critical → At-Risk → Healthy", (55, 88)),
        (29009, "Critical → At-Risk → Healthy", (55, 88)),
        (29017, "Critical → At-Risk → Healthy", (55, 88)),
        
        # Healthy → At-Risk → Critical
        (29002, "Healthy → At-Risk → Critical", (60, 90)),
        (29010, "Healthy → At-Risk → Critical", (60, 90)),
        (29018, "Healthy → At-Risk → Critical", (60, 90)),
        
        # Consistently Healthy
        (29003, "Consistently Healthy", (88, 92)),
        (29011, "Consistently Healthy", (88, 92)),
        (29019, "Consistently Healthy", (88, 92)),
        
        # Add more accounts as needed...
    ]
    
    results = []
    for account_id, pattern, health_range in manifest_accounts:
        result = validate_manifest_account(account_id, pattern, health_range)
        results.append(result)
        
        status_icon = "✅" if result['status'] == 'PASS' else "⚠️" if result['status'] == 'WARN' else "❌"
        print(f"\n{status_icon} Account {account_id}: {result['account_name']}")
        print(f"   Pattern: {pattern}")
        print(f"   Health Range: {result['health_range']} (Expected: {health_range})")
        if result['status'] != 'PASS':
            print(f"   Error: {result.get('error', 'Health range mismatch')}")
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in results if r['status'] == 'PASS')
    warned = sum(1 for r in results if r['status'] == 'WARN')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    
    print(f"✅ Passed: {passed}")
    print(f"⚠️  Warnings: {warned}")
    print(f"❌ Failed: {failed}")
    print(f"Total: {len(results)}")
    
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
```

### Script 2: Journey API E2E Test

**File:** `test_journey_api_e2e.py`

```python
#!/usr/bin/env python3
"""
E2E Test for Journey API Endpoints
Tests journey data retrieval and visualization
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = 'http://localhost:5059'

def test_journey_api(account_id, customer_id):
    """Test journey API endpoint"""
    print(f"\n🧪 Testing Journey API for Account {account_id}")
    
    # Test 1: Get journey data
    response = requests.get(
        f"{BASE_URL}/api/journey/{account_id}",
        headers={'X-Customer-ID': str(customer_id)},
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get journey data: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return False
    
    data = response.json()
    
    # Validate response structure
    required_fields = ['weeks', 'health_scores', 'events', 'milestones']
    missing_fields = [f for f in required_fields if f not in data]
    
    if missing_fields:
        print(f"❌ Missing required fields: {missing_fields}")
        return False
    
    # Validate data quality
    if not data.get('weeks'):
        print(f"❌ No weeks data")
        return False
    
    if not data.get('health_scores'):
        print(f"❌ No health scores")
        return False
    
    # Check health score progression
    health_scores = data['health_scores']
    min_health = min(health_scores.values())
    max_health = max(health_scores.values())
    
    print(f"✅ Journey data retrieved successfully")
    print(f"   Weeks: {len(data['weeks'])}")
    print(f"   Events: {len(data.get('events', []))}")
    print(f"   Milestones: {len(data.get('milestones', []))}")
    print(f"   Health Range: {min_health:.1f} - {max_health:.1f}")
    
    return True

def test_journey_visualization(account_id, customer_id):
    """Test journey visualization format"""
    print(f"\n🧪 Testing Journey Visualization for Account {account_id}")
    
    response = requests.get(
        f"{BASE_URL}/api/journey/{account_id}",
        headers={'X-Customer-ID': str(customer_id)},
        timeout=30
    )
    
    if response.status_code != 200:
        return False
    
    data = response.json()
    
    # Validate visualization format
    if 'weeks' not in data:
        print("❌ Missing 'weeks' in response")
        return False
    
    # Check week structure
    for week_num, week_data in list(data['weeks'].items())[:3]:  # Check first 3 weeks
        if 'health_score' not in week_data:
            print(f"❌ Week {week_num} missing health_score")
            return False
    
    print("✅ Visualization format valid")
    return True

def main():
    """Run E2E journey API tests"""
    print("=" * 70)
    print("JOURNEY API E2E TEST")
    print("=" * 70)
    
    # Test accounts from manifest
    test_accounts = [
        (29001, 29),  # Account ID, Customer ID
        (29002, 29),
        (29003, 29),
    ]
    
    results = []
    for account_id, customer_id in test_accounts:
        api_test = test_journey_api(account_id, customer_id)
        viz_test = test_journey_visualization(account_id, customer_id)
        
        results.append({
            'account_id': account_id,
            'api_test': api_test,
            'viz_test': viz_test,
            'overall': api_test and viz_test
        })
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results if r['overall'])
    total = len(results)
    
    for result in results:
        status = "✅" if result['overall'] else "❌"
        print(f"{status} Account {result['account_id']}: "
              f"API={result['api_test']}, Viz={result['viz_test']}")
    
    print(f"\nPassed: {passed}/{total}")
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
```

### Script 3: Complete Demo Flow Test

**File:** `test_demo_flow_e2e.py`

```python
#!/usr/bin/env python3
"""
Complete E2E Demo Flow Test
Tests entire demo scenario from manifest
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = 'http://localhost:5059'

def authenticate(email, password):
    """Authenticate and get session"""
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/login",
        json={'email': email, 'password': password},
        timeout=30
    )
    
    if response.status_code == 200:
        return session
    return None

def test_demo_scenario(session, account_id, scenario_name, expected_steps):
    """Test a complete demo scenario"""
    print(f"\n🎬 Testing Demo Scenario: {scenario_name}")
    print(f"   Account ID: {account_id}")
    
    # Step 1: Get account details
    print("\n   Step 1: Fetching account details...")
    response = session.get(
        f"{BASE_URL}/api/accounts",
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"   ❌ Failed to get accounts: {response.status_code}")
        return False
    
    accounts = response.json()
    account = next((a for a in accounts if a['account_id'] == account_id), None)
    
    if not account:
        print(f"   ❌ Account {account_id} not found")
        return False
    
    print(f"   ✅ Account found: {account['account_name']}")
    
    # Step 2: Get journey data
    print("\n   Step 2: Fetching journey data...")
    response = session.get(
        f"{BASE_URL}/api/journey/{account_id}",
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"   ❌ Failed to get journey: {response.status_code}")
        return False
    
    journey_data = response.json()
    print(f"   ✅ Journey data retrieved")
    print(f"      Weeks: {len(journey_data.get('weeks', {}))}")
    print(f"      Events: {len(journey_data.get('events', []))}")
    
    # Step 3: Verify health score progression
    print("\n   Step 3: Verifying health score progression...")
    health_scores = journey_data.get('health_scores', {})
    
    if not health_scores:
        print(f"   ❌ No health scores found")
        return False
    
    score_values = [float(v) for v in health_scores.values() if v is not None]
    min_score = min(score_values)
    max_score = max(score_values)
    
    print(f"   ✅ Health score range: {min_score:.1f} - {max_score:.1f}")
    
    # Step 4: Verify milestones
    print("\n   Step 4: Verifying milestones...")
    milestones = journey_data.get('milestones', [])
    print(f"   ✅ Found {len(milestones)} milestones")
    
    # Step 5: Verify events match pattern
    print("\n   Step 5: Verifying event pattern...")
    events = journey_data.get('events', [])
    
    # Check for expected event types based on scenario
    if scenario_name == "Turnaround Success":
        # Should have intervention events
        intervention_events = [e for e in events if 'intervention' in e.get('event_type', '').lower()]
        if not intervention_events:
            print(f"   ⚠️  No intervention events found (expected for turnaround)")
        else:
            print(f"   ✅ Found {len(intervention_events)} intervention events")
    
    print(f"\n   ✅ Demo scenario '{scenario_name}' completed successfully")
    return True

def main():
    """Run complete demo flow tests"""
    print("=" * 70)
    print("COMPLETE DEMO FLOW E2E TEST")
    print("=" * 70)
    
    # Authenticate
    print("\n🔐 Authenticating...")
    session = authenticate("test@example.com", "test123")
    
    if not session:
        print("❌ Authentication failed")
        return 1
    
    print("✅ Authenticated successfully")
    
    # Test scenarios from manifest
    demo_scenarios = [
        {
            'account_id': 29001,
            'name': 'Turnaround Success',
            'description': 'Critical → At-Risk → Healthy',
            'expected_steps': ['account_details', 'journey_data', 'health_progression', 'milestones']
        },
        {
            'account_id': 29002,
            'name': 'Early Warning Detection',
            'description': 'Healthy → At-Risk → Critical',
            'expected_steps': ['account_details', 'journey_data', 'health_progression', 'warning_signals']
        },
        {
            'account_id': 29003,
            'name': 'Best-in-Class Account',
            'description': 'Consistently Healthy',
            'expected_steps': ['account_details', 'journey_data', 'health_progression', 'advocacy_indicators']
        },
    ]
    
    results = []
    for scenario in demo_scenarios:
        result = test_demo_scenario(
            session,
            scenario['account_id'],
            scenario['name'],
            scenario['expected_steps']
        )
        results.append({
            'scenario': scenario['name'],
            'account_id': scenario['account_id'],
            'passed': result
        })
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    
    for result in results:
        status = "✅" if result['passed'] else "❌"
        print(f"{status} {result['scenario']} (Account {result['account_id']})")
    
    print(f"\nPassed: {passed}/{total}")
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
```

---

## Verification Checklist

### Pre-Demo Checklist

- [ ] All manifest accounts exist in database
- [ ] Journey JSON files generated for all accounts
- [ ] Health scores match expected ranges
- [ ] Journey API endpoints return correct data
- [ ] Frontend visualizer loads without errors
- [ ] Demo flow steps work as documented

### During Demo Checklist

- [ ] Account selection works
- [ ] Journey timeline renders correctly
- [ ] Health score progression visible
- [ ] Milestones display properly
- [ ] Events show correct timeline
- [ ] Interactive features work (zoom, filter, etc.)

### Post-Demo Checklist

- [ ] All demo scenarios tested
- [ ] No console errors
- [ ] Performance acceptable (< 2s load time)
- [ ] Data accuracy verified
- [ ] Documentation updated

---

## Common Issues & Solutions

### Issue 1: Journey File Not Found

**Error:** `Journey file not found for account {account_id}`

**Solution:**
```bash
# Check if journey files exist
ls -la verticals/customer*/journey/wizard_a/outputs/*.json

# Regenerate journey data if missing
cd verticals/customer19-dc2_s/journey/wizard_a
python3 wizard_milestone_generator.py
```

### Issue 2: Health Score Mismatch

**Error:** Health scores don't match manifest expectations

**Solution:**
```bash
# Verify KPI data exists
psql -d your_db -c "SELECT COUNT(*) FROM dc2s_kpis WHERE account_id = 29001;"

# Recalculate health scores
python3 backend/scripts/recalculate_health_scores.py --account-id 29001
```

### Issue 3: API Returns 404

**Error:** `/api/journey/{account_id}` returns 404

**Solution:**
```bash
# Check account exists
psql -d your_db -c "SELECT account_id, account_name FROM accounts WHERE account_id = 29001;"

# Verify customer_id calculation
# Account 29001 → Customer 29 (29001 // 1000)

# Check journey API registration
grep -r "journey_api" backend/app_v3_minimal.py
```

### Issue 4: Frontend Visualization Broken

**Error:** Journey visualizer doesn't render

**Solution:**
```bash
# Check API response format
curl -H "X-Customer-ID: 29" http://localhost:5059/api/journey/29001 | jq '.weeks | keys | length'

# Verify frontend component
grep -r "JourneyVisualizer" kpi-dashboard/src/components/

# Check browser console for errors
# Open DevTools → Console tab
```

---

## Best Practices

### 1. Test Data Isolation

Always use dedicated demo accounts (29001-29020) for testing. Never use production accounts.

### 2. Version Control

Keep manifest files in version control:
```bash
git add backend/customer19_synthetic_data/DEMO_MANIFEST.md
git commit -m "Update demo manifest with new accounts"
```

### 3. Automated Testing

Run E2E tests before each demo:
```bash
# Run all journey tests
python3 backend/test_manifest_validation.py
python3 backend/test_journey_api_e2e.py
python3 backend/test_demo_flow_e2e.py
```

### 4. Documentation

Update manifest when adding new demo scenarios:
- Add account to manifest
- Document expected pattern
- Add to test scripts
- Update demo flow documentation

### 5. Performance Monitoring

Monitor API response times:
```bash
# Time journey API call
time curl -H "X-Customer-ID: 29" http://localhost:5059/api/journey/29001
```

---

## Quick Reference

### Run All Tests

```bash
cd kpi-dashboard/backend

# 1. Validate manifest
python3 test_manifest_validation.py

# 2. Test API endpoints
python3 test_journey_api_e2e.py

# 3. Test complete demo flow
python3 test_demo_flow_e2e.py
```

### Check Specific Account

```bash
# Check account exists
psql -d your_db -c "SELECT * FROM accounts WHERE account_id = 29001;"

# Check journey file
ls -la verticals/customer29-dc2_s/journey/wizard_a/outputs/account_29001_journey.json

# Test API
curl -H "X-Customer-ID: 29" http://localhost:5059/api/journey/29001 | jq
```

### Regenerate Journey Data

```bash
cd verticals/customer19-dc2_s/journey/wizard_a
python3 wizard_milestone_generator.py
```

---

## Summary

This guide provides a comprehensive approach to testing end-to-end demo manifest-based journeys:

1. **Validate** manifest accounts exist and have correct data
2. **Test** API endpoints return expected format
3. **Verify** complete demo flows work as documented
4. **Monitor** performance and data accuracy

For questions or issues, refer to the troubleshooting section or check the journey API implementation in `journey_api_dynamic.py`.
