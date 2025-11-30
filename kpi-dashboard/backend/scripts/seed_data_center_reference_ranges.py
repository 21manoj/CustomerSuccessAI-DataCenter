#!/usr/bin/env python3
"""
Script to seed KPI reference ranges for the Data Center customer (Serverless Model).

These reference ranges are used for:
1. Alerting (playbook triggers)
2. Dashboard visualization (color-coding)
3. KPI health status indicators

Note: Health score calculation uses regression formula (not these ranges).
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extensions import db
from models import KPIReferenceRange, Customer
from app_v3_minimal import app

# Data Center Customer Reference Ranges
DATA_CENTER_RANGES = [
    {
        'kpi_name': 'daily_invocations',
        'unit': 'count',
        'higher_is_better': True,
        'critical_min': 0,
        'critical_max': 956,
        'risk_min': 956,
        'risk_max': 32551,
        'healthy_min': 32551,
        'healthy_max': 267534,
        'description': 'Daily invocation count - High-volume production workload'
    },
    {
        'kpi_name': 'invocations_30d',
        'unit': 'count',
        'higher_is_better': True,
        'critical_min': 0,
        'critical_max': 28680,
        'risk_min': 28680,
        'risk_max': 976530,
        'healthy_min': 976530,
        'healthy_max': 8026020,
        'description': '30-day invocation count - Enterprise-scale usage'
    },
    {
        'kpi_name': 'invocation_velocity_change_pct',
        'unit': '%',
        'higher_is_better': True,
        'critical_min': -100,
        'critical_max': -15,
        'risk_min': -15,
        'risk_max': 30,
        'healthy_min': 30,
        'healthy_max': 75,
        'description': 'Month-over-month velocity change - STRONGEST PREDICTOR (r=0.985)'
    },
    {
        'kpi_name': 'monthly_spend',
        'unit': 'USD',
        'higher_is_better': True,
        'critical_min': 0,
        'critical_max': 1386,
        'risk_min': 1386,
        'risk_max': 13046,
        'healthy_min': 13046,
        'healthy_max': 81205,
        'description': 'Monthly spend in USD - High-value customer'
    },
    {
        'kpi_name': 'days_since_last_invocation',
        'unit': 'days',
        'higher_is_better': False,  # Lower is better
        'critical_min': 8,
        'critical_max': 44,
        'risk_min': 1,
        'risk_max': 8,
        'healthy_min': 0,
        'healthy_max': 1,
        'description': 'Days since last invocation - STRONG CHURN SIGNAL (r=-0.924)'
    },
    {
        'kpi_name': 'error_rate_pct',
        'unit': '%',
        'higher_is_better': False,  # Lower is better
        'critical_min': 2.03,
        'critical_max': 20.17,
        'risk_min': 0.64,
        'risk_max': 2.03,
        'healthy_min': 0,
        'healthy_max': 0.64,
        'description': 'Error rate percentage - STRONG QUALITY SIGNAL (r=-0.868)'
    },
    {
        'kpi_name': 'p95_latency_ms',
        'unit': 'milliseconds',
        'higher_is_better': True,
        'critical_min': 0,
        'critical_max': 156138,
        'risk_min': 156138,
        'risk_max': 414223,
        'healthy_min': 414223,
        'healthy_max': 883815,
        'description': 'P95 latency in milliseconds - Complex workloads'
    },
    {
        'kpi_name': 'avg_execution_time_sec',
        'unit': 'seconds',
        'higher_is_better': True,
        'critical_min': 0,
        'critical_max': 152.4,
        'risk_min': 152.4,
        'risk_max': 407.9,
        'healthy_min': 407.9,
        'healthy_max': 875.7,
        'description': 'Average execution time in seconds - Long-running compute tasks'
    },
    {
        'kpi_name': 'cold_start_pct',
        'unit': '%',
        'higher_is_better': False,  # Lower is better
        'critical_min': 60.65,
        'critical_max': 116.4,
        'risk_min': 21.5,
        'risk_max': 60.65,
        'healthy_min': 0,
        'healthy_max': 21.5,
        'description': 'Cold start percentage - Warm containers, frequent usage'
    },
    {
        'kpi_name': 'health_score',
        'unit': 'score',
        'higher_is_better': True,
        'critical_min': 0,
        'critical_max': 39,
        'risk_min': 39,
        'risk_max': 65,
        'healthy_min': 65,
        'healthy_max': 107,
        'description': 'Overall health score (0-100) - Low churn risk, expansion opportunity'
    }
]


def seed_data_center_reference_ranges(customer_id=None, customer_name=None):
    """
    Seed KPI reference ranges for the Data Center customer.
    
    Args:
        customer_id: Specific customer ID (if None, will search by name)
        customer_name: Customer name to search for (default: "Data Center" or "Serverless")
    """
    with app.app_context():
        # Find customer
        if customer_id:
            customer = Customer.query.get(customer_id)
        elif customer_name:
            customer = Customer.query.filter(
                Customer.customer_name.ilike(f'%{customer_name}%')
            ).first()
        else:
            # Try common names
            customer = Customer.query.filter(
                (Customer.customer_name.ilike('%data center%')) |
                (Customer.customer_name.ilike('%serverless%')) |
                (Customer.customer_name.ilike('%modal%')) |
                (Customer.customer_name.ilike('%baseten%')) |
                (Customer.customer_name.ilike('%fal%'))
            ).first()
        
        if not customer:
            print("❌ ERROR: Data Center customer not found!")
            print("\nAvailable customers:")
            all_customers = Customer.query.all()
            for c in all_customers:
                print(f"  - ID: {c.customer_id}, Name: {c.customer_name}")
            print("\nUsage:")
            print("  python seed_data_center_reference_ranges.py <customer_id>")
            print("  OR")
            print("  python seed_data_center_reference_ranges.py --name 'Customer Name'")
            return False
        
        print(f"✅ Found customer: ID={customer.customer_id}, Name={customer.customer_name}")
        
        # Delete existing ranges for this customer
        deleted_count = KPIReferenceRange.query.filter_by(customer_id=customer.customer_id).delete()
        print(f"🗑️  Deleted {deleted_count} existing reference ranges for customer {customer.customer_id}")
        
        # Insert new ranges
        created_count = 0
        for range_data in DATA_CENTER_RANGES:
            # Create range strings for UI display
            critical_range_str = f"{range_data['critical_min']}-{range_data['critical_max']} {range_data['unit']}"
            risk_range_str = f"{range_data['risk_min']}-{range_data['risk_max']} {range_data['unit']}"
            healthy_range_str = f"{range_data['healthy_min']}-{range_data['healthy_max']} {range_data['unit']}"
            
            ref_range = KPIReferenceRange(
                customer_id=customer.customer_id,
                kpi_name=range_data['kpi_name'],
                unit=range_data['unit'],
                higher_is_better=range_data['higher_is_better'],
                critical_min=range_data['critical_min'],
                critical_max=range_data['critical_max'],
                risk_min=range_data['risk_min'],
                risk_max=range_data['risk_max'],
                healthy_min=range_data['healthy_min'],
                healthy_max=range_data['healthy_max'],
                critical_range=critical_range_str,
                risk_range=risk_range_str,
                healthy_range=healthy_range_str,
                description=range_data['description']
            )
            
            db.session.add(ref_range)
            created_count += 1
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n✅ Successfully created {created_count} reference ranges for customer {customer.customer_id}")
        print(f"   Customer: {customer.customer_name}")
        print(f"\n📊 Reference Ranges Created:")
        for range_data in DATA_CENTER_RANGES:
            print(f"   - {range_data['kpi_name']} ({range_data['unit']})")
        
        # Verify
        verify_count = KPIReferenceRange.query.filter_by(customer_id=customer.customer_id).count()
        print(f"\n✅ Verification: {verify_count} ranges in database for customer {customer.customer_id}")
        
        return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed Data Center customer KPI reference ranges')
    parser.add_argument('customer_id', type=int, nargs='?', help='Customer ID')
    parser.add_argument('--name', type=str, help='Customer name to search for')
    
    args = parser.parse_args()
    
    if args.customer_id:
        seed_data_center_reference_ranges(customer_id=args.customer_id)
    elif args.name:
        seed_data_center_reference_ranges(customer_name=args.name)
    else:
        seed_data_center_reference_ranges()

