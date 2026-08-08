# 10 — Governance & Audit Layer

**Layer:** Ops

**Status:** ✅ Validated — see [Validation Note](#validation-note) at the bottom.
A spec-only fresh-agent rebuild (2026-08-07) proved seven defects with executable
tests — headlined by the drift auditor's own key-parser reproducing the very
blind spot (`return jsonify(variable)`) it exists to close — all fixed below.

## Purpose

Keep a running — or regenerated — instance honest, automatically. This module
owns none of the platform's behavior; it owns the **executable checks that catch
when that behavior drifts, loses coverage, or ships without a control**: a
code-parity drift auditor, the enforcement framework around the context-graph
invariants, a tool-auth coverage sweep, an LLM call-site coverage gate, and the
model-governance register with its unblock criteria. The governing principle,
learned the hard way in this codebase, is that **a governance control is only
real if an executable check enforces it AND that check cannot pass vacuously** —
because the single most dangerous failure here is a check that reports "clean"
while the problem it exists to catch is sitting right in front of it (the origin
drift auditor did exactly that while nineteen critical findings were live). This
is the same discipline the consulting-framework applies to itself; Module 10 is
that discipline turned into standing infrastructure for the client.

## Boundary

**Owns:**
- The **code-parity drift auditor**: the AST audit that catches the same logical
  function existing in two places (an MCP tool and a Flask route) and silently
  diverging — with the property that it *discovers* all sites rather than reading
  a hardcoded list, and *fails* rather than passing when discovery finds nothing
  (Gotcha 1).
- The **invariant enforcement framework**: the registry, the 3-layer pattern
  (pre-commit gate + post-commit audit), and the **meta-test that every
  registered invariant has paired clean+dirty tests** (Gotcha 4). It does NOT own
  the invariants themselves — those are Module 04.
- The **tool-auth coverage meta-test**: the AST sweep asserting every tool calls
  an auth function, with a nonzero tool-count floor so it can't pass on empty
  discovery (Gotcha 2). It does NOT own the auth functions — those are Module 07.
- The **LLM call-site coverage gate**: the check that bans raw SDK calls outside
  the tracked wrapper (with an explicit approved-grandfather list), plus the
  requirement that the gate is wired into CI, not just a local hook (Gotcha 3).
  It does NOT own `record_usage`/the wrapper — that is Module 06.
- The **model-governance register + unblock criteria**: the model-card schema
  (tier, risk class, validator, drift monitor, known limitations), the rule that
  a known limitation is a *pending control* tracked as a CR (not documentation),
  and the gate that a Tier-1 model does not reach production without its controls
  (Gotcha 7).

**Explicitly does not own:**
- Any audited behavior: the tools (07), the graph + the invariant *rules* (04),
  scoring (03), the LLM wrapper (06), the `process_data` pipeline (00). This
  module reads and checks them; it implements none of them.
- The audit *trail storage* (WizardRun rows, usage logs) — Modules 05/06 own
  those tables; this module owns the check that every writer populates them
  (Gotcha 6).

## Dependencies

- **Module 00 (Bootstrap):** the running app / DB the auditors inspect; a CLI
  entrypoint to run Layer-C audits on demand.
- **Module 04 (Context Graph):** the invariant *rules* (I1…In) this module
  registers and enforces; `validate_edge_pre_commit` is called from 04's
  `upsert_edge`/`upsert_node`.
- **Module 06 (Signal/LLM):** the `llm_call` tracked wrapper and `record_usage`
  the coverage gate protects.
- **Module 07 (MCP Tool Layer):** the `@mcp.tool` registry and the auth
  functions (`require_auth`, `require_account_auth`, `require_read_key`,
  `require_cross_customer_auth`, `require_auth_if_key_present`) the coverage sweep
  asserts every tool calls.

### Data Shapes

```
Invariant registry entry:
  name (str, e.g. "I16"),
  checker (callable(session, candidate=None) -> list[Violation] — ONE signature;
    candidate=None audits the whole graph (Layer C), a non-None candidate
    validates just that pending edge (Layer A/B). Both call sites pass this shape),
  pre_commit (bool — is it also enforced as a Layer-A/B write-time gate?)

Audit finding:
  kind ("signature_drift"|"response_key_drift"|"helper_drift"|"ungated_tool"|
        "untracked_llm_call"|"missing_audit_row"|"ungoverned_model"|
        "dangerous_shape"|"invalid_tier"),
  where (file:symbol), detail (str), allowlisted (bool)

Model card (register entry) — an OBJECT/dataclass (fields accessed as
attributes: m.id, m.tier, m.status, getattr(m, control_name), lim.cr_id):
  id ("MOD-007"), name, tier (int — validated against REQUIRED_CONTROLS, may be
    out of range, Gotcha handled in piece 5), signal_type, method,
  validator (str | "MISSING"), drift_monitor (str | "MISSING"),
  known_limitations[]: objects with .text and .cr_id (str | None — None =
    untracked, Gotcha 7),
  status ("production"|"spec'd_not_shipped"), risk_class
```

**Anti-vacuous rule (this whole module):** every check declares a coverage floor
and FAILS when coverage is zero. An invariant registry with no entries, a drift
audit that discovers no pairs, a tool sweep that finds no tools, an LLM scan over
no files — each is a *broken check*, not a clean result, and must raise. This is
the module's core invariant; test the zero-coverage case for every check.

## Engine vs. Config

**Engine (build once):** the drift-auditor AST logic, the invariant registry +
3-layer enforcement + the paired-test meta-test, the tool-auth coverage sweep,
the LLM call-site gate, the model-card schema + governance gate, and the
anti-vacuous floor woven through all of them.

**Config (an FDE fills in per client):** the specific invariants (Module 04's
rules), the drift-audit allowlist + baseline, the LLM approved-grandfather list,
the coverage floors (tool count, etc.), and the model-register entries.

## Build Prompt

> Build the governance/audit layer — the executable checks that keep the platform
> honest. Seven numbered pieces. Every helper is defined below, OR is a named
> dependency hook whose contract Dependencies states (`module04_invariant_rules`,
> `module06_llm_call`, `module07_tool_registry`, the stdlib `ast`), OR is one of
> the named AST sub-walkers below whose one-line contract is given here — each is
> a small, well-scoped `ast.walk` over a function body, and each MUST be built to
> its stated contract (an under-detecting sub-walker reproduces the exact blind
> spot the check exists to close, Gotcha 1):
> - `discover_files(glob)` -> file paths matching the glob (never a hardcoded list).
> - `discover_duplicated_functions(mcp_dir, flask_files)` -> [(mcp_fn_ast,
>   flask_fn_ast)] pairs sharing a logical name across the two surfaces.
> - `signature_drift`, `helper_drift` -> findings where two paired functions differ
>   in parameter list / in which vertical-aware helper they delegate to.
> - `response_key_drift(mcp_fn, flask_fn)` -> a finding when
>   `response_keys(mcp_fn) != response_keys(flask_fn)` (uses the defined
>   `response_keys`, so it inherits the all-shapes coverage).
> - `discover_mcp_tools(modules)` -> every `@mcp.tool` FunctionDef; `calls_any(fn,
>   names)` -> True if `fn` calls any function in `names`.
> - `raw_sdk_calls(file, banned)` -> call sites matching a banned SDK pattern;
>   `within_wrapper(site, name)` -> True if the call is lexically inside `name`.
>
> This module CHECKS other modules; it implements no rule, auth function, or
> wrapper itself. The one property every check shares: **it declares a coverage
> floor and raises when coverage is zero** — a check that can pass on empty input
> is the exact failure this module exists to prevent (Gotcha 1/2).
>
> Origin references: `kpi-dashboard/backend/utils/context_graph_invariants.py`
> (`INVARIANTS_REGISTRY:1206`, `run_all_invariants:1227`, `validate_edge_pre_commit:1257`),
> `kpi-dashboard/backend/tests/test_context_graph_invariants.py`
> (`test_registry_every_invariant_has_clean_and_dirty_tests:727`),
> `kpi-dashboard/backend/tests/test_mcp_tool_auth_coverage.py:75`,
> `scripts/audit_flask_mcp_drift.py` (`_discover_flask_files:146`,
> `_build_dict_var_env:360`, `diff_pair:1038`), `scripts/check_llm_wrapper.sh`,
> `kpi-dashboard/docs/governance/{MODEL_INVENTORY.md,GOVERNANCE_ROADMAP.md}`.
>
> 1. **Invariant enforcement framework + paired-test meta-test.** The rules come
>    from Module 04; this module provides the registry, the 3-layer enforcement,
>    and the meta-test that guarantees each rule is tested both ways:
>    ```
>    INVARIANTS = {}    # name -> {checker, pre_commit}; Config-populated from Module 04
>    # Every checker has ONE signature: checker(session, candidate=None) -> list.
>    # candidate=None  => audit the whole graph (Layer C); a non-None candidate
>    # => validate just that pending edge (Layer A/B). Both call sites below pass
>    # the same shape, so a single checker satisfies both (fixes the two-call-site
>    # signature split).
>    def register_invariant(name, checker, pre_commit=False):
>        INVARIANTS[name] = {"checker": checker, "pre_commit": pre_commit}
>
>    def run_all_invariants(session):          # Layer C: post-commit audit
>        if not INVARIANTS:
>            raise GovernanceError("invariant registry is empty — a broken audit, not a clean graph")
>        return {n: inv["checker"](session, candidate=None) for n, inv in INVARIANTS.items()}
>
>    def validate_edge_pre_commit(edge, session):   # Layer A/B: reject before it lands
>        for n, inv in INVARIANTS.items():
>            if inv["pre_commit"]:
>                v = inv["checker"](session, candidate=edge)
>                if v: raise InvariantViolation(f"{n}: {v}")
>
>    def assert_every_invariant_has_paired_tests(test_module):
>        # Executable governance of the TESTS: a rule tested only on clean data
>        # proves nothing about whether it catches the dirty case (Gotcha 4).
>        names = list(INVARIANTS)
>        if not names:
>            raise GovernanceError("no invariants registered — meta-test would pass vacuously")
>        missing = []
>        for n in names:
>            for kind in ("clean", "dirty"):
>                if not hasattr(test_module, f"test_{n.lower()}_{kind}"):
>                    missing.append(f"test_{n.lower()}_{kind}")
>        if missing: raise GovernanceError(f"invariants missing paired tests: {missing}")
>    ```
>
> 2. **Code-parity drift auditor.** Catch the same logical function drifting
>    between an MCP tool and a Flask route. Discover the file set (do not hardcode
>    it — the origin's hardcoded 9-file list is exactly why it went blind,
>    Gotcha 1), and raise if discovery yields nothing:
>    ```
>    def audit_code_parity(mcp_dir, flask_glob, allowlist):
>        flask_files = discover_files(flask_glob)          # glob, not a hardcoded list
>        pairs = discover_duplicated_functions(mcp_dir, flask_files)
>        if not pairs:
>            raise GovernanceError(
>                "0 duplicated-function pairs discovered — discovery is broken, "
>                "not the code clean")                      # anti-vacuous floor
>        findings = []
>        for mcp_fn, flask_fn in pairs:
>            findings += signature_drift(mcp_fn, flask_fn)
>            findings += response_key_drift(mcp_fn, flask_fn)
>            findings += helper_drift(mcp_fn, flask_fn)
>        return [f for f in findings if (f.where, f.kind) not in allowlist]
>
>    # AST sub-helpers for response_keys — DEFINED, not assumed: they are the
>    # load-bearing parts of the Gotcha-1 guard, so an under-detecting one
>    # reproduces Gotcha 1 inside the very check meant to prevent it.
>    def is_dict_literal(v):  return isinstance(v, ast.Dict)
>    def is_name(v):          return isinstance(v, ast.Name)
>    def is_jsonify_call(v):  return isinstance(v, ast.Call) and \
>                                    getattr(v.func, "id", None) == "jsonify"
>    def dict_literal_keys(v):
>        return {k.value for k in v.keys if isinstance(k, ast.Constant)}
>    def env_update(env, node):        # result = {...}  /  result['k'] = v
>        for tgt in node.targets:
>            if is_name(tgt) and is_dict_literal(node.value):
>                env[tgt.id] = dict_literal_keys(node.value)
>            elif isinstance(tgt, ast.Subscript) and is_name(tgt.value) \
>                    and isinstance(tgt.slice, ast.Constant):
>                env.setdefault(tgt.value.id, set()).add(tgt.slice.value)
>    def _keys_of(v, env):             # resolve one return expression's keys
>        if is_dict_literal(v):  return dict_literal_keys(v)
>        if is_name(v):          return env.get(v.id, set())
>        if is_jsonify_call(v) and v.args:
>            return _keys_of(v.args[0], env)   # jsonify(LITERAL) *and* jsonify(VARIABLE)
>        return set()
>
>    def response_keys(fn_ast):
>        # Parse EVERY return shape (Gotcha 1): bare dict, jsonify(dict),
>        # jsonify(variable), and result={}; result['k']=v; return jsonify(result).
>        # Two passes so an assignment that follows the return in walk order still
>        # resolves.
>        keys, env = set(), {}
>        for node in ast.walk(fn_ast):                 # pass 1: build var -> keys
>            if isinstance(node, ast.Assign):
>                env_update(env, node)
>        for node in ast.walk(fn_ast):                 # pass 2: resolve returns
>            if isinstance(node, ast.Return) and node.value is not None:
>                keys |= _keys_of(node.value, env)     # dispatches on literal/name/jsonify
>        return keys
>    ```
>    Prove the detector bites with a self-test: a known signature/response/helper
>    drift must be reported, and mutating the auditor to skip a shape must make the
>    self-test fail (Acceptance).
>
> 3. **Tool-auth coverage sweep.** Every `@mcp.tool` must call an auth function;
>    the count floor makes the sweep impossible to pass on empty discovery
>    (Gotcha 2):
>    ```
>    AUTH_CALLS = {"require_auth", "require_account_auth", "require_read_key",
>                  "require_cross_customer_auth", "require_auth_if_key_present"}
>    def audit_tool_auth(mcp_modules, floor):
>        tools = discover_mcp_tools(mcp_modules)            # every @mcp.tool, AST-discovered
>        if len(tools) < floor:
>            raise GovernanceError(
>                f"discovered {len(tools)} tools (< floor {floor}) — the sweep would "
>                f"pass vacuously; discovery is broken")   # anti-vacuous
>        ungated = [t.name for t in tools if not calls_any(t, AUTH_CALLS)]
>        return ungated                                     # empty == all gated
>    ```
>
> 4. **LLM call-site coverage gate.** Ban raw SDK calls outside the tracked
>    wrapper; an explicit approved list grandfathers audited exceptions. The gate
>    is only real if it runs in CI — a local-only hook is a convention, not a gate
>    (Gotcha 3):
>    ```
>    BANNED = ("client.messages.create", "chat.completions.create")
>    def audit_llm_call_sites(src_files, approved):
>        if not src_files:
>            raise GovernanceError("no source files scanned — broken LLM audit")  # anti-vacuous
>        offenders = []
>        for f in src_files:
>            for site in raw_sdk_calls(f, BANNED):
>                if f not in approved and not within_wrapper(site, "llm_call"):
>                    offenders.append(f"{f}:{site.lineno}")
>        return offenders
>
>    def assert_gate_wired_to_ci(ci_config_text, gate_name):
>        # A ban-direct-calls check CI does not run is documentation, not a gate.
>        if gate_name not in ci_config_text:
>            raise GovernanceError(f"{gate_name} is not referenced in CI — it is not enforced")
>    ```
>
> 5. **Model-governance register + unblock gate.** Each model is a card; a known
>    limitation is a *pending control* tracked as a CR, and a Tier-1 model does not
>    reach production without its required controls (Gotcha 7):
>    ```
>    REQUIRED_CONTROLS = {1: {"validator", "drift_monitor"}, 2: {"validator"}, 3: set()}
>    def audit_model_governance(register):
>        if not register:
>            raise GovernanceError("empty model register — broken governance audit")  # anti-vacuous
>        violations = []
>        for m in register:
>            if m.tier not in REQUIRED_CONTROLS:             # an ungoverned model must not
>                violations.append((m.id, "invalid_tier", m.tier))  # crash the audit — flag it
>                continue
>            if m.status == "production":
>                have = {c for c in REQUIRED_CONTROLS[m.tier]
>                        if getattr(m, c, "MISSING") != "MISSING"}
>                missing = REQUIRED_CONTROLS[m.tier] - have
>                if missing:
>                    violations.append((m.id, "missing_controls", sorted(missing)))
>            for lim in m.known_limitations:
>                if lim.cr_id is None:                       # a limitation with no CR is untracked
>                    violations.append((m.id, "untracked_limitation", lim.text))
>        return violations
>    ```
>
> 6. **Dangerous-shape audit (dead-but-present code, Gotcha 5).** Flag a query
>    with no tenant filter regardless of caller count — "unused" is not "safe":
>    ```
>    def audit_dangerous_shapes(src_files, floor, tenant_key="customer_id"):
>        if len(src_files) < floor:
>            raise GovernanceError(
>                f"scanned {len(src_files)} files (< floor {floor}) — broken shape audit")
>        findings = []
>        for f in src_files:
>            tree = ast.parse(read(f))
>            for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
>                if reads_by_account_id(fn) and not filters_on(fn, tenant_key):
>                    findings.append((f"{f}:{fn.name}", "dangerous_shape",
>                                     f"account read with no {tenant_key} filter"))
>                    # reported even at zero callers — a latent re-introduction hazard
>        return findings
>
>    def reads_by_account_id(fn):   # a query keyed on account_id (an AST filter-by check)
>        return "account_id" in filter_kwargs(fn)
>    def filters_on(fn, key):       # ... and also constrained by the tenant key
>        return key in filter_kwargs(fn)
>    def filter_kwargs(fn):
>        # collect keys used in filter_by(...) / filter(Model.<k>==...) calls in fn
>        keys = set()
>        for n in ast.walk(fn):
>            if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "filter_by":
>                keys |= {kw.arg for kw in n.keywords if kw.arg}
>        return keys
>    ```
>
> 7. **Audit-trail writer-coverage audit (Gotcha 6).** Every writer of an audited
>    entity must create its audit row — enumerate ALL write paths, not just the
>    main one:
>    ```
>    def audit_audit_trail_coverage(entity, audit_row_ctor, writer_fns, floor):
>        # writer_fns = every function AST that creates/updates `entity`.
>        if len(writer_fns) < floor:
>            raise GovernanceError(
>                f"discovered {len(writer_fns)} writers of {entity} (< floor {floor}) "
>                f"— broken writer-coverage audit")           # anti-vacuous
>        missing = []
>        for fn in writer_fns:
>            if not constructs(fn, audit_row_ctor):           # e.g. constructs a WizardRun row
>                missing.append((fn.qualname, "missing_audit_row",
>                                f"{entity} writer does not create {audit_row_ctor}"))
>        return missing                                       # empty == every writer audited
>
>    def constructs(fn, ctor_name):
>        return any(isinstance(n, ast.Call) and getattr(n.func, "id", None) == ctor_name
>                   for n in ast.walk(fn))
>    ```

## Acceptance Criteria

- **Every check fails on zero coverage (the module's core rule).** Assert each of
  the five raises `GovernanceError` on the empty/broken-discovery input: empty
  invariant registry, drift audit with no discovered pairs, tool sweep below the
  floor, LLM audit over no files, empty model register. A check that returns
  "clean" on empty input is the defect this module exists to prevent.
- **Paired-test meta-test bites (Gotcha 4).** With an invariant registered but
  only its `_clean` test present, `assert_every_invariant_has_paired_tests`
  raises naming the missing `_dirty` test; with both present it passes; with an
  empty registry it raises (not passes).
- **Drift auditor discovers all sites and parses all return shapes (Gotcha 1).**
  Given a Flask file only reachable by glob (not in any hardcoded list), the
  auditor still audits it. Given a route that returns `jsonify({...})` and one
  that builds `result={}; result['k']=v; return jsonify(result)`, `response_keys`
  extracts the keys from both — assert a response-key drift in a `jsonify`/
  variable-built return is caught, and that a parser reading only bare `return
  {...}` would miss it (mutation check).
- **Tool-auth sweep names the offender and enforces the floor (Gotcha 2).** A
  tool with no auth call is returned by `audit_tool_auth`; the sweep raises when
  the discovered tool count is below the floor (proving it can't pass on a broken
  discovery that finds zero tools).
- **LLM gate flags an untracked call AND requires CI wiring (Gotcha 3).** A raw
  `client.messages.create` outside `llm_call` and not in the approved list is
  reported; a file in the approved list is not. Separately,
  `assert_gate_wired_to_ci` raises when the gate name is absent from the CI
  config — a local hook that CI doesn't run does not count as enforced.
- **Model gate blocks an ungoverned Tier-1 production model and untracked
  limitations (Gotcha 7).** A Tier-1 model with `status="production"` and a
  `MISSING` drift monitor is a violation; a `spec'd_not_shipped` model is not
  blocked but its known limitations with `cr_id=None` are flagged as untracked.
- **Dead-but-dangerous code is auditable (Gotcha 5).** The auditor can flag a
  function with a cross-tenant read shape (no `customer_id` filter) even when it
  currently has zero callers — assert a zero-caller vulnerable function is
  reported, not skipped because it's "unused."
- **Audit-trail coverage (Gotcha 6).** Given multiple writers of an audited
  entity (e.g. WizardRun), the check flags any writer path that does not create
  the audit row — assert an admin/side path that skips it is caught.

## Reference Test Harness

1. **Anti-vacuous suite** — one test per check driving the empty/zero-coverage
   input and asserting `GovernanceError`. This is the headline suite: it proves
   no check can silently pass on broken discovery.
2. **Paired-test meta-test** — registry with a clean-only invariant (raises),
   both-present (passes), empty (raises).
3. **Drift parser** — fixtures for bare-dict, `jsonify(dict)`, and
   variable-built returns; assert keys extracted from all three; a mutation
   dropping the `jsonify`/variable branch makes a real drift go undetected
   (proving the branch is load-bearing).
4. **Tool-auth sweep** — a gated tool (passes), an ungated tool (named),
   sub-floor discovery (raises).
5. **LLM gate** — untracked call (flagged), approved file (ignored),
   CI-wiring-absent (raises).
6. **Model gate** — ungoverned Tier-1 prod (blocked), untracked limitation
   (flagged), spec'd-not-shipped (not blocked).

## Known Gotchas

**1. A drift auditor that under-detects reports "clean" while everything is
broken — false assurance is worse than no check**
*Symptom:* The audit tooling is green, yet duplicated Flask/MCP logic has drifted
all over the codebase and nobody knows, because the auditor looked in the wrong
places and parsed the wrong shapes.
*Root cause:* Two narrownesses. (a) A hardcoded include-list of files to audit —
so any file not on the list is invisible; (b) a return-value parser that only
read bare `return {...}` literals, missing `return jsonify({...})` and
`result={}; result['k']=v; return jsonify(result)`. In the origin, "the existing
drift-audit tooling reports 'clean' while all of this exists" — nineteen critical
findings live.
*Fix:* Discover the file set by glob with an explicit skip-list; parse every
return shape (literal, `jsonify`, variable-tracked); and add an anti-vacuous
floor — if discovery yields zero pairs, that's a broken auditor, raise. Prove the
detector bites with a self-test and a mutation. Cited: `AUDIT_REPORT_E2E_2026-08-03.md:15`,
`scripts/audit_flask_mcp_drift.py` (`_discover_flask_files:146`,
`_build_dict_var_env:360`, blind-spot comment `:110-119`), commit `022a9d377`.

**2. A coverage sweep that passes vacuously when discovery breaks**
*Symptom:* The "every tool is authenticated" test is green, but a refactor
changed how tools are discovered and the sweep now audits *zero* tools — so it
passes while every tool is unguarded.
*Root cause:* A coverage check that asserts "no offenders found" without also
asserting it *looked at something* passes trivially on an empty set.
*Fix:* Assert a nonzero coverage floor (`tool_count > 50` in the origin) so the
sweep raises rather than passes when discovery finds nothing. Every check in this
module carries this floor. Cited:
`tests/test_mcp_tool_auth_coverage.py:75` (the `tool_count > 50` assertion).

**3. A governance control that lives in a comment or a local-only hook**
*Symptom:* "We track every LLM call" — but a new file makes raw SDK calls with no
tracking, and invisible spend accumulates; or the ban-direct-calls check exists
but CI never runs it, so it catches nothing.
*Root cause:* Two forms of the same failure. A per-call-site memory/convention
("remember to use the wrapper") is not enforcement — the origin's Apr-20 incident
was 6 files, `$0.45` of untracked spend, after exactly such a convention failed.
And a gate that isn't wired into CI is documentation.
*Fix:* Make tracking unbypassable at the language level (the `llm_call` wrapper,
Module 06) AND enforce coverage with a check that bans raw SDK calls outside it —
AND assert that check is referenced in the CI config. Cited:
`utils/llm_budget_controller.py:415-430` (incident + `llm_call:433`),
`scripts/check_llm_wrapper.sh` (the ban + `APPROVED` list; note: shell hook, no
pytest equivalent — verify CI actually invokes it).

**4. A new invariant tested only on clean data proves nothing**
*Symptom:* An invariant is "covered" by a passing test, but it never actually
catches a violation because the only test feeds it clean data.
*Root cause:* Clean-only tests assert the checker doesn't false-positive; they say
nothing about whether it true-positives on the dirty case it exists to catch.
*Fix:* A meta-test that enumerates the registry and requires both
`test_<inv>_clean` and `test_<inv>_dirty` for every entry — and raises on an empty
registry so the meta-test itself can't pass vacuously. Cited:
`tests/test_context_graph_invariants.py:727`
(`test_registry_every_invariant_has_clean_and_dirty_tests`).

**5. Dead-but-present vulnerable code is a latent re-introduction hazard**
*Symptom:* A cross-tenant-leaking function was "fixed" by removing its callers,
but the function still exists — and a future caller silently reintroduces the
leak.
*Root cause:* Remediation that redirects callers without deleting the dangerous
implementation. The origin's `health_score_storage.py:261
get_account_health_trends(account_id, months)` still exists with no `customer_id`
filter and zero current callers (C-18's reader was fixed by redirecting to the
tenant-safe path).
*Fix:* The governance audit flags a dangerous *shape* (a query with no tenant
filter) even at zero callers — "unused" is not "safe." Cited:
`AUDIT_REPORT_E2E_2026-08-03.md:44` (C-18), `health_score_storage.py:261`.

**6. Side-path writers that skip the audit trail**
*Symptom:* An admin-triggered recalibration happens but leaves no trace — the
audit trail shows only the main-path runs, so an investigation can't see what an
admin changed.
*Root cause:* Multiple creators of an audited entity with inconsistent
conventions; the origin has "4 creators, 3 conventions" for WizardRun, and "admin
recalibrate routes create no WizardRun rows at all."
*Fix:* A check that every writer of an audited entity creates its audit row —
enumerate the write paths, not just the main one. Cited:
`AUDIT_REPORT_E2E_2026-08-03.md:137` (§4.7).

**7. Known limitations recorded as documentation instead of tracked as controls**
*Symptom:* A model's "Known Limitations" and "Missing" cells sit in a doc for
months; nobody actions them; a Tier-1 model reaches production without its
validator or drift monitor.
*Root cause:* Governance-as-documentation. A limitation written in a model card
with no linked CR is not on anyone's queue.
*Fix:* A known limitation is a pending control with a `cr_id`; the audit flags any
with `cr_id=None`, and blocks a Tier-1 `production` model missing a required
control. The auto-CR policy ("every hotfix touching Tier-1 logic gets a post-hoc
CR within 24 hours") makes this standing. Cited:
`kpi-dashboard/docs/governance/MODEL_INVENTORY.md` (the 15-model register,
MOD-003/MOD-012 "spec'd, not shipped" gating `:118,:234`),
`GOVERNANCE_ROADMAP.md:186-187` (no-ship-without-governance + auto-CR).

## Provenance

Origin files: `scripts/audit_flask_mcp_drift.py` (code-parity auditor — `diff_pair:1038`,
`_discover_flask_files:146`, `_build_dict_var_env:360`, `VERTICAL_HELPER_PAIRS:189`);
`AUDIT_REPORT_E2E_2026-08-03.md` (C-1..C-19 `:25-45`; C-6 swallowed failures `:32`,
C-10 21 un-authed tools `:36`, C-18 cross-tenant read `:44`, C-19 50.0 sentinel
`:45`, "auditor reports clean" `:15`, WizardRun audit gap §4.7 `:137`);
`docs/AUDIT_REMEDIATION_WAVE1_SPEC.md` (Workstreams A/B/C, canonical-store decision
`:5`); `kpi-dashboard/backend/utils/context_graph_invariants.py` (3-layer defense —
`INVARIANTS_REGISTRY:1206`, `run_all_invariants:1227`, `validate_edge_pre_commit:1257`,
`clamp_unearned_confidence:1413`; 16 runtime invariants I1–I17 + I7 code-check);
`kpi-dashboard/backend/tests/test_context_graph_invariants.py` (paired tests + meta-test
`:727`, I7 `:756`, isolated-DB guard `:43`); `kpi-dashboard/backend/scripts/audit_context_graph.py`
(Layer-C CLI); `kpi-dashboard/backend/tests/test_mcp_tool_auth_coverage.py:75`
(auth coverage sweep + count floor); `kpi-dashboard/backend/mcp_server/auth.py`
(the four gates, `require_read_key:372`, `require_cross_customer_auth:405`);
`kpi-dashboard/backend/utils/llm_budget_controller.py` (`record_usage:210`,
`llm_call:433`, incident `:415-430`); `scripts/check_llm_wrapper.sh` (ban + APPROVED);
`kpi-dashboard/docs/governance/` (`AI_GOVERNANCE_FRAMEWORK.md`, `MODEL_INVENTORY.md`
15-model register, `GOVERNANCE_ROADMAP.md` unblock criteria, `DRIFT_MONITORING.md`,
`CHANGE_MANAGEMENT.md`, `AUDIT_TRAIL_REQUIREMENTS.md`, `QUALITATIVE_SIGNAL_GOVERNANCE.md`);
`kpi-dashboard/backend/utils/account_health.py` (C-18/C-19 convergence,
`get_account_health:57`, `_log_healthtrend_divergence:180`). Commit provenance:
`022a9d377` (widen auditor + C-10), `241473604` (account-health convergence),
`6f7664b18` (Flask/MCP drift audit), `a83e7d085` (invariant 3-layer defense),
`4730e4f79` (governance docs).

Corrections from the code study, incorporated above: the invariant count is **16
runtime (I1–I17, I7 is a code-only check)**, not 11; and the governance docs live
under `kpi-dashboard/docs/governance/`, not the top-level `docs/`.

Authored 2026-08-07 against HEAD `017a07edc`, and validated the same day (see
Validation Note).

## Validation Note

Validated 2026-08-07. A fresh agent, given ONLY this spec in isolation, built a
self-contained implementation with **real `ast`** (so the drift parser and
coverage sweeps ran for real) and wrote pytest tests executing the spec's literal
pseudocode. Result: **19 passed (11 acceptance-coverage tests + 8 defect proofs
with corrected versions)**, and **seven real defects**.

The reassuring result first: **all six anti-vacuous floors were actually present
in Build-Prompt code and each raised as written** — unlike Modules 00 and 11,
where a promised floor was missing from a piece. The lesson from those modules
held. The seven defects were elsewhere:

- **D1 — HIGH/most severe (shape b/d).** `response_keys` handled `jsonify(dict-
  literal)` but dropped `jsonify(variable)` — so `return jsonify(result)` (an
  extremely common Flask shape) yielded no keys, and a real cross-file
  response-key drift over it went undetected. The guard built to close Gotcha 1
  reproduced Gotcha 1 inside itself. *Fixed:* a recursive `_keys_of` dispatches
  literal/name/jsonify (including `jsonify(variable)`), all sub-helpers now
  defined, two-pass walk so assignment order doesn't matter.
- **D2 — (shape a).** The invariant `checker` had two contradictory signatures
  across its call sites (`checker(session)` vs `checker(session, candidate=edge)`)
  and Data Shapes declared only the one-arg form → `TypeError` at one site.
  *Fixed:* one signature `checker(session, candidate=None)`, documented, both
  sites consistent.
- **D3 / D4 — (shape c).** Two checks the Boundary/AC promised — the dead-but-
  dangerous cross-tenant-shape audit (Gotcha 5) and the audit-trail writer-
  coverage audit (Gotcha 6) — had **no Build-Prompt piece at all**. *Fixed:* added
  as pieces 6 and 7, each with its own anti-vacuous floor.
- **D5 — (shape e/a).** `REQUIRED_CONTROLS[m.tier]` raised `KeyError` on an out-
  of-range tier — the ungoverned-model detector taken down by an ungoverned
  model. *Fixed:* guarded lookup emits an `invalid_tier` finding and continues.
- **D6 — (shape a).** Data Shapes declared `known_limitations` as dicts while the
  code read `lim.cr_id`/`.text` as attributes → `AttributeError`. *Fixed:* Data
  Shapes now declares model cards and limitations as attribute-accessed objects.
- **D7 — (shape c).** The "every helper is defined or a named hook" claim was
  false — nine AST sub-helpers were referenced-but-undefined, and that
  underspecification was the *mechanism* by which D1 recurred (an FDE's natural
  `response_keys` sub-helpers under-detect). *Fixed:* the load-bearing sub-helpers
  are now defined, and the remaining AST sub-walkers are named with explicit
  one-line contracts.

**Library-level note:** the anti-vacuous-floor lesson from 00/11 transferred
cleanly (zero floor defects here) — the first time a hard-won lesson demonstrably
carried to a later module without recurring. But shape (c/d) — a promised
deliverable or helper with no code behind it — struck five more times (D1, D3,
D4, D7 and part of D2), confirming it as the library's dominant, most persistent
defect class. Most telling of all: the defect was in the *drift auditor's own key
parser*, i.e. the governance check reproduced the exact bug it was written to
catch — the strongest possible argument for never trusting a governance control
without an adversarial test that proves it bites.
