"""
Edge supersession (WS-2 2g).

Covers the tier-ordering / writer-priority decision in
utils/supersession.py, its write-time hook inside upsert_edge()
(utils/context_graph.py), and its retirement from get_causal_chain().

Run against a dedicated postgres test DB (create once: createdb cs_pulse_test)
    DATABASE_URL="postgresql://manojgupta@localhost:5432/cs_pulse_test" \\
        python3 -m pytest tests/test_edge_supersession.py -v
"""

import os
import sys
import uuid
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app, db
from models import Account, ContextEdge, ContextNode, Customer
from utils.context_graph import get_causal_chain, upsert_edge
from utils.supersession import (
    INFERRED,
    INFERRED_TIER_WRITER_PRIORITY,
    OBSERVED,
    apply_supersession,
    resolve_evidence_tier,
    should_supersede,
)


# ═════════════════════════════════════════════════════════════════════
# Fixtures — same convention as tests/test_context_graph_invariants.py
# ═════════════════════════════════════════════════════════════════════


def _assert_isolated_test_db(uri: str) -> None:
    """Guard against running this suite's db.drop_all() teardown against a
    real database. See tests/test_context_graph_invariants.py for the
    incident history behind this guard."""
    if os.environ.get('ALLOW_DESTRUCTIVE_TEST_DB') == '1':
        return
    db_name = uri.rsplit('/', 1)[-1].split('?', 1)[0]
    if 'test' not in db_name.lower():
        raise RuntimeError(
            f"test_edge_supersession.py refuses to run db.drop_all() "
            f"against database {db_name!r} — its name doesn't contain "
            f"'test'. Point DATABASE_URL at a dedicated test database "
            f"(e.g. cs_pulse_test), or set ALLOW_DESTRUCTIVE_TEST_DB=1 if "
            f"you are certain this is safe to wipe."
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
        unique_email = f'supersession_{uuid.uuid4().hex[:8]}@test.com'
        customer = Customer(customer_name='Supersession Test Co', email=unique_email)
        db.session.add(customer)
        db.session.commit()

        acct = Account(
            customer_id=customer.customer_id,
            account_name='Test Account',
            revenue=1_000_000,
            external_account_id='SUP-001',
            account_status='active',
        )
        db.session.add(acct)
        db.session.commit()

        yield {'customer_id': customer.customer_id, 'account_id': acct.account_id}

        db.session.remove()
        db.drop_all()


def _clear_graph(customer_id: int):
    ContextEdge.query.filter_by(customer_id=customer_id).delete()
    ContextNode.query.filter_by(customer_id=customer_id).delete()
    db.session.commit()


def _make_signal_outcome_pair(ctx):
    """A SIGNAL->OUTCOME node pair that passes I1/I2/I17 for any LED_TO
    edge drawn between them (same polarity, same occurred_at — mirrors
    test_context_graph_invariants.py's test_i2_clean fixture shape)."""
    occurred = datetime(2026, 1, 1)
    s = ContextNode(
        customer_id=ctx['customer_id'],
        account_id=ctx['account_id'],
        node_type='SIGNAL',
        node_subtype='escalation',
        title='Escalation signal',
        occurred_at=occurred,
        source='test',
        source_platform='test',
        tier=1,
    )
    o = ContextNode(
        customer_id=ctx['customer_id'],
        account_id=ctx['account_id'],
        node_type='OUTCOME',
        node_subtype='churn_lost',
        title='Churn outcome',
        occurred_at=occurred,
        revenue_impact=-100_000,
        revenue_impact_type='lost',
        source='test',
        source_platform='test',
        tier=1,
    )
    db.session.add_all([s, o])
    db.session.flush()
    return s, o


def _raw_edge(ctx, from_node, to_node, *, source_platform, evidence_tier=None, edge_id_hint=None):
    """Construct a ContextEdge directly (bypassing upsert_edge) to seed a
    pre-existing row for tests that need two rows sharing the exact same
    (from,to,edge_type,source_platform) dedup key — a state upsert_edge's
    own dedup never produces on its own (see test 5 below)."""
    props = {}
    if evidence_tier is not None:
        props['evidence_tier'] = evidence_tier
    e = ContextEdge(
        customer_id=ctx['customer_id'],
        from_node_id=from_node.node_id,
        to_node_id=to_node.node_id,
        edge_type='LED_TO',
        confidence=None,
        source_platform=source_platform,
        created_by=source_platform,
        properties=props,
    )
    db.session.add(e)
    db.session.flush()
    return e


# ═════════════════════════════════════════════════════════════════════
# Pure decision function — utils.supersession.should_supersede
# ═════════════════════════════════════════════════════════════════════


def test_resolve_evidence_tier_absent_key_treated_as_inferred():
    """This implementation's own extension (not a verbatim 2g decision —
    see utils/supersession.py module docstring): an edge with no
    evidence_tier key at all resolves to `inferred` for ranking."""
    assert resolve_evidence_tier(None) == INFERRED
    assert resolve_evidence_tier({}) == INFERRED
    assert resolve_evidence_tier({'derivation': 'system.self.x'}) == INFERRED
    assert resolve_evidence_tier({'evidence_tier': 'observed'}) == OBSERVED


def test_should_supersede_cross_tier_strictly_higher_only():
    assert should_supersede(
        existing_tier='inferred', existing_platform='wizard_a',
        incoming_tier='observed', incoming_platform='csv_import',
    ) is True
    assert should_supersede(
        existing_tier='observed', existing_platform='csv_import',
        incoming_tier='inferred', incoming_platform='wizard_a',
    ) is False
    assert should_supersede(
        existing_tier='asserted', existing_platform='csm_manual',
        incoming_tier='observed', incoming_platform='csv_import',
    ) is True
    assert should_supersede(
        existing_tier='unknown', existing_platform='legacy',
        incoming_tier='inferred', incoming_platform='wizard_a',
    ) is True


# ═════════════════════════════════════════════════════════════════════
# 1. Cross-tier: observed supersedes inferred
# ═════════════════════════════════════════════════════════════════════


def test_observed_supersedes_existing_inferred(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s, o = _make_signal_outcome_pair(ctx)

        old_edge, created = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=None, source_platform='wizard_a', created_by='wizard_a',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'inferred', 'derivation': 'system.self.template'},
        )
        db.session.commit()
        assert created is True
        assert old_edge.superseded_by is None

        new_edge, created2 = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=1.0, source_platform='csv_import', created_by='csv_import',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'observed'},
        )
        db.session.commit()
        assert created2 is True

        refreshed_old = db.session.get(ContextEdge, old_edge.edge_id)
        assert refreshed_old.superseded_by == new_edge.edge_id
        assert new_edge.superseded_by is None


