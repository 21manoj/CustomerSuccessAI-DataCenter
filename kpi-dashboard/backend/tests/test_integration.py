"""
Integration Tests for Playbook Triggers System

Tests end-to-end workflows and integration between components
"""

import pytest
import json
from datetime import datetime
from app import app, db
from models import PlaybookTrigger, Account, Customer, KPI

@pytest.fixture
def client():
    """Create test client with full database"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            setup_integration_test_data()
            yield client
            db.session.remove()
            db.drop_all()

def setup_integration_test_data():
    """Setup comprehensive test data"""
    # Create customer
    customer = Customer(
        customer_id=1,
        customer_name='Integration Test Co',
        email='integration@test.com'
    )
    db.session.add(customer)
    
    # Create accounts with varied profiles
    accounts = [
        # Critical account - should trigger VoC Sprint
        Account(
            account_id=1,
            customer_id=1,
            account_name='Critical Health Account',
            revenue=100000,
            
            account_status='At Risk',
            industry='Technology',
            region='North America'
        ),
        # Low adoption account - should trigger Activation Blitz
        Account(
            account_id=2,
            customer_id=1,
            account_name='Low Adoption Account',
            revenue=50000,
            
            account_status='Active',
            industry='Healthcare',
            region='Europe'
        ),
        # Healthy account - should NOT trigger
        Account(
            account_id=3,
            customer_id=1,
            account_name='Healthy Account',
            revenue=150000,
            
            account_status='Active',
            industry='Finance',
            region='Asia-Pacific'
        )
    ]
    
    for account in accounts:
        db.session.add(account)
    
    # Add KPIs for feature usage tracking
    kpis = [
        KPI(kpi_id=1, account_id=1, category='Product Usage', kpi_parameter='Feature A', data='low'),
        KPI(kpi_id=2, account_id=1, category='Customer Success', kpi_parameter='Support Tickets', data='high'),
        KPI(kpi_id=3, account_id=2, category='Product Usage', kpi_parameter='Feature A', data='minimal'),
        KPI(kpi_id=4, account_id=3, category='Product Usage', kpi_parameter='Feature A', data='excellent'),
        KPI(kpi_id=5, account_id=3, category='Product Usage', kpi_parameter='Feature B', data='excellent'),
        KPI(kpi_id=6, account_id=3, category='Product Usage', kpi_parameter='Feature C', data='excellent'),
    ]
    
    for kpi in kpis:
        db.session.add(kpi)
    
    db.session.commit()


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows"""
    
    def test_configure_and_evaluate_voc_workflow(self, client):
        """Test complete VoC Sprint configuration and evaluation workflow"""
        # Step 1: Configure VoC triggers
        trigger_config = {
            'playbook_type': 'voc',
            'triggers': {
                'nps_threshold': 10,
                'csat_threshold': 3.6,
                'churn_risk_threshold': 0.30,
                'health_score_drop_threshold': 10,
                'churn_mentions_threshold': 2,
                'auto_trigger_enabled': True
            }
        }
        
        save_response = client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_config)
        )
        
        assert save_response.status_code == 200
        
        # Step 2: Retrieve configuration
        get_response = client.get(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1'}
        )
        
        assert get_response.status_code == 200
        get_data = json.loads(get_response.data)
        assert 'voc' in get_data['triggers']
        
        # Step 3: Test triggers
        test_response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_config)
        )
        
        assert test_response.status_code == 200
        test_data = json.loads(test_response.data)
        
        # Should trigger for account 1 (critical health)
        assert test_data['triggered'] == True
        assert len(test_data['affected_accounts']) > 0
        assert any(acc['account_id'] == 1 for acc in test_data['affected_accounts'])
        
        # Step 4: Evaluate all triggers
        eval_response = client.post(
            '/api/playbook-triggers/evaluate-all',
            headers={'X-Customer-ID': '1'}
        )
        
        assert eval_response.status_code == 200
        eval_data = json.loads(eval_response.data)
        assert eval_data['total_triggers_evaluated'] == 1
        
        # Step 5: Check history
        history_response = client.get(
            '/api/playbook-triggers/history',
            headers={'X-Customer-ID': '1'}
        )
        
        assert history_response.status_code == 200
        history_data = json.loads(history_response.data)
        assert len(history_data['history']) > 0
        assert history_data['history'][0]['trigger_count'] > 0
    
    def test_configure_and_evaluate_activation_workflow(self, client):
        """Test complete Activation Blitz configuration and evaluation workflow"""
        # Step 1: Configure Activation triggers
        trigger_config = {
            'playbook_type': 'activation',
            'triggers': {
                'adoption_index_threshold': 60,
                'active_users_threshold': 50,
                'dau_mau_threshold': 0.25,
                'unused_feature_check': True,
                'auto_trigger_enabled': True
            }
        }
        
        save_response = client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_config)
        )
        
        assert save_response.status_code == 200
        
        # Step 2: Test triggers
        test_response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_config)
        )
        
        assert test_response.status_code == 200
        test_data = json.loads(test_response.data)
        
        # Should trigger for accounts 1 and 2 (low adoption)
        assert test_data['triggered'] == True
        affected_ids = [acc['account_id'] for acc in test_data['affected_accounts']]
        assert 1 in affected_ids or 2 in affected_ids
    
    def test_multiple_playbooks_workflow(self, client):
        """Test workflow with multiple playbooks configured"""
        # Configure both VoC and Activation
        voc_config = {
            'playbook_type': 'voc',
            'triggers': {'nps_threshold': 10, 'auto_trigger_enabled': True}
        }
        
        activation_config = {
            'playbook_type': 'activation',
            'triggers': {'adoption_index_threshold': 60, 'auto_trigger_enabled': True}
        }
        
        client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(voc_config)
        )
        
        client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(activation_config)
        )
        
        # Evaluate all
        response = client.post(
            '/api/playbook-triggers/evaluate-all',
            headers={'X-Customer-ID': '1'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['total_triggers_evaluated'] == 2
        assert len(data['results']) == 2
        
        playbook_types = [r['playbook_type'] for r in data['results']]
        assert 'voc' in playbook_types
        assert 'activation' in playbook_types


class TestAccountScenarios:
    """Test different account scenarios"""
    
    def test_critical_health_triggers_voc(self, client):
        """Test that critical health account triggers VoC Sprint"""
        trigger_config = {
            'playbook_type': 'voc',
            'triggers': {'nps_threshold': 10, 'csat_threshold': 3.6}
        }
        
        response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_config)
        )
        
        data = json.loads(response.data)
        
        # Account 1 has health_score of 25.0 - should trigger
        affected_ids = [acc['account_id'] for acc in data['affected_accounts']]
        assert 1 in affected_ids
        
        # Account 3 has health_score of 92.0 - should NOT trigger
        assert 3 not in affected_ids
    
    def test_low_adoption_triggers_activation(self, client):
        """Test that low adoption account triggers Activation Blitz"""
        trigger_config = {
            'playbook_type': 'activation',
            'triggers': {'adoption_index_threshold': 60}
        }
        
        response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_config)
        )
        
        data = json.loads(response.data)
        
        # Accounts 1 and 2 have health_score < 60 - should trigger
        affected_ids = [acc['account_id'] for acc in data['affected_accounts']]
        assert 1 in affected_ids or 2 in affected_ids
        
        # Account 3 has health_score of 92.0 - should NOT trigger
        assert 3 not in affected_ids
    
    def test_healthy_account_no_triggers(self, client):
        """Test that healthy accounts don't trigger any playbooks"""
        # Test VoC
        voc_config = {
            'playbook_type': 'voc',
            'triggers': {'nps_threshold': 10}
        }
        
        voc_response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(voc_config)
        )
        
        voc_data = json.loads(voc_response.data)
        voc_affected = [acc['account_id'] for acc in voc_data['affected_accounts']]
        assert 3 not in voc_affected
        
        # Test Activation
        activation_config = {
            'playbook_type': 'activation',
            'triggers': {'adoption_index_threshold': 60}
        }
        
        activation_response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(activation_config)
        )
        
        activation_data = json.loads(activation_response.data)
        activation_affected = [acc['account_id'] for acc in activation_data['affected_accounts']]
        assert 3 not in activation_affected


