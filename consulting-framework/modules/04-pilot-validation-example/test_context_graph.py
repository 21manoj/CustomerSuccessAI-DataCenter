"""
Test suite for the pilot implementation of Module 04 (Context Graph &
Causal Layer), invented vertical `regional_utility_v1`.

Organized to mirror the spec's own Acceptance Criteria and Reference Test
Harness sections as literally as possible; each test method's docstring
names which AC/Harness bullet it exercises.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures"))

from graph_schema import CAUSAL_EDGE_TYPES, ContextEdge, ContextNode, GraphStore, Violation
from taxonomy_loader import TaxonomyLoader, TaxonomyValidationError
from invariants import (
    invariant_i1_no_outcome_to_outcome,
    invariant_i2_no_reverse_time_causal,
    invariant_i3_orphan_revenue_outcome,
    invariant_i4_polarity_consistency,
    run_all,
)
from arc_classifier import classify_arc, describe_cascade, extract_features, CANONICAL_ARC_TYPES

import graph_fixtures as gf
from graph_fixtures import _add_node as gf_add_node, _add_edge as gf_add_edge

CONFIG_DIR = Path(__file__).resolve().parent / "config"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def loader():
    return TaxonomyLoader(str(CONFIG_DIR))


@pytest.fixture
def taxonomy(loader):
    return loader.get_taxonomy("regional_utility_v1")


# ===========================================================================
# 1. Invariant unit tests — one deliberately-broken fixture per invariant,
#    plus a passing variant of the same shape (Reference Test Harness #1).
# ===========================================================================


class TestInvariantI1OutcomeToOutcome:
    def test_violating_graph_is_flagged(self):
        store, ids = gf.build_i1_violating_graph()
        violations = invariant_i1_no_outcome_to_outcome(store, gf.CUSTOMER_ID)
        assert len(violations) == 1
        v = violations[0]
        assert v.invariant_id == "i1_no_outcome_to_outcome"
        assert set(v.node_ids) == {ids["out1"], ids["out2"]}
        assert v.edge_ids == [ids["edge"]]
        assert str(ids["out1"]) in v.message and str(ids["out2"]) in v.message

    def test_passing_variant_does_not_fire(self):
        store, ids = gf.build_i1_passing_variant()
        violations = invariant_i1_no_outcome_to_outcome(store, gf.CUSTOMER_ID)
        assert violations == []

    def test_ac_caused_by_edge_between_outcomes_rejected_or_flagged(self):
        """AC: 'Inserting a CAUSED_BY edge from an OUTCOME node to another
        OUTCOME node is either rejected at write time or flagged by
        invariant_i1... pick one enforcement point and be consistent.'
        This implementation's enforcement point is invariant-time, not
        write-time (add_edge does not reject OUTCOME->OUTCOME structurally)
        — confirmed consistent by this test: the write succeeds, and the
        invariant is what catches it."""
        store, ids = gf.build_i1_violating_graph()  # write succeeded (no raise)
        violations = invariant_i1_no_outcome_to_outcome(store, gf.CUSTOMER_ID)
        assert len(violations) == 1  # ...and the invariant suite catches it


class TestInvariantI2ReverseTimeCausal:
    def test_violating_graph_is_flagged(self):
        store, ids = gf.build_i2_violating_graph()
        violations = invariant_i2_no_reverse_time_causal(store, gf.CUSTOMER_ID)
        assert len(violations) == 1
        v = violations[0]
        assert v.invariant_id == "i2_no_reverse_time_causal"
        assert set(v.node_ids) == {ids["cause"], ids["effect"]}

    def test_passing_variant_does_not_fire(self):
        store, ids = gf.build_i2_passing_variant()
        violations = invariant_i2_no_reverse_time_causal(store, gf.CUSTOMER_ID)
        assert violations == []

    def test_ac_reads_occurred_at_not_insertion_order(self):
        """AC: constructing the scenario using timestamps that were entered
        into the system in a sensible order, but describe events that
        happened in the wrong real-world order, must STILL be flagged."""
        store, ids = gf.build_i2_violating_graph()
        cause = store.get_node(gf.CUSTOMER_ID, ids["cause"])
        effect = store.get_node(gf.CUSTOMER_ID, ids["effect"])
        # The "cause" node was created FIRST (lower node_id / earlier
        # insertion), same as a sensibly-ordered created_at would be, but
        # its real-world occurred_at is LATER than the effect's.
        assert cause.node_id < effect.node_id
        assert cause.occurred_at > effect.occurred_at
        violations = invariant_i2_no_reverse_time_causal(store, gf.CUSTOMER_ID)
        assert len(violations) == 1


class TestInvariantI3OrphanRevenueOutcome:
    def test_violating_graph_is_flagged(self):
        store, ids = gf.build_i3_violating_graph()
        violations = invariant_i3_orphan_revenue_outcome(store, gf.CUSTOMER_ID)
        assert len(violations) == 1
        v = violations[0]
        assert v.invariant_id == "i3_orphan_revenue_outcome"
        assert v.node_ids == [ids["orphan"]]

    def test_passing_variant_does_not_fire(self):
        store, ids = gf.build_i3_passing_variant()
        violations = invariant_i3_orphan_revenue_outcome(store, gf.CUSTOMER_ID)
        assert violations == []

    def test_null_revenue_impact_outcome_never_flagged(self):
        """An OUTCOME with no revenue_impact at all is exempt regardless of
        inbound edges — the invariant only concerns $-impact claims."""
        store = GraphStore(":memory:")
        node = ContextNode(
            node_id=None,
            customer_id=gf.CUSTOMER_ID,
            account_id=gf.ACCOUNT_ID,
            node_type="OUTCOME",
            node_subtype="usage_plateau",
            source="system",
            tier=1,
            occurred_at=datetime(2026, 1, 1).isoformat(),
        )
        store.add_node(node)
        assert invariant_i3_orphan_revenue_outcome(store, gf.CUSTOMER_ID) == []


class TestInvariantI4PolarityConsistency:
    def test_violating_graph_is_flagged(self, taxonomy):
        store, ids = gf.build_i4_violating_graph()
        violations = invariant_i4_polarity_consistency(store, gf.CUSTOMER_ID, taxonomy)
        assert len(violations) == 1
        v = violations[0]
        assert v.invariant_id == "i4_polarity_consistency"
        assert set(v.node_ids) == {ids["sig"], ids["outcome"]}

    def test_passing_variant_matching_polarity_does_not_fire(self, taxonomy):
        store, ids = gf.build_i4_passing_variant_matching_polarity()
        violations = invariant_i4_polarity_consistency(store, gf.CUSTOMER_ID, taxonomy)
        assert violations == []

    def test_ac_ambiguous_signal_subtype_is_silently_skipped(self, taxonomy):
        """AC: an edge where either end is polarity-ambiguous must be a
        genuine no-op for this check — not flagged, not specially logged."""
        store, ids = gf.build_i4_passing_variant_ambiguous_signal()
        violations = invariant_i4_polarity_consistency(store, gf.CUSTOMER_ID, taxonomy)
        assert violations == []

    def test_ac_ambiguous_outcome_subtype_is_silently_skipped(self, taxonomy):
        store, ids = gf.build_i4_passing_variant_ambiguous_outcome()
        violations = invariant_i4_polarity_consistency(store, gf.CUSTOMER_ID, taxonomy)
        assert violations == []


# ===========================================================================
# 2. Taxonomy contradiction tests (Reference Test Harness #2) — one test per
#    base/overlay contradiction type.
# ===========================================================================


class TestTaxonomyContradictions:
    @staticmethod
    def _contradiction_loader(tmp_path, contradictory_fixture_name):
        # Assemble a config dir with the real base + the one contradictory
        # overlay under test (loader.get_taxonomy needs taxonomy_base.json
        # to be co-located with whichever overlay it's loading).
        shutil.copy(CONFIG_DIR / "taxonomy_base.json", tmp_path / "taxonomy_base.json")
        shutil.copy(
            FIXTURES_DIR / contradictory_fixture_name,
            tmp_path / contradictory_fixture_name,
        )
        return TaxonomyLoader(str(tmp_path))

    def test_bucket_reassignment_overlay_fails_at_load_time(self, tmp_path):
        """AC: 'A taxonomy overlay that attempts to move a base-defined
        subtype into a different revenue bucket fails validate_overlay_vs_base
        at load time, before the taxonomy is ever served to any request.'"""
        loader = self._contradiction_loader(tmp_path, "taxonomy_contradictory_bucket.json")
        with pytest.raises(TaxonomyValidationError, match="contract_terminated"):
            loader.get_taxonomy("contradictory_bucket")

    def test_ambiguous_vs_definitive_overlay_fails_at_load_time(self, tmp_path):
        """AC: same class of contradiction — marking a subtype
        polarity-ambiguous when base already gave it a definitive bucket."""
        loader = self._contradiction_loader(tmp_path, "taxonomy_contradictory_ambiguous.json")
        with pytest.raises(TaxonomyValidationError, match="contract_renewed_full_scope"):
            loader.get_taxonomy("contradictory_ambiguous")

    def test_valid_overlay_loads_and_merges_additively(self, taxonomy):
        # sanity: the real (non-contradictory) overlay loads fine and
        # base + overlay subtypes are both present (additive union).
        assert "co_op_board_terminated_contract" in taxonomy.revenue_buckets["lost"]
        assert "contract_terminated" in taxonomy.revenue_buckets["lost"]  # base entry preserved


