/**
 * VPCS Phases 0–2: metric guide, context-graph strip, pre-proof banner.
 */
import React, { useState } from 'react';
import { ChevronDown, GitBranch, Info } from 'lucide-react';

export type CustomerPhase = 'pre_deploy' | 'onboarding' | 'active' | 'mature';

export interface VPCSContextGraphRevenue {
  revenue_at_risk: number;
  graph_revenue_protected: number;
  expansion_pipeline: number;
  revenue_risk_label: string;
}

export interface VPCSProofData {
  executions_total?: number;
  realized_roi?: number;
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

export const VPCSMetricGuideBanner: React.FC = () => {
  const [collapsed, setCollapsed] = useState(true);
  return (
    <div className="mb-4 rounded-lg border border-teal-900/40 bg-teal-950/20 px-4 py-2.5">
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between text-left gap-2"
      >
        <span className="text-[10px] font-semibold text-teal-300/90 uppercase tracking-wide">
          How to read VP CS metrics
        </span>
        <ChevronDown
          className={`w-3.5 h-3.5 text-teal-500 shrink-0 transition-transform ${collapsed ? '' : 'rotate-180'}`}
        />
      </button>
      {!collapsed && (
        <ul className="mt-2 space-y-1.5 text-[10px] text-gray-400 list-disc list-inside leading-relaxed">
          <li>
            <span className="text-gray-300">Confirmed revenue at risk</span> — context-graph OUTCOME $
            (same engine as CFO/CRO).
          </li>
          <li>
            <span className="text-gray-300">Health buckets</span> — ARR in healthy / at-risk / critical bands;
            not the same dollar amount as confirmed graph $.
          </li>
          <li>
            <span className="text-gray-300">Playbook success %</span> — resolved executions ÷ total runs;
            attributed $ may still be $0 until outcomes close.
          </li>
          <li>
            <span className="text-gray-300">Capacity planning</span> — modeled headcount from account load
            and at-risk coverage; use hours utilization for feasibility.
          </li>
          <li>
            <span className="text-gray-300">Critical → expansion leaders</span> — CSMs ranked by recovery
            wins + expansion $ on playbooks in the last 90d.
          </li>
        </ul>
      )}
      {collapsed && (
        <p className="text-[9px] text-gray-500 mt-1">
          Graph $ ≠ health-band ARR · Playbook % ≠ attributed ROI · expand for definitions
        </p>
      )}
    </div>
  );
};

export const VPCSPreProofBanner: React.FC<{
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
            Playbook success is logged; attributed revenue not closed yet
          </p>
          <p className="text-amber-100/70">
            {executionsTotal} execution{executionsTotal === 1 ? '' : 's'} with{' '}
            <span className="text-amber-200/90">$0 attributed</span> so far. Rankings and capacity
            planning use execution outcomes; confirmed $ is in the graph strip below.
            <span className="block mt-1 text-[10px] text-amber-100/50">
              Phase: {phase.replace('_', ' ')}
            </span>
          </p>
        </div>
      </div>
    </div>
  );
};

export const VPCSContextGraphStrip: React.FC<{
  data: VPCSContextGraphRevenue;
}> = ({ data }) => {
  const tiles = [
    {
      label: 'Confirmed revenue at risk',
      value: data.revenue_at_risk,
      accent: 'text-red-400',
      border: 'border-t-red-500',
    },
    {
      label: 'Confirmed revenue protected',
      value: data.graph_revenue_protected,
      accent: 'text-emerald-400',
      border: 'border-t-emerald-500',
    },
    {
      label: 'Expansion pipeline (confirmed)',
      value: data.expansion_pipeline,
      accent: 'text-teal-400',
      border: 'border-t-teal-500',
    },
  ];

  return (
    <div className="bg-[#131826] rounded-xl border border-teal-800/40 p-5 mb-6">
      <div className="flex items-start justify-between gap-3 mb-4 pb-2 border-b border-gray-700/50">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-teal-400 shrink-0" />
          <div>
            <h3 className="text-[10px] font-bold text-teal-300/90 uppercase tracking-[2px]">
              Revenue intelligence (context graph)
            </h3>
            <p className="text-[10px] text-gray-500 mt-0.5">
              {data.revenue_risk_label} · same confirmed $ as CFO / CRO
            </p>
          </div>
        </div>
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
        Legacy “Revenue Intelligence” row used the same fields without graph labeling — prefer this strip
        for board-ready confirmed $.
      </p>
    </div>
  );
};

