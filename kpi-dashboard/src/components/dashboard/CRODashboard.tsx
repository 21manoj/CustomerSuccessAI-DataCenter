/**
 * CRO Revenue Intelligence Dashboard
 * ====================================
 *
 * Dark-themed executive dashboard for Chief Revenue Officers featuring:
 * - Revenue at Risk / Protected / Expansion pipeline cards
 * - Health score metrics with trend indicators
 * - Context Graph Story Arcs
 * - Highest Risk Accounts grid
 * - Power of 1 ROI Engine widget
 * - Revenue Timeline for selected accounts
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell
} from 'recharts';
import {
  AlertTriangle, TrendingUp, TrendingDown, Shield, Zap,
  Target, DollarSign, Users, BarChart3, Clock,
  ChevronRight, ChevronDown, Eye, Activity, GitBranch, Sparkles,
  ArrowRight, Briefcase, Info
} from 'lucide-react';
import { classify, classifyColor, thresholdValues } from '../../utils/healthThresholds';
import DashboardTopBar from './DashboardTopBar';
import { useSession } from '../../contexts/SessionContext';
import { apiCall, getCustomerIdentifier } from '../../utils/api';
import AskAIPortal from '../ai/AskAIPortal';
import { trackPageView, trackEvent } from '../../utils/activityTracker';
import { PredictorV3Tile } from '../predictor/PredictorV3Tile';
import { DashboardErrorState } from '../shared/DashboardErrorState';
import {
  type CroPeriod,
  type QuarterBucket,
  getCalendarQuarter,
  monthInPeriod,
  periodDisplayLabel,
  periodToAnchorBucket,
  previousQuarter,
} from '../../utils/croPeriod';
import {
  CROMetricGuideBanner,
  CROPreProofBanner,
  CROContextGraphStrip,
  type CROContextGraphRevenue,
  type CROProofData,
  type CustomerPhase,
} from './CROOverviewHonesty';
import PendingDecisionsQueue from './PendingDecisionsQueue';

// Lazy-load sub-views
const SignalTimelineView = React.lazy(() => import('./views/SignalTimelineView'));
const ContextGraphView = React.lazy(() => import('./views/ContextGraphView'));
const ROIEngineView = React.lazy(() => import('./views/ROIEngineView'));
const AccountsView = React.lazy(() => import('./views/AccountsView'));

type ViewId = 'cro-overview' | 'signal-timeline' | 'context-graph' | 'journey-intelligence' | 'roi-engine' | 'accounts' | 'playbooks' | 'approvals';

// ============================================================================
// TYPES
// ============================================================================

interface RevenueCard {
  label: string;
  amount: number;
  subtitle: string;
  account_count?: number;
  accent: string;
  badge?: string;
  footnote?: string;
}

interface MetricCard {
  label: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'flat';
  accent?: string;
  tooltip?: string;
}

interface StoryArc {
  id: string;
  name: string;
  icon: string;
  description: string;
  account_count: number;
  revenue_impact: number;
  impact_type: 'risk' | 'opportunity' | 'recovery' | 'threat' | 'growth';
}

interface RiskAccount {
  account_id: string | number;
  account_name: string;
  health_score: number;
  arr: number;
  classification: 'critical' | 'at_risk' | 'healthy';
  signal_count: number;
  pillar_scores?: Record<string, number>;
  // CRO-5: CSM owner surfaced on at-risk table — backed by Account.assigned_csm
  // via the CRO dashboard endpoint. May be null if account is unassigned.
  assigned_csm?: string | null;
}

interface ROIScalingPoint {
  accounts: number;
  label: string;
  roi: number;
}

interface TimelineEvent {
  month: string;
  date: string;
  type: 'signal' | 'intervention' | 'outcome';
  color: string;
  title: string;
  description: string;
}

interface RevenueTimeline {
  account_name: string;
  arr: number;
  events: TimelineEvent[];
}

interface NRRTrajectoryPoint {
  nrr_pct: number;
  crossings: Array<{ account_name: string; crossing: string }>;
}

interface NRRWaterfallAccount {
  account_name: string;
  arr: number;
  health_now: number;
  churn_prob_pct: number;
  expected_loss: number;
  attributed_save: number;
}

// CRO-6: shape of a single health-threshold transition from
// /api/v1/health-score-history. We filter client-side for healthy→at_risk
// (or healthy→critical) flips and render the most recent in a banner.
interface HealthTransition {
  account_id: number;
  account_name: string;
  month: string;       // 'YYYY-MM'
  from_status: 'healthy' | 'at_risk' | 'critical';
  to_status: 'healthy' | 'at_risk' | 'critical';
  score: number;
  arr: number;
}

// CRO-7: per-account monthly history needed for QoQ / YoY at-risk ARR
// comparison. We sum at-risk ARR per quarter from monthly_scores rather
// than building a new aggregation endpoint — single source of truth.
interface MonthlyScore {
  month: string;        // 'YYYY-MM'
  health_score: number;
  status: 'healthy' | 'at_risk' | 'critical';
  change?: number;
  pillars?: Record<string, number>;
}

interface AccountHistory {
  account_id: number;
  account_name: string;
  arr: number;
  current_health: number;
  starting_health: number;
  net_change: number;
  trajectory: 'improving' | 'declining' | 'stable';
  monthly_scores: MonthlyScore[];
}

interface CRODashboardData {
  revenue_cards: RevenueCard[];
  metrics: MetricCard[];
  story_arcs: StoryArc[];
  risk_accounts: RiskAccount[];
  roi_summary: {
    roi_pct: number;
    invested: number;
    impact: number;
    scaling: ROIScalingPoint[];
  };
  // Dual NRR
  nrr_current: number;
  nrr_with_intervention: number;
  nrr_arr_protected: number;
  nrr_trajectory: Record<string, NRRTrajectoryPoint>;
  nrr_waterfall: {
    total_exposure: number;
    expected_loss: number;
    gross_saved: number;
    attributed_save: number;
    intervention_cost: number;
    roi_x: number;
    accounts: NRRWaterfallAccount[];
  };
  renewals_at_risk: Array<{ account_name: string; arr: number; days_until: number; health_score: number }>;
  period: string;
  last_updated: string;
  arr_exposure: number;
  arr_exposure_label: string;
  revenue_risk_label: string;
  context_graph_revenue: CROContextGraphRevenue | null;
  proof_data: CROProofData;
  customer_phase: CustomerPhase;
  playbook_roi_estimated: boolean;
  wizard_b_nrr: {
    with_cs_pulse_nrr_pct?: number;
    without_cs_pulse_nrr_pct?: number;
    delta_pct?: number;
  } | null;
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

function formatCompactNoSign(value: number): string {
  return formatCompact(value).replace('$', '');
}

const ACCENT_MAP: Record<string, string> = {
  red: '#ef4444',
  green: '#22c55e',
  cyan: '#06b6d4',
  yellow: '#eab308',
  purple: '#a855f7',
  orange: '#f97316',
};

const IMPACT_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  risk: { bg: 'bg-red-500/20', text: 'text-red-400', label: 'At Risk' },
  opportunity: { bg: 'bg-cyan-500/20', text: 'text-cyan-400', label: 'Opportunity' },
  recovery: { bg: 'bg-green-500/20', text: 'text-green-400', label: 'Recovery' },
  threat: { bg: 'bg-orange-500/20', text: 'text-orange-400', label: 'Threat' },
  growth: { bg: 'bg-purple-500/20', text: 'text-purple-400', label: 'Growth' },
};

const STORY_ARC_ICONS: Record<string, React.ReactNode> = {
  silent_churn: <AlertTriangle className="w-5 h-5 text-red-400" />,
  expansion_champion: <TrendingUp className="w-5 h-5 text-cyan-400" />,
  crisis_recovery: <Shield className="w-5 h-5 text-green-400" />,
  competitive_displacement: <Target className="w-5 h-5 text-orange-400" />,
  land_and_expand: <Sparkles className="w-5 h-5 text-purple-400" />,
  stakeholder_exodus: <Users className="w-5 h-5 text-yellow-400" />,
  adoption_stall: <Activity className="w-5 h-5 text-yellow-400" />,
  renewal_momentum: <Zap className="w-5 h-5 text-green-400" />,
};

// Sidebar navigation items — views are rendered in-place, not by route
const NAV_ITEMS = {
  intelligence: [
    { id: 'cro-overview' as ViewId, label: 'CRO Overview', badge: null, icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'signal-timeline' as ViewId, label: 'Signal Timeline', badge: null, icon: <Activity className="w-4 h-4" /> },
    { id: 'context-graph' as ViewId, label: 'Context Graph', badge: null, icon: <GitBranch className="w-4 h-4" /> },
    // Issue #8 fix (May 4 2026): surface the Journey Intelligence dashboard
    // (3-line health graph + Signal-DNA composite + toggle layers for arcs,
    // forecast, outcomes, decisions) in the CRO sidebar at the same level
    // as Context Graph. Component lives at /dc-dashboard/journey-intelligence;
    // we link out via <a> rather than handleViewChange because the view has
    // its own page chrome.
    { id: 'journey-intelligence' as ViewId, label: 'Journey Intelligence', badge: null, icon: <TrendingUp className="w-4 h-4" />, href: '/dc-dashboard/journey-intelligence' },
    // ROI Engine hidden — redundant with CFO Power-of-1 and sidebar widget
  ],
  operations: [
    { id: 'accounts' as ViewId, label: 'Accounts', badge: null, icon: <Users className="w-4 h-4" /> },
    // Playbooks + Approvals hidden until Sprint 1-2 ships execution UI
  ],
};

// No fallback data — dashboard requires live API connection

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
const SidebarNav: React.FC<{ activeId: ViewId; onViewChange: (view: ViewId) => void; onNavigate: (path: string) => void; accountCount?: number; signalCount?: number; roiPct?: number }> = ({ activeId, onViewChange, onNavigate, accountCount, signalCount, roiPct }) => {
  // Dynamic badges from real data
  const getBadge = (id: string): string | null => {
    if (id === 'accounts' && accountCount) return String(accountCount);
    if (id === 'signal-timeline' && signalCount) return String(signalCount);
    if (id === 'roi-engine' && roiPct) return `${roiPct}%`;
    return null;
  };

  return (
    <aside className="w-48 flex-shrink-0 bg-[#0d1117] border-r border-gray-700/50 py-6 px-3 flex flex-col gap-6 overflow-y-auto">
      {/* Intelligence section */}
      <div>
        <h3 className="text-[10px] font-semibold tracking-[0.2em] text-gray-500 uppercase mb-3 px-2">Intelligence</h3>
        <nav className="flex flex-col gap-0.5">
          {NAV_ITEMS.intelligence.map((item) => {
            const isActive = item.id === activeId;
            const badge = getBadge(item.id);
            const hasHref = 'href' in item && (item as any).href;
            const className = `flex items-center gap-2 px-2 py-2 rounded-lg text-sm transition-all group w-full text-left ${
              isActive
                ? 'bg-cyan-500/10 text-cyan-400'
                : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`;
            const inner = (
              <>
                <span className={isActive ? 'text-cyan-400' : 'text-gray-500 group-hover:text-gray-300'}>
                  {item.icon}
                </span>
                <span className="flex-1 truncate">{item.label}</span>
                {badge && (
                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                    isActive ? 'bg-cyan-500/20 text-cyan-400' : 'bg-gray-700/50 text-gray-400'
                  }`}>
                    {badge}
                  </span>
                )}
              </>
            );
            // Items with `href` link out to a dedicated route; others trigger
            // the in-place view change. Same visual treatment for both.
            // Derive the dashboard-family prefix from current path so SaaS
            // tenants land on /saas-dashboard/* and DC tenants on /dc-dashboard/*.
            const prefix = typeof window !== 'undefined' && window.location.pathname.startsWith('/saas-dashboard')
              ? '/saas-dashboard'
              : '/dc-dashboard';
            const resolvedHref = hasHref
              ? (item as any).href.replace(/^\/dc-dashboard/, prefix)
              : null;
            return hasHref ? (
              <a key={item.id} href={resolvedHref} className={className}>
                {inner}
              </a>
            ) : (
              <button key={item.id} onClick={() => onViewChange(item.id)} className={className}>
                {inner}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Operations section */}
      <div>
        <h3 className="text-[10px] font-semibold tracking-[0.2em] text-gray-500 uppercase mb-3 px-2">Operations</h3>
        <nav className="flex flex-col gap-0.5">
          {NAV_ITEMS.operations.map((item) => {
            const isActive = item.id === activeId;
            const badge = getBadge(item.id);
            return (
              <button
                key={item.id}
                onClick={() => onViewChange(item.id)}
                className={`flex items-center gap-2 px-2 py-2 rounded-lg text-sm transition-all group w-full text-left ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-400'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <span className={isActive ? 'text-cyan-400' : 'text-gray-500 group-hover:text-gray-300'}>
                  {item.icon}
                </span>
                <span className="flex-1 truncate">{item.label}</span>
                {badge && (
                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                    isActive ? 'bg-cyan-500/20 text-cyan-400' : 'bg-gray-700/50 text-gray-400'
                  }`}>
                    {badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Separator */}
      <div className="px-2 pt-2">
        <div className="h-px bg-gray-700/30 mb-3" />
        <button
          onClick={() => onNavigate('/cfo-dashboard')}
          className="flex items-center gap-2 px-2 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-all group w-full text-left"
        >
          <Briefcase className="w-4 h-4 text-gray-500 group-hover:text-gray-300" />
          <span className="flex-1 truncate">CFO View</span>
          <ArrowRight className="w-3 h-3 text-gray-600" />
        </button>
      </div>

      {/* Branding */}
      <div className="mt-auto px-2 pt-4 border-t border-gray-700/30">
        <div className="text-[10px] text-gray-600 leading-relaxed">
          CS Pulse<br />
          Revenue Intelligence
        </div>
      </div>
    </aside>
  );
};

/** Large revenue card with expandable drill-down */
const RevenueCardComponent: React.FC<{ card: RevenueCard; riskAccounts?: RiskAccount[] }> = ({ card, riskAccounts }) => {
  const [expanded, setExpanded] = React.useState(false);
  const accent = ACCENT_MAP[card.accent] || '#06b6d4';
  const isRiskCard = card.accent === 'red' && riskAccounts && riskAccounts.length > 0;

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 relative overflow-hidden group hover:border-gray-600/50 transition-all">
      {/* Accent bar */}
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ backgroundColor: accent }} />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-16 opacity-10 blur-2xl" style={{ backgroundColor: accent }} />
      <div className="relative p-5">
        <div className="flex items-center gap-2 mb-1">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">{card.label}</p>
          {card.badge && (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-gray-700/80 text-gray-300 font-medium">
              {card.badge}
            </span>
          )}
        </div>
        <p className="text-3xl font-bold text-white mb-1" style={{ color: accent }}>{formatCompact(card.amount)}</p>
        <p className="text-xs text-gray-500 mb-1">{card.subtitle}</p>
        {card.footnote && (
          <p className="text-[10px] text-gray-600 mb-2">{card.footnote}</p>
        )}
        {card.account_count != null && card.account_count > 0 && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1 text-xs text-gray-400">
              <Users className="w-3 h-3" />
              <span>{card.account_count} accounts</span>
            </div>
            {isRiskCard && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="text-[10px] text-teal-500 hover:text-teal-400 flex items-center gap-0.5"
              >
                <ChevronDown className={`w-3 h-3 transition-transform ${expanded ? 'rotate-180' : ''}`} />
                {expanded ? 'Hide' : 'Show'} details
              </button>
            )}
          </div>
        )}
      </div>
      {/* Expandable account drill-down */}
      {expanded && isRiskCard && (
        <div className="px-5 pb-4 border-t border-gray-700/30 pt-3 space-y-2">
          {riskAccounts!.slice(0, 5).map((a) => {
            const cls = classify(a.health_score);
            return (
              <div key={a.account_id} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${cls === 'critical' ? 'bg-red-400' : 'bg-yellow-400'}`} />
                  <span className="text-gray-300 truncate">{a.account_name}</span>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0 ml-2">
                  <span className="text-gray-500">{formatCompact(a.arr)}</span>
                  <span className={`font-semibold ${cls === 'critical' ? 'text-red-400' : 'text-yellow-400'}`}>{a.health_score}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

/** Small metric card */
const MetricCardComponent: React.FC<{ metric: MetricCard }> = ({ metric }) => {
  const isUp = metric.trend === 'up';
  const TrendIcon = isUp ? TrendingUp : TrendingDown;
  const trendColor = isUp ? 'text-green-400' : 'text-red-400';
  const accent = metric.accent ? ACCENT_MAP[metric.accent] : undefined;
  const [showTip, setShowTip] = React.useState(false);

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4 hover:border-gray-600/50 transition-all relative">
      <div className="flex items-center gap-1.5 mb-2">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">{metric.label}</p>
        {metric.tooltip && (
          <button
            className="text-gray-600 hover:text-gray-400 transition-colors"
            onMouseEnter={() => setShowTip(true)}
            onMouseLeave={() => setShowTip(false)}
            onClick={() => setShowTip(!showTip)}
          >
            <Info className="w-3 h-3" />
          </button>
        )}
      </div>
      {showTip && metric.tooltip && (
        <div className="absolute z-50 top-full left-0 mt-1 w-72 p-3 bg-gray-900 border border-gray-600 rounded-lg shadow-xl text-xs text-gray-300 leading-relaxed">
          <div className="flex items-start gap-2">
            <Info className="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold text-amber-400 mb-1">Methodology</p>
              <p>{metric.tooltip}</p>
            </div>
          </div>
        </div>
      )}
      <p className="text-2xl font-bold mb-1" style={{ color: accent || '#ffffff' }}>
        {metric.value}
      </p>
      <div className={`flex items-center gap-1 text-xs ${trendColor}`}>
        <TrendIcon className="w-3 h-3" />
        <span>{metric.change}</span>
      </div>
    </div>
  );
};

/** Story arc row */
const StoryArcRow: React.FC<{ arc: StoryArc; onClick: () => void }> = ({ arc, onClick }) => {
  const impact = IMPACT_COLORS[arc.impact_type] || IMPACT_COLORS.risk;
  const icon = STORY_ARC_ICONS[arc.icon] || <GitBranch className="w-5 h-5 text-gray-400" />;

  return (
    <button
      onClick={onClick}
      className="flex items-center gap-3 px-4 py-3 bg-[#1a1f2e] rounded-lg border border-gray-700/50 hover:border-gray-600/50 transition-all w-full text-left group"
    >
      <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-gray-800/80 flex items-center justify-center">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white truncate">{arc.name}</p>
        <p className="text-xs text-gray-500 truncate">{arc.description}</p>
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        <span className="text-xs text-gray-500">{arc.account_count} accts</span>
        <span className="text-sm font-semibold text-white">{formatCompact(arc.revenue_impact)}</span>
        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${impact.bg} ${impact.text}`}>
          {impact.label}
        </span>
        <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-gray-400 transition-colors" />
      </div>
    </button>
  );
};

/** NRR per-account attribution — expandable below waterfall.
 *  Issue #2 + #7 fix (May 4 2026): clarify what each column means.
 *    ARR        = account ARR (real)
 *    Churn %    = churn probability under current health (max(5, 50 - health × 0.5))
 *    +90d Save  = (expected_loss − projected_loss) × 0.5 attribution. Forward-only,
 *                 trend-continuation, attributed at 50% per industry default.
 *  Distinct from Wizard B's backward-looking dip-recovery `attributed_save` — same
 *  underlying data, different counterfactual window. */
const NRRAccountAttribution: React.FC<{ accounts: NRRWaterfallAccount[] }> = ({ accounts }) => {
  const [expanded, setExpanded] = React.useState(false);
  const sorted = [...accounts].sort((a, b) => a.expected_loss - b.expected_loss); // worst first (most negative)
  return (
    <div className="px-4 pb-3 border-t border-gray-700/30">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between py-2"
      >
        <span className="text-[10px] text-gray-500 uppercase tracking-wide">Per-Account NRR Impact</span>
        <ChevronDown className={`w-3 h-3 text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>
      {expanded && (
        <div className="space-y-1">
          {/* Column header row — explicit labels (issue #2) */}
          <div className="flex items-center justify-between text-[9px] uppercase tracking-wide text-gray-500 pb-1 border-b border-gray-800/60">
            <span className="flex-1">Account</span>
            <div className="flex items-center gap-3 flex-shrink-0 ml-2">
              <span className="w-14 text-right">ARR</span>
              <span className="w-10 text-right" title="Annual churn probability projected from health score (max(5, 50 − health × 0.5))">Churn %</span>
              <span className="w-16 text-right" title="90d projected save, attributed at 50% — (expected_loss − projected_loss) × 0.5. Forward-only, distinct from CFO realized save.">+90d Save (att)</span>
            </div>
          </div>
          {sorted.map((a, i) => {
            const isDetractor = a.expected_loss < 0;
            const isSaver = a.attributed_save > 0;
            return (
              <div key={i} className="flex items-center justify-between text-xs py-0.5">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${isDetractor ? 'bg-red-400' : isSaver ? 'bg-green-400' : 'bg-gray-500'}`} />
                  <span className="text-gray-300 truncate">{a.account_name}</span>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0 ml-2">
                  <span className="text-gray-500 w-14 text-right">{formatCompact(a.arr)}</span>
                  <span className="text-gray-500 w-10 text-right">{a.churn_prob_pct}%</span>
                  {isDetractor && <span className="text-red-400 font-semibold w-16 text-right">{formatCompact(a.expected_loss)}</span>}
                  {isSaver && <span className="text-green-400 font-semibold w-16 text-right">+{formatCompact(a.attributed_save)}</span>}
                  {!isDetractor && !isSaver && <span className="text-gray-500 w-16 text-right">—</span>}
                </div>
              </div>
            );
          })}
          <div className="text-[9px] text-gray-600 pt-1 border-t border-gray-800">
            Churn % = max(5, 50 − health × 0.5). +90d Save = (expected_loss − projected_loss) × 0.5
            attribution, where projected health = today + 90d trend continuation. For trailing-12-month
            realized save (different methodology), see CFO Overview · NRR tile.
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// CRO-6: Transition Alert Banner
// ============================================================================
// Dismissible banner shown above revenue cards when accounts have flipped
// from healthy → at_risk (or critical) in the most recent month of history.
// Reads transitions[] directly from /api/v1/health-score-history; no
// AlertRecord backend dependency. If a buyer later demands real alert-table
// integration, swap the data source — render path stays unchanged.

const TransitionAlertBanner: React.FC<{
  transitions: HealthTransition[];
  dismissedKeys: Set<string>;
  onDismissKey: (key: string) => void;
  period: CroPeriod;
}> = ({ transitions, dismissedKeys, onDismissKey, period }) => {
  // Filter: only healthy → at_risk OR healthy → critical, and dedupe per
  // account (keep the most recent transition per account in case multiple
  // months flipped within the window — latest is what the CRO cares about).
  const flips = React.useMemo(() => {
    const downward = transitions.filter(
      (t) =>
        monthInPeriod(t.month, period) &&
        t.from_status === 'healthy' &&
        (t.to_status === 'at_risk' || t.to_status === 'critical')
    );
    // Latest month first
    downward.sort((a, b) => (a.month < b.month ? 1 : a.month > b.month ? -1 : 0));
    const byAccount = new Map<number, HealthTransition>();
    for (const t of downward) {
      if (!byAccount.has(t.account_id)) byAccount.set(t.account_id, t);
    }
    return Array.from(byAccount.values());
  }, [transitions, period]);

  // The "most recent month" with any flip is the cohort we surface in the
  // banner. Older flips just contribute to the count history.
  const mostRecentMonth = flips.length > 0 ? flips[0].month : null;
  const recentFlips = flips.filter((t) => t.month === mostRecentMonth);

  // Stable dismiss key from month + account-id set: dismissed cohort stays
  // dismissed across re-renders, but a NEW month's flip surfaces fresh
  // (user dismissed Feb's banner; March flip → new banner).
  const cohortKey = mostRecentMonth
    ? `${mostRecentMonth}:${recentFlips.map((t) => t.account_id).sort().join(',')}`
    : null;

  if (!cohortKey || dismissedKeys.has(cohortKey) || recentFlips.length === 0) {
    return null;
  }

  const totalArr = recentFlips.reduce((s, t) => s + (t.arr || 0), 0);
  const monthLabel = (() => {
    // 'YYYY-MM' → 'Feb 2026'
    const [y, m] = mostRecentMonth!.split('-');
    const d = new Date(Number(y), Number(m) - 1, 1);
    return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  })();

  return (
    <div className="bg-gradient-to-r from-red-500/10 to-orange-500/5 border border-red-500/30 rounded-xl px-4 py-3 mb-4 flex items-start gap-3">
      <div className="flex-shrink-0 pt-0.5">
        <AlertTriangle className="w-4 h-4 text-red-400" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-xs font-semibold text-white">
            {recentFlips.length} account{recentFlips.length === 1 ? '' : 's'} flipped to at-risk in {monthLabel}
            <span className="text-red-300 ml-2">{formatCompact(totalArr)} ARR exposed</span>
          </p>
          <button
            onClick={() => onDismissKey(cohortKey)}
            className="text-[10px] text-gray-500 hover:text-gray-300 transition-colors flex-shrink-0"
            aria-label="Dismiss transition alert"
          >
            Dismiss
          </button>
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1.5">
          {recentFlips.slice(0, 6).map((t) => (
            <div key={t.account_id} className="text-[11px] text-gray-300 flex items-center gap-1.5">
              <span className="font-medium truncate max-w-[180px]">{t.account_name}</span>
              <span className="text-gray-500">·</span>
              <span
                className={`font-semibold ${
                  t.to_status === 'critical' ? 'text-red-400' : 'text-yellow-400'
                }`}
                title={`Health score ${t.score} (${t.from_status} → ${t.to_status})`}
              >
                {t.score}
              </span>
              <span className="text-gray-500">·</span>
              <span className="text-gray-500">{formatCompact(t.arr)}</span>
            </div>
          ))}
          {recentFlips.length > 6 && (
            <span className="text-[11px] text-gray-500 italic">+{recentFlips.length - 6} more</span>
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// CRO-7: Quarterly At-Risk ARR Comparison
// ============================================================================
// Two-column tile: "This quarter vs last quarter" + "This quarter vs same
// quarter last year". Sums ARR for accounts whose health_score < healthy_min
// (70) in the latest available month of each quarter. Uses raw monthly_scores
// from /api/v1/health-score-history rather than a separate aggregation
// endpoint — simpler, single source of truth, no new API.

interface QuarterlyAtRisk {
  label: string;       // 'Q4 2025' etc
  arr: number;
  accountCount: number;
  // Whether this quarter has data (≥1 month present in monthly_scores).
  // If false, render N/A instead of $0 — avoids implying a real zero.
  hasData: boolean;
}

function monthsInQuarterBucket(b: { y: number; q: number }): string[] {
  const startM = (b.q - 1) * 3 + 1;
  return [0, 1, 2].map((i) => `${b.y}-${String(startM + i).padStart(2, '0')}`);
}

function snapshotForBucket(
  accounts: AccountHistory[],
  b: { y: number; q: number },
  healthyMin: number,
): QuarterlyAtRisk {
  const candidateMonths = monthsInQuarterBucket(b).reverse();
  let totalAtRiskArr = 0;
  let atRiskCount = 0;
  let anyDataFound = false;
  for (const acc of accounts) {
    let scoreInQuarter: MonthlyScore | null = null;
    for (const m of candidateMonths) {
      const ms = (acc.monthly_scores || []).find((x) => x.month === m);
      if (ms) {
        scoreInQuarter = ms;
        anyDataFound = true;
        break;
      }
    }
    if (scoreInQuarter && scoreInQuarter.health_score < healthyMin) {
      totalAtRiskArr += acc.arr || 0;
      atRiskCount += 1;
    }
  }
  return {
    label: `Q${b.q} ${b.y}`,
    arr: totalAtRiskArr,
    accountCount: atRiskCount,
    hasData: anyDataFound,
  };
}

function computeQuarterlyAtRisk(
  accounts: AccountHistory[],
  anchor?: QuarterBucket | null,
): { current: QuarterlyAtRisk; lastQuarter: QuarterlyAtRisk; yearAgo: QuarterlyAtRisk } {
  const healthyMin = thresholdValues().healthy_min;
  const empty: QuarterlyAtRisk = { label: 'N/A', arr: 0, accountCount: 0, hasData: false };

  const allMonths = new Set<string>();
  for (const acc of accounts) {
    for (const ms of acc.monthly_scores || []) allMonths.add(ms.month);
  }
  const sortedMonths = Array.from(allMonths).sort();
  if (sortedMonths.length === 0) {
    return { current: empty, lastQuarter: empty, yearAgo: empty };
  }

  let currentBucket: { y: number; q: number };
  if (anchor) {
    currentBucket = { y: anchor.y, q: anchor.q };
  } else {
    const latestMonth = sortedMonths[sortedMonths.length - 1];
    const [yStr, mStr] = latestMonth.split('-');
    const latestM = Number(mStr);
    currentBucket = { y: Number(yStr), q: Math.ceil(latestM / 3) };
  }

  const prior = previousQuarter({ y: currentBucket.y, q: currentBucket.q, label: '' });
  const lastBucket = { y: prior.y, q: prior.q };
  const yearAgoBucket = { y: currentBucket.y - 1, q: currentBucket.q };

  return {
    current: snapshotForBucket(accounts, currentBucket, healthyMin),
    lastQuarter: snapshotForBucket(accounts, lastBucket, healthyMin),
    yearAgo: snapshotForBucket(accounts, yearAgoBucket, healthyMin),
  };
}

/** Period-aware view: historical tabs use health-score snapshots, not live graph $. */
function applyPeriodToCroData(
  base: CRODashboardData,
  period: CroPeriod,
  historyAccounts: AccountHistory[],
): CRODashboardData {
  const anchor = periodToAnchorBucket(period);
  const isLiveQuarter = period === 'Q4' && anchor.label === getCalendarQuarter().label;
  const quarterly = computeQuarterlyAtRisk(historyAccounts, anchor);

  const revenue_cards = base.revenue_cards.map((card, i) => {
    if (i === 0 && quarterly.current.hasData) {
      return {
        ...card,
        amount: isLiveQuarter ? card.amount : quarterly.current.arr,
        subtitle: isLiveQuarter
          ? card.subtitle
          : `Health-based at-risk ARR · end of ${quarterly.current.label}`,
        account_count: isLiveQuarter ? card.account_count : quarterly.current.accountCount,
      };
    }
    if ((i === 1 || i === 2) && !isLiveQuarter) {
      return {
        ...card,
        subtitle: `Point-in-time (context graph) · select Q4 for current confirmed $`,
      };
    }
    return card;
  });

  const healthyMin = thresholdValues().healthy_min;
  const candidateMonths = monthsInQuarterBucket(anchor).reverse();
  const risk_accounts = isLiveQuarter
    ? base.risk_accounts
    : historyAccounts
        .map((acc): RiskAccount | null => {
          let scoreInQuarter: MonthlyScore | null = null;
          for (const m of candidateMonths) {
            const ms = (acc.monthly_scores || []).find((x) => x.month === m);
            if (ms) {
              scoreInQuarter = ms;
              break;
            }
          }
          if (!scoreInQuarter || scoreInQuarter.health_score >= healthyMin) return null;
          const score = scoreInQuarter.health_score;
          const cls = score < 50 ? 'critical' as const : score < 70 ? 'at_risk' as const : 'healthy' as const;
          return {
            account_id: acc.account_id,
            account_name: acc.account_name,
            health_score: score,
            arr: acc.arr || 0,
            classification: cls,
            signal_count: 0,
            pillar_scores: {},
          };
        })
        .filter((a): a is RiskAccount => a != null)
        .sort((a, b) => a.health_score - b.health_score);

  return {
    ...base,
    revenue_cards,
    risk_accounts,
    period: periodDisplayLabel(period),
  };
}

const QuarterlyAtRiskTile: React.FC<{
  accounts: AccountHistory[];
  loading: boolean;
  monthsAvailable: number;
  period: CroPeriod;
}> = ({ accounts, loading, monthsAvailable, period }) => {
  const anchor = periodToAnchorBucket(period);
  const stats = React.useMemo(
    () => computeQuarterlyAtRisk(accounts, anchor),
    [accounts, anchor.y, anchor.q],
  );

  const renderDelta = (curr: number, ref: QuarterlyAtRisk) => {
    if (!ref.hasData) {
      return (
        <p className="text-[10px] text-gray-500 italic">
          N/A — only {monthsAvailable} month{monthsAvailable === 1 ? '' : 's'} of history available
        </p>
      );
    }
    const delta = curr - ref.arr;
    const pct = ref.arr > 0 ? (delta / ref.arr) * 100 : 0;
    const up = delta > 0;
    const flat = Math.abs(delta) < 1;
    const arrow = flat ? '→' : up ? '↑' : '↓';
    // At-risk going UP is BAD (red); down is GOOD (green).
    const color = flat ? 'text-gray-400' : up ? 'text-red-400' : 'text-green-400';
    return (
      <p className={`text-[11px] font-medium ${color}`}>
        {arrow} {formatCompact(Math.abs(delta))} ({pct >= 0 ? '+' : ''}{pct.toFixed(1)}%) vs {ref.label}
      </p>
    );
  };

  if (loading) {
    return (
      <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4 mb-4">
        <SkeletonLine w="w-1/3" />
        <div className="mt-3 grid grid-cols-2 gap-4">
          <SkeletonCard className="h-20" />
          <SkeletonCard className="h-20" />
        </div>
      </div>
    );
  }

  if (!stats.current.hasData) {
    // No history at all — hide rather than render zeros.
    return null;
  }

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4 mb-4 relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-red-500" />
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
          <h3 className="text-[10px] font-semibold text-white uppercase tracking-wide">
            Revenue at Risk · Quarterly Trend
            <span className="text-gray-500 normal-case font-normal ml-1">({periodDisplayLabel(period)})</span>
          </h3>
        </div>
        <span
          className="text-[9px] text-gray-600 italic cursor-help"
          title="At-risk ARR = total revenue of accounts with health < 70 at the end of each quarter. Snapshot at the latest available month within each quarter. QoQ = prior quarter. YoY = same quarter, prior year."
        >
          end-of-quarter snapshot
        </span>
      </div>
      <div className="grid grid-cols-2 gap-4">
        {/* QoQ */}
        <div className="bg-gray-800/30 rounded-lg p-3">
          <p className="text-[9px] text-gray-500 uppercase tracking-wide mb-1">
            This Q ({stats.current.label}) vs Last Q
          </p>
          <p className="text-xl font-bold text-red-400">{formatCompact(stats.current.arr)}</p>
          <p className="text-[10px] text-gray-500 mb-1">
            {stats.current.accountCount} at-risk account{stats.current.accountCount === 1 ? '' : 's'}
          </p>
          {renderDelta(stats.current.arr, stats.lastQuarter)}
        </div>
        {/* YoY */}
        <div className="bg-gray-800/30 rounded-lg p-3">
          <p className="text-[9px] text-gray-500 uppercase tracking-wide mb-1">
            This Q ({stats.current.label}) vs Same Q Last Year
          </p>
          <p className="text-xl font-bold text-red-400">{formatCompact(stats.current.arr)}</p>
          <p className="text-[10px] text-gray-500 mb-1">
            {stats.current.accountCount} at-risk account{stats.current.accountCount === 1 ? '' : 's'}
          </p>
          {renderDelta(stats.current.arr, stats.yearAgo)}
        </div>
      </div>
    </div>
  );
};

/** Risk account card with expandable pillar breakdown + action buttons */
const RiskAccountCard: React.FC<{ account: RiskAccount; onClick: () => void; onDraftEmail?: (account: RiskAccount) => void }> = ({ account, onClick, onDraftEmail }) => {
  const [showPillars, setShowPillars] = React.useState(false);
  const cls = classify(account.health_score);
  const color = classifyColor(account.health_score);
  const barWidth = Math.max(5, Math.min(100, account.health_score));
  const pillars = account.pillar_scores || {};
  const pillarEntries = Object.entries(pillars).sort(([, a], [, b]) => a - b); // worst first

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 hover:border-gray-600/50 transition-all text-left w-full">
      <button onClick={onClick} className="p-4 w-full text-left group">
        <div className="flex items-start justify-between mb-3">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-white truncate">{account.account_name}</p>
            <p className="text-xs text-gray-500">{formatCompact(account.arr)} ARR</p>
            {/* CRO-5: CSM owner row — lets CRO route escalations without
                drilling into get_crm_account_data. Shows "Unassigned" italic
                when null so a missing CSM is visible, not silently hidden. */}
            <p className="text-[10px] text-gray-500 mt-1 truncate flex items-center gap-1">
              <Users className="w-2.5 h-2.5 text-gray-600 flex-shrink-0" />
              <span className="text-gray-600">CSM:</span>
              {account.assigned_csm ? (
                <span className="text-gray-300 font-medium truncate">{account.assigned_csm}</span>
              ) : (
                <span className="italic text-gray-600">Unassigned</span>
              )}
            </p>
          </div>
          <span
            className={`text-[10px] font-semibold px-2 py-0.5 rounded-full flex-shrink-0 ml-2 ${
              cls === 'critical' ? 'bg-red-500/20 text-red-400'
              : cls === 'at_risk' ? 'bg-yellow-500/20 text-yellow-400'
              : 'bg-green-500/20 text-green-400'
            }`}
          >
            {cls === 'critical' ? 'Critical' : cls === 'at_risk' ? 'At Risk' : 'Healthy'}
          </span>
        </div>
        {/* Health bar */}
        <div className="mb-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-500">Health Score</span>
            <span className="text-xs font-semibold" style={{ color }}>{account.health_score}</span>
          </div>
          <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all" style={{ width: `${barWidth}%`, background: `linear-gradient(90deg, ${color}, ${color}88)` }} />
          </div>
        </div>
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <AlertTriangle className="w-3 h-3" />
          <span>{account.signal_count > 0 ? `${account.signal_count} active signals` : 'No recent signals'}</span>
        </div>
      </button>
      {/* Expandable pillar breakdown */}
      {pillarEntries.length > 0 && (
        <div className="px-4 pb-3">
          <button
            onClick={(e) => { e.stopPropagation(); setShowPillars(!showPillars); }}
            className="text-[10px] text-teal-500 hover:text-teal-400 flex items-center gap-1"
          >
            <ChevronDown className={`w-3 h-3 transition-transform ${showPillars ? 'rotate-180' : ''}`} />
            {showPillars ? 'Hide' : 'Show'} Pillar Breakdown
          </button>
          {showPillars && (
            <div className="mt-2 space-y-1.5">
              {pillarEntries.map(([pillar, score], idx) => {
                const pColor = classifyColor(score);
                const pWidth = Math.max(5, Math.min(100, score));
                const isWorst = idx === 0 && score < 50;
                return (
                  <div key={pillar} className="flex items-center gap-2">
                    <span className={`text-[10px] w-20 truncate font-mono ${isWorst ? 'text-red-400 font-bold' : 'text-gray-500'}`} title={(() => { try { const pl = JSON.parse(localStorage.getItem('pillar_labels') || '{}'); return pl[pillar] || pillar; } catch { return pillar; } })()}>{(() => { try { const pl = JSON.parse(localStorage.getItem('pillar_labels') || '{}'); return pl[pillar] || pillar; } catch { return pillar; } })()}</span>
                    <div className="flex-1 h-1 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${pWidth}%`, backgroundColor: pColor }} />
                    </div>
                    <span className={`text-[10px] w-6 text-right ${isWorst ? 'text-red-400 font-bold' : 'text-gray-400'}`}>{Math.round(score)}</span>
                    {isWorst && <span className="text-[9px] text-red-400">← worst</span>}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
      {/* Quick action buttons */}
      <div className="px-4 pb-3 flex items-center gap-2">
        {onDraftEmail && (
          <button
            onClick={(e) => { e.stopPropagation(); onDraftEmail(account); }}
            className="text-[10px] px-2 py-1 rounded bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition-colors"
            aria-label={`Draft email to ${account.account_name}`}
          >
            Draft Email
          </button>
        )}
        <button
          onClick={(e) => { e.stopPropagation(); onClick(); }}
          className="text-[10px] px-2 py-1 rounded bg-gray-700/50 text-gray-400 hover:bg-gray-600/50 transition-colors"
          aria-label={`View timeline for ${account.account_name}`}
        >
          View Timeline
        </button>
      </div>
    </div>
  );
};

/** ROI scaling bar chart (right sidebar) */
const ROIScalingChart: React.FC<{ data: ROIScalingPoint[] }> = ({ data }) => (
  <ResponsiveContainer width="100%" height={140}>
    <BarChart data={data} margin={{ top: 10, right: 0, left: -15, bottom: 0 }}>
      <XAxis
        dataKey="label"
        tick={{ fill: '#6b7280', fontSize: 10 }}
        axisLine={false}
        tickLine={false}
      />
      <YAxis
        tick={{ fill: '#6b7280', fontSize: 10 }}
        axisLine={false}
        tickLine={false}
        tickFormatter={(v: number) => `${v}%`}
      />
      <Tooltip
        contentStyle={{ backgroundColor: '#1a1f2e', border: '1px solid #374151', borderRadius: 8, fontSize: 12, color: '#fff' }}
        formatter={(value: number) => [`${value}%`, 'ROI']}
      />
      <Bar dataKey="roi" radius={[4, 4, 0, 0]}>
        {data.map((entry, i) => (
          <Cell key={`cell-${i}`} fill={i === 0 ? '#06b6d4' : i === 1 ? '#22c55e' : '#a855f7'} />
        ))}
      </Bar>
    </BarChart>
  </ResponsiveContainer>
);

/** Revenue timeline (right sidebar) */
const RevenueTimelineWidget: React.FC<{ timeline: RevenueTimeline | null; loading: boolean }> = ({ timeline, loading }) => {
  if (loading) {
    return (
      <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
        <SkeletonLine w="w-3/4" />
        <div className="mt-4 space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-3 animate-pulse">
              <div className="w-2 h-2 rounded-full bg-gray-700 mt-1.5" />
              <div className="flex-1 space-y-1">
                <div className="h-3 bg-gray-700 rounded w-2/3" />
                <div className="h-2 bg-gray-700 rounded w-full" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!timeline) {
    return (
      <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
        <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-3">
          Revenue Timeline
        </h3>
        <p className="text-xs text-gray-500 text-center py-4">
          Click a risk account to view its revenue timeline.
        </p>
      </div>
    );
  }

  const typeColors: Record<string, string> = {
    signal: 'text-yellow-400',
    intervention: 'text-cyan-400',
    outcome: 'text-green-400',
  };

  let lastMonth = '';

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
      <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-1">
        Revenue Timeline
      </h3>
      <p className="text-xs text-gray-400 mb-4">
        {timeline.account_name} &middot; {formatCompact(timeline.arr)} ARR
      </p>
      <div className="relative pl-4">
        {/* Vertical line */}
        <div className="absolute left-[7px] top-1 bottom-1 w-px bg-gray-700/50" />
        <div className="space-y-4">
          {timeline.events.map((event, i) => {
            const showMonth = event.month !== lastMonth;
            lastMonth = event.month;
            const dotColor = ACCENT_MAP[event.color] || '#6b7280';
            return (
              <div key={i} className="relative">
                {showMonth && (
                  <p className="text-[10px] font-semibold text-gray-600 uppercase tracking-wider mb-1 -ml-4">
                    {event.month}
                  </p>
                )}
                <div className="flex gap-3 items-start">
                  <div
                    className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ring-2 ring-[#1a1f2e]"
                    style={{ backgroundColor: dotColor }}
                  />
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-medium ${typeColors[event.type] || 'text-gray-300'}`}>
                      {event.title}
                    </p>
                    <p className="text-[11px] text-gray-500 leading-relaxed">{event.description}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const CRODashboard: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { session } = useSession();

  // View state — read from URL param or default to overview
  const viewParam = (searchParams.get('view') || 'cro-overview') as ViewId;
  const [activeView, setActiveView] = useState<ViewId>(viewParam);

  const [data, setData] = useState<CRODashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);

  const [timeline, setTimeline] = useState<RevenueTimeline | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [selectedAccountId, setSelectedAccountId] = useState<string | number | null>(null);

  const [activePeriod, setActivePeriod] = useState<'Q3' | 'Q4' | 'TTM'>('Q4');
  const [emailDraftAccount, setEmailDraftAccount] = useState<RiskAccount | null>(null);

  // CRO-6: client-side flip-detection from /api/v1/health-score-history.
  // We pull the transitions[] array and filter for healthy → at_risk (or
  // critical). months=12 is the tool's max; tenants with shorter history
  // simply produce fewer transitions — banner hides cleanly.
  const [historyTransitions, setHistoryTransitions] = useState<HealthTransition[]>([]);
  const [dismissedTransitionKeys, setDismissedTransitionKeys] = useState<Set<string>>(new Set());

  // CRO-7: per-account monthly history powers the QoQ + YoY at-risk ARR
  // tile. Same /api/v1/health-score-history fetch as CRO-6 (one network
  // call). historyMonthsAvailable lets the YoY tile show "N/A — only X
  // months" instead of $0 for tenants without 12 months of history.
  const [historyAccounts, setHistoryAccounts] = useState<AccountHistory[]>([]);
  const [historyMonthsAvailable, setHistoryMonthsAvailable] = useState<number>(0);
  const [historyLoading, setHistoryLoading] = useState<boolean>(true);

  // Forecast horizon for Predictor v3 tile. Defaults to '12mo' so existing
  // dashboard behavior is preserved; selecting 'quarter' answers the FDE
  // CRO-1 question ("revenue at risk next quarter") with a 3-month window;
  // 'renewal' uses each account's contract renewal date. The PredictorV3Tile
  // re-fetches when this changes (its useEffect depends on horizon).
  const [predictorHorizon, setPredictorHorizon] = useState<'renewal' | 'quarter' | '12mo'>('12mo');

  // Update URL when view changes
  const handleViewChange = useCallback((view: ViewId) => {
    trackEvent('dashboard_switch', `cro_${view}`, { persona: 'cro', view });
    setActiveView(view);
    if (view === 'cro-overview') {
      setSearchParams({});
    } else {
      setSearchParams({ view });
    }
  }, [setSearchParams]);

  // Fetch main dashboard data
  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const customerId = getCustomerIdentifier(session);
        const resp = await apiCall('/api/executive/cro-dashboard', {
          headers: { 'X-Customer-ID': customerId },
        });
        if (!resp.ok) {
          setErrorStatus(resp.status);
          throw new Error(`API returned ${resp.status}`);
        }
        const json = await resp.json();
        // Store vertical context for pillar label resolution across components
        if (json.pillar_labels) {
          try { localStorage.setItem('pillar_labels', JSON.stringify(json.pillar_labels)); } catch {}
        }
        if (json.vertical) {
          try { localStorage.setItem('vertical', json.vertical); } catch {}
        }
        if (!cancelled) {
          // Transform flat API response into CRODashboardData shape
          const isEstimatedRoi = json.playbook_roi_estimated === true;
          const roiLabel = isEstimatedRoi ? 'Estimated (Power-of-1)' : `↑ ${json.playbook_roi_pct || 0}pp vs Q3`;
          const proof = json.proof_data || {};
          const executionsTotal = proof.executions_total || 0;
          const realizedRoi = proof.realized_roi || 0;
          const customerPhase: CustomerPhase =
            executionsTotal === 0 ? 'pre_deploy'
            : executionsTotal <= 5 ? 'onboarding'
            : 'active';
          const graphProv = json.context_graph_provenance || null;
          const contextGraphRevenue: CROContextGraphRevenue | null = {
            revenue_at_risk: json.revenue_at_risk || 0,
            graph_revenue_protected: json.revenue_protected || 0,
            expansion_pipeline: json.expansion_pipeline || 0,
            revenue_risk_label: json.revenue_risk_label || 'Confirmed Risk (Context Graph)',
            provenance: graphProv,
          };
          const arrExposure = json.arr_exposure || 0;
          const transformed: CRODashboardData = {
            revenue_cards: [
              {
                label: 'Revenue at Risk',
                amount: json.revenue_at_risk || 0,
                subtitle: json.revenue_risk_label || 'Confirmed (context graph)',
                account_count: json.accounts_at_risk_count || 0,
                accent: 'red',
                badge: 'Confirmed',
                footnote: arrExposure > 0
                  ? `ARR exposure (health-band): ${formatCompact(arrExposure)} · ${json.arr_exposure_label || 'sub-70 accounts'}`
                  : undefined,
              },
              {
                label: 'Revenue Protected',
                amount: json.revenue_protected || 0,
                subtitle: json.accounts_recovered_count ? 'Playbook interventions proven' : 'Context graph confirmed',
                account_count: json.accounts_recovered_count || undefined,
                accent: 'green',
                badge: 'Confirmed',
              },
              {
                label: 'Expansion Pipeline',
                amount: json.expansion_pipeline || 0,
                subtitle: json.expansion_candidates_count ? 'Stakeholder maps confirmed' : 'Context graph confirmed',
                account_count: json.expansion_candidates_count || undefined,
                accent: 'cyan',
                badge: 'Confirmed',
              },
            ],
            metrics: [
              { label: 'Avg Health Score', value: (json.avg_health_score || 0).toFixed(1), change: `${json.health_score_change >= 0 ? '↑' : '↓'} ${Math.abs(json.health_score_change || 0).toFixed(1)} vs Q3`, trend: json.health_score_change >= 0 ? 'up' : 'down', tooltip: 'Revenue-weighted average across all accounts. Larger accounts (by ARR) have proportionally more influence on this score.' },
              { label: 'Early Warning Lead', value: `${json.early_warning_days || 0}d`, change: '↑ 12d vs Q3', trend: 'up', tooltip: 'Average number of days between first risk signal detection and health score decline. Higher = more lead time to intervene.' },
              { label: 'Playbook ROI', value: `${json.playbook_roi_pct || 0}%`, change: roiLabel, trend: 'up', tooltip: isEstimatedRoi ? 'Projected ROI from Power-of-1 industry benchmarks (TSIA, Gainsight Pulse, KeyBanc). Shows what 1% improvement across all metrics would deliver at your ARR.' : 'ROI from tracked playbook executions and measured health score improvements.' },
              { label: 'NRR Projection', value: `${json.nrr_projection || 100}%`, change: `${(json.nrr_change || 0) >= 0 ? '↑' : '↓'} ${Math.abs(json.nrr_change || 0)}pp vs baseline`, trend: (json.nrr_change || 0) >= 0 ? 'up' : 'down', accent: (json.nrr_projection || 100) >= 100 ? 'cyan' : undefined, tooltip: 'Projected Net Revenue Retention derived from health score correlation. Health ≥70 → expansion (NRR>100%). Health <70 → contraction (NRR<100%). Based on industry benchmarks (TSIA, KeyBanc).' },
            ],
            story_arcs: (json.story_arcs || []).map((arc: any) => ({
              id: arc.id || arc.name?.toLowerCase().replace(/\s+/g, '_') || 'unknown',
              name: arc.name || 'Unknown Arc',
              icon: arc.icon || 'alert',
              description: arc.description || '',
              account_count: arc.accounts || arc.account_count || 0,
              revenue_impact: arc.revenue_impact || 0,
              impact_type: arc.impact_type || 'risk',
            })),
            risk_accounts: (json.highest_risk_accounts || []).map((a: any) => {
              const score = a.health_score || 0;
              const cls = score < 50 ? 'critical' as const
                        : score < 70 ? 'at_risk' as const
                        : 'healthy' as const;
              return {
                account_id: a.account_id,
                account_name: a.account_name,
                health_score: score,
                arr: a.revenue || a.arr || 0,
                classification: cls,
                signal_count: a.signal_count || 0,
                pillar_scores: a.pillar_scores || {},
                assigned_csm: a.assigned_csm || null,
              };
            }),
            roi_summary: {
              roi_pct: json.playbook_roi_pct || 0,
              invested: json.cs_investment || json.estimated_investment || 0,
              impact: json.roi_impact || ((json.cs_investment || json.estimated_investment || 0) * (1 + (json.playbook_roi_pct || 0) / 100)),
              scaling: [
                { accounts: 10, label: '10 accts', roi: json.playbook_roi_pct || 0 },
                { accounts: 50, label: '50 accts', roi: Math.round((json.playbook_roi_pct || 0) * 2.44) },
                { accounts: 200, label: '200 accts', roi: Math.round((json.playbook_roi_pct || 0) * 3.79) },
              ],
            },
            // Dual NRR
            nrr_current: json.nrr_current || json.nrr_projection || 100,
            nrr_with_intervention: json.nrr_with_intervention || json.nrr_projection || 100,
            nrr_arr_protected: json.nrr_arr_protected || 0,
            nrr_trajectory: json.nrr_trajectory || {},
            nrr_waterfall: json.nrr_waterfall_summary || { total_exposure: 0, expected_loss: 0, gross_saved: 0, attributed_save: 0, intervention_cost: 0, roi_x: 0, accounts: [] },
            renewals_at_risk: json.renewals_at_risk || [],
            period: json.quarter_label || `Q${Math.ceil((new Date().getMonth() + 1) / 3)} ${new Date().getFullYear()}`,
            last_updated: json.last_updated || new Date().toISOString(),
            arr_exposure: arrExposure,
            arr_exposure_label: json.arr_exposure_label || 'Exposure (ARR in at-risk accounts)',
            revenue_risk_label: json.revenue_risk_label || 'Confirmed Risk (Context Graph)',
            context_graph_revenue: contextGraphRevenue,
            proof_data: proof,
            customer_phase: customerPhase,
            playbook_roi_estimated: isEstimatedRoi,
            wizard_b_nrr: json.wizard_b_nrr || null,
          };
          setData(transformed);
          trackPageView('cro_dashboard', { accounts: transformed.risk_accounts?.length || 0 });
        }
      } catch {
        if (!cancelled) {
          setError('Unable to load dashboard data. Please check your connection and try again.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchData();
    return () => { cancelled = true; };
  }, [session]);

  // CRO-6 + CRO-7: fetch 12 months of health-score history powers both
  // transition alerts and QoQ/YoY at-risk ARR comparison. Endpoint
  // /api/v1/health-score-history is vertical-agnostic (works for SaaS
  // Premium + DC2S, backed by the DC2S handler which queries by
  // customer_id). Non-fatal on failure: tile + banner just won't render.
  useEffect(() => {
    let cancelled = false;
    const fetchHistory = async () => {
      setHistoryLoading(true);
      try {
        const customerId = getCustomerIdentifier(session);
        const resp = await apiCall('/api/v1/health-score-history?months=12', {
          headers: { 'X-Customer-ID': customerId },
        });
        if (!resp.ok) {
          throw new Error(`history API returned ${resp.status}`);
        }
        const json = await resp.json();
        if (cancelled) return;
        setHistoryTransitions((json.transitions || []) as HealthTransition[]);
        setHistoryAccounts((json.accounts || []) as AccountHistory[]);
        // Months actually available = max length across accounts. Used by
        // the YoY tile to show "N/A — only X months of history" rather
        // than silently rendering zeros for tenants without 12 months.
        const maxMonths = (json.accounts || []).reduce(
          (m: number, a: AccountHistory) => Math.max(m, (a.monthly_scores || []).length),
          0
        );
        setHistoryMonthsAvailable(maxMonths);
      } catch {
        if (!cancelled) {
          setHistoryTransitions([]);
          setHistoryAccounts([]);
          setHistoryMonthsAvailable(0);
        }
      } finally {
        if (!cancelled) setHistoryLoading(false);
      }
    };
    fetchHistory();
    return () => { cancelled = true; };
  }, [session]);

  // Fetch revenue timeline for selected account
  const fetchTimeline = useCallback(async (accountId: string | number) => {
    setTimelineLoading(true);
    setSelectedAccountId(accountId);
    try {
      const customerId = getCustomerIdentifier(session);
      const resp = await apiCall(`/api/executive/revenue-timeline?account_id=${accountId}`, {
        headers: { 'X-Customer-ID': customerId },
      });
      if (!resp.ok) {
          setErrorStatus(resp.status);
          throw new Error(`API returned ${resp.status}`);
        }
      const json = await resp.json();
      setTimeline(json);
    } catch {
      setTimeline(null);
    } finally {
      setTimelineLoading(false);
    }
  }, [session]);

  const handleNav = useCallback((path: string) => {
    navigate(path);
  }, [navigate]);

  // Sidebar badge data — show count of truly at-risk/critical accounts, not array length
  const accountCount = data?.risk_accounts?.filter(a => (a.health_score || 0) < 70).length || 0;
  const signalCount = data?.story_arcs?.reduce((s, a) => s + (a.account_count || 0), 0) || 0;
  const roiPct = data?.roi_summary?.roi_pct || 0;

  const displayData = useMemo(() => {
    if (!data) return null;
    return applyPeriodToCroData(data, activePeriod, historyAccounts);
  }, [data, activePeriod, historyAccounts]);

  const isLiveQuarter =
    activePeriod === 'Q4' && periodToAnchorBucket('Q4').label === getCalendarQuarter().label;

  // ---- Sub-view rendering (non-overview views) ----
  if (activeView !== 'cro-overview') {
    return (
      <div className="flex h-screen bg-[#0f1419] text-white font-['Inter',sans-serif]">
        <SidebarNav
          activeId={activeView}
          onViewChange={handleViewChange}
          onNavigate={handleNav}
          accountCount={accountCount}
          signalCount={signalCount}
          roiPct={roiPct}
        />
        <main className="flex-1 overflow-y-auto">
          <React.Suspense fallback={
            <div className="p-6">
              <div className="grid grid-cols-4 gap-4 mb-6">
                <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
              </div>
              <div className="space-y-4">
                <SkeletonCard className="h-64" />
                <SkeletonCard className="h-48" />
              </div>
            </div>
          }>
            {activeView === 'signal-timeline' && <SignalTimelineView />}
            {activeView === 'context-graph' && <ContextGraphView />}
            {activeView === 'roi-engine' && <ROIEngineView />}
            {activeView === 'accounts' && <AccountsView />}
            {activeView === 'playbooks' && (
              <div className="p-6">
                <h1 className="text-lg font-semibold mb-4">Playbooks</h1>
                <p className="text-gray-400">Playbook management coming soon. View playbooks from the <button onClick={() => handleViewChange('cro-overview')} className="text-cyan-400 hover:text-cyan-300">CRO Overview</button>.</p>
              </div>
            )}
            {activeView === 'approvals' && (
              <div className="p-6">
                <h1 className="text-lg font-semibold mb-4">Approval Queue</h1>
                <p className="text-gray-400">Approval queue coming soon. View approvals from the <button onClick={() => handleViewChange('cro-overview')} className="text-cyan-400 hover:text-cyan-300">CRO Overview</button>.</p>
              </div>
            )}
          </React.Suspense>
        </main>
      </div>
    );
  }

  // ---- Loading state (overview only) ----
  if (loading) {
    return (
      <div className="flex h-screen bg-[#0f1419] text-white font-['Inter',sans-serif]">
        <SidebarNav activeId="cro-overview" onViewChange={handleViewChange} onNavigate={handleNav} />
        <main className="flex-1 p-6 overflow-y-auto">
          <div className="mb-6">
            <SkeletonLine w="w-64" />
          </div>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <SkeletonCard /><SkeletonCard /><SkeletonCard />
          </div>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
          </div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => <SkeletonCard key={i} className="h-16" />)}
          </div>
        </main>
        <aside className="w-80 bg-[#0d1117] border-l border-gray-700/50 p-4">
          <SkeletonCard className="h-72 mb-4" />
          <SkeletonCard className="h-64" />
        </aside>
      </div>
    );
  }

  if (error) {
    return (
      <DashboardErrorState
        dashboardLabel="CRO dashboard"
        errorMessage={error}
        errorStatus={errorStatus}
      />
    );
  }

  // ---- Error state ----
  if (error && !data) {
    return (
      <DashboardErrorState
        dashboardLabel="CRO dashboard"
        errorMessage={error}
        errorStatus={errorStatus}
      />
    );
  }

  if (!data || !displayData) {
    return (
      <DashboardErrorState
        dashboardLabel="CRO dashboard"
        errorMessage="No dashboard data available."
        errorStatus={null}
      />
    );
  }

  const d = displayData;

  return (
    <div className="flex flex-col h-screen bg-[#0f1419] text-white font-['Inter',sans-serif]">
      <DashboardTopBar accent="red" />
      <div className="flex flex-1 overflow-hidden">
      {/* ---- Left Sidebar ---- */}
      <SidebarNav
        activeId="cro-overview"
        onViewChange={handleViewChange}
        onNavigate={handleNav}
        accountCount={accountCount}
        signalCount={signalCount}
        roiPct={roiPct}
      />

      {/* ---- Main Content ---- */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-[1200px]">
          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-lg font-semibold text-white tracking-tight">
                REVENUE INTELLIGENCE
                <span className="text-gray-500 font-normal ml-2">&middot; {displayData.period}</span>
              </h1>
              <div className="h-0.5 w-12 bg-red-500 mt-1.5 rounded-full" />
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
              <span className="text-gray-700">|</span>
              {(['Q3', 'Q4', 'TTM'] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => {
                    setActivePeriod(p);
                    trackEvent('cro_period_change', p, { persona: 'cro', period: p });
                  }}
                  className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                    activePeriod === p
                      ? 'bg-white/10 text-white ring-1 ring-white/20'
                      : 'text-gray-500 hover:text-gray-300'
                  }`}
                  aria-pressed={activePeriod === p}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <CROMetricGuideBanner />
          {d.context_graph_revenue && (
            <CROContextGraphStrip
              data={d.context_graph_revenue}
              onOpenGraph={() => handleViewChange('context-graph')}
            />
          )}
          <CROPreProofBanner
            phase={d.customer_phase}
            executionsTotal={d.proof_data.executions_total || 0}
            realizedRoi={d.proof_data.realized_roi || 0}
          />

          {!isLiveQuarter && (
            <div className="mb-4 rounded-lg border border-amber-700/40 bg-amber-950/20 px-4 py-2.5 text-[11px] text-amber-100/80">
              Viewing <span className="font-semibold text-amber-200">{displayData.period}</span> — revenue at risk
              and account list use health-score snapshots for that period. Protected / expansion $ and forward
              forecast are point-in-time; switch to <span className="font-semibold">Q4</span> for live context-graph totals.
            </div>
          )}

          {/* CRO-6: dismissible alert when accounts flipped healthy → at_risk
              in the most recent month. Computed client-side from
              health-score-history transitions[]. Hidden when no flips or
              when the cohort has been dismissed. */}
          <TransitionAlertBanner
            transitions={historyTransitions}
            dismissedKeys={dismissedTransitionKeys}
            onDismissKey={(k) =>
              setDismissedTransitionKeys((prev) => new Set(prev).add(k))
            }
            period={activePeriod}
          />

          {/* Row 1: Revenue cards */}
          <div className="grid grid-cols-3 gap-4 mb-4">
            {displayData.revenue_cards.map((card, i) => (
              <RevenueCardComponent key={i} card={card} riskAccounts={i === 0 ? displayData.risk_accounts : undefined} />
            ))}
          </div>

          {/* CRO-7: QoQ + YoY at-risk ARR comparison. Sits just under the
              Revenue at Risk card so the CRO has trend context without
              hunting for it. Hides cleanly if no history available. */}
          <QuarterlyAtRiskTile
            accounts={historyAccounts}
            loading={historyLoading}
            monthsAvailable={historyMonthsAvailable}
            period={activePeriod}
          />

          {/* Predictor v3 — top expansion + top at-risk per-account forecast.
              Renders for any tenant with a calibrated Wizard D fit.
              The CRO is the primary consumer of per-account forecasts
              (where to deploy plays, who to escalate); CFO sees the
              portfolio aggregate, CRO sees the per-account drill-down.

              Horizon selector (added May 17 2026, FDE CRO-1 fix): switches
              the at-risk + expansion + per-account NRR queries between
              account-specific renewal date, 3-month quarter window, and
              12-month default. The tile re-fetches when horizon changes. */}
          {isLiveQuarter && session && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <div className="text-[10px] uppercase tracking-[0.18em] text-gray-500">
                  Forward NRR Forecast
                </div>
                <div
                  className="inline-flex items-center gap-1 text-[11px]"
                  role="radiogroup"
                  aria-label="Forecast horizon"
                >
                  <span className="text-gray-500 mr-1">Horizon:</span>
                  {([
                    { id: 'renewal' as const, label: 'Renewal' },
                    { id: 'quarter' as const, label: 'Quarter' },
                    { id: '12mo' as const,    label: '12mo'    },
                  ]).map((opt) => {
                    const active = predictorHorizon === opt.id;
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        role="radio"
                        aria-checked={active}
                        onClick={() => {
                          setPredictorHorizon(opt.id);
                          trackEvent('cro_horizon_change', `horizon_${opt.id}`, {
                            persona: 'cro',
                            horizon: opt.id,
                          });
                        }}
                        className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
                          active
                            ? 'bg-cyan-500/15 text-cyan-300 ring-1 ring-cyan-500/40'
                            : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                        }`}
                        title={
                          opt.id === 'renewal' ? "Each account's contract renewal date"
                          : opt.id === 'quarter' ? "3 months from now — answers 'this quarter' questions"
                          : '12 months from now (default)'
                        }
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>
              <PredictorV3Tile
                customerId={session.customer_id}
                saasProfile={(session.vertical === 'saas_premium') ? 'saas_enterprise' : 'saas_enterprise'}
                horizon={predictorHorizon}
                limit={5}
              />
            </div>
          )}

          {/* Row 2: Metric cards (first 3) + Dual NRR card */}
          <div className="grid grid-cols-4 gap-4 mb-4">
            {d.metrics.slice(0, 3).map((m, i) => (
              <MetricCardComponent key={i} metric={m} />
            ))}
            {/* Forward NRR Card — health-weighted projection at 90d horizon.
                Distinct from CFO Overview's NRR tile, which shows realized
                NRR from definitive lifecycle outcomes. This card projects
                NRR forward by attributing residual at-risk ARR through the
                health-to-churn-prob curve. Same Without/With dichotomy,
                different time horizon. */}
            <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4 relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-0.5 bg-cyan-500" />
              <div className="flex items-baseline justify-between mb-2">
                <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Forward NRR</p>
                <span className="text-[9px] text-gray-600">90d horizon</span>
              </div>
              <div className="flex items-end gap-3 mb-2">
                <div>
                  <p className="text-[9px] text-gray-500 mb-0.5">Without CS Pulse</p>
                  <p className={`text-2xl font-bold ${d.nrr_current >= 100 ? 'text-cyan-400' : 'text-red-400'}`}>{d.nrr_current}%</p>
                </div>
                <div className="text-gray-600 text-lg pb-1">&rarr;</div>
                <div>
                  <p className="text-[9px] text-gray-500 mb-0.5">With CS Pulse (projected)</p>
                  <p className="text-2xl font-bold text-green-400">{d.nrr_with_intervention}%</p>
                </div>
              </div>
              {d.nrr_arr_protected > 0 && (
                <p className="text-[10px] text-green-400/80">
                  {formatCompact(d.nrr_arr_protected)} ARR protectable (attributed)
                </p>
              )}
              <p className="text-[9px] text-gray-600 mt-1">
                Forward projection — health-weighted churn risk over the next 90 days. For
                realized NRR (lifecycle outcomes), see CFO Overview · NRR tile.
              </p>
            </div>
          </div>

          {/* NRR Trajectory + Revenue Waterfall */}
          {(Object.keys(d.nrr_trajectory).length > 0 || d.nrr_waterfall.accounts.length > 0) && (
            <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden mb-6">
              <div className="px-5 py-3 border-b border-gray-700/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-[10px] font-semibold text-white uppercase tracking-wide">NRR Forecast &middot; Revenue Waterfall</h3>
                </div>
              </div>
              <div className="grid grid-cols-2 divide-x divide-gray-700/50">
                {/* Left: T+30/60/90 trajectory.
                    Issue #3 + #10 fix (May 4 2026): clarify methodology vs Forward NRR card.
                    This trajectory uses ALL accounts with a 5% churn floor (every account
                    contributes some loss); Forward NRR card uses at-risk-only without floor.
                    Same data, different attribution windows — different numbers. */}
                <div className="p-4">
                  <div className="flex items-baseline justify-between mb-3">
                    <p className="text-[9px] text-gray-500 uppercase tracking-wide">Trajectory · all accounts</p>
                    <span
                      className="text-[8px] text-gray-600 italic cursor-help"
                      title="Portfolio NRR projected at T+30/60/90 days using linear health trend continuation, with a 5% churn-probability floor on every account (no account is treated as risk-free). Differs from Forward NRR tile, which scopes to at-risk only with no floor — same data, two attribution windows."
                    >
                      with 5% floor
                    </span>
                  </div>
                  <div className="flex items-end gap-6">
                    {['t30', 't60', 't90'].map((k, i) => {
                      const pt = d.nrr_trajectory[k];
                      if (!pt) return null;
                      const color = pt.nrr_pct >= 100 ? 'text-green-400' : pt.nrr_pct >= 95 ? 'text-yellow-400' : 'text-red-400';
                      return (
                        <div key={k} className="text-center">
                          <p className={`text-xl font-bold ${color}`}>{pt.nrr_pct}%</p>
                          <p className="text-[9px] text-gray-500">T+{(i + 1) * 30}d</p>
                          {pt.crossings.length > 0 && (
                            <p
                              className="text-[8px] text-orange-400 mt-1 cursor-help"
                              title="Accounts whose projected health crosses below the at-risk threshold (health < 70) by this horizon — these are the next playbook candidates."
                            >
                              {pt.crossings.length} cross{pt.crossings.length > 1 ? 'ings' : 'ing'} into at-risk
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
                {/* Right: Waterfall summary */}
                <div className="p-4">
                  <p className="text-[9px] text-gray-500 uppercase tracking-wide mb-3">Revenue Impact</p>
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between"><span className="text-gray-400">ARR Exposed</span><span className="text-red-400 font-semibold">{formatCompact(d.nrr_waterfall.total_exposure)}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Expected Loss</span><span className="text-red-400">{formatCompact(d.nrr_waterfall.expected_loss)}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Protectable (attributed)</span><span className="text-green-400 font-semibold">{formatCompact(d.nrr_waterfall.attributed_save)}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Intervention Cost</span><span className="text-gray-300">{formatCompact(d.nrr_waterfall.intervention_cost)}</span></div>
                    {d.nrr_waterfall.roi_x > 0 && (
                      <div className="flex justify-between border-t border-gray-700/50 pt-1.5"><span className="text-gray-400">Projected ROI</span><span className="text-cyan-400 font-bold">{d.nrr_waterfall.roi_x}x</span></div>
                    )}
                  </div>
                </div>
              </div>
              {/* Per-account NRR attribution (expandable) */}
              {d.nrr_waterfall.accounts.length > 0 && (
                <NRRAccountAttribution accounts={d.nrr_waterfall.accounts} />
              )}
            </div>
          )}

          {/* Story Arcs — click navigates to filtered account list */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[10px] font-semibold tracking-[0.2em] text-gray-500 uppercase">
                Context Graph &middot; Story Arcs
              </h2>
              <button
                onClick={() => handleViewChange('context-graph')}
                className="text-xs text-cyan-500 hover:text-cyan-400 transition-colors flex items-center gap-1"
              >
                View all <ArrowRight className="w-3 h-3" />
              </button>
            </div>
            <div className="space-y-2">
              {d.story_arcs.map((arc) => (
                <StoryArcRow
                  key={arc.id}
                  arc={arc}
                  onClick={() => {
                    setSearchParams({ view: 'accounts', arc: arc.id });
                    setActiveView('accounts');
                  }}
                />
              ))}
            </div>
          </div>

          {/* Renewals at Risk — compact banner */}
          {d.renewals_at_risk.length > 0 && (
            <div className="bg-[#1a1f2e] rounded-xl border border-yellow-600/30 p-4 mb-6">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-3.5 h-3.5 text-yellow-500" />
                  <span className="text-[10px] font-semibold text-white uppercase tracking-wide">Renewals at Risk</span>
                  <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400">
                    {d.renewals_at_risk.length}
                  </span>
                </div>
                <span className="text-[10px] text-gray-500">{formatCompact(d.renewals_at_risk.reduce((s: number, r: any) => s + r.arr, 0))} ARR in next 90d</span>
              </div>
              <div className="flex gap-3 overflow-x-auto pb-1">
                {d.renewals_at_risk.slice(0, 6).map((r, i) => (
                  <div key={i} className="flex-shrink-0 bg-gray-800/50 rounded-lg px-3 py-2 text-xs">
                    <p className="text-white font-medium truncate max-w-[120px]">{r.account_name}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-gray-500">{formatCompact(r.arr)}</span>
                      <span className="font-semibold" style={{ color: classifyColor(r.health_score) }}>{r.health_score}</span>
                      <span className={`font-medium ${r.days_until <= 30 ? 'text-red-400' : 'text-yellow-400'}`}>{r.days_until}d</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Highest Risk Accounts */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[10px] font-semibold tracking-[0.2em] text-gray-500 uppercase">
                Highest Risk Accounts
              </h2>
              <button
                onClick={() => handleViewChange('accounts')}
                className="text-xs text-cyan-500 hover:text-cyan-400 transition-colors flex items-center gap-1"
              >
                View all <ArrowRight className="w-3 h-3" />
              </button>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {d.risk_accounts.map((account) => (
                <RiskAccountCard
                  key={account.account_id}
                  account={account}
                  onClick={() => fetchTimeline(account.account_id)}
                  onDraftEmail={(a) => setEmailDraftAccount(a)}
                />
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* ---- Right Sidebar ---- */}
      <aside className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 overflow-y-auto flex flex-col gap-5">
        {/* Pending Decisions Queue — read-only v1 */}
        <PendingDecisionsQueue persona="cro" />

        {/* Power of 1 ROI Engine */}
        <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-xs font-semibold text-white">Power of 1 &middot; ROI Engine</h3>
            <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-purple-500/20 text-purple-400">
              Non-linear scaling
            </span>
          </div>

          {/* Big ROI number */}
          <div className="text-center py-4">
            <p className="text-5xl font-bold text-cyan-400 tracking-tight">
              {d.roi_summary.roi_pct}%
            </p>
            <p className="text-xs text-gray-500 mt-1">Estimated Portfolio ROI</p>
          </div>

          {/* Methodology badge */}
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg px-3 py-2 mb-3">
            <div className="flex items-start gap-2">
              <Info className="w-3 h-3 text-amber-400 mt-0.5 flex-shrink-0" />
              <p className="text-[10px] text-amber-300/80 leading-relaxed">
                Based on real pillar score improvements scaled with industry benchmarks (TSIA Research, Gainsight Pulse, KeyBanc SaaS Metrics). Investment and impact estimates are ARR-proportional projections, not actual cost tracking.
              </p>
            </div>
          </div>

          {/* Investment stats */}
          <div className="space-y-1.5 mb-4">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Estimated investment</span>
              <span className="text-gray-300 font-medium">{formatCompact(d.roi_summary.invested)}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Estimated impact</span>
              <span className="text-green-400 font-medium">
                {formatCompact(d.roi_summary.invested)} &rarr; {formatCompact(d.roi_summary.impact)}
              </span>
            </div>
          </div>

          {/* ROI scaling chart */}
          <div className="mb-3">
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">
              ROI scaling by volume
            </p>
            <ROIScalingChart data={d.roi_summary.scaling} />
          </div>

          {/* Footer tagline + citation */}
          <p className="text-[10px] text-gray-600 text-center italic">
            Same playbooks. Same platform. Non-linear returns.
          </p>
          <p className="text-[8px] text-gray-700 text-center mt-2 leading-relaxed">
            * Benchmarks: Gainsight Pulse 2024, TSIA CS Benchmark,
            KeyBanc SaaS Metrics Survey, Bain &amp; Co. NPS Economics.
            Dollar impacts are ARR-proportional projections scaled at 1% improvement.
          </p>
        </div>

        {/* Revenue Timeline */}
        <RevenueTimelineWidget timeline={timeline} loading={timelineLoading} />

        {/* Quick action link */}
        {/* ROI Engine link removed — sidebar widget shows key metrics */}
      </aside>

      {/* Floating AI Advisor */}
      <AskAIPortal persona="cro" />

      {/* Email Draft Modal — inline for CRO quick action */}
      {emailDraftAccount && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center" onClick={() => setEmailDraftAccount(null)}>
          <div className="bg-[#1a1f2e] rounded-xl border border-gray-700 w-full max-w-lg p-6 mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white">Draft Email — {emailDraftAccount.account_name}</h3>
              <button onClick={() => setEmailDraftAccount(null)} className="text-gray-500 hover:text-white" aria-label="Close">&times;</button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-gray-500 uppercase tracking-wide block mb-1">Subject</label>
                <input
                  defaultValue={`Account Health Review — ${emailDraftAccount.account_name} (Score: ${emailDraftAccount.health_score})`}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white"
                />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 uppercase tracking-wide block mb-1">Body</label>
                <textarea
                  rows={6}
                  defaultValue={`Hi team,\n\nI'd like to discuss ${emailDraftAccount.account_name} (${formatCompact(emailDraftAccount.arr)} ARR). Current health score is ${emailDraftAccount.health_score}, classified as ${classify(emailDraftAccount.health_score) === 'critical' ? 'Critical' : 'At Risk'}.\n\nKey concerns:\n- ${emailDraftAccount.signal_count} active signals flagged\n\nLet's schedule a review this week.\n\nBest regards`}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white resize-none"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button onClick={() => setEmailDraftAccount(null)} className="px-4 py-2 text-xs text-gray-400 hover:text-white transition-colors">Cancel</button>
                <button
                  onClick={() => { setEmailDraftAccount(null); }}
                  className="px-4 py-2 text-xs font-medium text-white bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors"
                >
                  Copy to Clipboard
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
    </div>
  );
};

export default CRODashboard;
