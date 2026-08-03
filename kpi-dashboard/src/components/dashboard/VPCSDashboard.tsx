/**
 * VP Customer Success — Team Performance Dashboard
 * ==================================================
 *
 * Dark-themed executive dashboard for VP of Customer Success featuring:
 * - Total Accounts / Avg Health Score / Playbook Completion / Renewals cards
 * - Account Health Distribution (Healthy / At-Risk / Critical buckets)
 * - Active Playbooks / Actions Queue table
 * - Account Portfolio Table (sorted by health ascending)
 * - Team Capacity gauge, Renewal Pipeline, Quick Stats (right sidebar)
 * - Navigation links to CSM View and CRO View
 *
 * Accent color: TEAL (#14B8A6)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell
} from 'recharts';
import {
  AlertTriangle, TrendingUp, TrendingDown, Minus, Shield, Zap,
  Target, Users, BarChart3, Clock,
  ChevronRight, Eye, Activity, GitBranch, Sparkles,
  ArrowRight, ArrowUpRight, Briefcase, CheckCircle2,
  Calendar, Timer, PlayCircle, ClipboardList, UserCheck,
  Gauge, RefreshCcw
} from 'lucide-react';
import { classify, classifyColor, thresholdValues } from '../../utils/healthThresholds';
import DashboardTopBar from './DashboardTopBar';
import NavLogoutButton from '../shared/NavLogoutButton';
import { useSession } from '../../contexts/SessionContext';
import { apiCall, getCustomerIdentifier } from '../../utils/api';
import { trackPageView, trackDashboardSwitch } from '../../utils/activityTracker';
import AskAIPortal from '../ai/AskAIPortal';
import { DashboardErrorState } from '../shared/DashboardErrorState';
import {
  VPCSMetricGuideBanner,
  VPCSPreProofBanner,
  VPCSContextGraphStrip,
  VPCSCapacityPlanningPanel,
  type CustomerPhase,
  type CapacityPlanningData,
  type UncoveredAccount,
} from './VPCSOverviewHonesty';

// ============================================================================
// TYPES
// ============================================================================

interface SummaryCard {
  label: string;
  value: string;
  subtitle: string;
  tag?: string;
  accent: string;
  icon: React.ReactNode;
}

interface HealthBucket {
  label: string;
  count: number;
  pct: number;
  arr: number;
  color: string;
  bgClass: string;
  textClass: string;
}

interface ActionItem {
  priority: number;
  account_name: string;
  assigned_csm?: string;
  action: string;
  urgency: 'critical' | 'high' | 'medium' | 'low';
  est_hours: number;
  impact_dollars: number;
  playbook?: string;
}

interface AccountRow {
  account_id: string | number;
  account_name: string;
  assigned_csm?: string;
  health_score: number;
  arr: number;
  industry: string;
  region: string;
  last_signal: string;
  classification: string;
  renewal_date?: string;
}

interface RenewalItem {
  account_name: string;
  arr: number;
  days_until: number;
  health_score: number;
}

interface CSMScorecard {
  csm_name: string;
  accounts_managed: number;
  total_arr: number;
  avg_health_delta: number;
  accounts_improving: number;
  accounts_declining: number;
  playbooks_executed: number;
  playbooks_resolved: number;
  success_rate_pct: number;
  revenue_protected: number;
  revenue_expanded: number;
  total_revenue_impact: number;
}

interface HealthHistoryAccount {
  account_id: number;
  account_name: string;
  arr: number;
  current_health: number;
  current_status: string;
  net_change: number;
  trajectory: string;
  monthly_scores: Array<{ month: string; health_score: number; status: string }>;
}

interface PlaybookMetric {
  playbook_id: string;
  total_executions: number;
  resolved: number;
  escalated: number;
  timeout: number;
  success_rate_pct: number;
  avg_health_delta: number;
  total_revenue_protected: number;
  total_revenue_expanded: number;
}

interface RevenueSummary {
  revenue_at_risk: number;
  revenue_protected: number;
  expansion_pipeline: number;
  total_arr: number;
}

interface VPCSDashboardData {
  summary_cards: SummaryCard[];
  health_buckets: HealthBucket[];
  actions: ActionItem[];
  accounts: AccountRow[];
  renewals_90d: RenewalItem[];
  renewal_count_90d: number;
  renewal_arr_90d: number;
  team_capacity: {
    accounts_per_csm: number;
    target_per_csm: number;
    csm_count: number;
    per_csm_breakdown: Array<{
      csm_name: string;
      accounts_managed: number;
      total_arr: number;
      active_playbooks: number;
      hours_committed: number;
      hours_available: number;
      utilization_pct: number;
      at_risk_accounts: number;
    }>;
    // Hours-based resource-pool view (from PR-29 backend enrichment).
    // Optional so the dashboard still renders against an older API build.
    total_hours_available?: number;
    total_hours_planned?: number;
    total_hours_utilization_pct?: number;
    total_fte?: number;
    total_annual_cost?: number;
    feasible?: boolean;
    bottleneck_roles?: string[];
    recommendation?: string;
    active_playbooks?: number;
  };
  quick_stats: {
    avg_resolution_days: number;
    playbook_success_rate: number;
    nps_score: number;
    actions_completed_pct: number;
  };
  csm_scorecards: CSMScorecard[];
  health_history_accounts: HealthHistoryAccount[];
  portfolio_trajectory: {
    improving_count: number;
    declining_count: number;
    stable_count: number;
    improving_arr_pct: number;
    declining_arr_pct: number;
  };
  playbook_metrics: PlaybookMetric[];
  revenue_summary: RevenueSummary | null;
  capacity_planning: CapacityPlanningData | null;
  uncovered_at_risk: UncoveredAccount[];
  customer_phase: CustomerPhase;
  proof_executions_total: number;
  proof_realized_roi: number;
  period: string;
  last_updated: string;
  is_live_data: boolean;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const TEAL = '#14B8A6';
const TEAL_LIGHT = '#2dd4bf';

const ACCENT_MAP: Record<string, string> = {
  teal: '#14B8A6',
  white: '#ffffff',
  green: '#22c55e',
  cyan: '#06b6d4',
  red: '#ef4444',
  yellow: '#eab308',
  purple: '#a855f7',
  orange: '#f97316',
  emerald: '#10b981',
};

const URGENCY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  critical: { bg: 'bg-red-500/20', text: 'text-red-400', label: 'Critical' },
  high: { bg: 'bg-orange-500/20', text: 'text-orange-400', label: 'High' },
  medium: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', label: 'Medium' },
  low: { bg: 'bg-gray-500/20', text: 'text-gray-400', label: 'Low' },
};

type VPCSViewId = 'vpcs-overview' | 'accounts' | 'playbooks' | 'renewals' | 'health-trends' | 'team-metrics';

// Sidebar navigation items — view switching within the dashboard
const NAV_ITEMS = {
  management: [
    { id: 'vpcs-overview' as VPCSViewId, label: 'Team Overview', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'accounts' as VPCSViewId, label: 'All Accounts', icon: <Users className="w-4 h-4" /> },
    { id: 'playbooks' as VPCSViewId, label: 'Playbooks', icon: <Target className="w-4 h-4" /> },
    { id: 'renewals' as VPCSViewId, label: 'Renewals', icon: <Calendar className="w-4 h-4" /> },
  ],
  insights: [
    { id: 'health-trends' as VPCSViewId, label: 'Health Trends', icon: <Activity className="w-4 h-4" /> },
    { id: 'team-metrics' as VPCSViewId, label: 'Team Metrics', icon: <Gauge className="w-4 h-4" /> },
  ],
};

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

// ============================================================================
// FALLBACK DATA
// ============================================================================

const FALLBACK_DATA: VPCSDashboardData = {
  summary_cards: [
    { label: 'Total Accounts', value: '15', subtitle: 'Across 3 CSMs', accent: 'white', icon: <Users className="w-4 h-4" /> },
    { label: 'Avg Health Score', value: '71.4', subtitle: 'Portfolio weighted avg', accent: 'teal', icon: <Activity className="w-4 h-4" /> },
    { label: 'Playbook Completion', value: '68%', subtitle: '24 of 35 actions done', tag: 'On track', accent: 'green', icon: <CheckCircle2 className="w-4 h-4" /> },
    { label: 'Renewals This Qtr', value: '6', subtitle: '$8.4M ARR renewing', accent: 'cyan', icon: <Calendar className="w-4 h-4" /> },
  ],
  health_buckets: [
    { label: 'Healthy', count: 8, pct: 53, arr: 12400000, color: '#22c55e', bgClass: 'bg-green-500/10', textClass: 'text-green-400' },
    { label: 'At-Risk', count: 4, pct: 27, arr: 5800000, color: '#eab308', bgClass: 'bg-yellow-500/10', textClass: 'text-yellow-400' },
    { label: 'Critical', count: 3, pct: 20, arr: 3000000, color: '#ef4444', bgClass: 'bg-red-500/10', textClass: 'text-red-400' },
  ],
  actions: [
    { priority: 1, account_name: 'Apex Infrastructure', action: 'Executive business review — renewal at risk', urgency: 'critical', est_hours: 4, impact_dollars: 1200000, playbook: 'PB-01' },
    { priority: 2, account_name: 'CloudScale Corp', action: 'Stakeholder re-engagement after champion loss', urgency: 'critical', est_hours: 3, impact_dollars: 890000, playbook: 'PB-03' },
    { priority: 3, account_name: 'TechFlow Systems', action: 'Usage adoption workshop — declining API calls', urgency: 'high', est_hours: 2.5, impact_dollars: 580000, playbook: 'PB-04' },
    { priority: 4, account_name: 'DataPrime Inc', action: 'Health check call — score dropped below 50', urgency: 'high', est_hours: 1.5, impact_dollars: 420000, playbook: 'PB-02' },
    { priority: 5, account_name: 'NetVault Solutions', action: 'QBR preparation and scheduling', urgency: 'medium', est_hours: 2, impact_dollars: 340000, playbook: 'PB-05' },
    { priority: 6, account_name: 'Meridian Analytics', action: 'Feature adoption follow-up', urgency: 'medium', est_hours: 1, impact_dollars: 270000, playbook: 'PB-04' },
    { priority: 7, account_name: 'Summit Hosting', action: 'Expansion opportunity review', urgency: 'medium', est_hours: 2, impact_dollars: 450000, playbook: 'PB-06' },
    { priority: 8, account_name: 'Pinnacle DC', action: 'Onboarding milestone check-in', urgency: 'low', est_hours: 1, impact_dollars: 320000 },
    { priority: 9, account_name: 'Horizon Cloud', action: 'NPS follow-up action items', urgency: 'low', est_hours: 0.5, impact_dollars: 180000 },
    { priority: 10, account_name: 'Catalyst Systems', action: 'Monthly health review', urgency: 'low', est_hours: 1, impact_dollars: 240000 },
  ],
  accounts: [
    { account_id: 'A103', account_name: 'CloudScale Corp', health_score: 28, arr: 890000, industry: 'Technology', region: 'West', last_signal: 'Champion loss detected', classification: 'critical' },
    { account_id: 'A101', account_name: 'TechFlow Systems', health_score: 34, arr: 580000, industry: 'Financial Services', region: 'East', last_signal: 'Usage decline 34%', classification: 'critical' },
    { account_id: 'A106', account_name: 'Apex Infrastructure', health_score: 38, arr: 1200000, industry: 'Healthcare', region: 'Central', last_signal: 'Renewal risk flagged', classification: 'critical' },
    { account_id: 'A102', account_name: 'DataPrime Inc', health_score: 42, arr: 420000, industry: 'Retail', region: 'East', last_signal: 'Support tickets spike', classification: 'at_risk' },
    { account_id: 'A104', account_name: 'NetVault Solutions', health_score: 55, arr: 340000, industry: 'Manufacturing', region: 'Central', last_signal: 'QBR overdue', classification: 'at_risk' },
    { account_id: 'A105', account_name: 'Meridian Analytics', health_score: 61, arr: 270000, industry: 'Technology', region: 'West', last_signal: 'Low feature adoption', classification: 'at_risk' },
    { account_id: 'A110', account_name: 'Summit Hosting', health_score: 64, arr: 450000, industry: 'Media', region: 'West', last_signal: 'Expansion signal', classification: 'at_risk' },
    { account_id: 'A107', account_name: 'Pinnacle DC', health_score: 72, arr: 320000, industry: 'Technology', region: 'East', last_signal: 'Onboarding on track', classification: 'healthy' },
    { account_id: 'A108', account_name: 'Horizon Cloud', health_score: 76, arr: 180000, industry: 'Education', region: 'Central', last_signal: 'NPS score: 8', classification: 'healthy' },
    { account_id: 'A109', account_name: 'Catalyst Systems', health_score: 78, arr: 240000, industry: 'Financial Services', region: 'East', last_signal: 'Stable usage', classification: 'healthy' },
    { account_id: 'A111', account_name: 'Vanguard Hosting', health_score: 82, arr: 680000, industry: 'Healthcare', region: 'West', last_signal: 'Active champion', classification: 'healthy' },
    { account_id: 'A112', account_name: 'Zenith Networks', health_score: 85, arr: 520000, industry: 'Telecom', region: 'Central', last_signal: 'Feature rollout success', classification: 'healthy' },
    { account_id: 'A113', account_name: 'Atlas Computing', health_score: 88, arr: 410000, industry: 'Technology', region: 'East', last_signal: 'Expansion in pipeline', classification: 'healthy' },
    { account_id: 'A114', account_name: 'Nova Enterprises', health_score: 91, arr: 780000, industry: 'Manufacturing', region: 'Central', last_signal: 'Renewal confirmed', classification: 'healthy' },
    { account_id: 'A115', account_name: 'Stellar Infrastructure', health_score: 94, arr: 920000, industry: 'Financial Services', region: 'West', last_signal: 'NPS score: 10', classification: 'healthy' },
  ],
  renewals_90d: [
    { account_name: 'Apex Infrastructure', arr: 1200000, days_until: 22, health_score: 38 },
    { account_name: 'Zenith Networks', arr: 520000, days_until: 35, health_score: 85 },
    { account_name: 'Nova Enterprises', arr: 780000, days_until: 48, health_score: 91 },
    { account_name: 'NetVault Solutions', arr: 340000, days_until: 61, health_score: 55 },
    { account_name: 'Catalyst Systems', arr: 240000, days_until: 75, health_score: 78 },
    { account_name: 'Stellar Infrastructure', arr: 920000, days_until: 88, health_score: 94 },
  ],
  renewal_count_90d: 6,
  renewal_arr_90d: 4000000,
  team_capacity: {
    accounts_per_csm: 5,
    target_per_csm: 6,
    csm_count: 3,
    per_csm_breakdown: [],
  },
  quick_stats: {
    avg_resolution_days: 4.2,
    playbook_success_rate: 73,
    nps_score: 42,
    actions_completed_pct: 68,
  },
  csm_scorecards: [],
  health_history_accounts: [],
  portfolio_trajectory: { improving_count: 0, declining_count: 0, stable_count: 0, improving_arr_pct: 0, declining_arr_pct: 0 },
  playbook_metrics: [],
  revenue_summary: null,
  capacity_planning: null,
  uncovered_at_risk: [],
  customer_phase: 'active',
  proof_executions_total: 0,
  proof_realized_roi: 0,
  period: 'Q1 2026',
  last_updated: '2m ago',
  is_live_data: false,
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

/** Left sidebar navigation — view switching within dashboard */
const SidebarNav: React.FC<{
  activeId: VPCSViewId;
  onViewChange: (id: VPCSViewId) => void;
  onNavigate: (path: string) => void;
  accountCount?: number;
  actionCount?: number;
}> = ({ activeId, onViewChange, onNavigate, accountCount, actionCount }) => {
  const getBadge = (id: string): string | null => {
    if (id === 'accounts' && accountCount) return String(accountCount);
    if (id === 'playbooks' && actionCount) return String(actionCount);
    return null;
  };

  return (
    <aside className="w-48 flex-shrink-0 bg-[#0d1117] border-r border-gray-700/50 py-6 px-3 flex flex-col gap-6 overflow-y-auto">
      {/* Management section */}
      <div>
        <h3 className="text-[10px] font-semibold tracking-[0.2em] text-gray-500 uppercase mb-3 px-2">Management</h3>
        <nav className="flex flex-col gap-0.5">
          {NAV_ITEMS.management.map((item) => {
            const isActive = item.id === activeId;
            const badge = getBadge(item.id);
            return (
              <button
                key={item.id}
                onClick={() => onViewChange(item.id)}
                className={`flex items-center gap-2 px-2 py-2 rounded-lg text-sm transition-all group w-full text-left ${
                  isActive
                    ? 'bg-teal-500/10 text-teal-400'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <span className={isActive ? 'text-teal-400' : 'text-gray-500 group-hover:text-gray-300'}>
                  {item.icon}
                </span>
                <span className="flex-1 truncate">{item.label}</span>
                {badge && (
                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                    isActive ? 'bg-teal-500/20 text-teal-400' : 'bg-gray-700/50 text-gray-400'
                  }`}>
                    {badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Insights section */}
      <div>
        <h3 className="text-[10px] font-semibold tracking-[0.2em] text-gray-500 uppercase mb-3 px-2">Insights</h3>
        <nav className="flex flex-col gap-0.5">
          {NAV_ITEMS.insights.map((item) => {
            const isActive = item.id === activeId;
            return (
              <button
                key={item.id}
                onClick={() => onViewChange(item.id)}
                className={`flex items-center gap-2 px-2 py-2 rounded-lg text-sm transition-all group w-full text-left ${
                  isActive
                    ? 'bg-teal-500/10 text-teal-400'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <span className={isActive ? 'text-teal-400' : 'text-gray-500 group-hover:text-gray-300'}>
                  {item.icon}
                </span>
                <span className="flex-1 truncate">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Cross-dashboard links */}
      <div className="px-2 pt-2">
        <div className="h-px bg-gray-700/30 mb-3" />
        <button
          onClick={() => onNavigate('/dc-dashboard/csm')}
          className="flex items-center gap-2 px-2 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-all group w-full text-left"
        >
          <ClipboardList className="w-4 h-4 text-gray-500 group-hover:text-gray-300" />
          <span className="flex-1 truncate">CSM View</span>
          <ArrowRight className="w-3 h-3 text-gray-600" />
        </button>
        <button
          onClick={() => onNavigate('/cro-dashboard')}
          className="flex items-center gap-2 px-2 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-all group w-full text-left"
        >
          <Briefcase className="w-4 h-4 text-gray-500 group-hover:text-gray-300" />
          <span className="flex-1 truncate">CRO View</span>
          <ArrowRight className="w-3 h-3 text-gray-600" />
        </button>
      </div>

      <div className="mt-auto px-2 pt-4 border-t border-gray-700/30 space-y-2">
        <NavLogoutButton variant="dark-sidebar" />
        <div className="text-[10px] text-gray-600 leading-relaxed pt-2 border-t border-gray-700/30">
          CS Pulse<br />
          Team Performance
        </div>
      </div>
    </aside>
  );
};

/** Summary card with icon */
const SummaryCardComponent: React.FC<{ card: SummaryCard }> = ({ card }) => {
  const accent = ACCENT_MAP[card.accent] || TEAL;
  const isHighlight = card.accent === 'teal' || card.accent === 'cyan';
  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 relative overflow-hidden group hover:border-gray-600/50 transition-all">
      {/* Accent bar */}
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ backgroundColor: accent }} />
      {/* Glow effect */}
      {isHighlight && (
        <div
          className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-16 opacity-10 blur-2xl"
          style={{ backgroundColor: accent }}
        />
      )}
      <div className="relative">
        <div className="flex items-center gap-2 mb-1">
          <span style={{ color: accent }}>{card.icon}</span>
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">{card.label}</p>
        </div>
        <p className="text-3xl font-bold mb-1" style={{ color: accent }}>
          {card.value}
        </p>
        <p className="text-xs text-gray-500 mb-1">{card.subtitle}</p>
        {card.tag && (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-teal-500/15 text-teal-400 mt-1">
            <Sparkles className="w-3 h-3" />
            {card.tag}
          </span>
        )}
      </div>
    </div>
  );
};

/** Health distribution section — 3 buckets */
const HealthDistribution: React.FC<{ buckets: HealthBucket[]; onBucketClick?: (label: string) => void }> = ({ buckets, onBucketClick }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
    <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Shield className="w-4 h-4 text-teal-400" />
        <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
          Account Health Distribution
        </h3>
      </div>
      <span className="text-[10px] text-gray-500">
        {buckets.reduce((s, b) => s + b.count, 0)} total accounts
      </span>
    </div>
    <div className="grid grid-cols-3 divide-x divide-gray-700/50">
      {buckets.map((bucket) => (
        <div
          key={bucket.label}
          className={`p-5 ${bucket.bgClass} relative overflow-hidden ${onBucketClick ? 'cursor-pointer hover:brightness-110 transition-all' : ''}`}
          onClick={() => onBucketClick?.(bucket.label)}
          role={onBucketClick ? 'button' : undefined}
          tabIndex={onBucketClick ? 0 : undefined}
          aria-label={`${bucket.label}: ${bucket.count} accounts, ${formatCompact(bucket.arr)} ARR`}
          onKeyDown={(e) => { if (e.key === 'Enter' && onBucketClick) onBucketClick(bucket.label); }}
        >
          {/* Glow */}
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-24 h-12 opacity-10 blur-2xl"
            style={{ backgroundColor: bucket.color }}
          />
          <div className="relative text-center">
            <p className={`text-xs font-semibold uppercase tracking-wide mb-3 ${bucket.textClass}`}>
              {bucket.label}
            </p>
            <p className="text-4xl font-bold text-white mb-1">{bucket.count}</p>
            <p className="text-xs text-gray-500 mb-3">{bucket.pct}% of portfolio</p>
            {/* ARR bar */}
            <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden mb-2">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${Math.min(100, bucket.pct * 1.5)}%`,
                  backgroundColor: bucket.color,
                }}
              />
            </div>
            <p className="text-sm font-semibold" style={{ color: bucket.color }}>
              {formatCompact(bucket.arr)}
            </p>
            <p className="text-[10px] text-gray-600">ARR in bucket</p>
          </div>
        </div>
      ))}
    </div>
  </div>
);

/** Actions Queue table */
const ActionsQueueTable: React.FC<{ actions: ActionItem[] }> = ({ actions }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
    <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <PlayCircle className="w-4 h-4 text-teal-400" />
        <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
          Active Playbooks &middot; Actions Queue
        </h3>
      </div>
      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-teal-500/15 text-teal-400">
        {actions.length} actions
      </span>
    </div>
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700/50">
            <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider w-12">#</th>
            <th className="text-left px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Account</th>
            <th className="text-left px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">CSM</th>
            <th className="text-left px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Action</th>
            <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Urgency</th>
            <th className="text-right px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Est. Hrs</th>
            <th className="text-right px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Impact $</th>
          </tr>
        </thead>
        <tbody>
          {actions.map((action, i) => {
            const urgency = URGENCY_STYLES[action.urgency] || URGENCY_STYLES.low;
            return (
              <tr key={i} className="border-b border-gray-700/30 hover:bg-white/[0.02] transition-colors">
                <td className="text-center px-3 py-3">
                  <span className="text-xs font-bold text-gray-500">{action.priority}</span>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs font-medium text-white">{action.account_name}</span>
                </td>
                <td className="px-3 py-3 text-xs text-gray-400 max-w-[88px] truncate">
                  {action.assigned_csm || '—'}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-300 leading-tight max-w-[280px] truncate">{action.action}</span>
                    {action.playbook && (
                      <span className="text-[9px] font-mono font-medium px-1.5 py-0.5 rounded bg-gray-700/50 text-gray-400 flex-shrink-0">
                        {action.playbook}
                      </span>
                    )}
                  </div>
                </td>
                <td className="text-center px-3 py-3">
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${urgency.bg} ${urgency.text}`}>
                    {urgency.label}
                  </span>
                </td>
                <td className="text-right px-3 py-3 text-xs text-gray-400 font-mono">
                  {action.est_hours}h
                </td>
                <td className="text-right px-5 py-3 text-xs text-teal-400 font-semibold font-mono">
                  {formatCompact(action.impact_dollars)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  </div>
);

/** Account portfolio table */
const AccountPortfolioTable: React.FC<{ accounts: AccountRow[] }> = ({ accounts }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
    <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Users className="w-4 h-4 text-teal-400" />
        <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
          Account Portfolio
        </h3>
      </div>
      <span className="text-[10px] text-gray-500">Sorted by health (worst first)</span>
    </div>
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700/50">
            <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Account</th>
            <th className="text-left px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">CSM</th>
            <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider w-32">Health</th>
            <th className="text-right px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">ARR</th>
            <th className="text-left px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Industry</th>
            <th className="text-left px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Region</th>
            <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Last Signal</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((acct, i) => {
            const color = classifyColor(acct.health_score);
            const cls = classify(acct.health_score);
            const barWidth = Math.max(5, Math.min(100, acct.health_score));
            return (
              <tr
                key={acct.account_id}
                className="border-b border-gray-700/30 hover:bg-white/[0.02] transition-colors cursor-pointer group"
              >
                <td className="px-5 py-3">
                  <span className="text-xs font-medium text-white group-hover:text-teal-400 transition-colors">
                    {acct.account_name}
                  </span>
                </td>
                <td className="px-3 py-3 text-xs text-gray-400 max-w-[96px] truncate">
                  {acct.assigned_csm || '—'}
                </td>
                <td className="px-3 py-3">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${barWidth}%`,
                          background: `linear-gradient(90deg, ${color}, ${color}88)`,
                        }}
                      />
                    </div>
                    <span className="text-xs font-semibold w-7 text-right" style={{ color }}>
                      {acct.health_score}
                    </span>
                  </div>
                </td>
                <td className="text-right px-4 py-3 text-xs text-gray-300 font-mono">
                  {formatCompact(acct.arr)}
                </td>
                <td className="px-4 py-3 text-xs text-gray-500">{acct.industry}</td>
                <td className="px-4 py-3 text-xs text-gray-500">{acct.region}</td>
                <td className="px-5 py-3 text-xs text-gray-400 truncate max-w-[180px]">{acct.last_signal}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  </div>
);

/** Team Capacity gauge (right sidebar).
 *
 * Hours-based utilization view (PR-29). Reads the resource-pool aggregate
 * exposed by /api/v1/team-capacity (PR-21 enrichment): total annual hours
 * available across all 5 CS roles, hours committed by active playbooks,
 * resulting utilization %, FTE/cost totals, bottleneck list, and the
 * backend-computed recommendation.
 *
 * Legacy props (accountsPerCsm, targetPerCsm, csmCount, accountUtilization)
 * are accepted for backward compatibility but are no longer the primary
 * gauge — they ALWAYS pinned to ~100% on a fully-loaded portfolio.
 */
const TeamCapacityGauge: React.FC<{
  hoursAvailable: number;
  hoursCommitted: number;
  hoursUtilizationPct: number;
  totalFte?: number;
  totalAnnualCost?: number;
  activePlaybooks?: number;
  bottleneckRoles?: string[];
  feasible?: boolean;
  recommendation?: string;
  // Legacy/fallback inputs — used only when hoursAvailable === 0
  // (e.g. cold-start tenant or older API build without resource_pool).
  accountsPerCsm: number;
  targetPerCsm: number;
  csmCount: number;
}> = ({
  hoursAvailable,
  hoursCommitted,
  hoursUtilizationPct,
  totalFte,
  totalAnnualCost,
  activePlaybooks,
  bottleneckRoles,
  feasible,
  recommendation,
  accountsPerCsm,
  targetPerCsm,
  csmCount,
}) => {
  // Prefer hours-based utilization. Fall back to account-count only when the
  // resource pool isn't available (older backend or load error).
  const useHours = hoursAvailable > 0;
  const utilization = useHours
    ? Math.round(hoursUtilizationPct)
    : Math.round((accountsPerCsm / targetPerCsm) * 100);
  const circumference = 2 * Math.PI * 40;
  const progress = (Math.min(utilization, 100) / 100) * circumference;
  const gaugeColor = utilization > 90 ? '#ef4444' : utilization > 75 ? '#eab308' : TEAL;

  const formatHours = (h: number): string => {
    if (h >= 1000) return `${(h / 1000).toFixed(1)}k`;
    return `${Math.round(h)}`;
  };

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
      <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-1">
        Team Capacity
      </h3>
      <p className="text-[9px] text-gray-600 mb-3">
        {useHours ? 'Hours committed vs available (annual)' : 'Accounts per CSM (target ratio)'}
      </p>
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
              stroke={gaugeColor}
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={circumference - progress}
              className="transition-all duration-1000"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold" style={{ color: gaugeColor }}>{utilization}%</span>
            <span className="text-[9px] text-gray-500">utilized</span>
          </div>
        </div>
      </div>
      {/* Stats */}
      <div className="space-y-2.5">
        {useHours ? (
          <>
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-gray-500">Hours Committed</span>
              <span className="text-xs font-semibold text-teal-400">
                {formatHours(hoursCommitted)}h
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-gray-500">Hours Available</span>
              <span className="text-xs font-medium text-gray-300">
                {formatHours(hoursAvailable)}h
              </span>
            </div>
            {(totalFte !== undefined && totalFte > 0) && (
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-gray-500">Total FTE</span>
                <span className="text-xs font-semibold text-white">{totalFte.toFixed(2)}</span>
              </div>
            )}
            {(totalAnnualCost !== undefined && totalAnnualCost > 0) && (
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-gray-500">Annual Cost</span>
                <span className="text-xs font-medium text-gray-300 font-mono">
                  {formatCompact(totalAnnualCost)}
                </span>
              </div>
            )}
            {csmCount > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-gray-500">CSMs on Team</span>
                <span className="text-xs font-medium text-gray-300">{csmCount}</span>
              </div>
            )}
            <div className="w-full h-1 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, utilization)}%`, backgroundColor: gaugeColor }}
              />
            </div>
            {/* Bottleneck / feasibility line */}
            <div className="pt-2 border-t border-gray-700/40 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-gray-500">Bottlenecks</span>
                {bottleneckRoles && bottleneckRoles.length > 0 ? (
                  <span className="text-[10px] font-semibold text-orange-400">
                    {bottleneckRoles.join(', ')}
                  </span>
                ) : (
                  <span className="text-[10px] font-medium text-green-400">None</span>
                )}
              </div>
              {activePlaybooks !== undefined && (
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-gray-500">Active Playbooks</span>
                  <span className="text-xs font-semibold text-white">{activePlaybooks}</span>
                </div>
              )}
            </div>
            {recommendation && (
              <p className="text-[10px] text-gray-400 leading-snug pt-1">
                {recommendation}
              </p>
            )}
          </>
        ) : (
          // Fallback (cold-start / older backend): the prior account-count gauge
          <>
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-gray-500">CSMs on Team</span>
              <span className="text-xs font-semibold text-white">{csmCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-gray-500">Accounts per CSM</span>
              <span className="text-xs font-semibold text-teal-400">{accountsPerCsm}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-gray-500">Target per CSM</span>
              <span className="text-xs font-medium text-gray-300">{targetPerCsm}</span>
            </div>
            <div className="w-full h-1 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${Math.min(100, utilization)}%`, backgroundColor: gaugeColor }}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
};

/** Renewal Pipeline widget (right sidebar) */
const RenewalPipelineWidget: React.FC<{
  renewals: RenewalItem[];
  totalCount: number;
  totalArr: number;
}> = ({ renewals, totalCount, totalArr }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
    <div className="flex items-center justify-between mb-1">
      <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase">
        Renewal Pipeline
      </h3>
      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-teal-500/15 text-teal-400">
        Next 90 days
      </span>
    </div>

    {/* Summary */}
    <div className="flex items-baseline gap-2 mb-4 mt-2">
      <span className="text-2xl font-bold text-teal-400">{totalCount}</span>
      <span className="text-xs text-gray-500">renewals</span>
      <span className="text-gray-700 mx-1">&middot;</span>
      <span className="text-sm font-semibold text-white">{formatCompact(totalArr)}</span>
    </div>

    {/* Renewal list */}
    <div className="space-y-2.5">
      {renewals.slice(0, 5).map((renewal, i) => {
        const color = classifyColor(renewal.health_score);
        const isUrgent = renewal.days_until <= 30;
        return (
          <div key={i} className="flex items-center gap-2">
            <div
              className="w-1.5 h-1.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: color }}
            />
            <div className="flex-1 min-w-0">
              <p className="text-[11px] text-gray-300 truncate">{renewal.account_name}</p>
            </div>
            <span className="text-[10px] text-gray-500 flex-shrink-0">
              {renewal.days_until}d
            </span>
            <span className="text-[10px] font-semibold text-gray-300 flex-shrink-0 w-12 text-right">
              {formatCompactNoSign(renewal.arr)}
            </span>
            {isUrgent && (
              <AlertTriangle className="w-3 h-3 text-red-400 flex-shrink-0" />
            )}
          </div>
        );
      })}
    </div>
  </div>
);

/** Quick Stats widget (right sidebar) */
const QuickStatsWidget: React.FC<{
  stats: VPCSDashboardData['quick_stats'];
}> = ({ stats }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
    <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-3">
      Quick Stats
    </h3>
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Timer className="w-3.5 h-3.5 text-gray-500" />
          <span className="text-[11px] text-gray-500">Avg Resolution</span>
        </div>
        <span className="text-xs font-semibold text-white">{stats.avg_resolution_days}d</span>
      </div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Target className="w-3.5 h-3.5 text-gray-500" />
          <span className="text-[11px] text-gray-500">Playbook Success</span>
        </div>
        <span className="text-xs font-semibold text-teal-400">{stats.playbook_success_rate}%</span>
      </div>
      <div className="w-full h-1 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-teal-500 rounded-full transition-all"
          style={{ width: `${stats.playbook_success_rate}%` }}
        />
      </div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <UserCheck className="w-3.5 h-3.5 text-gray-500" />
          <span className="text-[11px] text-gray-500">NPS Score</span>
        </div>
        <span className="text-xs font-semibold text-white">{stats.nps_score}</span>
      </div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-gray-500" />
          <span className="text-[11px] text-gray-500">Actions Completed</span>
        </div>
        <span className="text-xs font-semibold text-green-400">{stats.actions_completed_pct}%</span>
      </div>
    </div>
  </div>
);

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const VPCSDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { session } = useSession();

  const [data, setData] = useState<VPCSDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [activeView, setActiveViewRaw] = useState<VPCSViewId>('vpcs-overview');
  const [healthFilter, setHealthFilter] = useState<string | null>(null);
  const setActiveView = useCallback((view: VPCSViewId) => {
    trackDashboardSwitch(activeView, `vpcs_${view}`);
    setActiveViewRaw(view);
    if (view !== 'accounts') setHealthFilter(null);
  }, [activeView]);

  // Fetch dashboard data from multiple endpoints
  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const customerId = getCustomerIdentifier(session);
        const headers = { 'X-Customer-ID': customerId };

        // Parallel fetch from all endpoints (including new ones)
        const [accountsResp, actionsResp, healthResp, roiResp, capacityResp, scorecardResp, playbookMetricsResp, historyResp, renewalsResp] = await Promise.allSettled([
          apiCall('/api/v1/accounts', { headers }),
          apiCall('/api/v1/daily-actions', { headers }),
          apiCall('/api/v1/health-summary', { headers }),
          apiCall('/api/outcome-roi/portfolio-summary', { headers }),
          apiCall('/api/v1/team-capacity', { headers }),
          apiCall('/api/v1/csm-scorecard', { headers }),
          apiCall('/api/v1/playbook-success-metrics', { headers }),
          apiCall('/api/v1/health-score-history?months=6', { headers }),
          apiCall('/api/v1/renewals?days=90', { headers }),
        ]);

        // Detect session-expired across any endpoint and surface to error UI.
        // Primary signal: accountsResp (the dashboard's anchor data); any 401
        // on it means auth has lapsed and we should send the user to /login.
        const anchorResp = (accountsResp.status === 'fulfilled') ? accountsResp.value : null;
        if (anchorResp && anchorResp.status === 401) {
          setErrorStatus(401);
        }

        // Parse responses (graceful fallback per endpoint)
        const parse = async (r: PromiseSettledResult<Response>) =>
          r.status === 'fulfilled' && r.value.ok ? r.value.json() : null;

        const accountsData = await parse(accountsResp);
        const actionsData = await parse(actionsResp);
        const healthData = await parse(healthResp);
        const roiData = await parse(roiResp);
        const capacityData = await parse(capacityResp);
        const scorecardData = await parse(scorecardResp);
        const playbookMetrics = await parse(playbookMetricsResp);
        const historyData = await parse(historyResp);
        const renewalsData = await parse(renewalsResp);

        if (cancelled) return;

        // Track whether we got real data from the backend
        const hasLiveData = !!(accountsData || actionsData || healthData);

        // If no API data at all, show error
        if (!hasLiveData) {
          setError('No data available. Upload your data to get started.');
          setLoading(false);
          return;
        }

        // Transform accounts data
        const rawAccounts = accountsData?.accounts || accountsData || [];
        const csmByAccountName = new Map<string, string>();
        const accounts: AccountRow[] = (Array.isArray(rawAccounts) ? rawAccounts : []).map((a: any) => {
          const name = a.account_name || a.name || 'Unknown';
          const meta = a.profile_metadata || {};
          const assigned = meta.assigned_csm || meta.csm_name || a.assigned_csm;
          if (assigned) csmByAccountName.set(name, assigned);
          return {
            account_id: a.account_id || a.id,
            account_name: name,
            assigned_csm: assigned,
            health_score: a.health_score || a.overall_health || 0,
            arr: a.arr || a.revenue || 0,
            industry: a.industry || a.vertical || 'N/A',
            region: a.region || 'N/A',
            last_signal: a.last_signal || a.latest_signal || 'No recent signals',
            classification: classify(a.health_score || a.overall_health || 0),
            renewal_date: a.renewal_date || meta.renewal_date || undefined,
          };
        }).sort((a: AccountRow, b: AccountRow) => a.health_score - b.health_score);

        // Compute health buckets
        const { healthy_min, at_risk_min } = thresholdValues();
        const healthyAccts = accounts.filter((a) => a.health_score >= healthy_min);
        const atRiskAccts = accounts.filter((a) => a.health_score >= at_risk_min && a.health_score < healthy_min);
        const criticalAccts = accounts.filter((a) => a.health_score < at_risk_min);
        const total = accounts.length || 1;
        const totalArr = accounts.reduce((s, a) => s + a.arr, 0);
        const avgHealth = totalArr > 0
          ? accounts.reduce((s, a) => s + a.health_score * a.arr, 0) / totalArr
          : accounts.reduce((s, a) => s + a.health_score, 0) / total;

        const healthBuckets: HealthBucket[] = [
          { label: 'Healthy', count: healthyAccts.length, pct: Math.round((healthyAccts.length / total) * 100), arr: healthyAccts.reduce((s, a) => s + a.arr, 0), color: '#22c55e', bgClass: 'bg-green-500/10', textClass: 'text-green-400' },
          { label: 'At-Risk', count: atRiskAccts.length, pct: Math.round((atRiskAccts.length / total) * 100), arr: atRiskAccts.reduce((s, a) => s + a.arr, 0), color: '#eab308', bgClass: 'bg-yellow-500/10', textClass: 'text-yellow-400' },
          { label: 'Critical', count: criticalAccts.length, pct: Math.round((criticalAccts.length / total) * 100), arr: criticalAccts.reduce((s, a) => s + a.arr, 0), color: '#ef4444', bgClass: 'bg-red-500/10', textClass: 'text-red-400' },
        ];

        // Transform actions data
        const rawActions = actionsData?.actions || actionsData || [];
        const actions: ActionItem[] = (Array.isArray(rawActions) ? rawActions : []).slice(0, 10).map((a: any, i: number) => {
          const acctName = a.account_name || a.account || 'Unknown';
          return {
            priority: a.rank || a.priority || i + 1,
            account_name: acctName,
            assigned_csm: a.assigned_csm || a.csm_name || csmByAccountName.get(acctName),
            action: a.action_title || a.action || a.description || a.title || 'Action required',
            urgency: (a.urgency || a.severity || 'medium').toLowerCase() as ActionItem['urgency'],
            est_hours: a.estimated_hours || a.est_hours || a.effort_hours || 2,
            impact_dollars: a.roi_projected_impact || a.impact_dollars || a.dollar_impact || a.projected_impact || 0,
            playbook: a.related_playbook_id || a.playbook || a.playbook_id || undefined,
          };
        });

        // Use real playbook metrics for completion rate
        const pbSummary = playbookMetrics?.portfolio_summary;
        const completionRate = pbSummary?.overall_success_rate_pct ?? (roiData?.playbook_success_rate || 68);
        const totalRuns = pbSummary?.total_runs || 0;
        const completedRuns = Math.round(totalRuns * completionRate / 100);

        // ROI / renewal data
        const renewalCount = roiData?.renewals_90d_count || healthData?.renewal_count || 0;
        const renewalArr = roiData?.renewals_90d_arr || 0;

        const apiRenewals: RenewalItem[] = (renewalsData?.renewals || []).map((r: any) => ({
          account_name: r.account_name,
          arr: r.arr,
          days_until: r.days_until,
          health_score: r.health_score,
        }));

        const now = new Date();
        const renewals: RenewalItem[] = apiRenewals.length > 0
          ? apiRenewals
          : accounts
            .filter((a) => a.renewal_date)
            .map((a) => {
              const renewDate = new Date(a.renewal_date!);
              const diffMs = renewDate.getTime() - now.getTime();
              const daysUntil = Math.max(0, Math.round(diffMs / (1000 * 60 * 60 * 24)));
              return { account_name: a.account_name, arr: a.arr, days_until: daysUntil, health_score: a.health_score };
            })
            .filter((r) => r.days_until <= 90)
            .sort((a, b) => a.days_until - b.days_until)
            .slice(0, 6);

        const finalRenewals = renewals;

        // Team capacity from real endpoint
        const realCsmCount = capacityData?.csm_count || Math.ceil(accounts.length / 5);
        const realAcctsPerCsm = capacityData?.accounts_per_csm || Math.round(accounts.length / Math.max(1, realCsmCount));
        const realTargetPerCsm = capacityData?.target_per_csm || 6;

        // CSM scorecards from real endpoint
        const rawScorecards = scorecardData?.scorecards || {};
        const csmScorecards: CSMScorecard[] = Object.values(rawScorecards);

        // Health history accounts
        const historyAccounts: HealthHistoryAccount[] = (historyData?.accounts || []).map((a: any) => ({
          account_id: a.account_id,
          account_name: a.account_name,
          arr: a.arr,
          current_health: a.current_health,
          current_status: a.current_status,
          net_change: a.net_change,
          trajectory: a.trajectory,
          monthly_scores: a.monthly_scores || [],
        }));

        const portfolioTraj = historyData?.portfolio_trajectory || {
          improving_count: 0, declining_count: 0, stable_count: 0,
          improving_arr_pct: 0, declining_arr_pct: 0,
        };

        const transformed: VPCSDashboardData = {
          summary_cards: [
            { label: 'Total Accounts', value: String(accounts.length), subtitle: `Across ${realCsmCount} CSMs`, accent: 'white', icon: <Users className="w-4 h-4" /> },
            { label: 'Avg Health Score', value: avgHealth.toFixed(1), subtitle: 'Portfolio weighted avg', accent: 'teal', icon: <Activity className="w-4 h-4" /> },
            { label: 'Playbook Success', value: `${Math.round(completionRate)}%`, subtitle: totalRuns > 0 ? `${completedRuns} of ${totalRuns} resolved` : 'No executions yet', tag: completionRate >= 65 ? 'On track' : undefined, accent: 'green', icon: <CheckCircle2 className="w-4 h-4" /> },
            { label: 'Renewals 90d', value: String(finalRenewals.length || renewalCount), subtitle: `${formatCompact(finalRenewals.reduce((s, r) => s + r.arr, 0) || renewalArr)} ARR renewing`, accent: 'cyan', icon: <Calendar className="w-4 h-4" /> },
          ],
          health_buckets: healthBuckets,
          actions: actions,
          accounts,
          renewals_90d: finalRenewals,
          renewal_count_90d: finalRenewals.length || renewalCount,
          renewal_arr_90d: finalRenewals.reduce((s, r) => s + r.arr, 0) || renewalArr,
          team_capacity: {
            accounts_per_csm: realAcctsPerCsm,
            target_per_csm: realTargetPerCsm,
            csm_count: realCsmCount,
            per_csm_breakdown: capacityData?.per_csm_breakdown || [],
            // Hours-based resource-pool view (preferred; PR-29 fix).
            total_hours_available: Number(capacityData?.total_hours_available || 0),
            total_hours_planned: Number(capacityData?.total_hours_planned || 0),
            total_hours_utilization_pct: Number(capacityData?.total_hours_utilization_pct || 0),
            total_fte: Number(capacityData?.resource_pool?.totals?.total_fte || 0),
            total_annual_cost: Number(capacityData?.resource_pool?.totals?.total_annual_cost || 0),
            feasible: capacityData?.feasible !== undefined ? !!capacityData.feasible : true,
            bottleneck_roles: Array.isArray(capacityData?.bottleneck_roles) ? capacityData.bottleneck_roles : [],
            recommendation: typeof capacityData?.recommendation === 'string' ? capacityData.recommendation : '',
            active_playbooks: Number(capacityData?.active_playbooks || 0),
          },
          quick_stats: {
            avg_resolution_days: roiData?.avg_resolution_days || 4.2,
            playbook_success_rate: Math.round(completionRate),
            nps_score: roiData?.nps_score || 42,
            actions_completed_pct: Math.round(completionRate),
          },
          csm_scorecards: csmScorecards,
          health_history_accounts: historyAccounts,
          portfolio_trajectory: portfolioTraj,
          playbook_metrics: Object.entries(playbookMetrics?.playbooks || {}).map(([pid, pb]: [string, any]) => ({
            playbook_id: pid,
            total_executions: pb.total_executions || 0,
            resolved: pb.resolved || 0,
            escalated: pb.escalated || 0,
            timeout: pb.timeout || 0,
            success_rate_pct: pb.success_rate_pct || 0,
            avg_health_delta: pb.avg_health_delta || 0,
            total_revenue_protected: pb.total_revenue_protected || 0,
            total_revenue_expanded: pb.total_revenue_expanded || 0,
          })),
          revenue_summary: roiData ? {
            revenue_at_risk: roiData.revenue_at_risk || roiData.at_risk_amount || 0,
            revenue_protected: roiData.revenue_protected || roiData.protected_amount || 0,
            expansion_pipeline: roiData.expansion_pipeline || roiData.expansion_amount || 0,
            total_arr: roiData.total_arr || totalArr || 0,
          } : null,
          capacity_planning: capacityData?.capacity_planning || null,
          uncovered_at_risk: Array.isArray(capacityData?.uncovered_at_risk)
            ? capacityData.uncovered_at_risk
            : [],
          customer_phase: (roiData?.customer_phase || 'active') as CustomerPhase,
          proof_executions_total: totalRuns,
          proof_realized_roi: Number(roiData?.realized_roi || roiData?.total_revenue_impact || 0),
          period: roiData?.quarter_label || `Q${Math.ceil((new Date().getMonth() + 1) / 3)} ${new Date().getFullYear()}`,
          last_updated: 'just now',
          is_live_data: hasLiveData,
        };

        setData(transformed);
        trackPageView('vpcs_dashboard', { accounts: transformed.accounts?.length || 0 });
      } catch {
        if (!cancelled) {
          setError('Unable to load VP CS dashboard data. Please check your connection and try again.');
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

  const accountCount = data?.accounts?.length || 0;
  const actionCount = data?.actions?.length || 0;

  // ---- Loading state ----
  if (loading) {
    return (
      <div className="flex h-screen bg-[#0f1419] text-white font-['Inter',sans-serif]">
        <SidebarNav activeId={activeView} onViewChange={setActiveView} onNavigate={handleNav} />
        <main className="flex-1 p-6 overflow-y-auto">
          <div className="mb-6">
            <SkeletonLine w="w-64" />
          </div>
          <div className="grid grid-cols-4 gap-4 mb-4">
            <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
          </div>
          <SkeletonCard className="h-48 mb-4" />
          <SkeletonCard className="h-64 mb-4" />
          <SkeletonCard className="h-64" />
        </main>
        <aside className="w-80 bg-[#0d1117] border-l border-gray-700/50 p-4">
          <SkeletonCard className="h-56 mb-4" />
          <SkeletonCard className="h-48 mb-4" />
          <SkeletonCard className="h-40" />
        </aside>
      </div>
    );
  }

  // ---- Error state ----
  if (error && !data) {
    return (
      <DashboardErrorState
        dashboardLabel="VP CS dashboard"
        errorMessage={error}
        errorStatus={errorStatus}
      />
    );
  }

  const d = data!;

  return (
    <div className="flex flex-col h-screen bg-[#0f1419] text-white font-['Inter',sans-serif]">
      <DashboardTopBar accent="teal" />
      <div className="flex flex-1 overflow-hidden">
      {/* ---- Left Sidebar ---- */}
      <SidebarNav
        activeId={activeView}
        onViewChange={setActiveView}
        onNavigate={handleNav}
        accountCount={accountCount}
        actionCount={actionCount}
      />

      {/* ---- Main Content ---- */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-[1200px]">
          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-lg font-semibold text-white tracking-tight">
                {activeView === 'vpcs-overview' && 'CS TEAM PERFORMANCE'}
                {activeView === 'accounts' && 'ACCOUNT PORTFOLIO'}
                {activeView === 'playbooks' && 'PLAYBOOK PERFORMANCE'}
                {activeView === 'renewals' && 'RENEWAL PIPELINE'}
                {activeView === 'health-trends' && 'HEALTH TRENDS'}
                {activeView === 'team-metrics' && 'TEAM METRICS'}
                <span className="text-gray-500 font-normal ml-2">&middot; {d.period}</span>
              </h1>
              <div className="h-0.5 w-12 mt-1.5 rounded-full" style={{ backgroundColor: TEAL }} />
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

          {/* ============ VIEW: Team Overview (default) ============ */}
          {activeView === 'vpcs-overview' && (
            <>
              <VPCSMetricGuideBanner />
              <VPCSPreProofBanner
                phase={d.customer_phase}
                executionsTotal={d.proof_executions_total}
                realizedRoi={d.proof_realized_roi}
              />
              {/* Row 1: Summary cards */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                {d.summary_cards.map((card, i) => (
                  <SummaryCardComponent key={i} card={card} />
                ))}
              </div>

              {d.revenue_summary && (
                <VPCSContextGraphStrip
                  data={{
                    revenue_at_risk: d.revenue_summary.revenue_at_risk,
                    graph_revenue_protected: d.revenue_summary.revenue_protected,
                    expansion_pipeline: d.revenue_summary.expansion_pipeline,
                    revenue_risk_label: 'Context-graph confirmed',
                  }}
                />
              )}

              {d.capacity_planning && (
                <VPCSCapacityPlanningPanel
                  planning={d.capacity_planning}
                  uncovered={d.uncovered_at_risk}
                />
              )}

              {/* Row 3: Health Distribution — click bucket to drill into filtered accounts */}
              <div className="mb-6">
                <HealthDistribution
                  buckets={d.health_buckets}
                  onBucketClick={(label) => {
                    setHealthFilter(label);
                    setActiveView('accounts');
                  }}
                />
              </div>

              {/* Row 3: Actions Queue */}
              <div className="mb-6">
                <ActionsQueueTable actions={d.actions} />
              </div>

              {/* Row 4: Account Portfolio */}
              <AccountPortfolioTable accounts={d.accounts} />
            </>
          )}

          {/* ============ VIEW: All Accounts ============ */}
          {activeView === 'accounts' && (
            <>
              {healthFilter && (
                <div className="mb-4 flex items-center gap-2">
                  <span className="text-xs text-gray-400">Filtered by:</span>
                  <span className="px-2 py-1 rounded text-xs font-semibold bg-gray-700 text-white">{healthFilter}</span>
                  <button
                    onClick={() => setHealthFilter(null)}
                    className="text-xs text-teal-400 hover:text-teal-300 ml-1"
                    aria-label="Clear health filter"
                  >
                    Clear filter
                  </button>
                </div>
              )}
              <AccountPortfolioTable
                accounts={healthFilter
                  ? d.accounts.filter(a => {
                      const cls = classify(a.health_score);
                      const map: Record<string, string> = { 'Healthy': 'healthy', 'At-Risk': 'at_risk', 'Critical': 'critical' };
                      return cls === (map[healthFilter] ?? healthFilter.toLowerCase());
                    })
                  : d.accounts
                }
              />
            </>
          )}

          {/* ============ VIEW: Playbooks ============ */}
          {activeView === 'playbooks' && (
            <>
              <div className="mb-6">
                <ActionsQueueTable actions={d.actions} />
              </div>
              {/* Per-Playbook Effectiveness Table */}
              <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Target className="w-4 h-4 text-teal-400" />
                    <h3 className="text-xs font-semibold text-white uppercase tracking-wide">Playbook Effectiveness</h3>
                  </div>
                  <span className="text-xs text-teal-400 font-semibold">{d.quick_stats.playbook_success_rate}% overall</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700/50">
                        <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">Playbook</th>
                        <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Runs</th>
                        <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Resolved</th>
                        <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Success %</th>
                        <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Health &Delta;</th>
                        <th className="text-right px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Rev Protected</th>
                        <th className="text-right px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">Rev Expanded</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.playbook_metrics.map((pm) => {
                        const successColor = pm.success_rate_pct >= 70 ? 'text-green-400' : pm.success_rate_pct >= 50 ? 'text-yellow-400' : 'text-red-400';
                        const deltaColor = pm.avg_health_delta > 0 ? 'text-green-400' : pm.avg_health_delta < 0 ? 'text-red-400' : 'text-gray-400';
                        return (
                          <tr key={pm.playbook_id} className="border-b border-gray-700/30 hover:bg-white/[0.02]">
                            <td className="px-5 py-3 text-xs font-medium text-white">{pm.playbook_id}</td>
                            <td className="text-center px-3 py-3 text-xs text-gray-300">{pm.total_executions}</td>
                            <td className="text-center px-3 py-3 text-xs text-gray-300">{pm.resolved}</td>
                            <td className="text-center px-3 py-3">
                              <span className={`text-xs font-semibold ${successColor}`}>{pm.success_rate_pct}%</span>
                            </td>
                            <td className="text-center px-3 py-3">
                              <span className={`text-xs font-semibold ${deltaColor}`}>
                                {pm.avg_health_delta > 0 ? '+' : ''}{pm.avg_health_delta.toFixed(1)}
                              </span>
                            </td>
                            <td className="text-right px-3 py-3 text-xs text-green-400 font-mono">{formatCompact(pm.total_revenue_protected)}</td>
                            <td className="text-right px-5 py-3 text-xs text-teal-400 font-mono">{formatCompact(pm.total_revenue_expanded)}</td>
                          </tr>
                        );
                      })}
                      {d.playbook_metrics.length === 0 && (
                        <tr><td colSpan={7} className="text-center py-8 text-gray-500 text-xs">No playbook execution data yet. Run playbooks to see effectiveness metrics.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {/* ============ VIEW: Renewals ============ */}
          {activeView === 'renewals' && (
            <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-teal-400" />
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wide">Renewal Pipeline &middot; Next 90 Days</h3>
                </div>
                <span className="text-[10px] text-gray-500">{d.renewals_90d.length} renewals &middot; {formatCompact(d.renewal_arr_90d)} ARR</span>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700/50">
                    <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">Account</th>
                    <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Health</th>
                    <th className="text-right px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase">ARR</th>
                    <th className="text-right px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">Days Until</th>
                  </tr>
                </thead>
                <tbody>
                  {d.renewals_90d.map((r, i) => {
                    const color = classifyColor(r.health_score);
                    return (
                      <tr key={i} className="border-b border-gray-700/30 hover:bg-white/[0.02]">
                        <td className="px-5 py-3 text-xs font-medium text-white">{r.account_name}</td>
                        <td className="text-center px-3 py-3">
                          <span className="text-xs font-semibold" style={{ color }}>{r.health_score}</span>
                        </td>
                        <td className="text-right px-4 py-3 text-xs text-gray-300 font-mono">{formatCompact(r.arr)}</td>
                        <td className="text-right px-5 py-3">
                          <span className={`text-xs font-semibold ${r.days_until <= 30 ? 'text-red-400' : r.days_until <= 60 ? 'text-yellow-400' : 'text-gray-300'}`}>
                            {r.days_until}d
                          </span>
                          {r.days_until <= 30 && <AlertTriangle className="w-3 h-3 text-red-400 inline ml-1" />}
                        </td>
                      </tr>
                    );
                  })}
                  {d.renewals_90d.length === 0 && (
                    <tr><td colSpan={4} className="text-center py-8 text-gray-500 text-xs">No renewals in the next 90 days</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* ============ VIEW: Health Trends ============ */}
          {activeView === 'health-trends' && (
            <>
              {/* Portfolio trajectory summary */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 text-center">
                  <TrendingUp className="w-5 h-5 text-green-400 mx-auto mb-2" />
                  <p className="text-3xl font-bold text-green-400">{d.portfolio_trajectory.improving_count}</p>
                  <p className="text-xs text-gray-500 mt-1">Improving</p>
                  <p className="text-[10px] text-gray-600">{d.portfolio_trajectory.improving_arr_pct}% of ARR</p>
                </div>
                <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 text-center">
                  <Minus className="w-5 h-5 text-gray-400 mx-auto mb-2" />
                  <p className="text-3xl font-bold text-gray-300">{d.portfolio_trajectory.stable_count}</p>
                  <p className="text-xs text-gray-500 mt-1">Stable</p>
                </div>
                <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 text-center">
                  <TrendingDown className="w-5 h-5 text-red-400 mx-auto mb-2" />
                  <p className="text-3xl font-bold text-red-400">{d.portfolio_trajectory.declining_count}</p>
                  <p className="text-xs text-gray-500 mt-1">Declining</p>
                  <p className="text-[10px] text-gray-600">{d.portfolio_trajectory.declining_arr_pct}% of ARR</p>
                </div>
              </div>

              {/* Per-account trajectory table */}
              <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-700/50 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-teal-400" />
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wide">Account Health Trajectories</h3>
                </div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700/50">
                      <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">Account</th>
                      <th className="text-right px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">ARR</th>
                      <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Current</th>
                      <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Change</th>
                      <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Trajectory</th>
                      <th className="text-center px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">Sparkline</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.health_history_accounts.map((a) => {
                      const color = classifyColor(a.current_health);
                      const changeColor = a.net_change > 5 ? 'text-green-400' : a.net_change < -5 ? 'text-red-400' : 'text-gray-400';
                      const trajIcon = a.trajectory === 'improving'
                        ? <TrendingUp className="w-3 h-3 text-green-400" />
                        : a.trajectory === 'declining'
                        ? <TrendingDown className="w-3 h-3 text-red-400" />
                        : <Minus className="w-3 h-3 text-gray-400" />;
                      // Simple text sparkline from monthly scores
                      const scores = a.monthly_scores.map((m) => m.health_score);
                      const maxS = Math.max(...scores, 100);
                      const minS = Math.min(...scores, 0);
                      const range = maxS - minS || 1;
                      return (
                        <tr key={a.account_id} className="border-b border-gray-700/30 hover:bg-white/[0.02]">
                          <td className="px-5 py-3 text-xs font-medium text-white">{a.account_name}</td>
                          <td className="text-right px-3 py-3 text-xs text-gray-300 font-mono">{formatCompact(a.arr)}</td>
                          <td className="text-center px-3 py-3">
                            <span className="text-xs font-semibold" style={{ color }}>{a.current_health}</span>
                          </td>
                          <td className="text-center px-3 py-3">
                            <span className={`text-xs font-semibold ${changeColor}`}>
                              {a.net_change > 0 ? '+' : ''}{a.net_change}
                            </span>
                          </td>
                          <td className="text-center px-3 py-3">
                            <span className="inline-flex items-center gap-1">
                              {trajIcon}
                              <span className="text-[10px] text-gray-500 capitalize">{a.trajectory}</span>
                            </span>
                          </td>
                          <td className="px-5 py-3">
                            {/* SVG mini sparkline */}
                            <svg width="80" height="20" className="inline-block">
                              <polyline
                                fill="none"
                                stroke={a.trajectory === 'improving' ? '#22c55e' : a.trajectory === 'declining' ? '#ef4444' : '#6b7280'}
                                strokeWidth="1.5"
                                points={scores.map((s, i) => `${(i / Math.max(scores.length - 1, 1)) * 76 + 2},${18 - ((s - minS) / range) * 16}`).join(' ')}
                              />
                            </svg>
                          </td>
                        </tr>
                      );
                    })}
                    {d.health_history_accounts.length === 0 && (
                      <tr><td colSpan={6} className="text-center py-8 text-gray-500 text-xs">No health history available. Run process_data to generate scores.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* ============ VIEW: Team Metrics (CSM Scorecard) ============ */}
          {activeView === 'team-metrics' && (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                {d.summary_cards.map((card, i) => (
                  <SummaryCardComponent key={i} card={card} />
                ))}
              </div>

              {/* CSM Scorecard Table */}
              <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-700/50 flex items-center gap-2">
                  <UserCheck className="w-4 h-4 text-teal-400" />
                  <h3 className="text-xs font-semibold text-white uppercase tracking-wide">CSM Performance Scorecard</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700/50">
                        <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">CSM</th>
                        <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Accounts</th>
                        <th className="text-right px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">ARR</th>
                        <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Health &Delta;</th>
                        <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Playbooks</th>
                        <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Success</th>
                        <th className="text-right px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Rev Protected</th>
                        <th className="text-right px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">Rev Expanded</th>
                      </tr>
                    </thead>
                    <tbody>
                      {d.csm_scorecards.map((sc) => {
                        const deltaColor = sc.avg_health_delta > 3 ? 'text-green-400' : sc.avg_health_delta < -3 ? 'text-red-400' : 'text-gray-300';
                        return (
                          <tr key={sc.csm_name} className="border-b border-gray-700/30 hover:bg-white/[0.02]">
                            <td className="px-5 py-3 text-xs font-medium text-white">{sc.csm_name}</td>
                            <td className="text-center px-3 py-3 text-xs text-gray-300">{sc.accounts_managed}</td>
                            <td className="text-right px-3 py-3 text-xs text-gray-300 font-mono">{formatCompact(sc.total_arr)}</td>
                            <td className="text-center px-3 py-3">
                              <span className={`text-xs font-semibold ${deltaColor}`}>
                                {sc.avg_health_delta > 0 ? '+' : ''}{sc.avg_health_delta}
                              </span>
                              <span className="text-[10px] text-gray-600 ml-1">
                                ({sc.accounts_improving}&#x2191; {sc.accounts_declining}&#x2193;)
                              </span>
                            </td>
                            <td className="text-center px-3 py-3 text-xs text-gray-300">{sc.playbooks_executed}</td>
                            <td className="text-center px-3 py-3">
                              <span className={`text-xs font-semibold ${sc.success_rate_pct >= 70 ? 'text-green-400' : sc.success_rate_pct >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                                {sc.success_rate_pct}%
                              </span>
                            </td>
                            <td className="text-right px-3 py-3 text-xs text-green-400 font-semibold font-mono">
                              {formatCompact(sc.revenue_protected)}
                            </td>
                            <td className="text-right px-5 py-3 text-xs text-teal-400 font-semibold font-mono">
                              {formatCompact(sc.revenue_expanded)}
                            </td>
                          </tr>
                        );
                      })}
                      {d.csm_scorecards.length === 0 && (
                        <tr><td colSpan={8} className="text-center py-8 text-gray-500 text-xs">No CSM assignment data. Ensure accounts have assigned_csm in profiles.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Team Capacity detail */}
              <div className="mt-6">
                <TeamCapacityGauge
                  hoursAvailable={d.team_capacity.total_hours_available || 0}
                  hoursCommitted={d.team_capacity.total_hours_planned || 0}
                  hoursUtilizationPct={d.team_capacity.total_hours_utilization_pct || 0}
                  totalFte={d.team_capacity.total_fte}
                  totalAnnualCost={d.team_capacity.total_annual_cost}
                  activePlaybooks={d.team_capacity.active_playbooks}
                  bottleneckRoles={d.team_capacity.bottleneck_roles}
                  feasible={d.team_capacity.feasible}
                  recommendation={d.team_capacity.recommendation}
                  accountsPerCsm={d.team_capacity.accounts_per_csm}
                  targetPerCsm={d.team_capacity.target_per_csm}
                  csmCount={d.team_capacity.csm_count}
                />
              </div>

              {d.capacity_planning && (
                <VPCSCapacityPlanningPanel
                  planning={d.capacity_planning}
                  uncovered={d.uncovered_at_risk}
                />
              )}

              {/* Per-CSM Capacity Breakdown */}
              {d.team_capacity.per_csm_breakdown.length > 0 && (
                <div className="mt-6 bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
                  <div className="px-5 py-4 border-b border-gray-700/50 flex items-center gap-2">
                    <Users className="w-4 h-4 text-teal-400" />
                    <h3 className="text-xs font-semibold text-white uppercase tracking-wide">Per-CSM Capacity</h3>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-700/50">
                          <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">CSM</th>
                          <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Accounts</th>
                          <th className="text-right px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">ARR</th>
                          <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">Active PBs</th>
                          <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase">At Risk</th>
                          <th className="text-right px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase">Utilization</th>
                        </tr>
                      </thead>
                      <tbody>
                        {d.team_capacity.per_csm_breakdown.map((csm) => {
                          const utilColor = csm.utilization_pct > 100 ? 'text-red-400' : csm.utilization_pct > 80 ? 'text-yellow-400' : 'text-green-400';
                          const barColor = csm.utilization_pct > 100 ? 'bg-red-500' : csm.utilization_pct > 80 ? 'bg-yellow-500' : 'bg-green-500';
                          return (
                            <tr key={csm.csm_name} className="border-b border-gray-700/30 hover:bg-white/[0.02]">
                              <td className="px-5 py-3 text-xs font-medium text-white">{csm.csm_name}</td>
                              <td className="text-center px-3 py-3 text-xs text-gray-300">{csm.accounts_managed}</td>
                              <td className="text-right px-3 py-3 text-xs text-gray-300 font-mono">{formatCompact(csm.total_arr)}</td>
                              <td className="text-center px-3 py-3 text-xs text-gray-300">{csm.active_playbooks}</td>
                              <td className="text-center px-3 py-3">
                                <span className={`text-xs font-semibold ${csm.at_risk_accounts > 0 ? 'text-red-400' : 'text-gray-400'}`}>
                                  {csm.at_risk_accounts}
                                </span>
                              </td>
                              <td className="text-right px-5 py-3">
                                <div className="flex items-center justify-end gap-2">
                                  <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                                    <div className={`h-full rounded-full ${barColor}`} style={{ width: `${Math.min(csm.utilization_pct, 100)}%` }} />
                                  </div>
                                  <span className={`text-xs font-semibold ${utilColor} w-10 text-right`}>{csm.utilization_pct}%</span>
                                </div>
                                <p className="text-[10px] text-gray-600 text-right mt-0.5">{csm.hours_committed}h / {csm.hours_available}h</p>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {/* ---- Right Sidebar ---- */}
      <aside className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 overflow-y-auto flex flex-col gap-5">
        {/* Team Capacity */}
        <TeamCapacityGauge
          hoursAvailable={d.team_capacity.total_hours_available || 0}
          hoursCommitted={d.team_capacity.total_hours_planned || 0}
          hoursUtilizationPct={d.team_capacity.total_hours_utilization_pct || 0}
          totalFte={d.team_capacity.total_fte}
          totalAnnualCost={d.team_capacity.total_annual_cost}
          activePlaybooks={d.team_capacity.active_playbooks}
          bottleneckRoles={d.team_capacity.bottleneck_roles}
          feasible={d.team_capacity.feasible}
          recommendation={d.team_capacity.recommendation}
          accountsPerCsm={d.team_capacity.accounts_per_csm}
          targetPerCsm={d.team_capacity.target_per_csm}
          csmCount={d.team_capacity.csm_count}
        />

        {/* Renewal Pipeline */}
        <RenewalPipelineWidget
          renewals={d.renewals_90d}
          totalCount={d.renewal_count_90d}
          totalArr={d.renewal_arr_90d}
        />

        {/* Quick Stats */}
        <QuickStatsWidget stats={d.quick_stats} />

        {/* Navigation buttons */}
        <div className="space-y-2.5">
          <button
            onClick={() => navigate('/dc-dashboard/csm')}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-lg bg-teal-600/10 border border-teal-500/20 text-teal-400 text-xs font-medium hover:bg-teal-600/20 transition-colors"
          >
            <ClipboardList className="w-3.5 h-3.5" />
            Go to CSM View
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => navigate('/cro-dashboard')}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-lg bg-cyan-600/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium hover:bg-cyan-600/20 transition-colors"
          >
            <Briefcase className="w-3.5 h-3.5" />
            Go to CRO View
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </aside>

      {/* Floating AI Advisor */}
      <AskAIPortal persona="vpcs" />
    </div>
    </div>
  );
};

export default VPCSDashboard;
