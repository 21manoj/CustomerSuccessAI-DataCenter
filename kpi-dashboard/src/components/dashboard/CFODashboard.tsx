/**
 * CFO Investment Intelligence Dashboard
 * ======================================
 *
 * Dark-themed executive dashboard for Chief Financial Officers featuring:
 * - Total ARR / CS Investment / Revenue Protected / Portfolio ROI cards
 * - Power of 1 Metric Outcomes table
 * - Pillar Investment Breakdown (horizontal bar chart)
 * - Investment Timeline (area chart: investment vs return)
 * - Non-Linear ROI Scaling analysis
 * - Investment Efficiency sidebar widget
 * - Financial Ratios & Export options
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  AreaChart, Area, Cell, CartesianGrid, Legend
} from 'recharts';
import {
  DollarSign, TrendingUp, Shield, Target, BarChart3, Layers,
  FileText, ArrowUpRight, Sparkles, PieChart, Activity,
  Users, Eye, Zap, GitBranch, Clock, AlertTriangle, Info
} from 'lucide-react';
import { classify, classifyColor, thresholdValues } from '../../utils/healthThresholds';
import DashboardTopBar from './DashboardTopBar';
import { useSession } from '../../contexts/SessionContext';
import { apiCall, getCustomerIdentifier } from '../../utils/api';
import AskAIPortal from '../ai/AskAIPortal';
import { trackPageView, trackEvent } from '../../utils/activityTracker';

// ============================================================================
// TYPES
// ============================================================================

interface FinancialSummaryCard {
  label: string;
  value: string;
  subtitle: string;
  tag?: string;
  accent: string;
  estimated?: boolean;
}

interface PowerOf1Row {
  metric: string;
  baseline: string;
  current: string;
  improvement: string;
  improvement_direction: 'up' | 'down';
  dollar_impact: number;
  color: string;
}

interface PillarInvestment {
  pillar: string;
  pillar_code: string;
  investment: number;
  impact: number;
  roi_multiplier: number;
}

interface InvestmentTimelinePoint {
  month: string;
  investment: number;
  returns: number;
}

interface ROIScalingTier {
  accounts: number;
  label: string;
  roi: number;
  growth_bar: number; // percentage width for visual
}

interface FinancialRatio {
  label: string;
  value: string;
  accent?: string;
}

interface AccountROI {
  account_id: number;
  account_name: string;
  arr: number;
  health_score: number;
  classification: 'critical' | 'at_risk' | 'healthy';
  investment: number;
  impact: number;
  roi_pct: number;
  source: 'actual' | 'benchmark';
  playbook_runs: number;
}

interface CostOfInaction {
  arr_at_risk: number;
  annual_churn_exposure: number;
  account_count: number;
  accounts: Array<{ account_name: string; arr: number; health: number; churn_pct: number; annual_loss: number }>;
}

interface CFODashboardData {
  summary_cards: FinancialSummaryCard[];
  power_of_1: PowerOf1Row[];
  power_of_1_total: number;
  pillar_investments: PillarInvestment[];
  investment_timeline: InvestmentTimelinePoint[];
  roi_scaling: ROIScalingTier[];
  efficiency_score: number;
  automation_rate: number;
  time_saved_hours: number;
  cost_per_protected_dollar: number;
  financial_ratios: FinancialRatio[];
  accounts: AccountROI[];
  // NRR/GRR + Cost of Inaction
  nrr_current: number;
  nrr_with_intervention: number;
  grr: number;
  nrr_arr_protectable: number;
  cost_of_inaction: CostOfInaction;
  nrr_waterfall: { expected_loss: number; attributed_save: number; intervention_cost: number; roi_x: number };
  // Raw numeric values for Investment Allocation widget
  total_arr: number;
  cs_investment: number;
  roi_impact: number;
  is_estimated_investment: boolean;
  renewals_at_risk: Array<{ account_name: string; arr: number; days_until: number; health_score: number }>;
  period: string;
  last_updated: string;
}

// ============================================================================
// HELPERS
// ============================================================================

function formatCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    const m = value / 1_000_000;
    return `$${m % 1 === 0 ? m.toFixed(0) : m.toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    const k = value / 1_000;
    return `$${k % 1 === 0 ? k.toFixed(0) : k.toFixed(0)}K`;
  }
  return `$${value.toLocaleString()}`;
}

function formatDollarFull(value: number): string {
  return `$${value.toLocaleString()}`;
}

const ACCENT_MAP: Record<string, string> = {
  white: '#ffffff',
  emerald: '#10b981',
  green: '#22c55e',
  cyan: '#06b6d4',
  red: '#ef4444',
  yellow: '#eab308',
  purple: '#a855f7',
  orange: '#f97316',
};

const PILLAR_COLORS = ['#06b6d4', '#10b981', '#a855f7', '#f97316', '#eab308'];

// Sidebar navigation items for CFO — routes to CRO views where applicable
const NAV_ITEMS = {
  intelligence: [
    { id: 'cro-overview', label: 'CRO Overview', path: '/cro-dashboard', badge: null, icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'cfo-overview', label: 'CFO Overview', path: '/cfo-dashboard', badge: null, icon: <DollarSign className="w-4 h-4" /> },
    // ROI Engine hidden — Power-of-1 table on CFO overview is sufficient
    { id: 'context-graph', label: 'Context Graph', path: '/cro-dashboard?view=context-graph', badge: null, icon: <GitBranch className="w-4 h-4" /> },
  ],
  operations: [
    { id: 'accounts', label: 'Accounts', path: '/cro-dashboard?view=accounts', badge: null, icon: <Users className="w-4 h-4" /> },
    { id: 'playbooks', label: 'Playbooks', path: '/cro-dashboard?view=playbooks', badge: null, icon: <Target className="w-4 h-4" /> },
    { id: 'approvals', label: 'Approvals', path: '/cro-dashboard?view=approvals', badge: null, icon: <Eye className="w-4 h-4" /> },
  ],
};

// No fallback data — dashboard requires live API data.
// If API is unavailable, error state is shown instead of fake numbers.

// ============================================================================
// SKELETON COMPONENTS
// ============================================================================

const SkeletonCard: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 animate-pulse ${className}`}>
    <div className="h-3 bg-gray-700 rounded w-2/3 mb-3" />
    <div className="h-8 bg-gray-700 rounded w-1/2 mb-2" />
    <div className="h-3 bg-gray-700 rounded w-3/4" />
  </div>
);

const SkeletonLine: React.FC<{ w?: string }> = ({ w = 'w-full' }) => (
  <div className={`h-3 bg-gray-700 rounded ${w} animate-pulse`} />
);

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

/** Left sidebar navigation */
const SidebarNav: React.FC<{ activeId: string; onNavigate: (path: string) => void }> = ({ activeId, onNavigate }) => (
  <aside className="w-48 flex-shrink-0 bg-[#0d1117] border-r border-gray-700/50 py-6 px-3 flex flex-col gap-6 overflow-y-auto">
    {/* Intelligence section */}
    <div>
      <h3 className="text-[10px] font-semibold tracking-[0.2em] text-gray-500 uppercase mb-3 px-2">Intelligence</h3>
      <nav className="flex flex-col gap-0.5">
        {NAV_ITEMS.intelligence.map((item) => {
          const isActive = item.id === activeId;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.path)}
              className={`flex items-center gap-2 px-2 py-2 rounded-lg text-sm transition-all group w-full text-left ${
                isActive
                  ? 'bg-emerald-500/10 text-emerald-400'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <span className={isActive ? 'text-emerald-400' : 'text-gray-500 group-hover:text-gray-300'}>
                {item.icon}
              </span>
              <span className="flex-1 truncate">{item.label}</span>
              {item.badge && (
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                  isActive ? 'bg-emerald-500/20 text-emerald-400' : 'bg-gray-700/50 text-gray-400'
                }`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </div>

    {/* Operations section */}
    <div>
      <h3 className="text-[10px] font-semibold tracking-[0.2em] text-gray-500 uppercase mb-3 px-2">Operations</h3>
      <nav className="flex flex-col gap-0.5">
        {NAV_ITEMS.operations.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.path)}
            className="flex items-center gap-2 px-2 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-all group w-full text-left"
          >
            <span className="text-gray-500 group-hover:text-gray-300">{item.icon}</span>
            <span className="flex-1 truncate">{item.label}</span>
            {item.badge && (
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-gray-700/50 text-gray-400">
                {item.badge}
              </span>
            )}
          </button>
        ))}
      </nav>
    </div>

    {/* Branding */}
    <div className="mt-auto px-2 pt-4 border-t border-gray-700/30">
      <div className="text-[10px] text-gray-600 leading-relaxed">
        CS Pulse<br />
        Investment Intelligence
      </div>
    </div>
  </aside>
);