class TestThresholdAdjustments:
    """Test different threshold configurations"""
    
    def test_strict_thresholds_fewer_triggers(self, client):
        """Test that stricter thresholds result in fewer triggers"""
        # Lenient thresholds
        lenient_config = {
            'playbook_type': 'voc',
            'triggers': {'nps_threshold': 100, 'csat_threshold': 5.0}
        }
        
        lenient_response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(lenient_config)
        )
        
        lenient_data = json.loads(lenient_response.data)
        lenient_count = len(lenient_data['affected_accounts'])
        
        # Strict thresholds
        strict_config = {
            'playbook_type': 'voc',
            'triggers': {'nps_threshold': 1, 'csat_threshold': 1.0}
        }
        
        strict_response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(strict_config)
        )
        
        strict_data = json.loads(strict_response.data)
        strict_count = len(strict_data['affected_accounts'])
        
        # Lenient should trigger more accounts
        assert lenient_count >= strict_count
    
    def test_threshold_updates_reflect_immediately(self, client):
        """Test that threshold updates are reflected in evaluations"""
        # Save initial thresholds
        initial_config = {
            'playbook_type': 'activation',
            'triggers': {'adoption_index_threshold': 30}
        }
        
        client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(initial_config)
        )
        
        # Test with initial thresholds
        initial_test = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(initial_config)
        )
        
        initial_data = json.loads(initial_test.data)
        initial_count = len(initial_data['affected_accounts'])
        
        # Update thresholds
        updated_config = {
            'playbook_type': 'activation',
            'triggers': {'adoption_index_threshold': 95}
        }
        
        client.post(
            '/api/playbook-triggers',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(updated_config)
        )
        
        # Test with updated thresholds
        updated_test = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(updated_config)
        )
        
        updated_data = json.loads(updated_test.data)
        updated_count = len(updated_data['affected_accounts'])
        
        # Updated threshold should affect different accounts
        # (threshold of 95 should trigger more accounts than 30)
        assert updated_count >= initial_count


