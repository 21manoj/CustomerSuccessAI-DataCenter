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

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell
} from 'recharts';
import {
  AlertTriangle, TrendingUp, TrendingDown, Shield, Zap,
  Target, DollarSign, Users, BarChart3, Clock,
  ChevronRight, Eye, Activity, GitBranch, Sparkles,
  ArrowRight, Briefcase
} from 'lucide-react';
import { classify, classifyColor, thresholdValues } from '../../utils/healthThresholds';
import { useSession } from '../../contexts/SessionContext';
import { apiCall, getCustomerIdentifier } from '../../utils/api';
import AskAnythingDialog from './AskAnythingDialog';

// Lazy-load sub-views
const SignalTimelineView = React.lazy(() => import('./views/SignalTimelineView'));
const ContextGraphView = React.lazy(() => import('./views/ContextGraphView'));
const ROIEngineView = React.lazy(() => import('./views/ROIEngineView'));
const AccountsView = React.lazy(() => import('./views/AccountsView'));

type ViewId = 'cro-overview' | 'signal-timeline' | 'context-graph' | 'roi-engine' | 'accounts' | 'playbooks' | 'approvals';

// ============================================================================
// TYPES
// ============================================================================

interface RevenueCard {
  label: string;
  amount: number;
  subtitle: string;
  account_count: number;
  accent: string;
}

interface MetricCard {
  label: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'flat';
  accent?: string;
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
  classification: 'critical' | 'at_risk';
  signal_count: number;
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
    { id: 'roi-engine' as ViewId, label: 'ROI Engine', badge: null, icon: <Zap className="w-4 h-4" /> },
  ],
  operations: [
    { id: 'accounts' as ViewId, label: 'Accounts', badge: null, icon: <Users className="w-4 h-4" /> },
    { id: 'playbooks' as ViewId, label: 'Playbooks', badge: null, icon: <Target className="w-4 h-4" /> },
    { id: 'approvals' as ViewId, label: 'Approvals', badge: null, icon: <Eye className="w-4 h-4" /> },
  ],
};

// Fallback data when API is unavailable
const FALLBACK_DATA: CRODashboardData = {
  revenue_cards: [
    { label: 'Revenue at Risk', amount: 4200000, subtitle: 'Causal evidence chains active', account_count: 23, accent: 'red' },
    { label: 'Revenue Protected', amount: 1800000, subtitle: 'Playbook interventions proven', account_count: 11, accent: 'green' },
    { label: 'Expansion Pipeline', amount: 2100000, subtitle: 'Stakeholder maps confirmed', account_count: 18, accent: 'cyan' },
  ],
  metrics: [
    { label: 'Avg Health Score', value: '71.4', change: '↓ 2.3 vs Q3', trend: 'down' },
    { label: 'Early Warning Lead', value: '67d', change: '↑ 12d vs Q3', trend: 'up' },
    { label: 'Playbook ROI', value: '294%', change: '↑ 41pp vs Q3', trend: 'up' },
    { label: 'NRR Projection', value: '118%', change: '↑ 5pp vs Q3', trend: 'up', accent: 'cyan' },
  ],
  story_arcs: [
    { id: 'arc_silent_churn', name: 'Silent Churn', icon: 'silent_churn', description: 'Usage declining without complaint signals', account_count: 8, revenue_impact: 1400000, impact_type: 'risk' },
    { id: 'arc_expansion', name: 'Expansion Champion', icon: 'expansion_champion', description: 'Multi-threaded stakeholder engagement growing', account_count: 12, revenue_impact: 2100000, impact_type: 'opportunity' },
    { id: 'arc_crisis', name: 'Crisis Recovery', icon: 'crisis_recovery', description: 'Active intervention reversing health decline', account_count: 5, revenue_impact: 890000, impact_type: 'recovery' },
    { id: 'arc_competitive', name: 'Competitive Displacement', icon: 'competitive_displacement', description: 'Competitor signals detected in accounts', account_count: 4, revenue_impact: 720000, impact_type: 'threat' },
    { id: 'arc_land_expand', name: 'Land & Expand', icon: 'land_and_expand', description: 'New accounts with expansion indicators', account_count: 9, revenue_impact: 1600000, impact_type: 'growth' },
  ],
  risk_accounts: [
    { account_id: 'A101', account_name: 'TechFlow Systems', health_score: 34, arr: 580000, classification: 'critical', signal_count: 7 },
    { account_id: 'A102', account_name: 'DataPrime Inc', health_score: 42, arr: 420000, classification: 'critical', signal_count: 5 },
    { account_id: 'A103', account_name: 'CloudScale Corp', health_score: 28, arr: 890000, classification: 'critical', signal_count: 9 },
    { account_id: 'A104', account_name: 'NetVault Solutions', health_score: 55, arr: 340000, classification: 'at_risk', signal_count: 4 },
    { account_id: 'A105', account_name: 'Meridian Analytics', health_score: 61, arr: 270000, classification: 'at_risk', signal_count: 3 },
    { account_id: 'A106', account_name: 'Apex Infrastructure', health_score: 38, arr: 1200000, classification: 'critical', signal_count: 8 },
  ],
  roi_summary: {
    roi_pct: 294,
    invested: 578000,
    impact: 2280000,
    scaling: [
      { accounts: 10, label: '10 accts', roi: 294 },
      { accounts: 50, label: '50 accts', roi: 717 },
      { accounts: 200, label: '200 accts', roi: 1114 },
    ],
  },
  period: 'Q1 2026',
  last_updated: '2m ago',
};

