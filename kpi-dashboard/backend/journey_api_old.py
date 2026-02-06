"""
Journey API Blueprint (FIXED)
==============================

Provides endpoints for Journey Visualizer V2 to display account journey data.

Endpoints:
  GET /api/journey/<account_id>          - Get full journey for an account
  GET /api/journey/<account_id>/week/<n> - Get specific week data
  GET /api/journey/accounts              - List all accounts with journey data
  GET /api/journey/<account_id>/summary  - Get journey summary/stats

Database Tables Used:
  - journey_accounts (PK: journey_account_id, has account_id like 10001)
  - journey_events (FK: journey_account_id)
  - journey_kpis (FK: journey_account_id)
  - journey_health (FK: journey_account_id)
  - journey_milestones (FK: journey_account_id)
"""

from flask import Blueprint, jsonify, request, g
from functools import wraps
import logging

logger = logging.getLogger(__name__)

journey_api = Blueprint('journey_api', __name__, url_prefix='/api/journey')


# ============================================================================
# AUTH DECORATOR (uses your existing auth)
# ============================================================================

def require_auth(f):
    """Require authentication for journey endpoints"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check if user is authenticated (uses your existing session)
        if not hasattr(g, 'user') or g.user is None:
            # Try to get from session
            from flask import session
            if 'user_id' not in session:
                return jsonify({
                    'error': 'Authentication required',
                    'status': 'unauthorized'
                }), 401
        return f(*args, **kwargs)
    return decorated


# ============================================================================
# DATABASE HELPER
# ============================================================================

def execute_query(query, params=None):
    """Execute a query and return results as list of dicts"""
    import os
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    database_url = os.environ.get('DATABASE_URL')
    
    try:
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Database query error: {e}")
        raise


def get_journey_account_id(account_id):
    """
    Get the internal journey_account_id from the external account_id (10001, 10003, etc.)
    """
    query = """
        SELECT journey_account_id 
        FROM journey_accounts 
        WHERE account_id = %s
    """
    result = execute_query(query, (account_id,))
    if result:
        return result[0]['journey_account_id']
    return None


# ============================================================================
# ENDPOINTS
# ============================================================================

@journey_api.route('/accounts', methods=['GET'])
@require_auth
def list_journey_accounts():
    """
    List all accounts that have journey data.
    """
    try:
        query = """
            SELECT 
                journey_account_id,
                account_id,
                account_name,
                pattern_type,
                total_weeks,
                starting_health,
                ending_health,
                final_outcome,
                created_at
            FROM journey_accounts
            ORDER BY account_id
        """
        
        accounts = execute_query(query)
        
        # Convert to serializable format
        result = []
        for acc in accounts:
            result.append({
                'journey_account_id': acc['journey_account_id'],
                'account_id': acc['account_id'],
                'account_name': acc['account_name'],
                'pattern_type': acc['pattern_type'],
                'total_weeks': acc['total_weeks'],
                'starting_health': float(acc['starting_health']) if acc['starting_health'] else 0,
                'ending_health': float(acc['ending_health']) if acc['ending_health'] else 0,
                'final_outcome': acc.get('final_outcome'),
                'created_at': str(acc['created_at']) if acc['created_at'] else None
            })
        
        return jsonify({
            'accounts': result,
            'total': len(result)
        })
        
    except Exception as e:
        logger.error(f"Error listing journey accounts: {e}")
        return jsonify({'error': str(e)}), 500


@journey_api.route('/<account_id>', methods=['GET'])
@require_auth
def get_account_journey(account_id):
    """
    Get full journey data for an account.
    This is the main endpoint used by JourneyVisualizerV2.
    """
    try:
        # Get account info and journey_account_id
        account_query = """
            SELECT 
                journey_account_id,
                account_id,
                account_name,
                pattern_type,
                total_weeks,
                starting_health,
                ending_health,
                final_outcome
            FROM journey_accounts
            WHERE account_id = %s
        """
        accounts = execute_query(account_query, (account_id,))
        
        if not accounts:
            return jsonify({'error': f'Account {account_id} not found'}), 404
        
        account = accounts[0]
        journey_account_id = account['journey_account_id']
        
        # Get weekly health data
        health_query = """
            SELECT 
                week_number,
                overall_health_score as health_score,
                phase,
                pillar_scores,
                data_quality,
                coverage_pct
            FROM journey_health
            WHERE journey_account_id = %s
            ORDER BY week_number
        """
        health_data = execute_query(health_query, (journey_account_id,))
        
        # Get KPI data grouped by week
        kpi_query = """
            SELECT 
                week_number,
                kpi_code as kpi_name,
                value as raw_value,
                normalized_value,
                unit,
                pillar
            FROM journey_kpis
            WHERE journey_account_id = %s
            ORDER BY week_number, kpi_code
        """
        kpi_data = execute_query(kpi_query, (journey_account_id,))
        
        # Get events
        events_query = """
            SELECT 
                week_number,
                event_type,
                description,
                sentiment,
                health_impact
            FROM journey_events
            WHERE journey_account_id = %s
            ORDER BY week_number
        """
        events_data = execute_query(events_query, (journey_account_id,))
        
        # Get milestones
        milestones_query = """
            SELECT 
                milestone_type,
                week_number,
                description
            FROM journey_milestones
            WHERE journey_account_id = %s
            ORDER BY week_number
        """
        milestones = execute_query(milestones_query, (journey_account_id,))
        
        # Organize KPIs by week
        kpis_by_week = {}
        for kpi in kpi_data:
            week = kpi['week_number']
            if week not in kpis_by_week:
                kpis_by_week[week] = {'raw': {}, 'normalized': {}}
            
            kpi_name = kpi['kpi_name']
            kpis_by_week[week]['raw'][kpi_name] = {
                'value': float(kpi['raw_value']) if kpi['raw_value'] else 0,
                'unit': kpi['unit'] or ''
            }
            kpis_by_week[week]['normalized'][kpi_name] = float(kpi['normalized_value']) if kpi['normalized_value'] else 0
        
        # Organize events by week
        events_by_week = {}
        for event in events_data:
            week = event['week_number']
            if week not in events_by_week:
                events_by_week[week] = []
            events_by_week[week].append({
                'event_type': event['event_type'],
                'description': event['description'],
                'sentiment': event['sentiment'],
                'health_impact': float(event['health_impact']) if event['health_impact'] else 0
            })
        
        # Build weekly_data array
        weekly_data = []
        for health in health_data:
            week_num = health['week_number']
            
            week_entry = {
                'week_number': week_num,
                'health_score': float(health['health_score']) if health['health_score'] else 0,
                'phase': health['phase'] or 'unknown',
                'pillars': health['pillar_scores'] or {},
                'data_quality': float(health['data_quality']) if health['data_quality'] else 0,
                'coverage_pct': float(health['coverage_pct']) if health['coverage_pct'] else 0,
                'raw_kpis': kpis_by_week.get(week_num, {}).get('raw', {}),
                'normalized_kpis': kpis_by_week.get(week_num, {}).get('normalized', {}),
                'kpis': kpis_by_week.get(week_num, {}).get('normalized', {}),  # V1 compat
                'events': events_by_week.get(week_num, [])
            }
            
            # Calculate available/missing KPIs
            available_kpis = list(week_entry['normalized_kpis'].keys())
            week_entry['available_kpis'] = available_kpis
            
            weekly_data.append(week_entry)
        
        # Build response
        response = {
            'account_id': account['account_id'],
            'account_name': account['account_name'],
            'pattern_type': account['pattern_type'],
            'total_weeks': account['total_weeks'],
            'starting_health': float(account['starting_health']) if account['starting_health'] else 0,
            'ending_health': float(account['ending_health']) if account['ending_health'] else 0,
            'final_outcome': account.get('final_outcome'),
            'weekly_data': weekly_data,
            'milestones': milestones,
            'summary': {
                'total_events': len(events_data),
                'total_kpi_readings': len(kpi_data),
                'weeks_with_data': len(weekly_data)
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting journey for account {account_id}: {e}")
        return jsonify({'error': str(e)}), 500


@journey_api.route('/<account_id>/week/<int:week_number>', methods=['GET'])
@require_auth
def get_week_detail(account_id, week_number):
    """
    Get detailed data for a specific week.
    """
    try:
        # Get journey_account_id
        journey_account_id = get_journey_account_id(account_id)
        if not journey_account_id:
            return jsonify({'error': f'Account {account_id} not found'}), 404
        
        # Get health snapshot
        health_query = """
            SELECT 
                overall_health_score as health_score,
                phase,
                pillar_scores,
                data_quality,
                coverage_pct
            FROM journey_health
            WHERE journey_account_id = %s AND week_number = %s
        """
        health_data = execute_query(health_query, (journey_account_id, week_number))
        
        if not health_data:
            return jsonify({'error': f'No data for week {week_number}'}), 404
        
        health = health_data[0]
        
        # Get KPIs for this week
        kpi_query = """
            SELECT 
                kpi_code as kpi_name,
                value as raw_value,
                normalized_value,
                unit,
                pillar
            FROM journey_kpis
            WHERE journey_account_id = %s AND week_number = %s
        """
        kpi_data = execute_query(kpi_query, (journey_account_id, week_number))
        
        # Get events for this week
        events_query = """
            SELECT 
                event_type,
                description,
                sentiment,
                health_impact
            FROM journey_events
            WHERE journey_account_id = %s AND week_number = %s
        """
        events = execute_query(events_query, (journey_account_id, week_number))
        
        # Build KPI structures
        raw_kpis = {}
        normalized_kpis = {}
        for kpi in kpi_data:
            kpi_name = kpi['kpi_name']
            raw_kpis[kpi_name] = {
                'value': float(kpi['raw_value']) if kpi['raw_value'] else 0,
                'unit': kpi['unit'] or ''
            }
            normalized_kpis[kpi_name] = float(kpi['normalized_value']) if kpi['normalized_value'] else 0
        
        response = {
            'account_id': account_id,
            'week_number': week_number,
            'health_score': float(health['health_score']) if health['health_score'] else 0,
            'phase': health['phase'],
            'pillars': health['pillar_scores'] or {},
            'data_quality': float(health['data_quality']) if health['data_quality'] else 0,
            'coverage_pct': float(health['coverage_pct']) if health['coverage_pct'] else 0,
            'raw_kpis': raw_kpis,
            'normalized_kpis': normalized_kpis,
            'events': events
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting week {week_number} for account {account_id}: {e}")
        return jsonify({'error': str(e)}), 500


@journey_api.route('/<account_id>/summary', methods=['GET'])
@require_auth
def get_journey_summary(account_id):
    """
    Get summary statistics for an account's journey.
    """
    try:
        # Get account info
        account_query = """
            SELECT 
                journey_account_id,
                account_id,
                account_name,
                pattern_type,
                starting_health,
                ending_health,
                final_outcome
            FROM journey_accounts
            WHERE account_id = %s
        """
        accounts = execute_query(account_query, (account_id,))
        
        if not accounts:
            return jsonify({'error': f'Account {account_id} not found'}), 404
        
        account = accounts[0]
        journey_account_id = account['journey_account_id']
        
        # Get event stats
        events_query = """
            SELECT 
                COUNT(*) as total_events,
                COUNT(*) FILTER (WHERE sentiment = 'negative') as negative_events,
                COUNT(*) FILTER (WHERE sentiment = 'positive') as positive_events
            FROM journey_events
            WHERE journey_account_id = %s
        """
        event_stats = execute_query(events_query, (journey_account_id,))
        
        # Get data quality stats
        quality_query = """
            SELECT 
                AVG(data_quality) as avg_data_quality,
                AVG(coverage_pct) as avg_coverage
            FROM journey_health
            WHERE journey_account_id = %s
        """
        quality_stats = execute_query(quality_query, (journey_account_id,))
        
        # Get milestones
        milestones_query = """
            SELECT milestone_type, COUNT(*) as count
            FROM journey_milestones
            WHERE journey_account_id = %s
            GROUP BY milestone_type
        """
        milestone_counts = execute_query(milestones_query, (journey_account_id,))
        
        # Calculate health trend
        starting = float(account['starting_health']) if account['starting_health'] else 0
        ending = float(account['ending_health']) if account['ending_health'] else 0
        health_change = ending - starting
        
        if health_change > 10:
            trend = 'improving'
        elif health_change < -10:
            trend = 'declining'
        else:
            trend = 'stable'
        
        response = {
            'account_id': account['account_id'],
            'account_name': account['account_name'],
            'pattern_type': account['pattern_type'],
            'final_outcome': account.get('final_outcome'),
            'health_trend': trend,
            'starting_health': starting,
            'ending_health': ending,
            'health_change': health_change,
            'total_events': event_stats[0]['total_events'] if event_stats else 0,
            'negative_events': event_stats[0]['negative_events'] if event_stats else 0,
            'positive_events': event_stats[0]['positive_events'] if event_stats else 0,
            'avg_data_quality': float(quality_stats[0]['avg_data_quality']) if quality_stats and quality_stats[0]['avg_data_quality'] else 0,
            'avg_coverage': float(quality_stats[0]['avg_coverage']) if quality_stats and quality_stats[0]['avg_coverage'] else 0,
            'milestones': {m['milestone_type']: m['count'] for m in milestone_counts}
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting summary for account {account_id}: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# HEALTH CHECK
# ============================================================================

@journey_api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint (no auth required)"""
    try:
        # Quick DB check
        result = execute_query("SELECT COUNT(*) as count FROM journey_accounts")
        account_count = result[0]['count'] if result else 0
        
        return jsonify({
            'status': 'healthy',
            'accounts_loaded': account_count,
            'endpoints': [
                'GET /api/journey/accounts',
                'GET /api/journey/<account_id>',
                'GET /api/journey/<account_id>/week/<n>',
                'GET /api/journey/<account_id>/summary',
                'GET /api/journey/health'
            ]
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
