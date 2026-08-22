"""
Onboarding demo-mode CSV generator directory — vertical-coupling guard test
(Aug 21 2026 vertical-coupling audit, bug B).

complete_onboarding() in onboarding_api_v2_config_aware.py builds the
output directory it hands to the synthetic-data generator (and later
re-reads for account-ID verification) with an f-string. Two call sites
hardcoded the literal suffix '-dc2_s' instead of interpolating the
already-resolved `vertical` local variable — the same variable that IS
correctly used a few lines above at the custom-mode
`get_customer_directory(customer_id, vertical)` call. Net effect: demo-mode
onboarding for any non-dc2_s customer (saas_premium, datacenter_v1,
healthcare_provider) wrote its generated CSVs into
verticals/customer{id}-dc2_s/data instead of
verticals/customer{id}-{vertical}/data — the wrong directory for that
customer's own vertical.

This is a structural/source-level test (AST), not a live-generation test —
mirrors test_vertical_catalog_consistency.py's approach for defects that
live in a specific function body rather than in an importable pure
function.
"""

import ast
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

ONBOARDING_API_PY = BACKEND / "onboarding_api_v2_config_aware.py"


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Could not find function {name!r} in AST.")


def test_complete_onboarding_demo_csv_dir_uses_resolved_vertical_not_dc2s():
    source = ONBOARDING_API_PY.read_text()
    tree = ast.parse(source)
    fn = _find_function(tree, "complete_onboarding")
    fn_source = ast.get_source_segment(source, fn) or ""

    # The specific f-string pattern the generator/verification code builds
    # its data_dir from. A hardcoded '-dc2_s' suffix here silently sends
    # every non-dc2_s customer's synthetic CSVs to the wrong directory.
    hardcoded_pattern = re.compile(r"verticals/customer\{customer_id\}-dc2_s")
    matches = hardcoded_pattern.findall(fn_source)
    assert not matches, (
        "complete_onboarding() hardcodes '-dc2_s' as the demo-mode CSV "
        "generator's directory suffix instead of interpolating the "
        "already-resolved `vertical` variable (the same variable used "
        "correctly a few lines above for custom-mode's "
        "get_customer_directory(customer_id, vertical) call). Non-dc2_s "
        "demo onboarding would write generated CSVs into the wrong "
        "customer's vertical directory."
    )

    # And positively confirm the fixed, vertical-aware form is present at
    # least once (generator invocation) so this test can't pass by
    # accident if the whole data_dir-building block were deleted.
    resolved_pattern = re.compile(r"verticals/customer\{customer_id\}-\{vertical\}")
    assert resolved_pattern.search(fn_source), (
        "complete_onboarding() no longer builds the demo-mode CSV "
        "directory from the resolved `vertical` variable — expected a "
        "pattern like f'verticals/customer{customer_id}-{vertical}/data'."
    )
