#!/usr/bin/env python3
"""
SaaS Premium Vertical - KPI Definitions
Product-led SaaS companies

Source of truth: config/saas_premium_kpi_catalog.json (v3.0)
This module loads from JSON and exposes the same API as the legacy Python dicts.

41 KPIs across 5 pillars:
- P1: Product Adoption & Usage (30%)
- P2: Customer Engagement (15%)
- P3: Customer Sentiment & Support (20%)
- P4: Partner & Ecosystem Health (15%)
- P5: Revenue & Growth (20%)
"""

import json
import os
from typing import Dict, Any

# ============================================================
# LOAD FROM JSON CATALOG (single source of truth)
# ============================================================

_CATALOG_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'config', 'saas_premium_kpi_catalog.json'
)

with open(_CATALOG_PATH) as _f:
    _CATALOG = json.load(_f)

SAAS_PILLARS: Dict[str, Dict[str, Any]] = _CATALOG['pillars']
SAAS_KPIS: Dict[str, Dict[str, Any]] = _CATALOG['kpis']

# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================


def get_kpi(code: str) -> Dict:
    """Get KPI definition by code (e.g. P1-KPI1)."""
    return SAAS_KPIS.get(code)


def get_pillar(code: str) -> Dict:
    """Get pillar definition by code (e.g. P1)."""
    return SAAS_PILLARS.get(code)


def get_kpis_for_pillar(pillar_code: str) -> Dict[str, Dict]:
    """Get all KPIs for a pillar."""
    return {k: v for k, v in SAAS_KPIS.items() if v["pillar"] == pillar_code}