# ═════════════════════════════════════════════════════════════════════
# 2. Wrong direction: inferred does NOT supersede existing observed
# ═════════════════════════════════════════════════════════════════════


def test_inferred_does_not_supersede_existing_observed(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s, o = _make_signal_outcome_pair(ctx)

        old_edge, created = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=1.0, source_platform='csv_import', created_by='csv_import',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'observed'},
        )
        db.session.commit()
        assert created is True

        new_edge, created2 = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=None, source_platform='wizard_a', created_by='wizard_a',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'inferred'},
        )
        db.session.commit()
        assert created2 is True

        refreshed_old = db.session.get(ContextEdge, old_edge.edge_id)
        refreshed_new = db.session.get(ContextEdge, new_edge.edge_id)
        assert refreshed_old.superseded_by is None, "observed edge must not be retired by a weaker arrival"
        assert refreshed_new.superseded_by is None, "wrong direction must not fire at all — both stay live"


# ═════════════════════════════════════════════════════════════════════
# 3. Writer priority within `inferred`: llm_enrichment > wizard_a,
#    regardless of arrival order
# ═════════════════════════════════════════════════════════════════════


def test_llm_enrichment_beats_wizard_a_when_wizard_a_first(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s, o = _make_signal_outcome_pair(ctx)

        wa_edge, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=None, source_platform='wizard_a', created_by='wizard_a',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'inferred'},
        )
        db.session.commit()

        llm_edge, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=None, source_platform='llm_enrichment', created_by='llm_enrichment',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'inferred'},
        )
        db.session.commit()

        assert db.session.get(ContextEdge, wa_edge.edge_id).superseded_by == llm_edge.edge_id
        assert db.session.get(ContextEdge, llm_edge.edge_id).superseded_by is None


def test_llm_enrichment_beats_wizard_a_when_llm_first(ctx):
    """Same pair, opposite arrival order — the outcome must be identical:
    llm_enrichment live, wizard_a superseded. Writer-priority is
    identity-based, not arrival-order-based."""
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s, o = _make_signal_outcome_pair(ctx)

        llm_edge, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=None, source_platform='llm_enrichment', created_by='llm_enrichment',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'inferred'},
        )
        db.session.commit()

        wa_edge, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=None, source_platform='wizard_a', created_by='wizard_a',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'inferred'},
        )
        db.session.commit()

        # wizard_a arrived SECOND here, yet must still end up superseded —
        # it is born superseded by the pre-existing, higher-priority
        # llm_enrichment edge.
        assert db.session.get(ContextEdge, wa_edge.edge_id).superseded_by == llm_edge.edge_id
        assert db.session.get(ContextEdge, llm_edge.edge_id).superseded_by is None


def test_priority_list_is_llm_enrichment_then_wizard_a():
    """Guard the documented first-pass ranking itself, so a reordering is
    a deliberate diff, not an accident."""
    assert INFERRED_TIER_WRITER_PRIORITY.index('llm_enrichment') < \
        INFERRED_TIER_WRITER_PRIORITY.index('wizard_a')


# ═════════════════════════════════════════════════════════════════════
# 4. Unranked writer pair — neither supersedes (fail safe)
# ═════════════════════════════════════════════════════════════════════


