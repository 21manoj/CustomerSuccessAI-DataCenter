#!/usr/bin/env python3
"""
Ask AI Tool Definitions & Dispatcher

Defines Claude tool schemas that mirror MCP tools, dispatches tool_use calls
to underlying Python functions (same process, no MCP transport), and extracts
structured artifacts from tool results for rich frontend rendering.

Behind feature flag: ASK_AI_V2
"""

import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

# Ensure mcp_server dir is on path for imports
_backend_dir = os.path.dirname(os.path.abspath(__file__))
_mcp_dir = os.path.join(_backend_dir, 'mcp_server')
if _mcp_dir not in sys.path:
    sys.path.insert(0, _mcp_dir)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Prefer MCP @mcp.tool implementations (same code path as external agents).
# Falls back to _execute_direct when fastmcp / MCP modules are unavailable (local dev).
def _mcp_stack_available() -> bool:
    try:
        import fastmcp  # noqa: F401
        import mcp_server.cs_pulse_mcp_server  # noqa: F401
        return True
    except ImportError:
        return False


_MCP_AVAILABLE = _mcp_stack_available()

# ─── Tool Definitions (Claude tool_use format) ───────────────────────────────
# Each mirrors an MCP tool but uses Claude's JSON Schema tool format.
# Only include tools useful for executive Q&A — skip admin/onboarding tools.

