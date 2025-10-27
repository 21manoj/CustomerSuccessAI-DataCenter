"""
Playbook Recommendations API

Analyzes which accounts need which playbooks based on their current KPI data and metrics
"""

from flask import Blueprint, request, jsonify
from models import db, Account, KPI, KPITimeSeries
from datetime import datetime, timedelta
from sqlalchemy import func
import json

playbook_recommendations_api = Blueprint('playbook_recommendations_api', __name__)


def get_customer_id():
    """Get customer ID from request headers"""
    return request.headers.get('X-Customer-ID', type=int, default=1)


def calculate_health_score_proxy(account_id):
    """Calculate a health score proxy from KPIs using a simplified approach"""
    # Get recent KPIs for the account
    kpis = KPI.query.filter_by(account_id=account_id).all()
    
    if not kpis:
        return 50.0  # Default middle score
    
    # Simple health calculation based on KPI data and impact levels
    total_score = 0
    valid_kpis = 0
    
    for kpi in kpis:
        try:
            # Parse the KPI data value
            data_str = str(kpi.data).replace('%', '').replace('$', '').replace('K', '000').replace('M', '000000')
            value = float(data_str) if data_str.strip() else 0
            
            # Normalize to 0-100 scale based on KPI type
            if 'score' in kpi.kpi_parameter.lower() or 'rate' in kpi.kpi_parameter.lower():
                # Already in percentage or score format
                normalized_score = min(100, max(0, value))
            elif 'count' in kpi.kpi_parameter.lower() or 'ticket' in kpi.kpi_parameter.lower():
                # Count-based KPIs - lower is better
                if value == 0:
                    normalized_score = 100
                elif value <= 10:
                    normalized_score = 80
                elif value <= 50:
                    normalized_score = 60
                elif value <= 100:
                    normalized_score = 40
                else:
                    normalized_score = 20
            else:
                # Default normalization
                normalized_score = min(100, max(0, value))
            
            # Weight by impact level
            impact_weight = 1.0
            if kpi.impact_level == 'Critical':
                impact_weight = 3.0
            elif kpi.impact_level == 'High':
                impact_weight = 2.0
            elif kpi.impact_level == 'Medium':
                impact_weight = 1.5
            
            total_score += normalized_score * impact_weight
            valid_kpis += impact_weight
            
        except (ValueError, TypeError):
            # Skip invalid KPI data
            continue
    
    if valid_kpis > 0:
        average_score = total_score / valid_kpis
        return max(0, min(100, average_score))
    else:
        return 50.0  # Default if no valid KPIs


def evaluate_account_for_voc_sprint(account, triggers):
    """Evaluate if account needs VoC Sprint playbook"""
    reasons = []
    score = 0  # Higher score = more urgent need
    
    # Calculate health score proxy
    health_score = calculate_health_score_proxy(account.account_id)
    
    # Check NPS threshold (using health score as proxy)
    nps_threshold = triggers.get('nps_threshold', 6.0)  # More realistic default
    nps_proxy = health_score / 10  # Convert to 0-10 scale
    if nps_proxy < nps_threshold:
        reasons.append(f"Low NPS proxy ({nps_proxy:.1f} < {nps_threshold})")
        score += 30
    
    # Check CSAT threshold (using health score as proxy)
    csat_threshold = triggers.get('csat_threshold', 3.0)  # More realistic default
    csat_proxy = health_score / 20  # Convert to 0-5 scale
    if csat_proxy < csat_threshold:
        reasons.append(f"Low CSAT proxy ({csat_proxy:.1f} < {csat_threshold})")
        score += 25
    
    # Check account status for churn risk
    if account.account_status.lower() == 'at risk':
        reasons.append("Account marked 'At Risk'")
        score += 40
    
    # Check health score drop
    health_drop_threshold = triggers.get('health_score_drop_threshold', 10)
    if health_score < 50:  # Simplified check
        reasons.append(f"Low health score ({health_score:.1f})")
        score += 20
    
    
    return {
        'needed': score > 0,
        'urgency_score': score,
        'urgency_level': 'Critical' if score >= 60 else ('High' if score >= 30 else 'Medium'),
        'reasons': reasons,
        'health_score': health_score
    }


