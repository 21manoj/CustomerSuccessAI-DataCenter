"""
Context graph preamble for Ask AI (v1 + v2) and shared revenue trace helpers.

Loads context graph nodes/edges and portfolio facts before the LLM answers so
revenue figures match executive dashboards (aggregate_revenue_across_accounts).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from extensions import db
from models import (
    Account,
    ContextEdge,
    ContextNode,
    HealthScore,
    PillarScore,
    PlaybookExecutionV2,
    ROISnapshot,
)
from utils.context_graph import aggregate_revenue_across_accounts
import utils.health_thresholds as ht

logger = logging.getLogger(__name__)


def build_ask_context_graph_block(
    customer_id: int,
    *,
    max_nodes: int = 200,
    max_edges: int = 300,
    max_signals: int = 20,
    max_playbooks: int = 15,
) -> Tuple[str, Dict[str, Any]]:
    """
    Build structured context string from DB + context graph for Ask AI prompts.

    Returns:
        (context_text, stats_dict)
    """
    accounts = Account.query.filter_by(customer_id=customer_id).all()
    if not accounts:
        return "No accounts found for this customer.", {'accounts': 0}

    account_ids = [a.account_id for a in accounts]
    account_lookup = {a.account_id: a for a in accounts}

    health_rows = (
        db.session.query(HealthScore)
        .filter(HealthScore.account_id.in_(account_ids))
        .order_by(HealthScore.measurement_month.desc())
        .all()
    )
    latest_health: Dict[int, HealthScore] = {}
    for h in health_rows:
        if h.account_id not in latest_health:
            latest_health[h.account_id] = h

    pillar_rows = (
        db.session.query(PillarScore)
        .filter(PillarScore.account_id.in_(account_ids))
        .order_by(PillarScore.measurement_month.desc())
        .all()
    )
    pillars_by_account: Dict[int, Dict[str, float]] = {}
    for p in pillar_rows:
        if p.account_id not in pillars_by_account:
            pillars_by_account[p.account_id] = {}
        pc = p.pillar_code
        if pc not in pillars_by_account[p.account_id]:
            pillars_by_account[p.account_id][pc] = float(p.pillar_score or 0)

    ctx_nodes = (
        ContextNode.query
        .filter(ContextNode.customer_id == customer_id)
        .order_by(ContextNode.occurred_at.desc())
        .limit(max_nodes)
        .all()
    )

    node_ids = [n.node_id for n in ctx_nodes]
    ctx_edges: List[ContextEdge] = []
    if node_ids:
        ctx_edges = (
            ContextEdge.query
            .filter(
                ContextEdge.from_node_id.in_(node_ids),
                ContextEdge.to_node_id.in_(node_ids),
            )
            .limit(max_edges)
            .all()
        )

    roi_snap = (
        ROISnapshot.query
        .filter_by(customer_id=customer_id)
        .order_by(ROISnapshot.created_at.desc())
        .first()
    )

    recent_playbooks = (
        PlaybookExecutionV2.query
        .filter(PlaybookExecutionV2.account_id.in_(account_ids))
        .order_by(PlaybookExecutionV2.triggered_at.desc())
        .limit(30)
        .all()
    )

    ctx_parts: List[str] = []

    total_arr = sum(a.revenue or 0 for a in accounts)
    critical = [
        a for a in accounts
        if latest_health.get(a.account_id)
        and ht.classify(latest_health[a.account_id].health_score) == 'critical'
    ]
    at_risk = [
        a for a in accounts
        if latest_health.get(a.account_id)
        and ht.classify(latest_health[a.account_id].health_score) == 'at_risk'
    ]
    healthy = [
        a for a in accounts
        if latest_health.get(a.account_id)
        and ht.classify(latest_health[a.account_id].health_score) == 'healthy'
    ]

    ctx_parts.append(
        f"""=== PORTFOLIO SUMMARY ===
Total accounts: {len(accounts)} | Total ARR: ${total_arr:,.0f}
Critical: {len(critical)} accounts | At-Risk: {len(at_risk)} | Healthy: {len(healthy)}
Health thresholds: Critical (<{ht.at_risk_min()}), At-Risk ({ht.at_risk_min()}-{ht.healthy_min() - 1}), Healthy (>={ht.healthy_min()})"""
    )

    ctx_parts.append("\n=== ACCOUNT DETAILS ===")
    for acc in sorted(
        accounts,
        key=lambda a: getattr(latest_health.get(a.account_id), 'health_score', 50) or 50,
    ):
        hs = latest_health.get(acc.account_id)
        score = float(hs.health_score) if hs else 50.0
        status = ht.classify(score)
        pillars = pillars_by_account.get(acc.account_id, {})
        pillar_str = ', '.join(f"{k}={v:.0f}" for k, v in pillars.items()) if pillars else 'no pillar data'
        ctx_parts.append(
            f"  {acc.account_name}: ARR=${acc.revenue or 0:,.0f}, Health={score:.0f} ({status}), "
            f"Pillars: [{pillar_str}]"
        )

    revenue_data = aggregate_revenue_across_accounts(customer_id, account_ids)
    ctx_parts.append(
        f"""\n=== REVENUE INTELLIGENCE (Context Graph — canonical source for $ at risk / protected / expansion) ===
