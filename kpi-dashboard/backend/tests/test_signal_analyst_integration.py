"""
Integration tests for Signal Analyst Agent with real data

These tests require:
- Database connection
- Valid OpenAI API key
- Test account data
"""

import unittest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extensions import db
from app import app
from models import Account, KPI, AccountNote, Customer, CustomerConfig
from agents import SignalAnalystAgent, SignalAnalystInput, SignalData
from agents.vertical_mapper import map_vertical_to_agent_type
from agents.signal_converter import convert_database_models_to_signals
from agents.qdrant_integration import convert_qdrant_results_to_signal_data
from openai_key_utils import get_openai_api_key


@unittest.skipUnless(
    os.getenv('RUN_INTEGRATION_TESTS') == 'true',
    "Integration tests skipped. Set RUN_INTEGRATION_TESTS=true to run."
)
class TestSignalAnalystIntegration(unittest.TestCase):
    """Integration tests for Signal Analyst Agent"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database and fixtures"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
            'TEST_DATABASE_URL',
            'postgresql://dcuser:dcpass123@localhost:5432/cs_pulse_test'
        )
        cls.app = app
        cls.client = app.test_client()
        
        with app.app_context():
            db.create_all()
            
            # Create test customer
            cls.test_customer = Customer.query.filter_by(email='test@signalanalyst.com').first()
            if not cls.test_customer:
                cls.test_customer = Customer(
                    customer_name='Signal Analyst Test Customer',
                    email='test@signalanalyst.com'
                )
                db.session.add(cls.test_customer)
                db.session.commit()
            
            # Create test account
            cls.test_account = Account.query.filter_by(
                account_name='Signal Analyst Test Account',
                customer_id=cls.test_customer.customer_id
            ).first()
            
            if not cls.test_account:
                cls.test_account = Account(
                    customer_id=cls.test_customer.customer_id,
                    account_name='Signal Analyst Test Account',
                    revenue=150000,
                    industry='Technology',
                    region='North America',
                    account_status='active'
                )
                db.session.add(cls.test_account)
                db.session.commit()
    
    def setUp(self):
        """Set up for each test"""
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up after each test"""
        self.app_context.pop()
    
    def test_signal_converter_with_real_account(self):
        """Test converting real account data to signals"""
        with self.app.app_context():
            # Get test account
            account = Account.query.filter_by(
                account_id=self.test_account.account_id
            ).first()
            
            self.assertIsNotNone(account)
            
            # Convert to signals
            signals = convert_database_models_to_signals(account=account)
            
            self.assertIn('quantitative_signals', signals)
            self.assertGreater(len(signals['quantitative_signals']), 0)
            
            # Check signal structure
            signal = signals['quantitative_signals'][0]
            self.assertIsInstance(signal, SignalData)
            self.assertIn('account_name', signal.payload)
            self.assertEqual(signal.payload['account_id'], account.account_id)
    
    def test_vertical_mapping_integration(self):
        """Test vertical mapping with real customer"""
        with self.app.app_context():
            # Test saas mapping
            agent_vertical = map_vertical_to_agent_type('saas')
            self.assertEqual(agent_vertical, 'saas_customer_success')
            
            # Test datacenter mapping
            agent_vertical = map_vertical_to_agent_type('datacenter')
            self.assertEqual(agent_vertical, 'data_center_infrastructure')
    
    def test_agent_input_creation_with_real_data(self):
        """Test creating SignalAnalystInput with real account data"""
        with self.app.app_context():
            account = Account.query.filter_by(
                account_id=self.test_account.account_id
            ).first()
            
            # Convert to signals
            signals = convert_database_models_to_signals(account=account)
            
            # Create input
            agent_input = SignalAnalystInput(
                account_id=str(account.account_id),
                customer_id=account.customer_id,
                vertical_type=map_vertical_to_agent_type('saas'),
                account_name=account.account_name,
                account_arr=float(account.revenue) if account.revenue else None,
                quantitative_signals=signals['quantitative_signals'],
                qualitative_signals=signals['qualitative_signals'],
                historical_patterns=signals['historical_patterns'],
                analysis_type='comprehensive',
                time_horizon_days=60
            )
            
            self.assertEqual(agent_input.account_id, str(account.account_id))
            self.assertEqual(agent_input.customer_id, account.customer_id)
            self.assertGreater(len(agent_input.quantitative_signals), 0)
    
    @unittest.skipUnless(
        get_openai_api_key(1) is not None,
        "OpenAI API key not configured. Skipping agent analysis test."
    )
    def test_agent_analysis_with_real_data(self):
        """Test running agent analysis with real account data (requires OpenAI API key)"""
        with self.app.app_context():
            account = Account.query.filter_by(
                account_id=self.test_account.account_id
            ).first()
            
            # Get OpenAI API key
            openai_api_key = get_openai_api_key(self.test_customer.customer_id)
            if not openai_api_key:
                self.skipTest("OpenAI API key not configured")
            
            # Convert to signals
            signals = convert_database_models_to_signals(account=account)
            
            # Create input
            agent_input = SignalAnalystInput(
                account_id=str(account.account_id),
                customer_id=account.customer_id,
                vertical_type=map_vertical_to_agent_type('saas'),
                account_name=account.account_name,
                account_arr=float(account.revenue) if account.revenue else None,
                quantitative_signals=signals['quantitative_signals'],
                qualitative_signals=signals['qualitative_signals'],
                historical_patterns=signals['historical_patterns'],
                analysis_type='comprehensive',
                time_horizon_days=60
            )
            
            # Initialize agent
            agent = SignalAnalystAgent(
                openai_api_key=openai_api_key,
                model="gpt-4o",
                temperature=0.3
            )
            
            # Run analysis (this will call OpenAI API)
            try:
                result = agent.analyze(agent_input)
                
                # Verify result structure
                self.assertIsNotNone(result)
                self.assertEqual(result.account_id, str(account.account_id))
                self.assertGreaterEqual(result.churn_probability, 0)
                self.assertLessEqual(result.churn_probability, 100)
                self.assertGreaterEqual(result.health_score, 0)
                self.assertLessEqual(result.health_score, 100)
                self.assertIsNotNone(result.reasoning)
                self.assertIsNotNone(result.confidence)
                
            except Exception as e:
                self.fail(f"Agent analysis failed: {e}")


if __name__ == '__main__':
    unittest.main()

