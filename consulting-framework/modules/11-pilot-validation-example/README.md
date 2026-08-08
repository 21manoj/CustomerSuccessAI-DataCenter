# Module 11 — Adversarial Validation Worked Example

Artifact of the **spec-only adversarial rebuild** of
[Module 11 — Load-Driver Synthetic Data & Testing](../11-ops-loaddriver-testing.md),
run 2026-08-07. A fresh agent was given ONLY the spec (no origin `load-driver/`
or `kpi-dashboard/` code, no other modules) and asked to build a self-contained
implementation and PROVE any defects with executable tests.

- `impl.py`, `gen_scripts.py` — spec-faithful implementation, including the
  cross-process determinism harness that seeds two subprocesses with different
  `PYTHONHASHSEED`.
- `test_spec.py` — 12 acceptance-criteria tests + 6 defect proofs (each with the
  corrected version passing).

Run:

```bash
python3 -m pytest test_spec.py -q
```

Expected: **18 passed** (Python 3.9, pytest 7.4).

## The six defects this rebuild proved (all fixed in the spec)

The whole cluster shared one root: the module's headline guard was built but
never invoked, and everything it needed was referenced-but-undefined.

1. **HIGH/most severe** — the arc **round-trip guard was dead**: `run_acceptance`
   never called `assert_arc_roundtrip`, so a `silent_churn` scenario that
   mis-classified to `crisis_recovery` passed with `status="success"`. Now the
   harness invokes it per account.
2. **HIGH** — `INTENDED_CANONICAL` (the table the guard indexes) was undefined →
   `KeyError`. Now a named Config table.
3. **HIGH** — `ARC_TEMPLATES`/`CLASSIFICATION_TO_ARC` used as bare globals in the
   harness (defined only as params in piece 2) → `NameError`. Now threaded.
4. **MEDIUM** — trajectory constants (`NOISE_SD`, `DECAY_PER_MONTH`, …) used but
   never assigned → `NameError`. Now pinned defaults.
5. **MEDIUM** — `generate_all` (the subject of the Determinism AC) had no piece
   and no determinism contract. The agent confirmed a natural `hash(kpi_code)`
   stream diverges across `PYTHONHASHSEED` while the single-rng version is
   byte-identical. Now defined as piece 6.
6. **MEDIUM** — the `lifecycle` ARR event was required by Data Shapes/AC but no
   code referenced it; the null-safety AC passed *vacuously*. Now
   `apply_lifecycle` is defined and called, with a positive-case AC.

See the spec's
[Validation Note](../11-ops-loaddriver-testing.md#validation-note) for the full
write-up and the library-level lesson (shapes c/d — referenced-but-undefined and
dead-requirement — account for all six).
