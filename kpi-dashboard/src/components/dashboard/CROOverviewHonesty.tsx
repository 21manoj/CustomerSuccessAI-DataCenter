/**
 * CRO Phases 0–2: metric guide, context-graph strip, pre-proof banner.
 */
import React, { useState } from 'react';
import { ChevronDown, GitBranch, Info } from 'lucide-react';

export type CustomerPhase = 'pre_deploy' | 'onboarding' | 'active' | 'mature';

export interface ContextGraphOutcomeSample {
  node_id: string;
  account_name?: string;
  title?: string;
  occurred_at?: string | null;
}

export interface ContextGraphProvenanceBucket {
  value?: number;
  label?: string;
  sample_nodes: ContextGraphOutcomeSample[];
}

export interface ContextGraphProvenance {
  source: string;
  engine: string;
  outcome_node_count: number;
  revenue_at_risk: ContextGraphProvenanceBucket;
  revenue_protected: ContextGraphProvenanceBucket;
  expansion_pipeline: ContextGraphProvenanceBucket;
}

export interface CROContextGraphRevenue {
  revenue_at_risk: number;
  graph_revenue_protected: number;
  expansion_pipeline: number;
  revenue_risk_label: string;
  provenance: ContextGraphProvenance | null;
}

export interface CROProofData {
  executions_total?: number;
  executions_resolved?: number;
  realized_roi?: number;
  total_cost?: number;
  revenue_protected?: number;
}

function formatCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    const m = value / 1_000_000;
    return `$${m % 1 === 0 ? m.toFixed(0) : m.toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `$${Math.round(value / 1_000)}K`;
  }
  return `$${value.toLocaleString()}`;
}

function expectedProofHint(phase: CustomerPhase): string {
  switch (phase) {
    case 'pre_deploy':
      return 'Expected first attributed saves after playbooks close on at-risk accounts.';
    case 'onboarding':
      return 'Playbook ROI rankings fill in as executions close with attributed $.';
    case 'active':
      return 'Ask AI should cite get_outcome_roi_story when ranking playbook $.';
    default:
      return 'Attributed playbook $ appears in proof data and playbook ROI answers.';
  }
}

export const CROMetricGuideBanner: React.FC = () => {
  const [collapsed, setCollapsed] = useState(true);
  return (
    <div className="mb-4 rounded-lg border border-cyan-900/40 bg-cyan-950/20 px-4 py-2.5">
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between text-left gap-2"
      >
        <span className="text-[10px] font-semibold text-cyan-300/90 uppercase tracking-wide">
          How to read CRO metrics
        </span>
        <ChevronDown
          className={`w-3.5 h-3.5 text-cyan-500 shrink-0 transition-transform ${collapsed ? '' : 'rotate-180'}`}
        />
      </button>
      {!collapsed && (
        <ul className="mt-2 space-y-1.5 text-[10px] text-gray-400 list-disc list-inside leading-relaxed">
          <li>
            <span className="text-gray-300">Risk exposure</span> — context-graph OUTCOME $
            (node-evidenced, not independently verified). Same totals as CFO.
          </li>
          <li>
            <span className="text-gray-300">ARR exposure</span> — health-band ARR in sub-70 accounts;
            not the same as the risk-exposure graph $.
          </li>
          <li>
            <span className="text-gray-300">NRR %</span> — two horizons, not interchangeable:
            <span className="text-gray-300"> Foresight</span> (Predictor v3 forward — “Foresight NRR — Next 12mo”,
            same as CFO) predicts where live accounts are heading;
            <span className="text-gray-300"> Hindsight</span> (Wizard B counterfactual — “Hindsight NRR — TTM”)
            shows what CS Pulse would/did protect on realized outcomes. Plus historical outcomes (Row A on CFO).
          </li>
          <li>
            <span className="text-gray-300">T+30/60/90 trajectory</span> — short-horizon health-trend
            model for playbook timing; not the 12mo forecast.
          </li>
          <li>
            <span className="text-gray-300">Period tabs (Q3 / Q4 / TTM)</span> — filter at-risk $ and
            the account list client-side; protected / expansion stay point-in-time.
          </li>
          <li>
            <span className="text-gray-300">Playbook ROI %</span> — estimated (Power-of-1) until closed
            executions attribute proof $.
          </li>
        </ul>
      )}
      {collapsed && (
        <p className="text-[9px] text-gray-500 mt-1">
          Risk-exposure graph $ ≠ ARR exposure · Foresight NRR = Predictor v3 forward · Hindsight NRR = Wizard B counterfactual (backward) · expand for definitions
        </p>
      )}
    </div>
  );
};

export const CROPreProofBanner: React.FC<{
  phase: CustomerPhase;
  executionsTotal: number;
  realizedRoi: number;
}> = ({ phase, executionsTotal, realizedRoi }) => {
  if (realizedRoi > 0) return null;
  if (executionsTotal === 0) return null;
  return (
    <div className="mb-4 rounded-lg border border-amber-700/40 bg-amber-950/25 px-4 py-3">
      <div className="flex items-start gap-2">
        <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-[11px] text-amber-100/90 leading-relaxed">
          <p className="font-semibold text-amber-200 mb-1">
            Playbook ROI is estimated until attributions close
          </p>
          <p className="text-amber-100/70">
            {executionsTotal} execution{executionsTotal === 1 ? '' : 's'} logged with{' '}
            <span className="text-amber-200/90">$0 attributed</span> revenue so far. Context-graph $
            is in the strip below; playbook rankings in Ask AI use outcome history when
            available.
            <span className="block mt-1 text-[10px] text-amber-100/50">
              Phase: {phase.replace('_', ' ')} · {expectedProofHint(phase)}
            </span>
          </p>
        </div>
      </div>
    </div>
  );
};

type ProvenanceBucketKey = 'revenue_at_risk' | 'revenue_protected' | 'expansion_pipeline';

export const CROContextGraphStrip: React.FC<{
  data: CROContextGraphRevenue;
  onOpenGraph?: () => void;
}> = ({ data, onOpenGraph }) => {
  const prov = data.provenance;
  const nodeCount = prov?.outcome_node_count ?? 0;
  const tiles = [
    {
      label: 'Risk exposure',
      value: data.revenue_at_risk,
      accent: 'text-red-400',
      border: 'border-t-red-500',
    },
    {
      label: 'Customer-reported saves (unverified)',
      value: data.graph_revenue_protected,
      accent: 'text-emerald-400',
      border: 'border-t-emerald-500',
    },
    {
      label: 'Expansion pipeline',
      value: data.expansion_pipeline,
      accent: 'text-cyan-400',
      border: 'border-t-cyan-500',
    },
  ];

  return (
    <div className="bg-[#131826] rounded-xl border border-cyan-800/40 p-5 mb-6">
      <div className="flex items-start justify-between gap-3 mb-4 pb-2 border-b border-gray-700/50">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-cyan-400 shrink-0" />
          <div>
            <h3 className="text-[10px] font-bold text-cyan-300/90 uppercase tracking-[2px]">
              Revenue intelligence (context graph)
            </h3>
            <p className="text-[10px] text-gray-500 mt-0.5">
              {data.revenue_risk_label} · {nodeCount} OUTCOME node{nodeCount === 1 ? '' : 's'} with $
              · same engine as CFO
            </p>
          </div>
        </div>
        {onOpenGraph && (
          <button
            type="button"
            onClick={onOpenGraph}
            className="text-[10px] text-cyan-500 hover:text-cyan-400 font-medium shrink-0"
          >
            Open graph →
          </button>
        )}
      </div>
      <div className="grid grid-cols-3 gap-4">
        {tiles.map((t) => (
          <div
            key={t.label}
            className={`bg-[#1a1f2e] border border-gray-700/50 rounded-lg p-4 border-t-[3px] ${t.border}`}
          >
            <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-1">
              {t.label}
            </p>
            <p className={`text-2xl font-bold ${t.accent}`}>{formatCompact(t.value)}</p>
          </div>
        ))}
      </div>
      <p className="text-[9px] text-gray-600 mt-3">
        Top-row revenue cards may also show ARR exposure (health-based). Period tabs re-anchor
        at-risk history; protected / expansion stay point-in-time.
      </p>
    </div>
  );
};