def evaluate_account_for_activation_blitz(account, triggers):
    """Evaluate if account needs Activation Blitz playbook"""
    reasons = []
    score = 0
    
    # Calculate adoption proxy from health score
    adoption_proxy = calculate_health_score_proxy(account.account_id)
    
    # Check adoption index
    adoption_threshold = triggers.get('adoption_index_threshold', 60)
    if adoption_proxy < adoption_threshold:
        reasons.append(f"Low adoption index ({adoption_proxy:.1f} < {adoption_threshold})")
        score += 30
    
    # Check active users (estimate from revenue as proxy)
    active_users_threshold = triggers.get('active_users_threshold', 50)
    estimated_users = int(account.revenue / 5000) if account.revenue else 0
    if estimated_users < active_users_threshold:
        reasons.append(f"Low estimated active users (~{estimated_users} < {active_users_threshold})")
        score += 25
    
    # Check for low feature usage
    kpi_count = KPI.query.filter_by(account_id=account.account_id).count()
    if kpi_count < 10:
        reasons.append(f"Limited feature usage ({kpi_count} KPIs tracked)")
        score += 20
    
    # Check DAU/MAU (simulated based on health)
    dau_mau_threshold = triggers.get('dau_mau_threshold', 0.25)
    dau_mau_proxy = 0.15 if adoption_proxy < 60 else 0.35
    if dau_mau_proxy < dau_mau_threshold:
        reasons.append(f"Low DAU/MAU ratio (~{dau_mau_proxy:.2f} < {dau_mau_threshold})")
        score += 20
    
    # Check if high-revenue but low adoption (expansion opportunity)
    if account.revenue and account.revenue > 100000 and adoption_proxy < 60:
        reasons.append(f"High revenue (${account.revenue:,.0f}) but low adoption")
        score += 15
    
    return {
        'needed': score > 0,
        'urgency_score': score,
        'urgency_level': 'Critical' if score >= 60 else ('High' if score >= 30 else 'Medium'),
        'reasons': reasons,
        'adoption_index': adoption_proxy
    }


def evaluate_account_for_sla_stabilizer(account, triggers):
    """Evaluate if account needs SLA Stabilizer playbook"""
    reasons = []
    score = 0
    
    # Get SLA-related KPIs
    kpis = KPI.query.filter_by(account_id=account.account_id).all()
    
    # Check SLA breach threshold (configurable)
    sla_breach_threshold = triggers.get('sla_breach_threshold', 5)
    sla_breach_kpi = next((k for k in kpis if 'sla' in k.kpi_parameter.lower() or 'breach' in k.kpi_parameter.lower()), None)
    if sla_breach_kpi:
        try:
            breach_count = int(sla_breach_kpi.data) if sla_breach_kpi.data else 0
            if breach_count > sla_breach_threshold:
                reasons.append(f"SLA breaches ({breach_count} > {sla_breach_threshold})")
                score += 40
        except:
            if sla_breach_kpi.impact_level == 'Critical':
                reasons.append("SLA breaches detected")
                score += 40
    
    # Check response time multiplier (configurable)
    response_time_multiplier = triggers.get('response_time_multiplier', 2.0)
    response_kpi = next((k for k in kpis if 'response' in k.kpi_parameter.lower()), None)
    if response_kpi:
        try:
            response_time = float(response_kpi.data) if response_kpi.data else 0
            if response_time > (24 * response_time_multiplier):  # 24 hours * multiplier
                reasons.append(f"Slow response times ({response_time:.1f}h > {24 * response_time_multiplier}h)")
                score += 30
        except:
            if response_kpi.impact_level in ['Critical', 'High']:
                reasons.append("Slow response times detected")
                score += 30
    
    # Check escalation trend (configurable)
    escalation_trend = triggers.get('escalation_trend', 'increasing')
    escalation_kpi = next((k for k in kpis if 'escalat' in k.kpi_parameter.lower()), None)
    if escalation_kpi and escalation_trend == 'increasing':
        if escalation_kpi.impact_level == 'Critical':
            reasons.append("High escalation volume")
            score += 20
    
    # Check reopen rate threshold (configurable)
    reopen_rate_threshold = triggers.get('reopen_rate_threshold', 0.20)
    reopen_kpi = next((k for k in kpis if 'reopen' in k.kpi_parameter.lower()), None)
    if reopen_kpi:
        try:
            reopen_rate = float(reopen_kpi.data) if reopen_kpi.data else 0
            if reopen_rate > reopen_rate_threshold:
                reasons.append(f"High reopen rate ({reopen_rate:.1%} > {reopen_rate_threshold:.1%})")
                score += 25
        except:
            pass
    
    return {
        'needed': score > 0,
        'urgency_score': score,
        'urgency_level': 'Critical' if score >= 60 else ('High' if score >= 30 else 'Medium'),
        'reasons': reasons,
        'sla_metrics': len([k for k in kpis if 'sla' in k.kpi_parameter.lower()])
    }


