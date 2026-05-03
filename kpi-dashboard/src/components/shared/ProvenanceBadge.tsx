/**
 * Provenance Badge — visual indicator for ContextNode/ContextEdge.source.
 *
 * Three states (matches backend utils/provenance.py vocabulary):
 *   observed   — customer-asserted (CSV / SoR sync). No badge by default;
 *                this is the trustworthy baseline.
 *   inferred   — runtime detection over real signals (LLM Tier-1,
 *                signal_analyst). Soft "AI-inferred" pill.
 *   synthetic  — arc-template fabrication (Wizard A). Loud
 *                "model-generated" badge so users don't mistake narrative
 *                scaffolding for asserted facts.
 */

import React from 'react';
import { Sparkles, Bot } from 'lucide-react';
import type { ProvenanceSource } from '../../types/contextGraph';

interface ProvenanceBadgeProps {
  source: ProvenanceSource | undefined | null;
  /** When true, renders the badge for observed nodes too (default: hide). */
  showObserved?: boolean;
  /** Compact mode — icon-only, smaller padding. */
  compact?: boolean;
  className?: string;
}

const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({
  source,
  showObserved = false,
  compact = false,
  className = '',
}) => {
  if (!source) return null;
  if (source === 'observed' && !showObserved) return null;

  const config = {
    observed: {
      label: 'Observed',
      title: 'From customer-uploaded data (CSV / SoR sync)',
      icon: null,
      bg: 'bg-emerald-50',
      text: 'text-emerald-700',
      border: 'border-emerald-200',
    },
    inferred: {
      label: 'AI-inferred',
      title: 'Detected at runtime from real customer signals (LLM Tier-1, signal analyst)',
      icon: <Bot className="w-3 h-3" />,
      bg: 'bg-blue-50',
      text: 'text-blue-700',
      border: 'border-blue-200',
    },
    synthetic: {
      label: 'Model-generated',
      title: 'Generated from an arc template (Wizard A) — narrative scaffolding, not asserted by the customer',
      icon: <Sparkles className="w-3 h-3" />,
      bg: 'bg-amber-50',
      text: 'text-amber-700',
      border: 'border-amber-200',
    },
  }[source];

  if (!config) return null;

  const padding = compact ? 'px-1.5 py-0.5' : 'px-2 py-0.5';
  const fontSize = compact ? 'text-[10px]' : 'text-xs';

  return (
    <span
      title={config.title}
      data-provenance={source}
      className={`inline-flex items-center gap-1 ${padding} ${fontSize} font-medium rounded ${config.bg} ${config.text} border ${config.border} ${className}`}
    >
      {config.icon}
      {!compact && config.label}
    </span>
  );
};

export default ProvenanceBadge;
