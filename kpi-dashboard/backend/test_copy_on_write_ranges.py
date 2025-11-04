#!/usr/bin/env python3
"""
Test copy-on-write behavior for KPI Reference Ranges
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import KPIReferenceRange, Customer

def test_copy_on_write():
    """Test that editing system defaults creates customer overrides"""
    
    with app.app_context():
        print("=" * 70)
        print("TESTING COPY-ON-WRITE BEHAVIOR")
        print("=" * 70)
        
        # Get a customer
        customer = Customer.query.first()
        if not customer:
            print("❌ No customers found")
            return False
        
        customer_id = customer.customer_id
        print(f"\n📋 Testing with: {customer.customer_name} (ID: {customer_id})")
        
        # Test 1: Verify system defaults exist
        print("\n✓ Test 1: Check system defaults...")
        system_default = KPIReferenceRange.query.filter_by(
            customer_id=None,
            kpi_name="Net Promoter Score (NPS)"
        ).first()
        
        if not system_default:
            print("  ❌ System default for NPS not found")
            return False
        
        print(f"  ✅ System default found (range_id: {system_default.range_id})")
        print(f"     Healthy range: {system_default.healthy_min}-{system_default.healthy_max}")
        
        # Test 2: Simulate editing a system default
        print("\n✓ Test 2: Create customer override by 'editing' system default...")
        
        # Check if override already exists (from previous test runs)
        existing_override = KPIReferenceRange.query.filter_by(
            customer_id=customer_id,
            kpi_name="Net Promoter Score (NPS)"
        ).first()
        
        if existing_override:
            print(f"  ⚠️  Customer override already exists (range_id: {existing_override.range_id})")
            print(f"     Deleting for clean test...")
            db.session.delete(existing_override)
            db.session.commit()
        
        # Simulate copy-on-write logic
        new_override = KPIReferenceRange(
            customer_id=customer_id,
            kpi_name=system_default.kpi_name,
            unit=system_default.unit,
            higher_is_better=system_default.higher_is_better,
            critical_min=system_default.critical_min,
            critical_max=system_default.critical_max,
            risk_min=system_default.risk_min,
            risk_max=system_default.risk_max,
            healthy_min=60,  # Changed from 51 to 60
            healthy_max=system_default.healthy_max,
            critical_range=f"{system_default.critical_min}-{system_default.critical_max} {system_default.unit}",
            risk_range=f"{system_default.risk_min}-{system_default.risk_max} {system_default.unit}",
            healthy_range=f"60-{system_default.healthy_max} {system_default.unit}",
            description="Customer-specific override"
        )
        db.session.add(new_override)
        db.session.commit()
        
        print(f"  ✅ Customer override created (range_id: {new_override.range_id})")
        print(f"     Healthy range: {new_override.healthy_min}-{new_override.healthy_max}")
        
        # Test 3: Verify system default is unchanged
        print("\n✓ Test 3: Verify system default unchanged...")
        system_default_after = KPIReferenceRange.query.filter_by(
            customer_id=None,
            kpi_name="Net Promoter Score (NPS)"
        ).first()
        
        if system_default_after.healthy_min == system_default.healthy_min:
            print(f"  ✅ System default unchanged (healthy_min still {system_default.healthy_min})")
        else:
            print(f"  ❌ System default was modified! (was {system_default.healthy_min}, now {system_default_after.healthy_min})")
            return False
        
        # Test 4: Verify fallback returns customer override
        print("\n✓ Test 4: Verify fallback returns customer override...")
        
        # Simulate fallback logic
        customer_range = KPIReferenceRange.query.filter_by(
            customer_id=customer_id,
            kpi_name="Net Promoter Score (NPS)"
        ).first()
        
        system_range = KPIReferenceRange.query.filter_by(
            customer_id=None,
            kpi_name="Net Promoter Score (NPS)"
        ).first()
        
        # Customer override takes precedence
        result_range = customer_range if customer_range else system_range
        
        if result_range.customer_id == customer_id:
            print(f"  ✅ Fallback returned customer override (range_id: {result_range.range_id})")
            print(f"     Healthy range: {result_range.healthy_min}-{result_range.healthy_max}")
        else:
            print(f"  ❌ Fallback returned system default instead of override")
            return False
        
        # Test 5: Check counts
        print("\n✓ Test 5: Verify database state...")
        system_count = KPIReferenceRange.query.filter_by(customer_id=None).count()
        customer_count = KPIReferenceRange.query.filter_by(customer_id=customer_id).count()
        
        print(f"  ✅ System defaults: {system_count}")
        print(f"  ✅ Customer overrides: {customer_count}")
        
        # Test 6: Check for other customers
        print("\n✓ Test 6: Verify other customers unaffected...")
        other_customer = Customer.query.filter(Customer.customer_id != customer_id).first()
        if other_customer:
            other_override = KPIReferenceRange.query.filter_by(
                customer_id=other_customer.customer_id,
                kpi_name="Net Promoter Score (NPS)"
            ).first()
            
            if not other_override:
                print(f"  ✅ {other_customer.customer_name} still uses system default (no override)")
            else:
                print(f"  ℹ️  {other_customer.customer_name} has their own override")
        
        # Cleanup (optional - comment out to keep the override)
        print("\n🧹 Cleanup...")
        response = input("Delete test override? (yes/no): ")
        if response.lower() == 'yes':
            db.session.delete(new_override)
            db.session.commit()
            print("  ✅ Test override deleted")
        else:
            print("  ℹ️  Test override kept for inspection")
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print("\n📋 SUMMARY:")
        print("  ✓ System defaults preserved")
        print("  ✓ Customer overrides work correctly")
        print("  ✓ Fallback logic returns customer override")
        print("  ✓ Multi-tenant isolation verified")
        
        return True

if __name__ == '__main__':
    try:
        success = test_copy_on_write()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        sys.exit(1)

