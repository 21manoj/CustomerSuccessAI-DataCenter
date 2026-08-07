# 05 — Prediction Wizards (Orchestration Framework)

**Layer:** Intelligence

**Status:** ✅ Validated — see [Validation Note](#validation-note) at the bottom.

## Purpose

Give a client a way to run expensive, periodic analysis jobs — pattern
detection, weight self-calibration, churn/expansion prediction — safely: with
an audit trail of every run, a single well-defined "currently active" result
at any time even though history is never destroyed, and governance over WHEN
these jobs are allowed to fire (never silently, on every data refresh, only
on an explicit ask or a well-defined lazy trigger). This module is
deliberately scoped to the ORCHESTRATION FRAMEWORK, not to fully prescribing
distinct analytical algorithms — see Boundary. An FDE plugs a client's actual
analysis logic into this framework's contract; this module makes sure that
logic runs safely, auditably, and only when it's supposed to.

## Boundary

**Owns:**
- Run tracking: every wizard execution gets an auditable record (who/what
  triggered it, when, with what config, what it produced, whether it
  succeeded) — regardless of which specific analysis that wizard runs.
- The single-active-version pattern: a wizard that recalibrates something
  never overwrites history in place — it appends a new versioned row and
  atomically deactivates the previous one, so "what's active right now" is
  always a single well-defined answer and "what did we believe last quarter"
  is still recoverable.
- Trigger governance, BOTH halves: rejecting a lazy trigger for an
  explicit-only wizard, AND providing the lazy-trigger entry point itself
  (fire once if and only if no active result exists yet) that Module 08
  calls — with enforcement mechanisms, not just documentation.
- Each wizard's CONTRACT (input signature, output shape, trigger policy) —
  not its internal analysis algorithm.

**Explicitly does not own:**
- The actual pattern-detection/calibration/prediction algorithms — these are
  legitimately client- and domain-specific, not reusable Engine code. An FDE
  or data scientist implements the algorithm; this module only guarantees it
  runs inside a tracked, versioned, governed execution.
- The context graph these wizards read from — Module 04.
- The KPI/weight storage a calibration wizard writes into — Modules 01/02/03.
- Rendering wizard results in a UI — Module 08 calls this module's
  `ensure_artifact` API (defined below); this module never reaches into the
  UI layer.

## Dependencies

- **Module 01 (Data Model):** `Customer`, `Account`.
- **Module 04 (Context Graph):** only for wizards doing pattern/arc analysis;
  not required by a client who wants weight calibration alone.

### Data Shapes

```
WizardRun: run_id (PK, string, globally unique), customer_id (FK, NULLABLE —
           a wizard may run at vertical/platform level with no single
           customer; every query filtering on this column MUST be NULL-safe,
           see Gotcha 5), wizard_id (string), status
           (queued|running|completed|failed — all four reachable, see the
           transitions in Build Prompt piece 1), config (JSON — the kwargs
           the caller requested this run with; populated from
           trigger_wizard's own `config` parameter), results (JSON),
           error_message (TEXT, nullable — populated on failure, separate
           from `results`), trigger_source (string, NOT NULL, validated —
           see Gotcha 3), created_at, started_at, completed_at

VersionedArtifact (the shared shape behind pattern-learning results AND
           calibration-coefficient sets — one pattern, many payloads):
           id (PK), customer_id (FK, NULLABLE — same NULL-safety rule),
           scope (string, NOT NULL — disambiguates artifact TYPES for the
           same customer, e.g. "wizard_b_patterns" vs
           "wizard_d_hazard_submodel"; without it, activating a new
           calibration would wrongly deactivate an unrelated pattern row),
           version (INTEGER, incrementing per (customer_id, scope)),
           source_run_id (FK to WizardRun.run_id), payload (JSON),
           is_active (bool), created_at
           UNIQUE (customer_id, scope, version) — NOT (customer_id, version):
           versions increment per-scope, so two scopes both legitimately have
           a version 1 for the same customer.
           AT MOST ONE row with is_active=true per (customer_id, scope) — if
           your database supports a partial unique index
           (`... WHERE is_active`), add it as a backstop; the write path must
           deactivate-then-insert (in that order — see Build Prompt piece 3)
           so it is compatible with such an index rather than transiently
           violating it.

Wizard entry-point contract — every wizard implements EXACTLY this signature:
           run_wizard_X(customer_id: int | None, run_id: str,
                        **config) -> dict
           `run_id` is passed so a wizard can link any VersionedArtifact it
           writes back to the run that produced it. Return dict signals
           success via EITHER 'return_code' (0=success) or 'status'
           ('completed'/'failed'); the orchestration layer handles both
           without wizard-specific branching, and treats a dict containing
           NEITHER key as FAILURE (fail closed).
```

## Engine vs. Config

**Engine (build once):**
- `WizardRun` bookkeeping: every trigger creates a `queued` row before any
  work, moves it to `running` at invocation, and to `completed`/`failed`
  with `completed_at` and (on failure) `error_message` — even if the
  wizard's own code raises an unhandled exception.
- The versioned-artifact write pattern: deactivate the current active row
  for that `(customer_id, scope)`, then insert the new active row, as ONE
  atomic transaction. Never two separate commits — a crash between them
  leaves zero or two active rows, and "exactly one, always" is this
  pattern's entire purpose.
- Trigger-policy enforcement, with `explicit_only` as a STRUCTURAL default
  (a dataclass field default, not documentation) — a wizard registered
  without an explicit policy is explicit-only automatically, and can never
  raise a lookup error for a missing policy entry.
- `ensure_artifact`: the lazy-trigger API — returns the active artifact for
  a `(customer_id, scope)` if one exists, otherwise policy-checks and fires
  the wizard exactly once, then returns its result.
- Result-shape normalization handling both success conventions plus the
  neither-key fail-closed case, in ONE place with no wizard-specific
  branching.

**Config (an FDE / client engagement fills in):**
- The analysis inside each `run_wizard_X` — pattern rules, calibration math,
  prediction models. Substantial domain-specific work; not templated here.
- Which wizards exist for a client, and each one's trigger policy (a
  one-token change in the registry).

