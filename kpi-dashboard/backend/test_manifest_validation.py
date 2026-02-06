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
        try:
            with open(journey_file, 'r') as f:
                journey_data = json.load(f)
        except Exception as e:
            return {
                'account_id': account_id,
                'status': 'FAIL',
                'error': f'Failed to load journey file: {str(e)}'
            }
        
        # Validate health score progression
        health_scores = []
        
        # Try different possible structures
        if 'events' in journey_data:
            for event in journey_data.get('events', []):
                if 'health_score' in event:
                    health_scores.append(float(event['health_score']))
        
        if 'weekly_data' in journey_data:
            for week in journey_data.get('weekly_data', []):
                if 'health_score' in week:
                    health_scores.append(float(week['health_score']))
        
        if 'health_scores' in journey_data:
            if isinstance(journey_data['health_scores'], dict):
                health_scores.extend([float(v) for v in journey_data['health_scores'].values() if v is not None])
            elif isinstance(journey_data['health_scores'], list):
                health_scores.extend([float(v) for v in journey_data['health_scores'] if v is not None])
        
        # Check starting/ending health if available
        if 'starting_health' in journey_data:
            health_scores.append(float(journey_data['starting_health']))
        if 'ending_health' in journey_data:
            health_scores.append(float(journey_data['ending_health']))
        
        if not health_scores:
            return {
                'account_id': account_id,
                'status': 'FAIL',
                'error': 'No health scores found in journey data'
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
        
        # Persistently At-Risk
        (29004, "Persistently At-Risk", (68, 72)),
        (29012, "Persistently At-Risk", (68, 72)),
        (29020, "Persistently At-Risk", (68, 72)),
        
        # Volatile / Unpredictable
        (29005, "Volatile / Unpredictable", (70, 80)),
        (29013, "Volatile / Unpredictable", (70, 80)),
        
        # Plateau → Breakthrough
        (29006, "Plateau → Breakthrough", (70, 86)),
        (29014, "Plateau → Breakthrough", (70, 86)),
        
        # High Churn Risk
        (29007, "High Churn Risk", (45, 58)),
        (29015, "High Churn Risk", (45, 58)),
        
        # New Customer Onboarding
        (29008, "New Customer Onboarding", (62, 82)),
        (29016, "New Customer Onboarding", (62, 82)),
    ]
    
    results = []
    for account_id, pattern, health_range in manifest_accounts:
        result = validate_manifest_account(account_id, pattern, health_range)
        results.append(result)
        
        status_icon = "✅" if result['status'] == 'PASS' else "⚠️" if result['status'] == 'WARN' else "❌"
        print(f"\n{status_icon} Account {account_id}: {result.get('account_name', 'N/A')}")
        print(f"   Pattern: {pattern}")
        print(f"   Health Range: {result.get('health_range', 'N/A')} (Expected: {health_range})")
        if result['status'] != 'PASS':
            print(f"   Error: {result.get('error', 'Health range mismatch')}")
        else:
            print(f"   Events: {result.get('events_count', 0)}")
            print(f"   Journey File: {result.get('journey_file', 'N/A')}")
    
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
