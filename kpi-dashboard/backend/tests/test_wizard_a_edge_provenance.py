"""
WS-1.1 regression guard — wizard_a_journey_db's TRIGGERED edge writer
(edge-provenance work, Aug 2026).

The journey builder's arc-detection path wrote ContextEdge rows through a
raw constructor with NO source_platform — 724 NULL-source rows accumulated
Apr–Aug 2026 (an active writer, not migration debris) — and only a
free-text label, bypassing the I1/I2/I4 pre-commit invariant gate that the
sibling path (utils/arc_edge_generator.py) already routes through via
upsert_edge().

These are source-level structural guards (AST), same convention as
test_vertical_catalog_consistency.py — no DB needed, and they can't pass
by accident while a raw constructor still exists in the file.

WS-2 2f/2g scoping (docs/WS2_2F_2G_SCOPING.md §3 Q3, decided 2026-08-27):
wizard_a is one of the 4 known inferred-tier writers that constructed its
properties dict with no `evidence_tier` key at all, relying on I3'-E's
absent-key-treated-as-inferred fallback. This file's TRIGGERED-edge writer
now stamps `evidence_tier=INFERRED` explicitly (imported from
utils.provenance, never a hand-typed literal) — the tests below guard that.
"""
import ast
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

WIZARD_A_JOURNEY = BACKEND / "wizards" / "wizard_a_journey_db.py"


def _tree():
    return ast.parse(WIZARD_A_JOURNEY.read_text())


def test_no_raw_context_edge_constructor_remains():
    """No `ContextEdge(...)` call anywhere in the journey builder — every
    edge write must route through upsert_edge (the one sanctioned path,
    which enforces source_platform and the invariant gate)."""
    raw_calls = [
        node.lineno for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == 'ContextEdge'
    ]
    assert not raw_calls, (
        f"raw ContextEdge constructor call(s) at line(s) {raw_calls} — "
        f"route through utils.context_graph.upsert_edge instead (WS-1.1)"
    )


def _upsert_edge_calls():
    return [
        node for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == 'upsert_edge'
    ]


def test_upsert_edge_call_sets_source_platform_and_derivation():
    calls = _upsert_edge_calls()
    assert calls, "expected at least one upsert_edge call in wizard_a_journey_db"
    for call in calls:
        kwargs = {kw.arg: kw.value for kw in call.keywords if kw.arg}
        assert 'source_platform' in kwargs, (
            f"upsert_edge at line {call.lineno} missing source_platform"
        )
        sp = kwargs['source_platform']
        assert isinstance(sp, ast.Constant) and sp.value == 'wizard_a', (
            f"upsert_edge at line {call.lineno}: source_platform must be the "
            f"literal 'wizard_a'"
        )
        props = kwargs.get('properties')
        assert isinstance(props, ast.Dict), (
            f"upsert_edge at line {call.lineno} must pass a literal properties dict"
        )
        prop_keys = {
            k.value for k in props.keys
            if isinstance(k, ast.Constant)
        }
        for required in ('arc_type', 'derivation', 'confidence_semantics', 'evidence_tier'):
            assert required in prop_keys, (
                f"upsert_edge at line {call.lineno}: properties missing "
                f"{required!r} — structured derivation is the point of WS-1.1, "
                f"a bare free-text label was the defect"
            )


def test_confidence_semantics_marks_rule_match_not_epistemic():
    """WS-1.2: the value written into edge confidence originates in
    _classify_trajectory_with_confidence's rule-match scoring (base +
    delta/20, clamped), not an epistemic estimate of the causal claim.
    The properties must say so, so downstream consumers stop reading it
    as calibrated."""
    src = WIZARD_A_JOURNEY.read_text()
    assert "'confidence_semantics': 'trajectory_rule_match_score'" in src


# ─────────────────────────────────────────────────────────────────────
# WS-2 2f/2g §3 Q3 — evidence_tier stamped explicitly, from the canonical
# constant (not a second hand-typed literal that could drift).
# ─────────────────────────────────────────────────────────────────────

def test_imports_inferred_constant_from_provenance():
    src = WIZARD_A_JOURNEY.read_text()
    assert 'from utils.provenance import INFERRED' in src, (
        "wizard_a_journey_db must import INFERRED from utils.provenance "
        "rather than hardcoding the string 'inferred'"
    )


