#!/usr/bin/env python3
"""
Load Bootstrap Weights to Database
===================================

Loads Supermicro simulation weights from bootstrap_weights_config.json
into the bootstrap_weights and kpi_mapping tables.

Usage:
    python3 load_bootstrap_weights.py --db-url "$DATABASE_URL"
"""

import json
import os
import sys
import argparse
from sqlalchemy import create_engine, text
from datetime import datetime


def load_bootstrap_weights(db_url, config_path):
    """Load bootstrap weights from JSON to database"""
    
    print("="*70)
    print("LOADING BOOTSTRAP WEIGHTS")
    print("="*70)
    print()
    
    # Load JSON config
    print(f"📖 Loading config from: {config_path}")
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"   ✅ Config loaded")
    print(f"   Version: {config.get('config_version', 'unknown')}")
    print(f"   Source: {config.get('source', 'unknown')}")
    print()
    
    # Connect to database
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Clear existing weights
        print("🗑️  Clearing existing bootstrap weights...")
        conn.execute(text("DELETE FROM bootstrap_weights"))
        conn.execute(text("DELETE FROM kpi_mapping"))
        conn.commit()
        print("   ✅ Existing data cleared")
        print()
        
        # Prepare SQL
        weight_sql = text("""
            INSERT INTO bootstrap_weights (
                pillar_code, pillar_name, kpi_code, kpi_name,
                l2_weight, l1_weight, effective_weight, rank_by_importance,
                source, confidence_level
            ) VALUES (
                :pillar_code, :pillar_name, :kpi_code, :kpi_name,
                :l2_weight, :l1_weight, :effective_weight, :rank,
                :source, :confidence
            )
        """)
        
        # Get L2 (pillar) weights
        l2_weights = config['pillar_weights_L2']
        l1_weights = config['kpi_weights_L1']
        
        # Calculate and insert all weights
        print("💾 Inserting bootstrap weights...")
        
        all_weights = []
        for pillar_code, kpis in l1_weights.items():
            pillar_weight = l2_weights[pillar_code]
            pillar_name = pillar_code.replace('_', ' ').title()
            
            for kpi_code, l1_weight in kpis.items():
                effective_weight = pillar_weight * l1_weight
                
                all_weights.append({
                    'pillar_code': pillar_code,
                    'pillar_name': pillar_name,
                    'kpi_code': kpi_code,
                    'kpi_name': kpi_code.replace('_', ' ').title(),
                    'l2_weight': pillar_weight,
                    'l1_weight': l1_weight,
                    'effective_weight': effective_weight,
                    'rank': 0,  # Will update after
                    'source': config.get('source', 'Supermicro_simulation'),
                    'confidence': config.get('confidence_level', 'high')
                })
        
        # Sort by effective weight to assign ranks
        all_weights.sort(key=lambda x: x['effective_weight'], reverse=True)
        for rank, weight in enumerate(all_weights, 1):
            weight['rank'] = rank
        
        # Insert all weights
        for weight in all_weights:
            conn.execute(weight_sql, weight)
        
        conn.commit()
        print(f"   ✅ Inserted {len(all_weights)} bootstrap weights")
        print()
        
        # Show top 10
        print("🏆 Top 10 Most Important KPIs:")
        result = conn.execute(text("""
            SELECT rank_by_importance, kpi_code, effective_weight
            FROM bootstrap_weights
            ORDER BY effective_weight DESC
            LIMIT 10
        """))
        
        for row in result:
            rank, kpi, weight = row
            print(f"   {rank:2d}. {kpi:35s} {weight*100:5.2f}%")
        print()
        
        # Load KPI mapping
        print("🔗 Loading KPI mapping...")
        mapping_path = os.path.join(os.path.dirname(config_path),'kpi_mapping_config.json')
        
        if os.path.exists(mapping_path):
            with open(mapping_path, 'r') as f:
                mapping_config = json.load(f)
            
            mapping_sql = text("""
                INSERT INTO kpi_mapping (
                    bootstrap_kpi_code, bootstrap_kpi_name,
                    journey_kpi_code, journey_kpi_name,
                    mapping_weight, mapping_type, confidence
                ) VALUES (
                    :bootstrap_kpi, :bootstrap_name,
                    :journey_kpi, :journey_name,
                    :weight, :mapping_type, :confidence
                )
            """)
            
            # KPI names mapping
            kpi_names = {
                'P1': 'Workload Running', 'P2': 'GPU Utilization', 'P3': 'Active Users',
                'P4': 'Training Jobs Completed', 'P5': 'Inference Requests', 'P6': 'Model Accuracy',
                'P7': 'Data Processing Throughput', 'P8': 'API Response Time',
                'C1': 'Cost per Training Job', 'C2': 'Cost per 1M Inferences', 'C3': 'Idle GPU Time',
                'C4': 'Storage Cost Efficiency', 'C5': 'Compute ROI', 'C6': 'Budget Utilization',
                'C7': 'Cost Predictability',
                'S1': 'Capacity Utilization', 'S2': 'Workload Growth Rate', 'S3': 'New Use Cases Deployed',
                'S4': 'Time to Scale', 'S5': 'Resource Elasticity', 'S6': 'Peak Load Handling',
                'S7': 'Expansion Readiness',
                'R1': 'System Uptime', 'R2': 'Support Ticket Volume', 'R3': 'Mean Time to Resolution',
                'R4': 'Critical Incidents', 'R5': 'Support Satisfaction', 'R6': 'Documentation Usage',
                'B1': 'Business Value Score', 'B2': 'User Satisfaction (NPS)', 'B3': 'Feature Adoption',
                'B4': 'Time to Value', 'B5': 'Strategic Alignment', 'B6': 'Executive Engagement',
                'B7': 'Competitive Position'
            }
            
            mapping_count = 0
            for pillar, kpis in mapping_config['kpi_mappings'].items():
                for bootstrap_kpi, mapping_info in kpis.items():
                    journey_kpis = mapping_info['journey_kpis']
                    weights = mapping_info['weights']
                    mapping_type = mapping_info['mapping_type']
                    confidence = mapping_info['confidence']
                    
                    for journey_kpi, weight in zip(journey_kpis, weights):
                        conn.execute(mapping_sql, {
                            'bootstrap_kpi': bootstrap_kpi,
                            'bootstrap_name': bootstrap_kpi.replace('_', ' ').title(),
                            'journey_kpi': journey_kpi,
                            'journey_name': kpi_names.get(journey_kpi, journey_kpi),
                            'weight': weight,
                            'mapping_type': mapping_type,
                            'confidence': confidence
                        })
                        mapping_count += 1
            
            conn.commit()
            print(f"   ✅ Loaded {mapping_count} KPI mappings")
        else:
            print(f"   ⚠️  Mapping file not found: {mapping_path}")
            print(f"   Skipping KPI mapping load")
        
        print()
        
        # Summary
        print("="*70)
        print("✅ BOOTSTRAP WEIGHTS LOADED SUCCESSFULLY!")
        print("="*70)
        print()
        
        # Stats
        stats = conn.execute(text("""
            SELECT 
                COUNT(*) as total_weights,
                COUNT(DISTINCT pillar_code) as pillars,
                MIN(effective_weight) as min_weight,
                MAX(effective_weight) as max_weight,
                AVG(effective_weight) as avg_weight
            FROM bootstrap_weights
        """)).fetchone()
        
        print("📊 Statistics:")
        print(f"   Total KPIs: {stats[0]}")
        print(f"   Pillars: {stats[1]}")
        print(f"   Weight range: {stats[2]*100:.2f}% - {stats[3]*100:.2f}%")
        print(f"   Average weight: {stats[4]*100:.2f}%")
        print()
        
        # Pillar breakdown
        print("📊 Weights by Pillar:")
        pillar_stats = conn.execute(text("""
            SELECT 
                pillar_code,
                CAST(l2_weight * 100 AS NUMERIC(5,2)) as pillar_weight,
                COUNT(*) as kpi_count
            FROM bootstrap_weights
            GROUP BY pillar_code, l2_weight
            ORDER BY l2_weight DESC
        """))
        
        for row in pillar_stats:
            print(f"   {row[0]:35s} {row[1]:5.1f}% ({row[2]} KPIs)")
        print()
        
        print("Next step: Test Signal Analyst")
        print("  python3 scripts/phase5/test_signal_analyst.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Load bootstrap weights to database')
    parser.add_argument('--db-url', 
                       default=os.environ.get('DATABASE_URL'),
                       help='PostgreSQL connection URL')
    parser.add_argument('--config',
                       default='data/bootstrap/bootstrap_weights_config.json',
                       help='Path to bootstrap weights JSON file')
    
    args = parser.parse_args()
    
    if not args.db_url:
        print("❌ ERROR: Database URL not provided")
        print()
        print("Usage:")
        print("  export DATABASE_URL='postgresql://user:pass@host:5432/database'")
        print("  python3 load_bootstrap_weights.py")
        print()
        print("Or:")
        print("  python3 load_bootstrap_weights.py --db-url 'postgresql://...'")
        sys.exit(1)
    
    if not os.path.exists(args.config):
        print(f"❌ ERROR: Config file not found: {args.config}")
        sys.exit(1)
    
    try:
        load_bootstrap_weights(args.db_url, args.config)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
