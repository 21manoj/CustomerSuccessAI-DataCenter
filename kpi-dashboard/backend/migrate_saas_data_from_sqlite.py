#!/usr/bin/env python3
"""
Migrate SaaS data from old PostgreSQL database to new PostgreSQL instance
Transfers all data for customer_id=1 (Test Company) from old kpi-dashboard PostgreSQL to new PostgreSQL instance
"""

import sys
import os
from dotenv import load_dotenv
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import sql
from urllib.parse import urlparse
import json

# Load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path=env_path)

# Old PostgreSQL database URL
OLD_PG_URL = 'postgresql://kpi_user@localhost:5432/kpi_dashboard'

# New PostgreSQL connection
PG_URL = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')
if not PG_URL:
    print("❌ Error: DATABASE_URL not found in .env")
    sys.exit(1)

def parse_pg_url(url):
    """Parse PostgreSQL URL into connection parameters"""
    # Format: postgresql://user:pass@host:port/dbname or postgresql://user@host:port/dbname
    url = url.replace('postgresql://', '')
    if '@' in url:
        auth, rest = url.split('@', 1)
        if ':' in auth:
            user, password = auth.split(':', 1)
        else:
            user = auth
            password = None
    else:
        user, password = None, None
        rest = url
    
    if '/' in rest:
        host_port, dbname = rest.split('/', 1)
        if ':' in host_port:
            host, port = host_port.split(':')
        else:
            host = host_port
            port = 5432
    else:
        host = rest
        port = 5432
        dbname = None
    
    params = {
        'host': host,
        'port': int(port),
        'database': dbname,
        'user': user
    }
    if password:
        params['password'] = password
    
    return params

def migrate_kpis_by_accounts_with_mapping(old_pg_conn, new_pg_conn, account_ids, account_id_map):
    """Migrate KPIs filtered by account IDs with account_id remapping"""
    table_name = 'kpis'
    print(f"\n📦 Migrating table: {table_name} (by account_ids with remapping)")
    
    old_cursor = old_pg_conn.cursor()
    old_cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    columns = old_cursor.fetchall()
    
    if not columns:
        print(f"   ⚠️  Table {table_name} not found in old PostgreSQL")
        return 0
    
    col_names = [col[0] for col in columns]
    col_names_str = ', '.join(col_names)
    
    # Filter by account_ids
    placeholders = ','.join(['%s'] * len(account_ids))
    query = f"SELECT {col_names_str} FROM {table_name} WHERE account_id IN ({placeholders})"
    old_cursor.execute(query, account_ids)
    rows = old_cursor.fetchall()
    
    if not rows:
        print(f"   ⚠️  No KPIs found for {len(account_ids)} account(s)")
        return 0
    
    print(f"   Found {len(rows)} KPIs")
    
    # Insert into new PostgreSQL (same logic as migrate_table)
    new_cursor = new_pg_conn.cursor()
    new_cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        );
    """, (table_name,))
    
    if not new_cursor.fetchone()[0]:
        print(f"   ⚠️  Table {table_name} does not exist in new PostgreSQL. Skipping.")
        return 0
    
    new_cursor.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    new_pg_columns = [row[0] for row in new_cursor.fetchall()]
    
    col_mapping = {}
    for old_col in col_names:
        new_col = next((pgc for pgc in new_pg_columns if pgc.lower() == old_col.lower()), None)
        if new_col:
            col_mapping[old_col] = new_col
    
    if not col_mapping:
        print(f"   ⚠️  No matching columns found. Skipping.")
        return 0
    
    new_cursor.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s
    """, (table_name,))
    new_pg_column_types = {row[0]: row[1] for row in new_cursor.fetchall()}
    
    mapped_cols = [col_mapping[col] for col in col_names if col in col_mapping]
    
    # Find account_id column index
    account_id_col_idx = None
    for i, col_name in enumerate(col_names):
        if col_name.lower() == 'account_id':
            account_id_col_idx = i
            break
    
    prepared_rows = []
    for row in rows:
        prepared_row = []
        for i, col_name in enumerate(col_names):
            if col_name not in col_mapping:
                continue
            value = row[i]
            
            # Remap account_id if this is the account_id column
            if i == account_id_col_idx and value is not None and value in account_id_map:
                value = account_id_map[value]
            
            new_pg_col_name = col_mapping[col_name]
            new_pg_type = new_pg_column_types.get(new_pg_col_name, '')
            
            if value is None:
                prepared_row.append(None)
            elif new_pg_type == 'boolean':
                if isinstance(value, bool):
                    prepared_row.append(value)
                elif isinstance(value, int):
                    prepared_row.append(bool(value))
                elif isinstance(value, str):
                    prepared_row.append(value.lower() in ('true', '1', 'yes', 't'))
                else:
                    prepared_row.append(bool(value))
            elif isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                try:
                    json.loads(value)
                    prepared_row.append(value)
                except:
                    prepared_row.append(value)
            elif isinstance(value, datetime):
                prepared_row.append(value.isoformat())
            elif isinstance(value, bytes):
                prepared_row.append(value)
            else:
                prepared_row.append(value)
        
        prepared_rows.append(tuple(prepared_row))
    
    if not prepared_rows:
        return 0
    
    insert_query = f"""
        INSERT INTO {table_name} ({', '.join(mapped_cols)})
        VALUES %s
        ON CONFLICT DO NOTHING
    """
    
    try:
        execute_values(new_cursor, insert_query, prepared_rows)
        new_pg_conn.commit()
        print(f"   ✅ Inserted {len(prepared_rows)} rows")
        return len(prepared_rows)
    except Exception as e:
        new_pg_conn.rollback()
        print(f"   ❌ Error inserting data: {e}")
        import traceback
        traceback.print_exc()
        return 0

