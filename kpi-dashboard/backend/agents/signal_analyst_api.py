"""
Signal Analyst Agent API

Flask Blueprint for Signal Analyst Agent endpoints
"""

from flask import Blueprint, request, jsonify
from auth_middleware import get_current_customer_id
from extensions import db
from models import Account, KPI, AccountNote, Customer, DC2SKPI, QualitativeSignal
try:
    from enhanced_rag_qdrant import get_qdrant_rag_system
except ImportError:
    get_qdrant_rag_system = None
from openai_key_utils import get_openai_api_key

from .signal_analyst_agent import SignalAnalystAgent, AnalysisError, ResponseParseError
from .models import SignalAnalystInput, SignalData
from .vertical_mapper import map_vertical_to_agent_type
try:
    from .qdrant_integration import (
        get_quantitative_signals_from_qdrant,
        get_qualitative_signals_from_qdrant,
        get_historical_patterns_from_qdrant,
        convert_qdrant_results_to_signal_data
    )
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False
    def get_quantitative_signals_from_qdrant(*a, **kw): return []
    def get_qualitative_signals_from_qdrant(*a, **kw): return []
    def get_historical_patterns_from_qdrant(*a, **kw): return []
    def convert_qdrant_results_to_signal_data(*a, **kw): return []

from .signal_converter import convert_database_models_to_signals
from .signal_deduplicator import deduplicate_signals

import logging
import os
from datetime import datetime, timedelta
from sqlalchemy import func

logger = logging.getLogger(__name__)

# ── Signal lookback configuration ──────────────────────────────────────────
# Both quantitative and qualitative signals use the SAME time window
# so the analyst sees a consistent snapshot of the account.
SIGNAL_LOOKBACK_MONTHS = 3
SIGNAL_MAX_QUANT = 500   # safety cap to avoid LLM context overflow
SIGNAL_MAX_QUAL  = 100


def _signal_date_cutoff(account_id_int: int) -> 'datetime | None':
    """Return the start of the 3-month lookback window for an account.

    Anchored to the most recent DC2S KPI measurement so it works with
    both synthetic (2024) and live data.  Returns None if no data found.
    """
    latest = db.session.query(func.max(DC2SKPI.measured_at)).filter_by(
        account_id=account_id_int
    ).scalar()
    if latest is None:
        return None
    # 3 calendar months back (approximate: 91 days)
    return latest - timedelta(days=SIGNAL_LOOKBACK_MONTHS * 30 + 1)


signal_analyst_api = Blueprint('signal_analyst_api', __name__)

# Import entitlement gating (graceful fallback if not available)
try:
    from entitlements import require_entitlement, check_entitlement
except ImportError:
    # Fallback: no-op decorator if entitlements module unavailable
    def require_entitlement(feature_name):
        def decorator(f):
            return f
        return decorator
    def check_entitlement(customer_id, feature_name):
        return True


