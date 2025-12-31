"""
Signal Analyst Agent API

Flask Blueprint for Signal Analyst Agent endpoints
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id
from extensions import db
from models import Account, KPI, AccountNote, Customer
from enhanced_rag_qdrant import get_qdrant_rag_system
from openai_key_utils import get_openai_api_key

from .signal_analyst_agent import SignalAnalystAgent, AnalysisError, ResponseParseError
from .models import SignalAnalystInput, SignalData
from .vertical_mapper import map_vertical_to_agent_type
from .qdrant_integration import (
    get_quantitative_signals_from_qdrant,
    get_qualitative_signals_from_qdrant,
    get_historical_patterns_from_qdrant,
    convert_qdrant_results_to_signal_data
)
from .signal_converter import convert_database_models_to_signals

import logging

logger = logging.getLogger(__name__)

signal_analyst_api = Blueprint('signal_analyst_api', __name__)


@signal_analyst_api.route('/api/signal-analyst/analyze', methods=['POST'])
def analyze_account():
    """
    Analyze account signals to predict churn/expansion and provide recommendations
    
    Request body:
    {
        "account_id": "123" or 123,
        "analysis_type": "comprehensive" | "churn_risk" | "expansion_opportunity" | "health_analysis",
        "time_horizon_days": 60,
        "use_qdrant": true,  # Optional: use Qdrant for signal retrieval
        "use_database": true  # Optional: use database models for signal retrieval
    }
    
    Returns:
        SignalAnalystOutput as JSON
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.json
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        # Extract and validate account_id
        account_id_raw = data.get('account_id')
        if not account_id_raw:
            return jsonify({'error': 'account_id is required'}), 400
        
        # Validate account_id is a positive integer
        try:
            account_id_int = int(account_id_raw)
            if account_id_int <= 0:
                return jsonify({'error': 'Invalid account_id: must be a positive integer'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid account_id: must be a number'}), 400
        
        account_id = str(account_id_int)  # Convert to string for consistency
        
        # Get account from database (for validation and context)
        account = Account.query.filter_by(
            account_id=account_id_int,
            customer_id=customer_id
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Get vertical type from customer or default to 'saas'
        # TODO: Store vertical in customer model or config
        vertical = 'saas'  # Default, should be retrieved from customer config
        agent_vertical_type = map_vertical_to_agent_type(vertical)
        
        # Validate and get analysis parameters
        valid_analysis_types = ['comprehensive', 'churn_risk', 'expansion_opportunity', 'health_analysis']
        analysis_type = data.get('analysis_type', 'comprehensive')
        if analysis_type not in valid_analysis_types:
            return jsonify({
                'error': f'Invalid analysis_type. Must be one of: {", ".join(valid_analysis_types)}'
            }), 400
        
        # Validate time_horizon_days
        time_horizon_days_raw = data.get('time_horizon_days', 60)
        try:
            time_horizon_days = int(time_horizon_days_raw)
            if time_horizon_days < 30 or time_horizon_days > 365:
                return jsonify({'error': 'time_horizon_days must be between 30 and 365'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'time_horizon_days must be a number'}), 400
        
        use_qdrant = data.get('use_qdrant', True)
        use_database = data.get('use_database', True)
        
        # Collect signals
        quantitative_signals = []
        qualitative_signals = []
        historical_patterns = []
        
        # Option 1: Get signals from Qdrant
        if use_qdrant:
            try:
                rag_system = get_qdrant_rag_system(customer_id)
                
                # Get quantitative signals
                quant_signals = get_quantitative_signals_from_qdrant(
                    rag_system, account_id, customer_id, top_k=20
                )
                quantitative_signals.extend(quant_signals)
                
                # Get qualitative signals
                qual_signals = get_qualitative_signals_from_qdrant(
                    rag_system, account_id, customer_id, top_k=20
                )
                qualitative_signals.extend(qual_signals)
                
                # Get historical patterns
                hist_patterns = get_historical_patterns_from_qdrant(
                    rag_system, account_id, customer_id, top_k=10
                )
                historical_patterns.extend(hist_patterns)
                
            except Exception as e:
                logger.warning(f"Error retrieving signals from Qdrant: {e}")
                # Continue with database signals if Qdrant fails
        
        # Option 2: Get signals from database
        if use_database:
            try:
                # Get KPIs for this account (account_id_int already validated above)
                kpis = KPI.query.filter_by(
                    account_id=account_id_int,
                    customer_id=customer_id
                ).limit(50).all()
                
                # Get account notes (account_id_int already validated above)
                notes = AccountNote.query.filter_by(
                    account_id=account_id_int,
                    customer_id=customer_id
                ).order_by(AccountNote.created_at.desc()).limit(20).all()
                
                # Convert to signals
                db_signals = convert_database_models_to_signals(
                    account=account,
                    kpis=kpis,
                    notes=notes
                )
                
                quantitative_signals.extend(db_signals['quantitative_signals'])
                qualitative_signals.extend(db_signals['qualitative_signals'])
                historical_patterns.extend(db_signals['historical_patterns'])
                
            except Exception as e:
                logger.warning(f"Error retrieving signals from database: {e}")
        
        # Get OpenAI API key
        openai_api_key = get_openai_api_key(customer_id)
        if not openai_api_key:
            return jsonify({
                'error': 'OpenAI API key not configured. Please configure it in Settings > OpenAI Key Settings.'
            }), 400
        
        # Build agent input
        agent_input = SignalAnalystInput(
            account_id=account_id,
            customer_id=customer_id,
            vertical_type=agent_vertical_type,
            account_name=account.account_name,
            account_arr=float(account.revenue) if account.revenue else None,
            quantitative_signals=quantitative_signals,
            qualitative_signals=qualitative_signals,
            historical_patterns=historical_patterns,
            analysis_type=analysis_type,
            time_horizon_days=time_horizon_days
        )
        
        # Initialize agent
        agent = SignalAnalystAgent(
            openai_api_key=openai_api_key,
            model="gpt-4o",
            temperature=0.3
        )
        
        # Run analysis
        analysis_result = agent.analyze(agent_input)
        
        # Convert to JSON-serializable format
        result_dict = analysis_result.model_dump()
        
        return jsonify(result_dict)
        
    except AnalysisError as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        return jsonify({'error': 'Analysis failed. Please try again later.'}), 500
    
    except ResponseParseError as e:
        logger.error(f"Response parse error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to process analysis response. Please try again later.'}), 500
    
    except ValueError as e:
        # Handle input validation errors (should be caught earlier, but safe fallback)
        logger.warning(f"Input validation error: {e}", exc_info=True)
        return jsonify({'error': 'Invalid input parameters'}), 400
    
    except Exception as e:
        logger.error(f"Unexpected error in analyze_account: {e}", exc_info=True)
        # Don't expose internal error details to client
        return jsonify({'error': 'Internal server error. Please try again later.'}), 500


@signal_analyst_api.route('/api/signal-analyst/test', methods=['POST'])
def test_analysis_with_mock_data():
    """
    Test endpoint that uses mock data to verify the agent works
    
    Request body (optional):
    {
        "account_id": "test-account-001",
        "analysis_type": "comprehensive"
    }
    
    Returns:
        SignalAnalystOutput with mock data
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.json or {}
        account_id = data.get('account_id', 'test-account-001')
        
        # Validate analysis_type
        valid_analysis_types = ['comprehensive', 'churn_risk', 'expansion_opportunity', 'health_analysis']
        analysis_type = data.get('analysis_type', 'comprehensive')
        if analysis_type not in valid_analysis_types:
            return jsonify({
                'error': f'Invalid analysis_type. Must be one of: {", ".join(valid_analysis_types)}'
            }), 400
        
        # Validate time_horizon_days
        time_horizon_days_raw = data.get('time_horizon_days', 60)
        try:
            time_horizon_days = int(time_horizon_days_raw)
            if time_horizon_days < 30 or time_horizon_days > 365:
                return jsonify({'error': 'time_horizon_days must be between 30 and 365'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'time_horizon_days must be a number'}), 400
        
        # Get vertical (default to saas)
        vertical = 'saas'
        agent_vertical_type = map_vertical_to_agent_type(vertical)
        
        # Create mock signals
        mock_quantitative = [
            SignalData(
                similarity=0.95,
                payload={
                    "pillar": "usage",
                    "metric_type": "dau",
                    "current_value": 1250,
                    "trend": -0.30,
                    "text": "DAU declining 30% over 30 days"
                }
            ),
            SignalData(
                similarity=0.88,
                payload={
                    "pillar": "financial",
                    "metric_type": "arr",
                    "current_value": 120000,
                    "trend": -0.15,
                    "text": "ARR declining 15%"
                }
            )
        ]
        
        mock_qualitative = [
            SignalData(
                similarity=0.92,
                payload={
                    "signal_type": "support_ticket",
                    "signal_source": "internal",
                    "sentiment": "negative",
                    "severity": "critical",
                    "text": "Salesforce integration broken for 2 weeks, blocking sales team"
                }
            ),
            SignalData(
                similarity=0.85,
                payload={
                    "signal_type": "executive_change",
                    "signal_source": "external",
                    "sentiment": "negative",
                    "severity": "high",
                    "text": "New CTO hired, previously used competitor products"
                }
            )
        ]
        
        mock_historical = [
            SignalData(
                similarity=0.82,
                payload={
                    "outcome_type": "churn",
                    "signals_summary": "Usage declined 40%, champion left, integration bugs unresolved. Churned after 60 days."
                }
            )
        ]
        
        # Build agent input
        agent_input = SignalAnalystInput(
            account_id=account_id,
            customer_id=customer_id,
            vertical_type=agent_vertical_type,
            account_name="Test Account",
            account_arr=120000.0,
            quantitative_signals=mock_quantitative,
            qualitative_signals=mock_qualitative,
            historical_patterns=mock_historical,
            analysis_type=analysis_type,
            time_horizon_days=time_horizon_days
        )
        
        # Get OpenAI API key
        openai_api_key = get_openai_api_key(customer_id)
        if not openai_api_key:
            return jsonify({
                'error': 'OpenAI API key not configured. Please configure it in Settings > OpenAI Key Settings.'
            }), 400
        
        # Initialize agent
        agent = SignalAnalystAgent(
            openai_api_key=openai_api_key,
            model="gpt-4o",
            temperature=0.3
        )
        
        # Run analysis
        analysis_result = agent.analyze(agent_input)
        
        # Convert to JSON-serializable format
        result_dict = analysis_result.model_dump()
        
        return jsonify({
            **result_dict,
            '_test_mode': True,
            '_mock_data_used': True
        })
        
    except ValueError as e:
        # Handle input validation errors
        logger.warning(f"Input validation error in test endpoint: {e}", exc_info=True)
        return jsonify({'error': 'Invalid input parameters'}), 400
    
    except Exception as e:
        logger.error(f"Error in test_analysis_with_mock_data: {e}", exc_info=True)
        # Don't expose internal error details to client
        return jsonify({'error': 'Test failed. Please try again later.'}), 500

