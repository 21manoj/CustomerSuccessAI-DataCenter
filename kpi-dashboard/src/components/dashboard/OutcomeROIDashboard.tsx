import React, { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, DollarSign, Target, Shield, Zap,
  ArrowRight, Activity, Clock, BarChart3, CheckCircle2, ChevronRight,
  Loader2, AlertCircle, SlidersHorizontal, ArrowUpRight, ArrowDownRight,
  Sparkles, Eye, EyeOff
} from 'lucide-react';
import { apiCall } from '../../utils/api';

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
  payback_months: number;
  improvement_pct_avg: number;
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
}

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
              {metric.baseline_value}{metric.unit === 'percent' ? '%' : ` ${metric.unit}`}
              {' '}<ArrowRight className="inline h-3 w-3" />{' '}
              {metric.current_value}{metric.unit === 'percent' ? '%' : ` ${metric.unit}`}
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
          <span>Payback: {s.payback_months < 100 ? `${s.payback_months.toFixed(1)} months` : 'N/A'}</span>
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
// Main Component
// ────────────────────────────────────────────────────────

const OutcomeROIDashboard: React.FC = () => {
  const [story, setStory] = useState<OutcomeStory | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [improvementPct, setImprovementPct] = useState(4.0);
  const [showEvidence, setShowEvidence] = useState(false);
  const [demoMode, setDemoMode] = useState(false);

  const fetchStory = useCallback(async (pct: number, isDemo: boolean): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const endpoint = isDemo
        ? `/api/outcome-roi/demo?improvement_pct=${pct}`
        : `/api/outcome-roi/story?improvement_pct=${pct}`;
      const res = await apiCall(endpoint);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        // If auth fails, fall back to demo
        if (res.status === 400 || res.status === 403) {
          if (!isDemo) {
            setDemoMode(true);
            return fetchStory(pct, true);
          }
        }
        throw new Error(errData.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setStory(data.story);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      // Auto-fallback to demo mode
      if (!isDemo) {
        setDemoMode(true);
        return fetchStory(pct, true);
      }
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStory(improvementPct, demoMode);
  }, []);

  const handleSliderChange = (newPct: number) => {
    setImprovementPct(newPct);
    fetchStory(newPct, demoMode);
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

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Page header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Outcome ROI</h1>
            <p className="text-sm text-gray-500 mt-1">
              Business outcomes delivered and projected — not operational KPIs
            </p>
          </div>
          <div className="flex items-center gap-4">
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

            {/* Improvement slider */}
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

            {demoMode && (
              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded-full font-medium">
                Demo Mode
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Combined hero stats */}
      <CombinedHero combined={story.combined} />

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
    </div>
  );
};

export default OutcomeROIDashboard;
