"""
Signal Analyst Agent API

Flask Blueprint for Signal Analyst Agent endpoints
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id
from extensions import db
from models import Account, KPI, AccountNote, Customer, DC2SKPI, QualitativeSignal
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
from .signal_deduplicator import deduplicate_signals

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
        # Check customer config for vertical
        vertical = 'saas'  # Default
        try:
            from models import CustomerConfig
            config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
            if config and config.vertical:
                vertical = config.vertical
        except Exception as e:
            logger.warning(f"Could not load customer config: {e}")
        
        agent_vertical_type = map_vertical_to_agent_type(vertical)
        
        # Load customer pillar weights for DC2_S customers
        pillar_weights = None
        if vertical == 'dc2_s':
            try:
                from utils.config_loader import ConfigLoader
                config_loader = ConfigLoader(customer_id)
                pillar_weights = config_loader.get_pillar_weights()
                logger.info(f"Using customer's pillar weights: {pillar_weights}")
            except Exception as e:
                logger.warning(f"Could not load pillar weights, using defaults: {e}")
                pillar_weights = {
                    'AI': 0.25, 'CH': 0.20, 'DV': 0.15, 'EX': 0.20, 'OS': 0.20
                }
        
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
        
        # Get or calculate health score
        overall_health_score = None
        
        # DC2_S: use KPI-based health from dc2s_kpis (same as /api/dc2s/health-score/:id)
        if vertical == 'dc2_s':
            try:
                from models import DC2SKPI
                from verticals.dc2_s.api_routes import calculate_kpi_health
                kpis = DC2SKPI.query.filter_by(account_id=account_id_int).order_by(DC2SKPI.measured_at.desc()).all()
                latest_kpis = {}
                for kpi in kpis:
                    if kpi.kpi_code not in latest_kpis:
                        latest_kpis[kpi.kpi_code] = kpi
                kpi_values = {kpi_code: float(kpi.value) for kpi_code, kpi in latest_kpis.items()}
                if kpi_values:
                    overall_health_score, _ = calculate_kpi_health(kpi_values, customer_id=customer_id)
                    overall_health_score = round(float(overall_health_score), 1)
                    logger.info(f"DC2_S health score for account {account_id}: {overall_health_score}/100")
                else:
                    logger.info(f"DC2_S: No KPI data for account {account_id}, health score will be omitted")
            except Exception as e:
                logger.warning(f"DC2_S health score calculation failed: {e}", exc_info=True)
        
        # SaaS / fallback: HealthTrend and HealthScoreStorageService
        if overall_health_score is None:
            try:
                from models import HealthTrend
                from health_score_storage import HealthScoreStorageService
                from datetime import datetime, timedelta
                
                health_trend = HealthTrend.query.filter_by(
                    account_id=account_id_int,
                    customer_id=customer_id
                ).order_by(HealthTrend.created_at.desc()).first()
                
                should_recalculate = False
                if health_trend and health_trend.overall_health_score:
                    health_score_age = (datetime.utcnow() - health_trend.created_at).total_seconds() / (24 * 3600)
                    if health_score_age > 7:
                        should_recalculate = True
                    else:
                        overall_health_score = float(health_trend.overall_health_score)
                        logger.info(f"Using existing health score: {overall_health_score:.1f} (age: {health_score_age:.1f} days)")
                else:
                    should_recalculate = True
                
                if should_recalculate and overall_health_score is None:
                    storage_service = HealthScoreStorageService()
                    health_scores = storage_service._calculate_account_health_scores(account, customer_id)
                    overall_health_score = health_scores.get('overall', 0)
                    now = datetime.utcnow()
                    month, year = now.month, now.year
                    existing_trend = HealthTrend.query.filter_by(
                        account_id=account_id_int, month=month, year=year
                    ).first()
                    if existing_trend:
                        existing_trend.overall_health_score = overall_health_score
                        existing_trend.updated_at = now
                        db.session.commit()
                    else:
                        new_trend = HealthTrend(
                            account_id=account_id_int, customer_id=customer_id, month=month, year=year,
                            overall_health_score=overall_health_score,
                            product_usage_score=health_scores.get('product_usage', 0),
                            support_score=health_scores.get('support', 0),
                            customer_sentiment_score=health_scores.get('customer_sentiment', 0),
                            business_outcomes_score=health_scores.get('business_outcomes', 0),
                            relationship_strength_score=health_scores.get('relationship_strength', 0),
                            total_kpis=health_scores.get('total_kpis', 0),
                            valid_kpis=health_scores.get('valid_kpis', 0)
                        )
                        db.session.add(new_trend)
                        db.session.commit()
                    logger.info(f"✅ Health score for account {account.account_name}: {overall_health_score:.1f}/100")
            except Exception as e:
                logger.warning(f"Error getting/calculating health score: {e}", exc_info=True)
        
        # Ensure numeric for agent (0-100); None becomes 0 only for display fallback
        if overall_health_score is not None:
            overall_health_score = max(0, min(100, float(overall_health_score)))
        
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
                # Determine if this is a DC customer by checking account vertical or DC2S KPIs
                is_dc_customer = False
                if account.vertical and account.vertical.lower() in ['dc2s', 'dc', 'datacenter']:
                    is_dc_customer = True
                else:
                    # Check if account has DC2S KPIs
                    dc_kpi_check = DC2SKPI.query.filter_by(account_id=account_id_int).first()
                    if dc_kpi_check:
                        is_dc_customer = True
                
                kpis = None
                dc_kpis = None
                
                if is_dc_customer:
                    # Get DC2S KPIs for Data Center accounts
                    logger.info(f"Fetching DC2S KPIs for account {account_id_int}")
                    dc_kpis = DC2SKPI.query.filter_by(
                        account_id=account_id_int
                    ).order_by(DC2SKPI.measured_at.desc()).limit(50).all()
                    logger.info(f"Found {len(dc_kpis)} DC2S KPIs for account {account_id_int}")
                else:
                    # Get SaaS KPIs for regular accounts
                    logger.info(f"Fetching SaaS KPIs for account {account_id_int}")
                    kpis = KPI.query.filter_by(
                        account_id=account_id_int,
                        customer_id=customer_id
                    ).limit(50).all()
                    logger.info(f"Found {len(kpis)} SaaS KPIs for account {account_id_int}")
                
                # Get account notes (account_id_int already validated above)
                notes = AccountNote.query.filter_by(
                    account_id=account_id_int,
                    customer_id=customer_id
                ).order_by(AccountNote.created_at.desc()).limit(20).all()
                
                # Get qualitative signals from QualitativeSignal table (from signals.csv uploads)
                from .qualitative_signal_converter import convert_qualitative_signals_to_signal_data
                qual_signals_from_db = QualitativeSignal.query.filter_by(
                    account_id=account_id_int
                ).order_by(QualitativeSignal.signal_date.desc()).limit(30).all()
                
                logger.info(f"Found {len(qual_signals_from_db)} qualitative signals from QualitativeSignal table for account {account_id_int}")
                
                # Convert qualitative signals to SignalData
                qual_signal_data = convert_qualitative_signals_to_signal_data(qual_signals_from_db)
                
                # Convert to signals (include health score for temporal grouping)
                db_signals = convert_database_models_to_signals(
                    account=account,
                    kpis=kpis,
                    dc_kpis=dc_kpis,
                    notes=notes,
                    account_health_score=overall_health_score
                )
                
                # Add qualitative signals from QualitativeSignal table
                db_signals['qualitative_signals'].extend(qual_signal_data)
                logger.info(f"Added {len(qual_signal_data)} qualitative signals from QualitativeSignal table")
                
                quantitative_signals.extend(db_signals['quantitative_signals'])
                qualitative_signals.extend(db_signals['qualitative_signals'])
                historical_patterns.extend(db_signals['historical_patterns'])
                
                logger.info(f"Converted {len(db_signals['quantitative_signals'])} quantitative signals from database")
                logger.info(f"Converted {len(db_signals['qualitative_signals'])} qualitative signals from database")
            
            except Exception as e:
                logger.warning(f"Error retrieving signals from database: {e}", exc_info=True)
        
        # ✅ DEDUPLICATE signals before sending to LLM
        # Prefer database source (has exact data, no embedding loss)
        quantitative_signals = deduplicate_signals(quantitative_signals, prefer_source='database')
        qualitative_signals = deduplicate_signals(qualitative_signals, prefer_source='database')
        historical_patterns = deduplicate_signals(historical_patterns, prefer_source='database')
        
        logger.info(
            f"Final signal counts after deduplication: "
            f"{len(quantitative_signals)} quantitative, "
            f"{len(qualitative_signals)} qualitative, "
            f"{len(historical_patterns)} historical patterns"
        )
        
        # Get OpenAI API key
        openai_api_key = get_openai_api_key(customer_id)
        if not openai_api_key:
            return jsonify({
                'error': 'OpenAI API key not configured. Please configure it in Settings > OpenAI Key Settings.'
            }), 400
        
        # Build agent input (include health score)
        agent_input = SignalAnalystInput(
            account_id=account_id,
            customer_id=customer_id,
            vertical_type=agent_vertical_type,
            account_name=account.account_name,
            account_arr=float(account.revenue) if account.revenue else None,
            health_score=overall_health_score,
            quantitative_signals=quantitative_signals,
            qualitative_signals=qualitative_signals,
            historical_patterns=historical_patterns,
            analysis_type=analysis_type,
            time_horizon_days=time_horizon_days
        )

        # Initialize agent — supports OpenAI (default) or Claude via provider param
        llm_provider = data.get('provider', 'openai').lower()
        llm_model = "gpt-4o"

        if llm_provider in ('anthropic', 'claude'):
            try:
                from .claude_signal_analyst_agent import ClaudeSignalAnalystAgent
                anthropic_key = os.getenv('ANTHROPIC_API_KEY')
                if not anthropic_key:
                    return jsonify({'error': 'ANTHROPIC_API_KEY not configured'}), 500
                llm_model = data.get('model', 'claude-sonnet-4-5-20250929')
                agent = ClaudeSignalAnalystAgent(
                    anthropic_api_key=anthropic_key,
                    model=llm_model,
                    temperature=0.3,
                    customer_id=customer_id,
                    account_id=str(account_id),
                )
            except ImportError:
                return jsonify({'error': 'Claude agent module not available'}), 500
        else:
            agent = SignalAnalystAgent(
                openai_api_key=openai_api_key,
                model="gpt-4o",
                temperature=0.3
            )

        # Run analysis
        analysis_result = agent.analyze(agent_input)

        # Convert to JSON-serializable format
        result_dict = analysis_result.model_dump()

        # Override with computed health score so report is never 0 when we have DC2_S/KPI data
        if overall_health_score is not None:
            agent_health = result_dict.get('health_score')
            result_dict['health_score'] = overall_health_score
            # If agent returned bogus values (0 health or 85% churn / 10% expansion), derive churn/expansion from real score
            bogus = (agent_health == 0 or agent_health is None) or (
                result_dict.get('churn_probability') == 85 and result_dict.get('expansion_probability') == 10
            )
            if bogus:
                hs = float(overall_health_score)
                result_dict['churn_probability'] = 80 if hs < 50 else (40 if hs < 70 else 15)
                result_dict['expansion_probability'] = 5 if hs < 50 else (30 if hs < 80 else 75)
        
        # Add API-level metadata
        import time
        result_dict['_metadata'] = {
            'endpoint': '/api/signal-analyst/analyze',
            'provider': llm_provider,
            'model': llm_model,
            'cost_tracked': True,
            'timestamp': time.time()
        }
        
        logger.info(
            "Returning analysis result to client",
            extra={
                'account_id': account_id,
                'response_size_bytes': len(str(result_dict))
            }
        )
        
        return jsonify(result_dict), 200
        
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

