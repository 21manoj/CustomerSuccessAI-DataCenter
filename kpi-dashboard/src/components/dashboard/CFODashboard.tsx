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
  Users, Eye, Zap, GitBranch, Clock, AlertTriangle
} from 'lucide-react';
import { classify, classifyColor, thresholdValues } from '../../utils/healthThresholds';
import DashboardTopBar from './DashboardTopBar';
import { useSession } from '../../contexts/SessionContext';
import { apiCall, getCustomerIdentifier } from '../../utils/api';
import AskAIPortal from '../ai/AskAIPortal';

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
    { id: 'roi-engine', label: 'ROI Engine', path: '/cro-dashboard?view=roi-engine', badge: null, icon: <Zap className="w-4 h-4" /> },
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
  const chartData = data.map((p, i) => ({
    name: p.pillar_code,
    investment: p.investment / 1000,
    impact: p.impact / 1000,
    roi: p.roi_multiplier,
    fill: PILLAR_COLORS[i % PILLAR_COLORS.length],
  }));

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <PieChart className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
            Pillar Investment Breakdown
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
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={30}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#1a1f2e', border: '1px solid #374151', borderRadius: 8, fontSize: 12, color: '#fff' }}
            formatter={(value: number, name: string) => [`$${value}K`, name === 'investment' ? 'Investment' : 'Impact']}
          />
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 10, color: '#9ca3af' }}
          />
          <Bar dataKey="investment" name="Investment" fill="#f97316" radius={[0, 3, 3, 0]} barSize={10} />
          <Bar dataKey="impact" name="Impact" fill="#22c55e" radius={[0, 3, 3, 0]} barSize={10} />
        </BarChart>
      </ResponsiveContainer>
      {/* ROI multipliers below */}
      <div className="flex justify-between mt-3 px-1">
        {data.map((p, i) => (
          <div key={p.pillar_code} className="text-center">
            <p className="text-[10px] text-gray-500">{p.pillar_code}</p>
            <p className="text-xs font-bold" style={{ color: PILLAR_COLORS[i % PILLAR_COLORS.length] }}>
              {p.roi_multiplier}x
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

/** Investment Timeline - area chart */
const InvestmentTimelineChart: React.FC<{ data: InvestmentTimelinePoint[] }> = ({ data }) => {
  const chartData = data.map((d) => ({
    month: d.month,
    Investment: d.investment / 1000,
    Return: d.returns / 1000,
  }));

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
            Investment Timeline
          </h3>
        </div>
        <span className="text-[10px] text-gray-500">6-month window</span>
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
            formatter={(value: number) => [`$${value}K`]}
          />
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 10, color: '#9ca3af' }}
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
        Same playbooks. Same platform. Non-linear returns.
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
              {/* Growth bar */}
              <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
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
      <p className="text-[10px] text-gray-600 text-center leading-relaxed">
        CS Pulse platform costs remain fixed while revenue impact compounds across accounts.
        Each additional account adds marginal cost but full playbook value.
      </p>
    </div>
  );
};

