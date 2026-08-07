"""
Fixture for the Gotcha-2 regression test: this legacy module DOES exist
(the vertical is real), but its own import statement is broken -- simulating
a renamed/never-existed dependency, exactly the shape of the live bug
Gotcha 2 documents (`cannot import name 'get_catalog' from
'utils.vertical_registry'`). catalog_loader.py's Tier 2 fallback must not
mistake this for "vertical does not exist" (Tier 3) -- it must fail loudly
instead of silently reporting "Unknown vertical: legacy_internally_broken_v1".
"""

from this_module_does_not_exist_anywhere import something_broken  # noqa: F401

PILLARS = {"P1": {"name": "Unreachable", "weight_l2": 1.0}}
KPIS = {}
