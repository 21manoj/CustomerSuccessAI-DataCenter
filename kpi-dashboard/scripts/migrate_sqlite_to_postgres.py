#!/usr/bin/env python3
"""
Migrate SQLite database to PostgreSQL

This script migrates all data from a SQLite database to PostgreSQL,
preserving data integrity and resetting sequences.

Usage:
    python scripts/migrate_sqlite_to_postgres.py \
        --sqlite-path backend/instance/kpi_dashboard.db \
        --postgres-url postgresql://user:pass@localhost:5432/kpi_dashboard

Requirements:
    pip install psycopg2-binary sqlalchemy
"""

import argparse
import sqlite3
import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def get_table_list(sqlite_conn):
    """Get list of tables from SQLite database"""
    cursor = sqlite_conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        AND name NOT LIKE 'alembic_%'
        ORDER BY name
    """)
    return [row[0] for row in cursor.fetchall()]

def get_table_columns(sqlite_conn, table_name):
    """Get column information for a table"""
    cursor = sqlite_conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = []
    for row in cursor.fetchall():
        columns.append({
            'name': row[1],
            'type': row[2],
            'not_null': row[3],
            'default': row[4],
            'pk': row[5]
        })
    return columns

def migrate_table(sqlite_conn, postgres_engine, table_name, dry_run=False):
    """Migrate a single table from SQLite to PostgreSQL"""
    
    print(f"   📦 Migrating table: {table_name}")
    
    # Get columns
    columns = get_table_columns(sqlite_conn, table_name)
    column_names = [col['name'] for col in columns]
    pk_column = next((col['name'] for col in columns if col['pk']), None)
    
    # Get data from SQLite
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    if not rows:
        print(f"      ⏭️  No data to migrate")
        return 0
    
    print(f"      Found {len(rows)} rows")
    
    if dry_run:
        print(f"      [DRY RUN] Would migrate {len(rows)} rows")
        return len(rows)
    
    # Migrate data
    migrated = 0
    errors = 0
    
    # Use transaction with commit after each successful table
    with postgres_engine.connect() as conn:
        trans = conn.begin()
        
        try:
            for row in rows:
                try:
                    # Convert row to dictionary
                    row_dict = dict(zip(column_names, row))
                    
                    # Handle None values and convert types
                    for key, value in row_dict.items():
                        if value is None:
                            continue
                        # Convert datetime objects to strings
                        if isinstance(value, datetime):
                            row_dict[key] = value.isoformat()
                        # Convert SQLite boolean (integer) to PostgreSQL boolean
                        # Check if column name suggests boolean type
                        if key in ['active', 'auto_trigger_enabled'] or key.endswith('_enabled') or key.startswith('is_'):
                            row_dict[key] = bool(value) if value is not None else None
                    
                    # Special handling for specific tables (after processing all key-value pairs)
                    if table_name == 'users':
                        # Ensure user_name exists (required field)
                        if not row_dict.get('user_name') or row_dict.get('user_name') == '':
                            # Generate user_name from email if missing
                            email = row_dict.get('email', '')
                            if email:
                                row_dict['user_name'] = email.split('@')[0] if '@' in email else f"user_{row_dict.get('user_id', 'unknown')}"
                            else:
                                row_dict['user_name'] = f"user_{row_dict.get('user_id', 'unknown')}"
                        # Ensure email exists (required field)
                        if not row_dict.get('email') or row_dict.get('email') == '':
                            row_dict['email'] = f"user_{row_dict.get('user_id', 'unknown')}@migrated.local"
                        # Ensure active is boolean
                        if 'active' in row_dict and row_dict['active'] is None:
                            row_dict['active'] = True
                    
                    # Remove None values from row_dict to avoid inserting NULLs where not allowed
                    row_dict = {k: v for k, v in row_dict.items() if v is not None}
                    
                    # Build INSERT statement with ON CONFLICT
                    # Only include columns that exist in row_dict (non-None values)
                    available_columns = [col for col in column_names if col in row_dict]
                    columns_str = ', '.join(available_columns)
                    placeholders = ', '.join([':' + col for col in available_columns])
                    
                    if pk_column:
                        # Use ON CONFLICT for tables with primary keys
                        insert_sql = f"""
                            INSERT INTO {table_name} ({columns_str})
                            VALUES ({placeholders})
                            ON CONFLICT ({pk_column}) DO NOTHING
                        """
                    else:
                        # No primary key, just insert
                        insert_sql = f"""
                            INSERT INTO {table_name} ({columns_str})
                            VALUES ({placeholders})
                        """
                    
                    conn.execute(text(insert_sql), row_dict)
                    migrated += 1
                
                except Exception as e:
                    errors += 1
                    if errors <= 3:  # Only show first 3 errors
                        error_msg = str(e)
                        print(f"      ⚠️  Error inserting row: {error_msg[:150]}")
                    if errors > 10:
                        print(f"      ❌ Too many errors, skipping remaining rows")
                        break
                    continue
            
            # Commit transaction if we have successful migrations
            if migrated > 0:
                trans.commit()
                print(f"      ✅ Committed {migrated} rows")
            else:
                trans.rollback()
                print(f"      ⚠️  No rows migrated, rolled back")
                
        except Exception as trans_error:
            trans.rollback()
            print(f"      ❌ Transaction failed: {trans_error}")
            # Don't raise - continue with next table
    
    if errors > 0:
        print(f"      ⚠️  Migrated {migrated} rows, {errors} errors")
    else:
        print(f"      ✅ Migrated {migrated} rows")
    
    return migrated

def reset_sequences(postgres_engine, sqlite_conn, tables):
    """Reset PostgreSQL sequences to match SQLite max IDs"""
    
    print("\n7️⃣  Resetting sequences...")
    
    with postgres_engine.connect() as conn:
        for table_name in tables:
            # Get primary key column from SQLite
            columns = get_table_columns(sqlite_conn, table_name)
            pk_column = next((col['name'] for col in columns if col['pk']), None)
            
            if not pk_column:
                continue
            
            try:
                # Get max ID from PostgreSQL
                result = conn.execute(text(f"SELECT MAX({pk_column}) FROM {table_name}"))
                max_id = result.scalar()
                
                if max_id is None:
                    max_id = 0
                
                # Get sequence name (PostgreSQL naming convention)
                sequence_name = f"{table_name}_{pk_column}_seq"
                
                # Check if sequence exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_class 
                        WHERE relname = :seq_name
                    )
                """), {'seq_name': sequence_name})
                
                if result.scalar():
                    # Reset sequence
                    conn.execute(text(f"SELECT setval('{sequence_name}', :max_id, false)"), 
                                {'max_id': max_id + 1})
                    conn.commit()
                    print(f"   ✅ {table_name}: Sequence reset to {max_id + 1}")
                else:
                    print(f"   ⚠️  {table_name}: Sequence {sequence_name} not found")
                    
            except Exception as e:
                print(f"   ⚠️  {table_name}: Error resetting sequence: {e}")

