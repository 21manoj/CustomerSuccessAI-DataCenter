# Module 08-UI — Adversarial Validation Worked Example

Artifact of the **spec-only adversarial rebuild** of
[Module 08-UI — Component Kit & UX Patterns](../08-ui-component-kit.md), run
2026-08-07. A fresh agent was given ONLY the spec (no origin `kpi-dashboard/`
code, no other modules) and asked to build the pure-logic contracts and PROVE any
defects with executable tests.

**Scope note:** this is a React component-kit spec, but per the spec's Validation
Note the testable core is **pure logic** — `bandFor`, `assertThresholdShape`, the
DataState decision, entitlement resolution, `money`, the anti-drift audit,
read-not-sum. React rendering fidelity is out of scope. So the worked example is
plain JS tested with Node's built-in runner, not React/JSX.

- `impl.mjs` — the pure-logic functions rebuilt from the spec.
- `test.mjs` — `node:test` tests: 13 acceptance-criteria + 5 defect proofs + 3
  corrected-version tests.

Run (needs Node ≥ 18; validated on Node v22):

```bash
node --test
```

Expected: **21 pass, 0 fail**.

## The five defects this rebuild proved (all fixed in the spec)

Dominated — as the last four modules were — by shape (c), *referenced-but-undefined*:

1. **HIGH/most severe** — `useEntitlement` failed **open**: an unknown feature →
   `TIER_ORDER.indexOf(undefined) === -1`, and `0 >= -1` grants everyone,
   including the least-privileged tier. The guard did the opposite of its
   fail-closed purpose. Fixed: `indexOf(need) === -1` now denies; `FEATURE_CATALOG`
   defined.
2. **HIGH** — `bandFor` referenced an undefined `DEFAULT_THRESHOLDS`, so it
   crashed before `loadThresholds` ran. Fixed: default defined (70/50/0).
3. `money` called an undefined `fmt` → `ReferenceError`. Fixed.
4. `money`'s `basisVal` was captured but never rendered (dead value — the thing
   Gotcha 8 says disambiguates figures). Fixed: it's now rendered.
5. The DataState hook's `isEmpty` was undefined and the partial-vs-empty ordering
   was ambiguous. Fixed.

See the spec's
[Validation Note](../08-ui-component-kit.md#validation-note) for the full write-up,
including the honest limit: the React-rendering acceptance claims rest on these
now-proven pure-logic contracts plus a visual review this process cannot perform.
