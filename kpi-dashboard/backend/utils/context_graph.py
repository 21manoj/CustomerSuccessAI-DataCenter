"""
Context Graph Query Helpers

Provides common graph traversal operations for the context graph.
All functions are guarded by the context_graph feature toggle.

Usage:
    from utils.context_graph import get_nodes, get_edges, traverse_2hop, get_revenue_at_risk, aggregate_revenue_across_accounts
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from extensions import db
from models import ContextNode, ContextEdge

logger = logging.getLogger(__name__)


# ─── Node Queries ────────────────────────────────────────────────────────────

def get_nodes(
    account_id: int,
    node_type: Optional[str] = None,
    node_subtype: Optional[str] = None,
    tier: Optional[int] = None,
    since: Optional[datetime] = None,
    limit: int = 100,
) -> List[ContextNode]:
    """
    Get context nodes for an account with optional filters.

    Args:
        account_id: Required — tenant isolation
        node_type: SIGNAL, STAKEHOLDER, DECISION, OUTCOME, EXTERNAL_CONTEXT
        node_subtype: e.g. kpi_change, ticket, champion_loss
        tier: 1=permanent, 2=decaying, 3=ephemeral
        since: Only nodes with occurred_at >= since
        limit: Max results (default 100)
    """
    q = ContextNode.query.filter_by(account_id=account_id)

    if node_type:
        q = q.filter_by(node_type=node_type)
    if node_subtype:
        q = q.filter_by(node_subtype=node_subtype)
    if tier is not None:
        q = q.filter_by(tier=tier)
    if since:
        q = q.filter(ContextNode.occurred_at >= since)

    # Exclude expired T2/T3 nodes
    now = datetime.utcnow()
    q = q.filter(
        db.or_(
            ContextNode.expires_at.is_(None),
            ContextNode.expires_at > now,
        )
    )

    return q.order_by(ContextNode.occurred_at.desc()).limit(limit).all()


def get_node_by_source(account_id: int, source_platform: str, source_event_id: str) -> Optional[ContextNode]:
    """Find a node by its external source ID (dedup check)."""
    return ContextNode.query.filter_by(
        account_id=account_id,
        source_platform=source_platform,
        source_event_id=source_event_id,
    ).first()


# ─── Edge Queries ────────────────────────────────────────────────────────────

def get_edges(
    node_id: int,
    direction: str = 'both',
    edge_type: Optional[str] = None,
) -> List[ContextEdge]:
    """
    Get edges connected to a node.

    Args:
        node_id: The node to query from
        direction: 'outgoing', 'incoming', or 'both'
        edge_type: Filter by edge type (CAUSED_BY, LED_TO, etc.)
    """
    filters_out = [ContextEdge.from_node_id == node_id]
    filters_in = [ContextEdge.to_node_id == node_id]

    if edge_type:
        filters_out.append(ContextEdge.edge_type == edge_type)
        filters_in.append(ContextEdge.edge_type == edge_type)

    if direction == 'outgoing':
        return ContextEdge.query.filter(*filters_out).all()
    elif direction == 'incoming':
        return ContextEdge.query.filter(*filters_in).all()
    else:
        outgoing = ContextEdge.query.filter(*filters_out).all()
        incoming = ContextEdge.query.filter(*filters_in).all()
        return outgoing + incoming


def get_causal_chain(node_id: int, direction: str = 'upstream', max_depth: int = 5) -> List[Dict[str, Any]]:
    """
    Walk causal edges to build a chain of connected nodes.

    Args:
        node_id: Starting node
        direction: 'upstream' (find what caused this node) or 'downstream' (find effects)
        max_depth: Stop after N hops
    Returns:
        List of {node, edge, depth} dicts in traversal order
    """
    # Causal edge types — any of these indicate cause/effect relationships
    CAUSAL_EDGE_TYPES = {'CAUSED_BY', 'LED_TO', 'TRIGGERED', 'INDICATES', 'RESULTED_IN'}

    visited = set()
    chain = []

    current_ids = [node_id]
    for depth in range(1, max_depth + 1):
        next_ids = []
        for nid in current_ids:
            if nid in visited:
                continue
            visited.add(nid)

            if direction == 'upstream':
                # Find edges pointing INTO this node (from_node → nid)
                # The from_node is the upstream cause
                edges = ContextEdge.query.filter(
                    ContextEdge.to_node_id == nid,
                    ContextEdge.edge_type.in_(CAUSAL_EDGE_TYPES),
                ).all()
                for edge in edges:
                    neighbor_id = edge.from_node_id
                    if neighbor_id not in visited:
                        neighbor = db.session.get(ContextNode, neighbor_id)
                        if neighbor:
                            chain.append({
                                'node': neighbor.to_dict(),
                                'edge': edge.to_dict(),
                                'depth': depth,
                            })
                            next_ids.append(neighbor_id)
            else:
                # Find edges going OUT from this node (nid → to_node)
                # The to_node is the downstream effect
                edges = ContextEdge.query.filter(
                    ContextEdge.from_node_id == nid,
                    ContextEdge.edge_type.in_(CAUSAL_EDGE_TYPES),
                ).all()
                for edge in edges:
                    neighbor_id = edge.to_node_id
                    if neighbor_id not in visited:
                        neighbor = db.session.get(ContextNode, neighbor_id)
                        if neighbor:
                            chain.append({
                                'node': neighbor.to_dict(),
                                'edge': edge.to_dict(),
                                'depth': depth,
                            })
                            next_ids.append(neighbor_id)

        current_ids = next_ids
        if not current_ids:
            break

    return chain


# ─── 2-Hop Traversal ────────────────────────────────────────────────────────

def traverse_2hop(
    account_id: int,
    center_node_id: int,
    edge_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    2-hop ego graph centered on a node. Returns all nodes and edges
    within 2 hops, useful for "impact neighborhood" visualization.

    Returns:
        {
            'center': node_dict,
            'nodes': [node_dicts...],
            'edges': [edge_dicts...],
            'revenue_at_risk': total $ across all nodes
        }
    """
    center = db.session.get(ContextNode, center_node_id)
    if not center or center.account_id != account_id:
        return {'center': None, 'nodes': [], 'edges': [], 'revenue_at_risk': 0}

    visited_nodes = {center_node_id}
    collected_edges = []
    hop1_ids = set()

    # Hop 1
    edges_1 = _get_all_edges_for_node(center_node_id, edge_types)
    for e in edges_1:
        collected_edges.append(e)
        neighbor = e.to_node_id if e.from_node_id == center_node_id else e.from_node_id
        hop1_ids.add(neighbor)
        visited_nodes.add(neighbor)

    # Hop 2
    for nid in hop1_ids:
        edges_2 = _get_all_edges_for_node(nid, edge_types)
        for e in edges_2:
            neighbor = e.to_node_id if e.from_node_id == nid else e.from_node_id
            if neighbor not in visited_nodes:
                visited_nodes.add(neighbor)
            collected_edges.append(e)

    # Deduplicate edges
    seen_edge_ids = set()
    unique_edges = []
    for e in collected_edges:
        if e.edge_id not in seen_edge_ids:
            seen_edge_ids.add(e.edge_id)
            unique_edges.append(e)

    # Load all nodes
    all_nodes = ContextNode.query.filter(
        ContextNode.node_id.in_(visited_nodes),
        ContextNode.account_id == account_id,
    ).all()

    # Revenue at risk: derived from health-score × ARR (consistent with
    # get_revenue_at_risk — signal nodes no longer carry revenue_impact).
    total_revenue = _calculate_at_risk_from_health(account_id)

    return {
        'center': center.to_dict(),
        'nodes': [n.to_dict() for n in all_nodes],
        'edges': [e.to_dict() for e in unique_edges],
        'revenue_at_risk': total_revenue,
    }


