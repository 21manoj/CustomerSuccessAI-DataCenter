"""
Customer 17 Journey API Adapter
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

journey_api_c17 = Blueprint('journey_api_c17', __name__, url_prefix='/api/journey')

# Base path to customer 17 journey data
BASE_DIR = Path(__file__).parent.parent.parent.parent
C17_JOURNEY_BASE = BASE_DIR / "verticals/customer17-dc2_s/journey/wizard_a"
C17_DATA_DIR = BASE_DIR / "verticals/customer17-dc2_s/data"

# Find the most recent test_run directory
def find_latest_test_run():
    """Find the most recent test_run directory"""
    if not C17_JOURNEY_BASE.exists():
        return None
    
    test_runs = []
    for item in C17_JOURNEY_BASE.iterdir():
        if item.is_dir() and item.name.startswith('test_run_'):
            test_runs.append((item.stat().st_mtime, item))
    
    if not test_runs:
        return None
    
    # Return the most recent
    test_runs.sort(reverse=True)
    return test_runs[0][1]


# Mapping from customer 17 account IDs to journey JSON account IDs
# Based on the actual data files available
ACCOUNT_ID_MAPPING = {
    '17001': '90001',  # AI Compute Corp -> Account 90001
    '17002': None,     # CloudScale Dynamics - no journey data yet
    '17003': '90003',  # DataForge Systems -> Account 90003
    '17004': '90004',  # NeuralNet Industries -> Account 90004
    '17005': '90005',  # If exists -> Account 90005
}

def load_journey_json(account_id):
    """
    Load journey JSON file for an account.
    Handles both account ID formats:
    - Customer 17 format: 17001, 17002, etc.
    - Journey JSON format: 90001, 90003, etc.
    
    Maps customer 17 account IDs to journey JSON account IDs.
    """
    test_run_dir = find_latest_test_run()
    if not test_run_dir:
        return None
    
    data_dir = test_run_dir / "data"
    
    # Check if we need to map the account ID
    mapped_id = ACCOUNT_ID_MAPPING.get(account_id, account_id)
    
    # If mapping says None, account has no journey data
    if mapped_id is None:
        return None
    
    # Try the mapped ID (or original if no mapping needed)
    journey_file = data_dir / f"account_{mapped_id}_journey.json"
    
    if not journey_file.exists():
        return None
    
    with open(journey_file, 'r') as f:
        journey_data = json.load(f)
        # Update account_id in the data to match the requested ID (for customer 17 format)
        if account_id.startswith('17') and journey_data.get('account_id') != account_id:
            journey_data['account_id'] = account_id
            # Get the real account name from accounts.csv
            accounts_file = C17_DATA_DIR / "accounts.csv"
            if accounts_file.exists():
                try:
                    with open(accounts_file, 'r') as af:
                        reader = csv.DictReader(af)
                        for row in reader:
                            if row.get('account_id') == account_id:
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


def load_kpi_data(account_id, start_date_str):
    """Load KPI measurements from CSV and group by week"""
    kpi_file = C17_DATA_DIR / "kpi_measurements.csv"
    if not kpi_file.exists():
        return {}
    
    kpis_by_week = defaultdict(lambda: {'raw': {}, 'normalized': {}})
    
    try:
        with open(kpi_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('account_id') == account_id:
                    date_str = row.get('date', '')
                    week_num = date_to_week_number(date_str, start_date_str)
                    if week_num:
                        kpi_code = row.get('kpi_code', '')
                        value = float(row.get('value', 0)) if row.get('value') else 0
                        unit = row.get('unit', '')
                        
                        # Store raw value
                        kpis_by_week[week_num]['raw'][kpi_code] = {
                            'value': value,
                            'unit': unit
                        }
                        
                        # Normalize value (simple normalization: use value as score if < 100, otherwise scale)
                        # This is a simplified approach - in production you'd use proper normalization
                        normalized = value if value <= 100 else (value / 10)  # Rough normalization
                        kpis_by_week[week_num]['normalized'][kpi_code] = normalized
    except Exception as e:
        print(f"Error loading KPI data: {e}")
    
    return kpis_by_week


def load_signals_data(account_id, start_date_str):
    """Load qualitative signals from CSV and group by week"""
    signals_file = C17_DATA_DIR / "qualitative_signals.csv"
    if not signals_file.exists():
        return {}
    
    signals_by_week = defaultdict(list)
    
    try:
        with open(signals_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('account_id') == account_id:
                    date_str = row.get('signal_date', '')
                    week_num = date_to_week_number(date_str, start_date_str)
                    if week_num:
                        signals_by_week[week_num].append({
                            'signal_id': row.get('signal_id', ''),
                            'date': date_str,
                            'week_number': week_num,  # Add week_number
                            'signal_type': row.get('signal_type', ''),
                            'source': row.get('signal_type', ''),  # Use signal_type as source
                            'from_contact': row.get('stakeholder_title', ''),
                            'to_contact': row.get('stakeholder_title', ''),
                            'subject': row.get('content', '')[:50] if row.get('content') else '',  # Truncate
                            'summary': row.get('content', ''),
                            'sentiment': row.get('sentiment', 'neutral'),
                            'sentiment_score': float(row.get('sentiment_score', 0)) if row.get('sentiment_score') else 0,
                            'priority': 'critical' if abs(float(row.get('sentiment_score', 0) or 0)) > 0.8 else ('high' if abs(float(row.get('sentiment_score', 0) or 0)) > 0.5 else 'medium'),
                            'keywords': row.get('keywords', '').split(',') if row.get('keywords') else []
                        })
    except Exception as e:
        print(f"Error loading signals data: {e}")
    
    return signals_by_week


def convert_to_weekly_format(journey_data):
    """
    Convert customer 17 journey JSON format to frontend visualizer format.
    
    Input format (customer 17):
    {
        "account_id": "90001",
        "events": [
            {
                "week_number": 5,
                "date": "2024-01-29",
                "phase": "crisis",
                "health_score_before": 90.14,
                "health_score_after": 35.14,
                "event_type": "support_ticket",
                ...
            }
        ]
    }
    
    Output format (frontend expects):
    {
        "weekly_data": [
            {
                "week_number": 5,
                "date": "2024-01-29",
                "health_score": 35.14,
                "phase": "crisis",
                "events": [...],
                "raw_kpis": {},
                "normalized_kpis": {},
                "pillars": {}
            }
        ]
    }
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
    account_id = journey_data.get('account_id', '')
    
    # Load KPI and signals data
    # Use the original account_id (17001 format) for loading from CSV files
    # The journey_data account_id might be mapped (90001), so we need to reverse map
    original_account_id = account_id
    if account_id.startswith('9'):
        # Reverse mapping: find which customer 17 account this maps to
        for c17_id, mapped_id in ACCOUNT_ID_MAPPING.items():
            if mapped_id == account_id:
                original_account_id = c17_id
                break
    
    kpis_by_week = load_kpi_data(original_account_id, start_date)
    signals_by_week = load_signals_data(original_account_id, start_date)
    
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
        
        # Get KPI data for this week
        week_kpis = kpis_by_week.get(week_num, {})
        raw_kpis = week_kpis.get('raw', {})
        normalized_kpis = week_kpis.get('normalized', {})
        
        # Get signals for this week
        week_signals = signals_by_week.get(week_num, [])
        
        # Calculate data quality metrics
        available_kpis = list(normalized_kpis.keys())
        coverage_pct = (len(available_kpis) / 35.0 * 100) if available_kpis else 0.0  # 35 KPIs total based on metadata
        data_quality = min(1.0, coverage_pct / 100.0)
        
        # Calculate pillar scores from KPIs
        # DC2_S 5-Pillar Model: P1=Infrastructure, P2=Operational, P3=Revenue, P4=Customer, P5=Strategic
        # Based on actual KPI prefixes: AI, CH, DV, EX, OS
        pillar_scores = {}
        pillar_kpi_mapping = {
            'Infrastructure Health': ['DV', 'OS'],      # Device, OS KPIs
            'Operational Efficiency': ['AI', 'OP', 'UT', 'TH'],  # AI, Operations, Utilization, Throughput
            'Revenue Protection': ['RV', 'MG', 'BL'],  # Revenue, Margin, Billing
            'Customer Success': ['CH', 'CS', 'AD', 'EN'],  # Champion, Customer Success, Adoption, Engagement
            'Strategic Growth': ['EX', 'GR', 'ST']      # Expansion, Growth, Strategic
        }
        
        def normalize_value(value):
            """Normalize KPI value to 0-100 range"""
            if not isinstance(value, (int, float)):
                return None
            # If already in 0-100 range, use as-is
            if 0 <= value <= 100:
                return value
            # If > 100, scale down (assume it's a raw metric that needs normalization)
            # For now, cap at 100 if > 100
            return min(100.0, max(0.0, value))
        
        for pillar_name, kpi_prefixes in pillar_kpi_mapping.items():
            pillar_kpis = [kpi for kpi in normalized_kpis.keys() 
                          if any(kpi.startswith(prefix + '-') for prefix in kpi_prefixes)]
            if pillar_kpis:
                pillar_values = [normalize_value(normalized_kpis[kpi]) for kpi in pillar_kpis]
                pillar_values = [v for v in pillar_values if v is not None]
                if pillar_values:
                    # Calculate average
                    avg_score = sum(pillar_values) / len(pillar_values)
                    pillar_scores[pillar_name] = round(avg_score, 2)
                else:
                    pillar_scores[pillar_name] = 0.0
            else:
                pillar_scores[pillar_name] = 0.0
        
        week_entry = {
            'week_number': week_num,
            'date': dates_by_week.get(week_num, start_date),  # Will need date calculation
            'health_score': float(health_score) if health_score else 0,
            'phase': phases_by_week.get(week_num, 'unknown'),
            'events': events_by_week.get(week_num, []),
            'raw_kpis': raw_kpis,
            'normalized_kpis': normalized_kpis,
            'kpis': normalized_kpis,  # V1 compatibility
            'pillar_scores': pillar_scores,  # Add calculated pillar scores
            'pillars': pillar_scores,  # Alias for compatibility
            'data_quality': data_quality,
            'coverage_pct': coverage_pct,
            'available_kpis': available_kpis,
            'missing_kpis': [],  # Could calculate from expected KPIs
            'signals': week_signals  # Add signals to weekly data
        }
        
        weekly_data.append(week_entry)
    
    return weekly_data


