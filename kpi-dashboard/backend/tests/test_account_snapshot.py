#!/usr/bin/env python3
"""
Tests for Account Snapshot Feature
"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app, db
from models import (
    Customer, Account, Product, KPI, KPIUpload, User,
    AccountNote, AccountSnapshot, HealthTrend, PlaybookExecution, PlaybookReport
)
from account_snapshot_api import create_account_snapshot
from health_score_engine import HealthScoreEngine


@pytest.fixture(scope='module')
def test_client():
    """Create test client and database"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
            with app.app_context():
                # Create all tables
                db.create_all()
                
                # Create test customer
                import uuid
                unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
                customer = Customer(
                    customer_name="Test Customer",
                    email=unique_email
                )
                db.session.add(customer)
                db.session.commit()
            
            # Create test user
            user = User(
                customer_id=customer.customer_id,
                user_name="testuser",
                email="testuser@example.com",
                password_hash="dummy_hash"
            )
            db.session.add(user)
            db.session.commit()
            
            # Create test account
            account = Account(
                customer_id=customer.customer_id,
                account_name="Test Account",
                revenue=100000,
                industry="Software",
                region="North America",
                account_status="active",
                external_account_id="TEST-001",
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
            
            # Create test product
            product = Product(
                account_id=account.account_id,
                customer_id=customer.customer_id,
                product_name="Product A",
                product_sku="PROD-A-001",
                status="active"
            )
            db.session.add(product)
            db.session.commit()
            
            # Create KPI upload
            kpi_upload = KPIUpload(
                customer_id=customer.customer_id,
                account_id=account.account_id,
                user_id=user.user_id,
                original_filename="test_kpis.xlsx"
            )
            db.session.add(kpi_upload)
            db.session.commit()
            
            # Create test KPIs
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
                source_review="Test Seed",
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
                source_review="Test Seed",
                health_score_component="Product Usage KPI"
            )
            db.session.add_all([kpi1, kpi2])
            db.session.commit()
            
            # Create health trend
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
            
            yield client, customer, account, user
            
            # Cleanup
            db.drop_all()


def test_create_account_note(test_client):
    """Test creating an account note"""
    client, customer, account, user = test_client
    
    with app.app_context():
        note = AccountNote(
            account_id=account.account_id,
            customer_id=customer.customer_id,
            note_type='qbr',
            note_title='Q4 2025 QBR',
            note_content='Discussed NPS improvement plan, committed to 3 feature requests...',
            created_by=user.user_id,
            meeting_date=datetime.now().date(),
            participants=['John Doe (CSM)', 'Jane Smith (Customer)']
        )
        db.session.add(note)
        db.session.commit()
        
        assert note.note_id is not None
        assert note.account_id == account.account_id
        assert note.note_type == 'qbr'
        assert 'NPS' in note.note_content
        
        # Verify retrieval
        retrieved = AccountNote.query.filter_by(note_id=note.note_id).first()
        assert retrieved is not None
        assert retrieved.note_content == note.note_content


def test_create_account_snapshot(test_client):
    """Test creating an account snapshot"""
    client, customer, account, user = test_client
    
    with app.app_context():
        # Mock get_current_user_id
        import account_snapshot_api
        original_get_user = account_snapshot_api.get_current_user_id
        account_snapshot_api.get_current_user_id = lambda: user.user_id
        
        snapshot = create_account_snapshot(
            account_id=account.account_id,
            customer_id=customer.customer_id,
            snapshot_type='manual',
            snapshot_reason='Test snapshot'
        )
        
        # Restore original function
        account_snapshot_api.get_current_user_id = original_get_user
        
        assert snapshot is not None
        assert snapshot.account_id == account.account_id
        assert snapshot.customer_id == customer.customer_id
        assert snapshot.snapshot_type == 'manual'
        assert snapshot.overall_health_score == 75.5  # From HealthTrend
        assert snapshot.revenue == 100000
        assert snapshot.products_used == ['Product A', 'Product B']
        assert snapshot.assigned_csm == 'John Doe'
        assert snapshot.total_kpis == 2
        assert snapshot.account_level_kpis == 1
        assert snapshot.product_level_kpis == 1
        assert snapshot.snapshot_sequence_number == 1


def test_snapshot_sequence_number(test_client):
    """Test that snapshot sequence numbers increment correctly"""
    client, customer, account, user = test_client
    
    with app.app_context():
        import account_snapshot_api
        original_get_user = account_snapshot_api.get_current_user_id
        account_snapshot_api.get_current_user_id = lambda: user.user_id
        
        # Create first snapshot
        snapshot1 = create_account_snapshot(
            account_id=account.account_id,
            customer_id=customer.customer_id,
            snapshot_type='manual'
        )
        
        assert snapshot1.snapshot_sequence_number == 1
        
        # Create second snapshot
        snapshot2 = create_account_snapshot(
            account_id=account.account_id,
            customer_id=customer.customer_id,
            snapshot_type='manual'
        )
        
        assert snapshot2.snapshot_sequence_number == 2
        
        # Restore original function
        account_snapshot_api.get_current_user_id = original_get_user


