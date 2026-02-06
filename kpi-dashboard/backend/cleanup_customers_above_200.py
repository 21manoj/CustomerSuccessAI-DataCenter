#!/usr/bin/env python3
"""
Cleanup script to remove all customers with ID > 200
Removes all related data from database tables and files
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app
from models import (
    Customer, Account, KPI, KPIUpload, User, 
    HealthTrend, CustomerConfig, KPITimeSeries, DC2SKPI, Product,
    AccountNote
)
# QualitativeSignal might not have customer_id, check if it exists
try:
    from models import QualitativeSignal
    HAS_QUALITATIVE_SIGNAL = True
except:
    HAS_QUALITATIVE_SIGNAL = False
from extensions import db
from sqlalchemy import text

def cleanup_customers_above_200():
    """Remove all customers with ID > 200 and all related data"""
    
    with app.app_context():
        # Find all customers with ID > 200
        customers = Customer.query.filter(Customer.customer_id > 200).all()
        
        if not customers:
            print('✅ No customers with ID > 200 found')
            return
        
        customer_ids = [c.customer_id for c in customers]
        print(f'🔍 Found {len(customers)} customers with ID > 200: {customer_ids}')
        
        # Count related data before deletion
        print(f'\n📊 Counting related data to be deleted...')
        
        accounts_count = Account.query.filter(Account.customer_id.in_(customer_ids)).count()
        kpi_uploads_count = KPIUpload.query.filter(KPIUpload.customer_id.in_(customer_ids)).count()
        kpis_count = KPI.query.join(KPIUpload).filter(KPIUpload.customer_id.in_(customer_ids)).count()
        users_count = User.query.filter(User.customer_id.in_(customer_ids)).count()
        signals_count = 0
        if HAS_QUALITATIVE_SIGNAL:
            try:
                signals_count = QualitativeSignal.query.filter(QualitativeSignal.account_id.in_(
                    db.session.query(Account.account_id).filter(Account.customer_id.in_(customer_ids))
                )).count()
            except:
                pass
        health_trends_count = HealthTrend.query.filter(HealthTrend.customer_id.in_(customer_ids)).count()
        configs_count = CustomerConfig.query.filter(CustomerConfig.customer_id.in_(customer_ids)).count()
        time_series_count = KPITimeSeries.query.filter(KPITimeSeries.customer_id.in_(customer_ids)).count()
        dc2s_kpis_count = DC2SKPI.query.join(Account).filter(Account.customer_id.in_(customer_ids)).count()
        products_count = Product.query.filter(Product.customer_id.in_(customer_ids)).count()
        notes_count = AccountNote.query.join(Account).filter(Account.customer_id.in_(customer_ids)).count()
        
        print(f'   Accounts: {accounts_count}')
        print(f'   KPI Uploads: {kpi_uploads_count}')
        print(f'   KPIs: {kpis_count}')
        print(f'   Users: {users_count}')
        print(f'   Qualitative Signals: {signals_count}')
        print(f'   Health Trends: {health_trends_count}')
        print(f'   Customer Configs: {configs_count}')
        print(f'   KPI Time Series: {time_series_count}')
        print(f'   DC2S KPIs: {dc2s_kpis_count}')
        print(f'   Products: {products_count}')
        print(f'   Account Notes: {notes_count}')
        
        # Delete in proper order (respecting foreign key constraints)
        print(f'\n🗑️  Starting deletion...')
        
        try:
            # Get account IDs first
            account_ids_list = [acc.account_id for acc in Account.query.filter(Account.customer_id.in_(customer_ids)).all()]
            
            # 1. Delete Account Notes
            if account_ids_list:
                deleted_notes = AccountNote.query.filter(AccountNote.account_id.in_(account_ids_list)).delete(synchronize_session=False)
            else:
                deleted_notes = 0
            print(f'   ✅ Deleted {deleted_notes} Account Notes')
            
            # 2. Delete KPIs (depends on KPIUpload)
            upload_ids = [u.upload_id for u in KPIUpload.query.filter(KPIUpload.customer_id.in_(customer_ids)).all()]
            if upload_ids:
                deleted_kpis = KPI.query.filter(KPI.upload_id.in_(upload_ids)).delete(synchronize_session=False)
            else:
                deleted_kpis = 0
            print(f'   ✅ Deleted {deleted_kpis} KPIs')
            
            # 3. Delete KPI Time Series
            deleted_time_series = KPITimeSeries.query.filter(KPITimeSeries.customer_id.in_(customer_ids)).delete(synchronize_session=False)
            print(f'   ✅ Deleted {deleted_time_series} KPI Time Series')
            
            # 4. Delete DC2S KPIs (depends on Accounts)
            if account_ids_list:
                deleted_dc2s_kpis = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids_list)).delete(synchronize_session=False)
            else:
                deleted_dc2s_kpis = 0
            print(f'   ✅ Deleted {deleted_dc2s_kpis} DC2S KPIs')
            
            # 5. Delete KPI Uploads
            deleted_uploads = KPIUpload.query.filter(KPIUpload.customer_id.in_(customer_ids)).delete(synchronize_session=False)
            print(f'   ✅ Deleted {deleted_uploads} KPI Uploads')
            
            # 6. Delete Products
            deleted_products = Product.query.filter(Product.customer_id.in_(customer_ids)).delete(synchronize_session=False)
            print(f'   ✅ Deleted {deleted_products} Products')
            
            # 6.5. Delete all account-related tables (handle all foreign key constraints)
            if account_ids_list:
                # List of tables that reference account_id
                account_related_tables = [
                    'account_profiles',
                    'kpi_measurements',
                    'account_health_history',
                    'expansion_readiness_scores',
                    'account_snapshots',
                    'playbook_executions',
                    'playbook_reports',
                    'playbook_triggers',
                    'account_notes'  # Already deleted, but just in case
                ]
                
                for table_name in account_related_tables:
                    try:
                        deleted = db.session.execute(
                            text(f"DELETE FROM {table_name} WHERE account_id = ANY(:account_ids)"),
                            {"account_ids": account_ids_list}
                        ).rowcount
                        if deleted > 0:
                            print(f'   ✅ Deleted {deleted} from {table_name}')
                    except Exception as e:
                        # Table might not exist or already deleted, skip
                        pass
            
            # 7. Delete Qualitative Signals (BEFORE accounts - foreign key constraint)
            deleted_signals = 0
            if HAS_QUALITATIVE_SIGNAL and account_ids_list:
                try:
                    deleted_signals = QualitativeSignal.query.filter(QualitativeSignal.account_id.in_(account_ids_list)).delete(synchronize_session=False)
                except:
                    pass
            print(f'   ✅ Deleted {deleted_signals} Qualitative Signals')
            
            # 8. Delete Accounts
            deleted_accounts = Account.query.filter(Account.customer_id.in_(customer_ids)).delete(synchronize_session=False)
            print(f'   ✅ Deleted {deleted_accounts} Accounts')
            
            # 9. Delete Health Trends (depends on accounts, but account_id might be nullable)
            deleted_health_trends = HealthTrend.query.filter(HealthTrend.customer_id.in_(customer_ids)).delete(synchronize_session=False)
            print(f'   ✅ Deleted {deleted_health_trends} Health Trends')
            
            # 10. Delete Customer Configs
            deleted_configs = CustomerConfig.query.filter(CustomerConfig.customer_id.in_(customer_ids)).delete(synchronize_session=False)
            print(f'   ✅ Deleted {deleted_configs} Customer Configs')
            
            # 11. Delete Users
            deleted_users = User.query.filter(User.customer_id.in_(customer_ids)).delete(synchronize_session=False)
            print(f'   ✅ Deleted {deleted_users} Users')
            
            # 12. Delete Customers
            deleted_customers = Customer.query.filter(Customer.customer_id.in_(customer_ids)).delete(synchronize_session=False)
            print(f'   ✅ Deleted {deleted_customers} Customers')
            
            # Commit all deletions
            db.session.commit()
            print(f'\n✅ Cleanup complete! Deleted {deleted_customers} customers and all related data.')
            
        except Exception as e:
            print(f'\n❌ Error during cleanup: {e}')
            # Rollback the failed transaction
            db.session.rollback()
            # Try to continue with remaining deletions using raw SQL in a fresh transaction
            print('   Attempting to continue with raw SQL deletions...')
            try:
                # Start fresh transaction
                db.session.begin()
                if account_ids_list:
                    # Delete remaining account-related data
                    remaining_tables = [
                        'playbook_reports', 'playbook_triggers', 'account_snapshots'
                    ]
                    for table in remaining_tables:
                        try:
                            db.session.execute(
                                text(f"DELETE FROM {table} WHERE account_id = ANY(:account_ids)"),
                                {"account_ids": account_ids_list}
                            )
                        except:
                            pass
                    
                    # Finally delete accounts
                    db.session.execute(
                        text("DELETE FROM accounts WHERE customer_id = ANY(:customer_ids)"),
                        {"customer_ids": customer_ids}
                    )
                
                # Delete remaining customer-related data
                db.session.execute(
                    text("DELETE FROM qualitative_signals WHERE customer_id = ANY(:customer_ids)"),
                    {"customer_ids": customer_ids}
                )
                db.session.execute(
                    text("DELETE FROM health_trends WHERE customer_id = ANY(:customer_ids)"),
                    {"customer_ids": customer_ids}
                )
                db.session.execute(
                    text("DELETE FROM customer_configs WHERE customer_id = ANY(:customer_ids)"),
                    {"customer_ids": customer_ids}
                )
                db.session.execute(
                    text("DELETE FROM users WHERE customer_id = ANY(:customer_ids)"),
                    {"customer_ids": customer_ids}
                )
                db.session.execute(
                    text("DELETE FROM customers WHERE customer_id = ANY(:customer_ids)"),
                    {"customer_ids": customer_ids}
                )
                db.session.commit()
                print('   ✅ Completed cleanup using raw SQL')
                return True
            except Exception as e2:
                db.session.rollback()
                print(f'   ❌ Raw SQL cleanup also failed: {e2}')
                import traceback
                traceback.print_exc()
                return False
        
        return True

if __name__ == '__main__':
    print('=' * 60)
    print('CLEANUP: Customers with ID > 200')
    print('=' * 60)
    success = cleanup_customers_above_200()
    if success:
        print('\n✅ Cleanup completed successfully!')
    else:
        print('\n❌ Cleanup failed. Please check errors above.')
    print('=' * 60)
