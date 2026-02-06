#!/usr/bin/env python3
"""
Remove Customers with Zero Accounts
====================================

This script removes customers that have no accounts, along with all their associated data.

Safety Features:
- Only removes customers with 0 accounts
- Shows preview before deletion
- Can filter by customer IDs or patterns
- Dry-run mode available

Usage:
    # Preview what will be deleted (dry-run)
    python3 remove_customers_with_no_accounts.py --dry-run
    
    # Remove all customers with 0 accounts
    python3 remove_customers_with_no_accounts.py
    
    # Remove specific customer IDs
    python3 remove_customers_with_no_accounts.py --customer-ids 7,11,12
    
    # Remove only test/onboarding customers
    python3 remove_customers_with_no_accounts.py --test-only
"""

import sys
import os
import argparse
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_v3_minimal import app, db
from sqlalchemy import text
from models import (
    Customer, User, Account, CustomerConfig, KPI, KPIUpload, Product,
    AccountNote, AccountSnapshot, HealthTrend, KPITimeSeries,
    PlaybookTrigger, PlaybookExecution, PlaybookReport,
    KPIReferenceRange, FeatureToggle
)

# Try to import optional models
try:
    from models import ActivityLog
    HAS_ACTIVITY_LOG = True
except ImportError:
    HAS_ACTIVITY_LOG = False

try:
    from product_analytics_models import ProductCatalog, ProductTrend, ProductAggregateTrend
    HAS_PRODUCT_ANALYTICS = True
except ImportError:
    HAS_PRODUCT_ANALYTICS = False


def get_customers_with_no_accounts(test_only=False, customer_ids=None):
    """Get list of customers that have zero accounts"""
    with app.app_context():
        # Get all customers
        query = Customer.query
        
        # Filter by customer IDs if provided
        if customer_ids:
            query = query.filter(Customer.customer_id.in_(customer_ids))
        
        customers = query.all()
        
        customers_to_delete = []
        
        for customer in customers:
            # Check account count
            account_count = Account.query.filter_by(customer_id=customer.customer_id).count()
            
            if account_count == 0:
                # Check if it's a test customer (if test_only is True)
                is_test = False
                if test_only:
                    email = customer.email or ''
                    name = customer.customer_name or ''
                    is_test = (
                        'test' in email.lower() or 
                        'test' in name.lower() or
                        'testdrive' in email.lower() or
                        'onboarding' in email.lower()
                    )
                
                if not test_only or is_test:
                    customers_to_delete.append(customer)
        
        return customers_to_delete