def test_snapshot_references_csm_notes(test_client):
    """Test that snapshot includes references to CSM notes"""
    client, customer, account, user = test_client
    
    with app.app_context():
        # Create CSM notes
        note1 = AccountNote(
            account_id=account.account_id,
            customer_id=customer.customer_id,
            note_type='meeting',
            note_content='Meeting note 1',
            created_by=user.user_id
        )
        note2 = AccountNote(
            account_id=account.account_id,
            customer_id=customer.customer_id,
            note_type='qbr',
            note_content='QBR note 2',
            created_by=user.user_id
        )
        db.session.add_all([note1, note2])
        db.session.commit()
        
        # Create snapshot
        import account_snapshot_api
        original_get_user = account_snapshot_api.get_current_user_id
        account_snapshot_api.get_current_user_id = lambda: user.user_id
        
        snapshot = create_account_snapshot(
            account_id=account.account_id,
            customer_id=customer.customer_id,
            snapshot_type='manual'
        )
        
        account_snapshot_api.get_current_user_id = original_get_user
        
        # Verify snapshot includes note references
        assert snapshot.recent_csm_note_ids is not None
        assert len(snapshot.recent_csm_note_ids) == 2
        assert note2.note_id in snapshot.recent_csm_note_ids  # Most recent first
        assert note1.note_id in snapshot.recent_csm_note_ids


def test_snapshot_health_score_trend(test_client):
    """Test health score trend calculation"""
    client, customer, account, user = test_client
    
    with app.app_context():
        import account_snapshot_api
        original_get_user = account_snapshot_api.get_current_user_id
        account_snapshot_api.get_current_user_id = lambda: user.user_id
        
        # Create first snapshot with lower health score
        health_trend1 = HealthTrend(
            customer_id=customer.customer_id,
            account_id=account.account_id,
            year=2025,
            month=1,
            overall_health_score=70.0
        )
        db.session.add(health_trend1)
        db.session.commit()
        
        snapshot1 = create_account_snapshot(
            account_id=account.account_id,
            customer_id=customer.customer_id,
            snapshot_type='manual'
        )
        
        # Update health trend to higher score
        health_trend1.overall_health_score = 80.0
        db.session.commit()
        
        snapshot2 = create_account_snapshot(
            account_id=account.account_id,
            customer_id=customer.customer_id,
            snapshot_type='manual'
        )
        
        account_snapshot_api.get_current_user_id = original_get_user
        
        # Verify trend is calculated
        assert snapshot2.health_score_trend in ['improving', 'declining', 'stable']
        assert snapshot2.health_score_change_from_last is not None


def test_snapshot_api_endpoint_create(test_client):
    """Test the create snapshot API endpoint"""
    client, customer, account, user = test_client
    
    with app.app_context():
        # Simulate login
        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['customer_id'] = customer.customer_id
        
        # Create snapshot via API
        response = client.post('/api/account-snapshots/create', json={
            'account_id': account.account_id,
            'snapshot_type': 'manual',
            'reason': 'Test API'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['snapshots']) == 1
        assert data['snapshots'][0]['account_id'] == account.account_id


def test_snapshot_api_endpoint_get_latest(test_client):
    """Test getting latest snapshot via API"""
    client, customer, account, user = test_client
    
    with app.app_context():
        # Create snapshot first
        import account_snapshot_api
        original_get_user = account_snapshot_api.get_current_user_id
        account_snapshot_api.get_current_user_id = lambda: user.user_id
        
        snapshot = create_account_snapshot(
            account_id=account.account_id,
            customer_id=customer.customer_id,
            snapshot_type='manual'
        )
        
        account_snapshot_api.get_current_user_id = original_get_user
        
        # Simulate login
        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['customer_id'] = customer.customer_id
        
        # Get latest snapshot
        response = client.get(f'/api/account-snapshots/latest?account_id={account.account_id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['snapshot']['account_id'] == account.account_id
        assert data['snapshot']['overall_health_score'] == 75.5


def test_snapshot_api_endpoint_history(test_client):
    """Test getting snapshot history via API"""
    client, customer, account, user = test_client
    
    with app.app_context():
        # Create multiple snapshots
        import account_snapshot_api
        original_get_user = account_snapshot_api.get_current_user_id
        account_snapshot_api.get_current_user_id = lambda: user.user_id
        
        snapshot1 = create_account_snapshot(
            account_id=account.account_id,
            customer_id=customer.customer_id,
            snapshot_type='manual'
        )
        
        snapshot2 = create_account_snapshot(
            account_id=account.account_id,
            customer_id=customer.customer_id,
            snapshot_type='manual'
        )
        
        account_snapshot_api.get_current_user_id = original_get_user
        
        # Simulate login
        with client.session_transaction() as sess:
            sess['user_id'] = user.user_id
            sess['customer_id'] = customer.customer_id
        
        # Get history
        response = client.get(f'/api/account-snapshots/history?account_id={account.account_id}&months=3')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['history']) >= 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

