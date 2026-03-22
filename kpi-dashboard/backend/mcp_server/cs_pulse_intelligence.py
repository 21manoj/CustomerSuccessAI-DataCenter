#!/usr/bin/env python3
"""
CS Pulse MCP — Intelligence Tools (Context Graph / Revenue Intelligence).

7 tools moved from cs_pulse_mcp_server.py:
  - get_revenue_at_risk
  - get_causal_chain
  - get_graph_summary
  - search_signals
  - get_account_journey_timeline
  - get_context_graph_mermaid
  - get_stakeholder_map

All tools register on the shared `mcp` instance from cs_pulse_mcp_server.
"""

from cs_pulse_mcp_server import (
    mcp,
    _check_mcp_enabled,
    _require_auth,
    _require_account_auth,
    _get_flask_app,
    _validate_account_ownership,
    _get_account_arr,
    _backend_dir,
    ToolError,
)


# ---------------------------------------------------------------------------
# Context graph gate (local to this module)
# ---------------------------------------------------------------------------
def _check_context_graph(customer_id: int):
    """Raise ToolError if context graph is not enabled for this customer."""
    from feature_toggles import is_context_graph_enabled
    if not is_context_graph_enabled(customer_id):
        raise ToolError(
            f"Context graph is not enabled for customer {customer_id}. "
            "Enable via the feature toggle API."
        )


# ---------------------------------------------------------------------------
# Visualization helpers (local to this module)
# ---------------------------------------------------------------------------
def _mermaid_safe(text: str, max_len: int = 40) -> str:
    """Escape and truncate text for Mermaid diagram labels."""
    if not text:
        return ""
    safe = text.replace('"', "'").replace("[", "(").replace("]", ")")
    safe = safe.replace("{", "(").replace("}", ")").replace("`", "'")
    safe = safe.replace("<", "\u2039").replace(">", "\u203a").replace("#", "")
    if len(safe) > max_len:
        safe = safe[: max_len - 1] + "\u2026"
    return safe


def _format_revenue_short(amount: float) -> str:
    """Format revenue as short string, e.g. '$5.2M' or '$424K'."""
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    elif amount > 0:
        return f"${amount:,.0f}"
    return ""


# ===================================================================
# Tool: get_revenue_at_risk
# ===================================================================

@mcp.tool
def get_revenue_at_risk(customer_id: int, account_id: int) -> dict:
    """Get revenue breakdown from context graph: at-risk, protected, expansion, lost.

    IMPORTANT: This is the ONLY authoritative source for revenue figures. Never manually
    sum revenue_impact values from individual context graph nodes — that causes double-counting.
    Individual SIGNAL nodes have revenue_impact=null; only OUTCOME nodes carry revenue.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from utils.context_graph import get_revenue_at_risk as _get_rev

        account = _validate_account_ownership(customer_id, account_id)
        result = _get_rev(account_id)
        result["scope"] = "account"
        result["account_id"] = account_id
        result["account_name"] = account.account_name
        return result


# ===================================================================
# Tool: get_causal_chain
# ===================================================================

@mcp.tool
def get_causal_chain(customer_id: int, node_id: int, direction: str = "upstream") -> dict:
    """Traverse the causal chain (Signal → Decision → Outcome) from a context graph node.

    Args:
        customer_id: The customer (tenant) ID
        node_id: The starting context graph node ID
        direction: 'upstream' (what caused this) or 'downstream' (what this led to)
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from utils.context_graph import get_causal_chain as _get_chain
        from models import ContextNode, db

        start_node = db.session.get(ContextNode, node_id)
        if not start_node:
            raise ToolError(f"Node {node_id} not found")

        # Tenant isolation: verify node belongs to this customer
        if start_node.customer_id != int(customer_id):
            raise ToolError(
                f"Node {node_id} not found for customer {customer_id}"
            )

        chain = _get_chain(node_id, direction=direction, max_depth=5)

        return {
            "scope": "node_traversal",
            "start_node": start_node.to_dict(),
            "direction": direction,
            "chain_length": len(chain),
            "chain": chain,
        }


# ===================================================================
# Tool: get_graph_summary
# ===================================================================

