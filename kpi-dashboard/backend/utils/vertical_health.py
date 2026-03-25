"""
Vertical-Aware Health Calculator Resolver
==========================================
Single source of truth for getting the correct calculate_kpi_health()
function based on a customer's vertical.

Resolution priority:
1. Vertical-specific Python module (verticals/{v}/api_routes.py) — if it exists
2. Generic JSON-based scorer (utils/generic_scorer.py) — for any vertical with a catalog

Design principle: DC2_S is not special. If verticals/dc2_s/ is deleted,
the generic scorer handles DC2_S via its JSON catalog.

Usage:
    from utils.vertical_health import get_health_calculator

    calculate_kpi_health = get_health_calculator(customer_id)
    overall_health, pillar_averages = calculate_kpi_health(kpi_values, customer_id)
"""

import logging

logger = logging.getLogger(__name__)

# Cache: customer_id -> vertical string
_vertical_cache = {}


def resolve_vertical(customer_id: int) -> str:
    """Resolve the vertical for a customer."""
    if customer_id is None:
        return 'dc2_s'  # Legacy default — will be removed

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
    from utils.vertical_registry import normalize_vertical
    vertical = normalize_vertical(vertical)

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

    Resolution:
    1. Try vertical-specific Python module (verticals/{v}/api_routes.py)
    2. Fall back to generic JSON-based scorer (works for ANY vertical with a catalog)

    Returns:
        callable: calculate_kpi_health(kpi_values, customer_id=None) -> (float, dict)
    """
    vertical = resolve_vertical(customer_id)

    # Try vertical-specific Python module first (legacy — DC2_S, SaaS Premium)
    calc = _try_python_module_calculator(vertical, customer_id)
    if calc:
        return calc

    # Fall back to generic JSON-based scorer
    return _make_generic_calculator(vertical, customer_id)


def _try_python_module_calculator(vertical: str, customer_id: int = None):
    """Try to load calculate_kpi_health from a vertical's Python module."""
    try:
        if vertical == 'dc2_s':
            from verticals.dc2_s.api_routes import calculate_kpi_health
            return calculate_kpi_health
        elif vertical == 'saas_premium':
            # SaaS Premium Python scorer is a stub (returns 50 for all KPIs).
            # Skip it — generic JSON-catalog scorer handles SaaS Premium correctly.
            return None
        else:
            # Try dynamic import
            import importlib
            mod = importlib.import_module(f'verticals.{vertical}.api_routes')
            return getattr(mod, 'calculate_kpi_health', None)
    except (ImportError, ModuleNotFoundError):
        return None
    except Exception as e:
        logger.debug(f"Python module calc not available for {vertical}: {e}")
        return None


def _make_generic_calculator(vertical: str, customer_id: int = None):
    """
    Create a calculate_kpi_health function using the generic scorer + JSON catalog.
    This works for ANY vertical that has a catalog — no Python module needed.
    """
    from utils.vertical_registry import get_kpis, get_pillars
    from utils.generic_scorer import score_account_health

    # Pre-load catalogs (cached by registry)
    try:
        kpi_catalog = get_kpis(vertical)
        pillar_catalog = get_pillars(vertical)
    except ValueError:
        logger.error(f"No catalog found for vertical '{vertical}' — cannot create scorer")
        raise

    logger.info(f"Using generic scorer for vertical '{vertical}' ({len(kpi_catalog)} KPIs)")

    def calculate_kpi_health(kpi_values, customer_id=None, vertical=None):
        """Generic health calculator using JSON catalog."""
        # Get weight overrides from CustomerConfig if available
        pillar_weight_overrides = None
        enabled_pillars = None
        if customer_id is not None:
            try:
                from models import CustomerConfig as CC
                cc = CC.query.filter_by(customer_id=int(customer_id)).first()
                if cc and cc.dc2s_pillar_weights:
                    pillar_weight_overrides = cc.dc2s_pillar_weights
                    enabled_pillars = set(cc.dc2s_pillar_weights.keys())
            except Exception:
                pass

        return score_account_health(
            kpi_values=kpi_values,
            kpi_catalog=kpi_catalog,
            pillar_catalog=pillar_catalog,
            pillar_weight_overrides=pillar_weight_overrides,
            enabled_pillars=enabled_pillars,
        )

    return calculate_kpi_health


def get_trailing_kpi_values_func(customer_id: int = None):
    """Return the correct _get_trailing_kpi_values function for a customer's vertical."""
    vertical = resolve_vertical(customer_id)

    # Try vertical-specific Python module
    try:
        if vertical == 'dc2_s':
            from verticals.dc2_s.api_routes import _get_trailing_kpi_values
            return _get_trailing_kpi_values
        elif vertical == 'saas_premium':
            from verticals.saas_premium.api_routes import _get_trailing_kpi_values
            return _get_trailing_kpi_values
    except (ImportError, ModuleNotFoundError):
        pass

    # Generic fallback: query DC2SKPI table (works for any vertical)
    def _generic_trailing_kpi_values(account_id, days=30):
        """Generic trailing KPI values — queries DC2SKPI table for any vertical."""
        from models import DC2SKPI, db
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = DC2SKPI.query.filter(
            DC2SKPI.account_id == account_id,
            DC2SKPI.measured_at >= cutoff,
        ).all()
        # Average by KPI code
        kpi_sums = {}
        kpi_counts = {}
        for r in rows:
            code = r.kpi_code
            kpi_sums[code] = kpi_sums.get(code, 0) + float(r.value)
            kpi_counts[code] = kpi_counts.get(code, 0) + 1
        return {code: kpi_sums[code] / kpi_counts[code] for code in kpi_sums}

    return _generic_trailing_kpi_values


def calculate_health_for_customer(kpi_values: dict, customer_id: int = None):
    """One-call convenience: resolve vertical + calculate health."""
    calc = get_health_calculator(customer_id)
    return calc(kpi_values, customer_id=customer_id)
