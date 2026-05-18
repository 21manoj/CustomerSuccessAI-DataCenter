#!/usr/bin/env python3
"""
audit_flask_mcp_drift.py

Static audit that catches "Flask + MCP duplication drift" — the bug class where
the same logical function exists in both ``kpi-dashboard/backend/mcp_server/*.py``
AND a Flask route file (``api_v1_routes.py``, ``executive_dashboard_api.py``,
``outcome_roi_api.py``, etc.). When one side gets fixed, the other silently
drifts — and which behaviour the buyer sees depends on whether the entry point
is the React UI or Claude.ai's MCP client.

Three real instances triggered this audit (May 2026 session):

  1. B-1: ``team_capacity`` health computation — MCP version of
     ``get_team_capacity`` correctly batch-loaded latest ``HealthScore`` rows
     to count at-risk accounts; the Flask sibling at
     ``verticals/dc2_s/api_routes.py:get_team_capacity_api`` was reading
     ``acct.health_score`` (which doesn't exist on Account).
  2. PR #30: ``team_capacity`` response shape — MCP returned ``resource_pool``,
     ``planned_hours``, ``utilization_pct``, ``bottleneck_roles``,
     ``portfolio_context``. Flask returned ``csm_count``, ``accounts_per_csm``,
     ``per_csm_breakdown`` — almost no overlap in keys.
  3. PR #33: ``get_playbook_recommendations`` vertical routing — MCP routed
     through the vertical-aware engine; the Flask ``v1_recommendations`` route
     hard-coded ``get_dc2s_recommendations``, so SaaS tenants got an empty
     list in the UI even though Claude.ai's MCP demo worked.

Algorithm
---------
1. **Index MCP functions.** Parse every ``*.py`` under
   ``kpi-dashboard/backend/mcp_server/`` and harvest:
     - functions decorated with ``@mcp.tool`` (any form: bare, called with
       parens, with arguments)
     - functions named ``get_*`` / ``list_*`` / ``calculate_*`` even without a
       decorator (covers helpers reused across MCP and Flask)
   For each, capture: name, file:line, arg signature, return-dict top-level
   keys (best-effort AST analysis of ``return {...}`` literals), and the set
   of *helper functions it calls* (e.g.
   ``get_recommendations_for_account``, ``calculate_kpi_health``).

2. **Index Flask routes.** Parse a curated set of route files
   (``api_v1_routes.py``, ``executive_dashboard_api.py``,
   ``outcome_roi_api.py``, ``playbook_recommendations_api.py``,
   ``playbook_triggers_api.py``, ``verticals/*/api_routes.py``).
   For each function that has a ``@<bp>.route(...)`` decorator OR sits next
   to one (helper extracted out of a route), record the same metadata, plus
   the URL stem (e.g. ``/team-capacity`` → stem ``team_capacity``).

3. **Pair MCP ↔ Flask.** A Flask function pairs with an MCP function if any
   of these conditions hold:
     - identical name
     - Flask name equals MCP name + one of the canonical suffixes:
       ``_api``, ``_route``, ``_handler``
     - Flask name equals MCP name with the ``get_/list_/calculate_`` prefix
       dropped (``get_team_capacity`` ↔ ``team_capacity``)
     - Flask name starts with ``v1_`` + the MCP name minus its verb prefix
       (``v1_team_capacity`` ↔ ``get_team_capacity``)
     - Flask name starts with ``get_dc2s_`` + MCP suffix
       (``get_dc2s_recommendations`` ↔ ``get_playbook_recommendations``)
     - Flask URL stem matches MCP suffix
       (route ``/recommendations/<id>`` ↔ MCP ``get_playbook_recommendations``)
     - explicit override in ``MANUAL_ALIASES``

4. **Diff per pair.** For each pair, emit a violation when:
     - **signature drift** — non-trivial mismatch in required arg names
       (excluding ``customer_id``/``account_id`` injected by ``@auth``,
       ``request.args`` etc.; we look at function-signature args)
     - **response key drift** — top-level keys returned differ; flag which
       side is richer
     - **helper drift** — MCP calls helper X but Flask calls helper Y, where
       X and Y look like alternates (e.g. one is the ``_dc2s_`` form and the
       other is the vertical-aware form) OR Flask hardcodes a vertical name
       that MCP resolves dynamically

5. **Allowlist** intentionally-different pairs in
   ``.audit_flask_mcp_drift_allowlist.yaml``.

False positives are an expected cost. The fix is either to align the two
sides, or to add an entry to the allowlist with a justification.

Usage
-----
    python scripts/audit_flask_mcp_drift.py                    # audit (exit 1 on findings)
    python scripts/audit_flask_mcp_drift.py --verbose          # show inventory + per-pair diff
    python scripts/audit_flask_mcp_drift.py --self-test        # built-in regression tests
    python scripts/audit_flask_mcp_drift.py --regenerate-baseline
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "kpi-dashboard" / "backend"
MCP_ROOT = BACKEND_ROOT / "mcp_server"

# Files we treat as Flask "route layer". Anything not in this list is ignored
# even if it imports flask — we want to be focused, not encyclopaedic.
FLASK_FILES: tuple[str, ...] = (
    "api_v1_routes.py",
    "executive_dashboard_api.py",
    "outcome_roi_api.py",
    "playbook_recommendations_api.py",
    "playbook_triggers_api.py",
    "account_snapshot_api.py",
    "verticals/dc2_s/api_routes.py",
    "verticals/saas_premium/api_routes.py",
)

ALLOWLIST_FILE = Path(__file__).resolve().parent.parent / ".audit_flask_mcp_drift_allowlist.yaml"
BASELINE_FILE = Path(__file__).resolve().parent / "audit_flask_mcp_drift_baseline.txt"

# Arg names we ignore when comparing signatures. These are conventionally
# injected from request context on the Flask side and passed explicitly on
# the MCP side — the asymmetry is structural, not a real drift.
INJECTED_ARGS = {
    "self",            # method receivers
    "cls",
    "request",         # flask
    "g",
    "session",
}

# Verb prefixes we can drop when matching MCP ↔ Flask names.
VERB_PREFIXES = ("get_", "list_", "calculate_", "compute_")

# Helper name *pairs* that strongly indicate a drift (left = vertical-aware /
# generic, right = DC2S-only hardcode). When MCP calls left and Flask calls
# right (or vice versa) for the same logical operation, flag it.
VERTICAL_HELPER_PAIRS: tuple[tuple[str, str], ...] = (
    ("get_recommendations_for_account", "get_dc2s_recommendations"),
    ("calculate_kpi_health",             "calculate_dc2s_kpi_health"),
    # The MCP version uses ``_resolve_customer_vertical`` to look up the
    # tenant's vertical from the DB. A Flask sibling that imports anything
    # from ``verticals.dc2_s.*`` for the same logical operation is suspicious.
)

# Manual aliases — when a Flask handler has a name that doesn't follow any
# of the inference rules, map it explicitly. Empty by default; add only
# after you've verified the pairing is real.
MANUAL_ALIASES: dict[str, str] = {
    # flask_function_name : mcp_function_name
    "get_outcome_story":   "get_outcome_roi_story",
    "playbook_economics":  "get_playbook_economics",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FuncInfo:
    name: str
    file_path: Path
    lineno: int
    args: list[str]                  # positional + keyword arg names
    return_keys: set[str]            # top-level dict keys returned (best-effort)
    return_unknown: bool             # True if at least one return is not a dict literal
    callees: set[str]                # set of helper names called inside the body
    route_urls: list[str] = field(default_factory=list)  # only for Flask routes
    has_mcp_tool: bool = False       # only for MCP-side
    layer: str = "?"                 # "mcp" or "flask"
    is_thin_proxy: bool = False      # True if Flask body is a 1-3 stmt `_dispatch(...)` shim


@dataclass
class Violation:
    kind: str                        # "signature_drift" | "response_key_drift" | "helper_drift"
    mcp: FuncInfo
    flask: FuncInfo
    detail: str
    suggestion: str | None = None

    def key(self, repo_root: Path) -> tuple[str, str, str]:
        """Stable key for baselining: (kind, mcp_qual, flask_qual). Line
        numbers are intentionally excluded so unrelated edits don't churn
        the baseline."""
        def rel(p: Path) -> str:
            try:
                return str(p.relative_to(repo_root))
            except ValueError:
                return str(p)
        return (
            self.kind,
            f"{rel(self.mcp.file_path)}:{self.mcp.name}",
            f"{rel(self.flask.file_path)}:{self.flask.name}",
        )

    def format(self, repo_root: Path) -> str:
        def rel(p: Path) -> str:
            try:
                return str(p.relative_to(repo_root))
            except ValueError:
                return str(p)
        head = (
            f"audit_flask_mcp_drift: {self.kind}\n"
            f"  MCP   :  {rel(self.mcp.file_path)}:{self.mcp.lineno}  {self.mcp.name}\n"
            f"  Flask :  {rel(self.flask.file_path)}:{self.flask.lineno}  {self.flask.name}\n"
            f"  {self.detail}"
        )
        if self.suggestion:
            wrapped = textwrap.fill(
                self.suggestion, width=88,
                initial_indent="    ", subsequent_indent="    ",
            )
            head = head + "\n" + wrapped
        return head


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _decorator_is_mcp_tool(d: ast.expr) -> bool:
    """Match @mcp.tool, @mcp.tool(), @mcp.tool(name='x'), bare ``mcp.tool``."""
    # @mcp.tool
    if isinstance(d, ast.Attribute):
        return (
            isinstance(d.value, ast.Name)
            and d.value.id == "mcp"
            and d.attr == "tool"
        )
    # @mcp.tool(...) / @mcp.tool(name='x')
    if isinstance(d, ast.Call):
        return _decorator_is_mcp_tool(d.func)
    return False


def _decorator_is_route(d: ast.expr) -> tuple[bool, str | None]:
    """Match ``@<something>.route('/url', ...)``. Returns ``(True, url)`` or
    ``(False, None)``. Also handles ``@app.get('/url')``, ``@bp.post(...)``,
    and ``@dc2s_api.route('/url')`` etc."""
    if not isinstance(d, ast.Call):
        return (False, None)
    fn = d.func
    if not isinstance(fn, ast.Attribute):
        return (False, None)
    attr = fn.attr
    if attr not in ("route", "get", "post", "put", "patch", "delete"):
        return (False, None)
    # First positional arg should be the URL.
    if not d.args:
        return (False, None)
    first = d.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return (True, first.value)
    return (False, None)


def _collect_dict_keys(node: ast.expr) -> tuple[set[str], bool]:
    """For a return-value AST expression, harvest the top-level dict keys (if
    it's a Dict literal) or jsonify({...}) call. Returns (keys, is_unknown)
    where is_unknown is True if we couldn't statically resolve it.

    Handles:
      return {'a': 1, 'b': 2}
      return jsonify({'a': 1, 'b': 2})
      return jsonify({**other, 'a': 1})         -> includes 'a', marks unknown
      return jsonify({'a': 1, 'b': 2}), 200     -> unwraps tuple
    """
    # Unwrap a (response, status_code) tuple.
    if isinstance(node, ast.Tuple) and node.elts:
        return _collect_dict_keys(node.elts[0])

    # jsonify(...) / make_response(jsonify(...))
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in ("jsonify", "make_response"):
            if node.args:
                return _collect_dict_keys(node.args[0])
        # jsonify(...) chained: e.g. _inject_vertical_context(data, customer_id)
        # — we can't introspect that, mark unknown
        return (set(), True)

    if isinstance(node, ast.Dict):
        keys: set[str] = set()
        any_unknown = False
        for k in node.keys:
            if k is None:  # {**spread}
                any_unknown = True
                continue
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                keys.add(k.value)
            else:
                any_unknown = True
        return (keys, any_unknown)

    return (set(), True)


def _collect_callees(node: ast.AST) -> set[str]:
    """Walk a function body and collect names of helpers referenced. Captures:
      - direct calls: ``f(args)``    -> {"f"}
      - method calls: ``a.b.c(args)`` -> {"c"}
      - imports:      ``from m import X`` -> {"X"}
      - bare name references (e.g. passing a helper to a dispatcher):
        ``_dispatch('recommendations', get_dc2s_recommendations, ...)``
        -> {"_dispatch", "get_dc2s_recommendations"}

    The last bullet is critical for catching the PR #33 bug pattern, where
    the DC2S-only helper is passed BY REFERENCE to a dispatcher, never
    directly called inside the Flask handler body.
    """
    callees: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            fn = sub.func
            if isinstance(fn, ast.Name):
                callees.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                callees.add(fn.attr)
        elif isinstance(sub, ast.ImportFrom):
            for alias in sub.names:
                callees.add(alias.asname or alias.name)
        elif isinstance(sub, ast.Name):
            # Treat any referenced bare Name as a "callee" candidate. This
            # captures the dispatcher-by-reference pattern in
            # api_v1_routes.py, where the actual handler is never called
            # directly but is passed to ``_dispatch(...)``.
            # We don't filter on ast.Load vs ast.Store -- it'd narrow false
            # positives but also lose ``import X`` patterns; the cost of a
            # few extra names in this set is negligible.
            callees.add(sub.id)
    return callees


def _function_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args: list[str] = []
    for a in node.args.posonlyargs:
        args.append(a.arg)
    for a in node.args.args:
        args.append(a.arg)
    for a in node.args.kwonlyargs:
        args.append(a.arg)
    return [a for a in args if a not in INJECTED_ARGS]


def _iter_function_scope(node: ast.AST) -> Iterable[ast.AST]:
    """Yield every descendent of ``node`` that lies in the same function
    scope -- i.e. don't cross into nested def/lambda/class bodies. The root
    node itself is not yielded."""
    stack: list[ast.AST] = list(ast.iter_child_nodes(node))
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        yield n
        stack.extend(ast.iter_child_nodes(n))


def _flask_implicit_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Harvest argument names that the Flask handler reads from request
    context. Treated as logical args for the purposes of signature-drift
    comparison.

    Captures:
        request.args.get('foo', ...)
        request.args.get('foo')
        request.json.get('foo', ...)
        request.form.get('foo', ...)
        data.get('foo', ...)        # data = request.json
        request.values.get('foo', ...)
        request.args['foo']
    """
    out: set[str] = set()
    for sub in _iter_function_scope(node):
        # request.args.get('foo', ...)
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if sub.func.attr == "get" and sub.args:
                arg0 = sub.args[0]
                if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                    # Look at the receiver: request.args / request.json / data / etc.
                    recv = sub.func.value
                    recv_name = None
                    if isinstance(recv, ast.Attribute):
                        # request.args -> Attribute(value=Name('request'), attr='args')
                        if isinstance(recv.value, ast.Name) and recv.value.id == "request":
                            recv_name = recv.attr
                    elif isinstance(recv, ast.Name):
                        # data.get(...) where data is request.json
                        recv_name = recv.id
                    if recv_name in ("args", "json", "form", "values", "data", "body", "payload"):
                        out.add(arg0.value)
        # request.args['foo']
        if isinstance(sub, ast.Subscript):
            sl = sub.slice
            if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                inner = sub.value
                if (isinstance(inner, ast.Attribute) and inner.attr in ("args", "json", "form", "values")
                        and isinstance(inner.value, ast.Name) and inner.value.id == "request"):
                    out.add(sl.value)
    return out


def _func_return_info(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[set[str], bool]:
    """Walk function body and aggregate top-level return-dict keys across all
    return statements. ``is_unknown`` becomes True if any return is opaque or
    if no return statement exists.

    Crucially, this DOES NOT descend into nested function/class definitions
    (which have their own returns). Without this guard, a helper closure that
    returns ``{'execution_backend': ...}`` pollutes the outer function's
    return-key set, producing false response-key drift findings.
    """
    keys: set[str] = set()
    any_unknown = False
    saw_return = False

    def walk(n: ast.AST) -> None:
        nonlocal any_unknown, saw_return
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)) and n is not node:
            return
        if isinstance(n, ast.Return) and n.value is not None:
            saw_return = True
            k, u = _collect_dict_keys(n.value)
            keys.update(k)
            if u:
                any_unknown = True
        for child in ast.iter_child_nodes(n):
            walk(child)

    for child in ast.iter_child_nodes(node):
        walk(child)

    if not saw_return:
        any_unknown = True
    return (keys, any_unknown)


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------


