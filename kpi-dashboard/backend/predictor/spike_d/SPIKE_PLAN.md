# Option D Spike Plan

**Objective.** Determine within 4 working days whether a 2-head architecture
(survival + net uplift among survivors) can replace the current 4-head
architecture (hazard + contraction + expansion_event + expansion_size)
without losing demo defensibility, identification quality, or numerical
sanity.

## Principle: parallel build, no cutover

The current 4-head model serves all production traffic during the spike.
Spike code lives entirely under `predictor/spike_d/` with its own
`features_v2.py`, `glmm_v2.py`, `inference_v2.py`, `cdi_seed_v2.py`, and
a comparison harness. No `PredictorCalibration` rows get the v2 fits — they
go to a dev-only JSON dump on disk. The decision at the end of Day 4 is to
*migrate*, not to *swap*.

## Scope

### In scope

- Net uplift outcome derived from the panel's existing `arr` column —
  no SQL panel changes (features-layer only).
- 2-head GLMM fit on the cust_395 sanity panel (single-tenant).
- 2-head inference path producing the equivalent API JSON shape.
- Side-by-side comparison on the 10 named accounts in
  `predictor/sql/g3_sanity_report__cust_395.md`.
- Fat-tail diagnostic on the net_uplift outcome.
- 2.5-head driver decomposition prototype: positive net_uplift contributors
  → expansion_drivers, negative → contraction_risks, so the API output
  remains comparable to the current `expansion_outlook` block.

### Out of scope

- API migration / consumer breakage.
- Database schema changes (PredictorCalibrationV2 table).
- Removing or deprecating any 4-head code.
- Bootstrap CI wiring (production task #4 stays in placeholder state).
- Multi-tenant fits.
- Phase 1.5 calibration on real data.

## Exit criteria — binary

The spike succeeds if and only if all six pass.

| # | Criterion | Pass condition |
|---|---|---|
| 1 | Hazard parity | `p_churn_at_horizon` within ±0.02 absolute (or ±20% relative, whichever larger) of 4-head for all 10 named accounts |
| 2 | Net uplift identification | Fit converges, `health` coefficient sign positive, ≥3 of 9 arc one-hots distinguishable from zero (\|coef\| > 1.5 × SE) |
| 3 | Fat-tail tractability | <5% of `net_arr_change_pct_h12` observations beyond ±50%, OR two-part variant resolves it |
| 4 | Numerical sanity | Hand-calculate Antares 12mo NRR through the spike's math; match API output to ±0.001 |
| 5 | Demo story preservation | Same NRR rank order across the 5 differentiation accounts (Antares, Deneb, Pegasus, Cassiopeia, Lyra); 2.5-head expansion_drivers overlap ≥50% with 4-head expansion_outlook drivers for ≥3 of 5 |
| 6 | Effort honesty | Total spike effort ≤5 working days |

## Decision matrix

| Result | Action |
|---|---|
| All 6 pass | Write Phase 1.5 migration plan and execute over a sprint |
| Exit 1 fails | Spike bug — fix before scoring others |
| Exit 2 fails | Net uplift doesn't identify on this panel size — wait for more data, keep 4-head for now |
| Exit 3 fails (`FAIL_USE_TWO_PART`) | Switch to two-part net_uplift; re-score |
| Exit 3 fails (`FAIL_KILL_SPIKE`) | Outcome too heavy-tailed; kill spike |
| Exit 4 fails | Math bug; if unfindable, kill spike |
| Exit 5 fails | Simplification costs the demo; kill spike, address 4-head identification debt separately |
| Exit 6 fails | Migration will cost more than projected; re-scope before committing |

## Day-by-day

- **Day 1.** `features_v2` + diagnostics. Histogram + Exit 3.
- **Day 2.** `glmm_v2` + `cdi_seed_v2` + first fit. Exit 2.
- **Day 3.** `inference_v2` + `run_comparison`. Exits 1, 4, 5.
- **Day 4.** `spike_d_decision.md`. Exit 6 honestly.

## What stays regardless of spike outcome

The three Phase 1 closeout fixes are architecture-independent and stay:
- `#6` (ci_method label honesty) — correct in any architecture
- `#1` (drop tenure_in_panel) — feature decision, not architectural
- `#5` (contraction symmetry) — load-bearing if 4-head; deletable if migrate to D
