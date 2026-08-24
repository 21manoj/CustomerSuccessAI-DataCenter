"""
Evidence Density / derivation-vocabulary contract (WS-2 matrix Hold 1,
signed 2026-08-24).

Cell 14 (playbook_auto_trigger x TRIGGERED) was signed `observed` under two
conditions that are binding on whoever builds the metric, whenever that
happens:

  1. `derivation` distinguishes system.self (the platform reacting to its
     own inference — auto-triggers) from system.external (a genuinely
     external logged fact — SoR sync, recorded trigger conditions).
  2. Evidence Density's observed-denominator counts system.external ONLY.
     Otherwise the metric climbs every time more auto-triggers ship —
     gaming itself by construction.

Per the reviewer: "recorded in a doc, they'll be honoured until the first
person who wasn't in this conversation touches the metric. A test is the
version that survives." Neither WS-2 2c's EdgeFactory nor WS-3's Evidence
Density exists yet, so these guards are CONDITIONAL: they skip while the
module is absent and bind the moment it appears under its conventional
name. Building the metric elsewhere without these exports IS the
violation — if you're renaming the module, move this test with it.

Conventional homes (first match wins):
  Evidence Density -> utils/evidence_density.py
  EdgeFactory      -> utils/edge_factory.py
"""
import importlib
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _try_import(module_name):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def test_evidence_density_excludes_system_self():
    mod = _try_import("utils.evidence_density")
    if mod is None:
        pytest.skip(
            "utils/evidence_density.py not built yet (WS-3) — this guard "
            "binds the moment it exists"
        )
    excludes = getattr(mod, "OBSERVED_DENOMINATOR_EXCLUDES", None)
    assert excludes is not None, (
        "utils.evidence_density must export OBSERVED_DENOMINATOR_EXCLUDES — "
        "the Hold-1 condition (metric counts system.external observed only) "
        "must be data the tests can see, not prose"
    )
    assert any(str(e).startswith("system.self") for e in excludes), (
        f"OBSERVED_DENOMINATOR_EXCLUDES={excludes!r} does not exclude "
        f"system.self — auto-trigger edges would inflate Evidence Density "
        f"by construction (WS-2 matrix Hold 1)"
    )


def test_edge_factory_auto_trigger_derivation_is_system_self():
    mod = _try_import("utils.edge_factory")
    if mod is None:
        pytest.skip(
            "utils/edge_factory.py not built yet (WS-2 2c) — this guard "
            "binds the moment it exists"
        )
    # The factory must expose the derivation it stamps on auto-trigger
    # edges, and it must live under the system.self namespace.
    deriv = getattr(mod, "AUTO_TRIGGER_DERIVATION", None)
    assert deriv is not None, (
        "utils.edge_factory must export AUTO_TRIGGER_DERIVATION (the "
        "derivation string stamped on playbook_auto_trigger edges)"
    )
    assert str(deriv).startswith("system.self"), (
        f"AUTO_TRIGGER_DERIVATION={deriv!r} must be under 'system.self' — "
        f"cell 14's `observed` was signed only with the self/external split "
        f"(WS-2 matrix Hold 1)"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