def _index_module(
    path: Path,
    layer: str,
    require_mcp_decorator: bool,
) -> list[FuncInfo]:
    """Walk a single .py file and harvest FuncInfo for either MCP or Flask side."""
    try:
        src = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return []

    out: list[FuncInfo] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        has_mcp = False
        route_urls: list[str] = []
        for d in node.decorator_list:
            if _decorator_is_mcp_tool(d):
                has_mcp = True
            ok, url = _decorator_is_route(d)
            if ok and url:
                route_urls.append(url)

        # MCP side: require the @mcp.tool decorator UNLESS the function looks
        # like a "verb prefix" helper we know is reused (``get_X``, ``list_X``,
        # ``calculate_X``).
        if layer == "mcp":
            if not has_mcp:
                if not _has_verb_prefix(node.name):
                    continue
        # Flask side: we want both decorated routes AND sibling helpers in the
        # same file that are clearly tool-shaped (e.g. ``get_dc2s_recommendations``
        # is the implementation function of the ``/recommendations`` route —
        # it has the decorator. But a helper like
        # ``_get_csm_scorecard_for_account`` doesn't have a decorator and isn't
        # a route — we skip those.) Heuristic: keep if has-route OR name
        # matches a verb prefix AND isn't private.
        if layer == "flask":
            if not route_urls and (node.name.startswith("_") or not _has_verb_prefix(node.name) and not _has_route_suffix(node.name)):
                continue

        return_keys, return_unknown = _func_return_info(node)
        callees = _collect_callees(node)
        args = _function_args(node)
        if layer == "flask":
            # Augment the visible signature with names read from
            # request.args/.json/.form/.values -- those are logical args.
            args = list(dict.fromkeys(args + sorted(_flask_implicit_args(node))))
        is_thin = _is_thin_proxy(node) if layer == "flask" else False

        out.append(FuncInfo(
            name=node.name,
            file_path=path,
            lineno=node.lineno,
            args=args,
            return_keys=return_keys,
            return_unknown=return_unknown,
            callees=callees,
            route_urls=route_urls,
            has_mcp_tool=has_mcp,
            layer=layer,
            is_thin_proxy=is_thin,
        ))
    return out


