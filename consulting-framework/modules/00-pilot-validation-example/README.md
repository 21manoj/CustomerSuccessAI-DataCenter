# Module 00 — Adversarial Validation Worked Example

Artifact of the **spec-only adversarial rebuild** of
[Module 00 — Integration & Bootstrap](../00-foundation-integration-bootstrap.md),
run 2026-08-07. A fresh agent was given ONLY the spec (no origin `kpi-dashboard/`
code, no other modules) and asked to build a self-contained implementation and
PROVE any defects with executable tests.

- `impl.py` — spec-faithful implementation using **real SQLAlchemy + sqlite** (so
  the schema-drift check runs against an actual database), with fakes for the
  `module01…09` hooks.
- `test_spec.py` — 9 acceptance-criteria tests + 2 defect proofs (each with the
  corrected version passing) + a rule-out test + idempotency.

Run:

```bash
python3 -m pytest test_spec.py -q
```

Expected: **14 passed** (Python 3.9, pytest 7.4; requires SQLAlchemy).

## The two defects this rebuild proved (both HIGH, both fixed in the spec)

1. **Schema-drift check ignored UNIQUE constraints** — it compared only FKs, so a
   DB missing an ORM-declared `UNIQUE` booted silently (the cross-tenant-collision
   case Gotcha 1 names). The module's *headline* guarantee was half-false. Fixed
   by comparing unique constraints alongside FKs. (The agent also ruled out a
   suspected FK name-munging no-op — the FK half genuinely works.)
2. **The feature-toggle system was orphaned** — `process_data` never called
   `is_enabled`, so the whole toggle manager was dead code and the "disabled
   module still boots" AC was unsatisfiable. Fixed with a `STAGE_TOGGLE` mapping
   and toggle gates in the sequencer.

The rest of the chassis — the FK drift guard, the three single-source resolvers,
the stage-order invariant, `scores_written` as a real int, wizards A/B-inline /
C/D-absent, centralized `classify` — all held under attack. See the spec's
[Validation Note](../00-foundation-integration-bootstrap.md#validation-note).
