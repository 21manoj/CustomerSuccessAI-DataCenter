/**
 * Provenance Tier Badge — visual indicator for a numeric value's basis.
 *
 * Five tiers (matches backend utils/value_provenance.py's vocabulary:
 * tag(), calibration_tier(), most_conservative()):
 *   measured     — computed from this tenant's own data. No badge by
 *                  default; this is the trustworthy baseline, same
 *                  "unmarked = real" convention as ProvenanceBadge's
 *                  'observed' tier for context-graph nodes.
 *   derived      — computed FROM measured values (a model, a rollup, a
 *                  counterfactual) — real signal, one step removed.
 *   benchmark    — an industry/platform constant, not this tenant's data.
 *                  The tier most worth marking loudly: it's what get_kpi_catalog
 *                  and the CFO dashboard's Po1 metrics served as if it were
 *                  this customer's own number before the Aug 21 2026 audit.
 *   default      — a config fallback, not computed from anything at all.
 *   unavailable  — could not be computed. Never render a fabricated 0 for
 *                  this tier — render '—' and this badge instead (see the
 *                  roi_scaling all-zeros bug, Aug 22 2026: a genuinely
 *                  missing value rendered as a real computed zero).
 *
 * Distinct from ProvenanceBadge (same directory): that component covers a
 * different, 3-tier vocabulary (observed/inferred/synthetic) for
 * ContextNode/ContextEdge graph provenance. Same visual grammar
 * (pill / border / optional icon / hover title), different domain — do not
 * merge them, the vocabularies mean different things.
 */

import React from 'react';

export type ProvenanceTier = 'measured' | 'derived' | 'benchmark' | 'default' | 'unavailable';

interface ProvenanceTierBadgeProps {
  tier: ProvenanceTier | undefined | null;
  /** Extra detail shown on hover, in addition to the tier's own label.
   * The label itself must always be legible without hovering — this is
   * supplementary (e.g. CFODashboard's system-of-record disclosure
   * sentences), never required to understand the tier. */
  detail?: string;
  /** When true, renders the badge for 'measured' too (default: hide —
   * unmarked is the point). */
  showMeasured?: boolean;
  /** Compact mode — smaller padding/text. */
  compact?: boolean;
  /** Dark-background variant, for hero banners on dark gradients (e.g.
   * ROIEngineView's header) where the light-mode bg-*-50 tokens would be
   * invisible. */
  dark?: boolean;
  className?: string;
}

const LIGHT_CONFIG: Record<ProvenanceTier, { label: string; defaultDetail: string; bg: string; text: string; border: string }> = {
  measured: {
    label: 'Measured',
    defaultDetail: "Computed from this tenant's own data",
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
  },
  derived: {
    label: 'Derived',
    defaultDetail: 'Computed from measured values — a model, rollup, or counterfactual',
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    border: 'border-slate-300',
  },
  benchmark: {
    label: 'Benchmark',
    defaultDetail: "Industry/platform constant — not this tenant's data",
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-300',
  },
  default: {
    label: 'Default',
    defaultDetail: 'Config fallback — not computed from anything',
    bg: 'bg-slate-100',
    text: 'text-slate-600',
    border: 'border-slate-300',
  },
  unavailable: {
    label: 'Unavailable',
    defaultDetail: 'Could not be computed',
    bg: 'bg-red-50',
    text: 'text-red-700',
    border: 'border-red-200',
  },
};

const DARK_CONFIG: Record<ProvenanceTier, { label: string; defaultDetail: string; classes: string }> = {
  measured: { ...LIGHT_CONFIG.measured, classes: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' },
  derived: { ...LIGHT_CONFIG.derived, classes: 'border-slate-400/30 bg-slate-400/10 text-slate-300' },
  benchmark: { ...LIGHT_CONFIG.benchmark, classes: 'border-amber-500/30 bg-amber-500/10 text-amber-400' },
  default: { ...LIGHT_CONFIG.default, classes: 'border-slate-400/30 bg-slate-400/10 text-slate-400' },
  unavailable: { ...LIGHT_CONFIG.unavailable, classes: 'border-red-500/30 bg-red-500/10 text-red-400' },
};

const ProvenanceTierBadge: React.FC<ProvenanceTierBadgeProps> = ({
  tier,
  detail,
  showMeasured = false,
  compact = false,
  dark = false,
  className = '',
}) => {
  if (!tier) return null;
  if (tier === 'measured' && !showMeasured) return null;

  const padding = compact ? 'px-1.5 py-0.5' : 'px-2 py-0.5';
  const fontSize = compact ? 'text-[10px]' : 'text-xs';

  if (dark) {
    const cfg = DARK_CONFIG[tier];
    if (!cfg) return null;
    return (
      <span
        title={detail || cfg.defaultDetail}
        data-provenance-tier={tier}
        className={`inline-flex items-center gap-1 ${padding} ${fontSize} font-medium rounded-full border ${cfg.classes} ${className}`}
      >
        {cfg.label}
      </span>
    );
  }

  const cfg = LIGHT_CONFIG[tier];
  if (!cfg) return null;
  return (
    <span
      title={detail || cfg.defaultDetail}
      data-provenance-tier={tier}
      className={`inline-flex items-center gap-1 ${padding} ${fontSize} font-medium rounded ${cfg.bg} ${cfg.text} border ${cfg.border} ${className}`}
    >
      {cfg.label}
    </span>
  );
};

export default ProvenanceTierBadge;
