#!/usr/bin/env python3
"""
Catalog Loader — Reads DC2_S KPI definitions from the shared JSON catalog.

Single source of truth: dc2s_kpi_catalog.json (generated from kpi_definitions.py).
All load-driver modules should use this instead of hardcoded weights/targets/ranges.
"""
import json
import os

_CATALOG_PATH = os.path.join(os.path.dirname(__file__), 'dc2s_kpi_catalog.json')
_cached = None


def _load():
    global _cached
    if _cached is None:
        with open(_CATALOG_PATH, 'r') as f:
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
            'ranges': kpi.get('ranges', {}),
        })
    return result
