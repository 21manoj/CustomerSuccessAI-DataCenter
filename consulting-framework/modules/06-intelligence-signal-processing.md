# 06 — Signal Processing Layer

**Layer:** Intelligence

**Status:** ✅ Validated — see [Validation Note](#validation-note) at the bottom.

## Purpose

Turn unstructured qualitative evidence — support tickets, emails, meeting
notes, call transcripts — into structured, scored signals the rest of the
platform can reason over. This is the LEADING-indicator half of the
platform's two-layer health model: KPI rollups (Module 03) tell you what
already happened; signals tell you what's about to. The gap between them is
the product's core value, so a signal that never gets extracted, or gets
extracted with a silently-wrong sentiment, directly costs the client the
early warning they bought the system for.

## Boundary

**Owns:**
- The `QualitativeSignal` record: a structured, tenant-scoped signal with
  sentiment, urgency, stakeholder attribution, and a link back to its raw
  source text.
- LLM enrichment orchestration: deciding whether to call an LLM at all for a
  given tenant/run (feature-flag + API-key + budget gating), and handling
  the call's failure modes without taking down the pipeline around it.
- **Cost governance**: the usage-record table, the per-model price table,
  the cost computation, the spend query, and the guarantee that every LLM
  call this module makes records all of it (see Gotcha 1).
- Confidence-gated review routing: enrichment below a confidence threshold —
  or with no confidence data at all — is flagged for human review rather
  than silently trusted.
- Deterministic (non-LLM) urgency derivation, and the rule for combining it
  with LLM-derived urgency.

**Explicitly does not own:**
- The connectors that fetch raw text from Slack/email/ticketing systems —
  that's Module 09 (Ingestion). This module receives raw text plus
  provenance; it doesn't reach out to third-party APIs.
- Turning enriched signals into graph nodes/edges — Module 04 owns the
  context graph. This module accepts an optional `cg_node_id` from a caller
  that has already created the node; it never creates one itself.
- KPI-derived health scoring — Module 03. A signal never writes a health
  score.
- Prompt text and price-table VALUES — Config an FDE tunes per client (the
  price table's existence and use are Engine; its numbers are Config).

## Dependencies

- **Module 01 (Data Model):** `Customer`, `Account` for tenant scoping.
- **Module 04 (Context Graph):** optional. If present, the CALLER creates
  the graph node and passes its id into `process_signal(..., cg_node_id=)`;
  this module only stores it.

### Data Shapes

```
QualitativeSignal:
  id (PK), signal_id (string, tenant-scoped — UNIQUE (customer_id,
    signal_id), NOT globally unique: two tenants legitimately both have a
    signal called "sig_001", see Gotcha 4),
  customer_id (FK, NOT NULL), account_id (FK, NOT NULL),
  signal_date (date, NOT NULL — when the signal OCCURRED, not when ingested),
  signal_type (string, nullable), source_type (string, nullable),
  raw_text (TEXT, nullable — original text, retained for audit and
    re-enrichment when a prompt or model changes),
  content (TEXT, nullable — normalized text; NULLABLE means every read of
    it must be null-safe, see Gotcha 5),

  # --- deterministic, ALWAYS populated (no LLM required) ---
  structural_urgency (critical|high|medium|low, NOT NULL),

  # --- LLM-enriched, ALL NULLABLE (may be absent entirely) ---
  sentiment (positive|negative|neutral, nullable),
  relationship_sentiment (float -1.0..+1.0, nullable),
  product_sentiment (float -1.0..+1.0, nullable),
  urgency_score (float 0.0..1.0, nullable),
  intent_signals (JSON list, nullable),
  stakeholder_roles (JSON, nullable),
  suggested_action (string, nullable),
  confidence (JSON — per-field confidence scores, nullable),
  llm_model_version (string, nullable — the exact model id THIS MODULE
    called, sourced from the call wrapper, never from the LLM's own output;
    REQUIRED whenever any enriched field above is non-null, see Gotcha 3),

  # --- derived ---
  effective_urgency (critical|high|medium|low, NOT NULL — max(structural,
    llm-derived); NEVER lower than structural_urgency),
  requires_review (bool, NOT NULL, default false),
  cg_node_id (int, nullable — supplied by the caller, see Dependencies)

LLMUsageRecord:
  id (PK), customer_id (FK, NOT NULL), module (string — caller identifier),
  model (string), tokens_in (int), tokens_out (int),
  cost_estimate_usd (NUMERIC(12,6), NOT NULL — computed, never left null;
    a usage row with no cost makes the budget gate structurally unable to
    fire, see Gotcha 1),
  success (bool, NOT NULL), error_message (TEXT, nullable),
  created_at (timestamp, NOT NULL, server-assigned)
```

**Every LLM-enriched field is nullable and the pipeline must work with all of
them null.** A tenant with LLM disabled, no API key, or an exhausted budget
still gets fully-functional signals — just deterministic ones. This is the
DEFAULT state for a large fraction of tenants, not a degraded edge case.

**Null-safety rule (applies to this whole module):** `content`, `raw_text`,
`urgency_score`, and `confidence` are all nullable. Every function reading
them must handle null without raising — a raise inside enrichment loses the
signal entirely, which violates this module's core guarantee that a signal is
always persisted. Test each null case explicitly; the non-null path passing
proves nothing about it (see Gotcha 5).

## Engine vs. Config

**Engine (build once):**
- The enrichment gate: one function deciding LLM-or-not, checking feature
  flag → API key → remaining budget, returning a structured reason (never a
  bare `False`).
- Cost governance end-to-end: `LLMUsageRecord` table, `MODEL_PRICING`
  lookup, `record_usage` computing and storing `cost_estimate_usd`, and
  `get_spend_this_period` summing it — without all four, the budget branch
  of the gate can never fire.
- The tracked call wrapper as the ONLY way this module calls an LLM,
  returning the model id it used so callers never source it from LLM output.
- Deterministic structural-urgency rules producing a floor LLM enrichment
  can raise but never lower, plus `score_to_level` bridging float→level.
- Confidence gating, including the no-confidence-data case.
- Graceful degradation: any LLM failure (timeout, rate limit, malformed
  response, missing fields, budget exhaustion) leaves the signal persisted
  with deterministic fields populated and enriched fields null.

**Config (an FDE fills in per client):**
- Prompt templates per vertical/signal-type.
- `MODEL_PRICING` values, `REVIEW_THRESHOLD` (default 0.6),
  `REVIEW_WHEN_CONFIDENCE_MISSING` (default true), urgency keyword lists,
  the structural-urgency rule table, `score_to_level` band thresholds.
- Per-tenant budget caps and the feature flag's default state.

## Build Prompt

> Build the signal processing layer. Six numbered pieces. Every function
> called anywhere below is DEFINED below — there are no undefined helpers.
>
> 1. **Schema** — `QualitativeSignal` AND `LLMUsageRecord`, both exactly as
>    Data Shapes specifies. `UNIQUE (customer_id, signal_id)` composite, not
>    a global unique on `signal_id`. All LLM-enriched columns nullable;
>    `cost_estimate_usd` NOT NULL.
>
> 2. **Cost governance** — build this FIRST, before any LLM code, because
>    the gate in piece 4 depends on it and a missing cost path silently
>    disables budget enforcement entirely (Gotcha 1):
>    ```
>    MODEL_PRICING = {   # USD per 1M tokens. Config: FDE sets real numbers.
>        "default": {"in": 3.00, "out": 15.00},
>    }
>    def estimate_cost(model, tokens_in, tokens_out) -> Decimal:
>        p = MODEL_PRICING.get(model, MODEL_PRICING["default"])
>        return (Decimal(tokens_in) / 1_000_000 * Decimal(str(p["in"]))
>              + Decimal(tokens_out) / 1_000_000 * Decimal(str(p["out"])))
>
>    def record_usage(customer_id, module_name, model, tokens_in, tokens_out,
>                      success, error_message=None):
>        row = LLMUsageRecord(
>            customer_id=customer_id, module=module_name, model=model,
>            tokens_in=tokens_in, tokens_out=tokens_out,
>            cost_estimate_usd=estimate_cost(model, tokens_in, tokens_out),
>            success=success, error_message=error_message)
>        # Commit on a SEPARATE session/transaction from the signal write —
>        # a rolled-back signal insert (e.g. a duplicate signal_id) must NOT
>        # discard the usage row for a call the provider already billed.
>        usage_session.add(row); usage_session.commit()
>
>    def get_spend_this_period(customer_id) -> Decimal:
>        return usage_session.query(
>            func.coalesce(func.sum(LLMUsageRecord.cost_estimate_usd), 0)
>        ).filter(LLMUsageRecord.customer_id == customer_id,
>                 LLMUsageRecord.created_at >= period_start()).scalar()
>    ```
>
> 3. **Deterministic enrichment (always runs, no LLM).** Note every text
>    read is null-safe — `content` is nullable and the first rule that
>    raises means no signal is ever persisted (Gotcha 5):
>    ```
>    def _text(signal) -> str:
>        return (signal.content or signal.raw_text or "").lower()
>
>    URGENCY_RULES = [   # ordered; first match wins. FDE-tunable Config.
>        ("critical", lambda s: s.signal_type == "escalation"
>                              or any(k in _text(s) for k in CRITICAL_KEYWORDS)),
>        ("high",     lambda s: s.source_type == "transcript"
>                              or any(k in _text(s) for k in HIGH_KEYWORDS)),
>        ("medium",   lambda s: s.signal_type in ("ticket", "email")),
>        ("low",      lambda s: True),   # mandatory catch-all
>    ]
>    URGENCY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
>
>    def derive_structural_urgency(signal) -> str:
>        for level, rule in URGENCY_RULES:
>            if rule(signal): return level
>        return "low"
>
>    URGENCY_BANDS = [(0.85, "critical"), (0.60, "high"), (0.30, "medium")]
>    def score_to_level(score) -> str | None:
>        if score is None: return None     # a well-formed enrichment may
>            # simply omit urgency_score — that is NOT an error, and must
>            # never raise (Gotcha 5)
>        for threshold, level in URGENCY_BANDS:
>            if score >= threshold: return level
>        return "low"
>
>    def normalize(raw_text) -> str | None:
>        if raw_text is None: return None
>        return " ".join(raw_text.split())    # collapse whitespace; an FDE
>            # may extend (strip signatures, quoted replies, etc.)
>    ```
>
> 4. **The enrichment gate** — returns a reason, never a bare boolean:
>    ```
>    @dataclass
>    class GateDecision:
>        allowed: bool
>        reason: str        # always populated, including when allowed
>
>    def check_enrichment_allowed(customer_id) -> GateDecision:
>        if not feature_enabled("LLM_ENRICHMENT", customer_id):
>            return GateDecision(False, "feature_flag_disabled")
>        if not get_api_key(customer_id):
>            return GateDecision(False, "no_api_key")
>        cap = get_budget_cap(customer_id)
>        if cap is not None:
>            spent = get_spend_this_period(customer_id)   # piece 2
>            if spent >= cap:
>                return GateDecision(False, f"budget_exhausted:{spent:.2f}/{cap:.2f}")
>        return GateDecision(True, "allowed")
>    ```
>
> 5. **The tracked LLM call wrapper — the ONLY way this module calls an
>    LLM.** No other code in this module may construct or invoke an LLM
>    client; inject the client rather than importing it globally, so the
>    source-level containment assertion in the test harness is satisfiable:
>    ```
>    @dataclass
>    class LLMCallResult:
>        response: object | None
>        status: str
>        model: str | None      # the model THIS MODULE called — the only
>            # trustworthy source of llm_model_version (Gotcha 3)
>
>    def call_llm_tracked(customer_id, module_name, prompt, client,
>                          model=DEFAULT_MODEL) -> LLMCallResult:
>        gate = check_enrichment_allowed(customer_id)
>        if not gate.allowed:
>            return LLMCallResult(None, gate.reason, None)
>        try:
>            response = client.complete(model=model, prompt=prompt)
>            record_usage(customer_id, module_name, model,
>                         response.tokens_in, response.tokens_out, success=True)
>            return LLMCallResult(response, "ok", model)
>        except Exception as e:
>            # Record FAILED calls too — they consumed quota and latency, and
>            # their absence makes cost reconciliation impossible.
>            record_usage(customer_id, module_name, model, 0, 0,
>                         success=False, error_message=str(e))
>            return LLMCallResult(None, f"llm_error:{type(e).__name__}", None)
>    ```
>
> 6. **Enrichment + persistence.** Every enriched column declared in Data
>    Shapes is written here — a column declared and never written is dead
>    schema:
>    ```
>    ENRICHED_FIELDS = ("sentiment", "relationship_sentiment",
>        "product_sentiment", "urgency_score", "intent_signals",
>        "stakeholder_roles", "suggested_action", "confidence")
>
>    def parse_enrichment(response) -> dict | None:
>        """Return a dict of ENRICHED_FIELDS present in the response, or None
>        if the response isn't usable. Catch only PARSE errors (JSON decode,
>        missing top-level key, wrong type) — never a bare `except
>        Exception`, which would also swallow bugs in this function itself
>        and report them as 'the LLM returned garbage'."""
>        try:
>            data = json.loads(response.text)
>        except (json.JSONDecodeError, AttributeError, TypeError):
>            return None
>        if not isinstance(data, dict): return None
>        return {k: data.get(k) for k in ENRICHED_FIELDS if k in data}
>
>    def assert_enrichment_pairing(signal):
>        """Executable invariant, not a comment: any enriched field implies a
>        recorded model version, and vice versa (Gotcha 3)."""
>        has_enriched = any(getattr(signal, f) is not None for f in ENRICHED_FIELDS)
>        if has_enriched and not signal.llm_model_version:
>            raise ValueError("enriched signal with no llm_model_version")
>        if signal.llm_model_version and not has_enriched:
>            raise ValueError("llm_model_version set but no enriched fields")
>
>    def process_signal(customer_id, account_id, raw_text, signal_date,
>                        signal_type, source_type, signal_id, client,
>                        cg_node_id=None) -> QualitativeSignal:
>        signal = QualitativeSignal(
>            customer_id=customer_id, account_id=account_id,
>            signal_id=signal_id, signal_date=signal_date,
>            signal_type=signal_type, source_type=source_type,
>            raw_text=raw_text, content=normalize(raw_text),
>            cg_node_id=cg_node_id)
>        signal.structural_urgency = derive_structural_urgency(signal)
>        signal.effective_urgency = signal.structural_urgency   # floor set
>            # BEFORE any LLM attempt, so a failed/skipped enrichment can
>            # never leave effective_urgency unset
>        signal.requires_review = False
>
>        call = call_llm_tracked(customer_id, "signal_enrichment",
>                                 build_prompt(signal), client)
>        parsed = parse_enrichment(call.response) if call.response else None
>        if parsed:
>            for field, value in parsed.items():
>                setattr(signal, field, value)
>            signal.llm_model_version = call.model      # from the WRAPPER,
>                # never from the LLM's own output (Gotcha 3)
>            llm_level = score_to_level(signal.urgency_score)   # None-safe
>            if llm_level and URGENCY_ORDER[llm_level] > \
>                            URGENCY_ORDER[signal.structural_urgency]:
>                signal.effective_urgency = llm_level      # RAISE only
>            conf = signal.confidence
>            if not conf:
>                signal.requires_review = REVIEW_WHEN_CONFIDENCE_MISSING
>                    # an enrichment with NO confidence data is the most
>                    # common LLM shortfall — defaulting it to "trusted"
>                    # silently defeats review routing
>            else:
>                signal.requires_review = any(v < REVIEW_THRESHOLD
>                                              for v in conf.values())
>        assert_enrichment_pairing(signal)
>        db.session.add(signal); db.session.commit()
>        return signal       # ALWAYS persisted, enriched or not
>    ```

## Acceptance Criteria

- A signal processed with the LLM feature flag disabled is still persisted,
  with `structural_urgency` and `effective_urgency` both set and every
  LLM-enriched column null — and the gate returns
  `reason="feature_flag_disabled"`, not a bare `False`.
- Same for no API key (`reason="no_api_key"`).
- **Budget enforcement actually fires**: with a low cap, repeated calls
  accumulate real `cost_estimate_usd` values, `get_spend_this_period`
  returns a non-zero sum, and a subsequent call is refused with
  `reason="budget_exhausted:<spent>/<cap>"` containing real numbers. A test
  that only checks the reason STRING without proving spend accumulates would
  pass against a permanently-zero-spend implementation — assert the sum.
- Every LLM call produces exactly one usage record, including failures, each
  with a non-null `cost_estimate_usd`. Assert structurally too: inspect the
  module's source and assert no LLM client is constructed or invoked outside
  `call_llm_tracked` (Gotcha 1 is precisely a case where an unwired call
  site existed; a behavioral test of known call sites cannot catch that).
- An LLM returning malformed output leaves the signal persisted with
  enriched fields null and does NOT raise — assert column-by-column
  equivalence with an actually-skipped enrichment, not merely "is null".
- An LLM raising leaves the signal persisted, records `success=false` with
  the message, and does not propagate.
- **Null-case matrix** (each must persist the signal, never raise):
  `raw_text=None`/`content=None`; a well-formed enrichment omitting
  `urgency_score`; a well-formed enrichment omitting `confidence`. The
  content-null case specifically must still produce a valid
  `structural_urgency` — a NOT NULL column whose derivation crashes on a
  legal null input means no signal is ever persisted for that input.
- `effective_urgency` is never lower than `structural_urgency`: a signal
  whose rules yield `critical` and whose LLM yields a low `urgency_score`
  stays `critical`. Assert across a full (structural × LLM) matrix.
- An enrichment with NO confidence block sets `requires_review` per
  `REVIEW_WHEN_CONFIDENCE_MISSING` (default true) — assert both settings.
- `llm_model_version` is non-null on every signal with ANY enriched field
  and null on every signal with none, enforced by
  `assert_enrichment_pairing` raising rather than by convention. Critically,
  it must equal the model the WRAPPER used — assert that an LLM response
  whose body contains no model identifier still yields a correct
  `llm_model_version`.
- Every column in `ENRICHED_FIELDS` is actually written when present in the
  LLM response — assert each one, not just `sentiment`/`urgency_score`. A
  declared-but-never-written column is dead schema.
- A usage row survives a failed signal insert (duplicate `signal_id`) — the
  provider billed for that call regardless of whether the signal persisted.
- Two DIFFERENT customers can each persist a signal with the identical
  `signal_id`; the SAME customer persisting a duplicate is rejected. Assert
  both — a global unique constraint passes the second and fails the first.

## Reference Test Harness

1. **Degradation matrix** — flag off, no key, budget exhausted, LLM raises,
   LLM returns garbage, plus the three null-input cases: eight scenarios,
   all asserting the signal is still persisted with deterministic fields
   intact. This path is the DEFAULT for many tenants; give it more coverage
   than the happy path, not less.
2. **Source-level containment assertion** — inspect this module's source and
   assert the LLM client appears only inside `call_llm_tracked`. Prove the
   detector works by mutating the module (append a second, untracked call
   site) and asserting the test then fails — a containment test that can't
   detect a violation is worse than none.
3. **Tenant-collision test** — two customers, same `signal_id`, both
   persist; then a same-customer duplicate is rejected.
4. **Urgency-floor matrix** — every (structural level × LLM level)
   combination including LLM-level `None`; assert `effective_urgency` is
   always the higher of the two.
5. **Budget-accumulation test** — drive real calls through the wrapper with
   a low cap and assert spend accumulates and the gate flips. See Gotcha 1:
   a gate whose spend is structurally always zero looks identical to a
   working gate in every test that doesn't sum the actual costs.

## Known Gotchas

**1. "We log LLM usage" is a claim about every call site AND about the cost
actually being computed — either half missing silently disables governance**
*Symptom:* Cost reconciliation doesn't match the provider's bill; a tenant's
budget cap is exceeded without the cap ever triggering; nobody can say which
feature drove a spend spike.
*Root cause:* Two independent failure modes that look identical from
outside. (a) A `record_usage()` helper exists and most call sites use it, so
the system LOOKS instrumented, but adding a new call site is a manual,
forgettable step — confirmed in the reference system by enumerating every
file constructing an LLM client and checking each for a `record_usage` call;
most were tracked, real exceptions existed. (b) Even with every call site
wired, if the recorded rows carry no COST, the budget gate reads a
permanently-zero spend and can never fire — the logs look full, the cap
looks configured, and nothing enforces it.
*Fix:* Make the tracked wrapper the only way to call an LLM AND make cost
computation part of the same non-optional path. Assert the containment
structurally (source inspection with a mutation check proving the detector
bites), and assert the budget gate by summing real accumulated spend, never
by checking a reason string alone.

**2. Letting LLM-derived urgency override a deterministic one downward**
*Symptom:* A signal with unmistakable escalation markers gets classified
medium/low because the LLM's holistic read of a long, calm-sounding message
scored it that way — and nobody notices, because the deterministic rule
"worked," it just got overwritten.
*Root cause:* Treating LLM urgency as authoritative rather than additive.
Rules are brittle but never miss an explicit marker; LLMs are holistic but
can be talked out of a signal by surrounding tone.
*Fix:* Take the MAX, never the LLM's value alone — the deterministic result
is a floor. Encode as an ordered-level comparison, not a "trust the LLM if
confident" heuristic.

**3. Sourcing the model version from the LLM's own output makes enriched
signals unauditable**
*Symptom:* After a model upgrade there's no reliable way to tell which
existing signals came from which model, so sentiment from two different
models gets compared as if equivalent — or a signal shows enriched fields
with no model version at all and nobody notices.
*Root cause:* Two compounding mistakes. First, reading the model id from the
LLM's response body: the model may simply not include it, yielding a fully
enriched signal with a null version and no error anywhere. Second, stating
the pairing requirement in a code COMMENT — comments don't execute.
*Fix:* The call wrapper returns the model it used; the caller reads it from
there. The pairing invariant is an executable assertion run before commit,
checked in BOTH directions.

**4. Globally-unique external IDs collide across tenants**
*Symptom:* Ingesting a second tenant's data fails on unique-constraint
violations for IDs that are perfectly valid within that tenant — or a naive
upsert silently overwrites one tenant's signal with another's.
*Root cause:* External source IDs are only unique within the system that
generated them; two tenants on the same ticketing product both have ticket
`#1042`.
*Fix:* `UNIQUE (customer_id, signal_id)`. Test the two-tenants-same-id case
explicitly — a global constraint passes every single-tenant test.

**5. A nullable column read unsafely inside enrichment destroys the "always
persisted" guarantee**
*Symptom:* Signals from a particular source silently never appear — not
partially enriched, entirely absent — because an exception fired before the
insert.
*Root cause:* `content`, `raw_text`, `urgency_score`, and `confidence` are
all legitimately null in normal operation, but code written against the
happy path calls `.lower()` on text or does a dict lookup on a level derived
from a null score. Because the exception happens BEFORE `db.session.add`,
the failure mode isn't a bad row — it's no row, which is much harder to
notice than corrupted data.
*Fix:* Null-safe accessors everywhere (`(content or raw_text or "")`,
`score_to_level(None) -> None`), and an explicit null-case test per nullable
column. This is Module 05's Gotcha 5 (NULL-unsafe predicates) recurring in a
different form — the class of bug generalizes beyond SQL predicates to any
read of a nullable value.

## Provenance

Origin: `kpi-dashboard/backend/models.py` (`QualitativeSignal` — its real
`UniqueConstraint('customer_id','signal_id')` and full QSIM-enrichment
column set including `structural_urgency`/`effective_urgency`,
`requires_review`, `llm_model_version`, `confidence`),
`kpi-dashboard/backend/utils/llm_budget_controller.py` (`record_usage`,
`estimate_cost`), `kpi-dashboard/backend/mcp_server/process_data_pipeline.py`
(`run_llm_tier1_inference` — the feature-gated, non-fatal-on-failure
enrichment stage pattern), `kpi-dashboard/backend/utils/signal_analyst.py`.

Gotcha 1 verified during this session by enumerating every backend file that
constructs or invokes an LLM client and checking each for a `record_usage`
call — the majority were tracked, with real exceptions found, confirming a
live gap rather than a hypothetical risk.

## Validation Note

Validated 2026-08-07. A fresh agent built a SQLite-backed implementation
with an injected fake LLM client (57 tests, plus three mutation runs
confirming the structural tests actually bite). Result: **the second module
in a row to hit all four documented failure shapes**, again with executable
proofs rather than assertions.

**Shape (a) — Build Prompt contradicting another section — four proven:**
- `llm_model_version` was read from the LLM's own output
  (`parsed.model_version`) while the wrapper never returned the model it
  called — so an LLM omitting that key produced a fully enriched, entirely
  unauditable signal with no error. Gotcha 3 and the AC both demanded the
  pairing; the code made it unachievable.
- `s.content.lower()` in the FIRST urgency rule, on a column Data Shapes
  declares nullable — raising before the "mandatory catch-all" could run,
  on a NOT NULL column, meaning no signal persisted at all.
- `URGENCY_ORDER[score_to_level(urgency_score)]` on a nullable score —
  a well-formed enrichment omitting `urgency_score` raised out of
  `process_signal`, losing the signal.
- `record_usage(...)` passed no cost and no cost formula existed anywhere,
  so `get_spend_this_period` was permanently 0 and the budget gate could
  never fire — reproducing Gotcha 1's own stated symptom ("a tenant's budget
  cap is exceeded without the cap ever triggering") in the prompt written to
  prevent it. Proven: 25 calls against a $0.01 cap, all allowed, spend 0.00.

**Shape (b):** `score_to_level` was called but never defined anywhere — not
even an ellipsis, a total absence — and its natural implementation raises on
`None`. Same for `record_usage` (natural implementation records what callers
pass: no cost) and `normalize`.

**Shape (c):** `LLMUsageRecord` had no DDL despite being in Data Shapes;
cost governance (a named Boundary "Owns" bullet) had no Build Prompt piece;
five enriched columns (`stakeholder_roles`, `relationship_sentiment`,
`product_sentiment`, `intent_signals`, `suggested_action`) were declared and
never written by any piece — including `stakeholder_roles`, which Boundary
names explicitly as "stakeholder attribution"; `cg_node_id` had no parameter
capable of populating it.

**Shape (d) — five verbatim recurrences:** a required check living in a
comment (Module 01, Module 05); a NULL-unsafe read (Module 05's Gotcha 5);
dead schema surface (Modules 03, 05); a scoring function left as
prose-or-nothing rather than pseudocode (Modules 03, 04 — its THIRD
appearance); a field declared with no parameter able to populate it
(Module 05).

**All fixed in the current spec**: new Build Prompt piece 2 for cost
governance end-to-end (price table, `estimate_cost`, `record_usage` body,
`get_spend_this_period` body, on a separate transaction so a rolled-back
signal doesn't discard a billed call's usage row); `LLMCallResult` carrying
the model id so `llm_model_version` comes from the wrapper; executable
`assert_enrichment_pairing` replacing the comment; `score_to_level` and
`normalize` defined with explicit null handling; null-safe `_text()`;
`ENRICHED_FIELDS` written by a loop so every declared column is populated;
`cg_node_id` parameter added and Dependencies reworded to say the caller
supplies it; `parse_enrichment` given a shape that catches parse errors
specifically rather than a bare `except`; `REVIEW_WHEN_CONFIDENCE_MISSING`
added so a no-confidence enrichment isn't silently trusted. New Gotcha 5 for
the nullable-read class. ACs rewritten to demand summed spend rather than a
reason string, a full null-case matrix, per-column enrichment assertions,
and a mutation check on the containment detector.

**Library-level observation:** modules 05 and 06 — the two most complex
specs so far — each hit all four shapes, while the three simpler earlier
modules hit one or two each. Defect count tracks spec complexity, not
author experience. The "prose instead of pseudocode for a scoring function"
defect has now appeared in three separate modules (03, 04, 06) despite being
documented after the first one; treat any float→category or score→label
conversion as a specific red flag requiring literal pseudocode with explicit
null handling.