def evaluate_account_for_renewal_safeguard(account, triggers):
    """Evaluate if account needs Renewal Safeguard playbook"""
    reasons = []
    score = 0
    
    # Calculate health score
    health_score = calculate_health_score_proxy(account.account_id)
    
    # Check health score threshold (configurable)
    health_threshold = triggers.get('health_score_threshold', 70)
    if health_score < health_threshold:
        reasons.append(f"Low health score ({health_score:.1f} < {health_threshold})")
        score += 35
    
    # Check renewal window days (configurable)
    renewal_window_days = triggers.get('renewal_window_days', 90)
    # Simplified check - assume accounts with low health are approaching renewal
    if health_score < 60:
        reasons.append(f"Likely approaching renewal window ({renewal_window_days} days)")
        score += 20
    
    # Check engagement trend (configurable)
    engagement_trend = triggers.get('engagement_trend', 'declining')
    if engagement_trend == 'declining':
        kpis = KPI.query.filter_by(account_id=account.account_id).all()
        engagement_kpis = [k for k in kpis if 'engagement' in k.kpi_parameter.lower() or 'qbr' in k.kpi_parameter.lower()]
        for kpi in engagement_kpis:
            if 'declin' in str(kpi.data).lower() or 'missed' in str(kpi.data).lower():
                reasons.append(f"Declining engagement: {kpi.kpi_parameter}")
                score += 25
                break
    
    # Check budget risk (configurable)
    budget_risk = triggers.get('budget_risk', True)
    if budget_risk and account.account_status.lower() == 'at risk':
        reasons.append("Account marked 'At Risk' - budget concerns")
        score += 30
    
    return {
        'needed': score > 0,
        'urgency_score': score,
        'urgency_level': 'Critical' if score >= 70 else ('High' if score >= 40 else 'Medium'),
        'reasons': reasons,
        'health_score': health_score,
        'revenue_at_risk': float(account.revenue) if account.revenue else 0
    }


def evaluate_account_for_expansion_timing(account, triggers):
    """Evaluate if account is ready for expansion"""
    reasons = []
    score = 0
    
    # Calculate adoption/health score
    health_score = calculate_health_score_proxy(account.account_id)
    
    # Check health score threshold (need HIGH health for expansion)
    health_threshold = triggers.get('health_score_threshold', 80)
    if health_score >= health_threshold:
        reasons.append(f"Excellent health score ({health_score:.1f} ≥ {health_threshold})")
        score += 40
    else:
        # Not ready for expansion if health is low
        return {
            'needed': False,
            'urgency_score': 0,
            'urgency_level': 'Low',
            'reasons': ['Health score too low for expansion'],
            'health_score': health_score
        }
    
    # Check adoption threshold (configurable)
    adoption_threshold = triggers.get('adoption_threshold', 85)
    kpi_count = KPI.query.filter_by(account_id=account.account_id).count()
    adoption_proxy = (kpi_count / 20) * 100  # Convert to percentage
    if adoption_proxy >= adoption_threshold:
        reasons.append(f"High adoption ({adoption_proxy:.1f}% ≥ {adoption_threshold}%)")
        score += 30
    else:
        return {
            'needed': False,
            'urgency_score': 0,
            'urgency_level': 'Low',
            'reasons': ['Insufficient adoption for expansion'],
            'health_score': health_score
        }
    
    # Check usage limit percentage (configurable)
    usage_limit_percentage = triggers.get('usage_limit_percentage', 0.80)
    usage_proxy = min(1.0, kpi_count / 25)  # Simulate usage as percentage of capacity
    if usage_proxy >= usage_limit_percentage:
        reasons.append(f"High usage ({usage_proxy:.1%} ≥ {usage_limit_percentage:.1%}) - expansion opportunity")
        score += 25
    
    # Check budget window (configurable)
    budget_window = triggers.get('budget_window', 'Q1_Q4')
    if budget_window in ['Q1_Q4', 'Q1', 'Q4']:  # Budget available in Q1 or Q4
        reasons.append(f"Budget window open ({budget_window})")
        score += 20
    
    return {
        'needed': score > 0,
        'urgency_score': score,
        'urgency_level': 'High' if score >= 80 else ('Medium' if score >= 50 else 'Low'),
        'reasons': reasons,
        'health_score': health_score,
        'expansion_potential': float(account.revenue * 0.3) if account.revenue else 0
    }


