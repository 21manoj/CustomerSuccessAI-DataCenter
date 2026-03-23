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

logger = logging.getLogger(__name__)

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
        "description": "Get revenue breakdown from context graph: at-risk, protected, expansion, lost. The ONLY authoritative source for revenue figures.",
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
        "name": "get_context_graph_mermaid",
        "description": "Generate a Mermaid flowchart of the context graph for an account. Shows signals, decisions, outcomes with causal edges. Use when asked to visualize or show the context graph.",
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
        "description": "Get chronological timeline of ALL context graph events for an account. Signals, decisions, outcomes in date order with revenue summary.",
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
]


# ─── Tool Dispatcher ─────────────────────────────────────────────────────────

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
        if tool_name == 'list_accounts':
            from mcp_server.cs_pulse_mcp_server import list_accounts
            return list_accounts(customer_id=customer_id)

        elif tool_name == 'get_account_health':
            from mcp_server.cs_pulse_mcp_server import get_account_health
            return get_account_health(customer_id=customer_id, account_id=tool_input['account_id'])

        elif tool_name == 'get_at_risk_accounts':
            from mcp_server.cs_pulse_mcp_server import get_at_risk_accounts
            return get_at_risk_accounts(customer_id=customer_id, threshold=tool_input.get('threshold', 70.0))

        elif tool_name == 'get_revenue_at_risk':
            from mcp_server.cs_pulse_intelligence import get_revenue_at_risk
            return get_revenue_at_risk(customer_id=customer_id, account_id=tool_input['account_id'])

        elif tool_name == 'get_context_graph_mermaid':
            from mcp_server.cs_pulse_intelligence import get_context_graph_mermaid
            return get_context_graph_mermaid(
                customer_id=customer_id,
                account_id=tool_input['account_id'],
                max_nodes=tool_input.get('max_nodes', 30)
            )

        elif tool_name == 'get_account_journey_timeline':
            from mcp_server.cs_pulse_intelligence import get_account_journey_timeline
            return get_account_journey_timeline(
                customer_id=customer_id,
                account_id=tool_input['account_id'],
                limit=tool_input.get('limit', 50)
            )

        elif tool_name == 'search_signals':
            from mcp_server.cs_pulse_intelligence import search_signals
            return search_signals(
                customer_id=customer_id,
                account_id=tool_input['account_id'],
                node_type=tool_input.get('node_type', 'SIGNAL'),
                node_subtype=tool_input.get('node_subtype'),
                limit=tool_input.get('limit', 20)
            )

        elif tool_name == 'get_stakeholder_map':
            from mcp_server.cs_pulse_intelligence import get_stakeholder_map
            return get_stakeholder_map(customer_id=customer_id, account_id=tool_input['account_id'])

        elif tool_name == 'get_csm_daily_actions':
            from mcp_server.cs_pulse_admin import get_csm_daily_actions
            return get_csm_daily_actions(customer_id=customer_id)

        elif tool_name == 'calculate_power_of_1':
            from mcp_server.cs_pulse_revenue import calculate_power_of_1
            return calculate_power_of_1(
                customer_id=customer_id,
                metric_id=tool_input['metric_id'],
                improvement_pct=tool_input.get('improvement_pct', 1.0)
            )

        elif tool_name == 'get_outcome_roi_story':
            from mcp_server.cs_pulse_revenue import get_outcome_roi_story
            return get_outcome_roi_story(
                customer_id=customer_id,
                account_id=tool_input['account_id'],
                target_improvement_pct=tool_input.get('target_improvement_pct', 10),
                projection_months=tool_input.get('projection_months', 12)
            )

        elif tool_name == 'get_playbook_recommendations':
            from mcp_server.cs_pulse_revenue import get_playbook_recommendations
            return get_playbook_recommendations(customer_id=customer_id, account_id=tool_input['account_id'])

        elif tool_name == 'get_portfolio_roi_summary':
            from mcp_server.cs_pulse_revenue import get_portfolio_roi_summary
            return get_portfolio_roi_summary(customer_id=customer_id)

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Tool execution error [{tool_name}]: {e}", exc_info=True)
        return {"error": f"Tool {tool_name} failed: {str(e)}"}


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
                        {'label': 'Revenue Protected', 'value': f"${hist.get('revenue_protected', 0):,.0f}", 'color': 'blue'},
                        {'label': 'Projected Impact', 'value': f"${proj.get('projected_impact', 0):,.0f}", 'color': 'cyan'},
                    ],
                })

    except Exception as e:
        logger.warning(f"Artifact extraction error [{tool_name}]: {e}")

    return artifacts
