"""
Module 10 — Governance & Audit Layer.

SELF-CONTAINED rebuild from SPEC.md ALONE (adversarial validation).

Implements the five Build-Prompt pieces LITERALLY (following the pseudocode
exactly), filling every undefined helper with its most-natural reading.
Every place I had to invent a helper the Build Prompt references but never
defines is marked `# [FILLED]` — those are candidate shape-(c) defects.

Corrected variants (used only by the defect tests to show the fix passing
alongside) are suffixed `_fixed`.
"""

import ast
import glob
import os


class GovernanceError(Exception):
    pass


class InvariantViolation(Exception):
    pass


# ---------------------------------------------------------------------------
# PIECE 1 — Invariant enforcement framework + paired-test meta-test (LITERAL)
# ---------------------------------------------------------------------------

INVARIANTS = {}  # name -> {checker, pre_commit}


def register_invariant(name, checker, pre_commit=False):
    INVARIANTS[name] = {"checker": checker, "pre_commit": pre_commit}


def run_all_invariants(session):  # Layer C: post-commit audit
    if not INVARIANTS:
        raise GovernanceError(
            "invariant registry is empty — a broken audit, not a clean graph"
        )
    # NOTE: calls checker with ONE positional arg (session).
    return {n: inv["checker"](session) for n, inv in INVARIANTS.items()}


def validate_edge_pre_commit(edge, session):  # Layer A/B: reject before it lands
    for n, inv in INVARIANTS.items():
        if inv["pre_commit"]:
            # NOTE: calls checker with session + keyword `candidate` — a DIFFERENT
            # signature from run_all_invariants above, and from the Data-Shapes
            # contract `checker(callable(session) -> list[Violation])`.
            v = inv["checker"](session, candidate=edge)
            if v:
                raise InvariantViolation(f"{n}: {v}")


def assert_every_invariant_has_paired_tests(test_module):
    names = list(INVARIANTS)
    if not names:
        raise GovernanceError(
            "no invariants registered — meta-test would pass vacuously"
        )
    missing = []
    for n in names:
        for kind in ("clean", "dirty"):
            if not hasattr(test_module, f"test_{n.lower()}_{kind}"):
                missing.append(f"test_{n.lower()}_{kind}")
    if missing:
        raise GovernanceError(f"invariants missing paired tests: {missing}")


# ---------------------------------------------------------------------------
# PIECE 2 — Code-parity drift auditor (LITERAL)
# ---------------------------------------------------------------------------


class Finding:
    """Audit finding shape from the Data Shapes section."""

    def __init__(self, kind, where, detail, allowlisted=False):
        self.kind = kind
        self.where = where
        self.detail = detail
        self.allowlisted = allowlisted

    def __repr__(self):
        return f"Finding({self.kind!r}, {self.where!r}, {self.detail!r})"


# --- helpers the Build Prompt USES in response_keys but never DEFINES -------
# [FILLED] most-natural readings:
def is_dict_literal(v):  # [FILLED]
    return isinstance(v, ast.Dict)


def dict_literal_keys(v):  # [FILLED]
    if not isinstance(v, ast.Dict):
        return set()
    keys = set()
    for k in v.keys:
        if isinstance(k, ast.Constant):
            keys.add(k.value)
    return keys


def is_jsonify_call(v):  # [FILLED]
    return (
        isinstance(v, ast.Call)
        and isinstance(v.func, ast.Name)
        and v.func.id == "jsonify"
    )


def is_name(v):  # [FILLED]
    return isinstance(v, ast.Name)


def _subscript_key(sub):
    sl = sub.slice
    if isinstance(sl, ast.Constant):  # py3.9 form
        return sl.value
    if isinstance(sl, ast.Index) and isinstance(sl.value, ast.Constant):  # py<3.9
        return sl.value.value
    return None


def env_update(env, node):  # [FILLED]
    if len(node.targets) != 1:
        return
    tgt = node.targets[0]
    # result = {...}
    if isinstance(tgt, ast.Name) and isinstance(node.value, ast.Dict):
        env[tgt.id] = dict_literal_keys(node.value)
    # result['k'] = v
    elif isinstance(tgt, ast.Subscript) and isinstance(tgt.value, ast.Name):
        key = _subscript_key(tgt)
        if key is not None:
            env.setdefault(tgt.value.id, set()).add(key)