TOOL_DEFINITIONS = [
    {
        "name": "list_accounts",
        "description": "List all accounts with health scores for a customer. Use when the user asks about their portfolio, account list, or overall health.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer", "description": "The customer (tenant) ID"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_account_health",
        "description": "Get detailed health score and pillar breakdown (P1-P5) for a specific account. Use when asked about a specific account's health or pillar scores.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "account_id": {"type": "integer", "description": "The account to analyze"}
            },
            "required": ["customer_id", "account_id"]
        }
    },
    {
        "name": "get_at_risk_accounts",
        "description": "List accounts with health scores below a threshold. Use when asked about at-risk or critical accounts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "threshold": {"type": "number", "default": 70, "description": "Health score threshold"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_revenue_at_risk",
        "description": "Get revenue breakdown from context graph for ONE account: at-risk, protected, expansion, lost. Use this for per-account drill-down. For portfolio-wide breakdowns (\"biggest expansion upside in the portfolio\", \"total revenue at risk across the book\"), use get_portfolio_revenue_breakdown instead — it aggregates across all accounts in one call.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "account_id": {"type": "integer"}
            },
            "required": ["customer_id", "account_id"]
        }
    },
    {
        "name": "get_portfolio_revenue_breakdown",
        "description": "Get portfolio-wide revenue breakdown across ALL accounts in ONE call. Returns BOTH portfolio totals AND top-3 accounts per bucket. Use for any portfolio-level revenue/expansion/at-risk question — this single call gives you everything needed for synthesis without further per-account drilling. Returns: revenue_at_risk, revenue_protected, expansion_realized, expansion_approved (pipeline), expansion_pipeline (realized+approved), AND top_at_risk_accounts, top_expansion_accounts, top_protected_accounts (each with account_id, account_name, arr, amount, health_score). After calling this, do NOT loop get_revenue_at_risk per-account — top_*_accounts already contains the highest-impact accounts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_context_graph_mermaid",
        "description": "Generate a Mermaid flowchart of the context graph for an account. Shows signals, decisions, outcomes with causal edges. Use when asked to visualize or show the context graph. IMPORTANT: You must first call list_accounts to get the correct account_id — account_ids are large integers like 444002, not small numbers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "account_id": {"type": "integer"},
                "max_nodes": {"type": "integer", "default": 30, "description": "Max nodes (default 30, max 60)"}
            },
            "required": ["customer_id", "account_id"]
        }
    },
    {
        "name": "get_account_journey_timeline",
        "description": "Get chronological timeline of ALL context graph events for an account. Returns signals (including CS Pulse automation signals like playbook_triggered, health_score_alert, sla_started), decisions (with playbook code, action taken, outcome achieved), outcomes, and stakeholders — in date order with revenue summary. Use this to answer: what happened with this account, what signals did CS Pulse detect, which playbooks were run, what actions were taken, what was the outcome.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "account_id": {"type": "integer"},
                "limit": {"type": "integer", "default": 50}
            },
            "required": ["customer_id", "account_id"]
        }
    },
    {
        "name": "search_signals",
        "description": "Search for context graph nodes (signals, decisions, outcomes) for an account. Filter by node_type and subtype.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "account_id": {"type": "integer"},
                "node_type": {"type": "string", "default": "SIGNAL", "description": "SIGNAL, DECISION, OUTCOME, STAKEHOLDER"},
                "node_subtype": {"type": "string", "description": "e.g. kpi_change, ticket, champion_loss"},
                "limit": {"type": "integer", "default": 20}
            },
            "required": ["customer_id", "account_id"]
        }
    },
    {
        "name": "get_stakeholder_map",
        "description": "Get the stakeholder network for an account — who influenced which decisions and outcomes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "account_id": {"type": "integer"}
            },
            "required": ["customer_id", "account_id"]
        }
    },
    {
        "name": "get_csm_daily_actions",
        "description": "Get top-10 prioritized CSM actions across all accounts. Use for 'What should I do today?' or daily briefing questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_csm_scorecard",
        "description": "Per-CSM performance scorecard across the portfolio: accounts managed, total ARR exposure, health Δ (improvement/decline), accounts rescued (critical → healthy), accounts lost (healthy → critical), playbooks run, actions taken, revenue impact. Use for 'which CSMs need help', 'show me Sarah's scorecard', 'compare CSM performance', or any per-CSM aggregation question. Filter to one CSM with csm_name (case-insensitive substring). Without csm_name, returns all CSMs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "csm_name": {"type": "string", "description": "Optional CSM name filter (substring match)"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_csm_ranking",
        "description": "Rank CSMs comparatively across the portfolio by a chosen metric. Use for 'which CSM is performing best/worst', 'rank my team', 'who needs coaching'. Built on get_csm_scorecard but pre-sorted with rank #s. metric options: 'composite' (default), 'health_delta', 'revenue_impact', 'accounts_rescued', 'success_rate'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "metric": {"type": "string", "default": "composite", "description": "Metric to rank by: composite | health_delta | revenue_impact | accounts_rescued | success_rate"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_team_capacity",
        "description": "CS team capacity utilization: hours used vs available, role-by-role bottleneck detection (CSM, CS Ops, Product, Platform, Leadership). Use for 'are we over capacity', 'team capacity review', 'where's the bottleneck', 'do we have headroom'. Returns active playbook hours by role + utilization % + over-capacity flags.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "calculate_power_of_1",
        "description": "Calculate the revenue impact of a 1% improvement in a business metric (Power-of-1). Use for ROI or 'what if' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "metric_id": {"type": "string", "description": "e.g. NRR, GRR, product_adoption, expansion_rate"},
                "improvement_pct": {"type": "number", "default": 1.0}
            },
            "required": ["customer_id", "metric_id"]
        }
    },
    {
        "name": "get_outcome_roi_story",
        "description": "Generate a full ROI narrative with proof points, projections, and context graph insights for an account.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "account_id": {"type": "integer"},
                "target_improvement_pct": {"type": "number", "default": 10},
                "projection_months": {"type": "integer", "default": 12}
            },
            "required": ["customer_id", "account_id"]
        }
    },
    {
        "name": "get_playbook_recommendations",
        "description": "Get recommended playbooks for an account based on health score and signals.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "account_id": {"type": "integer"}
            },
            "required": ["customer_id", "account_id"]
        }
    },
    {
        "name": "get_portfolio_roi_summary",
        "description": "Get the complete ROI story for a customer portfolio — historical proof + forward projection. Use for CFO/board-level ROI questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "analyze_root_cause",
        "description": "Analyze the root cause of an account's health trajectory. Returns causal chain (trigger → symptom → response → outcome), contributing factors, stakeholder dynamics, and prediction. Use when asked 'Why is [account] declining?' or 'What caused [account]'s health drop?'. Requires WITH_LLM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "account_id": {"type": "integer", "description": "The account to analyze"}
            },
            "required": ["customer_id", "account_id"]
        }
    },
    {
        "name": "explain_kpi_anomaly",
        "description": "Explain why a specific KPI changed significantly. Correlates the KPI change with signals, decisions, and stakeholder events in the same timeframe. Use when asked 'Why did [KPI] drop?' or 'What caused the NPS decline?'. Requires WITH_LLM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "account_id": {"type": "integer", "description": "The account to analyze"},
                "kpi_code": {"type": "string", "description": "KPI code (e.g., P1-KPI1, P3-KPI2)"}
            },
            "required": ["customer_id", "account_id", "kpi_code"]
        }
    },
    {
        "name": "generate_action_plan",
        "description": "Generate a specific, time-bound action plan for an account. Returns named stakeholders, talking points with real numbers, deadlines, and ROI projections. Use when CSM asks 'What should I do about [account]?' or 'How do I save [account]?'. Requires WITH_LLM feature flag.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "account_id": {"type": "integer", "description": "The account to generate a plan for"},
                "planning_horizon_days": {"type": "integer", "description": "Planning horizon in days (default 90)", "default": 90}
            },
            "required": ["customer_id", "account_id"]
        }
    },
    {
        "name": "get_calibration_history",
        "description": "Get weight calibration history — how KPI and pillar weights evolved over time. Use for what-if analysis ('what if we weighted P3 higher?'), drift detection, or understanding how the health model changed. Shows Wizard C calibrations, manual overrides, and tier upgrades with before/after weights and correlation scores.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "limit": {"type": "integer", "default": 10, "description": "Max calibration records to return"}
            },
            "required": ["customer_id"]
        }
    },
    # ════════════════════════════════════════════════════════════════════════
    # NRR FORECAST TOOLS (Predictor v3 + Wizard B)
    # ════════════════════════════════════════════════════════════════════════
    # These five tools surface NRR forecasting via two distinct engines.
    # Naming + descriptions are explicit so the LLM picks the right tool:
    #
    #   FORWARD per-account → get_account_nrr_forecast
    #   FORWARD portfolio   → get_portfolio_nrr_forecast_v3
    #   BACKWARD with/without CS Pulse counterfactual → get_realized_nrr_counterfactual
    #   "Top expansion opportunities" / "Top at-risk accounts" → v3 rankers
    {
        "name": "get_account_nrr_forecast",
        "description": "Per-account FORWARD NRR forecast at horizon (renewal, quarter=3mo, or 12mo) from Predictor v3 (Wizard D-calibrated GLMM). Returns expected_nrr point + 90% CI bounds, term_decomposition (p_churn, p_survive, expand/contract %, top_drivers with feature contributions), expansion_outlook (probability of expansion event, expected size, ARR lift), and calibration_id provenance. Use this when the user asks 'what's account X's NRR forecast?', 'why is X predicted at Y%?', or wants to explain a per-account number. Use horizon='quarter' for 'this quarter' framing. DO NOT use for portfolio-level questions (use get_portfolio_nrr_forecast_v3) or backward counterfactual (use get_realized_nrr_counterfactual).",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer", "description": "The customer (tenant) ID that owns the account"},
                "account_id": {"type": "integer", "description": "The account_id to forecast"},
                "horizon": {"type": "string", "enum": ["renewal", "quarter", "12mo"], "default": "12mo", "description": "Forecast horizon: 'renewal' (contract-specific), 'quarter' (3mo), or '12mo' (default)"}
            },
            "required": ["customer_id", "account_id"]
        }
    },
    {
        "name": "get_portfolio_nrr_forecast_v3",
        "description": "Portfolio-level FORWARD NRR forecast (Predictor v3, ARR-weighted aggregate of per-account predictions). Returns arr_weighted_nrr_pct, simple_avg_nrr_pct, account_count (active + total), top_5_nrr accounts, bottom_5_nrr accounts, prediction_method_counts, and calibration_freshness. Use when the user asks 'what's our forward NRR?', 'what's the v3 portfolio forecast?', or wants the aggregate forecast number. Use horizon='quarter' for 'this quarter' framing. DIFFERENT FROM get_realized_nrr_counterfactual — that's backward counterfactual (with vs without CS Pulse).",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "horizon": {"type": "string", "enum": ["renewal", "quarter", "12mo"], "default": "12mo"}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_top_expansion_opportunities_v3",
        "description": "Top expansion opportunities — per-account ranked by Predictor v3 expected_arr_lift over the horizon. Each result entry includes account_id, account_name, ARR, expansion_outlook (expected_arr_lift, p_expansion_event_horizon, expected_size_pct_given_event), expansion_drivers (top feature contributions). Use when the user asks 'where should we focus expansion plays?', 'top expansion bets?', 'which accounts have highest upside?'. Use horizon='quarter' for 'this quarter' framing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "horizon": {"type": "string", "enum": ["renewal", "quarter", "12mo"], "default": "12mo"},
                "limit": {"type": "integer", "default": 5}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_top_at_risk_accounts_v3",
        "description": "Top at-risk accounts — per-account ranked by Predictor v3 forecast NRR ascending (lowest NRR = highest churn risk). Each result includes account_id, account_name, ARR, expected_nrr {point, lower_90, upper_90}, term_decomposition (p_churn, p_survive, e_contract_pct, e_expand_pct, top_drivers), forecast_arr_loss (projected ARR loss = ARR × (1 - expected_nrr)). Use when the user asks 'which accounts are most at-risk?', 'where should defensive playbooks fire?', 'what's hurting NRR most?'. Use horizon='quarter' to answer 'revenue at risk this quarter' — quarter-bounded ARR-at-risk runs ~25-30% of the 12mo number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "horizon": {"type": "string", "enum": ["renewal", "quarter", "12mo"], "default": "12mo"},
                "limit": {"type": "integer", "default": 5}
            },
            "required": ["customer_id"]
        }
    },
    {
        "name": "get_realized_nrr_counterfactual",
        "description": "Backward-looking REALIZED NRR with CS Pulse counterfactual delta (Wizard B). Returns with_cs_pulse_nrr_pct, without_cs_pulse_nrr_pct, delta_pct (= CS Pulse attributable lift), arr_protected, accounts_saved, plus a forward what-if (with_interventions_nrr_pct). DIFFERENT FROM get_portfolio_nrr_forecast_v3 — that's forward point forecast; this is backward counterfactual answering 'did CS Pulse improve NRR vs baseline?'. Use when the user asks 'what's our realized NRR?', 'what was the CS Pulse impact?', 'NRR with vs without CS Pulse?'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "months": {"type": "integer", "default": 3, "description": "Forecast horizon for the forward what-if (default 3, max 12)"}
            },
            "required": ["customer_id"]
        }
    },
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _portfolio_revenue_breakdown_enriched(customer_id: int) -> dict:
    """Backward-compat wrapper — delegates to shared util (MCP uses same path)."""
    from utils.portfolio_revenue_breakdown import build_portfolio_revenue_breakdown
    return build_portfolio_revenue_breakdown(customer_id)


def _call_mcp(module_path: str, fn_name: str, **kwargs) -> dict:
    """Import an MCP tool and invoke its underlying .fn implementation."""
    import importlib
    mod = importlib.import_module(module_path)
    return _invoke_mcp_tool(getattr(mod, fn_name), **kwargs)


