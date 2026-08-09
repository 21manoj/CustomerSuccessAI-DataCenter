# Dual-Horizon Early Warning — Positioning & Design Note

**Status:** design clarification / positioning decision-in-progress. Parked for
later; this note is the durable record so we don't re-derive it.
**Date:** 2026-08-07.

## Why this note exists

"Early warning" in CS Pulse is one term doing **two jobs across two time
horizons**, produced by two different engines. That overlap is confusing — to us,
and (more dangerously) to a buyer who can't tell which claim they're hearing. The
architecture is sound; the *naming and the claims* are what need discipline. This
note fixes the vocabulary, splits the buyer claim, and records the two live gaps
that currently make both claims unsupported.

## The two engines (verified against code)

| | **Wizard B** — backward lens | **Wizard D** — forward lens |
|---|---|---|
| File | `kpi-dashboard/backend/wizards/wizard_b_pattern_db.py` ("DB-Native Pattern Analysis") | `kpi-dashboard/backend/wizards/wizard_d_predictor_calibrator.py` ("NRR Predictor v3"; inference in `backend/predictor/`) |
| Operates on | accounts with **known** outcomes (history) | **live** accounts (outcome not yet realized) |
| NRR output | (1) **realized NRR** that actually happened + (2) **counterfactual** — "what NRR CS Pulse would have protected" | **forecast NRR** (projected trajectory) |
| Early-warning flavor | **retrospective** — "had CS Pulse been running, it would have flagged this churn ~16 weeks early" | **prospective** — "we predict this live account is heading to churn, weeks ahead" |
| Job to be done | **prove** the value (on data the buyer can verify) | **run** the value (going forward) |

Both legitimately emit an "early warning." B's is **provable on history**; D's is
**predicted about the future**. Same word, opposite time directions — that is the
entire source of confusion.

## The naming convention (apply everywhere: code, dashboards, decks, model register)

Never say "early warning" without a **horizon qualifier**:

- **Wizard B → Hindsight Early Warning** (a.k.a. *Retrospective / Counterfactual*):
  "would-have-warned," demonstrated on realized outcomes.
- **Wizard D → Foresight Early Warning** (a.k.a. *Predictive*): "predicting," on
  live accounts.

("Hindsight / Foresight" for external/deck use; "Counterfactual / Predictive" for
technical use.)

**This maps onto the two-layer model we already sell.** Our core differentiator is
LEADING (signals) vs TRAILING (KPI rollup). Wire the two early-warnings to it so
the split reads as intentional:

- **Wizard B = the TRAILING lens** — realized NRR + the counterfactual overlay
  (Hindsight EW).
- **Wizard D = the LEADING lens** — forecast NRR + the live forward signal
  (Foresight EW).

## The two buyer claims (split them; each has its own evidence bar)

The confusion becomes a **credibility risk** when "16 weeks early" is stated
without saying which horizon it is — the two have very different evidentiary
weight.

1. **Hindsight claim (Wizard B):** *"On your last 12 months, CS Pulse would have
   surfaced N of these churns ~16 weeks before they happened."*
   → Evidence bar: a counterfactual backtest on the buyer's **own historical
   data**. The strongest possible proof — *if the detection actually runs.*
2. **Foresight claim (Wizard D):** *"CS Pulse flags live accounts heading to
   churn, weeks ahead."*
   → Evidence bar: the predictor **calibrated** (not `cold_start`) **and** enough
   real labeled outcomes accrued to measure forward accuracy.

## The two live gaps (why *neither* claim is fully backed today)

- **Wizard B counterfactual detection is effectively dead.** The 3-vocabulary arc
  mismatch (manifest `story_arc` labels → `ARC_TEMPLATES` → the classifier's
  canonical arcs) means the churn-pattern the detection keys on is silently
  reclassified, so the "would-have-warned" signal never fires. → the **Hindsight
  claim — our most provable — is currently ungenerated.** *Fix this first.* See
  the `roadmap_wizard_b_early_warning_dead_code` finding; partial mitigation in
  commit `868479ed2` (`silent_churn` seed).
- **Wizard D degrades to `cold_start` without recalibration.** Unless the
  post-load `trigger_wizard_d_recalibration` step runs, the predictor returns
  CDI seed priors, not a tenant-fit forecast. → the **Foresight number is a
  placeholder** until calibrated (and unproven until real outcomes exist).

## Governance (Module 10 model register)

Track them as **two distinct model cards**, each with its own *Independent
Validator*, *Drift Monitor*, and *Known Limitations*:

- **MOD — Retrospective Early Warning (Wizard B / Pattern Analysis).** Known
  limitation *today*: detection dead via arc-vocabulary mismatch; do not make the
  Hindsight claim until it fires and a backtest lead-time is measured.
- **MOD — Predictive Early Warning (Wizard D / NRR Predictor v3).** Known
  limitation *today*: `cold_start` without recalibration; forward accuracy
  unproven until labeled outcomes accrue (renewal-probability model is on a
  3-bucket lookup pending ≥50 labeled outcomes).

This is the mechanism that stops "16 weeks early" from reaching a deck before its
specific evidence exists.

## Recommended actions (when we come back to this)

1. **Adopt the horizon naming** (Hindsight / Foresight) across code, dashboards,
   decks, and the model register; wire to the leading/trailing two-layer model.
2. **Rewrite the buyer claim** as the two separate, horizon-labeled statements
   above, each with its evidence bar stated.
3. **Fix Wizard B's dead detection first** (the arc-vocabulary mismatch) — it
   unlocks the Hindsight claim, which is the strongest and the one that's broken.
4. **Make Wizard D recalibration a required onboarding step** (not optional) so
   the Foresight number is never a silent `cold_start` placeholder.
5. **Create the two model-register entries** with their current Known Limitations.

## Provenance

Verified 2026-08-07 against HEAD `6257b7a98`:
`kpi-dashboard/backend/wizards/wizard_b_pattern_db.py` (Pattern Analysis),
`wizards/wizard_d_predictor_calibrator.py` (NRR Predictor v3 offline calibration),
`backend/predictor/` (online inference). The dead-detection finding is
`roadmap_wizard_b_early_warning_dead_code` (Aug 3 2026) + the arc-vocabulary
mismatch documented in `consulting-framework/modules/11-ops-loaddriver-testing.md`
(Gotcha 1). The `cold_start` behavior is documented in
`consulting-framework/ONBOARDING_RUNBOOK.md` (step 5) and `load-driver/cs_pulse_driver.py`.
The two-layer LEADING/TRAILING model is the platform's stated core differentiator.
