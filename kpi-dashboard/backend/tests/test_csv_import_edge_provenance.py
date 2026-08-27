"""
WS-2 adjudication matrix Hold 2 (signed 2026-08-24) — csv_import edge
provenance regression guard.

Cells 1-3 (csv_import x LED_TO/TRIGGERED/CAUSED_BY) were provisionally
called `asserted`, but held: the platform cannot tell the load-driver from
a human uploader at write time (same API, same credentials class).
Interim resolution: csv-path writers stamp `evidence_tier='unknown'` — the
honest tier for "someone claimed this and we can't say who" — until
Customer.data_origin (WS-2 2a, shipped) is read by this write path and lets
a future pass re-tier by authenticated principal. This is forward-only:
existing rows are never touched.

Two writers produce csv_import causal edges:
  - mcp_server/cs_pulse_onboarding.py's _process_data_impl (the load-driver
    / process_data path — DB-verified as the one that has ever actually
    produced live csv_import rows: all 1,819 carry created_by='process_data')
  - onboarding_api_v2_config_aware.py's ingest_context_graph_csvs (the
    admin-created-tenant / regen-subscriber path)

Both are checked here:
  1. Static source checks — cheap, no DB — that each writer's edge
     properties are built from the canonical utils.provenance.UNKNOWN /
     utils.edge_factory.CSV_IMPORT_DERIVATION constants rather than a
     hand-typed literal that could drift from the vocabulary.
  2. A DB round-trip proving a freshly-written csv_import edge actually
     persists evidence_tier='unknown' (not 'asserted', not NULL), and that
     this representation stays structurally distinct from the quarantine
     representation (NULL source_platform / absent evidence_tier) per the
     Hold 2 follow-up: "they must never share a representation."

Run against a dedicated postgres test DB:
    DATABASE_URL="postgresql://manojgupta@localhost:5432/cs_pulse_test" \\
        python3 -m pytest tests/test_csv_import_edge_provenance.py -v
"""
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app, db
from models import Account, ContextEdge, ContextNode, Customer
from utils.provenance import UNKNOWN, OBSERVED, INFERRED, SYNTHETIC, ALL_SOURCES
from utils.edge_factory import (
    CSV_IMPORT_DERIVATION,
    AUTO_TRIGGER_DERIVATION,
    CLOSE_LINK_DERIVATION,
)

BACKEND = Path(__file__).resolve().parent.parent
CS_PULSE_ONBOARDING = BACKEND / 'mcp_server' / 'cs_pulse_onboarding.py'
ONBOARDING_API_V2 = BACKEND / 'onboarding_api_v2_config_aware.py'


# ═════════════════════════════════════════════════════════════════════
# 1. Vocabulary sanity
# ═════════════════════════════════════════════════════════════════════

class TestUnknownTierVocabulary:
    def test_unknown_is_a_distinct_string(self):
        assert UNKNOWN == 'unknown'

    def test_unknown_not_confused_with_existing_tiers(self):
        assert UNKNOWN not in (OBSERVED, INFERRED, SYNTHETIC)

    def test_unknown_kept_out_of_node_source_vocabulary(self):
        # UNKNOWN is an edge evidence_tier, not a ContextNode.source value —
        # it must not silently widen ALL_SOURCES/TRUSTWORTHY_SOURCES, which
        # would change node-level trustworthy-source filtering (Wizard B/C)
        # as an unintended side effect of this edge-only interim fix.
        assert UNKNOWN not in ALL_SOURCES

    def test_csv_import_derivation_is_distinct(self):
        assert CSV_IMPORT_DERIVATION not in (
            AUTO_TRIGGER_DERIVATION, CLOSE_LINK_DERIVATION,
        )
        # Neither system.self nor system.external — see edge_factory.py
        # docstring / CSV_IMPORT_DERIVATION comment for the reasoning.
        assert not CSV_IMPORT_DERIVATION.startswith('system.')


# ═════════════════════════════════════════════════════════════════════
# 2. Static source checks — the writers must use the constants, not a
#    hand-typed literal that could silently drift.
# ═════════════════════════════════════════════════════════════════════

class TestWritersReferenceCanonicalConstants:
    def test_process_data_impl_signal_edges_writer(self):
        src = CS_PULSE_ONBOARDING.read_text()
        # The signal_edges.csv → ContextEdge block (Steps: "Signal Edges
        # (must run last...)") must import and stamp both constants.
        assert 'from utils.provenance import UNKNOWN' in src
        assert 'from utils.edge_factory import CSV_IMPORT_DERIVATION' in src
        assert "'evidence_tier': _EVIDENCE_TIER_UNKNOWN" in src
        assert "'derivation': _CSV_IMPORT_DERIVATION" in src

    def test_ingest_context_graph_csvs_writer(self):
        src = ONBOARDING_API_V2.read_text()
        assert 'from utils.provenance import UNKNOWN' in src
        assert 'from utils.edge_factory import CSV_IMPORT_DERIVATION' in src
        assert "props['evidence_tier'] = _EVIDENCE_TIER_UNKNOWN" in src
        assert "props['derivation'] = _CSV_IMPORT_DERIVATION" in src
        # Scoped to the three causal-claim edge types the matrix adjudicated.
        assert "edge_type in ('LED_TO', 'TRIGGERED', 'CAUSED_BY')" in src