# ─── Tool Dispatcher ─────────────────────────────────────────────────────────

def _invoke_mcp_tool(tool_fn, **kwargs):
    """Call impl behind @mcp.tool (FunctionTool is not directly callable)."""
    impl = getattr(tool_fn, 'fn', None)
    if impl is not None:
        return impl(**kwargs)
    return tool_fn(**kwargs)


def execute_tool(tool_name: str, tool_input: dict, customer_id: int) -> dict:
    """
    Dispatch a Claude tool_use call to the underlying Python function.
    Calls the same functions the MCP tools wrap — same process, no transport.

    Args:
        tool_name: Tool name from Claude's tool_use block
        tool_input: Tool input parameters from Claude
        customer_id: Authenticated customer ID (injected, not from Claude)

    Returns:
        Tool result as dict (JSON-serializable)
    """
    # Always inject customer_id for security — never trust Claude's input for it
    tool_input['customer_id'] = customer_id

    try:
        logger.info(
            f"execute_tool: {tool_name} input={tool_input} customer={customer_id} "
            f"mcp={_MCP_AVAILABLE}"
        )
        if _MCP_AVAILABLE:
            try:
                return _execute_via_mcp(tool_name, tool_input, customer_id)
            except ImportError as imp_err:
                logger.warning(f"MCP import failed for {tool_name}, using direct: {imp_err}")
        return _execute_direct(tool_name, tool_input, customer_id)

    except Exception as e:
        logger.error(f"Tool execution error [{tool_name}]: {e}", exc_info=True)
        return {"error": f"Tool {tool_name} failed: {str(e)}"}


def _execute_via_mcp(tool_name: str, tool_input: dict, customer_id: int) -> dict:
    """Execute via MCP @mcp.tool implementations (single source of truth)."""
    if tool_name == 'list_accounts':
        return _call_mcp('mcp_server.cs_pulse_mcp_server', 'list_accounts', customer_id=customer_id)
    if tool_name == 'get_account_health':
        return _call_mcp(
            'mcp_server.cs_pulse_mcp_server', 'get_account_health',
            customer_id=customer_id, account_id=tool_input['account_id'],
        )
    if tool_name == 'get_at_risk_accounts':
        return _call_mcp(
            'mcp_server.cs_pulse_mcp_server', 'get_at_risk_accounts',
            customer_id=customer_id, threshold=tool_input.get('threshold', 70.0),
        )
    if tool_name == 'get_revenue_at_risk':
        return _call_mcp(
            'mcp_server.cs_pulse_intelligence', 'get_revenue_at_risk',
            customer_id=customer_id, account_id=tool_input['account_id'],
        )
    if tool_name == 'get_portfolio_revenue_breakdown':
        return _call_mcp(
            'mcp_server.cs_pulse_intelligence', 'get_portfolio_revenue_breakdown',
            customer_id=customer_id,
        )
    if tool_name == 'get_context_graph_mermaid':
        return _call_mcp(
            'mcp_server.cs_pulse_intelligence', 'get_context_graph_mermaid',
            customer_id=customer_id, account_id=tool_input['account_id'],
            max_nodes=tool_input.get('max_nodes', 30),
        )
    if tool_name == 'get_account_journey_timeline':
        return _call_mcp(
            'mcp_server.cs_pulse_intelligence', 'get_account_journey_timeline',
            customer_id=customer_id, account_id=tool_input['account_id'],
            limit=tool_input.get('limit', 50),
        )
    if tool_name == 'search_signals':
        return _call_mcp(
            'mcp_server.cs_pulse_intelligence', 'search_signals',
            customer_id=customer_id, account_id=tool_input['account_id'],
            node_type=tool_input.get('node_type', 'SIGNAL'),
            node_subtype=tool_input.get('node_subtype'),
            limit=tool_input.get('limit', 20),
        )
    if tool_name == 'get_stakeholder_map':
        return _call_mcp(
            'mcp_server.cs_pulse_intelligence', 'get_stakeholder_map',
            customer_id=customer_id, account_id=tool_input['account_id'],
        )
    if tool_name == 'get_csm_daily_actions':
        return _call_mcp('mcp_server.cs_pulse_admin', 'get_csm_daily_actions', customer_id=customer_id)
    if tool_name == 'get_csm_scorecard':
        return _call_mcp(
            'mcp_server.cs_pulse_admin', 'get_csm_scorecard',
            customer_id=customer_id, csm_name=tool_input.get('csm_name'),
        )
    if tool_name == 'get_csm_ranking':
        return _call_mcp(
            'mcp_server.cs_pulse_admin', 'get_csm_ranking',
            customer_id=customer_id, metric=tool_input.get('metric', 'composite'),
        )
    if tool_name == 'get_team_capacity':
        return _call_mcp('mcp_server.cs_pulse_revenue', 'get_team_capacity', customer_id=customer_id)
    if tool_name == 'calculate_power_of_1':
        return _call_mcp(
            'mcp_server.cs_pulse_revenue', 'calculate_power_of_1',
            customer_id=customer_id, metric_id=tool_input['metric_id'],
            improvement_pct=tool_input.get('improvement_pct', 1.0),
        )
    if tool_name == 'get_outcome_roi_story':
        return _call_mcp(
            'mcp_server.cs_pulse_revenue', 'get_outcome_roi_story',
            customer_id=customer_id, account_id=tool_input['account_id'],
            target_improvement_pct=tool_input.get('target_improvement_pct', 10),
            projection_months=tool_input.get('projection_months', 12),
        )
    if tool_name == 'get_playbook_recommendations':
        return _call_mcp(
            'mcp_server.cs_pulse_revenue', 'get_playbook_recommendations',
            customer_id=customer_id, account_id=tool_input['account_id'],
        )
    if tool_name == 'get_portfolio_roi_summary':
        return _call_mcp(
            'mcp_server.cs_pulse_revenue', 'get_portfolio_roi_summary',
            customer_id=customer_id,
        )
    if tool_name == 'analyze_root_cause':
        return _call_mcp(
            'mcp_server.cs_pulse_intelligence', 'analyze_root_cause',
            customer_id=customer_id, account_id=tool_input['account_id'],
        )
    if tool_name == 'explain_kpi_anomaly':
        return _call_mcp(
            'mcp_server.cs_pulse_intelligence', 'explain_kpi_anomaly',
            customer_id=customer_id, account_id=tool_input['account_id'],
            kpi_code=tool_input['kpi_code'],
        )
    if tool_name == 'generate_action_plan':
        return _call_mcp(
            'mcp_server.cs_pulse_intelligence', 'generate_action_plan',
            customer_id=customer_id, account_id=tool_input['account_id'],
            planning_horizon_days=tool_input.get('planning_horizon_days', 90),
        )
    if tool_name == 'get_calibration_history':
        return _call_mcp(
            'mcp_server.cs_pulse_admin', 'get_calibration_history',
            customer_id=customer_id, limit=tool_input.get('limit', 10),
        )
    if tool_name == 'get_account_nrr_forecast':
        return _call_mcp(
            'mcp_server.cs_pulse_predictor', 'get_account_nrr_forecast',
            customer_id=customer_id, account_id=tool_input['account_id'],
            horizon=tool_input.get('horizon', '12mo'),
        )
    if tool_name == 'get_portfolio_nrr_forecast_v3':
        return _call_mcp(
            'mcp_server.cs_pulse_predictor', 'get_portfolio_nrr_forecast_v3',
            customer_id=customer_id, horizon=tool_input.get('horizon', '12mo'),
        )
    if tool_name == 'get_top_expansion_opportunities_v3':
        return _call_mcp(
            'mcp_server.cs_pulse_predictor', 'get_top_expansion_opportunities_v3',
            customer_id=customer_id, horizon=tool_input.get('horizon', '12mo'),
            limit=tool_input.get('limit', 5),
        )
    if tool_name == 'get_top_at_risk_accounts_v3':
        return _call_mcp(
            'mcp_server.cs_pulse_predictor', 'get_top_at_risk_accounts_v3',
            customer_id=customer_id, horizon=tool_input.get('horizon', '12mo'),
            limit=tool_input.get('limit', 5),
        )
    if tool_name == 'get_realized_nrr_counterfactual':
        return _call_mcp(
            'mcp_server.cs_pulse_revenue', 'get_nrr_forecast',
            customer_id=customer_id, months=tool_input.get('months', 3),
        )
    return {"error": f"Unknown tool: {tool_name}"}


