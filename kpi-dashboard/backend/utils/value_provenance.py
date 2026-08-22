"""
Provenance vocabulary for customer-facing NUMBERS — KPI values, health
scores, ROI dollar figures, dashboard metrics. One layer up from
utils/provenance.py.

Relationship to utils/provenance.py (read that module first)
--------------------------------------------------------------
utils/provenance.py answers "how trustworthy is this GRAPH NODE/EDGE for
a learning algorithm to consume" with a 3-value vocabulary (observed /
inferred / synthetic) plus an edge-confidence threshold. It is internal
to the context graph and drives Wizard B/C correlation fitting + NRR
forecast reads.

This module answers a different, "one layer up" question: "how should a
NUMBER we are about to show a customer / CFO / CRO be labeled, given how
it was actually produced." It is consumed at the API / response-shaping
boundary — the last mile before a figure reaches a dashboard tile or a
JSON response — not at graph-fitting time.

The five values below are NOT a renaming of provenance.py's three values
and MUST NOT be conflated with them. A context-graph node can be
'observed' while the dollar figure computed downstream of it is
'derived'; a customer's KPI rows can all be real ('measured') while the
pillar weights used to roll them up are still 'benchmark' because
Wizard C hasn't calibrated yet. Same underlying data, two independent
questions.

Five tiers, ordered from most to least grounded in real customer data
-----------------------------------------------------------------------
  measured    — value came directly from a real ingested data point for
                this exact metric (an actual KPI measurement row, a
                real dashboard KPI reading). No transformation beyond
                unit formatting/rounding.
  derived     — computed/transformed from real customer data but not a
                1:1 measurement (a rolled-up score synthesized from
                real pillar scores, a dollar figure computed from a
                real score delta via an economics model, a velocity
                computed from real trend rows).
  benchmark   — blends real customer data with industry/vertical
                benchmark defaults. Most common case: a customer whose
                raw data is real but who hasn't been Wizard-C-calibrated
                yet, so their real KPI/pillar data is being read through
                default/benchmark weights rather than their own learned
                weights.
  default     — a static fallback baseline with no real customer signal
                behind it at all (e.g. brand-new tenant, zero accounts,
                zero measurements anywhere in the lookback window).
  unavailable — no data path could produce a value. MUST be surfaced as
                literally "unavailable" in the API/UI — never silently
                defaulted to a number that looks like real data.

Use ALL_TIERS / is_valid() to validate a value at a module boundary, and
calibration_tier() for the single most common judgment call this
taxonomy exists to standardize: "is this real customer data running
through the customer's own calibrated weights, or through benchmark
defaults because they haven't been calibrated yet."
"""

from __future__ import annotations

# Canonical values, ordered most -> least grounded in real customer data.
MEASURED = 'measured'
DERIVED = 'derived'
BENCHMARK = 'benchmark'
DEFAULT = 'default'
UNAVAILABLE = 'unavailable'

ALL_TIERS: tuple[str, ...] = (MEASURED, DERIVED, BENCHMARK, DEFAULT, UNAVAILABLE)

# Tiers that carry ANY real customer signal (as opposed to a pure
# fallback/absence). Mirrors provenance.py's TRUSTWORTHY_SOURCES role,
# but answers a display question, not a "safe to learn from" question.
REAL_SIGNAL_TIERS: tuple[str, ...] = (MEASURED, DERIVED, BENCHMARK)

_RANK = {tier: i for i, tier in enumerate(ALL_TIERS)}


def is_valid(tier: str | None) -> bool:
    """True if `tier` is one of the five canonical values."""
    return tier in ALL_TIERS


def is_real_signal(tier: str | None) -> bool:
    """True if a value has any real customer data behind it.

    False only for DEFAULT (no customer signal at all) and UNAVAILABLE
    (no value at all).
    """
    return tier in REAL_SIGNAL_TIERS


def most_conservative(tiers) -> str:
    """Return the least-grounded tier among `tiers`.

    Use when a single displayed number blends several sub-values that
    may each carry a different tier (e.g. a portfolio rollup where one
    account is measured and another is benchmark) — the honest label
    for the combined figure is the weakest of its inputs.

    Empty input -> UNAVAILABLE (nothing to blend from).
    """
    tiers = [t for t in tiers if t is not None]
    if not tiers:
        return UNAVAILABLE
    return max(tiers, key=lambda t: _RANK.get(t, _RANK[UNAVAILABLE]))


def calibration_tier(*, calibrated: bool) -> str:
    """Classify a value built from real customer data whose weighting
    depends on Wizard-C calibration state.

    This is the single most common judgment call in the outcome-ROI /
    KPI-rollup code paths this module was built for:

        calibrated=True  -> DERIVED   (real data, customer's own
                                        learned weights)
        calibrated=False -> BENCHMARK (real data, but read through
                                        default/benchmark weights
                                        because Wizard C hasn't run)

    Both branches assume real customer data was actually found — callers
    still own the DEFAULT/UNAVAILABLE decision for the "no data at all"
    case (see _get_baseline_actuals-style fallbacks in outcome_roi_api).
    """
    return DERIVED if calibrated else BENCHMARK


def label(tier: str) -> str:
    """Short human-readable label for a UI provenance badge."""
    return {
        MEASURED: 'Measured',
        DERIVED: 'Derived',
        BENCHMARK: 'Benchmark-blended',
        DEFAULT: 'Default (no customer data)',
        UNAVAILABLE: 'Unavailable',
    }.get(tier, tier or UNAVAILABLE)


class ValueProvenance(str):
    """A tier string that also carries a granular `detail` breadcrumb.

    Behaves exactly like a plain `str` equal to its tier (so existing
    code doing `data_source == 'benchmark'`, `jsonify({'data_source': x})`,
    or f-string interpolation keeps working unchanged) while giving
    callers who want it a `.tier` / `.detail` pair for logging, an
    audit-trail field, or a richer API response.

    `detail` is meant for humans/logs — e.g. "health_score_pillars_
    calibrated_stable_skip3" — and is intentionally NOT part of the
    string's identity/equality, so callers must opt in via `.detail`
    rather than accidentally branching on it.

    Example:
        >>> ds = tag(DERIVED, 'kpi_actuals_calibrated')
        >>> ds == DERIVED
        True
        >>> ds.tier, ds.detail
        ('derived', 'kpi_actuals_calibrated')
    """

    def __new__(cls, tier: str, detail: str | None = None):
        obj = str.__new__(cls, tier)
        obj.tier = tier
        obj.detail = detail if detail is not None else tier
        return obj

    def __repr__(self) -> str:  # pragma: no cover - debug aid only
        return f'ValueProvenance({self.tier!r}, detail={self.detail!r})'


def tag(tier: str, detail: str | None = None) -> ValueProvenance:
    """Build a ValueProvenance. Thin factory so call sites read as
    `value_provenance.tag(value_provenance.DERIVED, 'kpi_actuals')`
    instead of reaching for the class directly.
    """
    return ValueProvenance(tier, detail)