def migrate_table_with_account_mapping(old_pg_conn, new_pg_conn, table_name, customer_id, account_id_map, skip_columns=None):
    """Migrate table with account_id remapping"""
    skip_columns = skip_columns or []
    
    print(f"\n📦 Migrating table: {table_name} (with account_id remapping)")
    
    old_cursor = old_pg_conn.cursor()
    old_cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    columns = old_cursor.fetchall()
    
    if not columns:
        print(f"   ⚠️  Table {table_name} not found in old PostgreSQL")
        return 0
    
    col_names = [col[0] for col in columns if col[0] not in skip_columns]
    col_names_str = ', '.join(col_names)
    
    where_clause = f"WHERE customer_id = {customer_id}"
    query = f"SELECT {col_names_str} FROM {table_name} {where_clause}"
    old_cursor.execute(query)
    rows = old_cursor.fetchall()
    
    if not rows:
        print(f"   ⚠️  No data found for customer_id={customer_id}")
        return 0
    
    print(f"   Found {len(rows)} rows")
    
    new_cursor = new_pg_conn.cursor()
    new_cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        );
    """, (table_name,))
    
    if not new_cursor.fetchone()[0]:
        print(f"   ⚠️  Table {table_name} does not exist in new PostgreSQL. Skipping.")
        return 0
    
    new_cursor.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    new_pg_columns = [row[0] for row in new_cursor.fetchall()]
    
    col_mapping = {}
    for old_col in col_names:
        new_col = next((pgc for pgc in new_pg_columns if pgc.lower() == old_col.lower()), None)
        if new_col:
            col_mapping[old_col] = new_col
    
    if not col_mapping:
        print(f"   ⚠️  No matching columns found. Skipping.")
        return 0
    
    new_cursor.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s
    """, (table_name,))
    new_pg_column_types = {row[0]: row[1] for row in new_cursor.fetchall()}
    
    mapped_cols = [col_mapping[col] for col in col_names if col in col_mapping]
    
    # Find account_id column index
    account_id_col_idx = None
    for i, col_name in enumerate(col_names):
        if col_name.lower() == 'account_id':
            account_id_col_idx = i
            break
    
    prepared_rows = []
    for row in rows:
        prepared_row = []
        for i, col_name in enumerate(col_names):
            if col_name not in col_mapping:
                continue
            value = row[i]
            
            # Remap account_id if this is the account_id column
            if i == account_id_col_idx and value is not None and value in account_id_map:
                value = account_id_map[value]
            
            new_pg_col_name = col_mapping[col_name]
            new_pg_type = new_pg_column_types.get(new_pg_col_name, '')
            
            if value is None:
                prepared_row.append(None)
            elif new_pg_type == 'boolean':
                if isinstance(value, bool):
                    prepared_row.append(value)
                elif isinstance(value, int):
                    prepared_row.append(bool(value))
                elif isinstance(value, str):
                    prepared_row.append(value.lower() in ('true', '1', 'yes', 't'))
                else:
                    prepared_row.append(bool(value))
            elif isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                try:
                    json.loads(value)
                    prepared_row.append(value)
                except:
                    prepared_row.append(value)
            elif isinstance(value, datetime):
                prepared_row.append(value.isoformat())
            elif isinstance(value, bytes):
                prepared_row.append(value)
            else:
                prepared_row.append(value)
        
        prepared_rows.append(tuple(prepared_row))
    
    if not prepared_rows:
        return 0
    
    insert_query = f"""
        INSERT INTO {table_name} ({', '.join(mapped_cols)})
        VALUES %s
        ON CONFLICT DO NOTHING
    """
    
    try:
        execute_values(new_cursor, insert_query, prepared_rows)
        new_pg_conn.commit()
        print(f"   ✅ Inserted {len(prepared_rows)} rows")
        return len(prepared_rows)
    except Exception as e:
        new_pg_conn.rollback()
        print(f"   ❌ Error inserting data: {e}")
        import traceback
        traceback.print_exc()
        return 0

