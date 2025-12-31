#!/usr/bin/env python3
"""
Generate Data Center seed data and convert to Excel format for review
"""
import sys
import os
import pandas as pd
from pathlib import Path

# Add the generate_seed_data.py directory to path
sys.path.insert(0, os.path.expanduser('~/Downloads/dc_seed_data'))

try:
    from generate_seed_data import (
        generate_tenants, generate_kpi_values, TenantProfile, KPIRecord,
        START_DATE, END_DATE
    )
except ImportError as e:
    print(f"❌ Error importing generate_seed_data.py: {e}")
    print("   Please ensure generate_seed_data.py is in ~/Downloads/dc_seed_data/")
    sys.exit(1)

def generate_excel_file():
    """Generate seed data and save to Excel file"""
    print("\n" + "="*70)
    print("GENERATING DATA CENTER SEED DATA - EXCEL FORMAT")
    print("="*70)
    
    # Generate tenant profiles
    print("\n[1/3] Generating tenant profiles...")
    tenants = generate_tenants()
    print(f"✅ Generated {len(tenants)} tenant profiles")
    
    # Generate KPI history
    print("\n[2/3] Generating KPI history...")
    all_kpi_records = []
    current_date = START_DATE
    month_counter = 0
    
    while current_date <= END_DATE:
        month_counter += 1
        print(f"   Processing month {month_counter} ({current_date.strftime('%Y-%m-%d')})...")
        
        for tenant in tenants:
            kpi_values = generate_kpi_values(tenant, current_date)
            for kpi_id, value in kpi_values.items():
                all_kpi_records.append({
                    'tenant_id': tenant.tenant_id,
                    'tenant_name': tenant.tenant_name,
                    'month': current_date.strftime('%Y-%m'),
                    'kpi_id': kpi_id,
                    'value': value
                })
        
        # Move to next month
        from datetime import timedelta
        current_date += timedelta(days=30)
    
    print(f"✅ Generated {len(all_kpi_records)} KPI records")
    
    # Convert to DataFrames
    print("\n[3/3] Converting to Excel format...")
    
    # Tenants DataFrame
    tenants_data = []
    for tenant in tenants:
        tenants_data.append({
            'tenant_id': tenant.tenant_id,
            'tenant_name': tenant.tenant_name,
            'segment': tenant.segment,
            'industry': tenant.industry,
            'arr': tenant.arr,
            'mrr': tenant.mrr,
            'contract_start': tenant.contract_start,
            'contract_end': tenant.contract_end,
            'contract_term_months': tenant.contract_term_months,
            'service_type': tenant.service_type,
            'total_racks': tenant.total_racks,
            'power_allocation_kw': tenant.power_allocation_kw,
            'bandwidth_allocation_gbps': tenant.bandwidth_allocation_gbps,
            'sla_tier': tenant.sla_tier,
            'sla_uptime_target': tenant.sla_uptime_target,
            'csm_assigned': tenant.csm_assigned,
            'health_category': tenant.health_category,
            'onboarding_date': tenant.onboarding_date,
            'facilities_count': tenant.facilities_count,
            'services_active_count': tenant.services_active_count,
            'is_strategic': tenant.is_strategic,
        })
    
    df_tenants = pd.DataFrame(tenants_data)
    
    # KPI History DataFrame
    df_kpis = pd.DataFrame(all_kpi_records)
    
    # Create Excel file with multiple sheets
    output_file = os.path.expanduser('~/Downloads/dc_seed_data/DC_Seed_Data_Review.xlsx')
    
    print(f"\n📝 Writing to Excel file: {output_file}")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_tenants.to_excel(writer, sheet_name='Tenants', index=False)
        df_kpis.to_excel(writer, sheet_name='KPI_History', index=False)
        
        # Create summary sheet
        summary_data = {
            'Metric': [
                'Total Tenants',
                'Total KPI Records',
                'Months of Data',
                'Date Range Start',
                'Date Range End',
                'Tenants by Segment - Enterprise',
                'Tenants by Segment - Mid-Market',
                'Tenants by Segment - SMB',
                'Tenants by Segment - Transactional',
            ],
            'Value': [
                len(tenants),
                len(all_kpi_records),
                month_counter,
                START_DATE.strftime('%Y-%m-%d'),
                END_DATE.strftime('%Y-%m-%d'),
                len([t for t in tenants if t.segment == 'Enterprise']),
                len([t for t in tenants if t.segment == 'Mid-Market']),
                len([t for t in tenants if t.segment == 'SMB']),
                len([t for t in tenants if t.segment == 'Transactional']),
            ]
        }
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Summary', index=False)
    
    print(f"✅ Excel file created: {output_file}")
    print(f"\n📊 Summary:")
    print(f"   - Tenants: {len(tenants)}")
    print(f"   - KPI Records: {len(all_kpi_records)}")
    print(f"   - Months: {month_counter}")
    print(f"   - Date Range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
    print("\n" + "="*70)
    print("✅ READY FOR REVIEW")
    print("="*70)
    print(f"\n📁 File location: {output_file}")
    print("   Please review the Excel file before proceeding with database upload.")
    print("="*70)

if __name__ == "__main__":
    generate_excel_file()