## Build Prompt

> Build the wizard orchestration framework. Do NOT implement any wizard's
> analysis algorithm — implement only the scaffolding every wizard runs
> inside of. Four numbered pieces:
>
> 1. **Run bookkeeping** — the audit trail. Every field in `WizardRun` above
>    has a producer here; nothing is declared-but-never-written:
>    ```
>    def create_wizard_run(customer_id, wizard_id, trigger_source, config) -> WizardRun:
>        run = WizardRun(
>            run_id=f"{wizard_id}_{utcnow():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}",
>            customer_id=customer_id, wizard_id=wizard_id,
>            trigger_source=trigger_source,
>            config=config or {},          # the caller's requested kwargs
>            status="queued", created_at=utcnow(),
>        )
>        db.session.add(run); db.session.commit()
>        return run
>
>    def start_wizard_run(run):            # queued -> running
>        run.status = "running"; run.started_at = utcnow(); db.session.commit()
>
>    def complete_wizard_run(run, succeeded, results, error_message=None):
>        run.status = "completed" if succeeded else "failed"
>        run.results = results
>        run.error_message = error_message  # its OWN column, not buried in results
>        run.completed_at = utcnow(); db.session.commit()
>    ```
>
> 2. **One wizard registry — a SINGLE source of truth.** Do NOT create two
>    parallel dicts keyed by wizard id (one of entry points, one of
>    policies): that is exactly the "second, independent list that has to be
>    kept in sync by hand" that Gotcha 1's fix forbids, and it is how a
>    wizard ends up configured-but-unreachable or reachable-but-unconfigured.
>    Enumerate EVERY wizard explicitly — no `...`, no "and so on":
>    ```
>    @dataclass(frozen=True)
>    class WizardSpec:
>        entry_point: Callable[..., dict]
>        policy: str = "explicit_only"   # STRUCTURAL default (Gotcha 4) —
>            # a wizard registered without a policy is explicit-only, and a
>            # missing policy can never raise a lookup error
>
>    WIZARDS = {
>        "a": WizardSpec(run_wizard_a),
>        "b": WizardSpec(run_wizard_b),
>        "c": WizardSpec(run_wizard_c),
>        "d": WizardSpec(run_wizard_d),   # enumerate ALL — including the
>            # last one, which is historically the one that gets forgotten
>        # opting a wizard into lazy triggering is a visible one-token diff:
>        #   "e": WizardSpec(run_wizard_e, policy="lazy_ok"),
>    }
>    ```
>
> 3. **Trigger dispatcher.** Every guard below is EXECUTABLE CODE, not a
>    comment — a rule that lives only in a comment does not run:
>    ```
>    LAZY_PREFIX = "lazy_trigger:"
>    EXPLICIT_PREFIX = "explicit_trigger:"
>    GENERIC_SOURCES = {"system", "mcp", "internal", "default", "unknown"}
>
>    def validate_trigger_source(trigger_source):
>        if not trigger_source or not trigger_source.strip():
>            raise ValueError("trigger_source is required and cannot be blank")
>        if not trigger_source.startswith((LAZY_PREFIX, EXPLICIT_PREFIX)):
>            raise ValueError(
>                f"trigger_source must start with {EXPLICIT_PREFIX!r} or "
>                f"{LAZY_PREFIX!r} — an unprefixed source silently bypasses "
>                f"the policy check below, which is a governance hole, not a "
>                f"style issue")
>        suffix = trigger_source.split(":", 1)[1].strip()
>        if not suffix or suffix.lower() in GENERIC_SOURCES:
>            raise ValueError(
>                f"trigger_source {trigger_source!r} identifies no specific "
>                f"caller — see Gotcha 3")
>
>    def trigger_wizard(customer_id, wizard_id, trigger_source, config=None) -> dict:
>        validate_trigger_source(trigger_source)          # EXECUTED, not a comment
>        if wizard_id not in WIZARDS:
>            raise ValueError(f"Unknown wizard: {wizard_id}")
>        spec = WIZARDS[wizard_id]
>        if spec.policy == "explicit_only" and trigger_source.startswith(LAZY_PREFIX):
>            raise PermissionError(
>                f"Wizard {wizard_id} is explicit-only, cannot be lazy-triggered")
>        # ^ all rejections happen BEFORE create_wizard_run: a rejected
>        #   trigger leaves ZERO audit rows. Rejection is not failure.
>        run = create_wizard_run(customer_id, wizard_id, trigger_source, config)
>        try:
>            start_wizard_run(run)
>            result = spec.entry_point(customer_id, run_id=run.run_id, **(config or {}))
>            complete_wizard_run(run, interpret_result(result), result)
>        except Exception as e:
>            complete_wizard_run(run, False, {}, error_message=str(e))
>            raise
>        return run.to_dict()
>
>    def interpret_result(result: dict) -> bool:
>        # No wizard_id anywhere in this function — one rule for all wizards.
>        if "return_code" in result: return result["return_code"] == 0
>        if "status" in result:      return result["status"] == "completed"
>        return False                # neither key present => fail closed
>    ```
>
> 4. **Versioned-artifact writer + the lazy-trigger API.** Note the
>    deactivate-BEFORE-insert ordering and the NULL-safe customer predicate —
>    both are load-bearing, see Gotcha 5:
>    ```
>    def _same_customer(column, customer_id):
>        # SQL `col = NULL` is never true, so a plain == silently fails to
>        # match platform-level (customer_id IS NULL) rows, leaving TWO
>        # active artifacts — the exact thing this module exists to prevent.
>        return column.is_(None) if customer_id is None else column == customer_id
>
>    def write_versioned_artifact(customer_id, scope, payload, source_run_id):
>        with db.transaction():        # ONE transaction, not two commits
>            VersionedArtifact.query.filter(
>                _same_customer(VersionedArtifact.customer_id, customer_id),
>                VersionedArtifact.scope == scope,
>                VersionedArtifact.is_active.is_(True),
>            ).update({"is_active": False})       # deactivate FIRST, so a
>                # partial unique index on is_active is never transiently
>                # violated by having two active rows mid-transaction
>            next_version = 1 + (db.session.query(func.max(VersionedArtifact.version))
>                .filter(_same_customer(VersionedArtifact.customer_id, customer_id),
>                        VersionedArtifact.scope == scope).scalar() or 0)
>                # computed INSIDE the transaction, or concurrent writers collide
>            row = VersionedArtifact(
>                customer_id=customer_id, scope=scope, version=next_version,
>                payload=payload, source_run_id=source_run_id, is_active=True)
>            db.session.add(row)
>        return row
>
>    def ensure_artifact(customer_id, scope, wizard_id, trigger_source):
>        """The lazy-trigger API Module 08 calls. Fires the wizard at most
>        once — only when no active artifact exists yet."""
>        existing = VersionedArtifact.query.filter(
>            _same_customer(VersionedArtifact.customer_id, customer_id),
>            VersionedArtifact.scope == scope,
>            VersionedArtifact.is_active.is_(True),
>        ).first()
>        if existing:
>            return existing            # already calibrated — do NOT re-run
>        trigger_wizard(customer_id, wizard_id, trigger_source)  # policy-checked;
>            # raises PermissionError if this wizard isn't lazy_ok
>        return VersionedArtifact.query.filter(...same filters...).first()
>    ```
>
> A wizard's own code must never call `db.session.commit()` on a
> `VersionedArtifact` write directly — it receives `run_id` (piece 3 passes
> it) and calls `write_versioned_artifact(...)`, so the atomicity guarantee
> cannot be bypassed by an implementer who doesn't know why it matters.

