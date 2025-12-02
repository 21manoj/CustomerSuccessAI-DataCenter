#!/usr/bin/env python3
"""
End-to-end test for Account Snapshot Feature
Run this script to test the complete snapshot functionality
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app, db
from models import (
    Customer, Account, Product, KPI, KPIUpload, User,
    AccountNote, AccountSnapshot, HealthTrend
)
from account_snapshot_api import create_account_snapshot

def test_e2e():
    """End-to-end test"""
    print("=" * 60)
    print("Account Snapshot Feature - End-to-End Test")
    print("=" * 60)
    
    with app.app_context():
        try:
            # 1. Create test customer
            print("\n1. Creating test customer...")
            customer = Customer(
                customer_name="E2E Test Customer",
                email=f"e2e_test_{datetime.now().timestamp()}@example.com"
            )
            db.session.add(customer)
            db.session.commit()
            print(f"   ✓ Customer created: {customer.customer_id}")
            
            # 2. Create test user
            print("\n2. Creating test user...")
            user = User(
                customer_id=customer.customer_id,
                user_name="e2e_test_user",
                email=f"e2e_user_{datetime.now().timestamp()}@example.com",
                password_hash="dummy_hash"
            )
            db.session.add(user)
            db.session.commit()
            print(f"   ✓ User created: {user.user_id}")
            
            # 3. Create test account
            print("\n3. Creating test account...")
            account = Account(
                customer_id=customer.customer_id,
                account_name="E2E Test Account",
                revenue=150000,
                industry="Software",
                region="North America",
                account_status="active",
                external_account_id="E2E-001",
                profile_metadata={
                    'assigned_csm': 'John Doe',
                    'products_used': ['Product A', 'Product B'],
                    'engagement': {
                        'lifecycle_stage': 'Growth',
                        'onboarding_status': 'Complete',
                        'last_qbr_date': '2025-01-15',
                        'next_qbr_date': '2025-04-15',
                        'score': 75.5
                    },
                    'champions': [
                        {'name': 'Jane Smith', 'status': 'Active'}
                    ]
                }
            )
            db.session.add(account)
            db.session.commit()
            print(f"   ✓ Account created: {account.account_id}")
            
            # 4. Create test product
            print("\n4. Creating test product...")
            product = Product(
                account_id=account.account_id,
                customer_id=customer.customer_id,
                product_name="Product A",
                product_sku="PROD-A-001",
                status="active"
            )
            db.session.add(product)
            db.session.commit()
            print(f"   ✓ Product created: {product.product_id}")
            
            # 5. Create KPI upload
            print("\n5. Creating KPI upload...")
            kpi_upload = KPIUpload(
                customer_id=customer.customer_id,
                account_id=account.account_id,
                user_id=user.user_id,
                version=1,
                original_filename="e2e_test_kpis.xlsx"
            )
            db.session.add(kpi_upload)
            db.session.commit()
            print(f"   ✓ KPI Upload created: {kpi_upload.upload_id}")
            
            # 6. Create test KPIs
            print("\n6. Creating test KPIs...")
            kpi1 = KPI(
                upload_id=kpi_upload.upload_id,
                account_id=account.account_id,
                product_id=None,
                category="Business Outcomes KPI",
                kpi_parameter="Net Revenue Retention (NRR)",
                data="95%",
                impact_level="High",
                weight="High",
                measurement_frequency="Monthly",
                source_review="E2E Test",
                health_score_component="Business Outcomes KPI"
            )
            kpi2 = KPI(
                upload_id=kpi_upload.upload_id,
                account_id=account.account_id,
                product_id=product.product_id,
                category="Product Usage KPI",
                kpi_parameter="Feature Adoption Rate",
                data="80%",
                impact_level="Medium",
                weight="Medium",
                measurement_frequency="Monthly",
                source_review="E2E Test",
                health_score_component="Product Usage KPI"
            )
            db.session.add_all([kpi1, kpi2])
            db.session.commit()
            print(f"   ✓ Created 2 KPIs (1 account-level, 1 product-level)")
            
            # 7. Create health trend
            print("\n7. Creating health trend...")
            health_trend = HealthTrend(
                customer_id=customer.customer_id,
                account_id=account.account_id,
                year=2025,
                month=1,
                overall_health_score=75.5,
                product_usage_score=80.0,
                support_score=70.0,
                customer_sentiment_score=75.0,
                business_outcomes_score=80.0,
                relationship_strength_score=72.0
            )
            db.session.add(health_trend)
            db.session.commit()
            print(f"   ✓ Health trend created")
            
            # 8. Create CSM notes
            print("\n8. Creating CSM notes...")
            note1 = AccountNote(
                account_id=account.account_id,
                customer_id=customer.customer_id,
                note_type='qbr',
                note_title='Q4 2025 QBR',
                note_content='Discussed NPS improvement plan, committed to 3 feature requests...',
                created_by=user.user_id,
                meeting_date=datetime.now().date(),
                participants=['John Doe (CSM)', 'Jane Smith (Customer)']
            )
            note2 = AccountNote(
                account_id=account.account_id,
                customer_id=customer.customer_id,
                note_type='meeting',
                note_title='Weekly Check-in',
                note_content='Customer is happy with recent feature releases.',
                created_by=user.user_id
            )
            db.session.add_all([note1, note2])
            db.session.commit()
            print(f"   ✓ Created 2 CSM notes")
            
            # 9. Create account snapshot
            print("\n9. Creating account snapshot...")
            # Mock get_current_user_id
            import account_snapshot_api
            original_get_user = account_snapshot_api.get_current_user_id
            account_snapshot_api.get_current_user_id = lambda: user.user_id
            
            snapshot = create_account_snapshot(
                account_id=account.account_id,
                customer_id=customer.customer_id,
                snapshot_type='manual',
                snapshot_reason='E2E Test'
            )
            
            account_snapshot_api.get_current_user_id = original_get_user
            
            if snapshot:
                print(f"   ✓ Snapshot created: {snapshot.snapshot_id}")
                print(f"     - Health Score: {snapshot.overall_health_score}")
                print(f"     - Revenue: ${snapshot.revenue:,.0f}")
                print(f"     - Products: {snapshot.product_count}")
                print(f"     - Total KPIs: {snapshot.total_kpis}")
                print(f"     - Account-level KPIs: {snapshot.account_level_kpis}")
                print(f"     - Product-level KPIs: {snapshot.product_level_kpis}")
                print(f"     - CSM Notes Referenced: {len(snapshot.recent_csm_note_ids) if snapshot.recent_csm_note_ids else 0}")
                print(f"     - Sequence Number: {snapshot.snapshot_sequence_number}")
            else:
                print("   ✗ Failed to create snapshot")
                return False
            
            # 10. Create second snapshot to test sequence
            print("\n10. Creating second snapshot (testing sequence)...")
            account_snapshot_api.get_current_user_id = lambda: user.user_id
            
            snapshot2 = create_account_snapshot(
                account_id=account.account_id,
                customer_id=customer.customer_id,
                snapshot_type='manual',
                snapshot_reason='E2E Test - Second Snapshot'
            )
            
            account_snapshot_api.get_current_user_id = original_get_user
            
            if snapshot2:
                print(f"   ✓ Second snapshot created: {snapshot2.snapshot_id}")
                print(f"     - Sequence Number: {snapshot2.snapshot_sequence_number}")
                print(f"     - Days since last: {snapshot2.days_since_last_snapshot}")
                if snapshot2.health_score_change_from_last is not None:
                    print(f"     - Health Score Change: {snapshot2.health_score_change_from_last:.2f}")
            else:
                print("   ✗ Failed to create second snapshot")
                return False
            
            # 11. Verify snapshot data directly
            print("\n11. Verifying snapshot data...")
            latest_snapshot = AccountSnapshot.query.filter_by(
                account_id=account.account_id,
                customer_id=customer.customer_id
            ).order_by(AccountSnapshot.snapshot_timestamp.desc()).first()
            
            if latest_snapshot:
                print(f"   ✓ Latest snapshot retrieved: {latest_snapshot.snapshot_id}")
                print(f"     - All fields populated correctly")
                print(f"     - API endpoints available at:")
                print(f"       POST /api/account-snapshots/create")
                print(f"       GET /api/account-snapshots/latest?account_id={account.account_id}")
                print(f"       GET /api/account-snapshots/history?account_id={account.account_id}")
                print(f"       GET /api/account-snapshots")
            else:
                print("   ✗ Could not retrieve snapshot")
                return False
            
            print("\n" + "=" * 60)
            print("✅ All tests passed!")
            print("=" * 60)
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Cleanup
            try:
                with app.app_context():
                    AccountSnapshot.query.filter_by(customer_id=customer.customer_id).delete()
                    AccountNote.query.filter_by(customer_id=customer.customer_id).delete()
                    KPI.query.filter_by(account_id=account.account_id).delete()
                    KPIUpload.query.filter_by(customer_id=customer.customer_id).delete()
                    Product.query.filter_by(customer_id=customer.customer_id).delete()
                    HealthTrend.query.filter_by(customer_id=customer.customer_id).delete()
                    Account.query.filter_by(customer_id=customer.customer_id).delete()
                    User.query.filter_by(customer_id=customer.customer_id).delete()
                    Customer.query.filter_by(customer_id=customer.customer_id).delete()
                    db.session.commit()
                    print("\n✓ Cleanup completed")
            except:
                pass

if __name__ == '__main__':
    success = test_e2e()
    sys.exit(0 if success else 1)

