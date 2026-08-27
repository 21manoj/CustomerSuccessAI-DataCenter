"""
WS-2 2f/2g follow-up (docs/WS2_2F_2G_SCOPING.md §3 Q3, decided 2026-08-27).

Confirmed via exhaustive grep that 4 known inferred-tier edge writers built
their `properties` dict with no `evidence_tier` key at all, relying entirely
on I3'-E's absent-key-treated-as-inferred fallback:

  1. wizards/wizard_a_journey_db.py        — see tests/test_wizard_a_edge_provenance.py
  2. llm/tier1_inference.py                — covered here
  3. utils/signal_analyst.py               — covered here
  4. utils/urgent_signal_scanner.py        — covered here

This file covers writers 2-4: each now stamps `evidence_tier=INFERRED`
(imported from utils.provenance — never a hand-typed literal) at every
upsert_edge/ContextEdge call site. Forward-only: no backfill of existing
rows, no change to how I3'-E/apply_supersession consume the tag.

Two layers per writer:
  1. Static source checks — cheap, no DB — that the writer imports and uses
     the canonical INFERRED constant at every edge-properties call site
     (same convention as tests/test_csv_import_edge_provenance.py).
  2. A DB round-trip proving a freshly-written edge from that writer's real
     code path (or an exact reproduction of its properties shape, where the
     writer's entry point requires heavier mocking like an LLM call)
     actually persists evidence_tier='inferred'.

Run against a dedicated postgres test DB:
    DATABASE_URL="postgresql://manojgupta@localhost:5432/cs_pulse_test" \\
        python3 -m pytest tests/test_evidence_tier_stamping.py -v
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BACKEND = Path(__file__).resolve().parent.parent
TIER1_INFERENCE = BACKEND / 'llm' / 'tier1_inference.py'
SIGNAL_ANALYST = BACKEND / 'utils' / 'signal_analyst.py'
URGENT_SIGNAL_SCANNER = BACKEND / 'utils' / 'urgent_signal_scanner.py'


# ═════════════════════════════════════════════════════════════════════
# 1. Static source checks — no DB.
# ═════════════════════════════════════════════════════════════════════

class TestWritersImportCanonicalConstant:
    def test_tier1_inference_imports_inferred(self):
        src = TIER1_INFERENCE.read_text()
        assert 'from utils.provenance import INFERRED' in src

    def test_signal_analyst_imports_inferred(self):
        src = SIGNAL_ANALYST.read_text()
        assert 'from utils.provenance import INFERRED' in src

    def test_urgent_signal_scanner_imports_inferred(self):
        src = URGENT_SIGNAL_SCANNER.read_text()
        assert 'from utils.provenance import INFERRED' in src


class TestEveryEdgePropertiesSiteStampsEvidenceTier:
    """Every `upsert_edge(`/`ContextEdge(` call in these 3 writers must have
    a matching `'evidence_tier': INFERRED` in its properties dict — counts
    must line up so a future call site can't silently skip the stamp."""

    def test_tier1_inference_all_six_call_sites_stamped(self):
        src = TIER1_INFERENCE.read_text()
        call_sites = src.count('upsert_edge(')
        stamped = src.count("'evidence_tier': INFERRED")
        assert call_sites == 6, (
            f"expected 6 upsert_edge call sites in tier1_inference.py, found "
            f"{call_sites} — update this test's expectation if a call site "
            f"was added/removed, but verify the new one is stamped too"
        )
        assert stamped == call_sites, (
            f"tier1_inference.py has {call_sites} upsert_edge call sites but "
            f"only {stamped} stamp evidence_tier=INFERRED"
        )

    def test_signal_analyst_all_five_call_sites_stamped(self):
        src = SIGNAL_ANALYST.read_text()
        call_sites = src.count('ContextEdge(')
        stamped = src.count("'evidence_tier': INFERRED")
        assert call_sites == 5, (
            f"expected 5 ContextEdge call sites in signal_analyst.py, found "
            f"{call_sites} — update this test's expectation if a call site "
            f"was added/removed, but verify the new one is stamped too"
        )
        assert stamped == call_sites, (
            f"signal_analyst.py has {call_sites} ContextEdge call sites but "
            f"only {stamped} stamp evidence_tier=INFERRED"
        )

    def test_urgent_signal_scanner_both_call_sites_stamped(self):
        src = URGENT_SIGNAL_SCANNER.read_text()
        call_sites = src.count('ContextEdge(')
        stamped = src.count("'evidence_tier': INFERRED")
        assert call_sites == 2, (
            f"expected 2 ContextEdge call sites in urgent_signal_scanner.py, "
            f"found {call_sites} — update this test's expectation if a call "
            f"site was added/removed, but verify the new one is stamped too"
        )
        assert stamped == call_sites, (
            f"urgent_signal_scanner.py has {call_sites} ContextEdge call "
            f"sites but only {stamped} stamp evidence_tier=INFERRED"
        )


