import React, { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, DollarSign, Target, Shield, Zap,
  ArrowRight, Activity, Clock, BarChart3, CheckCircle2, ChevronRight, ChevronDown,
  Loader2, AlertCircle, AlertTriangle, SlidersHorizontal, ArrowUpRight, ArrowDownRight,
  Sparkles, Eye, EyeOff, FileText, PlayCircle, Layers,
  GitBranch, Star, Diamond, Signal, CalendarDays, Map, Gauge, Rocket
} from 'lucide-react';
import { apiCall } from '../../utils/api';
import NavLogoutButton from '../shared/NavLogoutButton';

// ────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────

interface MetricOutcome {
  metric_id: string;
  display_name: string;
  baseline_value: number;
  current_value: number;
  improvement_pct: number;
  unit: string;
  direction: string;
  dollar_impact: number;
  revenue_portion: number;
  savings_portion: number;
  category: string;
  linked_kpis: string[];
  linked_playbooks: string[];
}

interface ROISummary {
  total_investment: number;
  total_impact: number;
  revenue_protected: number;
  revenue_expanded: number;
  cost_savings: number;
  compounding_effect: number;
  roi_pct: number;
  payback_months: number | null;
  improvement_pct_avg: number;
}

interface HistoricalDisclosure {
  non_repeatable: boolean;
  period_basis: string;            // 'since_onboarding' | 'trailing_window' | 'stable_window'
  headline: string;                // short auditor-facing label
  detail: string;                  // full disclosure paragraph
  recommended_label: string;       // what the tile should display as the period
  data_source?: string;
}

interface OutcomeResult {
  view_type: string;
  period_label: string;
  period_start: string;
  period_end: string;
  summary: ROISummary;
  metric_outcomes: MetricOutcome[];
  investment_breakdown: { total: number; cs_initiatives: number; platform: number };
  top_outcomes: Array<{
    metric_id: string;
    display_name: string;
    dollar_impact: number;
    improvement_pct: number;
    headline: string;
  }>;
  // PR #20 (May 17) attaches this when the historical window surfaces
  // non-repeatable, one-time gains (e.g. fresh-tenant decline→recovery
  // trajectories where ROI > 500% and avg improvement > 2× forward steady-state).
  disclosure?: HistoricalDisclosure | null;
}

interface BridgeData {
  momentum_metrics: Array<{
    metric_id: string;
    display_name: string;
    historical_improvement: number;
    historical_dollars: number;
    forward_improvement: number;
    forward_dollars: number;
    total_dollars: number;
  }>;
  historical_roi_pct: number;
  forward_roi_pct: number;
  trajectory: string;
  narrative: string;
}

interface WorkPackage {
  name: string;
  description: string;
  hours: number;
  cost: number;
  roles: Record<string, number>;
  deliverables: string[];
}

interface AccountAtRisk {
  account_id: number;
  account_name: string;
  score: number;
  status: string;  // 'critical' | 'at_risk'
  revenue: number;
}

interface RoadmapMetricSummary {
  metric_id: string;
  display_name: string;
  estimated_impact: number;
  dollar_impact_per_pct: number;
  target_improvement_pct: number;
  active_quarters: string[];
  all_quarters: string[];
  linked_kpis?: string[];
  linked_playbooks?: string[];
  accounts_at_risk?: AccountAtRisk[];
  at_risk_revenue?: number;
  at_risk_count?: number;
}

interface RoadmapQuarter {
  quarter: string;
  label: string;
  months: string;
  focus: string;
  metrics: Array<{
    metric_id: string;
    display_name: string;
    dollar_impact_per_pct: number;
    target_improvement_pct: number;
    estimated_impact: number;
    total_metric_impact?: number;
    work_packages: WorkPackage[];
    accounts_at_risk?: AccountAtRisk[];
  }>;
  total_hours: number;
  total_cost: number;
}

interface Roadmap {
  projection_months: number;
  target_improvement_pct: number;
  metric_summary?: RoadmapMetricSummary[];
  quarters: RoadmapQuarter[];
  total_hours: number;
  total_cost: number;
  total_projected_impact?: number;
  roi_pct?: number;
  source_note: string;
}

interface OutcomeStory {
  historical: OutcomeResult;
  forward: OutcomeResult;
  combined: {
    total_impact: number;
    total_investment: number;
    combined_roi_pct: number;
    revenue_protected: number;
    revenue_expanded: number;
    cost_savings: number;
  };
  bridge: BridgeData;
  roadmap?: Roadmap;
}

// ── Historical Details Types ──

interface SignalEvidence {
  signal_id: string;
  date: string;
  type: string;
  content: string;
  sentiment: string;
  sentiment_score: number | null;
  stakeholder_level: string | null;
  stakeholder_title: string | null;
}

interface PlaybookEvidence {
  execution_id: string;
  playbook_id: string;
  playbook_name: string;
  status: string;
  outcome: string | null;
  outcome_notes: string | null;
  started_at: string | null;
  completed_at: string | null;
  current_step: string | null;
}

interface KPIImprovement {
  kpi_code: string;
  start_value: number | null;
  end_value: number | null;
  start_score: number;
  end_score: number;
  delta_score: number;
  status: string;
}

interface PillarChange {
  pillar_code: string;
  start_score: number;
  end_score: number;
  delta: number;
}

interface AccountEvidence {
  account_id: number;
  account_name: string;
  revenue: number;
  industry: string | null;
  risk_status: string;
  health_score_start: number | null;
  health_score_end: number | null;
  health_delta: number | null;
  expansion_signals: SignalEvidence[];
  churn_signals: SignalEvidence[];
  signal_summary: {
    total: number;
    positive: number;
    negative: number;
    neutral: number;
  };
  playbooks: PlaybookEvidence[];
  kpi_improvements: KPIImprovement[];
  pillar_changes: PillarChange[];
}

// ── Velocity / Pillar Boost Types ──

interface PillarVelocity {
  pillar_name: string;
  metric_id: string;
  velocity_per_month: number;
  headroom: number;
  decel_factor: number;
  base_projected_pct: number;
  boost_multiplier: number;
  boosted_projected_pct: number;
  earliest_score: number;
  latest_score: number;
  // Industry benchmark gap
  industry_target_pct?: number;
  gap_to_target_pct?: number;
  boost_needed_for_target?: number;
  at_or_above_target?: boolean;
}

type VelocityDetail = Record<string, PillarVelocity>; // keyed by pillar code (P1..P5)

type PillarBoost = Record<string, number>; // e.g. { P2: 1.5, P3: 2.0 }

const PILLAR_META: Record<string, { name: string; color: string; icon: string }> = {
  P1: { name: 'Deployment Velocity', color: 'blue', icon: '🚀' },
  P2: { name: 'Operational Stability', color: 'green', icon: '🛡️' },
  P3: { name: 'AI Workload Perf', color: 'purple', icon: '🧠' },
  P4: { name: 'Channel & Partner', color: 'amber', icon: '🤝' },
  P5: { name: 'Expansion Readiness', color: 'rose', icon: '📈' },
};

// ────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────