## Acceptance Criteria

- Every wizard id present in the `WIZARDS` registry is reachable: calling
  `trigger_wizard` for it actually invokes its entry point. There is no
  second, separately-maintained list of valid ids that could drift out of
  sync with the registry (assert structurally: the dispatcher's validity
  check IS registry membership).
- A wizard registered WITHOUT an explicit policy is treated as
  `explicit_only` — registering `WizardSpec(some_fn)` with no policy
  argument and then lazy-triggering it raises `PermissionError`, never a
  `KeyError`/lookup error and never a successful run.
- A `lazy_trigger:`-prefixed call to an `explicit_only` wizard raises
  `PermissionError` and creates ZERO `WizardRun` rows — a rejected trigger
  is not a `failed` run; rejection and failure are different events.
- A `lazy_ok`-policy wizard DOES accept a `lazy_trigger:` call and runs (the
  registry must ship at least one `lazy_ok` example so this affirmative
  branch is actually exercised, not just its rejection counterpart).
- `trigger_source` is validated in executable code, not documented in a
  comment: blank, whitespace-only, unprefixed (`"cro_dashboard"`), and
  generic-suffix (`"explicit_trigger:system"`) values are all rejected
  BEFORE any run row is created. The unprefixed case matters most — an
  unprefixed source would otherwise skip the policy check entirely and run
  an explicit-only wizard.
