#!/usr/bin/env python3
"""
Delete Customers 30-40 and Verify Deletion
==========================================

This script deletes customers with IDs between 30 and 40 (inclusive),
including all related data and customer directories.

Usage:
    python3 delete_customers_30_40.py [--dry-run] [--verify-only]

Options:
    --dry-run: Show what would be deleted without actually deleting
    --verify-only: Only verify if customers exist, don't delete
"""

import sys
import argparse
from pathlib import Path
from sqlalchemy import func
from datetime import datetime

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app_v3_minimal import app
from extensions import db
from models import (
    Customer, User, Account, Product, CustomerConfig, KPIUpload, KPI,
    HealthTrend, KPITimeSeries, KPIReferenceRange, FeatureToggle,
    PlaybookTrigger, PlaybookExecution, PlaybookReport, CustomerWorkflowConfig,
    ActivityLog, AccountSnapshot, QueryAudit, DC2SKPI
)

# Try to import optional models
try:
    from models import AccountNote
except ImportError:
    AccountNote = None
from onboarding_api import get_customer_directory


def get_customer_summary(customer_ids):
    """Get summary of data for customers before deletion"""
    with app.app_context():
        summary = {}
        for customer_id in customer_ids:
            customer = Customer.query.filter_by(customer_id=customer_id).first()
            if not customer:
                summary[customer_id] = None
                continue
            
            summary[customer_id] = {
                'customer': customer,
                'users': User.query.filter_by(customer_id=customer_id).count(),
                'accounts': Account.query.filter_by(customer_id=customer_id).count(),
                'products': Product.query.filter_by(customer_id=customer_id).count(),
                'config': CustomerConfig.query.filter_by(customer_id=customer_id).count(),
                'kpi_uploads': KPIUpload.query.filter_by(customer_id=customer_id).count(),
                'kpis': KPI.query.join(KPIUpload).filter(KPIUpload.customer_id == customer_id).count(),
                'dc2s_kpis': DC2SKPI.query.join(Account).filter(Account.customer_id == customer_id).count() if hasattr(DC2SKPI, 'account_id') else 0,
                'health_trends': HealthTrend.query.filter_by(customer_id=customer_id).count(),
                'kpi_time_series': KPITimeSeries.query.filter_by(customer_id=customer_id).count(),
                'kpi_ref_ranges': KPIReferenceRange.query.filter_by(customer_id=customer_id).count(),
                'feature_toggles': FeatureToggle.query.filter_by(customer_id=customer_id).count(),
                'playbook_triggers': PlaybookTrigger.query.filter_by(customer_id=customer_id).count(),
                'playbook_executions': PlaybookExecution.query.filter_by(customer_id=customer_id).count(),
                'playbook_reports': PlaybookReport.query.filter_by(customer_id=customer_id).count(),
                'workflow_configs': CustomerWorkflowConfig.query.filter_by(customer_id=customer_id).count(),
                'activity_logs': ActivityLog.query.filter_by(customer_id=customer_id).count(),
                'account_snapshots': AccountSnapshot.query.filter_by(customer_id=customer_id).count(),
                'account_notes': AccountNote.query.filter_by(customer_id=customer_id).count() if AccountNote else 0,
                'rag_queries': QueryAudit.query.filter_by(customer_id=customer_id).count(),
            }
        return summary


