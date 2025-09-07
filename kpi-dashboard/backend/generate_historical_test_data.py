#!/usr/bin/env python3
"""
Generate historical test data for 4-6 months to test time series functionality.
"""

from app import app
from health_score_storage import HealthScoreStorageService
from models import KPI, Account, HealthTrend, KPITimeSeries
from extensions import db
from datetime import datetime, timedelta
import random

def generate_historical_test_data(customer_id=6, months_back=6):
    """Generate historical KPI and health score data for testing."""
    
    with app.app_context():
        try:
            storage_service = HealthScoreStorageService()
            
            # Get all accounts for this customer
            accounts = Account.query.filter_by(customer_id=customer_id).all()
            print(f"Found {len(accounts)} accounts for customer {customer_id}")
            
            # Get all KPIs for this customer
            kpis = db.session.query(KPI).join(Account).filter(
                Account.customer_id == customer_id
            ).all()
            print(f"Found {len(kpis)} KPIs for customer {customer_id}")
            
            if not accounts or not kpis:
                print("No accounts or KPIs found. Please ensure data is loaded first.")
                return
            
            # Generate data for the last N months
            current_date = datetime.now()
            generated_data = {
                'health_trends': 0,
                'kpi_time_series': 0,
                'months_generated': []
            }
            
            for month_offset in range(months_back, 0, -1):
                # Calculate target date (going back in time)
                if month_offset == months_back:
                    # For the oldest month, go back full months_back
                    target_date = current_date.replace(day=1) - timedelta(days=30 * month_offset)
                else:
                    # For subsequent months, go back by month_offset
                    target_date = current_date.replace(day=1) - timedelta(days=30 * month_offset)
                
                month = target_date.month
                year = target_date.year
                month_key = f"{year}-{month:02d}"
                
                print(f"\nGenerating data for {month_key}...")
                
                # Generate health trends for this month
                health_count = 0
                for account in accounts:
                    # Generate realistic health scores with some variation
                    base_scores = {
                        'overall': random.uniform(60, 85),
                        'product_usage': random.uniform(65, 90),
                        'support': random.uniform(60, 80),
                        'customer_sentiment': random.uniform(55, 75),
                        'business_outcomes': random.uniform(45, 70),
                        'relationship_strength': random.uniform(60, 85)
                    }
                    
                    # Check if trend already exists
                    existing_trend = HealthTrend.query.filter_by(
                        account_id=account.account_id,
                        month=month,
                        year=year
                    ).first()
                    
                    if existing_trend:
                        # Update existing trend
                        existing_trend.overall_health_score = base_scores['overall']
                        existing_trend.product_usage_score = base_scores['product_usage']
                        existing_trend.support_score = base_scores['support']
                        existing_trend.customer_sentiment_score = base_scores['customer_sentiment']
                        existing_trend.business_outcomes_score = base_scores['business_outcomes']
                        existing_trend.relationship_strength_score = base_scores['relationship_strength']
                        existing_trend.updated_at = datetime.utcnow()
                    else:
                        # Create new trend
                        trend = HealthTrend(
                            account_id=account.account_id,
                            customer_id=customer_id,
                            month=month,
                            year=year,
                            overall_health_score=base_scores['overall'],
                            product_usage_score=base_scores['product_usage'],
                            support_score=base_scores['support'],
                            customer_sentiment_score=base_scores['customer_sentiment'],
                            business_outcomes_score=base_scores['business_outcomes'],
                            relationship_strength_score=base_scores['relationship_strength'],
                            total_kpis=len([k for k in kpis if k.account_id == account.account_id]),
                            valid_kpis=len([k for k in kpis if k.account_id == account.account_id])
                        )
                        db.session.add(trend)
                    
                    health_count += 1
                
                # Generate KPI time series data for this month
                kpi_count = 0
                for kpi in kpis:
                    # Generate realistic KPI values with some historical variation
                    # Parse current KPI value to understand the format
                    current_value = storage_service.health_engine.parse_kpi_value(kpi.data, kpi.kpi_parameter)
                    
                    if current_value is not None:
                        # Add some variation based on the month (trend over time)
                        variation_factor = 1.0 + (random.uniform(-0.15, 0.15) * (months_back - month_offset + 1) / months_back)
                        historical_value = current_value * variation_factor
                        
                        # Calculate health status and score for historical value
                        health_info = storage_service.health_engine.calculate_health_status(
                            historical_value, kpi.kpi_parameter
                        )
                        
                        # Check if time series record already exists
                        existing_record = KPITimeSeries.query.filter_by(
                            kpi_id=kpi.kpi_id,
                            month=month,
                            year=year
                        ).first()
                        
                        if existing_record:
                            # Update existing record
                            existing_record.value = historical_value
                            existing_record.health_status = health_info['status']
                            existing_record.health_score = health_info['score']
                            existing_record.updated_at = datetime.utcnow()
                        else:
                            # Create new record
                            kpi_trend = KPITimeSeries(
                                kpi_id=kpi.kpi_id,
                                account_id=kpi.account_id,
                                customer_id=customer_id,
                                month=month,
                                year=year,
                                value=historical_value,
                                health_status=health_info['status'],
                                health_score=health_info['score']
                            )
                            db.session.add(kpi_trend)
                        
                        kpi_count += 1
                
                # Commit for this month
                db.session.commit()
                
                generated_data['health_trends'] += health_count
                generated_data['kpi_time_series'] += kpi_count
                generated_data['months_generated'].append(month_key)
                
                print(f"✅ Generated {health_count} health trends and {kpi_count} KPI time series for {month_key}")
            
            print(f"\n🎉 Historical data generation complete!")
            print(f"Total health trends generated: {generated_data['health_trends']}")
            print(f"Total KPI time series generated: {generated_data['kpi_time_series']}")
            print(f"Months generated: {', '.join(generated_data['months_generated'])}")
            
            return generated_data
            
        except Exception as e:
            print(f"❌ Error generating historical test data: {e}")
            db.session.rollback()
            raise e

if __name__ == '__main__':
    # Generate 6 months of historical data
    result = generate_historical_test_data(customer_id=6, months_back=6)
    print(f"\nResult: {result}")