@signal_analyst_api.route('/api/signal-analyst/analyze', methods=['POST'])
@require_entitlement('signal_analyst')
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
        
        # Extract and validate account_id (accepts integer or UUID)
        account_id_raw = data.get('account_id')
        if not account_id_raw:
            return jsonify({'error': 'account_id is required'}), 400

        # Try integer first, then UUID resolution
        account = None
        account_id_int = None
        try:
            account_id_int = int(account_id_raw)
            if account_id_int <= 0:
                return jsonify({'error': 'Invalid account_id: must be a positive integer'}), 400
            account = Account.query.filter_by(
                account_id=account_id_int,
                customer_id=customer_id
            ).first()
        except (ValueError, TypeError):
            # May be a UUID — try resolving
            try:
                from uuid_utils import resolve_account
                account = resolve_account(account_id_raw, customer_id=customer_id, allow_none=True)
                if account:
                    account_id_int = account.account_id
            except Exception as e:
                logger.warning(f"UUID resolution failed for account_id: {e}")

        if not account or not account_id_int:
            return jsonify({'error': 'Account not found'}), 404

        account_id = str(account_id_int)  # Convert to string for consistency
        
        # Get vertical type from customer
        vertical = 'saas_premium'  # Default
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
                logger.warning(f"Could not load pillar weights, using catalog defaults: {e}")
                try:
                    from verticals.dc2_s.kpi_definitions import DC2S_PILLARS
                    pillar_weights = {p: v.get('weight_l2', 0.20) for p, v in DC2S_PILLARS.items()}
                except Exception:
                    pillar_weights = {'P1': 0.15, 'P2': 0.20, 'P3': 0.25, 'P4': 0.15, 'P5': 0.25}
        
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
        
        # DC2_S: resolve health score from the most recent source
        # Two sources: DC2SKPI (raw KPIs) and health_trends (pre-computed scores).
        # Use whichever has the more recent timestamp.
        if vertical in ('dc2_s', 'saas_premium', 'saas'):
            try:
                from models import DC2SKPI, HealthTrend as HT
                from utils.vertical_health import get_health_calculator
                calculate_kpi_health = get_health_calculator(customer_id)

                # Source 1: DC2SKPI — calculate from latest raw KPIs
                dc2s_score = None
                dc2s_date = None
                kpis = DC2SKPI.query.filter_by(account_id=account_id_int).order_by(DC2SKPI.measured_at.desc()).all()
                latest_kpis = {}
                for kpi in kpis:
                    if kpi.kpi_code not in latest_kpis:
                        latest_kpis[kpi.kpi_code] = kpi
                kpi_values = {kpi_code: float(kpi.value) for kpi_code, kpi in latest_kpis.items()}
                if kpi_values:
                    dc2s_score, _ = calculate_kpi_health(kpi_values, customer_id=customer_id)
                    dc2s_score = round(float(dc2s_score), 1)
                    # Latest KPI measurement date
                    dc2s_date = max(k.measured_at for k in latest_kpis.values()) if latest_kpis else None

                # Source 2: health_trends — pre-computed monthly score
                ht_score = None
                ht_date = None
                ht = HT.query.filter_by(account_id=account_id_int).order_by(
                    HT.year.desc(), HT.month.desc()
                ).first()
                if ht and ht.overall_health_score:
                    ht_score = round(float(ht.overall_health_score), 1)
                    # Build comparable date without datetime() constructor
                    # (avoids shadowing from 'from datetime import datetime' in SaaS fallback below)
                    from datetime import date as _date
                    ht_date = _date(ht.year, ht.month, 1)

                # Pick the more recent source
                if dc2s_score is not None and ht_score is not None:
                    if ht_date and dc2s_date and ht_date > (dc2s_date.date() if hasattr(dc2s_date, 'date') else dc2s_date):
                        overall_health_score = ht_score
                        logger.info(f"DC2_S: Using health_trends ({ht_date.date()}) score={ht_score} "
                                    f"over stale DC2SKPI ({dc2s_date.date()}) score={dc2s_score}")
                    else:
                        overall_health_score = dc2s_score
                        logger.info(f"DC2_S health score for account {account_id}: {dc2s_score}/100 (from DC2SKPI)")
                elif dc2s_score is not None:
                    overall_health_score = dc2s_score
                    logger.info(f"DC2_S health score for account {account_id}: {dc2s_score}/100 (from DC2SKPI)")
                elif ht_score is not None:
                    overall_health_score = ht_score
                    logger.info(f"DC2_S: No KPI data, using health_trends score: {ht_score}/100")
                else:
                    logger.info(f"DC2_S: No KPI data or health_trends for account {account_id}")
            except Exception as e:
                logger.warning(f"DC2_S health score calculation failed: {e}", exc_info=True)
        
        # SaaS / fallback: HealthTrend and HealthScoreStorageService
        if overall_health_score is None:
            try:
                from models import HealthTrend
                from health_score_storage import HealthScoreStorageService

                health_trend = HealthTrend.query.filter_by(
                    account_id=account_id_int,
                    customer_id=customer_id
                ).order_by(HealthTrend.year.desc(), HealthTrend.month.desc()).first()
                
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

                # Unified 3-month lookback window for ALL signal types
                cutoff = _signal_date_cutoff(account_id_int)
                if cutoff:
                    logger.info(f"Signal lookback: {SIGNAL_LOOKBACK_MONTHS}mo window, cutoff={cutoff.date()} for account {account_id_int}")

                if is_dc_customer:
                    # Get DC2S KPIs for Data Center accounts
                    logger.info(f"Fetching DC2S KPIs for account {account_id_int}")
                    q = DC2SKPI.query.filter_by(account_id=account_id_int)
                    if cutoff:
                        q = q.filter(DC2SKPI.measured_at >= cutoff)
                    dc_kpis = q.order_by(DC2SKPI.measured_at.desc()).limit(SIGNAL_MAX_QUANT).all()
                    logger.info(f"Found {len(dc_kpis)} DC2S KPIs for account {account_id_int}")
                else:
                    # Get SaaS KPIs for regular accounts
                    logger.info(f"Fetching SaaS KPIs for account {account_id_int}")
                    kpis = KPI.query.filter_by(
                        account_id=account_id_int,
                        customer_id=customer_id
                    ).limit(SIGNAL_MAX_QUANT).all()
                    logger.info(f"Found {len(kpis)} SaaS KPIs for account {account_id_int}")

                # Get account notes within the same window
                notes_q = AccountNote.query.filter_by(
                    account_id=account_id_int,
                    customer_id=customer_id
                ).order_by(AccountNote.created_at.desc())
                if cutoff:
                    notes_q = notes_q.filter(AccountNote.created_at >= cutoff)
                notes = notes_q.limit(SIGNAL_MAX_QUAL).all()

                # Get qualitative signals within the same window
                from .qualitative_signal_converter import convert_qualitative_signals_to_signal_data
                qual_q = QualitativeSignal.query.filter_by(account_id=account_id_int)
                if cutoff:
                    qual_q = qual_q.filter(QualitativeSignal.signal_date >= cutoff)
                qual_signals_from_db = qual_q.order_by(
                    QualitativeSignal.signal_date.desc()
                ).limit(SIGNAL_MAX_QUAL).all()

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
        
        # ── Context Graph signals (ContextNode / ContextEdge) ──────────────────
        try:
            from models import ContextNode, ContextEdge
            from feature_toggles import is_context_graph_enabled

            if is_context_graph_enabled(customer_id):
                cg_nodes = ContextNode.query.filter_by(account_id=account_id_int).all()
                if cg_nodes:
                    # Summarise node types
                    type_counts = {}
                    for n in cg_nodes:
                        type_counts[n.node_type] = type_counts.get(n.node_type, 0) + 1

                    # OUTCOME nodes → quantitative (revenue impact)
                    outcomes = [n for n in cg_nodes if n.node_type == 'OUTCOME']
                    for n in outcomes:
                        rev = float(n.revenue_impact or 0)
                        quantitative_signals.append(SignalData(
                            similarity=0.95,
                            payload={
                                'signal_type': 'context_graph_outcome',
                                'signal_source': 'context_graph',
                                'text': f"Context Graph OUTCOME: {n.title} | type={n.node_subtype} | revenue_impact=${rev:,.0f} | impact_type={n.revenue_impact_type or 'unknown'}",
                                'revenue_impact': rev,
                                'outcome_subtype': n.node_subtype,
                            }
                        ))

                    # DECISION nodes → qualitative
                    decisions = [n for n in cg_nodes if n.node_type == 'DECISION']
                    for n in decisions:
                        rev = float(n.revenue_impact or 0)
                        qualitative_signals.append(SignalData(
                            similarity=0.90,
                            payload={
                                'signal_type': 'context_graph_decision',
                                'signal_source': 'context_graph',
                                'text': f"Context Graph DECISION: {n.title} | revenue_impact=${rev:,.0f}",
                            }
                        ))

                    # STAKEHOLDER nodes → context only (not qualitative)
                    # Stakeholders are static entities, not time-varying signals.
                    # Including them in qualitative_signals pollutes the sentiment
                    # bucket with stale data (and their sentiment doesn't flow into
                    # the payload correctly anyway). Instead, stakeholder context is
                    # included in the context_graph_summary for LLM narrative use.
                    stakeholders = [n for n in cg_nodes if n.node_type == 'STAKEHOLDER']

                    # SIGNAL nodes (top 15 by recency) → qualitative
                    signal_nodes = sorted(
                        [n for n in cg_nodes if n.node_type == 'SIGNAL'],
                        key=lambda n: n.occurred_at or n.created_at or datetime.min,
                        reverse=True
                    )[:15]
                    for n in signal_nodes:
                        props = n.properties or {}
                        qualitative_signals.append(SignalData(
                            similarity=0.80,
                            payload={
                                'signal_type': 'context_graph_signal',
                                'signal_source': 'context_graph',
                                'text': f"Context Graph SIGNAL: {n.title} | subtype={n.node_subtype} | sentiment={props.get('sentiment', 'unknown')}",
                            }
                        ))

                    # Summary signal with revenue — use deduplicated totals
                    # (consistent with get_revenue_at_risk, avoids double-counting)
                    from utils.context_graph import get_revenue_at_risk as _gar
                    _rev = _gar(account_id_int)
                    expansion_rev = _rev.get('expansion', 0)
                    protected_rev = _rev.get('protected', 0)
                    total_rev = expansion_rev + protected_rev

                    # Build stakeholder context (included here, not in qual signals)
                    stakeholder_details = []
                    for n in stakeholders:
                        props = n.properties or {}
                        stakeholder_details.append(
                            f"{n.title} (role={n.node_subtype}, sentiment={props.get('sentiment', 'unknown')})"
                        )
                    stakeholder_text = (
                        f" Key stakeholders: {'; '.join(stakeholder_details[:5])}."
                        if stakeholder_details else ""
                    )

                    quantitative_signals.append(SignalData(
                        similarity=1.0,
                        payload={
                            'signal_type': 'context_graph_summary',
                            'signal_source': 'context_graph',
                            'text': (
                                f"Context Graph Summary: {len(cg_nodes)} nodes "
                                f"({', '.join(f'{t}={c}' for t, c in sorted(type_counts.items()))}). "
                                f"Total outcome revenue=${total_rev:,.0f} "
                                f"(expansion=${expansion_rev:,.0f}, protected=${protected_rev:,.0f}). "
                                f"{len(stakeholders)} stakeholders, {len(decisions)} decisions."
                                f"{stakeholder_text}"
                            ),
                        }
                    ))

                    logger.info(f"Added {len(outcomes)} outcome + {len(decisions)} decision + "
                                f"{len(stakeholders)} stakeholder + {len(signal_nodes)} signal nodes from context graph")
        except Exception as e:
            logger.warning(f"Error retrieving context graph signals: {e}", exc_info=True)

        # ── Health trend history (last 6 months) ─────────────────────────────
        try:
            from models import HealthTrend as HT
            trends = HT.query.filter_by(account_id=account_id_int).order_by(
                HT.year.desc(), HT.month.desc()
            ).limit(6).all()
            if trends:
                trend_text_parts = []
                for t in reversed(trends):  # chronological order
                    trend_text_parts.append(f"{t.year}-{t.month:02d}: {float(t.overall_health_score):.1f}")
                trend_direction = "improving" if len(trends) >= 2 and float(trends[0].overall_health_score) > float(trends[-1].overall_health_score) else "declining"
                historical_patterns.append(SignalData(
                    similarity=1.0,
                    payload={
                        'signal_type': 'health_trend_history',
                        'signal_source': 'database',
                        'text': (
                            f"Health Score Trend ({trend_direction}): "
                            f"{' → '.join(trend_text_parts)}. "
                            f"Latest actual score: {float(trends[0].overall_health_score):.1f}/100."
                        ),
                    }
                ))
                logger.info(f"Added health trend history: {len(trends)} months, direction={trend_direction}")
        except Exception as e:
            logger.warning(f"Error retrieving health trend history: {e}", exc_info=True)

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
        
        # Add UUID fields to response
        try:
            from uuid_utils import enrich_with_uuid
            result_dict = enrich_with_uuid(result_dict, account)
        except Exception as e:
            logger.warning(f"Failed to enrich response with UUID: {e}")

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