def response_keys(fn_ast):
    """LITERAL transcription of the Build-Prompt pseudocode."""
    keys = set()
    env = {}
    for node in ast.walk(fn_ast):
        if isinstance(node, ast.Assign):
            env_update(env, node)
        if isinstance(node, ast.Return) and node.value is not None:
            v = node.value
            if is_dict_literal(v):
                keys |= dict_literal_keys(v)
            elif is_jsonify_call(v):
                keys |= dict_literal_keys(v.args[0]) if v.args else set()
            elif is_name(v):
                keys |= env.get(v.id, set())
    return keys


def response_keys_fixed(fn_ast):
    """Corrected: the jsonify branch must fall through to the env lookup when
    its argument is a variable, i.e. handle `return jsonify(result)`."""
    keys = set()
    env = {}
    for node in ast.walk(fn_ast):
        if isinstance(node, ast.Assign):
            env_update(env, node)
        if isinstance(node, ast.Return) and node.value is not None:
            v = node.value
            if is_dict_literal(v):
                keys |= dict_literal_keys(v)
            elif is_jsonify_call(v) and v.args:
                arg = v.args[0]
                if is_dict_literal(arg):
                    keys |= dict_literal_keys(arg)
                elif is_name(arg):
                    keys |= env.get(arg.id, set())
            elif is_name(v):
                keys |= env.get(v.id, set())
    return keys


# --- helpers audit_code_parity USES but the Build Prompt never DEFINES ------
def discover_files(glob_pattern):  # [FILLED] "glob, not a hardcoded list"
    return sorted(glob.glob(glob_pattern, recursive=True))


