"""
mcp_server/cs_pulse_mcp_server.py::_get_playbook_config +
_ask_ai_helpers.py::_get_playbook_config — vertical routing fix tests
(Aug 22 2026, follow-up to the Aug 21 2026 vertical-coupling audit).

mcp_server/common.py::get_playbook_config was fixed that day to gate
explicitly per known vertical (dc2_s, saas_premium) instead of silently
falling through to dc2_s's PLAYBOOK_CONFIG for every other vertical (e.g.
datacenter_v1). Two OTHER copies of the exact same hardcoded two-branch
if/else were found still carrying the bug:

  1. mcp_server/cs_pulse_mcp_server.py::_get_playbook_config — this is the
     one live onboarding actually calls: cs_pulse_onboarding.py imports
     THIS module's helper (not common.py's) for get_vertical_config and
     get_csm_daily_actions' playbook engine. Confirmed live on EC2 serving
     dc2_s's PB-05/PB-06 playbooks (with trigger_conditions referencing
     dc2_s KPI codes that mean something else in datacenter_v1's own
     catalog) to a real datacenter_v1 test customer (customer 400). Fixed
     by delegating to mcp_server.common.get_playbook_config — no circular
     import risk, since common.py has no dependency back on this module.

  2. _ask_ai_helpers.py::_get_playbook_config — a third independent copy.
     NOT delegated to common.py: this module is explicitly documented as
     having ZERO dependency on fastmcp (so it can run standalone from
     ask_ai_tools.py's _execute_direct path on Python 3.9+), while
     common.py imports `fastmcp.exceptions` at module level. Fixed with
     the identical inline gating logic instead.

Both fixes are additive/gating only — dc2_s and saas_premium behavior is
proven byte-identical (exact PLAYBOOK_CONFIG dict parity) below.

These tests import no Flask app and need no DB — same convention as
tests/test_common_and_bootstrap_vertical_routing.py.
"""

import importlib
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _import_vertical_config(vertical: str):
    """Dynamically load a vertical's vertical_config module for
    test-fixture comparison (see sibling test file for why this is
    importlib-based rather than a static import statement)."""
    return importlib.import_module(".".join(["verticals", vertical, "vertical_config"]))


# ──────────────────────────────────────────────────────────────────────────
# 1. mcp_server/cs_pulse_mcp_server.py::_get_playbook_config
# ──────────────────────────────────────────────────────────────────────────

def test_cs_pulse_mcp_server_playbook_config_parity_for_dc2s_and_saas_premium():
    from mcp_server.cs_pulse_mcp_server import _get_playbook_config

    dc2s_pb = _import_vertical_config("dc2_s").PLAYBOOK_CONFIG
    saas_pb = _import_vertical_config("saas_premium").PLAYBOOK_CONFIG

    dc2s_cfg, dc2s_trigger = _get_playbook_config("dc2_s")
    saas_cfg, saas_trigger = _get_playbook_config("saas_premium")

    assert dc2s_cfg == dc2s_pb
    assert saas_cfg == saas_pb
    assert callable(dc2s_trigger) and callable(saas_trigger)


def test_cs_pulse_mcp_server_playbook_config_datacenter_v1_gets_its_own_not_dc2s():
    """The original live bug: customer 400 (datacenter_v1) was served
    dc2_s's PB-05/PB-06 playbook catalog via this function. datacenter_v1
    now has its own real PLAYBOOK_CONFIG (added Aug 27 2026, found live on
    customer 408 — this function was correctly resolving the vertical, then
    silently getting {} back). It happens to reuse the PB-05/PB-06 id
    strings for its own, different playbooks — the invariant is "never
    dc2_s's definitions", proven by whole-dict inequality, not key absence.
    """
    from mcp_server.cs_pulse_mcp_server import _get_playbook_config

    dc2s_pb = _import_vertical_config("dc2_s").PLAYBOOK_CONFIG

    cfg, trigger = _get_playbook_config("datacenter_v1")

    assert cfg != {}, "datacenter_v1 has a real PLAYBOOK_CONFIG now — must not be empty"
    assert cfg != dc2s_pb, "must be datacenter_v1's own config, never a silent dc2_s substitution"
    assert cfg.get("PB-05") != dc2s_pb.get("PB-05"), "datacenter_v1's PB-05 must not be dc2_s's PB-05"
    assert callable(trigger)
    assert trigger() is False