def _get_all_edges_for_node(node_id: int, edge_types: Optional[List[str]] = None) -> List[ContextEdge]:
    """Get all edges (both directions) for a node, optionally filtered."""
    q_out = ContextEdge.query.filter_by(from_node_id=node_id)
    q_in = ContextEdge.query.filter_by(to_node_id=node_id)

    if edge_types:
        q_out = q_out.filter(ContextEdge.edge_type.in_(edge_types))
        q_in = q_in.filter(ContextEdge.edge_type.in_(edge_types))

    return q_out.all() + q_in.all()


# ─── Revenue / ROI Aggregations ─────────────────────────────────────────────

def _deduplicate_outcome_amounts(amounts: List[float], threshold: float = 0.20) -> float:
    """
    Cluster outcome amounts that are within *threshold* of each other —
    these likely represent the same economic event counted from different
    perspectives (e.g. "Expansion Deal Closed" vs "ARR Growth" vs "ROI").

    Returns the sum of the **largest** amount from each cluster.
    """
    if not amounts:
        return 0.0

    sorted_amounts = sorted(amounts, reverse=True)
    used: set = set()
    total = 0.0

    for i, a in enumerate(sorted_amounts):
        if i in used:
            continue
        used.add(i)
        # Absorb any later amounts that are within threshold of *a*
        for j in range(i + 1, len(sorted_amounts)):
            if j in used:
                continue
            b = sorted_amounts[j]
            if a > 0 and abs(a - b) / a < threshold:
                used.add(j)                 # same event — skip the smaller
        total += a                          # keep the largest per cluster

    return total


