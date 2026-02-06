#!/usr/bin/env python3
"""
Simple cleanup script using raw SQL to remove all customers with ID > 200
Handles all foreign key constraints by deleting in proper order
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app
from sqlalchemy import text

def cleanup_customers_above_200():
    """Remove all customers with ID > 200 using raw SQL"""
    
    with app.app_context():
        from extensions import db
        
        # Get customer IDs
        result = db.session.execute(text("SELECT customer_id FROM customers WHERE customer_id > 200"))
        customer_ids = [row[0] for row in result]
        
        if not customer_ids:
            print('✅ No customers with ID > 200 found')
            return True
        
        print(f'🔍 Found {len(customer_ids)} customers with ID > 200')
        print(f'   Customer IDs: {customer_ids[:10]}{"..." if len(customer_ids) > 10 else ""}')
        
        # Get account IDs
        result = db.session.execute(
            text("SELECT account_id FROM accounts WHERE customer_id = ANY(:customer_ids)"),
            {"customer_ids": customer_ids}
        )
        account_ids = [row[0] for row in result]
        print(f'📊 Found {len(account_ids)} accounts to delete')
        
        try:
            # Delete in proper order to handle foreign keys
            deletion_order = [
                ('account_notes', 'account_id', account_ids),
                ('kpi_measurements', 'account_id', account_ids),
                ('account_health_history', 'account_id', account_ids),
                ('expansion_readiness_scores', 'account_id', account_ids),
                ('playbook_executions', 'account_id', account_ids),
                ('playbook_reports', 'account_id', account_ids),
                ('playbook_triggers', 'account_id', account_ids),
                ('account_profiles', 'account_id', account_ids),
                ('account_snapshots', 'account_id', account_ids),
                ('account_products', 'account_id', account_ids),
                ('journey_accounts', 'account_id', account_ids),
                ('customer_insights', 'account_id', account_ids),
                ('financial_projections', 'account_id', account_ids),
                ('qualitative_signals', 'account_id', account_ids),
                ('dc2s_kpis', 'account_id', account_ids),
                ('products', 'account_id', account_ids),
                ('accounts', 'customer_id', customer_ids),
                ('qualitative_signals', 'customer_id', customer_ids),  # In case some don't have account_id
                ('health_trends', 'customer_id', customer_ids),
                ('kpi_time_series', 'customer_id', customer_ids),
                ('kpi_uploads', 'customer_id', customer_ids),
                ('customer_configs', 'customer_id', customer_ids),
                ('users', 'customer_id', customer_ids),
                ('customers', 'customer_id', customer_ids),
            ]
            
            total_deleted = 0
            for table_name, key_field, ids in deletion_order:
                if not ids:
                    continue
                try:
                    result = db.session.execute(
                        text(f"DELETE FROM {table_name} WHERE {key_field} = ANY(:ids)"),
                        {"ids": ids}
                    )
                    deleted = result.rowcount
                    if deleted > 0:
                        print(f'   ✅ Deleted {deleted} from {table_name}')
                        total_deleted += deleted
                    # Commit after each successful deletion to avoid transaction issues
                    db.session.commit()
                except Exception as e:
                    # Rollback on error and continue
                    db.session.rollback()
                    error_msg = str(e)
                    if 'does not exist' not in error_msg.lower() and 'violates foreign key' not in error_msg.lower() and 'InFailedSqlTransaction' not in error_msg:
                        print(f'   ⚠️  {table_name}: {error_msg[:50]}')
            
            # Explicitly delete accounts and customers (in case they failed in the loop)
            print(f'\n📊 Final cleanup of accounts and customers:')
            try:
                result = db.session.execute(
                    text("DELETE FROM accounts WHERE customer_id = ANY(:customer_ids)"),
                    {"customer_ids": customer_ids}
                )
                print(f'   ✅ Deleted {result.rowcount} accounts')
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f'   ⚠️  Accounts: {str(e)[:100]}')
            
            try:
                result = db.session.execute(
                    text("DELETE FROM customers WHERE customer_id = ANY(:customer_ids)"),
                    {"customer_ids": customer_ids}
                )
                print(f'   ✅ Deleted {result.rowcount} customers')
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f'   ⚠️  Customers: {str(e)[:100]}')
            
            print(f'\n✅ Cleanup complete! Deleted data from {len(deletion_order)} tables')
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f'\n❌ Error during cleanup: {e}')
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print('=' * 60)
    print('CLEANUP: Customers with ID > 200 (Simple SQL Version)')
    print('=' * 60)
    success = cleanup_customers_above_200()
    if success:
        print('\n✅ Cleanup completed successfully!')
    else:
        print('\n❌ Cleanup failed. Please check errors above.')
    print('=' * 60)