def _is_thin_proxy(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """A Flask handler is a 'thin proxy' if its body is essentially
    ``return _dispatch(...)`` — possibly with one import line. We exclude
    these from pairing because the *real* handler is what ``_dispatch``
    forwards to, and we'll pair against that one directly.
    """
    body = [s for s in node.body if not isinstance(s, ast.Expr)
            or not isinstance(s.value, ast.Constant)]
    if not body:
        return False
    # Allow up to one import line + one return.
    has_dispatch_return = False
    extra_count = 0
    for s in body:
        if isinstance(s, (ast.Import, ast.ImportFrom)):
            extra_count += 1
            continue
        if isinstance(s, ast.Return) and isinstance(s.value, ast.Call):
            fn = s.value.func
            name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)
            if name == "_dispatch":
                has_dispatch_return = True
                continue
        # Anything else disqualifies.
        return False
    return has_dispatch_return and extra_count <= 1


def _has_verb_prefix(name: str) -> bool:
    return any(name.startswith(p) for p in VERB_PREFIXES)


def _has_route_suffix(name: str) -> bool:
    # Flask handlers we don't want to skip even without a decorator visible
    # to our parser (e.g. blueprint helpers reached via add_url_rule).
    return name.endswith(("_api", "_route", "_handler"))


def index_mcp(verbose: bool = False) -> dict[str, list[FuncInfo]]:
    """Returns {function_name: [FuncInfo, ...]} for MCP side. A name may have
    multiple entries if the same name appears in more than one MCP file
    (rare; we still pair against the first by file order)."""
    by_name: dict[str, list[FuncInfo]] = {}
    if not MCP_ROOT.exists():
        return by_name
    for path in sorted(MCP_ROOT.glob("*.py")):
        if path.name == "__init__.py":
            continue
        for info in _index_module(path, layer="mcp", require_mcp_decorator=False):
            by_name.setdefault(info.name, []).append(info)
    if verbose:
        n_tools = sum(1 for infos in by_name.values() for i in infos if i.has_mcp_tool)
        print(f"  MCP inventory: {sum(len(v) for v in by_name.values())} functions "
              f"({n_tools} @mcp.tool, "
              f"{sum(len(v) for v in by_name.values()) - n_tools} verb-prefix helpers)")
    return by_name


def index_flask(verbose: bool = False) -> list[FuncInfo]:
    out: list[FuncInfo] = []
    for rel in FLASK_FILES:
        path = BACKEND_ROOT / rel
        if not path.exists():
            continue
        out.extend(_index_module(path, layer="flask", require_mcp_decorator=False))
    if verbose:
        n_routes = sum(1 for i in out if i.route_urls)
        print(f"  Flask inventory: {len(out)} functions ({n_routes} routed)")
    return out


