#!/usr/bin/env python3
"""
audit_account_column_access.py

Static audit that catches Python code accessing `Account.<column>` (or
`<acct>.<column>` where `acct` was assigned from an `Account` query) where
`<column>` is not actually a column on the `Account` ORM model.

Why this exists
---------------
Three real production bugs in the last six weeks all shared the same shape:

  1. PR #21 (B-1):  acct.health_score        -- not on Account, lives in HealthScore
  2. PR #28 (hotfix from #23):  acct.assigned_csm  -- not on Account, lives in
     Account.profile_metadata (JSON)
  3. Session 11 memory note: journey_data vs journey_json  -- same root cause

Every instance had a unit test that mocked the Account object, masking the
missing-attribute error. Integration tests would catch it, but they're slow.
This audit catches it at pre-commit / CI time.

Algorithm
---------
1. Parse ``kpi-dashboard/backend/models.py`` and extract the column names declared
   on ``class Account(db.Model)`` via AST. We also harvest relationship names and
   method names so we don't false-positive on them.
2. Walk ``kpi-dashboard/backend/**/*.py`` (excluding tests, migrations, alembic,
   scripts/, tenant data dirs, and the model file itself).
3. For each file, identify variables that are "evidence-grade Account":
     - assigned from an `Account.query...` expression
     - assigned from an `Account(...)` constructor call
     - iterated in `for x in <expr>` where `<expr>` involves Account
     - parameter/loop var named ``acct``/``account``/``acc`` IF the file imports
       and references the ``Account`` model
4. For each ``<var>.<attr>`` (where `<var>` is evidence-grade Account) and each
   ``Account.<attr>`` directly, flag if ``<attr>`` is not in the allowlist
   (column set + relationship set + SQLAlchemy/ORM methods + Python dunders).
5. Print a friendly error per violation and exit non-zero if any found.

The heuristic is intentionally conservative on the "evidence" side and
conservative on the allowlist side. False positives are fine -- you fix them
by either adding the column to Account or by adding the symbol to
``KNOWN_OK_ATTRS`` below.

Usage
-----
    python scripts/audit_account_column_access.py                # full audit
    python scripts/audit_account_column_access.py --verbose      # show stats
    python scripts/audit_account_column_access.py --self-test    # run built-in
                                                                 # regression checks
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
import textwrap
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "kpi-dashboard" / "backend"
MODELS_FILE = BACKEND_ROOT / "models.py"
BASELINE_FILE = (
    Path(__file__).resolve().parent / "audit_account_column_access_baseline.txt"
)

# Directories whose contents we never audit. These are migrations, generated
# tenant data, test fixtures, etc. -- not production application code.
EXCLUDE_DIR_NAMES = {
    "tests",
    "test_csv_files",
    "test_qdrant",
    "migrations",
    "alembic",
    "scripts",  # ad-hoc dev scripts; spec excludes
    "__pycache__",
    "uploads",
    "data",
    "templates",
    "uuid_migration",
    "company_kpi_files",
    ".venv",
    "venv",
    "site-packages",
    "node_modules",
}

# Tenant-specific generated data folders inside backend/verticals/.
EXCLUDE_DIR_PATTERNS = (
    "customer",  # customer42-dc2_s, customer289-dc2_s, customer8-dc2_s, etc.
)

# Files we never audit (the model file itself, this audit script).
EXCLUDE_FILE_NAMES = {
    "models.py",
}

# Variable names that frequently refer to an Account row when an Account
# import is present in the file.
#
# We DO NOT use these as standalone evidence -- doing so produced too many
# false positives in practice (functions take parameters named ``account`` /
# ``acct`` that are dicts, named tuples, or other shapes). The set is kept
# around as a hint we surface in error messages and as a tie-breaker; the
# audit only flags a variable when there is *explicit* assignment-from-
# ``Account.query`` evidence in scope.
ACCOUNT_VARIABLE_NAMES = {"acct", "account", "acc"}

# Attributes that look like column accesses but are legitimately not columns.
# Anything in this set is silently allowed regardless of model schema.
KNOWN_OK_ATTRS = {
    # SQLAlchemy internals
    "query",
    "__table__",
    "__tablename__",
    "__table_args__",
    "__mapper__",
    "metadata",
    "registry",
    "_sa_instance_state",
    # Generic ORM helpers and serialization
    "to_dict",
    "as_dict",
    "serialize",
    "save",
    "delete",
    "update",
    "refresh",
    # Python dunders
    "__class__",
    "__dict__",
    "__doc__",
    "__hash__",
    "__eq__",
    "__init__",
    "__repr__",
    "__str__",
    "__module__",
}


# Suggested replacement when we encounter the historical bugs.
HISTORICAL_SUGGESTIONS = {
    "health_score": (
        "Account has no health_score column. Latest health lives in the HealthScore "
        "table (one row per account per measurement_month). See cs_pulse_revenue.py:"
        "get_team_capacity for the canonical batch-load-latest pattern."
    ),
    "assigned_csm": (
        "Account.assigned_csm doesn't exist. Use (acct.profile_metadata or {})."
        "get('assigned_csm') -- same convention as account_snapshot_api.py:381 / "
        "cs_pulse_admin.py:101 / scripts/verify_profile_data.py:65."
    ),
    "journey_data": (
        "Account has no journey_data column. The JourneyData model stores journey "
        "rows; use Account.profile_metadata for lifecycle hints if SaaS."
    ),
    "journey_phase": (
        "Account has no journey_phase column. Store lifecycle phase in "
        "Account.profile_metadata (DC vertical) or use a vertical-specific model."
    ),
    "renewal_date": (
        "Account has no renewal_date column. DC vertical stores it in "
        "profile_metadata; SaaS schema omits it entirely."
    ),
    "contract_start": (
        "Account has no contract_* columns. Store in profile_metadata or a "
        "vertical-specific model."
    ),
    "contract_end": (
        "Account has no contract_* columns. Store in profile_metadata or a "
        "vertical-specific model."
    ),
}


# ---------------------------------------------------------------------------
# 1. Parse models.py and extract Account columns + relationships + methods.
# ---------------------------------------------------------------------------


def extract_account_attrs(models_path: Path) -> tuple[set[str], set[str]]:
    """
    Returns (columns, members) for class Account.

    ``columns`` is just the column names (used in messages / suggestions).
    ``members`` is the full set of legitimately-defined attributes on Account
    (columns + relationships + methods + class-level constants).
    """
    src = models_path.read_text()
    tree = ast.parse(src, filename=str(models_path))

    account_cls = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Account":
            account_cls = node
            break
    if account_cls is None:
        raise RuntimeError(
            f"Could not find `class Account(...)` in {models_path}. "
            "Did the model get renamed?"
        )

    columns: set[str] = set()
    members: set[str] = set()

    for stmt in account_cls.body:
        # Assignments like:  account_id = db.Column(...)  /  account_id: int = db.Column(...)
        targets: list[ast.expr] = []
        value: ast.expr | None = None
        if isinstance(stmt, ast.Assign):
            targets = stmt.targets
            value = stmt.value
        elif isinstance(stmt, ast.AnnAssign) and stmt.target is not None:
            targets = [stmt.target]
            value = stmt.value

        for t in targets:
            if not isinstance(t, ast.Name):
                continue
            name = t.id
            members.add(name)
            if value is not None and _is_db_column_call(value):
                columns.add(name)
            if value is not None and _is_relationship_call(value):
                # relationship() return values are also legit attributes
                pass

        # Method definitions on the class
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            members.add(stmt.name)

    return columns, members


def _is_db_column_call(value: ast.expr) -> bool:
    """True if value looks like db.Column(...) or Column(...)."""
    if not isinstance(value, ast.Call):
        return False
    fn = value.func
    if isinstance(fn, ast.Attribute) and fn.attr == "Column":
        return True
    if isinstance(fn, ast.Name) and fn.id == "Column":
        return True
    return False


def _is_relationship_call(value: ast.expr) -> bool:
    if not isinstance(value, ast.Call):
        return False
    fn = value.func
    if isinstance(fn, ast.Attribute) and fn.attr == "relationship":
        return True
    if isinstance(fn, ast.Name) and fn.id == "relationship":
        return True
    return False


# ---------------------------------------------------------------------------
# 2. Walk backend files.
# ---------------------------------------------------------------------------


def iter_backend_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter directories in-place so os.walk doesn't descend
        pruned = []
        for d in dirnames:
            if d in EXCLUDE_DIR_NAMES:
                continue
            # Skip tenant-customer dirs like customer289-dc2_s
            lower = d.lower()
            if any(lower.startswith(p) for p in EXCLUDE_DIR_PATTERNS) and d != "customers":
                continue
            pruned.append(d)
        dirnames[:] = pruned

        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            if fname in EXCLUDE_FILE_NAMES:
                continue
            yield Path(dirpath) / fname


# ---------------------------------------------------------------------------
# 3. Per-file analysis.
# ---------------------------------------------------------------------------


# Variable "shapes" for tracking Account-related bindings.
#  INSTANCE -- single Account row. e.g. `acct = Account.query.first()`
#  LIST     -- list/collection of Account rows. e.g. `accts = Account.query.all()`
#  QUERY    -- SQLAlchemy Query object. e.g. `q = Account.query.filter(...)`
#  None     -- unknown / not relevant.
SHAPE_INSTANCE = "instance"
SHAPE_LIST = "list"
SHAPE_QUERY = "query"
# Sentinel meaning: "we know this binding exists in scope but it's NOT an
# Account-instance; do not flag attribute accesses on it." Used to shadow an
# outer-scope INSTANCE binding when entering a comprehension whose target
# shares the same name.
SHAPE_NOT_ACCOUNT = "not_account"

# Terminals on a Query that return a single Account row.
INSTANCE_TERMINALS = {"first", "one", "one_or_none", "get", "scalar"}
# Terminals that return a list/iterable of Account rows.
LIST_TERMINALS = {"all"}


class AccountAttrVisitor(ast.NodeVisitor):
    """
    Walks a module and flags attribute accesses on `Account` and on variables
    that are evidence-grade Account *instances*.

    The 'evidence-grade' check is local to each function scope. Module-level
    bindings are tracked separately.

    We distinguish three shapes (INSTANCE / LIST / QUERY) -- only attribute
    accesses on the INSTANCE shape are subject to the column-name check.
    Accesses on LIST (like `.sort`, `.append`) and QUERY (like `.all`,
    `.filter`) are skipped, avoiding the bulk of historical false positives.
    """

    def __init__(self, columns: set[str], members: set[str], file_path: Path,
                 file_imports_account: bool,
                 account_returning_helpers: dict[str, str] | None = None):
        self.columns = columns
        self.members = members
        self.file_path = file_path
        self.file_imports_account = file_imports_account
        # Each scope is a dict: var_name -> shape string (or absent if unknown).
        # We push/pop on FunctionDef.
        self.scope_stack: list[dict[str, str]] = [{}]
        self.violations: list[Violation] = []
        # Map of helper-function-name -> shape, populated by a first pass over
        # the module before this visitor runs. Calls to these helpers are
        # treated as returning the listed shape.
        self.account_returning_helpers = account_returning_helpers or {}

    # -- scope management ----------------------------------------------------

    def _current_scope(self) -> dict[str, str]:
        return self.scope_stack[-1]

    def _shape_of(self, name: str) -> str | None:
        # Search inner-to-outer. We deliberately don't fall back to a name-
        # only heuristic -- parameters named `account` / `acct` are commonly
        # dicts in this codebase, and the false-positive cost dominates.
        for scope in reversed(self.scope_stack):
            if name in scope:
                return scope[name]
        return None

    def _is_account_instance(self, name: str) -> bool:
        return self._shape_of(name) == SHAPE_INSTANCE

    def _mark_var(self, name: str, shape: str) -> None:
        self._current_scope()[name] = shape

    # -- helpers -------------------------------------------------------------

    def _expr_account_shape(self, value: ast.expr) -> str | None:
        """
        Classify the shape of an Account-related expression.

        Returns SHAPE_INSTANCE, SHAPE_LIST, SHAPE_QUERY, or None.

        We are conservative -- only return a shape for patterns we can prove
        statically. A false positive here cascades into many downstream
        false-positive violations.
        """
        # Account(...) constructor -> instance
        if isinstance(value, ast.Call):
            fn = value.func
            if isinstance(fn, ast.Name) and fn.id == "Account":
                return SHAPE_INSTANCE
            # Account.query.<...>.<terminal>(...)
            if isinstance(fn, ast.Attribute) and _outermost_name(fn) == "Account":
                terminal = fn.attr
                if terminal in INSTANCE_TERMINALS:
                    return SHAPE_INSTANCE
                if terminal in LIST_TERMINALS:
                    return SHAPE_LIST
                # any other call on an Account.query chain is itself a Query
                return SHAPE_QUERY
            # db.session.query(Account).<...>.<terminal>(...)
            sa_shape = _sqlalchemy_account_chain_shape(value)
            if sa_shape is not None:
                return sa_shape
            # Call to a same-module helper we've inferred returns Account(s).
            #   _get_customer_accounts(cid) -> LIST
            #   _get_account(cid, aid)      -> INSTANCE
            if isinstance(fn, ast.Name) and fn.id in self.account_returning_helpers:
                return self.account_returning_helpers[fn.id]
        # Account.query (no call) -- a Query object
        if isinstance(value, ast.Attribute):
            if _outermost_name(value) == "Account":
                # If the attribute is `query`, that's the canonical Query.
                # If it's an explicit column like Account.account_id, callers
                # are unlikely to bind that to a `accounts` variable; treat
                # as Query for safety.
                return SHAPE_QUERY
        # Direct `Account`
        if isinstance(value, ast.Name) and value.id == "Account":
            return SHAPE_QUERY  # being used as a class reference
        # Bound variable
        if isinstance(value, ast.Name):
            return self._shape_of(value.id)
        # Subscript like accounts[0] -- LIST becomes INSTANCE
        if isinstance(value, ast.Subscript):
            inner = self._expr_account_shape(value.value)
            if inner == SHAPE_LIST:
                return SHAPE_INSTANCE
            return None
        return None

    # -- visitor methods -----------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scope_stack.append({})
        # Function parameters: we don't auto-mark anything as Account from
        # the parameter name alone -- too noisy. Real Account evidence will
        # come from the function body (assignment from Account.query, etc).
        self.generic_visit(node)
        self.scope_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_Assign(self, node: ast.Assign) -> None:
        shape = self._expr_account_shape(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name) and shape is not None:
                self._mark_var(target.id, shape)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        # for acct in Account.query.filter_by(...).all():
        # Iterating a LIST/QUERY of accounts -> target is INSTANCE.
        # for-loop targets DON'T have their own scope in Python (unlike
        # comprehensions), so the binding genuinely persists past the loop;
        # we therefore reflect it accurately.
        if isinstance(node.target, ast.Name):
            iter_shape = self._expr_account_shape(node.iter)
            if iter_shape in (SHAPE_LIST, SHAPE_QUERY):
                self._mark_var(node.target.id, SHAPE_INSTANCE)
            else:
                # Loop binding is something else -- overwrite any prior
                # INSTANCE marking so a follow-up `for acct in non_accounts:`
                # doesn't keep `acct` flagged as Account.
                self._mark_var(node.target.id, SHAPE_NOT_ACCOUNT)
        self.generic_visit(node)

    def _visit_comprehension_like(self, node: ast.expr) -> None:
        """
        Handle GeneratorExp / ListComp / SetComp / DictComp. Each has a list
        of ast.comprehension generators; their .target is a Name (or Tuple)
        bound from .iter for the duration of the body.

        We approximate scope by pushing a fresh dict, marking each comprehension
        target if its iter yields Account (or if the name is in
        ACCOUNT_VARIABLE_NAMES and the file imports Account), then visiting
        all child nodes (elt(s) + ifs + iters) and popping.
        """
        self.scope_stack.append({})
        try:
            generators = getattr(node, "generators", []) or []
            for comp in generators:
                # Visit the iter expression first (it executes in OUTER scope
                # for the first generator, but for nested generators it's in
                # inner scope -- close enough for our heuristic).
                self.visit(comp.iter)
                iter_shape = self._expr_account_shape(comp.iter)
                if isinstance(comp.target, ast.Name):
                    if iter_shape in (SHAPE_LIST, SHAPE_QUERY):
                        self._mark_var(comp.target.id, SHAPE_INSTANCE)
                    else:
                        # Crucial: comprehensions have their own scope in Py3,
                        # so always shadow any outer same-name binding even
                        # when the iter isn't Account-shaped. Without this we
                        # leak an outer `for acct in accounts:` INSTANCE
                        # binding into a later `sum(1 for acct in dicts ...)`
                        # and produce a flood of false positives.
                        self._mark_var(comp.target.id, SHAPE_NOT_ACCOUNT)
                # Walk the comprehension's filter clauses
                for if_node in comp.ifs:
                    self.visit(if_node)
            # Walk the result expression(s)
            if isinstance(node, ast.DictComp):
                self.visit(node.key)
                self.visit(node.value)
            elif hasattr(node, "elt"):
                self.visit(node.elt)
        finally:
            self.scope_stack.pop()

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension_like(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension_like(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension_like(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension_like(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Direct: Account.<attr>
        if isinstance(node.value, ast.Name) and node.value.id == "Account":
            # Only flag if the attr looks like a column reference, not a
            # method/class-level helper. `Account.query`, `Account.metadata`
            # etc. are silently allowed via KNOWN_OK_ATTRS / members.
            self._check_attr(node, base_label="Account")
        # Variable: acct.<attr>  (only when the var is an Account INSTANCE)
        elif isinstance(node.value, ast.Name) and self._is_account_instance(node.value.id):
            self._check_attr(node, base_label=node.value.id)
        # Recurse into nested
        self.generic_visit(node)

    def _check_attr(self, node: ast.Attribute, base_label: str) -> None:
        attr = node.attr
        if attr.startswith("__") and attr.endswith("__"):
            return  # dunders are always OK
        if attr in self.members:
            return
        if attr in KNOWN_OK_ATTRS:
            return
        suggestion = HISTORICAL_SUGGESTIONS.get(attr)
        self.violations.append(
            Violation(
                file_path=self.file_path,
                line=node.lineno,
                col=node.col_offset,
                base=base_label,
                attr=attr,
                suggestion=suggestion,
            )
        )


class Violation:
    __slots__ = ("file_path", "line", "col", "base", "attr", "suggestion")

    def __init__(self, file_path: Path, line: int, col: int, base: str,
                 attr: str, suggestion: str | None):
        self.file_path = file_path
        self.line = line
        self.col = col
        self.base = base
        self.attr = attr
        self.suggestion = suggestion

    def format(self, repo_root: Path) -> str:
        try:
            rel = self.file_path.relative_to(repo_root)
        except ValueError:
            rel = self.file_path
        head = (
            f"audit_account_column_access: violation\n"
            f"  {rel}:{self.line}\n"
            f"    {self.base}.{self.attr}    <- not a column on Account"
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


def _outermost_name(node: ast.expr) -> str | None:
    """For an attribute chain like a.b.c.d, return 'a'."""
    cur: ast.expr = node
    while isinstance(cur, (ast.Attribute, ast.Call, ast.Subscript)):
        if isinstance(cur, ast.Attribute):
            cur = cur.value
        elif isinstance(cur, ast.Call):
            cur = cur.func
        elif isinstance(cur, ast.Subscript):
            cur = cur.value
    if isinstance(cur, ast.Name):
        return cur.id
    return None


SQLALCHEMY_TERMINALS = INSTANCE_TERMINALS | LIST_TERMINALS


def _sqlalchemy_account_chain_shape(node: ast.Call) -> str | None:
    """
    Detect calls of the shape

        db.session.query(Account).<...>.<all|first|one|one_or_none|get|scalar>()

    Returns SHAPE_INSTANCE/SHAPE_LIST/SHAPE_QUERY (the latter when the chain
    ends without a terminal but still pivots through .query(Account)), or
    None when there's no Account in the chain.
    """
    fn = node.func
    if not isinstance(fn, ast.Attribute):
        return None
    terminal = fn.attr
    # Walk inward looking for `.query(Account)`.
    cur: ast.expr = fn.value
    found_account_query = False
    while isinstance(cur, (ast.Attribute, ast.Call, ast.Subscript)):
        if isinstance(cur, ast.Call):
            inner_fn = cur.func
            if (isinstance(inner_fn, ast.Attribute)
                    and inner_fn.attr == "query"
                    and cur.args
                    and isinstance(cur.args[0], ast.Name)
                    and cur.args[0].id == "Account"):
                found_account_query = True
                break
            cur = inner_fn
        elif isinstance(cur, ast.Attribute):
            cur = cur.value
        elif isinstance(cur, ast.Subscript):
            cur = cur.value
    if not found_account_query:
        return None
    if terminal in INSTANCE_TERMINALS:
        return SHAPE_INSTANCE
    if terminal in LIST_TERMINALS:
        return SHAPE_LIST
    return SHAPE_QUERY


def find_account_returning_helpers(tree: ast.Module) -> dict[str, str]:
    """
    Pre-pass: find functions whose return statements yield a statically-
    inferable Account shape. The returned dict maps function name -> SHAPE_*.

    We only inspect direct `Account.query.<...>` or `Account(...)` returns
    (and the `db.session.query(Account)` form). Helpers that delegate to
    other helpers aren't followed -- that's a future enhancement.
    """
    helpers: dict[str, str] = {}

    # Lightweight shape classifier that doesn't need a full visitor scope.
    def shape_of(expr: ast.expr) -> str | None:
        if isinstance(expr, ast.Call):
            fn = expr.func
            if isinstance(fn, ast.Name) and fn.id == "Account":
                return SHAPE_INSTANCE
            if isinstance(fn, ast.Attribute) and _outermost_name(fn) == "Account":
                terminal = fn.attr
                if terminal in INSTANCE_TERMINALS:
                    return SHAPE_INSTANCE
                if terminal in LIST_TERMINALS:
                    return SHAPE_LIST
                return SHAPE_QUERY
            sa = _sqlalchemy_account_chain_shape(expr)
            if sa is not None:
                return sa
        if isinstance(expr, ast.Attribute):
            if _outermost_name(expr) == "Account":
                return SHAPE_QUERY
        return None

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # Look at every Return inside the function body (not into nested defs).
        return_shapes: list[str | None] = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Return) and sub.value is not None:
                return_shapes.append(shape_of(sub.value))
        # Helper qualifies only if every return is the same Account shape.
        non_none = [s for s in return_shapes if s is not None]
        if non_none and len(non_none) == len(return_shapes):
            # All returns yielded a shape; if they're consistent, record it.
            unique = set(non_none)
            if len(unique) == 1:
                helpers[node.name] = unique.pop()
    return helpers


def file_imports_account(tree: ast.Module) -> bool:
    """Cheap check: does the file import the Account model?"""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "Account":
                    return True
        # `from models import Account, Foo` already caught above.
        # `import models` then `models.Account` -- treat as a hit too.
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "models":
                    return True
    # Also accept files that reference Account directly (some files share a
    # module scope via star-import or are themselves submodules with Account
    # already in scope).
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "Account":
            return True
    return False


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def load_baseline(path: Path) -> set[tuple[str, str]]:
    """
    Load a baseline file. Format: one entry per line.

        <relpath>:<base>.<attr>     # comment

    Lines starting with `#` and blank lines are ignored. The line number is
    NOT part of the key -- only file + base.attr -- so renumbering due to
    edits in the file doesn't surface a "new" violation as long as the
    pattern is the same.
    """
    out: set[tuple[str, str]] = set()
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            continue
        relpath, rest = line.split(":", 1)
        if "." not in rest:
            continue
        base, attr = rest.split(".", 1)
        out.add((relpath.strip(), f"{base.strip()}.{attr.strip()}"))
    return out


def violation_baseline_key(v: Violation) -> tuple[str, str]:
    try:
        rel = v.file_path.relative_to(REPO_ROOT)
    except ValueError:
        rel = v.file_path
    return (str(rel), f"{v.base}.{v.attr}")


def audit(verbose: bool = False) -> list[Violation]:
    if not MODELS_FILE.exists():
        raise SystemExit(f"models.py not found at {MODELS_FILE}")
    columns, members = extract_account_attrs(MODELS_FILE)
    if verbose:
        print(f"Account columns ({len(columns)}): {sorted(columns)}")
        print(f"Account members  ({len(members)}): {sorted(members)}")

    files_checked = 0
    files_skipped_parse = 0
    all_violations: list[Violation] = []

    for path in iter_backend_files(BACKEND_ROOT):
        try:
            src = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        try:
            tree = ast.parse(src, filename=str(path))
        except SyntaxError:
            files_skipped_parse += 1
            continue
        files_checked += 1

        imports_account = file_imports_account(tree)
        # Even if it doesn't import Account, we still want to catch literal
        # `Account.<attr>` usages -- but those wouldn't compile without import.
        # So if no import, skip for speed.
        if not imports_account:
            continue

        helpers = find_account_returning_helpers(tree)
        visitor = AccountAttrVisitor(
            columns=columns,
            members=members,
            file_path=path,
            file_imports_account=imports_account,
            account_returning_helpers=helpers,
        )
        visitor.visit(tree)
        all_violations.extend(visitor.violations)

    if verbose:
        print(f"Files checked: {files_checked}")
        print(f"Files skipped (syntax error): {files_skipped_parse}")
        print(f"Violations: {len(all_violations)}")

    return all_violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else "")
    parser.add_argument("--verbose", action="store_true", help="Print scan stats")
    parser.add_argument(
        "--self-test", action="store_true",
        help="Run built-in regression checks (re-introduces historical bugs in "
             "in-memory snippets and asserts the audit flags them).",
    )
    parser.add_argument(
        "--no-baseline", action="store_true",
        help="Ignore the baseline file -- report every violation, including "
             "grandfathered ones. Useful for periodic cleanup sweeps.",
    )
    parser.add_argument(
        "--regenerate-baseline", action="store_true",
        help="Rewrite the baseline file with the current violation set, then "
             "exit 0. Use only after a deliberate review.",
    )
    args = parser.parse_args()

    if args.self_test:
        return _run_self_test()

    violations = audit(verbose=args.verbose)

    if args.regenerate_baseline:
        _write_baseline(BASELINE_FILE, violations)
        print(f"audit_account_column_access: wrote {len(violations)} entries to "
              f"{BASELINE_FILE.relative_to(REPO_ROOT)}")
        return 0

    baseline: set[tuple[str, str]] = set()
    if not args.no_baseline:
        baseline = load_baseline(BASELINE_FILE)

    new_violations = [v for v in violations if violation_baseline_key(v) not in baseline]
    grandfathered = len(violations) - len(new_violations)

    if not new_violations:
        if args.verbose or grandfathered:
            print(f"audit_account_column_access: clean "
                  f"(0 new, {grandfathered} grandfathered)")
        return 0

    print(f"audit_account_column_access: {len(new_violations)} new violation(s) "
          f"({grandfathered} grandfathered via baseline)\n")
    for v in new_violations:
        print(v.format(REPO_ROOT))
        print()
    print(
        "Fix options:\n"
        "  - Add the missing column to Account in models.py (with a migration).\n"
        "  - Read the value from Account.profile_metadata (JSON) if it's a "
        "lifecycle/CRM-style field.\n"
        "  - Move the attribute to its proper model (HealthScore for health, etc.) "
        "and update the call site.\n"
        f"  - If you have reviewed the new entry and consider it intentional, run\n"
        f"      python scripts/audit_account_column_access.py --regenerate-baseline\n"
        f"    to add it to {BASELINE_FILE.name}. Do this sparingly.\n"
    )
    return 1


def _write_baseline(path: Path, violations: list[Violation]) -> None:
    lines = [
        "# audit_account_column_access baseline",
        "# ",
        "# This file grandfathers KNOWN PRE-EXISTING violations so the audit can be",
        "# turned on without first cleaning the entire codebase. EVERY ENTRY HERE IS",
        "# A REAL OR LIKELY BUG. They should be fixed, not whitewashed.",
        "# ",
        "# Format: <relpath>:<base>.<attr>",
        "# Line numbers are intentionally excluded so unrelated edits don't churn",
        "# this file. To regenerate after a deliberate review:",
        "#   python scripts/audit_account_column_access.py --regenerate-baseline",
        "",
    ]
    keys = sorted({violation_baseline_key(v) for v in violations})
    for relpath, attr in keys:
        lines.append(f"{relpath}:{attr}")
    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Self-test: synthesises the historical bugs in-memory and asserts the audit
# catches them.
# ---------------------------------------------------------------------------


def _run_self_test() -> int:
    columns, members = extract_account_attrs(MODELS_FILE)

    cases = [
        (
            "B-1 health_score",
            textwrap.dedent("""
                from models import Account
                def f(customer_id):
                    accounts = Account.query.filter_by(customer_id=customer_id).all()
                    at_risk = sum(1 for a in accounts if float(a.health_score or 100) < 70)
                    return at_risk
            """),
            "health_score",
        ),
        (
            "#23->#28 assigned_csm",
            textwrap.dedent("""
                from models import Account
                def cro_dashboard():
                    for acct in Account.query.all():
                        x = {'assigned_csm': acct.assigned_csm or None}
                    return x
            """),
            "assigned_csm",
        ),
        (
            "Direct Account.health_score reference",
            textwrap.dedent("""
                from models import Account
                from sqlalchemy import desc
                q = Account.query.order_by(desc(Account.health_score)).all()
            """),
            "health_score",
        ),
        (
            "journey_data drift (session 11 memory note)",
            textwrap.dedent("""
                from models import Account
                def g():
                    acct = Account.query.first()
                    return acct.journey_data
            """),
            "journey_data",
        ),
    ]

    passed = 0
    failed: list[str] = []
    for label, source, expected_attr in cases:
        tree = ast.parse(source)
        v = AccountAttrVisitor(
            columns=columns,
            members=members,
            file_path=Path("<self-test>"),
            file_imports_account=True,
        )
        v.visit(tree)
        hit = any(viol.attr == expected_attr for viol in v.violations)
        if hit:
            passed += 1
            print(f"  PASS: {label}  ({expected_attr})")
        else:
            failed.append(label)
            print(f"  FAIL: {label}  (expected violation on .{expected_attr}; "
                  f"got {[viol.attr for viol in v.violations] or 'nothing'})")

    # Negative cases -- known-OK accesses that should NOT be flagged.
    negative_cases = [
        (
            "OK acct.account_id",
            textwrap.dedent("""
                from models import Account
                def h():
                    for acct in Account.query.all():
                        print(acct.account_id, acct.revenue, acct.profile_metadata)
            """),
        ),
        (
            "OK acct.profile_metadata.get(...)",
            textwrap.dedent("""
                from models import Account
                def h():
                    acct = Account.query.first()
                    csm = (acct.profile_metadata or {}).get('assigned_csm')
                    return csm
            """),
        ),
        (
            "OK unrelated variable named acct in a file that doesn't import Account",
            textwrap.dedent("""
                # No Account import. 'acct' here is something else entirely.
                def h(acct):
                    return acct.foo
            """),
        ),
    ]

    for label, source in negative_cases:
        tree = ast.parse(source)
        # For the third case, simulate no-Account-import.
        imports_account = "import Account" in source or "import models" in source
        v = AccountAttrVisitor(
            columns=columns,
            members=members,
            file_path=Path("<self-test>"),
            file_imports_account=imports_account,
        )
        v.visit(tree)
        if v.violations:
            failed.append(label)
            print(f"  FAIL (neg): {label}  (unexpected violation(s): "
                  f"{[viol.attr for viol in v.violations]})")
        else:
            passed += 1
            print(f"  PASS (neg): {label}")

    total = len(cases) + len(negative_cases)
    print(f"\nself-test: {passed}/{total} passed")
    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
