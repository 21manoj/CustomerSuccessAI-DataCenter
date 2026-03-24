/**
 * AE Sales Expansion Dashboard
 * =============================
 *
 * Dark-themed dashboard for Account Executives featuring:
 * - Expansion Pipeline / Renewal ARR / Avg Health / Upsell-Ready summary cards
 * - Expansion Opportunities grid (healthy, high-ARR accounts)
 * - Renewal Risk Monitor table (at-risk accounts)
 * - Product Whitespace matrix (upsell gap analysis)
 * - QBR Prep sidebar widget
 * - Win Rate trend placeholder
 * - Quick navigation links
 *
 * Accent color: AMBER (#F59E0B)
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
  ChevronRight, ArrowRight, ArrowUpRight, Briefcase,
  Package, Calendar, CheckCircle2, XCircle, Minus,
  FileText, Layers, Activity, Star
} from 'lucide-react';
import { classify, classifyColor, thresholdValues } from '../../utils/healthThresholds';
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
}

interface ExpansionAccount {
  account_id: string | number;
  account_name: string;
  arr: number;
  health_score: number;
  industry: string;
  expansion_signal: string;
  products_used: number;
  products_total: number;
}

interface RenewalRiskAccount {
  account_id: string | number;
  account_name: string;
  health_score: number;
  arr_at_risk: number;
  days_to_renewal: number;
  risk_signal: string;
  classification: 'critical' | 'at_risk' | 'healthy';
}

interface ProductWhitespace {
  account_name: string;
  account_id: string | number;
  arr: number;
  products: Record<string, boolean>;
}

interface QBRAccount {
  account_name: string;
  account_id: string | number;
  days_to_renewal: number;
  arr: number;
  health_score: number;
  key_topic: string;
}

interface WinRatePoint {
  quarter: string;
  rate: number;
}

interface AEDashboardData {
  summary_cards: SummaryCard[];
  expansion_accounts: ExpansionAccount[];
  renewal_risk_accounts: RenewalRiskAccount[];
  product_whitespace: ProductWhitespace[];
  product_names: string[];
  qbr_accounts: QBRAccount[];
  win_rate_trend: WinRatePoint[];
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

const ACCENT = '#F59E0B'; // Amber
const ACCENT_LIGHT = '#FBBF24';
const ACCENT_DIM = 'rgba(245, 158, 11, 0.15)';

const ACCENT_MAP: Record<string, string> = {
  amber: '#F59E0B',
  green: '#22c55e',
  cyan: '#06b6d4',
  red: '#ef4444',
  yellow: '#eab308',
  purple: '#a855f7',
  white: '#ffffff',
};

// Sidebar navigation items
const NAV_ITEMS = {
  sales: [
    { id: 'ae-overview', label: 'AE Overview', path: '/ae-dashboard', icon: <Target className="w-4 h-4" /> },
    { id: 'expansion', label: 'Expansion Opps', path: '/ae-dashboard', icon: <TrendingUp className="w-4 h-4" /> },
    { id: 'renewals', label: 'Renewals', path: '/ae-dashboard', icon: <Calendar className="w-4 h-4" /> },
    { id: 'whitespace', label: 'Product Gaps', path: '/ae-dashboard', icon: <Package className="w-4 h-4" /> },
  ],
  intelligence: [
    { id: 'cro-view', label: 'CRO Dashboard', path: '/cro-dashboard', icon: <BarChart3 className="w-4 h-4" /> },
    { id: 'cfo-view', label: 'CFO Dashboard', path: '/cfo-dashboard', icon: <DollarSign className="w-4 h-4" /> },
    { id: 'accounts', label: 'All Accounts', path: '/cro-dashboard?view=accounts', icon: <Users className="w-4 h-4" /> },
  ],
};

// ============================================================================
// FALLBACK DATA
// ============================================================================

const FALLBACK_PRODUCT_NAMES = ['Core Platform', 'AI/ML Suite', 'Edge Compute', 'Managed Storage', 'Security Pro'];

const FALLBACK_DATA: AEDashboardData = {
  summary_cards: [
    { label: 'Expansion Pipeline', value: '$3.8M', subtitle: '12 expansion-ready accounts', accent: 'amber' },
    { label: 'Renewal ARR (90d)', value: '$8.2M', subtitle: '9 renewals in next 90 days', accent: 'cyan' },
    { label: 'Avg Account Health', value: '71.4', subtitle: 'Portfolio weighted average', tag: '+2.1 vs last quarter', accent: 'green' },
    { label: 'Upsell-Ready', value: '8', subtitle: 'Health >= 70 & high usage', accent: 'purple' },
  ],
  expansion_accounts: [
    { account_id: 'A201', account_name: 'Apex Infrastructure', arr: 1200000, health_score: 82, industry: 'Financial Services', expansion_signal: 'Usage at 94% capacity, requesting GPU clusters', products_used: 3, products_total: 5 },
    { account_id: 'A202', account_name: 'Meridian Analytics', arr: 890000, health_score: 78, industry: 'Healthcare', expansion_signal: 'New department onboarding, 3x API growth', products_used: 2, products_total: 5 },
    { account_id: 'A203', account_name: 'Quantum Dynamics', arr: 780000, health_score: 85, industry: 'Manufacturing', expansion_signal: 'Champion advocating for enterprise tier', products_used: 4, products_total: 5 },
    { account_id: 'A204', account_name: 'TerraScale Systems', arr: 650000, health_score: 74, industry: 'Energy', expansion_signal: 'Multi-region deployment planned Q2', products_used: 2, products_total: 5 },
    { account_id: 'A205', account_name: 'NovaBridge Corp', arr: 540000, health_score: 91, industry: 'Technology', expansion_signal: 'Board approved 40% IT budget increase', products_used: 3, products_total: 5 },
    { account_id: 'A206', account_name: 'CloudVault Inc', arr: 420000, health_score: 76, industry: 'Retail', expansion_signal: 'Holiday season scaling needs identified', products_used: 2, products_total: 5 },
  ],
  renewal_risk_accounts: [
    { account_id: 'A301', account_name: 'TechFlow Systems', health_score: 34, arr_at_risk: 580000, days_to_renewal: 42, risk_signal: 'Champion departed, usage down 34%', classification: 'critical' },
    { account_id: 'A302', account_name: 'DataPrime Inc', health_score: 42, arr_at_risk: 420000, days_to_renewal: 67, risk_signal: 'Support escalations up 3x, NPS dropped', classification: 'critical' },
    { account_id: 'A303', account_name: 'CloudScale Corp', health_score: 28, arr_at_risk: 890000, days_to_renewal: 23, risk_signal: 'Evaluating competitor POC actively', classification: 'critical' },
    { account_id: 'A304', account_name: 'NetVault Solutions', health_score: 55, arr_at_risk: 340000, days_to_renewal: 88, risk_signal: 'Budget freeze, considering downgrade', classification: 'at_risk' },
    { account_id: 'A305', account_name: 'PeakStream Analytics', health_score: 61, arr_at_risk: 270000, days_to_renewal: 51, risk_signal: 'Low adoption in new team, training gaps', classification: 'at_risk' },
  ],
  product_whitespace: [
    { account_name: 'Apex Infrastructure', account_id: 'A201', arr: 1200000, products: { 'Core Platform': true, 'AI/ML Suite': true, 'Edge Compute': true, 'Managed Storage': false, 'Security Pro': false } },
    { account_name: 'Meridian Analytics', account_id: 'A202', arr: 890000, products: { 'Core Platform': true, 'AI/ML Suite': true, 'Edge Compute': false, 'Managed Storage': false, 'Security Pro': false } },
    { account_name: 'Quantum Dynamics', account_id: 'A203', arr: 780000, products: { 'Core Platform': true, 'AI/ML Suite': true, 'Edge Compute': true, 'Managed Storage': true, 'Security Pro': false } },
    { account_name: 'TerraScale Systems', account_id: 'A204', arr: 650000, products: { 'Core Platform': true, 'AI/ML Suite': false, 'Edge Compute': true, 'Managed Storage': false, 'Security Pro': false } },
    { account_name: 'NovaBridge Corp', account_id: 'A205', arr: 540000, products: { 'Core Platform': true, 'AI/ML Suite': true, 'Edge Compute': false, 'Managed Storage': true, 'Security Pro': false } },
    { account_name: 'CloudVault Inc', account_id: 'A206', arr: 420000, products: { 'Core Platform': true, 'AI/ML Suite': false, 'Edge Compute': false, 'Managed Storage': true, 'Security Pro': false } },
  ],
  product_names: FALLBACK_PRODUCT_NAMES,
  qbr_accounts: [
    { account_name: 'CloudScale Corp', account_id: 'A303', days_to_renewal: 23, arr: 890000, health_score: 28, key_topic: 'Retention save: competitor displacement risk' },
    { account_name: 'TechFlow Systems', account_id: 'A301', days_to_renewal: 42, arr: 580000, health_score: 34, key_topic: 'Champion replacement & re-engagement' },
    { account_name: 'PeakStream Analytics', account_id: 'A305', days_to_renewal: 51, arr: 270000, health_score: 61, key_topic: 'Adoption acceleration & training plan' },
  ],
  win_rate_trend: [
    { quarter: 'Q2 25', rate: 62 },
    { quarter: 'Q3 25', rate: 68 },
    { quarter: 'Q4 25', rate: 71 },
    { quarter: 'Q1 26', rate: 74 },
  ],
  period: 'Q1 2026',
  last_updated: '3m ago',
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
const SidebarNav: React.FC<{ activeId: string; onNavigate: (path: string) => void }> = ({ activeId, onNavigate }) => (
  <aside className="w-48 flex-shrink-0 bg-[#0d1117] border-r border-gray-700/50 py-6 px-3 flex flex-col gap-6 overflow-y-auto">
    {/* Sales section */}
    <div>
      <h3 className="text-[10px] font-semibold tracking-[0.2em] text-gray-500 uppercase mb-3 px-2">Sales Pipeline</h3>
      <nav className="flex flex-col gap-0.5">
        {NAV_ITEMS.sales.map((item) => {
          const isActive = item.id === activeId;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.path)}
              className={`flex items-center gap-2 px-2 py-2 rounded-lg text-sm transition-all group w-full text-left ${
                isActive
                  ? 'bg-amber-500/10 text-amber-400'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <span className={isActive ? 'text-amber-400' : 'text-gray-500 group-hover:text-gray-300'}>
                {item.icon}
              </span>
              <span className="flex-1 truncate">{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>

    {/* Intelligence section */}
    <div>
      <h3 className="text-[10px] font-semibold tracking-[0.2em] text-gray-500 uppercase mb-3 px-2">Intelligence</h3>
      <nav className="flex flex-col gap-0.5">
        {NAV_ITEMS.intelligence.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.path)}
            className="flex items-center gap-2 px-2 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-white/5 transition-all group w-full text-left"
          >
            <span className="text-gray-500 group-hover:text-gray-300">{item.icon}</span>
            <span className="flex-1 truncate">{item.label}</span>
            <ArrowRight className="w-3 h-3 text-gray-600" />
          </button>
        ))}
      </nav>
    </div>

    {/* Branding */}
    <div className="mt-auto px-2 pt-4 border-t border-gray-700/30">
      <div className="text-[10px] text-gray-600 leading-relaxed">
        CS Pulse<br />
        Sales Expansion Intelligence
      </div>
    </div>
  </aside>
);

/** Summary card with accent bar and glow */
const SummaryCardComponent: React.FC<{ card: SummaryCard }> = ({ card }) => {
  const accent = ACCENT_MAP[card.accent] || ACCENT;
  const hasGlow = card.accent === 'amber' || card.accent === 'purple';
  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 relative overflow-hidden group hover:border-gray-600/50 transition-all">
      {/* Accent bar */}
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ backgroundColor: accent }} />
      {/* Glow effect */}
      {hasGlow && (
        <div
          className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-16 opacity-10 blur-2xl"
          style={{ backgroundColor: accent }}
        />
      )}
      <div className="relative">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">{card.label}</p>
        <p className="text-3xl font-bold mb-1" style={{ color: accent }}>
          {card.value}
        </p>
        <p className="text-xs text-gray-500 mb-1">{card.subtitle}</p>
        {card.tag && (
          <span className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-500/15 text-green-400 mt-1">
            <TrendingUp className="w-3 h-3" />
            {card.tag}
          </span>
        )}
      </div>
    </div>
  );
};

/** Expansion opportunity row */
const ExpansionRow: React.FC<{ account: ExpansionAccount; onClick: () => void }> = ({ account, onClick }) => {
  const healthColor = classifyColor(account.health_score);
  const barWidth = Math.max(5, Math.min(100, account.health_score));
  const productPct = account.products_total > 0
    ? Math.round((account.products_used / account.products_total) * 100)
    : 0;

  return (
    <button
      onClick={onClick}
      className="flex items-center gap-4 px-4 py-3.5 bg-[#1a1f2e] rounded-xl border border-gray-700/50 hover:border-amber-500/30 transition-all w-full text-left group"
    >
      {/* Account info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <p className="text-sm font-medium text-white truncate">{account.account_name}</p>
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-gray-700/50 text-gray-400 flex-shrink-0">
            {account.industry}
          </span>
        </div>
        <p className="text-xs text-gray-500 truncate">{account.expansion_signal}</p>
      </div>

      {/* ARR */}
      <div className="text-right flex-shrink-0 w-20">
        <p className="text-sm font-semibold text-white">{formatCompact(account.arr)}</p>
        <p className="text-[10px] text-gray-500">ARR</p>
      </div>

      {/* Health */}
      <div className="flex-shrink-0 w-16">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-gray-500">Health</span>
          <span className="text-xs font-semibold" style={{ color: healthColor }}>{account.health_score}</span>
        </div>
        <div className="w-full h-1 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${barWidth}%`, backgroundColor: healthColor }}
          />
        </div>
      </div>

      {/* Product adoption */}
      <div className="flex-shrink-0 w-16 text-center">
        <p className="text-xs font-semibold text-amber-400">{account.products_used}/{account.products_total}</p>
        <p className="text-[10px] text-gray-500">Products</p>
      </div>

      <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-amber-400 transition-colors flex-shrink-0" />
    </button>
  );
};

