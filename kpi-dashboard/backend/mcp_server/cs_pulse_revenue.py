#!/usr/bin/env python3
"""
CS Pulse MCP — Revenue Intelligence & ROI tier.

7 tools covering context-graph revenue, ROI stories, portfolio views,
and cross-customer comparisons.

Port: 8002 (HTTP) or stdio.
"""

import os
import sys

# Ensure backend is on the Python path
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp_server import common

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "CS Pulse Revenue Intelligence",
    instructions=common.load_system_prompt(),
)


# ===================================================================
# Context Graph / Revenue Intelligence (3 tools)
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
    common.check_mcp_enabled()
    common.require_account_auth(customer_id, account_id)
    app = common.get_flask_app()

    with app.app_context():
        common.check_context_graph(customer_id)
        from utils.context_graph import get_revenue_at_risk as _get_rev

        account = common.validate_account_ownership(customer_id, account_id)
        result = _get_rev(account_id)
        result["scope"] = "account"
        result["account_id"] = account_id
        result["account_name"] = account.account_name
        return result


@mcp.tool
def get_causal_chain(customer_id: int, node_id: int, direction: str = "upstream") -> dict:
    """Traverse the causal chain (Signal → Decision → Outcome) from a context graph node.

    Args:
        customer_id: The customer (tenant) ID
        node_id: The starting context graph node ID
        direction: 'upstream' (what caused this) or 'downstream' (what this led to)
    """
    common.check_mcp_enabled()
    common.require_auth(customer_id)
    app = common.get_flask_app()

    with app.app_context():
        common.check_context_graph(customer_id)
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


@mcp.tool
def get_graph_summary(customer_id: int, account_id: int) -> dict:
    """Get context graph summary: node/edge counts and revenue breakdown.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
    """
    common.check_mcp_enabled()
    common.require_account_auth(customer_id, account_id)
    app = common.get_flask_app()

    with app.app_context():
        common.check_context_graph(customer_id)
        from utils.context_graph import get_account_graph_summary

        common.validate_account_ownership(customer_id, account_id)
        result = get_account_graph_summary(account_id)
        result["scope"] = "account"
        return result


# ===================================================================
# Financial / ROI (1 tool)
# ===================================================================

@mcp.tool
def get_outcome_roi_story(
    customer_id: int,
    account_id: int,
    target_improvement_pct: float = 10.0,
    projection_months: int = 12,
) -> dict:
    """Generate a full ROI narrative with proof points, projections, and context graph insights.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to analyze
        target_improvement_pct: Target improvement percentage (default 10%)
        projection_months: Projection horizon in months (default 12)
    """
    common.check_mcp_enabled()
    common.require_account_auth(customer_id, account_id)
    app = common.get_flask_app()

    with app.app_context():
        from outcome_roi_engine import calculate_outcome_story
        from power_of_1_model import POWER_OF_1_METRICS

        account = common.validate_account_ownership(customer_id, account_id)

        arr = common.get_account_arr(account)

        # Build metric_actuals in the format expected by calculate_outcome_story:
        # {metric_id: {"current": float, "baseline": float}}
        # Use baselines as defaults (the engine computes delta from there)
        metric_actuals = {}
        for mid, m in POWER_OF_1_METRICS.items():
            metric_actuals[mid] = {"current": m.baseline, "baseline": m.baseline}

        # Determine vertical from account
        acct_vertical = getattr(account, 'vertical', None)

        story = calculate_outcome_story(
            metric_actuals=metric_actuals,
            target_improvement_pct=target_improvement_pct,
            account_arr=arr,
            projection_months=projection_months,
            customer_id=customer_id,
            account_ids=[account_id],
            vertical=acct_vertical,
        )

        story["scope"] = "account"
        return story


# ===================================================================
# Portfolio ROI (1 tool)
# ===================================================================

