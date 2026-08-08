# 11 — Load-Driver Synthetic Data & Testing

**Layer:** Ops

**Status:** ✅ Validated — see [Validation Note](#validation-note) at the bottom.
A spec-only fresh-agent rebuild (2026-08-07) proved **six** defects with
executable tests — headlined by the arc round-trip guard (the module's entire
reason for existing) being defined but never invoked, plus the tables and
constants it needs being referenced-but-undefined — all fixed below.

## Purpose

Generate realistic synthetic tenants from a declarative manifest, load them
through the real onboarding path, and **assert the platform produced the numbers
the manifest asked for** — the acceptance/parity harness that proves a
regenerated instance actually works, not just compiles. This is the other half
of the "regenerate-and-verify as-is" proof: Module 00 builds the chassis and
defines the golden-path acceptance; this module manufactures the data that
exercises it and checks the result. Its two hardest jobs are (a) making the
synthetic data **deterministic** so a test means the same thing twice, and (b)
keeping the story-arc vocabulary **consistent end to end**, because a manifest
arc that the platform's classifier silently reinterprets is a test that passes
while asserting the wrong thing — the exact failure that once made `silent_churn`
unreachable and broke Wizard B's early-warning detection.

## Boundary

**Owns:**
- The **manifest contract**: a declarative JSON scenario (customer, time range,
  KPI selection, and per-account story arcs / classifications / trajectories).
- **Deterministic synthetic-data generation**: seeded, reproducible CSV
  generation for the canonical 4-CSV onboarding shape (Gotcha 2).
- **Story-arc resolution + consistency guards**: mapping a manifest `story_arc`
  to a generation template, and the executable check that the generated data
  round-trips through the platform's classifier back to the *intended* canonical
  arc (Gotcha 1).
- **Multi-phase mechanics**: baseline/intervention windowing, `--extend`
  continuation, and playbook-intervention triggering/closing.
- **The acceptance/validation harness**: generate → onboard → `process_data` →
  validate the health distribution against the manifest (tolerance-based, using
  *discovered* platform IDs), plus the post-load steps required for the CFO and
  predictor surfaces to be non-empty (Gotchas 3, 4, 5).

**Explicitly does not own:**
- Scoring, graph, wizard, or signal logic — Modules 03/04/05/06. This module
  feeds synthetic inputs in and asserts outputs; it computes no score itself.
- The `process_data` orchestration and bootstrap — Module 00. This module calls
  them.
- The KPI catalog / taxonomy — Module 02. The manifest *selects* a KPI tier; it
  does not define KPIs.
- The arc *classifier* — Module 04. This module *calls* it for the round-trip
  check; it does not implement classification.

## Dependencies

- **Module 00 (Integration & Bootstrap):** `create_customer`, `process_data`,
  and the client/API to upload CSVs. The harness is a caller of the chassis.
- **Module 01 (Data Model):** the CSV schemas it generates map to
  `Account`/`DC2SKPI`/`QualitativeSignal`/outcome tables.
- **Module 02 (Taxonomy):** `tier_codes(selection) -> codes[]` (the KPI **tiers**
  the manifest selects — Starter-9, Predictive-11 (the Power-of-1 lead-indicator
  set), Full-38) and `kpi_range(code) -> {lo, hi}` (a KPI's legal min/max, used to
  clamp synthesized values). The manifest names a tier or lists explicit codes;
  it never invents a KPI.
- **Module 03 (Scoring):** validated *against* — the harness asserts the
  platform's computed health matches the manifest's `target_health` within
  tolerance.
- **Module 04 (Context Graph):** `classify_arc(nodes) -> canonical_arc` for the
  round-trip guard (Gotcha 1); the generated `signal_edges` feed the graph.
- **Module 05 (Wizards):** `wizard_d_recalibration` (post-load, else the
  predictor returns `cold_start`, Gotcha 5).

### Data Shapes

```
Manifest (JSON):
  customer: {name, domain, vertical ("dc2_s"|"saas_premium"), admin_email, total_arr}
  time_range: {start, end, frequency ("monthly"|"weekly"|"daily"), data_points_per_kpi}
  kpis: {selection (tier name e.g. "predictive_11"), count, codes[] (e.g. "P1-KPI1")}
  accounts[]: {
     name, arr, target_health (0..100), classification ("healthy"|"at_risk"|"critical"),
     story_arc (label — MUST resolve to a template or documented fallback, Gotcha 1),
     kpi_trajectory ("declining"|"recovering"|"improving"|"stable"|...),
     decline_start_month (int, nullable), renewal_date, narrative,
     lifecycle: {event ("churn"|"expand"|"contract"|"new"), event_month, delta_pct} (nullable)
  }

Canonical onboarding output — the 4 Month-1 CSVs:
  account_details.csv, kpi_measurements.csv, qualitative_signals.csv, outcomes.csv
  (--minimal drops to 2: account_details + kpi_measurements. The KPI COUNT is the
   tier, orthogonal to the CSV count — "4 CSVs × 11 KPIs" means the 4-CSV
   onboarding carrying the Predictive-11 tier, NOT a universal default; the most
   common manifest tier is actually 20, and Full is 38.)

Validation result:
  status ("success"|"failed"), per_account[]: {name, expected_health, actual_health,
     within_tolerance (bool), expected_class, actual_class}, discovered_ids (dict name->id)
```

**Nullable rule:** `decline_start_month`, `lifecycle`, and `codes[]` (when a tier
name is given instead) are nullable. Trajectory synthesis must handle a null
`decline_start_month` (treat as no decline) and a null `lifecycle` (no ARR event)
without raising. Test each.

## Engine vs. Config

**Engine (build once):** the manifest loader + schema validation, the seeded
generator (`generate_all` + `apply_lifecycle`) and its RNG discipline, the arc
resolver + round-trip guard, the phase/extend windowing, the trajectory
synthesizer, and the acceptance harness that invokes the guard.

**Config (an FDE fills in per client):** the manifests themselves (the scenarios);
the three arc tables — `ARC_TEMPLATES`, `CLASSIFICATION_TO_ARC`, and
`INTENDED_CANONICAL` (story_arc → the canonical-8 arc the classifier should
return); the KPI tier definitions (from Module 02); the trajectory tunables
(`NOISE_SD`, `DECAY_PER_MONTH`, `RECOVERY_LAG`, `RECOVERY_PER_MONTH`,
`IMPROVE_PER_MONTH`), the health tolerance (`HEALTH_TOL`), and the seed.

## Build Prompt

> Build the load-driver + acceptance harness. Seven numbered pieces. Every helper
> is defined below OR is a named dependency hook whose contract Dependencies
> states — `module00_create_customer`/`module00_process_data`, `client_upload`,
> `module02_tier_codes`/`module02_kpi_range`, `module04_classify_arc`,
> `module05_wizard_d`, and `random` (stdlib). The three arc tables
> (`ARC_TEMPLATES`, `CLASSIFICATION_TO_ARC`, `INTENDED_CANONICAL`) and the
> trajectory tunables are Config, threaded as parameters — not module globals.
> This module GENERATES inputs and ASSERTS outputs; it computes no score or
> classification itself.
>
> Origin references: `load-driver/cs_pulse_driver.py` (the V3 CLI, manifest flow,
> post-load steps), `load-driver/scenarios/scenario_manifest.py`
> (`ManifestCSVGenerator`, `ARC_TEMPLATES` `:138`, `CLASSIFICATION_TO_ARC` `:488`,
> `generate_all` `:1624`, the 4-CSV set `:4319`, `_validate_post_process` `:3452`),
> `load-driver/manifests/*.json`, `kpi-dashboard/backend/utils/arc_classifier.py`
> (the canonical 8 arcs `:137`), `kpi-dashboard/backend/tests/test_scorer_parity.py`.
>
> 1. **Manifest loader + schema check.** Parse JSON; validate required keys;
>    resolve the KPI tier to explicit codes:
>    ```
>    def load_manifest(path):
>        m = json.loads(read(path))
>        for key in ("customer", "time_range", "kpis", "accounts"):
>            if key not in m: raise ManifestError(f"missing '{key}'")
>        m["kpis"]["codes"] = (m["kpis"].get("codes")
>                              or module02_tier_codes(m["kpis"]["selection"]))  # tier -> codes
>        return m
>    ```
>
> 2. **Arc resolution + the round-trip guard (Gotcha 1).** A manifest `story_arc`
>    resolves to a generation template directly, or via the documented
>    classification fallback — but a label that resolves ONLY by silent fallback
>    to a *different* arc is the bug. And the generated data, run back through the
>    platform's classifier, must land on the arc the manifest intended.
>
>    Three Config tables (FDE-supplied, threaded as parameters — not module
>    globals) drive this. All three are named Config deliverables:
>    ```
>    # ARC_TEMPLATES:        arc label -> generation template (event spine + edges)
>    # CLASSIFICATION_TO_ARC: classification -> fallback arc when no direct template
>    # INTENDED_CANONICAL:   story_arc -> the canonical-8 arc the platform's
>    #                        classifier is expected to return for that arc's data
>    # Example shapes (not the full sets — the FDE fills these per client):
>    #   ARC_TEMPLATES        = {"silent_churn": {...}, "crisis_recovery": {...}, ...}
>    #   CLASSIFICATION_TO_ARC= {"critical":"crisis_recovery","at_risk":"budget_pressure",
>    #                           "healthy":"steady_performer"}
>    #   INTENDED_CANONICAL   = {"silent_churn":"silent_churn",
>    #                           "land_and_expand":"land_and_expand", ...}
>
>    def resolve_arc(story_arc, classification, ARC_TEMPLATES, CLASSIFICATION_TO_ARC):
>        if story_arc in ARC_TEMPLATES:
>            return story_arc, "direct"
>        fallback = CLASSIFICATION_TO_ARC.get(classification)
>        if fallback in ARC_TEMPLATES:
>            return fallback, "fallback"     # allowed, but reported — not silent
>        raise ArcError(f"story_arc '{story_arc}' has no template and no usable fallback")
>
>    def check_arc_vocabulary(manifest, ARC_TEMPLATES, CLASSIFICATION_TO_ARC):
>        # Report every account whose arc resolves only by fallback, and fail on
>        # any with no template AND no fallback. Surfacing fallbacks is what keeps
>        # a manifest label from silently meaning a different arc than written.
>        report = []
>        for a in manifest["accounts"]:
>            arc, how = resolve_arc(a["story_arc"], a["classification"],
>                                   ARC_TEMPLATES, CLASSIFICATION_TO_ARC)
>            report.append({"name": a["name"], "declared": a["story_arc"],
>                           "generated_as": arc, "how": how})
>        return report
>
>    def assert_arc_roundtrip(story_arc, generated_nodes, INTENDED_CANONICAL):
>        # The generated data, classified by the PLATFORM (Module 04), must yield
>        # the canonical arc the manifest intended. This is the guard that would
>        # have caught silent_churn being reclassified as crisis_recovery.
>        produced = module04_classify_arc(generated_nodes)
>        intended = INTENDED_CANONICAL[story_arc]
>        if produced != intended:
>            raise ArcRoundtripError(
>                f"'{story_arc}' generated but classified as '{produced}', "
>                f"expected '{intended}'")
>    ```
>
> 3. **Deterministic RNG discipline (Gotcha 2).** One seeded generator threaded
>    through everything; no global `random.seed`, and no `hash(str)` in any seed:
>    ```
>    def make_rng(seed):
>        return random.Random(seed)   # ONE generator, passed to every producer.
>        # Do not call the module-level random.* (global state), and do not seed
>        # from hash(some_string): str hashing is salted by PYTHONHASHSEED per
>        # process, so a hash-seeded stream is not reproducible across runs.
>    ```
>    Every generator takes `rng` as a parameter and draws only from it. Two runs
>    with the same seed produce byte-identical CSVs (Acceptance).
>
> 4. **Trajectory synthesis (per-point values, deterministic).** Literal shape
>    per trajectory keyword; the same `rng` supplies noise; values clamp to the
>    KPI's legal range. Null `decline_start_month` means no decline. The tunables
>    are pinned constants (Config — an FDE may retune, but they are named and
>    assigned, not left implicit, so two runs reproduce):
>    ```
>    NOISE_SD, DECAY_PER_MONTH, RECOVERY_LAG, RECOVERY_PER_MONTH, IMPROVE_PER_MONTH = \
>        2.0, 8.0, 1, 6.0, 4.0
>    HEALTH_TOL = 5.0        # acceptance health tolerance (Config)
>    def kpi_range(code):    # KPI legal min/max — from Module 02's catalog
>        return module02_kpi_range(code)
>
>    def kpi_series(traj, months, target, decline_start, rng, kpi_rng):
>        out = []
>        ds = decline_start if decline_start is not None else months  # null => no decline
>        for m in range(months):
>            base = trajectory_value(traj, m, months, target, ds)
>            base += rng.gauss(0, NOISE_SD)            # SAME seeded rng, not global
>            out.append(clamp(base, kpi_rng.lo, kpi_rng.hi))
>        return out
>
>    def trajectory_value(traj, m, months, target, ds):
>        if traj == "declining":
>            return target - DECAY_PER_MONTH * max(0, m - ds)
>        if traj == "recovering":                      # V-shape: decline then recover
>            infl = min(ds + RECOVERY_LAG, months - 1)
>            if m <= infl: return target - DECAY_PER_MONTH * max(0, m - ds)
>            floor = target - DECAY_PER_MONTH * max(0, infl - ds)
>            return floor + RECOVERY_PER_MONTH * (m - infl)
>        if traj == "improving": return target + IMPROVE_PER_MONTH * m
>        if traj == "stable":    return target
>        return target                                 # explicit catch-all
>    ```
>
> 5. **Phase windowing + extend.** `baseline` = first 2/3 of points,
>    `intervention` = last 1/3 (advanced past the baseline window); `--extend`
>    appends the next N months continuing the arc against an EXISTING customer
>    (mutually exclusive with registering a new one):
>    ```
>    def phase_window(points, phase):
>        cut = points * 2 // 3
>        if phase == "baseline":     return range(0, cut)
>        if phase == "intervention": return range(cut, points)   # recovery half
>        return range(0, points)                                 # full run
>
>    def resolve_target(extend, register):
>        if extend and register:
>            raise ManifestError("--extend continues an existing customer; not with --register")
>        return "extend" if extend else "register"
>    ```
>
> 6. **Deterministic generation — `generate_all`.** The function every other
>    piece calls but that also carries the whole determinism guarantee. It
>    iterates accounts and KPI codes in **manifest order**, threads the single
>    `rng` into every draw, applies lifecycle ARR events (Gotcha 6), and returns
>    the 4 onboarding CSVs **plus** the per-account generated graph nodes (so the
>    harness can round-trip them, piece 7). No `hash(str)`, no per-stream
>    re-seeding — ordered iteration + one `rng` is the byte-identity contract
>    (Gotcha 2). The per-CSV row builders (`account_row`, `kpi_rows`,
>    `build_nodes`, `signals_from`, `outcomes_from`) are named sub-generators the
>    FDE fills to the Module-01 CSV schema; each draws only from the passed `rng`:
>    ```
>    def apply_lifecycle(arr, lifecycle, months):
>        if not lifecycle:                       # null => no ARR event (Gotcha 6)
>            return arr
>        # e.g. {"event":"expand","event_month":6,"delta_pct":25} -> arr*1.25 at month 6
>        return arr * (1 + lifecycle["delta_pct"] / 100.0)
>
>    def generate_all(manifest, rng, ARC_TEMPLATES, CLASSIFICATION_TO_ARC):
>        months = manifest["time_range"]["data_points_per_kpi"]
>        codes  = manifest["kpis"]["codes"]
>        acct_rows, kpi_rows_all, nodes_by_account = [], [], {}
>        for a in manifest["accounts"]:           # ordered: manifest account order
>            arc, _how = resolve_arc(a["story_arc"], a["classification"],
>                                    ARC_TEMPLATES, CLASSIFICATION_TO_ARC)
>            arr = apply_lifecycle(a["arr"], a.get("lifecycle"), months)   # Gotcha 6
>            acct_rows.append(account_row(a, arr))
>            for code in codes:                   # ordered: manifest code order
>                series = kpi_series(a["kpi_trajectory"], months, a["target_health"],
>                                    a.get("decline_start_month"), rng, kpi_range(code))
>                kpi_rows_all += kpi_rows(a["name"], code, series)
>            nodes_by_account[a["name"]] = build_nodes(a, arc, rng)   # signals/edges
>        csvs = {"account_details.csv": acct_rows,
>                "kpi_measurements.csv": kpi_rows_all,
>                "qualitative_signals.csv": signals_from(nodes_by_account),
>                "outcomes.csv": outcomes_from(nodes_by_account)}     # the 4-CSV set
>        return csvs, nodes_by_account
>    ```
>
> 7. **Acceptance harness.** Generate → **round-trip guard (piece 2, invoked
>    here)** → onboard → `process_data` → the two post-load steps → validate
>    against the manifest using DISCOVERED platform IDs (Gotcha 3), matching
>    accounts by NAME because the platform assigns its own ID sequence. The arc
>    tables are threaded as parameters (they are Config, not globals):
>    ```
>    def run_acceptance(manifest, client, ARC_TEMPLATES, CLASSIFICATION_TO_ARC,
>                       INTENDED_CANONICAL, seed=42, tol=HEALTH_TOL):
>        check_arc_vocabulary(manifest, ARC_TEMPLATES, CLASSIFICATION_TO_ARC)  # piece 2
>        csvs, nodes_by_account = generate_all(manifest, make_rng(seed),
>                                              ARC_TEMPLATES, CLASSIFICATION_TO_ARC)  # piece 6
>        for a in manifest["accounts"]:        # the round-trip guard is INVOKED here —
>            assert_arc_roundtrip(a["story_arc"],        # not just defined (Gotcha 1)
>                                 nodes_by_account[a["name"]], INTENDED_CANONICAL)
>        cid = module00_create_customer(manifest["customer"])["customer_id"]
>        client_upload(cid, csvs)
>        module00_process_data(cid)
>        module05_wizard_d(cid)              # else predictor = cold_start (Gotcha 5)
>        client.backfill_playbook_attribution(cid)   # else CFO tiles $0 / 0x (Gotcha 4)
>        return validate_post_process(manifest, client, cid, tol)
>
>    def validate_post_process(manifest, client, cid, tol):
>        platform = client.list_accounts(cid)     # DISCOVER real ids (Gotcha 3)
>        if len(platform) != len(manifest["accounts"]):
>            return {"status": "failed", "reason": "account count mismatch",
>                    "per_account": []}
>        by_name = {a["name"]: a for a in platform}   # match by NAME, not manifest id
>        rows, ok = [], True
>        for spec in manifest["accounts"]:
>            got = by_name.get(spec["name"])
>            within = got is not None and abs(got["health"] - spec["target_health"]) <= tol
>            ok = ok and within
>            rows.append({"name": spec["name"], "expected_health": spec["target_health"],
>                         "actual_health": got["health"] if got else None,
>                         "within_tolerance": within,
>                         "expected_class": spec["classification"],
>                         "actual_class": got["status"] if got else None})
>        return {"status": "success" if ok else "failed", "per_account": rows,
>                "discovered_ids": {n: a["account_id"] for n, a in by_name.items()}}
>    ```

## Acceptance Criteria

- **Determinism (Gotcha 2).** `generate_all(manifest, make_rng(42), ARC_TEMPLATES,
  CLASSIFICATION_TO_ARC)` run twice — in the same process AND in two separate
  processes with different `PYTHONHASHSEED` — produces **byte-identical** CSVs.
  Assert the cross-process case explicitly: a generator that seeds any stream from
  `hash(str)`, or iterates an unordered set, fails it while the ordered single-rng
  version passes.
- **Arc round-trips, and the guard is actually invoked (Gotcha 1).** For a
  `story_arc="silent_churn"` account, `assert_arc_roundtrip` passes only if the
  generated data classifies as `silent_churn` — and FAILS if the classifier reads
  it as `crisis_recovery`. **Assert the guard runs inside `run_acceptance`, not
  merely that it exists**: a scenario whose generated data mis-classifies must
  make `run_acceptance` raise, not return `status="success"`. A guard defined but
  never called by the harness is the exact defect this AC pins (source-inspect
  that `assert_arc_roundtrip` appears in the harness, and drive the failing
  scenario through `run_acceptance`).
- **Vocabulary surfaced, not silent.** `check_arc_vocabulary` reports every
  account resolving via classification fallback (`how="fallback"`) and RAISES for
  a `story_arc` with neither a template nor a usable fallback. Assert a
  manifest using `land_and_expand` (no template) is reported as a fallback, not
  silently accepted as if it had one.
- **Golden onboarding path.** A manifest generated at the 4-CSV shape, onboarded
  and processed, yields per-account health within `tol` of `target_health` and a
  matching classification — asserted against DISCOVERED platform IDs.
- **ID discovery (Gotcha 3).** Validation matches accounts by NAME and reads the
  platform's assigned `account_id`; it does NOT assume the manifest's
  `customer_id*1000+slot` IDs. Assert a run where the platform's IDs differ from
  the manifest's still validates.
- **Post-load steps are required (Gotchas 4, 5).** Assert the harness calls
  `wizard_d_recalibration` (a run without it leaves the predictor at
  `cold_start`) and `backfill_playbook_attribution` (a run without it leaves CFO
  Revenue-Protected at `$0`/`0x`). A harness that skips them "passes" health but
  ships empty CFO/predictor tiles.
- **Phase + extend (Gotcha on exclusivity).** `phase_window(points,"baseline")`
  is the first 2/3, `"intervention"` the last 1/3; `resolve_target(extend=True,
  register=True)` raises. Assert both.
- **Trajectory nulls.** `kpi_series` with `decline_start=None` produces no
  decline (a stable/flat series), and a null `lifecycle` applies no ARR event —
  neither raises. Assert both.
- **Lifecycle actually moves ARR (Gotcha 6).** `apply_lifecycle` with an
  `{"event":"expand","delta_pct":25}` event returns `arr * 1.25`, and the
  generated `account_details.csv` row carries the adjusted ARR — assert the
  positive case, not just the null one. A null-only test passes vacuously while
  the real behavior is unimplemented, so the non-null path must be exercised.
- **KPI tier resolution.** A manifest naming `selection="predictive_11"` with no
  explicit `codes` resolves to the 11 Predictive codes; one listing explicit
  codes uses them verbatim. Assert the count matches the tier.

## Reference Test Harness

1. **Determinism pair** — generate twice in-process (identical) and via two
   subprocesses with `PYTHONHASHSEED=0` and `=1` (identical). A mutation: seed a
   stream from `hash(kpi_code)` and assert the cross-process test then fails —
   proving the guard catches the real Gotcha 2 bug.
2. **Arc round-trip** — for each canonical arc, generate and assert
   `module04_classify_arc` returns the intended arc; a mutation that generates
   `silent_churn` data as a generic decline and asserts the round-trip FAILS.
3. **Vocabulary report** — a manifest mixing a templated arc, a fallback-only arc
   (`land_and_expand`), and an unresolvable arc; assert the first two are
   reported with the right `how` and the third raises.
4. **Golden acceptance** — a small fixture manifest (few accounts, the 4-CSV
   shape, a KPI tier) through `run_acceptance`; assert health-within-tolerance
   per account against discovered IDs, and that the two post-load steps ran.
5. **Null/edge suite** — `decline_start=None`, `lifecycle=None`, tier-vs-explicit
   codes, `--extend`+`--register` exclusivity.

## Known Gotchas

**1. Three arc vocabularies that don't line up, so a manifest arc silently
becomes a different one**
*Symptom:* An account authored as `silent_churn` (a slow, quiet disengagement)
generates data that the platform classifies as `crisis_recovery`, so the very
scenario a test exists to exercise never occurs — and a detector tuned for the
intended arc (Wizard B's early warning) never fires, while every test still
"passes."
*Root cause:* Three separate vocabularies: ~31 manifest `story_arc` labels, only
11 `ARC_TEMPLATES` generation keys, and 8 canonical classifier arcs. A label with
no template (e.g. `land_and_expand`, the most-used at 91×) falls through
`CLASSIFICATION_TO_ARC` (`critical→crisis_recovery`, `at_risk→budget_pressure`,
`healthy→steady_performer`) to a *different* arc, silently. `silent_churn` was
literally unreachable until its template was added (commit `b763acfe6`).
*Fix:* Two guards. `check_arc_vocabulary` reports every fallback resolution
(never silent) and fails on an unresolvable label. `assert_arc_roundtrip` runs
the generated data back through the platform's own classifier and fails unless it
lands on the intended canonical arc. Cited: `scenario_manifest.py:138`
(`ARC_TEMPLATES`), `:451-456` + `:488-492` (the silent fallback),
`arc_classifier.py:137` (canonical 8), commit `b763acfe6`.

**2. Mixed RNG sources make "deterministic" synthetic data non-reproducible**
*Symptom:* The same manifest + seed produces different CSVs on different machines
or runs, so a golden-fixture comparison flakes and a "deterministic CSV" claim is
false.
*Root cause:* The generator seeds the *global* `random` (`random.seed(seed)`) for
some values, isolated `random.Random(seed+idx)` for others, and — the real
killer — a stream seeded from `random.Random(self.seed + hash(kpi_code))`. Python
salts `hash(str)` with `PYTHONHASHSEED` per process, so that stream is not
reproducible across runs unless the env var is pinned.
*Fix:* One `random.Random(seed)` threaded through every producer; no module-level
`random.*`; no `hash(str)` in any seed (use the string itself or a stable index).
Test byte-identity across two processes with different `PYTHONHASHSEED`. Cited:
`scenario_manifest.py:1106` (global seed), `:1471` (hash-seeded stream), `:1544`
(global gauss), the "deterministic CSV" docstring `:5,:702`.

**3. Manifest IDs don't match the platform's assigned IDs**
*Symptom:* Validation looks up account `354001` (the manifest's
`customer_id*1000+slot`) and finds nothing, or matches the wrong account, because
the platform assigned its own sequential IDs at insert time.
*Root cause:* The manifest computes deterministic IDs (`account_id_base =
customer_id*1000+1`), but the platform's accounts table has a global sequence, so
the real IDs differ — and differ again on every re-register.
*Fix:* The validation harness DISCOVERS the platform's real IDs
(`client.list_accounts`) and matches accounts by a stable natural key (name), not
by the manifest's computed ID. Cited: `scenario_manifest.py:3468-3471` (the
discover-IDs comment), `:1194` (manifest ID formula).

**4. Playbook revenue attribution computes to $0 on synthetic data**
*Symptom:* The CFO dashboard's "Revenue Protected" reads `$0` and "Portfolio ROI"
reads `0x` after a load, even though playbooks ran.
*Root cause:* Closing a playbook auto-computes protected revenue from the health
delta between trigger and close; on freshly generated synthetic data
`health_at_close <= health_at_trigger` (or the close reads current instead of
point-in-time health), so the delta is zero.
*Fix:* A post-load `backfill_playbook_attribution` step (and point-in-time health
lookup at close). The acceptance harness runs it, and asserts the CFO tiles are
non-zero for a scenario that should protect revenue. Cited:
`cs_pulse_driver.py:276-283,301`, commits `54da5adfe`, `54c728bc7`.

**5. Predictor returns `cold_start` without post-load recalibration**
*Symptom:* Every account's NRR forecast shows `prediction_method="cold_start"`
(CDI seed priors only) — the predictor never fit to this tenant's data.
*Root cause:* Predictor v3 coefficients are fit by Wizard D, which is NOT part of
`process_data` (it's a separate trigger, per Module 00 Gotcha 4). A load that
stops at `process_data` leaves the predictor uncalibrated.
*Fix:* The harness calls `wizard_d_recalibration` after `process_data`; assert a
loaded tenant's predictor is not `cold_start`. Cited: `cs_pulse_driver.py:284-287`.

**6. Testing against a stale server hides fixes and corrupts idempotency**
*Symptom:* A code fix appears to have no effect; or a re-run doubles rows /
produces drifted IDs.
*Root cause:* Multiple `app_v3_minimal` processes (or a long-lived one) serve
stale code, and the CSV generator's `RefRegistry` carries state between
`generate_all()` calls if not reset.
*Fix:* Pre-flight the server (warn on multiple PIDs / long uptime) and reset the
`RefRegistry` between generations. Cited: `cs_pulse_driver.py:212-239` (stale-PID
pre-flight), `scenario_manifest.py:1203-1205,2051` (RefRegistry reset).

**7. Running the deprecated standalone compose**
*Symptom:* The load driver won't start, or runs the retired scenario CLI with
stale creds and no context-graph support.
*Root cause:* `docker-compose.loaddriver-standalone.yml` was deprecated
(2026-03-24) and reduced to empty `services: {}`, but still exists and invites
use.
*Fix:* Use `docker-compose.ec2-loaddriver.yml` (deployed) or
`docker-compose.loaddriver.yml` (local); the standalone file is dead. Cited: the
deprecation banner in `docker-compose.loaddriver-standalone.yml`.

## Provenance

Origin files: `load-driver/cs_pulse_driver.py` (V3 CLI `:522-530`, manifest flow
`:66-326`, post-load Wizard D + attribution `:284-311`, `--extend`/`--phase`
flags `:392-402`, stale-server pre-flight `:212-239`, cold-start note `:284-286`);
`load-driver/scenarios/scenario_manifest.py` (`ManifestCSVGenerator` `:697`,
`ARC_TEMPLATES` `:138`, `CLASSIFICATION_TO_ARC` `:488-492`, silent_churn fix
`:451-456`, `generate_all` `:1624`, trajectory synthesis `:1457-1580`, phase
windowing `:1133-1151`, 4-CSV set `:4319-4336`, `_validate_post_process` +
discovered IDs `:3452,3468-3471`, RNG seeding `:1106,1471,1544`, RefRegistry reset
`:1203-1205`); `load-driver/manifests/*.json` (35 manifests; `predictive_11_saas.json`
the 11-KPI Power-of-1 set); `kpi-dashboard/backend/utils/arc_classifier.py:137`
(canonical 8 arcs); `kpi-dashboard/backend/tests/{test_scorer_parity.py,
test_ask_ai_mcp_parity.py,test_onboarding_e2e.py,test_demo_manifests.py}`;
`docker-compose.{ec2-loaddriver,loaddriver,loaddriver-standalone}.yml`. Commit
provenance: `b763acfe6` (silent_churn unreachable), `54da5adfe` + `54c728bc7`
(attribution backfill / point-in-time health), `a15e71edf` (Month-1 = 4 CSVs),
`3c91e6d72` (3-CSV onboarding), `59eeb7f09` (post-process discovered IDs).

Authored 2026-08-07 against HEAD `8ef08b6b0`, and validated the same day (see
Validation Note). Two claims from prior notes were checked and dropped as
uncited: the "10s vs 650s" sim-engine performance figure (not present anywhere in
the tree — the `--extend`/manifest-vs-`simulation/` engine replacement is real,
but the numbers are unverified) and a UTC-mtime incremental-load gotcha (it lives
in Module 09's ingestion pipeline, not the load-driver).

## Validation Note

Validated 2026-08-07. A fresh agent, given ONLY this spec in isolation, built a
self-contained implementation and wrote pytest tests executing the spec's literal
pseudocode. Result: **18 passed (12 acceptance criteria + 6 defect proofs, each
with the corrected version alongside)**, and **six real defects** — the largest
cluster the library has seen, and all one root cause: the module's headline guard
was built but unplugged, and everything it depended on was referenced-but-
undefined.

- **Defect 1 — the round-trip guard is DEAD (never invoked) [MOST SEVERE, shapes
  c/d].** `run_acceptance` called only `check_arc_vocabulary`, never
  `assert_arc_roundtrip` — yet the round-trip is "the guard that would have caught
  silent_churn being reclassified as crisis_recovery" and the whole module's
  reason to exist. Proven: a `silent_churn` account whose generated data
  classifies as `crisis_recovery` sailed through `run_acceptance` with
  `status="success"`. *Fixed:* the harness now loops the accounts and calls
  `assert_arc_roundtrip` before onboarding; the AC now requires the guard run
  *inside* `run_acceptance`, not merely exist.
- **Defect 2 — `INTENDED_CANONICAL` undefined [HIGH, shape c].** The guard indexed
  a table defined nowhere → `KeyError` even if wired. *Fixed:* declared as a named
  Config table (story_arc → canonical-8 arc) and threaded into the harness.
- **Defect 3 — `ARC_TEMPLATES`/`CLASSIFICATION_TO_ARC` used as bare globals [HIGH,
  shape a/c].** Piece 2 defined them only as function *parameters*; the harness
  referenced them as globals → `NameError`. *Fixed:* threaded as `run_acceptance`
  and `generate_all` parameters.
- **Defect 4 — trajectory constants left as prose [MEDIUM, shape d].** `NOISE_SD`,
  `DECAY_PER_MONTH`, etc. used but never assigned → `NameError`; "means the same
  twice" only holds if pinned. *Fixed:* concrete defaults, listed under Config.
- **Defect 5 — `generate_all` had no piece and no determinism contract [MEDIUM,
  shape c].** The function the whole Determinism AC rests on was called but never
  defined; the agent confirmed a natural per-stream `hash(kpi_code)` reading is
  stable in-process but diverges across `PYTHONHASHSEED` (`450f…` vs `d566…`),
  while the single-rng reading stays identical (`a46c…` both). *Fixed:* added
  piece 6 defining `generate_all` — single threaded `rng`, ordered iteration, no
  `hash(str)`, byte-identity contract.
- **Defect 6 — lifecycle ARR event was a requirement with no code [MEDIUM, shape
  d].** Data Shapes / Nullable rule / AC required handling `lifecycle`
  (`expand +25%` etc.) and doing nothing when null, but no piece referenced it —
  the null-safety AC passed *vacuously* while the positive behavior was
  unimplemented (`expand` never moved ARR). *Fixed:* `apply_lifecycle` defined and
  called in `generate_all`; a positive-case AC added so the non-null path is
  exercised.

Confirmed NOT defects: null `decline_start_month` genuinely flattens; `recovering`
produces a real V; `validate_post_process`'s missing-account path is None-safe.

**Library-level note:** shape (d) — *a required behavior living only in a
comment/promise with no code calling it* — and its sibling shape (c) — *a
referenced-but-undefined helper/table* — together account for all six defects
here and were the whole story in Module 00 too. The reliable tell across the last
two modules: any name that appears in a Gotcha, an AC, or a Boundary bullet but is
only *mentioned* — never assigned, never called by a Build-Prompt line — is
almost certainly a defect. Grepping every such name against the pieces that
actually invoke it is now the highest-yield review step.
