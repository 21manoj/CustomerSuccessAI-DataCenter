#!/usr/bin/env python3
"""
Delete all Data Center data from the database
"""
import sys
import os
from dotenv import load_dotenv

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from extensions import db
from models import Customer, User, Account, KPI, KPIUpload, Product, HealthTrend, KPITimeSeries, KPIReferenceRange, PlaybookTrigger, PlaybookExecution, PlaybookReport, AccountSnapshot, AccountNote

# Load environment variables
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path=env_path)

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///kpi_dashboard.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def delete_dc_data():
    """Delete all Data Center customer data"""
    print("\n" + "="*70)
    print("DELETING ALL DATA CENTER DATA")
    print("="*70)
    
    with app.app_context():
        # Find DC customer (by email or name)
        dc_customer = Customer.query.filter(
            (Customer.email == 'dc@example.com') | 
            (Customer.customer_name.ilike('%data center%'))
        ).first()
        
        if not dc_customer:
            print("❌ No Data Center customer found in database")
            return
        
        customer_id = dc_customer.customer_id
        print(f"\n📋 Found DC Customer: {dc_customer.customer_name} (ID: {customer_id})")
        
        # Get counts before deletion
        accounts_count = Account.query.filter_by(customer_id=customer_id).count()
        products_count = Product.query.filter_by(customer_id=customer_id).count()
        upload_ids = [u.upload_id for u in KPIUpload.query.filter_by(customer_id=customer_id).all()]
        kpis_count = KPI.query.filter(KPI.upload_id.in_(upload_ids)).count() if upload_ids else 0
        uploads_count = len(upload_ids)
        health_trends_count = HealthTrend.query.filter_by(customer_id=customer_id).count()
        time_series_count = KPITimeSeries.query.filter_by(customer_id=customer_id).count()
        ref_ranges_count = KPIReferenceRange.query.filter_by(customer_id=customer_id).count()
        triggers_count = PlaybookTrigger.query.filter_by(customer_id=customer_id).count()
        executions_count = PlaybookExecution.query.filter_by(customer_id=customer_id).count()
        reports_count = PlaybookReport.query.filter_by(customer_id=customer_id).count()
        snapshots_count = AccountSnapshot.query.filter_by(customer_id=customer_id).count()
        notes_count = AccountNote.query.filter_by(customer_id=customer_id).count()
        
        print(f"\n📊 Current Data Counts:")
        print(f"   - Accounts: {accounts_count}")
        print(f"   - Products: {products_count}")
        print(f"   - KPI Uploads: {uploads_count}")
        print(f"   - KPIs: {kpis_count}")
        print(f"   - Health Trends: {health_trends_count}")
        print(f"   - Time Series: {time_series_count}")
        print(f"   - Reference Ranges: {ref_ranges_count}")
        print(f"   - Playbook Triggers: {triggers_count}")
        print(f"   - Playbook Executions: {executions_count}")
        print(f"   - Playbook Reports: {reports_count}")
        print(f"   - Account Snapshots: {snapshots_count}")
        print(f"   - Account Notes: {notes_count}")
        
        # Confirm deletion (skip if --force flag is provided)
        import sys
        force = '--force' in sys.argv
        if not force:
            print("\n⚠️  WARNING: This will delete ALL data for this customer!")
            response = input("Type 'DELETE' to confirm: ")
            if response != 'DELETE':
                print("❌ Deletion cancelled")
                return
        else:
            print("\n⚠️  WARNING: Deleting ALL data for this customer (--force mode)")
        
        print("\n🗑️  Deleting data...")
        
        try:
            # Delete in correct order (respecting foreign keys)
            # 1. Delete KPIs first
            if upload_ids:
                KPI.query.filter(KPI.upload_id.in_(upload_ids)).delete(synchronize_session=False)
                print(f"   ✅ Deleted {kpis_count} KPIs")
            
            # 2. Delete KPI Uploads
            KPIUpload.query.filter_by(customer_id=customer_id).delete()
            print(f"   ✅ Deleted {uploads_count} KPI Uploads")
            
            # 3. Delete Products
            Product.query.filter_by(customer_id=customer_id).delete()
            print(f"   ✅ Deleted {products_count} Products")
            
            # 4. Delete Accounts
            Account.query.filter_by(customer_id=customer_id).delete()
            print(f"   ✅ Deleted {accounts_count} Accounts")
            
            # 5. Delete Health Trends
            HealthTrend.query.filter_by(customer_id=customer_id).delete()
            print(f"   ✅ Deleted {health_trends_count} Health Trends")
            
            # 6. Delete Time Series
            KPITimeSeries.query.filter_by(customer_id=customer_id).delete()
            print(f"   ✅ Deleted {time_series_count} Time Series")
            
            # 7. Delete Reference Ranges
            KPIReferenceRange.query.filter_by(customer_id=customer_id).delete()
            print(f"   ✅ Deleted {ref_ranges_count} Reference Ranges")
            
            # 8. Delete Playbook data
            PlaybookReport.query.filter_by(customer_id=customer_id).delete()
            print(f"   ✅ Deleted {reports_count} Playbook Reports")
            
            PlaybookExecution.query.filter_by(customer_id=customer_id).delete()
            print(f"   ✅ Deleted {executions_count} Playbook Executions")
            
            PlaybookTrigger.query.filter_by(customer_id=customer_id).delete()
            print(f"   ✅ Deleted {triggers_count} Playbook Triggers")
            
            # 9. Delete Account Snapshots
            AccountSnapshot.query.filter_by(customer_id=customer_id).delete()
            print(f"   ✅ Deleted {snapshots_count} Account Snapshots")
            
            # 10. Delete Account Notes
            AccountNote.query.filter_by(customer_id=customer_id).delete()
            print(f"   ✅ Deleted {notes_count} Account Notes")
            
            # Commit all deletions
            db.session.commit()
            
            print("\n" + "="*70)
            print("✅ ALL DATA DELETED SUCCESSFULLY")
            print("="*70)
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error deleting data: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    delete_dc_data()

