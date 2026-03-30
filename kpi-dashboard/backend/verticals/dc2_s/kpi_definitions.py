#!/usr/bin/env python3
"""
DC2_S Vertical - KPI Definitions
Data Center Hardware Infrastructure

Source of truth: config/dc2s_kpi_catalog.json (v3.0)
This module loads from JSON and exposes the same API as the legacy Python dicts.

38 KPIs across 5 pillars:
- P1: Deployment Velocity (15%)
- P2: Operational Stability (20%)
- P3: AI Workload Performance (25%)
- P4: Channel & Partner Health (15%)
- P5: Expansion Readiness (25%)
"""

import json
import os
from typing import Dict, Any, Optional

# ============================================================
# LOAD FROM JSON CATALOG (single source of truth)
# ============================================================

_CATALOG_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'config', 'dc2s_kpi_catalog.json'
)

with open(_CATALOG_PATH) as _f:
    _CATALOG = json.load(_f)

DC2S_PILLARS: Dict[str, Dict[str, Any]] = _CATALOG['pillars']
DC2S_KPIS: Dict[str, Dict[str, Any]] = _CATALOG['kpis']

DC2S_METADATA: Dict[str, Any] = {
    "vertical_name": "dc2_S",
    "vertical_full_name": "Data Center Hardware Infrastructure",
    "version": _CATALOG.get('version', '3.0'),
    "description": _CATALOG.get('description', ''),
    "total_kpis": len(DC2S_KPIS),
    "pillar_count": len(DC2S_PILLARS),
    **_CATALOG.get('metadata', {}),
}

# ============================================================
# MEASUREMENT FREQUENCY CONSTANTS
# ============================================================

FREQ_REALTIME = "realtime"
FREQ_DAILY = "daily"
FREQ_WEEKLY = "weekly"
FREQ_MONTHLY = "monthly"
FREQ_QUARTERLY = "quarterly"

FREQ_DATA_POINTS = {
    FREQ_REALTIME: 30,
    FREQ_DAILY: 30,
    FREQ_WEEKLY: 4,
    FREQ_MONTHLY: 1,
    FREQ_QUARTERLY: 0,
}

VALID_FREQUENCIES = {FREQ_REALTIME, FREQ_DAILY, FREQ_WEEKLY, FREQ_MONTHLY, FREQ_QUARTERLY}

# ============================================================
# HELPER FUNCTIONS
# ============================================================


def get_kpi_by_code(kpi_code: str) -> Optional[Dict[str, Any]]:
    """Get KPI definition by code (e.g., 'P1-KPI1')"""
    return DC2S_KPIS.get(kpi_code)


def get_kpis_by_pillar(pillar: str) -> Dict[str, Dict[str, Any]]:
    """Get all KPIs for a specific pillar"""
    return {k: v for k, v in DC2S_KPIS.items() if v.get('pillar') == pillar}


def get_pillar_info(pillar: str) -> Optional[Dict[str, Any]]:
    """Get pillar definition"""
    return DC2S_PILLARS.get(pillar)


def get_kpi_frequency(kpi_code: str) -> str:
    """Get measurement frequency for a KPI (defaults to 'monthly')."""
    kpi = DC2S_KPIS.get(kpi_code)
    return kpi.get('frequency', 'monthly') if kpi else 'monthly'


def get_kpis_by_frequency(frequency: str) -> Dict[str, Dict[str, Any]]:
    """Get all KPIs with a given measurement frequency."""
    return {k: v for k, v in DC2S_KPIS.items() if v.get('frequency') == frequency}


def get_frequency_summary() -> Dict[str, int]:
    """Return count of KPIs per measurement frequency."""
    summary: Dict[str, int] = {}
    for kpi in DC2S_KPIS.values():
        freq = kpi.get('frequency', 'monthly')
        summary[freq] = summary.get(freq, 0) + 1
    return summary


def get_trailing_window_days(frequency: str) -> int:
    """Suggested trailing-average window size for a given frequency."""
    windows = {
        'realtime': 7,
        'daily': 30,
        'weekly': 56,
        'monthly': 90,
        'quarterly': 365,
    }
    return windows.get(frequency, 30)


def get_health_status(kpi_code: str, value: float) -> str:
    """Determine health status (healthy/risk/critical) for a KPI value."""
    kpi = get_kpi_by_code(kpi_code)
    if not kpi:
        return 'unknown'

    ranges = kpi.get('ranges', {})
    for status in ['healthy', 'risk', 'critical']:
        range_def = ranges.get(status, {})
        min_val = range_def.get('min', float('-inf'))
        max_val = range_def.get('max', float('inf'))
        if min_val <= value <= max_val:
            return status
    return 'unknown'


def calculate_pillar_score(pillar: str, kpi_values: Dict[str, float]) -> float:
    """Calculate weighted pillar score from KPI values (0-100)."""
    pillar_kpis = get_kpis_by_pillar(pillar)
    total_score = 0.0
    total_weight = 0.0

    for kpi_code, kpi_def in pillar_kpis.items():
        if kpi_code not in kpi_values:
            continue
        value = kpi_values[kpi_code]
        weight = kpi_def.get('weight_l1', 0)
        ranges = kpi_def.get('ranges', {})
        healthy_range = ranges.get('healthy', {})

        if kpi_def.get('higher_is_better', True):
            max_val = healthy_range.get('max', 100)
            normalized = min(100, (value / max_val) * 100) if max_val > 0 else 0
        else:
            min_val = healthy_range.get('min', 0)
            max_val = healthy_range.get('max', 100)
            normalized = max(0, 100 - ((value - min_val) / (max_val - min_val)) * 100) if (max_val - min_val) > 0 else 0

        total_score += normalized * weight
        total_weight += weight

    return (total_score / total_weight) if total_weight > 0 else 0


def calculate_overall_health(pillar_scores: Dict[str, float]) -> float:
    """Calculate overall health score from pillar scores (0-100)."""
    total_score = 0.0
    for pillar, score in pillar_scores.items():
        pillar_def = get_pillar_info(pillar)
        if pillar_def:
            weight = pillar_def.get('weight_l2', 0)
            total_score += score * weight
    return total_score
