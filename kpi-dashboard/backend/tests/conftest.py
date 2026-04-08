"""
Shared test fixtures for CS Pulse backend tests.

Usage:
    pytest kpi-dashboard/backend/tests/ -v
"""

import os
import sys
import pytest
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ═══════════════════════════════════════════════════════════════
# Factory Fixtures — create test data without DB
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def make_account():
    """Factory for account dicts (no DB required)."""
    _counter = [0]
    def _factory(*, name=None, health_score=75, arr=1_000_000, classification='healthy',
                 industry='Technology', region='US-West', csm='Alice Chen'):
        _counter[0] += 1
        return {
            'account_id': _counter[0],
            'account_name': name or f'Test Account {_counter[0]}',
            'health_score': health_score,
            'arr': arr,
            'classification': classification,
            'industry': industry,
            'region': region,
            'csm_name': csm,
        }
    return _factory


@pytest.fixture
def make_kpi_measurement():
    """Factory for KPI measurement dicts."""
    def _factory(*, account_id=1, kpi_code='P1-KPI1', value=85.0,
                 measurement_date=None):
        return {
            'account_id': account_id,
            'kpi_code': kpi_code,
            'value': value,
            'measurement_date': measurement_date or datetime.utcnow().strftime('%Y-%m-%d'),
        }
    return _factory


@pytest.fixture
def make_health_score():
    """Factory for health score records."""
    def _factory(*, account_id=1, overall_score=72, measurement_month=None,
                 pillar_scores=None):
        return {
            'account_id': account_id,
            'overall_score': overall_score,
            'measurement_month': measurement_month or datetime.utcnow().strftime('%Y-%m'),
            'pillar_scores': pillar_scores or {
                'P1': 75, 'P2': 70, 'P3': 68, 'P4': 72, 'P5': 74
            },
        }
    return _factory


@pytest.fixture
def make_signal():
    """Factory for qualitative signal dicts."""
    _counter = [0]
    def _factory(*, account_id=1, signal_type='champion_loss', severity='high',
                 content='Champion departed', source='slack'):
        _counter[0] += 1
        return {
            'signal_id': f'sig_{_counter[0]}',
            'account_id': account_id,
            'signal_type': signal_type,
            'severity': severity,
            'content': content,
            'source_channel': source,
            'created_at': datetime.utcnow().isoformat(),
        }
    return _factory


@pytest.fixture
def portfolio_accounts(make_account):
    """A realistic 10-account portfolio with mixed health states."""
    return [
        make_account(name='Alpha Corp', health_score=85, arr=5_000_000, classification='healthy'),
        make_account(name='Beta Inc', health_score=78, arr=3_200_000, classification='healthy'),
        make_account(name='Gamma LLC', health_score=72, arr=2_800_000, classification='healthy'),
        make_account(name='Delta Systems', health_score=65, arr=4_100_000, classification='at_risk'),
        make_account(name='Epsilon Tech', health_score=58, arr=1_500_000, classification='at_risk'),
        make_account(name='Zeta Cloud', health_score=55, arr=2_200_000, classification='at_risk'),
        make_account(name='Eta Networks', health_score=45, arr=3_800_000, classification='critical'),
        make_account(name='Theta Data', health_score=38, arr=1_200_000, classification='critical'),
        make_account(name='Iota Services', health_score=82, arr=6_000_000, classification='healthy'),
        make_account(name='Kappa Labs', health_score=91, arr=2_500_000, classification='healthy'),
    ]


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
