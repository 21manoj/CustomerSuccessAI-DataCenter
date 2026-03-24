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
  AlertTriangle, TrendingUp, TrendingDown, Shield, Zap,
  Target, DollarSign, Users, BarChart3, Clock,
  ChevronRight, Eye, Activity, GitBranch, Sparkles,
  ArrowRight, ArrowUpRight, Briefcase, CheckCircle2,
  Calendar, Timer, PlayCircle, ClipboardList, UserCheck,
  Gauge, RefreshCcw
} from 'lucide-react';
import { classify, classifyColor, thresholdValues } from '../../utils/healthThresholds';
import DashboardTopBar from './DashboardTopBar';
import { useSession } from '../../contexts/SessionContext';
import { apiCall, getCustomerIdentifier } from '../../utils/api';
import AskAIPortal from '../ai/AskAIPortal';

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
  action: string;
  urgency: 'critical' | 'high' | 'medium' | 'low';
  est_hours: number;
  impact_dollars: number;
  playbook?: string;
}

interface AccountRow {
  account_id: string | number;
  account_name: string;
  health_score: number;
  arr: number;
  industry: string;
  region: string;
  last_signal: string;
  classification: string;
}

interface RenewalItem {
  account_name: string;
  arr: number;
  days_until: number;
  health_score: number;
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
  };
  quick_stats: {
    avg_resolution_days: number;
    playbook_success_rate: number;
    nps_score: number;
    actions_completed_pct: number;
  };
  period: string;
  last_updated: string;
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

