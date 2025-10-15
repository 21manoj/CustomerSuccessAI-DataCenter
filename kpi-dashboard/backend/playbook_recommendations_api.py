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
    """Calculate a health score proxy from KPIs"""
    # Get recent KPIs for the account
    kpis = KPI.query.filter_by(account_id=account_id).all()
    
    if not kpis:
        return 50.0  # Default middle score
    
    # Simple health calculation based on KPI count and critical indicators
    critical_count = len([k for k in kpis if k.impact_level == 'Critical'])
    high_count = len([k for k in kpis if k.impact_level == 'High'])
    total_count = len(kpis)
    
    # Base score
    health_score = 70.0
    
    # Penalize for critical issues
    health_score -= (critical_count * 15)
    health_score -= (high_count * 5)
    
    # Bonus for having more KPIs tracked (engagement indicator)
    if total_count >= 20:
        health_score += 10
    
    return max(0, min(100, health_score))


def evaluate_account_for_voc_sprint(account, triggers):
    """Evaluate if account needs VoC Sprint playbook"""
    reasons = []
    score = 0  # Higher score = more urgent need
    
    # Calculate health score proxy
    health_score = calculate_health_score_proxy(account.account_id)
    
    # Check NPS threshold (using health score as proxy)
    nps_threshold = triggers.get('nps_threshold', 10)
    nps_proxy = health_score / 10  # Convert to 0-10 scale
    if nps_proxy < nps_threshold:
        reasons.append(f"Low NPS proxy ({nps_proxy:.1f} < {nps_threshold})")
        score += 30
    
    # Check CSAT threshold (using health score as proxy)
    csat_threshold = triggers.get('csat_threshold', 3.6)
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
    
    # Check for high support ticket volume (indicates dissatisfaction)
    kpis = KPI.query.filter_by(account_id=account.account_id).all()
    support_tickets_kpi = next((k for k in kpis if 'ticket' in k.kpi_parameter.lower()), None)
    if support_tickets_kpi and support_tickets_kpi.data:
        try:
            ticket_count = int(support_tickets_kpi.data)
            if ticket_count > 10:
                reasons.append(f"High support tickets ({ticket_count})")
                score += 15
        except:
            pass
    
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
    
    # Check for SLA breach indicators
    sla_breach_kpi = next((k for k in kpis if 'sla' in k.kpi_parameter.lower() or 'breach' in k.kpi_parameter.lower()), None)
    if sla_breach_kpi and sla_breach_kpi.impact_level == 'Critical':
        reasons.append("SLA breaches detected")
        score += 40
    
    # Check support ticket volume
    support_kpis = [k for k in kpis if 'support' in k.kpi_parameter.lower() or 'ticket' in k.kpi_parameter.lower()]
    if support_kpis:
        for kpi in support_kpis:
            if kpi.impact_level in ['Critical', 'High']:
                reasons.append(f"High support volume: {kpi.kpi_parameter}")
                score += 25
                break
    
    # Check response time indicators
    response_kpi = next((k for k in kpis if 'response' in k.kpi_parameter.lower()), None)
    if response_kpi and response_kpi.impact_level in ['Critical', 'High']:
        reasons.append("Slow response times detected")
        score += 30
    
    # Check escalation indicators
    escalation_kpi = next((k for k in kpis if 'escalat' in k.kpi_parameter.lower()), None)
    if escalation_kpi and escalation_kpi.impact_level == 'Critical':
        reasons.append("High escalation volume")
        score += 20
    
    return {
        'needed': score > 0,
        'urgency_score': score,
        'urgency_level': 'Critical' if score >= 60 else ('High' if score >= 30 else 'Medium'),
        'reasons': reasons,
        'support_metrics': len(support_kpis)
    }


def evaluate_account_for_renewal_safeguard(account, triggers):
    """Evaluate if account needs Renewal Safeguard playbook"""
    reasons = []
    score = 0
    
    # Calculate health score
    health_score = calculate_health_score_proxy(account.account_id)
    
    # Check health score threshold
    health_threshold = triggers.get('health_score_threshold', 70)
    if health_score < health_threshold:
        reasons.append(f"Low health score ({health_score:.1f} < {health_threshold})")
        score += 35
    
    # Check account status for risk signals
    if account.account_status.lower() == 'at risk':
        reasons.append("Account marked 'At Risk' - renewal jeopardy")
        score += 50
    
    # Check for engagement indicators
    kpis = KPI.query.filter_by(account_id=account.account_id).all()
    engagement_kpis = [k for k in kpis if 'engagement' in k.kpi_parameter.lower() or 'qbr' in k.kpi_parameter.lower()]
    for kpi in engagement_kpis:
        if 'declin' in str(kpi.data).lower() or 'missed' in str(kpi.data).lower():
            reasons.append(f"Declining engagement: {kpi.kpi_parameter}")
            score += 25
            break
    
    # Check revenue size (higher revenue = higher priority to save)
    if account.revenue and account.revenue > 200000:
        reasons.append(f"High-value account (${account.revenue:,.0f} ARR)")
        score += 15
    
    # Assume renewal within 90 days if health is low (simplified)
    if health_score < 60:
        reasons.append("Likely approaching renewal window")
        score += 10
    
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
    
    # Check adoption (high KPI count indicates good adoption)
    kpi_count = KPI.query.filter_by(account_id=account.account_id).count()
    if kpi_count >= 15:
        reasons.append(f"High feature adoption ({kpi_count} KPIs tracked)")
        score += 30
    
    # Check revenue size (expansion potential)
    if account.revenue and account.revenue > 100000:
        reasons.append(f"Strong revenue base (${account.revenue:,.0f}) - expansion ready")
        score += 20
    
    # Check for growth indicators
    growth_kpis = KPI.query.filter_by(account_id=account.account_id).filter(
        KPI.kpi_parameter.like('%growth%') | KPI.kpi_parameter.like('%user%')
    ).all()
    
    for kpi in growth_kpis:
        if 'grow' in str(kpi.data).lower() or 'increas' in str(kpi.data).lower():
            reasons.append(f"Growth signal: {kpi.kpi_parameter}")
            score += 15
            break
    
    # Check for usage approaching limits (simulated)
    if kpi_count >= 20:
        reasons.append("High usage - approaching capacity limits")
        score += 15
    
    return {
        'needed': score > 0,
        'urgency_score': score,
        'urgency_level': 'High' if score >= 80 else ('Medium' if score >= 50 else 'Low'),
        'reasons': reasons,
        'health_score': health_score,
        'expansion_potential': float(account.revenue * 0.3) if account.revenue else 0
    }


@playbook_recommendations_api.route('/api/playbooks/recommendations/<playbook_id>', methods=['POST'])
def get_playbook_recommendations(playbook_id):
    """Get account recommendations for a specific playbook"""
    try:
        customer_id = get_customer_id()
        data = request.json or {}
        triggers = data.get('triggers', {})
        
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

