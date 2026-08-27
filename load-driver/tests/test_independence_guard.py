"""AT-5 — THE INDEPENDENCE GUARD (fix-load-generator-prompt-v2.md).

"The generator must not import, read, parse, or derive from ARC_TEMPLATES,
and world files must not be authored from it... If the generated world is
'the templates plus noise,' discovery recovering the templates proves
nothing. These tests are what keep the harness capable of failing."

Two structural checks:
  1. No file under eval_profile/ imports utils.arc_edge_generator or
     references the name ARC_TEMPLATES.
  2. No world JSON file contains an arc-name string lifted from
     ARC_TEMPLATES's own keys (crisis_recovery, exec_sponsor_change, ...).
     A world DECLARING a disagreement WITH a template by name in prose
     (template_disagreements[].template, a human-readable citation) is fine
     and expected — see world_b.json; what's forbidden is the world's own
     causal vocabulary (observed_vocabulary, dag edge types) reusing a
     template's arc-name as if it were an event type.
"""
import ast
import json
import sys
from pathlib import Path

LOAD_DRIVER = Path(__file__).resolve().parent.parent
EVAL_PROFILE = LOAD_DRIVER / 'eval_profile'
BACKEND = LOAD_DRIVER.parent / 'kpi-dashboard' / 'backend'


def _arc_template_names() -> list:
    src = (BACKEND / 'utils' / 'arc_edge_generator.py').read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and getattr(node.target, 'id', None) == 'ARC_TEMPLATES':
            if isinstance(node.value, ast.Dict):
                return [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
    raise AssertionError("could not locate ARC_TEMPLATES in utils/arc_edge_generator.py — "
                          "guard can't run without a real reference list")


def test_arc_templates_actually_has_entries():
    # Sanity check on the extraction itself — if this drops to 0 the guard
    # below would trivially "pass" for the wrong reason.
    names = _arc_template_names()
    assert len(names) >= 5, names


def test_no_eval_profile_module_imports_arc_edge_generator():
    offenders = []
    for py_file in EVAL_PROFILE.rglob('*.py'):
        src = py_file.read_text()
        tree = ast.parse(src, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if 'arc_edge_generator' in alias.name:
                        offenders.append((py_file, alias.name))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ''
                if 'arc_edge_generator' in mod:
                    offenders.append((py_file, mod))
    assert not offenders, f"eval_profile imports arc_edge_generator: {offenders}"


def test_no_eval_profile_module_references_arc_templates_name():
    offenders = []
    for py_file in EVAL_PROFILE.rglob('*.py'):
        tree = ast.parse(py_file.read_text(), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == 'ARC_TEMPLATES':
                offenders.append(str(py_file))
    assert not offenders, f"eval_profile references ARC_TEMPLATES by name: {offenders}"


def test_no_world_file_uses_a_template_name_as_vocabulary():
    """A world's observed_vocabulary / dag edge types / account_archetypes
    must never literally BE one of ARC_TEMPLATES's arc names — that would be
    the world importing the template's identity through its data instead of
    its code, the same violation via a different door."""
    template_names = set(_arc_template_names())
    offenders = []
    for world_file in (EVAL_PROFILE / 'worlds').glob('*/*.json'):
        world = json.loads(world_file.read_text())
        vocab = set(world['observed_vocabulary'].get('signal_types', []))
        outcome_types = world['observed_vocabulary'].get('outcome_types', [])
        vocab |= set(outcome_types.keys()) if isinstance(outcome_types, dict) else set(outcome_types)
        vocab |= {a['archetype_id'] for a in world.get('account_archetypes', [])}
        vocab |= {e['edge_id'] for e in world.get('dag', [])}
        hit = vocab & template_names
        if hit:
            offenders.append((world_file.name, hit))
    assert not offenders, f"world file vocabulary collides with ARC_TEMPLATES names: {offenders}"


def test_at_least_one_world_per_covered_vertical_disagrees_with_templates():
    """'At least one world per vertical MUST contradict ARC_TEMPLATES.'
    Checked per vertical directory that actually has world files today —
    doesn't block on verticals with zero worlds yet (that's the world-count
    scale-out, a separate follow-on, not this guard's job)."""
    worlds_by_vertical = {}
    for world_file in (EVAL_PROFILE / 'worlds').glob('*/*.json'):
        world = json.loads(world_file.read_text())
        worlds_by_vertical.setdefault(world['vertical'], []).append(world)

    assert worlds_by_vertical, "no world files found at all"
    for vertical, worlds in worlds_by_vertical.items():
        has_disagreement = any(w.get('template_disagreements') for w in worlds)
        assert has_disagreement, (
            f"vertical {vertical!r} has {len(worlds)} world(s), none declare "
            f"template_disagreements — AT-1 needs at least one per vertical"
        )


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
