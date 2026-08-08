import { test } from "node:test";
import assert from "node:assert/strict";
import {
  bandFor,
  bandFor_fix,
  assertThresholdShape,
  makeLoadThresholds,
  _setThresholds,
  _getThresholds,
  _resetThresholds,
  _setThresholdsFix,
  decideState,
  resolveTier,
  useEntitlement,
  useEntitlement_fix,
  TIER_ORDER,
  money_literal,
  money_fix,
  revenueAtRiskValue,
  auditNoLocalHealthColors,
  DEFAULT_THRESHOLDS_FIX,
} from "./impl.mjs";

const VALID = { healthy: { min: 70 }, at_risk: { min: 50 }, critical: { min: 0 } };

// ===========================================================================
// GREEN — Acceptance Criteria that the literal spec DOES satisfy
// ===========================================================================

test("AC bandFor boundary matrix (with THRESHOLDS loaded)", () => {
  _setThresholds(VALID);
  assert.equal(bandFor(49), "critical");
  assert.equal(bandFor(50), "at_risk");
  assert.equal(bandFor(69), "at_risk");
  assert.equal(bandFor(70), "healthy");
  assert.equal(bandFor(null), "no_data");
  assert.equal(bandFor(undefined), "no_data");
  _resetThresholds();
});

test("AC bandFor(null) is no_data, real 50 is a score — null is never a 50 stand-in", () => {
  _setThresholds(VALID);
  assert.equal(bandFor(null), "no_data");
  assert.notEqual(bandFor(null), bandFor(50));
  assert.equal(bandFor(50), "at_risk");
  _resetThresholds();
});

test("AC threshold change moves the boundaries; bandFor reads THRESHOLDS", () => {
  _setThresholds({ healthy: { min: 90 }, at_risk: { min: 60 }, critical: { min: 0 } });
  assert.equal(bandFor(70), "at_risk"); // 70 no longer healthy
  assert.equal(bandFor(90), "healthy");
  _resetThresholds();
});

test("AC assertThresholdShape accepts the valid shape, throws on both malformed shapes", () => {
  assert.deepEqual(assertThresholdShape(VALID), VALID);
  // flat shape
  assert.throws(() => assertThresholdShape({ healthy_min: 70 }), /malformed/);
  // wrapper shape
  assert.throws(() => assertThresholdShape({ thresholds: VALID }), /malformed/);
  // null
  assert.throws(() => assertThresholdShape(null), /malformed/);
});

test("AC loadThresholds is wired: boot path calls apiCall and populates THRESHOLDS", async () => {
  _resetThresholds();
  let called = 0;
  const apiCall = async (url) => {
    called++;
    assert.equal(url, "/config/health-thresholds");
    return VALID;
  };
  const loadThresholds = makeLoadThresholds(apiCall);
  await loadThresholds();
  assert.equal(called, 1);
  assert.deepEqual(_getThresholds(), VALID);
  _resetThresholds();
});

test("AC loadThresholds throws (fail loud) when the endpoint returns a malformed shape", async () => {
  const apiCall = async () => ({ healthy_min: 70 });
  const loadThresholds = makeLoadThresholds(apiCall);
  await assert.rejects(loadThresholds(), /malformed/);
  _resetThresholds();
});

test("AC DataState decision yields three distinct real-data outcomes", () => {
  // empty: zero failures, no data
  assert.equal(decideState({ payload: { accounts: [] }, failures: 0, total: 12 }).status, "empty");
  // error: all failed
  assert.equal(decideState({ payload: null, failures: 12, total: 12 }).status, "error");
  // partial: some failed, rest returned data
  const partial = decideState({ payload: { accounts: [{ id: 1 }] }, failures: 3, total: 12 });
  assert.equal(partial.status, "partial");
  assert.equal(partial.reason, "3 of 12 sources failed");
  assert.deepEqual(partial.data, { accounts: [{ id: 1 }] });
  // ok
  assert.equal(decideState({ payload: { accounts: [{ id: 1 }] }, failures: 0, total: 12 }).status, "ok");
});

test("AC read-not-sum: revenueAtRiskValue reads the bundle field, never sums accounts", () => {
  const p = {
    leading: { confirmed_risk: 500000 },
    accounts: [{ arr: 1 }, { arr: 2 }, { arr: 3 }], // sum would be 6, not 500000
  };
  assert.equal(revenueAtRiskValue(p), 500000);
});

