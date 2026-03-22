#!/usr/bin/env python3
"""
CS Pulse MCP — Revenue & Portfolio Tools.

7 tools moved from cs_pulse_mcp_server.py:
  - calculate_power_of_1
  - get_outcome_roi_story
  - get_playbook_economics
  - get_playbook_recommendations
  - get_portfolio_roi_summary
  - list_portfolio_customers
  - get_portfolio_cross_customer_comparison

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
    _resolve_customer_vertical,
    _get_health_functions,
    _ensure_registry,
    _backend_dir,
    ToolError,
)


# ===================================================================
# Tool: calculate_power_of_1
# ===================================================================

@mcp.tool
def calculate_power_of_1(
    customer_id: int,
    metric_id: str,
    improvement_pct: float = 1.0,
    account_arr: float = None,
) -> dict:
    """Calculate the revenue impact of a 1% improvement in a business metric (Power-of-1).

    Args:
        customer_id: The customer (tenant) ID
        metric_id: Metric to improve (e.g. NRR, GRR, product_adoption, expansion_rate, ticket_resolution_time, TTFV)
        improvement_pct: Percentage improvement (default 1.0 = 1%)
        account_arr: Optional account ARR override. If omitted, uses portfolio total.
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from power_of_1_model import calculate_power_of_1_impact

        if account_arr:
            scope = "account"
            arr_source = "explicit_account_arr"
            effective_arr = account_arr
        else:
            scope = "portfolio"
            arr_source = "portfolio_total"
            accounts = Account.query.filter(
                Account.customer_id == int(customer_id),
            ).all()
            effective_arr = sum(_get_account_arr(a) for a in accounts)
            if not effective_arr:
                effective_arr = None

        po1_vertical = _resolve_customer_vertical(customer_id)

        result = calculate_power_of_1_impact(
            metric_id=metric_id,
            improvement_pct=improvement_pct,
            account_arr=effective_arr,
            vertical=po1_vertical,
        )

        if "error" in result:
            raise ToolError(f"Power-of-1 calculation failed: {result['error']}")

        result["scope"] = scope
        result["arr_source"] = arr_source
        return result


# ===================================================================
# Tool: get_outcome_roi_story
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
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        from outcome_roi_engine import calculate_outcome_story
        from power_of_1_model import POWER_OF_1_METRICS

        account = _validate_account_ownership(customer_id, account_id)

        arr = _get_account_arr(account)

        metric_actuals = {}
        for mid, m in POWER_OF_1_METRICS.items():
            metric_actuals[mid] = {"current": m.baseline, "baseline": m.baseline}

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
# Tool: get_playbook_economics
# ===================================================================