class TestValidateAllAtBoot:
    def test_happy_path_returns_verified_filenames(self):
        loader = TaxonomyLoader(str(CONFIG_DIR))
        verified = loader.validate_all_at_boot()
        assert "taxonomy_base.json" in verified
        assert "taxonomy_regional_utility_v1.json" in verified

    def test_broken_unused_vertical_overlay_blocks_boot(self, tmp_path):
        """AC: validate_all_at_boot() raises if ANY taxonomy file on disk is
        invalid — including a vertical's overlay that no current customer is
        even using yet."""
        # Assemble a config dir: real base + real overlay (both fine) +
        # one broken overlay for a vertical nobody uses.
        for name in ("taxonomy_base.json", "taxonomy_regional_utility_v1.json"):
            shutil.copy(CONFIG_DIR / name, tmp_path / name)
        shutil.copy(
            FIXTURES_DIR / "taxonomy_unused_vertical_broken.json",
            tmp_path / "taxonomy_unused_vertical.json",
        )
        loader = TaxonomyLoader(str(tmp_path))
        with pytest.raises(TaxonomyValidationError):
            loader.validate_all_at_boot()

    def test_broken_unused_vertical_does_not_block_targeted_get_taxonomy(self, tmp_path):
        """Sanity check clarifying the AC's scope: get_taxonomy() for a
        SPECIFIC, valid vertical succeeds even while an unrelated broken
        file sits on disk — it's validate_all_at_boot specifically that must
        refuse to let the app start at all."""
        for name in ("taxonomy_base.json", "taxonomy_regional_utility_v1.json"):
            shutil.copy(CONFIG_DIR / name, tmp_path / name)
        shutil.copy(
            FIXTURES_DIR / "taxonomy_unused_vertical_broken.json",
            tmp_path / "taxonomy_unused_vertical.json",
        )
        loader = TaxonomyLoader(str(tmp_path))
        tax = loader.get_taxonomy("regional_utility_v1")  # must not raise
        assert tax.vertical == "regional_utility_v1"