@playbook_recommendations_api.route('/api/playbooks/test-health-score/<int:account_id>', methods=['GET'])
def test_health_score(account_id):
    """Test endpoint to debug health score calculation"""
    try:
        health_score = calculate_health_score_proxy(account_id)
        return jsonify({
            'account_id': account_id,
            'health_score': health_score,
            'status': 'success'
        })
    except Exception as e:
        return jsonify({
            'account_id': account_id,
            'error': str(e),
            'status': 'error'
        }), 500

@playbook_recommendations_api.route('/api/playbooks/recommendations/<playbook_id>', methods=['POST'])
def get_playbook_recommendations(playbook_id):
    """Get account recommendations for a specific playbook"""
    try:
        customer_id = get_customer_id()
        data = request.json or {}
        triggers = data.get('triggers', {})
        
        # Always try to fetch from database first, then use provided triggers as fallback
        from models import PlaybookTrigger
        
        # Map API playbook_id to database playbook_type
        playbook_type_mapping = {
            'voc-sprint': 'voc',
            'activation-blitz': 'activation',
            'sla-stabilizer': 'sla',
            'renewal-safeguard': 'renewal',
            'expansion-timing': 'expansion'
        }
        db_playbook_type = playbook_type_mapping.get(playbook_id, playbook_id)
        
        trigger_config = PlaybookTrigger.query.filter_by(
            customer_id=customer_id,
            playbook_type=db_playbook_type
        ).first()
        
        if trigger_config and trigger_config.trigger_config:
            db_triggers = json.loads(trigger_config.trigger_config)
            # Merge provided triggers with database triggers (database takes precedence now)
            triggers = {**triggers, **db_triggers}
        
        # Get all accounts for customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        
        recommendations = []
        
        for account in accounts:
            # Evaluate based on playbook type
            if playbook_id == 'voc-sprint':
                evaluation = evaluate_account_for_voc_sprint(account, triggers)
            elif playbook_id == 'activation-blitz':
                evaluation = evaluate_account_for_activation_blitz(account, triggers)
            elif playbook_id == 'sla-stabilizer':
                evaluation = evaluate_account_for_sla_stabilizer(account, triggers)
            elif playbook_id == 'renewal-safeguard':
                evaluation = evaluate_account_for_renewal_safeguard(account, triggers)
            elif playbook_id == 'expansion-timing':
                evaluation = evaluate_account_for_expansion_timing(account, triggers)
            else:
                # Generic evaluation
                evaluation = {
                    'needed': False,
                    'urgency_score': 0,
                    'urgency_level': 'Low',
                    'reasons': []
                }
            
            recommendations.append({
                'account_id': account.account_id,
                'account_name': account.account_name,
                'industry': account.industry,
                'region': account.region,
                'revenue': float(account.revenue) if account.revenue else 0,
                'account_status': account.account_status,
                'needed': evaluation['needed'],
                'urgency_score': evaluation['urgency_score'],
                'urgency_level': evaluation['urgency_level'],
                'reasons': evaluation['reasons'],
                'metrics': {
                    k: v for k, v in evaluation.items() 
                    if k not in ['needed', 'urgency_score', 'urgency_level', 'reasons']
                }
            })
        
        # Sort by urgency score (highest first)
        recommendations.sort(key=lambda x: x['urgency_score'], reverse=True)
        
        # Count by urgency level
        urgency_counts = {
            'Critical': len([r for r in recommendations if r['urgency_level'] == 'Critical']),
            'High': len([r for r in recommendations if r['urgency_level'] == 'High']),
            'Medium': len([r for r in recommendations if r['urgency_level'] == 'Medium']),
            'Low': len([r for r in recommendations if not r['needed']])
        }
        
        return jsonify({
            'status': 'success',
            'playbook_id': playbook_id,
            'total_accounts': len(accounts),
            'accounts_needing_playbook': len([r for r in recommendations if r['needed']]),
            'urgency_breakdown': urgency_counts,
            'recommendations': recommendations
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

