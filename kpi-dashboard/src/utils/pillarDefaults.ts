/**
 * Pillar Defaults — Vertical-Aware (Frontend)
 *
 * Provides pillar names based on the customer's vertical.
 * SaaS customers see "Product Adoption", DC2_S customers see "Deployment Velocity".
 *
 * Usage:
 *   import { PILLAR_META, getPillarMeta } from 'utils/pillarDefaults';
 *   // Default (DC2_S fallback):
 *   PILLAR_META.P1.name → "Deployment Velocity"
 *   // Vertical-aware:
 *   getPillarMeta('saas_premium').P1.name → "Product Adoption & Usage"
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

/** Pillar display metadata per vertical */
const VERTICAL_PILLAR_META: Record<string, Record<string, { name: string; code: string }>> = {
  dc2_s: {
    P1: { name: 'Deployment Velocity', code: 'DV' },
    P2: { name: 'Operational Stability', code: 'OS' },
    P3: { name: 'AI Workload Performance', code: 'AI' },
    P4: { name: 'Channel & Partner Health', code: 'CH' },
    P5: { name: 'Expansion Readiness', code: 'EX' },
  },
  saas_premium: {
    P1: { name: 'Product Adoption & Usage', code: 'PA' },
    P2: { name: 'Customer Engagement', code: 'CE' },
    P3: { name: 'Customer Sentiment & Support', code: 'CS' },
    P4: { name: 'Partner & Ecosystem Health', code: 'PH' },
    P5: { name: 'Revenue & Growth', code: 'RG' },
  },
  saas: {
    P1: { name: 'Product Adoption & Usage', code: 'PA' },
    P2: { name: 'Customer Engagement', code: 'CE' },
    P3: { name: 'Customer Sentiment & Support', code: 'CS' },
    P4: { name: 'Partner & Ecosystem Health', code: 'PH' },
    P5: { name: 'Revenue & Growth', code: 'RG' },
  },
};

/** Default fallback (DC2_S) */
export const PILLAR_META = VERTICAL_PILLAR_META.dc2_s;

/**
 * Get vertical-aware pillar metadata.
 * Falls back to DC2_S if vertical is unknown.
 *
 * Can also accept pillar_labels from API response (overrides everything).
 */
export function getPillarMeta(
  vertical?: string | null,
  apiPillarLabels?: Record<string, string> | null,
): Record<string, { name: string; code: string }> {
  // If API provided pillar_labels, use those (highest priority)
  if (apiPillarLabels && Object.keys(apiPillarLabels).length > 0) {
    const meta: Record<string, { name: string; code: string }> = {};
    for (const [key, name] of Object.entries(apiPillarLabels)) {
      meta[key] = { name, code: key };
    }
    return meta;
  }

  // Vertical-based lookup
  const v = (vertical || '').toLowerCase().replace(/-/g, '_');
  if (v in VERTICAL_PILLAR_META) {
    return VERTICAL_PILLAR_META[v];
  }
  // Alias matching
  if (['saas', 'saas_premium', 'saas_starter'].some(s => v.includes(s))) {
    return VERTICAL_PILLAR_META.saas_premium;
  }
  if (['dc2_s', 'dc2s', 'dc', 'datacenter'].some(s => v.includes(s))) {
    return VERTICAL_PILLAR_META.dc2_s;
  }

  return VERTICAL_PILLAR_META.dc2_s; // fallback
}

/**
 * Get pillar name by code, vertical-aware.
 */
export function getPillarName(
  pillarCode: string,
  vertical?: string | null,
  apiPillarLabels?: Record<string, string> | null,
): string {
  const meta = getPillarMeta(vertical, apiPillarLabels);
  return meta[pillarCode]?.name || pillarCode;
}
