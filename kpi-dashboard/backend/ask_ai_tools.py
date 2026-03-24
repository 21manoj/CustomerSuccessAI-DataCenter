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

# The MCP modules require fastmcp at import time. If not installed,
# we fall back to calling the underlying utility functions directly.
_MCP_AVAILABLE = False
try:
    # Test if fastmcp is available (needed by cs_pulse_mcp_server)
    import fastmcp  # noqa: F401
    _MCP_AVAILABLE = True
except ImportError:
    logger.info("fastmcp not installed — Ask AI tools will use direct DB queries")

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
        logger.info(f"execute_tool: {tool_name} input={tool_input} customer={customer_id} mcp={_MCP_AVAILABLE}")
        # Route to the appropriate implementation
        if _MCP_AVAILABLE:
            return _execute_via_mcp(tool_name, tool_input, customer_id)
        else:
            return _execute_direct(tool_name, tool_input, customer_id)

    except Exception as e:
        logger.error(f"Tool execution error [{tool_name}]: {e}", exc_info=True)
        return {"error": f"Tool {tool_name} failed: {str(e)}"}


def _execute_via_mcp(tool_name: str, tool_input: dict, customer_id: int) -> dict:
    """Execute via MCP module functions (when fastmcp is installed)."""
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
        return get_context_graph_mermaid(customer_id=customer_id, account_id=tool_input['account_id'], max_nodes=tool_input.get('max_nodes', 30))
    elif tool_name == 'get_account_journey_timeline':
        from mcp_server.cs_pulse_intelligence import get_account_journey_timeline
        return get_account_journey_timeline(customer_id=customer_id, account_id=tool_input['account_id'], limit=tool_input.get('limit', 50))
    elif tool_name == 'search_signals':
        from mcp_server.cs_pulse_intelligence import search_signals
        return search_signals(customer_id=customer_id, account_id=tool_input['account_id'], node_type=tool_input.get('node_type', 'SIGNAL'), node_subtype=tool_input.get('node_subtype'), limit=tool_input.get('limit', 20))
    elif tool_name == 'get_stakeholder_map':
        from mcp_server.cs_pulse_intelligence import get_stakeholder_map
        return get_stakeholder_map(customer_id=customer_id, account_id=tool_input['account_id'])
    elif tool_name == 'get_csm_daily_actions':
        from mcp_server.cs_pulse_admin import get_csm_daily_actions
        return get_csm_daily_actions(customer_id=customer_id)
    elif tool_name == 'calculate_power_of_1':
        from mcp_server.cs_pulse_revenue import calculate_power_of_1
        return calculate_power_of_1(customer_id=customer_id, metric_id=tool_input['metric_id'], improvement_pct=tool_input.get('improvement_pct', 1.0))
    elif tool_name == 'get_outcome_roi_story':
        from mcp_server.cs_pulse_revenue import get_outcome_roi_story
        return get_outcome_roi_story(customer_id=customer_id, account_id=tool_input['account_id'], target_improvement_pct=tool_input.get('target_improvement_pct', 10), projection_months=tool_input.get('projection_months', 12))
    elif tool_name == 'get_playbook_recommendations':
        from mcp_server.cs_pulse_revenue import get_playbook_recommendations
        return get_playbook_recommendations(customer_id=customer_id, account_id=tool_input['account_id'])
    elif tool_name == 'get_portfolio_roi_summary':
        from mcp_server.cs_pulse_revenue import get_portfolio_roi_summary
        return get_portfolio_roi_summary(customer_id=customer_id)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def _execute_direct(tool_name: str, tool_input: dict, customer_id: int) -> dict:
    """Execute directly via DB queries (when fastmcp is NOT installed)."""
    from models import Account, HealthScore, PillarScore, ContextNode, ContextEdge, db
    import utils.health_thresholds as ht

    if tool_name == 'list_accounts':
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        result = []
        for a in accounts:
            hs = HealthScore.query.filter_by(account_id=a.account_id).order_by(HealthScore.measurement_month.desc()).first()
            score = float(hs.health_score) if hs else 0
            result.append({
                'account_id': a.account_id,
                'account_name': a.account_name,
                'health_score': round(score, 1),
                'health_status': ht.classify(score),
                'arr': float(a.revenue or 0),
                'industry': a.industry or '',
            })
        return {'accounts': sorted(result, key=lambda x: x['health_score']), 'count': len(result)}

    elif tool_name == 'get_account_health':
        account_id = tool_input['account_id']
        acct = Account.query.filter_by(account_id=account_id, customer_id=customer_id).first()
        if not acct:
            return {"error": f"Account {account_id} not found"}
        hs = HealthScore.query.filter_by(account_id=account_id).order_by(HealthScore.measurement_month.desc()).first()
        score = float(hs.health_score) if hs else 0
        # Get pillar scores: try PillarScore table, fallback to HealthScore.contributing_pillars
        pillars = PillarScore.query.filter_by(account_id=account_id).order_by(PillarScore.measurement_month.desc()).all()
        seen = {}
        for p in pillars:
            if p.pillar_code not in seen:
                seen[p.pillar_code] = round(float(p.pillar_score), 1)
        # Fallback: HealthScore.contributing_pillars JSON field
        if not seen and hs and hs.contributing_pillars:
            seen = {k: round(float(v), 1) for k, v in hs.contributing_pillars.items()}
        return {
            'account_id': account_id,
            'account_name': acct.account_name,
            'health_score': round(score, 1),
            'health_status': ht.classify(score),
            'arr': float(acct.revenue or 0),
            'pillar_scores': seen,
        }

    elif tool_name == 'get_at_risk_accounts':
        threshold = tool_input.get('threshold', 70.0)
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        result = []
        for a in accounts:
            hs = HealthScore.query.filter_by(account_id=a.account_id).order_by(HealthScore.measurement_month.desc()).first()
            score = float(hs.health_score) if hs else 0
            if score < threshold:
                result.append({
                    'account_id': a.account_id,
                    'account_name': a.account_name,
                    'health_score': round(score, 1),
                    'health_status': ht.classify(score),
                    'arr': float(a.revenue or 0),
                })
        return {'accounts': sorted(result, key=lambda x: x['health_score']), 'count': len(result), 'threshold': threshold}

    elif tool_name == 'get_revenue_at_risk':
        account_id = tool_input['account_id']
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
        account_id = tool_input['account_id']
        limit = tool_input.get('limit', 50)
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
        return {'account_id': account_id, 'timeline': timeline, 'event_count': len(timeline)}

    elif tool_name == 'search_signals':
        account_id = tool_input['account_id']
        q = ContextNode.query.filter_by(customer_id=customer_id, account_id=account_id, node_type=tool_input.get('node_type', 'SIGNAL'))
        if tool_input.get('node_subtype'):
            q = q.filter_by(node_subtype=tool_input['node_subtype'])
        nodes = q.order_by(ContextNode.occurred_at.desc()).limit(tool_input.get('limit', 20)).all()
        return {'nodes': [{'node_id': n.node_id, 'title': n.title, 'node_type': n.node_type, 'node_subtype': n.node_subtype, 'occurred_at': n.occurred_at.isoformat() if n.occurred_at else None, 'revenue_impact': float(n.revenue_impact) if n.revenue_impact else None} for n in nodes], 'count': len(nodes)}

    elif tool_name == 'get_stakeholder_map':
        account_id = tool_input['account_id']
        nodes = ContextNode.query.filter_by(customer_id=customer_id, account_id=account_id, node_type='STAKEHOLDER').all()
        return {'stakeholders': [{'node_id': n.node_id, 'title': n.title, 'node_subtype': n.node_subtype, 'properties': n.properties or {}} for n in nodes], 'stakeholder_count': len(nodes)}

    elif tool_name == 'get_csm_daily_actions':
        # Simplified: return at-risk accounts as action items
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        actions = []
        for a in accounts:
            hs = HealthScore.query.filter_by(account_id=a.account_id).order_by(HealthScore.measurement_month.desc()).first()
            score = float(hs.health_score) if hs else 50
            if score < ht.healthy_min():
                urgency = 'critical' if score < ht.at_risk_min() else 'high'
                actions.append({
                    'account_name': a.account_name,
                    'account_id': a.account_id,
                    'health_score': round(score, 1),
                    'urgency': urgency,
                    'action': f"Review health for {a.account_name} (score: {round(score, 1)})",
                    'dollar_impact': f"${a.revenue or 0:,.0f}",
                })
        return {'actions': sorted(actions, key=lambda x: x['health_score'])[:10], 'count': len(actions)}

    elif tool_name in ('calculate_power_of_1', 'get_outcome_roi_story', 'get_playbook_recommendations', 'get_portfolio_roi_summary'):
        # These require complex business logic — return a helpful message
        return {"note": f"Tool {tool_name} requires the full MCP server module. Install fastmcp for full functionality.", "data": {}}

    else:
        return {"error": f"Unknown tool: {tool_name}"}


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
