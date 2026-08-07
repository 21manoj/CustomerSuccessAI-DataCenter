# Pilot validation artifact — do not treat as a reference implementation

What a fresh agent built from **only**
[`../04-intelligence-context-graph.md`](../04-intelligence-context-graph.md)
— no access to `models.py`/`taxonomy_loader.py`/`context_graph_invariants.py`/
`arc_classifier.py` — for an invented "regional_utility_v1" vertical
(electric/water co-op CS platform). SQLite-backed graph schema.

Run `python -m pytest test_context_graph.py -q` — 28/28 pass.

See the spec's "Validation Note" for the two real defects this run found:
tiered decay promised in Boundary/Engine but silently absent from the Build
Prompt, and — notably — arc classification left as pure prose, the exact
same defect Module 03 already found and fixed once in this library,
recurring unfixed one module later.
