# 08-UI — Component Kit & UX Patterns

**Layer:** Interface (companion to Module 08 — 08 owns the dashboard *payload*, 08-UI owns the *pixels below composition*)

**Status:** ✅ Validated (pure-logic scope) — see [Validation Note](#validation-note).
A spec-only fresh-agent rebuild (2026-08-07, Node `node:test`) proved five defects
in the pure-logic contracts — headlined by the entitlement guard failing **open**
on any unknown feature (`indexOf(-1)` grants everyone), the exact opposite of its
stated purpose — all fixed below. This module's validation is **narrower than the
backend modules'** by design: its testable core is the pure-logic contracts (band
classification, the threshold-shape guard, entitlement resolution, the data-state
decision, `money` basis, read-not-sum, the anti-drift check); React *rendering
fidelity* is intentionally out of scope.

## Purpose

Give an FDE a **contract-bound, composable UI kit** — design tokens, primitives,
and domain patterns typed against the Module 08 payload — so the only bespoke
work per client is *arrangement + brand + copy*. The kit's whole value is that
each concern has exactly **one** source of truth that is actually wired and
testable: one health-band classifier, one threshold loader, one data-state
decision, one entitlement gate. The origin frontend is the cautionary opposite —
a "central" threshold util that is effectively a dead 70/50 constant because its
fetch is never called, fifteen-plus components with their own local
`getHealthColor`, three healthy cutoffs (80/75/70) inside a single file, mock data
silently shown as real, and an entitlement guard that fails open. This module
replaces that sprawl with a substrate an FDE composes but does not rebuild, and
whose contracts a test can prove.

## Boundary

**Owns:**
- **Design tokens**: the health-band palette (as *tokens*, not per-component
  colors), typography, spacing, light/dark — swappable per brand.
- **Primitives**: `StatTile`, **a single `HealthBadge`** (score→band→color through
  the one classifier), `Meter`, `Sparkline`, `ScopeChip`, `DataState`,
  `KanbanCard`, `ProvenanceBadge`.
- **The one health-band classifier + the one threshold loader**: `bandFor(score)`
  reading thresholds from a source that is actually loaded at boot (not a
  never-called fetch), behind a runtime shape guard (Gotchas 1, 2, 3).
- **The `DataState` system**: loading / empty / error / partial — always
  *labeled*, and it never substitutes mock for missing data (Gotchas 4, 5, 7).
- **Domain patterns** typed against the Module 08 payload: `TwoLayerHealthPanel`,
  `RevenueAtRiskPanel`, `L4PortfolioRollup`, `AccountHealthTable`,
  `SignalTimeline`, `NRRDualLens`.
- **The app shell**: routing, a **fail-closed** `EntitlementGuard`, the
  per-persona data hook (one fetch path), and the `arr_basis`-aware money
  formatter (Gotchas 6, 8).
- **The anti-drift meta-check**: a test that no component defines a local
  health-color helper or hardcodes a band threshold — everything routes through
  `bandFor` (Gotcha 3).

**Explicitly does not own:**
- The **persona compositions** (CRO/CFO/VPCS/CSM page layouts) — Config, arranged
  by the FDE per client. A pattern that hardcodes one persona's copy has leaked
  out of the kit.
- Any number's **computation** — Module 08 (payload) and its upstreams. The kit
  *renders* the payload; it derives nothing.
- **Auth/entitlement enforcement as security** — the guard is a UX affordance
  only; real enforcement is server-side (Module 07). The guard failing closed is
  about not *showing* locked features, not about access control (Gotcha 6).

## Dependencies

- **Module 08 (Persona Dashboards):** the payload envelope (`scope`, `persona`,
  `mode`, `arr_basis`, `arr_basis_value`, `trailing{}`, `leading{}`, `churn{}`,
  `accounts`). The kit's TS types are generated from / locked to this; a payload
  change becomes a compile error, not a silent mislabel.
- **Module 03 (Scoring) / centralized thresholds:** the canonical
  `health_thresholds` values (70/50) `bandFor` binds to — loaded once, one shape.
- **Module 07 (MCP/API):** the endpoints the per-persona hook calls and the
  entitlement feature flags the guard reads. Enforcement is server-side there.

### Data Shapes