@journey_api_c17.route('/<account_id>', methods=['GET'])
def get_account_journey(account_id):
    """
    Get full journey data for an account.
    This is the main endpoint used by JourneyVisualizerV2.
    Only handles Customer 17 accounts (17001-17999).
    """
    try:
        # Only handle Customer 17 accounts (start with 17)
        account_id_str = str(account_id)
        if not account_id_str.startswith('17'):
            # This account doesn't belong to Customer 17, let other journey APIs handle it
            return jsonify({
                'error': 'Account not found for Customer 17',
                'message': f'Account {account_id} does not belong to Customer 17'
            }), 404
        
        # Load journey JSON
        journey_data = load_journey_json(account_id_str)
        
        if not journey_data:
            return jsonify({
                'error': f'Account {account_id} journey data not found',
                'message': 'No journey JSON file found for this account'
            }), 404
        
        # Convert to weekly format
        weekly_data = convert_to_weekly_format(journey_data)
        
        if not weekly_data:
            return jsonify({
                'error': 'Failed to convert journey data',
                'message': 'Could not process journey JSON format'
            }), 500
        
        # Collect all signals from weekly data for separate signals array
        all_signals = []
        for week in weekly_data:
            for signal in week.get('signals', []):
                all_signals.append(signal)
        
        # Count total KPI readings
        total_kpi_readings = sum(len(w.get('available_kpis', [])) for w in weekly_data)
        
        # Get real account name from accounts.csv if available
        account_name = journey_data.get('account_name', f'Account {account_id}')
        accounts_file = C17_DATA_DIR / "accounts.csv"
        if accounts_file.exists():
            try:
                with open(accounts_file, 'r') as af:
                    reader = csv.DictReader(af)
                    for row in reader:
                        if row.get('account_id') == account_id:
                            account_name = row.get('account_name', account_name)
                            break
            except Exception as e:
                print(f"Warning: Could not load account name from CSV: {e}")
        
        # Build response
        response = {
            'account_id': account_id,  # Use requested account_id, not journey_data account_id
            'account_name': account_name,
            'pattern_type': journey_data.get('pattern_type', 'unknown'),
            'total_weeks': journey_data.get('total_weeks', len(weekly_data)),
            'starting_health': float(journey_data.get('starting_health', 0)),
            'ending_health': float(journey_data.get('ending_health', 0)),
            'weekly_data': weekly_data,
            'signals': all_signals,  # Include all signals for signals tab
            'summary': {
                'total_events': len(journey_data.get('events', [])),
                'total_kpi_readings': total_kpi_readings,
                'total_signals': len(all_signals),
                'weeks_with_data': len([w for w in weekly_data if w.get('events') or w.get('available_kpis')]),
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
            'traceback': traceback.format_exc()
        }), 500


@journey_api_c17.route('/accounts', methods=['GET'])
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
        
        data_dir = test_run_dir / "data"
        if not data_dir.exists():
            return jsonify({
                'accounts': [],
                'total': 0
            })
        
        accounts = []
        for journey_file in data_dir.glob('account_*_journey.json'):
            account_id = journey_file.stem.replace('account_', '').replace('_journey', '')
            
            try:
                with open(journey_file, 'r') as f:
                    journey_data = json.load(f)
                
                accounts.append({
                    'account_id': journey_data.get('account_id', account_id),
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