# ---------------------------------------------------------------------------
# Pairing
# ---------------------------------------------------------------------------


_URL_STEM_RE = re.compile(r"[^a-z0-9]+")


def _url_stem(url: str) -> str:
    """``/api/v1/team-capacity`` -> ``team_capacity``.
    Pick the last non-parameter segment as the stem."""
    parts = [p for p in url.split("/") if p and not p.startswith("<")]
    if not parts:
        return ""
    last = parts[-1].lower()
    return _URL_STEM_RE.sub("_", last).strip("_")


def _trailing_segment_match(a: str, b: str) -> bool:
    """True if ``a`` and ``b`` agree on their full underscore-split sequence
    (one might be a strict suffix of the other). Used to reject loose stem
    overlap like ``health_score_history`` vs ``trigger_history``.

    A single-word match is allowed only when the word is distinctive enough
    (length >= 12 chars), which lets ``recommendations`` (15) pair across
    ``get_playbook_recommendations`` ↔ ``v1_recommendations`` while still
    rejecting ``history`` (7) cross-matching unrelated *_history MCP tools.
    """
    pa = a.split("_")
    pb = b.split("_")
    if pa == pb:
        return True
    n = min(len(pa), len(pb))
    if pa[-n:] != pb[-n:]:
        return False
    if n >= 2:
        return True
    # n == 1: only allow when the shared single word is distinctive.
    return len(pa[-1]) >= 12


def _flask_concept(flask: FuncInfo) -> str:
    """Reduce a Flask function name to its core concept for stem-matching:
    drop leading 'v1_' / 'get_' / 'list_' / 'calculate_', 'dc2s_'/'saas_premium_'
    middles, and trailing '_api'/'_route'/'_handler'/'_detail'.

    ``v1_account_detail`` -> ``account_detail``
    ``get_dc2s_recommendations`` -> ``recommendations``
    ``get_team_capacity_api`` -> ``team_capacity``
    """
    n = flask.name
    if n.startswith("v1_"):
        n = n[3:]
    for p in VERB_PREFIXES:
        if n.startswith(p):
            n = n[len(p):]
            break
    for p in ("dc2s_", "saas_premium_"):
        if n.startswith(p):
            n = n[len(p):]
            break
    for suf in ("_api", "_route", "_handler"):
        if n.endswith(suf):
            n = n[: -len(suf)]
    return n


def _drop_verb_prefix(name: str) -> str:
    for p in VERB_PREFIXES:
        if name.startswith(p):
            return name[len(p):]
    return name


def _candidate_mcp_names(flask: FuncInfo) -> list[str]:
    """Generate MCP function-name candidates for a Flask function."""
    cands: list[str] = []

    n = flask.name

    # 1. exact name
    cands.append(n)

    # 2. strip _api / _route / _handler
    for suf in ("_api", "_route", "_handler"):
        if n.endswith(suf):
            cands.append(n[: -len(suf)])

    # 3. v1_X  -> X / get_X / list_X / calculate_X
    if n.startswith("v1_"):
        bare = n[len("v1_"):]
        cands.append(bare)
        for p in VERB_PREFIXES:
            cands.append(p + bare)

    # 4. get_dc2s_X  -> get_X / X
    if n.startswith("get_dc2s_"):
        bare = n[len("get_dc2s_"):]
        cands.append("get_" + bare)
        cands.append(bare)

    # 5. plain ``X`` -> ``get_X`` (e.g. flask ``playbook_economics`` -> mcp ``get_playbook_economics``)
    for p in VERB_PREFIXES:
        cands.append(p + n)

    # 6. URL-stem-based candidates -- only when the stem appears in the Flask
    # function's concept word (or vice versa). Without this, `/accounts/<id>`
    # routes (stem ``accounts``) get false-paired with MCP ``list_accounts``
    # even when the Flask function is ``get_dc2s_account_detail``.
    concept = _flask_concept(flask)
    for url in flask.route_urls:
        stem = _url_stem(url)
        if not stem:
            continue
        if stem not in concept and concept not in stem:
            continue
        cands.append(stem)
        for p in VERB_PREFIXES:
            cands.append(p + stem)

    # 7. manual alias
    if n in MANUAL_ALIASES:
        cands.insert(0, MANUAL_ALIASES[n])

    # de-dupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for c in cands:
        if c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


def _build_suffix_index(mcp_by_name: dict[str, list[FuncInfo]]) -> dict[str, list[FuncInfo]]:
    """
    Build a lookup ``stem -> [FuncInfo, ...]`` keyed by the *trailing word(s)*
    of each MCP function name. For ``get_playbook_recommendations``, we add:
      - "recommendations"  (single trailing word)
      - "playbook_recommendations" (two trailing words)
    so that a Flask URL stem ``recommendations`` finds the MCP tool even
    though the head verb prefix differs.
    """
    out: dict[str, list[FuncInfo]] = {}
    for name, infos in mcp_by_name.items():
        bare = _drop_verb_prefix(name)
        parts = bare.split("_")
        if not parts:
            continue
        # Trailing 1-word and 2-word suffixes.
        suffixes = {parts[-1]}
        if len(parts) >= 2:
            suffixes.add("_".join(parts[-2:]))
        for s in suffixes:
            if not s:
                continue
            out.setdefault(s, []).extend(infos)
    return out


