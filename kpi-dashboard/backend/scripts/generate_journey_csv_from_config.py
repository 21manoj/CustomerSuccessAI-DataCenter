#!/usr/bin/env python3
"""
Generate Journey CSV files from CustomerConfig
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app
from utils.config_loader import ConfigLoader
import csv
from pathlib import Path

def generate_kpi_foundation_csv(customer_id, output_path):
    """Generate kpi_foundation.csv from customer config"""
    
    with app.app_context():
        loader = ConfigLoader(customer_id)
        kpis = loader.get_all_kpi_definitions()
        output_file = Path(output_path) / 'kpi_foundation.csv'
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'kpi_code', 'pillar', 'name', 'unit', 
                'target', 'operator', 'range_min', 'range_max', 'weight'
            ])
            
            for kpi in sorted(kpis, key=lambda x: x['code']):
                pillar = kpi['pillar']
                kpi_weights = loader.get_kpi_weights(pillar)
                weight = kpi_weights.get(kpi['code'], 0.33)
                
                writer.writerow([
                    kpi['code'],
                    kpi['pillar'],
                    kpi['name'],
                    kpi.get('unit', ''),
                    kpi['target'],
                    kpi['operator'],
                    kpi['range'][0],
                    kpi['range'][1],
                    weight
                ])
        
        print(f"✅ Generated: {output_file}")
        print(f"   KPIs: {len(kpis)}")
        print(f"   Pillars: {sorted(list(set(k['pillar'] for k in kpis)))}")
        return output_file

def generate_pillar_weights_csv(customer_id, output_path):
    """Generate pillar_weights.csv from customer config"""
    
    with app.app_context():
        loader = ConfigLoader(customer_id)
        pillar_weights = loader.get_pillar_weights()
        output_file = Path(output_path) / 'pillar_weights.csv'
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['pillar', 'weight'])
            
            for pillar in sorted(pillar_weights.keys()):
                writer.writerow([pillar, pillar_weights[pillar]])
        
        print(f"✅ Generated: {output_file}")
        print(f"Pillars: {len(pillar_weights)}")
        return output_file

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Journey CSV files')
    parser.add_argument('--customer-id', type=int, required=True)
    parser.add_argument('--output-dir', default='verticals/customer9-dc2_s/journey/wizard_a/config')
    args = parser.parse_args()
    
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("="*70)
    print(f"GENERATING JOURNEY CSV FILES - Customer {args.customer_id}")
    print("="*70)
    print()
    
    try:
        generate_kpi_foundation_csv(args.customer_id, output_path)
        generate_pillar_weights_csv(args.customer_id, output_path)
        
        print()
        print("="*70)
        print("✅ GENERATION COMPLETE")
        print("="*70)
        print()
        print(f"Files created in: {output_path}")
        print("  • kpi_foundation.csv")
        print("  • pillar_weights.csv")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
	main()

