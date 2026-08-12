#!/usr/bin/env python3
"""
Catalog Loader — Reads KPI definitions from the shared JSON catalog.

Vertical-aware: loads the correct catalog based on set_vertical().
- dc2_s / dc / datacenter → dc2s_kpi_catalog.json
- saas / saas_premium → saas_premium_kpi_catalog.json
- Any other → looks for {vertical}_kpi_catalog.json

All load-driver modules should use this instead of hardcoded weights/targets/ranges.
"""
import json
import os
import logging

_logger = logging.getLogger(__name__)
_DIR = os.path.dirname(__file__)
# Canonical catalogs live in the backend config dir; load-driver keeps local copies
# for the legacy verticals. Search both so a NEW vertical only needs its backend
# catalog (no duplicate copy in load-driver/).
_BACKEND_CONFIG_DIR = os.path.abspath(os.path.join(_DIR, '..', 'kpi-dashboard', 'backend', 'config'))
_cached = None
_active_vertical = 'dc2_s'

# Vertical → catalog filename mapping
_CATALOG_FILES = {
    'dc2_s': 'dc2s_kpi_catalog.json',
    'dc': 'dc2s_kpi_catalog.json',
    'dc2s': 'dc2s_kpi_catalog.json',
    'datacenter': 'dc2s_kpi_catalog.json',
    'datacenter_v1': 'datacenter_v1_kpi_catalog.json',
    'saas': 'saas_premium_kpi_catalog.json',
    'saas_premium': 'saas_premium_kpi_catalog.json',
}


def set_vertical(vertical: str):
    """Set the active vertical for catalog loading. Call before get_kpis()."""
    global _active_vertical, _cached
    resolved = vertical.lower().strip() if vertical else 'dc2_s'
    if resolved != _active_vertical:
        _active_vertical = resolved
        _cached = None  # Force reload
        _logger.info(f"catalog_loader: vertical set to '{resolved}'")


def _get_catalog_path() -> str:
    """Resolve catalog JSON path for the active vertical."""
    filename = _CATALOG_FILES.get(_active_vertical)
    if not filename:
        # Try generic pattern: {vertical}_kpi_catalog.json
        filename = f"{_active_vertical}_kpi_catalog.json"

    # Prefer the load-driver copy (legacy verticals), then the canonical backend config.
    for base in (_DIR, _BACKEND_CONFIG_DIR):
        candidate = os.path.join(base, filename)
        if os.path.exists(candidate):
            return candidate
    _logger.warning(f"catalog_loader: {filename} not found in load-driver or backend config, falling back to dc2s_kpi_catalog.json")
    return os.path.join(_DIR, 'dc2s_kpi_catalog.json')


def _load():
    global _cached
    if _cached is None:
        catalog_path = _get_catalog_path()
        _logger.info(f"catalog_loader: loading {os.path.basename(catalog_path)} for vertical '{_active_vertical}'")
        with open(catalog_path, 'r') as f:
            content = f.read()
        # Handle preamble text before JSON (e.g. stdout from kpi_definitions.py)
        brace_pos = content.find('{')
        if brace_pos > 0:
            content = content[brace_pos:]
        _cached = json.loads(content)
    return _cached


def get_pillars() -> dict:
    """Return pillar definitions: {P1: {name, weight_l2, kpi_count}, ...}"""
    return _load()['pillars']


def get_kpis() -> dict:
    """Return full KPI catalog: {P1-KPI1: {name, pillar, weight_l1, unit, ...}, ...}"""
    return _load()['kpis']


def get_pillar_code_map() -> dict:
    """Return pillar code map from catalog (kept for backward compat)."""
    return _load().get('pillar_code_map', {})


def get_pillar_weight(pillar_code: str) -> float:
    """Get L2 weight for a pillar (P1..P5 format)."""
    return get_pillars().get(pillar_code, {}).get('weight_l2', 0.20)


def get_kpi_weight(kpi_code: str) -> float:
    """Get L1 weight for a KPI code (P1-KPI1 format)."""
    catalog = get_kpis()
    if kpi_code in catalog:
        return catalog[kpi_code].get('weight_l1', 0)
    return 0.0


def get_kpi_target(kpi_code: str) -> float:
    """Get target value for a KPI code."""
    catalog = get_kpis()
    if kpi_code in catalog:
        target = catalog[kpi_code].get('target')
        if isinstance(target, dict):
            return target.get('value', 85.0)
        return target if target else 85.0
    return 85.0


def get_kpi_list_for_load_driver() -> list:
    """
    Return simplified KPI list in P-format for csv_generator.
    """
    catalog = get_kpis()

    result = []
    for kpi_code, kpi in catalog.items():
        result.append({
            'code': kpi_code,
            'name': kpi['name'],
            'pillar': kpi['pillar'],
            'weight': kpi.get('weight_l1', 0),
            'unit': kpi.get('unit', ''),
            'target': kpi.get('target') if not isinstance(kpi.get('target'), dict) else kpi['target'].get('value', 85),
            'higher_is_better': kpi.get('higher_is_better', True),
            'frequency': kpi.get('frequency', 'monthly'),
            'ranges': kpi.get('ranges', {}),
        })
    return result


# ── Frequency constants (mirror kpi_definitions.py) ──
FREQ_DAYS = {
    'realtime': 1,    # streamed as daily aggregates
    'daily': 1,
    'weekly': 7,
    'monthly': 30,
    'quarterly': 90,
}


def get_kpi_frequency(kpi_code: str) -> str:
    """Get frequency for a KPI code."""
    catalog = get_kpis()
    if kpi_code in catalog:
        return catalog[kpi_code].get('frequency', 'monthly')
    return 'monthly'


def get_kpis_by_frequency() -> dict:
    """Group KPIs by frequency: {daily: [kpi_list], weekly: [...], ...}"""
    catalog = get_kpis()
    by_freq = {}
    for kpi_code, kpi in catalog.items():
        freq = kpi.get('frequency', 'monthly')
        by_freq.setdefault(freq, []).append(kpi_code)
    return by_freq
