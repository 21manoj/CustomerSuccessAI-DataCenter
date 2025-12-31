#!/usr/bin/env python3
"""
Fix duplicate uploads for Summit Analytics Group
"""
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from extensions import db
from models import Account, KPI, KPIUpload

basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///kpi_dashboard.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def fix_duplicate_uploads():
    """Fix duplicate uploads for Summit Analytics Group"""
    print("\n" + "="*70)
    print("FIXING DUPLICATE UPLOADS")
    print("="*70)
    
    with app.app_context():
        customer_id = 2
        problem_account = Account.query.filter_by(customer_id=customer_id, account_name='Summit Analytics Group').first()
        
        if not problem_account:
            print("❌ Account not found")
            return
        
        # Get all uploads for this account
        uploads = KPIUpload.query.filter_by(customer_id=customer_id, account_id=problem_account.account_id).all()
        
        # Group by filename
        from collections import defaultdict
        uploads_by_filename = defaultdict(list)
        for upload in uploads:
            uploads_by_filename[upload.original_filename].append(upload)
        
        # Find duplicates
        duplicates_to_delete = []
        for filename, upload_list in uploads_by_filename.items():
            if len(upload_list) > 1:
                # Keep the first upload, mark others for deletion
                upload_list.sort(key=lambda x: x.upload_id)  # Sort by upload_id
                print(f"\n📁 {filename}: {len(upload_list)} uploads")
                print(f"   Keeping upload ID: {upload_list[0].upload_id}")
                for dup_upload in upload_list[1:]:
                    print(f"   Deleting upload ID: {dup_upload.upload_id}")
                    duplicates_to_delete.append(dup_upload)
        
        if not duplicates_to_delete:
            print("\n✅ No duplicates found")
            return
        
        # Delete KPIs from duplicate uploads first
        duplicate_upload_ids = [u.upload_id for u in duplicates_to_delete]
        kpis_to_delete = KPI.query.filter(KPI.upload_id.in_(duplicate_upload_ids)).all()
        
        print(f"\n🗑️  Deleting {len(kpis_to_delete)} KPIs from duplicate uploads...")
        for kpi in kpis_to_delete:
            db.session.delete(kpi)
        
        # Delete duplicate uploads
        print(f"🗑️  Deleting {len(duplicates_to_delete)} duplicate uploads...")
        for upload in duplicates_to_delete:
            db.session.delete(upload)
        
        db.session.commit()
        
        # Verify
        remaining_uploads = KPIUpload.query.filter_by(customer_id=customer_id, account_id=problem_account.account_id).all()
        remaining_kpis = KPI.query.filter(KPI.upload_id.in_([u.upload_id for u in remaining_uploads])).all()
        
        print(f"\n✅ Fixed!")
        print(f"   Remaining uploads: {len(remaining_uploads)}")
        print(f"   Remaining KPIs: {len(remaining_kpis)}")
        print(f"   Expected KPIs: 217 (31 KPIs × 7 months)")

if __name__ == "__main__":
    fix_duplicate_uploads()



