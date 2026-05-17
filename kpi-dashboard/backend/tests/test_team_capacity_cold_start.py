#!/usr/bin/env python3
"""
Regression test for the cold-start path of the `get_team_capacity` MCP tool.

Pins the May 17 2026 fix for:
    Error calling tool 'get_team_capacity':
    'Account' object has no attribute 'health_score'

The `Account` model has NO `health_score` column — health scores live in the
separate `HealthScore` table (one row per account per measurement_month).
Before the fix, the tool dereferenced `account.health_score` directly, which
raised AttributeError for every tenant. The bug was observed against
freshly-registered SaaS tenants (cust 334 / cust 336) on May 17.

Cold-start case (this test): a freshly-registered tenant with
`recent_playbooks_90d == 0` AND no `HealthScore` rows yet must return a
200-shaped success response (not raise).
"""

import os
import sys
import uuid
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app, db
from models import Customer, Account, HealthScore

# The MCP tool imports fastmcp transitively. CI/EC2 have it; some dev shells
# don't. Skip the tool-invoking tests cleanly when the dep is missing — the
# model-shape canary at the bottom still runs as a cheap regression backstop.
def _has_fastmcp() -> bool:
    try:
        import fastmcp  # noqa: F401
        return True
    except ImportError:
        return False


_requires_fastmcp = pytest.mark.skipif(
    not _has_fastmcp(),
    reason='fastmcp not installed (CI/EC2 have it; some local dev shells do not)',
)


def _patch_mcp_helpers(monkeypatch):
    """Patch out MCP feature gate + auth so we can call the tool fn directly."""
    import mcp_server.cs_pulse_revenue as mod
    monkeypatch.setattr(mod, '_check_mcp_enabled', lambda: None)
    monkeypatch.setattr(mod, '_require_auth', lambda customer_id, *a, **kw: None)
    monkeypatch.setattr(mod, '_get_flask_app', lambda: app)


@pytest.fixture
def cold_start_tenant():
    """Freshly-registered tenant: 5 accounts, no HealthScore rows, no playbooks."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()

        customer = Customer(
            customer_name='Cold Start Tenant',
            email=f'cold_{uuid.uuid4().hex[:6]}@test.com',
        )
        db.session.add(customer)
        db.session.commit()

        for i in range(5):
            db.session.add(Account(
                customer_id=customer.customer_id,
                account_name=f'Fresh Account {i}',
                revenue=1_000_000,
                account_status='active',
                external_account_id=f'COLD-{i}',
            ))
        db.session.commit()

        yield {'customer_id': customer.customer_id}

        db.session.remove()
        db.drop_all()


@pytest.fixture
def warm_tenant_at_risk():
    """Tenant with HealthScore rows — one account below the healthy threshold."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()

        customer = Customer(
            customer_name='Warm Tenant',
            email=f'warm_{uuid.uuid4().hex[:6]}@test.com',
        )
        db.session.add(customer)
        db.session.commit()

        # 3 accounts: 2 healthy (80), 1 at-risk (55)
        scores = [80, 80, 55]
        for i, hs in enumerate(scores):
            acct = Account(
                customer_id=customer.customer_id,
                account_name=f'Warm Account {i}',
                revenue=2_000_000,
                account_status='active',
                external_account_id=f'WARM-{i}',
            )
            db.session.add(acct)
            db.session.commit()

            db.session.add(HealthScore(
                account_id=acct.account_id,
                measurement_month=date(2026, 5, 1),
                health_score=hs,
            ))
        db.session.commit()

        yield {'customer_id': customer.customer_id}

        db.session.remove()
        db.drop_all()


@_requires_fastmcp
def test_cold_start_tenant_no_health_scores_no_playbooks(monkeypatch, cold_start_tenant):
    """Cold-start path: no HealthScore rows + 0 recent playbooks → success, not AttributeError."""
    _patch_mcp_helpers(monkeypatch)
    from mcp_server.cs_pulse_revenue import get_team_capacity

    result = get_team_capacity(customer_id=cold_start_tenant['customer_id'])

    # Shape sanity
    assert isinstance(result, dict)
    assert result['scope'] == 'portfolio'
    assert result['customer_id'] == cold_start_tenant['customer_id']
    assert result['active_playbooks'] == 0
    assert result['recent_playbooks_90d'] == 0
    assert result['bottleneck_roles'] == []

    # Portfolio context: 5 accounts, $5M ARR, 0 at-risk (no HealthScore rows yet)
    ctx = result['portfolio_context']
    assert ctx['total_accounts'] == 5
    assert ctx['at_risk_accounts'] == 0, (
        'Cold-start tenants with no HealthScore rows must report 0 at-risk '
        'accounts (not raise AttributeError on Account.health_score).'
    )
    assert ctx['total_arr'] == 5_000_000


@_requires_fastmcp
def test_warm_tenant_health_scores_drive_at_risk_count(monkeypatch, warm_tenant_at_risk):
    """When HealthScore rows exist, at_risk_count must reflect them (below healthy_min)."""
    _patch_mcp_helpers(monkeypatch)
    from mcp_server.cs_pulse_revenue import get_team_capacity
    import utils.health_thresholds as ht

    result = get_team_capacity(customer_id=warm_tenant_at_risk['customer_id'])

    ctx = result['portfolio_context']
    assert ctx['total_accounts'] == 3
    # Score=55 is < healthy_min (70) → exactly 1 at-risk account
    assert ctx['at_risk_accounts'] == 1, (
        f'Expected 1 at-risk account (score=55 < healthy_min={ht.healthy_min()}), '
        f'got {ctx["at_risk_accounts"]}'
    )


def test_account_model_has_no_health_score_column():
    """Pin the assumption the fix is built on: Account does NOT carry health_score.

    If this test ever fails (i.e. a `health_score` column is added to Account),
    revisit cs_pulse_revenue.get_team_capacity — the HealthScore join is no
    longer needed and the simpler `a.health_score` access becomes safe again.
    """
    assert 'health_score' not in Account.__table__.columns.keys(), (
        'Account model gained a health_score column — review '
        'get_team_capacity in cs_pulse_revenue.py.'
    )
