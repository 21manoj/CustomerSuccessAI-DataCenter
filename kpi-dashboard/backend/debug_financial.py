#!/usr/bin/env python3
"""
Debug script for financial projections
"""

from app import app
from extensions import db
from models import HealthTrend, Account

def debug_financial_projections():
    with app.app_context():
        # Get account 1
        account = Account.query.filter_by(account_id=1).first()
        print(f"Account: {account.account_name}")
        
        # Get recent trends
        recent_trends = HealthTrend.query.filter_by(
            account_id=1
        ).order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).limit(3).all()
        
        print(f"Found {len(recent_trends)} trends")
        
        if recent_trends:
            latest_trend = recent_trends[0]
            print(f"Latest trend attributes: {[attr for attr in dir(latest_trend) if not attr.startswith('_')]}")
            print(f"Latest trend overall_health_score: {latest_trend.overall_health_score}")
            
            # Test accessing the attributes
            try:
                print(f"product_usage_score: {latest_trend.product_usage_score}")
                print(f"support_score: {latest_trend.support_score}")
                print(f"customer_sentiment_score: {latest_trend.customer_sentiment_score}")
                print(f"business_outcomes_score: {latest_trend.business_outcomes_score}")
                print(f"relationship_strength_score: {latest_trend.relationship_strength_score}")
                print(f"overall_health_score: {latest_trend.overall_health_score}")
            except Exception as e:
                print(f"Error accessing attributes: {e}")

if __name__ == '__main__':
    debug_financial_projections()