@mcp.tool
def get_graph_summary(customer_id: int, account_id: int) -> dict:
    """Get context graph summary: node/edge counts and revenue breakdown.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from utils.context_graph import get_account_graph_summary

        _validate_account_ownership(customer_id, account_id)
        result = get_account_graph_summary(account_id)
        result["scope"] = "account"
        return result


# ===================================================================
# Tool: search_signals
# ===================================================================

@mcp.tool
def search_signals(
    customer_id: int,
    account_id: int,
    node_type: str = "SIGNAL",
    node_subtype: str = None,
    limit: int = 20,
) -> dict:
    """Search for context graph nodes (signals, decisions, outcomes) for an account.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to search
        node_type: Node type filter: SIGNAL, DECISION, OUTCOME, STAKEHOLDER, EXTERNAL_CONTEXT
        node_subtype: Optional subtype filter (e.g. kpi_change, ticket, champion_loss)
        limit: Maximum number of results (default 20)
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from utils.context_graph import get_nodes

        _validate_account_ownership(customer_id, account_id)
        nodes = get_nodes(
            account_id=account_id,
            node_type=node_type,
            node_subtype=node_subtype,
            limit=limit,
        )

        return {
            "scope": "account",
            "account_id": account_id,
            "node_type": node_type,
            "node_subtype": node_subtype,
            "count": len(nodes),
            "nodes": [n.to_dict() for n in nodes],
        }


# ===================================================================
# Tool: get_account_journey_timeline
# ===================================================================

