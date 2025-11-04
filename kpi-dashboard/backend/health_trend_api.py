#!/usr/bin/env python3
"""
Health Trend API for tracking and retrieving monthly health score trends.
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id, get_current_user_id
from datetime import datetime, timedelta
from extensions import db
from models import HealthTrend, Account, Customer
import json

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
        print(f"Error fetching health trends: {e}")
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
        
        return jsonify({
            'message': 'Health trend saved successfully',
            'trend_id': trend.trend_id
        })
        
    except Exception as e:
        print(f"Error saving health trend: {e}")
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
        
        return jsonify({
            'message': f'Generated {generated_count} health trends',
            'generated_count': generated_count
        })
        
    except Exception as e:
        print(f"Error generating health trends: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to generate health trends'}), 500