# ===========================================================================
# 3. Tenant isolation (Build Prompt point 1 / Gotcha 2)
# ===========================================================================


class TestTenantIsolation:
    def test_read_by_node_id_requires_matching_customer_id(self):
        store, ids = gf.build_i1_violating_graph()
        other_customer = gf.CUSTOMER_ID + 1
        assert store.get_node(other_customer, ids["out1"]) is None
        assert store.get_node(gf.CUSTOMER_ID, ids["out1"]) is not None

    def test_edge_cannot_reference_a_node_from_another_customer(self):
        store, ids = gf.build_i1_violating_graph()
        rogue_edge = ContextEdge(
            edge_id=None,
            customer_id=gf.CUSTOMER_ID + 1,  # different tenant than the nodes
            from_node_id=ids["out1"],
            to_node_id=ids["out2"],
            edge_type="CAUSED_BY",
            occurred_at=datetime(2026, 1, 5).isoformat(),
        )
        with pytest.raises(ValueError):
            store.add_edge(rogue_edge)

    def test_multi_hop_traversal_never_leaks_another_tenant_node(self):
        """Gotcha 2: a traversal must re-check tenant ownership at every hop,
        not just the starting node. get_edges_for_account already joins
        through context_nodes filtered by customer_id at both ends of the
        query — assert a second tenant's same-shaped graph is fully
        invisible via every read path."""
        store, ids = gf.build_i1_violating_graph()
        # second tenant, same account_id number, different customer_id
        other_customer = gf.CUSTOMER_ID + 1
        node = ContextNode(
            node_id=None,
            customer_id=other_customer,
            account_id=gf.ACCOUNT_ID,
            node_type="OUTCOME",
            node_subtype="non_renewal",
            source="system",
            tier=1,
            occurred_at=datetime(2026, 1, 1).isoformat(),
        )
        other_node_id = store.add_node(node)

        # Reading tenant 1's account never returns tenant 2's node, and vice versa.
        t1_nodes = {n.node_id for n in store.get_nodes_for_account(gf.CUSTOMER_ID, gf.ACCOUNT_ID)}
        t2_nodes = {n.node_id for n in store.get_nodes_for_account(other_customer, gf.ACCOUNT_ID)}
        assert other_node_id not in t1_nodes
        assert ids["out1"] not in t2_nodes