@signal_analyst_api.route('/api/signal-analyst/analyze-with-loop', methods=['POST'])
@require_entitlement('agent_loop')
def analyze_with_agentic_loop():
    """
    Run the full agentic loop: Analyze → Evaluate → Enrich → Quantify → Decide → Act.

    Same input as /analyze but returns enriched output with:
    - $ impact on every recommendation (via Power of 1)
    - Confidence-gated decision (auto_execute / needs_review / rejected)
    - Shared memory storage for cross-agent intelligence
    - Event publishing for coordination

    Request body: same as /api/signal-analyst/analyze
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 401

        data = request.json or {}
        account_id_raw = data.get('account_id')
        if not account_id_raw:
            return jsonify({'error': 'account_id is required'}), 400

        # Accept integer or UUID
        account = None
        account_id_int = None
        try:
            account_id_int = int(account_id_raw)
            account = Account.query.filter_by(
                account_id=account_id_int, customer_id=customer_id
            ).first()
        except (ValueError, TypeError):
            try:
                from uuid_utils import resolve_account
                account = resolve_account(account_id_raw, customer_id=customer_id, allow_none=True)
                if account:
                    account_id_int = account.account_id
            except Exception as e:
                logger.warning(f"UUID resolution failed for account_id: {e}")

        if not account or not account_id_int:
            return jsonify({'error': 'Account not found'}), 404

        account_id = str(account_id_int)

        # Get ARR
        account_arr = float(account.revenue) if account.revenue else None

        # Build the same SignalAnalystInput as /analyze
        # (reuse the existing signal gathering logic)
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

        from agent_tool_registry import get_tool_registry, register_all_tools
        from agent_loop import AgenticLoop, loop_state_to_dict

        # Initialize tool registry
        registry = register_all_tools()

        # Get the analyze function — create agent instance
        openai_key = get_openai_api_key(customer_id)
        if not openai_key:
            return jsonify({'error': 'OpenAI API key not configured'}), 500

        agent = SignalAnalystAgent(
            openai_api_key=openai_key,
            customer_id=customer_id,
            account_id=account_id,
        )

        # Build input data (simplified — uses Qdrant signals)
        vertical = 'saas'
        try:
            from models import CustomerConfig
            config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
            if config and config.vertical:
                vertical = config.vertical
        except Exception:
            pass

        agent_vertical_type = map_vertical_to_agent_type(vertical)

        # Gather signals from Qdrant
        quantitative_signals = []
        qualitative_signals = []
        historical_patterns = []

        try:
            rag_system = get_qdrant_rag_system(customer_id)
            if rag_system:
                quant_raw = get_quantitative_signals_from_qdrant(rag_system, account_id)
                quantitative_signals = convert_qdrant_results_to_signal_data(quant_raw)
                qual_raw = get_qualitative_signals_from_qdrant(rag_system, account_id)
                qualitative_signals = convert_qdrant_results_to_signal_data(qual_raw)
                hist_raw = get_historical_patterns_from_qdrant(rag_system, account_id)
                historical_patterns = convert_qdrant_results_to_signal_data(hist_raw)
        except Exception as e:
            logger.warning(f"Qdrant signal retrieval failed: {e}")

        # Fallback to DB if no Qdrant signals
        if not quantitative_signals and not qualitative_signals:
            try:
                # Unified 3-month lookback window (same as /analyze path)
                cutoff = _signal_date_cutoff(account_id_int)
                if cutoff:
                    logger.info(f"Agentic loop: {SIGNAL_LOOKBACK_MONTHS}mo window, cutoff={cutoff.date()} for account {account_id}")

                dc_kpis = None
                kpis = None
                notes = None
                try:
                    is_dc = account.vertical and account.vertical.lower() in ['dc2s', 'dc2_s', 'dc', 'datacenter']
                    if not is_dc:
                        dc_check = DC2SKPI.query.filter_by(account_id=account_id_int).first()
                        is_dc = dc_check is not None

                    if is_dc:
                        q = DC2SKPI.query.filter_by(account_id=account_id_int)
                        if cutoff:
                            q = q.filter(DC2SKPI.measured_at >= cutoff)
                        dc_kpis = q.order_by(DC2SKPI.measured_at.desc()).limit(SIGNAL_MAX_QUANT).all()
                        logger.info(f"Agentic loop: loaded {len(dc_kpis)} DC2S KPIs for account {account_id}")
                    else:
                        kpis = KPI.query.filter_by(account_id=account_id_int, customer_id=customer_id).limit(SIGNAL_MAX_QUANT).all()

                    notes_q = AccountNote.query.filter_by(account_id=account_id_int, customer_id=customer_id).order_by(AccountNote.created_at.desc())
                    if cutoff:
                        notes_q = notes_q.filter(AccountNote.created_at >= cutoff)
                    notes = notes_q.limit(SIGNAL_MAX_QUAL).all()
                except Exception as e2:
                    logger.warning(f"DB model query failed: {e2}")

                db_signals = convert_database_models_to_signals(
                    account=account,
                    kpis=kpis,
                    dc_kpis=dc_kpis,
                    notes=notes,
                    account_health_score=None,
                )
                quantitative_signals = db_signals.get('quantitative', db_signals.get('quantitative_signals', []))
                qualitative_signals = db_signals.get('qualitative', db_signals.get('qualitative_signals', []))

                # Also query QualitativeSignal table within the same window
                try:
                    from .qualitative_signal_converter import convert_qualitative_signals_to_signal_data
                    qual_q = QualitativeSignal.query.filter_by(account_id=account_id_int)
                    if cutoff:
                        qual_q = qual_q.filter(QualitativeSignal.signal_date >= cutoff)
                    qual_signals_from_db = qual_q.order_by(
                        QualitativeSignal.signal_date.desc()
                    ).limit(SIGNAL_MAX_QUAL).all()
                    if qual_signals_from_db:
                        qual_signal_data = convert_qualitative_signals_to_signal_data(qual_signals_from_db)
                        qualitative_signals.extend(qual_signal_data)
                        logger.info(f"Agentic loop: added {len(qual_signal_data)} qualitative signals from QualitativeSignal table")
                except Exception as eq:
                    logger.warning(f"QualitativeSignal query failed in agentic loop: {eq}")

                logger.info(f"Agentic loop DB signals: {len(quantitative_signals)} quant, {len(qualitative_signals)} qual")
            except Exception as e:
                logger.warning(f"DB signal conversion failed: {e}")

        input_data = SignalAnalystInput(
            account_id=account_id,
            customer_id=customer_id,
            vertical_type=agent_vertical_type,
            account_name=getattr(account, 'company_name', None) or getattr(account, 'account_name', None) or getattr(account, 'name', f'Account-{account_id}'),
            account_arr=account_arr,
            health_score=None,
            quantitative_signals=quantitative_signals,
            qualitative_signals=qualitative_signals,
            historical_patterns=historical_patterns,
            analysis_type=data.get('analysis_type', 'comprehensive'),
            time_horizon_days=data.get('time_horizon_days', 60),
        )

        # Get event publisher if available
        event_publisher = None
        try:
            from app_v3_minimal import event_publisher as ep
            event_publisher = ep
        except ImportError:
            pass

        # Run the agentic loop
        loop = AgenticLoop(
            analyze_fn=agent.analyze,
            tool_registry=registry,
            event_publisher=event_publisher,
        )

        state = loop.run(
            customer_id=customer_id,
            account_id=account_id,
            input_data=input_data,
            account_arr=account_arr,
        )

        response_data = {
            'agentic_loop': loop_state_to_dict(state),
            'initial_analysis': state.initial_analysis,
            '_metadata': {
                'endpoint': '/api/signal-analyst/analyze-with-loop',
                'agentic': True,
                'tools_called': state.tools_called,
                'duration_ms': state.duration_ms,
            },
        }

        # Add UUID fields to response
        try:
            from uuid_utils import enrich_with_uuid
            response_data = enrich_with_uuid(response_data, account)
        except Exception as e:
            logger.warning(f"Failed to enrich agentic loop response with UUID: {e}")

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Agentic loop error: {e}", exc_info=True)
        return jsonify({'error': 'Agentic analysis failed. Please try again later.'}), 500


@signal_analyst_api.route('/api/signal-analyst/test', methods=['POST'])
@require_entitlement('signal_analyst')
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

