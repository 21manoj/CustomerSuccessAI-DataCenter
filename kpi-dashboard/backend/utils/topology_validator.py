#!/usr/bin/env python3
"""
Context Graph Topology Validator
=================================

Validates that the context graph for an account has complete causal chains
(SIGNAL -> DECISION -> OUTCOME) and flags gaps.

Called:
  - After Wizard A completes (edge generation)
  - On-demand via /api/context-graph/topology-health endpoint
  - From admin UI for diagnostics

Returns a TopologyReport with:
  - Node counts by type
  - Edge counts by type
  - Orphan nodes (no edges)
  - Broken chains (SIGNAL with no downstream DECISION/OUTCOME)
  - Disconnected stakeholders (STAKEHOLDER with no INVOLVES edges)
  - Overall topology_score (0-100)
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TopologyReport:
    """Structured report of context graph topology health."""
    account_id: int
    customer_id: int

    # Node counts
    signal_count: int = 0
    decision_count: int = 0
    outcome_count: int = 0
    stakeholder_count: int = 0
    external_count: int = 0
    total_nodes: int = 0

    # Edge counts
    edge_count: int = 0
    causal_edge_count: int = 0      # LED_TO, TRIGGERED, CAUSED_BY
    involves_edge_count: int = 0     # INVOLVES
    relates_edge_count: int = 0      # RELATES_TO, CORRELATES

    # Gaps
    orphan_nodes: list = field(default_factory=list)       # Nodes with zero edges
    broken_chains: list = field(default_factory=list)       # SIGNALs with no downstream
    disconnected_stakeholders: list = field(default_factory=list)  # STAKEHOLDERs with no INVOLVES
    missing_csv_types: list = field(default_factory=list)   # Expected node types not found

    # Score
    topology_score: int = 0  # 0-100
    recommendations: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


CAUSAL_EDGE_TYPES = {'LED_TO', 'TRIGGERED', 'CAUSED_BY'}
INVOLVES_TYPES = {'INVOLVES'}


def validate_topology(customer_id: int, account_id: int) -> TopologyReport:
    """Validate context graph topology for a single account.

    Returns TopologyReport with gaps and recommendations.
    Never raises — returns empty report on error.
    """
    report = TopologyReport(account_id=account_id, customer_id=customer_id)

    try:
        from models import ContextNode, ContextEdge, db

        # 1. Count nodes by type
        nodes = (
            ContextNode.query
            .filter_by(account_id=account_id, customer_id=customer_id)
            .all()
        )
        node_ids = set()
        nodes_by_type = {}
        for n in nodes:
            node_ids.add(n.node_id)
            nodes_by_type.setdefault(n.node_type, []).append(n)

        report.signal_count = len(nodes_by_type.get('SIGNAL', []))
        report.decision_count = len(nodes_by_type.get('DECISION', []))
        report.outcome_count = len(nodes_by_type.get('OUTCOME', []))
        report.stakeholder_count = len(nodes_by_type.get('STAKEHOLDER', []))
        report.external_count = len(nodes_by_type.get('EXTERNAL_CONTEXT', []))
        report.total_nodes = len(nodes)

        if not nodes:
            report.missing_csv_types = ['signals', 'decisions', 'outcomes', 'stakeholders']
            report.recommendations.append('No context graph data. Upload engagement_events.csv, decisions.csv, outcomes.csv, and stakeholders.csv.')
            return report

        # 2. Count edges
        edges = (
            ContextEdge.query
            .filter(
                ContextEdge.customer_id == customer_id,
                db.or_(
                    ContextEdge.from_node_id.in_(node_ids),
                    ContextEdge.to_node_id.in_(node_ids),
                ),
            )
            .all()
        )
        report.edge_count = len(edges)

        # Build adjacency sets
        has_outgoing = set()  # node_ids that have at least one outgoing edge
        has_incoming = set()  # node_ids that have at least one incoming edge
        has_involves = set()  # stakeholder node_ids with INVOLVES edges

        for e in edges:
            has_outgoing.add(e.from_node_id)
            has_incoming.add(e.to_node_id)

            if e.edge_type in CAUSAL_EDGE_TYPES:
                report.causal_edge_count += 1
            elif e.edge_type in INVOLVES_TYPES:
                report.involves_edge_count += 1
                has_involves.add(e.from_node_id)
                has_involves.add(e.to_node_id)
            else:
                report.relates_edge_count += 1

        # 3. Find orphan nodes (no edges at all)
        connected = has_outgoing | has_incoming
        for n in nodes:
            if n.node_id not in connected:
                report.orphan_nodes.append({
                    'node_id': n.node_id,
                    'node_type': n.node_type,
                    'title': n.title or f'{n.node_type} #{n.node_id}',
                })

        # 4. Find broken chains — SIGNALs with no downstream causal edge
        for sig in nodes_by_type.get('SIGNAL', []):
            has_downstream = any(
                e.from_node_id == sig.node_id and e.edge_type in CAUSAL_EDGE_TYPES
                for e in edges
            )
            if not has_downstream:
                report.broken_chains.append({
                    'node_id': sig.node_id,
                    'title': sig.title or f'SIGNAL #{sig.node_id}',
                    'subtype': sig.node_subtype,
                    'issue': 'No downstream causal edge (LED_TO/TRIGGERED) to DECISION or OUTCOME',
                })

        # 5. Find disconnected stakeholders
        for sh in nodes_by_type.get('STAKEHOLDER', []):
            if sh.node_id not in has_involves:
                report.disconnected_stakeholders.append({
                    'node_id': sh.node_id,
                    'title': sh.title or f'STAKEHOLDER #{sh.node_id}',
                    'issue': 'No INVOLVES edges to any DECISION node',
                })

        # 6. Check for missing expected node types
        if report.signal_count == 0:
            report.missing_csv_types.append('signals')
        if report.decision_count == 0:
            report.missing_csv_types.append('decisions')
        if report.outcome_count == 0:
            report.missing_csv_types.append('outcomes')
        if report.stakeholder_count == 0:
            report.missing_csv_types.append('stakeholders')

        # 7. Compute topology score (0-100)
        score = 100
        # Deduct for missing node types (-15 each)
        score -= len(report.missing_csv_types) * 15
        # Deduct for orphan nodes (-2 each, max -20)
        score -= min(len(report.orphan_nodes) * 2, 20)
        # Deduct for broken chains (-3 each, max -20)
        score -= min(len(report.broken_chains) * 3, 20)
        # Deduct for disconnected stakeholders (-5 each, max -15)
        score -= min(len(report.disconnected_stakeholders) * 5, 15)
        # Bonus for causal edges (+1 per edge, max +10)
        score += min(report.causal_edge_count, 10)
        # Bonus for INVOLVES edges (+2 per edge, max +10)
        score += min(report.involves_edge_count * 2, 10)

        report.topology_score = max(0, min(100, score))

        # 8. Generate recommendations
        if report.missing_csv_types:
            missing = ', '.join(report.missing_csv_types)
            report.recommendations.append(f'Missing node types: {missing}. Upload corresponding CSV files.')

        if len(report.orphan_nodes) > 3:
            report.recommendations.append(
                f'{len(report.orphan_nodes)} orphan nodes have no edges. '
                f'Run Wizard A to generate arc-based edges, or upload signal_edges.csv.'
            )

        if len(report.broken_chains) > 2:
            report.recommendations.append(
                f'{len(report.broken_chains)} SIGNAL nodes have no downstream causal chain. '
                f'Upload decisions.csv and signal_edges.csv to link signals to decisions.'
            )

        if report.disconnected_stakeholders:
            report.recommendations.append(
                f'{len(report.disconnected_stakeholders)} stakeholders are not linked to any decisions. '
                f'Ensure decisions.csv includes decision_maker_role matching stakeholder roles.'
            )

        if report.causal_edge_count == 0 and report.total_nodes > 5:
            report.recommendations.append(
                'No causal edges found. The context graph has nodes but no cause-effect chains. '
                'Run Wizard A or upload signal_edges.csv with LED_TO/TRIGGERED edge types.'
            )

    except Exception as e:
        logger.error(f"topology_validator: validation failed for account {account_id}: {e}", exc_info=True)
        report.recommendations.append(f'Validation error: {str(e)[:200]}')

    return report


def validate_customer_topology(customer_id: int) -> dict:
    """Validate topology for all accounts under a customer.

    Returns:
        {
            'customer_id': int,
            'total_accounts': int,
            'accounts_with_graph': int,
            'avg_topology_score': float,
            'worst_accounts': [...],
            'summary': {...},
            'accounts': [TopologyReport.to_dict(), ...]
        }
    """
    try:
        from models import Account

        accounts = Account.query.filter_by(customer_id=customer_id).all()
        reports = []

        for account in accounts:
            report = validate_topology(customer_id, account.account_id)
            if report.total_nodes > 0:
                reports.append(report)

        accounts_with_graph = len(reports)
        avg_score = (
            sum(r.topology_score for r in reports) / accounts_with_graph
            if accounts_with_graph > 0 else 0
        )

        # Sort by score ascending (worst first)
        reports.sort(key=lambda r: r.topology_score)

        # Aggregate summary
        total_orphans = sum(len(r.orphan_nodes) for r in reports)
        total_broken = sum(len(r.broken_chains) for r in reports)
        total_disconnected_sh = sum(len(r.disconnected_stakeholders) for r in reports)

        return {
            'customer_id': customer_id,
            'total_accounts': len(accounts),
            'accounts_with_graph': accounts_with_graph,
            'avg_topology_score': round(avg_score, 1),
            'worst_accounts': [r.to_dict() for r in reports[:5]],
            'summary': {
                'total_orphan_nodes': total_orphans,
                'total_broken_chains': total_broken,
                'total_disconnected_stakeholders': total_disconnected_sh,
            },
            'accounts': [r.to_dict() for r in reports],
        }

    except Exception as e:
        logger.error(f"topology_validator: customer validation failed: {e}", exc_info=True)
        return {
            'customer_id': customer_id,
            'error': str(e),
            'total_accounts': 0,
            'accounts_with_graph': 0,
            'avg_topology_score': 0,
        }
