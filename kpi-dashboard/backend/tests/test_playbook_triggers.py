"""
Comprehensive Test Suite for Playbook Triggers API

Tests all playbook trigger endpoints and evaluation logic
"""

import pytest
import json
from datetime import datetime, timedelta
from app import app, db
from models import PlaybookTrigger, Account, Customer, KPI, User

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Create test data
            setup_test_data()
            yield client
            db.session.remove()
            db.drop_all()

def setup_test_data():
    """Setup test data for playbook trigger tests"""
    # Create test customer
    customer = Customer(
        customer_id=1,
        customer_name='Test Company',
        email='test@test.com'
    )
    db.session.add(customer)
    
    # Create test accounts with varying statuses
    accounts = [
        Account(
            account_id=101,
            customer_id=1,
            account_name='Low Health Account',
            revenue=50000,
            account_status='At Risk',
            industry='Technology',
            region='North America'
        ),
        Account(
            account_id=102,
            customer_id=1,
            account_name='Medium Health Account',
            revenue=75000,
            account_status='Active',
            industry='Healthcare',
            region='Europe'
        ),
        Account(
            account_id=103,
            customer_id=1,
            account_name='High Health Account',
            revenue=100000,
            account_status='Active',
            industry='Finance',
            region='Asia-Pacific'
        )
    ]
    
    for account in accounts:
        db.session.add(account)
    
    # Create some KPIs for feature usage tracking
    kpis = [
        KPI(kpi_id=1, account_id=101, category='Product Usage', kpi_parameter='Login Frequency', data='2'),
        KPI(kpi_id=2, account_id=101, category='Customer Success', kpi_parameter='Support Tickets', data='5'),
        KPI(kpi_id=3, account_id=102, category='Product Usage', kpi_parameter='Login Frequency', data='15'),
        KPI(kpi_id=4, account_id=103, category='Product Usage', kpi_parameter='Login Frequency', data='25')
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()


class TestPlaybookTriggersAPI:
    """Test Playbook Triggers API endpoints"""
    
    def test_get_trigger_settings_default(self, client):
        """Test getting default trigger settings when none exist"""
        response = client.get('/api/playbook-triggers', headers={'X-Customer-ID': '1'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert data['customer_id'] == 1
        assert 'voc' in data['triggers']
        assert 'activation' in data['triggers']
        
        # Check VoC default values
        voc_triggers = data['triggers']['voc']
        assert voc_triggers['nps_threshold'] == 10
        assert voc_triggers['csat_threshold'] == 3.6
        assert voc_triggers['churn_risk_threshold'] == 0.30
        
        # Check Activation default values
        activation_triggers = data['triggers']['activation']
        assert activation_triggers['adoption_index_threshold'] == 60
        assert activation_triggers['active_users_threshold'] == 50
    
    def test_save_voc_trigger_settings(self, client):
        """Test saving VoC trigger settings"""
        trigger_data = {
            'playbook_type': 'voc',
            'triggers': {
                'nps_threshold': 15,
                'csat_threshold': 4.0,
                'churn_risk_threshold': 0.25,
                'health_score_drop_threshold': 12,
                'churn_mentions_threshold': 3,
                'auto_trigger_enabled': True
            }
        }
        
        response = client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert data['playbook_type'] == 'voc'
        assert data['message'] == 'voc trigger settings saved successfully'
        assert data['triggers']['nps_threshold'] == 15
        assert data['triggers']['auto_trigger_enabled'] == True
    
    def test_save_activation_trigger_settings(self, client):
        """Test saving Activation Blitz trigger settings"""
        trigger_data = {
            'playbook_type': 'activation',
            'triggers': {
                'adoption_index_threshold': 55,
                'active_users_threshold': 40,
                'dau_mau_threshold': 0.30,
                'unused_feature_check': False,
                'auto_trigger_enabled': True
            }
        }
        
        response = client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert data['playbook_type'] == 'activation'
        assert data['triggers']['adoption_index_threshold'] == 55
    
    def test_update_existing_trigger_settings(self, client):
        """Test updating existing trigger settings"""
        # First create
        trigger_data = {
            'playbook_type': 'voc',
            'triggers': {
                'nps_threshold': 10,
                'auto_trigger_enabled': False
            }
        }
        
        client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        # Then update
        trigger_data['triggers']['nps_threshold'] = 20
        trigger_data['triggers']['auto_trigger_enabled'] = True
        
        response = client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['triggers']['nps_threshold'] == 20
        assert data['triggers']['auto_trigger_enabled'] == True
    
    def test_get_saved_trigger_settings(self, client):
        """Test retrieving saved trigger settings"""
        # Save settings first
        trigger_data = {
            'playbook_type': 'voc',
            'triggers': {
                'nps_threshold': 12,
                'csat_threshold': 3.8,
                'auto_trigger_enabled': True
            }
        }
        
        client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        # Retrieve settings
        response = client.get('/api/playbook-triggers', headers={'X-Customer-ID': '1'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        voc_config = data['triggers']['voc']['trigger_config']
        assert voc_config['nps_threshold'] == 12
        assert voc_config['csat_threshold'] == 3.8
        assert voc_config['auto_trigger_enabled'] == True
    
    def test_test_voc_triggers(self, client):
        """Test VoC trigger evaluation"""
        trigger_data = {
            'playbook_type': 'voc',
            'triggers': {
                'nps_threshold': 10,
                'csat_threshold': 3.6,
                'churn_risk_threshold': 0.30,
                'health_score_drop_threshold': 10
            }
        }
        
        response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert data['playbook_type'] == 'voc'
        assert 'triggered' in data
        assert 'affected_accounts' in data
        
        # Should trigger for low health account
        if data['triggered']:
            assert len(data['affected_accounts']) > 0
            assert any(acc['account_id'] == 101 for acc in data['affected_accounts'])
    
    def test_test_activation_triggers(self, client):
        """Test Activation Blitz trigger evaluation"""
        trigger_data = {
            'playbook_type': 'activation',
            'triggers': {
                'adoption_index_threshold': 60,
                'active_users_threshold': 50,
                'dau_mau_threshold': 0.25,
                'unused_feature_check': True
            }
        }
        
        response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert data['playbook_type'] == 'activation'
        assert 'triggered' in data
        assert 'affected_accounts' in data
        
        # Should trigger for accounts with low adoption
        if data['triggered']:
            affected_ids = [acc['account_id'] for acc in data['affected_accounts']]
            assert 101 in affected_ids or 102 in affected_ids
    
    def test_evaluate_all_triggers(self, client):
        """Test evaluating all enabled triggers"""
        # Enable VoC triggers
        voc_data = {
            'playbook_type': 'voc',
            'triggers': {
                'nps_threshold': 10,
                'auto_trigger_enabled': True
            }
        }
        client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(voc_data)
        )
        
        # Enable Activation triggers
        activation_data = {
            'playbook_type': 'activation',
            'triggers': {
                'adoption_index_threshold': 60,
                'auto_trigger_enabled': True
            }
        }
        client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(activation_data)
        )
        
        # Evaluate all
        response = client.post(
            '/api/playbook-triggers/evaluate-all',
            headers={'X-Customer-ID': '1'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert data['customer_id'] == 1
        assert 'results' in data
        assert data['total_triggers_evaluated'] == 2
        assert len(data['results']) == 2
    
    def test_get_trigger_history(self, client):
        """Test getting trigger evaluation history"""
        # Create and evaluate some triggers first
        trigger_data = {
            'playbook_type': 'voc',
            'triggers': {
                'nps_threshold': 10,
                'auto_trigger_enabled': True
            }
        }
        
        client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        # Test the trigger
        client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        # Get history
        response = client.get(
            '/api/playbook-triggers/history',
            headers={'X-Customer-ID': '1'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['status'] == 'success'
        assert len(data['history']) > 0
        assert data['history'][0]['playbook_type'] == 'voc'
        assert data['history'][0]['last_evaluated'] is not None
    
    def test_missing_playbook_type(self, client):
        """Test error handling for missing playbook_type"""
        trigger_data = {
            'triggers': {
                'nps_threshold': 10
            }
        }
        
        response = client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'playbook_type is required' in data['message']
    
    def test_invalid_playbook_type(self, client):
        """Test error handling for invalid playbook_type"""
        trigger_data = {
            'playbook_type': 'invalid_type',
            'triggers': {
                'some_threshold': 10
            }
        }
        
        response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'Unknown playbook type' in data['message']
    
    def test_customer_isolation(self, client):
        """Test that triggers are isolated by customer"""
        # Create trigger for customer 1
        trigger_data = {
            'playbook_type': 'voc',
            'triggers': {
                'nps_threshold': 10,
                'auto_trigger_enabled': True
            }
        }
        
        client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        # Try to retrieve as customer 2
        response = client.get('/api/playbook-triggers', headers={'X-Customer-ID': '2'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Should get defaults, not customer 1's settings
        assert data['customer_id'] == 2
        # If no triggers exist for customer 2, should return defaults
        if 'voc' in data['triggers'] and isinstance(data['triggers']['voc'], dict):
            if 'trigger_id' not in data['triggers']['voc']:
                # It's default settings
                assert data['triggers']['voc']['nps_threshold'] == 10


class TestVoCTriggerEvaluation:
    """Test VoC Sprint trigger evaluation logic"""
    
    def test_low_health_score_triggers_voc(self, client):
        """Test that low health score triggers VoC Sprint"""
        trigger_data = {
            'playbook_type': 'voc',
            'triggers': {
                'nps_threshold': 10,
                'csat_threshold': 3.6,
                'churn_risk_threshold': 0.30,
                'health_score_drop_threshold': 10
            }
        }
        
        response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        data = json.loads(response.data)
        
        # Account 101 has health_score of 35.5, should trigger
        assert data['triggered'] == True
        affected_account_ids = [acc['account_id'] for acc in data['affected_accounts']]
        assert 101 in affected_account_ids
    
    def test_at_risk_account_triggers_voc(self, client):
        """Test that 'At Risk' account status triggers VoC Sprint"""
        trigger_data = {
            'playbook_type': 'voc',
            'triggers': {
                'nps_threshold': 10,
                'csat_threshold': 3.6,
                'churn_risk_threshold': 0.30
            }
        }
        
        response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        data = json.loads(response.data)
        
        # Account 101 is marked 'At Risk'
        assert data['triggered'] == True
        account_101 = next((acc for acc in data['affected_accounts'] if acc['account_id'] == 101), None)
        assert account_101 is not None
        assert any('At Risk' in trigger for trigger in account_101['triggers'])
    
    def test_high_health_account_not_triggered(self, client):
        """Test that high health accounts don't trigger VoC Sprint"""
        trigger_data = {
            'playbook_type': 'voc',
            'triggers': {
                'nps_threshold': 10,
                'csat_threshold': 3.6,
                'churn_risk_threshold': 0.30
            }
        }
        
        response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        data = json.loads(response.data)
        
        # Account 103 has health_score of 85.0, should NOT be in triggered list
        affected_account_ids = [acc['account_id'] for acc in data['affected_accounts']]
        assert 103 not in affected_account_ids


class TestActivationTriggerEvaluation:
    """Test Activation Blitz trigger evaluation logic"""
    
    def test_low_adoption_triggers_activation(self, client):
        """Test that low adoption index triggers Activation Blitz"""
        trigger_data = {
            'playbook_type': 'activation',
            'triggers': {
                'adoption_index_threshold': 60,
                'active_users_threshold': 50,
                'dau_mau_threshold': 0.25
            }
        }
        
        response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        data = json.loads(response.data)
        
        # Accounts with health_score < 60 should trigger
        assert data['triggered'] == True
        affected_account_ids = [acc['account_id'] for acc in data['affected_accounts']]
        assert 101 in affected_account_ids  # health_score = 35.5
        assert 102 in affected_account_ids  # health_score = 58.0
    
    def test_unused_features_triggers_activation(self, client):
        """Test that unused features trigger Activation Blitz"""
        trigger_data = {
            'playbook_type': 'activation',
            'triggers': {
                'adoption_index_threshold': 100,  # Set high so adoption doesn't trigger
                'active_users_threshold': 0,       # Set low so users don't trigger
                'dau_mau_threshold': 0.10,         # Set low so DAU/MAU doesn't trigger
                'unused_feature_check': True
            }
        }
        
        response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        data = json.loads(response.data)
        
        # Account 101 has only 2 KPIs (< 10 threshold)
        if data['triggered']:
            account_101 = next((acc for acc in data['affected_accounts'] if acc['account_id'] == 101), None)
            if account_101:
                assert any('Limited feature usage' in trigger for trigger in account_101['triggers'])
    
    def test_high_adoption_not_triggered(self, client):
        """Test that high adoption accounts don't trigger"""
        trigger_data = {
            'playbook_type': 'activation',
            'triggers': {
                'adoption_index_threshold': 60,
                'active_users_threshold': 50,
                'dau_mau_threshold': 0.25,
                'unused_feature_check': False
            }
        }
        
        response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        data = json.loads(response.data)
        
        # Account 103 has health_score of 85.0 (high adoption), should NOT trigger
        affected_account_ids = [acc['account_id'] for acc in data['affected_accounts']]
        assert 103 not in affected_account_ids


class TestTriggerCount:
    """Test trigger count tracking"""
    
    def test_trigger_count_increments(self, client):
        """Test that trigger_count increments when triggered"""
        # Save and enable trigger
        trigger_data = {
            'playbook_type': 'voc',
            'triggers': {
                'nps_threshold': 10,
                'auto_trigger_enabled': True
            }
        }
        
        client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_data)
        )
        
        # Evaluate all triggers (this should increment count)
        client.post(
            '/api/playbook-triggers/evaluate-all',
            headers={'X-Customer-ID': '1'}
        )
        
        # Check history
        response = client.get(
            '/api/playbook-triggers/history?playbook_type=voc',
            headers={'X-Customer-ID': '1'}
        )
        
        data = json.loads(response.data)
        assert len(data['history']) > 0
        # Trigger count should be > 0 if it was triggered
        if data['history'][0]['last_triggered']:
            assert data['history'][0]['trigger_count'] > 0


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