```
Thresholds (ONE canonical shape — a malformed shape must fail loud, not classify
everything healthy, Gotcha 2):
  { healthy: {min: 70}, at_risk: {min: 50}, critical: {min: 0} }

Band = "healthy" | "at_risk" | "critical" | "no_data"

DataState<T> (what the per-persona hook returns — never a bare T):
  { status: "loading" | "ok" | "empty" | "error" | "partial",
    data: T | null,           # null unless status ∈ {ok, partial}
    degraded: bool,           # true for empty/error/partial — the UI labels it
    reason: string | null }   # e.g. "3 of 12 accounts failed to load"
  # There is no "mock" status: mock data is never substituted for missing data.

Entitlement decision:
  { allowed: bool, requiredTier: Tier | null }
  # Resolved from session.tier — a MISSING tier resolves to the LEAST-privileged
  # tier, never the most (Gotcha 6).
```

## Engine vs. Config

**Engine (build once):** the token *structure*, all primitives, `bandFor` + the
threshold loader + shape guard, `DataState`, the domain patterns, the shell +
fail-closed guard + per-persona hook, the money formatter, and the anti-drift
meta-check.

**Config (an FDE fills in per client):** the token *values* (brand palette,
fonts), which persona pages exist and how patterns are arranged, tile copy, the
feature/entitlement catalog, and the threshold values (from Module 03).

## Build Prompt

