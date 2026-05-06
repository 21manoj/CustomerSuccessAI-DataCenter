# Block 5 — Wizard B Coexistence Audit

*Generated 2026-05-06 (Phase 1 final block).*

Per PLAN_nrr_predictor_v3.md A3 hard rule:

> **Never render Wizard B's `forecast_portfolio_nrr()` output and predictor v3 output on the same dashboard screen.**

Block 5 audit grep across `kpi-dashboard/src/` for the Wizard-B-legacy NRR field names. Each remaining reference must be either (a) replaced with a predictor v3 call, or (b) gated by `!FEATURE_PREDICTOR_V3_UI` (the demo gate `customer_id !== 395` until the toggle ships).

## Surfaces audited

### `src/components/dashboard/CFODashboard.tsx`

| Line | Reference | Status |
|---|---|---|
| 986, 992 | `wb.with_interventions_nrr_pct` (legacy Wizard B forecast inside the existing tile) | **GATED** — wrapped in `session?.customer_id !== 395 && (...)` per Block 3 day 3 commit |

CFODashboard correctly swaps when the demo gate trips. **Phase 1 OK.**

### `src/components/dashboard/NRRDashboard.tsx`

| Line | Reference | Status |
|---|---|---|
| 41 | `with_interventions_nrr_pct` (interface field) | UNGATED |
| 162, 164, 205, 224 | computed legacy delta | UNGATED |

NRRDashboard renders Wizard B legacy NRR unconditionally. **Phase 1.5 cleanup target** per A4 — should migrate to `PredictorV3Tile` or its own predictor v3 component when the dashboard is migrated. Out of Phase 1 scope (Phase 1 ships predictor v3 swap on CFO dashboard only).

### `src/components/journey-visualizer/JourneyIntelligenceView.tsx`

| Line | Reference | Status |
|---|---|---|
| 61, 63 | `without_cs_pulse_nrr_pct` / `with_interventions_nrr_pct` (interface) | UNGATED |
| 548–552 | Computed `withoutShiftPp` / `withShiftPp` from Wizard B forecast | UNGATED |
| 832–833 | Legacy organic-NRR badge in chart annotation | UNGATED |

Same as above — **Phase 1.5 cleanup target.** The Journey Intelligence view shows Wizard B's full forecast trajectory; migrating it to predictor v3 is more substantial than the CFO swap (different chart shape).

### `src/components/dashboard/CRODashboard.tsx`

No legacy NRR field references found in audit grep — this dashboard reads other API endpoints. **OK.**

## Required Phase 1 cleanup (none)

No remaining Wizard B legacy refs on the CFO dashboard surface that's targeted for Phase 1 demo. The swap is in place.

## Phase 1.5 cleanup tracker (queued)

Per A4 (Wizard B cleanup deliverable), once Phase 1.5 structural acceptance signs off, a single PR titled `cleanup(wizard-b): remove forecast/attribution code superseded by predictor v3` lands. That PR's frontend portion should also handle these surfaces:

- [ ] Migrate `NRRDashboard.tsx` to consume `/api/v1/predictor/customer/<id>/...` endpoints (or wrap in PredictorV3Tile)
- [ ] Migrate `JourneyIntelligenceView.tsx`'s NRR-trajectory rendering to consume predictor v3 output
- [ ] Verify no other dashboards added new Wizard B legacy refs while Phase 1.5 was running

## Backend coexistence

Per A3 + A4, Wizard B's `forecast_portfolio_nrr()` continues to run in Phase 1 (so the rollback path works — frontend can fall back to legacy on `FEATURE_PREDICTOR_API=false`). Phase 1.5 deletes Wizard B's NRR computation per the contractual deletion list in A4.

No backend changes needed in Block 5 — the legacy and v3 codepaths are fully independent (different modules, different DB tables, different API endpoints).

## Verdict

**Block 5 audit: PASS for Phase 1 scope.** CFO dashboard swap working, no leakage, Phase 1.5 cleanup tracker queued.