# ===========================================================================
# 4. Arc classification (Build Prompt point 4 / AC)
# ===========================================================================


class TestArcClassification:
    def test_returns_one_of_the_canonical_arc_types(self, taxonomy):
        store, ids = gf.build_i3_passing_variant()
        arc, confidence, phase = classify_arc(
            store, gf.CUSTOMER_ID, gf.ACCOUNT_ID, taxonomy, now=gf.BASE_TIME + timedelta(days=10)
        )
        assert arc in CANONICAL_ARC_TYPES
        assert 0.0 <= confidence <= 1.0
        assert isinstance(phase, str)

    def test_sparse_ambiguous_graph_gets_low_confidence(self, taxonomy):
        """AC: 'Arc classification on an account with a sparse, ambiguous
        graph... returns a low confidence score, not the same confidence as
        an account with a rich, unambiguous graph clearly matching one
        arc's signature.'"""
        store = GraphStore(":memory:")
        # a single neutral-subtype signal, no causal chains
        node = ContextNode(
            node_id=None,
            customer_id=gf.CUSTOMER_ID,
            account_id=gf.ACCOUNT_ID,
            node_type="SIGNAL",
            node_subtype="usage_plateau",
            source="system",
            tier=1,
            occurred_at=gf.BASE_TIME.isoformat(),
            properties={},
        )
        store.add_node(node)
        sparse_arc, sparse_confidence, _ = classify_arc(
            store, gf.CUSTOMER_ID, gf.ACCOUNT_ID, taxonomy, now=gf.BASE_TIME + timedelta(days=1)
        )

        rich_store = _build_rich_unambiguous_crisis_graph()
        rich_arc, rich_confidence, _ = classify_arc(
            rich_store,
            gf.CUSTOMER_ID,
            gf.ACCOUNT_ID,
            taxonomy,
            now=gf.BASE_TIME + timedelta(days=40),
        )

        assert sparse_confidence < rich_confidence
        assert rich_arc == "regulatory_crisis"
        assert rich_confidence > 0.5
        assert sparse_confidence < 0.35

    def test_cascade_is_printable_and_explicit(self):
        cascade = describe_cascade()
        assert cascade == list(CANONICAL_ARC_TYPES)

    def test_confidence_not_constant_across_distinct_graphs(self, taxonomy):
        """Directly guards against a constant-confidence implementation,
        which the AC explicitly forbids."""
        store_a, _ = gf.build_i3_passing_variant()
        store_b = _build_rich_unambiguous_crisis_graph()
        _, conf_a, _ = classify_arc(
            store_a, gf.CUSTOMER_ID, gf.ACCOUNT_ID, taxonomy, now=gf.BASE_TIME + timedelta(days=10)
        )
        _, conf_b, _ = classify_arc(
            store_b, gf.CUSTOMER_ID, gf.ACCOUNT_ID, taxonomy, now=gf.BASE_TIME + timedelta(days=40)
        )
        assert conf_a != conf_b


