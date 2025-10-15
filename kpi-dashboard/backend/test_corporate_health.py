#!/usr/bin/env python3
"""
Test corporate health score calculation directly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import KPI, Account
from health_score_engine import HealthScoreEngine

def test_corporate_health_scores():
    """Test corporate health score calculation directly"""
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
        
        # Group KPIs by component
        components = {
            'Product Usage': [],
            'Support': [],
            'Customer Sentiment': [],
            'Business Outcomes': [],
            'Relationship Strength': []
        }
        
        for kpi, _ in all_kpis_with_accounts:
            component = kpi.health_score_component
            if component in components:
                # Convert KPI object to dict for processing
                kpi_dict = {
                    'kpi_parameter': kpi.kpi_parameter,
                    'data': kpi.data,
                    'impact_level': kpi.impact_level,
                    'health_score_component': kpi.health_score_component,
                    'category': kpi.category,
                    'weight': kpi.weight,
                    'source_review': kpi.source_review,
                    'measurement_frequency': kpi.measurement_frequency
                }
                components[component].append(kpi_dict)
        
        # Calculate health scores for each category
        category_scores = []
        for component, kpis in components.items():
            if kpis:
                print(f"\n{component}: {len(kpis)} KPIs")
                category_score = HealthScoreEngine.calculate_category_health_score(kpis, component)
                category_scores.append(category_score)
                print(f"  Average Score: {category_score['average_score']:.1f}%")
                print(f"  Health Status: {category_score['health_status']}")
                print(f"  Color: {category_score['color']}")
        
        # Calculate overall health score
        overall_score = HealthScoreEngine.calculate_overall_health_score(category_scores)
        
        print(f"\nOverall Health Score: {overall_score['overall_score']:.1f}%")
        print(f"Overall Health Status: {overall_score['health_status']}")
        print(f"Overall Color: {overall_score['color']}")
        
        # Test individual KPI health scoring
        print("\nTesting individual KPI health scoring...")
        if all_kpis_with_accounts:
            sample_kpi = all_kpis_with_accounts[0][0]
            kpi_dict = {
                'kpi_parameter': sample_kpi.kpi_parameter,
                'data': sample_kpi.data,
                'impact_level': sample_kpi.impact_level,
                'health_score_component': sample_kpi.health_score_component,
                'category': sample_kpi.category,
                'weight': sample_kpi.weight,
                'source_review': sample_kpi.source_review,
                'measurement_frequency': sample_kpi.measurement_frequency
            }
            
            enhanced_kpi = HealthScoreEngine.calculate_kpi_health_score(kpi_dict)
            print(f"Sample KPI: {enhanced_kpi['kpi_parameter']}")
            print(f"  Data: {enhanced_kpi['data']}")
            print(f"  Parsed Value: {enhanced_kpi['parsed_value']}")
            print(f"  Health Score: {enhanced_kpi['health_score']:.1f}%")
            print(f"  Health Status: {enhanced_kpi['health_status']}")
            print(f"  Reference Range: {enhanced_kpi['reference_range']}")

if __name__ == "__main__":
    test_corporate_health_scores() 