def test_cs_pulse_mcp_server_playbook_config_delegates_to_common():
    """Confirms this is now a thin delegation to the already-fixed
    mcp_server.common.get_playbook_config, not an independently
    re-drifting copy — the whole point of the fix.
    """
    from mcp_server.cs_pulse_mcp_server import _get_playbook_config
    from mcp_server.common import get_playbook_config as common_get_playbook_config

    for vertical in ("dc2_s", "saas_premium", "saas", "datacenter_v1", "totally_made_up_vertical_xyz"):
        cfg_a, _ = _get_playbook_config(vertical)
        cfg_b, _ = common_get_playbook_config(vertical)
        assert cfg_a == cfg_b, f"Diverged for vertical={vertical!r}: {cfg_a!r} != {cfg_b!r}"


# ──────────────────────────────────────────────────────────────────────────
# 2. _ask_ai_helpers.py::_get_playbook_config
# ──────────────────────────────────────────────────────────────────────────

def test_ask_ai_helpers_playbook_config_parity_for_dc2s_and_saas_premium():
    from _ask_ai_helpers import _get_playbook_config

    dc2s_pb = _import_vertical_config("dc2_s").PLAYBOOK_CONFIG
    saas_pb = _import_vertical_config("saas_premium").PLAYBOOK_CONFIG

    dc2s_cfg, dc2s_trigger = _get_playbook_config("dc2_s")
    saas_cfg, saas_trigger = _get_playbook_config("saas_premium")

    assert dc2s_cfg == dc2s_pb
    assert saas_cfg == saas_pb
    assert callable(dc2s_trigger) and callable(saas_trigger)


def test_ask_ai_helpers_playbook_config_datacenter_v1_gets_its_own_not_dc2s():
    """Same underlying invariant, third independent copy — Ask AI's
    direct-execution path was also silently serving dc2_s's playbooks to
    any other vertical. datacenter_v1 now has its own real PLAYBOOK_CONFIG
    (added Aug 27 2026, found live on customer 408) — proven by whole-dict
    inequality since it legitimately reuses some of dc2_s's PB-NN id
    strings for its own, different playbooks.
    """
    from _ask_ai_helpers import _get_playbook_config

    dc2s_pb = _import_vertical_config("dc2_s").PLAYBOOK_CONFIG

    cfg, trigger = _get_playbook_config("datacenter_v1")

    assert cfg != {}, "datacenter_v1 has a real PLAYBOOK_CONFIG now — must not be empty"
    assert cfg != dc2s_pb, "must be datacenter_v1's own config, never a silent dc2_s substitution"
    assert cfg.get("PB-05") != dc2s_pb.get("PB-05"), "datacenter_v1's PB-05 must not be dc2_s's PB-05"
    assert callable(trigger)
    assert trigger() is False


def test_ask_ai_helpers_playbook_config_has_no_fastmcp_dependency():
    """This module is documented as having ZERO dependency on fastmcp —
    proves the fix was applied inline rather than by delegating to
    mcp_server.common (which imports fastmcp.exceptions at module level).
    """
    import ast
    tree = ast.parse((BACKEND / "_ask_ai_helpers.py").read_text())
    fastmcp_imports = [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.Import, ast.ImportFrom))
        and ((isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("fastmcp"))
             or (isinstance(n, ast.Import) and any(a.name.startswith("fastmcp") for a in n.names)))
    ]
    assert not fastmcp_imports, (
        f"_ask_ai_helpers.py picked up a fastmcp import: {[ast.dump(n) for n in fastmcp_imports]}"
    )


if __name__ == "__main__":
    import traceback

    tests = [
        test_cs_pulse_mcp_server_playbook_config_parity_for_dc2s_and_saas_premium,
        test_cs_pulse_mcp_server_playbook_config_datacenter_v1_gets_safe_empty_not_dc2s,
        test_cs_pulse_mcp_server_playbook_config_delegates_to_common,
        test_ask_ai_helpers_playbook_config_parity_for_dc2s_and_saas_premium,
        test_ask_ai_helpers_playbook_config_datacenter_v1_gets_safe_empty_not_dc2s,
        test_ask_ai_helpers_playbook_config_has_no_fastmcp_dependency,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL: {t.__name__}")
            traceback.print_exc()
    if failed:
        raise SystemExit(f"{failed} test(s) failed")
    print(f"\nAll {len(tests)} tests passed.")