def test_evidence_tier_value_is_the_imported_constant_not_a_literal():
    """The properties dict must reference the INFERRED name, not a
    hand-typed 'inferred' string literal — guards against vocabulary drift
    per the task's explicit ground rule."""
    calls = _upsert_edge_calls()
    assert calls, "expected at least one upsert_edge call in wizard_a_journey_db"
    for call in calls:
        kwargs = {kw.arg: kw.value for kw in call.keywords if kw.arg}
        props = kwargs.get('properties')
        assert isinstance(props, ast.Dict)
        evidence_tier_value = None
        for k, v in zip(props.keys, props.values):
            if isinstance(k, ast.Constant) and k.value == 'evidence_tier':
                evidence_tier_value = v
        assert evidence_tier_value is not None, (
            f"upsert_edge at line {call.lineno}: properties missing 'evidence_tier'"
        )
        assert isinstance(evidence_tier_value, ast.Name) and evidence_tier_value.id == 'INFERRED', (
            f"upsert_edge at line {call.lineno}: evidence_tier must be the "
            f"imported INFERRED constant, not a hardcoded literal"
        )


def _assert_isolated_test_db(uri: str) -> None:
    """Same guard as tests/test_context_graph_invariants.py — this fixture
    calls db.drop_all() on teardown and must never run against a
    non-test database (feedback_destructive_test_fixture.md)."""
    if os.environ.get('ALLOW_DESTRUCTIVE_TEST_DB') == '1':
        return
    db_name = uri.rsplit('/', 1)[-1].split('?', 1)[0]
    if 'test' not in db_name.lower():
        raise RuntimeError(
            f"test_wizard_a_edge_provenance.py refuses to run db.drop_all() "
            f"against database {db_name!r} — its name doesn't contain 'test'."
        )


@pytest.fixture(scope='module')
def ctx():
    from app_v3_minimal import app, db
    from models import Account, Customer

    app.config['TESTING'] = True
    db_uri = os.environ.get(
        'DATABASE_URL', 'postgresql://manojgupta@localhost:5432/cs_pulse_test'
    )
    _assert_isolated_test_db(db_uri)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    with app.app_context():
        db.create_all()
        unique_email = f'wizard_a_prov_{uuid.uuid4().hex[:8]}@test.com'
        customer = Customer(customer_name='Wizard A Provenance Test Co', email=unique_email)
        db.session.add(customer)
        db.session.commit()

        acct = Account(
            customer_id=customer.customer_id,
            account_name='Test Account',
            revenue=1_000_000,
            external_account_id='WIZA-PROV-001',
            account_status='active',
        )
        db.session.add(acct)
        db.session.commit()

        yield {'customer_id': customer.customer_id, 'account_id': acct.account_id}

        db.session.remove()
        db.drop_all()


class TestFreshWizardAEdgeCarriesInferredTier:
    def test_fresh_triggered_edge_stamped_inferred(self, ctx):
        """Reproduces exactly what wizard_a_journey_db.py's arc-detection
        path does for a new TRIGGERED edge: call upsert_edge with the same
        properties shape (including evidence_tier=INFERRED) and confirm it
        persists as 'inferred', not absent."""
        from app_v3_minimal import db
        from models import ContextNode
        from utils.context_graph import upsert_edge
        from utils.provenance import INFERRED

        sig = ContextNode(
            customer_id=ctx['customer_id'],
            account_id=ctx['account_id'],
            node_type='SIGNAL',
            source='observed',
            title='Test signal',
            occurred_at=datetime(2026, 1, 1),
        )
        arc_node = ContextNode(
            customer_id=ctx['customer_id'],
            account_id=ctx['account_id'],
            node_type='SIGNAL',
            source='synthetic',
            node_subtype='arc_detection',
            title='Arc Detected: test_pattern',
            occurred_at=datetime(2026, 1, 1),
        )
        db.session.add_all([sig, arc_node])
        db.session.commit()

        edge, created = upsert_edge(
            from_node_id=sig.node_id,
            to_node_id=arc_node.node_id,
            edge_type='TRIGGERED',
            confidence=0.65,
            properties={
                'label': 'Signal pattern triggered test_pattern arc classification',
                'arc_type': 'test_pattern',
                'arc_phase': 'onset',
                'derivation': 'wizard_a.trajectory_pattern',
                'confidence_semantics': 'trajectory_rule_match_score',
                'evidence_tier': INFERRED,
            },
            source_platform='wizard_a',
            created_by='wizard_a_journey',
            customer_id=ctx['customer_id'],
        )
        assert created is True

        reloaded = db.session.get(type(edge), edge.edge_id)
        assert reloaded.properties['evidence_tier'] == 'inferred'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
