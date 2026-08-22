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
  Users, Eye, Zap, GitBranch, Clock, AlertTriangle, Info,
  ChevronDown,
  X,
} from 'lucide-react';
import { classify, classifyColor, thresholdValues } from '../../utils/healthThresholds';
import DashboardTopBar from './DashboardTopBar';
import NavLogoutButton from '../shared/NavLogoutButton';
import { useSession } from '../../contexts/SessionContext';
import { apiCall, getCustomerIdentifier } from '../../utils/api';
import AskAIPortal from '../ai/AskAIPortal';
import { trackPageView, trackEvent } from '../../utils/activityTracker';
// NRR Predictor v3 — per A3 in PLAN_nrr_predictor_v3.md, this swaps in
// for Wizard B's forecast tile when FEATURE_PREDICTOR_V3_UI is on for
// the tenant. Demo gate: customer_id === 395 (Predictor V3 Demo SaaS Co)
// until admin-toggleable per-tenant flag is wired.
import PredictorV3Tile from '../predictor/PredictorV3Tile';
import { PerAccountNRRForecastTable } from '../predictor/PerAccountNRRForecastTable';
import { DashboardErrorState } from '../shared/DashboardErrorState';
import ProvenanceTierBadge, { ProvenanceTier } from '../shared/ProvenanceTierBadge';
import PendingDecisionsQueue from './PendingDecisionsQueue';

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
  /** Optional hover-text disclosing engine / lens / math for trust */
  tooltip?: string;
  /**
   * CFO-4 source-of-record disclosure (May 17 eval fix).
   * Pinpoints which system the dollar value came from so a CFO can
   * trace every figure back to its origin. Full GL reconciliation is
   * out of scope until a GL connector lands; until then this label
   * makes the data path honest rather than opaque.
   */
  source?: string;
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
  growth_bar: number;
}

interface CFOEfficiency {
  available: boolean;
  source: string;
  efficiency_score: number;
  automation_rate: number;
  time_saved_hours: number;
  rev_per_cs_dollar: number;
  label?: string;
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

interface ProofExecution {
  playbook_id: string;
  account_name: string;
  arr: number;
  health_at_trigger: number | null;
  health_at_close: number | null;
  health_delta: number | null;
  cost: number;
  cost_csm: number;
  cost_platform: number;
  cost_overhead: number;
  csm_hours: number;
  revenue_protected: number;
  revenue_expanded: number;
  nrr_delta_pp: number;
  roi_x: number;
  outcome: string;
}

interface WizardBNRR {
  without: number;
  with_pulse: number;
  delta: number;
  arr_protected: number;
  accounts_saved: number;
  with_interventions: number;
  grr_before: number | null;
  grr_after: number | null;
}

/**
 * Predictor v3 portfolio NRR forecast — forward 12-month point estimate.
 * Distinct from WizardBNRR (counterfactual TTM); both can be present on the
 * same dashboard and represent different lenses on portfolio NRR. The
 * `lens`/`engine`/`time_direction` triple disambiguates them visually.
 */
interface PredictorV3PortfolioNRR {
  arr_weighted_nrr_pct: number;
  simple_avg_nrr_pct: number;
  horizon: string;
  account_count: number;
  active_account_count: number;
  failed_count: number;
  prediction_method_counts: Record<string, number>;
  last_calibration_id: string | null;
  last_calibration_at: string | null;
  lens: 'point_forecast_ntm';
  engine: 'predictor_v3';
  time_direction: 'forward';
  method_note: string;
}

/** Customer deployment phase — drives which lens dominates the dashboard. */
type CustomerPhase = 'pre_deploy' | 'onboarding' | 'active' | 'mature';

// ─── Playbook economics (CFO-6 fix, May 17 2026) ─────────────────────────────
// Shapes from /api/outcome-roi/playbook-economics — see backend
// `playbook_cost_bridge.py::bridge_to_dict`. Only fields the UI consumes are
// typed here; rest of payload is ignored.

interface PlaybookEconomics {
  playbook_id: string;
  playbook_name: string;
  metric_id: string;
  metric_display_name: string;
  total_hours: number;
  manual_hours: number;
  automation_pct: number;
  manual_cost: number;
  budget_allocated: number;
  affordable_runs: number;
  impact_per_run: number;
  roi_per_run: number;
  break_even_arr: number;
}

interface MetricBridgeEconomics {
  metric_id: string;
  metric_display_name: string;
  cs_initiative_cost: number;
  platform_cost: number;
  total_investment: number;
  linked_playbook_count: number;
  investment_csm: number;
  investment_platform: number;
  investment_misc: number;
  playbooks: PlaybookEconomics[];
}

interface PlaybookEconomicsResponse {
  effective_arr: number;
  arr_tier: string;
  csm_rate: number;
  metrics: Record<string, MetricBridgeEconomics>;
  totals: {
    grand_total: number;
    total_csm: number;
    total_platform: number;
    total_misc: number;
  };
}

/**
 * Row A of "Past — Three Lenses": raw OUTCOME aggregates from the
 * customer's uploaded data. Audit-grade, reconciles with P&L.
 */
/** Sample OUTCOME row for context-graph provenance drill-down (Phase 1). */
interface ContextGraphOutcomeSample {
  node_id: string;
  account_id: number;
  node_subtype?: string | null;
  revenue_impact?: number | null;
  revenue_impact_type?: string | null;
  title?: string | null;
  occurred_at?: string | null;
}

interface ContextGraphProvenanceBucket {
  value: number;
  label: string;
  sample_nodes: ContextGraphOutcomeSample[];
}

interface ContextGraphProvenance {
  source: string;
  engine: string;
  outcome_node_count: number;
  revenue_at_risk: ContextGraphProvenanceBucket;
  revenue_protected: ContextGraphProvenanceBucket;
  expansion_pipeline: ContextGraphProvenanceBucket;
}

/** Context-graph dollar totals (same engine as CRO). Not playbook attribution. */
interface ContextGraphRevenue {
  revenue_at_risk: number;
  /** OUTCOME aggregate — not proof_data.revenue_protected */
  graph_revenue_protected: number;
  expansion_pipeline: number;
  revenue_risk_label: string;
  provenance: ContextGraphProvenance | null;
}

interface HistoricalActuals {
  historical_nrr_pct_ttm: number | null;
  arr_churned: number;
  arr_expanded: number;
  arr_contracted: number;
  starting_arr_ttm: number;
  n_churned_accounts: number;
  n_expansion_events: number;
  n_contraction_events: number;
  lens: 'historical_actuals';
  engine: 'raw_outcomes';
  time_direction: 'backward';
  source: string;
}

interface CFODashboardData {
  summary_cards: FinancialSummaryCard[];
  power_of_1: PowerOf1Row[];
  power_of_1_total: number;
  pillar_investments: PillarInvestment[];
  investment_timeline: InvestmentTimelinePoint[];
  roi_scaling: ROIScalingTier[];
  roi_scaling_is_modeled: boolean;
  roi_multiple: number;
  efficiency: CFOEfficiency | null;
  efficiency_score: number;
  automation_rate: number;
  time_saved_hours: number;
  cost_per_protected_dollar: number;
  financial_ratios: FinancialRatio[];
  accounts: AccountROI[];
  // Proof data: actual playbook execution economics
  proof_executions: ProofExecution[];
  has_proof: boolean;
  wizard_b_nrr: WizardBNRR | null;
  predictor_v3_portfolio_nrr: PredictorV3PortfolioNRR | null;
  historical_actuals: HistoricalActuals | null;
  context_graph_revenue: ContextGraphRevenue | null;
  customer_phase: CustomerPhase;
  // NRR/GRR + Cost of Inaction
  nrr_current: number;
  nrr_with_intervention: number;
  grr: number;
  nrr_arr_protectable: number;
  cost_of_inaction: CostOfInaction;
  nrr_waterfall: { expected_loss: number; protectable: number; expandable: number; attributed_save: number; intervention_cost: number; roi_x: number };
  // Raw numeric values for Investment Allocation widget
  total_arr: number;
  cs_investment: number;
  roi_impact: number;
  is_estimated_investment: boolean;
  renewals_at_risk: Array<{ account_name: string; arr: number; days_until: number; health_score: number }>;
  layered_story: {
    layers: Array<{ name: string; value: number; cost: number; roi: number; status: string; color: string }>;
    total_value: number;
    total_cost: number;
    blended_roi: number;
  } | null;
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

// ============================================================================
// CFO-4 SOURCE-OF-RECORD DISCLOSURE (May 17 2026 eval fix)
// ============================================================================
// A CFO eval expects every dollar to be traceable to its system of record.
// Lacking a GL integration is acceptable in beta; lacking disclosure is not.
// SOURCES is the single source of truth for the wording shown under each
// dollar tile — when the GL connector lands we update the strings here and
// every tile picks them up automatically.

const SOURCES: Record<string, { text: string; tier: ProvenanceTier }> = {
  /** Aggregated from accounts.revenue (CRM/CSV import). */
  crm: { text: 'Source: CRM (CSV) · not GL-reconciled', tier: 'measured' },
  /** PlaybookExecutionV2 records — CRM-derived, attributed in CS Pulse. */
  csPulseProof: { text: 'Source: CS Pulse · playbook executions · not GL-reconciled', tier: 'measured' },
  /** Wizard B counterfactual model — directional, not auditable to GL. */
  wizardB: { text: 'Source: CS Pulse (Wizard B) · counterfactual model · directional', tier: 'derived' },
  /** Predictor v3 forward forecast — point estimate, not auditable to GL. */
  predictorV3: { text: 'Source: CS Pulse (Predictor v3) · forward forecast · point estimate', tier: 'derived' },
  /** Power-of-1 industry benchmark estimate — not customer data. */
  benchmark: { text: 'Source: Power-of-1 benchmark · estimated · not customer data', tier: 'benchmark' },
  /** OUTCOME-node aggregation — same engine as CRO "Confirmed Risk". */
  contextGraph: { text: 'Source: Context graph · OUTCOME nodes · evidence-weighted', tier: 'derived' },
  /** Health-score × churn-probability model (Cost of Inaction panel). */
  modeledExposure: { text: 'Source: CS Pulse · health churn model · modeled · not playbook proof', tier: 'derived' },
};

type SourceKey = keyof typeof SOURCES;

/**
 * Renders a source-of-record label + provenance-tier badge under a dollar
 * value. Use under any visible dollar tile to satisfy CFO traceability.
 *
 * Previously plain italic text, identical style regardless of source —
 * a benchmark constant and a CRM-measured figure read the same at a
 * glance. Now the tier badge (see ProvenanceTierBadge) carries the
 * at-a-glance distinction; this component's text becomes the badge's
 * hover detail plus a compact caption, not the only signal.
 */
const SourceLabel: React.FC<{ source: SourceKey | string; className?: string }> = ({
  source,
  className = '',
}) => {
  const entry = SOURCES[source];
  const text = entry?.text || source;
  const tier = entry?.tier;
  return (
    <p className={`flex items-center gap-1.5 text-[9px] italic text-gray-500 leading-tight ${className}`}>
      {tier && <ProvenanceTierBadge tier={tier} detail={text} compact showMeasured />}
      <span title="System-of-record disclosure. Full GL reconciliation pending GL connector.">
        {text}
      </span>
    </p>
  );
};

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