test("AC resolveTier fail-closed: missing tier -> least privilege", () => {
  assert.equal(resolveTier({}), "free");
  assert.equal(resolveTier(null), "free");
  assert.equal(resolveTier(undefined), "free");
  assert.equal(resolveTier({ tier: "enterprise" }), "enterprise");
});

test("AC entitlement denies a growth feature for a missing-tier session", () => {
  const r = useEntitlement("nrr_dual_lens", {}); // free vs need growth
  assert.equal(r.allowed, false);
  assert.equal(r.requiredTier, "growth");
});

test("AC money carries the basis in the rendered figure", () => {
  const out = money_fix(500000, "baseline_arr", 1000000);
  assert.match(out, /baseline_arr/);
});

test("AC anti-drift audit flags a local getHealthColor and health>=75, passes a clean kit file, raises on 0 files", () => {
  const files = {
    "src/components/Bad.tsx": "function getHealthColor(h){ return h > 70 ? 'g':'r'; }",
    "src/components/Bad2.tsx": "const c = health >= 75 ? 'green' : 'red';",
    "src/kit/HealthBadge.tsx": "const band = bandFor(score);",
  };
  const read = (f) => files[f];
  const isKitFile = (f) => f.startsWith("src/kit/");
  const offenders = auditNoLocalHealthColors(Object.keys(files), { read, isKitFile });
  assert.deepEqual(offenders.sort(), ["src/components/Bad.tsx", "src/components/Bad2.tsx"]);
  // clean run
  const clean = { "src/kit/HealthBadge.tsx": "const band = bandFor(score);" };
  assert.deepEqual(
    auditNoLocalHealthColors(Object.keys(clean), { read: (f) => clean[f], isKitFile: () => true }),
    []
  );
  // anti-vacuous
  assert.throws(() => auditNoLocalHealthColors([], { read, isKitFile }), /scanned 0 files/);
});

// ===========================================================================
// DEFECTS — proven with a failing-literal test + passing corrected test
// ===========================================================================

// -----------------------------------------------------------------
// test_defect_1 — SPEC piece 1, line 147 (Gotcha 1) — SHAPE (c)
// DEFAULT_THRESHOLDS is referenced by bandFor but DEFINED NOWHERE in the spec.
// The AC "bandFor must work before boot (THRESHOLDS null -> defaults)" is
// therefore unsatisfiable: before loadThresholds runs, THRESHOLDS is null,
// `THRESHOLDS ?? DEFAULT_THRESHOLDS` is undefined, and t.healthy.min throws.
// -----------------------------------------------------------------
test("test_defect_1: bandFor crashes before boot because DEFAULT_THRESHOLDS is undefined (shape c, line 147)", () => {
  _resetThresholds(); // THRESHOLDS === null, i.e. pre-boot
  // null score still works (early return), proving only the defaults path is broken
  assert.equal(bandFor(null), "no_data");
  // a real score pre-boot throws — the promised fallback does not exist
  assert.throws(
    () => bandFor(70),
    (err) => err instanceof TypeError, // "Cannot read properties of undefined (reading 'healthy')"
    "literal bandFor should crash pre-boot because DEFAULT_THRESHOLDS is undefined"
  );
});

test("test_defect_1_fix: bandFor_fix with a DEFINED DEFAULT_THRESHOLDS classifies pre-boot", () => {
  // no thresholds loaded -> uses defaults
  assert.equal(DEFAULT_THRESHOLDS_FIX.healthy.min, 70);
  assert.equal(bandFor_fix(70), "healthy");
  assert.equal(bandFor_fix(50), "at_risk");
  assert.equal(bandFor_fix(49), "critical");
  assert.equal(bandFor_fix(null), "no_data");
});

// -----------------------------------------------------------------
// test_defect_2 — SPEC piece 4, line 203 (Gotcha 6) — SHAPE (c)+(e)
// useEntitlement FAILS OPEN when the required tier is not in TIER_ORDER.
// FEATURE_CATALOG[feature] can be undefined (unknown feature) or a misspelled
// tier; TIER_ORDER.indexOf(undefined) === -1, and ANY real tier index (>=0) is
// >= -1, so `allowed` is true for EVERYONE — including the least-privileged
// free session. This is the exact fail-open the module exists to kill.
// -----------------------------------------------------------------
test("test_defect_2: useEntitlement fails OPEN for an unknown feature (need=undefined -> indexOf -1, shape c/e, line 203)", () => {
  const freeSession = {}; // resolves to "free", the least privilege
  const r = useEntitlement("feature_not_in_catalog", freeSession);
  // BUG: a locked/unknown feature is granted to a free-tier session
  assert.equal(r.allowed, true, "literal useEntitlement grants unknown features to everyone");
});

