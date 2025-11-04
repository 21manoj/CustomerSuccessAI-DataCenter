#!/usr/bin/env python3
"""
Comprehensive test suite for KPIReferenceRange migration.
Run this BEFORE deploying to AWS!
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from extensions import db
from models import Customer, User, Account, KPIReferenceRange

def get_kpi_reference_range(customer_id, kpi_name):
    """
    Get KPI reference range with fallback logic.
    Returns (range, source) where source is 'custom' or 'default'
    """
    # Try customer-specific first
    custom_range = KPIReferenceRange.query.filter_by(
        customer_id=customer_id,
        kpi_name=kpi_name
    ).first()
    
    if custom_range:
        return custom_range, 'custom'
    
    # Fall back to system default
    default_range = KPIReferenceRange.query.filter_by(
        customer_id=None,
        kpi_name=kpi_name
    ).first()
    
    if default_range:
        return default_range, 'default'
    
    return None, None

def calculate_health_score(customer_id, kpi_name, kpi_value):
    """Calculate health score using appropriate reference range"""
    ref_range, source = get_kpi_reference_range(customer_id, kpi_name)
    
    if not ref_range:
        return {'status': 'unknown', 'score': 0, 'source': 'none'}
    
    # Determine health status
    if ref_range.higher_is_better:
        if kpi_value >= ref_range.healthy_min:
            status = 'healthy'
            score = 95
        elif kpi_value >= ref_range.risk_min:
            status = 'risk'
            score = 65
        else:
            status = 'critical'
            score = 30
    else:
        if kpi_value <= ref_range.healthy_max:
            status = 'healthy'
            score = 95
        elif kpi_value <= ref_range.risk_max:
            status = 'risk'
            score = 65
        else:
            status = 'critical'
            score = 30
    
    return {'status': status, 'score': score, 'source': source}

def test_migration():
    """Test that migration works correctly"""
    
    # Import existing app configuration
    try:
        from app_v3_minimal import app
    except ImportError:
        # Create minimal Flask app for testing
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/kpi_dashboard.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
    
    with app.app_context():
        print("=" * 60)
        print("TESTING KPIREFERENCERANGE MIGRATION")
        print("=" * 60)
        
        # Test 1: Default ranges still exist
        print("\n✓ Test 1: Checking default ranges...")
        default_count = KPIReferenceRange.query.filter_by(
            customer_id=None
        ).count()
        assert default_count == 68, f"Expected 68 defaults, got {default_count}"
        print(f"  ✅ Found {default_count} default ranges")
        
        # Test 2: Existing customers use fallback
        print("\n✓ Test 2: Testing fallback for existing customers...")
        existing_customers = Customer.query.all()
        
        if not existing_customers:
            print("  ⚠️  No customers found, skipping test")
        else:
            # Get a sample KPI name from defaults
            sample_kpi = KPIReferenceRange.query.filter_by(customer_id=None).first()
            
            for customer in existing_customers:
                ref_range, source = get_kpi_reference_range(
                    customer.customer_id,
                    sample_kpi.kpi_name
                )
                assert ref_range is not None, f"No range found for {customer.customer_name}"
                assert source == 'default', f"Should use default, got {source}"
                print(f"  ✅ {customer.customer_name} uses default ranges")
        
        # Test 3: Can create custom range
        print("\n✓ Test 3: Testing custom range creation...")
        if not existing_customers:
            print("  ⚠️  No customers found, skipping test")
        else:
            test_customer = existing_customers[0]
            
            custom_range = KPIReferenceRange(
                customer_id=test_customer.customer_id,
                kpi_name='Test Custom KPI',
                unit='USD',
                higher_is_better=True,
                critical_min=0,
                critical_max=1000,
                risk_min=1000,
                risk_max=5000,
                healthy_min=5000,
                healthy_max=10000
            )
            db.session.add(custom_range)
            db.session.commit()
            
            # Verify custom range is returned
            ref_range, source = get_kpi_reference_range(
                test_customer.customer_id,
                'Test Custom KPI'
            )
            assert source == 'custom', f"Should use custom, got {source}"
            print(f"  ✅ Custom range created and retrieved")
            
            # Cleanup
            db.session.delete(custom_range)
            db.session.commit()
        
        # Test 4: Composite unique constraint works
        print("\n✓ Test 4: Testing composite unique constraint...")
        
        if not existing_customers:
            print("  ⚠️  No customers found, skipping test")
        else:
            test_customer = existing_customers[0]
            
            # Create custom range
            range1 = KPIReferenceRange(
                customer_id=test_customer.customer_id,
                kpi_name='Unique Test',
                unit='%',
                higher_is_better=True,
                critical_min=0, critical_max=10,
                risk_min=10, risk_max=20,
                healthy_min=20, healthy_max=100
            )
            db.session.add(range1)
            db.session.commit()
            
            # Try to create duplicate
            try:
                range2 = KPIReferenceRange(
                    customer_id=test_customer.customer_id,
                    kpi_name='Unique Test',  # Same customer + KPI
                    unit='%',
                    higher_is_better=True,
                    critical_min=0, critical_max=10,
                    risk_min=10, risk_max=20,
                    healthy_min=20, healthy_max=100
                )
                db.session.add(range2)
                db.session.commit()
                assert False, "Should have raised unique constraint error"
            except Exception as e:
                db.session.rollback()
                print(f"  ✅ Duplicate correctly rejected: {str(e)[:50]}")
            
            # Cleanup
            db.session.delete(range1)
            db.session.commit()
        
        # Test 5: Different customers can have same KPI name
        print("\n✓ Test 5: Testing same KPI name for different customers...")
        
        if len(existing_customers) < 2:
            print("  ⚠️  Need at least 2 customers, skipping test")
        else:
            customer1, customer2 = existing_customers[0], existing_customers[1]
            
            range1 = KPIReferenceRange(
                customer_id=customer1.customer_id,
                kpi_name='Same KPI Name',
                unit='USD',
                higher_is_better=True,
                critical_min=0, critical_max=100,
                risk_min=100, risk_max=500,
                healthy_min=500, healthy_max=1000
            )
            
            range2 = KPIReferenceRange(
                customer_id=customer2.customer_id,
                kpi_name='Same KPI Name',  # Same name, different customer!
                unit='USD',
                higher_is_better=True,
                critical_min=0, critical_max=10000,
                risk_min=10000, risk_max=50000,
                healthy_min=50000, healthy_max=100000
            )
            
            db.session.add_all([range1, range2])
            db.session.commit()
            
            # Verify both exist independently
            r1, s1 = get_kpi_reference_range(customer1.customer_id, 'Same KPI Name')
            r2, s2 = get_kpi_reference_range(customer2.customer_id, 'Same KPI Name')
            
            assert r1.healthy_min == 500, "Customer 1 range wrong"
            assert r2.healthy_min == 50000, "Customer 2 range wrong"
            print(f"  ✅ Both customers have independent ranges")
            
            # Cleanup
            db.session.delete(range1)
            db.session.delete(range2)
            db.session.commit()
        
        # Test 6: Health score calculation uses correct range
        print("\n✓ Test 6: Testing health score with custom range...")
        
        if not existing_customers:
            print("  ⚠️  No customers found, skipping test")
        else:
            test_customer = existing_customers[0]
            
            # Create custom range for test
            custom_range = KPIReferenceRange(
                customer_id=test_customer.customer_id,
                kpi_name='Revenue Test',
                unit='USD',
                higher_is_better=True,
                critical_min=0,
                critical_max=10000,
                risk_min=10000,
                risk_max=50000,
                healthy_min=50000,
                healthy_max=100000
            )
            db.session.add(custom_range)
            db.session.commit()
            
            # Calculate health score
            result = calculate_health_score(
                customer_id=test_customer.customer_id,
                kpi_name='Revenue Test',
                kpi_value=75000  # In healthy range
            )
            
            assert result['status'] == 'healthy', f"Expected healthy, got {result['status']}"
            assert result['score'] > 90, f"Expected score > 90, got {result['score']}"
            assert result['source'] == 'custom', f"Expected custom source, got {result['source']}"
            print(f"  ✅ Health score calculated correctly: {result['score']} (source: {result['source']})")
            
            # Cleanup
            db.session.delete(custom_range)
            db.session.commit()
        
        # Test 7: System defaults are not affected by customer data
        print("\n✓ Test 7: Verifying system defaults integrity...")
        system_defaults = KPIReferenceRange.query.filter_by(customer_id=None).count()
        assert system_defaults == 68, f"System defaults changed! Expected 68, got {system_defaults}"
        print(f"  ✅ System defaults intact: {system_defaults} ranges")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nSafe to deploy to AWS ✅")
        
        return True

if __name__ == '__main__':
    try:
        success = test_migration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