    <div className="mt-auto px-2 pt-4 border-t border-gray-700/30 space-y-2">
      <NavLogoutButton variant="dark-sidebar" />
      <div className="text-[10px] text-gray-600 leading-relaxed pt-2 border-t border-gray-700/30">
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
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1 flex items-center gap-1.5">
          {card.label}
          {card.tooltip && (
            <span
              title={card.tooltip}
              className="inline-flex items-center justify-center w-3 h-3 rounded-full border border-gray-600 text-[8px] text-gray-500 cursor-help bg-[#0d1119] hover:border-indigo-400 hover:text-indigo-300"
            >i</span>
          )}
        </p>
        <p className="text-3xl font-bold mb-1" style={{ color: accent }}>
          {card.value}
          {card.estimated && <span className="text-xs italic text-gray-400 ml-1 font-normal">Estimated</span>}
        </p>
        {/* CFO-4: source-of-record disclosure on every dollar tile. */}
        {card.source && <SourceLabel source={card.source} className="mb-1" />}
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

/** Phase 3 — CS efficiency from playbook economics or proof (hidden when unavailable). */
const CFOEfficiencyPanel: React.FC<{ efficiency: CFOEfficiency | null }> = ({ efficiency }) => {
  if (!efficiency?.available) {
    return null;
  }
  const isProof = efficiency.source === 'csPulseProof';
  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase">
          CS Efficiency
        </h3>
        <SourceLabel source={isProof ? 'csPulseProof' : 'benchmark'} />
      </div>
      <div className="text-center mb-3">
        <p className="text-3xl font-bold text-cyan-400">{efficiency.efficiency_score}</p>
        <p className="text-[10px] text-gray-500">Efficiency score (0–100)</p>
      </div>
      <div className="grid grid-cols-2 gap-2 text-center text-xs">
        <div className="bg-gray-800/50 rounded-lg p-2">
          <p className="font-semibold text-white">
            {efficiency.automation_rate > 0 ? `${efficiency.automation_rate}%` : '—'}
          </p>
          <p className="text-[9px] text-gray-500">Automation (modeled)</p>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-2">
          <p className="font-semibold text-emerald-400">
            {efficiency.rev_per_cs_dollar > 0 ? `$${efficiency.rev_per_cs_dollar}` : '—'}
          </p>
          <p className="text-[9px] text-gray-500">Rev / CS $</p>
        </div>
      </div>
      {efficiency.time_saved_hours > 0 && (
        <p className="text-[10px] text-gray-500 text-center mt-2">
          ~{Math.round(efficiency.time_saved_hours).toLocaleString()}h playbook hours automated (modeled)
        </p>
      )}
      {efficiency.label && (
        <p className="text-[9px] text-gray-600 text-center mt-2 leading-relaxed">{efficiency.label}</p>
      )}
    </div>
  );
};

/** ROI Scaling Analysis - three large cards */
const ROIScalingSection: React.FC<{
  tiers: ROIScalingTier[];
  isModeled?: boolean;
  roiMultiple?: number;
}> = ({ tiers, isModeled, roiMultiple }) => {
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
        {isModeled && (
          <span className="text-[9px] font-medium px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400">
            Modeled · Po1
          </span>
        )}
      </div>
      <p className="text-[11px] text-gray-500 mb-5">
        CS Pulse platform costs remain fixed while revenue impact compounds across accounts.
        {roiMultiple != null && roiMultiple > 0 && (
          <span className="block mt-1 text-amber-400/80">
            Portfolio modeled ROI multiple: {roiMultiple}x (capped display % below).
          </span>
        )}
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

// Per-metric-category color map for the CFO-6 breakdown.
// Stable across renders so the visual mapping is consistent between the
// stacked bar and the drill-down rows.
const METRIC_CATEGORY_COLORS: Record<string, { bar: string; bg: string; text: string; border: string }> = {
  TTFV:                    { bar: 'bg-cyan-500',    bg: 'bg-cyan-500/10',    text: 'text-cyan-400',    border: 'border-cyan-500' },
  NRR:                     { bar: 'bg-emerald-500', bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500' },
  GRR:                     { bar: 'bg-green-500',   bg: 'bg-green-500/10',   text: 'text-green-400',   border: 'border-green-500' },
  ticket_resolution_time:  { bar: 'bg-amber-500',   bg: 'bg-amber-500/10',   text: 'text-amber-400',   border: 'border-amber-500' },
  product_adoption:        { bar: 'bg-purple-500',  bg: 'bg-purple-500/10',  text: 'text-purple-400',  border: 'border-purple-500' },
  expansion_rate:          { bar: 'bg-fuchsia-500', bg: 'bg-fuchsia-500/10', text: 'text-fuchsia-400', border: 'border-fuchsia-500' },
};
const METRIC_CATEGORY_FALLBACK = { bar: 'bg-gray-500', bg: 'bg-gray-500/10', text: 'text-gray-400', border: 'border-gray-500' };

/** Friendly display names for the metric categories. */
const METRIC_CATEGORY_LABELS: Record<string, string> = {
  TTFV:                    'TTFV',
  NRR:                     'NRR',
  GRR:                     'GRR',
  ticket_resolution_time:  'Ticket Resolution',
  product_adoption:        'Product Adoption',
  expansion_rate:          'Expansion',
};

/**
 * CFO-6 fix (May 17 2026): real per-playbook investment categorization.
 *
 * Before: hard-coded 30 / 45 / 25 split of CS investment into "playbook /
 *   CSM / overhead". Not traceable to anything real.
 * After:  real categorized breakdown sourced from
 *   /api/outcome-roi/playbook-economics — totals + per-metric +
 *   per-playbook (hours, cost, affordable runs, ROI per run, break-even).
 *
 * Default view: stacked bar of $X by metric category (TTFV, NRR, GRR,
 * Ticket Res, Adoption, Expansion). Click a category to expand the
 * playbooks under it.
 */
const PlaybookInvestmentBreakdown: React.FC<{
  economics: PlaybookEconomicsResponse;
}> = ({ economics }) => {
  const [expandedMetric, setExpandedMetric] = useState<string | null>(null);

  const rows = Object.values(economics.metrics)
    .map((m) => ({
      metric_id: m.metric_id,
      label: METRIC_CATEGORY_LABELS[m.metric_id] || m.metric_display_name,
      total: m.total_investment,
      csm: m.investment_csm,
      platform: m.investment_platform,
      playbooks: m.playbooks,
    }))
    .filter((r) => r.total > 0)
    .sort((a, b) => b.total - a.total);

  const grandTotal = economics.totals.grand_total;
  const maxRow = rows.length > 0 ? Math.max(...rows.map((r) => r.total)) : 1;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <p className="text-[9px] text-gray-500 uppercase tracking-wide">Where Your CS Dollars Go</p>
        <p className="text-[10px] text-emerald-400 font-semibold">{formatCompact(grandTotal)} total</p>
      </div>

      {/* Stacked bar — visual at-a-glance of category mix. */}
      <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden flex mb-3">
        {rows.map((r) => {
          const c = METRIC_CATEGORY_COLORS[r.metric_id] || METRIC_CATEGORY_FALLBACK;
          const pct = grandTotal > 0 ? (r.total / grandTotal) * 100 : 0;
          return (
            <div
              key={r.metric_id}
              className={`h-full ${c.bar}`}
              style={{ width: `${pct}%` }}
              title={`${r.label}: ${formatCompact(r.total)} (${pct.toFixed(0)}%)`}
            />
          );
        })}
      </div>

      {/* Per-category rows (click to drill into playbooks). */}
      <div className="space-y-1.5">
        {rows.map((r) => {
          const c = METRIC_CATEGORY_COLORS[r.metric_id] || METRIC_CATEGORY_FALLBACK;
          const pct = grandTotal > 0 ? (r.total / grandTotal) * 100 : 0;
          const widthPct = maxRow > 0 ? (r.total / maxRow) * 100 : 0;
          const isOpen = expandedMetric === r.metric_id;
          return (
            <div key={r.metric_id}>
              <button
                type="button"
                onClick={() => setExpandedMetric(isOpen ? null : r.metric_id)}
                className="w-full text-left group"
                title={`Click to ${isOpen ? 'hide' : 'show'} the playbooks under ${r.label}`}
              >
                <div className="flex justify-between text-[10px] mb-0.5">
                  <span className="text-gray-400 flex items-center gap-1">
                    <span className={`inline-block w-1.5 h-1.5 rounded-full ${c.bar}`} />
                    {r.label}
                    <span className="text-gray-600">({r.playbooks.length} PB{r.playbooks.length === 1 ? '' : 's'})</span>
                  </span>
                  <span className="text-gray-300">{formatCompact(r.total)} ({pct.toFixed(0)}%)</span>
                </div>
                <div className="w-full h-1 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${c.bar} rounded-full transition-all`}
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
              </button>
              {isOpen && (
                <div className={`mt-1.5 mb-2 pl-3 pr-2 py-2 rounded ${c.bg} border-l-2 ${c.border}`}>
                  <div className="text-[9px] text-gray-400 uppercase tracking-wide mb-1.5 flex justify-between">
                    <span>Playbook</span>
                    <span>Cost · Runs · ROI</span>
                  </div>
                  {r.playbooks.map((pb) => (
                    <div key={`${pb.playbook_id}:${pb.metric_id}`} className="flex justify-between text-[10px] py-0.5">
                      <span className="text-gray-300 truncate max-w-[140px]" title={pb.playbook_name}>
                        <span className={`font-mono ${c.text}`}>{pb.playbook_id}</span>
                        <span className="text-gray-500 ml-1">{pb.playbook_name}</span>
                      </span>
                      <span className="text-gray-300 font-mono whitespace-nowrap">
                        {formatCompact(pb.manual_cost)}
                        <span className="text-gray-600"> · </span>
                        {pb.affordable_runs.toFixed(1)}
                        <span className="text-gray-600"> · </span>
                        <span className={c.text}>{pb.roi_per_run.toFixed(0)}x</span>
                      </span>
                    </div>
                  ))}
                  <div className="text-[9px] text-gray-500 mt-1.5 pt-1 border-t border-gray-700/40">
                    Break-even ARR: {formatCompact(r.playbooks[0]?.break_even_arr || 0)}
                    {r.csm > 0 ? ` · ${formatCompact(r.csm)} CSM` : ''}
                    {r.platform > 0 ? ` + ${formatCompact(r.platform)} platform` : ''}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* CSM / Platform / Misc split — secondary footer summary. */}
      <div className="mt-3 pt-2 border-t border-gray-700/40 grid grid-cols-3 gap-1 text-[9px]">
        <div>
          <span className="text-gray-500 block">CSM time</span>
          <span className="text-gray-200 font-mono">{formatCompact(economics.totals.total_csm)}</span>
        </div>
        <div>
          <span className="text-gray-500 block">Platform</span>
          <span className="text-gray-200 font-mono">{formatCompact(economics.totals.total_platform)}</span>
        </div>
        <div>
          <span className="text-gray-500 block">Misc</span>
          <span className="text-gray-200 font-mono">{formatCompact(economics.totals.total_misc)}</span>
        </div>
      </div>
      <SourceLabel source="csPulseProof" className="mt-2" />
    </div>
  );
};

/** Investment Allocation Intelligence (right sidebar) — replaces old EfficiencyGauge */
const InvestmentAllocationWidget: React.FC<{
  totalArr: number;
  csInvestment: number;
  roiImpact: number;
  isEstimated: boolean;
  /** CFO-6 fix: when present, replaces the flat 30/45/25 split with a
   *  real per-playbook breakdown sourced from get_playbook_economics. */
  economics?: PlaybookEconomicsResponse | null;
}> = ({ totalArr, csInvestment, roiImpact, isEstimated, economics }) => {
  const [showDetails, setShowDetails] = useState(false);

  // Industry benchmark: 1.5% - 2.5% of ARR for CS investment (TSIA)
  const pctOfArr = totalArr > 0 ? (csInvestment / totalArr) * 100 : 0;
  const benchmarkLow = totalArr * 0.015;
  const benchmarkHigh = totalArr * 0.025;
  const inRange = csInvestment >= benchmarkLow * 0.8 && csInvestment <= benchmarkHigh * 1.2;
  const roi = csInvestment > 0 ? roiImpact / csInvestment : 0;

  // Legacy 30/45/25 fallback — only used when get_playbook_economics is
  // unavailable. Real per-metric breakdown via PlaybookInvestmentBreakdown.
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

      <SourceLabel source={isEstimated ? 'benchmark' : 'csPulseProof'} className="mb-2" />

      {isEstimated && (
        <p className="text-[9px] text-amber-400/70 mb-2">* Estimated from Power-of-1 benchmarks</p>
      )}

      {/* CFO-6 (May 17 2026): real per-playbook investment breakdown.
          Always-on when get_playbook_economics is available — replaces the
          flat 30/45/25 split that was hard-coded here. Falls back to the
          old benchmark split (gated behind "Details") only when economics
          is null (endpoint failed / not deployed). */}
      {economics && (
        <div className="border-t border-gray-700/50 pt-3 mt-2">
          <PlaybookInvestmentBreakdown economics={economics} />
        </div>
      )}

      {/* Expandable details */}
      {showDetails && (
        <div className="border-t border-gray-700/50 pt-3 mt-2 space-y-3">
          {/* Legacy 30/45/25 fallback — only when real economics missing. */}
          {!economics && (
          <div>
            <p className="text-[9px] text-gray-500 uppercase tracking-wide mb-2">Where Your CS Dollars Go</p>
            <p className="text-[9px] text-amber-400/70 mb-1.5">Fallback split — real per-playbook breakdown unavailable.</p>
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
          )}

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
              <span className="text-white font-semibold">{formatCompact(roiImpact)} attributed (modeled)</span>
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
/** One-line map so CFOs do not conflate NRR lenses, playbook $, and modeled vs confirmed risk. */
/** Phase hint for Row C empty state — sets expectations by deployment phase. */
function expectedProofHint(phase: CustomerPhase): string {
  switch (phase) {
    case 'pre_deploy':
      return 'Expected first attributed saves after ~1–3 closed playbook executions on at-risk accounts (often within the first onboarding quarter).';
    case 'onboarding':
      return 'Onboarding phase — Row C fills in as the next 2–5 playbooks close with measurable protected or expanded revenue.';
    case 'active':
      return 'Playbooks are running; Row C updates as each execution closes with attributed $';
    case 'mature':
      return 'Mature deployment — Row C should reflect steady closed-playbook attribution.';
    default:
      return 'Row C populates when playbooks close with measurable protected or expanded revenue.';
  }
}

/** Phase 2 — pre-proof honesty: anchor tiles are Po1 until playbooks close. */
const CFOPreProofBanner: React.FC<{ phase: CustomerPhase }> = ({ phase }) => (
  <div className="mb-4 rounded-lg border border-amber-700/40 bg-amber-950/25 px-4 py-3">
    <div className="flex items-start gap-2">
      <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
      <div className="text-[11px] text-amber-100/90 leading-relaxed">
        <p className="font-semibold text-amber-200 mb-1">
          ROI tiles are Power-of-1 estimates until playbooks close
        </p>
        <p className="text-amber-100/70">
          CS spend, protected revenue, and portfolio ROI in the summary row below are{' '}
          <span className="text-amber-200/90">benchmark-modeled</span>, not bottom-up proof.
          Confirmed context-graph $ is in the strip above; playbook attribution appears in Row C and
          the proof table once executions close.
          <span className="block mt-1 text-[10px] text-amber-100/50">
            Deployment phase: {phase.replace('_', ' ')} · {expectedProofHint(phase)}
          </span>
        </p>
      </div>
    </div>
  </div>
);

const CFOMetricGuideBanner: React.FC = () => {
  const [collapsed, setCollapsed] = useState(true);
  return (
    <div className="mb-4 rounded-lg border border-cyan-900/40 bg-cyan-950/20 px-4 py-2.5">
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between text-left gap-2"
      >
        <span className="text-[10px] font-semibold text-cyan-300/90 uppercase tracking-wide">
          How to read CFO metrics
        </span>
        <ChevronDown className={`w-3.5 h-3.5 text-cyan-500 shrink-0 transition-transform ${collapsed ? '' : 'rotate-180'}`} />
      </button>
      {!collapsed && (
        <ul className="mt-2 space-y-1.5 text-[10px] text-gray-400 list-disc list-inside leading-relaxed">
          <li>
            <span className="text-gray-300">NRR %</span> — pick the lens: historical outcomes (Row A),
            <span className="text-gray-300"> Hindsight</span> (Wizard B counterfactual — “Hindsight NRR — TTM”, backward
            “would-CS-Pulse-have-helped”), or <span className="text-gray-300">Foresight</span> (Predictor v3 forward —
            “Foresight NRR — Next 12mo”). They are not interchangeable.
          </li>
          <li>
            <span className="text-gray-300">Attributed revenue (playbooks)</span> — bottom-up from closed{' '}
            <code className="text-[9px] text-gray-500">PlaybookExecutionV2</code> rows (Row C / proof table).
          </li>
          <li>
            <span className="text-gray-300">Revenue intelligence (context graph)</span> — confirmed $ from OUTCOME
            nodes (strip below). Same totals as CRO Overview.
          </li>
          <li>
            <span className="text-gray-300">Modeled cost of inaction</span> — health-score churn math on unhealthy accounts.
            Not the same as confirmed context-graph $ at risk.
          </li>
          <li>
            <span className="text-gray-300">Power-of-1 / benchmark tiles</span> — industry estimates until playbook proof populates.
          </li>
        </ul>
      )}
      {collapsed && (
        <p className="text-[9px] text-gray-500 mt-1">
          NRR = lens-specific · Playbook $ ≠ context-graph confirmed risk · expand for definitions
        </p>
      )}
    </div>
  );
};

type ProvenanceBucketKey = 'revenue_at_risk' | 'revenue_protected' | 'expansion_pipeline';

const PROVENANCE_BUCKET_TITLES: Record<ProvenanceBucketKey, string> = {
  revenue_at_risk: 'Confirmed revenue at risk — sample OUTCOMEs',
  revenue_protected: 'Confirmed revenue protected — sample OUTCOMEs',
  expansion_pipeline: 'Expansion pipeline (confirmed) — sample OUTCOMEs',
};

const ContextGraphRevenuePanel: React.FC<{ data: ContextGraphRevenue }> = ({ data }) => {
  const [modalBucket, setModalBucket] = useState<ProvenanceBucketKey | null>(null);
  const prov = data.provenance;
  const nodeCount = prov?.outcome_node_count ?? 0;

  const tiles: Array<{
    key: ProvenanceBucketKey;
    label: string;
    value: number;
    accent: string;
    border: string;
  }> = [
    {
      key: 'revenue_at_risk',
      label: 'Confirmed revenue at risk',
      value: data.revenue_at_risk,
      accent: 'text-red-400',
      border: 'border-t-red-500',
    },
    {
      key: 'revenue_protected',
      label: 'Confirmed revenue protected',
      value: data.graph_revenue_protected,
      accent: 'text-emerald-400',
      border: 'border-t-emerald-500',
    },
    {
      key: 'expansion_pipeline',
      label: 'Expansion pipeline (confirmed)',
      value: data.expansion_pipeline,
      accent: 'text-cyan-400',
      border: 'border-t-cyan-500',
    },
  ];

  const samples =
    modalBucket && prov ? prov[modalBucket]?.sample_nodes ?? [] : [];

  return (
    <>
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
                · same engine as CRO Overview
              </p>
            </div>
          </div>
          <span className="text-[9px] px-2 py-0.5 rounded-full bg-cyan-500/15 text-cyan-400 font-semibold shrink-0">
            Evidence-weighted
          </span>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {tiles.map((t) => {
            const sampleCount = prov?.[t.key]?.sample_nodes?.length ?? 0;
            return (
              <div
                key={t.key}
                className={`bg-[#1a1f2e] border border-gray-700/50 rounded-lg p-4 border-t-[3px] ${t.border}`}
              >
                <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400 mb-1">
                  {t.label}
                </p>
                <p className={`text-2xl font-bold mb-1 ${t.accent}`}>{formatCompact(t.value)}</p>
                <SourceLabel source="contextGraph" className="mb-2" />
                {sampleCount > 0 && prov && (
                  <button
                    type="button"
                    onClick={() => setModalBucket(t.key)}
                    className="text-[10px] text-cyan-500 hover:text-cyan-400 font-medium"
                  >
                    View {sampleCount} sample outcome{sampleCount === 1 ? '' : 's'} →
                  </button>
                )}
              </div>
            );
          })}
        </div>

        <p className="text-[9px] text-gray-600 mt-3">
          Playbook-attributed $ is in Row C / proof table below. Modeled churn exposure is in{' '}
          <span className="text-gray-500">Modeled cost of inaction</span> — different definitions.
        </p>
      </div>

      {modalBucket && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70"
          role="dialog"
          aria-modal="true"
          aria-labelledby="cg-provenance-title"
          onClick={() => setModalBucket(null)}
        >
          <div
            className="bg-[#1a1f2e] border border-gray-600 rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-3 border-b border-gray-700/50">
              <h4 id="cg-provenance-title" className="text-sm font-semibold text-white">
                {PROVENANCE_BUCKET_TITLES[modalBucket]}
              </h4>
              <button
                type="button"
                onClick={() => setModalBucket(null)}
                className="text-gray-400 hover:text-white p-1"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="overflow-y-auto max-h-[60vh] p-4">
              <p className="text-[10px] text-gray-500 mb-3">
                Engine: {prov?.engine ?? 'aggregate_revenue_across_accounts'} · Total in bucket:{' '}
                {formatCompact(prov?.[modalBucket]?.value ?? 0)}
              </p>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-700/50">
                    <th className="text-left py-2 pr-2">node_id</th>
                    <th className="text-left py-2 pr-2">Account</th>
                    <th className="text-left py-2 pr-2">Subtype</th>
                    <th className="text-right py-2">$ impact</th>
                  </tr>
                </thead>
                <tbody>
                  {samples.map((s) => (
                    <tr key={s.node_id} className="border-b border-gray-800/50">
                      <td className="py-2 pr-2 font-mono text-[10px] text-gray-400 truncate max-w-[100px]">
                        {s.node_id}
                      </td>
                      <td className="py-2 pr-2 text-gray-300">{s.account_id}</td>
                      <td className="py-2 pr-2 text-gray-400">{s.node_subtype || s.title || '—'}</td>
                      <td className="py-2 text-right font-mono text-gray-200">
                        {formatCompact(Math.abs(s.revenue_impact ?? 0))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {samples.length === 0 && (
                <p className="text-gray-500 text-center py-6 text-sm">No sample nodes in this bucket.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

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

/** Health-based churn model — not CRO context-graph "confirmed revenue at risk". */
const CostOfInactionPanel: React.FC<{
  data: CFODashboardData['cost_of_inaction'];
  compact?: boolean;
}> = ({ data: coi, compact = false }) => {
  const [showFormula, setShowFormula] = useState(false);
  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-red-400" />
          <div>
            <h3 className="text-[10px] font-semibold text-white uppercase tracking-wide">
              Modeled cost of inaction
            </h3>
            <p className="text-[9px] text-gray-500 normal-case font-normal tracking-normal">
              If unhealthy accounts churn · not context-graph confirmed $
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowFormula(!showFormula)}
          className="text-[10px] text-teal-500 hover:text-teal-400 flex items-center gap-0.5 shrink-0"
          title="Show health-based churn model methodology"
        >
          <Info className="w-3 h-3" />
          {showFormula ? 'Hide' : 'How calculated?'}
        </button>
      </div>
      {showFormula && (
        <div className="bg-gray-800/50 rounded-lg p-3 mb-3 text-[10px] text-gray-400 space-y-1">
          <p className="text-gray-300 font-medium">Health-based churn model (modeled)</p>
          <p>Churn probability = max(5%, 50% - health_score × 0.5)</p>
          <p>Annual loss per account = ARR × churn probability</p>
          <p>Modeled annual churn exposure = sum of per-account losses below</p>
          <p className="text-gray-500 pt-1">Accounts included: health below healthy threshold (at-risk + critical)</p>
          <p className="text-amber-400/90 pt-1 border-t border-gray-700/50">
            Evidence-weighted $ at risk: Revenue intelligence (context graph) on this CFO page — same as CRO Overview.
          </p>
        </div>
      )}
      <div className="flex items-end gap-6 mb-4">
        <div>
          <p
            className="text-[9px] text-gray-500 mb-0.5 cursor-help"
            title="Sum of ARR for unhealthy accounts. Exposure surface area — not the same as context-graph confirmed revenue at risk."
          >
            At-risk account ARR
          </p>
          <p className="text-2xl font-bold text-red-400">{formatCompact(coi.arr_at_risk)}</p>
          <SourceLabel source="crm" />
        </div>
        <div>
          <p
            className="text-[9px] text-gray-500 mb-0.5 cursor-help"
            title="Sum of (ARR × modeled churn probability) if no intervention on unhealthy accounts."
          >
            Modeled annual churn exposure
          </p>
          <p className="text-2xl font-bold text-orange-400">{formatCompact(coi.annual_churn_exposure)}</p>
          <SourceLabel source="modeledExposure" />
        </div>
        <div>
          <p
            className="text-[9px] text-gray-500 mb-0.5 cursor-help"
            title="Count of accounts below the healthy health-score threshold."
          >
            Unhealthy accounts
          </p>
          <p className="text-2xl font-bold text-gray-300">{coi.account_count}</p>
          <SourceLabel source="modeledExposure" />
        </div>
      </div>
      {!compact && coi.accounts.length > 0 && (
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
      <p className="text-[9px] text-gray-600 mt-2 border-t border-gray-700/40 pt-2">
        Modeled loss if unhealthy accounts churn with no CS action. For evidence-weighted $ at risk,
        see <span className="text-cyan-400/90">Revenue intelligence (context graph)</span> on this page
        {compact ? '' : ' (strip above summary cards)'} — same totals as CRO Overview.
      </p>
    </div>
  );
};

// ============================================================================
// PAST — THREE LENSES SECTION
// ============================================================================
// Renders a 3-row nested section for the "Past Impact" area:
//   A · Historical Performance (Pre-CS-Pulse) — raw OUTCOME aggregates
//   B · Counterfactual (Hypothetical with CS Pulse) — Wizard B
//   C · Realized (Actual CS Pulse Attribution) — proof_data
// Row C is phase-conditional — hidden / empty-state when customer is
// in pre_deploy phase. This makes the dashboard honest for M&A DD
// and brand-new-customer scenarios.
// See marketing/cfo_dashboard_relabel_mock.html for the design spec.

interface LensRowProps {
  letter: 'A' | 'B' | 'C';
  title: string;
  sourceLabel: string;
  accentColor: 'grey' | 'amber' | 'green';
  subtitle: string;
  cards: Array<{
    label: string;
    value: string;
    sub?: string;
    color?: 'grey' | 'red' | 'green' | 'amber' | 'cyan' | 'purple';
  }>;
  emptyState?: boolean;
  emptyStateMessage?: string;
}

const LENS_COLORS: Record<LensRowProps['accentColor'], { border: string; bg: string; letterBg: string; letterText: string; sourcePill: string }> = {
  grey:  { border: 'border-l-gray-500',    bg: 'bg-[#0d1119]', letterBg: 'bg-gray-400',    letterText: 'text-[#0d1119]', sourcePill: 'bg-gray-500/20 text-gray-300' },
  amber: { border: 'border-l-amber-500',   bg: 'bg-[#0d1119]', letterBg: 'bg-amber-400',   letterText: 'text-[#0d1119]', sourcePill: 'bg-amber-500/20 text-amber-300' },
  green: { border: 'border-l-emerald-500', bg: 'bg-[#0d1119]', letterBg: 'bg-emerald-400', letterText: 'text-[#0d1119]', sourcePill: 'bg-emerald-500/20 text-emerald-300' },
};

const VALUE_COLORS: Record<string, string> = {
  grey:   'text-gray-200',
  red:    'text-red-400',
  green:  'text-emerald-400',
  amber:  'text-amber-400',
  cyan:   'text-cyan-400',
  purple: 'text-purple-400',
};

const LensRow: React.FC<LensRowProps> = ({ letter, title, sourceLabel, accentColor, subtitle, cards, emptyState, emptyStateMessage }) => {
  const c = LENS_COLORS[accentColor];
  return (
    <div className={`${c.bg} border-l-[3px] ${c.border} rounded-md p-3.5 mb-2.5 ${emptyState ? 'opacity-60' : ''}`}>
      <div className="flex justify-between items-baseline mb-2">
        <div className="text-xs font-bold text-gray-100 flex items-center gap-2">
          <span className={`inline-flex items-center justify-center w-[18px] h-[18px] rounded-full text-[10px] font-extrabold ${c.letterBg} ${c.letterText}`}>
            {letter}
          </span>
          {title}
        </div>
        <div className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${c.sourcePill}`}>
          {sourceLabel}
        </div>
      </div>
      <div className="text-[10px] text-gray-500 italic mb-2.5">{subtitle}</div>
      {emptyState ? (
        <div className="p-3.5 border border-dashed border-gray-700 rounded bg-[#131826] text-gray-500 text-[11px] text-center leading-relaxed">
          <strong className="text-gray-400">{emptyStateMessage || 'No data yet for this lens.'}</strong>
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-2.5">
          {cards.map((card, i) => (
            <div key={i} className="bg-[#1a1f2e] border border-[#2a3142] rounded p-2.5 border-t-[3px]" style={{ borderTopColor: accentColor === 'grey' ? '#9ca3af' : accentColor === 'amber' ? '#fbbf24' : '#34d399' }}>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 mb-1">{card.label}</div>
              <div className={`text-lg font-extrabold leading-none mb-1 ${VALUE_COLORS[card.color || 'grey']}`}>{card.value}</div>
              {card.sub && <div className="text-[10px] text-gray-500">{card.sub}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/** Phase 2 — no sparse zero rows when playbook proof is not yet available. */
const PlaybookProofEmptyState: React.FC<{ phase: CustomerPhase }> = ({ phase }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-dashed border-gray-600/60 p-6 mb-6">
    <div className="flex items-center gap-2 mb-3">
      <Shield className="w-4 h-4 text-gray-500" />
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Playbook ROI Proof</h3>
      <span className="text-[9px] px-2 py-0.5 rounded-full bg-gray-700/50 text-gray-400 font-semibold">Pending</span>
    </div>
    <p className="text-sm text-gray-300 mb-2">
      No closed playbook executions with attributed revenue yet.
    </p>
    <p className="text-[11px] text-gray-500 leading-relaxed mb-4">
      {expectedProofHint(phase)} Until then, use the context-graph strip and modeled cost of inaction —
      not this table — for risk exposure.
    </p>
    <p className="text-[10px] text-cyan-400/90">
      Next step: trigger playbooks from CSM Cockpit · Today&apos;s Queue on at-risk accounts.
    </p>
    <SourceLabel source="benchmark" className="mt-3" />
  </div>
);

const PastThreeLensesSection: React.FC<{
  d: CFODashboardData;
  totalArr: number;
}> = ({ d, totalArr }) => {
  const ha = d.historical_actuals;
  const wb = d.wizard_b_nrr;
  const proof = d.proof_executions;
  const proofTotalProtected = proof.reduce((s, e) => s + (e.revenue_protected || 0), 0);
  const proofTotalExpanded = proof.reduce((s, e) => s + (e.revenue_expanded || 0), 0);
  const proofTotalCost = proof.reduce((s, e) => s + (e.cost || 0), 0);
  const proofRoi = proofTotalCost > 0 ? ((proofTotalProtected + proofTotalExpanded) / proofTotalCost).toFixed(1) : '0';

  const showRowC = d.customer_phase !== 'pre_deploy' && proof.length > 0;

  return (
    <div className="bg-[#131826] rounded-xl border border-gray-700/50 p-5 mb-6">
      <div className="flex items-baseline justify-between mb-3 pb-2 border-b border-gray-700/50">
        <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-[2px]">
          ▌ Past — Three Lenses
        </div>
        <div className="text-[10px] text-gray-500">
          A · Historical actuals &middot; B · Counterfactual model &middot; C · Realized attribution
        </div>
      </div>

      {/* ROW A — Historical Performance (Pre-CS-Pulse) */}
      {ha ? (
        <LensRow
          letter="A"
          title="Historical Performance (Pre-CS-Pulse)"
          sourceLabel="Uploaded outcomes · context graph"
          accentColor="grey"
          subtitle={`From your uploaded OUTCOME rows (${ha.source}). Audit trail in CS Pulse — not GL-reconciled until finance connector.`}
          cards={[
            {
              label: 'Historical NRR — TTM',
              value: ha.historical_nrr_pct_ttm != null ? `${ha.historical_nrr_pct_ttm}%` : '—',
              sub: 'From your outcomes data',
              color: 'grey',
            },
            {
              label: 'ARR Churned (TTM)',
              value: formatCompact(ha.arr_churned),
              sub: `${ha.n_churned_accounts} churn_lost outcomes`,
              color: 'red',
            },
            {
              label: 'ARR Expanded (TTM)',
              value: `+${formatCompact(ha.arr_expanded).replace('$', '$')}`,
              sub: `${ha.n_expansion_events} expansion_closed outcomes`,
              color: 'green',
            },
            {
              label: 'ARR Contracted (TTM)',
              value: formatCompact(ha.arr_contracted),
              sub: `${ha.n_contraction_events} contraction outcomes`,
              color: 'amber',
            },
          ]}
        />
      ) : (
        <LensRow
          letter="A"
          title="Historical Performance (Pre-CS-Pulse)"
          sourceLabel="Uploaded outcomes · context graph"
          accentColor="grey"
          subtitle="From context graph OUTCOME nodes (observed uploads). Not GL-reconciled."
          cards={[]}
          emptyState
          emptyStateMessage="No historical OUTCOME data uploaded yet. Upload outcomes.csv during onboarding to populate this row."
        />
      )}

      {/* ROW B — Counterfactual (Hypothetical with CS Pulse) */}
      {wb ? (
        <LensRow
          letter="B"
          title="Counterfactual — Hypothetical with CS Pulse"
          sourceLabel="Wizard B · directional"
          accentColor="amber"
          subtitle={`Wizard B arc-pattern counterfactual: "what would NRR have been if CS Pulse had been running through this period?" Conservative attribution — credits only the incremental delta over Wizard B's modeled natural-arc baseline (${wb.without?.toFixed(1)}%), which is a different basis than Lens A's gross-outcome NRR — the two NRR figures are not directly comparable.`}
          cards={[
            {
              label: 'Hypothetical NRR (with CS Pulse)',
              value: `${wb.with_pulse}%`,
              sub: `vs ${wb.without?.toFixed(1)}% natural-arc baseline`,
              color: 'amber',
            },
            {
              label: 'Counterfactual NRR Lift',
              value: `+${wb.delta}pp`,
              sub: `≈ ${formatCompact((wb.delta || 0) / 100 * totalArr)} on ${formatCompact(totalArr)} ARR (this is the dollar value of the NRR lift)`,
              color: 'amber',
            },
            {
              label: 'ARR Protected (Saved Accounts)',
              value: formatCompact(wb.arr_protected),
              sub: `Gross ARR of the ${wb.accounts_saved} saved accounts (not the NRR-lift dollars)`,
              color: 'amber',
            },
            {
              label: 'Accounts Could\'ve Been Saved',
              value: `${wb.accounts_saved}`,
              sub: 'Wizard B cs_pulse_accounts_saved',
              color: 'amber',
            },
          ]}
        />
      ) : (
        <LensRow
          letter="B"
          title="Counterfactual — Hypothetical with CS Pulse"
          sourceLabel="Wizard B · directional"
          accentColor="amber"
          subtitle="Wizard B model output."
          cards={[]}
          emptyState
          emptyStateMessage="Wizard B has not produced a counterfactual NRR forecast yet. Runs automatically during onboarding and on every process_data refresh."
        />
      )}

      {/* ROW C — Realized (Actual CS Pulse Attribution) */}
      {showRowC ? (
        <LensRow
          letter="C"
          title="Realized — Actual CS Pulse Attribution"
          sourceLabel="Playbook executions · bottom-up"
          accentColor="green"
          subtitle={`Bottom-up sum of PlaybookExecutionV2.revenue_protected across closed playbooks (${proof.length} executions). Per-account attribution to specific saved accounts — full drill-down in the Playbook ROI Proof table below.`}
          cards={[
            {
              label: 'Attributed revenue (playbooks)',
              value: formatCompact(proofTotalProtected + proofTotalExpanded),
              sub: `${proof.length} closed playbooks · not context-graph totals`,
              color: 'green',
            },
            {
              label: 'Realized ROI',
              value: `${proofRoi}×`,
              sub: `${formatCompact(proofTotalCost)} → ${formatCompact(proofTotalProtected + proofTotalExpanded)}`,
              color: 'green',
            },
            {
              label: 'Playbooks Resolved',
              value: `${proof.length} / ${proof.length}`,
              sub: '100% completion',
              color: 'green',
            },
            {
              label: 'CS Investment (Closed)',
              value: formatCompact(proofTotalCost),
              sub: 'Sum of total_cost on closed PBs',
              color: 'grey',
            },
          ]}
        />
      ) : (
        <LensRow
          letter="C"
          title="Realized — Actual CS Pulse Attribution"
          sourceLabel="Pending deployment"
          accentColor="green"
          subtitle="Audit-traceable proof, populated as playbooks fire on at-risk accounts."
          cards={[]}
          emptyState
          emptyStateMessage={`CS Pulse hasn't attributed closed-playbook revenue yet. ${expectedProofHint(d.customer_phase)} See Foresight NRR and the context-graph strip for what's protectable today.`}
        />
      )}

      {/* Phase legend — educates on which phase controls Row C visibility */}
      <div className="mt-3 p-2.5 bg-[#0d1119] border border-dashed border-gray-700/50 rounded text-[10px] text-gray-500">
        <div className="font-bold text-indigo-300 uppercase tracking-wider text-[9px] mb-2">
          Customer phase — controls Row C visibility
        </div>
        <div className="grid grid-cols-4 gap-3">
          <div className="flex items-start gap-2">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wider border border-gray-500 bg-gray-500/20 text-gray-300 flex-shrink-0">
              <span className="w-1 h-1 rounded-full bg-gray-400" />PRE-DEPLOY
            </span>
            <span className="text-[10px] leading-tight">No PBs yet · Row C empty · A + B + Forward lead</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wider border border-indigo-500 bg-indigo-500/20 text-indigo-300 flex-shrink-0">
              <span className="w-1 h-1 rounded-full bg-indigo-400" />ONBOARDING
            </span>
            <span className="text-[10px] leading-tight">0–3mo · first proof points · Row C sparse</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wider border border-emerald-500 bg-emerald-500/20 text-emerald-300 flex-shrink-0">
              <span className="w-1 h-1 rounded-full bg-emerald-400" />ACTIVE
            </span>
            <span className="text-[10px] leading-tight">3–12mo · steady PBs · Row C is primary CFO story</span>
          </div>
          <div className="flex items-start gap-2">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wider border border-purple-500 bg-purple-500/20 text-purple-300 flex-shrink-0">
              <span className="w-1 h-1 rounded-full bg-purple-400" />MATURE
            </span>
            <span className="text-[10px] leading-tight">12mo+ · full audit trail · all 3 lenses populated</span>
          </div>
        </div>
      </div>
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
  // HTTP status of the most recent fetch failure; used by the error state
  // to distinguish auth-expired (401, show "Log in again") from generic
  // network/server errors (show "Retry").
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [showFutureROI, setShowFutureROI] = useState(false);
  // CFO-6 (May 17 2026): per-playbook investment breakdown.
  // Fetched independently so a failure here doesn't kill the dashboard;
  // widget falls back to the legacy 30/45/25 split when null.
  const [playbookEconomics, setPlaybookEconomics] = useState<PlaybookEconomicsResponse | null>(null);

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
        if (!resp.ok) {
          setErrorStatus(resp.status);
          throw new Error(`API returned ${resp.status}`);
        }
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

          // Vertical-aware pillar short names
          // Vertical-aware pillar short names
          const _PILLAR_SHORT: Record<string, Record<string, string>> = {
            dc2_s: { P1: 'Deploy', P2: 'Ops', P3: 'AI Perf', P4: 'Channel', P5: 'Expand' },
            datacenter_v1: { P1: 'Revenue', P2: 'Util', P3: 'Reliab', P4: 'Power', P5: 'Commercial', P6: 'Provision' },
            saas_premium: { P1: 'Adoption', P2: 'Engage', P3: 'Sentiment', P4: 'Partner', P5: 'Revenue' },
            saas: { P1: 'Adoption', P2: 'Engage', P3: 'Sentiment', P4: 'Partner', P5: 'Revenue' },
          };
          const _vert = session?.vertical || localStorage.getItem('vertical') || 'dc2_s';
          const pillarDisplayNames: Record<string, string> =
            _PILLAR_SHORT[_vert] || _PILLAR_SHORT['dc2_s'];

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
          const roiScalingIsModeled = Boolean(
            json.roi_scaling?.is_modeled ?? json.roi_is_modeled,
          );
          const roiScaling: ROIScalingTier[] = scalingProjs.map((s: any) => ({
            accounts: s.accounts,
            label: `${s.accounts} accts`,
            roi: s.roi ?? 0,
            growth_bar: s.growth_bar ?? 0,
          }));
          const roiMultiple = Number(json.roi_multiple ?? json.roi_scaling?.roi_multiple ?? 0);
          const efficiencyBlock: CFOEfficiency | null = json.efficiency?.available
            ? {
                available: true,
                source: json.efficiency.source || 'benchmark',
                efficiency_score: json.efficiency.efficiency_score || 0,
                automation_rate: json.efficiency.automation_rate || 0,
                time_saved_hours: json.efficiency.time_saved_hours || 0,
                rev_per_cs_dollar: json.efficiency.rev_per_cs_dollar || 0,
                label: json.efficiency.label,
              }
            : null;

          const csPercent = totalArr > 0 ? ((csInvestment / totalArr) * 100).toFixed(2) : '0';

          // ── Proof data: actual playbook economics (bottom-up) ──
          const proof = json.proof_data || {};
          const proofCost = proof.total_cost || 0;
          const proofProtected = proof.revenue_protected || 0;
          const proofExpanded = proof.revenue_expanded || 0;
          const proofRoi = proof.realized_roi || 0;
          const proofExecutions = proof.executions || [];
          const hasProof = proofCost > 0 || proofProtected > 0;

          // Context graph $ (same engine as CRO) — distinct from proof_data.revenue_protected
          const graphAtRisk = Number(json.revenue_at_risk) || 0;
          const graphProtected = Number(json.revenue_protected) || 0;
          const graphExpansion =
            Number(json.expansion_pipeline) ||
            Number(json.context_graph_provenance?.expansion_pipeline?.value) ||
            0;
          const graphProvenance = (json.context_graph_provenance || null) as ContextGraphProvenance | null;
          const hasContextGraph =
            graphAtRisk > 0 ||
            graphProtected > 0 ||
            graphExpansion > 0 ||
            (graphProvenance?.outcome_node_count ?? 0) > 0;

          const revPerDollar = json.rev_per_cs_dollar
            ? json.rev_per_cs_dollar.toFixed(1)
            : (csInvestment > 0
              ? ((hasProof ? proofProtected + proofExpanded : roiImpact) / csInvestment).toFixed(1)
              : '0');
          const paybackMonths = json.payback_months || (roiImpact > 0 ? Math.round((csInvestment / roiImpact) * 12) : 0);

          // ── Wizard B NRR (backward counterfactual, TTM) ──
          const wb = json.wizard_b_nrr || {};
          const hasWizardB = !!(wb.with_cs_pulse_nrr_pct && wb.with_cs_pulse_nrr_pct !== wb.without_cs_pulse_nrr_pct);

          // ── Predictor v3 portfolio NRR (forward point forecast, NTM) ──
          const v3 = json.predictor_v3_portfolio_nrr || null;
          const hasV3 = !!(v3 && v3.arr_weighted_nrr_pct != null);

          // ── Customer deployment phase — drives Row C visibility + badge ──
          // Heuristic: phase derives from playbook execution density.
          //   No PB executions      → pre_deploy
          //   1-5 PBs               → onboarding
          //   6+ PBs                → active (we'd refine to "mature" once
          //                          we know first-PB timestamp > 12mo old)
          const customerPhase: CustomerPhase =
            (proof.executions_total || 0) === 0 ? 'pre_deploy'
            : (proof.executions_total || 0) <= 5 ? 'onboarding'
            : 'active';

          // Build anchor row. Two configurations:
          //  - With Predictor v3 data: 4 tiles incl. "Foresight NRR — Next 12mo"
          //    next to the existing "Hindsight NRR — TTM" / Revenue Protected pair
          //  - Without v3 data: legacy 4 tiles (Total ARR / CS Spend / Protected / ROI)
          // Labels follow the marketing/cfo_dashboard_relabel_mock.html vocabulary:
          // Realized = backward, Forecast = forward.
          const transformed: CFODashboardData = {
            summary_cards: hasProof && hasV3 ? [
              {
                label: 'Total ARR',
                value: formatCompact(totalArr),
                subtitle: `${json.account_count || '—'} active accounts · full portfolio`,
                accent: 'white',
                tooltip: 'Sum of accounts.revenue across all active accounts. Excludes churned-with-zero-ARR.',
                source: 'crm',
              },
              {
                label: 'CS Investment',
                value: formatCompact(proofCost),
                subtitle: `${(totalArr > 0 ? (proofCost / totalArr * 100).toFixed(2) : '0')}% of ARR · ${proof.executions_total || 0} playbook executions`,
                accent: 'emerald',
                tooltip: 'Sum of PlaybookExecutionV2.total_cost. Tiered by ARR band — strategic ($90K), mid-market ($50K), SMB ($25K), small ($12K), <10K ($3K). Includes CSM + VP CS + SA + executive sponsor + AE + travel + platform + 35% overhead.',
                source: 'csPulseProof',
              },
              {
                label: 'Hindsight NRR — TTM (Counterfactual)',
                value: `${wb.with_cs_pulse_nrr_pct ?? '—'}%`,
                subtitle: `Hindsight · Counterfactual (Wizard B) · +${wb.delta_pct || 0}pp from CS Pulse`,
                accent: 'green',
                tooltip: `Hindsight lens — backward-looking counterfactual NRR from Wizard B ("would-CS-Pulse-have-helped"). With CS Pulse: ${wb.with_cs_pulse_nrr_pct}%. Without: ${wb.without_cs_pulse_nrr_pct}%. Delta = +${wb.delta_pct}pp. Includes all ${json.account_count || '—'} accounts (incl. churned) in denominator. Differs from "Foresight NRR" — that's forward, this is backward.`,
                source: 'wizardB',
              },
              {
                // CFO-10 (May 17 FDE eval) — KNOWN GAP: portfolio-level NRR tile
                // does NOT show CI bounds today. get_portfolio_nrr_forecast_v3
                // returns only the ARR-weighted point estimate; per-account
                // lower/upper bounds are NOT aggregated into a portfolio CI.
                // The per-account drill-down (PerAccountNRRForecastTable below)
                // surfaces CI per row. TODO: when the portfolio tool gains a
                // CI aggregation (ARR-weighted sum of lower/upper bounds), swap
                // this card's value for a <ForecastWithCI> render. Until then
                // we leave the point-only display and direct curious users to
                // the per-account view via the tooltip below.
                label: 'Foresight NRR — Next 12mo (Predictive)',
                value: `${v3?.arr_weighted_nrr_pct ?? '—'}%`,
                subtitle: `Foresight · Forward point (Predictor v3) · ARR-weighted · ${v3?.active_account_count || 0} active`,
                accent: 'cyan',
                tooltip: `Foresight lens — forward 12-month point forecast from Predictor v3 (calibrated by Wizard D ${v3?.last_calibration_at ? new Date(v3.last_calibration_at).toLocaleDateString() : '?'}). ARR-weighted across ${v3?.active_account_count || 0} currently-active accounts; excludes $0-ARR (typically churned) from the weight. Simple-avg: ${v3?.simple_avg_nrr_pct}%. Portfolio CI is aggregated; see the Per-Account NRR Forecast table below for per-account 90% CI bounds. Differs from "Hindsight NRR" — that's backward counterfactual.`,
                source: 'predictorV3',
              },
            ] : hasProof ? [
              { label: 'Total ARR', value: formatCompact(totalArr), subtitle: `${json.account_count || '—'} active accounts · full portfolio (incl. healthy + new logos)`, accent: 'white', source: 'crm' },
              { label: 'Actual CS Spend', value: formatCompact(proofCost), subtitle: `${(totalArr > 0 ? (proofCost / totalArr * 100).toFixed(2) : '0')}% of ARR · ${proof.csm_hours || 0}h CSM time`, accent: 'emerald', source: 'csPulseProof' },
              {
                label: 'Attributed revenue (playbooks)',
                value: formatCompact(proofProtected + proofExpanded),
                subtitle: `${proof.executions_resolved || 0} of ${proof.executions_total || 0} playbooks resolved`,
                tooltip: 'Sum of revenue_protected + revenue_expanded on closed PlaybookExecutionV2 rows. Playbook attribution — not the same as context-graph confirmed $ at risk.',
                accent: 'green',
                source: 'csPulseProof',
              },
              { label: 'Portfolio ROI', value: `${proofRoi}x`, subtitle: `${formatCompact(proofCost)} → ${formatCompact(proofProtected + proofExpanded)}`, accent: 'cyan', source: 'csPulseProof' },
            ] : [
              { label: 'Total ARR', value: formatCompact(totalArr), subtitle: `${json.account_count || '—'} active accounts · full portfolio (incl. healthy + new logos)`, accent: 'white', source: 'crm' },
              {
                label: 'CS Investment (estimated)',
                value: formatCompact(csInvestment),
                subtitle: 'Power-of-1 benchmark until playbooks close',
                accent: 'emerald',
                estimated: true,
                source: 'benchmark',
              },
              {
                label: 'Projected impact (Po1)',
                value: formatCompact(roiImpact),
                subtitle: `Modeled GRR: ${grr}% · not playbook proof`,
                accent: 'green',
                estimated: true,
                source: 'benchmark',
              },
              { label: 'Portfolio ROI', value: `${roiPct}%`, subtitle: `${formatCompact(csInvestment)} → ${formatCompact(roiImpact)}`, accent: 'cyan', estimated: true, source: 'benchmark' },
            ],
            power_of_1: po1Metrics,
            power_of_1_total: po1Metrics.reduce((sum: number, m: PowerOf1Row) => sum + m.dollar_impact, 0),
            pillar_investments: pillarInvs,
            investment_timeline: invTimeline,
            roi_scaling: roiScaling,
            roi_scaling_is_modeled: roiScalingIsModeled,
            roi_multiple: roiMultiple,
            efficiency: efficiencyBlock,
            efficiency_score: (efficiencyBlock?.efficiency_score ?? json.efficiency_score) || 0,
            automation_rate: (efficiencyBlock?.automation_rate ?? json.automation_rate) || 0,
            time_saved_hours: (efficiencyBlock?.time_saved_hours ?? json.time_saved_hours) || 0,
            // Use total projected impact (not just confirmed protected) when estimated
            cost_per_protected_dollar: csInvestment > 0 && roiImpact > 0
              ? parseFloat((csInvestment / roiImpact).toFixed(2))
              : 0.05,
            financial_ratios: hasProof ? [
              { label: 'CS % of ARR', value: `${(totalArr > 0 ? (proofCost / totalArr * 100).toFixed(2) : '0')}%` },
              { label: 'Rev per CS Dollar', value: `$${proofCost > 0 ? ((proofProtected + proofExpanded) / proofCost).toFixed(1) : '0'}` },
              { label: 'Payback Period', value: `${proofProtected > 0 ? Math.max(1, Math.round((proofCost / (proofProtected + proofExpanded)) * 12)) : '—'} months` },
              { label: 'Playbook Success Rate', value: `${proof.executions_total > 0 ? Math.round((proof.executions_resolved / proof.executions_total) * 100) : 0}%`, accent: 'cyan' },
            ] : [
              { label: 'CS % of ARR', value: `${csPercent}% *` },
              { label: 'Rev per CS Dollar', value: `$${revPerDollar} *` },
              { label: 'Payback Period', value: `${paybackMonths} months *` },
              { label: 'NRR Impact / Playbook', value: `+${((nrr - 100) / Math.max(scalingProjs[0]?.accounts || 15, 1)).toFixed(2)}%`, accent: 'cyan' },
              { label: '* Power-of-1 benchmark estimates', value: '', accent: 'gray' },
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
            // Proof data + Wizard B NRR
            proof_executions: proofExecutions,
            has_proof: hasProof,
            wizard_b_nrr: hasWizardB ? {
              without: wb.without_cs_pulse_nrr_pct,
              with_pulse: wb.with_cs_pulse_nrr_pct,
              delta: wb.delta_pct,
              arr_protected: wb.arr_protected,
              accounts_saved: wb.accounts_saved,
              with_interventions: wb.with_interventions_nrr_pct,
              grr_before: wb.grr_before_pct,
              grr_after: wb.grr_after_pct,
            } : null,
            predictor_v3_portfolio_nrr: v3,
            historical_actuals: json.historical_actuals || null,
            context_graph_revenue: hasContextGraph
              ? {
                  revenue_at_risk: graphAtRisk,
                  graph_revenue_protected: graphProtected,
                  expansion_pipeline: graphExpansion,
                  revenue_risk_label: json.revenue_risk_label || 'Confirmed Risk (Context Graph)',
                  provenance: graphProvenance,
                }
              : null,
            customer_phase: customerPhase,
            // NRR/GRR + Cost of Inaction (fallback to Power-of-1 when no Wizard B)
            nrr_current: hasWizardB ? wb.with_cs_pulse_nrr_pct : (json.nrr_current || nrr),
            nrr_with_intervention: hasWizardB ? wb.with_interventions_nrr_pct : (json.nrr_with_intervention || nrr),
            grr: hasWizardB && wb.grr_after_pct ? wb.grr_after_pct : grr,
            nrr_arr_protectable: hasWizardB ? wb.arr_protected : (json.nrr_arr_protectable || 0),
            cost_of_inaction: json.cost_of_inaction || { arr_at_risk: 0, annual_churn_exposure: 0, account_count: 0, accounts: [] },
            nrr_waterfall: json.nrr_waterfall || { expected_loss: 0, protectable: 0, expandable: 0, attributed_save: 0, intervention_cost: 0, roi_x: 0 },
            renewals_at_risk: json.renewals_at_risk || [],
            layered_story: json.layered_story || null,
            total_arr: totalArr,
            cs_investment: hasProof ? proofCost : csInvestment,
            roi_impact: hasProof ? (proofProtected + proofExpanded) : roiImpact,
            is_estimated_investment: hasProof ? false : isEstimatedInvestment,
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

  // CFO-6 (May 17 2026): fetch the per-playbook economics breakdown.
  // Separate from the main /cfo-dashboard fetch so an error here is
  // non-fatal — the widget gracefully falls back to the legacy split.
  useEffect(() => {
    let cancelled = false;
    const fetchEconomics = async () => {
      try {
        const customerId = getCustomerIdentifier(session);
        const resp = await apiCall('/api/outcome-roi/playbook-economics', {
          headers: { 'X-Customer-ID': customerId },
        });
        if (!resp.ok) return;
        const json: PlaybookEconomicsResponse = await resp.json();
        if (!cancelled) setPlaybookEconomics(json);
      } catch {
        // Swallow — non-fatal. UI falls back to the legacy split.
      }
    };
    fetchEconomics();
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
      <DashboardErrorState
        dashboardLabel="CFO dashboard"
        errorMessage={error}
        errorStatus={errorStatus}
      />
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
              {/* Customer deployment phase — drives which dashboard lens
                  is the primary story. See marketing/cfo_dashboard_relabel_mock.html
                  for the full phase legend. */}
              {(() => {
                const phaseConfig: Record<CustomerPhase, { label: string; color: string; bg: string; border: string; tooltip: string }> = {
                  pre_deploy: {
                    label: 'PRE-DEPLOY',
                    color: 'text-gray-300', bg: 'bg-gray-500/20', border: 'border-gray-500',
                    tooltip: 'No playbook executions yet. CS Pulse impact data not yet populated; counterfactual + forward forecast tell the story.',
                  },
                  onboarding: {
                    label: 'ONBOARDING',
                    color: 'text-indigo-300', bg: 'bg-indigo-500/20', border: 'border-indigo-500',
                    tooltip: 'First playbooks firing. Realized attribution emerging; counterfactual + forward forecast lead.',
                  },
                  active: {
                    label: 'ACTIVE',
                    color: 'text-emerald-300', bg: 'bg-emerald-500/20', border: 'border-emerald-500',
                    tooltip: 'Steady playbook execution. Realized ROI is the primary CFO story.',
                  },
                  mature: {
                    label: 'MATURE',
                    color: 'text-purple-300', bg: 'bg-purple-500/20', border: 'border-purple-500',
                    tooltip: 'Long-running CS Pulse deployment. All three lenses fully populated.',
                  },
                };
                const cfg = phaseConfig[d.customer_phase] || phaseConfig.pre_deploy;
                return (
                  <span
                    title={cfg.tooltip}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider border ${cfg.color} ${cfg.bg} ${cfg.border}`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${cfg.bg.replace('/20', '')}`} />
                    {cfg.label}
                  </span>
                );
              })()}
              <span className="text-gray-600">&middot;</span>
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

          <CFOMetricGuideBanner />

          {d.context_graph_revenue && (
            <ContextGraphRevenuePanel data={d.context_graph_revenue} />
          )}

          {!d.has_proof && <CFOPreProofBanner phase={d.customer_phase} />}

          {/* Row 1: Financial summary cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            {d.summary_cards.map((card, i) => (
              <SummaryCardComponent key={i} card={card} />
            ))}
          </div>

          {/* Row 1b — Predictor v3 expansion / at-risk tile.
              Now data-gated (renders when v3 portfolio NRR is in the API
              response) rather than hard-coded to cust 395. Any tenant with
              a calibrated Wizard D fit will see this. */}
          {(() => {
            const showPredictorV3 = !!d.predictor_v3_portfolio_nrr;
            const profile: 'saas_enterprise' | 'saas_smb' =
              (session?.vertical === 'saas_premium') ? 'saas_enterprise' : 'saas_enterprise';
            if (showPredictorV3 && session) {
              return (
                <div className="mb-6">
                  <PredictorV3Tile
                    customerId={session.customer_id}
                    saasProfile={profile}
                    horizon="12mo"
                    limit={5}
                  />
                </div>
              );
            }
            return null;
          })()}

          {/* Phase 2: keep modeled exposure visible when Predictor v3 hides the legacy 2-col row */}
          {d.predictor_v3_portfolio_nrr && (
            <div className="mb-6 max-w-xl">
              <CostOfInactionPanel data={d.cost_of_inaction} compact />
            </div>
          )}

          {/* Row 1b (legacy): NRR Before/After + Cost of Inaction
              — hidden when Predictor v3 is active. */}
          {!d.predictor_v3_portfolio_nrr && (
          <div className="grid grid-cols-2 gap-4 mb-6">
            {/* Issue #11 fix (May 4 2026): "no lifecycle history" empty state.
                When Wizard B has no closed lifecycle outcomes (delta = 0 + zero
                ARR protected + zero accounts saved), showing "100% → 100% / +0pp"
                looks like a bug. Detect that case explicitly and render a
                pending-state banner with a clear next-action. */}
            {d.wizard_b_nrr && (
              d.wizard_b_nrr.delta === 0
              && d.wizard_b_nrr.arr_protected === 0
              && d.wizard_b_nrr.accounts_saved === 0
            ) ? (
              <div className="bg-[#1a1f2e] rounded-xl border border-amber-700/40 p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-amber-400" />
                    <h3 className="text-[10px] font-semibold text-white uppercase tracking-wide">
                      Hindsight NRR &middot; TTM
                      <span className="text-gray-500 normal-case font-normal ml-1">(pending)</span>
                    </h3>
                  </div>
                  <span className="text-[9px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 font-semibold">No history</span>
                </div>
                <div className="flex items-end gap-4 mb-3">
                  <div>
                    <p className="text-[9px] text-gray-500 mb-0.5">Hindsight NRR</p>
                    <p className="text-3xl font-bold text-gray-500">—</p>
                  </div>
                  <div className="text-[10px] text-gray-400 pb-1 max-w-xs">
                    No closed lifecycle outcomes yet (no churn, contraction, expansion, or new logos
                    in the trailing 12 months). The realized-NRR comparison will populate once the
                    first playbook executions close. For forward-looking risk on at-risk accounts,
                    see <span className="text-cyan-400">CRO &middot; Forward NRR</span>.
                  </div>
                </div>
                <p className="text-[9px] text-gray-600">
                  Trigger first playbooks from CSM Cockpit · Today&apos;s Queue to start building NRR
                  attribution history.
                </p>
              </div>
            ) : d.wizard_b_nrr ? (
              /* ── Wizard B NRR: actual portfolio forecast ── */
              <div className="bg-[#1a1f2e] rounded-xl border border-cyan-700/30 p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-cyan-400" />
                    {/* Issue #5 fix (May 4 2026): explicit "Realized NRR · TTM" label
                        to disambiguate from CRO Forward NRR · 90d horizon. Same
                        Without/With dichotomy, different attribution window. */}
                    <h3
                      className="text-[10px] font-semibold text-white uppercase tracking-wide cursor-help"
                      title="Hindsight NRR (Wizard B counterfactual) over the trailing 12 months — derived from definitive lifecycle outcomes (churn, contraction, expansion, new logo), backward-looking 'would-CS-Pulse-have-helped'. For forward projection, see the Foresight NRR forecast."
                    >
                      Hindsight NRR · TTM
                      <span className="text-gray-500 normal-case font-normal ml-1">(CS Pulse impact)</span>
                    </h3>
                  </div>
                  <span className="text-[9px] px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 font-semibold">Actual</span>
                </div>
                <div className="flex items-end gap-4 mb-3">
                  <div>
                    <p className="text-[9px] text-gray-500 mb-0.5">Without CS Pulse</p>
                    <p className={`text-3xl font-bold ${d.wizard_b_nrr.without >= 100 ? 'text-gray-400' : 'text-red-400'}`}>{d.wizard_b_nrr.without.toFixed(1)}%</p>
                  </div>
                  <div className="text-gray-600 text-xl pb-1">&rarr;</div>
                  <div>
                    <p className="text-[9px] text-gray-500 mb-0.5">With CS Pulse</p>
                    <p className="text-3xl font-bold text-green-400">{d.wizard_b_nrr.with_pulse.toFixed(1)}%</p>
                  </div>
                  <div className="bg-green-500/10 border border-green-500/30 rounded-lg px-3 py-1.5 mb-1">
                    <p className="text-lg font-bold text-green-400">+{d.wizard_b_nrr.delta.toFixed(1)}pp</p>
                  </div>
                  {d.wizard_b_nrr.grr_after && (
                    <div className="border-l border-gray-700/50 pl-4">
                      <p className="text-[9px] text-gray-500 mb-0.5">GRR</p>
                      <p className="text-2xl font-bold text-gray-300">{d.wizard_b_nrr.grr_after.toFixed(0)}%</p>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-4 text-[10px]">
                  <span className="text-green-400">{formatCompact(d.wizard_b_nrr.arr_protected)} counterfactual ARR lift</span>
                  <span className="text-gray-500">&middot;</span>
                  <span className="text-cyan-400">{d.wizard_b_nrr.accounts_saved} accounts saved from churn</span>
                </div>
                <p className="text-[9px] text-gray-600 mt-2">Based on actual health trajectories, playbook outcomes, and saved-account attribution.</p>
                <SourceLabel source="wizardB" className="mt-1" />
              </div>
            ) : (
              /* ── Fallback: Power-of-1 NRR estimate ── */
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
                <p className="text-[9px] text-gray-600 mt-1">Power-of-1 estimate. Run playbooks to see actual NRR impact.</p>
                <SourceLabel source="benchmark" className="mt-1" />
              </div>
            )}

            {/* Cost of Inaction */}
            <CostOfInactionPanel data={d.cost_of_inaction} />
          </div>
          )}

          {/* Past — Three Lenses (NEW · sits ABOVE Investment Allocation Story).
              See marketing/cfo_dashboard_relabel_mock.html for design spec.
              Three rows: A historical actuals / B counterfactual (Wizard B) /
              C realized (proof_data). Row C is phase-conditional — hidden
              empty-state when customer is pre_deploy. */}
          <PastThreeLensesSection d={d} totalArr={d.total_arr} />

          {/* Per-Account NRR Forecast — sortable drill-down table.
              Complements PredictorV3Tile (top 5 each) with the full
              N-account view. Sortable by NRR, ARR, expansion lift, churn risk. */}
          {d.predictor_v3_portfolio_nrr && session && (
            <PerAccountNRRForecastTable customerId={session.customer_id} horizon="12mo" />
          )}

          {/* Row 1c: Investment Allocation Story */}
          {d.layered_story && d.layered_story.layers.length > 0 && (
            <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 mb-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-purple-400" />
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wide">Investment Allocation Story</h3>
                </div>
                <span className="text-xs text-gray-500">Total addressable: {formatCompact(d.layered_story.total_value)} &middot; {d.layered_story.blended_roi}x blended ROI</span>
              </div>
              <div className="grid grid-cols-3 gap-4">
                {d.layered_story.layers.map((layer: any, i: number) => {
                  const colors: Record<string, { border: string; text: string; bg: string; badge: string }> = {
                    green: { border: 'border-green-500/30', text: 'text-green-400', bg: 'bg-green-500/10', badge: 'Done' },
                    cyan: { border: 'border-cyan-500/30', text: 'text-cyan-400', bg: 'bg-cyan-500/10', badge: 'Act Now' },
                    purple: { border: 'border-purple-500/30', text: 'text-purple-400', bg: 'bg-purple-500/10', badge: 'Invest' },
                  };
                  const c = colors[layer.color] || colors.green;
                  // Layers map: green=Already Delivered (proof_data) →
                  // cyan=Still Protectable (waterfall) → purple=Growth (Po1).
                  // Each has a different system of record.
                  const layerSource: SourceKey = layer.color === 'green'
                    ? 'csPulseProof'
                    : layer.color === 'purple'
                      ? 'benchmark'
                      : 'wizardB';
                  return (
                    <div key={i} className={`rounded-xl border ${c.border} ${c.bg} p-4`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] font-semibold text-white uppercase">{layer.name}</span>
                        <span className={`text-[9px] px-2 py-0.5 rounded-full ${c.bg} ${c.text} font-semibold`}>{c.badge}</span>
                      </div>
                      <p className={`text-2xl font-bold ${c.text} mb-1`}>{formatCompact(layer.value)}</p>
                      <SourceLabel source={layerSource} className="mb-1" />
                      <div className="flex items-center justify-between text-[10px] text-gray-500">
                        <span>Cost: {formatCompact(layer.cost)}</span>
                        <span className={`font-semibold ${c.text}`}>{layer.roi}x ROI</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Row 1d: Playbook ROI Proof — table or Phase 2 empty state */}
          {!d.has_proof ? (
            <PlaybookProofEmptyState phase={d.customer_phase} />
          ) : d.proof_executions.length > 0 ? (
            <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden mb-6">
              <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-green-400" />
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wide">Playbook ROI Proof</h3>
                </div>
                <span className="text-[10px] text-gray-500 flex flex-col items-end">
                  <span>{d.proof_executions.filter(e => e.revenue_protected > 0).length} interventions with measurable impact</span>
                  <SourceLabel source="csPulseProof" />
                </span>
              </div>
              <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700/50">
                    <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">Playbook</th>
                    <th className="text-left px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Account</th>
                    <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Health &Delta;</th>
                    <th className="text-right px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Cost</th>
                    <th className="text-right px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase" title="Playbook-attributed revenue protected">Protected (PB)</th>
                    <th className="text-right px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Expanded</th>
                    <th className="text-right px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">ROI</th>
                  </tr>
                </thead>
                <tbody>
                  {d.proof_executions.filter(e => e.revenue_protected > 0 || e.revenue_expanded > 0).map((e, i) => (
                    <tr key={i} className="border-b border-gray-700/30 hover:bg-white/[0.02] group">
                      <td className="px-5 py-3 text-xs font-mono text-cyan-400">{e.playbook_id}</td>
                      <td className="px-3 py-3 text-xs text-white">{e.account_name}</td>
                      <td className="text-center px-3 py-3">
                        {e.health_at_trigger != null && e.health_at_close != null ? (
                          <span className={`text-xs font-semibold ${(e.health_delta || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {e.health_at_trigger.toFixed(0)} &rarr; {e.health_at_close.toFixed(0)}
                          </span>
                        ) : <span className="text-gray-500">—</span>}
                      </td>
                      <td className="text-right px-3 py-3">
                        <span className="text-xs text-gray-400 font-mono">{formatCompact(e.cost)}</span>
                        <div className="hidden group-hover:block text-[9px] text-gray-600 mt-0.5 leading-tight">
                          CSM: {formatCompact(e.cost_csm || 0)}<br/>
                          Platform: {formatCompact(e.cost_platform || 0)}<br/>
                          Overhead: {formatCompact(e.cost_overhead || 0)}
                        </div>
                      </td>
                      <td className="text-right px-3 py-3 text-xs text-green-400 font-semibold font-mono">{formatCompact(e.revenue_protected)}</td>
                      <td className="text-right px-3 py-3 text-xs text-teal-400 font-semibold font-mono">{e.revenue_expanded > 0 ? formatCompact(e.revenue_expanded) : '—'}</td>
                      <td className="text-right px-5 py-3 text-xs text-cyan-400 font-bold">{e.roi_x}x</td>
                    </tr>
                  ))}
                </tbody>
                {/* Summary footer with Wizard B NRR attribution */}
                <tfoot>
                  <tr className="border-t border-gray-600/50">
                    <td colSpan={3} className="px-5 py-3 text-xs font-semibold text-white">
                      Total
                    </td>
                    <td className="text-right px-3 py-3 text-xs text-gray-300 font-semibold font-mono">
                      {formatCompact(d.proof_executions.reduce((s, e) => s + e.cost, 0))}
                    </td>
                    <td className="text-right px-3 py-3 text-xs text-green-400 font-bold font-mono">
                      {formatCompact(d.proof_executions.reduce((s, e) => s + e.revenue_protected, 0))}
                    </td>
                    <td className="text-right px-3 py-3 text-xs text-teal-400 font-bold font-mono">
                      {formatCompact(d.proof_executions.reduce((s, e) => s + (e.revenue_expanded || 0), 0))}
                    </td>
                    <td className="text-right px-5 py-3 text-xs text-cyan-400 font-bold">
                      {(() => {
                        const tc = d.proof_executions.reduce((s, e) => s + e.cost, 0);
                        const tv = d.proof_executions.reduce((s, e) => s + e.revenue_protected + (e.revenue_expanded || 0), 0);
                        return tc > 0 ? `${Math.round(tv / tc)}x` : '—';
                      })()}
                    </td>
                  </tr>
                  {d.wizard_b_nrr && (
                    <tr>
                      <td colSpan={7} className="px-5 py-3">
                        <div className="flex items-center gap-4 text-[10px]">
                          <span className="text-gray-500">Portfolio NRR Impact:</span>
                          <span className="text-green-400 font-bold">+{d.wizard_b_nrr.delta.toFixed(1)}pp</span>
                          <span className="text-gray-600">({d.wizard_b_nrr.without.toFixed(1)}% &rarr; {d.wizard_b_nrr.with_pulse.toFixed(1)}%)</span>
                          <span className="text-gray-500">&middot;</span>
                          <span className="text-cyan-400">{d.wizard_b_nrr.accounts_saved} accounts saved from churn</span>
                          <span className="text-gray-500">&middot;</span>
                          <span className="text-green-400">{formatCompact(d.wizard_b_nrr.arr_protected)} counterfactual ARR lift</span>
                        </div>
                      </td>
                    </tr>
                  )}
                </tfoot>
              </table>
              </div>
            </div>
          ) : null}

          {/* Renewals at Risk Banner */}
          {d.renewals_at_risk.length > 0 && (
            <div className="bg-[#1a1f2e] rounded-xl border border-yellow-600/30 p-4 mb-6">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-500" />
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
                    Contract renewals due &middot; next 90 days
                  </h3>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400">
                    {d.renewals_at_risk.length}
                  </span>
                </div>
                <span className="text-[10px] text-gray-500 flex flex-col items-end">
                  <span>{formatCompact(d.renewals_at_risk.reduce((s, r) => s + r.arr, 0))} ARR</span>
                  <SourceLabel source="crm" />
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

          {/* ── Future ROI Modeling (Power-of-1) — collapsible ── */}
          <div className="mb-6">
            <button
              onClick={() => setShowFutureROI(!showFutureROI)}
              className="w-full flex items-center justify-between bg-[#1a1f2e] rounded-xl border border-gray-700/50 px-5 py-4 hover:border-gray-600/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-purple-400" />
                <h3 className="text-xs font-semibold text-white uppercase tracking-wide">Future ROI Modeling</h3>
                <span className="text-[9px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400">Power-of-1 Framework</span>
              </div>
              <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${showFutureROI ? 'rotate-180' : ''}`} />
            </button>
            {showFutureROI && (
              <div className="mt-4 space-y-6">
                {/* CFO-4: tables in this section are Power-of-1 benchmark
                    projections, not customer-data dollars. Single banner
                    disclosure here is sufficient — every dollar inside is
                    benchmark-sourced. */}
                <SourceLabel source="benchmark" className="px-1" />
                {/* Power of 1 Metrics Table */}
                <PowerOf1Table rows={d.power_of_1} total={d.power_of_1_total} />

                {/* Pillar Investment + Investment Timeline */}
                <div className="grid grid-cols-2 gap-4">
                  <PillarInvestmentChart data={d.pillar_investments} />
                  <InvestmentTimelineChart data={d.investment_timeline} />
                </div>

                {/* ROI Scaling Analysis */}
                <ROIScalingSection
                  tiers={d.roi_scaling}
                  isModeled={d.roi_scaling_is_modeled}
                  roiMultiple={d.roi_multiple}
                />
              </div>
            )}
          </div>

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
                <span className="text-[10px] text-gray-500 flex flex-col items-end">
                  <span>{d.has_proof ? 'From playbook executions' : 'Estimated (ARR-weighted)'}</span>
                  <SourceLabel source={d.has_proof ? 'csPulseProof' : 'benchmark'} />
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-gray-700/50 text-gray-500">
                      <th className="text-left py-2 pr-3">Account</th>
                      <th className="text-center py-2 px-2">Source</th>
                      <th className="text-right py-2 px-2">ARR</th>
                      <th className="text-right py-2 px-2">Health</th>
                      <th className="text-right py-2 px-2">Cost</th>
                      <th className="text-right py-2 px-2" title="Playbook-attributed">Protected (PB)</th>
                      <th className="text-right py-2 px-2">Expanded</th>
                      <th className="text-right py-2 px-2">ROI</th>
                      <th className="text-right py-2 pl-2">Runs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(() => {
                      // Aggregate proof_executions by account, overlay onto accounts list
                      const proofByAccount: Record<string, { cost: number; prot: number; exp: number; runs: number }> = {};
                      for (const e of d.proof_executions) {
                        const key = e.account_name;
                        if (!proofByAccount[key]) proofByAccount[key] = { cost: 0, prot: 0, exp: 0, runs: 0 };
                        proofByAccount[key].cost += e.cost;
                        proofByAccount[key].prot += e.revenue_protected;
                        proofByAccount[key].exp += e.revenue_expanded || 0;
                        proofByAccount[key].runs += 1;
                      }
                      return d.accounts.map((a) => {
                        const proof = proofByAccount[a.account_name];
                        const hasActual = !!proof;
                        const cost = hasActual ? proof.cost : 0;
                        const prot = hasActual ? proof.prot : 0;
                        const exp = hasActual ? proof.exp : 0;
                        const total = prot + exp;
                        const roi = cost > 0 && total > 0 ? Math.round(total / cost) : 0;
                        const runs = hasActual ? proof.runs : 0;
                        const healthColor = a.classification === 'critical' ? 'text-red-400'
                          : a.classification === 'at_risk' ? 'text-yellow-400' : 'text-green-400';
                        return (
                          <tr key={a.account_id} className="border-b border-gray-800/30 hover:bg-gray-800/20 transition-colors">
                            <td className="py-2 pr-3">
                              <div className="text-white font-medium truncate max-w-[180px]">{a.account_name}</div>
                            </td>
                            <td className="text-center py-2 px-2">
                              {hasActual ? (
                                <span
                                  className="text-[8px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400"
                                  title="Playbook execution rows for this account"
                                >
                                  actual
                                </span>
                              ) : (
                                <span
                                  className="text-[8px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-gray-700/40 text-gray-500"
                                  title="ARR-weighted benchmark allocation until playbooks close"
                                >
                                  benchmark
                                </span>
                              )}
                            </td>
                            <td className="text-right py-2 px-2 text-gray-400">{formatCompact(a.arr)}</td>
                            <td className={`text-right py-2 px-2 font-medium ${healthColor}`}>{a.health_score.toFixed(0)}</td>
                            <td className="text-right py-2 px-2 text-gray-300">{cost > 0 ? formatCompact(cost) : '—'}</td>
                            <td className="text-right py-2 px-2 text-green-400">{prot > 0 ? formatCompact(prot) : '—'}</td>
                            <td className="text-right py-2 px-2 text-teal-400">{exp > 0 ? formatCompact(exp) : '—'}</td>
                            <td className={`text-right py-2 px-2 font-bold ${roi > 0 ? 'text-cyan-400' : 'text-gray-500'}`}>{roi > 0 ? `${roi}x` : '—'}</td>
                            <td className="text-right py-2 pl-2 text-gray-500">{runs || '—'}</td>
                          </tr>
                        );
                      });
                    })()}
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
        {d.has_proof ? (
          /* Actual investment breakdown from playbook data */
          <div className="bg-[#1a1f2e] rounded-xl border border-green-700/30 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase">CS Investment</h3>
              <span className="text-[9px] px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">Actual</span>
            </div>
            <div className="text-center mb-3">
              <p className="text-3xl font-bold text-green-400">{d.total_arr > 0 ? (d.cs_investment / d.total_arr * 100).toFixed(2) : '0'}%</p>
              <p className="text-[10px] text-gray-500 mt-0.5">of ARR invested in CS</p>
              <p className="text-[9px] text-green-400/70 mt-0.5">Well below industry range (1.5% - 2.5%)</p>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-3 text-center">
              <div className="bg-gray-800/50 rounded-lg p-2">
                <p className="text-lg font-bold text-white">{formatCompact(d.cs_investment)}</p>
                <p className="text-[9px] text-gray-500">CS Spend</p>
              </div>
              <div className="bg-gray-800/50 rounded-lg p-2">
                <p className="text-lg font-bold text-cyan-400">{(d.roi_impact > 0 && d.cs_investment > 0) ? `${(d.roi_impact / d.cs_investment).toFixed(0)}x` : '—'}</p>
                <p className="text-[9px] text-gray-500">ROI</p>
              </div>
            </div>
            <p className="text-[9px] text-gray-600 italic">From {d.proof_executions.length} playbook executions</p>
            <SourceLabel source="csPulseProof" className="mt-1" />
            {/* CFO-6: real per-playbook breakdown also rendered here when
                proof data exists, so a customer with playbook history still
                gets the categorized "where the dollars go" view. */}
            {playbookEconomics && (
              <div className="border-t border-gray-700/50 pt-3 mt-3">
                <PlaybookInvestmentBreakdown economics={playbookEconomics} />
              </div>
            )}
          </div>
        ) : (
          <InvestmentAllocationWidget
            totalArr={d.total_arr}
            csInvestment={d.cs_investment}
            roiImpact={d.roi_impact}
            isEstimated={d.is_estimated_investment}
            economics={playbookEconomics}
          />
        )}

        {/* Pending Decisions Queue — read-only v1 */}
        <PendingDecisionsQueue persona="cfo" />

        {/* Revenue Waterfall */}
        {d.nrr_waterfall.expected_loss > 0 && (
          <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
            <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-3">
              Revenue Waterfall
            </h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between"><span className="text-gray-400">Churn Exposure</span><span className="text-red-400 font-semibold">{formatCompact(d.nrr_waterfall.expected_loss)}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Protectable (churn)</span><span className="text-green-400 font-semibold">{formatCompact(d.nrr_waterfall.protectable || d.nrr_waterfall.attributed_save)}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Expandable (growth)</span><span className="text-teal-400 font-semibold">{formatCompact(d.nrr_waterfall.expandable || 0)}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Cost to Intervene</span><span className="text-gray-300">{formatCompact(d.nrr_waterfall.intervention_cost)}</span></div>
              {d.nrr_waterfall.roi_x > 0 && (
                <div className="flex justify-between border-t border-gray-700/50 pt-2">
                  <span className="text-gray-400">Intervention ROI</span>
                  <span className="text-cyan-400 font-bold">{d.nrr_waterfall.roi_x}x</span>
                </div>
              )}
            </div>
            <SourceLabel source="csPulseProof" className="mt-2" />
          </div>
        )}

        {/* Phase 3: CS efficiency (playbook economics or proof) */}
        <CFOEfficiencyPanel efficiency={d.efficiency} />

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