- Entry points returning `{'return_code': 1}`, `{'status': 'failed'}`, and
  `{}` (neither key) are ALL interpreted as failure by the same code path,
  with no wizard id appearing anywhere in the interpretation function.
- An entry point raising an unhandled exception still yields a `failed` run
  with `completed_at` set and the message in the `error_message` COLUMN (not
  only inside the `results` JSON).
- All four `status` values are reachable in practice — in particular a run
  observed mid-execution is `running`, distinguishing a hung wizard from one
  that never started.
- `WizardRun.config` is populated from the caller's requested kwargs — a
  parameter exists that can actually fill it (a declared-but-unfillable
  field is dead schema).
- Two sequential `write_versioned_artifact` calls for the same
  `(customer_id, scope)` leave exactly one `is_active` row, with no window
  where zero or two are active. Prove the atomicity, don't assert it: inject
  a fault between the deactivate and insert steps and confirm the PREVIOUS
  row is still active afterward (a failed write must never leave zero active
  rows).
- Writes for the same customer but DIFFERENT scopes don't affect each
  other's `is_active` state, AND both can hold version 1 simultaneously
  (this is why uniqueness is `(customer_id, scope, version)`, not
  `(customer_id, version)`).
- A platform-level artifact (`customer_id IS NULL`) written twice for the
  same scope leaves exactly ONE active row — the NULL-safe predicate is
  exercised, not just present.
- `ensure_artifact` returns an existing active artifact WITHOUT triggering a
  run; called again after one exists, it still does not re-run. Called when
  none exists for an `explicit_only` wizard, it raises `PermissionError`
  rather than running.

## Reference Test Harness

1. **Registry-reachability regression test** — for every id in `WIZARDS`,
   assert `trigger_wizard` reaches and invokes its entry point (track
   invocations with a stub log). "Reached" is the property a dead branch
   violates; a wizard that runs and *fails* still counts as reached. This is
   the class of bug an integration test catches and a code read does not —
   see Gotcha 1, where exactly this has been live in the reference system.
2. **Policy-enforcement tests, both directions** — an `explicit_only` wizard
   rejects a lazy trigger; a `lazy_ok` wizard accepts one; a
   policy-unspecified wizard behaves as `explicit_only`.
3. **Atomicity/fault-injection test** — a hook between the deactivate and
   insert halves that raises; assert the previous row is still active and no
   partial row survives. Add a real multi-connection concurrency test if the
   test infrastructure allows.
4. **Structural (source-level) assertions** — some rules here are properties
   of the code's shape, not its behavior, and can only be tested by
   inspecting source: `interpret_result` contains no wizard id; the
   dispatcher has no per-wizard branching. Use source inspection for these
   rather than skipping them.

