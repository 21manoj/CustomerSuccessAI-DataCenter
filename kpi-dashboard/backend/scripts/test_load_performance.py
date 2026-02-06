#!/usr/bin/env python3
"""
Load Testing - Test Score Calculator Performance
Tests score calculation with multiple accounts to verify performance
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from models import db, Account, DC2SKPI, CustomerConfig
from utils.score_calculator import calculate_customer_scores
from datetime import date, timedelta
from sqlalchemy import func

def test_load_performance():
    """Test score calculation performance with multiple accounts"""
    with app.app_context():
        print("="*70)
        print("LOAD TESTING - SCORE CALCULATOR PERFORMANCE")
        print("="*70)
        print()
        
        customer_id = 9
        
        # Get account count
        account_count = Account.query.filter_by(customer_id=customer_id).count()
        print(f"Customer {customer_id} has {account_count} accounts")
        print()
        
        # Test 1: Calculate scores for all accounts
        print("Test 1: Calculate scores for all accounts")
        measurement_month = date(2024, 12, 1)
        
        start_time = time.time()
        try:
            results = calculate_customer_scores(customer_id, measurement_month)
            elapsed_time = time.time() - start_time
            
            successful = sum(1 for r in results.values() if r and 'error' not in r)
            failed = len(results) - successful
            
            print(f"   ✅ Completed in {elapsed_time:.2f} seconds")
            print(f"   Accounts processed: {len(results)}")
            print(f"   Successful: {successful}")
            print(f"   Failed: {failed}")
            print(f"   Average time per account: {elapsed_time/len(results):.3f}s")
            print()
            
            # Performance metrics
            if elapsed_time < 60:
                print("   ✅ Performance: EXCELLENT (< 60s)")
            elif elapsed_time < 120:
                print("   ✅ Performance: GOOD (< 120s)")
            elif elapsed_time < 300:
                print("   ⚠️  Performance: ACCEPTABLE (< 5min)")
            else:
                print("   ❌ Performance: POOR (> 5min)")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        
        # Test 2: Check database query performance
        print("Test 2: Database query performance")
        
        # Count KPI measurements
        start_time = time.time()
        kpi_count = db.session.query(func.count(DC2SKPI.kpi_id)).filter(
            DC2SKPI.account_id.in_(
                db.session.query(Account.account_id).filter_by(customer_id=customer_id)
            )
        ).scalar()
        query_time = time.time() - start_time
        
        print(f"   Total KPI measurements: {kpi_count}")
        print(f"   Query time: {query_time:.3f}s")
        print()
        
        # Test 3: Check score table sizes
        print("Test 3: Score table sizes")
        from models import KPIScore, PillarScore, HealthScore
        
        kpi_score_count = KPIScore.query.count()
        pillar_score_count = PillarScore.query.count()
        health_score_count = HealthScore.query.count()
        
        print(f"   KPI Scores: {kpi_score_count}")
        print(f"   Pillar Scores: {pillar_score_count}")
        print(f"   Health Scores: {health_score_count}")
        print()
        
        print("="*70)
        print("✅ LOAD TEST COMPLETE")
        print("="*70)

if __name__ == '__main__':
    test_load_performance()