def pair_functions(
    mcp_by_name: dict[str, list[FuncInfo]],
    flask_funcs: list[FuncInfo],
) -> list[tuple[FuncInfo, FuncInfo]]:
    """Return list of (mcp, flask) pairs."""
    pairs: list[tuple[FuncInfo, FuncInfo]] = []
    suffix_index = _build_suffix_index(mcp_by_name)

    def _pick(infos: list[FuncInfo]) -> FuncInfo:
        # Prefer an MCP function with @mcp.tool decorator (more authoritative).
        return next((i for i in infos if i.has_mcp_tool), infos[0])

    for flask in flask_funcs:
        # Thin-proxy Flask routes: we still pair them, but ONLY for the
        # purpose of catching the PR #33 bug pattern -- "a proxy in
        # api_v1_routes.py hardcodes a get_dc2s_* delegate while the MCP
        # tool routes through the vertical-aware helper". The proxy's
        # signature and response shape are opaque, so the only check that
        # produces a useful signal on these is the helper-drift one.
        # `diff_pair` handles the suppression of the other two diff kinds
        # for thin proxies; we still pair so we can run the helper check.

        matched: FuncInfo | None = None

        # First pass: exact / prefixed / suffixed direct lookups.
        for cand in _candidate_mcp_names(flask):
            if cand in mcp_by_name:
                matched = _pick(mcp_by_name[cand])
                break

        # Second pass: URL-stem suffix lookup.  Flask URL `/recommendations/<id>`
        # matches MCP ``get_playbook_recommendations`` via the suffix index --
        # but only if (a) the URL stem appears in the Flask function's concept
        # word AND (b) the MCP candidate's bare name (after dropping verb
        # prefix) shares its trailing segment with the Flask concept. The
        # second guard rejects e.g. URL ``/trigger-history`` (concept
        # ``trigger_history``) cross-matching MCP ``get_health_score_history``
        # via the too-generic single-word stem ``history``.
        if matched is None:
            flask_concept = _flask_concept(flask)
            for url in flask.route_urls:
                stem = _url_stem(url)
                if not stem:
                    continue
                if stem not in flask_concept and flask_concept not in stem:
                    continue
                if stem in suffix_index:
                    candidates = suffix_index[stem]
                    # Require MCP bare-name's *full* trailing-segment match
                    # the Flask concept's full trailing-segment. This rules
                    # out e.g. ``health_score_history`` matching the concept
                    # ``trigger_history`` even though both end in ``history``.
                    good = [
                        c for c in candidates
                        if _trailing_segment_match(_drop_verb_prefix(c.name), flask_concept)
                    ]
                    if good:
                        matched = _pick(good)
                        break

        # Third pass: bare-name suffix lookup. Flask `get_dc2s_recommendations`
        # -> bare "recommendations" -> suffix-match `get_playbook_recommendations`.
        if matched is None:
            bare = _drop_verb_prefix(flask.name)
            for prefix_to_strip in ("dc2s_", "saas_premium_"):
                if bare.startswith(prefix_to_strip):
                    bare = bare[len(prefix_to_strip):]
                    break
            bare = bare.rstrip("_")
            for suf in ("_api", "_route", "_handler"):
                if bare.endswith(suf):
                    bare = bare[: -len(suf)]
            if bare and bare in suffix_index:
                matched = _pick(suffix_index[bare])

        if matched is not None:
            pairs.append((matched, flask))
    return pairs


# ---------------------------------------------------------------------------
# Diffing
# ---------------------------------------------------------------------------


# Args that are commonly only present on one side because of how the layers
# inject context. We tolerate their presence/absence in either direction.
ARGS_TOLERATED_EITHER_SIDE = {
    "customer_id",
    "account_id",
    "csm_name",
    "metric",
    "period",
    "portfolio_id",
}

# Response keys we ignore in the diff. ``status``/``error`` is always added
# by jsonify wrappers; ``customer_id``/``vertical``/``pillar_labels``/
# ``kpi_labels`` get injected by ``_dispatch`` in ``api_v1_routes.py``.
KEYS_TOLERATED_EITHER_SIDE = {
    "status",
    "error",
    "customer_id",
    "vertical",
    "pillar_labels",
    "kpi_labels",
    # MCP-only book-keeping
    "scope",
}


def _signature_drift(mcp: FuncInfo, flask: FuncInfo) -> str | None:
    """Return a non-empty description if the signatures meaningfully differ."""
    mcp_args = set(mcp.args)
    fla_args = set(flask.args)
    only_mcp = mcp_args - fla_args - ARGS_TOLERATED_EITHER_SIDE
    only_fla = fla_args - mcp_args - ARGS_TOLERATED_EITHER_SIDE
    if not only_mcp and not only_fla:
        return None
    bits: list[str] = []
    if only_mcp:
        bits.append(f"MCP-only args: {sorted(only_mcp)}")
    if only_fla:
        bits.append(f"Flask-only args: {sorted(only_fla)}")
    return "; ".join(bits)


def _response_key_drift(mcp: FuncInfo, flask: FuncInfo) -> str | None:
    """Return a non-empty description if top-level response keys differ
    meaningfully."""
    if mcp.return_unknown or flask.return_unknown:
        # Can't be confident either way.
        if not mcp.return_keys and not flask.return_keys:
            return None
    mcp_k = mcp.return_keys - KEYS_TOLERATED_EITHER_SIDE
    fla_k = flask.return_keys - KEYS_TOLERATED_EITHER_SIDE
    if not mcp_k or not fla_k:
        return None
    only_mcp = mcp_k - fla_k
    only_fla = fla_k - mcp_k
    # Need a non-trivial divergence: at least 2 keys on one side that the
    # other lacks, or one side missing more than half of the other's keys.
    overlap = mcp_k & fla_k
    if not only_mcp and not only_fla:
        return None
    # Skip if difference is just one or two minor keys.
    min_side = min(len(mcp_k), len(fla_k))
    if min_side >= 4 and len(only_mcp) <= 1 and len(only_fla) <= 1:
        return None
    if not overlap and (mcp_k or fla_k):
        richer = "MCP" if len(mcp_k) > len(fla_k) else "Flask"
        return (
            f"NO overlap in response keys. MCP={sorted(mcp_k)} | "
            f"Flask={sorted(fla_k)}. Richer side: {richer}."
        )
    if len(only_mcp) >= 2 or len(only_fla) >= 2:
        return (
            f"MCP-only keys: {sorted(only_mcp)} | "
            f"Flask-only keys: {sorted(only_fla)} | "
            f"shared: {sorted(overlap)}"
        )
    return None


def _helper_drift(mcp: FuncInfo, flask: FuncInfo) -> str | None:
    """Catch the case where MCP calls helper X and Flask calls helper Y for
    the same logical operation, and (X, Y) is in VERTICAL_HELPER_PAIRS."""
    for vertical_aware, dc2s_only in VERTICAL_HELPER_PAIRS:
        if vertical_aware in mcp.callees and dc2s_only in flask.callees:
            return (
                f"MCP routes through '{vertical_aware}' (vertical-aware), "
                f"Flask hardcodes '{dc2s_only}' (DC2S-only). "
                f"This is the PR #33 bug pattern."
            )
        # symmetric — Flask is the right one
        if dc2s_only in mcp.callees and vertical_aware in flask.callees:
            return (
                f"MCP hardcodes '{dc2s_only}' (DC2S-only), Flask routes "
                f"through '{vertical_aware}' (vertical-aware). MCP side "
                f"needs updating."
            )
    return None


