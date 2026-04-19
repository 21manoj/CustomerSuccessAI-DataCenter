#!/usr/bin/env python3
"""
Tests for manifest playbook revenue attribution (point-in-time health lookup).

Covers the fix for:
  - start_execution: fallback must honor triggered_at when health_at_trigger is None
  - close_execution: health_at_close must use closed_at, not utcnow()
  - End-to-end: historical trigger + historical close → non-zero revenue when
    the account's health recovered between the two dates.
"""

import os
import sys
import uuid
from datetime import datetime, date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app, db
from models import Customer, Account, HealthScore, PlaybookExecutionV2
from utils.playbook_lifecycle import start_execution, close_execution


@pytest.fixture(scope='module')
def ctx():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        customer = Customer(customer_name='Test Cust', email=f'rev_{uuid.uuid4().hex[:6]}@test.com')
        db.session.add(customer)
        db.session.commit()

        account = Account(
            customer_id=customer.customer_id,
            account_name='Recovery Account',
            revenue=4_000_000,  # $4M ARR
            account_status='active',
            external_account_id='REV-001',
        )
        db.session.add(account)
        db.session.commit()

        # Health trajectory: critical in Dec (42), recovering Jan (65), healthy April (80)
        for month, score in [
            (date(2025, 12, 1), 42),   # trigger month: critical
            (date(2026, 1, 1), 65),    # close month: at-risk, recovering
            (date(2026, 2, 1), 72),
            (date(2026, 3, 1), 76),
            (date(2026, 4, 1), 80),    # current month: healthy
        ]:
            db.session.add(HealthScore(
                account_id=account.account_id,
                measurement_month=month,
                health_score=score,
            ))
        db.session.commit()

        yield {'customer_id': customer.customer_id, 'account_id': account.account_id}

        db.session.remove()
        db.drop_all()


def test_start_execution_uses_historical_health_when_triggered_at_set(ctx):
    """Fallback must respect triggered_at and pick Dec 2025 health (42), not April (80)."""
    with app.app_context():
        trigger_date = datetime(2025, 12, 10)
        exec_v2 = start_execution(
            customer_id=ctx['customer_id'],
            account_id=ctx['account_id'],
            playbook_id='PB-02',
            triggered_by='manifest_test',
            triggered_at=trigger_date,
            # health_at_trigger deliberately omitted → exercises fallback
        )
        assert exec_v2.health_at_trigger == 42, (
            f'Expected Dec 2025 health=42, got {exec_v2.health_at_trigger}'
        )
        assert exec_v2.health_status_at_trigger == 'critical'
        assert exec_v2.arr_at_trigger == 4_000_000
        assert exec_v2.triggered_at == trigger_date


def test_start_execution_uses_latest_health_when_no_triggered_at(ctx):
    """Backward-compat: without triggered_at, still pick latest health."""
    with app.app_context():
        exec_v2 = start_execution(
            customer_id=ctx['customer_id'],
            account_id=ctx['account_id'],
            playbook_id='PB-05',
            triggered_by='csm_manual',
        )
        assert exec_v2.health_at_trigger == 80, 'Should default to April 2026 (latest)'


def test_close_execution_uses_historical_health_when_closed_at_set(ctx):
    """health_at_close must come from Jan 2026 (65), not April (80)."""
    with app.app_context():
        # Seed an execution anchored at Dec 2025 first
        trigger_date = datetime(2025, 12, 10)
        exec_v2 = start_execution(
            customer_id=ctx['customer_id'],
            account_id=ctx['account_id'],
            playbook_id='PB-02',
            triggered_by='manifest_test',
            triggered_at=trigger_date,
        )
        eid = exec_v2.execution_id

        # Close with historical closed_at
        close_date = datetime(2026, 1, 10)
        closed = close_execution(
            customer_id=ctx['customer_id'],
            execution_id=eid,
            outcome='resolved',
            outcome_notes='recovered',
            closed_at=close_date,
        )
        assert closed.health_at_trigger == 42
        assert closed.health_at_close == 65, (
            f'Expected Jan 2026 health=65, got {closed.health_at_close}'
        )
        assert closed.health_delta == 23


def test_revenue_attribution_nonzero_with_historical_dates(ctx):
    """End-to-end: historical trigger + close → non-zero revenue_protected."""
    with app.app_context():
        exec_v2 = start_execution(
            customer_id=ctx['customer_id'],
            account_id=ctx['account_id'],
            playbook_id='PB-01',
            triggered_by='manifest_test',
            triggered_at=datetime(2025, 12, 10),
        )
        closed = close_execution(
            customer_id=ctx['customer_id'],
            execution_id=exec_v2.execution_id,
            outcome='resolved',
            closed_at=datetime(2026, 1, 10),
        )
        # Health 42→65: churn prob drops from ~43% to ~17.5%.
        # rev_protected ≈ (0.43 - 0.175) * $4M * 0.5 ≈ $510k
        assert closed.revenue_protected > 400_000, (
            f'Expected sizable revenue_protected, got {closed.revenue_protected}'
        )
        assert closed.realized_roi_pct > 0


def test_regression_both_unset_uses_current_month(ctx):
    """No triggered_at + no closed_at → health_delta is ~0 (latest-to-latest)."""
    with app.app_context():
        exec_v2 = start_execution(
            customer_id=ctx['customer_id'],
            account_id=ctx['account_id'],
            playbook_id='PB-06',
            triggered_by='csm_manual',
        )
        closed = close_execution(
            customer_id=ctx['customer_id'],
            execution_id=exec_v2.execution_id,
            outcome='resolved',
        )
        # Both snapshots should be April 80 → delta 0 → revenue_protected 0.
        assert closed.health_at_trigger == 80
        assert closed.health_at_close == 80
        assert closed.health_delta == 0