# ═════════════════════════════════════════════════════════════════════
# 2. DB round-trip — a freshly-written edge from each writer's real code
#    (or an exact reproduction of its properties shape) persists
#    evidence_tier='inferred'.
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
            f"test_evidence_tier_stamping.py refuses to run db.drop_all() "
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
        unique_email = f'evtier_{uuid.uuid4().hex[:8]}@test.com'
        customer = Customer(customer_name='Evidence Tier Test Co', email=unique_email)
        db.session.add(customer)
        db.session.commit()

        acct = Account(
            customer_id=customer.customer_id,
            account_name='Test Account',
            revenue=1_000_000,
            external_account_id='EVTIER-001',
            account_status='active',
        )
        db.session.add(acct)
        db.session.commit()

        yield {'customer_id': customer.customer_id, 'account_id': acct.account_id}

        db.session.remove()
        db.drop_all()


def _make_node(ctx, db, ContextNode, **kwargs):
    defaults = {
        'customer_id': ctx['customer_id'],
        'account_id': ctx['account_id'],
        'node_type': 'SIGNAL',
        'title': 'Test node',
        'source': 'observed',
        'occurred_at': datetime(2026, 1, 1),
    }
    defaults.update(kwargs)
    n = ContextNode(**defaults)
    db.session.add(n)
    db.session.flush()
    return n


class TestTier1InferenceStampsInferredTier:
    def test_write_simple_edges_stamps_inferred(self, ctx):
        """Calls the real _write_simple_edges writer (signal -> decision,
        decision -> outcome) and confirms the persisted edges carry
        evidence_tier='inferred'."""
        from app_v3_minimal import db
        from models import ContextEdge, ContextNode
        from llm.tier1_inference import _write_simple_edges

        sig = _make_node(ctx, db, ContextNode, node_type='SIGNAL', title='Signal')
        dec = _make_node(ctx, db, ContextNode, node_type='DECISION', title='Decision')
        out = _make_node(ctx, db, ContextNode, node_type='OUTCOME', title='Outcome')
        db.session.commit()

        created_node_ids = {
            'signal:0': sig.node_id,
            'decision:0': dec.node_id,
            'outcome:0': out.node_id,
        }
        count = _write_simple_edges(
            ctx['customer_id'], created_node_ids,
            source_platform='llm_enrichment', created_by='llm_enrichment',
            derivation={'derivation': 'system.external'},
        )
        db.session.commit()
        assert count == 2

        edges = ContextEdge.query.filter_by(
            customer_id=ctx['customer_id'], source_platform='llm_enrichment',
        ).all()
        assert edges, "expected at least one persisted edge"
        for e in edges:
            assert e.properties.get('evidence_tier') == 'inferred'

    def test_write_explicit_edges_stamps_inferred(self, ctx):
        """Calls the real _write_explicit_edges writer (edges_only / LLM
        edge-enrichment mode) and confirms the persisted causal_edges and
        signal_to_signal_edges both carry evidence_tier='inferred'."""
        from app_v3_minimal import db
        from models import ContextEdge, ContextNode
        from llm.tier1_inference import _write_explicit_edges

        sig_a = _make_node(ctx, db, ContextNode, node_type='SIGNAL', title='Signal A')
        sig_b = _make_node(ctx, db, ContextNode, node_type='SIGNAL', title='Signal B')
        dec = _make_node(ctx, db, ContextNode, node_type='DECISION', title='Decision')
        out = _make_node(ctx, db, ContextNode, node_type='OUTCOME', title='Outcome')
        db.session.commit()

        created_node_ids = {'decision:0': dec.node_id, 'outcome:0': out.node_id}
        signal_ref_to_node_id = {'sig_a': sig_a.node_id, 'sig_b': sig_b.node_id}
        inference = {
            'causal_edges': [
                {'from_ref': 'sig_a', 'to_ref': 'decision:0', 'edge_type': 'TRIGGERED',
                 'confidence': 0.7, 'label': 'test'},
            ],
            'signal_to_signal_edges': [
                {'from_signal_ref': 'sig_a', 'to_signal_ref': 'sig_b',
                 'edge_type': 'INDICATES', 'confidence': 0.6, 'label': 'test'},
            ],
        }

        count = _write_explicit_edges(
            ctx['customer_id'], inference, created_node_ids, signal_ref_to_node_id,
            source_platform='llm_enrichment', created_by='llm_enrichment',
            derivation={'derivation': 'system.external'},
        )
        db.session.commit()
        assert count == 2

        edges = ContextEdge.query.filter_by(
            customer_id=ctx['customer_id'], source_platform='llm_enrichment',
        ).all()
        assert len(edges) >= 2
        for e in edges:
            assert e.properties.get('evidence_tier') == 'inferred'


