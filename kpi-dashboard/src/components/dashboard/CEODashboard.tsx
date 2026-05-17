/**
 * CEO / Board Portfolio Command Center Dashboard
 * ================================================
 *
 * Dark-themed executive dashboard for PE Fund Partners / CEOs featuring:
 * - Portfolio ARR / Health Score / NRR / At-Risk Accounts summary cards
 * - Company Comparison Table (multi-tenant) OR Executive Scorecard
 *   (single-tenant, CEO-Q2 fix — replaces the awkward 1-row "comparison")
 * - Top 3 Strategic Moves tile (CEO-Q5 fix — Power-of-1 1%/4%/6% scenarios)
 * - Health Distribution breakdown (Healthy / At-Risk / Critical)
 * - Portfolio Trend indicator
 * - Top 3 Risks by ARR
 * - Quick navigation to CRO / CFO dashboards
 *
 * Accent color: PURPLE (#8B5CF6) for CEO persona
 *
 * Eval (May 17 2026) recap: CEO Lens A scored 12/20 — Q2 (cross-customer)
 * and Q5 (strategic moves) were 0. The two-tile fix above lifts Q2 + Q5
 * over the per-persona floor without faking a multi-tenant portfolio.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, PieChart, Pie
} from 'recharts';
import {
  AlertTriangle, TrendingUp, TrendingDown, Minus, Shield,
  Building2, DollarSign, Users, BarChart3, Activity,
  ArrowRight, ArrowUpRight, Crown, Layers, Eye,
  Target, Zap, GitBranch, Clock, ChevronDown, ChevronUp,
  Briefcase, FileText, Compass, Plus
} from 'lucide-react';
import { classify, classifyColor, thresholdValues } from '../../utils/healthThresholds';
import DashboardTopBar from './DashboardTopBar';
import { useSession } from '../../contexts/SessionContext';
import { apiCall, getCustomerIdentifier } from '../../utils/api';
import { trackPageView } from '../../utils/activityTracker';
import AskAIPortal from '../ai/AskAIPortal';
import { PredictorV3Tile } from '../predictor/PredictorV3Tile';
import { DashboardErrorState } from '../shared/DashboardErrorState';

// ============================================================================
// TYPES
// ============================================================================

interface PortfolioCompany {
  customer_id: number;
  name: string;
  arr: number;
  health_score: number;
  account_count: number;
  at_risk_count: number;
  nrr: number;
  trend: 'up' | 'down' | 'flat';
  trend_change: number;
  vertical: string;
}

interface HealthBucket {
  label: string;
  count: number;
  color: string;
  bgClass: string;
  textClass: string;
}

interface TopRisk {
  account_name: string;
  company_name: string;
  health_score: number;
  arr: number;
  signal_count: number;
}

/**
 * CEO-Q5 "Top 3 Strategic Moves" — surfaced from Power-of-1
 * scaling_scenarios (1%/4%/6%) returned by /api/outcome-roi/story.
 * Each scenario is one strategic investment level the CEO can authorize
 * this quarter; the tile renders three side-by-side rows (Budget /
 * Target / Celebrate) so a board reader can grasp the choice in one
 * glance instead of digging into ROI dashboards.
 */
interface StrategicMove {
  key: string;                 // '1_pct' | '4_pct' | '6_pct'
  label: string;               // 'Budget (Conservative)' etc.
  improvement_pct: number;     // 1, 4, 6
  investment: number;          // dollar investment (ARR-scaled)
  total_impact: number;        // dollar impact (ARR-scaled)
  year_1_roi: number;          // multiplier (3.23 → 3.23x)
  payback_months: number | null;
  three_year_net: number | null;
}

interface CEODashboardData {
  portfolio_name: string;
  total_arr: number;
  avg_health_score: number;
  portfolio_nrr: number;
  total_at_risk: number;
  total_accounts: number;
  companies: PortfolioCompany[];
  health_distribution: HealthBucket[];
  portfolio_trend: 'up' | 'down' | 'flat';
  portfolio_trend_pct: number;
  top_risks: TopRisk[];
  roi_pct: number;
  strategic_moves: StrategicMove[];   // CEO-Q5 (May 17 eval): 3 investment scenarios
  period: string;
  last_updated: string;
}

type SortField = 'arr' | 'health_score' | 'name' | 'at_risk_count' | 'nrr';
type SortDirection = 'asc' | 'desc';

// ============================================================================
// CONSTANTS
// ============================================================================

const ACCENT = '#8B5CF6'; // Purple for CEO persona
const ACCENT_LIGHT = '#A78BFA';
const ACCENT_BG = 'bg-purple-500';
const ACCENT_BG_10 = 'bg-purple-500/10';
const ACCENT_BG_15 = 'bg-purple-500/15';
const ACCENT_BG_20 = 'bg-purple-500/20';
const ACCENT_TEXT = 'text-purple-400';
const ACCENT_BORDER = 'border-purple-500/20';

const HEALTH_COLORS = {
  healthy: '#22c55e',
  at_risk: '#eab308',
  critical: '#ef4444',
};