def diff_pair(mcp: FuncInfo, flask: FuncInfo) -> list[Violation]:
    out: list[Violation] = []

    if flask.is_thin_proxy:
        # Two checks fire on thin proxies; sig + response are opaque so we
        # skip those.
        #
        # (A) Generic helper drift: MCP calls helper X and Flask references
        #     helper Y where (X, Y) is in VERTICAL_HELPER_PAIRS.
        helper = _helper_drift(mcp, flask)
        if helper:
            out.append(Violation(
                kind="helper_drift",
                mcp=mcp, flask=flask,
                detail=helper,
                suggestion=(
                    "This Flask handler dispatches via `_dispatch(...)` but "
                    "the imported delegate is the DC2S-only helper. The MCP "
                    "tool uses the vertical-aware engine. SaaS / future-"
                    "vertical tenants will hit the wrong code path. See "
                    "PR #33 for the canonical fix."
                ),
            ))

        # (B) Heuristic catch: a v1_* / *_v1 / api_v1 proxy that hardcodes a
        #     get_dc2s_* / *_dc2s_* delegate. This is the PR #33 shape even
        #     when neither (X, Y) entry is in VERTICAL_HELPER_PAIRS, because
        #     the MCP layer can dispatch via a registry rather than a named
        #     helper, hiding the vertical-aware side from our callee scan.
        if not helper and "api_v1_routes.py" in str(flask.file_path):
            dc2s_callees = [
                c for c in flask.callees
                if c.startswith("get_dc2s_") or c.startswith("dc2s_") or "_dc2s_" in c
            ]
            if dc2s_callees:
                out.append(Violation(
                    kind="helper_drift",
                    mcp=mcp, flask=flask,
                    detail=(
                        f"Vertical-agnostic proxy {flask.name} hardcodes a "
                        f"DC2S-only delegate: {sorted(dc2s_callees)}. "
                        f"MCP {mcp.name} routes through the vertical-aware "
                        f"engine. SaaS tenants will hit the wrong handler. "
                        f"This is the PR #33 bug pattern."
                    ),
                    suggestion=(
                        "Route the /api/v1 proxy through the vertical-aware "
                        "helper (e.g. ``playbook_recommendations_api"
                        ".get_recommendations_for_account``), not the DC2S "
                        "endpoint handler. See the PR #33 diff for the "
                        "canonical migration."
                    ),
                ))
        return out

    sig = _signature_drift(mcp, flask)
    if sig:
        out.append(Violation(
            kind="signature_drift",
            mcp=mcp, flask=flask,
            detail=sig,
            suggestion=(
                "Align the two function signatures or add a comment to the "
                "Flask handler explaining why it intentionally omits the arg "
                "(e.g. injected from request context). If intentional, add to "
                f"{ALLOWLIST_FILE.name}."
            ),
        ))

    keys = _response_key_drift(mcp, flask)
    if keys:
        out.append(Violation(
            kind="response_key_drift",
            mcp=mcp, flask=flask,
            detail=keys,
            suggestion=(
                "Bring the leaner side up to the richer side, or document the "
                "difference. Today's PR #30 incident was exactly this — the "
                "Flask team-capacity returned per-CSM rollups while MCP "
                "returned a resource_pool + utilization model, with zero "
                "overlap in keys."
            ),
        ))

    helper = _helper_drift(mcp, flask)
    if helper:
        out.append(Violation(
            kind="helper_drift",
            mcp=mcp, flask=flask,
            detail=helper,
            suggestion=(
                "Route the Flask handler through the same vertical-aware "
                "helper the MCP tool uses. If the Flask handler intentionally "
                "stays DC2S-only (e.g. an /api/dc2s/* alias), add it to "
                f"{ALLOWLIST_FILE.name} with a 'reason' note."
            ),
        ))

    return out


# ---------------------------------------------------------------------------
# Allowlist + baseline
# ---------------------------------------------------------------------------


def load_allowlist(path: Path) -> set[tuple[str, str, str]]:
    """
    YAML-ish format -- we parse without requiring PyYAML (no dependency).

    Format:
        # comment
        - kind: helper_drift
          mcp:   kpi-dashboard/backend/mcp_server/cs_pulse_revenue.py:get_playbook_recommendations
          flask: kpi-dashboard/backend/verticals/dc2_s/api_routes.py:get_dc2s_recommendations
          reason: |
            DC2S alias kept for backward compat with /api/dc2s/*.
    """
    out: set[tuple[str, str, str]] = set()
    if not path.exists():
        return out
    src = path.read_text()
    current: dict[str, str] = {}
    in_reason = False
    for raw in src.splitlines():
        line = raw.rstrip()
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if in_reason:
            # Reason continuation -- skip
            if line.startswith("  ") and ":" not in line:
                continue
            in_reason = False
        if stripped.startswith("- "):
            # commit prior
            if current.get("kind") and current.get("mcp") and current.get("flask"):
                out.add((current["kind"], current["mcp"], current["flask"]))
            current = {}
            # Maybe this line is "- kind: foo" inline:
            rest = stripped[2:]
            if ":" in rest:
                k, v = rest.split(":", 1)
                current[k.strip()] = v.strip()
            continue
        if ":" in stripped:
            k, v = stripped.split(":", 1)
            key = k.strip()
            val = v.strip()
            if key == "reason":
                in_reason = True
                continue
            current[key] = val
    # tail
    if current.get("kind") and current.get("mcp") and current.get("flask"):
        out.add((current["kind"], current["mcp"], current["flask"]))
    return out


def load_baseline(path: Path) -> set[tuple[str, str, str]]:
    """One entry per line:  <kind>|<mcp_qual>|<flask_qual>"""
    out: set[tuple[str, str, str]] = set()
    if not path.exists():
        return out
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) != 3:
            continue
        out.add((parts[0].strip(), parts[1].strip(), parts[2].strip()))
    return out