def delete_customer_data(customer_id, dry_run=False):
    """Delete all data for a customer in the correct order"""
    deleted_counts = {
        'customer_id': customer_id,
        'rag_queries': 0,
        'account_notes': 0,
        'account_snapshots': 0,
        'activity_logs': 0,
        'playbook_reports': 0,
        'playbook_executions': 0,
        'playbook_triggers': 0,
        'workflow_configs': 0,
        'feature_toggles': 0,
        'kpi_ref_ranges': 0,
        'kpi_time_series': 0,
        'health_trends': 0,
        'dc2s_kpis': 0,
        'kpis': 0,
        'kpi_uploads': 0,
        'products': 0,
        'accounts': 0,
        'users': 0,
        'config': 0,
        'customer': 0,
    }
    
    if dry_run:
        return deleted_counts
    
    try:
        # Get account IDs first (needed for some deletions)
        account_ids = [a.account_id for a in Account.query.filter_by(customer_id=customer_id).all()]
        
        # 1. Delete RAG queries (QueryAudit)
        deleted_counts['rag_queries'] = QueryAudit.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 2. Delete account notes (if model exists)
        if AccountNote:
            deleted_counts['account_notes'] = AccountNote.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 3. Delete account snapshots
        deleted_counts['account_snapshots'] = AccountSnapshot.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 4. Delete activity logs (has CASCADE, but delete explicitly for clarity)
        deleted_counts['activity_logs'] = ActivityLog.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 5. Delete playbook reports (before executions due to FK)
        deleted_counts['playbook_reports'] = PlaybookReport.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 6. Delete playbook executions
        deleted_counts['playbook_executions'] = PlaybookExecution.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 7. Delete playbook triggers
        deleted_counts['playbook_triggers'] = PlaybookTrigger.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 8. Delete workflow configs (has CASCADE)
        deleted_counts['workflow_configs'] = CustomerWorkflowConfig.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 9. Delete feature toggles
        deleted_counts['feature_toggles'] = FeatureToggle.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 10. Delete KPI reference ranges (has CASCADE)
        deleted_counts['kpi_ref_ranges'] = KPIReferenceRange.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 11. Delete KPI time series
        deleted_counts['kpi_time_series'] = KPITimeSeries.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 12. Delete health trends
        deleted_counts['health_trends'] = HealthTrend.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 13. Delete DC2SKPI records
        if account_ids:
            deleted_counts['dc2s_kpis'] = DC2SKPI.query.filter(DC2SKPI.account_id.in_(account_ids)).delete(synchronize_session=False)
        
        # 14. Delete KPIs (via upload_ids)
        upload_ids = [u.upload_id for u in KPIUpload.query.filter_by(customer_id=customer_id).all()]
        if upload_ids:
            deleted_counts['kpis'] = KPI.query.filter(KPI.upload_id.in_(upload_ids)).delete(synchronize_session=False)
        
        # 15. Delete KPI uploads
        deleted_counts['kpi_uploads'] = KPIUpload.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 16. Delete products
        deleted_counts['products'] = Product.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 17. Delete accounts
        deleted_counts['accounts'] = Account.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 18. Delete users
        deleted_counts['users'] = User.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 19. Delete customer config
        deleted_counts['config'] = CustomerConfig.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        # 20. Delete customer (last)
        deleted_counts['customer'] = Customer.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Failed to delete customer {customer_id}: {str(e)}")
    
    return deleted_counts


def delete_customer_directory(customer_id, dry_run=False):
    """Delete customer directory from file system"""
    deleted_dirs = []
    
    # Try different vertical slugs
    vertical_slugs = ['DC2_S', 'dc2_s', 'DC2S', 'dc2s']
    
    for vertical_slug in vertical_slugs:
        try:
            customer_dir = get_customer_directory(customer_id, vertical_slug=vertical_slug)
            if customer_dir.exists():
                if not dry_run:
                    import shutil
                    shutil.rmtree(customer_dir)
                deleted_dirs.append(str(customer_dir))
        except:
            pass
    
    # Also try direct path check
    backend_dir = Path(__file__).parent
    verticals_dir = backend_dir / "verticals"
    for vertical_slug in vertical_slugs:
        customer_dir = verticals_dir / f"customer{customer_id}-{vertical_slug}"
        if customer_dir.exists():
            if not dry_run:
                import shutil
                shutil.rmtree(customer_dir)
            if str(customer_dir) not in deleted_dirs:
                deleted_dirs.append(str(customer_dir))
    
    return deleted_dirs


