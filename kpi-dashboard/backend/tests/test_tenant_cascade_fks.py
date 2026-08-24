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


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