@mcp.tool
def get_account_journey_timeline(
    customer_id: int,
    account_id: int,
    limit: int = 50,
) -> dict:
    """Get a chronological timeline of ALL context graph events for an account.

    Returns signals, decisions, outcomes, and stakeholder events in date order
    with a pre-computed revenue summary. Replaces multiple search_signals calls.
    The revenue_summary field uses get_revenue_at_risk internally (deduplicated).

    PREFERRED over calling search_signals multiple times — one call replaces 3+ search_signals calls.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
        limit: Max events to return (default 50, max 200)
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from models import ContextNode, db
        from utils.context_graph import get_revenue_at_risk
        from datetime import datetime

        account = _validate_account_ownership(customer_id, account_id)
        arr = _get_account_arr(account)

        limit = min(max(limit, 1), 200)
        now = datetime.utcnow()

        # All non-expired nodes, chronological
        nodes = (
            ContextNode.query
            .filter(
                ContextNode.account_id == account_id,
                db.or_(
                    ContextNode.expires_at.is_(None),
                    ContextNode.expires_at > now,
                ),
            )
            .order_by(ContextNode.occurred_at.asc())
            .limit(limit)
            .all()
        )

        if not nodes:
            return {
                "scope": "account",
                "account_id": account_id,
                "account_name": account.account_name,
                "event_count": 0,
                "timeline": [],
                "revenue_summary": get_revenue_at_risk(account_id),
            }

        # Counts by type
        counts: dict = {}
        for n in nodes:
            counts[n.node_type] = counts.get(n.node_type, 0) + 1

        # Build compact timeline entries
        timeline = []
        for n in nodes:
            props = n.properties or {}
            entry = {
                "node_id": n.node_id,
                "node_type": n.node_type,
                "node_subtype": n.node_subtype,
                "title": n.title,
                "occurred_at": n.occurred_at.isoformat() if n.occurred_at else None,
            }
            sentiment = props.get("sentiment") or props.get("sentiment_score")
            if sentiment is not None:
                entry["sentiment"] = sentiment

            sname = props.get("stakeholder_name") or props.get("stakeholder_title")
            if sname:
                entry["stakeholder"] = sname

            if n.revenue_impact is not None:
                entry["revenue_impact"] = float(n.revenue_impact)
                entry["revenue_impact_type"] = n.revenue_impact_type

            timeline.append(entry)

        rev = get_revenue_at_risk(account_id)

        return {
            "scope": "account",
            "account_id": account_id,
            "account_name": account.account_name,
            "arr": arr,
            "date_range": {
                "start": nodes[0].occurred_at.isoformat() if nodes[0].occurred_at else None,
                "end": nodes[-1].occurred_at.isoformat() if nodes[-1].occurred_at else None,
            },
            "event_count": len(nodes),
            "counts_by_type": counts,
            "revenue_summary": rev,
            "timeline": timeline,
        }


# ===================================================================
# Tool: get_context_graph_mermaid
# ===================================================================

@mcp.tool
def get_context_graph_mermaid(
    customer_id: int,
    account_id: int,
    max_nodes: int = 30,
) -> dict:
    """Generate a Mermaid flowchart of the context graph for an account.

    Returns a renderable Mermaid diagram string with nodes color-coded by type
    (signal=orange, decision=blue, outcome=green, stakeholder=purple) and
    causal edges labeled. Revenue annotations appear only on OUTCOME nodes.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to visualize
        max_nodes: Maximum nodes in diagram (default 30, max 60)
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from models import ContextNode, ContextEdge, db
        from datetime import datetime

        _validate_account_ownership(customer_id, account_id)

        max_nodes = min(max(max_nodes, 5), 60)
        now = datetime.utcnow()

        nodes = (
            ContextNode.query
            .filter(
                ContextNode.account_id == account_id,
                db.or_(
                    ContextNode.expires_at.is_(None),
                    ContextNode.expires_at > now,
                ),
            )
            .order_by(ContextNode.occurred_at.asc())
            .limit(max_nodes)
            .all()
        )

        if not nodes:
            return {
                "scope": "account",
                "account_id": account_id,
                "mermaid": "flowchart TD\n    empty[No context graph data]",
                "node_count": 0,
                "edge_count": 0,
            }

        node_ids = {n.node_id for n in nodes}
        node_id_list = list(node_ids)
        edges = (
            ContextEdge.query
            .filter(
                ContextEdge.from_node_id.in_(node_id_list),
                ContextEdge.to_node_id.in_(node_id_list),
            )
            .all()
        )

        lines = [
            "flowchart TD",
            '    classDef signal fill:#FFA500,stroke:#333,color:#000',
            '    classDef decision fill:#4169E1,stroke:#333,color:#fff',
            '    classDef outcome fill:#2E8B57,stroke:#333,color:#fff,stroke-width:3px',
            '    classDef stakeholder fill:#8B5CF6,stroke:#333,color:#fff',
            '    classDef external fill:#6B7280,stroke:#333,color:#fff',
            "",
        ]

        SHAPE_MAP = {
            "SIGNAL":           ('["', '"]'),
            "DECISION":         ('{{"', '"}}'),
            "OUTCOME":          ('["', '"]'),
            "STAKEHOLDER":      ('(("', '"))'),
            "EXTERNAL_CONTEXT": ('["', '"]'),
        }

        CLASS_MAP = {
            "SIGNAL": "signal",
            "DECISION": "decision",
            "OUTCOME": "outcome",
            "STAKEHOLDER": "stakeholder",
            "EXTERNAL_CONTEXT": "external",
        }

        for n in nodes:
            nid = f"n{n.node_id}"
            date_prefix = ""
            if n.occurred_at:
                date_prefix = n.occurred_at.strftime("%b %d") + ": "

            label = _mermaid_safe(n.title, max_len=35)

            rev_note = ""
            if n.node_type == "OUTCOME" and n.revenue_impact:
                amt = _format_revenue_short(abs(float(n.revenue_impact)))
                rtype = n.revenue_impact_type or "impact"
                rev_note = f"\\n{amt} {rtype}"

            open_br, close_br = SHAPE_MAP.get(n.node_type, ('["', '"]'))
            css_class = CLASS_MAP.get(n.node_type, "signal")

            lines.append(
                f'    {nid}{open_br}{date_prefix}{label}{rev_note}{close_br}:::{css_class}'
            )

        lines.append("")

        for e in edges:
            if e.from_node_id in node_ids and e.to_node_id in node_ids:
                label = e.edge_type or ""
                lines.append(
                    f"    n{e.from_node_id} -->|{label}| n{e.to_node_id}"
                )

        mermaid_str = "\n".join(lines)

        return {
            "scope": "account",
            "account_id": account_id,
            "mermaid": mermaid_str,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "legend": {
                "signal": "orange (#FFA500)",
                "decision": "blue (#4169E1)",
                "outcome": "green (#2E8B57)",
                "stakeholder": "purple (#8B5CF6)",
                "external": "gray (#6B7280)",
            },
        }


# ===================================================================
# Tool: get_stakeholder_map
# ===================================================================

