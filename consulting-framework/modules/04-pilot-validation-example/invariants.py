"""
Invariant framework — each invariant is an independently-callable,
independently-testable function `invariant_iN_description(store, customer_id,
taxonomy) -> list[Violation]`.

Deviation from the Build Prompt's literal signature: the spec's pseudocode
signature is `invariant_iN_description(customer_id) -> list[Violation]`,
implying the function reaches into some ambient store/taxonomy. Since this
pilot has no global singleton store (Module 01's Gotcha 2 lesson — never
assume implicit access is safe — argues against a hidden global), every
invariant here explicitly takes `store` and (where needed) `taxonomy` as
parameters alongside `customer_id`. This is called out because it's a small,
deliberate deviation from the literal signature, not an oversight.

Only CAUSED_BY/LED_TO are treated as "causal" edges for the purposes of I1-I3
— see graph_schema.CAUSAL_EDGE_TYPES and the comment there for why (spec
ambiguity: the term "causal edge" is never mapped to specific edge_type
values anywhere in the Module 04 spec).
"""

from __future__ import annotations

from graph_schema import CAUSAL_EDGE_TYPES, ContextEdge, ContextNode, GraphStore, Violation
from taxonomy_loader import Taxonomy


def invariant_i1_no_outcome_to_outcome(store: GraphStore, customer_id: int) -> list[Violation]:
    """No CAUSED_BY/LED_TO causal edge directly from an OUTCOME node to
    another OUTCOME node — a realized result can't directly cause another
    realized result without an intervening SIGNAL/DECISION."""
    violations = []
    for edge in store.get_all_edges(customer_id):
        if edge.edge_type not in CAUSAL_EDGE_TYPES:
            continue
        from_node = store.get_node(customer_id, edge.from_node_id)
        to_node = store.get_node(customer_id, edge.to_node_id)
        if from_node is None or to_node is None:
            continue
        if from_node.node_type == "OUTCOME" and to_node.node_type == "OUTCOME":
            violations.append(
                Violation(
                    invariant_id="i1_no_outcome_to_outcome",
                    severity="error",
                    account_id=from_node.account_id,
                    node_ids=[from_node.node_id, to_node.node_id],
                    edge_ids=[edge.edge_id],
                    message=(
                        f"OUTCOME node {from_node.node_id} "
                        f"({from_node.node_subtype}) has a {edge.edge_type} "
                        f"edge (edge_id={edge.edge_id}) directly to OUTCOME "
                        f"node {to_node.node_id} ({to_node.node_subtype}) — "
                        f"an OUTCOME cannot directly cause another OUTCOME; "
                        f"an intervening SIGNAL/DECISION is required"
                    ),
                )
            )
    return violations


def invariant_i2_no_reverse_time_causal(store: GraphStore, customer_id: int) -> list[Violation]:
    """No causal edge where to_node.occurred_at < from_node.occurred_at — an
    effect cannot occur before its cause. MUST read occurred_at, never
    created_at (Gotcha 1) — there is no created_at field in this schema at
    all, which structurally forecloses the mistake, but the check below is
    still written to make the field it reads explicit for reviewers."""
    violations = []
    for edge in store.get_all_edges(customer_id):
        if edge.edge_type not in CAUSAL_EDGE_TYPES:
            continue
        from_node = store.get_node(customer_id, edge.from_node_id)
        to_node = store.get_node(customer_id, edge.to_node_id)
        if from_node is None or to_node is None:
            continue
        if to_node.occurred_at < from_node.occurred_at:
            violations.append(
                Violation(
                    invariant_id="i2_no_reverse_time_causal",
                    severity="error",
                    account_id=from_node.account_id,
                    node_ids=[from_node.node_id, to_node.node_id],
                    edge_ids=[edge.edge_id],
                    message=(
                        f"{edge.edge_type} edge (edge_id={edge.edge_id}) "
                        f"points from node {from_node.node_id} "
                        f"(occurred_at={from_node.occurred_at}) to node "
                        f"{to_node.node_id} (occurred_at={to_node.occurred_at}) "
                        f"— the effect occurs before its cause"
                    ),
                )
            )
    return violations


def invariant_i3_orphan_revenue_outcome(store: GraphStore, customer_id: int) -> list[Violation]:
    """Every OUTCOME node carrying a non-null revenue_impact has at least one
    inbound causal (CAUSED_BY/LED_TO) edge — a $-impact claim with zero
    supporting evidence in the graph is not audit-defensible."""
    violations = []
    for node in store.get_all_nodes(customer_id):
        if node.node_type != "OUTCOME" or node.revenue_impact is None:
            continue
        inbound = store.get_inbound_edges(customer_id, node.node_id)
        causal_inbound = [e for e in inbound if e.edge_type in CAUSAL_EDGE_TYPES]
        if not causal_inbound:
            violations.append(
                Violation(
                    invariant_id="i3_orphan_revenue_outcome",
                    severity="error",
                    account_id=node.account_id,
                    node_ids=[node.node_id],
                    edge_ids=[],
                    message=(
                        f"OUTCOME node {node.node_id} ({node.node_subtype}) "
                        f"carries revenue_impact={node.revenue_impact} but has "
                        f"no inbound CAUSED_BY/LED_TO edge — a $-impact claim "
                        f"with no supporting causal evidence in the graph"
                    ),
                )
            )
    return violations


