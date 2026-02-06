"""
Customer 9 Journey API Adapter
===============================

Serves journey data from JSON files to the frontend JourneyVisualizerV2 component.
Reads from wizard_a test_run directories and converts to the expected API format.

Endpoint: GET /api/journey/<account_id>
"""

from flask import Blueprint, jsonify
from pathlib import Path
import json
import os
import csv
from collections import defaultdict
from datetime import datetime, timedelta

journey_api_c9 = Blueprint('journey_api_c9', __name__, url_prefix='/api/journey')

# Base path to customer 9 journey data
# Use absolute path resolution to ensure it works when imported by Flask
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
C9_JOURNEY_BASE = BASE_DIR / "verticals/customer9-dc2_s/journey/wizard_a"
C9_DATA_DIR = BASE_DIR / "verticals/customer9-dc2_s/data"

# Find the most recent test_run directory
def find_latest_test_run():
    """Find the most recent test_run directory"""
    if not C9_JOURNEY_BASE.exists():
        return None
    
    test_runs = []
    for item in C9_JOURNEY_BASE.iterdir():
        if item.is_dir() and item.name.startswith('test_run_'):
            test_runs.append((item.stat().st_mtime, item))
    
    if not test_runs:
        return None
    
    # Return the most recent
    test_runs.sort(reverse=True)
    return test_runs[0][1]


# Mapping from Customer 9 account IDs (10001, 10003, etc.) to journey JSON account IDs (90001, 90003, etc.)
# Pattern: Extract last 4 digits of account ID and prepend 9
# Account 10001 -> Journey 90001, Account 10003 -> Journey 90003
def account_id_to_journey_id(account_id):
    """Convert Customer 9 account ID to journey JSON ID"""
    account_id_str = str(account_id)
    if len(account_id_str) >= 5:
        # Extract last 4 digits (e.g., 10001 -> 0001, 10003 -> 0003)
        last_4 = account_id_str[-4:]
        # Prepend 9 to get journey ID (e.g., 90001, 90003)
        journey_id = f"9{last_4}"
        return journey_id
    return None


def load_journey_json(account_id):
    """
    Load journey JSON file for an account.
    Maps Customer 9 account IDs (10001, 10003, etc.) to journey JSON IDs (90001, 90003, etc.)
    """
    test_run_dir = find_latest_test_run()
    if not test_run_dir:
        print(f"[DEBUG customer9_journey_api] No test_run directory found. C9_JOURNEY_BASE: {C9_JOURNEY_BASE}")
        return None
    
    # Check if files are in test_run/data/ or directly in test_run/
    data_dir = test_run_dir / "data"
    if not data_dir.exists():
        # Files might be directly in test_run directory (newer format)
        data_dir = test_run_dir
    
    # Try to find the journey JSON file
    # First try with actual account ID (newer format: account_10001_journey.json)
    journey_file = data_dir / f"account_{account_id}_journey.json"
    
    # If not found, try with journey ID mapping (older format: account_90001_journey.json)
    if not journey_file.exists():
        journey_id = account_id_to_journey_id(account_id)
        if journey_id:
            journey_file = data_dir / f"account_{journey_id}_journey.json"
    
    print(f"[DEBUG customer9_journey_api] Looking for account_id: {account_id}")
    print(f"[DEBUG customer9_journey_api] Trying file: {journey_file}")
    print(f"[DEBUG customer9_journey_api] File exists: {journey_file.exists()}")
    print(f"[DEBUG customer9_journey_api] Absolute path: {journey_file.resolve()}")
    
    if not journey_file.exists():
        # List available files for debugging
        if data_dir.exists():
            available_files = list(data_dir.glob("account_*_journey.json"))
            print(f"[DEBUG customer9_journey_api] Available files: {[f.name for f in available_files[:10]]}")
        return None
    
    with open(journey_file, 'r') as f:
        journey_data = json.load(f)
        # Update account_id in the data to match the requested account ID
        journey_data['account_id'] = str(account_id)
        
        # Get the real account name from accounts.csv
        accounts_file = C9_DATA_DIR / "accounts.csv"
        if accounts_file.exists():
            try:
                with open(accounts_file, 'r') as af:
                    reader = csv.DictReader(af)
                    for row in reader:
                        if str(row.get('account_id')) == str(account_id):
                            journey_data['account_name'] = row.get('account_name', f'Account {account_id}')
                            break
            except Exception as e:
                print(f"Warning: Could not load account name from CSV: {e}")
        
        return journey_data


