"""
Deliberately-broken (and passing-variant) graph fixtures, one pair per
invariant, per Reference Test Harness item 1: "construct the minimal graph
that should trip each rule... construct a passing variant of the same shape
and assert it does NOT fire (both directions matter)."

Every builder returns a fresh in-memory GraphStore plus a dict of the
node/edge ids it created, so tests can assert violations name the correct
ids.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph_schema import ContextEdge, ContextNode, GraphStore  # noqa: E402

CUSTOMER_ID = 9001
ACCOUNT_ID = 42
BASE_TIME = datetime(2026, 1, 1)


def _t(days: int) -> str:
    return (BASE_TIME + timedelta(days=days)).isoformat()


def _mk_store() -> GraphStore:
    return GraphStore(":memory:")


def _add_node(store, node_type, subtype, day, **kwargs) -> int:
    node = ContextNode(
        node_id=None,
        customer_id=CUSTOMER_ID,
        account_id=ACCOUNT_ID,
        node_type=node_type,
        node_subtype=subtype,
        source=kwargs.pop("source", "system"),
        tier=kwargs.pop("tier", 1),
        occurred_at=_t(day),
        **kwargs,
    )
    return store.add_node(node)


def _add_edge(store, edge_type, from_id, to_id, day, **kwargs) -> int:
    edge = ContextEdge(
        edge_id=None,
        customer_id=CUSTOMER_ID,
        from_node_id=from_id,
        to_node_id=to_id,
        edge_type=edge_type,
        occurred_at=_t(day),
        **kwargs,
    )
    return store.add_edge(edge)


# ---------------------------------------------------------------------------
# I1 — no OUTCOME -> OUTCOME causal edge
# ---------------------------------------------------------------------------


def build_i1_violating_graph():
    store = _mk_store()
    out1 = _add_node(store, "OUTCOME", "downgrade_requested", 0)
    out2 = _add_node(store, "OUTCOME", "renewal_at_risk", 5)
    edge = _add_edge(store, "CAUSED_BY", out1, out2, 5)
    return store, {"out1": out1, "out2": out2, "edge": edge}


def build_i1_passing_variant():
    """Same shape, but an intervening SIGNAL breaks the direct OUTCOME->OUTCOME
    link — this must NOT fire."""
    store = _mk_store()
    out1 = _add_node(store, "OUTCOME", "downgrade_requested", 0)
    sig = _add_node(store, "SIGNAL", "escalation_raised", 3, properties={"polarity": "negative"})
    out2 = _add_node(store, "OUTCOME", "renewal_at_risk", 5)
    e1 = _add_edge(store, "CAUSED_BY", out1, sig, 3)
    e2 = _add_edge(store, "CAUSED_BY", sig, out2, 5)
    return store, {"out1": out1, "sig": sig, "out2": out2, "e1": e1, "e2": e2}


# ---------------------------------------------------------------------------
# I2 — no reverse-time causal edge (reads occurred_at, never created_at)
# ---------------------------------------------------------------------------


def build_i2_violating_graph():
    """cause occurs AFTER effect in real-world time (occurred_at), even
    though it was written to the store in a sensible created_at-style order
    (added first) — proves the check reads occurred_at, not insertion/
    creation order."""
    store = _mk_store()
    cause = _add_node(store, "SIGNAL", "escalation_raised", 10, properties={"polarity": "negative"})
    effect = _add_node(store, "OUTCOME", "renewal_at_risk", 2)  # earlier real-world time
    edge = _add_edge(store, "CAUSED_BY", cause, effect, 10)
    return store, {"cause": cause, "effect": effect, "edge": edge}


def build_i2_passing_variant():
    store = _mk_store()
    cause = _add_node(store, "SIGNAL", "escalation_raised", 2, properties={"polarity": "negative"})
    effect = _add_node(store, "OUTCOME", "renewal_at_risk", 10)
    edge = _add_edge(store, "CAUSED_BY", cause, effect, 10)
    return store, {"cause": cause, "effect": effect, "edge": edge}


# ---------------------------------------------------------------------------
# I3 — every revenue-carrying OUTCOME has >=1 inbound causal edge
# ---------------------------------------------------------------------------


def build_i3_violating_graph():
    store = _mk_store()
    orphan = _add_node(
        store, "OUTCOME", "non_renewal", 5, revenue_impact=-50000.0, revenue_impact_type="lost"
    )
    return store, {"orphan": orphan}


def build_i3_passing_variant():
    store = _mk_store()
    cause = _add_node(store, "SIGNAL", "escalation_raised", 0, properties={"polarity": "negative"})
    outcome = _add_node(
        store, "OUTCOME", "non_renewal", 5, revenue_impact=-50000.0, revenue_impact_type="lost"
    )
    edge = _add_edge(store, "CAUSED_BY", cause, outcome, 5)
    return store, {"cause": cause, "outcome": outcome, "edge": edge}


# ---------------------------------------------------------------------------
# I4 — polarity consistency (positive SIGNAL can't cause negative OUTCOME,
# unless either subtype is polarity-ambiguous)
# ---------------------------------------------------------------------------


def build_i4_violating_graph():
    store = _mk_store()
    sig = _add_node(store, "SIGNAL", "positive_feedback_survey", 0, properties={"polarity": "positive"})
    outcome = _add_node(store, "OUTCOME", "non_renewal", 5)  # base bucket: 'lost' -> negative
    edge = _add_edge(store, "CAUSED_BY", sig, outcome, 5)
    return store, {"sig": sig, "outcome": outcome, "edge": edge}


def build_i4_passing_variant_matching_polarity():
    store = _mk_store()
    sig = _add_node(store, "SIGNAL", "escalation_raised", 0, properties={"polarity": "negative"})
    outcome = _add_node(store, "OUTCOME", "non_renewal", 5)
    edge = _add_edge(store, "CAUSED_BY", sig, outcome, 5)
    return store, {"sig": sig, "outcome": outcome, "edge": edge}


def build_i4_passing_variant_ambiguous_signal():
    """SIGNAL subtype is polarity-ambiguous in the base taxonomy
    ('stakeholder_reorg') -> the check must skip this edge entirely, even
    though the tagged 'positive' polarity property would otherwise mismatch
    the negative OUTCOME."""
    store = _mk_store()
    sig = _add_node(store, "SIGNAL", "stakeholder_reorg", 0, properties={"polarity": "positive"})
    outcome = _add_node(store, "OUTCOME", "non_renewal", 5)
    edge = _add_edge(store, "CAUSED_BY", sig, outcome, 5)
    return store, {"sig": sig, "outcome": outcome, "edge": edge}


def build_i4_passing_variant_ambiguous_outcome():
    """OUTCOME subtype is polarity-ambiguous in the base taxonomy
    ('usage_plateau', not placed in any revenue bucket) -> skip entirely."""
    store = _mk_store()
    sig = _add_node(store, "SIGNAL", "positive_feedback_survey", 0, properties={"polarity": "positive"})
    outcome = _add_node(store, "OUTCOME", "usage_plateau", 5)
    edge = _add_edge(store, "CAUSED_BY", sig, outcome, 5)
    return store, {"sig": sig, "outcome": outcome, "edge": edge}