class TestPerformance:
    """Test performance and scalability"""
    
    def test_evaluate_multiple_accounts_performance(self, client):
        """Test performance with multiple accounts"""
        import time
        
        trigger_config = {
            'playbook_type': 'voc',
            'triggers': {'nps_threshold': 10}
        }
        
        start_time = time.time()
        
        response = client.post(
            '/api/playbook-triggers/test',
            headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
            data=json.dumps(trigger_config)
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        assert response.status_code == 200
        # Should execute in reasonable time (< 1 second for 3 accounts)
        assert execution_time < 1.0
    
    def test_evaluate_all_triggers_performance(self, client):
        """Test performance when evaluating all triggers"""
        import time
        
        # Configure multiple triggers
        for playbook_type in ['voc', 'activation']:
            trigger_config = {
                'playbook_type': playbook_type,
                'triggers': {'auto_trigger_enabled': True}
            }
            client.post(
                '/api/playbook-triggers',
                headers={'X-Customer-ID': '1', 'Content-Type': 'application/json'},
                data=json.dumps(trigger_config)
            )
        
        start_time = time.time()
        
        response = client.post(
            '/api/playbook-triggers/evaluate-all',
            headers={'X-Customer-ID': '1'}
        )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        assert response.status_code == 200
        # Should execute in reasonable time
        assert execution_time < 2.0


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