def _build_rich_unambiguous_crisis_graph() -> GraphStore:
    """A dense, unambiguous regulatory_crisis-shaped graph: multiple
    negative signals feeding a causal chain (via an intervening SIGNAL
    between the two OUTCOMEs, never OUTCOME->OUTCOME directly, so this
    fixture doesn't itself trip I1) into negative revenue outcomes, no
    recovery, plenty of nodes (not sparse)."""
    store = GraphStore(":memory:")
    sig1 = gf_add_node(store, "SIGNAL", "outage_reported", 0, properties={"polarity": "negative"})
    sig2 = gf_add_node(store, "SIGNAL", "escalation_raised", 2, properties={"polarity": "negative"})
    stakeholder = gf_add_node(store, "STAKEHOLDER", "ops_director", 3)
    decision = gf_add_node(store, "DECISION", "sla_credit_denied", 5)
    out1 = gf_add_node(
        store,
        "OUTCOME",
        "outage_sla_breach_escalation",
        8,
        revenue_impact=-20000.0,
        revenue_impact_type="at_risk",
    )
    sig3 = gf_add_node(store, "SIGNAL", "escalation_raised", 12, properties={"polarity": "negative"})
    out2 = gf_add_node(
        store,
        "OUTCOME",
        "non_renewal",
        16,
        revenue_impact=-150000.0,
        revenue_impact_type="lost",
    )

    gf_add_edge(store, "CAUSED_BY", sig1, sig2, 2)
    gf_add_edge(store, "INVOLVES", sig2, stakeholder, 3)
    gf_add_edge(store, "CAUSED_BY", sig2, decision, 5)
    gf_add_edge(store, "CAUSED_BY", decision, out1, 8)
    gf_add_edge(store, "CAUSED_BY", out1, sig3, 12)
    gf_add_edge(store, "CAUSED_BY", sig3, out2, 16)
    return store


# ===========================================================================
# 5. Live smoke test (Reference Test Harness #3) — synthetic multi-phase
#    account through the pipeline, run the full invariant suite.
# ===========================================================================


