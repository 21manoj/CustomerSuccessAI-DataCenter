/**
 * DC2_S Pillar Defaults — Single Source of Truth (Frontend)
 *
 * Canonical weights live in backend: verticals/dc2_s/kpi_definitions.py
 * Frontend loads from API at runtime; these are offline fallbacks only.
 *
 * P1(DV)=0.15  P2(OS)=0.20  P3(AI)=0.25  P4(CH)=0.15  P5(EX)=0.25
 */

export interface PillarWeights {
  AI: number;
  CH: number;
  DV: number;
  EX: number;
  OS: number;
}

/** Default L2 pillar weights (matches kpi_definitions.py DC2S_PILLARS) */
export const DEFAULT_PILLAR_WEIGHTS: PillarWeights = {
  AI: 0.25,  // P3 — AI Workload Performance
  CH: 0.15,  // P4 — Channel & Partner Health
  DV: 0.15,  // P1 — Deployment Velocity
  EX: 0.25,  // P5 — Expansion Readiness
  OS: 0.20,  // P2 — Operational Stability
};

/** Pillar display metadata */
export const PILLAR_META: Record<string, { name: string; code: string }> = {
  P1: { name: 'Deployment Velocity', code: 'DV' },
  P2: { name: 'Operational Stability', code: 'OS' },
  P3: { name: 'AI Workload Performance', code: 'AI' },
  P4: { name: 'Channel & Partner Health', code: 'CH' },
  P5: { name: 'Expansion Readiness', code: 'EX' },
};
