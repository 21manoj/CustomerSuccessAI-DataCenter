#!/usr/bin/env python3
"""
Test script for Customer 17 Journey API
"""

import sys
import os
from pathlib import Path

# Add the journey directory to path
sys.path.insert(0, str(Path(__file__).parent))

from customer17_journey_api import find_latest_test_run, load_journey_json, convert_to_weekly_format

def test_find_latest_test_run():
    """Test finding the latest test run"""
    print('Test 1: Finding latest test run...')
    test_run = find_latest_test_run()
    if test_run:
        print(f'✅ Found test run: {test_run}')
        return True
    else:
        print('❌ No test run found')
        return False

def test_load_journey_json():
    """Test loading journey JSON"""
    print('\nTest 2: Loading journey JSON for account 90001...')
    journey_data = load_journey_json('90001')
    if journey_data:
        print(f'✅ Loaded journey data for account: {journey_data.get("account_id")}')
        print(f'   Account name: {journey_data.get("account_name")}')
        print(f'   Pattern type: {journey_data.get("pattern_type")}')
        print(f'   Total weeks: {journey_data.get("total_weeks")}')
        print(f'   Total events: {len(journey_data.get("events", []))}')
        print(f'   Starting health: {journey_data.get("starting_health")}')
        print(f'   Ending health: {journey_data.get("ending_health")}')
        return journey_data
    else:
        print('❌ Failed to load journey data')
        return None

def test_convert_to_weekly_format(journey_data):
    """Test converting to weekly format"""
    print('\nTest 3: Converting to weekly format...')
    weekly_data = convert_to_weekly_format(journey_data)
    if weekly_data:
        print(f'✅ Converted to {len(weekly_data)} weeks')
        print(f'   First week: Week {weekly_data[0]["week_number"]}, Health: {weekly_data[0]["health_score"]:.2f}, Phase: {weekly_data[0]["phase"]}')
        print(f'   Last week: Week {weekly_data[-1]["week_number"]}, Health: {weekly_data[-1]["health_score"]:.2f}, Phase: {weekly_data[-1]["phase"]}')
        
        # Check a week with events
        week_with_events = next((w for w in weekly_data if w.get('events')), None)
        if week_with_events:
            print(f'   Week {week_with_events["week_number"]} has {len(week_with_events["events"])} events')
            print(f'   Sample event: {week_with_events["events"][0]["event_type"]} - {week_with_events["events"][0]["description"][:50]}...')
        
        # Check weeks with health scores
        weeks_with_health = [w for w in weekly_data if w.get('health_score', 0) > 0]
        print(f'   Weeks with health data: {len(weeks_with_health)}/{len(weekly_data)}')
        
        return weekly_data
    else:
        print('❌ Failed to convert to weekly format')
        return None

def test_list_accounts():
    """Test listing accounts"""
    print('\nTest 4: Testing list accounts endpoint logic...')
    from customer17_journey_api import find_latest_test_run
    import json
    
    test_run_dir = find_latest_test_run()
    if not test_run_dir:
        print('❌ No test run found')
        return False
    
    data_dir = test_run_dir / "data"
    if not data_dir.exists():
        print('❌ Data directory not found')
        return False
    
    accounts = []
    for journey_file in data_dir.glob('account_*_journey.json'):
        account_id = journey_file.stem.replace('account_', '').replace('_journey', '')
        try:
            with open(journey_file, 'r') as f:
                journey_data = json.load(f)
            accounts.append({
                'account_id': journey_data.get('account_id', account_id),
                'account_name': journey_data.get('account_name', f'Account {account_id}'),
            })
        except Exception as e:
            print(f'   ⚠️  Error loading {journey_file}: {e}')
            continue
    
    print(f'✅ Found {len(accounts)} accounts:')
    for acc in accounts:
        print(f'   - {acc["account_id"]}: {acc["account_name"]}')
    
    return len(accounts) > 0

if __name__ == '__main__':
    print('=' * 60)
    print('Customer 17 Journey API Test Suite')
    print('=' * 60)
    
    # Test 1
    if not test_find_latest_test_run():
        sys.exit(1)
    
    # Test 2
    journey_data = test_load_journey_json()
    if not journey_data:
        sys.exit(1)
    
    # Test 3
    weekly_data = test_convert_to_weekly_format(journey_data)
    if not weekly_data:
        sys.exit(1)
    
    # Test 4
    if not test_list_accounts():
        sys.exit(1)
    
    print('\n' + '=' * 60)
    print('✅ All tests passed!')
    print('=' * 60)
