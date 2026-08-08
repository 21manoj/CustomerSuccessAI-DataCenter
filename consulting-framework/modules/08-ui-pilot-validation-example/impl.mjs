// impl.mjs — literal port of SPEC.md Build Prompt pure-logic pieces,
// plus CORRECTED versions. Literal = exactly what the spec pseudocode says,
// including its undefined helpers, so tests can prove the failures.

// ---------------------------------------------------------------------------
// PIECE 1 — tokens, assertThresholdShape, loadThresholds, bandFor
// ---------------------------------------------------------------------------

export const BAND_TOKENS = {
  healthy: "var(--band-healthy)",
  at_risk: "var(--band-at-risk)",
  critical: "var(--band-critical)",
  no_data: "var(--band-no-data)",
};

// Literal, line 135-140
export function assertThresholdShape(t) {
  const ok =
    t &&
    ["healthy", "at_risk", "critical"].every(
      (k) => typeof t?.[k]?.min === "number"
    );
  if (!ok) throw new Error("malformed thresholds — refusing to classify");
  return t;
}

// Module-level THRESHOLDS, line 141
let THRESHOLDS = null;

// SPEC line 147 references DEFAULT_THRESHOLDS but the spec NEVER defines it.
// To reproduce the literal behaviour we declare it undefined (as a real module
// that simply named an unresolved symbol would blow up at reference time; the
// closest faithful JS reproduction is an undefined binding).
let DEFAULT_THRESHOLDS; // === undefined  (referenced-but-undefined, shape c)

// Literal loadThresholds, line 142-144. apiCall injected for the mock.
export function makeLoadThresholds(apiCall) {
  return async function loadThresholds() {
    THRESHOLDS = assertThresholdShape(await apiCall("/config/health-thresholds"));
  };
}

// Literal bandFor, line 145-151
export function bandFor(score) {
  if (score === null || score === undefined) return "no_data";
  const t = THRESHOLDS ?? DEFAULT_THRESHOLDS; // <-- undefined before boot
  if (score >= t.healthy.min) return "healthy";
  if (score >= t.at_risk.min) return "at_risk";
  return "critical";
}

// test helpers to drive module state
export function _setThresholds(t) {
  THRESHOLDS = t;
}
export function _getThresholds() {
  return THRESHOLDS;
}
export function _resetThresholds() {
  THRESHOLDS = null;
}

// ---------------------------------------------------------------------------
// PIECE 5 — usePersonaDashboard DataState decision, extracted to decideState
// Literal port of the if/else ladder, lines 223-229.
// ---------------------------------------------------------------------------

// isEmpty is referenced (line 226) but NEVER defined in the spec (shape c).
// Most-natural reading: a payload is empty when it has no accounts / is falsy.
function isEmpty_literal(payload) {
  // The spec gives no body. We fill the most natural reading and note it.
  if (!payload) return true;
  if (Array.isArray(payload.accounts)) return payload.accounts.length === 0;
  return false;
}

export function decideState({ payload, failures, total }) {
  const isEmpty = isEmpty_literal(payload);
  if (failures === total)
    return { status: "error", data: null, degraded: true, reason: "all sources failed" };
  else if (isEmpty && failures === 0)
    return { status: "empty", data: null, degraded: true, reason: null };
  else if (failures > 0)
    return {
      status: "partial",
      data: payload,
      degraded: true,
      reason: `${failures} of ${total} sources failed`,
    };
  else return { status: "ok", data: payload, degraded: false, reason: null };
}

// ---------------------------------------------------------------------------
// PIECE 4 — resolveTier / useEntitlement (literal, lines 196-205)
// ---------------------------------------------------------------------------

export const TIER_ORDER = ["free", "starter", "growth", "enterprise"];

// FEATURE_CATALOG referenced (line 202) but NEVER defined in the spec (shape c).
// Config says "the feature/entitlement catalog" is FDE-filled, but the Engine
// still needs a binding. We supply a plausible one so useEntitlement can run.
export const FEATURE_CATALOG = {
  nrr_dual_lens: "growth",
  revenue_at_risk: "starter",
};

export function resolveTier(session) {
  return session?.tier ?? TIER_ORDER[0];
}

// Literal useEntitlement — session & feature injected (no React hooks here).
export function useEntitlement(feature, session) {
  const tier = resolveTier(session);
  const need = FEATURE_CATALOG[feature];
  return {
    allowed: TIER_ORDER.indexOf(tier) >= TIER_ORDER.indexOf(need),
    requiredTier: need,
  };
}

// ---------------------------------------------------------------------------
// PIECE 3 — money + RevenueAtRiskPanel data read (literal, lines 182-184)
// ---------------------------------------------------------------------------

// fmt referenced (line 184) but NEVER defined in the spec (shape c/d).
// Not a named dependency either. Literal port leaves it undefined.
export function money_literal(v, basis, basisVal) {
  // eslint-disable-next-line no-undef
  return `${fmt(v)} · ${basis}`; // fmt is undefined -> ReferenceError
}

// The pure "read-not-sum" data function behind RevenueAtRiskPanel.
export function revenueAtRiskValue(p) {
  return p.leading.confirmed_risk; // reads bundle field; never sums accounts
}

// ---------------------------------------------------------------------------
// PIECE 6 — auditNoLocalHealthColors (literal, lines 241-251)
// ---------------------------------------------------------------------------

// read() and isKitFile() referenced but NOT defined in spec (shape c).
// Inject a file-reader and kit-detector so the pure logic can run.
export function auditNoLocalHealthColors(srcFiles, { read, isKitFile }) {
  if (srcFiles.length === 0) throw new Error("scanned 0 files — broken audit");
  const offenders = [];
  for (const f of srcFiles) {
    const s = read(f);
    if (
      /function\s+getHealth(Color|Status)/.test(s) ||
      /health\w*\s*[<>]=?\s*(70|75|80|50)\b/.test(s)
    )
      if (!isKitFile(f)) offenders.push(f);
  }
  return offenders;
}

// ===========================================================================
// CORRECTED versions (what the SPEC should say)
// ===========================================================================

export const DEFAULT_THRESHOLDS_FIX = {
  healthy: { min: 70 },
  at_risk: { min: 50 },
  critical: { min: 0 },
};

let THRESHOLDS_FIX = null;
export function _setThresholdsFix(t) {
  THRESHOLDS_FIX = t;
}
export function _resetThresholdsFix() {
  THRESHOLDS_FIX = null;
}
export function bandFor_fix(score) {
  if (score === null || score === undefined) return "no_data";
  const t = THRESHOLDS_FIX ?? DEFAULT_THRESHOLDS_FIX;
  if (score >= t.healthy.min) return "healthy";
  if (score >= t.at_risk.min) return "at_risk";
  return "critical";
}

export function money_fix(v, basis, basisVal) {
  const fmt = (n) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(n);
  return `${fmt(v)} · ${basis}`;
}

// Corrected entitlement: unknown/off-list required tier -> fail CLOSED (deny).
export function useEntitlement_fix(feature, session) {
  const tier = resolveTier(session);
  const need = FEATURE_CATALOG[feature];
  const needIdx = TIER_ORDER.indexOf(need);
  if (needIdx === -1) {
    // unknown feature/tier: deny, do not fall open
    return { allowed: false, requiredTier: need ?? null };
  }
  return {
    allowed: TIER_ORDER.indexOf(tier) >= needIdx,
    requiredTier: need,
  };
}
