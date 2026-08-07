# Pilot validation artifact — do not treat as a reference implementation

What a fresh agent built from **only**
[`../05-intelligence-wizards.md`](../05-intelligence-wizards.md) — no access
to `cs_pulse_onboarding.py`, `models.py`, or `wizards/*`. SQLite-backed with
explicit `BEGIN IMMEDIATE`/`COMMIT`/`ROLLBACK` so the atomicity guarantees
are enforced by a real database rather than simulated.

Run `python -m pytest test_wizard_orchestration.py -q` — 63/63 pass.

**This is the most valuable artifact in the library so far.** Many of its
tests are executable *proofs that the original spec was wrong* — e.g.
`test_literal_writer_leaves_two_active_rows_for_platform_scope`,
`test_data_shapes_unique_constraint_makes_scope_isolation_impossible`,
`test_literal_dispatcher_accepts_a_blank_trigger_source`. Each one runs the
spec's original literal pseudocode and demonstrates the failure, then the
corrected version. Read those tests alongside the spec's Validation Note:
this run found all four of the library's documented failure shapes in a
single module.
