#!/usr/bin/env python3
"""
Context Graph REST API
======================
Account-scoped endpoints for querying and incrementally ingesting context graph data.
Exposes the graph helpers in utils/context_graph.py as REST endpoints.

Endpoints:
  GET  /api/context-graph/summary          — Graph density + revenue overview
  GET  /api/context-graph/nodes            — Query nodes with filters
  GET  /api/context-graph/edges/<node_id>  — Edges connected to a node
  GET  /api/context-graph/chain/<node_id>  — Walk causal chain from a node
  GET  /api/context-graph/ego/<node_id>    — 2-hop ego graph
  GET  /api/context-graph/revenue          — Revenue at risk breakdown
  POST /api/context-graph/ingest           — Incremental upsert of nodes + edges

Feature flag: 'context_graph' (global + per-customer DB toggle)
"""

import logging
from datetime import datetime

from flask import Blueprint, request, jsonify

from auth_middleware import get_current_customer_id
from feature_toggles import is_context_graph_enabled
from models import Account, ContextNode, ContextEdge
from extensions import db
from utils.context_graph import (
    get_nodes,
    get_edges,
    get_causal_chain,
    traverse_2hop,
    get_revenue_at_risk,
    get_account_graph_summary,
    aggregate_revenue_across_accounts,
    upsert_node,
    upsert_edge,
)

logger = logging.getLogger(__name__)

context_graph_api = Blueprint('context_graph_api', __name__)


# ─── Shared helpers ──────────────────────────────────────────────────────────

def _guard(customer_id: int, account_id: int = None):
    """
    Common auth + feature-toggle + tenant-isolation guard.

    Returns:
        (None, None) on success — caller proceeds.
        (response, status_code) on failure — caller returns immediately.
    """
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 400

    if not is_context_graph_enabled(customer_id):
        return jsonify({'error': 'Context graph not enabled for this customer'}), 403

    if account_id is not None:
        account = Account.query.filter_by(
            account_id=account_id, customer_id=customer_id
        ).first()
        if not account:
            return jsonify({'error': 'Account not found or access denied'}), 404

    return None, None


def _require_account_id():
    """Extract account_id from query params; returns (account_id, error_response)."""
    account_id = request.args.get('account_id', type=int)
    if not account_id:
        return None, (jsonify({'error': 'account_id query parameter is required'}), 400)
    return account_id, None


# ─── 1. Summary ──────────────────────────────────────────────────────────────