@mcp.tool
def get_portfolio_roi_summary(customer_id: int) -> dict:
    """Get the complete ROI story for a customer portfolio — historical proof (what we delivered) + forward projection (what we will deliver) + bridging narrative + trajectory assessment. Covers all accounts.

    Args:
        customer_id: The customer (tenant) ID
    """
    common.check_mcp_enabled()
    common.require_auth(customer_id)
    app = common.get_flask_app()

    with app.app_context():
        from models import Account
        from outcome_roi_engine import calculate_outcome_story
        from outcome_roi_api import _extract_historical_actuals, _extract_accounts_at_risk

        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        if not accounts:
            raise ToolError(f"No accounts found for customer {customer_id}")

        total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None
        account_ids = [a.account_id for a in accounts]

        # Extract historical metric actuals from DB
        metric_actuals, data_source = _extract_historical_actuals(accounts, 6)

        # Identify at-risk accounts per Power of 1 metric
        accounts_at_risk = _extract_accounts_at_risk(accounts, customer_id=customer_id)

        # Determine vertical from first account (portfolio is single-vertical)
        portfolio_vertical = getattr(accounts[0], 'vertical', None) if accounts else None

        story = calculate_outcome_story(
            metric_actuals=metric_actuals,
            target_improvement_pct=4.0,
            account_arr=total_arr,
            projection_months=6,
            accounts_at_risk=accounts_at_risk,
            customer_id=customer_id,
            account_ids=account_ids,
            vertical=portfolio_vertical,
        )

        return {
            "scope": "portfolio",
            "customer_id": customer_id,
            "total_arr": total_arr,
            "arr_basis": "portfolio_total",
            "arr_basis_value": total_arr,
            "account_count": len(accounts),
            "data_source": data_source,
            "story": story,
        }


# ===================================================================
# Portfolio / CEO View (2 tools)
# ===================================================================

@mcp.tool
def list_portfolio_customers(portfolio_id: int) -> dict:
    """List all customers in a PE portfolio with health and ARR summary.

    NOTE: This tool uses portfolio_id (not customer_id). A portfolio is a PE fund or
    holding company that owns multiple customers. Each customer has its own accounts.

    Args:
        portfolio_id: The portfolio (PE fund / holding company) ID
    """
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        from models import Portfolio, PortfolioMembership, Customer, Account
        import utils.health_thresholds as ht

        portfolio = Portfolio.query.filter_by(
            portfolio_id=portfolio_id, enabled=True,
        ).first()
        if not portfolio:
            raise ToolError(f"Portfolio {portfolio_id} not found or disabled")

        memberships = PortfolioMembership.query.filter_by(
            portfolio_id=portfolio_id,
        ).all()

        if not memberships:
            return {
                "scope": "portfolio",
                "portfolio_id": portfolio_id,
                "portfolio_name": portfolio.portfolio_name,
                "customers": [],
                "summary": {"total_customers": 0, "total_arr": 0, "avg_health": 0},
            }

        customer_summaries = []
        for mem in memberships:
            customer = Customer.query.filter_by(
                customer_id=mem.customer_id,
            ).first()
            if not customer:
                continue

            mem_vertical = getattr(customer, 'vertical', None) or mem.vertical or 'dc2_s'
            calc_health, get_trailing, get_precalc = common.get_health_functions(mem_vertical)

            accounts = Account.query.filter(
                Account.customer_id == mem.customer_id,
            ).all()

            total_arr = sum(common.get_account_arr(a) for a in accounts)
            health_scores = []
            at_risk_count = 0

            for acct in accounts:
                ph, ps, _ = get_precalc(acct.account_id)
                if ph is not None:
                    health_scores.append(ph)
                    if ps in ('at_risk', 'critical'):
                        at_risk_count += 1
                else:
                    kv = get_trailing(acct.account_id)
                    h, _ = calc_health(kv, mem.customer_id)
                    health_scores.append(h)
                    if ht.classify(h) in ('at_risk', 'critical'):
                        at_risk_count += 1

            avg_health = round(
                sum(health_scores) / len(health_scores), 1
            ) if health_scores else 0

            customer_summaries.append({
                "customer_id": mem.customer_id,
                "customer_name": getattr(customer, 'customer_name', None) or getattr(customer, 'company_name', 'Unknown'),
                "vertical": mem_vertical,
                "status": mem.status,
                "total_accounts": len(accounts),
                "total_arr": round(total_arr, 2),
                "avg_health_score": avg_health,
                "at_risk_accounts": at_risk_count,
                "synergies_realized": mem.synergies_realized,
                "synergy_value": float(mem.synergy_value or 0),
            })

        customer_summaries.sort(key=lambda x: x["avg_health_score"])

        total_arr = sum(c["total_arr"] for c in customer_summaries)
        total_accounts = sum(c["total_accounts"] for c in customer_summaries)
        avg_health = round(
            sum(c["avg_health_score"] * c["total_accounts"] for c in customer_summaries)
            / total_accounts, 1
        ) if total_accounts else 0

        return {
            "scope": "portfolio",
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "total_aum": float(portfolio.total_aum) if portfolio.total_aum else None,
            "customers": customer_summaries,
            "summary": {
                "total_customers": len(customer_summaries),
                "total_accounts": total_accounts,
                "total_arr": round(total_arr, 2),
                "avg_health_score": avg_health,
                "total_at_risk": sum(c["at_risk_accounts"] for c in customer_summaries),
            },
        }


