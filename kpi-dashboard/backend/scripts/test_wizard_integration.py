#!/usr/bin/env python3
"""
Test Wizard integration with CustomerConfig
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from models import db, CustomerConfig
from utils.config_loader import ConfigLoader

def test_config_loader():
    with app.app_context():
        print("="*70)
        print("TESTING CONFIG LOADER - CUSTOMER 9")
        print("="*70)
        print()
        
        # Test config loading
        loader = ConfigLoader(customer_id=9)
        
        print("1. Enabled KPIs:")
        enabled_kpis = loader.get_enabled_kpis()
        print(f"   Total: {len(enabled_kpis)}")
        for kpi_code in enabled_kpis[:5]:
            print(f"   - {kpi_code}")
        if len(enabled_kpis) > 5:
            print(f"   ... and {len(enabled_kpis) - 5} more")
        print()
        
        print("2. Pillar Weights:")
        pillar_weights = loader.get_pillar_weights()
        for pillar, weight in pillar_weights.items():
            print(f"   {pillar}: {weight*100:.1f}%")
        print()
        
        print("3. KPIs by Pillar:")
        kpis_by_pillar = loader.get_kpis_by_pillar()
        for pillar, kpis in kpis_by_pillar.items():
            if kpis:
                print(f"   {pillar}: {len(kpis)} KPIs")
                for kpi_code in kpis[:3]:
                    print(f"      - {kpi_code}")
                if len(kpis) > 3:
                    print(f"      ... and {len(kpis) - 3} more")
        print()
        
        print("4. Sample KPI Definition:")
        if enabled_kpis:
            sample_kpi = loader.get_kpi_definition(enabled_kpis[0])
            if sample_kpi:
                print(f"   Code: {enabled_kpis[0]}")
                print(f"   Name: {sample_kpi.get('name', 'N/A')}")
                print(f"   Pillar: {sample_kpi.get('pillar', 'N/A')}")
                print(f"   Target: {sample_kpi.get('target', 'N/A')} {sample_kpi.get('unit', '')}")
        print()
        
        print("5. All KPI Definitions:")
        all_definitions = loader.get_all_kpi_definitions()
        print(f"   Total definitions: {len(all_definitions)}")
        print(f"   Sample (first 3):")
        for kpi_def in all_definitions[:3]:
            print(f"      - {kpi_def.get('code')}: {kpi_def.get('name')} ({kpi_def.get('pillar')})")
        print()
        
        print("="*70)
        print("✅ CONFIG LOADER TEST COMPLETE")
        print("="*70)

if __name__ == '__main__':
    test_config_loader()
