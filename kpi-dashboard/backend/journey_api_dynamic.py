"""
Dynamic Journey API - No hardcoding required!
Discovers customer journey APIs automatically based on directory structure.
Works for ALL customers without requiring code changes or server restarts.
"""

from flask import Blueprint, jsonify, current_app
from pathlib import Path
import json
import os
import csv
from collections import defaultdict
from datetime import datetime, timedelta, date

def get_customer_from_account(account_id):
    """
    Extract customer ID from account ID
    Account ID format: CUSTOMERID * 1000 + 001-999
    E.g., 113001 → customer 113, 17001 → customer 17
    """
    account_id_int = int(account_id) if isinstance(account_id, str) else account_id
    return account_id_int // 1000

def find_journey_file(customer_id, account_id):
    """
    Find journey JSON file for account
    Checks multiple possible paths:
    1. verticals/customerX-dc2_s/journey/wizard_a/outputs/account_{account_id}_journey.json
    2. verticals/customerX-DC2_S/journey/wizard_a/outputs/account_{account_id}_journey.json
    3. verticals/customerX-dc2_s/journey/wizard_a/test_run_*/data/account_{account_id}_journey.json
    """
    verticals_dir = Path(__file__).parent / "verticals"
    account_id_str = str(account_id)
    
    # Try different vertical slug formats
    possible_dirs = [
        verticals_dir / f"customer{customer_id}-dc2_s",
        verticals_dir / f"customer{customer_id}-DC2_S",
        verticals_dir / f"customer{customer_id}-dc2s",
    ]
    
    for customer_dir in possible_dirs:
        if not customer_dir.exists():
            continue
        
        # Check outputs directory first (most recent)
        outputs_dir = customer_dir / "journey" / "wizard_a" / "outputs"
        journey_file = outputs_dir / f"account_{account_id_str}_journey.json"
        
        if journey_file.exists():
            return journey_file
        
        # Fallback: check test_run directories
        wizard_a_dir = customer_dir / "journey" / "wizard_a"
        if wizard_a_dir.exists():
            test_runs = []
            for item in wizard_a_dir.iterdir():
                if item.is_dir() and (item.name.startswith('test_run_') or item.name == 'outputs'):
                    test_runs.append((item.stat().st_mtime, item))
            
            if test_runs:
                # Try most recent first
                test_runs.sort(reverse=True)
                for _, test_dir in test_runs:
                    # Check data subdirectory if it exists
                    data_dir = test_dir / "data"
                    if data_dir.exists():
                        journey_file = data_dir / f"account_{account_id_str}_journey.json"
                    else:
                        journey_file = test_dir / f"account_{account_id_str}_journey.json"
                    
                    if journey_file.exists():
                        return journey_file
    
    return None

def load_journey_data(journey_file):
    """Load and return journey JSON data"""
    with open(journey_file, 'r') as f:
        return json.load(f)

def convert_to_weekly_format(journey_data, account_id=None):
    """
    Convert journey JSON format to frontend visualizer format.
    Similar to customer-specific journey APIs but generic.
    """
    if not journey_data:
        return None, None
    
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
    
    # Store start_date for later use in signal processing
    global_start_date = start_date
    
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
        
        # Calculate data quality metrics
        available_kpis = []  # Could load from KPI data if available
        coverage_pct = 0.0
        data_quality = 0.0
        
        # Calculate pillar scores from journey data if available
        pillar_scores = journey_data.get('pillar_scores', {})
        if not pillar_scores:
            # Default pillar scores
            pillar_scores = {
                'Infrastructure Health': 0.0,
                'Operational Efficiency': 0.0,
                'Revenue Protection': 0.0,
                'Customer Success': 0.0,
                'Strategic Growth': 0.0
            }
        
        week_entry = {
            'week_number': week_num,
            'date': dates_by_week.get(week_num, start_date),
            'health_score': float(health_score) if health_score else 0,
            'phase': phases_by_week.get(week_num, 'unknown'),
            'events': events_by_week.get(week_num, []),
            'raw_kpis': {},
            'normalized_kpis': {},
            'kpis': {},
            'pillar_scores': pillar_scores,
            'pillars': pillar_scores,
            'data_quality': data_quality,
            'coverage_pct': coverage_pct,
            'available_kpis': available_kpis,
            'missing_kpis': [],
            'signals': []  # Could load from signals data if available
        }
        
        weekly_data.append(week_entry)
    
    return weekly_data, start_date


