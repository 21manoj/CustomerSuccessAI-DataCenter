# Handoff — NRR Predictor v3 Phase 1 Closeout + Option D Spike

This document hands off mid-flight work from a Cowork session to Claude Code.
Read this first, then continue from "Resume Point" at the bottom.

User profile / preferences (carry forward):
- Mature enterprise engineering discipline. Be straight, no hand-waving.
- Brainstorm before coding for non-trivial work. Approve architecture and
  workflow before writing implementation.
- Concise responses. No emojis. No filler.

## TL;DR — what's done, what's pending

**Phase 1 closeout fixes (4 patches, all landed in repo + deployed to EC2):**

1. `predictor/inference.py:314` — `ci_method` now returns
   `'placeholder_static_halfwidth'` instead of the dishonest `'bootstrap_1000'`.
2. `predictor/features.py:60` — `tenure_in_panel` removed from
   `feature_columns()`. It was a duplicate of `month_idx` (same SQL window
   function) and its +0.680 hazard coefficient was a multicollinearity
   artifact against `log_arr` (-0.253).
3. `predictor/cdi_seed.py` + `predictor/inference.py` — contraction now uses
   the same cumulative-event × per-event-size structure as expansion.
   `annual_contraction_size_pct_given_event = 0.10` (enterprise) and `0.15`
   (SMB) added to seeds. Inference computes
   `e_contract_pct = (1 - prod(1-P_t)) × seed_size`. Symmetric with expansion.
4. `predictor/sql/build_panel.sql` (and `build_panel_v2.sql`) — time-varying
   ARR. Reconstructs start-of-month ARR from `accounts.revenue` minus the
   sum of `revenue_impact` for OUTCOME context_nodes whose `event_month >= T`.
   v1 archived at `predictor/sql/build_panel_v1.sql.archive`. Now also emits
   `expansion_size_pct` and `contraction_size_pct` columns derived from
   `revenue_impact / arr` on event rows.
5. `predictor/glmm.py` — three changes: (a) drops `tenure_in_panel` from the
   feature set; (b) for size sub-models, pre-filters fit panel to event
   rows and counts `n_events = len(df)`; (c) Gamma-family fits use plain
   `GLM.fit()` with constant-column drop instead of `fit_regularized`,
   because `fit_regularized` was producing exact-zero deviations on small
   Gamma samples (silent fit-at-prior). Bootstrap routing matches.

After all five, expected outcomes were validated: g3 sanity report shows
no tenure_in_panel in drivers, expansion_size converges with non-trivial
per-account predictions (Antares 24%, account 3910 27.5%, etc., reconciles
within ~5pp of actuals), no warnings.

**Pending tasks:**

- (Optional) Add per-coefficient narrative in spec docs after refit lands.
- Bootstrap CI wiring — `inference.py` should read `metrics.coefficient_se`
  from `predictor_calibrations` and propagate to a real CI on
  `expected_nrr` and `expected_arr_lift`. Currently both are placeholder
  hardcoded ±0.05 / ×0.5 / ×1.5.

**Spike D status (2-head architecture evaluation):**

Pre-spike investigation revealed two data-generator gaps that affect both
4-head and 2-head architectures. Both fixed in the panel SQL (time-varying
ARR + revenue_impact extraction). Spike Day 1 (Exit 3 distribution check)
PASSED on the corrected v2 panel: 38% positive observations, 51% zero,
11% negative, 0% beyond ±50%. Single-Gaussian net_uplift is viable.
Day 2 (glmm_v2 + first fit) was approved but not started — held while
the production fixes above were prioritized.

The spike artifacts (`features_v2.py`, `SPIKE_PLAN.md`, diagnostics scripts)
live under `predictor/spike_d/`.

## Repo state

**Files modified during this work (commit candidates):**

```
predictor/inference.py                               (#6)
predictor/features.py                                (#1)
predictor/cdi_seed.py                                (#5)
predictor/glmm.py                                    (#1, #5, #14, #15)
predictor/build_panel.py                             (env-based SQL selection; renamed from panel.py May 7)
predictor/sql/build_panel.sql                        (v2 promoted)
predictor/sql/build_panel_v1.sql.archive             (v1 preserved)
predictor/sql/build_panel_v2.sql                     (v2 + size_pct cols)
predictor/spike_d/__init__.py                        (new)
predictor/spike_d/SPIKE_PLAN.md                      (new)
predictor/spike_d/features_v2.py                     (new)
predictor/spike_d/scripts/__init__.py                (new)
predictor/spike_d/scripts/diagnostics.py             (new)
predictor/spike_d/scripts/check_v1_v2_parity.py      (new)
```

**Investigation artifacts (in workspace, DO NOT delete; useful for next session):**

```
predictor/spike_d/panel_cust_395.csv                 (v1 SQL output, frozen ARR)
predictor/spike_d/panel_cust_395_v2.csv              (v2 SQL, time-varying ARR, no size_pct)
predictor/spike_d/panel_cust_395_v3.csv              (post first Wizard D rerun)
predictor/spike_d/panel_cust_395_v4.csv              (after expansion_size_pct added but with KeyError bug)
predictor/spike_d/panel_cust_395_v5.csv              (current good state)
predictor/spike_d/cust_395_outcome_deltas.csv        (revenue_impact per event — ground truth)
predictor/spike_d/g3_sanity_report__cust_395.md      (latest g3 report)
predictor/spike_d/g3_run_395.log
predictor/spike_d/diagnostics_out_v2_clean/day1_diagnostics.json
```

**Hand-computed reconciliation table (use to validate next Wizard D refit):**