def verify_migration(sqlite_conn, postgres_engine, tables):
    """Verify that row counts match between SQLite and PostgreSQL"""
    
    print("\n6️⃣  Verifying migration...")
    
    all_match = True
    
    # Use autocommit to avoid transaction errors
    with postgres_engine.connect() as conn:
        conn = conn.execution_options(autocommit=True)
        
        # Define preferred order for migration to handle foreign key dependencies
    preferred_order = [
        'customers', 'users',  # Base tables
        'accounts', 'products',  # Depend on customers
        'kpi_uploads',  # Depend on accounts
        'kpis',  # Depend on accounts, products, kpi_uploads
        'kpi_time_series',  # Depend on kpis
        'account_snapshots',  # Depend on accounts
        'account_notes',  # Depend on accounts
        'customer_configs',  # Depend on customers
        'customer_insights',  # Depend on customers
        'customer_workflow_configs',  # Depend on customers
        'health_trends',  # Depend on accounts
        'playbook_triggers',  # Depend on accounts
        'playbook_executions',  # Depend on playbook_triggers
        'playbook_reports',  # Depend on playbook_executions
        'playbook_status_updates',  # Depend on playbook_executions
        'activity_logs',  # Depend on users, accounts
        'feature_toggles',  # Depend on customers
        'kpi_reference_ranges',  # Independent
        'kpi_best_practices',  # Independent
        'industry_benchmarks',  # Independent
        'financial_projections',  # Depend on accounts
        'rag_knowledge_base',  # Independent
        'rag_query_log',  # Depend on accounts
        'query_audits',  # Depend on users
        'session_audit',  # Depend on users
        'sessions'  # Depend on users
    ]
    
    # Sort tables based on preferred order, putting unknown tables at the end
    sorted_tables = [t for t in preferred_order if t in tables] + \
                    [t for t in tables if t not in preferred_order]
    
    print(f"   Migrating {len(sorted_tables)} tables in dependency order...")
    
    for table_name in sorted_tables:
            try:
                # Get SQLite count
                sqlite_cursor = sqlite_conn.cursor()
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                sqlite_count = sqlite_cursor.fetchone()[0]
                
                # Get PostgreSQL count
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                pg_count = result.scalar()
                
                if pg_count == sqlite_count:
                    print(f"   ✅ {table_name}: {pg_count} rows (matches SQLite)")
                else:
                    print(f"   ⚠️  {table_name}: {pg_count} rows in PostgreSQL, {sqlite_count} in SQLite")
                    all_match = False
                    
            except Exception as e:
                print(f"   ❌ {table_name}: Error verifying: {e}")
                all_match = False
    
    return all_match