def _calculate_at_risk_from_health(account_id: int) -> float:
    """
    Derive at-risk revenue from the account's health score and ARR.

    Churn-probability bands (aligned with health thresholds):
      - Critical (health < 50):  40 % of ARR at risk
      - At-risk  (50 ≤ h < 70): 20 % of ARR at risk
      - Healthy  (h ≥ 70):       5 % of ARR at risk

    Health score is read from the ``health_scores`` table (latest
    measurement month).  ARR comes from ``accounts.revenue`` or
    ``accounts.profile_metadata.arr``.

    This replaces the old approach of summing negative SIGNAL
    revenue_impact values, which produced cumulative / stale
    estimates that were never real independent revenue events.
    """
    from models import Account, HealthScore

    account = Account.query.filter_by(account_id=account_id).first()
    if not account:
        return 0.0

    # ── ARR ──
    arr = 0.0
    if account.revenue:
        arr = float(account.revenue)
    elif account.profile_metadata and isinstance(account.profile_metadata, dict):
        arr = float(account.profile_metadata.get('arr', 0) or 0)

    # ── Latest health score ──
    latest_hs = (
        HealthScore.query
        .filter_by(account_id=account_id)
        .order_by(HealthScore.measurement_month.desc())
        .first()
    )
    health = float(latest_hs.health_score) if latest_hs and latest_hs.health_score else 50.0

    if health < 50:
        churn_pct = 0.40
    elif health < 70:
        churn_pct = 0.20
    else:
        churn_pct = 0.05

    return round(arr * churn_pct, 2)


def get_revenue_at_risk(account_id: int) -> Dict[str, Any]:
    """
    Aggregate revenue impact across all active nodes for an account.
    This is the primary CRO/CFO metric.

    Revenue-counting rules (prevents double-counting across the causal chain):
      - **at_risk**:   Derived from health-score × ARR × churn-probability.
                        SIGNAL nodes do NOT carry revenue_impact (those were
                        stale / cumulative estimates, not real events).
      - **protected**: Only OUTCOME nodes with revenue_impact_type='protected'.
      - **expansion**: Only OUTCOME nodes with revenue_impact_type='expansion'.
      - **lost**:      Only OUTCOME nodes with revenue_impact_type='lost'.
      - DECISION nodes are *excluded* — they are intermediate steps whose
        value is realised through downstream OUTCOME nodes.

    Outcome de-duplication:
      Within each bucket, outcome amounts that are within 20 % of each other
      are treated as the same economic event; only the largest is kept.

    Returns:
        {
            'at_risk': total ARR currently at risk,
            'protected': total ARR protected by interventions,
            'expansion': expansion revenue (de-duplicated),
            'lost': confirmed lost ARR,
            'net_impact': protected + expansion - lost,
            'node_count': number of revenue-contributing nodes
        }
    """
    now = datetime.utcnow()

    # ── at_risk: health-score × ARR (no longer from signal nodes) ──
    at_risk = _calculate_at_risk_from_health(account_id)

    # ── protected / expansion / lost: OUTCOME nodes only ──
    outcome_nodes = ContextNode.query.filter(
        ContextNode.account_id == account_id,
        ContextNode.node_type == 'OUTCOME',
        ContextNode.revenue_impact.isnot(None),
        db.or_(
            ContextNode.expires_at.is_(None),
            ContextNode.expires_at > now,
        )
    ).all()

    outcome_buckets: Dict[str, List[float]] = {
        'protected': [], 'expansion': [], 'lost': [],
    }
    # Normalize revenue_impact_type → bucket name
    # close_playbook writes 'revenue_protected', data generator writes 'protected'
    _BUCKET_ALIASES = {
        # Protected bucket
        'revenue_protected': 'protected', 'churn_averted': 'protected',
        'renewal_secured': 'protected', 'engagement_recovery': 'protected',
        'intervention_outcome': 'protected', 'playbook_outcome': 'protected',
        'renewal_confirmed': 'protected',
        # Lost bucket
        'revenue_at_risk': 'lost', 'revenue_lost': 'lost',
        'engagement_decline': 'lost', 'renewal_uncertainty': 'lost',
        'capacity_constraint': 'lost', 'churn_risk': 'lost',
        'churn_lost': 'lost', 'contraction': 'lost',
        'partial_recovery': 'lost', 'partner_friction': 'lost',
        # Expansion bucket
        'expansion_closed': 'expansion', 'revenue_expanded': 'expansion',
        'expansion_approved': 'expansion', 'expansion_opportunity': 'expansion',
        'revenue_growth': 'expansion', 'new_logo': 'expansion',
    }
    for n in outcome_nodes:
        impact = abs(float(n.revenue_impact) * float(n.confidence or 1.0))
        raw_type = n.revenue_impact_type or 'expansion'
        bucket = _BUCKET_ALIASES.get(raw_type, raw_type)
        if bucket in outcome_buckets:
            outcome_buckets[bucket].append(impact)

    # De-duplicate within each bucket (same economic event → keep largest)
    protected  = _deduplicate_outcome_amounts(outcome_buckets['protected'])
    expansion  = _deduplicate_outcome_amounts(outcome_buckets['expansion'])
    lost       = _deduplicate_outcome_amounts(outcome_buckets['lost'])

    node_count = len(outcome_nodes) + (1 if at_risk > 0 else 0)

    return {
        'at_risk':    round(at_risk, 2),
        'protected':  round(protected, 2),
        'expansion':  round(expansion, 2),
        'lost':       round(lost, 2),
        'net_impact': round(protected + expansion - lost, 2),
        'node_count': node_count,
    }


