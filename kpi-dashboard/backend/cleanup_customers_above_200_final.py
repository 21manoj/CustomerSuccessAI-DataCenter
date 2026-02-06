#!/usr/bin/env python3
"""
Final cleanup script that discovers all foreign key constraints and deletes in proper order
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app
from sqlalchemy import text, inspect
from extensions import db

def cleanup_customers_above_200():
    """Remove all customers with ID > 200 by discovering all FK constraints"""
    
    with app.app_context():
        # Get customer IDs
        result = db.session.execute(text("SELECT customer_id FROM customers WHERE customer_id > 200"))
        customer_ids = [row[0] for row in result]
        
        if not customer_ids:
            print('✅ No customers with ID > 200 found')
            return True
        
        print(f'🔍 Found {len(customer_ids)} customers with ID > 200')
        
        # Get account IDs
        result = db.session.execute(
            text("SELECT account_id FROM accounts WHERE customer_id = ANY(:customer_ids)"),
            {"customer_ids": customer_ids}
        )
        account_ids = [row[0] for row in result]
        print(f'📊 Found {len(account_ids)} accounts to delete')
        
        # Discover all tables with foreign keys to account_id or customer_id
        inspector = inspect(db.engine)
        all_tables = inspector.get_table_names()
        
        account_fk_tables = set()
        customer_fk_tables = set()
        
        for table in all_tables:
            try:
                fks = inspector.get_foreign_keys(table)
                for fk in fks:
                    ref_cols = fk.get('constrained_columns', [])
                    if 'account_id' in ref_cols:
                        account_fk_tables.add(table)
                    if 'customer_id' in ref_cols:
                        customer_fk_tables.add(table)
            except:
                pass
        
        print(f'📋 Found {len(account_fk_tables)} tables with FK to account_id')
        print(f'📋 Found {len(customer_fk_tables)} tables with FK to customer_id')
        
        # Delete from account-related tables
        deleted_count = 0
        for table in account_fk_tables:
            if table == 'accounts':  # Skip accounts itself
                continue
            try:
                result = db.session.execute(
                    text(f"DELETE FROM {table} WHERE account_id = ANY(:account_ids)"),
                    {"account_ids": account_ids}
                )
                if result.rowcount > 0:
                    print(f'   ✅ Deleted {result.rowcount} from {table}')
                    deleted_count += result.rowcount
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                error_msg = str(e)
                if 'does not exist' not in error_msg.lower():
                    print(f'   ⚠️  {table}: {error_msg[:80]}')
        
        # Delete accounts
        try:
            result = db.session.execute(
                text("DELETE FROM accounts WHERE customer_id = ANY(:customer_ids)"),
                {"customer_ids": customer_ids}
            )
            print(f'   ✅ Deleted {result.rowcount} accounts')
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f'   ❌ Error deleting accounts: {str(e)[:100]}')
            return False
        
        # Delete from customer-related tables (excluding accounts which we already deleted)
        for table in customer_fk_tables:
            if table in ['accounts', 'customers']:  # Skip these
                continue
            try:
                result = db.session.execute(
                    text(f"DELETE FROM {table} WHERE customer_id = ANY(:customer_ids)"),
                    {"customer_ids": customer_ids}
                )
                if result.rowcount > 0:
                    print(f'   ✅ Deleted {result.rowcount} from {table}')
                    deleted_count += result.rowcount
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                error_msg = str(e)
                if 'does not exist' not in error_msg.lower():
                    print(f'   ⚠️  {table}: {error_msg[:80]}')
        
        # Finally delete customers
        try:
            result = db.session.execute(
                text("DELETE FROM customers WHERE customer_id = ANY(:customer_ids)"),
                {"customer_ids": customer_ids}
            )
            print(f'   ✅ Deleted {result.rowcount} customers')
            db.session.commit()
            print(f'\n✅ SUCCESS: All customers with ID > 200 have been removed!')
            return True
        except Exception as e:
            db.session.rollback()
            print(f'   ❌ Error deleting customers: {str(e)[:100]}')
            return False

if __name__ == '__main__':
    print('=' * 60)
    print('CLEANUP: Customers with ID > 200 (Final Version)')
    print('=' * 60)
    success = cleanup_customers_above_200()
    if success:
        print('\n✅ Cleanup completed successfully!')
    else:
        print('\n❌ Cleanup failed. Please check errors above.')
    print('=' * 60)
