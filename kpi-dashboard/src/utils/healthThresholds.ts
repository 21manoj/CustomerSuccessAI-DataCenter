/**
 * Centralized health score thresholds.
 *
 * Single source of truth for healthy / at-risk / critical boundaries.
 * Fetches config from /api/dc2s/config/health-thresholds (backed by
 * backend/config/health_thresholds.json). Settings UI can PUT to update.
 *
 * Usage:
 *   import { getThresholds, classify, classifyColor } from '../utils/healthThresholds';
 *   const t = await getThresholds();          // { healthy: { min: 70, ... }, ... }
 *   classify(75)     // 'healthy'
 *   classifyColor(40) // '#dc2626'
 */

export interface ThresholdTier {
  min: number;
  label: string;
  color: string;
  hex: string;
  bg_class: string;
  text_class: string;
}

export interface HealthThresholds {
  healthy: ThresholdTier;
  at_risk: ThresholdTier;
  critical: ThresholdTier;
}

// Defaults (used before API response arrives or as fallback)
const DEFAULTS: HealthThresholds = {
  healthy:  { min: 70, label: 'Healthy',  color: 'green',  hex: '#16a34a', bg_class: 'bg-green-100',  text_class: 'text-green-800' },
  at_risk:  { min: 50, label: 'At Risk',  color: 'yellow', hex: '#ca8a04', bg_class: 'bg-yellow-100', text_class: 'text-yellow-800' },
  critical: { min: 0,  label: 'Critical', color: 'red',    hex: '#dc2626', bg_class: 'bg-red-100',    text_class: 'text-red-800' },
};

let cached: HealthThresholds | null = null;

/**
 * Fetch thresholds from backend (cached after first call).
 * Falls back to DEFAULTS on network error.
 */
export async function getThresholds(): Promise<HealthThresholds> {
  if (cached) return cached;
  try {
    const res = await fetch('/api/dc2s/config/health-thresholds');
    if (res.ok) {
      cached = await res.json();
      return cached!;
    }
  } catch {
    // network error — use defaults
  }
  cached = DEFAULTS;
  return cached;
}

/** Synchronous access (returns cached or defaults). Call getThresholds() first in app init. */
export function getThresholdsSync(): HealthThresholds {
  return cached || DEFAULTS;
}

/** Force re-fetch from backend (call after Settings UI saves). */
export async function reloadThresholds(): Promise<HealthThresholds> {
  cached = null;
  return getThresholds();
}

/** Classify a score: 'healthy' | 'at_risk' | 'critical' */
export function classify(score: number): 'healthy' | 'at_risk' | 'critical' {
  const t = getThresholdsSync();
  if (score >= t.healthy.min) return 'healthy';
  if (score >= t.at_risk.min) return 'at_risk';
  return 'critical';
}

/** Return the display label for a score. */
export function classifyLabel(score: number): string {
  return getThresholdsSync()[classify(score)].label;
}

/** Return the hex color for a score. */
export function classifyColor(score: number): string {
  return getThresholdsSync()[classify(score)].hex;
}

/** Return Tailwind bg class for a score. */
export function classifyBgClass(score: number): string {
  return getThresholdsSync()[classify(score)].bg_class;
}

/** Return Tailwind text class for a score. */
export function classifyTextClass(score: number): string {
  return getThresholdsSync()[classify(score)].text_class;
}

/** Return combined bg + text Tailwind classes for a score. */
export function classifyBadgeClass(score: number): string {
  const tier = getThresholdsSync()[classify(score)];
  return `${tier.bg_class} ${tier.text_class}`;
}

/** Return { healthy_min, at_risk_min } for use in comparisons. */
export function thresholdValues(): { healthy_min: number; at_risk_min: number } {
  const t = getThresholdsSync();
  return { healthy_min: t.healthy.min, at_risk_min: t.at_risk.min };
}
