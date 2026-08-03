#!/usr/bin/env python3
"""
CS Pulse MCP — Executive persona dashboard summaries.

Thin wrappers over /api/executive/cro-dashboard, cfo-dashboard, ceo-dashboard
so external MCP agents get the same pre-aggregated tiles as the UI.
"""

from typing import Optional

from cs_pulse_mcp_server import (
    mcp,
    _check_mcp_enabled,
    _require_auth,
    _get_flask_app,
    ToolError,
)


@mcp.tool
def get_cro_dashboard_summary(customer_id: int, period: str = None) -> dict:
    """CRO executive dashboard summary (same data as GET /api/executive/cro-dashboard).

    Returns revenue at risk/protected/expansion, NRR projection lenses (Wizard B +
    Predictor v3), story arcs, early warning days, highest-risk accounts, and
    playbook ROI proof data.

    Args:
        customer_id: Tenant ID
        period: Optional tab echo — Q3, Q4, or TTM (UI filters client-side; echoed in response)
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()
    with app.app_context():
        from utils.executive_dashboard_mcp import fetch_executive_dashboard
        result = fetch_executive_dashboard(customer_id, 'cro', period=period)
        if result.get('error'):
            raise ToolError(result['error'])
        return result


@mcp.tool
def get_cfo_dashboard_summary(customer_id: int) -> dict:
    """CFO executive dashboard summary (same data as GET /api/executive/cfo-dashboard).

    Returns CS investment, ROI snapshot, Power-of-1 metrics, scaling projections,
    pillar investment breakdown, and Predictor v3 portfolio NRR when available.
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()
    with app.app_context():
        from utils.executive_dashboard_mcp import fetch_executive_dashboard
        result = fetch_executive_dashboard(customer_id, 'cfo')
        if result.get('error'):
            raise ToolError(result['error'])
        return result


@mcp.tool
def get_ceo_dashboard_summary(customer_id: int) -> dict:
    """CEO executive dashboard summary (same data as GET /api/executive/ceo-dashboard).

    Returns portfolio-of-one company summary (or portfolio_id when the tenant
    belongs to a PE portfolio), cross-account health/NRR/ROI, and top at-risk accounts.
    """
    _check_mcp_enabled()
    _require_auth(customer_id)
    app = _get_flask_app()
    with app.app_context():
        from utils.executive_dashboard_mcp import fetch_executive_dashboard
        result = fetch_executive_dashboard(customer_id, 'ceo')
        if result.get('error'):
            raise ToolError(result['error'])
        return result