@mcp.tool
def get_portfolio_cross_customer_comparison(portfolio_id: int) -> dict:
    """Compare all customers in a portfolio side-by-side: health, ARR, risk, expansion. CEO-level view.

    NOTE: Uses portfolio_id (not customer_id). Includes context graph revenue intelligence
    when enabled. Use for board-level cross-company benchmarking.

    Args:
        portfolio_id: The portfolio (PE fund / holding company) ID
    """
    common.check_mcp_enabled()
    app = common.get_flask_app()

    with app.app_context():
        from models import Portfolio, PortfolioMembership, Customer, Account
        import utils.health_thresholds as ht

        portfolio = Portfolio.query.filter_by(
            portfolio_id=portfolio_id, enabled=True,
        ).first()
        if not portfolio:
            raise ToolError(f"Portfolio {portfolio_id} not found or disabled")

        memberships = PortfolioMembership.query.filter_by(
            portfolio_id=portfolio_id,
        ).all()

        comparisons = []
        for mem in memberships:
            customer = Customer.query.filter_by(
                customer_id=mem.customer_id,
            ).first()
            if not customer:
                continue

            mem_vertical = getattr(customer, 'vertical', None) or mem.vertical or 'dc2_s'
            calc_health, get_trailing, get_precalc = common.get_health_functions(mem_vertical)

            accounts = Account.query.filter(
                Account.customer_id == mem.customer_id,
            ).all()

            total_arr = sum(common.get_account_arr(a) for a in accounts)
            pillar_totals = {}
            health_scores = []
            statuses = {'healthy': 0, 'at_risk': 0, 'critical': 0}

            for acct in accounts:
                ph, ps, pp = get_precalc(acct.account_id)
                if ph is not None:
                    health_scores.append(ph)
                    statuses[ps] = statuses.get(ps, 0) + 1
                    if pp:
                        for k, v in pp.items():
                            pillar_totals.setdefault(k, []).append(v)
                else:
                    kv = get_trailing(acct.account_id)
                    h, pillars = calc_health(kv, mem.customer_id)
                    health_scores.append(h)
                    cls = ht.classify(h)
                    statuses[cls] = statuses.get(cls, 0) + 1
                    for k, v in pillars.items():
                        pillar_totals.setdefault(k, []).append(v)

            avg_health = round(
                sum(health_scores) / len(health_scores), 1
            ) if health_scores else 0

            avg_pillars = {
                k: round(sum(v) / len(v), 1) for k, v in pillar_totals.items()
            } if pillar_totals else {}

            weakest_pillar = min(avg_pillars, key=avg_pillars.get) if avg_pillars else None

            # Context graph revenue (if enabled)
            revenue_data = None
            try:
                from feature_toggles import is_context_graph_enabled
                if is_context_graph_enabled(mem.customer_id):
                    from utils.context_graph import get_revenue_at_risk as _gar
                    total_rev = {'at_risk': 0, 'protected': 0, 'expansion': 0, 'net_impact': 0}
                    for acct in accounts:
                        rev = _gar(acct.account_id)
                        if rev.get('node_count', 0) > 0:
                            for k in total_rev:
                                total_rev[k] += rev.get(k, 0)
                    revenue_data = {k: round(v, 2) for k, v in total_rev.items()}
            except Exception:
                pass

            comparisons.append({
                "customer_id": mem.customer_id,
                "customer_name": getattr(customer, 'customer_name', None) or getattr(customer, 'company_name', 'Unknown'),
                "total_arr": round(total_arr, 2),
                "avg_health_score": avg_health,
                "account_distribution": statuses,
                "total_accounts": len(accounts),
                "avg_pillar_scores": avg_pillars,
                "weakest_pillar": weakest_pillar,
                "revenue_intelligence": revenue_data,
            })

        comparisons.sort(key=lambda x: x["avg_health_score"])

        return {
            "scope": "portfolio",
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "comparisons": comparisons,
        }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    common.run_server(mcp, default_port=8002)
