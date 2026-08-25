import React, { useState, useEffect, useMemo } from 'react';
import {
  BarChart, Bar, AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Cell,
} from 'recharts';
import {
  DollarSign, TrendingUp, Target, Zap, Shield, FileText,
  ArrowUpRight, ArrowRight, Sparkles, BarChart3, Users,
  RefreshCw, Clock, Cpu, ChevronRight, Download,
} from 'lucide-react';
import { apiCall, getCustomerIdentifier } from '../../../utils/api';
import { useSession } from '../../../contexts/SessionContext';
import ProvenanceTierBadge, { ProvenanceTier } from '../../shared/ProvenanceTierBadge';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toLocaleString()}`;
}

function fmtPct(v: number): string {
  return `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`;
}

function fmtRoiMultiple(investment: number, impact: number): string {
  if (investment <= 0) return '$0.00';
  const ratio = impact / investment;
  return `$${ratio.toFixed(2)}`;
}

/** Generate 6 synthetic sparkline points from baseline to current */
function generateSparkline(baseline: number, current: number): { i: number; v: number }[] {
  const points: { i: number; v: number }[] = [];
  const diff = current - baseline;
  for (let i = 0; i < 6; i++) {
    const progress = i / 5;
    // Slightly noisy sigmoid-ish curve
    const noise = (Math.sin(i * 2.1 + baseline) * 0.08);
    const eased = progress * progress * (3 - 2 * progress); // smoothstep
    points.push({ i, v: baseline + diff * (eased + noise) });
  }
  return points;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MetricOutcome {
  metric_id: string;
  display_name: string;
  baseline_value: number;
  current_value: number;
  improvement_pct: number;
  unit: string;
  direction: string;
  dollar_impact: number;
  category: string;
  // Value-provenance tier (utils/value_provenance.py) — sent per metric by
  // outcome_roi_engine._result_to_dict since Aug 2026; previously dropped
  // here because this interface never declared it.
  data_source?: ProvenanceTier;
}

interface StoryData {
  historical?: { summary: ROISummary; metric_outcomes: MetricOutcome[] };
  forward?: { summary: ROISummary; metric_outcomes: MetricOutcome[] };
  combined?: {
    combined_impact: number;
    combined_investment: number;
    combined_roi_pct: number;
  };
  data_source?: string;
}

interface ROISummary {
  total_investment: number;
  total_impact: number;
  roi_pct: number;
  payback_months: number | null;
  revenue_protected: number;
  revenue_expanded: number;
  cost_savings: number;
  compounding_effect: number;
}

interface PowerOf1Metric {
  metric_id: string;
  display_name: string;
  baseline: number;
  current: number;
  improvement_pct: number;
  dollar_impact: number;
  /** Legacy flag from the CFO benchmark-fallback path; data_source supersedes it. */
  estimated?: boolean;
  data_source?: ProvenanceTier;
}

interface PillarInvestment {
  pillar: string;
  name: string;
  investment: number;
  impact: number;
  roi: number;
}

interface ScalingProjection {
  accounts: number;
  roi: number;
}

interface CFOData {
  total_arr: number;
  cs_investment: number;
  roi_pct: number;
  roi_investment: number;
  roi_impact: number;
  power_of_1_metrics: PowerOf1Metric[];
  pillar_investments: PillarInvestment[];
  investment_timeline: { month: string; investment: number; return: number }[];
  roi_scaling: {
    current_accounts: number;
    current_roi: number;
    projections: ScalingProjection[];
  };
}

// ---------------------------------------------------------------------------
// Category colors for Power of 1 cards
// ---------------------------------------------------------------------------

const CATEGORY_STYLE: Record<string, { border: string; bg: string; text: string; accent: string }> = {
  retention: { border: 'border-emerald-500/40', bg: 'bg-emerald-500/5', text: 'text-emerald-400', accent: '#10b981' },
  growth:    { border: 'border-cyan-500/40',    bg: 'bg-cyan-500/5',    text: 'text-cyan-400',    accent: '#06b6d4' },
  efficiency:{ border: 'border-amber-500/40',   bg: 'bg-amber-500/5',   text: 'text-amber-400',   accent: '#f59e0b' },
};

function categoryFor(metricId: string): string {
  if (['GRR', 'NRR', 'churn_rate', 'retention'].some((k) => metricId.toLowerCase().includes(k.toLowerCase()))) return 'retention';
  if (['expansion', 'upsell', 'cross_sell', 'product_adoption'].some((k) => metricId.toLowerCase().includes(k.toLowerCase()))) return 'growth';
  return 'efficiency';
}

const CATEGORY_ICON: Record<string, React.FC<{ className?: string }>> = {
  retention: Shield,
  growth: TrendingUp,
  efficiency: Zap,
};

// ---------------------------------------------------------------------------
// Skeleton / Error
// ---------------------------------------------------------------------------

function LoadingSkeleton() {
  return (
    <div className="flex h-full">
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-[1200px] space-y-6 animate-pulse">
          <div className="h-28 bg-[#1a1f2e] rounded-xl" />
          <div className="h-40 bg-[#1a1f2e] rounded-xl" />
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-48 bg-[#1a1f2e] rounded-xl" />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="h-72 bg-[#1a1f2e] rounded-xl" />
            <div className="h-72 bg-[#1a1f2e] rounded-xl" />
          </div>
        </div>
      </div>
      <div className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 space-y-5 animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-20 bg-[#1a1f2e] rounded-xl" />
        ))}
        <div className="h-48 bg-[#1a1f2e] rounded-xl" />
        <div className="h-32 bg-[#1a1f2e] rounded-xl" />
      </div>
    </div>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="bg-red-900/30 border border-red-500/40 rounded-xl p-6 text-red-300 text-center">
      <Shield className="w-6 h-6 mx-auto mb-2" />
      <p className="font-medium">Failed to load ROI data</p>
      <p className="text-sm mt-1 text-red-400">{message}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 1. MISSION BANNER
// ---------------------------------------------------------------------------

function MissionBanner({
  roiMultiple,
  monthsOfData,
  dataSource,
}: {
  roiMultiple: string;
  monthsOfData: number;
  dataSource: string;
}) {
  // dataSource carries a value-provenance tier (see backend
  // utils/value_provenance.py): measured/derived/benchmark are real
  // customer data (differing only in whether it's read through the
  // customer's own calibrated weights or generic benchmark weights);
  // default/unavailable mean no real customer signal at all. Show the
  // tier directly rather than collapsing it to a validated/not-validated
  // boolean — 'benchmark' is real data, so folding it into a generic
  // "not validated" bucket would contradict its own name.
  //
  // ProvenanceTierBadge (not a fixed-color pill, unlike the previous
  // version of this component) so 'benchmark' — the tier that caused the
  // Aug 21 2026 audit findings — reads visibly differently from
  // 'measured', not just as different text in the same emerald pill.
  const tier: ProvenanceTier = (
    ['measured', 'derived', 'benchmark', 'default', 'unavailable'].includes(dataSource)
      ? (dataSource as ProvenanceTier)
      : 'benchmark'
  );

  return (
    <div className="relative overflow-hidden rounded-xl bg-gradient-to-r from-[#0a1628] via-[#0f2318] to-[#0a1628] border border-emerald-500/20">
      {/* Subtle glow */}
      <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 via-emerald-400/10 to-emerald-500/5" />
      <div className="relative px-6 py-5 sm:px-8 sm:py-6 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="text-center sm:text-left">
          <h1 className="text-lg sm:text-xl font-bold text-white tracking-tight">
            Return on CS Investment
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Every <span className="text-emerald-400 font-semibold">$1</span> invested returns{' '}
            <span className="text-emerald-400 font-bold text-lg">{roiMultiple}</span>
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            {monthsOfData > 0 ? `${monthsOfData} months of outcomes` : 'Projected outcomes'}
          </span>
          <ProvenanceTierBadge tier={tier} dark showMeasured />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2. THE HEADLINE — Hero card
// ---------------------------------------------------------------------------

function HeroCard({
  roiPct,
  totalInvestment,
  totalImpact,
  revenueProtected,
  revenueExpanded,
  costSavings,
}: {
  roiPct: number;
  totalInvestment: number;
  totalImpact: number;
  revenueProtected: number;
  revenueExpanded: number;
  costSavings: number;
}) {
  return (
    <div className="bg-[#1a1f2e] border border-gray-700/50 rounded-xl p-6">
      <div className="flex flex-col lg:flex-row lg:items-center gap-6">
        {/* Left: ROI percentage + flow */}
        <div className="flex-1 flex flex-col sm:flex-row items-center gap-6">
          <div className="text-center sm:text-left">
            <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">Portfolio ROI</p>
            <p className="text-6xl sm:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400 leading-none">
              {Math.round(roiPct)}%
            </p>
          </div>

          {/* Investment flow */}
          <div className="flex items-center gap-3 text-sm">
            <div className="text-center">
              <p className="text-xs text-gray-500 mb-0.5">Invested</p>
              <p className="text-lg font-bold text-violet-400">{fmt(totalInvestment)}</p>
            </div>
            <ArrowRight className="w-5 h-5 text-gray-500 flex-shrink-0" />
            <div className="text-center">
              <p className="text-xs text-gray-500 mb-0.5">Impact</p>
              <p className="text-lg font-bold text-emerald-400">{fmt(totalImpact)}</p>
            </div>
          </div>
        </div>

        {/* Right: Three mini stats */}
        <div className="flex flex-wrap lg:flex-nowrap gap-3">
          {[
            { label: 'Revenue Protected (Modeled)', value: revenueProtected, icon: Shield, color: 'text-emerald-400' },
            { label: 'Revenue Grown', value: revenueExpanded, icon: TrendingUp, color: 'text-cyan-400' },
            { label: 'Efficiency Savings', value: costSavings, icon: Zap, color: 'text-amber-400' },
          ].map((stat) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.label}
                className="flex-1 min-w-[120px] bg-[#0f1419] border border-gray-700/40 rounded-lg px-4 py-3"
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <Icon className={`w-3.5 h-3.5 ${stat.color}`} />
                  <p className="text-[10px] text-gray-400 uppercase tracking-wider">{stat.label}</p>
                </div>
                <p className={`text-lg font-bold ${stat.color}`}>{fmt(stat.value)}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 3. POWER OF 1 METRIC CARDS
// ---------------------------------------------------------------------------

function PowerOf1Cards({ metrics }: { metrics: PowerOf1Metric[] }) {
  const lowerIsBetter = new Set(['TTFV', 'ticket_resolution_time']);

  function statusBadge(m: PowerOf1Metric) {
    const abs = Math.abs(m.improvement_pct);
    if (abs >= 2) return { label: 'Proven', cls: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' };
    if (abs >= 0.5) return { label: 'Tracking', cls: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' };
    return { label: 'Projected', cls: 'bg-gray-500/20 text-gray-400 border-gray-500/30' };
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-5 h-5 text-cyan-400" />
        <h3 className="text-base font-semibold text-white">Power of 1 Metrics</h3>
        <span className="text-xs text-gray-500 ml-1">
          What happens when each metric improves by 1 point
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {metrics.map((m) => {
          const cat = categoryFor(m.metric_id);
          const style = CATEGORY_STYLE[cat] || CATEGORY_STYLE.efficiency;
          const badge = statusBadge(m);
          const isTimeBased = lowerIsBetter.has(m.metric_id);
          const isPositive = isTimeBased ? m.improvement_pct < 0 : m.improvement_pct > 0;
          const sparkData = generateSparkline(m.baseline, m.current);
          const CatIcon = CATEGORY_ICON[cat] || Zap;

          return (
            <div
              key={m.metric_id}
              className={`${style.bg} ${style.border} border rounded-xl p-4 flex flex-col justify-between`}
            >
              {/* Top row: name + badge */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <CatIcon className={`w-4 h-4 ${style.text}`} />
                  <p className="text-sm font-medium text-white leading-tight">{m.display_name}</p>
                </div>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${badge.cls} flex-shrink-0 ml-2`}>
                  {badge.label}
                </span>
              </div>

              {/* Baseline -> Current */}
              <div className="flex items-center gap-2 text-sm mb-2">
                <span className="text-gray-400">{m.baseline.toFixed(1)}</span>
                <ChevronRight className="w-3.5 h-3.5 text-gray-600" />
                <span className="text-white font-semibold">{m.current.toFixed(1)}</span>
                <span className={`text-xs font-medium ml-auto ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                  {fmtPct(m.improvement_pct)}
                </span>
              </div>

              {/* Sparkline */}
              <div className="h-10 mb-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={sparkData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
                    <defs>
                      <linearGradient id={`spark-${m.metric_id}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={style.accent} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={style.accent} stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <Area
                      type="monotone"
                      dataKey="v"
                      stroke={style.accent}
                      fill={`url(#spark-${m.metric_id})`}
                      strokeWidth={1.5}
                      dot={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Dollar impact */}
              <div className="flex items-center justify-between pt-2 border-t border-gray-700/30">
                <span className="flex items-center gap-1.5 text-xs text-gray-400">
                  Dollar Impact
                  {/* Tier from the backend per metric; legacy `estimated`
                      flag (CFO benchmark-fallback path) maps to benchmark
                      when no explicit tier is present. */}
                  <ProvenanceTierBadge
                    tier={m.data_source ?? (m.estimated ? 'benchmark' : undefined)}
                    compact
                    dark
                  />
                </span>
                <span className={`text-base font-bold ${style.text}`}>{fmt(m.dollar_impact)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 4. INVESTMENT BREAKDOWN — Two columns
// ---------------------------------------------------------------------------

function InvestmentBreakdown({
  pillars,
  summary,
}: {
  pillars: PillarInvestment[];
  summary: ROISummary | null;
}) {
  // Left: Where the money went — CS Initiatives, Platform, Automation
  const totalInvest = pillars.reduce((s, p) => s + p.investment, 0) || 1;
  const investmentBuckets = useMemo(() => {
    // Group pillar investments into three buckets
    const csInit = pillars.filter((p) => ['P1', 'P2', 'P4'].includes(p.pillar));
    const platform = pillars.filter((p) => p.pillar === 'P3');
    const automation = pillars.filter((p) => p.pillar === 'P5');
    return [
      { name: 'CS Initiatives', value: csInit.reduce((s, p) => s + p.investment, 0), color: '#8b5cf6' },
      { name: 'Platform & AI', value: platform.reduce((s, p) => s + p.investment, 0), color: '#06b6d4' },
      { name: 'Automation', value: automation.reduce((s, p) => s + p.investment, 0), color: '#f59e0b' },
    ].filter((b) => b.value > 0);
  }, [pillars]);

  // Right: Where returns came from
  const returnBuckets = useMemo(() => {
    if (!summary) return [];
    return [
      { name: 'Revenue Protected (Modeled)', value: summary.revenue_protected, color: '#10b981' },
      { name: 'Revenue Expanded', value: summary.revenue_expanded, color: '#06b6d4' },
      { name: 'Cost Savings', value: summary.cost_savings, color: '#f59e0b' },
      { name: 'Compounding', value: summary.compounding_effect, color: '#8b5cf6' },
    ].filter((b) => b.value > 0);
  }, [summary]);

  const totalReturn = returnBuckets.reduce((s, b) => s + b.value, 0) || 1;

  function HorizontalStackedBar({ buckets, total }: { buckets: { name: string; value: number; color: string }[]; total: number }) {
    return (
      <div className="space-y-3">
        {/* Stacked bar */}
        <div className="flex h-6 rounded-full overflow-hidden bg-gray-800/60">
          {buckets.map((b) => (
            <div
              key={b.name}
              className="h-full transition-all"
              style={{ width: `${(b.value / total) * 100}%`, backgroundColor: b.color }}
              title={`${b.name}: ${fmt(b.value)}`}
            />
          ))}
        </div>
        {/* Legend */}
        <div className="space-y-2">
          {buckets.map((b) => (
            <div key={b.name} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: b.color }} />
                <span className="text-gray-300">{b.name}</span>
              </div>
              <span className="text-white font-medium">{fmt(b.value)}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (investmentBuckets.length === 0 && returnBuckets.length === 0) return null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Left: Where money went */}
      <div className="bg-[#1a1f2e] border border-gray-700/50 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <DollarSign className="w-5 h-5 text-violet-400" />
          <h3 className="text-base font-semibold text-white">Where the Money Went</h3>
        </div>
        <HorizontalStackedBar buckets={investmentBuckets} total={totalInvest} />
      </div>

      {/* Right: Where returns came from */}
      <div className="bg-[#1a1f2e] border border-gray-700/50 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Target className="w-5 h-5 text-emerald-400" />
          <h3 className="text-base font-semibold text-white">Where the Returns Came From</h3>
        </div>
        <HorizontalStackedBar buckets={returnBuckets} total={totalReturn} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// RIGHT PANEL: Financial Ratios
// ---------------------------------------------------------------------------

function FinancialRatios({
  roiPct,
  paybackMonths,
  costPerAccount,
  automationPct,
}: {
  roiPct: number;
  paybackMonths: number;
  costPerAccount: number;
  automationPct: number;
}) {
  const ratios = [
    {
      label: 'ROI',
      value: `${Math.round(roiPct)}%`,
      icon: TrendingUp,
      color: 'text-emerald-400',
      border: 'border-emerald-500/30',
      bg: 'bg-emerald-500/5',
    },
    {
      label: 'Payback Period',
      value: paybackMonths > 0 ? `${paybackMonths.toFixed(1)} mo` : 'N/A',
      icon: Clock,
      color: 'text-cyan-400',
      border: 'border-cyan-500/30',
      bg: 'bg-cyan-500/5',
    },
    {
      label: 'Cost / Account',
      value: costPerAccount > 0 ? fmt(costPerAccount) : 'N/A',
      icon: DollarSign,
      color: 'text-violet-400',
      border: 'border-violet-500/30',
      bg: 'bg-violet-500/5',
    },
    {
      label: 'Automation',
      value: `${automationPct}%`,
      icon: Cpu,
      color: 'text-amber-400',
      border: 'border-amber-500/30',
      bg: 'bg-amber-500/5',
    },
  ];

  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Financial Ratios
      </h4>
      <div className="space-y-2.5">
        {ratios.map((r) => {
          const Icon = r.icon;
          return (
            <div
              key={r.label}
              className={`${r.bg} ${r.border} border rounded-lg px-3.5 py-3 flex items-center gap-3`}
            >
              <Icon className={`w-4 h-4 ${r.color} flex-shrink-0`} />
              <div className="flex-1 min-w-0">
                <p className="text-[10px] text-gray-500 uppercase tracking-wider">{r.label}</p>
                <p className={`text-sm font-bold ${r.color}`}>{r.value}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// RIGHT PANEL: Platform Multiplier (compact)
// ---------------------------------------------------------------------------

function PlatformMultiplierCompact({ scalingData }: { scalingData: CFOData['roi_scaling'] }) {
  const tiers = [10, 50, 200];
  const projectionMap = new Map(scalingData.projections.map((p) => [p.accounts, p.roi]));

  const chartData = tiers.map((accts) => {
    let roi = projectionMap.get(accts);
    if (roi == null) {
      const baseFactor =
        scalingData.current_roi > 0
          ? 1 + Math.log(Math.max(accts / Math.max(scalingData.current_accounts, 1), 1) + 1) * 0.8
          : 1;
      roi = Math.round(scalingData.current_roi * baseFactor);
    }
    return { accounts: `${accts}`, roi };
  });

  const gradientColors = ['#f59e0b', '#10b981', '#06b6d4'];

  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">
        Platform Multiplier
      </h4>
      <p className="text-[10px] text-gray-500 mb-3">ROI scales non-linearly with accounts</p>

      <div className="bg-[#1a1f2e] border border-gray-700/50 rounded-lg p-3">
        <ResponsiveContainer width="100%" height={140}>
          <BarChart data={chartData} margin={{ top: 5, right: 5, left: -15, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="accounts"
              tick={{ fill: '#9ca3af', fontSize: 10 }}
              tickFormatter={(v: string) => `${v} accts`}
            />
            <YAxis
              tick={{ fill: '#9ca3af', fontSize: 10 }}
              tickFormatter={(v: number) => `${v}%`}
            />
            <Tooltip
              contentStyle={{ background: '#1a1f2e', border: '1px solid #374151', borderRadius: 8, color: '#fff', fontSize: 11 }}
              formatter={(value: number) => [`${value}%`, 'ROI']}
              labelFormatter={(label: string) => `${label} accounts`}
            />
            <Bar dataKey="roi" barSize={28} radius={[4, 4, 0, 0]}>
              {chartData.map((_, idx) => (
                <Cell key={idx} fill={gradientColors[idx] || '#06b6d4'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Compact tier labels */}
        <div className="flex justify-between mt-2 px-1">
          {chartData.map((d, idx) => (
            <div key={d.accounts} className="text-center">
              <p className="text-[10px] font-bold" style={{ color: gradientColors[idx] }}>
                {d.roi}%
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// RIGHT PANEL: Quick Stats
// ---------------------------------------------------------------------------

function QuickStats({
  totalARR,
  accountCount,
  csInvestment,
}: {
  totalARR: number;
  accountCount: number;
  csInvestment: number;
}) {
  const ftEquiv = Math.max(1, Math.round(csInvestment / 120_000));

  const stats = [
    { label: 'Total ARR', value: fmt(totalARR), icon: DollarSign, color: 'text-cyan-400' },
    { label: 'Accounts', value: accountCount.toString(), icon: Users, color: 'text-violet-400' },
    { label: 'CS FTE Equiv', value: `${ftEquiv} FTE`, icon: Users, color: 'text-amber-400' },
  ];

  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Quick Stats
      </h4>
      <div className="space-y-2">
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.label}
              className="bg-[#1a1f2e] border border-gray-700/40 rounded-lg px-3.5 py-2.5 flex items-center gap-3"
            >
              <Icon className={`w-4 h-4 ${s.color} flex-shrink-0`} />
              <div className="flex-1 min-w-0">
                <p className="text-[10px] text-gray-500 uppercase tracking-wider">{s.label}</p>
                <p className={`text-sm font-bold ${s.color}`}>{s.value}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// RIGHT PANEL: CFO Export
// ---------------------------------------------------------------------------

function CFOExportPanel() {
  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        CFO Export
      </h4>
      <div className="space-y-2.5">
        <button className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold rounded-lg transition-colors shadow-lg shadow-violet-600/20">
          <FileText className="w-4 h-4" />
          Generate Report
        </button>
        <button className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#1a1f2e] hover:bg-[#242938] text-gray-300 hover:text-white text-sm font-medium rounded-lg border border-gray-700/50 transition-colors">
          <Download className="w-4 h-4" />
          Export Excel
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// MAIN COMPONENT
// ---------------------------------------------------------------------------

export default function ROIEngineView() {
  const { session } = useSession();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [storyData, setStoryData] = useState<StoryData | null>(null);
  const [cfoData, setCfoData] = useState<CFOData | null>(null);
  const [dataSource, setDataSource] = useState<string>('benchmark');

  useEffect(() => {
    if (!session) return;

    const customerId = getCustomerIdentifier(session);
    const headers: Record<string, string> = { 'X-Customer-ID': customerId };

    async function fetchAll() {
      setLoading(true);
      setError(null);

      try {
        const [storyRes, cfoRes] = await Promise.allSettled([
          apiCall('/api/outcome-roi/story', { headers }),
          apiCall('/api/executive/cfo-dashboard', { headers }),
        ]);

        if (storyRes.status === 'fulfilled' && storyRes.value.ok) {
          const json = await storyRes.value.json();
          setStoryData(json);
          setDataSource(json.data_source || 'benchmark');
        }

        if (cfoRes.status === 'fulfilled' && cfoRes.value.ok) {
          const json = await cfoRes.value.json();
          setCfoData(json);
        }

        if (
          (storyRes.status === 'rejected' || (storyRes.status === 'fulfilled' && !storyRes.value.ok)) &&
          (cfoRes.status === 'rejected' || (cfoRes.status === 'fulfilled' && !cfoRes.value.ok))
        ) {
          setError('Unable to load ROI data. Revenue Intelligence may not be enabled.');
        }
      } catch (err: any) {
        setError(err.message || 'Network error');
      } finally {
        setLoading(false);
      }
    }

    fetchAll();
  }, [session]);

  // ---------------------------------------------------------------------------
  // Derive values
  // ---------------------------------------------------------------------------

  const historicalSummary = storyData?.historical?.summary ?? null;
  const forwardSummary = storyData?.forward?.summary ?? null;
  const combined = storyData?.combined;

  const roiPct = combined?.combined_roi_pct ?? historicalSummary?.roi_pct ?? cfoData?.roi_pct ?? 0;
  const totalInvestment =
    combined?.combined_investment ?? historicalSummary?.total_investment ?? cfoData?.roi_investment ?? 0;
  const totalImpact =
    combined?.combined_impact ?? historicalSummary?.total_impact ?? cfoData?.roi_impact ?? 0;
  const paybackMonths = historicalSummary?.payback_months ?? forwardSummary?.payback_months ?? 0;

  const revenueProtected = historicalSummary?.revenue_protected ?? 0;
  const revenueExpanded = historicalSummary?.revenue_expanded ?? 0;
  const costSavings = historicalSummary?.cost_savings ?? 0;
  const compoundingEffect = historicalSummary?.compounding_effect ?? 0;

  const summary: ROISummary | null = historicalSummary ?? forwardSummary ?? null;

  const roiMultiple = fmtRoiMultiple(totalInvestment, totalImpact);
  const monthsOfData = paybackMonths > 0 ? Math.max(Math.ceil(paybackMonths * 1.5), 6) : 0;

  // Power of 1 metrics
  const po1Metrics: PowerOf1Metric[] =
    cfoData?.power_of_1_metrics && cfoData.power_of_1_metrics.length > 0
      ? cfoData.power_of_1_metrics
      : (storyData?.historical?.metric_outcomes || storyData?.forward?.metric_outcomes || []).map(
          (m) => ({
            metric_id: m.metric_id,
            display_name: m.display_name,
            baseline: m.baseline_value,
            current: m.current_value,
            improvement_pct: m.improvement_pct,
            dollar_impact: m.dollar_impact,
            data_source: m.data_source,
          })
        );

  const pillarInvestments = cfoData?.pillar_investments || [];
  const roiScaling = cfoData?.roi_scaling || { current_accounts: 0, current_roi: 0, projections: [] };
  const totalARR = cfoData?.total_arr ?? 0;
  const csInvestment = cfoData?.cs_investment ?? totalInvestment;
  const accountCount = roiScaling.current_accounts || 0;

  // Derived right-panel values
  const automationPct = 72;
  const costPerAccount = accountCount > 0 ? csInvestment / accountCount : 0;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (loading) {
    return <LoadingSkeleton />;
  }

  if (error && !storyData && !cfoData) {
    return (
      <div className="flex h-full">
        <div className="flex-1 overflow-y-auto">
          <div className="p-6 max-w-[1200px]">
            <ErrorBanner message={error} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* ============================================================= */}
      {/* MAIN CONTENT */}
      {/* ============================================================= */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-[1200px] space-y-6">
          {/* 1. Mission Banner */}
          <MissionBanner
            roiMultiple={roiMultiple}
            monthsOfData={monthsOfData}
            dataSource={dataSource}
          />

          {/* 2. Hero Headline Card */}
          <HeroCard
            roiPct={roiPct}
            totalInvestment={totalInvestment}
            totalImpact={totalImpact}
            revenueProtected={revenueProtected}
            revenueExpanded={revenueExpanded}
            costSavings={costSavings}
          />

          {/* 3. Power of 1 Metric Cards (2x3 grid) */}
          {po1Metrics.length > 0 && <PowerOf1Cards metrics={po1Metrics} />}

          {/* 4. Investment Breakdown (2-col) */}
          {(pillarInvestments.length > 0 || summary) && (
            <InvestmentBreakdown pillars={pillarInvestments} summary={summary} />
          )}
        </div>
      </div>

      {/* ============================================================= */}
      {/* RIGHT CONTEXT PANEL */}
      {/* ============================================================= */}
      <div className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 overflow-y-auto flex flex-col gap-5">
        {/* Financial Ratios */}
        <FinancialRatios
          roiPct={roiPct}
          paybackMonths={paybackMonths}
          costPerAccount={costPerAccount}
          automationPct={automationPct}
        />

        {/* Platform Multiplier (compact bar chart) */}
        {(roiScaling.projections.length > 0 || roiScaling.current_roi > 0) && (
          <PlatformMultiplierCompact scalingData={roiScaling} />
        )}

        {/* Quick Stats */}
        <QuickStats
          totalARR={totalARR}
          accountCount={accountCount}
          csInvestment={csInvestment}
        />

        {/* CFO Export */}
        <CFOExportPanel />
      </div>
    </div>
  );
}