def write_baseline(path: Path, violations: list[Violation], repo_root: Path) -> None:
    # Preserve any existing per-entry comment lines so a hand-curated baseline
    # doesn't lose its context on regenerate. We look up "key -> comment"
    # from the prior file.
    prior_comments: dict[tuple[str, str, str], str] = {}
    if path.exists():
        last_comment: list[str] = []
        for raw in path.read_text().splitlines():
            stripped = raw.strip()
            if stripped.startswith("#"):
                last_comment.append(raw)
                continue
            if not stripped:
                last_comment = []
                continue
            parts = [p.strip() for p in stripped.split("|")]
            if len(parts) == 3:
                key = (parts[0], parts[1], parts[2])
                # Treat ONLY comments that are immediately above (no blank
                # gap) as belonging to that entry.
                if last_comment:
                    prior_comments[key] = "\n".join(last_comment)
            last_comment = []

    lines = [
        "# audit_flask_mcp_drift baseline",
        "#",
        "# Pre-existing MCP/Flask drift that we know about but aren't fixing in",
        "# the same PR as the audit. Each entry is a real concern -- a bug, a",
        "# latent SaaS-routing risk, or a structural difference we accept for",
        "# now. The audit treats baseline entries as 'not new', so they don't",
        "# fail CI; but they're not in the allowlist because they should",
        "# eventually be fixed (or moved to the allowlist with a reason).",
        "#",
        "# Format:  <kind> | <mcp_relpath:funcname> | <flask_relpath:funcname>",
        "# Comments directly above an entry are preserved on --regenerate-baseline.",
        "#",
    ]
    keys = sorted({v.key(repo_root) for v in violations})
    for key in keys:
        kind, mcp_q, flask_q = key
        lines.append("")
        if key in prior_comments:
            lines.append(prior_comments[key])
        lines.append(f"{kind} | {mcp_q} | {flask_q}")
    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def audit(verbose: bool = False) -> tuple[list[Violation], list[tuple[FuncInfo, FuncInfo]]]:
    mcp_by_name = index_mcp(verbose=verbose)
    flask_funcs = index_flask(verbose=verbose)

    pairs = pair_functions(mcp_by_name, flask_funcs)
    if verbose:
        print(f"  Pairs found: {len(pairs)}")
        for m, f in pairs:
            try:
                fp = f.file_path.relative_to(REPO_ROOT)
            except ValueError:
                fp = f.file_path
            print(f"    {m.name}  <->  {fp}:{f.name}")

    violations: list[Violation] = []
    for mcp, flask in pairs:
        violations.extend(diff_pair(mcp, flask))
    return violations, pairs


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Flask + MCP duplication drift")
    parser.add_argument("--verbose", action="store_true", help="Print inventory + pair list")
    parser.add_argument("--self-test", action="store_true",
                        help="Built-in regression tests using inline source snippets")
    parser.add_argument("--no-baseline", action="store_true",
                        help="Ignore the baseline file -- report every violation")
    parser.add_argument("--regenerate-baseline", action="store_true",
                        help="Overwrite the baseline file with the current violation set")
    parser.add_argument("--time", action="store_true", help="Print wall-clock runtime")
    args = parser.parse_args()

    if args.self_test:
        return _run_self_test()

    t0 = time.time()
    violations, pairs = audit(verbose=args.verbose)
    elapsed = time.time() - t0

    if args.regenerate_baseline:
        # Don't write entries that are already in the allowlist -- those have
        # an explicit reason and shouldn't double-count in the baseline.
        allowlist_for_filter = load_allowlist(ALLOWLIST_FILE)
        to_baseline = [v for v in violations if v.key(REPO_ROOT) not in allowlist_for_filter]
        write_baseline(BASELINE_FILE, to_baseline, REPO_ROOT)
        print(f"audit_flask_mcp_drift: wrote {len(to_baseline)} entries to "
              f"{BASELINE_FILE.relative_to(REPO_ROOT)} "
              f"({len(violations) - len(to_baseline)} skipped — in allowlist)")
        return 0

    allowlist = load_allowlist(ALLOWLIST_FILE)
    baseline: set[tuple[str, str, str]] = set()
    if not args.no_baseline:
        baseline = load_baseline(BASELINE_FILE)

    # Drop violations that match allowlist or baseline.
    new_violations: list[Violation] = []
    n_allowlisted = 0
    n_grandfathered = 0
    for v in violations:
        key = v.key(REPO_ROOT)
        if key in allowlist:
            n_allowlisted += 1
            continue
        if key in baseline:
            n_grandfathered += 1
            continue
        new_violations.append(v)

    if args.time:
        print(f"audit_flask_mcp_drift: {elapsed:.2f}s")
    if not new_violations:
        if args.verbose or n_allowlisted or n_grandfathered:
            print(f"audit_flask_mcp_drift: clean ({len(pairs)} pairs checked, "
                  f"0 new, {n_grandfathered} grandfathered, "
                  f"{n_allowlisted} allowlisted)")
        return 0

    print(f"audit_flask_mcp_drift: {len(new_violations)} new violation(s) "
          f"({n_grandfathered} grandfathered, {n_allowlisted} allowlisted, "
          f"{len(pairs)} pairs checked)\n")
    for v in new_violations:
        print(v.format(REPO_ROOT))
        print()
    print(
        "Fix options:\n"
        "  - Align the two implementations (preferred). The MCP side is usually\n"
        "    the more recent / more vertical-aware one; bring Flask up to match.\n"
        "  - Add to the allowlist if the difference is intentional:\n"
        f"      edit {ALLOWLIST_FILE.relative_to(REPO_ROOT)}\n"
        f"  - Regenerate baseline after a deliberate review:\n"
        f"      python scripts/audit_flask_mcp_drift.py --regenerate-baseline\n"
    )
    return 1


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _parse_funcs_from_source(src: str, path: Path, layer: str) -> list[FuncInfo]:
    """Helper for self-test: parse an in-memory source string as if it were a
    module on disk."""
    tree = ast.parse(src)
    out: list[FuncInfo] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        has_mcp = False
        route_urls: list[str] = []
        for d in node.decorator_list:
            if _decorator_is_mcp_tool(d):
                has_mcp = True
            ok, url = _decorator_is_route(d)
            if ok and url:
                route_urls.append(url)
        return_keys, return_unknown = _func_return_info(node)
        out.append(FuncInfo(
            name=node.name,
            file_path=path,
            lineno=node.lineno,
            args=_function_args(node),
            return_keys=return_keys,
            return_unknown=return_unknown,
            callees=_collect_callees(node),
            route_urls=route_urls,
            has_mcp_tool=has_mcp,
            layer=layer,
        ))
    return out


