# Module 08 — Adversarial Validation Worked Example

Artifact of the **spec-only adversarial rebuild** of
[Module 08 — Persona Dashboards](../08-interface-persona-dashboards.md),
run 2026-08-07. A fresh agent was given ONLY the spec (no origin `kpi-dashboard/`
code, no other modules) and asked to build a self-contained implementation and
PROVE any defects with executable tests.

- `impl.py` — spec-faithful implementation: fake `Account`, fake Module
  01/03/04/05 hooks, and two reconstructed Module 07 `envelope()` variants (one
  with a `persona` param, one without) to test the contract both ways.
- `test_spec.py` — 12 acceptance-criteria tests + 5 defect/guard proofs.

Run:

```bash
python3 -m pytest test_spec.py -q
```

Expected: **17 passed** (Python 3.9, pytest 7.4).

## The two defects this rebuild proved (both fixed in the spec)

1. **HIGH** — `build_dashboard` called `envelope(..., persona=...)`, but Module
   07's shipped `envelope(scope, payload, arr_basis=, arr_basis_value=)` has no
   `persona` param → `TypeError` on every dashboard. Fixed by carrying `persona`
   inside `payload` (no change to the shipped Module 07).
2. **MEDIUM** — `account_arr` used `if arr:`, so an explicit
   `profile_metadata={"arr": 0}` fell through to the revenue column and the
   account escaped its `n_zero_arr` count (reintroducing Gotcha 8 via the
   accessor). Fixed with `if arr is not None:`.

The spec's hardest invariants — churned exclusion, zero-ARR weighting,
None-vs-`50.0`, leading/trailing signal independence, cross-persona parity — all
held under proof. See the spec's
[Validation Note](../08-interface-persona-dashboards.md#validation-note) for the
full write-up.
