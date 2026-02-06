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
    # AI Workload Performance
    'DC2S_PERF_GPU_UTIL': 'AI',
    'DC2S_PERF_CPU_UTIL': 'AI',
    'DC2S_PERF_MEM_UTIL': 'AI',
    'DC2S_PERF_THROUGHPUT': 'AI',
    'DC2S_PERF_LATENCY': 'AI',
    'DC2S_PERF_IOPS': 'AI',
    'DC2S_PERF_NETWORK_UTIL': 'AI',
    
    # Customer Health
    'DC2S_SUP_CUSTOMER_SATISFACTION': 'CH',
    'DC2S_BIZ_FEATURE_ADOPTION': 'CH',
    'DC2S_BIZ_TIME_TO_VALUE': 'CH',
    'DC2S_SUP_TICKET_RESOLUTION_TIME': 'CH',
    
    # Deployment Velocity
    'DC2S_SCALE_DEPLOYMENT_VELOCITY': 'DV',
    'DC2S_SCALE_CLUSTER_EXPANSION': 'DV',
    'DC2S_SCALE_WORKLOAD_GROWTH': 'DV',
    'DC2S_SCALE_AUTO_SCALING_SCORE': 'DV',
    'DC2S_SCALE_ELASTICITY_SCORE': 'DV',
    
    # Expansion & Growth
    'DC2S_BIZ_ROI': 'EX',
    'DC2S_BIZ_REVENUE_IMPACT': 'EX',
    'DC2S_BIZ_STRATEGIC_ALIGNMENT': 'EX',
    'DC2S_BIZ_COMPETITIVE_ADVANTAGE': 'EX',
    'DC2S_BIZ_INNOVATION_SCORE': 'EX',
    'DC2S_SCALE_CAPACITY_HEADROOM': 'EX',
    
    # Operational Stability
    'DC2S_SUP_UPTIME_PCT': 'OS',
    'DC2S_SUP_MTBF': 'OS',
    'DC2S_SUP_MTTR': 'OS',
    'DC2S_SUP_SLA_COMPLIANCE': 'OS',
    'DC2S_COST_TOTAL_MONTHLY': 'OS',
    'DC2S_COST_PER_WORKLOAD': 'OS',
    'DC2S_COST_POWER_EFFICIENCY': 'OS',
    'DC2S_COST_COOLING_EFFICIENCY': 'OS',
    'DC2S_COST_OPTIMIZATION_SCORE': 'OS',
    'DC2S_COST_CAPEX_UTILIZATION': 'OS',
    'DC2S_COST_OPEX_RATIO': 'OS',
    'DC2S_PERF_STORAGE_UTIL': 'OS',
    'DC2S_SCALE_STORAGE_GROWTH': 'OS'
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
        kpis_by_pillar = {'AI': [], 'CH': [], 'DV': [], 'EX': [], 'OS': []}
        unmapped_kpis = []
        
        for kpi_code in kpi_codes:
            # Try mapping first (for DC2S_PERF_* format)
            pillar = KPI_TO_PILLAR_MAPPING.get(kpi_code)
            
            # If not found, try extracting from catalog format (AI-KPI1 -> AI)
            if not pillar and '-' in kpi_code:
                prefix = kpi_code.split('-')[0]
                if prefix in ['AI', 'CH', 'DV', 'EX', 'OS']:
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
            'AI': 0.25,
            'CH': 0.20,
            'DV': 0.15,
            'EX': 0.20,
            'OS': 0.20
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
        print(f"  • AI KPIs: {len(kpis_by_pillar['AI'])}")
        print(f"  • CH KPIs: {len(kpis_by_pillar['CH'])}")
        print(f"  • DV KPIs: {len(kpis_by_pillar['DV'])}")
        print(f"  • EX KPIs: {len(kpis_by_pillar['EX'])}")
        print(f"  • OS KPIs: {len(kpis_by_pillar['OS'])}")
        print()
        print("Next steps:")
        print("  1. Test config API: curl http://localhost:5059/api/dc2s/config")
        print("  2. Proceed to Phase 2 (Score Calculator)")
        print()

if __name__ == '__main__':
    initialize_customer9_config()