def test_unranked_writer_pair_neither_supersedes(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s, o = _make_signal_outcome_pair(ctx)

        first_edge, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=None, source_platform='signal_analyst', created_by='signal_analyst',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'inferred'},
        )
        db.session.commit()

        second_edge, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=None, source_platform='urgent_signal_scanner', created_by='urgent_signal_scanner',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'inferred'},
        )
        db.session.commit()

        assert db.session.get(ContextEdge, first_edge.edge_id).superseded_by is None
        assert db.session.get(ContextEdge, second_edge.edge_id).superseded_by is None


def test_one_ranked_one_unranked_writer_neither_supersedes(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s, o = _make_signal_outcome_pair(ctx)

        wa_edge, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=None, source_platform='wizard_a', created_by='wizard_a',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'inferred'},
        )
        db.session.commit()

        auto_linker_edge, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=None, source_platform='auto_linker', created_by='auto_linker',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'inferred'},
        )
        db.session.commit()

        assert db.session.get(ContextEdge, wa_edge.edge_id).superseded_by is None
        assert db.session.get(ContextEdge, auto_linker_edge.edge_id).superseded_by is None


# ═════════════════════════════════════════════════════════════════════
# 5. Same writer, same tier, re-firing — recency wins
#
# NOTE: upsert_edge()'s own dedup key is (from_node_id, to_node_id,
# edge_type, source_platform) — identical to what a same-writer re-fire on
# the same triple would match. That existing dedup logic (unchanged by
# 2g, and deliberately not touched by supersession's own separate,
# looser match key) always finds and updates that one row in place, so a
# real same-writer re-fire through upsert_edge never produces two
# separate rows for supersession to act on in the first place. This test
# therefore exercises the mechanism directly — apply_supersession() — the
# same function upsert_edge calls, against two rows seeded to simulate a
# pre-existing duplicate (e.g. legacy data predating this fix).
# ═════════════════════════════════════════════════════════════════════


def test_same_writer_same_tier_refire_recency_wins(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s, o = _make_signal_outcome_pair(ctx)

        older = _raw_edge(ctx, s, o, source_platform='wizard_a', evidence_tier='inferred')
        newer = _raw_edge(ctx, s, o, source_platform='wizard_a', evidence_tier='inferred')
        db.session.commit()

        apply_supersession(newer)
        db.session.commit()

        assert db.session.get(ContextEdge, older.edge_id).superseded_by == newer.edge_id
        assert db.session.get(ContextEdge, newer.edge_id).superseded_by is None


# ═════════════════════════════════════════════════════════════════════
# 6. observed/asserted ties do NOT auto-resolve
# ═════════════════════════════════════════════════════════════════════


def test_two_observed_tier_edges_neither_supersedes(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s, o = _make_signal_outcome_pair(ctx)

        crm_edge, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=1.0, source_platform='crm_sync', created_by='crm_sync',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'observed'},
        )
        db.session.commit()

        csv_edge, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=1.0, source_platform='csv_import', created_by='csv_import',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'observed'},
        )
        db.session.commit()

        assert db.session.get(ContextEdge, crm_edge.edge_id).superseded_by is None
        assert db.session.get(ContextEdge, csv_edge.edge_id).superseded_by is None


def test_two_asserted_tier_edges_neither_supersedes(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s, o = _make_signal_outcome_pair(ctx)

        first, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=0.9, source_platform='csm_manual_a', created_by='csm_manual_a',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'asserted'},
        )
        db.session.commit()

        second, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=0.9, source_platform='csm_manual_b', created_by='csm_manual_b',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'asserted'},
        )
        db.session.commit()

        assert db.session.get(ContextEdge, first.edge_id).superseded_by is None
        assert db.session.get(ContextEdge, second.edge_id).superseded_by is None


# ═════════════════════════════════════════════════════════════════════
# 7. get_causal_chain() retirement — excludes superseded edges
# ═════════════════════════════════════════════════════════════════════


def test_get_causal_chain_excludes_superseded_edge(ctx):
    with app.app_context():
        _clear_graph(ctx['customer_id'])
        s, o = _make_signal_outcome_pair(ctx)

        old_edge, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=None, source_platform='wizard_a', created_by='wizard_a',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'inferred'},
        )
        db.session.commit()

        new_edge, _ = upsert_edge(
            from_node_id=s.node_id, to_node_id=o.node_id, edge_type='LED_TO',
            confidence=1.0, source_platform='csv_import', created_by='csv_import',
            customer_id=ctx['customer_id'],
            properties={'evidence_tier': 'observed'},
        )
        db.session.commit()

        assert db.session.get(ContextEdge, old_edge.edge_id).superseded_by == new_edge.edge_id

        chain = get_causal_chain(o.node_id, direction='upstream', customer_id=ctx['customer_id'])

        # Only the live (observed) edge should surface node `s` — not twice,
        # and not via the superseded wizard_a edge.
        matching = [c for c in chain if c['node']['node_id'] == s.node_id]
        assert len(matching) == 1, f"expected node {s.node_id} exactly once, got {matching}"
        assert matching[0]['edge']['edge_id'] == new_edge.edge_id


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
