"""
Vertical-Aware Health Calculator Resolver
==========================================
Single source of truth for getting the correct calculate_kpi_health()
function based on a customer's vertical.

Usage:
    from utils.vertical_health import get_health_calculator

    calculate_kpi_health = get_health_calculator(customer_id)
    overall_health, pillar_averages = calculate_kpi_health(kpi_values, customer_id)

This replaces all hardcoded `from verticals.dc2_s.api_routes import calculate_kpi_health`.
"""

import logging

logger = logging.getLogger(__name__)

# Cache: customer_id -> vertical string
_vertical_cache = {}


def resolve_vertical(customer_id: int) -> str:
    """Resolve the vertical for a customer. Returns 'dc2_s' as default."""
    if customer_id is None:
        return 'dc2_s'

    cid = int(customer_id)
    if cid in _vertical_cache:
        return _vertical_cache[cid]

    vertical = 'dc2_s'
    try:
        from models import CustomerConfig
        cc = CustomerConfig.query.filter_by(customer_id=cid).first()
        if cc and cc.vertical:
            vertical = cc.vertical
        else:
            # Check directory-based detection
            import os
            base = os.path.join(os.path.dirname(__file__), '..', 'verticals')
            for suffix in ('saas', 'saas_premium'):
                if os.path.isdir(os.path.join(base, f'customer{cid}-{suffix}')):
                    vertical = 'saas_premium'
                    break
    except Exception as e:
        logger.debug(f"Could not resolve vertical for customer {cid}: {e}")

    # Normalize aliases
    if vertical in ('saas', 'saas_premium'):
        vertical = 'saas_premium'

    _vertical_cache[cid] = vertical
    return vertical


def clear_vertical_cache(customer_id: int = None):
    """Clear the vertical cache. Call when customer config changes."""
    if customer_id:
        _vertical_cache.pop(int(customer_id), None)
    else:
        _vertical_cache.clear()


def get_health_calculator(customer_id: int = None):
    """
    Return the correct calculate_kpi_health function for a customer's vertical.

    Returns:
        callable: calculate_kpi_health(kpi_values, customer_id=None) -> (float, dict)
    """
    vertical = resolve_vertical(customer_id)

    if vertical == 'saas_premium':
        try:
            from verticals.saas_premium.api_routes import calculate_kpi_health
            return calculate_kpi_health
        except ImportError:
            logger.warning(f"SaaS Premium module not available for customer {customer_id}, falling back to DC2_S")

    from verticals.dc2_s.api_routes import calculate_kpi_health
    return calculate_kpi_health


def get_trailing_kpi_values_func(customer_id: int = None):
    """Return the correct _get_trailing_kpi_values function for a customer's vertical."""
    vertical = resolve_vertical(customer_id)

    if vertical == 'saas_premium':
        try:
            from verticals.saas_premium.api_routes import _get_trailing_kpi_values
            return _get_trailing_kpi_values
        except ImportError:
            pass

    from verticals.dc2_s.api_routes import _get_trailing_kpi_values
    return _get_trailing_kpi_values


def calculate_health_for_customer(kpi_values: dict, customer_id: int = None):
    """
    Convenience: resolve vertical + calculate in one call.

    Returns:
        tuple: (overall_health: float, pillar_averages: dict)
    """
    calc = get_health_calculator(customer_id)
    return calc(kpi_values, customer_id)
