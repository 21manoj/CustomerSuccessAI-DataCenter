# Module 10 — Adversarial Validation Worked Example

Artifact of the **spec-only adversarial rebuild** of
[Module 10 — Governance & Audit Layer](../10-ops-governance-audit.md), run
2026-08-07. A fresh agent was given ONLY the spec (no origin `kpi-dashboard/`
code, no other modules) and asked to build a self-contained implementation and
PROVE any defects with executable tests.

- `impl.py` — spec-faithful implementation using **real `ast`** (so the drift
  parser and coverage sweeps run for real), with every undefined helper filled in
  its most-natural reading (marked `# [FILLED]`).
- `test_spec.py` — 11 acceptance-coverage tests + 8 defect proofs (each with the
  corrected version passing).

Run:

```bash
python3 -m pytest test_spec.py -q
```

Expected: **19 passed** (Python 3.9, pytest 7.4).

## The seven defects this rebuild proved (all fixed in the spec)

The good news the rebuild confirmed: **all six anti-vacuous floors were genuinely
in code** — the lesson from Modules 00/11 held. The defects were elsewhere:

1. **HIGH/most severe** — `response_keys` dropped the `return jsonify(variable)`
   shape, so the drift auditor's own key parser reproduced the exact Gotcha-1
   blind spot it exists to close. Fixed with a recursive dispatcher.
2. The invariant `checker` had two contradictory signatures across call sites →
   `TypeError`. Unified to `checker(session, candidate=None)`.
3–4. Two checks the Boundary/AC promised (dead-but-dangerous cross-tenant shape;
   audit-trail writer coverage) had **no Build-Prompt piece** — added as pieces
   6 and 7.
5. Model gate `KeyError` on an out-of-range tier — the ungoverned-model detector
   crashed by an ungoverned model. Guarded.
6. `known_limitations` declared as dicts but read as attributes → `AttributeError`.
   Data Shapes now declares objects.
7. Nine AST sub-helpers were referenced-but-undefined (the mechanism by which #1
   recurred) — the load-bearing ones are now defined, the rest named with
   contracts.

See the spec's
[Validation Note](../10-ops-governance-audit.md#validation-note) — including the
capstone observation: the defect was in the *governance check's own parser*,
reproducing the bug it was written to catch.
