# 00 — Integration & Bootstrap

**Layer:** Foundation (built *last* in knowledge, run *first* in execution — the chassis every other module bolts onto)

**Status:** ✅ Validated — see [Validation Note](#validation-note) at the bottom.
A spec-only fresh-agent rebuild (2026-08-07, real SQLAlchemy + sqlite) proved two
HIGH defects with executable tests — a schema-drift check that silently ignored
UNIQUE constraints (half-false headline guarantee) and an orphaned feature-toggle
system the sequencer never consulted — both fixed below.

## Purpose

Everything modules 01–09 build is a component; this module is the **car**. It
owns the single Flask `app`, the single `db`, the schema-authority decision, the
shared config-resolution services, the feature-toggle system, and — the load-
bearing seam — the **`process_data` orchestration** that sequences ingestion →
scoring → graph → signals → wizards into one idempotent, fault-isolated pipeline.
Its reason to exist: eleven individually-correct modules do not compose into a
running system on their own. The seams between them — how the schema is actually
created, which of two vertical columns wins, whether a threshold edit reaches
every read site, what order the pipeline stages run in — are where an integration
silently produces wrong numbers, and no other module owns a seam. This module's
acceptance criterion is therefore a *whole-system* one: the canonical 4-CSV ×
11-KPI onboarding runs end to end and the numbers come out right.

## Boundary

**Owns:**
- **App + db bootstrap**: one module-level `app` (not a factory), one shared
  `db`, fail-fast config loading, and the rule for how the schema comes to exist
  (Gotcha 1).
- **Schema authority + drift detection**: the decision that migrations — not
  `db.create_all()` — are the source of truth for schema *changes*, and an
  executable check that the live DB's constraints match the ORM (Gotcha 1).
- **The `process_data` stage sequencer**: stage order, per-stage fault isolation
  (a stage never takes down the pipeline), idempotency, structured result
  aggregation, and the boundary of which wizards run inline vs. on demand
  (Gotchas 4, 8).
- **Config-resolution services** (single source each): the 3-tier weight
  resolver, the threshold accessor, and the vertical resolver — plus the rule
  that every module reads *these*, never a second copy or a hardcoded value
  (Gotchas 5, 6, 7).
- **The feature-toggle system**: enum, env override, dependency gating, and the
  per-customer gate.
- **The new-tenant bootstrap sequence**: the ordered create→config→key→scaffold
  →load→process flow (which is also the E2E acceptance path).

**Explicitly does not own:**
- Any module's business logic. Scoring is Module 03, the graph is 04, wizards
  are 05, signals are 06, ingestion validation/upsert is 09, the tool layer is
  07, dashboards are 08. This module *sequences and wires* them; it computes no
  KPI, edge, or forecast itself. A stage body that re-derives a score instead of
  calling Module 03 is scope creep.
- The `CustomerApiKey`/model *definitions* — Module 01. This module assembles
  them into one `db.metadata` and owns how that metadata becomes a live schema.
- Tool auth — Module 07 (this module mounts 07's server; it does not
  re-implement auth).

## Dependencies

- **Modules 01–09** as importable engines, each exposing a plain callable this
  module can sequence (a `_impl`/service function, not only a decorated tool —
  see Module 07 Gotcha 2). State the minimal "mountable" interface: models as
  `db.Model` subclasses registered on the one `db.metadata`; each pipeline
  capability as `run_<stage>(customer_id, ...) -> result | None`.
- **A relational DB** (Postgres in the origin) reachable via
  `SQLALCHEMY_DATABASE_URI` or `DATABASE_URL`.
- Deliberately **incrementally buildable**: stand up the app with only Module 01,
  boot it, then add each module behind a feature toggle. A disabled module must
  leave the app booting and the rest of the pipeline working (Acceptance).

### Data Shapes

```
process_data result (structured — never string-parsed, see Gotcha 8):
  status ("success" | "partial" | "failed"),
  steps_completed (list[str]),
  errors (list[str]),
  scores_written (int — an explicit integer field, NOT recovered by splitting a
    step-description string),
  stages (dict: stage_name -> {ok: bool, detail: str})

Vertical resolution (ONE source of truth, see Gotcha 6):
  canonical_vertical (string, normalized long form e.g. "dc2_s", "saas_premium")
  — derived once from the single canonical column and used for BOTH the data
  path AND scoring. Nullable upstream columns default through normalize_vertical,
  never to two different fallbacks.

Weight resolution (3-tier, ordered — Gotcha 7):
  tier1: CustomerConfig weights from DB (Wizard-C calibrated) — if present,
  else tier2: bootstrap_weights_config.json — if present,
  else tier3: kpi_definitions default for the vertical.
  Exactly one resolver; the first non-empty tier wins.
```

**Nullable rule (this module):** `Customer.vertical`, `CustomerConfig.vertical`,
and the DB-weight columns are all nullable. The vertical resolver and weight
resolver must each handle "all tiers empty" by falling through to the documented
default **once**, from **one** function — not via a second parallel resolver with
its own default (Gotcha 7). Test the all-empty path explicitly.

## Engine vs. Config

**Engine (build once):**
- The app-factory-less bootstrap, the single `db`, the schema-authority +
  drift-check logic, the stage sequencer, the three resolvers, the toggle
  manager, and the bootstrap sequence.

**Config (an FDE fills in per client):**
- Which modules/toggles are enabled; env vars and the DB URL; the deployment
  target; the actual config artifacts (`bootstrap_weights_config.json`,
  `health_thresholds.json`, the vertical's `kpi_definitions`) — the "Config
  Pack." The stage *list* is Engine; which optional stages a client runs is
  Config.

## Build Prompt

> Build the integration/bootstrap chassis. Six numbered pieces. Every helper is
> either defined below OR is a named dependency hook whose contract Dependencies
> states — `module01_metadata` (the assembled `db.metadata`), `module03_score`,
> `module04_build_graph`, `module05_wizard_a`/`module05_wizard_b`,
> `module06_signal_scan`, `module09_load_csvs`, and the web framework
> (`Flask`, `SQLAlchemy` as `db`, `Migrate`). This chassis SEQUENCES and WIRES;
> it computes no score, edge, or forecast itself.
>
> Origin references to follow, not reinvent: `kpi-dashboard/backend/
> app_v3_minimal.py` (module-level `app`, `db.init_app`, `create_all` at
> `:112`), `extensions.py:4` (the single `db`), `mcp_server/cs_pulse_onboarding.py:1089`
> (`_process_data_impl`), `mcp_server/process_data_pipeline.py` (the 13 isolated
> stages), `utils/score_calculator.py:36` (the 3-tier weight resolver),
> `utils/health_thresholds.py` (the threshold accessor), `utils/vertical_registry.py`
> (vertical normalization), `feature_toggles.py`.
>
> 1. **App + db + fail-fast config.** One module-level `app` (Gunicorn imports
>    it), one shared `db`, a hard failure if the DB URL is absent:
>    ```
>    # extensions.py
>    db = SQLAlchemy()          # the ONE instance every model binds to
>
>    # app.py — module level, no create_app() factory
>    app = Flask(__name__)
>    app.config.from_object(config_for(os.environ.get("FLASK_ENV", "production")))
>    db_url = os.environ.get("SQLALCHEMY_DATABASE_URI") or os.environ.get("DATABASE_URL")
>    if not db_url:
>        raise ValueError("SQLALCHEMY_DATABASE_URI or DATABASE_URL is required")
>    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
>    db.init_app(app)           # called ONCE per app object
>    Migrate(app, db)
>    ```
>    Any secondary app (e.g. a minimal app for a worker/MCP process) binds the
>    SAME `db` and calls `db.init_app` on its own app object exactly once — one
>    `db`, N app objects, never N `db` instances (Gotcha 2).
>
> 2. **Schema authority + drift check.** `create_all()` only creates *missing*
>    tables — it never ALTERs an existing one to add a column or constraint. So
>    it cannot be the authority for schema *changes*; migrations are. On a fresh
>    DB, `create_all()` is a convenience; on an existing DB, a declared-but-
>    absent constraint is invisible until it corrupts a transaction. Make the
>    drift executable so it fails loudly at boot instead of silently at runtime
>    (Gotcha 1):
>    ```
>    def ensure_schema(app, db, run_migrations):
>        with app.app_context():
>            db.create_all()              # fills MISSING tables only
>            run_migrations(db)           # applies ALTERs create_all cannot
>            report = check_constraint_drift(db)
>            if report.missing:
>                raise SchemaDriftError(
>                    f"ORM declares constraints absent in the live DB: {report.missing}. "
>                    f"A migration is required — create_all cannot add them.")
>
>    def check_constraint_drift(db):
>        # Compare ORM-declared FKs AND uniques against the live DB's actual
>        # constraints via the inspector. Returns descriptors the ORM declares
>        # that the DB lacks. Covering uniques (not only FKs) is what catches
>        # Gotcha 1's cross-tenant collision, where a UNIQUE was absent from the DB.
>        insp = inspect(db.engine)
>        missing = []
>        for table in db.metadata.sorted_tables:
>            # --- foreign keys ---
>            declared_fk = {f"{fk.column.table.name}.{fk.column.name}"
>                           for c in table.columns for fk in c.foreign_keys}
>            live_fk = {f"{fk['referred_table']}.{col}"
>                       for fk in insp.get_foreign_keys(table.name)
>                       for col in fk["referred_columns"]}
>            missing += [f"FK {table.name}->{d}" for d in declared_fk if d not in live_fk]
>            # --- unique constraints (a missing UNIQUE is the cross-tenant
>            #     collision in Gotcha 1 — checked here alongside FKs) ---
>            declared_uq = {tuple(sorted(uc.columns.keys()))
>                           for uc in table.constraints
>                           if isinstance(uc, UniqueConstraint)}
>            live_uq = {tuple(sorted(u["column_names"]))
>                       for u in insp.get_unique_constraints(table.name)}
>            missing += [f"UNIQUE {table.name}{cols}" for cols in declared_uq if cols not in live_uq]
>        return DriftReport(missing=missing)
>    ```
>    (`UniqueConstraint`/`inspect` are SQLAlchemy. The acceptance test pins the
>    behavior, not the exact descriptor strings: given a table whose ORM declares
>    an FK **or** a UNIQUE the live DB lacks, `ensure_schema` raises rather than
>    booting — both cases, since a missing UNIQUE is precisely Gotcha 1's
>    cross-tenant collision.)
>
> 3. **Config-resolution services — one resolver each.** Weight hierarchy is a
>    single ordered function; the first non-empty tier wins. Do not build a
>    second resolver with its own default (Gotcha 7):
>    ```
>    def resolve_weights(customer_id, vertical):
>        db_w = module01_customer_config_weights(customer_id)   # tier 1 (Wizard C)
>        if db_w: return db_w
>        boot = load_bootstrap_weights(customer_id)             # tier 2 (JSON)
>        if boot: return boot
>        return default_weights(vertical)                       # tier 3 (kpi_definitions)
>    ```
>    Thresholds come from ONE accessor reading the JSON — no literal 70/50
>    anywhere else (Gotcha 5):
>    ```
>    THRESHOLDS = load_json("config/health_thresholds.json")  # {"healthy":{"min":70},"at_risk":{"min":50}}
>    def classify(health) -> str:
>        if health is None: return "no_data"
>        if health >= THRESHOLDS["healthy"]["min"]:  return "healthy"
>        if health >= THRESHOLDS["at_risk"]["min"]:  return "at_risk"
>        return "critical"
>    ```
>    Vertical is resolved ONCE, from one canonical column, and drives BOTH the
>    data path and scoring (Gotcha 6):
>    ```
>    def resolve_vertical(customer_id) -> str:
>        raw = (module01_customer_config_vertical(customer_id)   # the ONE canonical source
>               or module01_customer_vertical(customer_id))      # legacy, same value at create
>        return normalize_vertical(raw) if raw else "dc2_s"      # single fallback, one place
>    def data_path(customer_id):
>        return f"verticals/customer{customer_id}-{resolve_vertical(customer_id)}/data"
>    ```
>
> 4. **Feature toggles.** Enum + env override + dependency gating + per-customer
>    gate; a disabled toggle degrades cleanly:
>    ```
>    def is_enabled(toggle, customer_id=None) -> bool:
>        cfg = TOGGLES[toggle]
>        env = os.environ.get(f"FEATURE_{toggle.name}")
>        enabled = (env.lower() in ("true","1","yes")) if env is not None else cfg.default
>        if not enabled: return False
>        for dep in cfg.dependencies:               # off if any dependency is off
>            if not is_enabled(dep, customer_id): return False
>        if customer_id is not None and cfg.per_customer:
>            return per_customer_row_enabled(toggle, customer_id)  # defaults True if no row
>        return True
>    ```
>
> 5. **The `process_data` stage sequencer.** Ordered stages; each isolated (a
>    stage returns a result or None on failure and NEVER raises out of the
>    pipeline); idempotent; the result is a structured object with an explicit
>    integer `scores_written` (Gotcha 8). Wizards A and B run inline; C and D do
>    not (Gotcha 4). Stage order carries real dependencies — signal scan reads
>    health, so it follows scoring (Gotcha 9):
>    ```
>    def run_stage(name, fn, result):
>        try:
>            out = fn()
>            result.stages[name] = {"ok": True, "detail": str(out)}
>            result.steps_completed.append(name)
>            return out
>        except Exception as e:               # per-stage isolation: log it, return None
>            result.stages[name] = {"ok": False, "detail": f"non-fatal: {e}"}
>            result.errors.append(f"{name}: {e}")
>            return None
>
>    STAGE_ORDER = ["score", "publish_health", "signal_scan", "wizard_a",
>                   "llm_tier1", "wizard_b", "signal_analyst", "roi", "index",
>                   "record_run"]   # 'score' precedes 'signal_scan' by contract
>
>    # Bind gate-able stage names to Toggle enum members (piece 4). A stage whose
>    # toggle is off is skipped; core stages (score/publish_health/signal_scan/
>    # wizard_a) have no entry, so they run unconditionally. This mapping is what
>    # connects the toggle manager to the pipeline — without it it's dead code.
>    STAGE_TOGGLE = {"llm_tier1": Toggle.WITH_LLM, "signal_analyst": Toggle.SIGNAL_ENGINE,
>                    "roi": Toggle.ROI, "index": Toggle.QDRANT_INDEX,
>                    "record_run": Toggle.AUDIT}
>
>    def process_data(customer_id, mode="auto"):
>        assert mode in ("auto", "full_recalc")
>        result = ProcessResult(status="", steps_completed=[], errors=[],
>                               scores_written=0, stages={})
>        if fresh_or_incremental_csvs(customer_id):
>            module09_load_csvs(customer_id, data_path(customer_id))  # 09 owns validation/upsert
>        n = run_stage("score", lambda: module03_score(customer_id, mode), result)
>        result.scores_written = int(n or 0)          # explicit int, not parsed from a string
>        run_stage("publish_health", lambda: publish_health_events(customer_id), result)
>        run_stage("signal_scan", lambda: module06_signal_scan(customer_id), result)  # after score
>        run_stage("wizard_a", lambda: module05_wizard_a(customer_id), result)
>        if is_enabled(STAGE_TOGGLE["llm_tier1"], customer_id):     # WITH_LLM (default off)
>            run_stage("llm_tier1", lambda: run_llm_tier1(customer_id), result)
>        if journey_count(customer_id) >= MIN_ACCOUNTS_FOR_WIZARD_B:
>            run_stage("wizard_b", lambda: module05_wizard_b(customer_id), result)
>        for extra in ("signal_analyst", "roi", "index", "record_run"):
>            if not is_enabled(STAGE_TOGGLE[extra], customer_id):   # piece 4 gate — skip disabled
>                continue
>            run_stage(extra, lambda e=extra: OPTIONAL_STAGES[e](customer_id), result)
>        result.status = ("success" if result.steps_completed and not result.errors
>                         else "failed" if not result.steps_completed else "partial")
>        return result
>    ```
>    Idempotency lives in the score stage (Module 03): in `auto` mode an already-
>    scored `(account_id, month)` is skipped (`ON CONFLICT DO NOTHING`);
>    `full_recalc` updates. Re-running `process_data` writes no duplicate rows.
>    Wizard C (calibration) and Wizard D (predictor) are NOT stages here — they
>    fire on their own explicit triggers; folding them in is a known bug
>    (Gotcha 4).
>
> 6. **New-tenant bootstrap.** One ordered transaction, then load + process. The
>    vertical is written to its single canonical home; if a legacy second column
>    exists it is set from the same value in the same call so the two cannot
>    diverge (Gotcha 6):
>    ```
>    def create_customer(name, domain, vertical, admin_email, tier=None):
>        v = normalize_vertical(vertical)
>        cust = Customer(name=name, domain=domain, vertical=v); db.session.add(cust); db.session.flush()
>        db.session.add(User(customer_id=cust.customer_id, email=admin_email, ...))
>        db.session.add(CustomerConfig(customer_id=cust.customer_id, vertical=v,  # same v, one call
>                                      **kpi_tier(tier, v)))
>        raw_key = generate_api_key(cust.customer_id)      # returned ONCE, stored hashed (Module 01)
>        provision_data_dir(cust.customer_id, v)
>        for t in DEFAULT_CUSTOMER_TOGGLES: enable_per_customer(t, cust.customer_id)
>        db.session.commit()
>        return {"customer_id": cust.customer_id, "api_key": raw_key}
>    # then: upload the 4 Month-1 CSVs -> process_data(customer_id) -> complete_onboarding()
>    ```

## Acceptance Criteria

- **The golden E2E runs.** A fresh tenant onboarded with the canonical **4 CSVs
  × 11 KPIs** → `process_data` returns `status="success"`, `scores_written > 0`,
  L1→L4 scores exist, the context graph is populated, and a dashboard payload
  (Module 08) reads non-empty. This is the whole point of the module — assert it
  end to end against a golden fixture.
- **Idempotent re-run.** Calling `process_data(customer_id, "auto")` twice
  writes no duplicate score rows and leaves `scores_written` on the second run
  reflecting zero *new* writes — assert row counts are unchanged.
- **Schema drift fails loudly (Gotcha 1).** Given a table whose ORM declares an
  FK **or a UNIQUE** the live DB lacks, `ensure_schema` raises `SchemaDriftError`
  naming the constraint — it does NOT boot silently. Assert **both** constraint
  kinds independently: a missing FK raises, AND a missing UNIQUE raises (the
  cross-tenant-collision case — a drift check that only compares FKs passes
  silently on a missing unique, which is the exact half-guarantee to avoid).
  Then: matched schema → boots; `create_all` alone on an already-existing table
  adds neither the missing FK nor the missing unique (prove the trap the check
  guards).
- **A disabled module still boots the pipeline.** With an optional stage's
  toggle off, the app boots and `process_data` returns `status` in
  {`success`,`partial`} with that stage absent from `steps_completed` and the
  others intact — one module off does not fail the chassis.
- **Stage isolation (Gotcha 9 ordering + fault).** A stage that raises records a
  `non-fatal` entry in `errors`/`stages[name].ok=False` and the remaining stages
  still run. Assert `STAGE_ORDER.index("score") < STAGE_ORDER.index("signal_scan")`
  — the signal scan must not run before scores exist.
- **Wizards A/B inline, C/D not (Gotcha 4).** A default `process_data` runs
  `wizard_a` (and `wizard_b` when `journey_count >= MIN_ACCOUNTS_FOR_WIZARD_B`)
  and does NOT run wizard C or D. Assert wizard_b is *absent* from
  `steps_completed` when journeys < the minimum, and that no C/D stage exists in
  `STAGE_ORDER`.
- **`scores_written` is a real integer (Gotcha 8).** Assert `result.scores_written`
  is an `int` set from the score stage's return value — not recovered by
  splitting a step-description string. A test that mangles step-description text
  must not change `scores_written`.
- **One weight resolver, all-tiers-empty falls through once (Gotcha 7).** With
  DB weights empty and no bootstrap JSON, `resolve_weights` returns the
  `kpi_definitions` default; with DB weights present they win. Assert there is a
  single resolver — a second parallel resolver with its own default is the bug.
- **One vertical source (Gotcha 6).** `resolve_vertical` returns the same
  normalized value used for BOTH `data_path` and scoring; a customer whose two
  columns disagree resolves deterministically from the canonical one (not two
  different answers). Assert `data_path` and the scoring vertical are equal.
- **Thresholds centralized (Gotcha 5).** `classify(49)`→critical, `(50)`→at_risk,
  `(70)`→healthy, `(None)`→no_data, all driven by the JSON; changing the JSON
  moves every classification. Assert no literal `70`/`50` health comparison
  exists outside `classify` (source inspection with a mutation: change the JSON
  and assert classification boundaries move).

## Reference Test Harness

1. **Golden E2E** — a fixture tenant + 4 CSVs × 11 KPIs (the canonical default),
   run through `create_customer → load → process_data`, asserting the structured
   result and a golden snapshot of L1→L4 + graph counts + a dashboard payload.
   This is the module's headline test and the "regenerate-and-verify as-is"
   proof (pairs with Module 11).
2. **Drift-check pair** — one DB matching the ORM (boots), one with a table
   missing a declared FK (`ensure_schema` raises). Plus a mutation: add an FK to
   a model without a migration and assert the check catches it.
3. **Idempotency** — run `process_data` twice; assert score-row counts stable.
4. **Toggle/degradation** — each optional stage disabled in turn; assert the
   pipeline completes with that stage absent and the rest intact.
5. **Resolver singularity** — weight all-tiers-empty fallthrough; vertical
   two-column-disagreement determinism; threshold JSON-move. Each with a mutation
   proving a second resolver / hardcoded threshold would be caught.
6. **Stage-order invariant** — assert `score` precedes `signal_scan`; a
   raising stage is isolated and non-fatal.

## Known Gotchas

**1. `db.create_all()` is the schema authority, so declared constraints silently
never exist**
*Symptom:* A transaction rolls back with a foreign-key error against a
constraint the ORM clearly declares; or two tenants collide on an ID whose
"unique" constraint was never created — on some DBs but not others.
*Root cause:* Schema is created by `db.create_all()` (`app_v3_minimal.py:112-114`),
which creates only *missing tables* and never ALTERs an existing one, while the
Alembic baseline is a **no-op stamp** (`alembic/versions/2026_03_29_0001_...py:21-28`,
`upgrade()` = `pass`). So any FK/constraint added to a model *after* a DB was
first provisioned is present in the ORM and absent in that DB. Confirmed twice in
the origin by the opposite fix — removing ORM FKs that DID exist in the DB and
broke V2 transactions (commits `0177a1f50`, `4250e7644`, retired
`playbook_executions` FKs).
*Fix:* Migrations own schema *changes*; `create_all` is a fresh-DB convenience
only. Run an executable `check_constraint_drift` at boot that compares ORM-
declared constraints to the live DB and raises, so drift fails loudly at startup
rather than silently mid-transaction. Test the missing-FK case explicitly.

**2. One `db`, but multiple app objects re-initializing it**
*Symptom:* Intermittent "application context" errors, or a worker/tool process
that sees a different engine than the web app.
*Root cause:* The web app (`app_v3_minimal.py:29`) and the MCP minimal apps
(`cs_pulse_mcp_server.py:93`, `common.py:80`) each create their own `Flask` and
call `db.init_app` on the single `extensions.db` — up to three inits against one
instance. Correct as long as there is exactly one `db` and each app object inits
it once; it breaks the moment someone creates a second `SQLAlchemy()`.
*Fix:* One `db` in `extensions.py`, imported everywhere; N app objects each
calling `db.init_app(their_app)` once; never a second `SQLAlchemy()` instance.
Every DB access happens inside `with app.app_context():`.

**3. Two migration systems, one of them running every boot**
*Symptom:* A schema change works locally (someone ran the hand-written script)
but not in a fresh deploy, or runs twice.
*Root cause:* Formal Alembic (`alembic/versions/`, only the no-op baseline) AND
hand-written idempotent scripts (`migrations/*.py`) coexist; one
(`add_customer_id_to_qualitative_signals.py`) is executed on every boot
(`app_v3_minimal.py:116-121`) to fix a PK collision `create_all` could never
apply to a pre-existing table.
*Fix:* Pick one authority (Alembic) and fold the hand-written idempotent ALTERs
into versioned migrations; if a boot-time idempotent runner is kept, it must be
idempotent-by-construction (guarded `IF NOT EXISTS`) and covered by the drift
check in Gotcha 1.

**4. Auto-running every wizard inside `process_data`**
*Symptom:* Ingesting a CSV silently recalibrates weights or reruns the
predictor, changing scores nobody asked to change; or the pipeline is slow
because it does far more than ingest.
*Root cause:* Wizards A and B legitimately run inline (stages 5 and 7,
`process_data_pipeline.py:237,346`) because they are incremental read-models —
but Wizards C (weight calibration) and D (predictor) are decoupled *on purpose*
and fire on explicit triggers. Folding them into the ingest path is a tempting
"run all wizards" cleanup that is actually a bug.
*Fix:* Keep C/D out of `STAGE_ORDER`; only A and B are inline, and B is gated on
`journey_count >= MIN_ACCOUNTS_FOR_WIZARD_B` (silently no-ops below it —
`process_data_pipeline.py:365`). Reject future "auto-run all wizards" changes.

**5. Centralized thresholds that are also hardcoded in five other files**
*Symptom:* Editing `health_thresholds.json` moves the dashboards and the
pipeline but not the arc classifier, the graph builder, or the invariant checks —
so "at risk" means 70 in one place and a hardcoded 50 in another.
*Root cause:* `classify()` reads the JSON (`utils/health_thresholds.py:42-49`),
but literal `70`/`50` comparisons live in `arc_classifier.py:519`,
`context_graph.py:356,358`, `context_graph_invariants.py:795,812`,
`playbook_lifecycle.py`. Centralization was started, not finished.
*Fix:* One `classify()`/threshold accessor; every read site calls it. Guard with
a source-inspection test that fails on a literal health-threshold comparison
outside the accessor, and a JSON-move test proving boundaries shift everywhere.

**6. The vertical lives in two columns with two resolvers and two defaults**
*Symptom:* A tenant is scored as `dc2_s` while its data loads from a
`saas_premium` folder (or vice-versa); a `== "saas_premium"` check silently
misses.
*Root cause:* `Customer.vertical` (short code, `models.py:20`) drives the data-
folder path in `_process_data_impl` (`cs_pulse_onboarding.py:1123-1125`), while
`CustomerConfig.vertical` (long form, `models.py:82`, default `saas_premium`)
drives scoring via `vertical_registry.get_vertical_for_customer`. Two sources of
truth, each with its own `dc2_s` fallback. They agree only because
`create_customer` writes both from one value — nothing enforces it afterward.
*Fix:* One `resolve_vertical` reading the single canonical column, normalized,
with one fallback; both the data path and scoring derive from it. If a legacy
second column must exist, write it from the same value in the same call and never
read it independently.

**7. Two parallel config-resolution systems**
*Symptom:* Weights resolve differently depending on which code path asked; a
Wizard-C calibration "takes" on the dashboard but not in a wizard.
*Root cause:* `ScoreCalculator._load_config` (`utils/score_calculator.py:36-89`)
is the 3-tier DB→bootstrap-JSON→defaults resolver, but a *different*
`config_resolver.resolve_config` (`utils/config_resolver.py:93`) resolves a
`VerticalTemplate→CustomerVerticalConfig→AccountConfigOverride` chain over
entirely different tables. Two systems, two defaults.
*Fix:* One resolver owns weight/threshold resolution; the second system (if
retained for a different concern) must not also resolve weights. The Build
Prompt's `resolve_weights` is the single authority; test the all-tiers-empty
fallthrough happens once.

**8. Recovering a number by string-splitting a log message**
*Symptom:* A reported "scores written" count is wrong or crashes after an
unrelated wording change to a step description.
*Root cause:* `scores_written` is recovered as
`int(_health_step.split('_')[-2])` (`cs_pulse_onboarding.py:2168`), coupling a
count to the exact text of a step-description string produced elsewhere
(`process_data_pipeline.py:225`).
*Fix:* Return counts as structured integer fields from the stage that produced
them; never parse them back out of human-readable text. Test that changing a
step-description string does not change `scores_written`.

**9. Stage order carries silent data dependencies**
*Symptom:* Signals scan finds nothing, or wizards read stale/absent health,
because a stage ran before the stage it depends on.
*Root cause:* The signal scan reads health scores, so it must run *after*
scoring — a real dependency the origin encodes only by call order (the scan was
deliberately moved after health scoring, `cs_pulse_onboarding.py:2052-2053`).
*Fix:* Make the ordering an explicit, asserted invariant
(`STAGE_ORDER.index("score") < STAGE_ORDER.index("signal_scan")`), not just the
happenstance of call sequence.

## Provenance

Origin files: `app_v3_minimal.py` (module-level `app` `:29`, `db.init_app` `:95`,
`Migrate` `:96`, config/DB-URL fail-fast `:65-87`, `create_all` `:112-114`,
boot-time hand migration `:116-121`, 82 blueprint registrations `:373-1334`);
`extensions.py:4` (single `db`); `models.py` (43 models, `Account.customer_id`
ORM FK `:107`, plain-int no-FK columns `:658,1983,2092`, event hooks late-imported
`:1651`); `alembic/versions/2026_03_29_0001_baseline_stamp_existing_schema.py:21-28`
(no-op baseline), `alembic/env.py:40`, `migrations/*.py` (hand scripts);
`mcp_server/cs_pulse_onboarding.py` (`_process_data_impl` `:1089`, ingestion paths
`:1131-1191`, vertical read `:1123`, stage calls `:2055-2169`, scores_written
string-parse `:2168`, UTC mtime fix `:1172-1176`), `mcp_server/process_data_pipeline.py`
(13 isolated stages, idempotency `:88-122,180-197`, Wizard-B gate `:365`,
record_wizard_run `:671`); `utils/score_calculator.py:36-89` (3-tier weights),
`utils/config_resolver.py:93` (the parallel resolver), `utils/health_thresholds.py`
(+ hardcoded 70/50 at `arc_classifier.py:519`, `context_graph.py:356,358`,
`context_graph_invariants.py:795,812`, `playbook_lifecycle.py`),
`utils/vertical_registry.py:36-107`; `feature_toggles.py` (enum, deps, per-customer
gate `:256-283`); `cs_pulse_mcp_server.py:93` / `common.py:80` (dual minimal apps);
`create_customer` `cs_pulse_onboarding.py:536-709`. Commit provenance: `f91e55587`
(UTC mtime), `9eeb7973c` (qualitative_signals PK), `0177a1f50` + `4250e7644`
(FK/DB drift), `cce93f7c4` (record_wizard_run), `7bc577bd5` (vertical default).

Authored 2026-08-07 against HEAD `b38689c5d`, and validated the same day (see
Validation Note).

## Validation Note

Validated 2026-08-07. A fresh agent, given ONLY this spec in isolation, built a
self-contained implementation using **real SQLAlchemy + sqlite** (so the
schema-drift check ran against an actual DB) plus fakes for the `module01…09`
hooks, and wrote pytest tests executing the spec's literal pseudocode. Result:
**14 passed (9 acceptance criteria + 2 defect proofs with corrected versions + a
rule-out + idempotency)**, and **two real defects, both HIGH** — each proven by a
test that runs the spec-as-written and then the fix.

Most of the chassis held up under attack — the FK half of the drift guard raises
correctly (the agent explicitly ruled out my suspicion that the FK name-munging
was a dead no-op), the three resolvers are singular and fall through once, the
stage-order invariant holds, `scores_written` stays an int under
step-string mangling, wizards C/D are absent from `STAGE_ORDER`, `classify`
boundaries move with the JSON, and the `lambda e=extra` loop has no late-binding
bug. The two defects:

- **Defect 1 — HIGH (shapes a + d).** `check_constraint_drift` promised "FKs
  **and** uniques" in its comment, and Gotcha 1's own symptom names the missing-
  UNIQUE cross-tenant collision — but the pseudocode only iterated
  `get_foreign_keys`. Proven: a live DB with the FK present but the ORM-declared
  `UNIQUE(email)` absent yielded `report.missing == []`, so `ensure_schema`
  **booted silently on drifted schema** — the module's *headline* guarantee was
  half-false. *Fixed:* the drift check now compares `UniqueConstraint`s via
  `get_unique_constraints` alongside FKs, the AC asserts both constraint kinds
  independently, and the "illustrative" hedge now names both cases.
- **Defect 2 — HIGH (shapes c + d).** The entire piece-4 feature-toggle manager
  was built but **never consumed** — `process_data` contained no `is_enabled`
  call and no stage-name→`Toggle` mapping existed — so the Boundary "owns the
  toggle system," the Dependencies "add each module behind a toggle," and the AC
  "a disabled module still boots the pipeline" were all unsatisfiable against the
  literal pseudocode (a disabled `roi` still ran). *Fixed:* added the
  `STAGE_TOGGLE` mapping, gated `llm_tier1` on `WITH_LLM` and the optional-stage
  loop on `is_enabled(...)`, so a disabled stage is skipped while the rest run.

No shape-(b) or shape-(e) defects. **Library-level note:** shape (d) — a required
behavior living only in a comment/promise with no executable code behind it —
struck twice again ("FKs and uniques" in a comment; a whole subsystem wired
nowhere). This is now the single most recurrent defect class across the library;
the reliable tell is a component or clause named in prose that no Build Prompt
line actually *calls*.