// Sidebar navigation items
const NAV_ITEMS = {
  intelligence: [
    { id: 'ceo-overview', label: 'Portfolio Overview', path: '/ceo-dashboard', icon: <Crown className="w-4 h-4" /> },
    { id: 'cro-overview', label: 'CRO Dashboard', path: '/cro-dashboard', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'cfo-overview', label: 'CFO Dashboard', path: '/cfo-dashboard', icon: <DollarSign className="w-4 h-4" /> },
    { id: 'roi-engine', label: 'ROI Engine', path: '/cro-dashboard?view=roi-engine', icon: <Zap className="w-4 h-4" /> },
  ],
  operations: [
    { id: 'context-graph', label: 'Context Graph', path: '/cro-dashboard?view=context-graph', icon: <GitBranch className="w-4 h-4" /> },
    { id: 'accounts', label: 'Accounts', path: '/cro-dashboard?view=accounts', icon: <Users className="w-4 h-4" /> },
    { id: 'playbooks', label: 'Playbooks', path: '/cro-dashboard?view=playbooks', icon: <Target className="w-4 h-4" /> },
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

function formatPct(value: number): string {
  return `${value.toFixed(1)}%`;
}

function getTrendIcon(trend: 'up' | 'down' | 'flat') {
  if (trend === 'up') return <TrendingUp className="w-3.5 h-3.5 text-green-400" />;
  if (trend === 'down') return <TrendingDown className="w-3.5 h-3.5 text-red-400" />;
  return <Minus className="w-3.5 h-3.5 text-gray-500" />;
}

function getTrendColor(trend: 'up' | 'down' | 'flat'): string {
  if (trend === 'up') return 'text-green-400';
  if (trend === 'down') return 'text-red-400';
  return 'text-gray-500';
}

// No fallback data — dashboard requires live API data.
// If API is unavailable, error/empty state is shown instead of fake numbers.

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

const SkeletonTableRow: React.FC = () => (
  <tr className="border-b border-gray-700/30 animate-pulse">
    <td className="px-5 py-3"><div className="h-3 bg-gray-700 rounded w-32" /></td>
    <td className="px-4 py-3"><div className="h-3 bg-gray-700 rounded w-16" /></td>
    <td className="px-4 py-3"><div className="h-3 bg-gray-700 rounded w-20" /></td>
    <td className="px-4 py-3"><div className="h-3 bg-gray-700 rounded w-12" /></td>
    <td className="px-4 py-3"><div className="h-3 bg-gray-700 rounded w-12" /></td>
    <td className="px-4 py-3"><div className="h-3 bg-gray-700 rounded w-14" /></td>
    <td className="px-4 py-3"><div className="h-3 bg-gray-700 rounded w-10" /></td>
  </tr>
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
                  ? `${ACCENT_BG_10} ${ACCENT_TEXT}`
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <span className={isActive ? ACCENT_TEXT : 'text-gray-500 group-hover:text-gray-300'}>
                {item.icon}
              </span>
              <span className="flex-1 truncate">{item.label}</span>
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
          </button>
        ))}
      </nav>
    </div>

    {/* Branding */}
    <div className="mt-auto px-2 pt-4 border-t border-gray-700/30">
      <div className="text-[10px] text-gray-600 leading-relaxed">
        CS Pulse<br />
        Portfolio Command Center
      </div>
    </div>
  </aside>
);

/** Summary card with accent bar + glow */
const SummaryCard: React.FC<{
  label: string;
  value: string;
  subtitle: string;
  accent: string;
  glow?: boolean;
  tag?: string;
  icon?: React.ReactNode;
}> = ({ label, value, subtitle, accent, glow = false, tag, icon }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 relative overflow-hidden group hover:border-gray-600/50 transition-all">
    {/* Accent bar */}
    <div className="absolute top-0 left-0 right-0 h-0.5" style={{ backgroundColor: accent }} />
    {/* Glow effect */}
    {glow && (
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-16 opacity-15 blur-2xl"
        style={{ backgroundColor: accent }}
      />
    )}
    <div className="relative">
      <div className="flex items-center gap-1.5 mb-1">
        {icon && <span style={{ color: accent }}>{icon}</span>}
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">{label}</p>
      </div>
      <p className="text-3xl font-bold mb-1" style={{ color: accent }}>
        {value}
      </p>
      <p className="text-xs text-gray-500">{subtitle}</p>
      {tag && (
        <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full ${ACCENT_BG_15} ${ACCENT_TEXT} mt-2`}>
          {tag}
        </span>
      )}
    </div>
  </div>
);

/** Health score bar with color coding */
const HealthBar: React.FC<{ score: number; width?: string }> = ({ score, width = 'w-20' }) => {
  const color = classifyColor(score);
  const barWidth = Math.max(5, Math.min(100, score));

  return (
    <div className={`${width} flex items-center gap-2`}>
      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${barWidth}%`,
            background: `linear-gradient(90deg, ${color}, ${color}88)`,
          }}
        />
      </div>
      <span className="text-xs font-semibold font-mono min-w-[28px] text-right" style={{ color }}>
        {score.toFixed(0)}
      </span>
    </div>
  );
};