/** Investment Efficiency gauge (right sidebar) */
const EfficiencyGauge: React.FC<{
  score: number;
  automationRate: number;
  timeSaved: number;
  costPerProtected: number;
}> = ({ score, automationRate, timeSaved, costPerProtected }) => {
  const circumference = 2 * Math.PI * 40;
  const progress = (score / 100) * circumference;

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
      <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-4">
        Investment Efficiency
      </h3>
      {/* Gauge */}
      <div className="flex justify-center mb-4">
        <div className="relative w-24 h-24">
          <svg className="w-24 h-24 -rotate-90" viewBox="0 0 96 96">
            <circle cx="48" cy="48" r="40" fill="none" stroke="#1f2937" strokeWidth="6" />
            <circle
              cx="48"
              cy="48"
              r="40"
              fill="none"
              stroke="#10b981"
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={circumference - progress}
              className="transition-all duration-1000"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-emerald-400">{score}</span>
            <span className="text-[9px] text-gray-500">/ 100</span>
          </div>
        </div>
      </div>
      {/* Stats */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-gray-500">Automation Rate</span>
          <span className="text-xs font-semibold text-emerald-400">{automationRate}%</span>
        </div>
        <div className="w-full h-1 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-all"
            style={{ width: `${automationRate}%` }}
          />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-gray-500">Time Saved</span>
          <span className="text-xs font-medium text-gray-300">{timeSaved} hrs/mo</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-gray-500">Cost per Protected $</span>
          <span className="text-xs font-medium text-cyan-400">${costPerProtected.toFixed(2)}</span>
        </div>
      </div>
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
          const rawCsInvestment = json.cs_investment || json.roi_investment || 0;
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
            P1: 'Deployment Velocity', P2: 'Operational Stability', P3: 'AI Workload Perf',
            P4: 'Channel & Partner', P5: 'Expansion Readiness',
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
          const revPerDollar = csInvestment > 0 ? ((json.revenue_protected || 0) / csInvestment).toFixed(1) : '0';
          const paybackMonths = json.payback_months || (roiImpact > 0 ? Math.round((csInvestment / roiImpact) * 12) : 0);

          const transformed: CFODashboardData = {
            summary_cards: [
              { label: 'Total ARR', value: formatCompact(totalArr), subtitle: `${json.roi_scaling?.current_accounts || json.account_count || '—'} active accounts`, accent: 'white' },
              { label: 'CS Investment', value: formatCompact(csInvestment), subtitle: isEstimatedInvestment ? 'Power-of-1 benchmark estimate' : 'Playbook execution cost', tag: json.automation_rate ? `${json.automation_rate}% automated` : undefined, accent: 'emerald', estimated: isEstimatedInvestment },
              { label: 'Revenue Protected', value: formatCompact(json.revenue_protected || 0), subtitle: `GRR: ${grr}%`, accent: 'green' },
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
            cost_per_protected_dollar: csInvestment > 0 && (json.revenue_protected || 0) > 0
              ? parseFloat((csInvestment / (json.revenue_protected || 1)).toFixed(3))
              : 0.05,
            financial_ratios: [
              { label: 'CS % of ARR', value: `${csPercent}%${isEstimatedInvestment ? ' *' : ''}` },
              { label: 'Rev per CS Dollar', value: `$${revPerDollar}${isEstimatedInvestment ? ' *' : ''}` },
              { label: 'Payback Period', value: `${paybackMonths} months${isEstimatedInvestment ? ' *' : ''}` },
              { label: 'NRR Impact / Playbook', value: `+${((nrr - 100) / Math.max(scalingProjs[0]?.accounts || 15, 1)).toFixed(2)}%`, accent: 'cyan' },
              ...(isEstimatedInvestment ? [{ label: '* Based on benchmark estimate', value: '', accent: 'gray' }] : []),
            ],
            period: json.quarter_label || 'Q1 2026',
            last_updated: json.last_updated || new Date().toISOString(),
          };
          setData(transformed);
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

          {/* Row 1: Financial summary cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            {d.summary_cards.map((card, i) => (
              <SummaryCardComponent key={i} card={card} />
            ))}
          </div>

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
        </div>
      </main>

      {/* ---- Right Sidebar ---- */}
      <aside className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 overflow-y-auto flex flex-col gap-5">
        {/* Investment Efficiency Score */}
        <EfficiencyGauge
          score={d.efficiency_score}
          automationRate={d.automation_rate}
          timeSaved={d.time_saved_hours}
          costPerProtected={d.cost_per_protected_dollar}
        />

        {/* Quick Financial Ratios */}
        <FinancialRatiosWidget ratios={d.financial_ratios} />

        {/* Export Options */}
        <div className="space-y-2.5">
          <button className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-lg bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium hover:bg-emerald-600/20 transition-colors">
            <FileText className="w-3.5 h-3.5" />
            Export CFO Brief
          </button>
          <button className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-lg bg-purple-600/10 border border-purple-500/20 text-purple-400 text-xs font-medium hover:bg-purple-600/20 transition-colors">
            <Layers className="w-3.5 h-3.5" />
            Generate Board Deck
          </button>
        </div>

        {/* Link to ROI Engine */}
        <button
          onClick={() => navigate('/dc-dashboard?tab=roi')}
          className="flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-cyan-600/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium hover:bg-cyan-600/20 transition-colors"
        >
          <Zap className="w-3.5 h-3.5" />
          Open ROI Engine
          <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
      </aside>

      {/* Floating AI Advisor */}
      <AskAIPortal persona="cfo" />
    </div>
    </div>
  );
};

export default CFODashboard;