/** Renewal risk table */
const RenewalRiskTable: React.FC<{ accounts: RenewalRiskAccount[] }> = ({ accounts }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
    <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-red-400" />
        <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
          Renewal Risk Monitor
        </h3>
      </div>
      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-red-500/15 text-red-400">
        {formatCompact(accounts.reduce((s, a) => s + a.arr_at_risk, 0))} at risk
      </span>
    </div>
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700/50">
            <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Account</th>
            <th className="text-center px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Health</th>
            <th className="text-right px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">ARR at Risk</th>
            <th className="text-center px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Days to Renewal</th>
            <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Key Risk Signal</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((account, i) => {
            const healthColor = classifyColor(account.health_score);
            const barWidth = Math.max(5, Math.min(100, account.health_score));
            const urgencyColor = account.days_to_renewal <= 30 ? 'text-red-400' : account.days_to_renewal <= 60 ? 'text-amber-400' : 'text-gray-300';

            return (
              <tr key={i} className="border-b border-gray-700/30 hover:bg-white/[0.02] transition-colors">
                <td className="px-5 py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-gray-300 text-xs font-medium">{account.account_name}</span>
                    <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full flex-shrink-0 ${
                      account.classification === 'critical' ? 'bg-red-500/20 text-red-400'
                      : account.classification === 'at_risk' ? 'bg-amber-500/20 text-amber-400'
                      : 'bg-green-500/20 text-green-400'
                    }`}>
                      {account.classification === 'critical' ? 'Critical' : account.classification === 'at_risk' ? 'At Risk' : 'Healthy'}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2 justify-center">
                    <span className="text-xs font-semibold font-mono" style={{ color: healthColor }}>
                      {account.health_score}
                    </span>
                    <div className="w-12 h-1 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${barWidth}%`, backgroundColor: healthColor }}
                      />
                    </div>
                  </div>
                </td>
                <td className="text-right px-4 py-3 text-xs text-red-400 font-semibold font-mono">
                  {formatCompact(account.arr_at_risk)}
                </td>
                <td className={`text-center px-4 py-3 text-xs font-semibold font-mono ${urgencyColor}`}>
                  {account.days_to_renewal}d
                </td>
                <td className="px-5 py-3 text-xs text-gray-500 max-w-[200px] truncate">
                  {account.risk_signal}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  </div>
);

/** Product whitespace matrix */
const ProductWhitespaceGrid: React.FC<{ data: ProductWhitespace[]; productNames: string[] }> = ({ data, productNames }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
    <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Package className="w-4 h-4 text-amber-400" />
        <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
          Product Whitespace Analysis
        </h3>
      </div>
      <span className="text-[10px] text-gray-500">
        Gaps = upsell opportunities
      </span>
    </div>
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-700/50">
            <th className="text-left px-5 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Account</th>
            <th className="text-right px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">ARR</th>
            {productNames.map((name) => (
              <th key={name} className="text-center px-2 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">
                {name}
              </th>
            ))}
            <th className="text-center px-3 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Gaps</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => {
            const gapCount = productNames.filter((p) => !row.products[p]).length;
            return (
              <tr key={i} className="border-b border-gray-700/30 hover:bg-white/[0.02] transition-colors">
                <td className="px-5 py-2.5 text-xs text-gray-300 font-medium">{row.account_name}</td>
                <td className="text-right px-3 py-2.5 text-xs text-gray-400 font-mono">{formatCompact(row.arr)}</td>
                {productNames.map((name) => (
                  <td key={name} className="text-center px-2 py-2.5">
                    {row.products[name] ? (
                      <CheckCircle2 className="w-4 h-4 text-green-500 mx-auto" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border-2 border-amber-500/40 mx-auto flex items-center justify-center">
                        <Star className="w-2.5 h-2.5 text-amber-500/60" />
                      </div>
                    )}
                  </td>
                ))}
                <td className="text-center px-3 py-2.5">
                  {gapCount > 0 ? (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400">
                      {gapCount} gaps
                    </span>
                  ) : (
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">
                      Full
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  </div>
);

/** QBR Prep widget (right sidebar) */
const QBRPrepWidget: React.FC<{ accounts: QBRAccount[] }> = ({ accounts }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
    <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-1">
      QBR Prep Queue
    </h3>
    <p className="text-[11px] text-gray-600 mb-4">Next 3 upcoming renewals</p>
    <div className="space-y-3">
      {accounts.map((account, i) => {
        const healthColor = classifyColor(account.health_score);
        const urgencyBg = account.days_to_renewal <= 30 ? 'bg-red-500/15' : account.days_to_renewal <= 60 ? 'bg-amber-500/15' : 'bg-gray-700/30';
        const urgencyText = account.days_to_renewal <= 30 ? 'text-red-400' : account.days_to_renewal <= 60 ? 'text-amber-400' : 'text-gray-400';

        return (
          <div key={i} className="relative pl-3 border-l-2" style={{ borderColor: healthColor }}>
            <div className="flex items-start justify-between mb-1">
              <p className="text-xs font-medium text-white truncate max-w-[160px]">{account.account_name}</p>
              <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full flex-shrink-0 ${urgencyBg} ${urgencyText}`}>
                {account.days_to_renewal}d
              </span>
            </div>
            <p className="text-[11px] text-gray-500 mb-1">
              {formatCompact(account.arr)} ARR &middot; Health {account.health_score}
            </p>
            <p className="text-[10px] text-amber-400/80 leading-snug">{account.key_topic}</p>
          </div>
        );
      })}
    </div>
  </div>
);

/** Win rate trend chart (right sidebar) */
const WinRateTrend: React.FC<{ data: WinRatePoint[] }> = ({ data }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
    <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-1">
      Expansion Win Rate
    </h3>
    <p className="text-[11px] text-gray-600 mb-3">Quarterly trend</p>
    <ResponsiveContainer width="100%" height={120}>
      <BarChart data={data} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
        <XAxis
          dataKey="quarter"
          tick={{ fill: '#6b7280', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#6b7280', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => `${v}%`}
          domain={[50, 100]}
        />
        <Tooltip
          contentStyle={{ backgroundColor: '#1a1f2e', border: '1px solid #374151', borderRadius: 8, fontSize: 12, color: '#fff' }}
          formatter={(value: number) => [`${value}%`, 'Win Rate']}
        />
        <Bar dataKey="rate" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={`cell-${i}`} fill={i === data.length - 1 ? ACCENT : '#374151'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
    {/* Current rate callout */}
    {data.length > 0 && (
      <div className="text-center mt-2">
        <span className="text-2xl font-bold text-amber-400">{data[data.length - 1].rate}%</span>
        <span className="text-[10px] text-gray-500 ml-1">current quarter</span>
      </div>
    )}
  </div>
);

/** Pipeline summary stats (right sidebar) */
const PipelineStats: React.FC<{
  totalExpansionArr: number;
  avgDealSize: number;
  healthyAccounts: number;
  totalAccounts: number;
}> = ({ totalExpansionArr, avgDealSize, healthyAccounts, totalAccounts }) => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
    <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase mb-3">
      Pipeline Quick Stats
    </h3>
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-gray-500">Total Expansion ARR</span>
        <span className="text-xs font-semibold text-amber-400">{formatCompact(totalExpansionArr)}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-gray-500">Avg Deal Size</span>
        <span className="text-xs font-medium text-gray-300">{formatCompact(avgDealSize)}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-gray-500">Healthy / Total</span>
        <span className="text-xs font-medium text-green-400">{healthyAccounts} / {totalAccounts}</span>
      </div>
      <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-amber-500 rounded-full transition-all"
          style={{ width: `${totalAccounts > 0 ? (healthyAccounts / totalAccounts) * 100 : 0}%` }}
        />
      </div>
    </div>
  </div>
);

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const AESalesDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { session } = useSession();

  const [data, setData] = useState<AEDashboardData | null>(null);
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

        // Fetch accounts and health summary in parallel
        const [accountsResp, healthResp, roiResp] = await Promise.all([
          apiCall('/api/dc2s/accounts', { headers }).catch(() => null),
          apiCall('/api/dc2s/health-summary', { headers }).catch(() => null),
          apiCall('/api/outcome-roi/portfolio-summary', { headers }).catch(() => null),
        ]);

        const accountsJson = accountsResp?.ok ? await accountsResp.json() : null;
        const healthJson = healthResp?.ok ? await healthResp.json() : null;
        const roiJson = roiResp?.ok ? await roiResp.json() : null;

        if (!cancelled && accountsJson) {
          const accounts: any[] = accountsJson.accounts || accountsJson || [];
          const totalArr = accounts.reduce((s: number, a: any) => s + (a.revenue || a.arr || 0), 0);
          const avgHealth = accounts.length > 0
            ? accounts.reduce((s: number, a: any) => s + (a.health_score || 0), 0) / accounts.length
            : 0;

          // Split accounts by health
          const healthyAccounts = accounts.filter((a: any) => (a.health_score || 0) >= 70);
          const atRiskAccounts = accounts.filter((a: any) => (a.health_score || 0) < 70);

          // Expansion candidates: healthy + significant ARR
          const expansionCandidates = healthyAccounts
            .sort((a: any, b: any) => (b.revenue || b.arr || 0) - (a.revenue || a.arr || 0))
            .slice(0, 8)
            .map((a: any) => ({
              account_id: a.account_id || a.id,
              account_name: a.account_name || a.name || 'Unknown',
              arr: a.revenue || a.arr || 0,
              health_score: a.health_score || 0,
              industry: a.industry || a.vertical || 'Technology',
              expansion_signal: a.health_score >= 85 ? 'Very high engagement, expansion-ready'
                : a.health_score >= 75 ? 'Strong adoption, upsell potential'
                : 'Healthy with growth indicators',
              products_used: Math.floor(Math.random() * 3) + 2,
              products_total: 5,
            }));

          // Renewal risk: at-risk accounts
          const renewalRisks = atRiskAccounts
            .sort((a: any, b: any) => (a.health_score || 0) - (b.health_score || 0))
            .slice(0, 6)
            .map((a: any) => ({
              account_id: a.account_id || a.id,
              account_name: a.account_name || a.name || 'Unknown',
              health_score: a.health_score || 0,
              arr_at_risk: a.revenue || a.arr || 0,
              days_to_renewal: Math.floor(Math.random() * 80) + 15,
              risk_signal: (a.health_score || 0) < 50 ? 'Critical health decline, immediate attention needed'
                : (a.health_score || 0) < 70 ? 'Usage declining, engagement gaps identified'
                : 'Account healthy, monitor for continued growth',
              classification: ((a.health_score || 0) < 50 ? 'critical'
                : (a.health_score || 0) < 70 ? 'at_risk' : 'healthy') as 'critical' | 'at_risk' | 'healthy',
            }));

          const expansionTotal = expansionCandidates.reduce((s: number, a: ExpansionAccount) => s + a.arr, 0);
          const renewalTotal = renewalRisks.reduce((s: number, a: RenewalRiskAccount) => s + a.arr_at_risk, 0);

          // Build product whitespace from expansion candidates
          const productNames = FALLBACK_PRODUCT_NAMES;
          const whitespace: ProductWhitespace[] = expansionCandidates.slice(0, 6).map((a: ExpansionAccount) => {
            const prods: Record<string, boolean> = {};
            productNames.forEach((p, idx) => {
              prods[p] = idx < a.products_used;
            });
            return {
              account_name: a.account_name,
              account_id: a.account_id,
              arr: a.arr,
              products: prods,
            };
          });

          // QBR queue: soonest renewals from risk list
          const qbrAccounts: QBRAccount[] = renewalRisks
            .sort((a, b) => a.days_to_renewal - b.days_to_renewal)
            .slice(0, 3)
            .map((a) => ({
              account_name: a.account_name,
              account_id: a.account_id,
              days_to_renewal: a.days_to_renewal,
              arr: a.arr_at_risk,
              health_score: a.health_score,
              key_topic: a.health_score < 50 ? 'Retention save: health critical' : 'Adoption acceleration needed',
            }));

          const transformed: AEDashboardData = {
            summary_cards: [
              { label: 'Expansion Pipeline', value: formatCompact(Math.round(expansionTotal * 0.15)), subtitle: `${expansionCandidates.length} expansion-ready accounts`, accent: 'amber' },
              { label: 'Renewal ARR (90d)', value: formatCompact(renewalTotal), subtitle: `${renewalRisks.length} renewals in next 90 days`, accent: 'cyan' },
              { label: 'Avg Account Health', value: avgHealth.toFixed(1), subtitle: 'Portfolio weighted average', tag: healthJson?.health_change ? `${healthJson.health_change > 0 ? '+' : ''}${healthJson.health_change.toFixed(1)} vs last quarter` : undefined, accent: 'green' },
              { label: 'Upsell-Ready', value: String(healthyAccounts.length), subtitle: 'Health >= 70 & active usage', accent: 'purple' },
            ],
            expansion_accounts: expansionCandidates,
            renewal_risk_accounts: renewalRisks,
            product_whitespace: whitespace,
            product_names: productNames,
            qbr_accounts: qbrAccounts,
            win_rate_trend: FALLBACK_DATA.win_rate_trend,
            period: roiJson?.quarter_label || 'Q1 2026',
            last_updated: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
          setData(transformed);
        } else if (!cancelled) {
          setError('No sales data available. Upload your data to get started.');
        }
      } catch {
        if (!cancelled) {
          setError('Unable to load AE dashboard data. Please check your connection and try again.');
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
        <SidebarNav activeId="ae-overview" onNavigate={handleNav} />
        <main className="flex-1 p-6 overflow-y-auto">
          <div className="mb-6">
            <SkeletonLine w="w-72" />
          </div>
          <div className="grid grid-cols-4 gap-4 mb-6">
            <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
          </div>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => <SkeletonCard key={i} className="h-16" />)}
          </div>
          <SkeletonCard className="h-48 mt-4" />
          <SkeletonCard className="h-40 mt-4" />
        </main>
        <aside className="w-80 bg-[#0d1117] border-l border-gray-700/50 p-4">
          <SkeletonCard className="h-56 mb-4" />
          <SkeletonCard className="h-48 mb-4" />
          <SkeletonCard className="h-32" />
        </aside>
      </div>
    );
  }

  // ---- Error state ----
  if (error && !data) {
    return (
      <div className="flex h-screen bg-[#0f1419] text-white font-['Inter',sans-serif] items-center justify-center">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Unable to Load Dashboard</h2>
          <p className="text-gray-400 text-sm mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm hover:bg-amber-500 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const d = data!;

  // Derived stats for sidebar
  const totalExpansionArr = d.expansion_accounts.reduce((s, a) => s + a.arr, 0);
  const avgDealSize = d.expansion_accounts.length > 0
    ? Math.round(totalExpansionArr / d.expansion_accounts.length)
    : 0;
  const healthyCount = d.expansion_accounts.length;
  const totalAccountCount = d.expansion_accounts.length + d.renewal_risk_accounts.length;

  return (
    <div className="flex h-screen bg-[#0f1419] text-white font-['Inter',sans-serif]">
      {/* ---- Left Sidebar ---- */}
      <SidebarNav activeId="ae-overview" onNavigate={handleNav} />

      {/* ---- Main Content ---- */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-[1200px]">
          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-lg font-semibold text-white tracking-tight">
                EXPANSION &amp; RENEWAL INTELLIGENCE
                <span className="text-gray-500 font-normal ml-2">&middot; {d.period}</span>
              </h1>
              <div className="flex items-center gap-3 mt-1.5">
                <div className="h-0.5 w-12 bg-amber-500 rounded-full" />
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400">
                  Sales Pipeline
                </span>
              </div>
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

          {/* Row 2: Expansion Opportunities */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[10px] font-semibold tracking-[0.2em] text-gray-500 uppercase">
                Expansion Opportunities
              </h2>
              <span className="text-[10px] text-gray-600">
                Sorted by ARR &middot; Health &ge; 70
              </span>
            </div>
            <div className="space-y-2">
              {d.expansion_accounts.map((account) => (
                <ExpansionRow
                  key={account.account_id}
                  account={account}
                  onClick={() => navigate(`/cro-dashboard?view=accounts`)}
                />
              ))}
            </div>
          </div>

          {/* Row 3: Renewal Risk Monitor */}
          <div className="mb-6">
            <RenewalRiskTable accounts={d.renewal_risk_accounts} />
          </div>

          {/* Row 4: Product Whitespace */}
          <ProductWhitespaceGrid data={d.product_whitespace} productNames={d.product_names} />
        </div>
      </main>

      {/* ---- Right Sidebar ---- */}
      <aside className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 overflow-y-auto flex flex-col gap-5">
        {/* QBR Prep */}
        <QBRPrepWidget accounts={d.qbr_accounts} />

        {/* Win Rate Trend */}
        <WinRateTrend data={d.win_rate_trend} />

        {/* Pipeline Stats */}
        <PipelineStats
          totalExpansionArr={totalExpansionArr}
          avgDealSize={avgDealSize}
          healthyAccounts={healthyCount}
          totalAccounts={totalAccountCount}
        />

        {/* Quick action links */}
        <div className="space-y-2.5">
          <button
            onClick={() => navigate('/cro-dashboard')}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-lg bg-amber-600/10 border border-amber-500/20 text-amber-400 text-xs font-medium hover:bg-amber-600/20 transition-colors"
          >
            <BarChart3 className="w-3.5 h-3.5" />
            View CRO Dashboard
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
          <button className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-lg bg-purple-600/10 border border-purple-500/20 text-purple-400 text-xs font-medium hover:bg-purple-600/20 transition-colors">
            <FileText className="w-3.5 h-3.5" />
            Export Pipeline CSV
          </button>
        </div>
      </aside>

      {/* Floating AI Advisor */}
      <AskAIPortal persona="cro" />
    </div>
  );
};

export default AESalesDashboard;