@context_graph_api.route('/api/context-graph/summary', methods=['GET'])
def graph_summary():
    """
    Graph density + revenue overview for a single account.
    Lightweight — good for dashboard cards.

    Query params:
        account_id (required): Account to summarize
    """
    try:
        customer_id = get_current_customer_id()
        account_id, err = _require_account_id()
        if err:
            return err

        fail = _guard(customer_id, account_id)
        if fail[0] is not None:
            return fail

        summary = get_account_graph_summary(account_id)
        return jsonify({'status': 'success', **summary})

    except Exception as e:
        logger.error(f"Error in graph_summary: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── 2. Nodes ────────────────────────────────────────────────────────────────

@context_graph_api.route('/api/context-graph/nodes', methods=['GET'])
def graph_nodes():
    """
    Query context graph nodes with filters.

    Query params:
        account_id  (required)
        node_type   — SIGNAL, STAKEHOLDER, DECISION, OUTCOME, EXTERNAL_CONTEXT
        node_subtype
        tier        — 1 (permanent), 2 (decaying), 3 (ephemeral)
        since       — ISO-8601 date string (e.g. 2026-01-01)
        limit       — max results (default 100)
    """
    try:
        customer_id = get_current_customer_id()
        account_id, err = _require_account_id()
        if err:
            return err

        fail = _guard(customer_id, account_id)
        if fail[0] is not None:
            return fail

        # Collect optional filters
        node_type = request.args.get('node_type')
        node_subtype = request.args.get('node_subtype')
        tier = request.args.get('tier', type=int)
        limit = request.args.get('limit', 100, type=int)

        since = None
        since_str = request.args.get('since')
        if since_str:
            try:
                since = datetime.fromisoformat(since_str)
            except ValueError:
                return jsonify({'error': f'Invalid since date: {since_str}'}), 400

        nodes = get_nodes(
            account_id=account_id,
            node_type=node_type,
            node_subtype=node_subtype,
            tier=tier,
            since=since,
            limit=limit,
        )

        return jsonify({
            'status': 'success',
            'account_id': account_id,
            'count': len(nodes),
            'nodes': [n.to_dict() for n in nodes],
        })

    except Exception as e:
        logger.error(f"Error in graph_nodes: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── 3. Edges ────────────────────────────────────────────────────────────────

@context_graph_api.route('/api/context-graph/edges/<int:node_id>', methods=['GET'])
def graph_edges(node_id: int):
    """
    Get edges connected to a node.

    Path params:
        node_id — The node to query

    Query params:
        direction  — outgoing, incoming, or both (default: both)
        edge_type  — LED_TO, CAUSED_BY, INVOLVES, INDICATES, etc.
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 400
        if not is_context_graph_enabled(customer_id):
            return jsonify({'error': 'Context graph not enabled for this customer'}), 403

        # Verify node belongs to customer (tenant isolation)
        node = ContextNode.query.filter_by(node_id=node_id).first()
        if not node:
            return jsonify({'error': 'Node not found'}), 404

        account = Account.query.filter_by(
            account_id=node.account_id, customer_id=customer_id
        ).first()
        if not account:
            return jsonify({'error': 'Access denied'}), 403

        direction = request.args.get('direction', 'both')
        edge_type = request.args.get('edge_type')

        edges = get_edges(node_id, direction=direction, edge_type=edge_type)

        return jsonify({
            'status': 'success',
            'node_id': node_id,
            'direction': direction,
            'count': len(edges),
            'edges': [e.to_dict() for e in edges],
        })

    except Exception as e:
        logger.error(f"Error in graph_edges: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── 3b. Bulk Edges by Account ────────────────────────────────────────────────

@context_graph_api.route('/api/context-graph/account-edges', methods=['GET'])
def graph_account_edges():
    """
    Get ALL edges between nodes belonging to an account.  Single round-trip
    replacement for N per-node edge queries.

    Query params:
        account_id  (required)
        limit       — max edges (default 500, max 2000)
    """
    try:
        customer_id = get_current_customer_id()
        account_id, err = _require_account_id()
        if err:
            return err

        fail = _guard(customer_id, account_id)
        if fail[0] is not None:
            return fail

        limit = min(request.args.get('limit', 500, type=int), 2000)

        # Get all node IDs for this account
        node_ids = [
            r[0] for r in
            db.session.query(ContextNode.node_id)
            .filter(ContextNode.account_id == account_id)
            .all()
        ]

        if not node_ids:
            return jsonify({
                'status': 'success',
                'account_id': account_id,
                'count': 0,
                'edges': [],
            })

        # Edges where BOTH endpoints belong to this account's nodes
        edges = (
            ContextEdge.query
            .filter(
                ContextEdge.from_node_id.in_(node_ids),
                ContextEdge.to_node_id.in_(node_ids),
            )
            .limit(limit)
            .all()
        )

        return jsonify({
            'status': 'success',
            'account_id': account_id,
            'count': len(edges),
            'edges': [e.to_dict() for e in edges],
        })

    except Exception as e:
        logger.error(f"Error in graph_account_edges: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── 4. Causal Chain ─────────────────────────────────────────────────────────

@context_graph_api.route('/api/context-graph/chain/<int:node_id>', methods=['GET'])
def graph_chain(node_id: int):
    """
    Walk causal chain (LED_TO / CAUSED_BY) from a node.

    Path params:
        node_id — Starting node

    Query params:
        direction  — upstream (follow CAUSED_BY) or downstream (follow LED_TO)
                     Default: downstream
        max_depth  — Max hops (default 5, max 10)
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 400
        if not is_context_graph_enabled(customer_id):
            return jsonify({'error': 'Context graph not enabled for this customer'}), 403

        # Verify node belongs to customer
        node = ContextNode.query.filter_by(node_id=node_id).first()
        if not node:
            return jsonify({'error': 'Node not found'}), 404

        account = Account.query.filter_by(
            account_id=node.account_id, customer_id=customer_id
        ).first()
        if not account:
            return jsonify({'error': 'Access denied'}), 403

        direction = request.args.get('direction', 'downstream')
        if direction not in ('upstream', 'downstream'):
            return jsonify({'error': 'direction must be upstream or downstream'}), 400

        max_depth = min(request.args.get('max_depth', 5, type=int), 10)

        chain = get_causal_chain(node_id, direction=direction, max_depth=max_depth)

        return jsonify({
            'status': 'success',
            'node_id': node_id,
            'direction': direction,
            'max_depth': max_depth,
            'chain_length': len(chain),
            'chain': chain,
        })

    except Exception as e:
        logger.error(f"Error in graph_chain: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── 5. Ego Graph (2-hop) ────────────────────────────────────────────────────

@context_graph_api.route('/api/context-graph/ego/<int:node_id>', methods=['GET'])
def graph_ego(node_id: int):
    """
    2-hop ego graph centered on a node.
    Returns all nodes and edges within 2 hops — useful for
    "impact neighborhood" visualization.

    Path params:
        node_id — Center node

    Query params:
        account_id  (required)
        edge_types  — Comma-separated filter (e.g. LED_TO,CAUSED_BY)
    """
    try:
        customer_id = get_current_customer_id()
        account_id, err = _require_account_id()
        if err:
            return err

        fail = _guard(customer_id, account_id)
        if fail[0] is not None:
            return fail

        edge_types = None
        edge_types_str = request.args.get('edge_types')
        if edge_types_str:
            edge_types = [et.strip() for et in edge_types_str.split(',')]

        result = traverse_2hop(
            account_id=account_id,
            center_node_id=node_id,
            edge_types=edge_types,
        )

        return jsonify({
            'status': 'success',
            **result,
        })

    except Exception as e:
        logger.error(f"Error in graph_ego: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── 6. Revenue at Risk ──────────────────────────────────────────────────────

@context_graph_api.route('/api/context-graph/revenue', methods=['GET'])
def graph_revenue():
    """
    Revenue at risk breakdown for an account.
    Primary CRO/CFO metric.

    Query params:
        account_id (required)

    Returns:
        at_risk, protected, expansion, lost, net_impact, node_count
    """
    try:
        customer_id = get_current_customer_id()
        account_id, err = _require_account_id()
        if err:
            return err

        fail = _guard(customer_id, account_id)
        if fail[0] is not None:
            return fail

        revenue = get_revenue_at_risk(account_id)

        return jsonify({
            'status': 'success',
            'account_id': account_id,
            **revenue,
        })

    except Exception as e:
        logger.error(f"Error in graph_revenue: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── 6b. Portfolio Revenue ─────────────────────────────────────────────────

@context_graph_api.route('/api/context-graph/portfolio-revenue', methods=['GET'])
def graph_portfolio_revenue():
    """
    Revenue breakdown aggregated across ALL accounts for the customer.
    Uses the same aggregate_revenue_across_accounts() function as CRO/CFO dashboards
    to ensure consistent numbers.

    Returns:
        revenue_at_risk, revenue_protected, expansion_pipeline, node_count,
        contributing_signals (count of SIGNAL nodes feeding into risk outcomes)
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 400

        # Get all account IDs for this customer
        account_ids = [
            a.account_id for a in
            Account.query.filter_by(customer_id=customer_id).all()
        ]

        if not account_ids:
            return jsonify({
                'status': 'success',
                'revenue_at_risk': 0,
                'revenue_protected': 0,
                'expansion_pipeline': 0,
                'node_count': 0,
                'contributing_signals': 0,
            })

        # Use the SAME function as CRO/CFO dashboards
        revenue = aggregate_revenue_across_accounts(customer_id, account_ids)

        # Also count contributing signals (SIGNAL nodes in at-risk accounts)
        at_risk_account_ids = [
            a.account_id for a in
            Account.query.filter_by(customer_id=customer_id).all()
            if a.account_id in account_ids
        ]
        signal_count = (
            ContextNode.query
            .filter(
                ContextNode.customer_id == customer_id,
                ContextNode.account_id.in_(account_ids),
                ContextNode.node_type == 'SIGNAL',
            )
            .count()
        )

        return jsonify({
            'status': 'success',
            'revenue_at_risk': revenue['revenue_at_risk'],
            'revenue_protected': revenue['revenue_protected'],
            'expansion_pipeline': revenue['expansion_pipeline'],
            'node_count': revenue['node_count'],
            'contributing_signals': signal_count,
        })

    except Exception as e:
        logger.error(f"Error in graph_portfolio_revenue: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── 7. Incremental Ingest ─────────────────────────────────────────────────

@context_graph_api.route('/api/context-graph/ingest', methods=['POST'])
def graph_ingest():
    """
    Incrementally upsert context graph nodes and edges.
    Unlike process_data() (which does a full DELETE + re-insert), this is
    non-destructive: it deduplicates via source_event_id for nodes and
    (from, to, edge_type, source_platform) for edges.

    JSON body:
        {
            "customer_id": 291,
            "nodes": [
                {
                    "account_id": 1001,
                    "node_type": "SIGNAL",
                    "node_subtype": "kpi_improvement",
                    "title": "...",
                    "occurred_at": "2026-01-15T00:00:00",
                    "source_event_id": "s9-acc1001-P1-signal-m1",
                    "source_platform": "scenario_9_roi",
                    "properties": {...},
                    "revenue_impact": 50000,
                    "revenue_impact_type": "protected",
                    "confidence": 0.85,
                    "tier": 1
                }, ...
            ],
            "edges": [
                {
                    "from_source_event_id": "s9-acc1001-P1-signal-m1",
                    "to_source_event_id": "s9-acc1001-P1-signal-m2",
                    "edge_type": "LED_TO",
                    "weight": 1.0,
                    "confidence": 0.9,
                    "source_platform": "scenario_9_roi",
                    "lag_days": 30,
                    "revenue_impact": 10000
                }, ...
            ]
        }

    Phase 1: Upsert all nodes → build source_event_id → node_id map
    Phase 2: Resolve edge references using the map, then upsert edges

    Returns:
        {status, nodes_upserted, nodes_created, nodes_updated,
         edges_upserted, edges_created, edges_updated}
    """
    try:
        customer_id = get_current_customer_id()
        if not customer_id:
            return jsonify({'error': 'Authentication required'}), 400

        if not is_context_graph_enabled(customer_id):
            return jsonify({'error': 'Context graph not enabled for this customer'}), 403

        data = request.get_json(force=True)
        if not data:
            return jsonify({'error': 'JSON body required'}), 400

        payload_customer_id = data.get('customer_id')
        if payload_customer_id and int(payload_customer_id) != customer_id:
            return jsonify({'error': 'customer_id mismatch with authenticated session'}), 403

        nodes_data = data.get('nodes', [])
        edges_data = data.get('edges', [])

        if not nodes_data and not edges_data:
            return jsonify({'error': 'At least one of nodes or edges is required'}), 400

        nodes_created = 0
        nodes_updated = 0
        edges_created = 0
        edges_updated = 0

        # ── Phase 1: Upsert nodes and build source_event_id → node_id map ──
        source_id_map = {}

        for nd in nodes_data:
            account_id = nd.get('account_id')
            if not account_id:
                continue

            # Verify account belongs to this customer
            acct = Account.query.filter_by(
                account_id=account_id, customer_id=customer_id
            ).first()
            if not acct:
                logger.warning(f"Ingest: skipping node for unknown account {account_id}")
                continue

            occurred_at_str = nd.get('occurred_at')
            try:
                occurred_at = datetime.fromisoformat(occurred_at_str) if occurred_at_str else datetime.utcnow()
            except (ValueError, TypeError):
                occurred_at = datetime.utcnow()

            source_event_id = nd.get('source_event_id')
            source_platform = nd.get('source_platform', 'api_ingest')

            # Check if node exists to track created vs updated
            from utils.context_graph import get_node_by_source
            existing = get_node_by_source(account_id, source_platform, source_event_id) if source_event_id else None

            node = upsert_node(
                customer_id=customer_id,
                account_id=account_id,
                node_type=nd.get('node_type', 'SIGNAL'),
                title=nd.get('title', ''),
                occurred_at=occurred_at,
                properties=nd.get('properties', {}),
                source_platform=source_platform,
                source_event_id=source_event_id,
                node_subtype=nd.get('node_subtype'),
                tier=nd.get('tier', 1),
                revenue_impact=nd.get('revenue_impact'),
                revenue_impact_type=nd.get('revenue_impact_type'),
                confidence=nd.get('confidence'),
            )

            if existing:
                nodes_updated += 1
            else:
                nodes_created += 1

            if source_event_id:
                source_id_map[source_event_id] = node.node_id

        # ── Phase 2: Resolve edge references and upsert edges ──
        for ed in edges_data:
            from_ref = ed.get('from_source_event_id')
            to_ref = ed.get('to_source_event_id')

            # Resolve source_event_id → node_id
            from_node_id = source_id_map.get(from_ref) if from_ref else ed.get('from_node_id')
            to_node_id = source_id_map.get(to_ref) if to_ref else ed.get('to_node_id')

            if not from_node_id or not to_node_id:
                logger.warning(
                    f"Ingest: skipping edge — unresolved refs "
                    f"from={from_ref}→{from_node_id}, to={to_ref}→{to_node_id}"
                )
                continue

            edge, created = upsert_edge(
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                edge_type=ed.get('edge_type', 'LED_TO'),
                weight=ed.get('weight', 1.0),
                confidence=ed.get('confidence', 1.0),
                source_platform=ed.get('source_platform', 'api_ingest'),
                created_by=ed.get('created_by', 'api_ingest'),
                customer_id=customer_id,
                lag_days=ed.get('lag_days'),
                revenue_impact=ed.get('revenue_impact'),
            )

            if created:
                edges_created += 1
            else:
                edges_updated += 1

        # ── Phase 3: Auto-link OUTCOME nodes to recent signals ──
        # For any OUTCOME node created without explicit edges, connect to the
        # most recent SIGNAL and DECISION nodes for that account. Enables
        # "Why did this happen?" causal traversal for lifecycle outcomes
        # (churn_lost, expansion_closed) and any other orphan outcomes.
        #
        # Polarity gate (Apr 2026): the prior implementation linked the 3 most
        # recent signals regardless of sentiment polarity, producing nonsense
        # edges like `kpi_recovery → churn_lost` (positive signal causing
        # negative outcome). Now we only cross-link same-polarity signals.
        NEGATIVE_OUTCOME_SUBTYPES = {
            'churn_lost', 'contraction', 'renewal_at_risk', 'revenue_at_risk',
            'escalation', 'intervention_outcome',
        }
        POSITIVE_OUTCOME_SUBTYPES = {
            'expansion_closed', 'new_logo', 'revenue_protected',
            'playbook_outcome', 'recovery_milestone',
        }
        NEGATIVE_SIGNAL_SUBTYPES = {
            'champion_loss', 'engagement_drop', 'usage_decline', 'kpi_decline',
            'escalation', 'support_escalation', 'executive_escalation',
            'critical_incident', 'competitive_eval', 'silent_churn',
            'budget_cut', 'contract_dispute', 'downgrade_request',
            'arc_detection',  # often triggered by negative state
            'crisis_event', 'integration_stall', 'churn_signal',
        }
        POSITIVE_SIGNAL_SUBTYPES = {
            'kpi_recovery', 'usage_spike', 'champion_reengagement',
            'executive_engagement', 'expansion_signal', 'csm_intervention',
            'feature_adoption_push', 'deployment_improvement',
            'recovery_milestone', 'qbr_positive', 'qbr_alignment',
            'adoption_growth', 'seasonal_peak', 'capacity_add',
            'health_improvement',
        }

        def _signal_polarity_matches(sig_subtype, out_subtype):
            """Return True if signal polarity is compatible with outcome polarity."""
            if not sig_subtype or not out_subtype:
                return True  # unknown = permissive
            if out_subtype in NEGATIVE_OUTCOME_SUBTYPES:
                return sig_subtype not in POSITIVE_SIGNAL_SUBTYPES
            if out_subtype in POSITIVE_OUTCOME_SUBTYPES:
                return sig_subtype not in NEGATIVE_SIGNAL_SUBTYPES
            return True

        for nd in nodes_data:
            if nd.get('node_type') != 'OUTCOME':
                continue
            source_event_id = nd.get('source_event_id')
            if not source_event_id:
                continue
            node_id = source_id_map.get(source_event_id)
            if not node_id:
                continue
            account_id = nd.get('account_id')

            # Check if this outcome already has incoming edges (from Phase 2 or prior)
            existing_incoming = ContextEdge.query.filter_by(
                customer_id=customer_id, to_node_id=node_id
            ).count()
            if existing_incoming > 0:
                continue  # Already connected

            # Pull more candidates and then polarity-filter — prevents the case
            # where the top-3 most recent signals all have wrong polarity and
            # we produce zero edges. We check ~10 candidates and keep up to 3.
            recent_signals = (
                ContextNode.query
                .filter(
                    ContextNode.customer_id == customer_id,
                    ContextNode.account_id == account_id,
                    ContextNode.node_type == 'SIGNAL',
                    ContextNode.node_id != node_id,
                )
                .order_by(ContextNode.occurred_at.desc())
                .limit(10)
                .all()
            )
            recent_decisions = (
                ContextNode.query
                .filter(
                    ContextNode.customer_id == customer_id,
                    ContextNode.account_id == account_id,
                    ContextNode.node_type == 'DECISION',
                    ContextNode.node_id != node_id,
                )
                .order_by(ContextNode.occurred_at.desc())
                .limit(5)
                .all()
            )

            subtype = nd.get('node_subtype', 'outcome')
            signal_count = 0
            for sig in recent_signals:
                if signal_count >= 3:
                    break
                if not _signal_polarity_matches(sig.node_subtype, subtype):
                    continue  # skip polarity-mismatched signals
                edge, created = upsert_edge(
                    from_node_id=sig.node_id, to_node_id=node_id,
                    edge_type='LED_TO', confidence=0.7,
                    source_platform='auto_linker', created_by='outcome_auto_linker',
                    customer_id=customer_id,
                    properties={'label': f'{sig.node_subtype or "signal"} → {subtype}'},
                )
                if created:
                    edges_created += 1
                signal_count += 1
            decision_count = 0
            for dec in recent_decisions:
                if decision_count >= 2:
                    break
                # DECISION nodes are neutral — link freely (for now).
                edge, created = upsert_edge(
                    from_node_id=dec.node_id, to_node_id=node_id,
                    edge_type='LED_TO', confidence=0.75,
                    source_platform='auto_linker', created_by='outcome_auto_linker',
                    customer_id=customer_id,
                    properties={'label': f'{dec.node_subtype or "decision"} → {subtype}'},
                )
                if created:
                    edges_created += 1
                decision_count += 1

        # ── Phase 4: Account-state reconciliation ──
        # When a lifecycle outcome (churn_lost or expansion_closed) is ingested,
        # the Account row must reflect the new state or list_accounts will
        # return ghost customers (e.g., Nimbus showing $1.5M ARR "at risk" when
        # it already churned). Prior behavior: OUTCOME node created in context
        # graph but Account row untouched, causing CRM↔CG divergence.
        # Account model already imported at module top; no local import needed.
        for nd in nodes_data:
            if nd.get('node_type') != 'OUTCOME':
                continue
            subtype = nd.get('node_subtype') or ''
            aid = nd.get('account_id')
            if not aid:
                continue
            acct = Account.query.filter_by(
                account_id=aid, customer_id=customer_id
            ).first()
            if not acct:
                continue
            if subtype == 'churn_lost':
                if acct.account_status != 'churned':
                    acct.account_status = 'churned'
                    # Preserve original ARR on the Account row for historical
                    # reporting; dashboards should filter on account_status.
            elif subtype == 'expansion_closed':
                # Grow the account's ARR by the realized expansion.
                expansion_arr = float(nd.get('revenue_impact') or 0)
                if expansion_arr > 0:
                    acct.revenue = float(acct.revenue or 0) + expansion_arr

        # Single commit for all nodes + edges
        db.session.commit()

        # ── Phase 5: Non-blocking invariant audit ──
        # Runs the 11 context-graph invariants and emits WARN logs for any
        # violations. Does NOT fail the ingest — violations surface in
        # platform logs + /api/admin/audit for triage. Pipeline completes
        # regardless so the fix-forward story still works.
        invariants_summary = None
        try:
            from utils.context_graph_invariants import (
                run_all_invariants,
                log_violations_summary,
            )
            violations = run_all_invariants(customer_id)
            invariants_summary = log_violations_summary(violations, customer_id)
        except Exception as _inv_err:
            logger.warning(
                "context_graph_invariants audit failed (non-fatal): %s", _inv_err
            )

        result = {
            'status': 'success',
            'nodes_upserted': nodes_created + nodes_updated,
            'nodes_created': nodes_created,
            'nodes_updated': nodes_updated,
            'edges_upserted': edges_created + edges_updated,
            'invariants_audit': invariants_summary,
            'edges_created': edges_created,
            'edges_updated': edges_updated,
        }
        logger.info(
            f"Context graph ingest for customer {customer_id}: "
            f"{result['nodes_upserted']} nodes ({nodes_created} new), "
            f"{result['edges_upserted']} edges ({edges_created} new)"
        )
        return jsonify(result)

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in graph_ingest: {e}", exc_info=True)
        return jsonify({'error': f'Ingest failed: {str(e)}'}), 500


# ─── 8. Journey Timeline ─────────────────────────────────────────────────────

@context_graph_api.route('/api/context-graph/journey-timeline', methods=['GET'])
def graph_journey_timeline():
    """
    Chronological timeline of ALL context graph events for an account.
    Replaces multiple search_signals calls with a single unified endpoint.

    Query params:
        account_id (required)
        limit      (optional, default 50, max 200)

    Returns:
        account info, date_range, counts_by_type, revenue_summary, timeline[]
    """
    try:
        customer_id = get_current_customer_id()
        account_id, err = _require_account_id()
        if err:
            return err

        fail = _guard(customer_id, account_id)
        if fail[0] is not None:
            return fail

        account = Account.query.filter_by(
            account_id=account_id, customer_id=customer_id,
        ).first()

        limit = min(max(request.args.get('limit', 50, type=int), 1), 200)
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
            .limit(limit)
            .all()
        )

        rev = get_revenue_at_risk(account_id)

        if not nodes:
            return jsonify({
                'status': 'success',
                'scope': 'account',
                'account_id': account_id,
                'account_name': account.account_name if account else None,
                'event_count': 0,
                'timeline': [],
                'revenue_summary': rev,
            })

        counts = {}
        for n in nodes:
            counts[n.node_type] = counts.get(n.node_type, 0) + 1

        timeline = []
        for n in nodes:
            props = n.properties or {}
            entry = {
                'node_id': n.node_id,
                'node_type': n.node_type,
                'node_subtype': n.node_subtype,
                'title': n.title,
                'occurred_at': n.occurred_at.isoformat() if n.occurred_at else None,
            }
            sentiment = props.get('sentiment') or props.get('sentiment_score')
            if sentiment is not None:
                entry['sentiment'] = sentiment
            sname = props.get('stakeholder_name') or props.get('stakeholder_title')
            if sname:
                entry['stakeholder'] = sname
            if n.revenue_impact is not None:
                entry['revenue_impact'] = float(n.revenue_impact)
                entry['revenue_impact_type'] = n.revenue_impact_type
            timeline.append(entry)

        arr = float(account.revenue) if account and account.revenue else 0

        return jsonify({
            'status': 'success',
            'scope': 'account',
            'account_id': account_id,
            'account_name': account.account_name if account else None,
            'arr': arr,
            'date_range': {
                'start': nodes[0].occurred_at.isoformat() if nodes[0].occurred_at else None,
                'end': nodes[-1].occurred_at.isoformat() if nodes[-1].occurred_at else None,
            },
            'event_count': len(nodes),
            'counts_by_type': counts,
            'revenue_summary': rev,
            'timeline': timeline,
        })

    except Exception as e:
        logger.error(f"Error in graph_journey_timeline: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


# ─── 9. Stakeholder Map ──────────────────────────────────────────────────────

@context_graph_api.route('/api/context-graph/stakeholder-map', methods=['GET'])
def graph_stakeholder_map():
    """
    Stakeholder network for an account — who influenced which decisions/outcomes.

    Query params:
        account_id (required)

    Returns:
        stakeholder_count, stakeholders[] with connected decisions/outcomes,
        influence_summary
    """
    try:
        customer_id = get_current_customer_id()
        account_id, err = _require_account_id()
        if err:
            return err

        fail = _guard(customer_id, account_id)
        if fail[0] is not None:
            return fail

        account = Account.query.filter_by(
            account_id=account_id, customer_id=customer_id,
        ).first()
        now = datetime.utcnow()

        # Fetch stakeholder, decision, and outcome nodes
        stakeholder_nodes = (
            ContextNode.query
            .filter(
                ContextNode.account_id == account_id,
                ContextNode.node_type == 'STAKEHOLDER',
                db.or_(ContextNode.expires_at.is_(None), ContextNode.expires_at > now),
            )
            .order_by(ContextNode.occurred_at.asc())
            .all()
        )

        decision_nodes = {
            n.node_id: n
            for n in ContextNode.query.filter(
                ContextNode.account_id == account_id,
                ContextNode.node_type == 'DECISION',
            ).all()
        }
        outcome_nodes = {
            n.node_id: n
            for n in ContextNode.query.filter(
                ContextNode.account_id == account_id,
                ContextNode.node_type == 'OUTCOME',
            ).all()
        }

        # Find INVOLVES edges connected to stakeholders
        stakeholder_ids = [s.node_id for s in stakeholder_nodes]
        involves_edges = []
        if stakeholder_ids:
            involves_edges = (
                ContextEdge.query
                .filter(
                    ContextEdge.edge_type == 'INVOLVES',
                    db.or_(
                        ContextEdge.from_node_id.in_(stakeholder_ids),
                        ContextEdge.to_node_id.in_(stakeholder_ids),
                    ),
                )
                .all()
            )

        # Build adjacency map
        connections = {s.node_id: set() for s in stakeholder_nodes}
        for e in involves_edges:
            if e.from_node_id in connections:
                connections[e.from_node_id].add(e.to_node_id)
            if e.to_node_id in connections:
                connections[e.to_node_id].add(e.from_node_id)

        # Also match via decision_maker_role in decision properties
        for dec in decision_nodes.values():
            maker_role = (dec.properties or {}).get('decision_maker_role', '')
            if maker_role:
                for s in stakeholder_nodes:
                    if (
                        maker_role.lower() in (s.node_subtype or '').lower()
                        or maker_role.lower() in (s.title or '').lower()
                    ):
                        connections[s.node_id].add(dec.node_id)

        total_decisions = 0
        total_outcomes = 0
        total_revenue = 0.0
        stakeholders = []

        for s in stakeholder_nodes:
            props = s.properties or {}
            connected = connections.get(s.node_id, set())

            connected_decs = []
            connected_outs = []
            for cid in connected:
                if cid in decision_nodes:
                    d = decision_nodes[cid]
                    connected_decs.append({
                        'node_id': d.node_id,
                        'title': d.title,
                        'occurred_at': d.occurred_at.isoformat() if d.occurred_at else None,
                    })
                if cid in outcome_nodes:
                    o = outcome_nodes[cid]
                    rev = float(o.revenue_impact) if o.revenue_impact else 0
                    connected_outs.append({
                        'node_id': o.node_id,
                        'title': o.title,
                        'revenue_impact': rev,
                        'revenue_impact_type': o.revenue_impact_type,
                    })
                    total_revenue += abs(rev)

            total_decisions += len(connected_decs)
            total_outcomes += len(connected_outs)

            stakeholders.append({
                'node_id': s.node_id,
                'name': s.title,
                'role': s.node_subtype,
                'engagement_frequency': props.get('engagement_frequency'),
                'department': props.get('department'),
                'is_active': props.get('is_active', True),
                'sentiment': props.get('sentiment'),
                'connected_decisions': connected_decs,
                'connected_outcomes': connected_outs,
                'edge_count': len(connected),
            })

        stakeholders.sort(key=lambda x: x['edge_count'], reverse=True)

        def _fmt_rev(v):
            if v >= 1_000_000:
                return f'${v / 1_000_000:.1f}M'
            if v >= 1_000:
                return f'${v / 1_000:.0f}K'
            return f'${v:.0f}'

        return jsonify({
            'status': 'success',
            'scope': 'account',
            'account_id': account_id,
            'account_name': account.account_name if account else None,
            'stakeholder_count': len(stakeholders),
            'stakeholders': stakeholders,
            'influence_summary': (
                f"{len(stakeholders)} stakeholders, "
                f"{total_decisions} decision links, "
                f"{total_outcomes} outcome links, "
                f"{_fmt_rev(total_revenue)} total revenue influenced"
            ),
        })

    except Exception as e:
        logger.error(f"Error in graph_stakeholder_map: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@context_graph_api.route('/api/context-graph/topology-health', methods=['GET'])
def graph_topology_health():
    """
    Validate context graph topology for an account or all accounts.

    Query params:
        account_id (optional) — validate single account. If omitted, validates all.

    Returns:
        Topology score, node/edge counts, orphan nodes, broken chains,
        disconnected stakeholders, and actionable recommendations.
    """
    try:
        customer_id = get_current_customer_id()
        from utils.topology_validator import validate_topology, validate_customer_topology

        account_id = request.args.get('account_id', type=int)

        if account_id:
            # Single account validation
            fail = _guard(customer_id, account_id)
            if fail[0] is not None:
                return fail

            report = validate_topology(customer_id, account_id)
            return jsonify({
                'status': 'success',
                'scope': 'account',
                **report.to_dict(),
            })
        else:
            # Full customer validation
            result = validate_customer_topology(customer_id)
            return jsonify({
                'status': 'success',
                'scope': 'customer',
                **result,
            })

    except Exception as e:
        logger.error(f"Error in graph_topology_health: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
