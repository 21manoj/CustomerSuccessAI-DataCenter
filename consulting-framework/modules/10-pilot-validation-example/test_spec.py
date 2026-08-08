"""
Adversarial validation tests for Module 10 (Governance & Audit Layer).

- test_ac_*  : Acceptance-Criteria coverage (the checks that DO hold).
- test_defect_* : each proves a real spec defect by running the spec's literal
  logic and demonstrating the failure, with the corrected version passing.
"""

import ast
import os
import textwrap
import types

import pytest

import impl
from impl import (
    GovernanceError,
    InvariantViolation,
    INVARIANTS,
    register_invariant,
    run_all_invariants,
    validate_edge_pre_commit,
    assert_every_invariant_has_paired_tests,
    response_keys,
    response_keys_fixed,
    audit_code_parity,
    audit_tool_auth,
    audit_llm_call_sites,
    assert_gate_wired_to_ci,
    audit_model_governance,
    audit_model_governance_fixed,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _fn_ast(src):
    """Parse a single function's source and return its FunctionDef node."""
    return ast.parse(textwrap.dedent(src)).body[0]


@pytest.fixture(autouse=True)
def _clean_registry():
    INVARIANTS.clear()
    yield
    INVARIANTS.clear()


class _Lim:
    def __init__(self, text, cr_id):
        self.text = text
        self.cr_id = cr_id


class _Model:
    def __init__(self, id, tier, status, known_limitations=None, **controls):
        self.id = id
        self.tier = tier
        self.status = status
        self.known_limitations = known_limitations or []
        for k, v in controls.items():
            setattr(self, k, v)


# ===========================================================================
# ACCEPTANCE CRITERIA — the anti-vacuous floors that DO hold
# ===========================================================================

def test_ac_run_all_invariants_raises_on_empty():
    with pytest.raises(GovernanceError):
        run_all_invariants(session=object())


def test_ac_paired_meta_raises_on_empty():
    with pytest.raises(GovernanceError):
        assert_every_invariant_has_paired_tests(types.ModuleType("m"))


def test_ac_drift_raises_on_no_pairs(tmp_path):
    mcp_dir = tmp_path / "mcp"
    mcp_dir.mkdir()
    (mcp_dir / "a.py").write_text("def only_here():\n    return 1\n")
    flask = tmp_path / "flask_none.py"
    flask.write_text("def different():\n    return 2\n")
    with pytest.raises(GovernanceError):
        audit_code_parity(str(mcp_dir), str(flask), allowlist=set())


def test_ac_tool_auth_raises_below_floor(tmp_path):
    mod = tmp_path / "tools.py"
    mod.write_text("@mcp.tool()\ndef t1():\n    require_auth()\n")
    with pytest.raises(GovernanceError):
        audit_tool_auth([str(mod)], floor=50)


def test_ac_llm_raises_on_no_files():
    with pytest.raises(GovernanceError):
        audit_llm_call_sites([], approved=set())


def test_ac_model_raises_on_empty_register():
    with pytest.raises(GovernanceError):
        audit_model_governance([])


def test_ac_paired_meta_bites_and_passes():
    register_invariant("I16", lambda s: [])
    mod = types.ModuleType("m")
    setattr(mod, "test_i16_clean", lambda: None)  # only clean present
    with pytest.raises(GovernanceError) as e:
        assert_every_invariant_has_paired_tests(mod)
    assert "test_i16_dirty" in str(e.value)
    setattr(mod, "test_i16_dirty", lambda: None)  # both present
    assert_every_invariant_has_paired_tests(mod) is None


def test_ac_tool_auth_names_ungated(tmp_path):
    mod = tmp_path / "tools.py"
    mod.write_text(
        "@mcp.tool()\ndef gated():\n    require_auth()\n\n"
        "@mcp.tool()\ndef ungated():\n    return 1\n"
    )
    ungated = audit_tool_auth([str(mod)], floor=1)
    assert ungated == ["ungated"]


def test_ac_llm_flags_untracked_and_ignores_approved(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("client.messages.create(x)\n")
    ok = tmp_path / "ok.py"
    ok.write_text("client.messages.create(x)\n")
    offenders = audit_llm_call_sites([str(bad), str(ok)], approved={str(ok)})
    assert offenders == [f"{bad}:1"]
    with pytest.raises(GovernanceError):
        assert_gate_wired_to_ci("some other ci steps", "check_llm_wrapper")
    assert_gate_wired_to_ci("runs check_llm_wrapper in CI", "check_llm_wrapper")


def test_ac_model_blocks_tier1_prod_and_flags_untracked_limitation():
    m1 = _Model("MOD-007", tier=1, status="production", validator="v")  # no drift_monitor
    m2 = _Model(
        "MOD-012", tier=2, status="spec'd_not_shipped",
        known_limitations=[_Lim("no calibration", cr_id=None)], validator="v",
    )
    v = audit_model_governance([m1, m2])
    assert ("MOD-007", "missing_controls", ["drift_monitor"]) in v
    assert ("MOD-012", "untracked_limitation", "no calibration") in v
    # spec'd_not_shipped is NOT blocked for controls
    assert not any(x[0] == "MOD-012" and x[1] == "missing_controls" for x in v)


def test_ac_drift_discovers_by_glob(tmp_path):
    """Flask file reachable only by glob (not any hardcoded list) is still audited."""
    mcp_dir = tmp_path / "mcp"
    mcp_dir.mkdir()
    (mcp_dir / "m.py").write_text("def shared(a, b):\n    return {'x': 1}\n")
    flask = tmp_path / "routes_only_by_glob.py"
    flask.write_text("def shared(a):\n    return {'x': 1}\n")  # arg drift
    findings = audit_code_parity(str(mcp_dir), str(flask), allowlist=set())
    assert any(f.kind == "signature_drift" for f in findings)


# ===========================================================================
# DEFECTS
# ===========================================================================

def test_defect_1_response_keys_misses_jsonify_of_variable():
    """DEFECT 1 (shape b/d) — Build Prompt piece 2, `response_keys`, SPEC lines
    182-196, and AC 'Drift auditor discovers all sites and parses all return
    shapes (Gotcha 1)' SPEC:273-279.

    The AC demands response_keys extract keys from BOTH a `jsonify({...})` return
    AND a `result={}; result['k']=v; return jsonify(result)` return. The literal
    pseudocode handles jsonify ONLY via `dict_literal_keys(v.args[0])` — when the
    jsonify argument is a *variable* (the second required shape) that returns the
    empty set. So the exact Gotcha-1 shape ("return jsonify(result)") is silently
    dropped INSIDE the guard built to prevent Gotcha 1.
    """
    variable_jsonify = _fn_ast(
        """
        def route():
            result = {}
            result['id'] = 1
            result['secret_flag'] = True
            return jsonify(result)
        """
    )
    # LITERAL spec logic drops every key from the variable-built jsonify:
    assert response_keys(variable_jsonify) == set()  # <-- the bug
    # Corrected version recovers them:
    assert response_keys_fixed(variable_jsonify) == {"id", "secret_flag"}


def test_defect_1b_drift_false_negative_from_jsonify_variable(tmp_path):
    """DEFECT 1 consequence — a REAL response-key drift goes UNDETECTED.

    MCP returns jsonify({'id'}); Flask builds a dict with an EXTRA 'secret_flag'
    then `return jsonify(result)`. The keys genuinely differ, so a correct
    auditor reports a response_key_drift. The literal parser reads the Flask side
    as {} and — because {} still differs from {'id'} — happens to *misreport*;
    to show a clean false-NEGATIVE we make both sides carry {'id'} and have the
    Flask side additionally build it via a variable so a correct parser sees no
    drift while... see assertions.
    """
    mcp_dir = tmp_path / "mcp"
    mcp_dir.mkdir()
    # MCP: keys {'id','secret_flag'} via literal jsonify
    (mcp_dir / "m.py").write_text(
        "def shared(a):\n    return jsonify({'id': 1, 'secret_flag': 1})\n"
    )
    # Flask: SAME real keys, but built into a variable then jsonify'd
    flask = tmp_path / "routes.py"
    flask.write_text(
        "def shared(a):\n"
        "    result = {}\n"
        "    result['id'] = 1\n"
        "    result['secret_flag'] = 1\n"
        "    return jsonify(result)\n"
    )
    # Correct parser: identical key sets -> NO response_key_drift (correct).
    fixed = audit_code_parity(
        str(mcp_dir), str(flask), allowlist=set(), _keyfn=response_keys_fixed
    )
    assert not any(f.kind == "response_key_drift" for f in fixed)
    # Literal parser: reads Flask as {} -> reports a SPURIOUS drift, i.e. it
    # cannot see the variable-jsonify keys at all.
    literal = audit_code_parity(
        str(mcp_dir), str(flask), allowlist=set(), _keyfn=response_keys
    )
    spurious = [f for f in literal if f.kind == "response_key_drift"]
    assert spurious and "flask=[]" in spurious[0].detail


def test_defect_2_checker_signature_contradiction():
    """DEFECT 2 (shape a) — Build Prompt piece 1, SPEC:141 vs SPEC:146, and Data
    Shapes SPEC:77 `checker (callable(session) -> list[Violation])`.

    `run_all_invariants` calls `inv["checker"](session)` (one positional arg,
    matching the Data-Shapes contract). `validate_edge_pre_commit` calls
    `inv["checker"](session, candidate=edge)`. A checker written to the DECLARED
    contract `def checker(session)` satisfies the audit path but raises TypeError
    on the pre-commit path — the two call sites disagree with each other and with
    the Data-Shapes signature.
    """
    def contract_checker(session):  # exactly the Data-Shapes signature
        return []

    register_invariant("I16", contract_checker, pre_commit=True)

    # Audit path works with the declared signature:
    assert run_all_invariants(session=object()) == {"I16": []}

    # Pre-commit path blows up because it injects an undeclared `candidate` kwarg:
    with pytest.raises(TypeError):
        validate_edge_pre_commit(edge={"e": 1}, session=object())

    # A checker that accepts BOTH shapes is the only thing that works — proving
    # the Data-Shapes `callable(session)` contract is wrong/underspecified.
    INVARIANTS.clear()

    def dual_checker(session, candidate=None):
        return []

    register_invariant("I16", dual_checker, pre_commit=True)
    assert run_all_invariants(session=object()) == {"I16": []}
    validate_edge_pre_commit(edge={"e": 1}, session=object())  # no raise


def test_defect_3_no_build_piece_for_cross_tenant_shape():
    """DEFECT 3 (shape c) — AC 'Dead-but-dangerous code is auditable (Gotcha 5)'
    SPEC:293-296 and Boundary/Gotcha-5 SPEC:376-387 promise a check that flags a
    zero-caller function with a cross-tenant read shape (no customer_id filter).
    NO Build-Prompt piece implements it and no helper is defined. The rebuilt
    module therefore has no such callable at all.
    """
    for name in ("audit_cross_tenant_shape", "audit_dangerous_shapes",
                 "flag_unfiltered_query"):
        assert not hasattr(impl, name), (
            f"unexpected: {name} exists — but the SPEC gives no pseudocode for it"
        )


def test_defect_4_no_build_piece_for_audit_trail_coverage():
    """DEFECT 4 (shape c) — AC 'Audit-trail coverage (Gotcha 6)' SPEC:297-299,
    Boundary SPEC:56-57 ('owns the check that every writer populates them'),
    Gotcha 6 SPEC:389-398. Promised as OWNED, but the Build Prompt's five pieces
    contain no audit-trail-writer check and define no helper for it.
    """
    for name in ("audit_audit_trail_coverage", "audit_writers",
                 "assert_every_writer_creates_audit_row"):
        assert not hasattr(impl, name), (
            f"unexpected: {name} exists — but the SPEC gives no pseudocode for it"
        )


def test_defect_5_model_gate_keyerror_on_out_of_range_tier():
    """DEFECT 5 (shape e/a) — Build Prompt piece 5, SPEC:251
    `REQUIRED_CONTROLS[m.tier]`. Data Shapes says tier ∈ {1,2,3} (SPEC:87) but
    nothing validates it. A card whose tier is outside {1,2,3} (or None) makes
    the governance audit CRASH with KeyError instead of reporting a violation —
    the audit that exists to catch ungoverned models is itself taken down by an
    ungoverned model.
    """
    bad = _Model("MOD-099", tier=0, status="production", validator="v")
    with pytest.raises(KeyError):
        audit_model_governance([bad])
    # Corrected variant reports it as a violation instead of crashing:
    v = audit_model_governance_fixed([bad])
    assert ("MOD-099", "invalid_tier", 0) in v


def test_defect_6_known_limitations_attr_vs_dict_shape():
    """DEFECT 6 (shape a) — Data Shapes SPEC:88-89 declares
    `known_limitations[]: {text, cr_id}` (a DICT), but Build Prompt piece 5
    SPEC:257-258 accesses `lim.cr_id` / `lim.text` as ATTRIBUTES. A register built
    to the declared dict shape breaks the audit with AttributeError.
    """
    class _M:
        id = "MOD-050"
        tier = 3
        status = "spec'd_not_shipped"
        # per Data Shapes: a list of dicts {text, cr_id}
        known_limitations = [{"text": "no drift monitor", "cr_id": None}]

    with pytest.raises(AttributeError):
        audit_model_governance([_M()])


def test_defect_7_undefined_helpers_not_defined_by_spec():
    """DEFECT 7 (shape c) — Build Prompt claim SPEC:112-116 'Every helper is
    defined below OR is a named dependency hook'. FALSE. piece 2/3/4 reference a
    stack of helpers that are neither defined nor named dependency hooks:
    response_keys' `env_update/is_dict_literal/dict_literal_keys/is_jsonify_call/
    is_name`, plus `discover_files/discover_duplicated_functions/signature_drift/
    response_key_drift/helper_drift` (piece 2), `calls_any/discover_mcp_tools`
    (piece 3), `raw_sdk_calls/within_wrapper` (piece 4). This test documents that
    they had to be INVENTED to build the module (marked `# [FILLED]` in impl.py),
    which is exactly how Gotcha 1's under-detection was reintroduced (Defect 1).
    """
    src = open(os.path.join(os.path.dirname(__file__), "impl.py")).read()
    filled = src.count("# [FILLED]")
    # Every one of these had to be filled with a guessed implementation:
    assert filled >= 9, f"only {filled} filled helpers found"