export interface CapacityPerformer {
  csm_name: string;
  recovery_wins: number;
  expansion_dollars: number;
  critical_to_expansion_score: number;
  top_playbooks: Array<{ playbook_id: string; expansion_events: number }>;
}

export interface CapacityPlanningData {
  csm_count_current: number;
  recommended_csm_count: number;
  target_accounts_per_csm: number;
  accounts_per_csm_current: number;
  at_risk_accounts: number;
  allocation_rationale: string;
  top_performers: CapacityPerformer[];
}

export interface UncoveredAccount {
  account_name: string;
  health_score: number;
  arr: number;
  assigned_csm: string;
  days_without_playbook: number;
}

export const VPCSCapacityPlanningPanel: React.FC<{
  planning: CapacityPlanningData;
  uncovered: UncoveredAccount[];
}> = ({ planning, uncovered }) => (
  <div className="mb-6 space-y-4">
    <div className="bg-[#1a1f2e] rounded-xl border border-teal-800/30 p-5">
      <h3 className="text-xs font-semibold text-white uppercase tracking-wide mb-3 flex items-center gap-2">
        <span className="text-teal-400">Capacity planning &amp; allocation</span>
        <span className="text-[9px] font-normal text-gray-500 normal-case">modeled</span>
      </h3>
      <div className="grid grid-cols-3 gap-4 mb-3">
        <div>
          <p className="text-[10px] text-gray-500 uppercase">CSMs today</p>
          <p className="text-2xl font-bold text-white">{planning.csm_count_current}</p>
        </div>
        <div>
          <p className="text-[10px] text-gray-500 uppercase">Recommended</p>
          <p className="text-2xl font-bold text-teal-400">{planning.recommended_csm_count}</p>
        </div>
        <div>
          <p className="text-[10px] text-gray-500 uppercase">Accounts / CSM</p>
          <p className="text-2xl font-bold text-gray-200">
            {planning.accounts_per_csm_current}
            <span className="text-sm text-gray-500 font-normal"> / {planning.target_accounts_per_csm}</span>
          </p>
        </div>
      </div>
      <p className="text-[11px] text-gray-400 leading-relaxed">{planning.allocation_rationale}</p>
    </div>

    {planning.top_performers.length > 0 && (
      <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-700/50">
          <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
            Top performers · critical → expansion playbooks
          </h3>
          <p className="text-[10px] text-gray-500 mt-0.5">90d recovery wins + expansion attribution by CSM</p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700/50">
              <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">CSM</th>
              <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Recoveries</th>
              <th className="text-right px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Expansion $</th>
              <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">Top playbooks</th>
            </tr>
          </thead>
          <tbody>
            {planning.top_performers.map((p) => (
              <tr key={p.csm_name} className="border-b border-gray-700/30">
                <td className="px-5 py-3 text-xs font-medium text-white">{p.csm_name}</td>
                <td className="text-center px-3 py-3 text-xs text-green-400">{p.recovery_wins}</td>
                <td className="text-right px-3 py-3 text-xs text-teal-400 font-mono">
                  {formatCompact(p.expansion_dollars)}
                </td>
                <td className="px-5 py-3 text-[10px] text-gray-400 font-mono">
                  {p.top_playbooks.map((pb) => pb.playbook_id).join(', ') || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}

    {uncovered.length > 0 && (
      <div className="bg-[#1a1f2e] rounded-xl border border-red-900/30 overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-700/50">
          <h3 className="text-xs font-semibold text-red-300 uppercase tracking-wide">Uncovered at-risk</h3>
          <p className="text-[10px] text-gray-500 mt-0.5">Below healthy threshold, no playbook in 45+ days</p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700/50">
              <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">Account</th>
              <th className="text-left px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase">CSM</th>
              <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Health</th>
              <th className="text-right px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">Days idle</th>
            </tr>
          </thead>
          <tbody>
            {uncovered.slice(0, 8).map((u) => (
              <tr key={u.account_name} className="border-b border-gray-700/30">
                <td className="px-5 py-3 text-xs text-white">{u.account_name}</td>
                <td className="px-4 py-3 text-xs text-gray-400">{u.assigned_csm}</td>
                <td className="text-center px-3 py-3 text-xs text-red-400">{u.health_score}</td>
                <td className="text-right px-5 py-3 text-xs text-gray-400">{u.days_without_playbook}d</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </div>
);