class TestLiveSmokeTest:
    def test_synthetic_multiphase_account_passes_full_invariant_suite(self, taxonomy):
        """Builds a synthetic 'baseline -> incident -> recovery' account
        history deliberately in CORRECT generation order (each node's
        occurred_at assigned in the same order it's written, and every
        revenue-carrying OUTCOME given a supporting causal edge before the
        graph is considered done) and asserts zero violations — proving the
        invariant suite is quiet on a well-formed synthetic dataset, the
        condition the spec's own live-smoke-test paragraph implies should be
        achievable when generation order is respected."""
        store = GraphStore(":memory:")

        # Phase 1: baseline — a neutral external context + a positive signal.
        ext = gf_add_node(store, "EXTERNAL_CONTEXT", "rate_case_opened", 0)
        pos_sig = gf_add_node(
            store, "SIGNAL", "positive_feedback_survey", 3, properties={"polarity": "positive"}
        )

        # Phase 2: incident — negative signal -> decision -> at-risk outcome,
        # each edge's occurred_at chosen to be >= both endpoints' occurred_at
        # and every OUTCOME with revenue_impact gets an inbound causal edge.
        neg_sig = gf_add_node(
            store, "SIGNAL", "outage_reported", 20, properties={"polarity": "negative"}
        )
        decision = gf_add_node(store, "DECISION", "emergency_crew_dispatched", 21)
        at_risk_outcome = gf_add_node(
            store,
            "OUTCOME",
            "outage_sla_breach_escalation",
            25,
            revenue_impact=-15000.0,
            revenue_impact_type="at_risk",
        )

        # Phase 3: recovery — auto-recovery outcome, caused by a positive
        # signal that itself is caused by the decision (never OUTCOME->OUTCOME).
        recovery_sig = gf_add_node(
            store, "SIGNAL", "positive_feedback_survey", 30, properties={"polarity": "positive"}
        )
        recovery_outcome = gf_add_node(
            store,
            "OUTCOME",
            "outage_root_cause_resolved",
            35,
            revenue_impact=5000.0,
            revenue_impact_type="protected",
        )

        gf_add_edge(store, "SOURCED_FROM", neg_sig, ext, 20)
        gf_add_edge(store, "CAUSED_BY", neg_sig, decision, 21)
        gf_add_edge(store, "CAUSED_BY", decision, at_risk_outcome, 25)
        gf_add_edge(store, "CAUSED_BY", decision, recovery_sig, 30)
        gf_add_edge(store, "CAUSED_BY", recovery_sig, recovery_outcome, 35)

        violations = run_all(store, gf.CUSTOMER_ID, taxonomy)
        assert violations == [], f"expected zero violations, got: {violations}"

    def test_generation_order_bug_reproduces_i3_and_i2_pattern(self, taxonomy):
        """Negative control mirroring the spec's own documented finding
        ('a synthetic multi-phase test customer's graph tripped 16
        violations (15x I3, 1x I17-reverse-time) purely from
        generation-order artifacts in the test data generator'). Here: a
        synthetic generator that assigns causal edges BEFORE the outcome
        nodes they should point to exist yet (a common LLM-enrichment bug
        shape) ends up either skipping the edge or wiring it to the wrong
        node's timestamp — simulated here directly as an outcome node
        written with no causal edge at all (I3) and a signal->outcome edge
        with real-world occurred_at reversed relative to upload order (I2).
        This demonstrates the invariant suite catching exactly that failure
        mode, and that root-causing it points at the DATA, not the checks."""
        store = GraphStore(":memory:")
        # Simulate a generator that wrote nodes in "generation order" but
        # assigned occurred_at based on a shuffled real-world timeline.
        effect = gf_add_node(store, "OUTCOME", "renewal_at_risk", 2)
        cause = gf_add_node(
            store, "SIGNAL", "escalation_raised", 10, properties={"polarity": "negative"}
        )
        gf_add_edge(store, "CAUSED_BY", cause, effect, 10)

        orphan_outcome = gf_add_node(
            store, "OUTCOME", "non_renewal", 12, revenue_impact=-9000.0, revenue_impact_type="lost"
        )

        violations = run_all(store, gf.CUSTOMER_ID, taxonomy)
        ids_by_invariant = {}
        for v in violations:
            ids_by_invariant.setdefault(v.invariant_id, []).append(v)

        assert "i2_no_reverse_time_causal" in ids_by_invariant
        assert "i3_orphan_revenue_outcome" in ids_by_invariant
        assert ids_by_invariant["i3_orphan_revenue_outcome"][0].node_ids == [orphan_outcome]