def _normalize_kpi_code_for_journey(kpi_code, dc2s_kpis):
    """Map AI/CH/DV/EX/OS KPI codes to P1-P5 catalog codes for DC2S_KPIS lookup."""
    if kpi_code in dc2s_kpis:
        return kpi_code
    if "-" in str(kpi_code):
        parts = str(kpi_code).split("-", 1)
        if len(parts) == 2 and parts[0] in ("AI", "CH", "DV", "EX", "OS"):
            catalog = {"AI": "P3", "CH": "P4", "DV": "P1", "EX": "P5", "OS": "P2"}
            lookup = catalog.get(parts[0], "") + "-" + parts[1]
            if lookup in dc2s_kpis:
                return lookup
    return None


def _kpi_normalized_score(kpi_code, value, dc2s_kpis):
    """Return 0-100 score for one KPI using DC2_S target/operator logic."""
    if kpi_code not in dc2s_kpis:
        return None
    kpi_def = dc2s_kpis[kpi_code]
    target_raw = kpi_def.get('target', 100)
    if isinstance(target_raw, dict):
        target = target_raw.get('value', 100)
        operator = target_raw.get('operator', '>')
    else:
        target = target_raw
        operator = '>'
    if not target or target <= 0:
        return min(100, float(value))
    val = float(value)
    if operator == '<':
        return min(100.0, (target / max(val, 0.01)) * 100)
    return min(100.0, (val / target) * 100)


