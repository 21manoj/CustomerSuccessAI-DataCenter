"""
Playbook close-linker abstention + residue marker (WS-2 review, 2026-08-24).

The close path used to write two heuristic edges per playbook close: the
account's most recent DECISION -> outcome as RESULTED_IN at a typed
confidence=1.0, and the 3 most recent prior SIGNALs -> outcome as LED_TO
at a typed 0.7. Both were adjudicated `inferred` (matrix cells 12/13);
neither is a logged causal fact. Per the reviewer's direction the writer
now ABSTAINS — stopping accumulation is one branch; a half-fix (NULLing
confidence without stamping evidence_tier) reproduces the second-order
trap this codebase keeps hitting.

Two guards here:
  1. Static (always runs): _write_context_graph_outcome constructs NO
     edges — abstention can't be quietly reverted.
  2. Residue marker (DB-gated, xfail(strict=True) — same convention as
     item 22): zero typed-0.7 playbook_execution edges on live tenants.
     115 exist as of 2026-08-24. Flips green when WS-2 2c re-tiers or the
     tenants regenerate; errors loudly if it passes unexpectedly — which
     also catches someone quietly running the UPDATE instead of 2c.
"""
import ast
import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

LIFECYCLE = BACKEND / "utils" / "playbook_lifecycle.py"


def _function_node(name):
    tree = ast.parse(LIFECYCLE.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found")


def test_close_linker_writes_no_edges():
    """No ContextEdge constructor and no upsert_edge call anywhere in
    _write_context_graph_outcome — the abstention is the fix; reinstating
    linkage belongs to WS-2 2c's EdgeFactory, not here."""
    fn = _function_node("_write_context_graph_outcome")
    offenders = [
        n.lineno for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id in ("ContextEdge", "upsert_edge")
    ]
    assert not offenders, (
        f"edge construction reappeared in _write_context_graph_outcome at "
        f"line(s) {offenders} — the close-linker must abstain until WS-2 2c "
        f"(see module docstring)"
    )


def test_typed_confidence_literals_gone_from_close_path():
    """The two typed constants themselves (1.0 RESULTED_IN / 0.7 LED_TO)
    must not exist as confidence= keywords on an edge-construction call in
    this file's close path.

    Scoped to ContextEdge/upsert_edge/add_edge calls specifically (same
    functions test_close_linker_writes_no_edges checks), not every call in
    the function — WS-2 2f's playbook-close OUTCOME-node clamp fix
    (2026-08-27) legitimately passes confidence=1.0 into
    clamp_unearned_confidence() as the node's pre-clamp starting value,
    which is an unrelated, correct usage this test must not flag.
    """
    fn = _function_node("_write_context_graph_outcome")
    typed = [
        (n.lineno, kw.value.value)
        for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id in ("ContextEdge", "upsert_edge", "add_edge")
        for kw in getattr(n, "keywords", [])
        if kw.arg == "confidence" and isinstance(kw.value, ast.Constant)
    ]
    assert not typed, f"typed confidence constants back in an edge-construction call: {typed}"


def _db_url():
    return os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")


@pytest.mark.skipif(not _db_url(), reason="no DATABASE_URL — residue marker runs where a DB exists")
@pytest.mark.xfail(
    reason="open residue (WS-2 review hold 4, option c): 115 playbook_execution "
           "LED_TO edges with the typed confidence=0.7 remain on live tenants as "
           "of 2026-08-24. They re-tier when WS-2 2c ships (or the demo tenants "
           "regenerate). strict=True so an unexpected pass — including someone "
           "quietly UPDATE-ing them — errors loudly instead of vanishing.",
    strict=True,
)
def test_no_typed_07_playbook_edges_on_live_tenants():
    import sqlalchemy as sa

    engine = sa.create_engine(_db_url())
    with engine.connect() as conn:
        total_pb_edges = conn.execute(sa.text("""
            SELECT COUNT(*) FROM context_edges
            WHERE source_platform = 'playbook_execution' AND edge_type = 'LED_TO'
        """)).scalar()
        if total_pb_edges == 0:
            # This DB has no playbook_execution LED_TO edges at all — the
            # residue class doesn't exist here (e.g. a fresh local dev DB).
            # The marker is about the LIVE residue; skipping keeps the
            # strict xfail meaningful where it applies.
            pytest.skip("no playbook_execution LED_TO edges in this DB — residue marker not applicable")
        n = conn.execute(sa.text("""
            SELECT COUNT(*) FROM context_edges e
            JOIN customers c ON c.customer_id = e.customer_id
            WHERE e.source_platform = 'playbook_execution'
              AND e.edge_type = 'LED_TO'
              AND e.confidence = 0.7
        """)).scalar()
    assert n == 0, f"{n} typed-0.7 playbook_execution LED_TO edges remain on live tenants"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
