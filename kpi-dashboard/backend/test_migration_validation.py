#!/usr/bin/env python3
"""
Simple Migration Validation Test

Tests that the migration worked correctly and basic queries function.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import KPI, Account, Customer
from kpi_queries import get_account_level_kpis, get_product_kpis

def test_migration():
    """Test that migration worked correctly"""
    
    print("="*60)
    print("MIGRATION VALIDATION TEST")
    print("="*60)
    
    with app.app_context():
        # Test 1: Verify columns exist
        print("\n[1/5] Verifying columns exist...")
        try:
            # Try to query with product_id filter
            kpis = KPI.query.filter(KPI.product_id.is_(None)).limit(1).all()
            print("✅ product_id column exists and is queryable")
        except Exception as e:
            print(f"❌ FAIL: {e}")
            return False
        
        try:
            # Try to query with aggregation_type filter
            kpis = KPI.query.filter(KPI.aggregation_type.is_(None)).limit(1).all()
            print("✅ aggregation_type column exists and is queryable")
        except Exception as e:
            print(f"❌ FAIL: {e}")
            return False
        
        # Test 2: Verify all existing KPIs have product_id = NULL
        print("\n[2/5] Verifying existing data...")
        try:
            total_kpis = KPI.query.count()
            null_product_kpis = KPI.query.filter(KPI.product_id.is_(None)).count()
            
            if total_kpis == null_product_kpis:
                print(f"✅ All {total_kpis} existing KPIs have product_id=NULL")
            else:
                print(f"⚠️  WARN: {total_kpis} total KPIs, {null_product_kpis} have product_id=NULL")
        except Exception as e:
            print(f"❌ FAIL: {e}")
            return False
        
        # Test 3: Test helper functions
        print("\n[3/5] Testing helper functions...")
        try:
            # Get first account
            account = Account.query.first()
            if account:
                customer_id = account.customer_id
                account_kpis = get_account_level_kpis(account.account_id, customer_id)
                
                # Verify all returned KPIs have product_id = NULL
                for kpi in account_kpis:
                    if kpi.product_id is not None:
                        print(f"❌ FAIL: KPI {kpi.kpi_id} has product_id={kpi.product_id}")
                        return False
                
                print(f"✅ get_account_level_kpis() works correctly ({len(account_kpis)} KPIs)")
            else:
                print("⚠️  No accounts found, skipping helper function test")
        except Exception as e:
            print(f"❌ FAIL: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 4: Test product KPIs query (should return empty for now)
        print("\n[4/5] Testing product KPIs query...")
        try:
            if account:
                product_kpis = get_product_kpis(account.account_id, customer_id=customer_id)
                print(f"✅ get_product_kpis() works correctly ({len(product_kpis)} product KPIs)")
            else:
                print("⚠️  No accounts found, skipping product KPIs test")
        except Exception as e:
            print(f"❌ FAIL: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test 5: Verify no double-counting
        print("\n[5/5] Verifying no double-counting...")
        try:
            if account:
                # Get all KPIs directly
                all_kpis = KPI.query.filter_by(account_id=account.account_id).all()
                product_count = sum(1 for k in all_kpis if k.product_id is not None)
                
                # Get account-level via helper
                account_kpis = get_account_level_kpis(account.account_id, customer_id)
                
                # Verify account_kpis doesn't include products
                account_with_products = sum(1 for k in account_kpis if k.product_id is not None)
                
                if account_with_products == 0:
                    print(f"✅ No double-counting: {len(account_kpis)} account KPIs, {product_count} product KPIs")
                else:
                    print(f"❌ FAIL: Found {account_with_products} product KPIs in account-level query!")
                    return False
            else:
                print("⚠️  No accounts found, skipping double-counting test")
        except Exception as e:
            print(f"❌ FAIL: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\n" + "="*60)
    print("✅ MIGRATION VALIDATION: PASS")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_migration()
    sys.exit(0 if success else 1)


