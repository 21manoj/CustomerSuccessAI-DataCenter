#!/usr/bin/env python3
"""
Ask AI Helper Functions — extracted from cs_pulse_mcp_server.py

These are the shared helper functions used by both:
1. @mcp.tool decorated functions (via cs_pulse_mcp_server.py import)
2. _execute_direct in ask_ai_tools.py (no fastmcp needed)

This module has ZERO dependency on fastmcp. It can run on Python 3.9+.
"""


def _resolve_customer_vertical(customer_id: int) -> str:
    """Look up the vertical for a customer. Falls back to 'dc2_s'."""
    from models import Customer
    customer = Customer.query.get(int(customer_id))
    if not customer:
        raise ValueError(f"Customer {customer_id} not found")
    return getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'


def _get_precalculated_scores(account_id: int):
    """Read pre-calculated scores from HealthScore/PillarScore tables.
    Returns (health_score, health_status, pillar_dict) or (None, None, None).
    """
    try:
        from models import HealthScore, PillarScore
        import utils.health_thresholds as ht

        hs = HealthScore.query.filter_by(account_id=account_id) \
            .order_by(HealthScore.measurement_month.desc()).first()
        if not hs or hs.health_score is None:
            return None, None, None

        health = float(hs.health_score)
        status = hs.health_status or ht.classify(health)

        pillars = {}
        if hs.contributing_pillars:
            pillars = {k: float(v) for k, v in hs.contributing_pillars.items()}
        else:
            ps_rows = PillarScore.query.filter_by(
                account_id=account_id,
                measurement_month=hs.measurement_month,
            ).all()
            for ps in ps_rows:
                if ps.pillar_score is not None:
                    pillars[ps.pillar_code] = float(ps.pillar_score)

        return health, status, pillars
    except Exception:
        return None, None, None


def _get_trailing_kpi_values_generic(account_id: int, days: int = 30) -> dict:
    """Read latest KPI values from DC2SKPI table.
    Returns dict of {kpi_code: value}.
    """
    try:
        from models import DC2SKPI
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = DC2SKPI.query.filter(
            DC2SKPI.account_id == account_id,
            DC2SKPI.measurement_date >= cutoff,
        ).order_by(DC2SKPI.measurement_date.desc()).all()
        seen = {}
        for r in rows:
            if r.kpi_code not in seen and r.kpi_value is not None:
                seen[r.kpi_code] = float(r.kpi_value)
        return seen
    except Exception:
        return {}


def _get_health_functions(vertical: str):
    """Return (calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores)."""
    # Try vertical-specific modules (legacy)
    if vertical in ('saas_premium', 'saas'):
        try:
            from verticals.saas_premium.api_routes import (
                calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores,
            )
            return calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores
        except ImportError:
            pass

    if vertical in ('dc2_s', 'dc2s', 'dc', 'datacenter'):
        try:
            from verticals.dc2_s.api_routes import (
                calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores,
            )
            return calculate_kpi_health, _get_trailing_kpi_values, get_precalculated_scores
        except ImportError:
            pass

    # Generic scorer
    try:
        from utils.generic_scorer import calculate_health_generic
        def _generic_calculate(kpi_values, customer_id=None):
            return calculate_health_generic(kpi_values, vertical)
        return _generic_calculate, _get_trailing_kpi_values_generic, _get_precalculated_scores
    except ImportError:
        pass

    # Last resort: noop
    def _noop(kpi_values, customer_id=None):
        return 0.0, {}
    return _noop, _get_trailing_kpi_values_generic, _get_precalculated_scores


def _get_kpi_definitions(vertical: str) -> dict:
    """Return the KPI definitions dict for a vertical."""
    if vertical in ('saas_premium', 'saas'):
        try:
            from verticals.saas_premium.kpi_definitions import SAAS_KPIS
            return SAAS_KPIS
        except ImportError:
            return {}
    try:
        from verticals.dc2_s.kpi_definitions import DC2S_KPIS
        return DC2S_KPIS
    except ImportError:
        return {}


def _get_playbook_config(vertical: str):
    """Return (PLAYBOOK_CONFIG, should_trigger_playbook) for a vertical."""
    if vertical in ('saas_premium', 'saas'):
        try:
            from verticals.saas_premium.vertical_config import PLAYBOOK_CONFIG, should_trigger_playbook
            return PLAYBOOK_CONFIG, should_trigger_playbook
        except ImportError:
            return {}, lambda *a, **kw: False
    try:
        from verticals.dc2_s.vertical_config import PLAYBOOK_CONFIG, should_trigger_playbook
        return PLAYBOOK_CONFIG, should_trigger_playbook
    except ImportError:
        return {}, lambda *a, **kw: False