def verify_deletion(customer_ids):
    """Verify that customers are actually deleted"""
    with app.app_context():
        results = {}
        for customer_id in customer_ids:
            customer = Customer.query.filter_by(customer_id=customer_id).first()
            user_count = User.query.filter_by(customer_id=customer_id).count()
            account_count = Account.query.filter_by(customer_id=customer_id).count()
            
            # Check directory
            backend_dir = Path(__file__).parent
            verticals_dir = backend_dir / "verticals"
            dir_exists = any(
                (verticals_dir / f"customer{customer_id}-{vs}").exists()
                for vs in ['DC2_S', 'dc2_s', 'DC2S', 'dc2s']
            )
            
            results[customer_id] = {
                'customer_exists': customer is not None,
                'users_exist': user_count > 0,
                'accounts_exist': account_count > 0,
                'directory_exists': dir_exists,
                'fully_deleted': customer is None and user_count == 0 and account_count == 0 and not dir_exists
            }
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Delete customers 30-40 and verify deletion')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--verify-only', action='store_true', help='Only verify if customers exist, don\'t delete')
    args = parser.parse_args()
    
    customer_ids = list(range(30, 41))  # 30 to 40 inclusive
    
    print("="*70)
    print("DELETE CUSTOMERS 30-40")
    print("="*70)
    print(f"Customer IDs: {customer_ids}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'VERIFY ONLY' if args.verify_only else 'DELETE'}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*70)
    print()
    
    with app.app_context():
        # Get summary before deletion
        print("📊 PRE-DELETION SUMMARY")
        print("-" * 70)
        summary = get_customer_summary(customer_ids)
        
        existing_customers = []
        for customer_id, data in summary.items():
            if data is None:
                print(f"  Customer {customer_id}: ❌ Not found")
            else:
                existing_customers.append(customer_id)
                customer = data['customer']
                print(f"  Customer {customer_id}: ✅ {customer.customer_name}")
                print(f"    - Users: {data['users']}")
                print(f"    - Accounts: {data['accounts']}")
                print(f"    - Products: {data['products']}")
                print(f"    - KPI Uploads: {data['kpi_uploads']}")
                print(f"    - KPIs: {data['kpis']}")
                print(f"    - DC2S KPIs: {data['dc2s_kpis']}")
                print(f"    - Health Trends: {data['health_trends']}")
                print(f"    - Playbook Executions: {data['playbook_executions']}")
                print()
        
        if not existing_customers:
            print("✅ No customers found in range 30-40")
            return 0
        
        if args.verify_only:
            print("\n✅ Verification complete (no deletion performed)")
            return 0
        
        if args.dry_run:
            print("\n🔍 DRY RUN - No data will be deleted")
            print("="*70)
            return 0
        
        # Confirm deletion
        print(f"\n⚠️  WARNING: About to delete {len(existing_customers)} customers and all their data!")
        response = input("Type 'DELETE' to confirm: ")
        if response != 'DELETE':
            print("❌ Deletion cancelled")
            return 1
        
        # Delete customers
        print("\n🗑️  DELETING CUSTOMERS")
        print("-" * 70)
        deletion_results = []
        
        for customer_id in existing_customers:
            print(f"\nDeleting Customer {customer_id}...")
            try:
                # Delete database data
                counts = delete_customer_data(customer_id, dry_run=False)
                
                # Delete directory
                deleted_dirs = delete_customer_directory(customer_id, dry_run=False)
                
                deletion_results.append({
                    'customer_id': customer_id,
                    'success': True,
                    'counts': counts,
                    'directories': deleted_dirs
                })
                
                print(f"  ✅ Customer {customer_id} deleted")
                print(f"    - Database records deleted: {sum(v for k, v in counts.items() if k != 'customer_id')}")
                if deleted_dirs:
                    print(f"    - Directories deleted: {', '.join(deleted_dirs)}")
                
            except Exception as e:
                deletion_results.append({
                    'customer_id': customer_id,
                    'success': False,
                    'error': str(e)
                })
                print(f"  ❌ Failed to delete Customer {customer_id}: {e}")
        
        # Verify deletion
        print("\n🔍 VERIFYING DELETION")
        print("-" * 70)
        verification = verify_deletion(customer_ids)
        
        all_deleted = True
        for customer_id, result in verification.items():
            if result['fully_deleted']:
                print(f"  Customer {customer_id}: ✅ Fully deleted")
            else:
                all_deleted = False
                issues = []
                if result['customer_exists']:
                    issues.append("customer record")
                if result['users_exist']:
                    issues.append("users")
                if result['accounts_exist']:
                    issues.append("accounts")
                if result['directory_exists']:
                    issues.append("directory")
                print(f"  Customer {customer_id}: ❌ Still has: {', '.join(issues)}")
        
        print("\n" + "="*70)
        if all_deleted:
            print("✅ ALL CUSTOMERS 30-40 SUCCESSFULLY DELETED AND VERIFIED")
        else:
            print("⚠️  SOME CUSTOMERS MAY NOT BE FULLY DELETED - CHECK ABOVE")
        print("="*70)
        
        return 0 if all_deleted else 1


if __name__ == "__main__":
    sys.exit(main())
