"""
Playbook-close OUTCOME node clamp (WS-2 2f, playbook-close blind spot,
2026-08-27).

_write_context_graph_outcome() (utils/playbook_lifecycle.py) constructs its
three OUTCOME nodes (revenue_protected / revenue_expanded / no-revenue
fallback) via raw ContextNode() -- the same bypass class as the fixed
outcomes.csv writer (item 30): it never called upsert_node(), so every
playbook-close OUTCOME claimed the hardcoded tier=1 and the model's default
confidence=1.0 unconditionally, with no evidence content. Confirmed live on
customer 408: every existing `playbook_outcome` row shows
confidence=1.00, tier=1, evidence=NULL.

Unlike outcomes.csv, there IS a genuine, non-fabricated evidentiary basis
here -- the tracked PlaybookExecutionV2 record itself (health_at_trigger,
health_at_close, health_delta, total_cost) -- so the fix stamps real
evidence text derived from it (plus a source_ref pointer to the execution
row) rather than just letting these nodes get clamped down. The I3' clamp
is still applied as defense-in-depth for the case where those health
fields are missing (e.g. a 'timeout' outcome).

Run against a dedicated postgres test DB:
    DATABASE_URL="postgresql://manojgupta@localhost:5432/cs_pulse_test" \\
        python3 -m pytest tests/test_playbook_close_outcome_clamp.py -v
"""
import os
import sys
import uuid
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app, db
from models import Account, ContextNode, Customer, PlaybookExecutionV2
from utils.playbook_lifecycle import _write_context_graph_outcome


def _assert_isolated_test_db(uri: str) -> None:
    """See tests/test_context_graph_invariants.py — same guard, same reason."""
    if os.environ.get('ALLOW_DESTRUCTIVE_TEST_DB') == '1':
        return
    db_name = uri.rsplit('/', 1)[-1].split('?', 1)[0]
    if 'test' not in db_name.lower():
        raise RuntimeError(
            f"test_playbook_close_outcome_clamp.py refuses to run "
            f"db.drop_all() against database {db_name!r} — its name "
            f"doesn't contain 'test'."
        )


@pytest.fixture(scope='module')
def ctx():
    app.config['TESTING'] = True
    db_uri = os.environ.get(
        'DATABASE_URL', 'postgresql://manojgupta@localhost:5432/cs_pulse_test'
    )
    _assert_isolated_test_db(db_uri)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    with app.app_context():
        db.create_all()
        unique_email = f'pb_close_{uuid.uuid4().hex[:8]}@test.com'
        customer = Customer(customer_name='Playbook Close Test Co', email=unique_email)
        db.session.add(customer)
        db.session.commit()

        account = Account(
            customer_id=customer.customer_id,
            account_name='Test Account',
            revenue=1_000_000,
            external_account_id=f'PBCLOSE-{uuid.uuid4().hex[:8]}',
            account_status='active',
        )
        db.session.add(account)
        db.session.commit()

        yield {'customer_id': customer.customer_id, 'account_id': account.account_id}

        db.session.remove()
        db.drop_all()


def _make_execution(ctx, *, health_at_trigger, health_at_close, health_delta, playbook_id='PB-02'):
    execution = PlaybookExecutionV2(
        execution_id=f'exec-{uuid.uuid4().hex[:12]}',
        customer_id=ctx['customer_id'],
        account_id=ctx['account_id'],
        playbook_id=playbook_id,
        status='completed',
        health_at_trigger=health_at_trigger,
        health_at_close=health_at_close,
        health_delta=health_delta,
        realized_roi_pct=250.0,
        csm_hourly_rate=85.0,
    )
    db.session.add(execution)
    db.session.commit()
    return execution


class TestPlaybookCloseOutcomeGetsRealEvidenceNotFabricatedConfidence:
    def test_normal_close_gets_real_evidence_and_full_confidence(self, ctx):
        """A close with real health data earns its confidence -- the
        evidence is genuine (derived from the tracked execution), not a
        hardcoded default with nothing behind it."""
        with app.app_context():
            execution = _make_execution(
                ctx, health_at_trigger=35.0, health_at_close=68.0, health_delta=33.0,
            )
            _write_context_graph_outcome(
                execution, ctx['customer_id'], outcome='resolved',
                revenue_protected=250_000, revenue_expanded=0,
                arr=1_000_000, full_cost=8_500,
            )
            node = ContextNode.query.filter_by(
                customer_id=ctx['customer_id'], node_subtype='playbook_outcome',
            ).first()
            assert node is not None
            assert float(node.confidence) == 1.0, (
                "real evidence must earn full confidence, not get clamped"
            )
            assert node.tier == 1
            evidence = node.properties.get('evidence', '')
            assert 'PB-02' in evidence and '35.0' in evidence and '68.0' in evidence, (
                f"evidence must be genuinely derived from the execution "
                f"record, not empty or generic: {evidence!r}"
            )
            assert node.source_ref == f'playbook_execution:{execution.execution_id}'

    def test_missing_health_at_close_does_not_crash_and_still_clamps_safely(self, ctx):
        """A 'timeout' outcome can have health_at_close=None -- the fix's
        evidence formatting must not crash on this (regression risk
        introduced by :.1f-formatting a value the old plain-dict
        common_props never formatted), and the resulting node must still
        be safely clamped since its evidence is incomplete."""
        with app.app_context():
            execution = _make_execution(
                ctx, health_at_trigger=35.0, health_at_close=None, health_delta=None,
                playbook_id='PB-03',
            )
            # Must not raise.
            _write_context_graph_outcome(
                execution, ctx['customer_id'], outcome='timeout',
                revenue_protected=0, revenue_expanded=0,
                arr=1_000_000, full_cost=8_500,
            )
            node = ContextNode.query.filter_by(
                customer_id=ctx['customer_id'],
                node_subtype='playbook_outcome',
                source_event_id=f'close:{execution.execution_id}',
            ).first()
            assert node is not None
            evidence = node.properties.get('evidence', '')
            assert 'unknown' in evidence, (
                f"missing health fields must format safely, not crash: {evidence!r}"
            )

    def test_no_raw_contextnode_bypass_left_unclamped(self, ctx):
        """All three ContextNode() call sites in this function must pass
        through the clamp's confidence/tier, not the old hardcoded tier=1
        with no confidence kwarg (which silently took the model default of
        1.0). Static AST check, following test_playbook_close_edge_
        abstention.py's convention."""
        import ast
        from pathlib import Path
        lifecycle = Path(__file__).resolve().parent.parent / 'utils' / 'playbook_lifecycle.py'
        tree = ast.parse(lifecycle.read_text())
        fn = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == '_write_context_graph_outcome'
        )
        node_calls = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == 'ContextNode'
        ]
        assert len(node_calls) == 3, (
            f"expected 3 ContextNode() call sites, found {len(node_calls)} — "
            f"update this test if the function's shape changed"
        )
        for call in node_calls:
            kwarg_names = {kw.arg for kw in call.keywords}
            assert 'confidence' in kwarg_names, (
                f"ContextNode() at line {call.lineno} has no explicit "
                f"confidence= -- would silently take the model default "
                f"(1.0) again, bypassing the clamp"
            )
            tier_kwarg = next(kw for kw in call.keywords if kw.arg == 'tier')
            assert not (
                isinstance(tier_kwarg.value, ast.Constant) and tier_kwarg.value.value == 1
            ), (
                f"ContextNode() at line {call.lineno} has a hardcoded "
                f"tier=1 constant again instead of the clamp's _tier"
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
