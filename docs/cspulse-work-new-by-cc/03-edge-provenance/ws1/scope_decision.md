# WS-1.2 — scope decision: Account.arc_confidence and node properties.confidence

## Correction to the plan's premise (Step 0 finding)

The plan said the value from `_classify_trajectory_with_confidence()` (line 240) fans into **three** places. It fans into **two**:

1. the arc_detection node's `properties.confidence` (line 343)
2. the TRIGGERED edge's `confidence` (line 363 — now via upsert_edge, WS-1.1)

`Account.arc_confidence` (line 82) is fed by a **different classifier entirely** — `utils.arc_classifier.classify_arc()` (line 77), the 8-arc rule cascade — in a different function. Two classifiers, two confidences, same field-name family. (This matches the known "3 separate arc vocabularies" architecture note.)

## What the :240 value actually IS

A rule-match fit score: `base (0.55–0.65 by pattern) + min(|Δhealth|/20, 0.35)`, clamped to 1.0. It measures how cleanly a health-score series fits a slope shape. It is **not** an epistemic estimate of any causal claim — confirming the plan's suspicion (third instance of the typed-constant/confidence overloading class).

## The decision

Are the two NON-edge carriers in scope for WS-1?

- **Option A — extend now**: also stamp `confidence_semantics` into the arc_detection node's properties, and rename/annotate `Account.arc_confidence`. Pro: closes the overloading everywhere at once. Con: `Account.arc_confidence` is a DB column consumed by push_intelligence's live auto-trigger thresholds and by clone/display paths; touching its semantics mid-WS-1 expands a "stop the bleeding" change into a consumer-behavior change.
- **Option B — DEFER to WS-2** *(recommended)*: WS-1's stated scope is ContextEdge provenance. The edge now carries `confidence_semantics: 'trajectory_rule_match_score'` (WS-1.1). The node and the Account column are data-model semantics questions that belong with WS-2's tier/derivation schema work, where `confidence` handling is being redesigned anyway (NULL-for-inferred rule).

## Status

**Deferred to WS-2 (Option B), per the plan's own default-if-unanswered.** One improvement over a bare deferral: the arc_detection **node** written by wizard_a_journey_db sits immediately adjacent to the WS-1.1 edit and its properties dict already carries `confidence` — but it was left untouched to keep WS-1.1 strictly edge-scoped and separately revertable. Revisit both carriers in WS-2 2a alongside the `template_base` naming question (same "what does this number mean" family).