def get_customer_data_summary(customer_id):
    """Get summary of all data associated with a customer"""
    summary = {
        'users': User.query.filter_by(customer_id=customer_id).count(),
        'accounts': Account.query.filter_by(customer_id=customer_id).count(),
        'configs': CustomerConfig.query.filter_by(customer_id=customer_id).count(),
        'kpi_uploads': KPIUpload.query.filter_by(customer_id=customer_id).count(),
        'products': Product.query.filter_by(customer_id=customer_id).count(),
        'account_notes': AccountNote.query.filter_by(customer_id=customer_id).count(),
        'account_snapshots': AccountSnapshot.query.filter_by(customer_id=customer_id).count() if hasattr(AccountSnapshot, 'customer_id') else 0,
        'health_trends': HealthTrend.query.filter_by(customer_id=customer_id).count(),
        'kpi_time_series': KPITimeSeries.query.filter_by(customer_id=customer_id).count(),
        'playbook_triggers': PlaybookTrigger.query.filter_by(customer_id=customer_id).count(),
        'playbook_executions': PlaybookExecution.query.filter_by(customer_id=customer_id).count(),
        'playbook_reports': PlaybookReport.query.filter_by(customer_id=customer_id).count(),
        'kpi_reference_ranges': KPIReferenceRange.query.filter_by(customer_id=customer_id).count(),
        'feature_toggles': FeatureToggle.query.filter_by(customer_id=customer_id).count(),
    }
    
    # OnboardingSessions (check via raw SQL since model may not exist)
    try:
        user_ids = [u.user_id for u in User.query.filter_by(customer_id=customer_id).all()]
        if user_ids:
            conn = db.engine.connect()
            check_table = text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'onboarding_sessions'
                )
            """)
            table_exists = conn.execute(check_table).scalar()
            if table_exists:
                # Use IN clause
                placeholders = ','.join([':user_id_' + str(i) for i in range(len(user_ids))])
                params = {f'user_id_{i}': uid for i, uid in enumerate(user_ids)}
                count_query = text(f"""
                    SELECT COUNT(*) FROM onboarding_sessions 
                    WHERE user_id IN ({placeholders})
                """)
                summary['onboarding_sessions'] = conn.execute(count_query, params).scalar()
            else:
                summary['onboarding_sessions'] = 0
            conn.close()
        else:
            summary['onboarding_sessions'] = 0
    except:
        summary['onboarding_sessions'] = 0
    
    # Get KPI count (via uploads)
    upload_ids = [u.upload_id for u in KPIUpload.query.filter_by(customer_id=customer_id).all()]
    if upload_ids:
        summary['kpis'] = KPI.query.filter(KPI.upload_id.in_(upload_ids)).count()
    else:
        summary['kpis'] = 0
    
    # Optional models
    if HAS_ACTIVITY_LOG:
        summary['activity_logs'] = ActivityLog.query.filter_by(customer_id=customer_id).count()
    
    if HAS_PRODUCT_ANALYTICS:
        summary['product_catalogs'] = ProductCatalog.query.filter_by(customer_id=customer_id).count()
        summary['product_trends'] = ProductTrend.query.filter_by(customer_id=customer_id).count()
    
    return summary


def delete_customer_data(customer_id, dry_run=False):
    """Delete all data associated with a customer"""
    customer = Customer.query.get(customer_id)
    if not customer:
        return {'error': f'Customer {customer_id} not found'}
    
    summary = get_customer_data_summary(customer_id)
    
    if dry_run:
        return {
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'summary': summary,
            'action': 'would_delete'
        }
    
    try:
        # Delete in order to respect foreign key constraints
        
        # 1. Delete KPIs (via uploads)
        upload_ids = [u.upload_id for u in KPIUpload.query.filter_by(customer_id=customer_id).all()]
        if upload_ids:
            KPI.query.filter(KPI.upload_id.in_(upload_ids)).delete(synchronize_session=False)
        
        # 2. Delete KPI Time Series
        KPITimeSeries.query.filter_by(customer_id=customer_id).delete()
        
        # 3. Delete KPI Uploads
        KPIUpload.query.filter_by(customer_id=customer_id).delete()
        
        # 4. Delete Products
        Product.query.filter_by(customer_id=customer_id).delete()
        
        # 5. Delete Account-related data
        AccountNote.query.filter_by(customer_id=customer_id).delete()
        if hasattr(AccountSnapshot, 'customer_id'):
            AccountSnapshot.query.filter_by(customer_id=customer_id).delete()
        
        # 6. Delete Accounts (should be 0, but delete anyway)
        Account.query.filter_by(customer_id=customer_id).delete()
        
        # 7. Delete Health Trends
        HealthTrend.query.filter_by(customer_id=customer_id).delete()
        
        # 8. Delete Playbook data
        PlaybookReport.query.filter_by(customer_id=customer_id).delete()
        PlaybookExecution.query.filter_by(customer_id=customer_id).delete()
        PlaybookTrigger.query.filter_by(customer_id=customer_id).delete()
        
        # 9. Delete Customer-specific configs
        KPIReferenceRange.query.filter_by(customer_id=customer_id).delete()
        FeatureToggle.query.filter_by(customer_id=customer_id).delete()
        CustomerConfig.query.filter_by(customer_id=customer_id).delete()
        
        # 10. Delete OnboardingSessions (using raw SQL since model may not exist) - must be before users
        # Get user IDs for this customer first
        user_ids = [u.user_id for u in User.query.filter_by(customer_id=customer_id).all()]
        if user_ids:
            try:
                # Check if table exists and delete sessions using raw SQL
                conn = db.engine.connect()
                # Check if table exists
                check_table = text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'onboarding_sessions'
                    )
                """)
                table_exists = conn.execute(check_table).scalar()
                
                if table_exists:
                    # Delete onboarding sessions for these users
                    # Use IN clause instead of ANY for better compatibility
                    placeholders = ','.join([':user_id_' + str(i) for i in range(len(user_ids))])
                    params = {f'user_id_{i}': uid for i, uid in enumerate(user_ids)}
                    delete_sessions = text(f"""
                        DELETE FROM onboarding_sessions 
                        WHERE user_id IN ({placeholders})
                    """)
                    conn.execute(delete_sessions, params)
                    conn.commit()
                conn.close()
            except Exception as e:
                # If table doesn't exist or error, continue
                print(f"   Note: Could not delete onboarding_sessions: {e}")
                import traceback
                traceback.print_exc()
        
        # 11. Delete Users
        User.query.filter_by(customer_id=customer_id).delete()
        
        # 12. Optional models
        if HAS_ACTIVITY_LOG:
            ActivityLog.query.filter_by(customer_id=customer_id).delete()
        
        if HAS_PRODUCT_ANALYTICS:
            ProductTrend.query.filter_by(customer_id=customer_id).delete()
            ProductAggregateTrend.query.filter_by(customer_id=customer_id).delete()
            ProductCatalog.query.filter_by(customer_id=customer_id).delete()
        
        # 13. Finally, delete the customer
        db.session.delete(customer)
        db.session.commit()
        
        return {
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'summary': summary,
            'action': 'deleted'
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'customer_id': customer_id,
            'customer_name': customer.customer_name,
            'error': str(e),
            'action': 'failed'
        }


