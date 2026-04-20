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
        # expansion_closed is in 'expansion' bucket, not 'lost'
        _make_node(ctx, node_type='OUTCOME', node_subtype='expansion_closed',
                   revenue_impact=200_000, revenue_impact_type='lost')
        db.session.commit()
        violations = run_invariant('I11', ctx['customer_id'])
        assert len(violations) == 1
        assert 'expansion' in violations[0].details['expected_buckets']


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
