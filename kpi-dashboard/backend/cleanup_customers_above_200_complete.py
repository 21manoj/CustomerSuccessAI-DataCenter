#!/usr/bin/env python3
"""
Complete cleanup script - deletes all customers with ID > 200
Handles ALL foreign key constraints in proper order
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app
from sqlalchemy import text
from extensions import db

def cleanup_customers_above_200():
    """Remove all customers with ID > 200 handling ALL foreign key constraints"""
    
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
        
        # Get journey_account IDs
        journey_account_ids = []
        if account_ids:
            result = db.session.execute(
                text("SELECT journey_account_id FROM journey_accounts WHERE account_id = ANY(:account_ids)"),
                {"account_ids": account_ids}
            )
            journey_account_ids = [row[0] for row in result]
            print(f'📊 Found {len(journey_account_ids)} journey_accounts to delete')
        
        try:
            # Step 1: Delete from ALL tables that reference journey_accounts
            journey_account_tables = [
                'journey_events',
                'journey_kpis',
                'journey_health',
                'journey_milestones',
                'signal_predictions',
                'signal_baseline_results'
            ]
            
            for table in journey_account_tables:
                if journey_account_ids:
                    try:
                        result = db.session.execute(
                            text(f"DELETE FROM {table} WHERE journey_account_id = ANY(:ids)"),
                            {"ids": journey_account_ids}
                        )
                        if result.rowcount > 0:
                            print(f'   ✅ Deleted {result.rowcount} from {table}')
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        error_msg = str(e)
                        if 'does not exist' not in error_msg.lower():
                            print(f'   ⚠️  {table}: {error_msg[:60]}')
            
            # Step 2: Delete journey_accounts
            if account_ids:
                result = db.session.execute(
                    text("DELETE FROM journey_accounts WHERE account_id = ANY(:account_ids)"),
                    {"account_ids": account_ids}
                )
                print(f'   ✅ Deleted {result.rowcount} from journey_accounts')
                db.session.commit()
            
            # Step 3: Delete from all other account-related tables
            account_tables = [
                'account_notes',
                'kpi_measurements',
                'account_health_history',
                'expansion_readiness_scores',
                'playbook_executions',
                'playbook_reports',
                'playbook_triggers',
                'account_profiles',
                'account_snapshots',
                'account_products',
                'customer_insights',
                'financial_projections',
                'qualitative_signals',
                'dc2s_kpis',
                'products'
            ]
            
            for table in account_tables:
                if account_ids:
                    try:
                        result = db.session.execute(
                            text(f"DELETE FROM {table} WHERE account_id = ANY(:account_ids)"),
                            {"account_ids": account_ids}
                        )
                        if result.rowcount > 0:
                            print(f'   ✅ Deleted {result.rowcount} from {table}')
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        error_msg = str(e)
                        if 'does not exist' not in error_msg.lower():
                            pass  # Silent skip
            
            # Step 4: Delete accounts
            result = db.session.execute(
                text("DELETE FROM accounts WHERE customer_id = ANY(:customer_ids)"),
                {"customer_ids": customer_ids}
            )
            print(f'   ✅ Deleted {result.rowcount} accounts')
            db.session.commit()
            
            # Step 5: Delete from customer-related tables
            customer_tables = [
                'qualitative_signals',  # In case some don't have account_id
                'health_trends',
                'kpi_time_series',
                'kpi_uploads',
                'customer_configs',
                'users'
            ]
            
            for table in customer_tables:
                try:
                    result = db.session.execute(
                        text(f"DELETE FROM {table} WHERE customer_id = ANY(:customer_ids)"),
                        {"customer_ids": customer_ids}
                    )
                    if result.rowcount > 0:
                        print(f'   ✅ Deleted {result.rowcount} from {table}')
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    error_msg = str(e)
                    if 'does not exist' not in error_msg.lower():
                        pass  # Silent skip
            
            # Step 6: Delete customers
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
            print(f'\n❌ Error during cleanup: {e}')
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print('=' * 60)
    print('CLEANUP: Customers with ID > 200 (Complete Version)')
    print('=' * 60)
    success = cleanup_customers_above_200()
    if success:
        print('\n✅ Cleanup completed successfully!')
    else:
        print('\n❌ Cleanup failed. Please check errors above.')
    print('=' * 60)