def _execute_direct(tool_name: str, tool_input: dict, customer_id: int) -> dict:
    """Execute directly via DB queries (when fastmcp is NOT installed)."""
    from models import Account, HealthScore, PillarScore, ContextNode, ContextEdge, db
    import utils.health_thresholds as ht

    # Wave 1 Workstream A (Aug 4 2026): health reads go through the canonical
    # service. The old fallback code here defaulted missing scores to 0
    # (while Flask defaulted them to 50.0 and MCP computed them — three
    # different answers per surface, audit §4.7/F3), took pillar rows
    # without month-pinning, and did not exclude churned accounts from
    # at-risk lists (invariant violation).
    from utils.account_health import get_account_health as _canonical_health

    if tool_name == 'list_accounts':
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        result = []
        for a in accounts:
            ah = _canonical_health(a.account_id)
            result.append({
                'account_id': a.account_id,
                'account_name': a.account_name,
                'health_score': round(ah.health_score, 1) if ah.ok else None,
                'health_status': ah.health_status if ah.ok else 'no_data',
                'arr': float(a.revenue or 0),
                'industry': a.industry or '',
            })
        return {'accounts': sorted(result, key=lambda x: (x['health_score'] is None, x['health_score'] or 0)),
                'count': len(result)}

    elif tool_name == 'get_account_health':
        account_id = tool_input['account_id']
        ah = _canonical_health(account_id, customer_id=customer_id)
        if ah.missing and ah.missing_reason == 'not_found_or_wrong_tenant':
            return {"error": f"Account {account_id} not found"}
        acct = Account.query.filter_by(account_id=account_id, customer_id=customer_id).first()
        return {
            'account_id': account_id,
            'account_name': acct.account_name if acct else '',
            'health_score': round(ah.health_score, 1) if ah.ok else None,
            'health_status': ah.health_status if ah.ok else 'no_data',
            'health_data_missing': not ah.ok,
            'arr': float(acct.revenue or 0) if acct else 0,
            'pillar_scores': {k: round(v, 1) for k, v in ah.pillars.items()},
        }

    elif tool_name == 'get_at_risk_accounts':
        threshold = tool_input.get('threshold', 70.0)
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        result = []
        for a in accounts:
            # Churned accounts are surfaced separately, never in at-risk
            # (matches MCP get_at_risk_accounts + invariant suite).
            if (a.account_status or '').lower() == 'churned':
                continue
            ah = _canonical_health(a.account_id)
            if ah.ok and ah.health_score < threshold:
                result.append({
                    'account_id': a.account_id,
                    'account_name': a.account_name,
                    'health_score': round(ah.health_score, 1),
                    'health_status': ah.health_status,
                    'arr': float(a.revenue or 0),
                })
        return {'accounts': sorted(result, key=lambda x: x['health_score']), 'count': len(result), 'threshold': threshold}

    elif tool_name == 'get_revenue_at_risk':
        # Use the real get_revenue_at_risk from utils/context_graph.py
        # This has de-duplication logic and correct revenue counting rules
        # that the simplified OUTCOME-only query misses
        account_id = tool_input['account_id']
        try:
            from utils.context_graph import get_revenue_at_risk as _cg_revenue
            result = _cg_revenue(account_id)
            result['account_id'] = account_id
            # Normalize field names to match what artifact extractor expects
            result.setdefault('revenue_at_risk', result.get('at_risk', 0))
            result.setdefault('revenue_protected', result.get('protected', 0))
            result.setdefault('expansion_pipeline', result.get('expansion', 0))
            return result
        except Exception as e:
            logger.warning(f"context_graph.get_revenue_at_risk failed, falling back: {e}")
            # Fallback to simple query
            nodes = ContextNode.query.filter_by(customer_id=customer_id, account_id=account_id, node_type='OUTCOME').all()
            at_risk = sum(float(n.revenue_impact or 0) for n in nodes if n.revenue_impact_type == 'at_risk')
            protected = sum(float(n.revenue_impact or 0) for n in nodes if n.revenue_impact_type == 'protected')
            expansion = sum(float(n.revenue_impact or 0) for n in nodes if n.revenue_impact_type == 'expansion')
            lost = sum(float(n.revenue_impact or 0) for n in nodes if n.revenue_impact_type == 'lost')
            return {
                'account_id': account_id,
                'revenue_at_risk': at_risk,
                'revenue_protected': protected,
                'expansion_pipeline': expansion,
                'lost': lost,
            }

    elif tool_name == 'get_portfolio_revenue_breakdown':
        # Apr 26-27 2026 (Sprint 1.3 + Fix A — same enriched path as _execute_via_mcp).
        return _portfolio_revenue_breakdown_enriched(customer_id)

    elif tool_name == 'get_context_graph_mermaid':
        # Mermaid generation with subgraph grouping for proper vertical layout
        account_id = tool_input['account_id']
        max_nodes = tool_input.get('max_nodes', 30)

        # Strategy: fetch ALL edges for this account first, then pull connected nodes
        # This ensures we get causal chains, not random disconnected nodes
        all_nodes = ContextNode.query.filter_by(customer_id=customer_id, account_id=account_id).all()
        if not all_nodes:
            return {'mermaid': 'flowchart TD\n    empty["No context graph data"]', 'node_count': 0, 'edge_count': 0}

        all_node_ids = [n.node_id for n in all_nodes]
        node_lookup = {n.node_id: n for n in all_nodes}

        # Get all edges between this account's nodes
        edges = ContextEdge.query.filter(
            ContextEdge.from_node_id.in_(all_node_ids),
            ContextEdge.to_node_id.in_(all_node_ids)
        ).all()

        # Prioritize connected nodes (they form causal chains)
        connected_ids = set()
        for e in edges:
            connected_ids.add(e.from_node_id)
            connected_ids.add(e.to_node_id)

        # Build node list: connected nodes first, then fill with recent unconnected
        nodes = [node_lookup[nid] for nid in connected_ids if nid in node_lookup]
        remaining = [n for n in all_nodes if n.node_id not in connected_ids]
        remaining.sort(key=lambda n: n.occurred_at or '', reverse=True)
        nodes.extend(remaining[:max(0, max_nodes - len(nodes))])
        nodes = nodes[:max_nodes]

        node_ids = set(n.node_id for n in nodes)
        # Filter edges to only included nodes
        edges = [e for e in edges if e.from_node_id in node_ids and e.to_node_id in node_ids]

        # Group nodes by type for subgraph layout
        by_type = {'SIGNAL': [], 'DECISION': [], 'OUTCOME': [], 'STAKEHOLDER': []}
        node_map = {}
        for n in nodes:
            ntype = n.node_type or 'SIGNAL'
            by_type.setdefault(ntype, []).append(n)
            node_map[n.node_id] = n

        # Only include nodes that participate in edges, plus top 3 per type
        connected_ids = set()
        for e in edges:
            connected_ids.add(e.from_node_id)
            connected_ids.add(e.to_node_id)

        def _safe_label(title):
            """Escape quotes and limit length for Mermaid."""
            s = (title or 'Unknown')[:35].replace('"', "'").replace('\n', ' ')
            return s

        type_styles = {'SIGNAL': 'signal', 'DECISION': 'decision', 'OUTCOME': 'outcome', 'STAKEHOLDER': 'stakeholder'}
        subgraph_labels = {
            'SIGNAL': 'Signals & Events',
            'DECISION': 'Decisions',
            'OUTCOME': 'Outcomes',
            'STAKEHOLDER': 'Stakeholders',
        }

        lines = ['flowchart TD']
        lines.append('    classDef signal fill:#FFA500,stroke:#FFA500,color:#000')
        lines.append('    classDef decision fill:#4169E1,stroke:#4169E1,color:#fff')
        lines.append('    classDef outcome fill:#2E8B57,stroke:#2E8B57,color:#fff')
        lines.append('    classDef stakeholder fill:#8B5CF6,stroke:#8B5CF6,color:#fff')

        included_ids = set()
        # Emit subgraphs in causal order: Signals → Decisions → Outcomes
        for ntype in ['SIGNAL', 'DECISION', 'OUTCOME', 'STAKEHOLDER']:
            type_nodes = by_type.get(ntype, [])
            if not type_nodes:
                continue
            # Include all nodes we already selected (they're already prioritized)
            selected = type_nodes
            if not selected:
                continue

            cls = type_styles.get(ntype, 'signal')
            label = subgraph_labels.get(ntype, ntype)
            lines.append(f'    subgraph {ntype}["{label}"]')
            for n in selected[:8]:  # Cap per subgraph for readability
                lbl = _safe_label(n.title)
                lines.append(f'        n{n.node_id}["{lbl}"]:::{cls}')
                included_ids.add(n.node_id)
            lines.append('    end')

        # Emit edges (only between included nodes)
        for e in edges:
            if e.from_node_id in included_ids and e.to_node_id in included_ids:
                edge_label = (e.edge_type or '').replace('"', "'")[:20]
                lines.append(f'    n{e.from_node_id} -->|{edge_label}| n{e.to_node_id}')

        # If no edges, add invisible links between subgraphs for vertical flow
        if not edges:
            type_order = [t for t in ['SIGNAL', 'DECISION', 'OUTCOME', 'STAKEHOLDER'] if by_type.get(t)]
            for i in range(len(type_order) - 1):
                first_a = by_type[type_order[i]][0]
                first_b = by_type[type_order[i + 1]][0]
                if first_a.node_id in included_ids and first_b.node_id in included_ids:
                    lines.append(f'    n{first_a.node_id} -.-> n{first_b.node_id}')

        return {'mermaid': '\n'.join(lines), 'node_count': len(included_ids), 'edge_count': len(edges)}

    elif tool_name == 'get_account_journey_timeline':
        # REAL: includes revenue_summary (matches MCP output)
        account_id = tool_input['account_id']
        limit = tool_input.get('limit', 50)
        acct = Account.query.filter_by(account_id=account_id, customer_id=customer_id).first()
        nodes = ContextNode.query.filter_by(customer_id=customer_id, account_id=account_id).order_by(ContextNode.occurred_at.asc()).limit(limit).all()
        timeline = [{
            'node_id': n.node_id,
            'node_type': n.node_type,
            'node_subtype': n.node_subtype,
            'title': n.title,
            'occurred_at': n.occurred_at.isoformat() if n.occurred_at else None,
            'revenue_impact': float(n.revenue_impact) if n.revenue_impact else None,
            'revenue_impact_type': n.revenue_impact_type,
        } for n in nodes]
        # Add revenue_summary (same as MCP version)
        try:
            from utils.context_graph import get_revenue_at_risk as _cg_rev
            rev = _cg_rev(account_id)
        except Exception:
            rev = {}
        counts = {}
        for n in nodes:
            counts[n.node_type] = counts.get(n.node_type, 0) + 1
        return {
            'scope': 'account',
            'account_id': account_id,
            'account_name': acct.account_name if acct else str(account_id),
            'arr': float(acct.revenue or 0) if acct else 0,
            'event_count': len(timeline),
            'counts_by_type': counts,
            'revenue_summary': rev,
            'timeline': timeline,
        }

    elif tool_name == 'search_signals':
        account_id = tool_input['account_id']
        q = ContextNode.query.filter_by(customer_id=customer_id, account_id=account_id, node_type=tool_input.get('node_type', 'SIGNAL'))
        if tool_input.get('node_subtype'):
            q = q.filter_by(node_subtype=tool_input['node_subtype'])
        nodes = q.order_by(ContextNode.occurred_at.desc()).limit(tool_input.get('limit', 20)).all()
        return {'nodes': [{'node_id': n.node_id, 'title': n.title, 'node_type': n.node_type, 'node_subtype': n.node_subtype, 'occurred_at': n.occurred_at.isoformat() if n.occurred_at else None, 'revenue_impact': float(n.revenue_impact) if n.revenue_impact else None} for n in nodes], 'count': len(nodes)}

    elif tool_name == 'get_stakeholder_map':
        # REAL: includes influenced_decisions and influenced_outcomes (matches MCP)
        account_id = tool_input['account_id']
        acct = Account.query.filter_by(account_id=account_id, customer_id=customer_id).first()
        stakeholders = ContextNode.query.filter_by(customer_id=customer_id, account_id=account_id, node_type='STAKEHOLDER').all()
        decisions = ContextNode.query.filter_by(customer_id=customer_id, account_id=account_id, node_type='DECISION').all()
        outcomes = ContextNode.query.filter_by(customer_id=customer_id, account_id=account_id, node_type='OUTCOME').all()
        # Find INVOLVES edges from stakeholders to decisions/outcomes
        stk_ids = [s.node_id for s in stakeholders]
        dec_out_ids = [n.node_id for n in decisions + outcomes]
        involves_edges = []
        if stk_ids and dec_out_ids:
            involves_edges = ContextEdge.query.filter(
                ContextEdge.from_node_id.in_(stk_ids),
                ContextEdge.to_node_id.in_(dec_out_ids)
            ).all()
        # Build influence map
        stk_decisions = {}
        stk_outcomes = {}
        dec_ids_set = set(n.node_id for n in decisions)
        out_ids_set = set(n.node_id for n in outcomes)
        for e in involves_edges:
            if e.to_node_id in dec_ids_set:
                stk_decisions.setdefault(e.from_node_id, []).append(e.to_node_id)
            if e.to_node_id in out_ids_set:
                stk_outcomes.setdefault(e.from_node_id, []).append(e.to_node_id)
        result_stk = []
        for s in stakeholders:
            result_stk.append({
                'node_id': s.node_id,
                'title': s.title,
                'node_subtype': s.node_subtype,
                'properties': s.properties or {},
                'influenced_decisions': stk_decisions.get(s.node_id, []),
                'influenced_outcomes': stk_outcomes.get(s.node_id, []),
            })
        return {
            'scope': 'account',
            'account_id': account_id,
            'account_name': acct.account_name if acct else str(account_id),
            'stakeholder_count': len(result_stk),
            'stakeholders': result_stk,
        }

    elif tool_name == 'get_csm_daily_actions':
        # REAL: uses the same priority formula as MCP (impact × 0.6 × arr_weight - effort × 0.4)
        from _ask_ai_helpers import _resolve_customer_vertical, _get_health_functions, _get_playbook_config, _get_kpi_definitions
        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)
        PLAYBOOK_CONFIG, should_trigger_playbook = _get_playbook_config(vertical)
        KPI_DEFS = _get_kpi_definitions(vertical)
        try:
            from verticals.dc2_s.api_routes import (
                _normalize_kpi_code_for_health, _compute_impact_score,
                _compute_effort_score, _determine_urgency, _get_roi_context,
            )
        except ImportError:
            # Minimal fallback if dc2_s not available
            return {"actions": [], "summary": {"total_actions": 0}}

        from datetime import datetime as _dt
        accounts = Account.query.filter(Account.customer_id == int(customer_id)).all()
        all_actions = []
        for account in accounts:
            precalc_health, precalc_status, precalc_pillars = get_precalculated_scores(account.account_id)
            trailing_kpis = _get_trailing_kpi_values(account.account_id, days=30)
            if precalc_health is not None:
                overall_health = precalc_health
                pillar_averages = precalc_pillars or {}
            else:
                overall_health, pillar_averages = calculate_kpi_health(trailing_kpis, customer_id=customer_id)
            normalized_kpis = {}
            for code, val in trailing_kpis.items():
                norm = _normalize_kpi_code_for_health(code)
                if norm:
                    normalized_kpis[norm] = val
            normalized_kpis['OVERALL_HEALTH'] = overall_health
            arr = float(account.revenue or 0)
            arr_weight = 1.5 if arr > 10_000_000 else (1.3 if arr > 5_000_000 else (1.1 if arr > 2_000_000 else (1.0 if arr > 0 else 0.8)))
            h_cls = ht.classify(overall_health)
            churn_prob = 80 if h_cls == 'critical' else (40 if h_cls == 'at_risk' else 15)
            expansion_prob = 75 if h_cls == 'healthy' else (30 if h_cls == 'at_risk' else 5)
            for pb_id, pb_cfg in PLAYBOOK_CONFIG.items():
                if should_trigger_playbook(pb_id, normalized_kpis):
                    impact = _compute_impact_score(overall_health, churn_prob, expansion_prob, pillar_averages)
                    effort = _compute_effort_score(pb_cfg)
                    priority_index = round((impact * 0.6 * arr_weight) - (effort * 0.4), 1)
                    total_hours = sum(s.get('estimated_hours', 0) for s in pb_cfg.get('sub_components', []))
                    roi_ctx = _get_roi_context('playbook', pb_id, arr)
                    _meta = account.profile_metadata if isinstance(account.profile_metadata, dict) else {}
                    all_actions.append({
                        'account_id': account.account_id,
                        'account_name': account.account_name,
                        'assigned_csm': _meta.get('assigned_csm') or _meta.get('csm_name') or 'Unassigned',
                        'action_title': f"Start {pb_cfg['name']} Playbook",
                        'action_type': 'playbook',
                        'related_playbook_id': pb_id,
                        'urgency': _determine_urgency(overall_health, churn_prob, expansion_prob),
                        'impact_score': impact,
                        'effort_score': effort,
                        'priority_index': priority_index,
                        'account_health': round(overall_health, 1),
                        'estimated_hours': total_hours,
                        **roi_ctx,
                    })
        all_actions.sort(key=lambda x: x.get('priority_index', 0), reverse=True)
        top = all_actions[:10]
        return {
            'scope': 'portfolio',
            'date': _dt.utcnow().strftime('%Y-%m-%d'),
            'actions': top,
            'summary': {
                'total_actions': len(top),
                'critical_count': sum(1 for a in top if a.get('urgency') == 'critical'),
                'high_count': sum(1 for a in top if a.get('urgency') == 'high'),
                'opportunity_count': sum(1 for a in top if a.get('urgency') == 'opportunity'),
                'total_estimated_hours': sum(a.get('estimated_hours', 0) for a in top),
                'total_roi_projected_impact': sum(a.get('projected_dollar_impact', 0) for a in top),
            },
        }

    elif tool_name == 'get_csm_scorecard':
        # Apr 26 2026 (Phase 1): direct path delegates to MCP impl since
        # the underlying logic (Account.profile_metadata.assigned_csm
        # grouping + HealthScore deltas + PlaybookExecutionV2 attribution)
        # is already implemented there with the right field knowledge.
        from mcp_server.cs_pulse_admin import get_csm_scorecard
        return _invoke_mcp_tool(
            get_csm_scorecard,
            customer_id=customer_id,
            csm_name=tool_input.get('csm_name'),
        )
    elif tool_name == 'get_csm_ranking':
        from mcp_server.cs_pulse_admin import get_csm_ranking
        return _invoke_mcp_tool(
            get_csm_ranking,
            customer_id=customer_id,
            metric=tool_input.get('metric', 'composite'),
        )
    elif tool_name == 'get_team_capacity':
        from mcp_server.cs_pulse_revenue import get_team_capacity
        return _invoke_mcp_tool(get_team_capacity, customer_id=customer_id)

    elif tool_name == 'calculate_power_of_1':
        # REAL: calls power_of_1_model.calculate_power_of_1_impact()
        from power_of_1_model import calculate_power_of_1_impact
        metric_id = tool_input['metric_id']
        improvement_pct = tool_input.get('improvement_pct', 1.0)
        account_arr = tool_input.get('account_arr')
        if not account_arr:
            accounts = Account.query.filter_by(customer_id=customer_id).all()
            account_arr = sum(float(a.revenue or 0) for a in accounts)
        result = calculate_power_of_1_impact(metric_id, improvement_pct, account_arr)
        if not result:
            return {"error": f"Unknown metric: {metric_id}"}
        return {
            'scope': 'portfolio',
            'metric_id': metric_id,
            'improvement_pct': improvement_pct,
            'arr_basis': account_arr,
            **result,
        }

    elif tool_name == 'get_outcome_roi_story':
        # REAL: calls outcome_roi_engine.calculate_outcome_story()
        account_id = tool_input['account_id']
        target_pct = tool_input.get('target_improvement_pct', 1.0)
        projection_months = tool_input.get('projection_months', 6)
        acct = Account.query.filter_by(account_id=account_id, customer_id=customer_id).first()
        if not acct:
            return {"error": f"Account {account_id} not found"}
        arr = float(acct.revenue or 0)
        try:
            from outcome_roi_api import _extract_historical_actuals
            metric_actuals, _ds = _extract_historical_actuals([acct], 6, customer_id=customer_id)
        except Exception:
            metric_actuals = {}
        try:
            from outcome_roi_engine import calculate_outcome_story
            result = calculate_outcome_story(
                customer_id=customer_id,
                account_arr=arr,
                metric_actuals=metric_actuals,
                target_improvement_pct=target_pct,
                projection_months=projection_months,
            )
            from outcome_roi_engine import _result_to_dict
            return _result_to_dict(result) if not isinstance(result, dict) else result
        except Exception as e:
            logger.warning(f"ROI story failed: {e}")
            return {"error": f"ROI calculation failed: {str(e)}"}

    elif tool_name == 'get_playbook_recommendations':
        # REAL: uses playbook trigger logic + health data
        account_id = tool_input['account_id']
        acct = Account.query.filter_by(account_id=account_id, customer_id=customer_id).first()
        if not acct:
            return {"error": f"Account {account_id} not found"}
        from _ask_ai_helpers import _resolve_customer_vertical, _get_health_functions, _get_playbook_config
        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)
        PLAYBOOK_CONFIG, should_trigger_playbook = _get_playbook_config(vertical)
        precalc_health, _, precalc_pillars = get_precalculated_scores(account_id)
        trailing = _get_trailing_kpi_values(account_id, days=30)
        if precalc_health is not None:
            health = precalc_health
            pillars = precalc_pillars or {}
        else:
            health, pillars = calculate_kpi_health(trailing, customer_id=customer_id)
        try:
            from utils.vertical_health import normalize_kpi_code
            _normalize_kpi_code_for_health = lambda c: normalize_kpi_code(c, customer_id)
        except ImportError:
            _normalize_kpi_code_for_health = lambda c: c
        normalized = {}
        for code, val in trailing.items():
            norm = _normalize_kpi_code_for_health(code)
            if norm:
                normalized[norm] = val
        normalized['OVERALL_HEALTH'] = health
        recs = []
        for pb_id, pb_cfg in PLAYBOOK_CONFIG.items():
            if should_trigger_playbook(pb_id, normalized):
                triggers = []
                for tk in pb_cfg.get('trigger_kpis', []):
                    if tk in normalized:
                        triggers.append({'kpi': tk, 'value': round(normalized[tk], 1)})
                recs.append({
                    'playbook_id': pb_id,
                    'playbook_name': pb_cfg.get('name', pb_id),
                    'priority': pb_cfg.get('priority', 'medium'),
                    'estimated_impact': pb_cfg.get('estimated_impact', ''),
                    'triggers': triggers,
                })
        return {
            'scope': 'account',
            'account_id': account_id,
            'account_name': acct.account_name,
            'health_score': round(health, 1),
            'recommendations': recs,
            'recommendation_count': len(recs),
        }

    elif tool_name == 'get_portfolio_roi_summary':
        # Use the SAME calculation as the CFO dashboard for consistency
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        total_arr = sum(float(a.revenue or 0) for a in accounts)
        try:
            from executive_dashboard_api import (
                _get_po1_benchmark_investment,
                _get_po1_benchmark_metrics,
            )
            investment = _get_po1_benchmark_investment(total_arr)
            po1_metrics = _get_po1_benchmark_metrics(total_arr, customer_id)
            total_impact = sum(m.get('dollar_impact', 0) for m in po1_metrics)
            roi_pct = round((total_impact - investment) / investment * 100) if investment > 0 else 0
            payback_months = round(investment / (total_impact / 12), 1) if total_impact > 0 else 0

            # Derive NRR from health (same formula as CRO dashboard)
            from models import HealthScore
            from sqlalchemy import func as sqlfunc
            account_ids = [a.account_id for a in accounts]
            latest_sub = (
                db.session.query(
                    HealthScore.account_id,
                    sqlfunc.max(HealthScore.measurement_month).label('max_month')
                )
                .filter(HealthScore.account_id.in_(account_ids))
                .group_by(HealthScore.account_id)
                .subquery()
            )
            health_rows = (
                db.session.query(HealthScore)
                .join(latest_sub, db.and_(
                    HealthScore.account_id == latest_sub.c.account_id,
                    HealthScore.measurement_month == latest_sub.c.max_month
                ))
                .all()
            )
            health_map = {h.account_id: float(h.health_score) for h in health_rows}
            scores = list(health_map.values())
            # Revenue-weighted avg health (same as CRO dashboard)
            revenue_map = {a.account_id: float(a.revenue or 0) for a in accounts}
            weighted_sum = sum(health_map.get(aid, 0) * revenue_map.get(aid, 0) for aid in account_ids)
            total_rev = sum(revenue_map.get(aid, 0) for aid in account_ids)
            avg_health = round(weighted_sum / total_rev, 1) if total_rev > 0 else (round(sum(scores) / len(scores), 1) if scores else 50)
            if avg_health >= 70:
                nrr = round(100 + (avg_health - 70) * 0.33)
            elif avg_health >= 40:
                nrr = round(90 + (avg_health - 40) * 0.33)
            else:
                nrr = round(85 + avg_health * 0.125)

            return {
                'scope': 'portfolio',
                'customer_id': customer_id,
                'total_arr': total_arr,
                'account_count': len(accounts),
                'cs_investment': investment,
                'cs_investment_label': 'Power-of-1 benchmark estimate (TSIA, Gainsight, KeyBanc)',
                'projected_impact': total_impact,
                'roi_pct': roi_pct,
                'roi_per_dollar': round(total_impact / investment, 2) if investment > 0 else 0,
                'payback_months': payback_months,
                'cs_pct_of_arr': round(investment / total_arr * 100, 2) if total_arr > 0 else 0,
                'nrr_current': nrr,
                'nrr_note': f'NRR {nrr}% derived from portfolio health score {avg_health}. This is the authoritative NRR — do NOT use 105% benchmark baseline.',
                'avg_health_score': avg_health,
                'metrics': [{
                    'metric': m['display_name'],
                    'baseline': m['baseline'],
                    'projected': m['current'],
                    'improvement': '1.0%',
                    'dollar_impact': m['dollar_impact'],
                } for m in po1_metrics],
                'note': 'All figures are Power-of-1 benchmark projections. '
                        'A 1% improvement across all metrics yields the projected impact. '
                        'These numbers match the CFO Investment Intelligence dashboard exactly.',
            }
        except Exception as e:
            logger.warning(f"Portfolio ROI (CFO-aligned) failed: {e}")
            return {"error": f"Portfolio ROI calculation failed: {str(e)}"}

    # ─── NRR forecast tools (Predictor v3 + Wizard B) — direct dispatch ───
    # Same backing functions as the MCP-path branches above; identical
    # behavior regardless of whether fastmcp is installed.
    elif tool_name == 'get_account_nrr_forecast':
        try:
            from predictor.inference import predict_for_account_id
            from models import Account
            account_id = tool_input.get('account_id')
            horizon = tool_input.get('horizon', '12mo')
            if not account_id:
                return {"error": "account_id is required"}
            if horizon not in ('renewal', 'quarter', '12mo'):
                return {"error": f"horizon must be 'renewal', 'quarter', or '12mo', got {horizon!r}"}
            # Tenant isolation: confirm the account belongs to the session's
            # customer before forecasting. Matches the MCP path's auth check.
            owned = Account.query.filter_by(
                account_id=int(account_id),
                customer_id=int(customer_id),
            ).first()
            if not owned:
                return {"error": f"Account {account_id} not found for customer {customer_id}"}
            return predict_for_account_id(account_id=int(account_id), horizon=horizon)
        except Exception as e:
            logger.warning(f"get_account_nrr_forecast failed: {e}")
            return {"error": f"Predictor v3 per-account forecast failed: {str(e)}"}

    elif tool_name == 'get_portfolio_nrr_forecast_v3':
        try:
            from mcp_server.cs_pulse_predictor import get_portfolio_nrr_forecast_v3 as _t
            impl = getattr(_t, 'fn', _t)
            return impl(
                customer_id=customer_id,
                horizon=tool_input.get('horizon', '12mo'),
            )
        except Exception as e:
            logger.warning(f"get_portfolio_nrr_forecast_v3 failed: {e}")
            return {"error": f"Predictor v3 portfolio forecast failed: {str(e)}"}

    elif tool_name == 'get_top_expansion_opportunities_v3':
        try:
            from mcp_server.cs_pulse_predictor import get_top_expansion_opportunities_v3 as _t
            impl = getattr(_t, 'fn', _t)
            return impl(
                customer_id=customer_id,
                horizon=tool_input.get('horizon', '12mo'),
                limit=tool_input.get('limit', 5),
            )
        except Exception as e:
            logger.warning(f"get_top_expansion_opportunities_v3 failed: {e}")
            return {"error": f"Top expansion v3 failed: {str(e)}"}

    elif tool_name == 'get_top_at_risk_accounts_v3':
        try:
            from mcp_server.cs_pulse_predictor import get_top_at_risk_accounts_v3 as _t
            impl = getattr(_t, 'fn', _t)
            return impl(
                customer_id=customer_id,
                horizon=tool_input.get('horizon', '12mo'),
                limit=tool_input.get('limit', 5),
            )
        except Exception as e:
            logger.warning(f"get_top_at_risk_accounts_v3 failed: {e}")
            return {"error": f"Top at-risk v3 failed: {str(e)}"}

    elif tool_name == 'get_realized_nrr_counterfactual':
        try:
            from mcp_server.cs_pulse_revenue import get_nrr_forecast as _t
            impl = getattr(_t, 'fn', _t)
            return impl(
                customer_id=customer_id,
                months=tool_input.get('months', 3),
            )
        except Exception as e:
            logger.warning(f"get_realized_nrr_counterfactual failed: {e}")
            return {"error": f"Wizard B counterfactual failed: {str(e)}"}

    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ─── Calibration History ─────────────────────────────────────────────────────

