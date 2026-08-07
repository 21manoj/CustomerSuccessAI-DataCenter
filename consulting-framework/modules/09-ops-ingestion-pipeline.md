# 09 — Ingestion & Onboarding Pipeline

**Layer:** Ops

**Status:** ✅ Validated — see [Validation Note](#validation-note) at the bottom.

## Purpose

Get a client's data into the platform and orchestrate everything that has to
happen afterward, in the right order, idempotently, without silent partial
failures. This is the module an FDE spends the most hands-on time in during
a real engagement (every client's source data is different and messy), and
it's the module where a silent no-op costs the most — a pipeline that reports
success while having processed nothing looks identical to a working one
until someone notices the numbers never move.

## Boundary

**Owns:**
- Upload + validation of source data (CSV or API payload) BEFORE it reaches
  the database — types, required columns, enum membership, referential
  sanity (shift-left: validate at the boundary, so downstream modules can
  assume clean input).
- Freshness detection: deciding whether there is genuinely new data to
  process, so a re-run is a cheap no-op instead of a redundant full
  recompute — and so a run with real new data is never *wrongly* treated as
  a no-op (see Gotcha 1, a real bug fixed in the reference system today).
- Stage orchestration: running the downstream modules' entry points in a
  fixed, dependency-correct order, with per-stage timing, per-stage
  failure isolation, and a single structured result.
- Idempotency at the ingestion level: re-uploading the same file twice does
  not duplicate rows.

**Explicitly does not own:**
- What any individual stage DOES — health scoring (03), graph building (04),
  wizard analysis (05), signal enrichment (06) each own their own logic. This
  module only decides when to call them, in what order, and what to do when
  one fails.
- Idempotency INSIDE a stage (e.g. Module 03's already-scored-month skip) —
  each stage owns its own re-entrancy. This module's idempotency guarantee
  is only about not double-inserting the same source rows.
- Connectors to third-party systems (Slack/CRM/ticketing APIs). Those are
  per-engagement integrations that call this module's upload entry point;
  the entry point itself is source-agnostic.

## Dependencies

- **Module 01 (Data Model):** `Customer`/`Account` — accounts are resolved
  or created during ingestion.
- **Modules 03, 04, 05, 06:** invoked as pipeline stages. Each is optional —
  a client without a causal graph simply has that stage absent from the
  stage list; the pipeline must not assume every stage exists.

### Data Shapes

```
UploadResult: file_type (string), rows_accepted (int), rows_rejected (int
              — a count of ROWS, not of errors; one row with three bad
              columns is ONE rejected row. rows_accepted + rows_rejected
              MUST equal the input row count),
              errors (list of {row_number, column, message} — may contain
              several entries for the same row_number),
              stored_path (string or null — null in validate_only mode and
              when no file storage is configured; non-null otherwise, so it
              needs a real producer, see Build Prompt piece 2),
              validated_only (bool)

PipelineResult: customer_id, mode ('auto' | 'full_recalc'), status
              ('success' | 'partial' | 'failed'), stages (list of
              StageResult), timings (dict stage_name -> seconds), total
              (float seconds)

StageResult: name (string), status ('completed'|'skipped'|'failed'),
             detail (string — for 'skipped' this MUST say WHY, e.g.
             "no_new_data", "feature_disabled"; never a bare "skipped"),
             error (string or null)

Ingestion state (per customer). TWO timestamps, both UTC, both stored
explicitly (never derived from a MAX() over a data table, see Gotcha 2):
             last_ingested_at  — moved ONLY by a successful persist.
             last_processed_at — moved ONLY by a completed process_data run.
                                 This is what freshness compares against.
             One mark CANNOT do both jobs: an upload necessarily runs AFTER
             the files it reads were written, so comparing file mtimes
             against last_ingested_at makes every first pipeline run a
             no-op — the precise silent-no-op failure this module exists to
             prevent. See Gotcha 5.
```

## Engine vs. Config

**Engine (build once):**
- Two-phase validation: a `validate_only` mode that returns exactly the same
  `UploadResult` shape as a real upload but persists nothing — so a client
  can dry-run a file before committing to it.
- UTC-normalized freshness detection with an explicit stored timestamp.
- Stage orchestration with per-stage isolation: a non-critical stage that
  raises is caught, recorded as `failed` in its `StageResult`, and the
  pipeline continues; a critical stage that raises aborts the run. Which
  stages are critical is Config, but the mechanism is Engine.
- Structured skip reasons (never a bare boolean or a silent no-op).
- Row-level idempotency via a natural key per file type.

**Config (an FDE fills in per client):**
- The column schema per file type, and the per-column validators.
- The stage list and their order, and which stages are critical vs.
  best-effort.
- The natural key per file type used for dedup.

## Build Prompt

> Build the ingestion & onboarding pipeline. SIX numbered pieces. Every
> helper called below is defined below — there are no undefined helpers, and
> no normative rule lives only in a comment (see Gotcha 6).
>
> 0. **Schema + natural-key indexes.** Ship DDL before any code: an
>    `ingestion_state` table (customer_id PK, `last_ingested_at`,
>    `last_processed_at`), plus for every file type a data table AND
>    ```
>    CREATE UNIQUE INDEX ux_<file_type> ON <table>(customer_id, <natural key cols>);
>    ```
>    The unique index is not optional: piece 3's upsert uses `ON CONFLICT`,
>    which requires a matching constraint to exist. **The natural key is
>    always tenant-scoped by the implementation**, so `NATURAL_KEYS` entries
>    must NOT themselves include `customer_id` — the index prepends it.
>
> 1. **Validation + upload** — one code path serving dry-run and real upload,
>    so they can never diverge:
>    ```
>    def upload(customer_id, file_type, rows, validate_only=False) -> UploadResult:
>        schema = FILE_SCHEMAS[file_type]          # Config
>        accepted, errors, rejected_rows = [], [], 0
>        for i, row in enumerate(rows, start=1):
>            row_errors = validate_row(customer_id, row, schema, i,
>                                       create_missing=not validate_only)
>            if row_errors:
>                errors.extend(row_errors); rejected_rows += 1   # count ROWS,
>                    # not errors — one row with three bad columns is ONE
>                    # rejected row (Data Shapes requires
>                    # accepted + rejected == len(rows))
>            else:
>                accepted.append(row)
>        if validate_only:
>            return UploadResult(file_type, len(accepted), rejected_rows,
>                                errors, None, True)
>        path = persist(customer_id, file_type, accepted)   # returns a path
>        touch(customer_id, "last_ingested_at")
>        return UploadResult(file_type, len(accepted), rejected_rows, errors,
>                            path, False)
>
>    def validate_row(customer_id, row, schema, row_number, create_missing) -> list:
>        errs = []
>        for col, rule in schema.items():
>            v = row.get(col)
>            if getattr(rule, "required", False) and v in (None, ""):
>                errs.append({"row_number": row_number, "column": col,
>                             "message": "required"}); continue
>            if v in (None, ""): continue          # optional + absent is fine
>            if getattr(rule, "enum", None) and v not in rule.enum:
>                errs.append({"row_number": row_number, "column": col,
>                             "message": f"not in {sorted(rule.enum)}"})
>            if getattr(rule, "cast", None):
>                try: rule.cast(v)
>                except (ValueError, TypeError):
>                    errs.append({"row_number": row_number, "column": col,
>                                 "message": f"cannot cast to {rule.cast.__name__}"})
>            # referential sanity — the shift-left promise downstream modules
>            # are told to rely on. Runs in BOTH modes; creates nothing in
>            # validate_only mode.
>            if getattr(rule, "references", None) == "account":
>                if not resolve_account(customer_id, v, create=create_missing):
>                    errs.append({"row_number": row_number, "column": col,
>                                 "message": f"unknown_account:{v}"})
>        return errs
>
>    def resolve_account(customer_id, account_ref, create):
>        acct = Account.query.filter_by(customer_id=customer_id,
>                                        external_ref=account_ref).first()
>        if acct or not create: return acct
>        acct = Account(customer_id=customer_id, external_ref=account_ref)
>        db.session.add(acct); db.session.flush()
>        return acct
>    ```
>
> 2. **Freshness detection — UTC on both sides, comparing against
>    `last_processed_at`.** Read Gotchas 1 and 5 before writing this; both
>    are real bugs, one of them found in this module's own first draft:
>    ```
>    def touch(customer_id, field):
>        state = get_or_create_ingestion_state(customer_id)
>        setattr(state, field, datetime.now(timezone.utc))   # TZ-AWARE UTC
>        db.session.commit()
>
>    def get_or_create_ingestion_state(customer_id):
>        st = IngestionState.query.get(customer_id)
>        if st is None:
>            st = IngestionState(customer_id=customer_id)
>            db.session.add(st); db.session.flush()
>        return st
>
>    def has_new_data(customer_id, source_files, mode) -> tuple[bool, str]:
>        if mode == "full_recalc":            return True, "full_recalc_requested"
>        st = IngestionState.query.get(customer_id)
>        if st is None or st.last_ingested_at is None:
>                                             return True, "never_ingested"
>        if st.last_processed_at is None:     return True, "never_processed"
>        last = as_utc(st.last_processed_at)      # PROCESSED, not INGESTED —
>            # comparing mtimes against last_ingested_at makes every first
>            # run a no-op, since upload always runs after the files were
>            # written (Gotcha 5)
>        for f in source_files:
>            # BOTH sides UTC. Never a naive local-time conversion.
>            if datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc) > last:
>                return True, f"new_data:{f.name}"
>        # source-agnostic: an API-payload tenant has NO files on disk at all,
>        # so file mtimes can never signal its freshness
>        if as_utc(st.last_ingested_at) > last:  return True, "new_upload"
>        return False, "no_new_data"
>
>    def as_utc(dt):
>        """Naive timestamps from the DB are UTC by convention; make that
>        explicit rather than comparing naive to aware (raises) or two naives
>        from different clocks (silently wrong)."""
>        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
>    ```
>
> 3. **Row-level idempotency** — executable, not a comment:
>    ```
>    NATURAL_KEYS = {                  # Config. NEVER includes customer_id —
>        "kpi_measurements": ("account_ref", "kpi_code", "measured_at"),
>        "signals":          ("signal_id",),
>    }
>    NULL_SENTINEL = "\x00__NULL__"   # SQL NULLs never conflict with each
>        # other, so a real NULL in a natural-key column silently defeats the
>        # unique index and duplicates rows. Normalize before both the
>        # in-memory dedup and the SQL upsert.
>
>    def natural_key(row, key_cols):
>        return tuple(NULL_SENTINEL if row.get(c) is None else row.get(c)
>                     for c in key_cols)      # .get, never row[c] — an
>            # optional natural-key column raises KeyError mid-persist
>            # otherwise, after earlier rows already committed
>
>    def persist(customer_id, file_type, rows) -> str:
>        key_cols = NATURAL_KEYS[file_type]
>        table = TABLES[file_type]
>        for row in rows:
>            values = dict(row, customer_id=customer_id)
>            for c in key_cols:
>                if values.get(c) is None: values[c] = NULL_SENTINEL
>            db.session.execute(
>                insert(table).values(**values)
>                .on_conflict_do_update(
>                    index_elements=["customer_id", *key_cols],
>                    set_={k: v for k, v in values.items()
>                          if k not in ("customer_id", *key_cols)}))
>        db.session.commit()
>        return store_raw_copy(customer_id, file_type, rows)   # returns the
>            # path Data Shapes declares; return None only if the deployment
>            # has no raw-file storage configured
>    ```
>
> 4. **Stage orchestration** — injectable stage list, real skip path:
>    ```
>    @dataclass
>    class Skip:
>        reason: str      # a stage returns Skip("feature_disabled") to skip
>
>    @dataclass
>    class Stage:
>        name: str
>        fn: Callable[[int], object]
>        critical: bool = False    # default best-effort
>
>    DEFAULT_STAGES = [            # Config: order matters, dependencies first
>        Stage("health_scores", run_health_scoring, critical=True),
>        Stage("context_graph", run_graph_build),
>        Stage("signal_enrichment", run_signal_enrichment),
>        Stage("wizards", run_wizards),
>    ]
>
>    def process_data(customer_id, source_files, mode="auto",
>                      stages=None) -> PipelineResult:
>        stages = DEFAULT_STAGES if stages is None else stages   # injectable,
>            # so a client without a graph passes a shorter list — no global
>            # monkeypatching required
>        fresh, reason = has_new_data(customer_id, source_files, mode)
>        results = [StageResult("freshness_check",
>                                "completed" if fresh else "skipped", reason, None)]
>            # the reason is recorded on EVERY run, not only skips, so
>            # "full_recalc_requested" is observable to callers
>        if not fresh:
>            return PipelineResult(customer_id, mode, "success", results, {}, 0.0)
>        timings = {}
>        for stage in stages:
>            t0 = monotonic()
>            try:
>                outcome = stage.fn(customer_id)
>            except Exception as e:
>                results.append(StageResult(stage.name, "failed", "", str(e)))
>                timings[stage.name] = monotonic() - t0
>                if stage.critical:
>                    return PipelineResult(customer_id, mode, "failed", results,
>                                          timings, sum(timings.values()))
>                continue
>            timings[stage.name] = monotonic() - t0
>            # Result construction sits OUTSIDE the except above, so a bug in
>            # this block surfaces as an orchestrator error rather than being
>            # swallowed and misreported as a stage failure.
>            if isinstance(outcome, Skip):
>                if not outcome.reason:
>                    raise ValueError(f"stage {stage.name} skipped with no reason")
>                results.append(StageResult(stage.name, "skipped", outcome.reason, None))
>            else:
>                results.append(StageResult(stage.name, "completed", str(outcome), None))
>        status = "partial" if any(r.status == "failed" for r in results) else "success"
>        touch(customer_id, "last_processed_at")    # ONLY here — a completed
>            # run is what advances the freshness mark
>        return PipelineResult(customer_id, mode, status, results, timings,
>                              sum(timings.values()))
>    ```
>    `status` is `"partial"`, never `"success"`, when any non-critical stage
>    failed — otherwise the failure is invisible to every caller (Gotcha 3).

## Acceptance Criteria

- `upload(..., validate_only=True)` returns the same `UploadResult` shape as
  a real upload, with identical `rows_accepted`/`rows_rejected`/`errors` for
  the same input, and persists NOTHING (assert the row count in the target
  table is unchanged, and that `last_ingested_at` did NOT move).
- A row failing validation is reported with its row number, the offending
  column, and a message — and does not prevent valid rows in the same file
  from being accepted (partial acceptance, not all-or-nothing).
- **Freshness detection is correct on a non-UTC host**: simulate a host
  whose local time is behind UTC (e.g. run the comparison with a file mtime
  written "now" against a `last_ingested_at` recorded a minute ago), and
  assert `has_new_data` returns `True`. A naive local-vs-UTC implementation
  returns `False` here — that is the exact live bug in Gotcha 1, and a test
  written only on a UTC host cannot catch it. Assert with an explicit
  timezone offset, not by relying on the test machine's own zone.
- **An upload immediately followed by `process_data` actually executes the
  stages** — assert the stage list ran, NOT `no_new_data`. This is the
  single most important test in the module: a freshness mark that advances
  on upload rather than on processing makes every first run a silent no-op
  while still reporting `status="success"` (Gotcha 5).
- Re-running `process_data` with no file changes returns
  `status="success"` with the freshness stage `skipped` and detail
  `"no_new_data"` — not a bare `skipped`, and not a full re-run.
- A tenant that supplies data by API payload with NO files on disk still
  processes after an upload — freshness must not depend solely on file
  mtimes, since a source-agnostic entry point means some tenants have zero
  files (`reason="new_upload"`).
- `rows_accepted + rows_rejected == len(input_rows)` for every upload,
  including one where a single row has several bad columns (that is ONE
  rejected row producing several error entries).
- `stored_path` is non-null after a real upload with storage configured, and
  null in `validate_only` mode — the two modes must be distinguishable by
  more than the `validated_only` flag alone.
- A row referencing an account that does not exist is REJECTED with an
  `unknown_account` message in `validate_only` mode (creating nothing), and
  resolves-or-creates the account in a real upload — assert both, and assert
  no account row appears in the dry-run case.
- A stage returning `Skip("feature_disabled")` yields a `StageResult` with
  status `skipped` and that reason — not `completed`. A stage returning
  `Skip("")` raises rather than recording an empty reason.
- A caller-supplied `stages=[...]` list shorter than the default runs
  cleanly with no monkeypatching of module globals — assert
  `process_data` accepts a `stages` parameter.
- Uploading a file whose natural-key column is NULL twice inserts ONE row,
  not two — SQL NULLs never conflict with each other, so a real NULL
  silently defeats the unique index unless normalized to a sentinel.
- `mode="full_recalc"` re-runs even when nothing changed, with reason
  `"full_recalc_requested"`.
- Uploading the identical file twice results in the same row count as
  uploading it once (natural-key upsert, not duplicate inserts).
- A non-critical stage raising leaves `PipelineResult.status == "partial"`,
  that stage's `StageResult.status == "failed"` with the error message
  captured, and every SUBSEQUENT stage still executed.
- A critical stage raising aborts the run with `status="failed"` and no
  subsequent stages executed.
- A stage list containing only some of the optional stages (e.g. no graph
  stage for a client without one) runs cleanly — the pipeline never assumes
  a specific stage exists.
- Every `StageResult` with status `skipped` has a non-empty `detail`
  explaining why; assert this across all stages in a run where several skip.

## Reference Test Harness

1. **Timezone matrix for freshness detection** — the single most valuable
   test here. Run `has_new_data` with `last_ingested_at` and file mtimes
   constructed at explicit UTC offsets (+0, -7, +5:30), asserting correct
   results in all cases. Do NOT write this test using only `datetime.now()`
   on the test machine; that passes on a UTC CI runner and hides the bug on
   a developer laptop, which is exactly how the reference system's version
   survived to production.
2. **Dry-run/real parity test** — same input through `validate_only=True`
   and `False`, assert identical validation outcomes; assert nothing
   persisted in the dry-run case.
3. **Stage-isolation matrix** — a stage list with an injected failing
   non-critical stage and, separately, an injected failing critical stage;
   assert continuation vs. abort, and the resulting `status` in each case.
4. **Double-upload idempotency test** — upload, count, upload again, count;
   assert equal.

## Known Gotchas

**1. Comparing a local-time file mtime against a UTC database timestamp
silently disables incremental processing**
*Symptom:* A pipeline run reports success but processes nothing — health
scores, graph nodes, and every downstream artifact stay frozen at their
previous values even though genuinely new data was uploaded. No error, no
warning, nothing in the logs. Worse, it works fine in the cloud/CI (UTC
containers) and fails only on developer laptops or any non-UTC host, so it
survives review and testing.
*Root cause:* Confirmed and FIXED in the reference system on 2026-08-07: the
freshness check compared `datetime.fromtimestamp(os.path.getmtime(f))` — a
LOCAL wall-clock conversion — against a database timestamp stored via
`datetime.utcnow()`. On any host whose local zone trails UTC (every US
timezone), a file written moments ago converts to a timestamp several hours
BEFORE the "last processed" mark, so `csv_mtime > last_ts` is false and the
entire load step is skipped. Found only because a multi-phase test run
produced identical health scores in both phases on a laptop while the same
manifest worked correctly on a UTC server.
*Fix:* Both sides of any timestamp comparison in UTC, explicitly —
`datetime.fromtimestamp(mtime, tz=timezone.utc)` and a timezone-aware
`last_ingested_at`. Never mix a naive local conversion with a UTC-stored
value. Test with explicit offsets, not the test host's own zone.

**2. Deriving "when did we last ingest" from a MAX() over a data table**
*Symptom:* Freshness detection behaves erratically after data is deleted,
backfilled, or partially re-loaded — a run is skipped when it shouldn't be,
or repeats when it shouldn't.
*Root cause:* Using `SELECT MAX(created_at) FROM <some data table>` as a
proxy for "last ingestion" couples the freshness signal to whatever happens
to be in that particular table. Delete some rows and the max moves
backwards; add a row through some other code path and it jumps forward
without an ingestion having occurred. It also silently breaks when a tenant
has data in one table but not the one being maxed over.
*Fix:* Store `last_ingested_at` explicitly, updated by the ingestion path
itself and by nothing else. One authority, moved deliberately.

**3. Reporting success when a stage failed**
*Symptom:* Callers (dashboards, CLI runs, other automation) treat a run as
healthy while one of its stages silently failed — the failure only surfaces
much later as missing downstream data.
*Root cause:* A pipeline that catches per-stage exceptions to keep going
(correct) but then returns an overall `success` regardless (incorrect),
because the caller-facing status only reflects "did the orchestration
finish," not "did every stage succeed."
*Fix:* Three-valued status — `success` / `partial` / `failed` — with
`partial` whenever any stage failed. A caller that only checks `!= "failed"`
still sees something is off, and one that checks `== "success"` gets the
truth.

**4. A "skipped" status with no reason is indistinguishable from a bug**
*Symptom:* An operator sees a stage was skipped and has no way to tell
whether that's correct behavior (feature disabled for this tenant, no new
data) or a malfunction, so every skip becomes an investigation.
*Root cause:* Modeling skip as a boolean or a bare status string, with the
reason available only in log output that may not be retained or correlated.
*Fix:* Skip is always `(skipped, reason)` in the returned structure, not
just in logs — same principle as Module 06's `GateDecision`. This module and
Module 06 both learned it; it generalizes to any conditional execution.

**5. One timestamp cannot mean both "last uploaded" and "last processed"**
*Symptom:* The very first pipeline run after an upload processes nothing and
reports success — `no_new_data` — even though the data is brand new and has
never been processed. Every subsequent run does the same. Downstream tables
stay permanently empty while every log line looks healthy.
*Root cause:* Freshness is computed as "is any source file newer than the
last-ingestion mark," and the ingestion mark is advanced by the upload
itself. Since an upload necessarily runs AFTER the files it reads were
written, the mark is always ahead of every file mtime — so the answer is
always "nothing new." The two questions ("when did we last load rows" and
"when did we last process them") are genuinely different and need separate
marks; collapsing them into one is an easy and completely silent mistake.
*Fix:* Two timestamps. `last_ingested_at` advances on persist;
`last_processed_at` advances only when a pipeline run completes; freshness
compares against `last_processed_at`. Test it directly: upload, then run,
then assert stages executed.

**6. Normative rules written as comments do not execute**
*Symptom:* A spec or codebase looks well-governed — comments say MUST,
never, always — and the actual behavior violates every one of them, because
a comment is documentation of intent, not a constraint.
*Root cause:* It is much easier to write `# never a bare INSERT` above an
undefined helper than to write the upsert. Reviewers reading the comment
absorb the rule and assume it's enforced somewhere. This module's own first
draft did exactly that with its idempotency contract: the entire upsert
requirement lived in a two-line comment above a function that was never
defined, and there was no DDL anywhere to make the required `ON CONFLICT`
even expressible.
*Fix:* If a rule contains MUST / never / always, it must become executable
code or a schema constraint before the spec is considered done. A comment
may explain WHY a line exists; it may never be the only place a requirement
lives. (This one generalizes across the whole library — four consecutive
modules have had a required check living only in a comment.)

## Provenance

Origin: `kpi-dashboard/backend/mcp_server/cs_pulse_onboarding.py`
(`_process_data_impl` — the `has_new_csvs` freshness detection block read
directly, INCLUDING the UTC fix applied to it during this session),
`kpi-dashboard/backend/mcp_server/process_data_pipeline.py` (the 9-stage
orchestration with per-stage timings and non-fatal stage failures),
`kpi-dashboard/backend/utils/csv_upload.py` (upload/registry/file-type
resolution), `kpi-dashboard/backend/onboarding_api_v2_config_aware.py`
(`validate_csv_against_config`, the `/validate-csv` dry-run endpoint).

Gotcha 1 is not a hypothetical: it was found, root-caused, fixed, and merged
as commit `b833d05d8` during this session, after a multi-phase load test
silently produced identical results in both phases on a PDT laptop while
working correctly on a UTC EC2 host.

## Validation Note

Validated 2026-08-07. A fresh agent built a SQLite implementation containing
BOTH the spec's literal pseudocode (runnable, as `SpecLiteral`) and a
corrected version — 72 tests plus 16 mutation checks, all passing. **Third
module in a row to hit all four failure shapes**, with eleven distinct
defects, two severe enough to make the pipeline a silent no-op — the exact
outcome this module's Purpose paragraph names as its worst failure.

**The severe one (shape (a), now Gotcha 5):** the Build Prompt advanced
`last_ingested_at` inside `upload()`, then compared file mtimes against it
for freshness. Since upload always runs AFTER the files it reads were
written, the mark is always ahead of every mtime — so the FIRST pipeline run
after an upload returned `status="success"` with `detail="no_new_data"` and
**zero stages executed**. Proven directly: upload 3 rows, run the pipeline,
observe nothing processed. This reproduced Gotcha 1's own symptom in the
prompt written to prevent it. Fixed by splitting into `last_ingested_at`
(advanced by persist) and `last_processed_at` (advanced by a completed run,
and what freshness compares against).

**Shape (b), textbook:** `upsert(...)` was called with its entire contract
in a comment — "never a bare INSERT, and never a SELECT-then-INSERT (racy)"
— while the spec contained no DDL and never mentioned a unique index, which
`ON CONFLICT` requires. So the comment forbade two options and made the
third inexpressible. Both natural fills were proven wrong: bare INSERT
duplicated (6 rows instead of 3); SELECT-then-INSERT silently discarded a
corrected value on re-upload.

**Shape (c):** referential sanity and account resolution — promised in
Boundary "Owns" and Dependencies — had no Build Prompt piece at all; a row
citing a nonexistent account was accepted with zero errors. The structured
skip mechanism existed only for the freshness check, so no stage could ever
skip, making `StageResult.status='skipped'` and Data Shapes'
`"feature_disabled"` example dead surface. `stored_path` had no producer
(`persist` had no return statement). `STAGES` was a global with no injection
point despite an AC requiring partial stage lists.

**Shape (d), four recurrences:** a required check living in a comment (now
its FOURTH consecutive module); a declared field with no producer
(`stored_path`, after Module 05's `config` and Module 06's `cg_node_id`);
dead schema surface (Modules 03, 05, 06); and a NULL-unsafe read —
`row[c]` instead of `row.get(c)` on an optional natural-key column, raising
mid-persist after earlier rows had already committed. That last one had a
second layer the agent caught: the obvious `.get()` fix is insufficient,
because SQL NULLs never conflict with each other, so a real NULL still
defeats the unique index and duplicates rows. Requires a sentinel.

**All fixed**: six-piece Build Prompt (added piece 0 for DDL + tenant-scoped
unique indexes, referential validation inside piece 1 running in both modes,
the two-timestamp freshness split, executable upsert with NULL sentinel,
injectable stage list, real `Skip(reason)` path with result construction
moved outside the isolation `except` so an orchestrator bug can't be
misreported as a stage failure). `rows_rejected` now counts rows not errors.
New Gotcha 5 (one timestamp can't mean two things) and Gotcha 6 (normative
rules written as comments don't execute).

**Library-level finding — the strongest one yet:** this module is
noticeably SIMPLER than 05 and 06 and still hit all four shapes. The agent's
diagnosis is worth quoting: the recurring pattern isn't complexity-driven,
it's that *"normative content keeps being written as comments and prose
adjacent to code rather than as code."* Four consecutive modules have had a
required check living only in a comment. That is now a hard template rule:
**if a comment in a Build Prompt contains MUST, never, or always, it is a
spec bug until it becomes an executable line or a schema constraint.**