@mcp.tool
def get_playbook_economics(
    customer_id: int,
    account_arr: float = None,
) -> dict:
    """Get playbook cost bridge economics — investment breakdown, hours, ROI per playbook.

    Returns per-metric and per-playbook economics derived from:
      - Power of 1 JSON benchmarks (source of truth for budgets)
      - PLAYBOOK_CONFIG hours (manual vs automated breakdown)
      - CSM hourly rate from resource_rates.json

    Use this to answer: "How much do playbooks cost?", "What's the CSM investment?",
    "Show me the investment breakdown", "What's the ROI per playbook run?"

    Args:
        customer_id: The customer (tenant) ID
        account_arr: Customer ARR for scaling (optional, defaults to sum of account revenues)
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from playbook_cost_bridge import calculate_cost_bridge, bridge_to_dict

        if account_arr:
            effective_arr = float(account_arr)
        else:
            accounts = Account.query.filter(
                Account.customer_id == int(customer_id),
            ).all()
            effective_arr = float(sum(_get_account_arr(a) for a in accounts)) if accounts else 10_000_000

        result = calculate_cost_bridge(account_arr=effective_arr)
        return bridge_to_dict(result)


# ===================================================================
# Tool: get_playbook_recommendations
# ===================================================================

@mcp.tool
def get_playbook_recommendations(
    customer_id: int,
    account_id: int,
) -> dict:
    """Get recommended playbooks for an account based on health score and signals.

    Args:
        customer_id: The customer (tenant) ID
        account_id: The account to get recommendations for
    """
    _check_mcp_enabled()
    _require_account_auth(customer_id, account_id)
    app = _get_flask_app()

    with app.app_context():
        _validate_account_ownership(customer_id, account_id)
        _ensure_registry()
        from agent_tool_registry import get_tool_registry

        vertical = _resolve_customer_vertical(customer_id)
        calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores = _get_health_functions(vertical)

        kpi_values = _get_trailing_kpi_values(account_id)

        precalc_health, _, _ = get_precalculated_scores(account_id)
        if precalc_health is not None:
            health = precalc_health
        else:
            health, _ = calculate_kpi_health(kpi_values, customer_id)

        registry = get_tool_registry()
        result = registry.invoke(
            "playbook_recommend",
            account_id=account_id,
            customer_id=customer_id,
            health_score=round(health, 1),
            kpi_values=kpi_values,
        )

        if not result.success:
            raise ToolError(f"Playbook recommendations failed: {result.error}")

        data = result.result
        data["scope"] = "account"
        return data


# ===================================================================
# Tool: get_portfolio_roi_summary
# ===================================================================

@mcp.tool
def get_portfolio_roi_summary(customer_id: int) -> dict:
    """Get the complete ROI story for a customer portfolio — historical proof (what we delivered) + forward projection (what we will deliver) + bridging narrative + trajectory assessment. Covers all accounts.

    Args:
        customer_id: The customer (tenant) ID
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()

    with app.app_context():
        from models import Account
        from outcome_roi_engine import calculate_outcome_story
        from outcome_roi_api import _extract_historical_actuals, _extract_accounts_at_risk

        accounts = Account.query.filter_by(customer_id=int(customer_id)).all()
        if not accounts:
            raise ToolError(f"No accounts found for customer {customer_id}")

        total_arr = sum(float(a.revenue) for a in accounts if a.revenue) or None
        account_ids = [a.account_id for a in accounts]

        metric_actuals, data_source = _extract_historical_actuals(accounts, 6)
        accounts_at_risk = _extract_accounts_at_risk(accounts, customer_id=customer_id)

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
# Tool: list_portfolio_customers
# ===================================================================

@mcp.tool
def list_portfolio_customers(portfolio_id: int) -> dict:
    """List all customers in a PE portfolio with health and ARR summary.

    NOTE: This tool uses portfolio_id (not customer_id). A portfolio is a PE fund or
    holding company that owns multiple customers. Each customer has its own accounts.

    Args:
        portfolio_id: The portfolio (PE fund / holding company) ID
    """
    _check_mcp_enabled()
    app = _get_flask_app()

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
            calc_health, get_trailing, get_precalc = _get_health_functions(mem_vertical)

            accounts = Account.query.filter(
                Account.customer_id == mem.customer_id,
            ).all()

            total_arr = sum(_get_account_arr(a) for a in accounts)
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
                "created_at": customer.created_at.isoformat() if customer.created_at else None,
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


# ===================================================================
# Tool: get_portfolio_cross_customer_comparison
# ===================================================================

@mcp.tool
def get_portfolio_cross_customer_comparison(portfolio_id: int) -> dict:
    """Compare all customers in a portfolio side-by-side: health, ARR, risk, expansion. CEO-level view.

    NOTE: Uses portfolio_id (not customer_id). Includes context graph revenue intelligence
    when enabled. Use for board-level cross-company benchmarking.

    Args:
        portfolio_id: The portfolio (PE fund / holding company) ID
    """
    _check_mcp_enabled()
    app = _get_flask_app()

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
            calc_health, get_trailing, get_precalc = _get_health_functions(mem_vertical)

            accounts = Account.query.filter(
                Account.customer_id == mem.customer_id,
            ).all()

            total_arr = sum(_get_account_arr(a) for a in accounts)
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