def _run_self_test() -> int:
    """In-memory cases that re-introduce the historical bugs and exercise
    the negative cases (allowlist + aligned pair)."""
    failures: list[str] = []

    # ── Case 1: PR #33 helper drift ─────────────────────────────────────────
    mcp_src = textwrap.dedent("""
        @mcp.tool
        def get_playbook_recommendations(customer_id: int, account_id: int) -> dict:
            vertical = _resolve_customer_vertical(customer_id)
            data = get_recommendations_for_account(
                account_id=account_id, customer_id=customer_id,
            )
            return {"recommendations": [], "vertical": vertical, "total": 0}
    """)
    flask_src = textwrap.dedent("""
        @api_v1.route('/recommendations/<int:account_id>')
        def v1_recommendations(account_id):
            from verticals.dc2_s.api_routes import get_dc2s_recommendations
            return _dispatch('recommendations', get_dc2s_recommendations, account_id=account_id)
    """)
    mcp_funcs = _parse_funcs_from_source(mcp_src, Path("<mcp>"), "mcp")
    fla_funcs = _parse_funcs_from_source(flask_src, Path("<flask>"), "flask")
    mcp_by_name = {f.name: [f] for f in mcp_funcs}
    pairs = pair_functions(mcp_by_name, fla_funcs)
    if not pairs:
        failures.append("Case 1 PR#33: pair NOT found "
                        "(v1_recommendations <-> get_playbook_recommendations)")
    else:
        vs = diff_pair(*pairs[0])
        if not any(v.kind == "helper_drift" for v in vs):
            failures.append("Case 1 PR#33: helper_drift NOT detected; "
                            f"got {[v.kind for v in vs]}")
        else:
            print("  PASS: Case 1 (PR #33) — helper drift detected "
                  "(get_recommendations_for_account vs get_dc2s_recommendations)")

    # ── Case 2: PR #30 response-key drift on team_capacity ──────────────────
    mcp_src = textwrap.dedent("""
        @mcp.tool
        def get_team_capacity(customer_id: int) -> dict:
            return {
                'scope': 'portfolio',
                'customer_id': customer_id,
                'resource_pool': {},
                'active_playbooks': 0,
                'planned_hours': {},
                'utilization_pct': {},
                'feasible': True,
                'bottleneck_roles': [],
                'overflow_hours': 0.0,
                'portfolio_context': {},
                'recommendation': '',
            }
    """)
    flask_src = textwrap.dedent("""
        @dc2s_api.route('/team-capacity', methods=['GET'])
        def get_team_capacity_api():
            return jsonify({
                'csm_count': 0,
                'csm_names': [],
                'accounts_per_csm': 0,
                'target_per_csm': 0,
                'total_accounts': 0,
                'active_playbooks': 0,
                'active_csm_hours': 0,
                'at_risk_accounts': 0,
                'total_arr': 0,
                'utilization_pct': 0,
                'per_csm_breakdown': [],
            })
    """)
    mcp_funcs = _parse_funcs_from_source(mcp_src, Path("<mcp>"), "mcp")
    fla_funcs = _parse_funcs_from_source(flask_src, Path("<flask>"), "flask")
    mcp_by_name = {f.name: [f] for f in mcp_funcs}
    pairs = pair_functions(mcp_by_name, fla_funcs)
    if not pairs:
        failures.append("Case 2 PR#30: pair NOT found "
                        "(get_team_capacity_api <-> get_team_capacity)")
    else:
        vs = diff_pair(*pairs[0])
        if not any(v.kind == "response_key_drift" for v in vs):
            failures.append("Case 2 PR#30: response_key_drift NOT detected; "
                            f"got {[v.kind for v in vs]}")
        else:
            print("  PASS: Case 2 (PR #30) — response-key drift detected "
                  "(team_capacity: resource_pool/planned_hours vs csm_count/per_csm_breakdown)")

    # ── Case 3: B-1 signature drift ─────────────────────────────────────────
    mcp_src = textwrap.dedent("""
        @mcp.tool
        def get_csm_scorecard(customer_id: int, csm_name: str = None, days: int = 30) -> dict:
            return {'csm_name': csm_name, 'rows': []}
    """)
    flask_src = textwrap.dedent("""
        @dc2s_api.route('/csm-scorecard')
        def get_csm_scorecard_api():
            # No csm_name / days args -- pure request.args lookup.
            return jsonify({'csm_name': '', 'rows': []})
    """)
    mcp_funcs = _parse_funcs_from_source(mcp_src, Path("<mcp>"), "mcp")
    fla_funcs = _parse_funcs_from_source(flask_src, Path("<flask>"), "flask")
    mcp_by_name = {f.name: [f] for f in mcp_funcs}
    pairs = pair_functions(mcp_by_name, fla_funcs)
    if not pairs:
        failures.append("Case 3 B-1 era: pair NOT found")
    else:
        vs = diff_pair(*pairs[0])
        if not any(v.kind == "signature_drift" for v in vs):
            failures.append("Case 3 B-1 era: signature_drift NOT detected "
                            "(MCP has 'days' arg, Flask doesn't)")
        else:
            print("  PASS: Case 3 (B-1 era) — signature drift detected "
                  "(MCP has 'days' arg, Flask doesn't)")

    # ── Case 4: aligned pair = no violations ────────────────────────────────
    mcp_src = textwrap.dedent("""
        @mcp.tool
        def get_revenue_at_risk(customer_id: int, account_id: int) -> dict:
            return {'account_id': account_id, 'revenue_at_risk': 0, 'health_score': 0}
    """)
    flask_src = textwrap.dedent("""
        @api_v1.route('/revenue-at-risk/<int:account_id>')
        def v1_revenue_at_risk(account_id):
            return jsonify({'account_id': account_id, 'revenue_at_risk': 0, 'health_score': 0})
    """)
    mcp_funcs = _parse_funcs_from_source(mcp_src, Path("<mcp>"), "mcp")
    fla_funcs = _parse_funcs_from_source(flask_src, Path("<flask>"), "flask")
    mcp_by_name = {f.name: [f] for f in mcp_funcs}
    pairs = pair_functions(mcp_by_name, fla_funcs)
    if not pairs:
        failures.append("Case 4 aligned: pair NOT found")
    else:
        vs = diff_pair(*pairs[0])
        if vs:
            failures.append(f"Case 4 aligned: unexpected violations {[v.kind for v in vs]}")
        else:
            print("  PASS: Case 4 (aligned pair) — zero violations as expected")

    # ── Case 5: allowlist suppresses an intentional difference ──────────────
    # Build a real Violation, then verify the allowlist parser matches its key.
    fake_mcp = FuncInfo(
        name="get_x", file_path=REPO_ROOT / "kpi-dashboard/backend/mcp_server/foo.py",
        lineno=1, args=[], return_keys=set(), return_unknown=False, callees=set(),
        has_mcp_tool=True, layer="mcp",
    )
    fake_flask = FuncInfo(
        name="get_x_api", file_path=REPO_ROOT / "kpi-dashboard/backend/api_v1_routes.py",
        lineno=1, args=[], return_keys=set(), return_unknown=False, callees=set(),
        layer="flask",
    )
    v = Violation(kind="response_key_drift", mcp=fake_mcp, flask=fake_flask,
                  detail="(synthetic)")
    fake_allowlist_yaml = textwrap.dedent("""
        # synthetic test allowlist
        - kind: response_key_drift
          mcp:   kpi-dashboard/backend/mcp_server/foo.py:get_x
          flask: kpi-dashboard/backend/api_v1_routes.py:get_x_api
          reason: |
            Allowed for self-test only.
    """)
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tf:
        tf.write(fake_allowlist_yaml)
        tf_path = Path(tf.name)
    try:
        allowed = load_allowlist(tf_path)
        if v.key(REPO_ROOT) not in allowed:
            failures.append(f"Case 5 allowlist: key {v.key(REPO_ROOT)} not loaded; "
                            f"got {allowed!r}")
        else:
            print("  PASS: Case 5 (allowlist) — synthetic entry suppresses violation")
    finally:
        tf_path.unlink(missing_ok=True)

    # ── Case 6: URL-stem-based pairing works ────────────────────────────────
    mcp_src = textwrap.dedent("""
        @mcp.tool
        def get_outcome_roi_story(customer_id: int) -> dict:
            return {'story': '', 'historical': {}, 'forward': {}}
    """)
    # Flask name (`get_outcome_story`) doesn't suffix-match — must hit URL stem
    # OR MANUAL_ALIASES (we register an alias for this real pair).
    flask_src = textwrap.dedent("""
        @outcome_roi_api.route('/api/outcome-roi/story', methods=['GET', 'POST'])
        def get_outcome_story():
            return jsonify({'story': '', 'historical': {}, 'forward': {}})
    """)
    mcp_funcs = _parse_funcs_from_source(mcp_src, Path("<mcp>"), "mcp")
    fla_funcs = _parse_funcs_from_source(flask_src, Path("<flask>"), "flask")
    mcp_by_name = {f.name: [f] for f in mcp_funcs}
    pairs = pair_functions(mcp_by_name, fla_funcs)
    if not pairs:
        failures.append("Case 6 URL-stem/alias: pair NOT found "
                        "(get_outcome_story <-> get_outcome_roi_story)")
    else:
        print("  PASS: Case 6 (URL-stem/manual-alias pairing)")

    # ── Case 7: real repo audit completes and runs under 5s (perf gate) ─────
    if BACKEND_ROOT.exists():
        t0 = time.time()
        _vs, _pairs = audit(verbose=False)
        elapsed = time.time() - t0
        if elapsed > 5.0:
            failures.append(f"Case 7 perf: audit took {elapsed:.2f}s (>5s)")
        else:
            print(f"  PASS: Case 7 (perf) — real-repo audit ran in {elapsed:.2f}s")

    if failures:
        print(f"\nself-test: {len(failures)} failure(s):")
        for f in failures:
            print(f"  FAIL: {f}")
        return 2
    print("\nself-test: all cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