> Build the component kit. Six numbered pieces, in TypeScript/React (the origin is
> Create-React-App under `kpi-dashboard/src/`; there is no `frontend/` dir). Every
> helper is defined below OR is one of these named external hooks: `apiCall` (the
> Module 07 client), `useSession`/`useState`/`useEffect` (session + React),
> `Payload` (the Module 08 payload type), `fetchPersona(customerId, persona) ->
> {payload, failures, total}` (the per-persona fetch impl piece 5 wraps),
> `renderApp()` (the app's render entry, called after `loadThresholds`), and the
> scanner pair `read(file)` / `isKitFile(file)` (fs read + "is this file part of
> the kit package") used by the piece-6 audit. The presentational leaves
> (`Skeleton`, `ErrorState`, `EmptyState`, `DegradedBanner`, `StatTile`,
> `UpsellCard`, `TrailingHealth`, `LeadingSignals`) are the kit's own display
> primitives; their JSX rendering is out of scope for validation (see Validation
> Note), but each consumes only the props shown. The kit RENDERS the payload; it
> computes no score, revenue, or classification of its own. The load-bearing rule:
> **each concern has exactly one implementation that is actually wired** — a second
> local copy, or a "central" helper nothing calls, is the defect this module exists
> to replace.
>
> Origin references (patterns to fix, not copy): `src/utils/healthThresholds.ts`
> (the dead-fetch util), `src/components/shared/` (StatusBadge/MetricCard/
> ProgressBar/EmptyState/DataState primitives), `src/components/shared/EntitlementGuard.tsx`
> + `src/hooks/useEntitlement.ts` (the fail-open guard), `src/components/csm/CSMFocusFlow.tsx`
> (mock-as-real), `src/components/dashboard/views/SignalTimelineView.tsx` (false-empty
> fan-out), `src/components/CSPlatform.tsx` (three color schemes).
>
> 1. **Tokens + the one band classifier + a wired, shape-guarded loader.** Health
>    bands are tokens; `bandFor` is the only classifier; thresholds are loaded once
>    and validated so a malformed response fails loud instead of classifying every
>    score `healthy` (Gotchas 1, 2):
>    ```ts
>    // tokens: health bands live in the token layer, not per-component
>    const BAND_TOKENS = { healthy: "var(--band-healthy)",
>                          at_risk: "var(--band-at-risk)",
>                          critical:"var(--band-critical)",
>                          no_data: "var(--band-no-data)" };
>
>    function assertThresholdShape(t: unknown): Thresholds {
>        const ok = t && ["healthy","at_risk","critical"].every(
>            k => typeof (t as any)?.[k]?.min === "number");
>        if (!ok) throw new Error("malformed thresholds — refusing to classify");  // fail loud
>        return t as Thresholds;
>    }
>    // The literal fallback — defined here, so bandFor works before loadThresholds
>    // runs and if a load ever fails. Config: an FDE may retune to match Module 03.
>    const DEFAULT_THRESHOLDS: Thresholds = {healthy:{min:70}, at_risk:{min:50}, critical:{min:0}};
>    let THRESHOLDS: Thresholds | null = null;
>    async function loadThresholds() {                 // CALLED at app boot (piece 4)
>        THRESHOLDS = assertThresholdShape(await apiCall("/config/health-thresholds"));
>    }
>    function bandFor(score: number | null): Band {
>        if (score === null || score === undefined) return "no_data";  // NOT 50, NOT a guess
>        const t = THRESHOLDS ?? DEFAULT_THRESHOLDS;   // defaults are a real fallback, not the only path
>        if (score >= t.healthy.min)  return "healthy";
>        if (score >= t.at_risk.min)  return "at_risk";
>        return "critical";
>    }
>    ```
>
> 2. **Primitives — each bound to the one classifier.** `HealthBadge` is the ONLY
>    score→band→color mapping; no component defines its own (Gotcha 3). `DataState`
>    renders a labeled state and never swaps in mock (Gotcha 4):
>    ```ts
>    function HealthBadge({score}: {score: number | null}) {
>        const band = bandFor(score);                  // the one classifier
>        return <span style={{color: BAND_TOKENS[band]}} data-band={band}>
>                 {band === "no_data" ? "—" : Math.round(score!)}</span>;
>    }
>    function DataState<T>({state, children}: {state: DataState<T>, children: (d:T)=>JSX}) {
>        if (state.status === "loading") return <Skeleton/>;
>        if (state.status === "error")   return <ErrorState reason={state.reason} labeled/>;
>        if (state.status === "empty")   return <EmptyState labeled/>;   // labeled, not mock
>        // "partial" renders data WITH a visible degraded banner (Gotcha 7)
>        return <>{state.degraded && <DegradedBanner reason={state.reason}/>}
>                 {children(state.data as T)}</>;
>    }
>    ```
>
> 3. **Domain patterns — typed against the payload, deriving nothing.**
>    `RevenueAtRiskPanel` reads the bundle field, never sums accounts (Module 08
>    Gotcha 2); `TwoLayerHealthPanel` renders leading and trailing independently
>    (no health gate on signals); money always carries its basis (Gotcha 8):
>    ```ts
>    function RevenueAtRiskPanel({p}: {p: Payload}) {
>        // read the single-source figure; there is no accounts.reduce(sum) here
>        return <StatTile label="Revenue at risk"
>                 value={money(p.leading.confirmed_risk, p.arr_basis, p.arr_basis_value)}/>;
>    }
>    const fmt = (n: number) =>
>        new Intl.NumberFormat("en-US", {style:"currency", currency:"USD",
>                                        notation:"compact", maximumFractionDigits:1}).format(n);
>    function money(v: number, basis: string, basisVal: number) {
>        // Render BOTH the basis label AND its value — two same-labeled figures
>        // scaled to different baselines are disambiguated only by basisVal (Gotcha 8).
>        return `${fmt(v)} · ${basis} (${fmt(basisVal)})`;
>    }
>    function TwoLayerHealthPanel({p}: {p: Payload}) {
>        return <><TrailingHealth data={p.trailing}/>   // KPI rollup
>                 <LeadingSignals data={p.leading}/></>; // signals — NOT filtered by trailing
>    }
>    ```
>
> 4. **App shell + fail-closed entitlement + boot.** `loadThresholds()` runs at
>    boot; the guard defaults a MISSING tier to the least privilege and every
>    persona route is guarded (Gotchas 1, 6):
>    ```ts
>    const TIER_ORDER = ["free", "starter", "growth", "enterprise"];  // least→most
>    const FEATURE_CATALOG: Record<string, Tier> = {};  // Config: FDE fills feature -> required tier
>    function resolveTier(session): Tier {
>        return session?.tier ?? TIER_ORDER[0];        // missing => LEAST privilege (fail closed)
>    }
>    function useEntitlement(feature): {allowed:boolean, requiredTier:Tier|null} {
>        const tier = resolveTier(useSession());
>        const need = FEATURE_CATALOG[feature];        // required tier for this feature
>        const needIdx = TIER_ORDER.indexOf(need);
>        if (needIdx === -1)                           // unknown feature / off-catalog tier:
>            return {allowed: false, requiredTier: need ?? null};  // DENY (fail closed), not grant
>        return {allowed: TIER_ORDER.indexOf(tier) >= needIdx, requiredTier: need};
>    }
>    function EntitlementGuard({feature, children}) {
>        const {allowed, requiredTier} = useEntitlement(feature);
>        return allowed ? children : <UpsellCard requiredTier={requiredTier}/>;
>    }
>    // Route table: EVERY persona route is wrapped — no unguarded landing alias.
>    async function boot() { await loadThresholds(); renderApp(); }
>    ```
>
> 5. **The per-persona data hook — one fetch path that distinguishes empty from
>    failure (Gotcha 7).** Returns a `DataState`, never a bare payload; a
>    fan-out where some calls fail is `partial`, not a false `empty`:
>    ```ts
>    const isEmpty = (p) => !p || !p.accounts || p.accounts.length === 0;  // no renderable rows
>    function usePersonaDashboard(customerId, persona): DataState<Payload> {
>        const [state, set] = useState({status:"loading", data:null, degraded:false, reason:null});
>        useEffect(() => { (async () => {
>            try {
>                const {payload, failures, total} = await fetchPersona(customerId, persona);
>                const empty = isEmpty(payload);
>                // Order matters: all-failed -> error; any failure -> partial (even if the
>                // survivors are empty, so the degraded banner still shows); then a genuine
>                // zero-failure empty; else ok.
>                if (failures === total)   set({status:"error", data:null, degraded:true,
>                                               reason:"all sources failed"});
>                else if (failures > 0)    set({status:"partial", data: empty ? null : payload,
>                                               degraded:true,
>                                               reason:`${failures} of ${total} sources failed`});
>                else if (empty)           set({status:"empty", data:null, degraded:true, reason:null});
>                else                      set({status:"ok", data:payload, degraded:false, reason:null});
>            } catch(e) { set({status:"error", data:null, degraded:true, reason:String(e)}); }
>        })(); }, [customerId, persona]);
>        return state;                        // a swallowed partial failure is 'partial', not 'empty'
>    }
>    ```
>
> 6. **Anti-drift meta-check (a test, Gotcha 3).** The kit governs its own reuse:
>    a test that fails if any component outside the kit defines a local
>    health-color helper or hardcodes a band threshold:
>    ```ts
>    // scan component source; the kit is the ONLY place bands are classified.
>    function auditNoLocalHealthColors(srcFiles): string[] {
>        if (srcFiles.length === 0) throw new Error("scanned 0 files — broken audit");  // anti-vacuous
>        const offenders = [];
>        for (const f of srcFiles) {
>            const s = read(f);
>            if (/function\s+getHealth(Color|Status)/.test(s) ||
>                /health\w*\s*[<>]=?\s*(70|75|80|50)\b/.test(s))
>                if (!isKitFile(f)) offenders.push(f);   // a local classifier/threshold outside the kit
>        }
>        return offenders;                                // empty == everyone uses bandFor
>    }
>    ```

## Acceptance Criteria

- **`bandFor` boundaries, from one source (Gotchas 1, 3).** `bandFor(49)`→critical,
  `(50)`→at_risk, `(69)`→at_risk, `(70)`→healthy, `(null)`→no_data. Changing the
  loaded thresholds moves the boundaries; assert `bandFor` reads `THRESHOLDS`, and
  that a real `50` classifies as a score (`at_risk`), while `null` is `no_data` —
  never `50` as a no-data stand-in.
- **The loader is wired and shape-guarded (Gotchas 1, 2).** Assert `loadThresholds`
  is called at boot (a kit where the fetch is never invoked is the origin bug —
  a test that the boot path calls it). Assert `assertThresholdShape` throws on a
  malformed response (e.g. a flat `{healthy_min:70}` or a `{thresholds:{...}}`
  wrapper) rather than letting `t.healthy.min` be `undefined` and classifying
  every score `healthy`.
- **DataState never substitutes mock (Gotchas 4, 5).** For `empty` and `error`,
  the kit renders a *labeled* state; assert there is no code path that returns
  fabricated data for an empty/failed fetch. Assert the kit ships **no** unused
  mock blob (a defined-but-unreferenced `FALLBACK_DATA` is a finding).
- **Partial failure is not a false empty (Gotcha 7).** Given a fan-out where some
  per-account calls fail and the rest return data, the hook yields
  `status="partial"` with a `reason`, not `status="empty"`. Assert an all-fail
  fan-out is `error`, and a genuine no-data (zero failures) is `empty` — three
  distinct outcomes.
- **Entitlement fails closed (Gotcha 6).** `resolveTier(session={})` returns the
  least-privileged tier, not `enterprise`; a feature needing `growth` is denied
  for a missing-tier session. Assert every persona route is wrapped by
  `EntitlementGuard` (no unguarded landing alias). Assert (in prose/test) that the
  guard is UX-only and does not stand in for server-side enforcement.
- **Money always carries its basis (Gotcha 8).** `money(v, basis, basisVal)`
  renders the `arr_basis` alongside the figure; assert a dollar tile without a
  basis is a finding (the origin renders dollars with no basis at all).
- **Revenue is read, not summed (Module 08 parity).** `RevenueAtRiskPanel` reads
  `p.leading.confirmed_risk`; assert no code path sums `p.accounts` into a revenue
  figure.
- **Anti-drift audit bites (Gotcha 3).** `auditNoLocalHealthColors` flags a
  component defining `getHealthColor` or comparing `health >= 75` outside the kit,
  passes when all classification routes through `bandFor`, and raises on zero
  files scanned (anti-vacuous).

## Reference Test Harness

The testable core is pure logic and can be unit-tested (Jest in the origin, or the
logic ported to any runner); React *rendering fidelity* is out of scope for the
adversarial rebuild (see Validation Note).
1. **`bandFor` table** — the boundary matrix incl. `null` vs real `50`, and a
   threshold-change moving the boundaries.
2. **Shape guard** — the three real endpoint shapes (`{healthy:{min}}`,
   `{healthy_min}`, `{thresholds:{...}}`); assert the first is accepted and the
   other two throw rather than silently classifying all-healthy.
3. **DataState decision** — the {ok, empty, error, partial} truth table from the
   hook; a mutation that returns mock on empty must be catchable.
4. **Entitlement fail-closed** — missing tier → least privilege; a mutation to
   `?? "enterprise"` must flip a denial to an allow (proving the default matters).
5. **Anti-drift audit** — a fixture component with a local `getHealthColor`
   (flagged) and one using `HealthBadge` (clean); zero-files raises.
6. **Read-not-sum** — stub the payload; assert `revenue at risk` equals the bundle
   field, not the account sum.

## Known Gotchas

**1. A "central" util that nothing wires is a hardcoded constant in disguise**
*Symptom:* A Settings screen lets an admin change health thresholds; the change
saves; no dashboard ever reflects it.
*Root cause:* The util has a `getThresholds()` that fetches and caches — but it is
never called anywhere, so the cache stays empty and the sync classifier always
returns the compiled-in 70/50 defaults. A central source of truth that isn't
loaded is just a constant with extra steps.
*Fix:* Call the loader once at app boot (and/or a provider), assert-tested; make
`bandFor` read the loaded value with defaults only as a genuine fallback. Cited:
`src/utils/healthThresholds.ts:43-61` (`getThresholds` with zero callers →
`getThresholdsSync` always returns `DEFAULTS`; the Settings PUT has no effect).

**2. One endpoint, three response shapes — a malformed one classifies everything
healthy**
*Symptom:* After a backend change, every account shows as healthy and nobody
notices for a while.
*Root cause:* The threshold endpoint is documented/returned three different ways —
`{healthy:{min}}`, flat `{critical_max, at_risk_min, healthy_min}`, and a
`{thresholds:{...}}` wrapper. Code reading `t.healthy.min` against the wrong shape
gets `undefined`; `score >= undefined` is `false`, so the classifier falls through
to... whatever the first branch is, and an unguarded parse silently mislabels.
*Fix:* One typed contract and a runtime `assertThresholdShape` that throws on a
malformed response — fail loud, never classify on `undefined`. Cited:
`healthThresholds.ts:46-48` vs `HealthThresholdsCard.tsx:6-13` vs
`backend/config/health_thresholds.json:1-3`.

**3. Fifteen local `getHealthColor` helpers and three cutoffs in one file**
*Symptom:* "At risk" is a different color and a different boundary depending on
which screen you're on; a threshold change reaches some tiles and not others.
*Root cause:* No single `HealthBadge`; ~15+ components define their own
`getHealthColor`/`getHealthStatus`, and even files that import the util bypass it.
`CSPlatform.tsx` alone uses healthy≥80, ≥75, and ≥70 in different places.
*Fix:* One `HealthBadge`/`bandFor`; ban local classifiers with an anti-drift
meta-check that greps for local health helpers / hardcoded band thresholds outside
the kit. Cited: `CSPlatform.tsx:1388,1460,1513,2482-2483,3485,3980` (three
schemes), `Dashboard_dc.tsx:163,465` (imports the util, uses hardcoded 80/70), the
26-file hardcoded-cutoff list.

**4. Mock data substituted for an empty OR failed fetch, unlabeled**
*Symptom:* A CSM opens an account with genuinely no actions and sees a plausible
list of fabricated ones; a demo shows numbers that don't exist.
*Root cause:* `list.length > 0 ? list : MOCK_ACTIONS` on the success path AND mock
in the catch — so both "no data" and "fetch failed" render fabricated data
indistinguishable from real, with no banner.
*Fix:* `DataState` renders a *labeled* empty/error state; mock is never
substituted for missing data. If a demo mode is wanted, it is an explicit,
labeled mode. Cited: `CSMFocusFlow.tsx:350,375,391`, `CSMCockpit.tsx:1046-1071`,
`csm/mockData.ts`.

**5. A dead mock blob shipped in the bundle**
*Symptom:* A large fabricated `FALLBACK_DATA` sits in a dashboard file; a future
edit wires it in and reintroduces mock-as-real.
*Root cause:* Mock kept "just in case" after the component moved to an honest
error state — defined but unreferenced.
*Fix:* No unused mock in shipped components; the anti-drift check can flag a large
mock literal with zero references. Cited: `VPCSDashboard.tsx:274` (`FALLBACK_DATA`
defined, referenced only at its definition).

**6. An entitlement guard that fails open**
*Symptom:* A session that lost its `tier` sees every premium feature; the default
landing route shows a gated dashboard with no gate.
*Root cause:* `session?.tier ?? 'enterprise'` — a MISSING tier resolves to the
MOST privileged, and the primary landing routes (`/cro-dashboard`,
`/cfo-dashboard`) are not wrapped by the guard at all, while their aliases are.
*Fix:* Resolve a missing tier to the LEAST privilege; wrap every persona route.
And treat the guard as UX-only — it hides locked features; it is not access
control (that is server-side, Module 07). Cited: `hooks/useEntitlement.ts:80,119`
(`?? 'enterprise'`), `App.tsx:401-417` (unguarded landing routes).

**7. An N+1 fan-out that swallows failures reports "no signals" when signals exist**
*Symptom:* The signal timeline says "No signals detected" for a customer that
clearly has signals — intermittently.
*Root cause:* One fetch per account, each `try/catch`→`[]` on failure, flattened;
if the per-account calls fail while the top-level accounts call succeeded, the
flattened result is empty and the empty state fires — a failure masquerading as
no-data.
*Fix:* The hook distinguishes `empty` (zero failures, no data) from `partial`
(some failures) from `error` (all failed), and surfaces a degraded banner rather
than a false empty. Cited: `SignalTimelineView.tsx:241-258` (swallowed per-account
failures), `:452-457` (the empty state).

**8. Dollar figures with no basis label**
*Symptom:* A revenue number on one screen means something different from the same
label on another, because one is scaled to a baseline ARR and the other isn't —
and nothing says which.
*Root cause:* The payload carries `arr_basis`/`arr_basis_value` (Module 08), but no
frontend component consumes it — dollars render bare.
*Fix:* The money formatter requires the basis and renders it; a dollar tile
without a basis is a finding. Cited: no `arr_basis` consumer exists in the origin
frontend (grep); Module 08 supplies it.

## Provenance

Origin files: `src/utils/healthThresholds.ts` (the dead-fetch util `:43-61`, shape
`:46-48`); `src/components/shared/` (`StatusBadge.tsx`, `MetricCard.tsx`,
`ProgressBar.tsx:35` third scheme, `EmptyState.tsx`, `DashboardErrorState.tsx`,
`ProvenanceBadge.tsx:40-72` the honest synthetic badge, `EntitlementGuard.tsx:24-90`);
`src/hooks/useEntitlement.ts:80,119` (fail-open default); `src/App.tsx:254-417`
(routing, unguarded landing routes `:401-417`); `src/components/csm/`
(`CSMFocusFlow.tsx:350-393`, `CSMCockpit.tsx:1046-1071`, `mockData.ts` — mock-as-real);
`src/components/dashboard/VPCSDashboard.tsx:274` (dead `FALLBACK_DATA`);
`src/components/dashboard/views/SignalTimelineView.tsx:241-258,452-457` (false-empty
fan-out); `src/components/CSPlatform.tsx:1388-3980` (three color schemes);
`backend/config/health_thresholds.json` (the canonical 70/50); `tailwind.config.js`
(no health-band tokens); `src/contexts/SessionContext.tsx` (client-trusted session);
`src/utils/api.ts` (`apiCall`). Test setup: Create-React-App Jest +
`@testing-library/react`; only 3 test files exist and none covers
`healthThresholds.ts`, `EntitlementGuard`, or any dashboard.

Authored 2026-08-07 against HEAD `10f67e9fc`, and validated the same day (see
Validation Note).

## Validation Note

Validated 2026-08-07, **pure-logic scope only**. A fresh agent, given ONLY this
spec in isolation, ported the pure-logic contracts to JS and tested them with
Node's built-in `node:test` runner (no React/JSX — the environment has Node v22
but not the RTL toolchain, and rendering fidelity is out of scope by design).
Result: **21 passed (13 acceptance-criteria + 5 defect proofs + 3 corrected
versions)**, and **five real defects**, dominated — as predicted — by shape (c)
referenced-but-undefined:

- **D1 — HIGH (shape c).** `bandFor` read `THRESHOLDS ?? DEFAULT_THRESHOLDS`, but
  `DEFAULT_THRESHOLDS` was defined nowhere — so before `loadThresholds` runs (or
  if a load fails), `t.healthy.min` threw `TypeError` and the sole classifier
  hard-crashed, making the AC's "defaults are a fallback" promise a lie. *Fixed:*
  `DEFAULT_THRESHOLDS = {healthy:{min:70}, at_risk:{min:50}, critical:{min:0}}`
  defined in piece 1.
- **D2 — HIGH/most severe (shape c+e).** `useEntitlement` computed `TIER_ORDER
  .indexOf(need)`; for an unknown feature `need` is `undefined` →
  `indexOf === -1`, and every real tier index (including least-privileged `free`
  = 0) satisfies `0 >= -1` → **allowed for everyone**. `FEATURE_CATALOG` was also
  undefined. The guard failed *open* — the exact opposite of its fail-closed
  purpose (Gotcha 6). *Fixed:* `FEATURE_CATALOG` defined (empty Config default);
  an `indexOf(need) === -1` now **denies**.
- **D3 — (shape c/d).** `money` called `fmt`, defined nowhere → `ReferenceError`
  on every call; the money formatter (a named Engine deliverable) was
  non-functional. *Fixed:* `fmt` defined via `Intl.NumberFormat`.
- **D4 — (shape d).** `money(v, basis, basisVal)` accepted `basisVal` but never
  rendered it — a captured-but-unrendered value, and the very thing Gotcha 8 says
  disambiguates two same-labeled figures. *Fixed:* `money` now renders the basis
  value alongside the label.
- **D5 — (shape c).** The DataState hook's `isEmpty` was undefined, and the
  branch order left a partial-failure-with-empty-survivors case ambiguous.
  *Fixed:* `isEmpty` defined; branch order reworked so any failure is `partial`
  (data null when survivors are empty) before a zero-failure `empty`.

Also folded in: the secondary referenced-but-undefined helpers (`renderApp`,
`fetchPersona`, the scanner's `read`/`isKitFile`) are now named external hooks in
the Build Prompt, and the presentational leaves are explicitly scoped out.

Verified NOT defective: `assertThresholdShape` correctly throws on both real
malformed shapes (flat and wrapper) while accepting the valid one; `bandFor`
boundaries (49/50/69/70/null) with `null` never a `50` stand-in; `resolveTier({})`
→ least privilege; `auditNoLocalHealthColors` catches a local `getHealthColor` /
`health >= 75` and raises on zero files; `revenueAtRiskValue` reads the bundle,
not an account sum.

**Explicitly out of scope (React-rendering, unverifiable in isolation):** that
`boot()` actually calls `renderApp`; that every persona route is wrapped by
`EntitlementGuard` with no unguarded landing alias; and the rendering fidelity of
`HealthBadge`/`DataState`/the domain-pattern components. Those acceptance claims
rest on the pure-logic contracts being correct (now proven) plus a visual review
this process cannot perform — the honest limit of validating a UI module by
spec-only rebuild.

**Library-level note:** shape (c) — a helper or constant referenced but never
defined — struck five times here, exactly as in Modules 00, 10, and 11. Across the
last four modules it is unambiguously the dominant defect class; a name used in
code that is neither defined nor a declared dependency is a near-certain defect,
and grepping for them is the single highest-yield review pass.
