"""
Regression: get_csm_daily_actions borrowed dc2_s's playbook ROI mapping and
KPI-code hardcode for every non-saas vertical.

Aug 21 2026 vertical-coupling audit, Bug 1 — three coupled locations feeding
the CSM-facing "daily actions" recommendations (mcp_server/cs_pulse_admin.py,
get_csm_daily_actions):

1. mcp_server/cs_pulse_admin.py (~line 481, pre-fix): a saas-only special
   case that always ImportErrored (verticals/saas_premium/api_routes.py
   never defined _get_roi_context et al.) and fell through to dc2_s's
   _get_roi_context/_compute_impact_score/etc for literally every vertical,
   including datacenter_v1/healthcare_provider.
2. mcp_server/cs_pulse_admin.py (~line 633, pre-fix): hardcoded the literal
   KPI code 'P5-KPI7' ("the expansion KPI") for every vertical, even though
   datacenter_v1 calls its equivalent P5-KPI4, saas_premium calls it
   P5-KPI3, and healthcare_provider has no such KPI at all.
3. verticals/dc2_s/api_routes.py's _get_roi_context / _PLAYBOOK_ROI_MAP /
   _ACTION_ROI_MAP: legitimately dc2_s-specific (PB-01..PB-06 → Power-of-1
   metrics) — correct for dc2_s's own Flask blueprint, but wrong when
   borrowed by the fallback above for other verticals. No code change was
   needed here; the fix is in gating who's allowed to import it (item 1).

Fix shape (a deliberately conservative "no fabricated mapping" fallback,
per the audit's explicit instruction not to hand-guess vertical-specific
playbook/KPI semantics): the ROI-context import now checks
`vertical == 'dc2_s'` explicitly and returns a `_no_roi_context` stub
(`roi_context_available: False`) for anything else, and the "expansion KPI"
is resolved by searching the vertical's own KPI catalog for a KPI whose
name contains "expansion" rather than assuming a fixed code.

These are AST-based / source-text checks — no Flask app or DB needed,
mirroring tests/test_vertical_catalog_consistency.py's convention.
"""

import ast
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

ADMIN_PY = BACKEND / "mcp_server" / "cs_pulse_admin.py"


def _get_csm_daily_actions_source() -> str:
    """Extract just the get_csm_daily_actions function body as source text,
    so assertions are scoped to this bug's function and don't accidentally
    match unrelated code elsewhere in the file (e.g. the P5-KPI7 use in a
    different tool at ~line 420, out of scope for this bug)."""
    tree = ast.parse(ADMIN_PY.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "get_csm_daily_actions":
            return ast.get_source_segment(ADMIN_PY.read_text(), node)
    raise AssertionError("get_csm_daily_actions function not found in cs_pulse_admin.py")


def test_get_csm_daily_actions_gates_dc2s_roi_import_on_vertical_check():
    """The dc2_s-specific _get_roi_context must only be imported/used when
    the resolved vertical is actually 'dc2_s' — not as an unconditional
    fallback for every vertical that isn't saas_premium."""
    src = _get_csm_daily_actions_source()

    assert "vertical == 'dc2_s'" in src or 'vertical == "dc2_s"' in src, (
        "get_csm_daily_actions no longer explicitly checks vertical == "
        "'dc2_s' before using dc2_s's _get_roi_context — looks like it "
        "reverted to the unconditional fallback."
    )

    # The old bug pattern: an except (ImportError, AttributeError) clause
    # unconditionally importing dc2_s's _get_roi_context as the catch-all.
    # The fix must instead provide an explicit "not available" fallback for
    # verticals that aren't dc2_s.
    assert "_no_roi_context" in src, (
        "Expected an explicit 'not available' ROI context fallback "
        "(_no_roi_context) for verticals with no verified playbook/KPI "
        "mapping — found none. A missing fallback means the code either "
        "still borrows dc2_s's map or crashes for other verticals."
    )


def test_get_csm_daily_actions_does_not_hardcode_p5_kpi7():
    """The 'expansion KPI' lookup must not be hardcoded to dc2_s's P5-KPI7
    literal — it must resolve per-vertical from the loaded KPI catalog."""
    src = _get_csm_daily_actions_source()

    # Scope the check to actual code (dict .get() calls), not explanatory
    # comments describing the historical bug or the per-vertical codes.
    code_lines = [ln for ln in src.splitlines() if not ln.strip().startswith("#")]
    code_only = "\n".join(code_lines)

    assert "get('P5-KPI7')" not in code_only and 'get("P5-KPI7")' not in code_only, (
        "get_csm_daily_actions still hardcodes the literal KPI code "
        "'P5-KPI7' as 'the expansion KPI' — this is dc2_s's code for that "
        "concept; datacenter_v1 uses P5-KPI4, saas_premium uses P5-KPI3, "
        "and healthcare_provider has no such KPI at all."
    )
    assert "expansion" in src.lower() and "kpi_defs" in src.lower() or "kpi_defs" in src, (
        "Expected the expansion KPI to be resolved dynamically from "
        "KPI_DEFS (the vertical's own catalog), not a fixed string."
    )


def test_no_roi_context_stub_shape():
    """AST-check that _no_roi_context (the honest 'not available' fallback)
    returns a dict with the expected keys and an explicit availability flag
    — this is what a caller (or future dashboard) would branch on instead
    of silently rendering a fabricated dollar figure."""
    src = _get_csm_daily_actions_source()
    tree = ast.parse(src)

    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_no_roi_context":
            found = True
            body_src = ast.dump(node)
            for key in ("roi_metric_id", "roi_projected_impact", "roi_context_available"):
                assert key in body_src, f"_no_roi_context missing expected key {key!r}"
    assert found, "_no_roi_context function not found inside get_csm_daily_actions"


def test_dc2s_still_gets_its_own_roi_context_unconditionally_correct():
    """Sanity: dc2_s tenants must still resolve to the real dc2_s
    _get_roi_context (not the stub) — the fix must not have broken dc2_s
    itself while fixing the leak to other verticals."""
    src = _get_csm_daily_actions_source()
    assert "from verticals.dc2_s.api_routes import _get_roi_context" in src


def test_dc2s_playbook_roi_map_unchanged_and_dc2s_specific():
    """verticals/dc2_s/api_routes.py's _get_roi_context legitimately stays
    dc2_s-specific (PB-01..PB-06) — no code change was needed there since
    the real fix is caller-side gating. This just pins that it still exists
    and is still scoped to dc2_s's own playbook IDs, i.e. nobody 'fixed'
    this by fabricating a fake per-vertical mapping inside it."""
    from verticals.dc2_s.api_routes import _PLAYBOOK_ROI_MAP

    assert set(_PLAYBOOK_ROI_MAP.keys()) == {
        'PB-01', 'PB-02', 'PB-03', 'PB-04', 'PB-05', 'PB-06',
    }