def migrate_table_from_pg(old_pg_conn, new_pg_conn, table_name, customer_id=1, skip_columns=None):
    """Migrate a table from SQLite to PostgreSQL"""
    skip_columns = skip_columns or []
    
    print(f"\n📦 Migrating table: {table_name}")
    
    # Get table schema from old PostgreSQL
    old_cursor = old_pg_conn.cursor()
    old_cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    columns = old_cursor.fetchall()
    
    if not columns:
        print(f"   ⚠️  Table {table_name} not found in old PostgreSQL")
        return 0
    
    # Build column list (skip specified columns)
    col_names = [col[0] for col in columns if col[0] not in skip_columns]
    col_names_str = ', '.join(col_names)
    
    # Filter by customer_id if table has customer_id column
    where_clause = ""
    if 'customer_id' in col_names:
        where_clause = f"WHERE customer_id = {customer_id}"
        print(f"   Filtering by customer_id = {customer_id}")
    
    # Get data from old PostgreSQL
    query = f"SELECT {col_names_str} FROM {table_name} {where_clause}"
    old_cursor.execute(query)
    rows = old_cursor.fetchall()
    
    if not rows:
        print(f"   ⚠️  No data found for customer_id={customer_id}")
        return 0
    
    print(f"   Found {len(rows)} rows")
    
    # Insert into new PostgreSQL
    new_cursor = new_pg_conn.cursor()
    
    # Check if table exists in new PostgreSQL
    new_cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = %s
        );
    """, (table_name,))
    
    if not new_cursor.fetchone()[0]:
        print(f"   ⚠️  Table {table_name} does not exist in new PostgreSQL. Skipping.")
        return 0
    
    # Get new PostgreSQL column names (to handle case differences)
    new_cursor.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    new_pg_columns = [row[0] for row in new_cursor.fetchall()]
    
    # Map old PostgreSQL columns to new PostgreSQL columns (case-insensitive)
    col_mapping = {}
    for old_col in col_names:
        # Find matching new PostgreSQL column (case-insensitive)
        new_col = next((pgc for pgc in new_pg_columns if pgc.lower() == old_col.lower()), None)
        if new_col:
            col_mapping[old_col] = new_col
        else:
            print(f"   ⚠️  Column {old_col} not found in new PostgreSQL table")
    
    if not col_mapping:
        print(f"   ⚠️  No matching columns found. Skipping.")
        return 0
    
    # Use mapped column names
    mapped_cols = [col_mapping[col] for col in col_names if col in col_mapping]
    
    # Get new PostgreSQL column types for type conversion
    new_cursor.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s
    """, (table_name,))
    new_pg_column_types = {row[0]: row[1] for row in new_cursor.fetchall()}
    
    # Prepare data (handle JSON fields, dates, type conversions, etc.)
    prepared_rows = []
    for row in rows:
        prepared_row = []
        for i, col_name in enumerate(col_names):
            if col_name not in col_mapping:
                continue
            value = row[i]
            new_pg_col_name = col_mapping[col_name]
            new_pg_type = new_pg_column_types.get(new_pg_col_name, '')
            
            # Handle None
            if value is None:
                prepared_row.append(None)
            # Handle boolean conversion (SQLite stores as integer 0/1)
            elif new_pg_type == 'boolean':
                if isinstance(value, bool):
                    prepared_row.append(value)
                elif isinstance(value, int):
                    prepared_row.append(bool(value))
                elif isinstance(value, str):
                    prepared_row.append(value.lower() in ('true', '1', 'yes', 't'))
                else:
                    prepared_row.append(bool(value))
            # Handle JSON fields
            elif isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                try:
                    json.loads(value)  # Validate JSON
                    prepared_row.append(value)
                except:
                    prepared_row.append(value)
            # Handle datetime
            elif isinstance(value, datetime):
                prepared_row.append(value.isoformat())
            # Handle bytes (for LargeBinary)
            elif isinstance(value, bytes):
                prepared_row.append(value)
            else:
                prepared_row.append(value)
        
        prepared_rows.append(tuple(prepared_row))
    
    if not prepared_rows:
        print(f"   ⚠️  No rows to insert after preparation")
        return 0
    
    # Build insert query for execute_values
    insert_query = f"""
        INSERT INTO {table_name} ({', '.join(mapped_cols)})
        VALUES %s
        ON CONFLICT DO NOTHING
    """
    
    # Batch insert using execute_values
    try:
        execute_values(new_cursor, insert_query, prepared_rows)
        new_pg_conn.commit()
        print(f"   ✅ Inserted {len(prepared_rows)} rows")
        return len(prepared_rows)
    except Exception as e:
        new_pg_conn.rollback()
        print(f"   ❌ Error inserting data: {e}")
        import traceback
        traceback.print_exc()
        return 0

