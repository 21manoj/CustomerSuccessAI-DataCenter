"""
Arc classification — a pure function over graph-derived features into one of
the client's defined canonical arc types, via an explicit, orderable rule
cascade.

*** Spec-fidelity note (see pilot report finding #1) ***
The Module 04 Build Prompt's "Arc classification" section is written
entirely in prose — no pseudocode, no formula, no worked example — unlike
every other piece of this Build Prompt (schema, taxonomy loader, invariants)
which is given literal, unambiguous pseudocode. Everything below (which
features to extract, how they combine into a score, how confidence is
computed, what "phase" means) is this pilot's own invented, defensible
design, not something transcribed from the spec. A different implementer
reading the same Build Prompt would very plausibly build a different rule
cascade with different confidence semantics — that divergence risk is
exactly the failure class Module 03's Gotcha-driven pseudocode rewrite was
designed to prevent elsewhere in this library, and it was not applied here.

Canonical arc types invented for this pilot's vertical (`regional_utility_v1`
— a CS platform for regional electric/water co-op customers), per the
Config-section instruction that a client's canonical arc set is theirs to
define, not the origin system's 8:

  - stable_operations     baseline / no clear signal of crisis or expansion
  - regulatory_crisis      negative causal chain: outage/regulatory signals
                            leading to at-risk/lost revenue outcomes
  - infrastructure_recovery a crisis-shaped history followed by a recovery
                            outcome (post-incident remediation, SLA restored)
  - expansion_momentum      positive signals + expansion/protected outcomes
                            with a supporting causal chain
  - silent_disengagement    sparse recent activity, no stakeholder
                            engagement, no causal chains — churn risk with
                            no explicit negative signal to point to
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from graph_schema import CAUSAL_EDGE_TYPES, ContextEdge, ContextNode, GraphStore
from taxonomy_loader import Taxonomy

CANONICAL_ARC_TYPES = (
    "regulatory_crisis",
    "infrastructure_recovery",
    "expansion_momentum",
    "silent_disengagement",
    "stable_operations",
)

SPARSE_NODE_THRESHOLD = 8  # fewer total nodes than this dampens confidence
SILENT_DAYS_THRESHOLD = 60  # no activity in this many days => disengagement signal


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


@dataclass
class ArcFeatures:
    total_nodes: int
    signal_total: int
    signal_negative: int
    signal_positive: int
    stakeholder_total: int
    outcome_total: int
    outcome_negative: int
    outcome_positive: int
    outcome_recovery: int
    recovery_after_negative: bool
    causal_depth: int
    most_recent_age_days: Optional[float]
    span_days: Optional[float]


def _longest_causal_chain(nodes: list[ContextNode], edges: list[ContextEdge]) -> int:
    """Longest path (# of edges) over the subgraph restricted to
    CAUSAL_EDGE_TYPES. Memoized DFS with a visiting-set cycle guard (the
    reverse-time invariant should prevent real cycles, but a fixture graph
    under test might deliberately violate that, and this function must not
    infinite-loop on bad input)."""
    adj: dict = {}
    for e in edges:
        if e.edge_type in CAUSAL_EDGE_TYPES:
            adj.setdefault(e.from_node_id, []).append(e.to_node_id)

    memo: dict = {}

    def longest_from(node_id, visiting: frozenset) -> int:
        if node_id in memo:
            return memo[node_id]
        if node_id in visiting:
            return 0  # cycle guard
        best = 0
        for nxt in adj.get(node_id, []):
            best = max(best, 1 + longest_from(nxt, visiting | {node_id}))
        memo[node_id] = best
        return best

    if not nodes:
        return 0
    return max((longest_from(n.node_id, frozenset()) for n in nodes), default=0)


def extract_features(
    nodes: list[ContextNode],
    edges: list[ContextEdge],
    taxonomy: Taxonomy,
    now: Optional[datetime] = None,
) -> ArcFeatures:
    now = now or datetime.utcnow()

    signals = [n for n in nodes if n.node_type == "SIGNAL"]
    outcomes = [n for n in nodes if n.node_type == "OUTCOME"]
    stakeholders = [n for n in nodes if n.node_type == "STAKEHOLDER"]

    signal_negative = sum(1 for n in signals if n.properties.get("polarity") == "negative")
    signal_positive = sum(1 for n in signals if n.properties.get("polarity") == "positive")

    outcome_negative = 0
    outcome_positive = 0
    outcome_recovery = 0
    negative_outcome_times = []
    recovery_times = []
    for n in outcomes:
        bucket = taxonomy.bucket_for(n.node_subtype)
        if bucket in ("lost", "at_risk"):
            outcome_negative += 1
            negative_outcome_times.append(_parse(n.occurred_at))
        elif bucket in ("expansion", "protected"):
            outcome_positive += 1
        if n.node_subtype in taxonomy.auto_recovery_outcome_subtypes:
            outcome_recovery += 1
            recovery_times.append(_parse(n.occurred_at))

    recovery_after_negative = bool(
        negative_outcome_times
        and recovery_times
        and max(recovery_times) > min(negative_outcome_times)
    )

    causal_depth = _longest_causal_chain(nodes, edges)

    all_times = [_parse(n.occurred_at) for n in nodes]
    most_recent_age_days = (now - max(all_times)).total_seconds() / 86400 if all_times else None
    span_days = (
        (max(all_times) - min(all_times)).total_seconds() / 86400
        if len(all_times) >= 2
        else 0.0
        if all_times
        else None
    )

    return ArcFeatures(
        total_nodes=len(nodes),
        signal_total=len(signals),
        signal_negative=signal_negative,
        signal_positive=signal_positive,
        stakeholder_total=len(stakeholders),
        outcome_total=len(outcomes),
        outcome_negative=outcome_negative,
        outcome_positive=outcome_positive,
        outcome_recovery=outcome_recovery,
        recovery_after_negative=recovery_after_negative,
        causal_depth=causal_depth,
        most_recent_age_days=most_recent_age_days,
        span_days=span_days,
    )


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _score_regulatory_crisis(f: ArcFeatures) -> float:
    if f.outcome_total == 0 and f.signal_total == 0:
        return 0.0
    raw = (
        0.6 * (1.0 if f.outcome_negative > 0 else 0.0)
        + 0.25 * min(1.0, f.causal_depth / 3)
        + 0.15 * (1.0 if f.signal_negative > 0 else 0.0)
    )
    recovery_dampener = f.outcome_recovery / max(1, f.outcome_total)
    return _clamp(raw * (1 - 0.5 * recovery_dampener))


def _score_infrastructure_recovery(f: ArcFeatures) -> float:
    if not (f.outcome_recovery > 0 and f.outcome_negative > 0):
        return 0.0
    raw = 0.7 * (1.0 if f.recovery_after_negative else 0.3) + 0.3 * min(1.0, f.causal_depth / 3)
    return _clamp(raw)


def _score_expansion_momentum(f: ArcFeatures) -> float:
    if f.outcome_total == 0 and f.signal_positive == 0:
        return 0.0
    outcome_frac = f.outcome_positive / max(1, f.outcome_total)
    signal_frac = f.signal_positive / max(1, f.signal_total) if f.signal_total else 0.0
    raw = 0.5 * outcome_frac + 0.3 * signal_frac + 0.2 * min(1.0, f.causal_depth / 3)
    return _clamp(raw)


def _score_silent_disengagement(f: ArcFeatures) -> float:
    if f.most_recent_age_days is None:
        return 0.0
    raw = (
        0.4 * (1.0 if f.most_recent_age_days > SILENT_DAYS_THRESHOLD else 0.0)
        + 0.3 * (1.0 if f.stakeholder_total == 0 else 0.0)
        + 0.3 * (1.0 if (f.causal_depth <= 1 and f.signal_total > 0) else 0.0)
    )
    return _clamp(raw)


def _score_stable_operations(f: ArcFeatures) -> float:
    # Baseline / null hypothesis: scores modestly, higher when there is
    # simply no strong negative or positive signal either way.
    no_strong_signal = f.outcome_negative == 0 and f.outcome_positive == 0
    return _clamp(0.3 + (0.2 if no_strong_signal else 0.0))


# Explicit, printable, orderable cascade — order matters only for
# deterministic tie-breaking (see classify_arc). Each entry is
# (arc_type, score_fn).
RULE_CASCADE = (
    ("regulatory_crisis", _score_regulatory_crisis),
    ("infrastructure_recovery", _score_infrastructure_recovery),
    ("expansion_momentum", _score_expansion_momentum),
    ("silent_disengagement", _score_silent_disengagement),
    ("stable_operations", _score_stable_operations),
)


def describe_cascade() -> list[str]:
    """Return the rule cascade's arc types in evaluation/tie-break order —
    what "print and explain" means for this cascade: an operator can list
    exactly which rules exist and in what priority they break ties."""
    return [name for name, _ in RULE_CASCADE]


def _derive_phase(f: ArcFeatures) -> str:
    if f.total_nodes == 0:
        return "no_data"
    if f.most_recent_age_days is None:
        return "no_data"
    if f.most_recent_age_days <= 30:
        return "active"
    if f.most_recent_age_days <= 120:
        return "cooling"
    return "dormant"


def classify_arc(
    store: GraphStore,
    customer_id: int,
    account_id: int,
    taxonomy: Taxonomy,
    now: Optional[datetime] = None,
) -> tuple[str, float, str]:
    """Deterministic feature-extraction + rule-cascade classifier. Returns
    (arc_type, confidence, phase). confidence is genuinely informative: low
    for sparse/ambiguous graphs, higher for a graph that clearly and
    unambiguously matches one arc's signature."""
    nodes = store.get_nodes_for_account(customer_id, account_id)
    edges = store.get_edges_for_account(customer_id, account_id)
    features = extract_features(nodes, edges, taxonomy, now=now)

    scores = [(name, fn(features)) for name, fn in RULE_CASCADE]
    scores_sorted = sorted(scores, key=lambda t: t[1], reverse=True)
    winner_arc, winner_score = scores_sorted[0]
    runner_up_score = scores_sorted[1][1] if len(scores_sorted) > 1 else 0.0
    margin = winner_score - runner_up_score

    sparsity_factor = _clamp(features.total_nodes / SPARSE_NODE_THRESHOLD)
    confidence = _clamp(winner_score * sparsity_factor * (0.5 + 0.5 * margin))

    phase = _derive_phase(features)
    return winner_arc, confidence, phase