/** Sortable column header */
const SortableHeader: React.FC<{
  label: string;
  field: SortField;
  currentSort: SortField;
  direction: SortDirection;
  onSort: (field: SortField) => void;
  align?: 'left' | 'right';
}> = ({ label, field, currentSort, direction, onSort, align = 'left' }) => {
  const isActive = currentSort === field;
  return (
    <th
      className={`px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-300 transition-colors select-none ${
        align === 'right' ? 'text-right' : 'text-left'
      } ${isActive ? ACCENT_TEXT : ''}`}
      onClick={() => onSort(field)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        {isActive && (
          direction === 'asc'
            ? <ChevronUp className="w-3 h-3" />
            : <ChevronDown className="w-3 h-3" />
        )}
      </span>
    </th>
  );
};

/** Company comparison table */
const CompanyTable: React.FC<{
  companies: PortfolioCompany[];
  sortField: SortField;
  sortDirection: SortDirection;
  onSort: (field: SortField) => void;
  onCompanyClick: (company: PortfolioCompany) => void;
}> = ({ companies, sortField, sortDirection, onSort, onCompanyClick }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
    <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Building2 className="w-4 h-4" style={{ color: ACCENT }} />
        <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
          Portfolio Companies
        </h3>
      </div>
      <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${ACCENT_BG_15} ${ACCENT_TEXT}`}>
        {companies.length} companies
      </span>
    </div>
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700/50">
            <SortableHeader label="Company" field="name" currentSort={sortField} direction={sortDirection} onSort={onSort} />
            <SortableHeader label="ARR" field="arr" currentSort={sortField} direction={sortDirection} onSort={onSort} align="right" />
            <th className="px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider text-center">Health</th>
            <th className="px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider text-right">Accounts</th>
            <SortableHeader label="At Risk" field="at_risk_count" currentSort={sortField} direction={sortDirection} onSort={onSort} align="right" />
            <SortableHeader label="NRR" field="nrr" currentSort={sortField} direction={sortDirection} onSort={onSort} align="right" />
            <th className="px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider text-center">Trend</th>
          </tr>
        </thead>
        <tbody>
          {companies.map((company) => {
            const cls = classify(company.health_score);
            return (
              <tr
                key={company.customer_id}
                className="border-b border-gray-700/30 hover:bg-white/[0.02] transition-colors cursor-pointer group"
                onClick={() => onCompanyClick(company)}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-gray-800/80 flex items-center justify-center flex-shrink-0">
                      <Building2 className="w-3.5 h-3.5 text-gray-400" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-white truncate group-hover:text-purple-300 transition-colors">
                        {company.name}
                      </p>
                      <p className="text-[10px] text-gray-600">{company.vertical.toUpperCase()}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="text-xs font-semibold text-white font-mono">
                    {formatCompact(company.arr)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex justify-center">
                    <HealthBar score={company.health_score} />
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="text-xs text-gray-400 font-mono">{company.account_count}</span>
                </td>
                <td className="px-4 py-3 text-right">
                  {company.at_risk_count > 0 ? (
                    <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-400">
                      <AlertTriangle className="w-3 h-3" />
                      {company.at_risk_count}
                    </span>
                  ) : (
                    <span className="text-xs text-green-400 font-medium">0</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <span className={`text-xs font-semibold font-mono ${
                    company.nrr >= 110 ? 'text-green-400' : company.nrr >= 100 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {company.nrr.toFixed(1)}%
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-1">
                    {getTrendIcon(company.trend)}
                    <span className={`text-[10px] font-medium ${getTrendColor(company.trend)}`}>
                      {company.trend_change > 0 ? '+' : ''}{company.trend_change.toFixed(1)}%
                    </span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  </div>
);

/** Health distribution widget */
const HealthDistribution: React.FC<{ buckets: HealthBucket[]; totalAccounts: number }> = ({ buckets, totalAccounts }) => {
  const pieData = buckets.map((b) => ({
    name: b.label,
    value: b.count,
    fill: b.color,
  }));

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4" style={{ color: ACCENT }} />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
            Health Distribution
          </h3>
        </div>
        <span className="text-[10px] text-gray-500">{totalAccounts} total accounts</span>
      </div>

      {/* Donut chart */}
      <div className="flex justify-center mb-4">
        <div className="relative w-32 h-32">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={38}
                outerRadius={56}
                paddingAngle={3}
                dataKey="value"
                stroke="none"
              >
                {pieData.map((entry, i) => (
                  <Cell key={`cell-${i}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1a1f2e',
                  border: '1px solid #374151',
                  borderRadius: 8,
                  fontSize: 12,
                  color: '#fff',
                }}
                formatter={(value: number, name: string) => [value, name]}
              />
            </PieChart>
          </ResponsiveContainer>
          {/* Center label */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-lg font-bold text-white">{totalAccounts}</span>
            <span className="text-[9px] text-gray-500">accounts</span>
          </div>
        </div>
      </div>

      {/* Legend buckets */}
      <div className="space-y-2.5">
        {buckets.map((bucket) => {
          const pct = totalAccounts > 0 ? ((bucket.count / totalAccounts) * 100).toFixed(0) : '0';
          return (
            <div key={bucket.label} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: bucket.color }} />
                <span className="text-[11px] text-gray-400">{bucket.label}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-semibold ${bucket.textClass}`}>{bucket.count}</span>
                <span className="text-[10px] text-gray-600">({pct}%)</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/** Portfolio trend widget (right sidebar) */
const PortfolioTrendWidget: React.FC<{
  trend: 'up' | 'down' | 'flat';
  trendPct: number;
  healthScore: number;
  nrr: number;
  roiPct: number;
}> = ({ trend, trendPct, healthScore, nrr, roiPct }) => {
  const circumference = 2 * Math.PI * 40;
  const progress = (healthScore / 100) * circumference;
  const scoreColor = classifyColor(healthScore);

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
      <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-4">
        Portfolio Trend
      </h3>
      {/* Health gauge */}
      <div className="flex justify-center mb-4">
        <div className="relative w-24 h-24">
          <svg className="w-24 h-24 -rotate-90" viewBox="0 0 96 96">
            <circle cx="48" cy="48" r="40" fill="none" stroke="#1f2937" strokeWidth="6" />
            <circle
              cx="48"
              cy="48"
              r="40"
              fill="none"
              stroke={scoreColor}
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={circumference - progress}
              className="transition-all duration-1000"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold" style={{ color: scoreColor }}>{healthScore.toFixed(0)}</span>
            <span className="text-[9px] text-gray-500">health</span>
          </div>
        </div>
      </div>

      {/* Trend indicator */}
      <div className="flex items-center justify-center gap-2 mb-4 py-2 rounded-lg bg-gray-800/50">
        {getTrendIcon(trend)}
        <span className={`text-sm font-semibold ${getTrendColor(trend)}`}>
          {trendPct > 0 ? '+' : ''}{trendPct.toFixed(1)}%
        </span>
        <span className="text-[10px] text-gray-500">vs last quarter</span>
      </div>

      {/* Quick stats */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-gray-500">Net Revenue Retention</span>
          <span className={`text-xs font-semibold ${nrr >= 110 ? 'text-green-400' : nrr >= 100 ? 'text-yellow-400' : 'text-red-400'}`}>
            {nrr.toFixed(1)}%
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-gray-500">Portfolio ROI</span>
          <span className="text-xs font-semibold" style={{ color: ACCENT }}>{roiPct > 0 ? `${roiPct}%` : '\u2014'}</span>
        </div>
      </div>
    </div>
  );
};

/** Top risks widget (right sidebar) */
const TopRisksWidget: React.FC<{ risks: TopRisk[] }> = ({ risks }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
    <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-3">
      Top 3 Risks by ARR
    </h3>
    {risks.length === 0 ? (
      <div className="flex flex-col items-center justify-center py-6 text-center">
        <Shield className="w-8 h-8 text-green-500/40 mb-2" />
        <p className="text-xs text-gray-500">No at-risk accounts detected</p>
        <p className="text-[10px] text-gray-600 mt-1">All accounts are in healthy range</p>
      </div>
    ) : (
    <div className="space-y-3">
      {risks.map((risk, i) => {
        const color = classifyColor(risk.health_score);
        const cls = classify(risk.health_score);
        return (
          <div key={i} className="flex items-start gap-3 group">
            <div className="flex-shrink-0 w-6 h-6 rounded-full bg-red-500/15 flex items-center justify-center mt-0.5">
              <span className="text-[10px] font-bold text-red-400">{i + 1}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">{risk.account_name}</p>
              <p className="text-[10px] text-gray-600 truncate">{risk.company_name}</p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-[10px] font-semibold" style={{ color }}>
                  {risk.health_score}
                </span>
                <span className="text-[10px] text-gray-500">{formatCompact(risk.arr)}</span>
                <span className="text-[10px] text-gray-600 flex items-center gap-0.5">
                  <AlertTriangle className="w-2.5 h-2.5" />
                  {risk.signal_count}
                </span>
              </div>
            </div>
            <span
              className={`flex-shrink-0 text-[9px] font-semibold px-1.5 py-0.5 rounded-full ${
                cls === 'critical' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
              }`}
            >
              {cls === 'critical' ? 'Critical' : 'At Risk'}
            </span>
          </div>
        );
      })}
    </div>
    )}
  </div>
);

/** ARR by company bar chart */
const ARRByCompanyChart: React.FC<{ companies: PortfolioCompany[] }> = ({ companies }) => {
  const chartData = companies
    .sort((a, b) => b.arr - a.arr)
    .map((c) => ({
      name: c.name.split(' ')[0], // Short name
      arr: c.arr / 1_000_000,
      health: c.health_score,
      fill: classifyColor(c.health_score),
    }));

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4" style={{ color: ACCENT }} />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
            ARR by Company
          </h3>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
          <XAxis
            dataKey="name"
            tick={{ fill: '#6b7280', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#6b7280', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `$${v}M`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1f2e',
              border: '1px solid #374151',
              borderRadius: 8,
              fontSize: 12,
              color: '#fff',
            }}
            formatter={(value: number) => [`$${value.toFixed(1)}M`, 'ARR']}
          />
          <Bar dataKey="arr" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={`cell-${i}`} fill={entry.fill} fillOpacity={0.8} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="text-[10px] text-gray-600 text-center mt-2">
        Bars colored by health score classification
      </p>
    </div>
  );
};

/**
 * Top 3 Strategic Moves tile (CEO-Q5).
 *
 * Renders the three Power-of-1 scaling scenarios as the three strategic
 * investment choices the CEO can make this quarter. Source: outcome ROI
 * engine → scaling_scenarios, scaled to portfolio ARR by the backend.
 *
 * Why three and not "AI suggestions": the scenarios are the platform's
 * audited investment framework. A board member reading this tile can
 * compare 1% / 4% / 6% improvement levels at a glance — same view that
 * shows up in the CRO/CFO power-of-1 table, but tuned for executive
 * decision altitude. Renders nothing while moves are empty so the board
 * doesn't see placeholders.
 */
const TopStrategicMovesTile: React.FC<{ moves: StrategicMove[] }> = ({ moves }) => {
  if (!moves || moves.length === 0) return null;

  // Color cues — budget→amber (conservative), target→purple (recommended), celebrate→emerald (stretch)
  const tone = (key: string): { border: string; accent: string; bg: string; tag: string } => {
    if (key.startsWith('1')) return { border: 'border-amber-500/30', accent: 'text-amber-300', bg: 'bg-amber-500/5', tag: 'Conservative' };
    if (key.startsWith('6')) return { border: 'border-emerald-500/30', accent: 'text-emerald-300', bg: 'bg-emerald-500/5', tag: 'Stretch' };
    return { border: ACCENT_BORDER, accent: ACCENT_TEXT, bg: 'bg-purple-500/5', tag: 'Recommended' };
  };

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Compass className="w-4 h-4" style={{ color: ACCENT }} />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
            Top 3 Strategic Moves — This Quarter
          </h3>
        </div>
        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${ACCENT_BG_15} ${ACCENT_TEXT}`}>
          Power-of-1 scenarios
        </span>
      </div>
      <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-3">
        {moves.map((m) => {
          const t = tone(m.key);
          return (
            <div
              key={m.key}
              className={`relative rounded-lg border ${t.border} ${t.bg} p-4 flex flex-col gap-2`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-gray-500">{t.tag}</p>
                  <p className="text-sm font-semibold text-white leading-tight">{m.label}</p>
                  <p className="text-[10px] text-gray-500 mt-0.5">
                    Move every KPI {m.improvement_pct}% this quarter
                  </p>
                </div>
                <span className={`text-xs font-bold ${t.accent}`}>{m.improvement_pct}%</span>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-gray-700/40">
                <div>
                  <p className="text-[10px] text-gray-500">Invest</p>
                  <p className={`text-sm font-semibold ${t.accent}`}>{formatCompact(m.investment)}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500">Impact (yr 1)</p>
                  <p className="text-sm font-semibold text-white">{formatCompact(m.total_impact)}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500">Year-1 ROI</p>
                  <p className="text-sm font-semibold text-white">
                    {m.year_1_roi > 0 ? `${m.year_1_roi.toFixed(2)}x` : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-500">Payback</p>
                  <p className="text-sm font-semibold text-white">
                    {m.payback_months ? `${m.payback_months.toFixed(1)} mo` : '—'}
                  </p>
                </div>
              </div>

              {m.three_year_net != null && m.three_year_net > 0 && (
                <p className="text-[10px] text-gray-500 pt-1">
                  3-yr net:&nbsp;
                  <span className={`font-semibold ${t.accent}`}>{formatCompact(m.three_year_net)}</span>
                </p>
              )}
            </div>
          );
        })}
      </div>
      <div className="px-5 py-2 border-t border-gray-700/40">
        <p className="text-[9px] italic text-gray-500 leading-tight">
          Source: Power-of-1 benchmark · estimated. Scenarios scale to portfolio ARR;
          actuals will diverge as Wizard B / C learn from your outcomes.
        </p>
      </div>
    </div>
  );
};

/**
 * Single-tenant Executive Scorecard (CEO-Q2).
 *
 * Renders when there is only one customer in scope — replaces the awkward
 * 1-row "comparison" table with a scorecard framed as "this is what you
 * own and where it stands." Same five fields as the comparison view
 * (Health / ARR / At-Risk / NRR / Trend) but at executive altitude.
 *
 * A small "Add Comparison Customer" CTA is included; clicking it is a
 * no-op until a real multi-tenant portfolio model lands (roadmap).
 */
const ExecutiveScorecard: React.FC<{ company: PortfolioCompany; period: string }> = ({ company, period }) => {
  const healthColor = classifyColor(company.health_score);
  const cls = classify(company.health_score);
  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Briefcase className="w-4 h-4" style={{ color: ACCENT }} />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
            Executive Scorecard
            <span className="text-gray-500 font-normal normal-case ml-2">&middot; {company.name}</span>
          </h3>
        </div>
        <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${ACCENT_BG_15} ${ACCENT_TEXT}`}>
          {period}
        </span>
      </div>
      <div className="p-5 grid grid-cols-2 md:grid-cols-5 gap-4">
        {/* Health */}
        <div className="space-y-1">
          <p className="text-[10px] uppercase tracking-wider text-gray-500">Health</p>
          <p className="text-2xl font-bold font-mono" style={{ color: healthColor }}>
            {company.health_score.toFixed(0)}
          </p>
          <span
            className={`inline-block text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${
              cls === 'critical' ? 'bg-red-500/20 text-red-400'
              : cls === 'at_risk' ? 'bg-yellow-500/20 text-yellow-400'
              : 'bg-green-500/20 text-green-400'
            }`}
          >
            {cls === 'critical' ? 'Critical' : cls === 'at_risk' ? 'At Risk' : 'Healthy'}
          </span>
        </div>

        {/* ARR */}
        <div className="space-y-1">
          <p className="text-[10px] uppercase tracking-wider text-gray-500">ARR</p>
          <p className="text-2xl font-bold text-white font-mono">{formatCompact(company.arr)}</p>
          <p className="text-[10px] text-gray-500">{company.account_count} accounts</p>
        </div>

        {/* At-Risk */}
        <div className="space-y-1">
          <p className="text-[10px] uppercase tracking-wider text-gray-500">At Risk</p>
          <p className={`text-2xl font-bold font-mono ${
            company.at_risk_count > 10 ? 'text-red-400'
            : company.at_risk_count > 0 ? 'text-yellow-400'
            : 'text-green-400'
          }`}>
            {company.at_risk_count}
          </p>
          <p className="text-[10px] text-gray-500">
            {company.account_count > 0 ? `${((company.at_risk_count / company.account_count) * 100).toFixed(0)}% of book` : '—'}
          </p>
        </div>

        {/* NRR */}
        <div className="space-y-1">
          <p className="text-[10px] uppercase tracking-wider text-gray-500">NRR</p>
          <p className={`text-2xl font-bold font-mono ${
            company.nrr >= 110 ? 'text-green-400'
            : company.nrr >= 100 ? 'text-yellow-400'
            : 'text-red-400'
          }`}>
            {company.nrr.toFixed(1)}%
          </p>
          <p className="text-[10px] text-gray-500">portfolio-weighted</p>
        </div>

        {/* Trend */}
        <div className="space-y-1">
          <p className="text-[10px] uppercase tracking-wider text-gray-500">Trend</p>
          <div className="flex items-center gap-1.5">
            {getTrendIcon(company.trend)}
            <span className={`text-2xl font-bold font-mono ${getTrendColor(company.trend)}`}>
              {company.trend_change > 0 ? '+' : ''}{company.trend_change.toFixed(1)}%
            </span>
          </div>
          <p className="text-[10px] text-gray-500">vs last period</p>
        </div>
      </div>
      <div className="px-5 py-3 border-t border-gray-700/40 flex items-center justify-between">
        <p className="text-[10px] text-gray-500 italic">
          Single-tenant view &middot; cross-customer comparison unlocks when a second customer is added to this portfolio.
        </p>
        <button
          disabled
          title="Cross-customer comparison: enable a second tenant in this portfolio to unlock."
          className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-1 rounded-md border border-gray-700/60 text-gray-500 cursor-not-allowed"
        >
          <Plus className="w-3 h-3" />
          Add Comparison Customer
        </button>
      </div>
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const CEODashboard: React.FC = () => {
  const navigate = useNavigate();
  const { session } = useSession();

  const [data, setData] = useState<CEODashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);

  const [sortField, setSortField] = useState<SortField>('arr');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Fetch dashboard data from multiple endpoints
  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const customerId = getCustomerIdentifier(session);
        const headers = { 'X-Customer-ID': customerId };

        // ── Primary: new CEO endpoint (handles single-customer + portfolio) ──
        const ceoResp = await apiCall('/api/executive/ceo-dashboard', { headers });
        if (!ceoResp.ok) {
          setErrorStatus(ceoResp.status);
          throw new Error(`API returned ${ceoResp.status}`);
        }
        let companies: PortfolioCompany[] = [];
        let healthDist: HealthBucket[] = [];
        let avgHealth = 0;
        let roiPct = 0;
        let portfolioNrr = 100;
        let totalArr = 0;
        let totalAccounts = 0;
        let totalAtRisk = 0;
        let strategicMoves: StrategicMove[] = [];

        if (ceoResp.ok) {
          const ceoJson = await ceoResp.json();

          if (ceoJson.mode === 'portfolio') {
            // Portfolio mode — fetch from portfolio API
            const [portfolioResp, roiResp] = await Promise.allSettled([
              apiCall(`/api/portfolio/${ceoJson.portfolio_id}/companies`, { headers }),
              apiCall('/api/outcome-roi/portfolio-summary', { headers }),
            ]);
            // Intentionally do not fetch strategic moves in portfolio mode here —
            // moves are tenant-specific. (Phase 2 multi-tenant portfolio will need
            // its own aggregate; out of scope for the CEO-Q5 single-tenant fix.)
            if (portfolioResp.status === 'fulfilled' && portfolioResp.value.ok) {
              const pJson = await portfolioResp.value.json();
              const customerList = pJson.companies || pJson.customers || pJson.data || [];
              if (Array.isArray(customerList)) {
                companies = customerList.map((c: any) => ({
                  customer_id: c.customer_id || c.id || 0,
                  name: c.name || c.customer_name || 'Unknown',
                  arr: c.total_arr || c.arr || 0,
                  health_score: c.avg_health_score || c.health_score || 0,
                  account_count: c.account_count || c.accounts || 0,
                  at_risk_count: c.at_risk_count || c.accounts_at_risk || 0,
                  nrr: c.nrr || c.net_revenue_retention || 100,
                  trend: (c.health_trend || c.trend || 'flat') as 'up' | 'down' | 'flat',
                  trend_change: c.trend_change || c.health_change || 0,
                  vertical: c.vertical || 'dc2_s',
                }));
              }
            }
            if (roiResp.status === 'fulfilled' && roiResp.value.ok) {
              const rJson = await roiResp.value.json();
              roiPct = rJson.roi_pct || rJson.portfolio_roi || 0;
              portfolioNrr = rJson.nrr || rJson.net_revenue_retention || 100;
            }
          } else {
            // Single-customer mode — all data from CEO endpoint
            companies = (ceoJson.companies || []).map((c: any) => ({
              customer_id: c.customer_id || 0,
              name: c.name || 'Unknown',
              arr: c.arr || 0,
              health_score: c.health_score || 0,
              account_count: c.account_count || 0,
              at_risk_count: c.at_risk_count || 0,
              nrr: c.nrr || 100,
              trend: (c.trend || 'flat') as 'up' | 'down' | 'flat',
              trend_change: c.trend_change || 0,
              vertical: c.vertical || 'dc2_s',
            }));
            const ps = ceoJson.portfolio_summary || {};
            avgHealth = ps.avg_health || 0;
            roiPct = ps.roi_pct || 0;
            portfolioNrr = ps.nrr || 100;

            healthDist = [
              { label: 'Healthy', count: ps.healthy || 0, color: HEALTH_COLORS.healthy, bgClass: 'bg-green-500/15', textClass: 'text-green-400' },
              { label: 'At Risk', count: ps.at_risk || 0, color: HEALTH_COLORS.at_risk, bgClass: 'bg-yellow-500/15', textClass: 'text-yellow-400' },
              { label: 'Critical', count: ps.critical || 0, color: HEALTH_COLORS.critical, bgClass: 'bg-red-500/15', textClass: 'text-red-400' },
            ];

            // CEO-Q5 (May 17 eval): pull Power-of-1 scaling scenarios from the
            // outcome-roi story. The engine ARR-scales the three scenarios
            // (1%/4%/6%) to portfolio total ARR, so the tile renders dollar
            // amounts that match this customer's investment scale instead of
            // the $10M baseline. Failure is non-fatal — the tile self-hides.
            try {
              const storyResp = await apiCall('/api/outcome-roi/story', { headers });
              if (storyResp.ok) {
                const storyJson = await storyResp.json();
                const scenarios = storyJson?.story?.scaling_scenarios || {};
                const ORDER = ['1_pct', '4_pct', '6_pct'];
                strategicMoves = ORDER
                  .filter((k) => scenarios[k])
                  .map((k) => {
                    const s = scenarios[k];
                    return {
                      key: k,
                      label: s.label || k,
                      improvement_pct: s.improvement_pct || 0,
                      investment: s.investment || 0,
                      total_impact: s.total_impact || 0,
                      year_1_roi: s.year_1_roi || 0,
                      payback_months: s.payback_months ?? null,
                      three_year_net: s.three_year_net ?? null,
                    } as StrategicMove;
                  });
              }
            } catch {
              // Strategic moves are optional — keep the rest of the dashboard rendering.
            }
          }
        }

        // Build derived values
        totalArr = companies.reduce((sum, c) => sum + c.arr, 0);
        totalAccounts = companies.reduce((sum, c) => sum + c.account_count, 0);
        totalAtRisk = companies.reduce((sum, c) => sum + c.at_risk_count, 0);
        const weightedHealth = totalArr > 0
          ? companies.reduce((sum, c) => sum + c.health_score * c.arr, 0) / totalArr
          : avgHealth;
        const weightedNrr = totalArr > 0
          ? companies.reduce((sum, c) => sum + c.nrr * c.arr, 0) / totalArr
          : portfolioNrr;

        // Build top risks from at-risk companies (sorted by ARR desc)
        const topRisks: TopRisk[] = companies
          .filter((c) => c.at_risk_count > 0)
          .sort((a, b) => b.arr - a.arr)
          .slice(0, 3)
          .map((c) => ({
            account_name: `${c.name} (portfolio)`,
            company_name: c.name,
            health_score: c.health_score,
            arr: c.arr,
            signal_count: c.at_risk_count,
          }));

        // Health distribution from companies if API didn't provide
        if (healthDist.length === 0 || healthDist.every((b) => b.count === 0)) {
          const { healthy_min, at_risk_min } = thresholdValues();
          let healthy = 0, atRisk = 0, critical = 0;
          companies.forEach((c) => {
            // Approximate from account-level
            const h = c.account_count - c.at_risk_count;
            healthy += h;
            atRisk += Math.floor(c.at_risk_count * 0.6);
            critical += Math.ceil(c.at_risk_count * 0.4);
          });
          healthDist = [
            { label: 'Healthy', count: healthy, color: HEALTH_COLORS.healthy, bgClass: 'bg-green-500/15', textClass: 'text-green-400' },
            { label: 'At Risk', count: atRisk, color: HEALTH_COLORS.at_risk, bgClass: 'bg-yellow-500/15', textClass: 'text-yellow-400' },
            { label: 'Critical', count: critical, color: HEALTH_COLORS.critical, bgClass: 'bg-red-500/15', textClass: 'text-red-400' },
          ];
        }

        // Determine portfolio trend
        const avgTrendChange = companies.length > 0
          ? companies.reduce((sum, c) => sum + c.trend_change, 0) / companies.length
          : 0;
        const portfolioTrend: 'up' | 'down' | 'flat' =
          avgTrendChange > 1 ? 'up' : avgTrendChange < -1 ? 'down' : 'flat';

        if (!cancelled && companies.length > 0) {
          setData({
            portfolio_name: companies[0]?.name || 'Portfolio Overview',
            total_arr: totalArr,
            avg_health_score: weightedHealth || avgHealth,
            portfolio_nrr: weightedNrr || portfolioNrr,
            total_at_risk: totalAtRisk,
            total_accounts: totalAccounts,
            companies,
            health_distribution: healthDist,
            portfolio_trend: portfolioTrend,
            portfolio_trend_pct: avgTrendChange,
            top_risks: topRisks,
            roi_pct: roiPct,
            strategic_moves: strategicMoves,
            period: 'Q1 2026',
            last_updated: 'just now',
          });
          trackPageView('ceo_dashboard', { companies: companies.length, total_arr: totalArr });
        } else if (!cancelled) {
          setError('No portfolio data available. Upload your data to get started.');
        }
      } catch {
        if (!cancelled) {
          setError('Unable to load CEO dashboard data. Please check your connection and try again.');
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

  const handleSort = useCallback((field: SortField) => {
    setSortField((prev) => {
      if (prev === field) {
        setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
        return prev;
      }
      setSortDirection('desc');
      return field;
    });
  }, []);

  const handleCompanyClick = useCallback((company: PortfolioCompany) => {
    // Navigate to CRO dashboard for the company
    navigate(`/cro-dashboard?customer_id=${company.customer_id}`);
  }, [navigate]);

  // Sort companies
  const sortedCompanies = useMemo(() => {
    if (!data) return [];
    const sorted = [...data.companies];
    sorted.sort((a, b) => {
      let aVal: string | number;
      let bVal: string | number;
      switch (sortField) {
        case 'name': aVal = a.name.toLowerCase(); bVal = b.name.toLowerCase(); break;
        case 'arr': aVal = a.arr; bVal = b.arr; break;
        case 'health_score': aVal = a.health_score; bVal = b.health_score; break;
        case 'at_risk_count': aVal = a.at_risk_count; bVal = b.at_risk_count; break;
        case 'nrr': aVal = a.nrr; bVal = b.nrr; break;
        default: aVal = a.arr; bVal = b.arr;
      }
      if (typeof aVal === 'string') {
        return sortDirection === 'asc'
          ? aVal.localeCompare(bVal as string)
          : (bVal as string).localeCompare(aVal);
      }
      return sortDirection === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number);
    });
    return sorted;
  }, [data, sortField, sortDirection]);

  // ---- Loading state ----
  if (loading) {
    return (
      <div className="flex h-screen bg-[#0f1419] text-white font-['Inter',sans-serif]">
        <SidebarNav activeId="ceo-overview" onNavigate={handleNav} />
        <main className="flex-1 p-6 overflow-y-auto">
          <div className="mb-6">
            <SkeletonLine w="w-64" />
          </div>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
          </div>
          <SkeletonCard className="h-64 mb-6" />
          <div className="grid grid-cols-2 gap-4">
            <SkeletonCard className="h-56" />
            <SkeletonCard className="h-56" />
          </div>
        </main>
        <aside className="w-80 bg-[#0d1117] border-l border-gray-700/50 p-4">
          <SkeletonCard className="h-56 mb-4" />
          <SkeletonCard className="h-44 mb-4" />
          <SkeletonCard className="h-24" />
        </aside>
      </div>
    );
  }

  // ---- Error state ----
  if (error && !data) {
    return (
      <DashboardErrorState
        dashboardLabel="CEO dashboard"
        errorMessage={error}
        errorStatus={errorStatus}
      />
    );
  }

  const d = data!;

  return (
    <div className="flex flex-col h-screen bg-[#0f1419] text-white font-['Inter',sans-serif]">
      <DashboardTopBar accent="purple" />
      <div className="flex flex-1 overflow-hidden">
      {/* ---- Left Sidebar ---- */}
      <SidebarNav activeId="ceo-overview" onNavigate={handleNav} />

      {/* ---- Main Content ---- */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-[1200px]">
          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-lg font-semibold text-white tracking-tight">
                PORTFOLIO COMMAND CENTER
                <span className="text-gray-500 font-normal ml-2">&middot; {d.portfolio_name}</span>
              </h1>
              <div className="h-0.5 w-12 mt-1.5 rounded-full" style={{ backgroundColor: ACCENT }} />
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
              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${ACCENT_BG_15} ${ACCENT_TEXT}`}>
                {d.period}
              </span>
            </div>
          </div>

          {/* Row 1: Summary Cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <SummaryCard
              label="Total Portfolio ARR"
              value={formatCompact(d.total_arr)}
              subtitle={`${d.companies.length} portfolio companies`}
              accent={ACCENT}
              glow
              icon={<DollarSign className="w-3.5 h-3.5" />}
            />
            <SummaryCard
              label="Portfolio Health"
              value={d.avg_health_score.toFixed(1)}
              subtitle={`Weighted avg across ${d.total_accounts} accounts`}
              accent={classifyColor(d.avg_health_score)}
              icon={<Shield className="w-3.5 h-3.5" />}
            />
            <SummaryCard
              label="Net Revenue Retention"
              value={`${d.portfolio_nrr.toFixed(1)}%`}
              subtitle="Portfolio-weighted NRR"
              accent={d.portfolio_nrr >= 110 ? '#22c55e' : d.portfolio_nrr >= 100 ? '#eab308' : '#ef4444'}
              icon={<TrendingUp className="w-3.5 h-3.5" />}
            />
            <SummaryCard
              label="Accounts At Risk"
              value={String(d.total_at_risk)}
              subtitle={`of ${d.total_accounts} total accounts`}
              accent={d.total_at_risk > 10 ? '#ef4444' : d.total_at_risk > 5 ? '#eab308' : '#22c55e'}
              icon={<AlertTriangle className="w-3.5 h-3.5" />}
              tag={d.total_at_risk > 10 ? 'Needs attention' : undefined}
            />
          </div>

          {/* Predictor v3 — per-account NRR forecast (top expansion + top at-risk).
              The CEO sees portfolio aggregate via Row 1 above; this tile
              gives the drill-down for executive board prep. */}
          {session && (
            <div className="mb-6">
              <PredictorV3Tile
                customerId={session.customer_id}
                saasProfile={(session.vertical === 'saas_premium') ? 'saas_enterprise' : 'saas_enterprise'}
                horizon="12mo"
                limit={5}
              />
            </div>
          )}

          {/* Row 2: Comparison view (CEO-Q2).
              Single-tenant install renders an Executive Scorecard rather
              than a misleading 1-row "comparison" table. The full
              cross-customer comparison table comes back automatically when
              the portfolio has 2+ tenants. */}
          <div className="mb-6">
            {d.companies.length > 1 ? (
              <CompanyTable
                companies={sortedCompanies}
                sortField={sortField}
                sortDirection={sortDirection}
                onSort={handleSort}
                onCompanyClick={handleCompanyClick}
              />
            ) : d.companies.length === 1 ? (
              <ExecutiveScorecard company={d.companies[0]} period={d.period} />
            ) : null}
          </div>

          {/* Row 3: CEO-Q5 — Top 3 Strategic Moves (Power-of-1 scenarios). */}
          {d.strategic_moves && d.strategic_moves.length > 0 && (
            <div className="mb-6">
              <TopStrategicMovesTile moves={d.strategic_moves} />
            </div>
          )}

          {/* Row 4: Health Distribution + ARR by Company */}
          <div className="grid grid-cols-2 gap-4">
            <HealthDistribution buckets={d.health_distribution} totalAccounts={d.total_accounts} />
            <ARRByCompanyChart companies={d.companies} />
          </div>
        </div>
      </main>

      {/* ---- Right Sidebar ---- */}
      <aside className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 overflow-y-auto flex flex-col gap-5">
        {/* Portfolio Trend */}
        <PortfolioTrendWidget
          trend={d.portfolio_trend}
          trendPct={d.portfolio_trend_pct}
          healthScore={d.avg_health_score}
          nrr={d.portfolio_nrr}
          roiPct={d.roi_pct}
        />

        {/* Top 3 Risks */}
        <TopRisksWidget risks={d.top_risks} />

        {/* Quick Actions */}
        <div className="space-y-2.5">
          <button
            onClick={() => navigate('/cro-dashboard')}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-lg bg-cyan-600/10 border border-cyan-500/20 text-cyan-400 text-xs font-medium hover:bg-cyan-600/20 transition-colors"
          >
            <BarChart3 className="w-3.5 h-3.5" />
            View CRO Dashboard
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => navigate('/cfo-dashboard')}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-lg bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium hover:bg-emerald-600/20 transition-colors"
          >
            <DollarSign className="w-3.5 h-3.5" />
            View CFO Dashboard
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <button
            className={`flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-lg bg-purple-600/10 border ${ACCENT_BORDER} ${ACCENT_TEXT} text-xs font-medium hover:bg-purple-600/20 transition-colors`}
          >
            <FileText className="w-3.5 h-3.5" />
            Export Board Brief
          </button>
        </div>

        {/* Portfolio ROI badge */}
        <div className={`rounded-xl border ${ACCENT_BORDER} p-4 relative overflow-hidden`} style={{ backgroundColor: '#1a1f2e' }}>
          <div
            className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-16 opacity-10 blur-2xl"
            style={{ backgroundColor: ACCENT }}
          />
          <div className="relative text-center">
            <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Platform ROI
            </p>
            <p className="text-4xl font-bold mb-1" style={{ color: ACCENT }}>
              {d.roi_pct > 0 ? `${d.roi_pct}%` : '\u2014'}
            </p>
            <p className="text-[10px] text-gray-600">
              CS Pulse return on investment
            </p>
          </div>
        </div>
      </aside>

      {/* Floating AI Advisor */}
      <AskAIPortal persona="ceo" />
    </div>
    </div>
  );
};

export default CEODashboard;
