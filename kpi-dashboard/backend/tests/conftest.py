"""
Shared test fixtures for CS Pulse backend tests.

Usage:
    pytest kpi-dashboard/backend/tests/ -v
"""

import os
import sys
import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def sample_kpi_values_healthy():
    """KPI values that should produce a healthy score (>= 70)."""
    return {
        'P1-KPI1': 88.0,   # DAU Rate — above target
        'P1-KPI3': 92.0,   # TTFV
        'P2-KPI1': 85.0,   # Exec Sponsor Engagement
        'P3-KPI1': 90.0,   # Ticket Resolution
        'P3-KPI3': 78.0,   # NPS
        'P3-KPI4': 88.0,   # Escalation Rate
        'P5-KPI1': 105.0,  # NRR
        'P5-KPI2': 95.0,   # GRR
        'P5-KPI3': 18.0,   # Expansion Rate
    }


@pytest.fixture
def sample_kpi_values_critical():
    """KPI values that should produce a critical score (< 50)."""
    return {
        'P1-KPI1': 25.0,
        'P1-KPI3': 30.0,
        'P2-KPI1': 20.0,
        'P3-KPI1': 35.0,
        'P3-KPI3': 15.0,
        'P3-KPI4': 40.0,
        'P5-KPI1': 85.0,
        'P5-KPI2': 78.0,
        'P5-KPI3': 3.0,
    }


@pytest.fixture
def sample_kpi_values_at_risk():
    """KPI values that should produce an at-risk score (50-69)."""
    return {
        'P1-KPI1': 55.0,
        'P1-KPI3': 60.0,
        'P2-KPI1': 50.0,
        'P3-KPI1': 65.0,
        'P3-KPI3': 45.0,
        'P3-KPI4': 60.0,
        'P5-KPI1': 95.0,
        'P5-KPI2': 88.0,
        'P5-KPI3': 8.0,
    }


@pytest.fixture
def starter_9_kpi_codes():
    """The 9 KPI codes in the SaaS Starter tier."""
    return [
        'P1-KPI1', 'P1-KPI3', 'P2-KPI1',
        'P3-KPI1', 'P3-KPI3', 'P3-KPI4',
        'P5-KPI1', 'P5-KPI2', 'P5-KPI3',
    ]


@pytest.fixture
def starter_9_pillar_weights():
    """Equal pillar weights for Starter 9 (4 pillars, P4 excluded)."""
    return {'P1': 0.25, 'P2': 0.25, 'P3': 0.25, 'P5': 0.25}


@pytest.fixture
def full_pillar_weights():
    """Default DC2_S pillar weights (all 5 pillars)."""
    return {'P1': 0.15, 'P2': 0.20, 'P3': 0.25, 'P4': 0.15, 'P5': 0.25}
