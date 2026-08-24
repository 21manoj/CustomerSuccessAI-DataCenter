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

# Dedicated logger for pre-commit rejection events. Ops tooling / SIEM can
# filter on this logger name to route alerts when an unknown subtype hits the
# invariant gate. Deduped per-process on (from_subtype, to_subtype, reason_key)
# to avoid alert spam when the same bad edge is retried many times.
_precommit_rejection_logger = logging.getLogger('cs_pulse.pre_commit_rejection')
_seen_rejections: set = set()

# Dedicated logger for unearned-confidence clamp events (I3' — OUTCOME written
# without evidence → confidence capped at 0.3, tier forced to 2). Ops tooling
# filters on this logger name to surface "producers emitting unearned OUTCOMEs"
# for investigation. Deduped per-process on (source_platform, subtype, impact).
_unearned_clamp_logger = logging.getLogger('cs_pulse.unearned_confidence_clamp')
_seen_unearned_clamps: set = set()


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


def get_causal_chain(
    node_id: int,
    direction: str = 'upstream',
    max_depth: int = 5,
    customer_id: int = None,
) -> List[Dict[str, Any]]:
    """
    Walk causal edges to build a chain of connected nodes.

    Args:
        node_id: Starting node
        direction: 'upstream' (find what caused this node) or 'downstream' (find effects)
        max_depth: Stop after N hops
        customer_id: If set, restrict traversal to this tenant (prevents
                     cross-tenant edge leakage via shared nodes).
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
                filters = [
                    ContextEdge.to_node_id == nid,
                    ContextEdge.edge_type.in_(CAUSAL_EDGE_TYPES),
                ]
                if customer_id is not None:
                    filters.append(ContextEdge.customer_id == customer_id)
                edges = ContextEdge.query.filter(*filters).all()
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
                filters = [
                    ContextEdge.from_node_id == nid,
                    ContextEdge.edge_type.in_(CAUSAL_EDGE_TYPES),
                ]
                if customer_id is not None:
                    filters.append(ContextEdge.customer_id == customer_id)
                edges = ContextEdge.query.filter(*filters).all()
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

def _dedupe_exact_outcome_nodes(nodes):
    """Collapse byte-identical duplicate OUTCOME nodes to one.

    Distinct from _deduplicate_outcome_amounts (a fuzzy same-economic-event
    AMOUNT collapse used per-account). This removes LITERAL duplicate nodes —
    same account, title, revenue_impact, type, and occurred_at but different
    node_ids — which a re-ingested CSV produces (found 2026-08-24: customer
    391's outcomes were ingested 4×, 63 excess rows, inflating the
    non-deduping CFO rollup's revenue_at_risk to $39.84M = 111% of its $35.9M
    ARR — an impossible number). Keeps the lowest node_id of each group.

    The account-level get_revenue_at_risk masked this via its amount-dedup;
    the cross-account rollups summed raw. Applying this in both rollups makes
    a literal duplicate impossible to double-count regardless of the ingest
    bug, which is the forward fix; the 391 residue is cleaned separately.
    """
    seen = {}
    for n in nodes:
        key = (n.account_id, n.title, str(n.revenue_impact),
               n.revenue_impact_type, n.occurred_at)
        prev = seen.get(key)
        if prev is None or n.node_id < prev.node_id:
            seen[key] = n
    return list(seen.values())


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
    # I3' filter: exclude unearned nodes (confidence < 0.5). Nodes that were
    # written without evidence got clamped to 0.3 by the pre-commit hook; we
    # don't want those contributing to CFO/CRO revenue claims. Nodes with
    # NULL confidence are treated as earned (legacy data, pre-clamp) —
    # the clamp only fires prospectively.
    outcome_nodes = ContextNode.query.filter(
        ContextNode.account_id == account_id,
        ContextNode.node_type == 'OUTCOME',
        ContextNode.revenue_impact.isnot(None),
        db.or_(
            ContextNode.expires_at.is_(None),
            ContextNode.expires_at > now,
        ),
        db.or_(
            ContextNode.confidence.is_(None),
            ContextNode.confidence >= 0.5,
        ),
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

    # Exact-duplicate collapse before summing — this rollup used to sum raw
    # (unlike the account-level path), so re-ingested duplicate nodes
    # inflated the total past ARR. See _dedupe_exact_outcome_nodes.
    outcome_nodes = _dedupe_exact_outcome_nodes(outcome_nodes)

    at_risk = 0.0
    protected = 0.0
    expansion = 0.0

    for node in outcome_nodes:
        bucket, amount = _outcome_revenue_bucket_and_amount(node)
        if bucket == 'at_risk':
            at_risk += amount
        elif bucket == 'expansion':
            expansion += amount
        elif bucket == 'protected':
            protected += amount

    return {
        'revenue_at_risk': round(at_risk, 2),
        'revenue_protected': round(protected, 2),
        'expansion_pipeline': round(expansion, 2),
        'node_count': len(outcome_nodes),
    }


# Classify OUTCOME revenue_impact into dashboard buckets (shared with provenance).
_OUTCOME_RISK_TYPES = {
    'at_risk', 'lost', 'revenue_at_risk', 'churn_lost', 'churn_risk',
    'engagement_decline', 'renewal_uncertainty', 'capacity_constraint',
    'partner_friction', 'partial_recovery',
}
_OUTCOME_PROTECTED_TYPES = {
    'protected', 'revenue_protected', 'churn_averted', 'renewal_secured',
    'revenue_saved', 'engagement_recovery', 'escalation_resolved', 'intervention_outcome',
}
_OUTCOME_EXPANSION_TYPES = {
    'expansion', 'expansion_closed', 'expansion_opportunity', 'expansion_approved',
    'expansion_realized', 'revenue_growth', 'upsell', 'cross_sell',
}


def _outcome_revenue_bucket_and_amount(node: ContextNode):
    """Return (bucket, abs_amount) or (None, 0) for an OUTCOME node with revenue_impact."""
    try:
        raw = float(node.revenue_impact)
    except (TypeError, ValueError):
        return None, 0.0

    impact_type = (node.revenue_impact_type or '').lower()
    subtype = (node.node_subtype or '').lower()

    if impact_type in _OUTCOME_RISK_TYPES or subtype in _OUTCOME_RISK_TYPES:
        return 'at_risk', abs(raw)
    if impact_type in _OUTCOME_EXPANSION_TYPES or subtype in _OUTCOME_EXPANSION_TYPES:
        return 'expansion', abs(raw)
    if impact_type in _OUTCOME_PROTECTED_TYPES or subtype in _OUTCOME_PROTECTED_TYPES:
        return 'protected', abs(raw)
    if raw < 0:
        return 'at_risk', abs(raw)
    if raw > 0:
        return 'protected', raw
    return None, 0.0


def _outcome_node_trace(node: ContextNode) -> Dict[str, Any]:
    return {
        'node_id': node.node_id,
        'account_id': node.account_id,
        'node_subtype': node.node_subtype,
        'revenue_impact': float(node.revenue_impact) if node.revenue_impact is not None else None,
        'revenue_impact_type': node.revenue_impact_type,
        'title': node.title,
        'occurred_at': node.occurred_at.isoformat() if node.occurred_at else None,
    }


def aggregate_revenue_with_provenance(
    customer_id: int,
    account_ids: List[int],
    sample_per_bucket: int = 8,
) -> Dict[str, Any]:
    """
    Same totals as aggregate_revenue_across_accounts, plus trace samples for UI / audit.
    """
    base = aggregate_revenue_across_accounts(customer_id, account_ids)
    empty_prov = {
        'source': 'context_graph',
        'engine': 'aggregate_revenue_across_accounts',
        'outcome_node_count': 0,
        'revenue_at_risk': {'sample_nodes': []},
        'revenue_protected': {'sample_nodes': []},
        'expansion_pipeline': {'sample_nodes': []},
    }
    if not account_ids:
        return {**base, 'provenance': empty_prov}

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

    # Same exact-duplicate collapse the base totals use, so the trace
    # samples don't show 4 identical rows for one economic event.
    outcome_nodes = _dedupe_exact_outcome_nodes(outcome_nodes)

    samples = {'at_risk': [], 'protected': [], 'expansion': []}
    for node in outcome_nodes:
        bucket, amount = _outcome_revenue_bucket_and_amount(node)
        if not bucket or amount <= 0:
            continue
        key = bucket if bucket != 'expansion' else 'expansion'
        if bucket == 'at_risk' and len(samples['at_risk']) < sample_per_bucket:
            samples['at_risk'].append(_outcome_node_trace(node))
        elif bucket == 'protected' and len(samples['protected']) < sample_per_bucket:
            samples['protected'].append(_outcome_node_trace(node))
        elif bucket == 'expansion' and len(samples['expansion']) < sample_per_bucket:
            samples['expansion'].append(_outcome_node_trace(node))

    provenance = {
        'source': 'context_graph',
        'engine': 'aggregate_revenue_across_accounts',
        'outcome_node_count': len(outcome_nodes),
        'revenue_at_risk': {
            'value': base['revenue_at_risk'],
            'label': 'Confirmed Risk (Context Graph)',
            'sample_nodes': samples['at_risk'],
        },
        'revenue_protected': {
            'value': base['revenue_protected'],
            'label': 'Protected (Context Graph OUTCOME nodes)',
            'sample_nodes': samples['protected'],
        },
        'expansion_pipeline': {
            'value': base['expansion_pipeline'],
            'label': 'Expansion (Context Graph OUTCOME nodes)',
            'sample_nodes': samples['expansion'],
        },
    }
    return {**base, 'provenance': provenance}


def get_account_graph_summary(account_id: int, include_narrative: bool = False) -> Dict[str, Any]:
    """
    Quick summary of graph density for an account.
    Useful for dashboard widgets and health overview.

    Mirrors the narrative filter in get_context_graph_mermaid: by default
    excludes narrative-only OUTCOMEs (no revenue_impact, no source_ref, no
    properties.evidence) so both tools report the same counts on the same
    account. Set include_narrative=True to see the unfiltered count.
    """
    now = datetime.utcnow()
    base_filter = db.and_(
        ContextNode.account_id == account_id,
        db.or_(
            ContextNode.expires_at.is_(None),
            ContextNode.expires_at > now,
        )
    )

    # Narrative filter: narrative-only OUTCOMEs are those with no
    # revenue_impact, no source_ref, and no properties.evidence. Applied via
    # SQL NOT predicate so the count is correct at the DB layer (not
    # post-filtered in Python). Uses postgres `->>` operator to extract
    # evidence as text regardless of whether `properties` is JSON or JSONB.
    if not include_narrative:
        _evidence_text = ContextNode.properties.op('->>')('evidence')
        narrative_only = db.and_(
            ContextNode.node_type == 'OUTCOME',
            ContextNode.revenue_impact.is_(None),
            db.or_(
                ContextNode.source_ref.is_(None),
                ContextNode.source_ref == '',
            ),
            db.or_(
                _evidence_text.is_(None),
                _evidence_text == '',
            ),
        )
        base_filter = db.and_(base_filter, db.not_(narrative_only))

    node_counts = db.session.query(
        ContextNode.node_type,
        db.func.count(ContextNode.node_id)
    ).filter(base_filter).group_by(ContextNode.node_type).all()

    total_nodes = sum(c for _, c in node_counts)

    # Count edges — only those connecting two VISIBLE nodes (both endpoints
    # must pass the filter). Mirrors how mermaid renders.
    # Additionally exclude causal edges that violate temporal ordering
    # (cause.occurred_at > effect.occurred_at) — Wizard A's arc-detection
    # signal fires at customer-creation and back-emits LED_TO edges to
    # pre-existing outcomes. Mechanically backward; also filtered by mermaid.
    visible_node_ids_subq = db.session.query(ContextNode.node_id).filter(base_filter).subquery()

    from_alias = db.aliased(ContextNode)
    to_alias = db.aliased(ContextNode)
    _causal_types = ['CAUSED_BY', 'LED_TO', 'TRIGGERED', 'RESULTED_IN', 'INDICATES']

    edge_count = (
        db.session.query(ContextEdge.edge_id)
        .join(from_alias, ContextEdge.from_node_id == from_alias.node_id)
        .join(to_alias, ContextEdge.to_node_id == to_alias.node_id)
        .filter(
            ContextEdge.from_node_id.in_(visible_node_ids_subq),
            ContextEdge.to_node_id.in_(visible_node_ids_subq),
        )
        .filter(db.not_(db.and_(
            ContextEdge.edge_type.in_(_causal_types),
            from_alias.occurred_at > to_alias.occurred_at,
        )))
        .count()
    )

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

    Pre-commit validation:
      I4  — confidence and properties.confidence clamped to [0, 1]
      I3' — OUTCOME without evidence (properties.evidence OR source_ref)
            gets confidence capped at 0.3 and tier forced to 2
    """
    # I4 pre-commit clamp (top-level + JSONB). Clamps only; doesn't reject.
    try:
        from utils.context_graph_invariants import (
            clamp_confidence,
            sanitize_properties_confidence,
        )
        if 'confidence' in kwargs:
            kwargs['confidence'] = clamp_confidence(kwargs.get('confidence'))
        properties = sanitize_properties_confidence(properties)
    except Exception:
        pass  # invariants module optional — fall through

    # I3' pre-commit clamp (OUTCOME without evidence → unearned).
    try:
        from utils.context_graph_invariants import clamp_unearned_confidence
        new_conf, new_props, new_tier, was_clamped = clamp_unearned_confidence(
            node_type=node_type,
            source_platform=source_platform,
            source_ref=kwargs.get('source_ref'),
            confidence=kwargs.get('confidence'),
            properties=properties,
            tier=kwargs.get('tier'),
        )
        if was_clamped:
            kwargs['confidence'] = new_conf
            kwargs['tier'] = new_tier
            properties = new_props
            # Structured WARN on first occurrence per (source_platform, subtype)
            # so ops tooling can alert on "unearned OUTCOMEs in the wild".
            _unearned_key = (source_platform, kwargs.get('node_subtype'), kwargs.get('revenue_impact_type'))
            if _unearned_key not in _seen_unearned_clamps:
                _seen_unearned_clamps.add(_unearned_key)
                _unearned_clamp_logger.warning(
                    'event=unearned_confidence_clamp first_seen=true '
                    'node_type=OUTCOME source_platform=%s subtype=%s '
                    'revenue_impact_type=%s customer_id=%s account_id=%s '
                    'clamped_to=%s tier_forced=%s',
                    source_platform, kwargs.get('node_subtype'),
                    kwargs.get('revenue_impact_type'),
                    customer_id, account_id, new_conf, new_tier,
                )
            else:
                logger.debug(
                    '[invariants] I3\' unearned-confidence clamp: OUTCOME %s '
                    'confidence→%s tier→%s',
                    kwargs.get('node_subtype'), new_conf, new_tier,
                )
    except Exception as _e:
        logger.debug(f'[invariants] unearned-clamp pass-through (error): {_e}')

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

    Pre-commit validation (Apr 2026):
      I1 — OUTCOME→OUTCOME causal edges are REJECTED (returns (None, False))
      I2 — polarity-mismatched signal→outcome edges are REJECTED
      I4 — confidence is clamped to [0, 1]

    Rejection logs a WARN with the offending subtypes so the producer
    (wizard_a, auto_linker, llm_enrichment, playbook_execution) can be
    identified from logs. Callers that iterate and check `created` will
    naturally skip rejected edges (created=False + edge=None).

    Returns:
        (ContextEdge, created: bool) — True if new, False if updated OR rejected.
        When rejected, the first element is None.
    """
    # I4 clamp
    try:
        from utils.context_graph_invariants import clamp_confidence
        confidence = clamp_confidence(confidence) if confidence is not None else 1.0
        if confidence is None:
            confidence = 1.0
    except Exception:
        pass

    # I1 / I2 pre-commit gate: look up node types to validate polarity/direction.
    try:
        from utils.context_graph_invariants import validate_edge_pre_commit
        from_node = db.session.get(ContextNode, from_node_id)
        to_node = db.session.get(ContextNode, to_node_id)
        if from_node and to_node:
            ok, reason = validate_edge_pre_commit(
                from_node_type=from_node.node_type,
                from_node_subtype=from_node.node_subtype,
                to_node_type=to_node.node_type,
                to_node_subtype=to_node.node_subtype,
                edge_type=edge_type,
                source_platform=source_platform,
            )
            if not ok:
                reason_key = (reason or '').split(':', 1)[0]
                dedup_key = (
                    from_node.node_subtype, to_node.node_subtype, reason_key, source_platform,
                )
                if dedup_key not in _seen_rejections:
                    _seen_rejections.add(dedup_key)
                    # First-occurrence structured event — ops/SIEM alert target.
                    _precommit_rejection_logger.warning(
                        'event=pre_commit_rejection first_seen=true '
                        'from_subtype=%s to_subtype=%s edge_type=%s '
                        'source_platform=%s customer_id=%s reason=%s',
                        from_node.node_subtype, to_node.node_subtype, edge_type,
                        source_platform, customer_id, reason,
                    )
                else:
                    # Subsequent occurrences — standard WARN (not alerted).
                    logger.warning(
                        '[invariants] edge rejected: %s (from_node=%s to_node=%s)',
                        reason, from_node_id, to_node_id,
                    )
                return (None, False)
    except Exception:
        # Never fail ingest on invariant module errors — log and proceed.
        pass

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