def _funcs_in_file(path):  # [FILLED]
    with open(path) as fh:
        tree = ast.parse(fh.read())
    return {
        n.name: n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def discover_duplicated_functions(mcp_dir, flask_files):  # [FILLED]
    mcp_funcs = {}
    for p in discover_files(os.path.join(mcp_dir, "**", "*.py")):
        mcp_funcs.update(_funcs_in_file(p))
    flask_funcs = {}
    for p in flask_files:
        flask_funcs.update(_funcs_in_file(p))
    pairs = []
    for name, mnode in mcp_funcs.items():
        if name in flask_funcs:
            pairs.append((mnode, flask_funcs[name]))
    return pairs


def _arg_names(fn):
    return [a.arg for a in fn.args.args]


def signature_drift(mcp_fn, flask_fn, keyfn=response_keys):  # [FILLED]
    if _arg_names(mcp_fn) != _arg_names(flask_fn):
        return [
            Finding(
                "signature_drift",
                f"{flask_fn.name}",
                f"{_arg_names(mcp_fn)} != {_arg_names(flask_fn)}",
            )
        ]
    return []


def response_key_drift(mcp_fn, flask_fn, keyfn=response_keys):  # [FILLED]
    mk = keyfn(mcp_fn)
    fk = keyfn(flask_fn)
    if mk != fk:
        return [
            Finding(
                "response_key_drift",
                f"{flask_fn.name}",
                f"mcp={sorted(mk)} flask={sorted(fk)}",
            )
        ]
    return []


def _called_names(fn):
    return {
        n.func.id
        for n in ast.walk(fn)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }


def helper_drift(mcp_fn, flask_fn):  # [FILLED]
    if _called_names(mcp_fn) != _called_names(flask_fn):
        return [
            Finding(
                "helper_drift",
                f"{flask_fn.name}",
                f"mcp={sorted(_called_names(mcp_fn))} flask={sorted(_called_names(flask_fn))}",
            )
        ]
    return []


def audit_code_parity(mcp_dir, flask_glob, allowlist, _keyfn=response_keys):
    flask_files = discover_files(flask_glob)  # glob, not a hardcoded list
    pairs = discover_duplicated_functions(mcp_dir, flask_files)
    if not pairs:
        raise GovernanceError(
            "0 duplicated-function pairs discovered — discovery is broken, "
            "not the code clean"
        )  # anti-vacuous floor
    findings = []
    for mcp_fn, flask_fn in pairs:
        findings += signature_drift(mcp_fn, flask_fn, _keyfn)
        findings += response_key_drift(mcp_fn, flask_fn, _keyfn)
        findings += helper_drift(mcp_fn, flask_fn)
    return [f for f in findings if (f.where, f.kind) not in allowlist]


# ---------------------------------------------------------------------------
# PIECE 3 — Tool-auth coverage sweep (LITERAL)
# ---------------------------------------------------------------------------

AUTH_CALLS = {
    "require_auth",
    "require_account_auth",
    "require_read_key",
    "require_cross_customer_auth",
    "require_auth_if_key_present",
}


class Tool:
    """Discovered @mcp.tool — name + ast node."""

    def __init__(self, name, node):
        self.name = name
        self.node = node


def calls_any(tool, auth_calls):  # [FILLED]
    return bool(_called_names(tool.node) & set(auth_calls))


def discover_mcp_tools(mcp_modules):  # [FILLED] AST-discover @mcp.tool decorated
    tools = []
    for path in mcp_modules:
        with open(path) as fh:
            tree = ast.parse(fh.read())
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in n.decorator_list:
                    if _is_mcp_tool_decorator(dec):
                        tools.append(Tool(n.name, n))
    return tools


def _is_mcp_tool_decorator(dec):
    target = dec.func if isinstance(dec, ast.Call) else dec
    return isinstance(target, ast.Attribute) and target.attr == "tool"


def audit_tool_auth(mcp_modules, floor):
    tools = discover_mcp_tools(mcp_modules)
    if len(tools) < floor:
        raise GovernanceError(
            f"discovered {len(tools)} tools (< floor {floor}) — the sweep would "
            f"pass vacuously; discovery is broken"
        )  # anti-vacuous
    ungated = [t.name for t in tools if not calls_any(t, AUTH_CALLS)]
    return ungated


# ---------------------------------------------------------------------------
# PIECE 4 — LLM call-site coverage gate (LITERAL)
# ---------------------------------------------------------------------------

BANNED = ("client.messages.create", "chat.completions.create")


class _Site:
    def __init__(self, lineno):
        self.lineno = lineno


def raw_sdk_calls(f, banned):  # [FILLED] find dotted-call sites matching banned
    with open(f) as fh:
        src = fh.read()
    tree = ast.parse(src)
    sites = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            dotted = _dotted_name(n.func)
            if dotted and any(dotted.endswith(b) for b in banned):
                sites.append(_Site(n.lineno))
    return sites


def _dotted_name(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def within_wrapper(site, wrapper_name):  # [FILLED]
    # The spec gives no AST context on `site` to determine enclosing function;
    # most-natural minimal reading: a bare Site has no wrapper context.
    return getattr(site, "wrapper", None) == wrapper_name


def audit_llm_call_sites(src_files, approved):
    if not src_files:
        raise GovernanceError("no source files scanned — broken LLM audit")  # anti-vacuous
    offenders = []
    for f in src_files:
        for site in raw_sdk_calls(f, BANNED):
            if f not in approved and not within_wrapper(site, "llm_call"):
                offenders.append(f"{f}:{site.lineno}")
    return offenders


def assert_gate_wired_to_ci(ci_config_text, gate_name):
    if gate_name not in ci_config_text:
        raise GovernanceError(
            f"{gate_name} is not referenced in CI — it is not enforced"
        )


# ---------------------------------------------------------------------------
# PIECE 5 — Model-governance register + unblock gate (LITERAL)
# ---------------------------------------------------------------------------

REQUIRED_CONTROLS = {1: {"validator", "drift_monitor"}, 2: {"validator"}, 3: set()}


def audit_model_governance(register):
    if not register:
        raise GovernanceError("empty model register — broken governance audit")  # anti-vacuous
    violations = []
    for m in register:
        if m.status == "production":
            have = {
                c
                for c in REQUIRED_CONTROLS[m.tier]
                if getattr(m, c, "MISSING") != "MISSING"
            }
            missing = REQUIRED_CONTROLS[m.tier] - have
            if missing:
                violations.append((m.id, "missing_controls", sorted(missing)))
        for lim in m.known_limitations:
            if lim.cr_id is None:  # a limitation with no CR is untracked
                violations.append((m.id, "untracked_limitation", lim.text))
    return violations


def audit_model_governance_fixed(register):
    """Corrected: guard REQUIRED_CONTROLS lookup against an out-of-range tier
    (Data Shapes says tier ∈ {1,2,3} but nothing validates it → KeyError)."""
    if not register:
        raise GovernanceError("empty model register — broken governance audit")
    violations = []
    for m in register:
        if m.tier not in REQUIRED_CONTROLS:
            violations.append((m.id, "invalid_tier", m.tier))
            continue
        if m.status == "production":
            have = {
                c
                for c in REQUIRED_CONTROLS[m.tier]
                if getattr(m, c, "MISSING") != "MISSING"
            }
            missing = REQUIRED_CONTROLS[m.tier] - have
            if missing:
                violations.append((m.id, "missing_controls", sorted(missing)))
        for lim in (m.known_limitations or []):
            if lim.cr_id is None:
                violations.append((m.id, "untracked_limitation", lim.text))
    return violations