const FALLBACK_TIMELINE: RevenueTimeline = {
  account_name: 'Apex Infrastructure',
  arr: 1200000,
  events: [
    { month: 'OCT', date: '2025-10-03', type: 'signal', color: 'yellow', title: 'Usage Decline Detected', description: 'API call volume dropped 34% over 2 weeks' },
    { month: 'OCT', date: '2025-10-15', type: 'signal', color: 'red', title: 'Champion Contact Left', description: 'VP Engineering role changed on LinkedIn' },
    { month: 'NOV', date: '2025-11-02', type: 'intervention', color: 'cyan', title: 'EBR Scheduled', description: 'CSM triggered executive business review' },
    { month: 'NOV', date: '2025-11-18', type: 'intervention', color: 'green', title: 'Playbook PB-03 Activated', description: 'Stakeholder re-engagement playbook launched' },
    { month: 'DEC', date: '2025-12-05', type: 'outcome', color: 'green', title: 'New Champion Identified', description: 'CTO engaged, usage recovery began' },
    { month: 'DEC', date: '2025-12-20', type: 'outcome', color: 'green', title: 'Renewal Confirmed', description: '$1.2M ARR renewed with 8% expansion' },
  ],
};

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

/** Large revenue card */
const RevenueCardComponent: React.FC<{ card: RevenueCard }> = ({ card }) => {
  const accent = ACCENT_MAP[card.accent] || '#06b6d4';
  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 relative overflow-hidden group hover:border-gray-600/50 transition-all">
      {/* Accent bar */}
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ backgroundColor: accent }} />
      {/* Glow effect */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-16 opacity-10 blur-2xl"
        style={{ backgroundColor: accent }}
      />
      <div className="relative">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">{card.label}</p>
        <p className="text-3xl font-bold text-white mb-1" style={{ color: accent }}>
          {formatCompact(card.amount)}
        </p>
        <p className="text-xs text-gray-500 mb-3">{card.subtitle}</p>
        <div className="flex items-center gap-1 text-xs text-gray-400">
          <Users className="w-3 h-3" />
          <span>{card.account_count} accounts</span>
        </div>
      </div>
    </div>
  );
};

