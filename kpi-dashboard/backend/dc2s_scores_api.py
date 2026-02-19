#!/usr/bin/env python3
"""
DC2_S Scores API
Endpoints for retrieving calculated scores
"""

from flask import Blueprint, request, jsonify
from models import db, KPIScore, PillarScore, HealthScore, Account
from auth_middleware import get_current_customer_id
from utils.score_calculator import ScoreCalculator, calculate_customer_scores, calculate_account_scores
from datetime import date, datetime
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

dc2s_scores_api = Blueprint('dc2s_scores_api', __name__, url_prefix='/api/dc2s/scores')

# ================================================================
# GET SCORES
# ================================================================

@dc2s_scores_api.route('/account/<int:account_id>/latest', methods=['GET'])
def get_latest_scores(account_id):
    """Get latest scores for an account"""
    customer_id = get_current_customer_id()
    
    # Verify account belongs to customer
    account = Account.query.filter_by(account_id=account_id, customer_id=customer_id).first()
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Get latest health score
    health = HealthScore.query.filter_by(account_id=account_id)\
        .order_by(HealthScore.measurement_month.desc())\
        .first()
    
    if not health:
        return jsonify({'error': 'No scores calculated yet'}), 404
    
    # Get pillar scores for same month
    pillars = PillarScore.query.filter_by(
        account_id=account_id,
        measurement_month=health.measurement_month
    ).all()
    
    # Get KPI scores for same month
    kpis = KPIScore.query.filter_by(
        account_id=account_id,
        measurement_month=health.measurement_month
    ).all()
    
    return jsonify({
        'account_id': account_id,
        'measurement_month': health.measurement_month.isoformat(),
        'health_score': health.to_dict(),
        'pillar_scores': [p.to_dict() for p in pillars],
        'kpi_scores': [k.to_dict() for k in kpis]
    })


@dc2s_scores_api.route('/account/<int:account_id>/history', methods=['GET'])
def get_score_history(account_id):
    """Get historical scores for an account"""
    customer_id = get_current_customer_id()
    
    # Verify account
    account = Account.query.filter_by(account_id=account_id, customer_id=customer_id).first()
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Get parameters
    months = request.args.get('months', 12, type=int)  # Default 12 months
    
    # Get health score history
    health_history = HealthScore.query.filter_by(account_id=account_id)\
        .order_by(HealthScore.measurement_month.desc())\
        .limit(months)\
        .all()
    
    return jsonify({
        'account_id': account_id,
        'months': len(health_history),
        'history': [h.to_dict() for h in health_history]
    })


@dc2s_scores_api.route('/customer/summary', methods=['GET'])
def get_customer_summary():
    """Get score summary for all customer accounts"""
    customer_id = get_current_customer_id()
    
    # Get all accounts
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    account_ids = [a.account_id for a in accounts]
    
    # Get latest health score for each account
    latest_scores = []
    for account_id in account_ids:
        health = HealthScore.query.filter_by(account_id=account_id)\
            .order_by(HealthScore.measurement_month.desc())\
            .first()
        
        if health:
            latest_scores.append({
                'account_id': account_id,
                'account_name': next((a.account_name for a in accounts if a.account_id == account_id), None),
                'health_score': float(health.health_score),
                'health_status': health.health_status,
                'trend': health.trend,
                'measurement_month': health.measurement_month.isoformat()
            })
    
    # Calculate averages
    if latest_scores:
        avg_health = sum(s['health_score'] for s in latest_scores) / len(latest_scores)
        status_counts = {}
        for s in latest_scores:
            status = s['health_status']
            status_counts[status] = status_counts.get(status, 0) + 1
    else:
        avg_health = 0
        status_counts = {}
    
    return jsonify({
        'customer_id': customer_id,
        'total_accounts': len(accounts),
        'accounts_with_scores': len(latest_scores),
        'average_health_score': round(avg_health, 2),
        'status_distribution': status_counts,
        'accounts': latest_scores
    })


# ================================================================
# CALCULATE/RECALCULATE SCORES
# ================================================================

@dc2s_scores_api.route('/calculate', methods=['POST'])
def calculate_scores():
    """
    Calculate scores for accounts
    
    Request body:
    {
      "account_id": 1001,  // Optional - if not provided, calculates all accounts
      "measurement_month": "2024-12-01"  // Optional - defaults to current month
    }
    """
    customer_id = get_current_customer_id()
    data = request.json or {}
    
    # Parse month
    month_str = data.get('measurement_month')
    if month_str:
        try:
            measurement_month = datetime.strptime(month_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': f'Invalid date format. Expected YYYY-MM-DD, got: {month_str}'
            }), 400
    else:
        # Default to first day of current month
        today = date.today()
        measurement_month = date(today.year, today.month, 1)
    
    account_id = data.get('account_id')
    
    try:
        if account_id:
            # Calculate for single account
            result = calculate_account_scores(customer_id, account_id, measurement_month)
            
            return jsonify({
                'success': True,
                'account_id': account_id,
                'measurement_month': measurement_month.isoformat(),
                'result': result
            })
        else:
            # Calculate for all accounts
            results = calculate_customer_scores(customer_id, measurement_month)
            
            successful = sum(1 for r in results.values() if r and 'error' not in r)
            failed = len(results) - successful
            
            return jsonify({
                'success': True,
                'measurement_month': measurement_month.isoformat(),
                'total_accounts': len(results),
                'successful': successful,
                'failed': failed,
                'results': results
            })
    
    except Exception as e:
        logger.error(f"Error calculating scores: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Score calculation failed. Please try again or contact support.'
        }), 500


# ================================================================
# PILLAR BREAKDOWN
# ================================================================

@dc2s_scores_api.route('/account/<int:account_id>/pillars/<pillar_code>', methods=['GET'])
def get_pillar_breakdown(account_id, pillar_code):
    """Get detailed breakdown for a specific pillar"""
    customer_id = get_current_customer_id()
    
    # Verify account
    account = Account.query.filter_by(account_id=account_id, customer_id=customer_id).first()
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    # Get latest pillar score
    pillar = PillarScore.query.filter_by(account_id=account_id, pillar_code=pillar_code)\
        .order_by(PillarScore.measurement_month.desc())\
        .first()
    
    if not pillar:
        return jsonify({'error': f'No scores found for pillar {pillar_code}'}), 404
    
    # Get individual KPI scores
    contributing_kpis = pillar.contributing_kpis or {}
    kpi_details = []
    
    for kpi_code in contributing_kpis.keys():
        kpi = KPIScore.query.filter_by(
            account_id=account_id,
            kpi_code=kpi_code,
            measurement_month=pillar.measurement_month
        ).first()
        
        if kpi:
            kpi_details.append(kpi.to_dict())
    
    return jsonify({
        'account_id': account_id,
        'pillar_code': pillar_code,
        'measurement_month': pillar.measurement_month.isoformat(),
        'pillar_score': float(pillar.pillar_score),
        'pillar_status': pillar.pillar_status,
        'kpi_weights': pillar.kpi_weights,
        'kpi_details': kpi_details
    })