def invariant_i4_polarity_consistency(
    store: GraphStore, customer_id: int, taxonomy: Taxonomy
) -> list[Violation]:
    """A positive-subtype SIGNAL cannot cause a negative-subtype OUTCOME (and
    vice versa) UNLESS either end is in the taxonomy's polarity-ambiguous
    set, in which case that edge is silently skipped by this check.

    "Positive"/"negative" is derived from the taxonomy's revenue-bucket
    classification for OUTCOME subtypes (lost/at_risk = negative,
    expansion/protected = positive; 'pipeline' is treated as neutral/
    non-definitive and skipped, same as polarity-ambiguous, since the spec
    never states a polarity for it either). SIGNAL polarity is read from
    node.properties['polarity'] (an explicit 'positive'/'negative' tag on
    the SIGNAL node) when present; this is a modeling decision this pilot
    had to make since the spec's taxonomy shape gives SIGNAL subtypes no
    revenue-bucket concept at all (see pilot report ambiguity #2) — SIGNAL
    polarity can only come from the taxonomy's polarity_ambiguous_signal_
    subtypes list (which tells us when polarity is UNKNOWN) or an explicit
    per-node tag (which tells us what it IS); the spec defines the former
    but never the latter.
    """
    violations = []
    for edge in store.get_all_edges(customer_id):
        if edge.edge_type not in CAUSAL_EDGE_TYPES:
            continue
        from_node = store.get_node(customer_id, edge.from_node_id)
        to_node = store.get_node(customer_id, edge.to_node_id)
        if from_node is None or to_node is None:
            continue

        signal_node, outcome_node = None, None
        if from_node.node_type == "SIGNAL" and to_node.node_type == "OUTCOME":
            signal_node, outcome_node = from_node, to_node
        elif from_node.node_type == "OUTCOME" and to_node.node_type == "SIGNAL":
            signal_node, outcome_node = to_node, from_node
        else:
            continue

        if taxonomy.is_signal_polarity_ambiguous(signal_node.node_subtype):
            continue
        if taxonomy.is_outcome_polarity_ambiguous(outcome_node.node_subtype):
            continue

        signal_polarity = signal_node.properties.get("polarity")
        outcome_bucket = taxonomy.bucket_for(outcome_node.node_subtype)
        outcome_polarity = _bucket_polarity(outcome_bucket)

        if signal_polarity not in ("positive", "negative"):
            continue  # unknown SIGNAL polarity — nothing to check against
        if outcome_polarity is None:
            continue  # neutral/unclassified bucket (e.g. pipeline) — skip

        if signal_polarity != outcome_polarity:
            violations.append(
                Violation(
                    invariant_id="i4_polarity_consistency",
                    severity="error",
                    account_id=signal_node.account_id,
                    node_ids=[signal_node.node_id, outcome_node.node_id],
                    edge_ids=[edge.edge_id],
                    message=(
                        f"{signal_polarity}-polarity SIGNAL node "
                        f"{signal_node.node_id} ({signal_node.node_subtype}) "
                        f"has a causal edge (edge_id={edge.edge_id}) to "
                        f"{outcome_polarity}-polarity OUTCOME node "
                        f"{outcome_node.node_id} ({outcome_node.node_subtype}, "
                        f"bucket={outcome_bucket}) — polarity mismatch, and "
                        f"neither subtype is in the polarity-ambiguous set"
                    ),
                )
            )
    return violations


def _bucket_polarity(bucket: str | None) -> str | None:
    if bucket in ("lost", "at_risk"):
        return "negative"
    if bucket in ("expansion", "protected"):
        return "positive"
    return None  # pipeline or unclassified — neutral, not checked


ALL_INVARIANTS = {
    "i1_no_outcome_to_outcome": invariant_i1_no_outcome_to_outcome,
    "i2_no_reverse_time_causal": invariant_i2_no_reverse_time_causal,
    "i3_orphan_revenue_outcome": invariant_i3_orphan_revenue_outcome,
    "i4_polarity_consistency": invariant_i4_polarity_consistency,
}


def run_all(store: GraphStore, customer_id: int, taxonomy: Taxonomy) -> list[Violation]:
    violations = []
    violations += invariant_i1_no_outcome_to_outcome(store, customer_id)
    violations += invariant_i2_no_reverse_time_causal(store, customer_id)
    violations += invariant_i3_orphan_revenue_outcome(store, customer_id)
    violations += invariant_i4_polarity_consistency(store, customer_id, taxonomy)
    return violations