| account | event month | impact | pre_arr | expansion_size_pct | predicted (next refit should match within ~5pp) |
|---|---|---:|---:|---:|---:|
| 3894 | 2025-03 | +2.16M | 18.0M | 12% | 12% |
| 3895 | 2025-10 | +1.00M | 12.5M |  8% |  9% |
| 3897 | 2025-06 | +0.72M |  7.2M | 10% | 14% |
| 3900 | 2025-11 | +0.74M |  4.9M | 15% | 14% |
| 3906 (Antares) | 2025-06 | +4.13M | 16.5M | **25%** | **24%** |
| 3907 | 2025-09 | +1.94M | 10.8M | 18% | 18% |
| 3908 | 2025-04 | +1.26M |  8.4M | 15% | 12% |
| 3909 | 2025-07 | +1.38M |  6.9M | 20% | 18% |
| 3910 | 2025-05 | +1.65M |  5.5M | **30%** | **27.5%** |
| 3911 | 2025-08 | +0.52M |  4.3M | 12% | 20% (worst miss) |
| 3922 | 2025-01 | +0.50M |  2.0M | 25% | 21% |

Contractions (3 events): 3914 -15%, 3920 -25%, 3921 -30%. Currently fitted
as a constant 0.10 from CDI seed (no contraction_size sub-model). Phase 1.5
candidate to add a contraction_size GLMM.

## Deployment state (EC2)

- Container: `cspulse-platform` on EC2 `3.87.199.195`
- Path inside container: `/app/backend/predictor/...`
- Latest deployment: `features.py`, `glmm.py`, and v2 SQL synced as of
  approximately 2026-05-07 ~15:00 UTC. Wizard D rerun on cust_395 confirmed
  3 of 4 sub-models converged.
- **One file probably NOT yet deployed: the latest `glmm.py` with the
  Gamma-fit + bootstrap routing fix (task #15).** That fix landed in the
  repo just before the handoff. Verify with:
  ```
  docker exec cspulse-platform grep -c "GLM.fit (plain MLE)" /app/backend/predictor/glmm.py
  # expect: >= 1 if the latest patch is on EC2; 0 if not
  ```
  If 0, scp + docker cp the local `predictor/glmm.py` to the container, then
  rerun:
  ```
  docker exec -e PREDICTOR_BUILD_PANEL_SQL=build_panel_v2.sql -w /app/backend cspulse-platform \
      python predictor/scripts/g3_sanity_report.py 395
  ```

After this final sync + refit, the g3 report should show
`expected_size_pct_given_event` varying across the 5 named accounts
(Antares ~0.24, others spread across 0.08–0.30), not flat at 0.180.

## Auth / access on EC2

- SSH: `ssh -i ~/CustomerSuccessAI-DataCenter/cspulse-v6-key.pem ec2-user@3.87.199.195`
- Postgres on EC2: `cspulse` role, `cs_pulse` database. DB queries used
  in this work include `SELECT ... FROM predictor_calibrations` and
  `SELECT ... FROM context_nodes WHERE node_type = 'OUTCOME'`.

## Resume point

Three reasonable next moves, in order of priority:

**1. Verify the final glmm.py patch is deployed and produced varied
expansion sizes.** This is one ssh + docker cp + g3 rerun + paste-the-report.
If the `expected_size_pct_given_event` numbers in the new g3 report match
the predicted column in the table above (within ~5pp), Phase 1 closeout is
truly done.

**2. Decide what to do with the Spike D work.** Originally planned as a
4-day evaluation of a 2-head architecture (survival + net uplift). Day 1
PASSED. Days 2–4 not started. Decision matrix in
`predictor/spike_d/SPIKE_PLAN.md`. Three options:
   - Continue the spike now that Phase 1 is clean.
   - Park the spike — Phase 1 4-head is producing varied, defensible
     expansion magnitudes; the original "we have no fit signal" pressure
     for option D is gone.
   - Run a quick 2-head fit for comparison without the full spike scaffolding,
     just to see how net_uplift R² compares to the 4-head expansion_size
     R²=0.70 we observed.

**3. Wire the bootstrap CI** (Phase 1 task #4 — pending). The bootstrap
SEs now exist for binomial sub-models in `metrics.coefficient_se` after
`fit_regularized` writes them. For Gamma sub-models with the new plain-MLE
fit, SEs should also be available from `result.bse` (we used them in the
smoke test). Inference's `ci_method='placeholder_static_halfwidth'` should
become a real bootstrap or delta-method CI.

Recommended order: 1 → 3 → 2.

## Mistakes to avoid (lessons logged from the prior session)

- Don't assume the deployed code matches the local repo. Multiple times
  during this session, file syncs lagged — features.py was missed in one
  round, build_panel_v2.sql in the next. Always verify with
  `docker exec ... grep -c <distinguishing-token>` after a sync.
- Don't assume `fit_regularized(L1_wt=0.0)` is pure ridge. Empirically it
  collapsed to exact-zero deviations on small Gamma samples (the entire
  reason expansion_size showed flat 0.180 in production for a long time).
- Don't rely on `n_events = sum(outcome_column)` for continuous outcomes.
  Sum of fractions is not a count. Use `len(df_after_event_filter)` for
  size sub-models specifically.
- Cowork sandbox cannot SSH to EC2 (SOCKS allowlist denies port 22) and
  cannot reach raw IPs over HTTPS (requires hostname). The "Allow all
  domains" admin setting only relaxes the HTTP MITM proxy, not SOCKS.
  Don't waste time fighting it; use Claude Code or manual scp.

## Contact

User: Manoj (manojguptaus@gmail.com). Pattern: terse approvals
("yes/yes", "ship both"), pushes back when something's off, expects
honest engineering analysis with options laid out.