## Known Gotchas

**1. A guard clause listing "valid" values, maintained separately from the
dispatch mechanism, makes implemented branches dead code**
*Symptom:* A wizard with a fully-written, correct implementation never runs —
every call fails with a generic "invalid option" error that doesn't mention
the real implementation, making it baffling to debug from the error alone.
*Root cause:* Confirmed live in the reference system: the dispatcher has an
early `if wizard not in ('a','b','c'): raise ToolError(...)`, followed later
in the SAME function by a fully-implemented `elif wizard == 'd':` calling a
real, working entry point. The allowlist was never updated when 'd' was
added, so 'd' always fails the guard and the working branch below is
permanently unreachable.
*Fix:* Never validate "is this a known option" against a list separate from
the dispatch mechanism. One registry; `if wizard_id not in WIZARDS` IS the
validity check. This extends to policies too — a separate policy dict keyed
by wizard id is the same anti-pattern wearing a different hat, which is why
the Build Prompt puts policy INSIDE the registry entry.

**2. Two different "did this succeed" conventions across code paths sharing
a caller**
*Symptom:* A failed wizard recorded as `completed` (or vice versa) depending
on which wizard ran; noticed much later when run history looks wrong.
*Root cause:* Different wizard implementations independently chose
`return_code == 0` vs. `status == 'completed'` with no shared contract, and
the orchestration code checked only one.
*Fix:* Normalize both in one place (`interpret_result`), and fail closed on
a dict containing neither key rather than defaulting to success.

**3. A blank or generic trigger-source value defeats the entire point of
tracking who triggered a run**
*Symptom:* Months later, an operator asks "did a user request this, or did a
dashboard silently kick it off?" and the audit trail can't answer.
*Root cause:* The field was populated with a constant (`"mcp_onboarding"`,
`"system"`) at every call site — the schema looks like it tracks provenance,
but the recorded values are useless for the one question the field exists to
answer.
*Fix:* Validate in executable code (not a comment) that the value carries a
required `explicit_trigger:`/`lazy_trigger:` prefix AND a specific,
non-generic suffix. The prefix is doubly load-bearing here: the policy check
keys off it, so an unprefixed source doesn't just degrade the audit trail,
it silently bypasses trigger governance entirely.

