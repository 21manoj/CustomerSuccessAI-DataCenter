"""
Portfolio-wide revenue breakdown from context-graph OUTCOME nodes.

Shared by MCP get_portfolio_revenue_breakdown and Ask AI (single code path).
"""

from __future__ import annotations

from collections import defaultdict


def build_portfolio_revenue_breakdown(customer_id: int) -> dict:
    """Portfolio totals + top-3 accounts per revenue bucket."""
    from utils.context_graph import aggregate_revenue_across_accounts
    from models import Account, ContextNode, HealthScore

    account_rows = Account.query.filter_by(customer_id=customer_id).all()
    account_ids = [a.account_id for a in account_rows]
    accounts_by_id = {a.account_id: a for a in account_rows}

    totals = aggregate_revenue_across_accounts(
        customer_id=customer_id,
        account_ids=account_ids,
    )

    risk_types = {
        'at_risk', 'lost', 'revenue_at_risk', 'churn_lost', 'churn_risk',
        'engagement_decline', 'renewal_uncertainty', 'capacity_constraint',
        'partner_friction', 'partial_recovery',
    }
    protected_types = {
        'protected', 'revenue_protected', 'churn_averted', 'renewal_secured',
        'revenue_saved', 'engagement_recovery', 'escalation_resolved',
        'intervention_outcome',
    }
    expansion_types = {
        'expansion', 'expansion_closed', 'expansion_realized', 'revenue_expanded',
        'revenue_growth', 'new_logo', 'upsell', 'cross_sell',
    }
    pipeline_types = {'expansion_approved', 'expansion_opportunity', 'pipeline'}

    per_acct_at_risk = defaultdict(float)
    per_acct_protected = defaultdict(float)
    per_acct_expansion = defaultdict(float)

    outcome_nodes = (
        ContextNode.query.filter(
            ContextNode.customer_id == customer_id,
            ContextNode.account_id.in_(account_ids),
            ContextNode.node_type == 'OUTCOME',
            ContextNode.revenue_impact.isnot(None),
        ).all()
    )
    for node in outcome_nodes:
        try:
            raw = float(node.revenue_impact)
        except (TypeError, ValueError):
            continue
        impact_type = (node.revenue_impact_type or '').lower()
        subtype = (node.node_subtype or '').lower()
        amt = abs(raw)
        if impact_type in risk_types or subtype in risk_types:
            per_acct_at_risk[node.account_id] += amt
        elif impact_type in pipeline_types or subtype in pipeline_types:
            per_acct_expansion[node.account_id] += amt
        elif impact_type in expansion_types or subtype in expansion_types:
            per_acct_expansion[node.account_id] += amt
        elif impact_type in protected_types or subtype in protected_types:
            per_acct_protected[node.account_id] += amt
        elif raw < 0:
            per_acct_at_risk[node.account_id] += amt
        elif raw > 0:
            per_acct_protected[node.account_id] += raw

    latest_health = {}
    for aid in account_ids:
        hs = (
            HealthScore.query.filter_by(account_id=aid)
            .order_by(HealthScore.measurement_month.desc())
            .first()
        )
        if hs and hs.health_score is not None:
            latest_health[aid] = round(float(hs.health_score), 1)

    def _format_top(per_acct_dict, top_n=3):
        sorted_accts = sorted(per_acct_dict.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
        out = []
        for aid, amount in sorted_accts:
            if amount <= 0:
                continue
            acct = accounts_by_id.get(aid)
            if not acct:
                continue
            out.append({
                'account_id': aid,
                'account_name': acct.account_name,
                'arr': float(acct.revenue or 0),
                'amount': round(amount, 2),
                'health_score': latest_health.get(aid),
            })
        return out

    return {
        'scope': 'portfolio',
        'customer_id': customer_id,
        **totals,
        'top_at_risk_accounts': _format_top(per_acct_at_risk),
        'top_expansion_accounts': _format_top(per_acct_expansion),
        'top_protected_accounts': _format_top(per_acct_protected),
        '_synthesis_hint': (
            'Use top_*_accounts for per-account narrative. Do NOT call '
            'get_revenue_at_risk per-account — top_*_accounts already '
            'contains the highest-impact per-account dollar amounts.'
        ),
    }