/** Small metric card */
const MetricCardComponent: React.FC<{ metric: MetricCard }> = ({ metric }) => {
  const isUp = metric.trend === 'up';
  const TrendIcon = isUp ? TrendingUp : TrendingDown;
  const trendColor = isUp ? 'text-green-400' : 'text-red-400';
  const accent = metric.accent ? ACCENT_MAP[metric.accent] : undefined;

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4 hover:border-gray-600/50 transition-all">
      <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">{metric.label}</p>
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

/** Risk account card */
const RiskAccountCard: React.FC<{ account: RiskAccount; onClick: () => void }> = ({ account, onClick }) => {
  const { healthy_min, at_risk_min } = thresholdValues();
  const cls = classify(account.health_score);
  const color = classifyColor(account.health_score);
  const barWidth = Math.max(5, Math.min(100, account.health_score));

  return (
    <button
      onClick={onClick}
      className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4 hover:border-gray-600/50 transition-all text-left group w-full"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-white truncate">{account.account_name}</p>
          <p className="text-xs text-gray-500">{formatCompact(account.arr)} ARR</p>
        </div>
        <span
          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full flex-shrink-0 ml-2 ${
            cls === 'critical' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
          }`}
        >
          {cls === 'critical' ? 'Critical' : 'At Risk'}
        </span>
      </div>
      {/* Health bar */}
      <div className="mb-2">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-500">Health Score</span>
          <span className="text-xs font-semibold" style={{ color }}>{account.health_score}</span>
        </div>
        <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${barWidth}%`,
              background: `linear-gradient(90deg, ${color}, ${color}88)`,
            }}
          />
        </div>
      </div>
      <div className="flex items-center gap-1 text-xs text-gray-500">
        <AlertTriangle className="w-3 h-3" />
        <span>{account.signal_count} active signals</span>
      </div>
    </button>
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

  if (!timeline) return null;

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

  const [timeline, setTimeline] = useState<RevenueTimeline | null>(FALLBACK_TIMELINE);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [selectedAccountId, setSelectedAccountId] = useState<string | number | null>(null);

  const [activePeriod, setActivePeriod] = useState<'Q3' | 'Q4' | 'TTM'>('Q4');

  // Update URL when view changes
  const handleViewChange = useCallback((view: ViewId) => {
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
        if (!resp.ok) throw new Error(`API returned ${resp.status}`);
        const json = await resp.json();
        if (!cancelled) {
          // Transform flat API response into CRODashboardData shape
          const transformed: CRODashboardData = {
            revenue_cards: [
              { label: 'Revenue at Risk', amount: json.revenue_at_risk || 0, subtitle: 'Causal evidence chains active', account_count: json.accounts_at_risk_count || 0, accent: 'red' },
              { label: 'Revenue Protected', amount: json.revenue_protected || 0, subtitle: 'Playbook interventions proven', account_count: json.accounts_recovered_count || 0, accent: 'green' },
              { label: 'Expansion Pipeline', amount: json.expansion_pipeline || 0, subtitle: 'Stakeholder maps confirmed', account_count: json.expansion_candidates_count || 0, accent: 'cyan' },
            ],
            metrics: [
              { label: 'Avg Health Score', value: (json.avg_health_score || 0).toFixed(1), change: `${json.health_score_change >= 0 ? '↑' : '↓'} ${Math.abs(json.health_score_change || 0).toFixed(1)} vs Q3`, trend: json.health_score_change >= 0 ? 'up' : 'down' },
              { label: 'Early Warning Lead', value: `${json.early_warning_days || 0}d`, change: '↑ 12d vs Q3', trend: 'up' },
              { label: 'Playbook ROI', value: `${json.playbook_roi_pct || 0}%`, change: `↑ 41pp vs Q3`, trend: 'up' },
              { label: 'NRR Projection', value: `${json.nrr_projection || 100}%`, change: `↑ ${json.nrr_change || 0}pp vs Q3`, trend: 'up', accent: 'cyan' },
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
            risk_accounts: (json.highest_risk_accounts || []).map((a: any) => ({
              account_id: a.account_id,
              account_name: a.account_name,
              health_score: a.health_score || 0,
              arr: a.revenue || a.arr || 0,
              classification: (a.health_score || 0) < 50 ? 'critical' as const : 'at_risk' as const,
              signal_count: a.signal_count || 0,
            })),
            roi_summary: {
              roi_pct: json.playbook_roi_pct || 0,
              invested: json.cs_investment || 578000,
              impact: (json.cs_investment || 578000) * (1 + (json.playbook_roi_pct || 294) / 100),
              scaling: [
                { accounts: 10, label: '10 accts', roi: json.playbook_roi_pct || 294 },
                { accounts: 50, label: '50 accts', roi: Math.round((json.playbook_roi_pct || 294) * 2.44) },
                { accounts: 200, label: '200 accts', roi: Math.round((json.playbook_roi_pct || 294) * 3.79) },
              ],
            },
            period: json.quarter_label || 'Q1 2026',
            last_updated: json.last_updated || new Date().toISOString(),
          };
          setData(transformed);
        }
      } catch {
        // Use fallback data when API is unavailable
        if (!cancelled) {
          setData(FALLBACK_DATA);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchData();
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
      if (!resp.ok) throw new Error(`API returned ${resp.status}`);
      const json = await resp.json();
      setTimeline(json);
    } catch {
      // Keep existing timeline on error
    } finally {
      setTimelineLoading(false);
    }
  }, [session]);

  const handleNav = useCallback((path: string) => {
    navigate(path);
  }, [navigate]);

  // Sidebar badge data
  const accountCount = data?.risk_accounts?.length || 0;
  const signalCount = data?.story_arcs?.reduce((s, a) => s + (a.account_count || 0), 0) || 0;
  const roiPct = data?.roi_summary?.roi_pct || 0;

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

  // ---- Error state ----
  if (error && !data) {
    return (
      <div className="flex h-screen bg-[#0f1419] text-white font-['Inter',sans-serif] items-center justify-center">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Unable to Load Dashboard</h2>
          <p className="text-gray-400 text-sm mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-cyan-600 text-white rounded-lg text-sm hover:bg-cyan-500 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const d = data!;

  return (
    <div className="flex h-screen bg-[#0f1419] text-white font-['Inter',sans-serif]">
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
                <span className="text-gray-500 font-normal ml-2">&middot; {d.period}</span>
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
                  onClick={() => setActivePeriod(p)}
                  className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                    activePeriod === p
                      ? 'bg-white/10 text-white'
                      : 'text-gray-500 hover:text-gray-300'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Row 1: Revenue cards */}
          <div className="grid grid-cols-3 gap-4 mb-4">
            {d.revenue_cards.map((card, i) => (
              <RevenueCardComponent key={i} card={card} />
            ))}
          </div>

          {/* Row 2: Metric cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            {d.metrics.map((m, i) => (
              <MetricCardComponent key={i} metric={m} />
            ))}
          </div>

          {/* Story Arcs */}
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
                  onClick={() => handleViewChange('context-graph')}
                />
              ))}
            </div>
          </div>

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
                />
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* ---- Right Sidebar ---- */}
      <aside className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 overflow-y-auto flex flex-col gap-5">
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
            <p className="text-xs text-gray-500 mt-1">Portfolio ROI</p>
          </div>

          {/* Investment stats */}
          <div className="space-y-1.5 mb-4">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Historical investment</span>
              <span className="text-gray-300 font-medium">{formatCompact(d.roi_summary.invested)}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Impact generated</span>
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

          {/* Footer tagline */}
          <p className="text-[10px] text-gray-600 text-center italic">
            Same playbooks. Same platform. Non-linear returns.
          </p>
        </div>

        {/* Revenue Timeline */}
        <RevenueTimelineWidget timeline={timeline} loading={timelineLoading} />

        {/* Quick action link */}
        <button
          onClick={() => handleViewChange('roi-engine')}
          className="flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-cyan-600/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium hover:bg-cyan-600/20 transition-colors"
        >
          <Zap className="w-3.5 h-3.5" />
          Open ROI Engine
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </aside>

      {/* Floating AI Advisor */}
      <AskAnythingDialog persona="cro" />
    </div>
  );
};

export default CRODashboard;