# ═════════════════════════════════════════════════════════════════════
# 3. DB round-trip — a freshly-written csv_import edge really does carry
#    evidence_tier='unknown', distinct from the quarantine representation.
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
            f"test_csv_import_edge_provenance.py refuses to run db.drop_all() "
            f"against database {db_name!r} — its name doesn't contain 'test'."
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
        unique_email = f'csv_prov_{uuid.uuid4().hex[:8]}@test.com'
        customer = Customer(customer_name='CSV Provenance Test Co', email=unique_email)
        db.session.add(customer)
        db.session.commit()

        acct = Account(
            customer_id=customer.customer_id,
            account_name='Test Account',
            revenue=1_000_000,
            external_account_id='CSVPROV-001',
            account_status='active',
        )
        db.session.add(acct)
        db.session.commit()

        yield {'customer_id': customer.customer_id, 'account_id': acct.account_id}

        db.session.remove()
        db.drop_all()


def _make_node(ctx, **kwargs) -> ContextNode:
    defaults = {
        'customer_id': ctx['customer_id'],
        'account_id': ctx['account_id'],
        'node_type': 'SIGNAL',
        'title': 'Test node',
        'occurred_at': datetime(2026, 1, 1),
        'source': 'observed',
        'source_platform': 'csv_import',
        'tier': 1,
    }
    defaults.update(kwargs)
    n = ContextNode(**defaults)
    db.session.add(n)
    db.session.flush()
    return n


class TestFreshCsvImportEdgeCarriesUnknownTier:
    def test_fresh_csv_import_edge_stamped_unknown(self, ctx):
        """Reproduces exactly what mcp_server/cs_pulse_onboarding.py's
        signal_edges.csv writer does for a new LED_TO edge: build the
        properties dict from the canonical constants and persist it."""
        from_node = _make_node(ctx, node_type='SIGNAL', title='Champion departed')
        to_node = _make_node(ctx, node_type='OUTCOME', title='Renewal at risk')

        edge = ContextEdge(
            customer_id=ctx['customer_id'],
            from_node_id=from_node.node_id,
            to_node_id=to_node.node_id,
            edge_type='LED_TO',
            weight=1.0,
            confidence=1.0,
            source_platform='csv_import',
            created_by='process_data',
            properties={
                'evidence': 'uploaded via signal_edges.csv',
                'evidence_tier': UNKNOWN,
                'derivation': CSV_IMPORT_DERIVATION,
            },
        )
        db.session.add(edge)
        db.session.commit()

        reloaded = db.session.get(ContextEdge, edge.edge_id)
        assert reloaded.properties['evidence_tier'] == 'unknown'
        assert reloaded.properties['evidence_tier'] != 'asserted'
        assert reloaded.properties['derivation'] == 'csv_import.unattributed'
        assert reloaded.source_platform == 'csv_import'

    def test_unknown_tier_distinct_from_quarantine_representation(self, ctx):
        """Hold 2 follow-up: `unknown` (know the path, not the principal)
        must never share a representation with quarantine (NULL source,
        nothing reconstructable) — otherwise the two states blur and the
        NULL-source rows stop being distinguishable from the csv path's
        interim state."""
        from_node = _make_node(ctx, node_type='SIGNAL', title='Signal A')
        to_node = _make_node(ctx, node_type='OUTCOME', title='Outcome A')

        unknown_edge = ContextEdge(
            customer_id=ctx['customer_id'],
            from_node_id=from_node.node_id,
            to_node_id=to_node.node_id,
            edge_type='TRIGGERED',
            weight=1.0,
            confidence=1.0,
            source_platform='csv_import',
            created_by='process_data',
            properties={'evidence_tier': UNKNOWN, 'derivation': CSV_IMPORT_DERIVATION},
        )
        quarantine_edge = ContextEdge(
            customer_id=ctx['customer_id'],
            from_node_id=from_node.node_id,
            to_node_id=to_node.node_id,
            edge_type='CAUSED_BY',
            weight=1.0,
            confidence=1.0,
            source_platform=None,   # the real NULL-source quarantine shape
            created_by=None,
            properties={},          # no evidence_tier at all
        )
        db.session.add_all([unknown_edge, quarantine_edge])
        db.session.commit()

        unknown_reloaded = db.session.get(ContextEdge, unknown_edge.edge_id)
        quarantine_reloaded = db.session.get(ContextEdge, quarantine_edge.edge_id)

        assert unknown_reloaded.properties.get('evidence_tier') == 'unknown'
        assert unknown_reloaded.source_platform == 'csv_import'

        assert quarantine_reloaded.properties.get('evidence_tier') is None
        assert quarantine_reloaded.source_platform is None

        # The two states must be trivially distinguishable by any reader.
        assert (
            unknown_reloaded.properties.get('evidence_tier')
            != quarantine_reloaded.properties.get('evidence_tier')
        )


if __name__ == '__main__':
    import pytest as _pytest
    _pytest.main([__file__, '-v'])