class TestSignalAnalystStampsInferredTier:
    def test_fresh_led_to_edge_stamped_inferred(self, ctx):
        """Reproduces exactly what utils/signal_analyst.py's check_and_analyze
        does for a Signal -> AI-insight LED_TO edge: build the properties
        dict the writer now builds (including evidence_tier=INFERRED via the
        canonical constant) and persist it."""
        from app_v3_minimal import db
        from models import ContextEdge, ContextNode
        from utils.provenance import INFERRED

        sig = _make_node(ctx, db, ContextNode, node_type='SIGNAL', title='Signal')
        insight = _make_node(ctx, db, ContextNode, node_type='SIGNAL',
                              node_subtype='ai_insight', title='AI Insight', source='inferred')
        db.session.commit()

        edge = ContextEdge(
            customer_id=ctx['customer_id'],
            from_node_id=sig.node_id,
            to_node_id=insight.node_id,
            edge_type='LED_TO',
            confidence=0.85,
            source_platform='signal_analyst',
            properties={'label': 'Signal led to health drop insight', 'evidence_tier': INFERRED},
        )
        db.session.add(edge)
        db.session.commit()

        reloaded = db.session.get(ContextEdge, edge.edge_id)
        assert reloaded.properties['evidence_tier'] == 'inferred'


class TestUrgentSignalScannerStampsInferredTier:
    def test_fresh_led_to_edge_stamped_inferred(self, ctx):
        """Reproduces exactly what utils/urgent_signal_scanner.py's alert
        writer does for the OUTCOME -> urgent-alert LED_TO edge."""
        from app_v3_minimal import db
        from models import ContextEdge, ContextNode
        from utils.provenance import INFERRED

        out = _make_node(ctx, db, ContextNode, node_type='OUTCOME', title='Revenue at risk')
        alert = _make_node(ctx, db, ContextNode, node_type='SIGNAL',
                            node_subtype='urgent_alert', title='Urgent Alert', source='inferred')
        db.session.commit()

        edge = ContextEdge(
            customer_id=ctx['customer_id'],
            from_node_id=out.node_id,
            to_node_id=alert.node_id,
            edge_type='LED_TO',
            confidence=0.9,
            source_platform='urgent_signal_scanner',
            properties={'label': 'Revenue risk outcome triggered urgent alert', 'evidence_tier': INFERRED},
        )
        db.session.add(edge)
        db.session.commit()

        reloaded = db.session.get(ContextEdge, edge.edge_id)
        assert reloaded.properties['evidence_tier'] == 'inferred'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