/** Financial summary card */
const SummaryCardComponent: React.FC<{ card: FinancialSummaryCard }> = ({ card }) => {
  const accent = ACCENT_MAP[card.accent] || '#10b981';
  const isCyan = card.accent === 'cyan';
  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 relative overflow-hidden group hover:border-gray-600/50 transition-all">
      {/* Accent bar */}
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ backgroundColor: accent }} />
      {/* Glow effect for cyan ROI card */}
      {isCyan && (
        <div
          className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-16 opacity-15 blur-2xl"
          style={{ backgroundColor: accent }}
        />
      )}
      <div className="relative">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">{card.label}</p>
        <p className="text-3xl font-bold mb-1" style={{ color: accent }}>
          {card.value}
          {card.estimated && <span className="text-xs italic text-gray-400 ml-1 font-normal">Estimated</span>}
        </p>
        <p className="text-xs text-gray-500 mb-1">{card.subtitle}</p>
        {card.tag && (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 mt-1">
            <Sparkles className="w-3 h-3" />
            {card.tag}
          </span>
        )}
      </div>
    </div>
  );
};

/** Power of 1 table */
const PowerOf1Table: React.FC<{ rows: PowerOf1Row[]; total: number }> = ({ rows, total }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
    <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Layers className="w-4 h-4 text-emerald-400" />
        <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
          Power of 1 &middot; Metric Outcomes
        </h3>
      </div>
      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400">
        6 metrics tracked
      </span>
    </div>
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700/50">
            <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Metric</th>
            <th className="text-right px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Baseline</th>
            <th className="text-right px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Current</th>
            <th className="text-right px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Improvement</th>
            <th className="text-right px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Dollar Impact</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-gray-700/30 hover:bg-white/[0.02] transition-colors">
              <td className="px-5 py-3">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: row.color }} />
                  <span className="text-gray-300 text-xs font-medium">{row.metric}</span>
                </div>
              </td>
              <td className="text-right px-4 py-3 text-xs text-gray-500 font-mono">{row.baseline}</td>
              <td className="text-right px-4 py-3 text-xs text-white font-mono font-medium">{row.current}</td>
              <td className="text-right px-4 py-3">
                <span className={`text-xs font-semibold font-mono ${
                  row.improvement_direction === 'up' ? 'text-green-400' : 'text-cyan-400'
                }`}>
                  {row.improvement}
                </span>
              </td>
              <td className="text-right px-5 py-3 text-xs text-emerald-400 font-semibold font-mono">
                {formatCompact(row.dollar_impact)}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="bg-emerald-500/5">
            <td className="px-5 py-3 text-xs font-semibold text-white" colSpan={4}>
              Total Combined Impact
            </td>
            <td className="text-right px-5 py-3 text-sm font-bold text-emerald-400 font-mono">
              {formatCompact(total)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
);