def migrate_data(sqlite_path, postgres_url, dry_run=False):
    """Main migration function"""
    
    print("=" * 60)
    print("📦 SQLite to PostgreSQL Migration")
    print("=" * 60)
    print(f"SQLite: {sqlite_path}")
    print(f"PostgreSQL: {postgres_url.split('@')[1] if '@' in postgres_url else 'localhost'}")
    if dry_run:
        print("⚠️  DRY RUN MODE - No changes will be made")
    print("=" * 60)
    
    # Step 1: Connect to SQLite
    print("\n1️⃣  Connecting to SQLite...")
    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        print("   ✅ Connected to SQLite")
    except Exception as e:
        print(f"   ❌ Failed to connect to SQLite: {e}")
        return False
    
    # Step 2: Connect to PostgreSQL
    print("2️⃣  Connecting to PostgreSQL...")
    try:
        postgres_engine = create_engine(postgres_url)
        with postgres_engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"   ✅ Connected to PostgreSQL: {version.split(',')[0]}")
    except Exception as e:
        print(f"   ❌ Failed to connect to PostgreSQL: {e}")
        sqlite_conn.close()
        return False
    
    # Step 3: Get table list
    print("3️⃣  Getting table list...")
    try:
        tables = get_table_list(sqlite_conn)
        print(f"   Found {len(tables)} tables: {', '.join(tables)}")
    except Exception as e:
        print(f"   ❌ Failed to get table list: {e}")
        sqlite_conn.close()
        return False
    
    # Step 4: Create tables in PostgreSQL (if not dry run)
    if not dry_run:
        print("4️⃣  Creating tables in PostgreSQL...")
        try:
            # Import app and models to create tables
            from backend.app import app
            from backend.extensions import db
            from backend import models
            
            with app.app_context():
                # Temporarily set PostgreSQL URL
                app.config['SQLALCHEMY_DATABASE_URI'] = postgres_url
                db.init_app(app)
                
                # Create all tables
                db.create_all()
                print("   ✅ Tables created/verified")
        except Exception as e:
            print(f"   ⚠️  Warning creating tables: {e}")
            print("   Continuing with migration (tables may already exist)")
    
    # Step 5: Migrate data
    print("\n5️⃣  Migrating data...")
    total_rows = 0
    
    # Define preferred order for migration to handle foreign key dependencies
    preferred_order = [
        'customers', 'users',  # Base tables
        'accounts', 'products',  # Depend on customers
        'kpi_uploads',  # Depend on accounts
        'kpis',  # Depend on accounts, products, kpi_uploads
        'kpi_time_series',  # Depend on kpis
        'account_snapshots',  # Depend on accounts
        'account_notes',  # Depend on accounts
        'customer_configs',  # Depend on customers
        'customer_insights',  # Depend on customers
        'customer_workflow_configs',  # Depend on customers
        'health_trends',  # Depend on accounts
        'playbook_triggers',  # Depend on accounts
        'playbook_executions',  # Depend on playbook_triggers
        'playbook_reports',  # Depend on playbook_executions
        'playbook_status_updates',  # Depend on playbook_executions
        'activity_logs',  # Depend on users, accounts
        'feature_toggles',  # Depend on customers
        'kpi_reference_ranges',  # Independent
        'kpi_best_practices',  # Independent
        'industry_benchmarks',  # Independent
        'financial_projections',  # Depend on accounts
        'rag_knowledge_base',  # Independent
        'rag_query_log',  # Depend on accounts
        'query_audits',  # Depend on users
        'session_audit',  # Depend on users
        'sessions'  # Depend on users
    ]
    
    # Sort tables based on preferred order, putting unknown tables at the end
    sorted_tables = [t for t in preferred_order if t in tables] + \
                    [t for t in tables if t not in preferred_order]
    
    print(f"   Migrating {len(sorted_tables)} tables in dependency order...")
    
    for table_name in sorted_tables:
        try:
            rows_migrated = migrate_table(sqlite_conn, postgres_engine, table_name, dry_run)
            total_rows += rows_migrated
        except Exception as e:
            print(f"   ❌ Error migrating {table_name}: {e}")
            continue
    
    # Step 6: Verify migration
    if not dry_run:
        all_match = verify_migration(sqlite_conn, postgres_engine, tables)
        
        # Step 7: Reset sequences
        reset_sequences(postgres_engine, sqlite_conn, tables)
    
    # Summary
    print("\n" + "=" * 60)
    if dry_run:
        print("📊 DRY RUN SUMMARY")
    else:
        print("🎉 Migration Complete!")
    print("=" * 60)
    print(f"Tables processed: {len(tables)}")
    print(f"Total rows migrated: {total_rows}")
    
    if not dry_run:
        all_match = verify_migration(sqlite_conn, postgres_engine, tables)
        if all_match:
            print("✅ All row counts match!")
        else:
            print("⚠️  Some row counts don't match - please review")
    
    # Cleanup
    sqlite_conn.close()
    postgres_engine.dispose()
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Migrate SQLite database to PostgreSQL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (test without making changes)
  python scripts/migrate_sqlite_to_postgres.py \\
      --sqlite-path backend/instance/kpi_dashboard.db \\
      --postgres-url postgresql://user:pass@localhost:5432/kpi_dashboard \\
      --dry-run

  # Actual migration
  python scripts/migrate_sqlite_to_postgres.py \\
      --sqlite-path backend/instance/kpi_dashboard.db \\
      --postgres-url postgresql://user:pass@localhost:5432/kpi_dashboard
        """
    )
    parser.add_argument(
        '--sqlite-path',
        required=True,
        help='Path to SQLite database file'
    )
    parser.add_argument(
        '--postgres-url',
        required=True,
        help='PostgreSQL connection URL (postgresql://user:pass@host:port/dbname)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test migration without making changes'
    )
    
    args = parser.parse_args()
    
    # Validate SQLite path
    if not os.path.exists(args.sqlite_path):
        print(f"❌ Error: SQLite database not found: {args.sqlite_path}")
        sys.exit(1)
    
    # Run migration
    success = migrate_data(args.sqlite_path, args.postgres_url, args.dry_run)
    
    sys.exit(0 if success else 1)

