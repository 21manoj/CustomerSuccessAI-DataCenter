#!/usr/bin/env python3
"""
Vertical Registry — single dispatch point for vertical-specific KPI definitions.

Usage:
    from utils.vertical_registry import get_pillars, get_kpis, get_vertical_for_customer

    pillars = get_pillars('saas_premium')   # → SAAS_PILLARS
    kpis = get_kpis('dc2_s')               # → DC2S_KPIS
    vertical = get_vertical_for_customer(444)  # → 'dc2_s'
"""

import logging
from typing import Dict, Any, Optional, Tuple

log = logging.getLogger(__name__)

# Lazy-loaded caches
_pillars_cache: Dict[str, Dict] = {}
_kpis_cache: Dict[str, Dict] = {}

# Vertical aliases (normalize before lookup)
VERTICAL_ALIASES = {
    'dc2_s': 'dc2_s',
    'dc2s': 'dc2_s',
    'datacenter': 'dc2_s',
    'saas': 'saas_premium',
    'saas_premium': 'saas_premium',
}

SUPPORTED_VERTICALS = {'dc2_s', 'saas_premium'}


def normalize_vertical(vertical: str) -> str:
    """Normalize vertical name to canonical form."""
    return VERTICAL_ALIASES.get(vertical, vertical)


def get_pillars(vertical: str) -> Dict[str, Dict[str, Any]]:
    """Get pillar definitions for a vertical."""
    vertical = normalize_vertical(vertical)

    if vertical not in _pillars_cache:
        _pillars_cache[vertical] = _load_pillars(vertical)

    return _pillars_cache[vertical]


def get_kpis(vertical: str) -> Dict[str, Dict[str, Any]]:
    """Get KPI definitions for a vertical."""
    vertical = normalize_vertical(vertical)

    if vertical not in _kpis_cache:
        _kpis_cache[vertical] = _load_kpis(vertical)

    return _kpis_cache[vertical]


def get_default_pillar_weights(vertical: str) -> Dict[str, float]:
    """Get default L2 pillar weights for a vertical."""
    pillars = get_pillars(vertical)
    return {pid: info.get('weight_l2', 0.20) for pid, info in pillars.items()}


def get_vertical_for_customer(customer_id: int) -> str:
    """Look up vertical from CustomerConfig DB."""
    try:
        from models import CustomerConfig
        config = CustomerConfig.query.filter_by(customer_id=customer_id).first()
        if config and config.vertical:
            return normalize_vertical(config.vertical)
    except Exception as e:
        log.debug("vertical_registry: could not load CustomerConfig for %s: %s", customer_id, e)

    return 'dc2_s'  # fallback


def get_catalog_for_customer(customer_id: int) -> Tuple[Dict, Dict]:
    """Return (pillars, kpis) for a customer's vertical. Convenience wrapper."""
    vertical = get_vertical_for_customer(customer_id)
    return get_pillars(vertical), get_kpis(vertical)


# ----------------------------------------------------------------
# Internal loaders
# ----------------------------------------------------------------

def _load_pillars(vertical: str) -> Dict:
    if vertical == 'dc2_s':
        from verticals.dc2_s.kpi_definitions import DC2S_PILLARS
        return DC2S_PILLARS
    elif vertical == 'saas_premium':
        from verticals.saas_premium.kpi_definitions import SAAS_PILLARS
        return SAAS_PILLARS
    else:
        raise ValueError(f"Unknown vertical: {vertical}")


def _load_kpis(vertical: str) -> Dict:
    if vertical == 'dc2_s':
        from verticals.dc2_s.kpi_definitions import DC2S_KPIS
        return DC2S_KPIS
    elif vertical == 'saas_premium':
        from verticals.saas_premium.kpi_definitions import SAAS_KPIS
        return SAAS_KPIS
    else:
        raise ValueError(f"Unknown vertical: {vertical}")
