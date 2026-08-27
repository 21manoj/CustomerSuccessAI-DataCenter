"""Eval-profile generator (Track D, fix-load-generator-prompt-v2.md).

Deliberately separate from `scenarios/scenario_manifest.py` — the demo-profile
generator that provisions every existing customer/demo. AT-0 requires demo
behaviour to be provably unchanged; the cleanest way to guarantee that is for
eval-profile code to never import from, or be imported by, the demo path.

INDEPENDENCE GUARD (see tests/test_independence_guard.py, AT-5): nothing under
this package may import `utils.arc_edge_generator` or reference
`ARC_TEMPLATES` — worlds are authored data, never derived from the template
library discovery is being scored against.
"""