const fmtDollar = (n: number) => {
  if (Math.abs(n) >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
};

const fmtPct = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`;

/** Format a metric value with correct unit (days, hrs, % — never $ for non-dollar metrics). */
const fmtMetricValue = (value: number, unit: string): string => {
  const u = (unit || '').toLowerCase();
  if (u === 'percent') return `${value.toFixed(1)}%`;
  if (u === 'days') return `${value.toFixed(0)} days`;
  if (u === 'hours') return `${value.toFixed(0)} hrs`;
  return `${value} ${unit}`.trim();
};

const METRIC_CONFIG: Record<string, { icon: string; color: string; bgColor: string }> = {
  TTFV: { icon: 'clock', color: 'text-orange-600', bgColor: 'bg-orange-50' },
  NRR: { icon: 'trending-up', color: 'text-emerald-600', bgColor: 'bg-emerald-50' },
  GRR: { icon: 'shield', color: 'text-blue-600', bgColor: 'bg-blue-50' },
  ticket_resolution_time: { icon: 'zap', color: 'text-amber-600', bgColor: 'bg-amber-50' },
  product_adoption: { icon: 'activity', color: 'text-purple-600', bgColor: 'bg-purple-50' },
  expansion_rate: { icon: 'arrow-up-right', color: 'text-cyan-600', bgColor: 'bg-cyan-50' },
};

const MetricIcon: React.FC<{ metricId: string; className?: string }> = ({ metricId, className = 'h-4 w-4' }) => {
  const config = METRIC_CONFIG[metricId];
  const iconMap: Record<string, React.ReactNode> = {
    'clock': <Clock className={className} />,
    'trending-up': <TrendingUp className={className} />,
    'shield': <Shield className={className} />,
    'zap': <Zap className={className} />,
    'activity': <Activity className={className} />,
    'arrow-up-right': <ArrowUpRight className={className} />,
  };
  return <>{iconMap[config?.icon || 'activity']}</>;
};

// ────────────────────────────────────────────────────────
// Sub-Components
// ────────────────────────────────────────────────────────

/** Hero KPI card for the combined summary */
const HeroCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}> = ({ icon, label, value, sub, accent = 'text-gray-900' }) => (
  <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-shadow">
    <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">{icon}{label}</div>
    <div className={`text-3xl font-bold ${accent}`}>{value}</div>
    {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
  </div>
);

/** Single metric outcome row */
const MetricOutcomeRow: React.FC<{
  metric: MetricOutcome;
  viewType: string;
  showEvidence: boolean;
}> = ({ metric, viewType, showEvidence }) => {
  const config = METRIC_CONFIG[metric.metric_id] || { color: 'text-gray-600', bgColor: 'bg-gray-50' };
  const isPositive = metric.improvement_pct > 0;
  const verb = viewType === 'historical' ? 'Delivered' : 'Will deliver';

  return (
    <div className="border border-gray-100 rounded-lg p-4 hover:bg-gray-50/50 transition">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${config.bgColor}`}>
            <MetricIcon metricId={metric.metric_id} className={`h-5 w-5 ${config.color}`} />
          </div>
          <div>
            <div className="font-semibold text-gray-900 text-sm">{metric.display_name}</div>
            <div className="text-xs text-gray-500 mt-0.5">
              {fmtMetricValue(metric.baseline_value, metric.unit)}
              {' '}<ArrowRight className="inline h-3 w-3" />{' '}
              {fmtMetricValue(metric.current_value, metric.unit)}
              {isPositive && (
                <span className="ml-1.5 text-emerald-600 font-medium">
                  ({metric.improvement_pct > 0 ? '+' : ''}{metric.improvement_pct}%)
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className={`text-lg font-bold ${isPositive ? 'text-emerald-600' : 'text-gray-400'}`}>
            {isPositive ? fmtDollar(metric.dollar_impact) : '--'}
          </div>
          <div className="text-xs text-gray-400">{verb}</div>
        </div>
      </div>

      {/* Evidence layer — drill-in for KPIs */}
      {showEvidence && metric.linked_kpis.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-1">
            <BarChart3 className="h-3 w-3" /> Evidence (KPIs)
          </div>
          <div className="flex flex-wrap gap-1.5">
            {metric.linked_kpis.map(kpi => (
              <span key={kpi} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                {kpi}
              </span>
            ))}
            {metric.linked_playbooks.map(pb => (
              <span key={pb} className="text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full">
                {pb}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

/** One side of the story (historical or forward) */
const OutcomePanel: React.FC<{
  result: OutcomeResult;
  accentColor: string;
  accentBg: string;
  headerIcon: React.ReactNode;
  showEvidence: boolean;
}> = ({ result, accentColor, accentBg, headerIcon, showEvidence }) => {
  const s = result.summary;

  return (
    <div className="flex-1 min-w-0">
      {/* Panel header */}
      <div className={`rounded-t-xl ${accentBg} px-6 py-4 border border-gray-200 border-b-0`}>
        <div className="flex items-center gap-2 mb-1">
          {headerIcon}
          <span className={`text-sm font-semibold ${accentColor}`}>
            {result.view_type === 'historical' ? 'PROVEN' : 'PROJECTED'}
          </span>
        </div>
        <h3 className="text-lg font-bold text-gray-900">{result.period_label}</h3>
        <div className="text-xs text-gray-500 mt-0.5">
          {result.period_start} to {result.period_end}
        </div>
      </div>

      {/* PR #20 disclosure — render when the historical view surfaces non-repeatable
          one-time gains (e.g. fresh tenants where ROI > 500% reflects onboarding lift).
          The backend already rewrites `period_label` above; this surfaces the structured
          warning auditors expect. */}
      {result.view_type === 'historical' && result.disclosure?.non_repeatable && (
        <div className="bg-amber-50 border-x border-amber-200 border-b border-amber-200 px-6 py-3">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" aria-hidden="true" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-amber-900 uppercase tracking-wide">
                {result.disclosure.headline}
              </p>
              <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                {result.disclosure.detail}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Summary stats */}
      <div className="bg-white border-x border-gray-200 px-6 py-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs text-gray-500 mb-1">Total Impact</div>
            <div className={`text-2xl font-bold ${accentColor}`}>{fmtDollar(s.total_impact)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-1">ROI</div>
            <div className={`text-2xl font-bold ${s.roi_pct >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
              {fmtPct(s.roi_pct)}
            </div>
          </div>
        </div>

        {/* Outcome breakdown */}
        <div className="mt-4 grid grid-cols-3 gap-3">
          <div className="bg-blue-50 rounded-lg p-3">
            <div className="text-xs text-blue-600 font-medium">Revenue Protected</div>
            <div className="text-sm font-bold text-blue-900 mt-1">{fmtDollar(s.revenue_protected)}</div>
          </div>
          <div className="bg-emerald-50 rounded-lg p-3">
            <div className="text-xs text-emerald-600 font-medium">Revenue Expanded</div>
            <div className="text-sm font-bold text-emerald-900 mt-1">{fmtDollar(s.revenue_expanded)}</div>
          </div>
          <div className="bg-amber-50 rounded-lg p-3">
            <div className="text-xs text-amber-600 font-medium">Cost Savings</div>
            <div className="text-sm font-bold text-amber-900 mt-1">{fmtDollar(s.cost_savings)}</div>
          </div>
        </div>

        {/* Investment vs payback */}
        <div className="mt-4 flex items-center justify-between text-xs text-gray-500 bg-gray-50 rounded-lg px-4 py-2.5">
          <span>Investment: {fmtDollar(s.total_investment)}</span>
          <span>Payback: {s.payback_months != null && s.payback_months < 100 ? `${s.payback_months.toFixed(1)} months` : 'N/A'}</span>
          <span>Avg improvement: {s.improvement_pct_avg.toFixed(1)}%</span>
        </div>
      </div>

      {/* Top outcomes */}
      {result.top_outcomes.length > 0 && (
        <div className="bg-white border-x border-gray-200 px-6 py-4 border-t border-gray-100">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Top Outcomes
          </div>
          {result.top_outcomes.map((outcome, i) => (
            <div key={outcome.metric_id} className="flex items-center gap-3 py-2">
              <span className={`text-xs font-bold ${accentColor} w-5`}>#{i + 1}</span>
              <span className="text-sm text-gray-700 flex-1">{outcome.headline}</span>
            </div>
          ))}
        </div>
      )}

      {/* Metric details */}
      <div className="bg-white border border-gray-200 rounded-b-xl px-6 py-4">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Metric Outcomes
        </div>
        <div className="space-y-2">
          {result.metric_outcomes
            .sort((a, b) => b.dollar_impact - a.dollar_impact)
            .map(metric => (
              <MetricOutcomeRow
                key={metric.metric_id}
                metric={metric}
                viewType={result.view_type}
                showEvidence={showEvidence}
              />
            ))}
        </div>
      </div>
    </div>
  );
};

/** Bridge section between historical and forward */
const BridgeSection: React.FC<{ bridge: BridgeData }> = ({ bridge }) => (
  <div className="bg-gradient-to-r from-blue-50 via-indigo-50 to-emerald-50 rounded-xl border border-indigo-200 p-6 my-6">
    <div className="flex items-center gap-2 mb-3">
      <Sparkles className="h-5 w-5 text-indigo-500" />
      <span className="text-sm font-semibold text-indigo-700 uppercase tracking-wider">
        Trajectory: {bridge.trajectory === 'accelerating' ? 'Accelerating' : 'Sustaining'}
      </span>
    </div>
    <p className="text-sm text-gray-700 leading-relaxed">{bridge.narrative}</p>

    {bridge.momentum_metrics.length > 0 && (
      <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
        {bridge.momentum_metrics.map(m => (
          <div key={m.metric_id} className="bg-white/70 rounded-lg p-3 border border-white">
            <div className="text-xs text-gray-500">{m.display_name}</div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-sm font-bold text-blue-600">{fmtDollar(m.historical_dollars)}</span>
              <ChevronRight className="h-3 w-3 text-gray-400" />
              <span className="text-sm font-bold text-emerald-600">{fmtDollar(m.forward_dollars)}</span>
            </div>
            <div className="text-xs text-gray-400 mt-0.5">
              Total: {fmtDollar(m.total_dollars)}
            </div>
          </div>
        ))}
      </div>
    )}
  </div>
);

/** Combined hero stats */
const CombinedHero: React.FC<{ combined: OutcomeStory['combined'] }> = ({ combined }) => (
  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
    <HeroCard
      icon={<DollarSign className="h-5 w-5 text-indigo-500" />}
      label="Total Outcome Value"
      value={fmtDollar(combined.total_impact)}
      sub={`On ${fmtDollar(combined.total_investment)} investment`}
      accent="text-indigo-600"
    />
    <HeroCard
      icon={<Target className="h-5 w-5 text-emerald-500" />}
      label="Combined ROI"
      value={fmtPct(combined.combined_roi_pct)}
      sub="Historical + projected"
      accent="text-emerald-600"
    />
    <HeroCard
      icon={<Shield className="h-5 w-5 text-blue-500" />}
      label="Revenue Protected"
      value={fmtDollar(combined.revenue_protected)}
      sub="GRR + support outcomes"
      accent="text-blue-600"
    />
    <HeroCard
      icon={<ArrowUpRight className="h-5 w-5 text-cyan-500" />}
      label="Revenue Expanded"
      value={fmtDollar(combined.revenue_expanded)}
      sub="NRR + expansion + adoption"
      accent="text-cyan-600"
    />
  </div>
);

// ────────────────────────────────────────────────────────
// Historical Details — Account-Level Evidence
// ────────────────────────────────────────────────────────

/** Pillar code display names */
const PILLAR_NAMES: Record<string, string> = {
  AI: 'AI & Analytics', CH: 'Customer Health', DV: 'Data & Visibility',
  EX: 'Experience', OS: 'Operations',
};

/** Status badge for playbook execution */
const PlaybookStatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const styles: Record<string, string> = {
    'completed': 'bg-emerald-100 text-emerald-700',
    'in-progress': 'bg-blue-100 text-blue-700',
    'failed': 'bg-red-100 text-red-700',
    'cancelled': 'bg-gray-100 text-gray-500',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[status] || 'bg-gray-100 text-gray-500'}`}>
      {status}
    </span>
  );
};

/** Risk status badge */
const RiskBadge: React.FC<{ status: string }> = ({ status }) => {
  const styles: Record<string, string> = {
    'critical': 'bg-red-100 text-red-700 border-red-200',
    'at-risk': 'bg-amber-100 text-amber-700 border-amber-200',
    'healthy': 'bg-emerald-100 text-emerald-700 border-emerald-200',
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${styles[status] || styles['healthy']}`}>
      {status}
    </span>
  );
};

/** Expanded detail for a single account */
const AccountDetailExpanded: React.FC<{ account: AccountEvidence }> = ({ account }) => (
  <div className="px-6 py-5 bg-gray-50/50 border-t border-gray-100 space-y-5">
    {/* Expansion Signals */}
    {account.expansion_signals.length > 0 && (
      <div>
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="h-4 w-4 text-emerald-500" />
          <span className="text-sm font-semibold text-emerald-700">Expansion Signals</span>
          <span className="text-xs text-gray-400">({account.signal_summary.positive} total)</span>
        </div>
        <div className="space-y-1.5 ml-6">
          {account.expansion_signals.map(sig => (
            <div key={sig.signal_id} className="flex items-start gap-2 text-sm">
              <span className="text-emerald-400 mt-0.5">&#x2022;</span>
              <div className="flex-1">
                <span className="text-gray-700">{sig.content}</span>
                <span className="text-xs text-gray-400 ml-2">
                  {sig.date} &middot; {sig.type}
                  {sig.stakeholder_level && ` &middot; ${sig.stakeholder_level}`}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    )}

    {/* Churn Signals */}
    {account.churn_signals.length > 0 && (
      <div>
        <div className="flex items-center gap-2 mb-2">
          <TrendingDown className="h-4 w-4 text-red-500" />
          <span className="text-sm font-semibold text-red-700">Churn Risk Signals</span>
          <span className="text-xs text-gray-400">({account.signal_summary.negative} total)</span>
        </div>
        <div className="space-y-1.5 ml-6">
          {account.churn_signals.map(sig => (
            <div key={sig.signal_id} className="flex items-start gap-2 text-sm">
              <span className="text-red-400 mt-0.5">&#x2022;</span>
              <div className="flex-1">
                <span className="text-gray-700">{sig.content}</span>
                <span className="text-xs text-gray-400 ml-2">
                  {sig.date} &middot; {sig.type}
                  {sig.stakeholder_level && ` &middot; ${sig.stakeholder_level}`}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    )}

    {/* Playbook Actions */}
    {account.playbooks.length > 0 && (
      <div>
        <div className="flex items-center gap-2 mb-2">
          <PlayCircle className="h-4 w-4 text-indigo-500" />
          <span className="text-sm font-semibold text-indigo-700">Playbook Actions</span>
        </div>
        <div className="space-y-2 ml-6">
          {account.playbooks.map(pb => (
            <div key={pb.execution_id} className="flex items-center gap-3 text-sm">
              <PlaybookStatusBadge status={pb.status} />
              <span className="font-medium text-gray-800">{pb.playbook_name}</span>
              {pb.started_at && (
                <span className="text-xs text-gray-400">Started {pb.started_at.split('T')[0]}</span>
              )}
              {pb.outcome && (
                <span className="text-xs text-gray-500 italic">{pb.outcome}</span>
              )}
            </div>
          ))}
        </div>
      </div>
    )}

    {/* KPI Improvements */}
    {account.kpi_improvements.length > 0 && (
      <div>
        <div className="flex items-center gap-2 mb-2">
          <BarChart3 className="h-4 w-4 text-blue-500" />
          <span className="text-sm font-semibold text-blue-700">KPI Score Changes (Top 8)</span>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 ml-6">
          {account.kpi_improvements.map(kpi => (
            <div
              key={kpi.kpi_code}
              className={`text-xs px-3 py-2 rounded-lg border ${
                kpi.delta_score > 0
                  ? 'bg-emerald-50 border-emerald-200'
                  : kpi.delta_score < 0
                    ? 'bg-red-50 border-red-200'
                    : 'bg-gray-50 border-gray-200'
              }`}
            >
              <div className="font-medium text-gray-700 truncate" title={kpi.kpi_code}>
                {kpi.kpi_code}
              </div>
              <div className="flex items-center gap-1 mt-1">
                <span className="text-gray-500">{kpi.start_score}</span>
                <ArrowRight className="h-3 w-3 text-gray-400" />
                <span className="text-gray-700 font-medium">{kpi.end_score}</span>
                <span className={`ml-auto font-bold ${
                  kpi.delta_score > 0 ? 'text-emerald-600' : kpi.delta_score < 0 ? 'text-red-600' : 'text-gray-400'
                }`}>
                  {kpi.delta_score > 0 ? '+' : ''}{kpi.delta_score}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    )}

    {/* Pillar Changes */}
    {account.pillar_changes.length > 0 && (
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Layers className="h-4 w-4 text-purple-500" />
          <span className="text-sm font-semibold text-purple-700">Pillar Score Changes</span>
        </div>
        <div className="flex flex-wrap gap-2 ml-6">
          {account.pillar_changes.map(p => (
            <div
              key={p.pillar_code}
              className={`text-xs px-3 py-2 rounded-lg border ${
                p.delta > 0 ? 'bg-emerald-50 border-emerald-200' : p.delta < 0 ? 'bg-red-50 border-red-200' : 'bg-gray-50 border-gray-200'
              }`}
            >
              <div className="font-medium text-gray-700">{PILLAR_NAMES[p.pillar_code] || p.pillar_code}</div>
              <div className="flex items-center gap-1 mt-0.5">
                <span className="text-gray-500">{p.start_score}</span>
                <ArrowRight className="h-3 w-3 text-gray-400" />
                <span className="font-medium">{p.end_score}</span>
                <span className={`ml-1 font-bold ${
                  p.delta > 0 ? 'text-emerald-600' : p.delta < 0 ? 'text-red-600' : 'text-gray-400'
                }`}>
                  ({p.delta > 0 ? '+' : ''}{p.delta})
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    )}

    {/* Empty state */}
    {account.expansion_signals.length === 0 && account.churn_signals.length === 0 &&
     account.playbooks.length === 0 && account.kpi_improvements.length === 0 && (
      <div className="text-sm text-gray-400 italic text-center py-4">
        No evidence data recorded for this account in the period.
      </div>
    )}
  </div>
);

/** Single account row in the details table */
const AccountRow: React.FC<{
  account: AccountEvidence;
  isExpanded: boolean;
  onToggle: () => void;
}> = ({ account, isExpanded, onToggle }) => {
  const hasData = account.signal_summary.total > 0 || account.playbooks.length > 0 ||
                  account.kpi_improvements.length > 0;

  return (
    <div className="border-b border-gray-100 last:border-b-0">
      {/* Summary row */}
      <button
        onClick={onToggle}
        className="w-full px-6 py-3 flex items-center gap-4 hover:bg-gray-50/70 transition text-left"
      >
        {/* Expand arrow */}
        <div className="shrink-0">
          {isExpanded
            ? <ChevronDown className="h-4 w-4 text-gray-400" />
            : <ChevronRight className="h-4 w-4 text-gray-400" />
          }
        </div>

        {/* Account name + status */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-900 truncate">{account.account_name}</span>
            <RiskBadge status={account.risk_status} />
          </div>
          {account.industry && (
            <span className="text-xs text-gray-400">{account.industry}</span>
          )}
        </div>

        {/* Revenue */}
        <div className="shrink-0 text-right w-24">
          <div className="text-sm font-medium text-gray-700">{fmtDollar(account.revenue)}</div>
          <div className="text-xs text-gray-400">ARR</div>
        </div>

        {/* Health Delta */}
        <div className="shrink-0 text-right w-20">
          {account.health_delta !== null ? (
            <>
              <div className={`text-sm font-bold ${
                account.health_delta > 0 ? 'text-emerald-600' : account.health_delta < 0 ? 'text-red-600' : 'text-gray-400'
              }`}>
                {account.health_delta > 0 ? '+' : ''}{account.health_delta}
              </div>
              <div className="text-xs text-gray-400">Health &#916;</div>
            </>
          ) : (
            <div className="text-xs text-gray-300">—</div>
          )}
        </div>

        {/* Signal counts */}
        <div className="shrink-0 w-24 flex items-center gap-2">
          {account.signal_summary.positive > 0 && (
            <span className="text-xs bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full font-medium">
              +{account.signal_summary.positive}
            </span>
          )}
          {account.signal_summary.negative > 0 && (
            <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full font-medium">
              -{account.signal_summary.negative}
            </span>
          )}
          {account.signal_summary.total === 0 && (
            <span className="text-xs text-gray-300">—</span>
          )}
        </div>

        {/* Playbook count */}
        <div className="shrink-0 w-20 text-right">
          {account.playbooks.length > 0 ? (
            <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium">
              {account.playbooks.length} {account.playbooks.length === 1 ? 'play' : 'plays'}
            </span>
          ) : (
            <span className="text-xs text-gray-300">—</span>
          )}
        </div>
      </button>

      {/* Expanded detail */}
      {isExpanded && hasData && <AccountDetailExpanded account={account} />}
      {isExpanded && !hasData && (
        <div className="px-6 py-4 bg-gray-50/50 border-t border-gray-100 text-sm text-gray-400 italic text-center">
          No evidence data for this account in the period.
        </div>
      )}
    </div>
  );
};

/** Historical Details Panel — account-level evidence drill-down */
const HistoricalDetailsPanel: React.FC = () => {
  const [expanded, setExpanded] = useState(false);
  const [details, setDetails] = useState<AccountEvidence[] | null>(null);
  const [expandedAccount, setExpandedAccount] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExpand = useCallback(async () => {
    if (!expanded && !details) {
      setLoading(true);
      setError(null);
      try {
        const res = await apiCall('/api/outcome-roi/historical-details?period=6m');
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        setDetails(data.accounts || []);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to load details';
        setError(message);
      } finally {
        setLoading(false);
      }
    }
    setExpanded(!expanded);
  }, [expanded, details]);

  // Stats for the header badge
  const totalSignals = details?.reduce((sum, a) => sum + a.signal_summary.total, 0) || 0;
  const totalPlaybooks = details?.reduce((sum, a) => sum + a.playbooks.length, 0) || 0;

  return (
    <div className="mt-6 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header / expand button */}
      <button
        onClick={handleExpand}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition"
      >
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-blue-500" />
          <div className="text-left">
            <h3 className="text-sm font-bold text-gray-900">
              Historical Details — Account-Level Evidence
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Expansion/churn signals, playbook actions, KPI improvements per account
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {details && (
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <span>{details.length} accounts</span>
              {totalSignals > 0 && <span>&middot; {totalSignals} signals</span>}
              {totalPlaybooks > 0 && <span>&middot; {totalPlaybooks} playbooks</span>}
            </div>
          )}
          {expanded
            ? <ChevronDown className="h-5 w-5 text-gray-400" />
            : <ChevronRight className="h-5 w-5 text-gray-400" />
          }
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-gray-200">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-gray-400 mr-2" />
              <span className="text-sm text-gray-500">Loading account evidence...</span>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center py-8">
              <AlertCircle className="h-5 w-5 text-red-400 mr-2" />
              <span className="text-sm text-red-500">{error}</span>
            </div>
          )}

          {details && details.length > 0 && !loading && (
            <>
              {/* Column headers */}
              <div className="px-6 py-2 bg-gray-50 border-b border-gray-200 flex items-center gap-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <div className="w-4" /> {/* expand arrow space */}
                <div className="flex-1">Account</div>
                <div className="w-24 text-right">Revenue</div>
                <div className="w-20 text-right">Health &#916;</div>
                <div className="w-24">Signals</div>
                <div className="w-20 text-right">Actions</div>
              </div>

              {/* Account rows */}
              <div className="max-h-[600px] overflow-y-auto">
                {details.map(account => (
                  <AccountRow
                    key={account.account_id}
                    account={account}
                    isExpanded={expandedAccount === account.account_id}
                    onToggle={() => setExpandedAccount(
                      expandedAccount === account.account_id ? null : account.account_id
                    )}
                  />
                ))}
              </div>
            </>
          )}

          {details && details.length === 0 && !loading && (
            <div className="py-8 text-center text-sm text-gray-400">
              No account data available for the historical period.
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/** Implementation Roadmap — "How to get there" aligned with forward projection */
const RoadmapSection: React.FC<{ roadmap: Roadmap }> = ({ roadmap }) => {
  const [expandedQ, setExpandedQ] = useState<string | null>('Q1');
  const QUARTER_COLORS: Record<string, string> = {
    Q1: 'border-orange-300 bg-orange-50',
    Q2: 'border-blue-300 bg-blue-50',
    Q3: 'border-purple-300 bg-purple-50',
    Q4: 'border-emerald-300 bg-emerald-50',
  };
  const QUARTER_ACCENT: Record<string, string> = {
    Q1: 'text-orange-700', Q2: 'text-blue-700', Q3: 'text-purple-700', Q4: 'text-emerald-700',
  };

  const numQuarters = roadmap.quarters.length;
  const gridCols = numQuarters <= 2 ? 'grid-cols-2' : numQuarters === 3 ? 'grid-cols-3' : 'grid-cols-4';

  return (
    <div className="mt-8 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-indigo-50 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-indigo-600" />
            <h2 className="text-lg font-bold text-gray-900">
              Implementation Roadmap — Next {roadmap.projection_months} Months
            </h2>
            <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">
              {roadmap.target_improvement_pct}% improvement target
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>{roadmap.total_hours.toLocaleString()} hours</span>
            <span>{fmtDollar(roadmap.total_cost)} investment</span>
            {roadmap.roi_pct != null && (
              <span className="font-semibold text-emerald-600">{roadmap.roi_pct}% ROI</span>
            )}
          </div>
        </div>
      </div>

      {/* ── Metric Summary Table — ALL 6 metrics with period-scaled impacts ── */}
      {roadmap.metric_summary && roadmap.metric_summary.length > 0 && (
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            All Power of 1 Metrics — {roadmap.projection_months}-Month Projected Impact
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {roadmap.metric_summary.map(ms => {
              const hasWorkInWindow = ms.active_quarters.length > 0;
              const atRiskAccounts = ms.accounts_at_risk || [];
              const criticalCount = atRiskAccounts.filter(a => a.status === 'critical').length;
              const riskCount = atRiskAccounts.filter(a => a.status === 'at_risk').length;
              return (
                <div
                  key={ms.metric_id}
                  className={`px-4 py-3 rounded-lg border ${
                    hasWorkInWindow
                      ? 'border-emerald-200 bg-emerald-50'
                      : 'border-gray-200 bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <MetricIcon metricId={ms.metric_id} />
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-800 truncate">{ms.display_name}</div>
                        <div className="text-xs text-gray-400">
                          {hasWorkInWindow
                            ? `Active: ${ms.active_quarters.join(', ')}`
                            : `Scheduled: ${ms.all_quarters.join(', ')}`
                          }
                        </div>
                      </div>
                    </div>
                    <div className="text-right shrink-0 ml-2">
                      <div className={`text-sm font-bold ${hasWorkInWindow ? 'text-emerald-700' : 'text-gray-500'}`}>
                        {fmtDollar(ms.estimated_impact)}
                      </div>
                      <div className="text-xs text-gray-400">
                        {fmtDollar(ms.dollar_impact_per_pct)}/1%
                      </div>
                    </div>
                  </div>
                  {/* At-risk accounts for this metric */}
                  {atRiskAccounts.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-200/60">
                      <div className="flex items-center gap-1.5 mb-1">
                        <AlertTriangle className="h-3 w-3 text-amber-500" />
                        <span className="text-xs font-medium text-gray-600">
                          {(ms.at_risk_count || atRiskAccounts.length)} accounts need attention
                          {criticalCount > 0 && <span className="text-red-600"> ({criticalCount} critical)</span>}
                        </span>
                        {ms.at_risk_revenue ? (
                          <span className="text-xs text-gray-400 ml-auto">{fmtDollar(ms.at_risk_revenue)} at risk</span>
                        ) : null}
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {atRiskAccounts.map(a => (
                          <span
                            key={a.account_id}
                            className={`text-xs px-1.5 py-0.5 rounded ${
                              a.status === 'critical'
                                ? 'bg-red-100 text-red-700'
                                : 'bg-amber-100 text-amber-700'
                            }`}
                            title={`Score: ${a.score} | Revenue: ${fmtDollar(a.revenue)}`}
                          >
                            {a.account_name} ({a.score})
                          </span>
                        ))}
                        {(ms.at_risk_count || 0) > atRiskAccounts.length && (
                          <span className="text-xs text-gray-400 px-1">
                            +{(ms.at_risk_count || 0) - atRiskAccounts.length} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                  {/* Linked KPIs and Playbooks */}
                  {(ms.linked_kpis?.length || ms.linked_playbooks?.length) ? (
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {ms.linked_kpis?.slice(0, 3).map(kpi => (
                        <span key={kpi} className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded">
                          {kpi}
                        </span>
                      ))}
                      {ms.linked_playbooks?.slice(0, 2).map(pb => (
                        <span key={pb} className="text-xs bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded">
                          {pb}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
          {roadmap.total_projected_impact != null && (
            <div className="mt-3 flex items-center justify-between px-4 py-2 bg-indigo-50 rounded-lg border border-indigo-200">
              <span className="text-sm font-semibold text-indigo-800">
                Total Projected Impact ({roadmap.projection_months}mo)
              </span>
              <span className="text-sm font-bold text-indigo-900">
                {fmtDollar(roadmap.total_projected_impact)}
              </span>
            </div>
          )}
        </div>
      )}

      {/* ── Quarter timeline tabs ── */}
      <div className={`grid ${gridCols} gap-0 border-b border-gray-200`}>
        {roadmap.quarters.map(q => (
          <button
            key={q.quarter}
            onClick={() => setExpandedQ(expandedQ === q.quarter ? null : q.quarter)}
            className={`px-4 py-3 text-left border-r last:border-r-0 transition-colors ${
              expandedQ === q.quarter ? QUARTER_COLORS[q.quarter] : 'bg-white hover:bg-gray-50'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className={`text-sm font-bold ${expandedQ === q.quarter ? QUARTER_ACCENT[q.quarter] : 'text-gray-700'}`}>
                {q.quarter}: {q.label}
              </span>
              <ChevronRight className={`h-4 w-4 transition-transform ${expandedQ === q.quarter ? 'rotate-90' : ''}`} />
            </div>
            <div className="text-xs text-gray-500 mt-0.5">{q.months}</div>
            <div className="text-xs text-gray-400">{q.focus}</div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs font-medium text-gray-600">{q.metrics.length} metrics</span>
              <span className="text-xs text-gray-400">·</span>
              <span className="text-xs text-gray-500">{q.total_hours}h</span>
              <span className="text-xs text-gray-400">·</span>
              <span className="text-xs text-gray-500">{fmtDollar(q.total_cost)}</span>
            </div>
          </button>
        ))}
      </div>

      {/* ── Expanded quarter detail ── */}
      {expandedQ && (() => {
        const q = roadmap.quarters.find(q => q.quarter === expandedQ);
        if (!q || q.metrics.length === 0) return (
          <div className="p-6 text-center text-gray-400 text-sm">No work packages scheduled for {expandedQ}</div>
        );
        return (
          <div className="p-6 space-y-4">
            {q.metrics.map(m => (
              <div key={m.metric_id} className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="px-4 py-3 bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <MetricIcon metricId={m.metric_id} />
                      <span className="font-semibold text-sm text-gray-800">{m.display_name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
                        {expandedQ} share: {fmtDollar(m.estimated_impact)}
                      </span>
                      {m.total_metric_impact != null && m.total_metric_impact !== m.estimated_impact && (
                        <span className="text-xs text-gray-400">
                          Total: {fmtDollar(m.total_metric_impact)}
                        </span>
                      )}
                    </div>
                  </div>
                  {/* At-risk accounts for this metric in quarter view */}
                  {m.accounts_at_risk && m.accounts_at_risk.length > 0 && (
                    <div className="mt-2 flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-gray-500 font-medium">Focus accounts:</span>
                      {m.accounts_at_risk.map(a => (
                        <span
                          key={a.account_id}
                          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            a.status === 'critical'
                              ? 'bg-red-100 text-red-700 border border-red-200'
                              : 'bg-amber-100 text-amber-700 border border-amber-200'
                          }`}
                          title={`Health: ${a.score} | Revenue: ${fmtDollar(a.revenue)}`}
                        >
                          {a.account_name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="divide-y divide-gray-100">
                  {m.work_packages.map((wp, i) => (
                    <div key={i} className="px-4 py-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="text-sm font-medium text-gray-800">{wp.name}</div>
                          <div className="text-xs text-gray-500 mt-0.5">{wp.description}</div>
                          {wp.deliverables.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1.5">
                              {wp.deliverables.map((d, j) => (
                                <span key={j} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                                  {d}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="text-right ml-4 shrink-0">
                          <div className="text-xs font-medium text-gray-700">{wp.hours}h</div>
                          <div className="text-xs text-gray-400">{fmtDollar(wp.cost)}</div>
                        </div>
                      </div>
                      {/* Role breakdown */}
                      <div className="flex gap-3 mt-2">
                        {Object.entries(wp.roles).filter(([, h]) => h > 0).map(([role, hours]) => (
                          <span key={role} className="text-xs text-gray-400">
                            {role}: {hours}h
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        );
      })()}

      {/* Source footnote */}
      <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
        <p className="text-xs text-gray-400 italic">{roadmap.source_note}</p>
      </div>
    </div>
  );
};

// ────────────────────────────────────────────────────────
// Revenue Timeline Component
// ────────────────────────────────────────────────────────

interface TimelineSignal {
  node_id: number;
  title: string;
  subtype: string;
  account_id: number;
  revenue_impact: number;
  revenue_impact_type: string;
  occurred_at: string | null;
}

interface TimelineMonth {
  month: string;
  label: string;
  signals: TimelineSignal[];
  decisions: TimelineSignal[];
  outcomes: TimelineSignal[];
  stakeholder_actions: number;
  kpi_movements: Array<{ kpi_code: string; metric: string | null; avg_score: number; account_count: number }>;
  revenue_impact: { protected: number; expanded: number; at_risk: number; lost: number };
  cumulative_impact: { protected: number; expanded: number; at_risk: number; lost: number };
  signal_count: number;
  decision_count: number;
  outcome_count: number;
}

interface CausalHighlight {
  outcome: { title: string; revenue: number; type: string; account_id: number };
  chain: Array<{ type: string; title: string; month: string; revenue_impact: number }>;
}

interface TimelineData {
  period: { start: string; end: string; months: number };
  timeline: TimelineMonth[];
  causal_highlights: CausalHighlight[];
  summary: {
    total_signals: number;
    total_decisions: number;
    total_outcomes: number;
    total_revenue_protected: number;
    total_revenue_expanded: number;
    total_revenue_at_risk: number;
    total_revenue_lost: number;
    peak_risk_month: string;
    peak_risk_amount: number;
  };
}

const NODE_TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  SIGNAL: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  DECISION: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' },
  OUTCOME: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  STAKEHOLDER: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' },
};

/** Causal chain visualization — signal → decision → outcome */
const CausalChainCard: React.FC<{ highlight: CausalHighlight }> = ({ highlight }) => (
  <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-sm transition">
    <div className="flex items-center gap-2 mb-3">
      <Star className="h-4 w-4 text-emerald-500" />
      <span className="text-sm font-semibold text-gray-900">{highlight.outcome.title}</span>
      <span className={`ml-auto text-xs font-bold px-2 py-0.5 rounded-full ${
        highlight.outcome.type === 'expansion' ? 'bg-emerald-100 text-emerald-700' :
        highlight.outcome.type === 'protected' ? 'bg-blue-100 text-blue-700' :
        'bg-red-100 text-red-700'
      }`}>
        {fmtDollar(Math.abs(highlight.outcome.revenue))}
      </span>
    </div>
    <div className="flex items-center gap-1 overflow-x-auto pb-1">
      {highlight.chain.map((step, idx) => {
        const colors = NODE_TYPE_COLORS[step.type] || NODE_TYPE_COLORS.SIGNAL;
        return (
          <React.Fragment key={idx}>
            {idx > 0 && <ArrowRight className="h-3 w-3 text-gray-300 flex-shrink-0" />}
            <div className={`flex-shrink-0 px-2 py-1 rounded text-xs border ${colors.bg} ${colors.text} ${colors.border}`}>
              <div className="font-medium truncate max-w-[160px]">{step.title}</div>
              <div className="text-[10px] opacity-70 mt-0.5">{step.month}</div>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  </div>
);

/** Single month in the timeline */
const TimelineMonthCard: React.FC<{
  month: TimelineMonth;
  isExpanded: boolean;
  onToggle: () => void;
  maxSignals: number;
}> = ({ month, isExpanded, onToggle, maxSignals }) => {
  const totalRev = month.revenue_impact.protected + month.revenue_impact.expanded;
  const totalRisk = month.revenue_impact.at_risk + month.revenue_impact.lost;
  const barWidth = maxSignals > 0 ? Math.max(5, (month.signal_count / maxSignals) * 100) : 5;

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition">
        {/* Month label */}
        <div className="w-20 text-left">
          <div className="text-sm font-bold text-gray-900">{month.label}</div>
        </div>

        {/* Signal density bar */}
        <div className="flex-1 flex items-center gap-2">
          <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden relative">
            {/* Protected/expanded portion */}
            {totalRev > 0 && (
              <div
                className="absolute left-0 top-0 h-full bg-emerald-400/60 rounded-l-full"
                style={{ width: `${Math.min(100, barWidth)}%` }}
              />
            )}
            {/* At-risk portion */}
            {totalRisk > 0 && (
              <div
                className="absolute right-0 top-0 h-full bg-red-400/40 rounded-r-full"
                style={{ width: `${Math.min(30, (totalRisk / (totalRev + totalRisk + 1)) * 100)}%` }}
              />
            )}
            {/* Count badges */}
            <div className="absolute inset-0 flex items-center justify-center gap-2 text-[10px]">
              {month.signal_count > 0 && (
                <span className="bg-amber-200/80 text-amber-800 px-1.5 rounded-full font-medium">
                  {month.signal_count} signals
                </span>
              )}
              {month.decision_count > 0 && (
                <span className="bg-purple-200/80 text-purple-800 px-1.5 rounded-full font-medium">
                  {month.decision_count} decisions
                </span>
              )}
              {month.outcome_count > 0 && (
                <span className="bg-emerald-200/80 text-emerald-800 px-1.5 rounded-full font-medium">
                  {month.outcome_count} outcomes
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Revenue impact */}
        <div className="w-28 text-right">
          {totalRev > 0 && <div className="text-xs font-semibold text-emerald-600">+{fmtDollar(totalRev)}</div>}
          {totalRisk > 0 && <div className="text-xs font-semibold text-red-500">-{fmtDollar(totalRisk)}</div>}
          {totalRev === 0 && totalRisk === 0 && <div className="text-xs text-gray-400">—</div>}
        </div>

        <ChevronRight className={`h-4 w-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
      </button>

      {/* Expanded drill-down */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-100 space-y-3 pt-3">
          {/* Signals */}
          {month.signals.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-amber-700 mb-1 flex items-center gap-1">
                <Signal className="h-3 w-3" /> Signals ({month.signal_count})
              </h4>
              <div className="space-y-1">
                {month.signals.map((s, i) => (
                  <div key={i} className="flex items-center justify-between text-xs bg-amber-50/50 rounded px-2 py-1">
                    <span className="text-gray-700 truncate max-w-[300px]">{s.title}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-400">{s.subtype}</span>
                      {s.revenue_impact > 0 && (
                        <span className="text-amber-600 font-medium">{fmtDollar(s.revenue_impact)}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Decisions */}
          {month.decisions.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-purple-700 mb-1 flex items-center gap-1">
                <Diamond className="h-3 w-3" /> Decisions ({month.decision_count})
              </h4>
              <div className="space-y-1">
                {month.decisions.map((d, i) => (
                  <div key={i} className="flex items-center justify-between text-xs bg-purple-50/50 rounded px-2 py-1">
                    <span className="text-gray-700 truncate max-w-[300px]">{d.title}</span>
                    {d.revenue_impact > 0 && (
                      <span className="text-purple-600 font-medium">{fmtDollar(d.revenue_impact)}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Outcomes */}
          {month.outcomes.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-emerald-700 mb-1 flex items-center gap-1">
                <Star className="h-3 w-3" /> Outcomes ({month.outcome_count})
              </h4>
              <div className="space-y-1">
                {month.outcomes.map((o, i) => (
                  <div key={i} className="flex items-center justify-between text-xs bg-emerald-50/50 rounded px-2 py-1">
                    <span className="text-gray-700 truncate max-w-[300px]">{o.title}</span>
                    <span className={`font-bold ${
                      o.revenue_impact_type === 'expansion' ? 'text-emerald-600' :
                      o.revenue_impact_type === 'protected' ? 'text-blue-600' :
                      'text-red-600'
                    }`}>
                      {fmtDollar(o.revenue_impact)} {o.revenue_impact_type}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* KPI Movements */}
          {month.kpi_movements.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-600 mb-1 flex items-center gap-1">
                <BarChart3 className="h-3 w-3" /> KPI Scores ({month.kpi_movements.length})
              </h4>
              <div className="flex flex-wrap gap-1">
                {month.kpi_movements.map((kpi, i) => (
                  <span key={i} className="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                    {kpi.kpi_code}: {kpi.avg_score}
                    {kpi.metric && <span className="text-gray-400"> ({kpi.metric})</span>}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Cumulative impact */}
          <div className="pt-2 border-t border-gray-100 flex items-center gap-4 text-xs text-gray-500">
            <span>Cumulative:</span>
            <span className="text-emerald-600 font-medium">
              Protected {fmtDollar(month.cumulative_impact.protected)}
            </span>
            <span className="text-emerald-600 font-medium">
              Expanded {fmtDollar(month.cumulative_impact.expanded)}
            </span>
            {month.cumulative_impact.at_risk > 0 && (
              <span className="text-red-500 font-medium">
                At Risk {fmtDollar(month.cumulative_impact.at_risk)}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

/** Revenue Timeline — full tab component */
const RevenueTimeline: React.FC = () => {
  const [data, setData] = useState<TimelineData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedMonth, setExpandedMonth] = useState<string | null>(null);
  const [period, setPeriod] = useState<'3m' | '6m' | '12m'>('6m');

  const fetchTimeline = useCallback(async (p: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiCall(`/api/outcome-roi/timeline?period=${p}`);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `HTTP ${res.status}`);
      }
      const result = await res.json();
      setData(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load timeline');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTimeline(period);
  }, [period, fetchTimeline]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center gap-3 text-gray-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Loading revenue timeline...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="h-8 w-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm text-gray-500">{error}</p>
          <p className="text-xs text-gray-400 mt-1">Context graph data is required for the revenue timeline.</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const maxSignals = Math.max(...data.timeline.map(m => m.signal_count), 1);

  return (
    <div className="space-y-6">
      {/* Period selector + summary cards */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {(['3m', '6m', '12m'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition ${
                period === p
                  ? 'bg-indigo-50 border-indigo-200 text-indigo-700'
                  : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'
              }`}
            >
              {p === '3m' ? '3 Months' : p === '6m' ? '6 Months' : '12 Months'}
            </button>
          ))}
        </div>
        <div className="text-xs text-gray-400">
          {data.period.start} — {data.period.end}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
            <Signal className="h-3.5 w-3.5 text-amber-500" />
            Signals Processed
          </div>
          <div className="text-2xl font-bold text-gray-900">{data.summary.total_signals}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
            <Diamond className="h-3.5 w-3.5 text-purple-500" />
            Decisions Tracked
          </div>
          <div className="text-2xl font-bold text-gray-900">{data.summary.total_decisions}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
            <Star className="h-3.5 w-3.5 text-emerald-500" />
            Outcomes Realized
          </div>
          <div className="text-2xl font-bold text-gray-900">{data.summary.total_outcomes}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
            <DollarSign className="h-3.5 w-3.5 text-emerald-500" />
            Net Revenue Impact
          </div>
          <div className="text-2xl font-bold text-emerald-600">
            {fmtDollar(data.summary.total_revenue_protected + data.summary.total_revenue_expanded)}
          </div>
          <div className="text-xs text-gray-400 mt-0.5">
            {fmtDollar(data.summary.total_revenue_protected)} protected
            {' + '}{fmtDollar(data.summary.total_revenue_expanded)} expanded
          </div>
        </div>
      </div>

      {/* Causal highlights */}
      {data.causal_highlights.length > 0 && (
        <div>
          <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-indigo-500" />
            How We Got Here — Causal Chains
          </h3>
          <div className="space-y-2">
            {data.causal_highlights.map((h, i) => (
              <CausalChainCard key={i} highlight={h} />
            ))}
          </div>
        </div>
      )}

      {/* Monthly timeline */}
      <div>
        <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
          <CalendarDays className="h-4 w-4 text-gray-500" />
          Month-by-Month Timeline
        </h3>
        <div className="space-y-2">
          {data.timeline.map((month) => (
            <TimelineMonthCard
              key={month.month}
              month={month}
              isExpanded={expandedMonth === month.month}
              onToggle={() => setExpandedMonth(expandedMonth === month.month ? null : month.month)}
              maxSignals={maxSignals}
            />
          ))}
        </div>
      </div>

      {/* Peak risk callout */}
      {data.summary.peak_risk_amount > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0" />
          <div>
            <div className="text-sm font-semibold text-red-700">
              Peak Risk: {fmtDollar(data.summary.peak_risk_amount)} in {data.summary.peak_risk_month}
            </div>
            <div className="text-xs text-red-600 mt-0.5">
              The system detected elevated risk signals during this period and tracked interventions that protected revenue.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};


// ────────────────────────────────────────────────────────
// Pillar Boost Panel — CEO investment scenario sliders
// ────────────────────────────────────────────────────────

const PillarBoostPanel: React.FC<{
  velocityDetail: VelocityDetail;
  pillarBoost: PillarBoost;
  onChange: (boost: PillarBoost) => void;
}> = ({ velocityDetail, pillarBoost, onChange }) => {
  const pillars = Object.entries(velocityDetail).sort(([a], [b]) => a.localeCompare(b));

  if (pillars.length === 0) return null;

  const handleBoostChange = (pillarCode: string, value: number) => {
    onChange({ ...pillarBoost, [pillarCode]: value });
  };

  const boostLabel = (v: number) => {
    if (v === 1.0) return 'Current pace';
    if (v < 1.0) return `${Math.round(v * 100)}% effort`;
    return `${v.toFixed(1)}x invest`;
  };

  const boostColor = (v: number) => {
    if (v > 1.0) return 'text-emerald-600';
    if (v < 1.0) return 'text-orange-500';
    return 'text-gray-500';
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <Rocket className="h-4 w-4 text-indigo-500" />
        <span className="text-sm font-semibold text-gray-800">Pillar Investment Scenario</span>
        <span className="text-xs text-gray-400 ml-2">Adjust multipliers to model increased/decreased investment per pillar</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {pillars.map(([code, vel]) => {
          const boost = pillarBoost[code] ?? 1.0;
          const meta = PILLAR_META[code] || { name: vel.pillar_name, color: 'gray', icon: '📊' };

          const currentPct = vel.base_projected_pct * boost;
          const target = vel.industry_target_pct ?? 4.0;
          const gap = Math.max(0, target - currentPct);
          const atTarget = currentPct >= target;

          return (
            <div key={code} className={`border rounded-lg p-3 ${atTarget ? 'border-emerald-200 bg-emerald-50/30' : 'border-gray-100 bg-gray-50/50'}`}>
              <div className="flex items-center gap-1.5 mb-2">
                <span className="text-sm">{meta.icon}</span>
                <span className="text-xs font-medium text-gray-700 truncate">{meta.name}</span>
                {atTarget && <span className="text-xs text-emerald-600 font-medium ml-auto">Leader</span>}
              </div>

              {/* Velocity stats */}
              <div className="flex items-baseline gap-2 mb-1">
                <span className="text-lg font-bold text-gray-900">
                  {vel.velocity_per_month > 0 ? '+' : ''}{vel.velocity_per_month.toFixed(1)}
                </span>
                <span className="text-xs text-gray-400">pts/mo</span>
              </div>

              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>{vel.earliest_score.toFixed(0)} → {vel.latest_score.toFixed(0)}</span>
                <span className="text-gray-400">hdroom: {vel.headroom.toFixed(0)}</span>
              </div>

              {/* Gap to industry benchmark */}
              <div className="mb-2">
                <div className="flex justify-between text-xs mb-0.5">
                  <span className="text-gray-400">Your trajectory</span>
                  <span className="text-gray-400">Target: {target.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5 relative">
                  <div
                    className={`h-1.5 rounded-full ${atTarget ? 'bg-emerald-500' : 'bg-indigo-500'}`}
                    style={{ width: `${Math.min(100, (currentPct / target) * 100)}%` }}
                  />
                  {/* Target marker */}
                  <div className="absolute top-0 right-0 w-0.5 h-1.5 bg-gray-600 rounded" />
                </div>
                {!atTarget && (
                  <div className="text-xs text-amber-600 mt-0.5">
                    Gap: {gap.toFixed(1)}% — need {(vel.boost_needed_for_target ?? (target / vel.base_projected_pct)).toFixed(1)}x boost
                  </div>
                )}
              </div>

              {/* Boost slider */}
              <input
                type="range"
                min={0.5}
                max={3.0}
                step={0.1}
                value={boost}
                onChange={(e) => handleBoostChange(code, parseFloat(e.target.value))}
                className="w-full h-1.5 accent-indigo-600 cursor-pointer"
              />
              <div className="flex justify-between items-center mt-1">
                <span className={`text-xs font-semibold ${boostColor(boost)}`}>
                  {boostLabel(boost)}
                </span>
                <span className="text-xs text-gray-400">
                  → {currentPct.toFixed(1)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};


// ────────────────────────────────────────────────────────
// Main Component
// ────────────────────────────────────────────────────────

const OutcomeROIDashboard: React.FC = () => {
  const [story, setStory] = useState<OutcomeStory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [improvementPct, setImprovementPct] = useState(4.0);
  const [showEvidence, setShowEvidence] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'timeline' | 'roadmap'>('overview');
  const [mode, setMode] = useState<'velocity' | 'flat'>('velocity');
  const [pillarBoost, setPillarBoost] = useState<PillarBoost>({});
  const [velocityDetail, setVelocityDetail] = useState<VelocityDetail>({});

  const fetchStory = useCallback(async (
    pct: number,
    isDemo: boolean,
    currentMode: 'velocity' | 'flat' = 'velocity',
    boost: PillarBoost = {},
  ): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      let res: Response;
      if (isDemo) {
        res = await apiCall(`/api/outcome-roi/demo?improvement_pct=${pct}`);
      } else {
        const params = new URLSearchParams({
          improvement_pct: String(pct),
          mode: currentMode,
        });
        const hasBoost = Object.keys(boost).length > 0;
        if (hasBoost) {
          // POST with pillar_boost body
          res = await apiCall(`/api/outcome-roi/story?${params}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pillar_boost: boost }),
          });
        } else {
          res = await apiCall(`/api/outcome-roi/story?${params}`);
        }
      }
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        if (res.status === 400 || res.status === 403) {
          if (!isDemo) {
            setDemoMode(true);
            return fetchStory(pct, true, currentMode, boost);
          }
        }
        throw new Error(errData.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setStory(data.story);
      setDemoMode(isDemo);  // reset demo flag based on which endpoint succeeded
      if (data.velocity_detail) {
        setVelocityDetail(data.velocity_detail);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      if (!isDemo) {
        setDemoMode(true);
        return fetchStory(pct, true, currentMode, boost);
      }
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStory(improvementPct, demoMode, mode, pillarBoost);
  }, []);

  const handleSliderChange = (newPct: number) => {
    setImprovementPct(newPct);
    fetchStory(newPct, demoMode, mode, pillarBoost);
  };

  const handleModeToggle = () => {
    const newMode = mode === 'velocity' ? 'flat' : 'velocity';
    setMode(newMode);
    fetchStory(improvementPct, demoMode, newMode, pillarBoost);
  };

  const handleBoostChange = (newBoost: PillarBoost) => {
    setPillarBoost(newBoost);
    fetchStory(improvementPct, demoMode, mode, newBoost);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex items-center gap-3 text-gray-500">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Loading outcome story...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex items-center gap-3 text-red-500">
          <AlertCircle className="h-6 w-6" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  if (!story) return null;

  const tabs = [
    { id: 'overview' as const, label: 'ROI Overview', icon: <BarChart3 className="h-4 w-4" /> },
    { id: 'timeline' as const, label: 'Revenue Timeline', icon: <GitBranch className="h-4 w-4" /> },
    { id: 'roadmap' as const, label: 'Implementation Roadmap', icon: <Map className="h-4 w-4" /> },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Page header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Outcome ROI</h1>
            <p className="text-sm text-gray-500 mt-1">
              Business outcomes delivered and projected — not operational KPIs
            </p>
          </div>
          <div className="flex items-center gap-4">
            {activeTab === 'overview' && (
              <>
                {/* Evidence toggle */}
                <button
                  onClick={() => setShowEvidence(!showEvidence)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm border transition ${
                    showEvidence
                      ? 'bg-indigo-50 border-indigo-200 text-indigo-700'
                      : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  {showEvidence ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                  {showEvidence ? 'Evidence On' : 'Evidence Off'}
                </button>

                {/* Mode toggle: Velocity vs Flat */}
                <button
                  onClick={handleModeToggle}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm border transition ${
                    mode === 'velocity'
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                      : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'
                  }`}
                  title={mode === 'velocity'
                    ? 'Velocity mode: per-pillar rates from historical data'
                    : 'Flat mode: uniform improvement % across all pillars'
                  }
                >
                  {mode === 'velocity'
                    ? <Gauge className="h-4 w-4" />
                    : <SlidersHorizontal className="h-4 w-4" />
                  }
                  {mode === 'velocity' ? 'Velocity' : 'Flat'}
                </button>

                {/* Flat mode slider (only shown in flat mode) */}
                {mode === 'flat' && (
                  <div className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg px-4 py-2">
                    <SlidersHorizontal className="h-4 w-4 text-gray-400" />
                    <span className="text-xs text-gray-500">Forward target:</span>
                    <input
                      type="range"
                      min={1}
                      max={6}
                      step={0.5}
                      value={improvementPct}
                      onChange={(e) => handleSliderChange(parseFloat(e.target.value))}
                      className="w-24 accent-indigo-600"
                    />
                    <span className="text-sm font-bold text-indigo-600 w-10 text-right">
                      {improvementPct}%
                    </span>
                  </div>
                )}
              </>
            )}

            {demoMode && (
              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded-full font-medium">
                Demo Mode
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Tab navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-0 -mb-px items-center">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
          <div className="ml-auto pb-1">
            <NavLogoutButton variant="inline" />
          </div>
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <>
          {/* Combined hero stats */}
          <CombinedHero combined={story.combined} />

          {/* Pillar Boost Panel (velocity mode only) */}
          {mode === 'velocity' && Object.keys(velocityDetail).length > 0 && (
            <PillarBoostPanel
              velocityDetail={velocityDetail}
              pillarBoost={pillarBoost}
              onChange={handleBoostChange}
            />
          )}

          {/* Bridge narrative */}
          <BridgeSection bridge={story.bridge} />

          {/* Side-by-side panels */}
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Historical — left */}
            <OutcomePanel
              result={story.historical}
              accentColor="text-blue-600"
              accentBg="bg-blue-50"
              headerIcon={<CheckCircle2 className="h-5 w-5 text-blue-500" />}
              showEvidence={showEvidence}
            />

            {/* Forward — right */}
            <OutcomePanel
              result={story.forward}
              accentColor="text-emerald-600"
              accentBg="bg-emerald-50"
              headerIcon={<TrendingUp className="h-5 w-5 text-emerald-500" />}
              showEvidence={showEvidence}
            />
          </div>
        </>
      )}

      {activeTab === 'timeline' && (
        <RevenueTimeline />
      )}

      {activeTab === 'roadmap' && (
        <>
          {/* Historical Details — Account-Level Evidence */}
          <HistoricalDetailsPanel />

          {/* Implementation Roadmap — "How to get there" */}
          {story.roadmap && (
            <RoadmapSection roadmap={story.roadmap} />
          )}
        </>
      )}
    </div>
  );
};

export default OutcomeROIDashboard;
