"""
Pytest suite for context graph invariants.

Each invariant has a paired (clean, dirty) test:
- clean_<Ix> seeds a known-good fixture, asserts zero violations
- dirty_<Ix> seeds a violation-inducing fixture, asserts the expected
  violation IS caught with the correct invariant_id + details

Run against a dedicated postgres test DB (create once: createdb cs_pulse_test)
    DATABASE_URL="postgresql://manojgupta@localhost:5432/cs_pulse_test" \\
        python3 -m pytest tests/test_context_graph_invariants.py -v
"""

import os
import sys
from datetime import date, datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app, db
from models import (
    Account,
    ContextEdge,
    ContextNode,
    Customer,
    HealthScore,
)
from utils.context_graph_invariants import (
    CANONICAL_ARC_TYPES,
    INVARIANTS_REGISTRY,
    run_all_invariants,
    run_invariant,
)


# ═════════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════════


@pytest.fixture(scope='module')
def ctx():
    """One-time customer + DB setup. Each test clears and reseeds context graph data."""
    import uuid
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'postgresql://manojgupta@localhost:5432/cs_pulse_test'
    )
    with app.app_context():
        db.create_all()
        unique_email = f'inv_{uuid.uuid4().hex[:8]}@test.com'
        customer = Customer(customer_name='Invariant Test Co', email=unique_email)
        db.session.add(customer)
        db.session.commit()

        acct = Account(
            customer_id=customer.customer_id,
            account_name='Test Account',
            revenue=1_000_000,
            external_account_id='INV-001',
            account_status='active',
        )
        db.session.add(acct)
        db.session.commit()

        yield {'customer_id': customer.customer_id, 'account_id': acct.account_id}

        db.session.remove()
        db.drop_all()


def _clear_graph(customer_id: int):
    """Remove all context graph data for this customer between tests."""
    ContextEdge.query.filter_by(customer_id=customer_id).delete()
    ContextNode.query.filter_by(customer_id=customer_id).delete()
    db.session.commit()


def _make_node(ctx, **kwargs) -> ContextNode:
    """Create a ContextNode with sensible defaults."""
    defaults = {
        'customer_id': ctx['customer_id'],
        'account_id': ctx['account_id'],
        'node_type': 'SIGNAL',
        'title': 'Test node',
        'occurred_at': datetime(2026, 1, 1),
        'source': 'test',
        'source_platform': 'test',
        'tier': 1,
    }
    defaults.update(kwargs)
    n = ContextNode(**defaults)
    db.session.add(n)
    db.session.flush()
    return n


def _make_edge(ctx, from_node, to_node, **kwargs) -> ContextEdge:
    defaults = {
        'customer_id': ctx['customer_id'],
        'from_node_id': from_node.node_id,
        'to_node_id': to_node.node_id,
        'edge_type': 'LED_TO',
        'confidence': 0.8,
        'source_platform': 'test',
        'created_by': 'test',
    }
    defaults.update(kwargs)
    e = ContextEdge(**defaults)
    db.session.add(e)
    db.session.flush()
    return e


# ═════════════════════════════════════════════════════════════════════
# I1 — No OUTCOME→OUTCOME causal edges
# ═════════════════════════════════════════════════════════════════════


