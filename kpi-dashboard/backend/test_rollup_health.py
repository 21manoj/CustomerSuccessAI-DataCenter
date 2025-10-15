#!/usr/bin/env python3
"""
Test rollup health score calculation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import KPI, Account
from corporate_api import calculate_enhanced_health_scores

def test_rollup_health():
    """Test rollup health score calculation"""
    with app.app_context():
        customer_id = 6
        
        # Get all accounts for this customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        print(f"Found {len(accounts)} accounts")
        
        # Get all KPIs with accounts
        all_kpis_with_accounts = []
        for account in accounts:
            account_kpis = KPI.query.filter_by(account_id=account.account_id).all()
            if account_kpis:
                for kpi in account_kpis:
                    all_kpis_with_accounts.append((kpi, account))
        
        print(f"Found {len(all_kpis_with_accounts)} KPI-account pairs")
        
        # Test enhanced health score calculation
        print("\nTesting enhanced health score calculation...")
        try:
            health_analysis = calculate_enhanced_health_scores(all_kpis_with_accounts)
            print("Health analysis completed successfully")
            print(f"Category scores: {len(health_analysis['category_scores'])}")
            print(f"Overall score: {health_analysis['overall_score']['overall_score']:.1f}%")
            
            # Test creating health_scores dict
            category_scores = health_analysis['category_scores']
            overall_score = health_analysis['overall_score']
            
            health_scores = {
                'product_usage': next((cat['average_score'] for cat in category_scores if cat['category'] == 'Product Usage'), 0),
                'support': next((cat['average_score'] for cat in category_scores if cat['category'] == 'Support'), 0),
                'customer_sentiment': next((cat['average_score'] for cat in category_scores if cat['category'] == 'Customer Sentiment'), 0),
                'business_outcomes': next((cat['average_score'] for cat in category_scores if cat['category'] == 'Business Outcomes'), 0),
                'relationship_strength': next((cat['average_score'] for cat in category_scores if cat['category'] == 'Relationship Strength'), 0),
                'overall': overall_score['overall_score']
            }
            
            print(f"Health scores dict: {health_scores}")
            
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_rollup_health() 