def main():
    print("🚀 Starting SaaS data migration from old PostgreSQL to new PostgreSQL")
    print("=" * 60)
    
    # Connect to old PostgreSQL
    print("\n📂 Connecting to OLD PostgreSQL database...")
    old_pg_params = parse_pg_url(OLD_PG_URL)
    try:
        old_pg_conn = psycopg2.connect(**old_pg_params)
        old_pg_conn.autocommit = False
        print(f"✅ Connected to OLD PostgreSQL: {old_pg_params['database']}")
    except Exception as e:
        print(f"❌ Error connecting to old PostgreSQL: {e}")
        sys.exit(1)
    
    # Connect to new PostgreSQL
    print("📂 Connecting to NEW PostgreSQL database...")
    new_pg_params = parse_pg_url(PG_URL)
    try:
        new_pg_conn = psycopg2.connect(**new_pg_params)
        new_pg_conn.autocommit = False
        print(f"✅ Connected to NEW PostgreSQL: {new_pg_params['database']}")
    except Exception as e:
        print(f"❌ Error connecting to new PostgreSQL: {e}")
        old_pg_conn.close()
        sys.exit(1)
    
    # Find all customers with data (accounts, KPIs, or uploads)
    old_cursor = old_pg_conn.cursor()
    old_cursor.execute("""
        SELECT DISTINCT c.customer_id, c.customer_name,
               (SELECT COUNT(*) FROM accounts WHERE customer_id = c.customer_id) as account_count,
               (SELECT COUNT(*) FROM kpi_uploads WHERE customer_id = c.customer_id) as upload_count
        FROM customers c
        WHERE EXISTS (
            SELECT 1 FROM accounts WHERE customer_id = c.customer_id
        ) OR EXISTS (
            SELECT 1 FROM kpi_uploads WHERE customer_id = c.customer_id
        )
        ORDER BY account_count DESC, upload_count DESC
    """)
    customers_with_data = old_cursor.fetchall()
    
    if not customers_with_data:
        print("❌ Error: No customers found with accounts or uploads")
        old_pg_conn.close()
        new_pg_conn.close()
        sys.exit(1)
    
    print(f"\n📊 Found {len(customers_with_data)} customer(s) with data:")
    for cid, cname, acc_count, upload_count in customers_with_data:
        print(f"   - {cname} (ID: {cid}): {acc_count} accounts, {upload_count} uploads")
    
    # Migrate all customers with data (or just the first one if you prefer)
    customers_to_migrate = customers_with_data
    
    # Tables to migrate (in order due to foreign keys)
    tables = [
        ('customers', []),  # Customer record
        ('users', []),  # Users
        ('customer_configs', []),  # Customer configs
        ('accounts', []),  # Accounts
        ('products', []),  # Products
        ('kpi_uploads', []),  # KPI Uploads
        ('kpis', []),  # KPIs (no customer_id filter - linked via accounts)
        ('health_trends', []),  # Health trends
        ('kpi_time_series', []),  # Time series
        ('kpi_reference_ranges', []),  # Reference ranges
        ('playbook_triggers', []),  # Playbook triggers
        ('playbook_executions', []),  # Playbook executions
        ('playbook_reports', []),  # Playbook reports
    ]
    
    total_migrated = 0
    
    # Migrate each customer
    for customer_id, customer_name, acc_count, upload_count in customers_to_migrate:
        print(f"\n{'='*60}")
        print(f"🔄 Migrating customer: {customer_name} (ID: {customer_id})")
        print(f"{'='*60}")
        
        # STEP 1: Migrate accounts first, create account_id mapping
        old_cursor.execute("SELECT account_id, account_name FROM accounts WHERE customer_id = %s ORDER BY account_id", (customer_id,))
        old_accounts = old_cursor.fetchall()
        
        new_cursor = new_pg_conn.cursor()
        account_id_map = {}  # Map old account_id to new account_id
        
        if old_accounts:
            print(f"\n📝 Migrating {len(old_accounts)} accounts...")
            for old_account_id, account_name in old_accounts:
                # Check if account already exists in new PostgreSQL
                new_cursor.execute("""
                    SELECT account_id FROM accounts 
                    WHERE customer_id = %s AND account_name = %s
                """, (customer_id, account_name))
                existing = new_cursor.fetchone()
                
                if existing:
                    new_account_id = existing[0]
                    print(f"   ✅ Account exists: {account_name} (ID: {new_account_id})")
                else:
                    # Get full account data from old DB
                    old_cursor.execute("""
                        SELECT account_name, revenue, account_status, industry, region, 
                               external_account_id, profile_metadata, created_at, updated_at
                        FROM accounts WHERE account_id = %s
                    """, (old_account_id,))
                    acc_data = old_cursor.fetchone()
                    
                    # Convert profile_metadata to JSON string if it's a dict
                    profile_metadata = acc_data[6]
                    if isinstance(profile_metadata, dict):
                        profile_metadata = json.dumps(profile_metadata)
                    elif profile_metadata is None:
                        profile_metadata = None
                    
                    # Create account in new PostgreSQL
                    new_cursor.execute("""
                        INSERT INTO accounts (customer_id, account_name, revenue, account_status, 
                                            industry, region, external_account_id, profile_metadata, 
                                            created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING account_id
                    """, (customer_id, acc_data[0], acc_data[1], acc_data[2], acc_data[3], 
                          acc_data[4], acc_data[5], profile_metadata, acc_data[7], acc_data[8]))
                    new_account_id = new_cursor.fetchone()[0]
                    new_pg_conn.commit()
                    print(f"   ✅ Created account: {account_name} (ID: {new_account_id})")
                
                account_id_map[old_account_id] = new_account_id
            
            print(f"   ✅ Migrated/mapped {len(account_id_map)} accounts")
        
        # STEP 2: Migrate tables
        for table_name, skip_cols in tables:
            try:
                # For KPIs table, filter by account_id instead of customer_id
                if table_name == 'kpis':
                    # Get old account IDs from old PostgreSQL
                    old_cursor.execute("SELECT account_id FROM accounts WHERE customer_id = %s", (customer_id,))
                    old_account_ids = [row[0] for row in old_cursor.fetchall()]
                    
                    if old_account_ids:
                        # Migrate KPIs for these accounts (will use account_id_map for remapping)
                        count = migrate_kpis_by_accounts_with_mapping(old_pg_conn, new_pg_conn, old_account_ids, account_id_map)
                        total_migrated += count
                    else:
                        print(f"\n📦 Migrating table: {table_name}")
                        print(f"   ⚠️  No accounts found for customer_id={customer_id}, skipping KPIs")
                elif table_name == 'kpi_uploads' and account_id_map:
                    # Update account_id in uploads before migrating
                    count = migrate_table_with_account_mapping(old_pg_conn, new_pg_conn, table_name, customer_id, account_id_map, skip_cols)
                    total_migrated += count
                else:
                    count = migrate_table_from_pg(old_pg_conn, new_pg_conn, table_name, customer_id, skip_cols)
                    total_migrated += count
            except Exception as e:
                print(f"   ❌ Error migrating {table_name}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    # Summary
    print("\n" + "=" * 60)
    print(f"✅ Migration complete!")
    print(f"   Total rows migrated: {total_migrated}")
    print(f"   Customers migrated: {len(customers_to_migrate)}")
    for cid, cname, _, _ in customers_to_migrate:
        print(f"      - {cname} (ID: {cid})")
    print("\n💡 Next steps:")
    print("   1. Restart the backend server")
    print("   2. Login with SaaS credentials")
    print("   3. Verify data appears correctly")
    
    # Close connections
    old_pg_conn.close()
    new_pg_conn.close()

if __name__ == '__main__':
    main()

