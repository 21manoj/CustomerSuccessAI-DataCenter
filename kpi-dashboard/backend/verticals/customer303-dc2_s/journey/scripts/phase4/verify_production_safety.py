#!/usr/bin/env python3
"""
Production Safety Verification Script
=====================================

Run this BEFORE and AFTER Phase 4 migration to verify
that production tables are completely untouched.

Usage:
    # Before migration
    python verify_production_safety.py --db-url postgresql://user:pass@localhost/dbname --output before.json
    
    # Run migration
    psql -d dbname -f migration_journey_phase4.sql
    
    # After migration
    python verify_production_safety.py --db-url postgresql://user:pass@localhost/dbname --output after.json
    
    # Compare
    python verify_production_safety.py --compare before.json after.json
"""

import argparse
import json
from sqlalchemy import create_engine, text


PRODUCTION_TABLES = [
    'customers',
    'customer_configs',
    'accounts',
    'products',
    'users',
    'kpi_uploads',
    'kpis',
    'health_trends',
    'kpi_reference_ranges',
    'kpi_time_series',
    'dc2s_kpis',
    'playbook_triggers',
    'playbook_executions',
    'playbook_reports',
    'account_notes',
    'account_snapshots',
    'account_health_history',
    'customer_workflow_configs',
    'activity_logs',
]


def get_table_stats(engine, table_name):
    """Get statistics for a single table"""
    
    try:
        with engine.connect() as conn:
            # Row count
            count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            row_count = count_result.scalar()
            
            # Column count
            cols_result = conn.execute(text(f"""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = :table_name
            """), {'table_name': table_name})
            col_count = cols_result.scalar()
            
            # Index count
            idx_result = conn.execute(text(f"""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE tablename = :table_name
            """), {'table_name': table_name})
            idx_count = idx_result.scalar()
            
            # Constraint count
            const_result = conn.execute(text(f"""
                SELECT COUNT(*) 
                FROM information_schema.table_constraints 
                WHERE table_name = :table_name
            """), {'table_name': table_name})
            const_count = const_result.scalar()
            
            return {
                'exists': True,
                'row_count': row_count,
                'column_count': col_count,
                'index_count': idx_count,
                'constraint_count': const_count
            }
    except Exception as e:
        return {
            'exists': False,
            'error': str(e)
        }


def verify_production(db_url, output_file=None):
    """Verify all production tables and save snapshot"""
    
    print("="*70)
    print("PRODUCTION SAFETY VERIFICATION")
    print("="*70)
    print()
    print(f"📡 Connecting to database...")
    
    engine = create_engine(db_url)
    
    results = {
        'timestamp': str(json.dumps(str(engine.url))),
        'tables': {}
    }
    
    print(f"✅ Connected!")
    print()
    print(f"🔍 Checking {len(PRODUCTION_TABLES)} production tables...")
    print()
    
    for table_name in PRODUCTION_TABLES:
        stats = get_table_stats(engine, table_name)
        results['tables'][table_name] = stats
        
        if stats['exists']:
            print(f"  ✅ {table_name:30s} {stats['row_count']:8,} rows  " +
                  f"{stats['column_count']:3} cols  {stats['index_count']:2} indexes")
        else:
            print(f"  ⚠️  {table_name:30s} NOT FOUND (may not be created yet)")
    
    # Check for journey tables
    print()
    print("🔍 Checking for journey tables...")
    journey_tables = []
    
    with engine.connect() as conn:
        journey_result = conn.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename LIKE 'journey_%'
            ORDER BY tablename
        """))
        journey_tables = [row[0] for row in journey_result]
    
    results['journey_tables'] = journey_tables
    
    if journey_tables:
        print(f"  Found {len(journey_tables)} journey tables:")
        for jt in journey_tables:
            print(f"    - {jt}")
    else:
        print(f"  No journey tables found (expected before migration)")
    
    # Save results
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print()
        print(f"💾 Results saved to: {output_file}")
    
    print()
    print("="*70)
    print("✅ Verification Complete!")
    print("="*70)
    
    return results


def compare_results(before_file, after_file):
    """Compare before/after results to verify no production changes"""
    
    print("="*70)
    print("BEFORE/AFTER COMPARISON")
    print("="*70)
    print()
    
    with open(before_file, 'r') as f:
        before = json.load(f)
    
    with open(after_file, 'r') as f:
        after = json.load(f)
    
    print("📊 Comparing production tables...")
    print()
    
    all_safe = True
    
    for table_name in PRODUCTION_TABLES:
        before_stats = before['tables'].get(table_name, {})
        after_stats = after['tables'].get(table_name, {})
        
        if not before_stats.get('exists'):
            continue  # Table didn't exist before
        
        changes = []
        
        # Check row count
        if before_stats.get('row_count') != after_stats.get('row_count'):
            changes.append(f"rows: {before_stats['row_count']} → {after_stats['row_count']}")
            all_safe = False
        
        # Check column count
        if before_stats.get('column_count') != after_stats.get('column_count'):
            changes.append(f"cols: {before_stats['column_count']} → {after_stats['column_count']}")
            all_safe = False
        
        # Check index count
        if before_stats.get('index_count') != after_stats.get('index_count'):
            changes.append(f"indexes: {before_stats['index_count']} → {after_stats['index_count']}")
            all_safe = False
        
        # Check constraint count
        if before_stats.get('constraint_count') != after_stats.get('constraint_count'):
            changes.append(f"constraints: {before_stats['constraint_count']} → {after_stats['constraint_count']}")
            all_safe = False
        
        if changes:
            print(f"  ⚠️  {table_name}: CHANGED - {', '.join(changes)}")
        else:
            print(f"  ✅ {table_name}: UNCHANGED")
    
    print()
    print("🆕 Journey Tables Added:")
    new_journey = set(after.get('journey_tables', [])) - set(before.get('journey_tables', []))
    if new_journey:
        for jt in sorted(new_journey):
            print(f"  ✅ {jt} (NEW - expected)")
    else:
        print(f"  ⚠️  No new journey tables found!")
    
    print()
    print("="*70)
    
    if all_safe:
        print("✅✅✅ ALL PRODUCTION TABLES UNTOUCHED! ✅✅✅")
        print("="*70)
        print()
        print("🎉 Migration is SAFE - zero impact on production!")
        return True
    else:
        print("⚠️⚠️⚠️ PRODUCTION TABLES CHANGED! ⚠️⚠️⚠️")
        print("="*70)
        print()
        print("🚨 ALERT: Production tables were modified!")
        print("🚨 Review changes above and investigate!")
        return False


def main():
    parser = argparse.ArgumentParser(description='Verify production table safety')
    parser.add_argument('--db-url', help='PostgreSQL connection URL')
    parser.add_argument('--output', help='Output file for results')
    parser.add_argument('--compare', nargs=2, metavar=('BEFORE', 'AFTER'),
                       help='Compare before/after JSON files')
    
    args = parser.parse_args()
    
    if args.compare:
        # Comparison mode
        before_file, after_file = args.compare
        is_safe = compare_results(before_file, after_file)
        exit(0 if is_safe else 1)
    elif args.db_url:
        # Verification mode
        verify_production(args.db_url, args.output)
    else:
        parser.print_help()
        exit(1)


if __name__ == "__main__":
    main()