def main():
    parser = argparse.ArgumentParser(description='Remove customers with zero accounts')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Preview what will be deleted without actually deleting')
    parser.add_argument('--customer-ids', type=str,
                        help='Comma-separated list of customer IDs to remove (e.g., 7,11,12)')
    parser.add_argument('--test-only', action='store_true',
                        help='Only remove test/onboarding customers')
    parser.add_argument('--force', action='store_true',
                        help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    # Parse customer IDs if provided
    customer_ids = None
    if args.customer_ids:
        try:
            customer_ids = [int(id.strip()) for id in args.customer_ids.split(',')]
        except ValueError:
            print("❌ ERROR: Invalid customer IDs format. Use comma-separated integers (e.g., 7,11,12)")
            sys.exit(1)
    
    with app.app_context():
        # Get customers to delete
        customers_to_delete = get_customers_with_no_accounts(
            test_only=args.test_only,
            customer_ids=customer_ids
        )
        
        if not customers_to_delete:
            print("✅ No customers found with zero accounts")
            if args.test_only:
                print("   (with test-only filter)")
            if customer_ids:
                print(f"   (with customer IDs filter: {customer_ids})")
            return
        
        print("=" * 70)
        print("CUSTOMERS WITH ZERO ACCOUNTS")
        print("=" * 70)
        print(f"\nFound {len(customers_to_delete)} customer(s) to remove:\n")
        
        # Preview
        for customer in customers_to_delete:
            summary = get_customer_data_summary(customer.customer_id)
            print(f"Customer ID: {customer.customer_id}")
            print(f"  Name: {customer.customer_name}")
            print(f"  Email: {customer.email or 'N/A'}")
            print(f"  Domain: {customer.domain or 'N/A'}")
            print(f"  Data to delete:")
            print(f"    - Users: {summary['users']}")
            print(f"    - Configs: {summary['configs']}")
            print(f"    - KPI Uploads: {summary['kpi_uploads']}")
            print(f"    - KPIs: {summary['kpis']}")
            print(f"    - Products: {summary['products']}")
            print(f"    - Account Notes: {summary['account_notes']}")
            print(f"    - Health Trends: {summary['health_trends']}")
            print(f"    - Playbook data: {summary['playbook_triggers']} triggers, "
                  f"{summary['playbook_executions']} executions, {summary['playbook_reports']} reports")
            print()
        
        if args.dry_run:
            print("🔍 DRY RUN MODE - No data will be deleted")
            print("   Run without --dry-run to actually delete")
            return
        
        # Confirmation
        if not args.force:
            print("⚠️  WARNING: This will permanently delete the above customers and all their data!")
            response = input("Type 'yes' to confirm: ")
            if response.lower() != 'yes':
                print("❌ Cancelled")
                return
        
        # Delete customers
        print("\n" + "=" * 70)
        print("DELETING CUSTOMERS...")
        print("=" * 70 + "\n")
        
        results = []
        for customer in customers_to_delete:
            result = delete_customer_data(customer.customer_id, dry_run=False)
            results.append(result)
            
            if result.get('error'):
                print(f"❌ Customer {result['customer_id']} ({result['customer_name']}): {result['error']}")
            else:
                print(f"✅ Deleted Customer {result['customer_id']} ({result['customer_name']})")
                summary = result['summary']
                print(f"   Removed: {summary['users']} users, {summary['kpi_uploads']} uploads, "
                      f"{summary['kpis']} KPIs, {summary['products']} products")
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        successful = sum(1 for r in results if r.get('action') == 'deleted')
        failed = sum(1 for r in results if r.get('error'))
        print(f"✅ Successfully deleted: {successful}")
        if failed > 0:
            print(f"❌ Failed: {failed}")
        print()


if __name__ == '__main__':
    main()