**4. Defaulting new wizards to auto-triggerable is an easy governance
regression**
*Symptom:* A new wizard added later by someone unfamiliar with the existing
convention runs automatically on every relevant event, silently changing
cost/timing/behavior nobody decided on.
*Root cause:* "Never silent-auto-run" was a real, deliberate design decision
in the reference system — but recorded as documentation, not as a structural
default. Documentation doesn't protect a new wizard added by someone who
never read it.
*Fix:* `explicit_only` must be a code-level default (a dataclass field
default, as in the Build Prompt's `WizardSpec`) — so silence in the config
is SAFE, and opting into auto-triggering is a visible, reviewable one-token
diff. Critically, a default is not the same as a required entry: a policy
dict that raises `KeyError` for an unregistered wizard is NOT a safe
default, it's a crash.

**5. `customer_id = NULL` breaks every naive equality predicate, silently**
*Symptom:* Platform/vertical-level artifacts (those with no single customer)
accumulate multiple simultaneously-active rows, while customer-scoped ones
behave correctly — so the "exactly one active" invariant appears to hold in
all normal testing and fails only for the nullable case.
*Root cause:* SQL `column = NULL` is never true, so a
"deactivate the previous active row WHERE customer_id = :cid" statement
matches nothing when `:cid` is NULL, and the old row stays active alongside
the new one.
*Fix:* Every predicate on a nullable `customer_id` must be NULL-safe
(`IS NULL` when the value is None, or `IS NOT DISTINCT FROM`) — never a bare
`==`. Test the platform-level (NULL) case explicitly; the customer-scoped
case passing tells you nothing about it.

## Provenance

Origin: `kpi-dashboard/backend/mcp_server/cs_pulse_onboarding.py`
(`trigger_wizard`, lines ~2262-2385 — the dead `elif wizard == 'd':` branch
read directly and confirmed unreachable by tracing the guard clause above
it), `kpi-dashboard/backend/models.py` (`WizardRun`, `WizardLearning`
including its `activate()`/`get_active()` single-active-row pattern,
`PredictorCalibration` whose docstring explicitly states "Wizard D never
UPDATEs in place, only INSERTs new rows and flips the previous row's
is_active to False" — confirming the pattern is deliberate),
`kpi-dashboard/backend/wizards/wizard_{a,b,c}_*_db.py` (entry-point
signatures), `kpi-dashboard/backend/wizards/wizard_d_predictor_calibrator.py`
(`run_wizard_d` — fully implemented despite being unreachable).

## Validation Note

Validated 2026-08-07. A fresh agent built a SQLite-backed implementation (63
tests, all passing, plus mutation checks confirming the tests actually bite)
and produced **the most severe validation result in this library so far: all
four documented failure shapes present in a single module**, each with an
executable proof rather than an assertion.

**Shape (a) — Build Prompt contradicting another section — four instances:**
- Gotcha 4's fix claimed `explicit_only` was already the structural default
  "as the Build Prompt's `TRIGGER_POLICY` dict does" — it did not. The
  prompt used `TRIGGER_POLICY[wizard_id]`, a subscript that raises
  `KeyError` for an unregistered wizard. The single safeguard against the
  governance regression the Gotcha exists to prevent did not exist.
- Data Shapes declared `UNIQUE (customer_id, version)` while versions
  increment per-scope — making the scope-isolation Acceptance Criterion
  literally impossible to satisfy. Proven with a real failing INSERT.
- Data Shapes suggested a partial unique index on `is_active` while the
  Build Prompt inserted-then-deactivated, transiently violating that index.
  Proven with a real `IntegrityError`.
- The writer filtered `customer_id == customer_id` on a column Data Shapes
  declared nullable — so platform-level artifacts never deactivated their
  predecessor, leaving two active rows: exactly what the module exists to
  prevent. Proven (literal spec produced 2 active rows; corrected produced 1).

**Shape (b) — ellipsis reproducing an anti-pattern:**
`WIZARD_ENTRY_POINTS = {"a": ..., "b": ..., ...}` trailed off after two
entries while the adjacent policy dict enumerated all four. The natural way
to fill that ellipsis is to register the wizards you happen to think of — and
the module's own Gotcha 1 is a case study of wizard `d` specifically being
the one omitted from a list. An implementer would reproduce the live
production bug verbatim, inside the code block written to prevent it.

**Shape (c) — promised in Boundary/Engine, absent from Build Prompt:**
Run tracking (Boundary "Owns" #1, Engine #1) had NO numbered piece — only
three undefined function calls. The lazy-trigger half of trigger governance,
and the "API Module 08 calls into," were promised in Boundary and existed
nowhere. `WizardRun.config` was declared with no parameter capable of
populating it; `status='running'` was declared but unreachable;
`error_message` was declared but never written.

**Shape (d) — earlier modules' defects recurring verbatim:**
- Module 01's exact finding (a required check living in a comment instead of
  executable code, in the same document position) recurred: `trigger_source`
  validation was a comment, and blank/generic values passed straight through.
- Module 01's other finding (a field required by the Build Prompt but
  missing from Data Shapes) recurred: `scope` was absent from
  `VersionedArtifact`'s field list despite the writer and two ACs depending
  on it.
- Module 03's dead-schema-surface finding recurred three times over.

**Everything above is fixed in the current spec**: single `WIZARDS` registry
with a structural `policy="explicit_only"` dataclass default (closing (b),
the KeyError, and Gotcha 1's own "no second list" rule simultaneously); a
new Build Prompt piece 1 for run bookkeeping with every field's producer; a
new piece 4 including `ensure_artifact` (the lazy-trigger API); executable
`validate_trigger_source` with prefix+specificity checks; NULL-safe
`_same_customer` predicate; deactivate-before-insert ordering; corrected
uniqueness to `(customer_id, scope, version)`; `error_message` as its own
column; all four `status` values reachable; `config` parameter added. New
Gotcha 5 added for the NULL-predicate class of bug. Acceptance Criteria
rewritten to demand proof (fault injection) rather than assertion, and to
cover the platform-level NULL case, the policy-unspecified case, the
neither-convention case, and the unprefixed-trigger-source governance
bypass. Reference Test Harness gained a fourth item for source-level
structural assertions.

**Library-level lesson:** this module was written immediately after Module
04's Validation Note recorded shape (d) as a warning against assuming
lesson-transfer between modules — and then reproduced shape (d) three times
over, alongside all three other shapes. The adversarial rebuild is not a
formality that can be tapered off as the library matures; on current
evidence it gets MORE valuable as specs get more complex, not less.