def aggregate_revenue_across_accounts(
    customer_id: int,
    account_ids: List[int],
) -> Dict[str, Any]:
    """
    Aggregate revenue metrics across multiple accounts from context graph OUTCOME nodes.

    This is the multi-account counterpart of get_revenue_at_risk() (which is per-account).
    Used by CRO, CFO, and CEO dashboards.  Imported from utils/context_graph to avoid
    duplication across executive_dashboard_api and outcome_roi_api.

    Returns:
        {
            'revenue_at_risk': float,
            'revenue_protected': float,
            'expansion_pipeline': float,
            'node_count': int,
        }
    """
    empty = {
        'revenue_at_risk': 0, 'revenue_protected': 0,
        'expansion_pipeline': 0, 'node_count': 0,
    }
    if not account_ids:
        return empty

    outcome_nodes = (
        ContextNode.query
        .filter(
            ContextNode.customer_id == customer_id,
            ContextNode.account_id.in_(account_ids),
            ContextNode.node_type == 'OUTCOME',
            ContextNode.revenue_impact.isnot(None),
        )
        .all()
    )

    at_risk = 0.0
    protected = 0.0
    expansion = 0.0

    # Classify by revenue_impact_type OR node_subtype into 3 buckets.
    # Must match all types used by close_execution, load_driver, and LLM enrichment.
    RISK_TYPES = {'at_risk', 'lost', 'revenue_at_risk', 'churn_lost', 'churn_risk',
                  'engagement_decline', 'renewal_uncertainty', 'capacity_constraint',
                  'partner_friction', 'partial_recovery'}
    PROTECTED_TYPES = {'protected', 'revenue_protected', 'churn_averted',
                       'renewal_secured', 'revenue_saved', 'engagement_recovery',
                       'escalation_resolved', 'intervention_outcome'}
    EXPANSION_TYPES = {'expansion', 'expansion_closed', 'expansion_opportunity',
                       'expansion_approved', 'expansion_realized', 'revenue_growth',
                       'upsell', 'cross_sell'}

    for node in outcome_nodes:
        try:
            raw = float(node.revenue_impact)
        except (TypeError, ValueError):
            continue

        # Check both revenue_impact_type and node_subtype for classification
        impact_type = (node.revenue_impact_type or '').lower()
        subtype = (node.node_subtype or '').lower()

        if impact_type in RISK_TYPES or subtype in RISK_TYPES:
            at_risk += abs(raw)
        elif impact_type in EXPANSION_TYPES or subtype in EXPANSION_TYPES:
            expansion += abs(raw)
        elif impact_type in PROTECTED_TYPES or subtype in PROTECTED_TYPES:
            protected += abs(raw)
        elif raw < 0:
            at_risk += abs(raw)  # negative revenue = at risk
        elif raw > 0:
            protected += raw     # positive unclassified = protected

    return {
        'revenue_at_risk': round(at_risk, 2),
        'revenue_protected': round(protected, 2),
        'expansion_pipeline': round(expansion, 2),
        'node_count': len(outcome_nodes),
    }