def _get_calibration_history(customer_id: int, limit: int = 10) -> dict:
    """Fallback when MCP stack unavailable — same util as MCP tool."""
    from utils.calibration_history import fetch_calibration_history
    return fetch_calibration_history(customer_id, limit=limit)


# ─── Artifact Extraction ─────────────────────────────────────────────────────

def extract_artifacts(tool_name: str, tool_result: dict) -> list:
    """
    Convert a tool result into renderable artifact(s) for the frontend.

    Returns a list of artifact dicts (usually 1, sometimes 0 or 2+).
    Each artifact has: type, title, and type-specific fields.
    """
    if 'error' in tool_result:
        return []

    artifacts = []

    try:
        if tool_name == 'get_context_graph_mermaid':
            mermaid_code = tool_result.get('mermaid', '')
            if mermaid_code:
                artifacts.append({
                    'type': 'mermaid',
                    'title': f"Context Graph ({tool_result.get('node_count', '?')} nodes)",
                    'content': mermaid_code,
                })

        elif tool_name == 'list_accounts':
            accounts = tool_result.get('accounts', [])
            if accounts:
                artifacts.append({
                    'type': 'table',
                    'title': f"Portfolio Accounts ({len(accounts)})",
                    'columns': ['Account', 'Health', 'Status', 'ARR', 'Industry'],
                    'rows': [
                        [a.get('account_name', ''), a.get('health_score', 0),
                         a.get('health_status', ''), f"${a.get('arr', a.get('revenue', 0)):,.0f}",
                         a.get('industry', '')]
                        for a in accounts
                    ],
                })

        elif tool_name == 'get_at_risk_accounts':
            accounts = tool_result.get('accounts', [])
            if accounts:
                artifacts.append({
                    'type': 'table',
                    'title': f"At-Risk Accounts ({len(accounts)})",
                    'columns': ['Account', 'Health', 'ARR', 'Days At Risk'],
                    'rows': [
                        [a.get('account_name', ''), a.get('health_score', 0),
                         f"${a.get('arr', a.get('revenue', 0)):,.0f}",
                         a.get('days_at_risk', '')]
                        for a in accounts
                    ],
                })

        elif tool_name == 'get_revenue_at_risk':
            artifacts.append({
                'type': 'metric_card',
                'title': 'Revenue Intelligence',
                'metrics': [
                    {'label': 'At Risk', 'value': f"${tool_result.get('revenue_at_risk', 0):,.0f}", 'color': 'red'},
                    {'label': 'Protected', 'value': f"${tool_result.get('revenue_protected', 0):,.0f}", 'color': 'green'},
                    {'label': 'Expansion', 'value': f"${tool_result.get('expansion_pipeline', 0):,.0f}", 'color': 'blue'},
                ],
            })

        elif tool_name == 'get_account_health':
            pillar_data = tool_result.get('pillars', tool_result.get('pillar_scores', {}))
            if pillar_data:
                artifacts.append({
                    'type': 'chart',
                    'title': f"Health Breakdown — {tool_result.get('account_name', 'Account')}",
                    'chart_type': 'bar',
                    'data': [
                        {'name': k, 'score': round(v, 1) if isinstance(v, (int, float)) else v}
                        for k, v in (pillar_data.items() if isinstance(pillar_data, dict) else [])
                    ],
                })

        elif tool_name == 'get_account_journey_timeline':
            timeline = tool_result.get('timeline', [])
            if timeline:
                artifacts.append({
                    'type': 'table',
                    'title': f"Journey Timeline ({len(timeline)} events)",
                    'columns': ['Date', 'Type', 'Title', 'Revenue Impact'],
                    'rows': [
                        [
                            (e.get('occurred_at', '')[:10] if e.get('occurred_at') else ''),
                            e.get('node_type', ''),
                            e.get('title', ''),
                            f"${e.get('revenue_impact', 0):,.0f}" if e.get('revenue_impact') else '',
                        ]
                        for e in timeline[:30]  # Cap for readability
                    ],
                })

        elif tool_name == 'get_stakeholder_map':
            stakeholders = tool_result.get('stakeholders', [])
            if stakeholders:
                artifacts.append({
                    'type': 'table',
                    'title': f"Stakeholder Map ({len(stakeholders)})",
                    'columns': ['Name', 'Role', 'Influence', 'Sentiment', 'Engagement'],
                    'rows': [
                        [
                            s.get('title', ''),
                            (s.get('properties', {}) or {}).get('role', ''),
                            (s.get('properties', {}) or {}).get('influence', ''),
                            (s.get('properties', {}) or {}).get('sentiment', ''),
                            (s.get('properties', {}) or {}).get('engagement_level', ''),
                        ]
                        for s in stakeholders
                    ],
                })

        elif tool_name == 'get_csm_daily_actions':
            actions = tool_result.get('actions', [])
            if actions:
                artifacts.append({
                    'type': 'table',
                    'title': f"Today's Actions ({len(actions)})",
                    'columns': ['Priority', 'Account', 'Action', 'Impact', 'Effort'],
                    'rows': [
                        [
                            a.get('urgency', ''),
                            a.get('account_name', ''),
                            a.get('action', a.get('playbook_name', '')),
                            a.get('dollar_impact', ''),
                            f"{a.get('effort_hours', '')}h",
                        ]
                        for a in actions
                    ],
                })

        elif tool_name == 'calculate_power_of_1':
            artifacts.append({
                'type': 'metric_card',
                'title': f"Power of 1% — {tool_result.get('metric_id', 'Metric')}",
                'metrics': [
                    {'label': 'Portfolio Impact', 'value': f"${tool_result.get('portfolio_impact', 0):,.0f}", 'color': 'green'},
                    {'label': 'Per-Customer', 'value': f"${tool_result.get('dollar_impact_per_customer', 0):,.0f}", 'color': 'blue'},
                ],
            })

        elif tool_name == 'get_portfolio_roi_summary':
            hist = tool_result.get('historical', {})
            proj = tool_result.get('projection', {})
            if hist or proj:
                artifacts.append({
                    'type': 'metric_card',
                    'title': 'Portfolio ROI Summary',
                    'metrics': [
                        {'label': 'Historical ROI', 'value': f"{hist.get('roi_pct', 0):.0f}%", 'color': 'green'},
                        # NOT the context-graph OUTCOME rollup (that one is
                        # customer-reported/unverified — see executive_dashboard_api.py).
                        # This is calculate_historical_roi()'s figure: real
                        # measured KPI improvement run through the Po1 benchmark
                        # $-per-point rate — the KPI move is real, the $ conversion is modeled.
                        {'label': 'Revenue Protected (Modeled from KPI Actuals)', 'value': f"${hist.get('revenue_protected', 0):,.0f}", 'color': 'blue'},
                        {'label': 'Projected Impact', 'value': f"${proj.get('projected_impact', 0):,.0f}", 'color': 'cyan'},
                    ],
                })

    except Exception as e:
        logger.warning(f"Artifact extraction error [{tool_name}]: {e}")

    return artifacts