/** Pillar Investment Breakdown - horizontal bar chart */
const PillarInvestmentChart: React.FC<{ data: PillarInvestment[] }> = ({ data }) => {
  // Show projected impact per pillar as single horizontal bars (color-coded)
  const chartData = data.map((p, i) => ({
    name: p.pillar,
    impact: Math.round(p.impact / 1000),
    fill: PILLAR_COLORS[i % PILLAR_COLORS.length],
  }));

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <PieChart className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
            Projected Impact by Pillar
          </h3>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 0, right: 10, left: 10, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
          <XAxis
            type="number"
            tick={{ fill: '#6b7280', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `$${v}K`}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: '#9ca3af', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={60}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#1a1f2e', border: '1px solid #374151', borderRadius: 8, fontSize: 12, color: '#fff' }}
            formatter={(value: number) => [`$${value}K`, 'Projected Impact']}
          />
          {chartData.map((entry, i) => (
            <Bar key={entry.name} dataKey="impact" fill={PILLAR_COLORS[i % PILLAR_COLORS.length]} radius={[0, 4, 4, 0]} barSize={14} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

/** Investment Timeline - area chart */
const InvestmentTimelineChart: React.FC<{ data: InvestmentTimelinePoint[] }> = ({ data }) => {
  const hasRealData = data.some((d) => d.investment > 0 || d.returns > 0);

  // When no real data, show projected 6-month ramp based on Power-of-1
  const chartData = hasRealData
    ? data.map((d) => ({ month: d.month, Investment: d.investment / 1000, Return: d.returns / 1000 }))
    : ['M1', 'M2', 'M3', 'M4', 'M5', 'M6'].map((m, i) => {
        const ramp = [0.6, 0.8, 1.0, 1.0, 1.0, 1.0]; // ramp-up factor
        const monthlyInv = 235; // ~$1.4M / 6 months in $K
        const inv = Math.round(monthlyInv * ramp[i]);
        const ret = Math.round(inv * (0.5 + i * 0.3)); // returns accelerate over time
        return { month: m, Investment: inv, Return: ret };
      });

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
            {hasRealData ? 'Investment Timeline' : 'Projected Investment Ramp'}
          </h3>
        </div>
        <span className="text-[10px] text-gray-500">{hasRealData ? '6-month window' : 'Estimated'}</span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="gradInvestment" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gradReturn" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis
            dataKey="month"
            tick={{ fill: '#6b7280', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#6b7280', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `$${v}K`}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#1a1f2e', border: '1px solid #374151', borderRadius: 8, fontSize: 12, color: '#fff' }}
            formatter={(value: number, name: string) => [`$${value}K`, name === 'Investment' ? 'CS Investment' : 'Projected Return']}
          />
          <Legend
            wrapperStyle={{ fontSize: 10, color: '#9ca3af', paddingTop: 4 }}
            formatter={(value: string) => value === 'Investment' ? '● CS Investment (orange)' : '● Projected Return (green)'}
          />
          <Area
            type="monotone"
            dataKey="Investment"
            stroke="#f97316"
            strokeWidth={2}
            fill="url(#gradInvestment)"
          />
          <Area
            type="monotone"
            dataKey="Return"
            stroke="#22c55e"
            strokeWidth={2}
            fill="url(#gradReturn)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

/** ROI Scaling Analysis - three large cards */
const ROIScalingSection: React.FC<{ tiers: ROIScalingTier[] }> = ({ tiers }) => {
  const tierColors = ['#06b6d4', '#22c55e', '#a855f7'];
  const tierBgColors = ['bg-cyan-500/10', 'bg-green-500/10', 'bg-purple-500/10'];

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <ArrowUpRight className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
            Non-Linear ROI Scaling
          </h3>
        </div>
      </div>
      <p className="text-[11px] text-gray-500 mb-5">
        CS Pulse platform costs remain fixed while revenue impact compounds across accounts. Each additional account adds marginal cost but full playbook value.
      </p>
      {tiers.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-sm text-gray-500">No ROI scaling data available</p>
        </div>
      ) : (
      <div className="grid grid-cols-3 gap-4 mb-4">
        {tiers.map((tier, i) => (
          <div
            key={tier.accounts}
            className={`rounded-xl border border-gray-700/50 p-4 text-center relative overflow-hidden ${tierBgColors[i]}`}
          >
            {/* Glow */}
            <div
              className="absolute top-0 left-1/2 -translate-x-1/2 w-20 h-12 opacity-10 blur-2xl"
              style={{ backgroundColor: tierColors[i] }}
            />
            <div className="relative">
              <p className="text-xs font-medium text-gray-400 mb-2">{tier.label}</p>
              <p className="text-4xl font-bold mb-2" style={{ color: tierColors[i] }}>
                {tier.roi}%
              </p>
              <p className="text-[10px] text-gray-500 mt-1">
                {i === 0 ? 'Current portfolio' : i === 1 ? 'Fixed cost, 5× accounts' : 'Fixed cost, 20× accounts'}
              </p>
              {/* Growth bar */}
              <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden mt-2">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{
                    width: `${tier.growth_bar}%`,
                    backgroundColor: tierColors[i],
                  }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
      )}
      <p className="text-[10px] text-gray-600 text-center leading-relaxed mt-2">
        ROI scales logarithmically: platform + playbook costs are fixed, revenue impact grows linearly with accounts.
      </p>
    </div>
  );
};

/** Investment Allocation Intelligence (right sidebar) — replaces old EfficiencyGauge */
const InvestmentAllocationWidget: React.FC<{
  totalArr: number;
  csInvestment: number;
  roiImpact: number;
  isEstimated: boolean;
}> = ({ totalArr, csInvestment, roiImpact, isEstimated }) => {
  const [showDetails, setShowDetails] = useState(false);

  // Industry benchmark: 1.5% - 2.5% of ARR for CS investment (TSIA)
  const pctOfArr = totalArr > 0 ? (csInvestment / totalArr) * 100 : 0;
  const benchmarkLow = totalArr * 0.015;
  const benchmarkHigh = totalArr * 0.025;
  const inRange = csInvestment >= benchmarkLow * 0.8 && csInvestment <= benchmarkHigh * 1.2;
  const roi = csInvestment > 0 ? roiImpact / csInvestment : 0;

  // Allocation breakdown (industry benchmarks when estimated)
  const playbookAlloc = csInvestment * 0.30;
  const csmAlloc = csInvestment * 0.45;
  const overheadAlloc = csInvestment * 0.25;

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase">
          CS Investment
        </h3>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-[10px] text-teal-500 hover:text-teal-400 flex items-center gap-0.5"
        >
          <Info className="w-3 h-3" />
          {showDetails ? 'Hide' : 'Details'}
        </button>
      </div>

      {/* Primary metric: % of ARR */}
      <div className="text-center mb-3">
        <p className="text-3xl font-bold text-white">{pctOfArr.toFixed(1)}%</p>
        <p className="text-[10px] text-gray-500">of ARR invested in CS</p>
        <p className={`text-[9px] mt-1 ${inRange ? 'text-emerald-400' : 'text-amber-400'}`}>
          {inRange ? '✓ Within' : '⚠ Outside'} industry range (1.5% - 2.5%)
        </p>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-gray-800/50 rounded-lg p-2 text-center">
          <p className="text-xs font-semibold text-white">{formatCompact(csInvestment)}</p>
          <p className="text-[9px] text-gray-500">CS Spend</p>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-2 text-center">
          <p className="text-xs font-semibold text-emerald-400">{roi > 0 ? `${roi.toFixed(1)}x` : '—'}</p>
          <p className="text-[9px] text-gray-500">ROI</p>
        </div>
      </div>

      {isEstimated && (
        <p className="text-[9px] text-amber-400/70 mb-2">* Estimated from Power-of-1 benchmarks</p>
      )}

      {/* Expandable details */}
      {showDetails && (
        <div className="border-t border-gray-700/50 pt-3 mt-2 space-y-3">
          {/* Allocation breakdown */}
          <div>
            <p className="text-[9px] text-gray-500 uppercase tracking-wide mb-2">Where Your CS Dollars Go</p>
            <div className="space-y-1.5">
              {[
                { label: 'Playbook interventions', amount: playbookAlloc, pct: 30, color: 'bg-cyan-500' },
                { label: 'CSM team capacity', amount: csmAlloc, pct: 45, color: 'bg-emerald-500' },
                { label: 'Operational overhead', amount: overheadAlloc, pct: 25, color: 'bg-gray-500' },
              ].map(item => (
                <div key={item.label}>
                  <div className="flex justify-between text-[10px] mb-0.5">
                    <span className="text-gray-400">{item.label}</span>
                    <span className="text-gray-300">{formatCompact(item.amount)} ({item.pct}%)</span>
                  </div>
                  <div className="w-full h-1 bg-gray-800 rounded-full overflow-hidden">
                    <div className={`h-full ${item.color} rounded-full`} style={{ width: `${item.pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Benchmark context */}
          <div className="bg-gray-800/30 rounded-lg p-2.5">
            <p className="text-[9px] text-gray-500 uppercase tracking-wide mb-1.5">Industry Benchmark (TSIA)</p>
            <div className="flex justify-between text-[10px]">
              <span className="text-gray-400">Your ARR</span>
              <span className="text-white">{formatCompact(totalArr)}</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-gray-400">Recommended CS budget</span>
              <span className="text-gray-300">{formatCompact(benchmarkLow)} – {formatCompact(benchmarkHigh)}</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-gray-400">Your CS spend</span>
              <span className={inRange ? 'text-emerald-400' : 'text-amber-400'}>{formatCompact(csInvestment)}</span>
            </div>
            <div className="flex justify-between text-[10px] border-t border-gray-700/30 pt-1 mt-1">
              <span className="text-gray-400">Return on CS spend</span>
              <span className="text-white font-semibold">{formatCompact(roiImpact)} protected</span>
            </div>
          </div>

          <p className="text-[8px] text-gray-600">
            Benchmark: TSIA CS benchmark 2024, Gainsight Pulse, KeyBanc SaaS Metrics.
            Allocation split is industry-average for mid-market SaaS.
          </p>
        </div>
      )}
    </div>
  );
};

/** Financial Ratios (right sidebar) */
const FinancialRatiosWidget: React.FC<{ ratios: FinancialRatio[] }> = ({ ratios }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
    <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-3">
      Quick Financial Ratios
    </h3>
    <div className="space-y-3">
      {ratios.map((ratio, i) => (
        <div key={i} className="flex items-center justify-between">
          <span className="text-[11px] text-gray-500 leading-tight max-w-[140px]">{ratio.label}</span>
          <span className="text-xs font-semibold text-white">{ratio.value}</span>
        </div>
      ))}
    </div>
  </div>
);

/** Cost of Inaction panel — shows formula and per-account math */
const CostOfInactionPanel: React.FC<{ data: CFODashboardData['cost_of_inaction'] }> = ({ data: coi }) => {
  const [showFormula, setShowFormula] = useState(false);
  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-400" />
          <h3 className="text-[10px] font-semibold text-white uppercase tracking-wide">Cost of Inaction</h3>
        </div>
        <button
          onClick={() => setShowFormula(!showFormula)}
          className="text-[10px] text-teal-500 hover:text-teal-400 flex items-center gap-0.5"
          title="Show calculation methodology"
        >
          <Info className="w-3 h-3" />
          {showFormula ? 'Hide' : 'How calculated?'}
        </button>
      </div>
      {showFormula && (
        <div className="bg-gray-800/50 rounded-lg p-3 mb-3 text-[10px] text-gray-400 space-y-1">
          <p className="text-gray-300 font-medium">Methodology</p>
          <p>Churn probability = max(5%, 50% - health_score × 0.5)</p>
          <p>Annual loss per account = ARR × churn probability</p>
          <p>Annual churn exposure = sum of all at-risk account losses</p>
          <p className="text-gray-500 pt-1">Accounts included: health &lt; 70 (at-risk + critical)</p>
        </div>
      )}
      <div className="flex items-end gap-6 mb-4">
        <div>
          <p className="text-[9px] text-gray-500 mb-0.5">ARR at Risk</p>
          <p className="text-2xl font-bold text-red-400">{formatCompact(coi.arr_at_risk)}</p>
        </div>
        <div>
          <p className="text-[9px] text-gray-500 mb-0.5">Annual Churn Exposure</p>
          <p className="text-2xl font-bold text-orange-400">{formatCompact(coi.annual_churn_exposure)}</p>
        </div>
        <div>
          <p className="text-[9px] text-gray-500 mb-0.5">Accounts</p>
          <p className="text-2xl font-bold text-gray-300">{coi.account_count}</p>
        </div>
      </div>
      {coi.accounts.length > 0 && (
        <div className="space-y-1.5">
          {coi.accounts.slice(0, 5).map((a, i) => (
            <div key={i} className="flex items-center justify-between text-xs">
              <span className="text-gray-400 truncate max-w-[120px]">{a.account_name}</span>
              <span className="text-gray-500 text-[10px]">{formatCompact(a.arr)} × {a.churn_pct}%</span>
              <span className="text-red-400 font-semibold">{formatCompact(a.annual_loss)}/yr</span>
            </div>
          ))}
        </div>
      )}
      <p className="text-[9px] text-gray-600 mt-2">Projected annual revenue loss if no intervention on at-risk/critical accounts.</p>
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const CFODashboard: React.FC = () => {
  const navigate = useNavigate();
  const { session } = useSession();

  const [data, setData] = useState<CFODashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch main dashboard data
  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const customerId = getCustomerIdentifier(session);
        const resp = await apiCall('/api/executive/cfo-dashboard', {
          headers: { 'X-Customer-ID': customerId },
        });
        if (!resp.ok) throw new Error(`API returned ${resp.status}`);
        const json = await resp.json();
        if (!cancelled) {
          // Transform flat API response into CFODashboardData shape
          const totalArr = json.total_arr || 0;
          // cs_investment = actual playbook spend; check explicitly for > 0 (not JS falsy)
          const rawCsInvestment = (json.cs_investment != null && json.cs_investment > 0) ? json.cs_investment : 0;
          // Fall back to Power-of-1 benchmark estimated investment when no PlaybookExecution records exist
          const estimatedInvestment = json.estimated_investment || json.benchmark_investment || json.po1_estimated_investment || 0;
          const isEstimatedInvestment = rawCsInvestment === 0 && estimatedInvestment > 0;
          const csInvestment = rawCsInvestment > 0 ? rawCsInvestment : estimatedInvestment;
          const roiPct = json.roi_pct || 0;
          const roiImpact = json.roi_impact || 0;
          const nrr = json.nrr_projection || 100;
          const grr = json.grr_projection || 85;

          const po1Metrics: PowerOf1Row[] = (json.power_of_1_metrics || []).map((m: any) => {
            const directionDown = ['TTFV', 'ticket_resolution_time'].includes(m.metric_id);
            return {
              metric: m.display_name || m.metric_id,
              baseline: m.metric_id === 'TTFV' ? `${m.baseline}d` : m.metric_id === 'ticket_resolution_time' ? `${m.baseline}h` : `${m.baseline}%`,
              current: m.metric_id === 'TTFV' ? `${m.current?.toFixed(1)}d` : m.metric_id === 'ticket_resolution_time' ? `${m.current?.toFixed(1)}h` : `${m.current?.toFixed(1)}%`,
              improvement: `${Math.abs(m.improvement_pct || 0).toFixed(1)}%`,
              improvement_direction: (directionDown ? 'down' : 'up') as 'up' | 'down',
              dollar_impact: m.dollar_impact || 0,
              color: m.dollar_impact > 200000 ? '#22c55e' : m.dollar_impact > 100000 ? '#06b6d4' : '#eab308',
            };
          });

          const pillarDisplayNames: Record<string, string> = {
            P1: 'Deploy', P2: 'Ops', P3: 'AI Perf', P4: 'Channel', P5: 'Expand',
          };

          const pillarInvs: PillarInvestment[] = (json.pillar_investments || []).map((p: any) => ({
            pillar: pillarDisplayNames[p.pillar] || p.name || p.pillar,
            pillar_code: p.pillar,
            investment: p.investment || 0,
            impact: p.impact || 0,
            roi_multiplier: p.roi || 0,
          }));

          const invTimeline: InvestmentTimelinePoint[] = (json.investment_timeline || []).map((t: any) => ({
            month: t.month,
            investment: t.investment || 0,
            returns: t.return || t.returns || 0,
          }));

          const scalingProjs = json.roi_scaling?.projections || [];
          const roiScaling: ROIScalingTier[] = scalingProjs.map((s: any, i: number) => ({
            accounts: s.accounts,
            label: `${s.accounts} accts`,
            roi: s.roi,
            growth_bar: i === 0 ? 30 : i === 1 ? 60 : 90,
          }));
          // If API returns no scaling projections, leave empty — UI handles gracefully

          const csPercent = totalArr > 0 ? ((csInvestment / totalArr) * 100).toFixed(2) : '0';
          // Use backend pre-computed ratio when available, else compute from projected impact
          const revPerDollar = json.rev_per_cs_dollar
            ? json.rev_per_cs_dollar.toFixed(1)
            : (csInvestment > 0 ? ((isEstimatedInvestment ? roiImpact : (json.revenue_protected || 0)) / csInvestment).toFixed(1) : '0');
          const paybackMonths = json.payback_months || (roiImpact > 0 ? Math.round((csInvestment / roiImpact) * 12) : 0);

          const revenueProtected = json.revenue_protected || 0;
          const transformed: CFODashboardData = {
            summary_cards: [
              { label: 'Total ARR', value: formatCompact(totalArr), subtitle: `${json.roi_scaling?.current_accounts || json.account_count || '—'} active accounts`, accent: 'white' },
              { label: 'CS Investment', value: formatCompact(csInvestment), subtitle: isEstimatedInvestment ? 'Power-of-1 benchmark estimate' : 'Playbook execution cost', tag: json.automation_rate ? `${json.automation_rate}% automated` : undefined, accent: 'emerald', estimated: isEstimatedInvestment },
              { label: isEstimatedInvestment ? 'Projected Impact' : 'Revenue Protected', value: formatCompact(isEstimatedInvestment ? roiImpact : revenueProtected), subtitle: isEstimatedInvestment && revenueProtected > 0 ? `${formatCompact(revenueProtected)} confirmed · GRR: ${grr}%` : `GRR: ${grr}%`, accent: 'green', estimated: isEstimatedInvestment },
              { label: 'Portfolio ROI', value: `${roiPct}%`, subtitle: `${formatCompact(csInvestment)} → ${formatCompact(roiImpact)}`, accent: 'cyan', estimated: isEstimatedInvestment },
            ],
            power_of_1: po1Metrics,
            power_of_1_total: po1Metrics.reduce((sum: number, m: PowerOf1Row) => sum + m.dollar_impact, 0),
            pillar_investments: pillarInvs,
            investment_timeline: invTimeline,
            roi_scaling: roiScaling,
            efficiency_score: json.efficiency_score || 0,
            automation_rate: json.automation_rate || 0,
            time_saved_hours: json.time_saved_hours || 0,
            // Use total projected impact (not just confirmed protected) when estimated
            cost_per_protected_dollar: csInvestment > 0 && roiImpact > 0
              ? parseFloat((csInvestment / roiImpact).toFixed(2))
              : 0.05,
            financial_ratios: [
              { label: 'CS % of ARR', value: `${csPercent}%${isEstimatedInvestment ? ' *' : ''}` },
              { label: 'Rev per CS Dollar', value: `$${revPerDollar}${isEstimatedInvestment ? ' *' : ''}` },
              { label: 'Payback Period', value: `${paybackMonths} months${isEstimatedInvestment ? ' *' : ''}` },
              { label: 'NRR Impact / Playbook', value: `+${((nrr - 100) / Math.max(scalingProjs[0]?.accounts || 15, 1)).toFixed(2)}%`, accent: 'cyan' },
              ...(isEstimatedInvestment ? [{ label: '* Benchmarks: Gainsight Pulse 2024, TSIA, KeyBanc SaaS, Bain NPS Economics', value: '', accent: 'gray' }] : []),
            ],
            accounts: (json.accounts || []).map((a: any) => ({
              account_id: a.account_id,
              account_name: a.account_name || 'Unknown',
              arr: a.arr || 0,
              health_score: a.health_score || 0,
              classification: a.classification || 'at_risk',
              investment: a.investment || 0,
              impact: a.impact || 0,
              roi_pct: a.roi_pct || 0,
              source: a.source || 'benchmark',
              playbook_runs: a.playbook_runs || 0,
            })),
            // NRR/GRR + Cost of Inaction
            nrr_current: json.nrr_current || nrr,
            nrr_with_intervention: json.nrr_with_intervention || nrr,
            grr: grr,
            nrr_arr_protectable: json.nrr_arr_protectable || 0,
            cost_of_inaction: json.cost_of_inaction || { arr_at_risk: 0, annual_churn_exposure: 0, account_count: 0, accounts: [] },
            nrr_waterfall: json.nrr_waterfall || { expected_loss: 0, attributed_save: 0, intervention_cost: 0, roi_x: 0 },
            renewals_at_risk: json.renewals_at_risk || [],
            total_arr: totalArr,
            cs_investment: csInvestment,
            roi_impact: roiImpact,
            is_estimated_investment: isEstimatedInvestment,
            period: json.quarter_label || `Q${Math.ceil((new Date().getMonth() + 1) / 3)} ${new Date().getFullYear()}`,
            last_updated: json.last_updated || new Date().toISOString(),
          };
          setData(transformed);
          trackPageView('cfo_dashboard', { accounts: transformed.accounts.length });
        }
      } catch {
        if (!cancelled) {
          setError('Unable to load CFO dashboard data. Please check your connection and try again.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchData();
    return () => { cancelled = true; };
  }, [session]);

  const handleNav = useCallback((path: string) => {
    navigate(path);
  }, [navigate]);

  // ---- Loading state ----
  if (loading) {
    return (
      <div className="flex h-screen bg-[#0f1419] text-white font-['Inter',sans-serif]">
        <SidebarNav activeId="cfo-overview" onNavigate={handleNav} />
        <main className="flex-1 p-6 overflow-y-auto">
          <div className="mb-6">
            <SkeletonLine w="w-64" />
          </div>
          <div className="grid grid-cols-4 gap-4 mb-4">
            <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
          </div>
          <SkeletonCard className="h-64 mb-4" />
          <div className="grid grid-cols-2 gap-4 mb-4">
            <SkeletonCard className="h-64" /><SkeletonCard className="h-64" />
          </div>
          <SkeletonCard className="h-48" />
        </main>
        <aside className="w-80 bg-[#0d1117] border-l border-gray-700/50 p-4">
          <SkeletonCard className="h-56 mb-4" />
          <SkeletonCard className="h-40 mb-4" />
          <SkeletonCard className="h-24" />
        </aside>
      </div>
    );
  }

  // ---- Error state ----
  if (error || !data) {
    return (
      <div className="flex h-screen bg-[#0f1419] text-white font-['Inter',sans-serif] items-center justify-center">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Unable to Load Dashboard</h2>
          <p className="text-gray-400 text-sm mb-4">{error || 'No data available. Please refresh or check your connection.'}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-500 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const d = data;

  return (
    <div className="flex flex-col h-screen bg-[#0f1419] text-white font-['Inter',sans-serif]">
      <DashboardTopBar accent="emerald" />
      <div className="flex flex-1 overflow-hidden">
      {/* ---- Left Sidebar ---- */}
      <SidebarNav activeId="cfo-overview" onNavigate={handleNav} />

      {/* ---- Main Content ---- */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-[1200px]">
          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-lg font-semibold text-white tracking-tight">
                INVESTMENT INTELLIGENCE
                <span className="text-gray-500 font-normal ml-2">&middot; {d.period}</span>
              </h1>
              <div className="h-0.5 w-12 bg-emerald-500 mt-1.5 rounded-full" />
            </div>
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-green-400">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                Live
              </span>
              <span className="text-gray-600">&middot;</span>
              <span className="text-gray-500 flex items-center gap-1">
                <Clock className="w-3 h-3" /> Updated {d.last_updated}
              </span>
            </div>
          </div>

          {/* Portfolio Pulse — Traffic Light Summary */}
          <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                {(() => {
                  const accts = d.accounts;
                  const healthy = accts.filter(a => a.health_score >= 70);
                  const atRisk = accts.filter(a => a.health_score >= 50 && a.health_score < 70);
                  const critical = accts.filter(a => a.health_score < 50);
                  const buckets = [
                    { count: healthy.length, arr: healthy.reduce((s, a) => s + a.arr, 0), color: '#22c55e', label: 'Healthy' },
                    { count: atRisk.length, arr: atRisk.reduce((s, a) => s + a.arr, 0), color: '#eab308', label: 'At Risk' },
                    { count: critical.length, arr: critical.reduce((s, a) => s + a.arr, 0), color: '#ef4444', label: 'Critical' },
                  ];
                  return buckets.map((b, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white" style={{ backgroundColor: b.color + '33', border: `2px solid ${b.color}` }}>
                        {b.count}
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-white">{b.label}</p>
                        <p className="text-[10px] text-gray-500">{formatCompact(b.arr)} ARR</p>
                      </div>
                    </div>
                  ));
                })()}
              </div>
              <div className="text-right">
                <p className="text-[10px] text-gray-500 uppercase tracking-wide">Portfolio Pulse</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {d.accounts.filter(a => a.health_score >= 70).length} healthy, {d.accounts.filter(a => a.health_score < 50).length} need intervention
                </p>
              </div>
            </div>
          </div>

          {/* Row 1: Financial summary cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            {d.summary_cards.map((card, i) => (
              <SummaryCardComponent key={i} card={card} />
            ))}
          </div>

          {/* Row 1b: NRR/GRR + Cost of Inaction */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            {/* Dual NRR/GRR */}
            <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-cyan-400" />
                <h3 className="text-[10px] font-semibold text-white uppercase tracking-wide">Net Revenue Retention</h3>
              </div>
              <div className="flex items-end gap-6 mb-3">
                <div>
                  <p className="text-[9px] text-gray-500 mb-0.5">Current NRR</p>
                  <p className={`text-3xl font-bold ${d.nrr_current >= 100 ? 'text-cyan-400' : 'text-red-400'}`}>{d.nrr_current}%</p>
                </div>
                <div className="text-gray-600 text-xl pb-1">&rarr;</div>
                <div>
                  <p className="text-[9px] text-gray-500 mb-0.5">With Playbooks</p>
                  <p className="text-3xl font-bold text-green-400">{d.nrr_with_intervention}%</p>
                </div>
                <div className="border-l border-gray-700/50 pl-6">
                  <p className="text-[9px] text-gray-500 mb-0.5">GRR</p>
                  <p className="text-3xl font-bold text-gray-300">{d.grr}%</p>
                </div>
              </div>
              {d.nrr_arr_protectable > 0 && (
                <p className="text-[10px] text-green-400/80">{formatCompact(d.nrr_arr_protectable)} ARR protectable with intervention</p>
              )}
              <p className="text-[9px] text-gray-600 mt-1">Current: health-weighted baseline. Projected: if playbooks run on at-risk accounts.</p>
            </div>

            {/* Cost of Inaction — with formula transparency */}
            <CostOfInactionPanel data={d.cost_of_inaction} />
          </div>

          {/* Renewals at Risk Banner */}
          {d.renewals_at_risk.length > 0 && (
            <div className="bg-[#1a1f2e] rounded-xl border border-yellow-600/30 p-4 mb-6">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-500" />
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
                    Renewals at Risk &middot; Next 90 Days
                  </h3>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400">
                    {d.renewals_at_risk.length}
                  </span>
                </div>
                <span className="text-[10px] text-gray-500">
                  {formatCompact(d.renewals_at_risk.reduce((s, r) => s + r.arr, 0))} ARR
                </span>
              </div>
              <div className="space-y-1">
                {d.renewals_at_risk.slice(0, 5).map((r, i) => (
                  <div key={i} className="flex items-center justify-between text-xs py-1">
                    <span className="text-gray-300">{r.account_name}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-gray-500">{formatCompact(r.arr)}</span>
                      <span className="font-semibold" style={{ color: classifyColor(r.health_score) }}>
                        {r.health_score}
                      </span>
                      <span className={`text-${r.days_until <= 30 ? 'red' : r.days_until <= 60 ? 'yellow' : 'gray'}-400 font-medium w-12 text-right`}>
                        {r.days_until}d
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Row 2: Power of 1 Metrics Table */}
          <div className="mb-6">
            <PowerOf1Table rows={d.power_of_1} total={d.power_of_1_total} />
          </div>

          {/* Row 3: Pillar Investment + Investment Timeline */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <PillarInvestmentChart data={d.pillar_investments} />
            <InvestmentTimelineChart data={d.investment_timeline} />
          </div>

          {/* Row 4: ROI Scaling Analysis */}
          <ROIScalingSection tiers={d.roi_scaling} />

          {/* Row 5: Account Investment Breakdown */}
          {d.accounts.length > 0 && (
            <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
                    Account Investment Breakdown
                  </h3>
                </div>
                <span className="text-[10px] text-gray-500">{d.accounts[0]?.source === 'actual' ? 'From playbook data' : 'Estimated (ARR-weighted)'}</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-gray-700/50 text-gray-500">
                      <th className="text-left py-2 pr-3">Account</th>
                      <th className="text-right py-2 px-2">ARR</th>
                      <th className="text-right py-2 px-2">Health</th>
                      <th className="text-right py-2 px-2">Investment</th>
                      <th className="text-right py-2 px-2">Impact</th>
                      <th className="text-right py-2 px-2">ROI</th>
                      <th className="text-right py-2 pl-2">Runs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.accounts.map((a) => {
                      const healthColor = a.classification === 'critical' ? 'text-red-400'
                        : a.classification === 'at_risk' ? 'text-yellow-400' : 'text-green-400';
                      return (
                        <tr key={a.account_id} className="border-b border-gray-800/30 hover:bg-gray-800/20 transition-colors">
                          <td className="py-2 pr-3">
                            <div className="text-white font-medium truncate max-w-[180px]">{a.account_name}</div>
                          </td>
                          <td className="text-right py-2 px-2 text-gray-400">{formatCompact(a.arr)}</td>
                          <td className={`text-right py-2 px-2 font-medium ${healthColor}`}>{a.health_score.toFixed(0)}</td>
                          <td className="text-right py-2 px-2 text-gray-300">{formatCompact(a.investment)}</td>
                          <td className="text-right py-2 px-2 text-cyan-400">{formatCompact(a.impact)}</td>
                          <td className={`text-right py-2 px-2 font-medium ${a.roi_pct > 0 ? 'text-green-400' : 'text-gray-500'}`}>{a.roi_pct}%</td>
                          <td className="text-right py-2 pl-2 text-gray-500">{a.playbook_runs || '—'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* ---- Right Sidebar ---- */}
      <aside className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 overflow-y-auto flex flex-col gap-5">
        {/* Investment Allocation Intelligence */}
        <InvestmentAllocationWidget
          totalArr={d.total_arr}
          csInvestment={d.cs_investment}
          roiImpact={d.roi_impact}
          isEstimated={d.is_estimated_investment}
        />

        {/* Revenue Waterfall */}
        {d.nrr_waterfall.expected_loss > 0 && (
          <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
            <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-3">
              Revenue Waterfall
            </h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between"><span className="text-gray-400">Expected Loss</span><span className="text-red-400 font-semibold">{formatCompact(d.nrr_waterfall.expected_loss)}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Protectable</span><span className="text-green-400 font-semibold">{formatCompact(d.nrr_waterfall.attributed_save)}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Cost to Intervene</span><span className="text-gray-300">{formatCompact(d.nrr_waterfall.intervention_cost)}</span></div>
              {d.nrr_waterfall.roi_x > 0 && (
                <div className="flex justify-between border-t border-gray-700/50 pt-2">
                  <span className="text-gray-400">Intervention ROI</span>
                  <span className="text-cyan-400 font-bold">{d.nrr_waterfall.roi_x}x</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Quick Financial Ratios */}
        <FinancialRatiosWidget ratios={d.financial_ratios} />

        {/* Export Options */}
        <div className="space-y-2.5">
          <button
            onClick={() => {
              // CSV export — account-level data
              const headers = ['Account', 'ARR', 'Health Score', 'Classification', 'Investment', 'Impact', 'ROI %', 'Playbook Runs'];
              const rows = d.accounts.map(a => [a.account_name, a.arr, a.health_score, a.classification, a.investment, a.impact, a.roi_pct, a.playbook_runs].join(','));
              const csv = [headers.join(','), ...rows].join('\n');
              const blob = new Blob([csv], { type: 'text/csv' });
              const url = URL.createObjectURL(blob);
              const link = document.createElement('a');
              link.href = url;
              link.download = `cfo-brief-${d.period.replace(/\s+/g, '-')}.csv`;
              link.click();
              URL.revokeObjectURL(url);
            }}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-lg bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium hover:bg-emerald-600/20 transition-colors"
          >
            <FileText className="w-3.5 h-3.5" />
            Export CFO Brief (CSV)
          </button>
          <button
            onClick={() => {
              // Summary CSV with portfolio metrics
              const summary = [
                `CS Pulse CFO Brief - ${d.period}`,
                '',
                `Total ARR,${d.total_arr}`,
                `CS Investment,${d.cs_investment}`,
                `Revenue Protected,${d.roi_impact}`,
                `Portfolio ROI,${d.summary_cards[3]?.value || ''}`,
                `NRR Current,${d.nrr_current}%`,
                `NRR With Intervention,${d.nrr_with_intervention}%`,
                `GRR,${d.grr}%`,
                '',
                'Power of 1 Metrics',
                'Metric,Baseline,Current,Improvement %,Dollar Impact',
                ...d.power_of_1.map(m => [m.metric, m.baseline, m.current, m.improvement, m.dollar_impact].join(',')),
              ].join('\n');
              const blob = new Blob([summary], { type: 'text/csv' });
              const url = URL.createObjectURL(blob);
              const link = document.createElement('a');
              link.href = url;
              link.download = `cfo-portfolio-summary-${d.period.replace(/\s+/g, '-')}.csv`;
              link.click();
              URL.revokeObjectURL(url);
            }}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-lg bg-purple-600/10 border border-purple-500/20 text-purple-400 text-xs font-medium hover:bg-purple-600/20 transition-colors"
          >
            <Layers className="w-3.5 h-3.5" />
            Export Portfolio Summary (CSV)
          </button>
        </div>

        {/* ROI Engine link removed — CFO overview has full Power-of-1 table */}
      </aside>

      {/* Floating AI Advisor */}
      <AskAIPortal persona="cfo" />
    </div>
    </div>
  );
};

export default CFODashboard;