def enrich_weekly_data_with_dc2s_kpis(weekly_data, account_id, start_date, total_weeks):
    """
    Enrich each week in weekly_data with KPI data from dc2s_kpis table.
    Groups DC2SKPI rows by week (from journey start_date) and fills
    normalized_kpis, raw_kpis, pillar_scores (and optionally health_score) per week.
    """
    if not weekly_data or total_weeks < 1:
        return
    try:
        from models import DC2SKPI
        from verticals.dc2_s.api_routes import calculate_kpi_health
        from verticals.dc2_s.kpi_definitions import DC2S_KPIS
    except ImportError as e:
        current_app.logger.debug(f"Journey KPI enrichment skip (import): {e}")
        return
    try:
        account_id_int = int(account_id) if isinstance(account_id, str) else account_id
        customer_id = get_customer_from_account(account_id_int)
    except (ValueError, TypeError):
        return
    if isinstance(start_date, str):
        try:
            start_d = datetime.strptime(start_date[:10], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return
    else:
        start_d = getattr(start_date, 'date', lambda: start_date)() if hasattr(start_date, 'date') else start_date
    kpis = DC2SKPI.query.filter_by(account_id=account_id_int).order_by(DC2SKPI.measured_at.asc()).all()
    if not kpis:
        return
    # Group by week: week_num = (measured_at.date() - start_d).days // 7 + 1, clamp to 1..total_weeks
    by_week = defaultdict(dict)  # week_num -> kpi_code -> latest row in that week
    for row in kpis:
        mt = row.measured_at
        if mt is None:
            continue
        d = mt.date() if hasattr(mt, 'date') and callable(mt.date) else (datetime.strptime(str(mt)[:10], '%Y-%m-%d').date() if isinstance(mt, str) else mt)
        try:
            days = (d - start_d).days
        except TypeError:
            continue
        week_num = max(1, min(total_weeks, (days // 7) + 1))
        # Keep latest in week (we're iterating asc, so later overwrites)
        by_week[week_num][row.kpi_code] = row
    for week_num in range(1, total_weeks + 1):
        if week_num > len(weekly_data):
            break
        week_entry = weekly_data[week_num - 1]
        rows = by_week.get(week_num)
        if not rows:
            continue
        kpi_values = {code: float(r.value) for code, r in rows.items()}
        overall_health, pillar_averages = calculate_kpi_health(kpi_values, customer_id=customer_id)
        normalized_kpis = {}
        raw_kpis = {}
        available_kpis = []
        for code, row in rows.items():
            lookup = _normalize_kpi_code_for_journey(code, DC2S_KPIS) or code
            kpi_def = DC2S_KPIS.get(lookup, {})
            name = kpi_def.get('name', kpi_def.get('kpi_name', code))
            unit = kpi_def.get('unit', '')
            score = _kpi_normalized_score(lookup, row.value, DC2S_KPIS)
            if score is not None:
                normalized_kpis[name] = round(score, 1)
            raw_kpis[name] = {'value': float(row.value), 'unit': unit or 'count'}
            available_kpis.append(name)
        # Pillar names for radar: use P1..P5 or display names
        pillar_scores = {k: round(v, 1) for k, v in pillar_averages.items()}
        week_entry['normalized_kpis'] = normalized_kpis
        week_entry['kpis'] = normalized_kpis
        week_entry['raw_kpis'] = raw_kpis
        week_entry['pillar_scores'] = pillar_scores
        week_entry['pillars'] = pillar_scores
        week_entry['available_kpis'] = available_kpis
        week_entry['health_score'] = round(overall_health, 1)
    return


def get_account_name(customer_id, account_id):
    """Get account name from accounts.csv if available"""
    verticals_dir = Path(__file__).parent / "verticals"
    account_id_str = str(account_id)
    
    # Try different vertical slug formats
    possible_dirs = [
        verticals_dir / f"customer{customer_id}-dc2_s",
        verticals_dir / f"customer{customer_id}-DC2_S",
        verticals_dir / f"customer{customer_id}-dc2s",
    ]
    
    for customer_dir in possible_dirs:
        accounts_file = customer_dir / "data" / "accounts.csv"
        if accounts_file.exists():
            try:
                with open(accounts_file, 'r') as af:
                    reader = csv.DictReader(af)
                    for row in reader:
                        if row.get('account_id') == account_id_str:
                            return row.get('account_name', f'Account {account_id}')
            except Exception as e:
                current_app.logger.warning(f"Could not load account name from CSV: {e}")
    
    return f'Account {account_id}'

# Create dynamic blueprint
journey_dynamic_api = Blueprint('journey_dynamic_api', __name__, url_prefix='/api/journey')

@journey_dynamic_api.route('/<account_id>', methods=['GET'])
def get_journey_dynamic(account_id):
    """
    Dynamic journey endpoint - works for ANY customer!
    Uses account's actual customer_id from DB when available (fixes accounts like 10003
    where account_id // 1000 would be wrong). Falls back to derived customer_id otherwise.
    """
    try:
        # Prefer customer_id from the account record so we look in the right vertical folder
        customer_id = None
        try:
            from auth_middleware import get_current_customer_id
            from models import Account
            current_customer_id = get_current_customer_id()
            if current_customer_id:
                account = Account.query.filter_by(
                    account_id=int(account_id),
                    customer_id=current_customer_id
                ).first()
                if account:
                    customer_id = account.customer_id
        except Exception:
            pass
        if customer_id is None:
            customer_id = get_customer_from_account(account_id)
        
        # Find journey file (try resolved customer_id first, then derived)
        journey_file = find_journey_file(customer_id, account_id)
        if not journey_file and customer_id != get_customer_from_account(account_id):
            journey_file = find_journey_file(get_customer_from_account(account_id), account_id)
        
        if not journey_file:
            return jsonify({
                'error': f'Account {account_id} journey data not found',
                'customer_id': customer_id,
                'message': 'No journey JSON file found for this account. This account may not have journey data generated yet. Has Wizard A been run?'
            }), 404
        
        # Load journey data
        journey_data = load_journey_data(journey_file)
        
        # Convert to weekly format
        weekly_data, start_date = convert_to_weekly_format(journey_data, account_id)
        
        # Enrich each week with DC2_S KPI data from db so Health overview shows KPIs per week
        total_weeks = journey_data.get('total_weeks', len(weekly_data))
        enrich_weekly_data_with_dc2s_kpis(weekly_data, account_id, start_date, total_weeks)
        
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
        
        # Also fetch signals from qualitative_signals database table
        try:
            from models import QualitativeSignal, Account
            from auth_middleware import get_current_customer_id
            from extensions import db
            from datetime import datetime, date
            import traceback
            
            customer_id = get_current_customer_id()
            current_app.logger.info(f"[Journey API] Fetching signals for account {account_id}, customer_id: {customer_id}")
            
            if customer_id:
                # Verify account belongs to customer
                account = Account.query.filter_by(
                    account_id=int(account_id),
                    customer_id=customer_id
                ).first()
                
                if account:
                    current_app.logger.info(f"[Journey API] Account {account_id} found, fetching signals...")
                    # Fetch qualitative signals from database
                    db_signals = QualitativeSignal.query.filter_by(
                        account_id=int(account_id)
                    ).order_by(QualitativeSignal.signal_date.desc()).all()
                    
                    current_app.logger.info(f"[Journey API] Found {len(db_signals)} signals in database for account {account_id}")
                    
                    # Helpers for subject/priority/health_impact (align with signals_query_helper)
                    def _subject_from_content(content):
                        if not content:
                            return ''
                        c = content.strip()
                        if len(c) <= 100:
                            return c
                        if '. ' in c[:150]:
                            return c[:c.index('. ', 0, 150) + 1]
                        return c[:100] + '...'
                    def _priority_from_sentiment(sentiment, sentiment_score):
                        if sentiment == 'negative' and sentiment_score is not None and sentiment_score < -0.5:
                            return 'critical'
                        if sentiment == 'negative':
                            return 'high'
                        if sentiment == 'neutral':
                            return 'medium'
                        return 'low'
                    def _health_impact_from_sentiment(sentiment, sentiment_score):
                        if sentiment_score is None:
                            return 5 if sentiment == 'positive' else (-5 if sentiment == 'negative' else 0)
                        return int(float(sentiment_score) * 15)
                    # Convert database signals to API format
                    for sig in db_signals:
                        try:
                            # Calculate week number from signal date (relative to journey start)
                            signal_date = sig.signal_date
                            if isinstance(signal_date, str):
                                signal_date = datetime.strptime(signal_date, '%Y-%m-%d').date()
                            elif not isinstance(signal_date, date):
                                signal_date = datetime.strptime(str(signal_date), '%Y-%m-%d').date()
                            
                            journey_start = start_date
                            if isinstance(journey_start, str):
                                journey_start = datetime.strptime(journey_start, '%Y-%m-%d').date()
                            
                            week_number = max(1, ((signal_date - journey_start).days // 7) + 1) if journey_start and isinstance(journey_start, date) else 1
                            
                            # Check if signal already exists (avoid duplicates)
                            signal_date_str = sig.signal_date.isoformat() if hasattr(sig.signal_date, 'isoformat') else str(sig.signal_date)
                            existing = next((s for s in all_signals if 
                                s.get('signal_id') == str(sig.signal_id) or
                                (s.get('date') == signal_date_str and
                                s.get('summary') == (sig.content or ''))
                            ), None)
                            
                            if not existing:
                                content = sig.content or ''
                                sentiment = sig.sentiment or 'neutral'
                                sentiment_score = float(sig.sentiment_score) if sig.sentiment_score is not None else None
                                # Parse keywords if stored as JSON string
                                keywords = []
                                if sig.keywords:
                                    try:
                                        import json
                                        keywords = json.loads(sig.keywords) if isinstance(sig.keywords, str) else sig.keywords
                                    except Exception:
                                        keywords = [sig.keywords] if isinstance(sig.keywords, str) else []
                                
                                all_signals.append({
                                    'signal_id': f'DB-{sig.signal_id}',
                                    'date': signal_date_str,
                                    'week_number': week_number,
                                    'signal_type': sig.signal_type or 'csm_note',
                                    'source': 'Database',
                                    'from_contact': sig.stakeholder_title or '',
                                    'to_contact': '',
                                    'subject': _subject_from_content(content),
                                    'summary': content,
                                    'sentiment': sentiment,
                                    'sentiment_score': sentiment_score if sentiment_score is not None else 0,
                                    'priority': _priority_from_sentiment(sentiment, sentiment_score),
                                    'keywords': keywords if isinstance(keywords, list) else [],
                                    'health_impact': _health_impact_from_sentiment(sentiment, sentiment_score)
                                })
                        except Exception as sig_error:
                            current_app.logger.warning(f"Error processing signal {sig.signal_id}: {sig_error}")
                            current_app.logger.debug(traceback.format_exc())
                else:
                    current_app.logger.warning(f"[Journey API] Account {account_id} not found or doesn't belong to customer {customer_id}")
            else:
                current_app.logger.warning(f"[Journey API] No customer_id found in session")
        except Exception as e:
            current_app.logger.error(f"Could not fetch qualitative signals from database: {e}")
            current_app.logger.debug(traceback.format_exc())
        
        # Count total KPI readings
        total_kpi_readings = sum(len(w.get('available_kpis', [])) for w in weekly_data)
        
        # Signals count breakdown for validation (matches Qualitative Signals tab)
        signals_positive = sum(1 for s in all_signals if s.get('sentiment') == 'positive')
        signals_negative = sum(1 for s in all_signals if s.get('sentiment') == 'negative')
        signals_neutral = sum(1 for s in all_signals if s.get('sentiment') == 'neutral')
        signals_critical = sum(1 for s in all_signals if s.get('priority') == 'critical')
        
        # Get account name
        account_name = get_account_name(customer_id, account_id)
        
        # Build response (same format as customer-specific APIs)
        response = {
            'account_id': account_id,
            'account_name': account_name,
            'pattern_type': journey_data.get('pattern_type', 'unknown'),
            'total_weeks': journey_data.get('total_weeks', len(weekly_data)),
            'starting_health': float(journey_data.get('starting_health', 0)),
            'ending_health': float(journey_data.get('ending_health', 0)),
            'weekly_data': weekly_data,
            'signals': all_signals,
            'summary': {
                'total_events': len(journey_data.get('events', [])),
                'total_kpi_readings': total_kpi_readings,
                'total_signals': len(all_signals),
                'signals_positive': signals_positive,
                'signals_negative': signals_negative,
                'signals_neutral': signals_neutral,
                'signals_critical': signals_critical,
                'weeks_with_data': len([w for w in weekly_data if w.get('events') or w.get('available_kpis')]),
                'lowest_health': float(journey_data.get('lowest_health', 0)),
                'highest_health': float(journey_data.get('highest_health', 0))
            }
        }
        
        # Add summary data if available
        if 'summary' in journey_data:
            response['journey_summary'] = journey_data['summary']
        
        return jsonify(response), 200
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error in dynamic journey API for account {account_id}: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'account_id': account_id,
            'traceback': traceback.format_exc()
        }), 500

@journey_dynamic_api.route('/accounts', methods=['GET'])
def list_journey_accounts():
    """
    List all accounts that have journey data (across all customers).
    """
    try:
        verticals_dir = Path(__file__).parent / "verticals"
        accounts = []
        
        # Scan all customer directories
        if not verticals_dir.exists():
            return jsonify({
                'accounts': accounts,
                'total': 0
            })
        
        for customer_dir in verticals_dir.iterdir():
            if not customer_dir.is_dir() or not customer_dir.name.startswith('customer'):
                continue
            
            # Check outputs directory
            outputs_dir = customer_dir / "journey" / "wizard_a" / "outputs"
            if outputs_dir.exists():
                for journey_file in outputs_dir.glob('account_*_journey.json'):
                    account_id = journey_file.stem.replace('account_', '').replace('_journey', '')
                    
                    try:
                        journey_data = load_journey_data(journey_file)
                        customer_id = get_customer_from_account(account_id)
                        
                        customer_id = get_customer_from_account(account_id)
                        accounts.append({
                            'account_id': journey_data.get('account_id', account_id),
                            'account_name': journey_data.get('account_name', f'Account {account_id}'),
                            'customer_id': customer_id,
                            'pattern_type': journey_data.get('pattern_type', 'unknown'),
                            'total_weeks': journey_data.get('total_weeks', 0),
                            'starting_health': float(journey_data.get('starting_health', 0)),
                            'ending_health': float(journey_data.get('ending_health', 0)),
                            'final_outcome': journey_data.get('summary', {}).get('final_outcome')
                        })
                    except Exception as e:
                        current_app.logger.warning(f"Error loading {journey_file}: {e}")
                        continue
        
        return jsonify({
            'accounts': accounts,
            'total': len(accounts)
        }), 200
        
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error listing journey accounts: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

def register_dynamic_journey_api(app):
    """Register the dynamic journey API with Flask app"""
    app.register_blueprint(journey_dynamic_api)
    print("✅ Registered dynamic journey API at /api/journey/<account_id> (works for ALL customers)")
