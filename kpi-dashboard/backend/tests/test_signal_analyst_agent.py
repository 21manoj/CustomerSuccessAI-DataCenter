"""
Unit tests for Signal Analyst Agent
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json

from agents import (
    SignalAnalystAgent,
    SignalAnalystInput,
    SignalAnalystOutput,
    SignalData,
    AnalysisError
)
from agents.vertical_mapper import map_vertical_to_agent_type
from agents.signal_converter import (
    convert_account_to_signal_data,
    convert_kpi_to_signal_data,
    convert_account_notes_to_signal_data
)
from agents.qdrant_integration import convert_qdrant_results_to_signal_data


class TestVerticalMapper(unittest.TestCase):
    """Test vertical mapping utility"""
    
    def test_map_saas_to_agent_type(self):
        result = map_vertical_to_agent_type('saas')
        self.assertEqual(result, 'saas_customer_success')
    
    def test_map_datacenter_to_agent_type(self):
        result = map_vertical_to_agent_type('datacenter')
        self.assertEqual(result, 'data_center_infrastructure')
    
    def test_map_data_center_to_agent_type(self):
        result = map_vertical_to_agent_type('data_center')
        self.assertEqual(result, 'data_center_infrastructure')
    
    def test_map_already_agent_format(self):
        result = map_vertical_to_agent_type('saas_customer_success')
        self.assertEqual(result, 'saas_customer_success')


class TestSignalConverter(unittest.TestCase):
    """Test signal data converter utility"""
    
    def test_convert_qdrant_results(self):
        """Test converting Qdrant results to SignalData"""
        qdrant_results = [
            {
                'similarity': 0.95,
                'text': 'Test signal text',
                'metadata': {
                    'account_id': 1,
                    'kpi_parameter': 'NPS',
                    'data': '50'
                }
            }
        ]
        
        signals = convert_qdrant_results_to_signal_data(qdrant_results)
        
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].similarity, 0.95)
        self.assertEqual(signals[0].payload['text'], 'Test signal text')
        self.assertEqual(signals[0].payload['account_id'], 1)
    
    def test_convert_qdrant_results_missing_similarity(self):
        """Test with missing similarity (should use default)"""
        qdrant_results = [
            {
                'text': 'Test signal',
                'metadata': {}
            }
        ]
        
        signals = convert_qdrant_results_to_signal_data(qdrant_results, default_similarity=0.7)
        self.assertEqual(signals[0].similarity, 0.7)


class TestSignalAnalystAgent(unittest.TestCase):
    """Test Signal Analyst Agent"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_api_key = "sk-test-key"
        self.agent = SignalAnalystAgent(
            openai_api_key=self.mock_api_key,
            model="gpt-4o",
            temperature=0.3
        )
        
        # Mock input data
        self.mock_input = SignalAnalystInput(
            account_id="test-account-001",
            customer_id=1,
            vertical_type="saas_customer_success",
            account_name="Test Account",
            account_arr=120000.0,
            quantitative_signals=[
                SignalData(
                    similarity=0.95,
                    payload={
                        "pillar": "usage",
                        "metric_type": "dau",
                        "current_value": 1250,
                        "trend": -0.30,
                        "text": "DAU declining 30%"
                    }
                )
            ],
            qualitative_signals=[
                SignalData(
                    similarity=0.92,
                    payload={
                        "signal_type": "support_ticket",
                        "signal_source": "internal",
                        "sentiment": "negative",
                        "severity": "critical",
                        "text": "Integration broken"
                    }
                )
            ],
            historical_patterns=[],
            analysis_type="comprehensive",
            time_horizon_days=60
        )
    
    @patch('agents.signal_analyst_agent.OpenAI')
    def test_agent_initialization(self, mock_openai_class):
        """Test agent initialization"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        agent = SignalAnalystAgent(
            openai_api_key="sk-test",
            model="gpt-4o"
        )
        
        self.assertEqual(agent.model, "gpt-4o")
        self.assertEqual(agent.temperature, 0.3)
        mock_openai_class.assert_called_once_with(api_key="sk-test")
    
    @patch('agents.signal_analyst_agent.OpenAI')
    def test_analyze_success(self, mock_openai_class):
        """Test successful analysis"""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "predicted_outcome": "churn",
            "churn_probability": 75.0,
            "expansion_probability": 10.0,
            "health_score": 45.0,
            "time_to_event": "45-60 days",
            "risk_drivers": [
                {
                    "driver": "Usage declining",
                    "impact": "critical",
                    "supporting_signals": ["DAU decline"],
                    "confidence": 0.92
                }
            ],
            "growth_drivers": [],
            "confidence": {
                "overall_confidence": 0.82,
                "confidence_factors": {
                    "signal_quality": 0.85,
                    "signal_quantity": 0.78,
                    "historical_matches": 0.83,
                    "pattern_clarity": 0.82
                }
            },
            "reasoning": "Account shows high churn risk due to declining usage",
            "key_insights": ["Usage declining", "Support issues"],
            "recommended_actions": [
                {
                    "action": "Schedule call with CTO",
                    "priority": "immediate",
                    "owner": "CSM",
                    "deadline_days": 1,
                    "expected_impact": "Address integration issues"
                }
            ]
        })
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        agent = SignalAnalystAgent(
            openai_api_key="sk-test",
            model="gpt-4o"
        )
        
        result = agent.analyze(self.mock_input)
        
        self.assertIsInstance(result, SignalAnalystOutput)
        self.assertEqual(result.account_id, "test-account-001")
        self.assertEqual(result.predicted_outcome, "churn")
        self.assertEqual(result.churn_probability, 75.0)
        self.assertGreater(result.analysis_duration_ms, 0)
    
    @patch('agents.signal_analyst_agent.OpenAI')
    def test_analyze_invalid_json(self, mock_openai_class):
        """Test handling of invalid JSON response"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Invalid JSON response"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client
        
        agent = SignalAnalystAgent(
            openai_api_key="sk-test",
            model="gpt-4o"
        )
        
        with self.assertRaises(AnalysisError):
            agent.analyze(self.mock_input)


class TestSignalData(unittest.TestCase):
    """Test SignalData model"""
    
    def test_signal_data_creation(self):
        """Test creating SignalData"""
        signal = SignalData(
            similarity=0.95,
            payload={
                'signal_type': 'test',
                'text': 'Test signal'
            }
        )
        
        self.assertEqual(signal.similarity, 0.95)
        self.assertEqual(signal.signal_type, 'test')
        self.assertEqual(signal.text, 'Test signal')
    
    def test_signal_data_similarity_bounds(self):
        """Test similarity bounds validation"""
        # Should accept valid range
        signal = SignalData(
            similarity=0.5,
            payload={'test': 'data'}
        )
        self.assertEqual(signal.similarity, 0.5)
        
        # Should raise validation error for out of bounds
        with self.assertRaises(Exception):  # Pydantic validation error
            SignalData(
                similarity=1.5,  # > 1.0
                payload={'test': 'data'}
            )


if __name__ == '__main__':
    unittest.main()