def get_account_graph_summary(account_id: int) -> Dict[str, Any]:
    """
    Quick summary of graph density for an account.
    Useful for dashboard widgets and health overview.
    """
    now = datetime.utcnow()
    base_filter = db.and_(
        ContextNode.account_id == account_id,
        db.or_(
            ContextNode.expires_at.is_(None),
            ContextNode.expires_at > now,
        )
    )

    node_counts = db.session.query(
        ContextNode.node_type,
        db.func.count(ContextNode.node_id)
    ).filter(base_filter).group_by(ContextNode.node_type).all()

    total_nodes = sum(c for _, c in node_counts)

    # Count edges connected to this account's nodes
    account_node_ids = db.session.query(ContextNode.node_id).filter(
        ContextNode.account_id == account_id
    ).subquery()

    edge_count = ContextEdge.query.filter(
        db.or_(
            ContextEdge.from_node_id.in_(account_node_ids),
            ContextEdge.to_node_id.in_(account_node_ids),
        )
    ).count()

    revenue = get_revenue_at_risk(account_id)

    return {
        'account_id': account_id,
        'total_nodes': total_nodes,
        'total_edges': edge_count,
        'nodes_by_type': {nt: c for nt, c in node_counts},
        'revenue': revenue,
    }


# ─── Write Helpers ───────────────────────────────────────────────────────────

def upsert_node(
    customer_id: int,
    account_id: int,
    node_type: str,
    title: str,
    occurred_at: datetime,
    properties: Dict[str, Any],
    source_platform: str = 'csv_import',
    source_event_id: Optional[str] = None,
    **kwargs,
) -> ContextNode:
    """
    Insert or update a context node. Deduplicates by source_platform + source_event_id.
    """
    existing = None
    if source_event_id:
        existing = get_node_by_source(account_id, source_platform, source_event_id)

    if existing:
        existing.title = title
        existing.properties = properties
        existing.occurred_at = occurred_at
        for k, v in kwargs.items():
            if hasattr(existing, k):
                setattr(existing, k, v)
        db.session.flush()
        return existing

    node = ContextNode(
        customer_id=customer_id,
        account_id=account_id,
        node_type=node_type,
        title=title,
        occurred_at=occurred_at,
        properties=properties,
        source_platform=source_platform,
        source_event_id=source_event_id,
        **kwargs,
    )
    db.session.add(node)
    db.session.flush()
    return node


def add_edge(
    from_node_id: int,
    to_node_id: int,
    edge_type: str,
    weight: float = 1.0,
    confidence: float = 1.0,
    source_platform: str = 'csv_import',
    created_by: str = 'csv_import',
    customer_id: Optional[int] = None,
    **kwargs,
) -> ContextEdge:
    """
    Add an edge between two nodes. Does NOT deduplicate — caller should
    check for existing edges if needed.
    """
    edge = ContextEdge(
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        edge_type=edge_type,
        weight=weight,
        confidence=confidence,
        source_platform=source_platform,
        created_by=created_by,
        customer_id=customer_id,
        **kwargs,
    )
    db.session.add(edge)
    db.session.flush()
    return edge


def upsert_edge(
    from_node_id: int,
    to_node_id: int,
    edge_type: str,
    weight: float = 1.0,
    confidence: float = 1.0,
    source_platform: str = 'csv_import',
    created_by: str = 'csv_import',
    customer_id: Optional[int] = None,
    **kwargs,
) -> tuple:
    """
    Insert or update an edge. Deduplicates by (from_node_id, to_node_id, edge_type, source_platform).

    Returns:
        (ContextEdge, created: bool) — True if new, False if updated existing
    """
    existing = ContextEdge.query.filter_by(
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        edge_type=edge_type,
        source_platform=source_platform,
    ).first()

    if existing:
        existing.weight = weight
        existing.confidence = confidence
        existing.created_by = created_by
        if customer_id is not None:
            existing.customer_id = customer_id
        for k, v in kwargs.items():
            if hasattr(existing, k):
                setattr(existing, k, v)
        db.session.flush()
        return (existing, False)

    edge = ContextEdge(
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        edge_type=edge_type,
        weight=weight,
        confidence=confidence,
        source_platform=source_platform,
        created_by=created_by,
        customer_id=customer_id,
        **kwargs,
    )
    db.session.add(edge)
    db.session.flush()
    return (edge, True)
