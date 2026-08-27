"""
WS-2 2f — csv_import OUTCOME-node blind spot for the I3' unearned-confidence
clamp (found and fixed 2026-08-27, during 2f scoping follow-up).

`clamp_unearned_confidence()` (I3') is correctly wired into `upsert_node()`
(utils/context_graph.py:942) and fires on every OUTCOME write that goes
through it. But `outcomes.csv`'s OUTCOME writer in
mcp_server/cs_pulse_onboarding.py's `_process_data_impl()` constructs
`ContextNode(...)` directly and never calls `upsert_node()` — the same bug
class already flagged for edges (`add_edge()` skipping the invariant gate),
just never previously caught for nodes. That bypass is deliberate for a
different reason (source_event_id is degenerate here — 'outcome:<type>',
shared across same-type rows — so upsert_node's cross-row dedup on that key
would silently overwrite distinct outcomes, reopening the 2026-08-24
accumulation-bug fix in a worse, data-loss form) — so the fix applies
`clamp_unearned_confidence()` directly rather than rerouting the write.

This test reproduces exactly what the fixed writer does (not a full
_process_data_impl() invocation, which needs a much larger CSV fixture set)
and is a DB round-trip in the same style as
tests/test_csv_import_edge_provenance.py.

Run against a dedicated postgres test DB:
    DATABASE_URL="postgresql://manojgupta@localhost:5432/cs_pulse_test" \\
        python3 -m pytest tests/test_csv_import_outcome_provenance.py -v
"""
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app, db
from models import Account, ContextNode, Customer
from utils.context_graph_invariants import clamp_unearned_confidence

BACKEND = Path(__file__).resolve().parent.parent
CS_PULSE_ONBOARDING = BACKEND / 'mcp_server' / 'cs_pulse_onboarding.py'


# ═════════════════════════════════════════════════════════════════════
# 1. Static source check — the writer must call the real clamp function,
#    not a hand-rolled reimplementation that could drift from I3'.
# ═════════════════════════════════════════════════════════════════════

def test_outcomes_writer_calls_the_real_clamp_function():
    src = CS_PULSE_ONBOARDING.read_text()
    assert 'from utils.context_graph_invariants import clamp_unearned_confidence' in src
    assert '_o_conf, _o_props, _o_tier, _o_clamped = clamp_unearned_confidence(' in src
    # The clamp's outputs must actually be used on the write, not computed
    # and discarded — this is the exact class of bug the "found no call
    # site" investigation was chasing.
    assert 'properties=_o_props,' in src
    assert 'tier=_o_tier, confidence=_o_conf,' in src


# ═════════════════════════════════════════════════════════════════════
# 2. DB round-trip — a fresh outcomes.csv-shaped OUTCOME node without
#    evidence gets clamped; one with real evidence does not.
# ═════════════════════════════════════════════════════════════════════

def _assert_isolated_test_db(uri: str) -> None:
    """See tests/test_context_graph_invariants.py — same guard, same reason:
    this fixture calls db.drop_all() on teardown and must never run against
    a non-test database (feedback_destructive_test_fixture.md)."""
    if os.environ.get('ALLOW_DESTRUCTIVE_TEST_DB') == '1':
        return
    db_name = uri.rsplit('/', 1)[-1].split('?', 1)[0]
    if 'test' not in db_name.lower():
        raise RuntimeError(
            f"test_csv_import_outcome_provenance.py refuses to run "
            f"db.drop_all() against database {db_name!r} — its name "
            f"doesn't contain 'test'."
        )


@pytest.fixture(scope='module')
def ctx():
    import uuid
    app.config['TESTING'] = True
    db_uri = os.environ.get(
        'DATABASE_URL', 'postgresql://manojgupta@localhost:5432/cs_pulse_test'
    )
    _assert_isolated_test_db(db_uri)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    with app.app_context():
        db.create_all()
        unique_email = f'csv_outcome_prov_{uuid.uuid4().hex[:8]}@test.com'
        customer = Customer(customer_name='CSV Outcome Provenance Test Co', email=unique_email)
        db.session.add(customer)
        db.session.commit()

        acct = Account(
            customer_id=customer.customer_id,
            account_name='Test Account',
            revenue=1_000_000,
            external_account_id='CSVOUTPROV-001',
            account_status='active',
        )
        db.session.add(acct)
        db.session.commit()

        yield {'customer_id': customer.customer_id, 'account_id': acct.account_id}

        db.session.remove()
        db.drop_all()


def _write_outcome_like_the_fixed_loop(ctx, *, evidence: str, title: str):
    """Reproduces exactly what the fixed outcomes.csv loop in
    _process_data_impl does for one row — construction, clamp call, and
    the same field mapping — without needing the full CSV fixture set
    _process_data_impl requires to reach this code path."""
    props = {'evidence': evidence, 'confidence': ''}
    source_platform = 'csv_import'
    conf, props, tier, clamped = clamp_unearned_confidence(
        node_type='OUTCOME',
        source_platform=source_platform,
        source_ref=None,
        confidence=1.0,
        properties=props,
        tier=1,
    )
    node = ContextNode(
        customer_id=ctx['customer_id'], account_id=ctx['account_id'],
        node_type='OUTCOME',
        source='observed',
        node_subtype='revenue_at_risk',
        title=title,
        revenue_impact=-100_000,
        revenue_impact_type='revenue_at_risk',
        properties=props,
        tier=tier, confidence=conf, occurred_at=datetime(2026, 1, 1),
        source_platform=source_platform,
        source_event_id='outcome:revenue_at_risk',
    )
    db.session.add(node)
    db.session.commit()
    return node


class TestCsvImportOutcomeGetsUnearnedConfidenceClamp:
    def test_outcome_without_evidence_is_clamped(self, ctx):
        """This is F3's exact live-data shape: properties.evidence='' and
        no source_ref — must be clamped, not pass through at full
        confidence/tier-1 the way the pre-fix bypass allowed."""
        node = _write_outcome_like_the_fixed_loop(
            ctx, evidence='', title='Revenue at Risk — No Evidence Co',
        )
        reloaded = db.session.get(ContextNode, node.node_id)

        assert float(reloaded.confidence) <= 0.3
        assert reloaded.tier == 2
        assert reloaded.properties.get('evidence_clamped') is True
        assert 'csv_import' in reloaded.properties.get('evidence_clamped_reason', '')

    def test_outcome_with_real_evidence_is_not_clamped(self, ctx):
        """A row that genuinely carries evidence text must pass through
        untouched — the clamp must not become a blanket csv_import
        penalty."""
        node = _write_outcome_like_the_fixed_loop(
            ctx, evidence='CRM opportunity #4471, escalation log attached',
            title='Revenue at Risk — Real Evidence Co',
        )
        reloaded = db.session.get(ContextNode, node.node_id)

        assert float(reloaded.confidence) == 1.0
        assert reloaded.tier == 1
        assert 'evidence_clamped' not in reloaded.properties


if __name__ == '__main__':
    import pytest as _pytest
    _pytest.main([__file__, '-v'])
