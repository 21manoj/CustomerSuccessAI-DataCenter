#!/usr/bin/env python3
"""
Simple test for financial projections
"""

from app import app
from extensions import db
from models import HealthTrend, Account
from financial_projections_api import calculate_financial_impact

def test_simple():
    with app.app_context():
        try:
            # Test the calculate_financial_impact function
            impact = calculate_financial_impact(
                'Product Usage KPI', 
                70.0, 
                80.0, 
                1000000
            )
            print(f"Financial impact calculation successful: {impact}")
            
            # Test accessing HealthTrend
            trend = HealthTrend.query.first()
            if trend:
                print(f"Trend found: {trend.overall_health_score}")
            else:
                print("No trends found")
                
        except Exception as e:
            import traceback
            print(f"Error: {e}")
            print(f"Traceback: {traceback.format_exc()}")

if __name__ == '__main__':
    test_simple()
