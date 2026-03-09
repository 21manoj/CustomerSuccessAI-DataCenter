#!/usr/bin/env python3
"""
Initialize DC2_S configuration for Customer 9
Maps existing KPIs to new pillar structure
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from models import db, CustomerConfig, DC2SKPI, Account
from sqlalchemy import func, distinct

# KPI to Pillar mapping (from your existing 35 KPIs)
KPI_TO_PILLAR_MAPPING = {
    # P3 - AI Workload Performance
    'DC2S_PERF_GPU_UTIL': 'P3',
    'DC2S_PERF_CPU_UTIL': 'P3',
    'DC2S_PERF_MEM_UTIL': 'P3',
    'DC2S_PERF_THROUGHPUT': 'P3',
    'DC2S_PERF_LATENCY': 'P3',
    'DC2S_PERF_IOPS': 'P3',
    'DC2S_PERF_NETWORK_UTIL': 'P3',

    # P4 - Customer Health
    'DC2S_SUP_CUSTOMER_SATISFACTION': 'P4',
    'DC2S_BIZ_FEATURE_ADOPTION': 'P4',
    'DC2S_BIZ_TIME_TO_VALUE': 'P4',
    'DC2S_SUP_TICKET_RESOLUTION_TIME': 'P4',

    # P1 - Delivery & Velocity
    'DC2S_SCALE_DEPLOYMENT_VELOCITY': 'P1',
    'DC2S_SCALE_CLUSTER_EXPANSION': 'P1',
    'DC2S_SCALE_WORKLOAD_GROWTH': 'P1',
    'DC2S_SCALE_AUTO_SCALING_SCORE': 'P1',
    'DC2S_SCALE_ELASTICITY_SCORE': 'P1',

    # P5 - Experience (Expansion & Growth)
    'DC2S_BIZ_ROI': 'P5',
    'DC2S_BIZ_REVENUE_IMPACT': 'P5',
    'DC2S_BIZ_STRATEGIC_ALIGNMENT': 'P5',
    'DC2S_BIZ_COMPETITIVE_ADVANTAGE': 'P5',
    'DC2S_BIZ_INNOVATION_SCORE': 'P5',
    'DC2S_SCALE_CAPACITY_HEADROOM': 'P5',

    # P2 - Operational Stability
    'DC2S_SUP_UPTIME_PCT': 'P2',
    'DC2S_SUP_MTBF': 'P2',
    'DC2S_SUP_MTTR': 'P2',
    'DC2S_SUP_SLA_COMPLIANCE': 'P2',
    'DC2S_COST_TOTAL_MONTHLY': 'P2',
    'DC2S_COST_PER_WORKLOAD': 'P2',
    'DC2S_COST_POWER_EFFICIENCY': 'P2',
    'DC2S_COST_COOLING_EFFICIENCY': 'P2',
    'DC2S_COST_OPTIMIZATION_SCORE': 'P2',
    'DC2S_COST_CAPEX_UTILIZATION': 'P2',
    'DC2S_COST_OPEX_RATIO': 'P2',
    'DC2S_PERF_STORAGE_UTIL': 'P2',
    'DC2S_SCALE_STORAGE_GROWTH': 'P2'
}

def initialize_customer9_config():
    with app.app_context():
        print("="*70)
        print("INITIALIZING CUSTOMER 9 DC2_S CONFIGURATION")
        print("="*70)
        print()
        
        # Check if config already exists
        config = CustomerConfig.query.filter_by(customer_id=9).first()
        
        if config and config.vertical == 'dc2_s':
            print("⚠️  Customer 9 already has DC2_S config")
            response = input("Do you want to overwrite? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                return
        
        # Get actual KPIs used by Customer 9
        print("🔍 Discovering KPIs used by Customer 9...")
        
        # Get accounts for customer 9
        customer9_accounts = db.session.query(Account.account_id).filter_by(customer_id=9).all()
        account_ids = [acc[0] for acc in customer9_accounts]
        
        if not account_ids:
            print("❌ No accounts found for customer 9")
            return
        
        # Get distinct KPI codes from DC2SKPI for these accounts
        existing_kpis = db.session.query(distinct(DC2SKPI.kpi_code))\
            .filter(DC2SKPI.account_id.in_(account_ids))\
            .all()
        
        kpi_codes = [kpi[0] for kpi in existing_kpis]
        
        print(f"   Found {len(kpi_codes)} unique KPIs")
        
        # Group KPIs by pillar
        kpis_by_pillar = {'P1': [], 'P2': [], 'P3': [], 'P4': [], 'P5': []}
        unmapped_kpis = []
        
        for kpi_code in kpi_codes:
            # Try mapping first (for DC2S_PERF_* format)
            pillar = KPI_TO_PILLAR_MAPPING.get(kpi_code)
            
            # If not found, try extracting from catalog format (P3-KPI1 -> P3)
            if not pillar and '-' in kpi_code:
                prefix = kpi_code.split('-')[0]
                if prefix in ['P1', 'P2', 'P3', 'P4', 'P5']:
                    pillar = prefix
            
            if pillar and pillar in kpis_by_pillar:
                kpis_by_pillar[pillar].append(kpi_code)
            else:
                unmapped_kpis.append(kpi_code)
        
        print()
        print("📊 KPI Distribution:")
        for pillar, kpis in kpis_by_pillar.items():
            print(f"   {pillar}: {len(kpis)} KPIs")
        
        if unmapped_kpis:
            print()
            print(f"⚠️  Unmapped KPIs ({len(unmapped_kpis)}):")
            for kpi in unmapped_kpis:
                print(f"   - {kpi}")
        
        # Calculate weights
        pillar_weights = {
            'P3': 0.25,
            'P4': 0.20,
            'P1': 0.15,
            'P5': 0.20,
            'P2': 0.20
        }
        
        kpi_weights = {}
        for pillar, kpis in kpis_by_pillar.items():
            if kpis:
                equal_weight = 1.0 / len(kpis)
                kpi_weights[pillar] = {kpi: equal_weight for kpi in kpis}
            else:
                kpi_weights[pillar] = {}
        
        # Create or update config
        if config:
            print()
            print("📝 Updating existing config...")
            config.vertical = 'dc2_s'
            config.dc2s_pillar_weights = pillar_weights
            config.dc2s_enabled_kpis = kpi_codes
            config.dc2s_kpi_overrides = {}
            config.dc2s_kpi_weights = kpi_weights
            config.dc2s_kpi_definitions = {}
            config.customized_by = 'system_initialization'
        else:
            print()
            print("📝 Creating new config...")
            config = CustomerConfig(
                customer_id=9,
                vertical='dc2_s',
                dc2s_pillar_weights=pillar_weights,
                dc2s_enabled_kpis=kpi_codes,
                dc2s_kpi_overrides={},
                dc2s_kpi_weights=kpi_weights,
                dc2s_kpi_definitions={},
                customized_by='system_initialization'
            )
            db.session.add(config)
        
        db.session.commit()
        
        print()
        print("="*70)
        print("✅ CUSTOMER 9 CONFIGURATION INITIALIZED!")
        print("="*70)
        print()
        print("Configuration Summary:")
        print(f"  • Total KPIs: {len(kpi_codes)}")
        print(f"  • P1 (Delivery & Velocity) KPIs: {len(kpis_by_pillar['P1'])}")
        print(f"  • P2 (Operational Stability) KPIs: {len(kpis_by_pillar['P2'])}")
        print(f"  • P3 (AI Workload Performance) KPIs: {len(kpis_by_pillar['P3'])}")
        print(f"  • P4 (Customer Health) KPIs: {len(kpis_by_pillar['P4'])}")
        print(f"  • P5 (Experience) KPIs: {len(kpis_by_pillar['P5'])}")
        print()
        print("Next steps:")
        print("  1. Test config API: curl http://localhost:5059/api/dc2s/config")
        print("  2. Proceed to Phase 2 (Score Calculator)")
        print()

if __name__ == '__main__':
    initialize_customer9_config()