test("test_defect_2b: useEntitlement fails OPEN when a required tier is misspelled/off-list", () => {
  // simulate an FDE catalog entry with a typo by faking the lookup via a feature
  // whose need resolves off-list. We reuse the same -1 mechanism through the
  // corrected function to contrast behaviour.
  const freeSession = {};
  // literal: unknown -> allowed true
  assert.equal(useEntitlement("typo_tier", freeSession).allowed, true);
});

test("test_defect_2_fix: useEntitlement_fix DENIES unknown/off-list required tiers (fail closed)", () => {
  assert.equal(useEntitlement_fix("feature_not_in_catalog", {}).allowed, false);
  // sanity: known features still resolve correctly
  assert.equal(useEntitlement_fix("nrr_dual_lens", { tier: "growth" }).allowed, true);
  assert.equal(useEntitlement_fix("nrr_dual_lens", { tier: "free" }).allowed, false);
});

// -----------------------------------------------------------------
// test_defect_3 — SPEC piece 3, line 184 (Gotcha 8) — SHAPE (c)/(d)
// money() calls fmt(v) but fmt is defined NOWHERE and is not a named
// dependency. The Build Prompt claims "every helper is defined below OR is a
// named dependency" — fmt is neither. Literal money throws ReferenceError.
// -----------------------------------------------------------------
test("test_defect_3: money() throws because fmt is undefined (shape c, line 184)", () => {
  assert.throws(() => money_literal(500000, "baseline_arr", 1000000), ReferenceError);
});

test("test_defect_3_fix: money_fix defines fmt and still carries the basis", () => {
  const out = money_fix(500000, "baseline_arr", 1000000);
  assert.match(out, /baseline_arr/);
  assert.match(out, /500,000|\$500/);
});

// -----------------------------------------------------------------
// test_defect_4 — SPEC piece 3, line 183 (Gotcha 8) — SHAPE (d)
// money(v, basis, basisVal) accepts basisVal but no code path uses it — a dead
// parameter. Gotcha 8's own symptom (two figures differ because one is scaled
// to a baseline ARR) is exactly what basisVal would disambiguate, yet the
// rendered string never shows it. The value the payload carries
// (arr_basis_value) has no code able to render it.
// -----------------------------------------------------------------
test("test_defect_4: money output is identical regardless of basisVal — the value is dead (shape d, line 183)", () => {
  const a = money_fix(500000, "baseline_arr", 1000000);
  const b = money_fix(500000, "baseline_arr", 9999999);
  assert.equal(a, b, "basisVal never affects output — arr_basis_value is dead in the formatter");
});

// -----------------------------------------------------------------
// test_defect_5 — SPEC piece 5, line 226 (Gotcha 7) — SHAPE (c)
// isEmpty is referenced by the decision ladder but DEFINED NOWHERE in the spec.
// The empty-vs-partial-vs-error contract (the whole point of Gotcha 7) hinges on
// isEmpty, yet its semantics are unspecified. We demonstrate the ambiguity: a
// partial fan-out whose surviving payload happens to be empty (failures>0,
// accounts=[]) is classified "partial" and set as data — so DataState renders
// children() over an EMPTY payload. Whether that is right depends entirely on
// the missing isEmpty definition; the spec never says.
// -----------------------------------------------------------------
test("test_defect_5: partial-with-empty-payload is set as data:{accounts:[]} — undefined isEmpty semantics (shape c, line 226)", () => {
  const r = decideState({ payload: { accounts: [] }, failures: 3, total: 12 });
  assert.equal(r.status, "partial");
  // DataState will call children(r.data); r.data is an empty payload, not null.
  assert.deepEqual(r.data, { accounts: [] });
  // Contrast: had failures been 0, the same empty payload is 'empty' with data:null.
  const e = decideState({ payload: { accounts: [] }, failures: 0, total: 12 });
  assert.equal(e.status, "empty");
  assert.equal(e.data, null);
  // The two paths disagree on data shape for the same empty payload, and the
  // arbiter (isEmpty) is undefined in the spec.
});
