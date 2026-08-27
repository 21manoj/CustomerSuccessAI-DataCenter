"""
Tenant-deletion cascade FKs — guard tests (2026-08-24).

Root cause of the orphan cleanup that removed 60% of context_edges:
customer deletion never cascaded (context_nodes/context_edges.customer_id
had NO FK on the live DB despite models.py declaring one — the tables
predate the declaration and create_all never ALTERs). The fix is
migrations/add_tenant_cascade_fks.py: DB-level ON DELETE CASCADE, the
only control that governs every deletion path including ad-hoc raw-SQL
scripts.

These are structural guards (no DB): the migration must exist, stay wired
into app startup, keep its fail-safe properties (skip-on-violations, never
silently delete), and stay idempotent by construction. Live functional
proof (scratch tenant + raw DELETE -> zero residue) was run against both
local and EC2 Postgres on 2026-08-24.
"""
import ast
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

MIGRATION = BACKEND / "migrations" / "add_tenant_cascade_fks.py"
APP = BACKEND / "app_v3_minimal.py"


def test_migration_exists_and_compiles():
    assert MIGRATION.is_file()
    ast.parse(MIGRATION.read_text())


def test_migration_is_wired_into_app_startup():
    src = APP.read_text()
    assert "from migrations.add_tenant_cascade_fks import run_migration" in src, (
        "app_v3_minimal.py must run the tenant-cascade migration at startup — "
        "removing it silently reintroduces the orphan-accumulation bug"
    )


def test_core_cascades_cover_the_orphan_source_tables():
    """The four constraints that caused the actual 2026-08-24 orphan pile
    must stay in the CORE list (the dynamic sweep is best-effort; these are
    mandatory)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("add_tenant_cascade_fks", MIGRATION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    core = {(t, c) for t, c, _, _ in mod.CORE_CASCADES}
    for required in [
        ("accounts", "customer_id"),
        ("context_nodes", "customer_id"),
        ("context_nodes", "account_id"),
        ("context_edges", "customer_id"),
    ]:
        assert required in core, f"{required} missing from CORE_CASCADES"


def test_migration_never_deletes_data():
    """The migration adds constraints; it must never clean violating rows
    itself (skip-and-report is the contract — silent cleanup here would be
    exactly the class of quiet data mutation this project bans)."""
    tree = ast.parse(MIGRATION.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            sql = node.value.strip().upper()
            assert not sql.startswith("DELETE"), (
                f"migration contains a DELETE statement: {node.value[:60]!r}"
            )
            assert not sql.startswith("TRUNCATE"), "migration contains TRUNCATE"


def test_non_postgres_is_a_noop():
    src = MIGRATION.read_text()
    assert "dialect.name != 'postgresql'" in src, (
        "migration must no-op on non-Postgres dialects (local sqlite test runs)"
    )


def test_customer_relationships_use_passive_deletes():
    """The DB-level ON DELETE CASCADE this migration adds is only half the
    fix — SQLAlchemy's ORM-level session.delete(customer) has its own,
    independent cascade behavior for any relationship() it manages, and by
    default (no passive_deletes) it tries to NULL each child's FK itself
    before the DB cascade ever runs. For a NOT NULL FK (activity_logs,
    query_audits, customer_workflow_configs all are), that crashes with
    IntegrityError — worked around with raw SQL DELETE every time this
    session instead of fixing the actual mismatch (2026-08-27).

    Setting passive_deletes=True only on the child->Customer side is NOT
    enough and still crashed on live retest: a plain string
    backref='activity_logs' auto-creates a SEPARATE mirrored relationship
    (Customer.activity_logs) with its own default config, and
    session.delete(customer) walks cascades from the Customer side — i.e.
    through that auto-created mirror, not through the side passive_deletes
    was set on. The fix needs db.backref('activity_logs',
    passive_deletes=True), which sets the flag on BOTH sides. This test
    checks both: the outer relationship() call AND, if backref= is present,
    that it's a db.backref(...) call (not a bare string) carrying its own
    passive_deletes=True.

    Every db.relationship('Customer', ...) in models.py must pass this. New
    ones must too, or they silently reintroduce the same crash."""
    src = (BACKEND / "models.py").read_text()
    tree = ast.parse(src)
    missing = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == 'relationship'):
            continue
        args_str = [a.value for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if 'Customer' not in args_str:
            continue

        kw_by_name = {kw.arg: kw.value for kw in node.keywords}
        problems = []
        if 'passive_deletes' not in kw_by_name:
            problems.append('outer relationship() missing passive_deletes=True')

        backref_val = kw_by_name.get('backref')
        if backref_val is None:
            pass  # no backref at all — nothing on the Customer side to check
        elif isinstance(backref_val, ast.Constant):
            problems.append(
                f"backref={backref_val.value!r} is a plain string — must be "
                f"db.backref({backref_val.value!r}, passive_deletes=True) or "
                f"the auto-created Customer-side mirror won't get the flag"
            )
        elif isinstance(backref_val, ast.Call):
            backref_kw_names = {kw.arg for kw in backref_val.keywords}
            if 'passive_deletes' not in backref_kw_names:
                problems.append('db.backref(...) call missing passive_deletes=True')

        if problems:
            missing.append((node.lineno, problems))

    assert not missing, (
        f"db.relationship('Customer', ...) not fully passive_deletes-safe "
        f"(line, problems): {missing}"
    )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