def test_i1_clean(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s = _make_node(ctx, node_type='SIGNAL', node_subtype='escalation')
        o = _make_node(ctx, node_type='OUTCOME', node_subtype='churn_lost',
                       revenue_impact=-100_000, revenue_impact_type='lost')
        _make_edge(ctx, s, o, edge_type='LED_TO')
        db.session.commit()
        violations = run_invariant('I1', ctx['customer_id'])
        assert violations == [], [v.to_dict() for v in violations]


def test_i1_dirty(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        o1 = _make_node(ctx, node_type='OUTCOME', node_subtype='playbook_outcome',
                        revenue_impact=50_000, revenue_impact_type='protected')
        o2 = _make_node(ctx, node_type='OUTCOME', node_subtype='renewal_at_risk',
                        revenue_impact=-100_000, revenue_impact_type='at_risk')
        _make_edge(ctx, o1, o2, edge_type='LED_TO')  # the bad edge
        db.session.commit()
        violations = run_invariant('I1', ctx['customer_id'])
        assert len(violations) == 1
        assert violations[0].invariant_id == 'I1'
        assert violations[0].severity == 'error'
        assert 'OUTCOME→OUTCOME' in violations[0].message


# ═════════════════════════════════════════════════════════════════════
# I2 — Polarity consistency
# ═════════════════════════════════════════════════════════════════════


def test_i2_clean(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s = _make_node(ctx, node_type='SIGNAL', node_subtype='escalation')  # negative
        o = _make_node(ctx, node_type='OUTCOME', node_subtype='churn_lost',  # negative
                       revenue_impact=-100_000, revenue_impact_type='lost')
        _make_edge(ctx, s, o, edge_type='LED_TO')
        db.session.commit()
        violations = run_invariant('I2', ctx['customer_id'])
        assert violations == []


def test_i2_dirty_positive_to_negative(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s = _make_node(ctx, node_type='SIGNAL', node_subtype='kpi_recovery')  # positive
        o = _make_node(ctx, node_type='OUTCOME', node_subtype='churn_lost',   # negative
                       revenue_impact=-100_000, revenue_impact_type='lost')
        _make_edge(ctx, s, o, edge_type='LED_TO')
        db.session.commit()
        violations = run_invariant('I2', ctx['customer_id'])
        assert len(violations) == 1
        assert violations[0].details['mismatch_type'] == 'positive_signal_to_negative_outcome'


def test_i2_dirty_negative_to_positive(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s = _make_node(ctx, node_type='SIGNAL', node_subtype='champion_loss')   # negative
        o = _make_node(ctx, node_type='OUTCOME', node_subtype='expansion_closed',  # positive
                       revenue_impact=200_000, revenue_impact_type='expansion')
        _make_edge(ctx, s, o, edge_type='LED_TO')
        db.session.commit()
        violations = run_invariant('I2', ctx['customer_id'])
        assert len(violations) == 1
        assert violations[0].details['mismatch_type'] == 'negative_signal_to_positive_outcome'


# ═════════════════════════════════════════════════════════════════════
# I3 — No orphan revenue OUTCOMEs
# ═════════════════════════════════════════════════════════════════════


def test_i3_clean(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s = _make_node(ctx, node_type='SIGNAL', node_subtype='escalation')
        o = _make_node(ctx, node_type='OUTCOME', node_subtype='churn_lost',
                       revenue_impact=-100_000, revenue_impact_type='lost')
        _make_edge(ctx, s, o, edge_type='LED_TO')
        db.session.commit()
        violations = run_invariant('I3', ctx['customer_id'])
        assert violations == []


def test_i3_dirty(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='OUTCOME', node_subtype='engagement_declining',
                   revenue_impact=-500_000, revenue_impact_type='at_risk')  # orphan
        db.session.commit()
        violations = run_invariant('I3', ctx['customer_id'])
        assert len(violations) == 1
        assert 'Orphan OUTCOME' in violations[0].message


# ═════════════════════════════════════════════════════════════════════
# I4 — Confidence bounds (top-level AND properties JSONB)
# ═════════════════════════════════════════════════════════════════════


def test_i4_clean(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='SIGNAL', node_subtype='arc_detection',
                   confidence=0.85, properties={'confidence': 0.85, 'arc_type': 'crisis'})
        db.session.commit()
        violations = run_invariant('I4', ctx['customer_id'])
        assert violations == []


def test_i4_dirty_toplevel(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='SIGNAL', node_subtype='arc_detection',
                   confidence=1.1, properties={'confidence': 0.9})
        db.session.commit()
        violations = run_invariant('I4', ctx['customer_id'])
        assert any(v.details.get('field') == 'context_nodes.confidence' for v in violations)


def test_i4_dirty_properties_jsonb(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='SIGNAL', node_subtype='arc_detection',
                   confidence=0.9, properties={'confidence': 1.1, 'arc_type': 'crisis'})
        db.session.commit()
        violations = run_invariant('I4', ctx['customer_id'])
        assert any(
            v.details.get('field') == 'context_nodes.properties.confidence'
            for v in violations
        )


# ═════════════════════════════════════════════════════════════════════
# I5 — arc_type enum validation
# ═════════════════════════════════════════════════════════════════════


def test_i5_clean(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='SIGNAL', node_subtype='arc_detection',
                   properties={'arc_type': 'crisis_recovery'})
        db.session.commit()
        violations = run_invariant('I5', ctx['customer_id'])
        assert violations == []


def test_i5_dirty(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='SIGNAL', node_subtype='arc_detection',
                   properties={'arc_type': 'made_up_arc'})
        db.session.commit()
        violations = run_invariant('I5', ctx['customer_id'])
        assert len(violations) == 1
        assert violations[0].details['arc_type'] == 'made_up_arc'


# ═════════════════════════════════════════════════════════════════════
# I8 — churn_lost reconciled with account_status
# ═════════════════════════════════════════════════════════════════════


def test_i8_clean(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        acct = Account.query.get(ctx['account_id'])
        acct.account_status = 'churned'
        _make_node(ctx, node_type='OUTCOME', node_subtype='churn_lost',
                   revenue_impact=-1_000_000, revenue_impact_type='lost')
        db.session.commit()
        try:
            violations = run_invariant('I8', ctx['customer_id'])
            assert violations == []
        finally:
            acct.account_status = 'active'
            db.session.commit()


def test_i8_dirty(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        acct = Account.query.get(ctx['account_id'])
        acct.account_status = 'active'  # WRONG — should be churned
        _make_node(ctx, node_type='OUTCOME', node_subtype='churn_lost',
                   revenue_impact=-1_000_000, revenue_impact_type='lost')
        db.session.commit()
        violations = run_invariant('I8', ctx['customer_id'])
        assert len(violations) == 1
        assert 'churn_lost' in violations[0].message
        # Restore
        acct.account_status = 'active'
        db.session.commit()


# ═════════════════════════════════════════════════════════════════════
# I9 — no duplicate lifecycle outcomes
# ═════════════════════════════════════════════════════════════════════


def test_i9_clean(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='OUTCOME', node_subtype='churn_lost',
                   revenue_impact=-1_000_000, revenue_impact_type='lost')
        db.session.commit()
        violations = run_invariant('I9', ctx['customer_id'])
        assert violations == []


def test_i9_dirty(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='OUTCOME', node_subtype='churn_lost',
                   revenue_impact=-1_000_000, revenue_impact_type='lost',
                   source_event_id='lifecycle:churn:ld')
        _make_node(ctx, node_type='OUTCOME', node_subtype='churn_lost',
                   revenue_impact=-1_000_000, revenue_impact_type='lost',
                   source_event_id='lifecycle:churn:verify')
        db.session.commit()
        violations = run_invariant('I9', ctx['customer_id'])
        assert len(violations) == 1
        assert violations[0].details['count'] == 2


# ═════════════════════════════════════════════════════════════════════
# I10 — churn_averted + churn_lost mutex
# ═════════════════════════════════════════════════════════════════════


def test_i10_clean(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='OUTCOME', node_subtype='churn_averted',
                   revenue_impact=600_000, revenue_impact_type='protected')
        db.session.commit()
        violations = run_invariant('I10', ctx['customer_id'])
        assert violations == []


def test_i10_dirty(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='OUTCOME', node_subtype='churn_averted',
                   revenue_impact=600_000, revenue_impact_type='protected')
        _make_node(ctx, node_type='OUTCOME', node_subtype='churn_lost',
                   revenue_impact=-1_500_000, revenue_impact_type='lost')
        db.session.commit()
        violations = run_invariant('I10', ctx['customer_id'])
        assert len(violations) == 1
        assert set(violations[0].details['subtypes']) == {'churn_averted', 'churn_lost'}


# ═════════════════════════════════════════════════════════════════════
# I11 — revenue bucket consistency
# ═════════════════════════════════════════════════════════════════════


def test_i11_clean(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='OUTCOME', node_subtype='churn_lost',
                   revenue_impact=-100_000, revenue_impact_type='lost')
        db.session.commit()
        violations = run_invariant('I11', ctx['customer_id'])
        assert violations == []


def test_i11_dirty(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        # expansion_closed subtype (bucket=expansion) tagged as 'lost' (bucket=lost)
        # is a polarity mismatch.
        _make_node(ctx, node_type='OUTCOME', node_subtype='expansion_closed',
                   revenue_impact=200_000, revenue_impact_type='lost')
        db.session.commit()
        violations = run_invariant('I11', ctx['customer_id'])
        assert len(violations) == 1
        assert violations[0].details['subtype_bucket'] == 'expansion'
        assert violations[0].details['tag_bucket'] == 'lost'


# ═════════════════════════════════════════════════════════════════════
# I12 — account_status vs health consistency
# ═════════════════════════════════════════════════════════════════════


def test_i12_clean(ctx):
    with app.app_context():
        acct = Account.query.get(ctx['account_id'])
        acct.account_status = 'active'
        HealthScore.query.filter_by(account_id=acct.account_id).delete()
        db.session.add(HealthScore(account_id=acct.account_id,
                                    measurement_month=date(2026, 3, 1),
                                    health_score=85))
        db.session.commit()
        violations = run_invariant('I12', ctx['customer_id'])
        assert violations == []


def test_i12_dirty(ctx):
    with app.app_context():
        acct = Account.query.get(ctx['account_id'])
        acct.account_status = 'at_risk'  # contradicts health=85
        HealthScore.query.filter_by(account_id=acct.account_id).delete()
        db.session.add(HealthScore(account_id=acct.account_id,
                                    measurement_month=date(2026, 3, 1),
                                    health_score=85))
        db.session.commit()
        violations = run_invariant('I12', ctx['customer_id'])
        assert len(violations) == 1
        assert 'healthy' in violations[0].message.lower() or 'at_risk' in violations[0].message
        # Restore
        acct.account_status = 'active'
        db.session.commit()


# ═════════════════════════════════════════════════════════════════════
# I13 — No duplicate definitive lifecycle OUTCOMEs (catches W-B double count)
# ═════════════════════════════════════════════════════════════════════


def test_i13_clean(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='OUTCOME', node_subtype='expansion_closed',
                   revenue_impact=500_000, revenue_impact_type='expansion',
                   source_platform='load_driver', source_event_id='lc:expand:1')
        db.session.commit()
        violations = run_invariant('I13', ctx['customer_id'])
        assert violations == []


def test_i13_dirty(ctx):
    """The actual W-B double-count bug: csv_import + load_driver both
    create expansion_closed for the same account."""
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='OUTCOME', node_subtype='expansion_closed',
                   revenue_impact=500_000, revenue_impact_type='expansion',
                   source_platform='csv_import', source_event_id='csv:exp:1')
        _make_node(ctx, node_type='OUTCOME', node_subtype='expansion_closed',
                   revenue_impact=375_000, revenue_impact_type='expansion',
                   source_platform='load_driver', source_event_id='lc:exp:1')
        db.session.commit()
        violations = run_invariant('I13', ctx['customer_id'])
        assert len(violations) == 1
        assert violations[0].details['subtype'] == 'expansion_closed'
        assert set(violations[0].details['sources']) == {'csv_import', 'load_driver'}
        assert violations[0].details['combined_revenue_impact'] == 875_000


# ═════════════════════════════════════════════════════════════════════
# I14 — revenue_impact sign matches polarity
# ═════════════════════════════════════════════════════════════════════


def test_i14_clean(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='OUTCOME', node_subtype='churn_lost',
                   revenue_impact=-100_000, revenue_impact_type='lost')
        _make_node(ctx, node_type='OUTCOME', node_subtype='expansion_closed',
                   revenue_impact=200_000, revenue_impact_type='expansion')
        db.session.commit()
        violations = run_invariant('I14', ctx['customer_id'])
        assert violations == []


def test_i14_dirty_positive_churn(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='OUTCOME', node_subtype='churn_lost',
                   revenue_impact=+1_000_000, revenue_impact_type='lost')  # sign flipped
        db.session.commit()
        violations = run_invariant('I14', ctx['customer_id'])
        assert len(violations) == 1
        assert 'positive revenue_impact' in violations[0].message


def test_i14_dirty_negative_expansion(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        _make_node(ctx, node_type='OUTCOME', node_subtype='expansion_closed',
                   revenue_impact=-500_000, revenue_impact_type='expansion')  # sign flipped
        db.session.commit()
        violations = run_invariant('I14', ctx['customer_id'])
        assert len(violations) == 1
        assert 'negative revenue_impact' in violations[0].message


# ═════════════════════════════════════════════════════════════════════
# I15 — no duplicate signal+outcome pair with same title on same day
# ═════════════════════════════════════════════════════════════════════


def test_i15_clean(ctx):
    """Signal alone, or outcome alone, or outcome carrying revenue — no violation."""
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        occurred = datetime(2026, 3, 14, 10, 0, 0)
        # Signal alone
        _make_node(ctx, node_type='SIGNAL', node_subtype='kpi_decline',
                   title='Jul 31: KPI metrics declining', occurred_at=occurred)
        # Outcome with different title on same day — not a dup
        _make_node(ctx, node_type='OUTCOME', node_subtype='renewal_secured',
                   title='Jul 31: Completely different event',
                   revenue_impact=50_000, revenue_impact_type='protected',
                   occurred_at=occurred)
        # Signal + OUTCOME same title but outcome carries revenue → exempt
        _make_node(ctx, node_type='SIGNAL', node_subtype='champion_loss',
                   title='Feb 08: Champion departed',
                   occurred_at=datetime(2026, 2, 8, 10, 0, 0))
        _make_node(ctx, node_type='OUTCOME', node_subtype='churn_averted',
                   title='Feb 08: Champion departed',
                   revenue_impact=200_000, revenue_impact_type='protected',
                   occurred_at=datetime(2026, 2, 8, 10, 0, 0))
        db.session.commit()
        violations = run_invariant('I15', ctx['customer_id'])
        assert violations == [], (
            f'Expected 0 violations (no narrative-only dup), got {len(violations)}'
        )


def test_i15_dirty(ctx):
    """Wizard A duplicate pattern: signal + narrative-only outcome, same title, same day."""
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        day = datetime(2026, 7, 31, 10, 0, 0)
        _make_node(ctx, node_type='SIGNAL', node_subtype='kpi_decline',
                   title='Jul 31: KPI metrics declining below threshold',
                   occurred_at=day)
        _make_node(ctx, node_type='OUTCOME', node_subtype='kpi_decline',
                   title='Jul 31: KPI metrics declining below threshold outcome',  # suffix
                   revenue_impact=None,  # narrative-only
                   occurred_at=day)
        db.session.commit()
        violations = run_invariant('I15', ctx['customer_id'])
        assert len(violations) == 1
        assert 'Wizard A template duplicate' in violations[0].message
        assert violations[0].severity == 'warning'
        assert violations[0].details['signal_count'] == 1
        assert violations[0].details['narrative_outcome_count'] == 1


# ═════════════════════════════════════════════════════════════════════
# Registry coverage — every registered invariant has at least one test
# ═════════════════════════════════════════════════════════════════════


def test_registry_every_invariant_has_clean_and_dirty_tests():
    """Meta-test: make sure we don't ship a new invariant without tests."""
    covered = set()
    import inspect
    for name, fn in inspect.getmembers(sys.modules[__name__]):
        if not name.startswith('test_i'):
            continue
        inv = name.split('_')[1].upper()  # test_i1_clean → I1
        covered.add(inv)
    missing = set(INVARIANTS_REGISTRY) - covered
    # I6 is optional (churned-no-future-expansion needs timing fixtures that
    # are expensive to set up; covered via manual audit for now)
    missing.discard('I6')
    assert not missing, f'Invariants without tests: {sorted(missing)}'


def test_run_all_invariants_returns_list(ctx):
    """Smoke test: run_all_invariants doesn't crash on an empty-ish tenant."""
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        result = run_all_invariants(ctx['customer_id'])
        assert isinstance(result, list)


# ═════════════════════════════════════════════════════════════════════
# I7 — MCP tool signature contract (pure code check, no DB needed)
# ═════════════════════════════════════════════════════════════════════


def test_i7_mcp_tool_signatures_match_underlying_functions():
    """I7: MCP wrappers pass only kwargs the underlying function accepts.

    Catches the April 2026 bug where get_causal_chain wrapper passed
    customer_id= but the underlying function signature didn't accept it,
    producing a runtime TypeError wrapped as an MCP validator error.
    """
    import inspect as _inspect

    # (wrapper_call_kwargs, underlying_function)
    from utils.context_graph import get_causal_chain as _gc_chain
    from utils.context_graph import get_account_graph_summary as _gc_summary

    contracts = [
        # get_causal_chain MCP tool passes these kwargs:
        ({'node_id', 'direction', 'max_depth', 'customer_id'}, _gc_chain),
        # get_account_graph_summary is a simpler call:
        ({'account_id'}, _gc_summary),
    ]

    for expected_kwargs, fn in contracts:
        sig = _inspect.signature(fn)
        accepted = set(sig.parameters.keys())
        missing = expected_kwargs - accepted
        assert not missing, (
            f'MCP wrapper passes {sorted(missing)} to {fn.__name__} '
            f'but function signature only accepts {sorted(accepted)}'
        )


# ═════════════════════════════════════════════════════════════════════
# I3' — Unearned-confidence clamp (pre-commit OUTCOME write-time)
# Not an invariant in INVARIANTS_REGISTRY (it's a mutation hook, not a
# post-hoc detector). Tested here because it's the write-time counterpart
# to I3 and shares the same provenance-verification semantic.
# ═════════════════════════════════════════════════════════════════════


def test_unearned_clamp_outcome_no_evidence_is_clamped():
    """OUTCOME with no evidence and no source_ref → confidence 0.3, tier 2."""
    from utils.context_graph_invariants import clamp_unearned_confidence
    conf, props, tier, clamped = clamp_unearned_confidence(
        node_type='OUTCOME',
        source_platform='csv_import',
        source_ref=None,
        confidence=1.0,
        properties={},
        tier=1,
    )
    assert clamped is True
    assert conf == 0.3
    assert tier == 2
    assert props.get('evidence_clamped') is True


def test_unearned_clamp_outcome_with_evidence_passes_through():
    """OUTCOME with non-empty properties.evidence → unchanged."""
    from utils.context_graph_invariants import clamp_unearned_confidence
    conf, props, tier, clamped = clamp_unearned_confidence(
        node_type='OUTCOME',
        source_platform='llm_enrichment',
        source_ref=None,
        confidence=0.87,
        properties={'evidence': 'support ticket ST-4891 cites champion departure 2026-03-14'},
        tier=1,
    )
    assert clamped is False
    assert conf == 0.87
    assert tier == 1
    assert 'evidence_clamped' not in props


def test_unearned_clamp_outcome_with_source_ref_passes_through():
    """OUTCOME with specific source_ref (e.g. SFDC Opp ID) → unchanged."""
    from utils.context_graph_invariants import clamp_unearned_confidence
    conf, props, tier, clamped = clamp_unearned_confidence(
        node_type='OUTCOME',
        source_platform='csv_import',
        source_ref='sfdc_opp:006x000000ABC',
        confidence=1.0,
        properties={},
        tier=1,
    )
    assert clamped is False
    assert conf == 1.0
    assert tier == 1


def test_unearned_clamp_signal_not_clamped():
    """Non-OUTCOME nodes pass through regardless of evidence."""
    from utils.context_graph_invariants import clamp_unearned_confidence
    conf, props, tier, clamped = clamp_unearned_confidence(
        node_type='SIGNAL',
        source_platform='csv_import',
        source_ref=None,
        confidence=1.0,
        properties={},
        tier=1,
    )
    assert clamped is False
    assert conf == 1.0
    assert tier == 1


def test_unearned_clamp_empty_evidence_string_still_clamps():
    """Empty/whitespace-only evidence string is treated as no evidence."""
    from utils.context_graph_invariants import clamp_unearned_confidence
    for ev in ('', '   ', None):
        _, _, _, clamped = clamp_unearned_confidence(
            node_type='OUTCOME',
            source_platform='csv_import',
            source_ref=None,
            confidence=1.0,
            properties={'evidence': ev} if ev is not None else {},
            tier=1,
        )
        assert clamped is True, f'Expected clamp for evidence={ev!r}'


def test_unearned_clamp_evidence_list_recognised():
    """evidence_list (plural) with content is also recognised as evidence."""
    from utils.context_graph_invariants import clamp_unearned_confidence
    _, _, _, clamped = clamp_unearned_confidence(
        node_type='OUTCOME',
        source_platform='csv_import',
        source_ref=None,
        confidence=1.0,
        properties={'evidence_list': ['ticket ST-4891', 'email thread 2026-03-14']},
        tier=1,
    )
    assert clamped is False


def test_unearned_clamp_caps_existing_low_confidence():
    """If caller passes confidence below the floor, the clamp does not raise it."""
    from utils.context_graph_invariants import clamp_unearned_confidence
    conf, _, _, clamped = clamp_unearned_confidence(
        node_type='OUTCOME',
        source_platform='csv_import',
        source_ref=None,
        confidence=0.15,  # already below the 0.3 floor
        properties={},
        tier=1,
    )
    assert clamped is True
    assert conf == 0.15  # capped at min(0.15, 0.3) = 0.15, not raised to 0.3


def test_upsert_node_applies_unearned_clamp_on_outcome(ctx):
    """Integration: upsert_node with OUTCOME + no evidence → DB row shows clamp."""
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        from utils.context_graph import upsert_node
        node = upsert_node(
            customer_id=ctx['customer_id'],
            account_id=ctx['account_id'],
            node_type='OUTCOME',
            title='Renewal Secured — $50K',
            occurred_at=datetime(2026, 3, 22, 10, 0, 0),
            properties={},  # empty evidence
            source_platform='csv_import',
            source_event_id='outcome:renewal_secured',
            node_subtype='renewal_secured',
            revenue_impact=50000,
            revenue_impact_type='protected',
            confidence=1.0,
            tier=1,
        )
        db.session.commit()
        assert float(node.confidence) == 0.3
        assert node.tier == 2
        assert node.properties.get('evidence_clamped') is True


def test_mod004_revenue_filter_excludes_unearned_outcomes(ctx):
    """get_revenue_at_risk confidence>=0.5 filter: unearned clamped nodes (0.3) are excluded."""
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        from utils.context_graph import upsert_node, get_revenue_at_risk

        # Earned outcome — has evidence, confidence=0.87, should count
        upsert_node(
            customer_id=ctx['customer_id'],
            account_id=ctx['account_id'],
            node_type='OUTCOME',
            title='Churn Averted — $200K (earned)',
            occurred_at=datetime(2026, 3, 15, 10, 0, 0),
            properties={'evidence': 'ticket ST-12 + exec meeting 2026-03-14'},
            source_platform='llm_enrichment',
            source_event_id='earned_001',
            node_subtype='churn_averted',
            revenue_impact=200000,
            revenue_impact_type='protected',
            confidence=0.87,
            tier=1,
        )
        # Unearned outcome — no evidence, will be clamped to 0.3
        upsert_node(
            customer_id=ctx['customer_id'],
            account_id=ctx['account_id'],
            node_type='OUTCOME',
            title='Renewal Secured — $50K (unearned)',
            occurred_at=datetime(2026, 3, 22, 10, 0, 0),
            properties={},
            source_platform='csv_import',
            source_event_id='outcome:renewal_secured',
            node_subtype='renewal_secured',
            revenue_impact=50000,
            revenue_impact_type='protected',
            confidence=1.0,
            tier=1,
        )
        db.session.commit()

        result = get_revenue_at_risk(ctx['account_id'])
        # Protected should include only the earned $200K, NOT the clamped $50K
        # (87% confidence applied in existing logic: 200000 * 0.87 = 174000)
        assert result['protected'] > 0, 'Earned outcome should contribute'
        assert result['protected'] < 250000, 'Unearned $50K must not contribute'
        # Specifically: with de-duplication on, exactly 1 amount in bucket.
        assert round(result['protected']) == round(200000 * 0.87), (
            f"Expected protected = 200K*0.87 (earned only), got {result['protected']}"
        )