Risk Exposure: ${revenue_data['revenue_at_risk']:,.0f} (OUTCOME nodes, engine: aggregate_revenue_across_accounts — node-evidenced, NOT independently verified)
Customer-Reported Saves: ${revenue_data['revenue_protected']:,.0f} (from customer-uploaded outcome data, NOT independently verified — never call this "confirmed")
Expansion Pipeline: ${revenue_data['expansion_pipeline']:,.0f}
Outcome nodes counted: {revenue_data['node_count']}
RULE: When answering revenue-at-risk questions, cite these totals — not critical-account ARR alone.
RULE: Never describe Risk Exposure or Customer-Reported Saves as "confirmed" or "verified" — they are
sourced from customer-uploaded data taken at face value, not an independent audit trail."""
    )

    signals = [n for n in ctx_nodes if n.node_type == 'SIGNAL'][:max_signals]
    decisions = [n for n in ctx_nodes if n.node_type == 'DECISION'][:10]
    outcomes = [n for n in ctx_nodes if n.node_type == 'OUTCOME'][:10]
    stakeholders = [n for n in ctx_nodes if n.node_type == 'STAKEHOLDER'][:10]

    if signals:
        ctx_parts.append("\n=== KEY SIGNALS (cite node_id when referencing) ===")
        for s in signals:
            acct_name = account_lookup.get(s.account_id, type('', (), {'account_name': '?'})).account_name
            ctx_parts.append(
                f"  [node_id={s.node_id}] [{acct_name}] {s.title or s.node_subtype}: "
                f"confidence={s.confidence or 0:.0%}, "
                f"revenue_impact=${s.revenue_impact or 0:,.0f} ({s.revenue_impact_type or 'n/a'})"
            )

    if decisions:
        ctx_parts.append("\n=== KEY DECISIONS ===")
        for d in decisions:
            acct_name = account_lookup.get(d.account_id, type('', (), {'account_name': '?'})).account_name
            ctx_parts.append(f"  [node_id={d.node_id}] [{acct_name}] {d.title or d.node_subtype}")

    if outcomes:
        ctx_parts.append("\n=== KEY OUTCOMES ===")
        for o in outcomes:
            acct_name = account_lookup.get(o.account_id, type('', (), {'account_name': '?'})).account_name
            ctx_parts.append(
                f"  [node_id={o.node_id}] [{acct_name}] {o.title or o.node_subtype}: "
                f"${o.revenue_impact or 0:,.0f} ({o.revenue_impact_type or 'n/a'})"
            )

    if stakeholders:
        ctx_parts.append("\n=== KEY STAKEHOLDERS ===")
        for sh in stakeholders:
            acct_name = account_lookup.get(sh.account_id, type('', (), {'account_name': '?'})).account_name
            props = sh.properties or {}
            ctx_parts.append(
                f"  [node_id={sh.node_id}] [{acct_name}] {sh.title or sh.node_subtype}: "
                f"sentiment={props.get('sentiment', 'n/a')}, influence={props.get('influence', 'n/a')}"
            )

    if ctx_edges:
        node_map = {n.node_id: n for n in ctx_nodes}
        ctx_parts.append("\n=== CAUSAL CHAINS (cause → effect) ===")
        edge_with_impact = []
        for e in ctx_edges:
            to_node = node_map.get(e.to_node_id)
            impact = abs(to_node.revenue_impact or 0) if to_node else 0
            edge_with_impact.append((e, impact))
        edge_with_impact.sort(key=lambda x: x[1], reverse=True)
        for edge, impact in edge_with_impact[:10]:
            from_n = node_map.get(edge.from_node_id)
            to_n = node_map.get(edge.to_node_id)
            if from_n and to_n:
                ctx_parts.append(
                    f"  {from_n.node_type}:{from_n.title or from_n.node_subtype} "
                    f"──{edge.edge_type}──> "
                    f"{to_n.node_type}:{to_n.title or to_n.node_subtype} "
                    f"(${impact:,.0f})"
                )

    if roi_snap:
        ctx_parts.append(
            f"""\n=== ROI DATA ===
Historical ROI: {roi_snap.historical_roi_pct:.0f}%
Investment: ${roi_snap.historical_investment:,.0f}
Impact: ${roi_snap.historical_impact:,.0f}
Forward ROI: {roi_snap.forward_roi_pct:.0f}%
Forward Impact: ${roi_snap.forward_impact:,.0f}"""
        )

    if recent_playbooks:
        ctx_parts.append("\n=== RECENT PLAYBOOK ACTIVITY ===")
        for pb in recent_playbooks[:max_playbooks]:
            acct_name = account_lookup.get(pb.account_id, type('', (), {'account_name': '?'})).account_name
            triggered = pb.triggered_at.strftime('%Y-%m-%d') if pb.triggered_at else 'n/a'
            ctx_parts.append(
                f"  [{acct_name}] {pb.playbook_id}: status={pb.status}, triggered={triggered}"
            )

    stats = {
        'accounts': len(accounts),
        'signals': len(signals),
        'decisions': len(decisions),
        'outcomes': len(outcomes),
        'stakeholders': len(stakeholders),
        'causal_edges': len(ctx_edges),
        'context_graph_nodes_loaded': len(ctx_nodes),
        'total_arr': total_arr,
        'revenue_at_risk': revenue_data['revenue_at_risk'],
        'revenue_protected': revenue_data['revenue_protected'],
        'expansion_pipeline': revenue_data['expansion_pipeline'],
        'context_graph_loaded': True,
    }
    return '\n'.join(ctx_parts), stats