def date_to_week_number(date_str, start_date_str):
    """Convert a date string to week number based on journey start date"""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        days_diff = (date - start_date).days
        week_num = (days_diff // 7) + 1
        return max(1, week_num)  # Ensure at least week 1
    except:
        return None


def convert_to_weekly_format(journey_data):
    """
    Convert journey JSON format to frontend visualizer format.
    Similar to Customer 17's format conversion.
    """
    if not journey_data:
        return None
    
    # Group events by week
    events_by_week = defaultdict(list)
    health_by_week = {}
    phases_by_week = {}
    dates_by_week = {}
    
    for event in journey_data.get('events', []):
        week_num = event.get('week_number')
        if week_num:
            events_by_week[week_num].append({
                'event_type': event.get('event_type'),
                'description': event.get('description'),
                'sentiment': event.get('sentiment'),
                'date': event.get('date'),
                'health_impact': event.get('health_score_after', 0) - event.get('health_score_before', 0)
            })
            
            # Use the health_score_after as the health for that week
            if week_num not in health_by_week:
                health_by_week[week_num] = event.get('health_score_after', 0)
                phases_by_week[week_num] = event.get('phase', 'unknown')
                dates_by_week[week_num] = event.get('date', '')
    
    # Build weekly_data array
    weekly_data = []
    
    # Get all weeks from start to end
    total_weeks = journey_data.get('total_weeks', 52)
    start_date = journey_data.get('start_date', '2024-01-01')
    
    # Get starting health for interpolation
    starting_health = journey_data.get('starting_health', 0)
    ending_health = journey_data.get('ending_health', 0)
    
    for week_num in range(1, total_weeks + 1):
        # Get health score for this week (use after score from events, or interpolate)
        health_score = health_by_week.get(week_num)
        
        # If no event for this week, interpolate from surrounding weeks
        if health_score is None:
            # Find the most recent week with health data before or at this week
            previous_weeks = [w for w in sorted(health_by_week.keys()) if w <= week_num]
            if previous_weeks:
                # Use the most recent week's health
                health_score = health_by_week[previous_weeks[-1]]
            else:
                # No events before this week, use starting health
                health_score = starting_health
            
            # If still None (shouldn't happen), use ending health
            if health_score is None:
                health_score = ending_health
        
        week_entry = {
            'week_number': week_num,
            'date': dates_by_week.get(week_num, start_date),
            'health_score': float(health_score) if health_score else 0,
            'phase': phases_by_week.get(week_num, 'unknown'),
            'events': events_by_week.get(week_num, []),
            'raw_kpis': {},
            'normalized_kpis': {},
            'kpis': {},  # V1 compatibility
            'pillar_scores': {},
            'pillars': {},  # Alias for compatibility
            'data_quality': 0.0,
            'coverage_pct': 0.0,
            'available_kpis': [],
            'missing_kpis': [],
            'signals': []
        }
        
        weekly_data.append(week_entry)
    
    return weekly_data


@journey_api_c9.route('/<account_id>', methods=['GET'])
def get_account_journey(account_id):
    """
    Get full journey data for an account.
    This is the main endpoint used by JourneyVisualizerV2.
    
    Only handles Customer 9 account IDs (10001-19999 range).
    Customer 17 account IDs (17001-17999) are handled by customer17_journey_api.
    """
    try:
        # Check if this is a Customer 9 account ID (10001-19999 range)
        # Since Customer 9 API is registered first, it will handle Customer 9 accounts
        # Customer 17 accounts (17001-17999) will fall through to Customer 17's API
        try:
            account_id_int = int(account_id)
            # Customer 9 accounts are in range 10001-19999
            # But Customer 17 also uses 17001-17999, so we need to exclude that range
            if account_id_int < 10001 or account_id_int >= 20000:
                # Not a Customer 9 account, abort so Flask can try Customer 17's route
                from flask import abort
                abort(404)
            # Exclude Customer 17 accounts (17001-17999) and Customer 56 accounts (56001-56999)
            if 17001 <= account_id_int <= 17999:
                # This is a Customer 17 account, abort so Customer 17's API handles it
                from flask import abort
                abort(404)
            if 56001 <= account_id_int <= 56999:
                # This is a Customer 56 account, abort so Customer 56's API handles it
                from flask import abort
                abort(404)
        except ValueError:
            # Invalid account ID format
            return jsonify({
                'error': 'Invalid account ID format',
                'message': f'Account ID must be a number'
            }), 400
        
        # Load journey JSON
        journey_data = load_journey_json(account_id)
        
        if not journey_data:
            return jsonify({
                'error': f'Account {account_id} journey data not found',
                'message': 'No journey JSON file found for this account. This account may not have journey data generated yet.'
            }), 404
        
        # Convert to weekly format
        weekly_data = convert_to_weekly_format(journey_data)
        
        if not weekly_data:
            return jsonify({
                'error': 'Failed to convert journey data',
                'message': 'Could not process journey JSON format'
            }), 500
        
        # Get real account name from accounts.csv if available
        account_name = journey_data.get('account_name', f'Account {account_id}')
        
        # Build response
        response = {
            'account_id': str(account_id),  # Use requested account_id
            'account_name': account_name,
            'pattern_type': journey_data.get('pattern_type', 'unknown'),
            'total_weeks': journey_data.get('total_weeks', len(weekly_data)),
            'starting_health': float(journey_data.get('starting_health', 0)),
            'ending_health': float(journey_data.get('ending_health', 0)),
            'weekly_data': weekly_data,
            'signals': [],  # Could be populated from CSV if needed
            'summary': {
                'total_events': len(journey_data.get('events', [])),
                'total_kpi_readings': 0,
                'total_signals': 0,
                'weeks_with_data': len([w for w in weekly_data if w.get('events')]),
                'lowest_health': float(journey_data.get('lowest_health', 0)),
                'highest_health': float(journey_data.get('highest_health', 0))
            }
        }
        
        # Add summary data if available
        if 'summary' in journey_data:
            response['journey_summary'] = journey_data['summary']
        
        return jsonify(response)
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'message': f'Failed to load journey data: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500


@journey_api_c9.route('/accounts', methods=['GET'])
def list_journey_accounts():
    """
    List all accounts that have journey data.
    """
    try:
        test_run_dir = find_latest_test_run()
        if not test_run_dir:
            return jsonify({
                'accounts': [],
                'total': 0,
                'message': 'No test run directories found'
            })
        
        # Check if files are in test_run/data/ or directly in test_run/
        data_dir = test_run_dir / "data"
        if not data_dir.exists():
            # Files might be directly in test_run directory (newer format)
            data_dir = test_run_dir
        
        accounts = []
        for journey_file in data_dir.glob('account_*_journey.json'):
            journey_id = journey_file.stem.replace('account_', '').replace('_journey', '')
            
            try:
                with open(journey_file, 'r') as f:
                    journey_data = json.load(f)
                
                # Convert journey ID back to account ID (90001 -> 10001)
                journey_id_int = int(journey_id)
                if journey_id_int >= 90000:
                    account_id = journey_id_int - 80000  # 90001 - 80000 = 10001
                else:
                    account_id = journey_id_int
                
                accounts.append({
                    'account_id': str(account_id),
                    'account_name': journey_data.get('account_name', f'Account {account_id}'),
                    'pattern_type': journey_data.get('pattern_type', 'unknown'),
                    'total_weeks': journey_data.get('total_weeks', 0),
                    'starting_health': float(journey_data.get('starting_health', 0)),
                    'ending_health': float(journey_data.get('ending_health', 0)),
                    'final_outcome': journey_data.get('summary', {}).get('final_outcome')
                })
            except Exception as e:
                print(f"Error loading {journey_file}: {e}")
                continue
        
        return jsonify({
            'accounts': accounts,
            'total': len(accounts)
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@journey_api_c9.route('/<account_id>/signals', methods=['GET'])
def get_journey_signals(account_id):
    """Get journey signals for an account"""
    try:
        journey_data = load_journey_json(account_id)
        
        if journey_data is None:
            return jsonify({
                'error': 'Journey data not found',
                'message': f'No journey JSON file found for account {account_id}'
            }), 404
        
        # Extract signals from events
        signals = []
        if 'events' in journey_data:
            for event in journey_data['events']:
                signals.append({
                    'week_number': event.get('week_number'),
                    'date': event.get('date'),
                    'phase': event.get('phase'),
                    'event_type': event.get('event_type'),
                    'description': event.get('description'),
                    'sentiment': event.get('sentiment'),
                    'sentiment_score': event.get('sentiment_value', 0),
                    'health_score_before': event.get('health_score_before'),
                    'health_score_after': event.get('health_score_after'),
                })
        
        return jsonify({
            'account_id': str(account_id),
            'account_name': journey_data.get('account_name'),
            'signals': signals,
            'total': len(signals)
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to load journey signals',
            'message': str(e)
        }), 500
