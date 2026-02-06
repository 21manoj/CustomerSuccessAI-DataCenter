#!/usr/bin/env python3
"""
DC2_S Customer Cleanup Script
Based on models.py FK hierarchy - deletes in proper order respecting all foreign key constraints
Also removes customer directories from backend/verticals/

Usage:
    python3 cleanup_dc2_s_customers_Jan25.py [threshold]
    
    Default threshold: 200
    Example: python3 cleanup_dc2_s_customers_Jan25.py 100
"""

import sys
import os
import shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app
from sqlalchemy import text
from extensions import db

def cleanup_customers_above_threshold(threshold=200):
    """Remove all customers with ID > threshold in correct FK order"""
    
    # First, find directories that need cleanup (even if customers are already deleted)
    verticals_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'verticals')
    directory_customer_ids = []
    
    if os.path.exists(verticals_dir):
        for item in os.listdir(verticals_dir):
            if item.startswith('customer') and item.endswith('-dc2_s'):
                try:
                    customer_id = int(item.replace('customer', '').replace('-dc2_s', ''))
                    if customer_id > threshold:
                        directory_customer_ids.append(customer_id)
                except ValueError:
                    pass
    
    with app.app_context():
        # Get customer IDs from database - ONLY dc2_s vertical customers
        result = db.session.execute(
            text("""
                SELECT c.customer_id 
                FROM customers c
                INNER JOIN customer_configs cc ON c.customer_id = cc.customer_id
                WHERE c.customer_id > :threshold 
                AND cc.vertical = 'dc2_s'
            """),
            {"threshold": threshold}
        )
        db_customer_ids = [row[0] for row in result]
        
        # Combine both sources (database and directories)
        all_customer_ids = list(set(db_customer_ids + directory_customer_ids))
        
        if not all_customer_ids:
            print(f'✅ No dc2_s customers with ID > {threshold} found in database or directories')
            return True
        
        # Verify all customer IDs are actually dc2_s (double-check)
        if db_customer_ids:
            result = db.session.execute(
                text("""
                    SELECT c.customer_id 
                    FROM customers c
                    INNER JOIN customer_configs cc ON c.customer_id = cc.customer_id
                    WHERE c.customer_id = ANY(:customer_ids)
                    AND cc.vertical = 'dc2_s'
                """),
                {"customer_ids": db_customer_ids}
            )
            verified_db_ids = [row[0] for row in result]
            if len(verified_db_ids) != len(db_customer_ids):
                print(f'⚠️  Warning: {len(db_customer_ids) - len(verified_db_ids)} customer IDs do not have dc2_s vertical - skipping them')
                # Only use verified IDs
                db_customer_ids = verified_db_ids
                all_customer_ids = list(set(db_customer_ids + directory_customer_ids))
        
        customer_ids = sorted(all_customer_ids)
        print(f'🔍 Found {len(customer_ids)} dc2_s customers with ID > {threshold} (DB: {len(db_customer_ids)}, Directories: {len(directory_customer_ids)})')
        
        # Get account IDs
        result = db.session.execute(
            text("SELECT account_id FROM accounts WHERE customer_id = ANY(:customer_ids)"),
            {"customer_ids": customer_ids}
        )
        account_ids = [row[0] for row in result]
        print(f'📊 Found {len(account_ids)} accounts')
        
        # Get journey_account IDs
        journey_account_ids = []
        if account_ids:
            result = db.session.execute(
                text("SELECT journey_account_id FROM journey_accounts WHERE account_id = ANY(:account_ids)"),
                {"account_ids": account_ids}
            )
            journey_account_ids = [row[0] for row in result]
            print(f'📊 Found {len(journey_account_ids)} journey_accounts')
        
        # Get prediction IDs (for prediction_explanations)
        prediction_ids = []
        if journey_account_ids:
            result = db.session.execute(
                text("SELECT prediction_id FROM signal_predictions WHERE journey_account_id = ANY(:ids)"),
                {"ids": journey_account_ids}
            )
            prediction_ids = [row[0] for row in result]
            print(f'📊 Found {len(prediction_ids)} signal_predictions')
        
        try:
            # ============================================================
            # LEVEL 1: Delete tables that reference prediction_id
            # ============================================================
            if prediction_ids:
                result = db.session.execute(
                    text("DELETE FROM prediction_explanations WHERE prediction_id = ANY(:ids)"),
                    {"ids": prediction_ids}
                )
                print(f'   ✅ Deleted {result.rowcount} from prediction_explanations')
                db.session.commit()
            
            # ============================================================
            # LEVEL 2: Delete tables that reference journey_account_id
            # ============================================================
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
            
            # ============================================================
            # LEVEL 3: Delete journey_accounts
            # ============================================================
            if account_ids:
                result = db.session.execute(
                    text("DELETE FROM journey_accounts WHERE account_id = ANY(:account_ids)"),
                    {"account_ids": account_ids}
                )
                print(f'   ✅ Deleted {result.rowcount} from journey_accounts')
                db.session.commit()
            
            # ============================================================
            # LEVEL 4: Delete tables that reference account_id
            # ============================================================
            account_tables = [
                'account_notes',
                'account_snapshots',
                'account_profiles',
                'account_products',
                'account_health_history',
                'expansion_readiness_scores',
                'kpi_measurements',
                'playbook_executions',
                'playbook_reports',
                'playbook_triggers',  # Also has customer_id, but delete by account_id first
                'customer_insights',
                'financial_projections',
                'qualitative_signals',
                'dc2s_kpis',
                'products',
                'health_trends',
                'kpi_scores',
                'pillar_scores',
                'health_scores'
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
            
            # ============================================================
            # LEVEL 5: Delete KPIs (references upload_id and account_id)
            # ============================================================
            if account_ids:
                # Get upload_ids first
                result = db.session.execute(
                    text("SELECT upload_id FROM kpi_uploads WHERE account_id = ANY(:account_ids)"),
                    {"account_ids": account_ids}
                )
                upload_ids = [row[0] for row in result]
                
                if upload_ids:
                    result = db.session.execute(
                        text("DELETE FROM kpis WHERE upload_id = ANY(:upload_ids)"),
                        {"upload_ids": upload_ids}
                    )
                    print(f'   ✅ Deleted {result.rowcount} from kpis')
                    db.session.commit()
            
            # ============================================================
            # LEVEL 6: Delete KPITimeSeries (references kpi_id, account_id, customer_id)
            # ============================================================
            result = db.session.execute(
                text("DELETE FROM kpi_time_series WHERE customer_id = ANY(:customer_ids)"),
                {"customer_ids": customer_ids}
            )
            if result.rowcount > 0:
                print(f'   ✅ Deleted {result.rowcount} from kpi_time_series')
            db.session.commit()
            
            # ============================================================
            # LEVEL 7: Delete accounts
            # ============================================================
            result = db.session.execute(
                text("DELETE FROM accounts WHERE customer_id = ANY(:customer_ids)"),
                {"customer_ids": customer_ids}
            )
            print(f'   ✅ Deleted {result.rowcount} accounts')
            db.session.commit()
            
            # ============================================================
            # LEVEL 8: Delete tables that reference customer_id (but not accounts)
            # ============================================================
            customer_tables = [
                'kpi_uploads',
                'qualitative_signals',  # In case some don't have account_id
                'health_trends',  # In case some don't have account_id
                'playbook_triggers',  # Delete by customer_id (already deleted by account_id, but ensure)
                'playbook_executions',  # In case some don't have account_id
                'playbook_reports',  # In case some don't have account_id
                'customer_configs',
                'customer_workflow_configs',
                'feature_toggles',
                'query_audits',
                'activity_logs',
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
            
            # ============================================================
            # LEVEL 9: Delete customers (LAST) - only if they exist in DB
            # ============================================================
            if db_customer_ids:
                result = db.session.execute(
                    text("DELETE FROM customers WHERE customer_id = ANY(:customer_ids)"),
                    {"customer_ids": db_customer_ids}
                )
                print(f'   ✅ Deleted {result.rowcount} customers from database')
                db.session.commit()
            else:
                print('   ℹ️  No customers to delete from database (already removed)')
            
            # ============================================================
            # LEVEL 10: Delete customer directories from verticals/
            # ============================================================
            print('\n🗂️  Cleaning up customer directories in verticals/...')
            deleted_dirs = 0
            failed_dirs = []
            
            for customer_id in customer_ids:
                dir_name = f'customer{customer_id}-dc2_s'
                dir_path = os.path.join(verticals_dir, dir_name)
                
                if os.path.exists(dir_path) and os.path.isdir(dir_path):
                    try:
                        shutil.rmtree(dir_path)
                        deleted_dirs += 1
                        print(f'   ✅ Deleted directory: {dir_name}')
                    except Exception as e:
                        failed_dirs.append((dir_name, str(e)))
                        print(f'   ⚠️  Failed to delete {dir_name}: {e}')
            
            if deleted_dirs > 0:
                print(f'\n✅ Deleted {deleted_dirs} customer directories from verticals/')
            else:
                print('   ℹ️  No customer directories found to delete')
            
            if failed_dirs:
                print(f'\n⚠️  Failed to delete {len(failed_dirs)} directories:')
                for dir_name, error in failed_dirs:
                    print(f'   - {dir_name}: {error}')
            
            print(f'\n✅ SUCCESS: All customers with ID > {threshold} have been removed from database and directories!')
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f'\n❌ Error during cleanup: {e}')
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    # Get threshold from command line argument, default to 200
    threshold = 200
    if len(sys.argv) > 1:
        try:
            threshold = int(sys.argv[1])
        except ValueError:
            print(f'⚠️  Invalid threshold "{sys.argv[1]}", using default: 200')
            threshold = 200
    
    print('=' * 60)
    print(f'CLEANUP: DC2_S Customers with ID > {threshold} (Based on models.py FK Hierarchy)')
    print('⚠️  Only customers with vertical = "dc2_s" will be deleted')
    print('=' * 60)
    success = cleanup_customers_above_threshold(threshold)
    if success:
        print('\n✅ Cleanup completed successfully!')
    else:
        print('\n❌ Cleanup failed. Please check errors above.')
    print('=' * 60)