@mcp.tool
def get_stakeholder_map(customer_id: int, account_id: int) -> dict:
    """Get the stakeholder network for an account — who influenced which decisions and outcomes.

    Returns each stakeholder with their role, engagement details, and the
    decisions and outcomes they are connected to via INVOLVES edges or
    decision_maker_role references.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _check_context_graph(customer_id)
        from models import ContextNode, ContextEdge, db
        from datetime import datetime

        account = _validate_account_ownership(customer_id, account_id)
        now = datetime.utcnow()

        stakeholder_nodes = (
            ContextNode.query
            .filter(
                ContextNode.account_id == account_id,
                ContextNode.node_type == "STAKEHOLDER",
                db.or_(
                    ContextNode.expires_at.is_(None),
                    ContextNode.expires_at > now,
                ),
            )
            .order_by(ContextNode.occurred_at.asc())
            .all()
        )

        decision_nodes = {
            n.node_id: n
            for n in ContextNode.query.filter(
                ContextNode.account_id == account_id,
                ContextNode.node_type == "DECISION",
            ).all()
        }
        outcome_nodes = {
            n.node_id: n
            for n in ContextNode.query.filter(
                ContextNode.account_id == account_id,
                ContextNode.node_type == "OUTCOME",
            ).all()
        }

        stakeholder_ids = [s.node_id for s in stakeholder_nodes]
        involves_edges = []
        if stakeholder_ids:
            involves_edges = (
                ContextEdge.query
                .filter(
                    ContextEdge.edge_type == "INVOLVES",
                    db.or_(
                        ContextEdge.from_node_id.in_(stakeholder_ids),
                        ContextEdge.to_node_id.in_(stakeholder_ids),
                    ),
                )
                .all()
            )

        stakeholder_connections: dict = {s.node_id: set() for s in stakeholder_nodes}
        for e in involves_edges:
            if e.from_node_id in stakeholder_connections:
                stakeholder_connections[e.from_node_id].add(e.to_node_id)
            if e.to_node_id in stakeholder_connections:
                stakeholder_connections[e.to_node_id].add(e.from_node_id)

        for dec in decision_nodes.values():
            dec_props = dec.properties or {}
            maker_role = dec_props.get("decision_maker_role", "")
            if maker_role:
                for s in stakeholder_nodes:
                    if (
                        maker_role.lower() in (s.node_subtype or "").lower()
                        or maker_role.lower() in (s.title or "").lower()
                    ):
                        stakeholder_connections[s.node_id].add(dec.node_id)

        total_decisions = 0
        total_outcomes = 0
        total_revenue = 0.0
        stakeholders = []

        for s in stakeholder_nodes:
            props = s.properties or {}
            connected = stakeholder_connections.get(s.node_id, set())

            connected_decs = []
            connected_outs = []
            for cid in connected:
                if cid in decision_nodes:
                    d = decision_nodes[cid]
                    connected_decs.append({
                        "node_id": d.node_id,
                        "title": d.title,
                        "occurred_at": d.occurred_at.isoformat() if d.occurred_at else None,
                    })
                if cid in outcome_nodes:
                    o = outcome_nodes[cid]
                    rev = float(o.revenue_impact) if o.revenue_impact else 0
                    connected_outs.append({
                        "node_id": o.node_id,
                        "title": o.title,
                        "revenue_impact": rev,
                        "revenue_impact_type": o.revenue_impact_type,
                    })
                    total_revenue += abs(rev)

            total_decisions += len(connected_decs)
            total_outcomes += len(connected_outs)

            stakeholders.append({
                "node_id": s.node_id,
                "name": s.title,
                "role": s.node_subtype,
                "engagement_frequency": props.get("engagement_frequency"),
                "department": props.get("department"),
                "is_active": props.get("is_active", True),
                "sentiment": props.get("sentiment"),
                "connected_decisions": connected_decs,
                "connected_outcomes": connected_outs,
                "edge_count": len(connected),
            })

        stakeholders.sort(key=lambda x: x["edge_count"], reverse=True)

        return {
            "scope": "account",
            "account_id": account_id,
            "account_name": account.account_name,
            "stakeholder_count": len(stakeholders),
            "stakeholders": stakeholders,
            "influence_summary": (
                f"{len(stakeholders)} stakeholders, "
                f"{total_decisions} decision links, "
                f"{total_outcomes} outcome links, "
                f"{_format_revenue_short(total_revenue)} total revenue influenced"
            ),
        }
