"""
WS-1.1 regression guard — wizard_a_journey_db's TRIGGERED edge writer
(edge-provenance work, Aug 2026).

The journey builder's arc-detection path wrote ContextEdge rows through a
raw constructor with NO source_platform — 724 NULL-source rows accumulated
Apr–Aug 2026 (an active writer, not migration debris) — and only a
free-text label, bypassing the I1/I2/I4 pre-commit invariant gate that the
sibling path (utils/arc_edge_generator.py) already routes through via
upsert_edge().

These are source-level structural guards (AST), same convention as
test_vertical_catalog_consistency.py — no DB needed, and they can't pass
by accident while a raw constructor still exists in the file.
"""
import ast
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

WIZARD_A_JOURNEY = BACKEND / "wizards" / "wizard_a_journey_db.py"


def _tree():
    return ast.parse(WIZARD_A_JOURNEY.read_text())


def test_no_raw_context_edge_constructor_remains():
    """No `ContextEdge(...)` call anywhere in the journey builder — every
    edge write must route through upsert_edge (the one sanctioned path,
    which enforces source_platform and the invariant gate)."""
    raw_calls = [
        node.lineno for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == 'ContextEdge'
    ]
    assert not raw_calls, (
        f"raw ContextEdge constructor call(s) at line(s) {raw_calls} — "
        f"route through utils.context_graph.upsert_edge instead (WS-1.1)"
    )


def _upsert_edge_calls():
    return [
        node for node in ast.walk(_tree())
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == 'upsert_edge'
    ]


def test_upsert_edge_call_sets_source_platform_and_derivation():
    calls = _upsert_edge_calls()
    assert calls, "expected at least one upsert_edge call in wizard_a_journey_db"
    for call in calls:
        kwargs = {kw.arg: kw.value for kw in call.keywords if kw.arg}
        assert 'source_platform' in kwargs, (
            f"upsert_edge at line {call.lineno} missing source_platform"
        )
        sp = kwargs['source_platform']
        assert isinstance(sp, ast.Constant) and sp.value == 'wizard_a', (
            f"upsert_edge at line {call.lineno}: source_platform must be the "
            f"literal 'wizard_a'"
        )
        props = kwargs.get('properties')
        assert isinstance(props, ast.Dict), (
            f"upsert_edge at line {call.lineno} must pass a literal properties dict"
        )
        prop_keys = {
            k.value for k in props.keys
            if isinstance(k, ast.Constant)
        }
        for required in ('arc_type', 'derivation', 'confidence_semantics'):
            assert required in prop_keys, (
                f"upsert_edge at line {call.lineno}: properties missing "
                f"{required!r} — structured derivation is the point of WS-1.1, "
                f"a bare free-text label was the defect"
            )


def test_confidence_semantics_marks_rule_match_not_epistemic():
    """WS-1.2: the value written into edge confidence originates in
    _classify_trajectory_with_confidence's rule-match scoring (base +
    delta/20, clamped), not an epistemic estimate of the causal claim.
    The properties must say so, so downstream consumers stop reading it
    as calibrated."""
    src = WIZARD_A_JOURNEY.read_text()
    assert "'confidence_semantics': 'trajectory_rule_match_score'" in src


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
