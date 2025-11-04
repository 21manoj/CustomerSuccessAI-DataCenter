#!/usr/bin/env python3
"""
Fix TTFV and other 'lower is better' KPI ranges that were stored incorrectly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from models import KPIReferenceRange
from health_score_config import KPI_REFERENCE_RANGES

def fix_lower_is_better_ranges():
    """Fix all 'lower is better' KPI ranges"""
    
    with app.app_context():
        print("=" * 70)
        print("FIXING 'LOWER IS BETTER' KPI RANGES")
        print("=" * 70)
        
        fixed_count = 0
        
        for kpi_name, config in KPI_REFERENCE_RANGES.items():
            if not config['higher_is_better']:
                # This is a "lower is better" KPI
                print(f"\n📊 Fixing: {kpi_name}")
                
                # Get the range from database
                ref_range = KPIReferenceRange.query.filter_by(
                    customer_id=None,  # System default
                    kpi_name=kpi_name
                ).first()
                
                if not ref_range:
                    print(f"   ⚠️  Not found in database, skipping")
                    continue
                
                # Map by color
                ranges = config['ranges']
                critical_range = None
                risk_range = None
                healthy_range = None
                
                for key, range_data in ranges.items():
                    if range_data['color'] == 'red':
                        critical_range = range_data
                    elif range_data['color'] == 'yellow':
                        risk_range = range_data
                    elif range_data['color'] == 'green':
                        healthy_range = range_data
                
                # Show current (wrong) values
                print(f"   Current (WRONG):")
                print(f"     Critical: {ref_range.critical_min}-{ref_range.critical_max}")
                print(f"     Risk: {ref_range.risk_min}-{ref_range.risk_max}")
                print(f"     Healthy: {ref_range.healthy_min}-{ref_range.healthy_max}")
                
                # Update with correct values
                ref_range.critical_min = critical_range['min']
                ref_range.critical_max = critical_range['max']
                ref_range.risk_min = risk_range['min']
                ref_range.risk_max = risk_range['max']
                ref_range.healthy_min = healthy_range['min']
                ref_range.healthy_max = healthy_range['max']
                
                # Update string representations
                ref_range.critical_range = f"{ref_range.critical_min}-{ref_range.critical_max} {config['unit']}"
                ref_range.risk_range = f"{ref_range.risk_min}-{ref_range.risk_max} {config['unit']}"
                ref_range.healthy_range = f"{ref_range.healthy_min}-{ref_range.healthy_max} {config['unit']}"
                
                print(f"   Fixed (CORRECT):")
                print(f"     Critical: {ref_range.critical_min}-{ref_range.critical_max} (RED)")
                print(f"     Risk: {ref_range.risk_min}-{ref_range.risk_max} (YELLOW)")
                print(f"     Healthy: {ref_range.healthy_min}-{ref_range.healthy_max} (GREEN)")
                
                fixed_count += 1
        
        db.session.commit()
        
        print("\n" + "=" * 70)
        print(f"✅ FIXED {fixed_count} 'LOWER IS BETTER' KPIs")
        print("=" * 70)
        
        # Verify TTFV specifically
        print("\n🔍 VERIFICATION - TTFV:")
        ttfv = KPIReferenceRange.query.filter_by(
            customer_id=None,
            kpi_name="Time to First Value (TTFV)"
        ).first()
        
        if ttfv:
            print(f"  Healthy: {ttfv.healthy_min}-{ttfv.healthy_max} days (should be 0-7)")
            print(f"  Risk: {ttfv.risk_min}-{ttfv.risk_max} days (should be 8-30)")
            print(f"  Critical: {ttfv.critical_min}-{ttfv.critical_max} days (should be 31-999)")
            
            if ttfv.healthy_min == 0 and ttfv.healthy_max == 7:
                print("\n✅ TTFV ranges are now CORRECT!")
            else:
                print("\n❌ TTFV ranges are still WRONG!")
        else:
            print("  ❌ TTFV not found")

if __name__ == '__main__':
    try:
        fix_lower_is_better_ranges()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        sys.exit(1)

