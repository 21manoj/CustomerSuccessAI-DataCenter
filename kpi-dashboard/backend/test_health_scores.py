#!/usr/bin/env python3
"""
Test script to debug health score calculation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import KPI, Account

def test_health_score_calculation():
    """Test health score calculation"""
    with app.app_context():
        customer_id = 6
        
        # Get all accounts for this customer
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        print(f"Found {len(accounts)} accounts")
        
        # Get all KPIs for this customer
        all_kpis = KPI.query.join(Account).filter(Account.customer_id == customer_id).all()
        print(f"Found {len(all_kpis)} KPIs")
        
        # Test component matching
        product_usage_kpis = [kpi for kpi in all_kpis if 'Product Usage' in kpi.health_score_component]
        support_kpis = [kpi for kpi in all_kpis if 'Support' in kpi.health_score_component]
        customer_sentiment_kpis = [kpi for kpi in all_kpis if 'Customer Sentiment' in kpi.health_score_component]
        business_outcomes_kpis = [kpi for kpi in all_kpis if 'Business Outcomes' in kpi.health_score_component]
        relationship_strength_kpis = [kpi for kpi in all_kpis if 'Relationship Strength' in kpi.health_score_component]
        
        print(f"Product Usage KPIs: {len(product_usage_kpis)}")
        print(f"Support KPIs: {len(support_kpis)}")
        print(f"Customer Sentiment KPIs: {len(customer_sentiment_kpis)}")
        print(f"Business Outcomes KPIs: {len(business_outcomes_kpis)}")
        print(f"Relationship Strength KPIs: {len(relationship_strength_kpis)}")
        
        # Test data parsing
        print("\nTesting data parsing:")
        for kpi in product_usage_kpis[:3]:
            print(f"  {kpi.kpi_parameter}: {kpi.data}")

if __name__ == "__main__":
    test_health_score_calculation() 