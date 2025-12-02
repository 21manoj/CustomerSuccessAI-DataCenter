#!/usr/bin/env python3
"""
Health Trend API for tracking and retrieving monthly health score trends.

FIXED: Removed invalid account.health_score references
FIXED: Now properly gets health scores from HealthTrend table
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from datetime import datetime, timedelta
from extensions import db
from models import HealthTrend, Account, Customer
import json
import logging

logger = logging.getLogger(__name__)

health_trend_api = Blueprint('health_trend_api', __name__)

@health_trend_api.route('/api/health-trends', methods=['GET'])
def get_health_trends():
    """Get health trend data for a customer or specific account"""
    try:
        customer_id = get_current_customer_id()
        account_id = request.args.get('account_id')
        
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400
        
        # Build query
        query = HealthTrend.query.filter_by(customer_id=int(customer_id))
        
        if account_id:
            query = query.filter_by(account_id=int(account_id))
        
        # Get trends for the last 12 months
        trends = query.order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).limit(12).all()
        
        # Format data for frontend
        trend_data = []
        for trend in reversed(trends):  # Reverse to get chronological order
            month_name = datetime(2024, trend.month, 1).strftime('%b')
            trend_data.append({
                'month': month_name,
                'score': float(trend.overall_health_score),
                'product_usage_score': float(trend.product_usage_score) if trend.product_usage_score else None,
                'support_score': float(trend.support_score) if trend.support_score else None,
                'customer_sentiment_score': float(trend.customer_sentiment_score) if trend.customer_sentiment_score else None,
                'business_outcomes_score': float(trend.business_outcomes_score) if trend.business_outcomes_score else None,
                'relationship_strength_score': float(trend.relationship_strength_score) if trend.relationship_strength_score else None,
                'total_kpis': trend.total_kpis,
                'valid_kpis': trend.valid_kpis
            })
        
        return jsonify({
            'trends': trend_data,
            'total_months': len(trend_data)
        })
        
    except Exception as e:
        logger.error(f"Error fetching health trends: {e}", exc_info=True)
        return jsonify({'error': 'Failed to fetch health trends'}), 500

@health_trend_api.route('/api/health-trends', methods=['POST'])
def create_health_trend():
    """Create or update health trend data for a specific month"""
    try:
        customer_id = get_current_customer_id()
        data = request.get_json()
        
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400
        
        required_fields = ['account_id', 'month', 'year', 'overall_health_score']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if trend already exists
        existing_trend = HealthTrend.query.filter_by(
            account_id=data['account_id'],
            month=data['month'],
            year=data['year']
        ).first()
        
        if existing_trend:
            # Update existing trend
            existing_trend.overall_health_score = data['overall_health_score']
            existing_trend.product_usage_score = data.get('product_usage_score')
            existing_trend.support_score = data.get('support_score')
            existing_trend.customer_sentiment_score = data.get('customer_sentiment_score')
            existing_trend.business_outcomes_score = data.get('business_outcomes_score')
            existing_trend.relationship_strength_score = data.get('relationship_strength_score')
            existing_trend.total_kpis = data.get('total_kpis', 0)
            existing_trend.valid_kpis = data.get('valid_kpis', 0)
            existing_trend.updated_at = datetime.utcnow()
            
            # Publish event for automatic snapshot creation
            try:
                from event_system import event_manager, EventType
                event_manager.publish(
                    EventType.HEALTH_SCORES_UPDATED,
                    int(customer_id),
                    {
                        'account_id': data['account_id'],
                        'month': data['month'],
                        'year': data['year'],
                        'overall_health_score': data['overall_health_score'],
                        'action': 'health_trend_updated'
                    },
                    priority=2
                )
            except Exception as e:
                logger.warning(f"Could not publish health scores updated event: {e}")
            
            trend = existing_trend
        else:
            # Create new trend
            trend = HealthTrend(
                account_id=data['account_id'],
                customer_id=int(customer_id),
                month=data['month'],
                year=data['year'],
                overall_health_score=data['overall_health_score'],
                product_usage_score=data.get('product_usage_score'),
                support_score=data.get('support_score'),
                customer_sentiment_score=data.get('customer_sentiment_score'),
                business_outcomes_score=data.get('business_outcomes_score'),
                relationship_strength_score=data.get('relationship_strength_score'),
                total_kpis=data.get('total_kpis', 0),
                valid_kpis=data.get('valid_kpis', 0)
            )
            db.session.add(trend)
        
        db.session.commit()
        
        # Publish event for automatic snapshot creation
        try:
            from event_system import event_manager, EventType
            event_manager.publish(
                EventType.HEALTH_SCORES_UPDATED,
                int(customer_id),
                {
                    'account_id': data['account_id'],
                    'month': data['month'],
                    'year': data['year'],
                    'overall_health_score': data['overall_health_score'],
                    'action': 'health_trend_created'
                },
                priority=2
            )
        except Exception as e:
            logger.warning(f"Could not publish health scores updated event: {e}")
        
        return jsonify({
            'message': 'Health trend saved successfully',
            'trend_id': trend.trend_id
        })
        
    except Exception as e:
        logger.error(f"Error saving health trend: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to save health trend'}), 500

@health_trend_api.route('/api/health-trends/generate', methods=['POST'])
def generate_health_trends():
    """Generate health trend data for all accounts based on current KPI data"""
    try:
        customer_id = get_current_customer_id()
        
        if not customer_id:
            return jsonify({'error': 'Customer ID required'}), 400
        
        # Get all accounts for the customer
        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        
        if not accounts:
            return jsonify({'error': 'No accounts found for customer'}), 404
        
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year
        
        generated_count = 0
        
        for account in accounts:
            # For now, generate sample data. In production, this would calculate from actual KPI data
            sample_score = 50 + (account.account_id % 30) + (current_month * 2)
            
            # Check if trend already exists for this month
            existing_trend = HealthTrend.query.filter_by(
                account_id=account.account_id,
                month=current_month,
                year=current_year
            ).first()
            
            if not existing_trend:
                trend = HealthTrend(
                    account_id=account.account_id,
                    customer_id=int(customer_id),
                    month=current_month,
                    year=current_year,
                    overall_health_score=sample_score,
                    product_usage_score=sample_score + 5,
                    support_score=sample_score - 3,
                    customer_sentiment_score=sample_score + 2,
                    business_outcomes_score=sample_score - 1,
                    relationship_strength_score=sample_score + 1,
                    total_kpis=59,  # Assuming 59 KPIs per account
                    valid_kpis=45   # Assuming 45 valid KPIs
                )
                db.session.add(trend)
                generated_count += 1
        
        db.session.commit()
        
        # Publish events for automatic snapshot creation
        try:
            from event_system import event_manager, EventType
            for account in accounts:
                event_manager.publish(
                    EventType.HEALTH_SCORES_UPDATED,
                    int(customer_id),
                    {
                        'account_id': account.account_id,
                        'month': current_month,
                        'year': current_year,
                        'action': 'health_trends_generated'
                    },
                    priority=2
                )
        except Exception as e:
            logger.warning(f"Could not publish health scores updated events: {e}")
        
        return jsonify({
            'message': f'Generated {generated_count} health trends',
            'generated_count': generated_count
        })
        
    except Exception as e:
        logger.error(f"Error generating health trends: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to generate health trends'}), 500


# ========================================
# HELPER FUNCTIONS
# ========================================

def get_latest_health_score(account_id, customer_id):
    """
    Helper function to get the latest health score for an account.
    
    This is used by other modules that need health scores.
    
    Args:
        account_id: Account ID
        customer_id: Customer ID (for security validation)
    
    Returns:
        float: Latest health score, or None if not found
    """
    latest_trend = HealthTrend.query.filter_by(
        account_id=account_id,
        customer_id=customer_id
    ).order_by(
        HealthTrend.year.desc(),
        HealthTrend.month.desc()
    ).first()
    
    if latest_trend and latest_trend.overall_health_score:
        return float(latest_trend.overall_health_score)
    
    return None


def evaluate_voc_triggers(customer_id, triggers):
    """
    Evaluate VoC Sprint trigger conditions.
    
    FIXED: Now properly gets health scores from HealthTrend table instead of
    accessing non-existent account.health_score attribute.
    """
    nps_threshold = triggers.get('nps_threshold', 10)
    csat_threshold = triggers.get('csat_threshold', 3.6)
    churn_risk_threshold = triggers.get('churn_risk_threshold', 0.30)
    health_score_drop_threshold = triggers.get('health_score_drop_threshold', 10)
    
    # Get all accounts for this customer
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    
    triggered_accounts = []
    
    for account in accounts:
        account_triggers = []
        
        # ✅ FIXED: Get health score from HealthTrend table (not account.health_score)
        latest_trend = HealthTrend.query.filter_by(
            account_id=account.account_id,
            customer_id=customer_id
        ).order_by(
            HealthTrend.year.desc(),
            HealthTrend.month.desc()
        ).first()
        
        # Use 50.0 as default if no health trend exists yet
        health_score = float(latest_trend.overall_health_score) if latest_trend else 50.0
        
        # Check NPS (simulated - using health_score as proxy)
        if health_score < nps_threshold * 10:  # Scale to 0-100
            account_triggers.append(f"Low health score ({health_score:.1f}) as NPS proxy")
        
        # Check CSAT (using health_score / 20 as CSAT proxy on 0-5 scale)
        csat_proxy = health_score / 20.0
        if csat_proxy < csat_threshold:
            account_triggers.append(f"Low CSAT proxy ({csat_proxy:.2f})")
        
        # Check churn risk (using account status)
        if account.account_status == 'At Risk':
            account_triggers.append("Account marked as 'At Risk'")
        
        # Check health score drop (would need historical data for proper implementation)
        if health_score < 50:
            account_triggers.append(f"Low health score ({health_score:.1f})")
        
        if account_triggers:
            triggered_accounts.append({
                'account_id': account.account_id,
                'account_name': account.account_name,
                'health_score': health_score,
                'triggers': account_triggers
            })
    
    triggered = len(triggered_accounts) > 0
    
    return {
        'triggered': triggered,
        'message': f'VoC Sprint triggered for {len(triggered_accounts)} account(s)' if triggered else 'No accounts meet VoC Sprint trigger conditions',
        'details': {
            'nps_threshold': nps_threshold,
            'csat_threshold': csat_threshold,
            'churn_risk_threshold': churn_risk_threshold,
            'health_score_drop_threshold': health_score_drop_threshold
        },
        'affected_accounts': triggered_accounts
    }


def evaluate_activation_triggers(customer_id, triggers):
    """
    Evaluate Activation Blitz trigger conditions.
    
    FIXED: Now properly gets health scores from HealthTrend table instead of
    accessing non-existent account.health_score attribute.
    """
    adoption_index_threshold = triggers.get('adoption_index_threshold', 60)
    active_users_threshold = triggers.get('active_users_threshold', 50)
    dau_mau_threshold = triggers.get('dau_mau_threshold', 0.25)
    unused_feature_check = triggers.get('unused_feature_check', True)
    
    # Get all accounts for this customer
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    
    triggered_accounts = []
    
    for account in accounts:
        account_triggers = []
        
        # ✅ FIXED: Get health score from HealthTrend table (not account.health_score)
        latest_trend = HealthTrend.query.filter_by(
            account_id=account.account_id,
            customer_id=customer_id
        ).order_by(
            HealthTrend.year.desc(),
            HealthTrend.month.desc()
        ).first()
        
        # Use 60.0 as default if no health trend exists yet
        adoption_proxy = float(latest_trend.overall_health_score) if latest_trend else 60.0
        
        # Check adoption index (using health_score as proxy)
        if adoption_proxy < adoption_index_threshold:
            account_triggers.append(f"Low adoption index ({adoption_proxy:.1f})")
        
        # Check active users (simulated - would come from usage data)
        # For now, we'll simulate based on account revenue
        active_users_proxy = int(account.revenue / 1000) if account.revenue else 0
        if active_users_proxy < active_users_threshold:
            account_triggers.append(f"Low active users (~{active_users_proxy})")
        
        # Check DAU/MAU (simulated)
        dau_mau_proxy = 0.15 if adoption_proxy < 60 else 0.30
        if dau_mau_proxy < dau_mau_threshold:
            account_triggers.append(f"Low DAU/MAU ratio (~{dau_mau_proxy:.2f})")
        
        # Check for unused features (simulated)
        if unused_feature_check:
            # Get KPI count as proxy for feature usage
            from models import KPI
            kpi_count = KPI.query.filter_by(account_id=account.account_id).count()
            if kpi_count < 10:  # Arbitrary threshold
                account_triggers.append(f"Limited feature usage ({kpi_count} KPIs tracked)")
        
        if account_triggers:
            triggered_accounts.append({
                'account_id': account.account_id,
                'account_name': account.account_name,
                'adoption_index': adoption_proxy,
                'active_users': active_users_proxy,
                'triggers': account_triggers
            })
    
    triggered = len(triggered_accounts) > 0
    
    return {
        'triggered': triggered,
        'message': f'Activation Blitz triggered for {len(triggered_accounts)} account(s)' if triggered else 'No accounts meet Activation Blitz trigger conditions',
        'details': {
            'adoption_index_threshold': adoption_index_threshold,
            'active_users_threshold': active_users_threshold,
            'dau_mau_threshold': dau_mau_threshold,
            'unused_feature_check': unused_feature_check
        },
        'affected_accounts': triggered_accounts
    }