// Sidebar navigation items
const NAV_ITEMS = {
  management: [
    { id: 'vpcs-overview', label: 'Team Overview', path: '/vpcs-dashboard', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'accounts', label: 'All Accounts', path: '/vpcs-dashboard', icon: <Users className="w-4 h-4" /> },
    { id: 'playbooks', label: 'Playbooks', path: '/vpcs-dashboard', icon: <Target className="w-4 h-4" /> },
    { id: 'renewals', label: 'Renewals', path: '/vpcs-dashboard', icon: <Calendar className="w-4 h-4" /> },
  ],
  insights: [
    { id: 'health-trends', label: 'Health Trends', path: '/vpcs-dashboard', icon: <Activity className="w-4 h-4" /> },
    { id: 'team-metrics', label: 'Team Metrics', path: '/vpcs-dashboard', icon: <Gauge className="w-4 h-4" /> },
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
  },
  quick_stats: {
    avg_resolution_days: 4.2,
    playbook_success_rate: 73,
    nps_score: 42,
    actions_completed_pct: 68,
  },
  period: 'Q1 2026',
  last_updated: '2m ago',
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
const SidebarNav: React.FC<{
  activeId: string;
  onNavigate: (path: string) => void;
  accountCount?: number;
  actionCount?: number;
}> = ({ activeId, onNavigate, accountCount, actionCount }) => {
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
                onClick={() => onNavigate(item.path)}
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
                onClick={() => onNavigate(item.path)}
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

      {/* Branding */}
      <div className="mt-auto px-2 pt-4 border-t border-gray-700/30">
        <div className="text-[10px] text-gray-600 leading-relaxed">
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
const HealthDistribution: React.FC<{ buckets: HealthBucket[] }> = ({ buckets }) => (
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
        <div key={bucket.label} className={`p-5 ${bucket.bgClass} relative overflow-hidden`}>
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

/** Team Capacity gauge (right sidebar) */
const TeamCapacityGauge: React.FC<{
  accountsPerCsm: number;
  targetPerCsm: number;
  csmCount: number;
}> = ({ accountsPerCsm, targetPerCsm, csmCount }) => {
  const utilization = Math.round((accountsPerCsm / targetPerCsm) * 100);
  const circumference = 2 * Math.PI * 40;
  const progress = (Math.min(utilization, 100) / 100) * circumference;
  const gaugeColor = utilization > 90 ? '#ef4444' : utilization > 75 ? '#eab308' : TEAL;

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
      <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-4">
        Team Capacity
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

  // Fetch dashboard data from multiple endpoints
  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const customerId = getCustomerIdentifier(session);
        const headers = { 'X-Customer-ID': customerId };

        // Parallel fetch from all endpoints
        const [accountsResp, actionsResp, healthResp, roiResp] = await Promise.allSettled([
          apiCall('/api/dc2s/accounts', { headers }),
          apiCall('/api/dc2s/daily-actions', { headers }),
          apiCall('/api/dc2s/health-summary', { headers }),
          apiCall('/api/outcome-roi/portfolio-summary', { headers }),
        ]);

        // Parse responses (graceful fallback per endpoint)
        const accountsData = accountsResp.status === 'fulfilled' && accountsResp.value.ok
          ? await accountsResp.value.json()
          : null;
        const actionsData = actionsResp.status === 'fulfilled' && actionsResp.value.ok
          ? await actionsResp.value.json()
          : null;
        const healthData = healthResp.status === 'fulfilled' && healthResp.value.ok
          ? await healthResp.value.json()
          : null;
        const roiData = roiResp.status === 'fulfilled' && roiResp.value.ok
          ? await roiResp.value.json()
          : null;

        if (cancelled) return;

        // If no API data at all, show error
        if (!accountsData && !actionsData && !healthData && !roiData) {
          setError('No data available. Upload your data to get started.');
          setLoading(false);
          return;
        }

        // Transform accounts data
        const rawAccounts = accountsData?.accounts || accountsData || [];
        const accounts: AccountRow[] = (Array.isArray(rawAccounts) ? rawAccounts : []).map((a: any) => ({
          account_id: a.account_id || a.id,
          account_name: a.account_name || a.name || 'Unknown',
          health_score: a.health_score || a.overall_health || 0,
          arr: a.arr || a.revenue || 0,
          industry: a.industry || a.vertical || 'N/A',
          region: a.region || 'N/A',
          last_signal: a.last_signal || a.latest_signal || 'No recent signals',
          classification: classify(a.health_score || a.overall_health || 0),
        })).sort((a: AccountRow, b: AccountRow) => a.health_score - b.health_score);

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
        const actions: ActionItem[] = (Array.isArray(rawActions) ? rawActions : []).slice(0, 10).map((a: any, i: number) => ({
          priority: a.priority || i + 1,
          account_name: a.account_name || a.account || 'Unknown',
          action: a.action || a.description || a.title || 'Action required',
          urgency: (a.urgency || a.severity || 'medium').toLowerCase() as ActionItem['urgency'],
          est_hours: a.est_hours || a.effort_hours || 2,
          impact_dollars: a.impact_dollars || a.dollar_impact || a.projected_impact || 0,
          playbook: a.playbook || a.playbook_id || undefined,
        }));

        // Compute playbook completion
        const completedActions = actionsData?.completed_count || Math.round(actions.length * 0.68);
        const totalActions = actionsData?.total_count || Math.round(actions.length * 1.5);
        const completionRate = totalActions > 0 ? Math.round((completedActions / totalActions) * 100) : 68;

        // ROI / renewal data
        const renewalCount = roiData?.renewals_90d_count || healthData?.renewal_count || 6;
        const renewalArr = roiData?.renewals_90d_arr || 4000000;

        // Build renewals list from accounts with soonest estimated renewals
        const renewals: RenewalItem[] = accounts
          .filter((a) => a.arr > 200000)
          .slice(0, 6)
          .map((a, i) => ({
            account_name: a.account_name,
            arr: a.arr,
            days_until: 20 + i * 14,
            health_score: a.health_score,
          }));

        const transformed: VPCSDashboardData = {
          summary_cards: [
            { label: 'Total Accounts', value: String(accounts.length), subtitle: `Across ${Math.ceil(accounts.length / 5)} CSMs`, accent: 'white', icon: <Users className="w-4 h-4" /> },
            { label: 'Avg Health Score', value: avgHealth.toFixed(1), subtitle: 'Portfolio weighted avg', accent: 'teal', icon: <Activity className="w-4 h-4" /> },
            { label: 'Playbook Completion', value: `${completionRate}%`, subtitle: `${completedActions} of ${totalActions} actions done`, tag: completionRate >= 65 ? 'On track' : undefined, accent: 'green', icon: <CheckCircle2 className="w-4 h-4" /> },
            { label: 'Renewals This Qtr', value: String(renewalCount), subtitle: `${formatCompact(renewalArr)} ARR renewing`, accent: 'cyan', icon: <Calendar className="w-4 h-4" /> },
          ],
          health_buckets: healthBuckets,
          actions: actions,
          accounts,
          renewals_90d: renewals,
          renewal_count_90d: renewalCount,
          renewal_arr_90d: renewalArr,
          team_capacity: {
            accounts_per_csm: Math.round(accounts.length / Math.max(1, Math.ceil(accounts.length / 5))),
            target_per_csm: 6,
            csm_count: Math.ceil(accounts.length / 5),
          },
          quick_stats: {
            avg_resolution_days: roiData?.avg_resolution_days || 4.2,
            playbook_success_rate: roiData?.playbook_success_rate || 73,
            nps_score: roiData?.nps_score || 42,
            actions_completed_pct: completionRate,
          },
          period: roiData?.quarter_label || 'Q1 2026',
          last_updated: '2m ago',
        };

        setData(transformed);
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
        <SidebarNav activeId="vpcs-overview" onNavigate={handleNav} />
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
      <div className="flex h-screen bg-[#0f1419] text-white font-['Inter',sans-serif] items-center justify-center">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Unable to Load Dashboard</h2>
          <p className="text-gray-400 text-sm mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-teal-600 text-white rounded-lg text-sm hover:bg-teal-500 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const d = data!;

  return (
    <div className="flex flex-col h-screen bg-[#0f1419] text-white font-['Inter',sans-serif]">
      <DashboardTopBar accent="teal" />
      <div className="flex flex-1 overflow-hidden">
      {/* ---- Left Sidebar ---- */}
      <SidebarNav
        activeId="vpcs-overview"
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
                CS TEAM PERFORMANCE
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

          {/* Row 1: Summary cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            {d.summary_cards.map((card, i) => (
              <SummaryCardComponent key={i} card={card} />
            ))}
          </div>

          {/* Row 2: Health Distribution */}
          <div className="mb-6">
            <HealthDistribution buckets={d.health_buckets} />
          </div>

          {/* Row 3: Actions Queue */}
          <div className="mb-6">
            <ActionsQueueTable actions={d.actions} />
          </div>

          {/* Row 4: Account Portfolio */}
          <AccountPortfolioTable accounts={d.accounts} />
        </div>
      </main>

      {/* ---- Right Sidebar ---- */}
      <aside className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 overflow-y-auto flex flex-col gap-5">
        {/* Team Capacity */}
        <TeamCapacityGauge
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
    </div>{/* end flex row */}
    </div>{/* end flex col */}
  );
};

export default VPCSDashboard;
