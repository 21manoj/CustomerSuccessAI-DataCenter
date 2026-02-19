import React, { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, Building2, DollarSign, Users, Target,
  BarChart3, ArrowRight, Activity, Layers, Zap, BookOpen, Shield, GitMerge
} from 'lucide-react';

// ────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────

interface SynergyBreakdown {
  type: string;
  label: string;
  multiplier: number;
  dollar_impact: number;
}

interface CompanyResult {
  company_id: string;
  company_name: string;
  arr: number;
  standalone_impact: number;
  synergy_impact: number;
  total_impact: number;
  standalone_investment: number;
  synergy_adjusted_investment: number;
  synergies: SynergyBreakdown[];
}

interface PortfolioResult {
  portfolio_name: string;
  company_count: number;
  total_arr: number;
  standalone_total_impact: number;
  synergy_total_impact: number;
  portfolio_total_impact: number;
  standalone_roi: number;
  portfolio_roi: number;
  synergy_uplift_pct: number;
  payback_months: number;
  synergy_breakdown: Record<string, number>;
  companies: CompanyResult[];
}

interface MAPlaybook {
  id: string;
  name: string;
  phase: 'due_diligence' | 'day_1' | 'first_100_days' | 'integration';
  status: 'not_started' | 'in_progress' | 'completed';
  progress: number;
  actions: string[];
}

// ────────────────────────────────────────────────────────
// Mock data (replace with API calls in production)
// ────────────────────────────────────────────────────────

const MOCK_PORTFOLIO: PortfolioResult = {
  portfolio_name: 'PE 5-Company Portfolio',
  company_count: 5,
  total_arr: 175_000_000,
  standalone_total_impact: 8_750_000,
  synergy_total_impact: 1_925_000,
  portfolio_total_impact: 10_675_000,
  standalone_roi: 7.1,
  portfolio_roi: 8.6,
  synergy_uplift_pct: 22.0,
  payback_months: 4.2,
  synergy_breakdown: {
    shared_playbooks: 580_000,
    shared_resources: 420_000,
    vendor_leverage: 310_000,
    cross_sell: 390_000,
    benchmarking: 225_000,
  },
  companies: [
    {
      company_id: 'co-1', company_name: 'DataVault Inc', arr: 80_000_000,
      standalone_impact: 4_000_000, synergy_impact: 0, total_impact: 4_000_000,
      standalone_investment: 247_000, synergy_adjusted_investment: 247_000, synergies: [],
    },
    {
      company_id: 'co-2', company_name: 'CloudMetrics', arr: 35_000_000,
      standalone_impact: 1_750_000, synergy_impact: 420_000, total_impact: 2_170_000,
      standalone_investment: 247_000, synergy_adjusted_investment: 222_000,
      synergies: [
        { type: 'shared_playbooks', label: 'Shared Playbooks', multiplier: 1.12, dollar_impact: 210_000 },
        { type: 'shared_resources', label: 'Shared Resources', multiplier: 1.08, dollar_impact: 140_000 },
        { type: 'cross_sell', label: 'Cross-Sell', multiplier: 1.04, dollar_impact: 70_000 },
      ],
    },
    {
      company_id: 'co-3', company_name: 'SecureStack', arr: 28_000_000,
      standalone_impact: 1_400_000, synergy_impact: 385_000, total_impact: 1_785_000,
      standalone_investment: 247_000, synergy_adjusted_investment: 210_000,
      synergies: [
        { type: 'shared_playbooks', label: 'Shared Playbooks', multiplier: 1.10, dollar_impact: 154_000 },
        { type: 'vendor_leverage', label: 'Vendor Leverage', multiplier: 1.06, dollar_impact: 84_000 },
        { type: 'benchmarking', label: 'Benchmarking', multiplier: 1.05, dollar_impact: 70_000 },
        { type: 'shared_resources', label: 'Shared Resources', multiplier: 1.06, dollar_impact: 77_000 },
      ],
    },
    {
      company_id: 'co-4', company_name: 'AICompute Labs', arr: 20_000_000,
      standalone_impact: 1_000_000, synergy_impact: 560_000, total_impact: 1_560_000,
      standalone_investment: 247_000, synergy_adjusted_investment: 198_000,
      synergies: [
        { type: 'shared_playbooks', label: 'Shared Playbooks', multiplier: 1.09, dollar_impact: 100_000 },
        { type: 'cross_sell', label: 'Cross-Sell', multiplier: 1.08, dollar_impact: 160_000 },
        { type: 'vendor_leverage', label: 'Vendor Leverage', multiplier: 1.05, dollar_impact: 100_000 },
        { type: 'shared_resources', label: 'Shared Resources', multiplier: 1.05, dollar_impact: 100_000 },
        { type: 'benchmarking', label: 'Benchmarking', multiplier: 1.05, dollar_impact: 100_000 },
      ],
    },
    {
      company_id: 'co-5', company_name: 'EdgeScale', arr: 12_000_000,
      standalone_impact: 600_000, synergy_impact: 560_000, total_impact: 1_160_000,
      standalone_investment: 247_000, synergy_adjusted_investment: 185_000,
      synergies: [
        { type: 'shared_playbooks', label: 'Shared Playbooks', multiplier: 1.08, dollar_impact: 116_000 },
        { type: 'cross_sell', label: 'Cross-Sell', multiplier: 1.10, dollar_impact: 160_000 },
        { type: 'vendor_leverage', label: 'Vendor Leverage', multiplier: 1.06, dollar_impact: 126_000 },
        { type: 'shared_resources', label: 'Shared Resources', multiplier: 1.04, dollar_impact: 103_000 },
        { type: 'benchmarking', label: 'Benchmarking', multiplier: 1.03, dollar_impact: 55_000 },
      ],
    },
  ],
};

const MOCK_MA_PLAYBOOKS: MAPlaybook[] = [
  {
    id: 'ma-dd-01', name: 'CS Due Diligence Assessment', phase: 'due_diligence',
    status: 'completed', progress: 100,
    actions: ['Customer health audit', 'Churn risk assessment', 'CSM org evaluation', 'Tech stack review'],
  },
  {
    id: 'ma-d1-01', name: 'Day 1 Customer Communication', phase: 'day_1',
    status: 'completed', progress: 100,
    actions: ['Joint announcement', 'CSM introduction', 'Support channel merge', 'FAQ distribution'],
  },
  {
    id: 'ma-100-01', name: 'Health Score Unification', phase: 'first_100_days',
    status: 'in_progress', progress: 65,
    actions: ['KPI alignment', 'Pillar weight calibration', 'Historical data migration', 'Unified dashboard rollout'],
  },
  {
    id: 'ma-100-02', name: 'Playbook Cross-Pollination', phase: 'first_100_days',
    status: 'in_progress', progress: 40,
    actions: ['Catalog existing playbooks', 'Identify shared patterns', 'Build unified library', 'Deploy to all portcos'],
  },
  {
    id: 'ma-int-01', name: 'Full Platform Integration', phase: 'integration',
    status: 'not_started', progress: 0,
    actions: ['Unified data model', 'Cross-company analytics', 'Synergy tracking automation', 'Consolidated reporting'],
  },
];

// ────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────

const fmtDollar = (n: number) => {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
};

const fmtPct = (n: number) => `${n.toFixed(1)}%`;

const SYNERGY_COLORS: Record<string, string> = {
  shared_playbooks: '#6366f1',  // indigo
  shared_resources: '#10b981',  // emerald
  vendor_leverage:  '#f59e0b',  // amber
  cross_sell:       '#3b82f6',  // blue
  benchmarking:     '#8b5cf6',  // violet
};

const SYNERGY_LABELS: Record<string, string> = {
  shared_playbooks: 'Shared Playbooks',
  shared_resources: 'Shared Resources',
  vendor_leverage:  'Vendor Leverage',
  cross_sell:       'Cross-Sell',
  benchmarking:     'Benchmarking',
};

const PHASE_LABELS: Record<string, string> = {
  due_diligence: 'Due Diligence',
  day_1: 'Day 1',
  first_100_days: 'First 100 Days',
  integration: 'Full Integration',
};

const STATUS_COLORS: Record<string, string> = {
  completed: 'bg-green-100 text-green-800',
  in_progress: 'bg-blue-100 text-blue-800',
  not_started: 'bg-gray-100 text-gray-600',
};

// ────────────────────────────────────────────────────────
// Sub-Components
// ────────────────────────────────────────────────────────

const KPICard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  color?: string;
}> = ({ icon, label, value, sub, color = 'text-gray-900' }) => (
  <div className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm">
    <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
      {icon}
      {label}
    </div>
    <div className={`text-2xl font-bold ${color}`}>{value}</div>
    {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
  </div>
);

const SynergyWaterfall: React.FC<{ breakdown: Record<string, number> }> = ({ breakdown }) => {
  const total = Object.values(breakdown).reduce((a, b) => a + b, 0);
  if (total === 0) return null;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <Layers className="h-4 w-4 text-indigo-500" />
        Synergy Value Waterfall
      </h3>
      <div className="space-y-3">
        {Object.entries(breakdown)
          .sort(([, a], [, b]) => b - a)
          .map(([type, amount]) => {
            const pct = (amount / total) * 100;
            return (
              <div key={type}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-gray-700">{SYNERGY_LABELS[type] || type}</span>
                  <span className="font-medium">{fmtDollar(amount)}</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-3">
                  <div
                    className="h-3 rounded-full transition-all duration-500"
                    style={{ width: `${pct}%`, backgroundColor: SYNERGY_COLORS[type] || '#94a3b8' }}
                  />
                </div>
              </div>
            );
          })}
        <div className="flex items-center justify-between text-sm font-bold pt-2 border-t border-gray-200">
          <span>Total Synergy Value</span>
          <span className="text-indigo-600">{fmtDollar(total)}</span>
        </div>
      </div>
    </div>
  );
};

const CompanyRow: React.FC<{ company: CompanyResult; index: number }> = ({ company, index }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-400 w-6">#{index + 1}</span>
          <Building2 className="h-5 w-5 text-gray-500" />
          <div>
            <div className="font-semibold text-gray-900">{company.company_name}</div>
            <div className="text-xs text-gray-500">ARR: {fmtDollar(company.arr)}</div>
          </div>
        </div>
        <div className="flex items-center gap-6 text-sm">
          <div className="text-right">
            <div className="text-gray-500">Standalone</div>
            <div className="font-medium">{fmtDollar(company.standalone_impact)}</div>
          </div>
          <ArrowRight className="h-4 w-4 text-gray-300" />
          <div className="text-right">
            <div className="text-gray-500">+ Synergy</div>
            <div className="font-medium text-green-600">+{fmtDollar(company.synergy_impact)}</div>
          </div>
          <ArrowRight className="h-4 w-4 text-gray-300" />
          <div className="text-right">
            <div className="text-gray-500">Total Impact</div>
            <div className="font-bold text-indigo-600">{fmtDollar(company.total_impact)}</div>
          </div>
        </div>
      </div>
      {expanded && company.synergies.length > 0 && (
        <div className="bg-gray-50 px-4 pb-4 border-t border-gray-100">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mt-3 mb-2">Synergy Breakdown</div>
          <div className="grid grid-cols-2 gap-2">
            {company.synergies.map((s, i) => (
              <div key={i} className="flex items-center gap-2 bg-white rounded px-3 py-2 text-sm border border-gray-100">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: SYNERGY_COLORS[s.type] || '#94a3b8' }} />
                <span className="text-gray-600">{s.label}</span>
                <span className="ml-auto font-medium text-gray-900">{s.multiplier.toFixed(2)}x</span>
                <span className="text-green-600 font-medium">+{fmtDollar(s.dollar_impact)}</span>
              </div>
            ))}
          </div>
          {company.synergy_adjusted_investment < company.standalone_investment && (
            <div className="mt-2 text-xs text-emerald-600">
              Investment reduced {fmtDollar(company.standalone_investment)} {'->'} {fmtDollar(company.synergy_adjusted_investment)} via shared resources
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const MAPlaybookCard: React.FC<{ playbook: MAPlaybook }> = ({ playbook }) => (
  <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
    <div className="flex items-center justify-between mb-2">
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[playbook.status]}`}>
        {playbook.status.replace('_', ' ')}
      </span>
      <span className="text-xs text-gray-400">{PHASE_LABELS[playbook.phase]}</span>
    </div>
    <h4 className="font-semibold text-gray-900 text-sm mb-2">{playbook.name}</h4>
    <div className="w-full bg-gray-100 rounded-full h-2 mb-3">
      <div
        className="h-2 rounded-full bg-indigo-500 transition-all duration-500"
        style={{ width: `${playbook.progress}%` }}
      />
    </div>
    <div className="space-y-1">
      {playbook.actions.map((action, i) => (
        <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
          <div className={`w-3 h-3 rounded-sm border flex items-center justify-center ${
            playbook.progress >= ((i + 1) / playbook.actions.length) * 100
              ? 'bg-green-500 border-green-500 text-white'
              : 'border-gray-300'
          }`}>
            {playbook.progress >= ((i + 1) / playbook.actions.length) * 100 && (
              <svg viewBox="0 0 12 12" className="w-2 h-2"><path d="M2 6l3 3 5-5" stroke="currentColor" fill="none" strokeWidth="2" /></svg>
            )}
          </div>
          {action}
        </div>
      ))}
    </div>
  </div>
);

const SynergyRealizationTracker: React.FC<{ companies: CompanyResult[] }> = ({ companies }) => {
  const totalSynergy = companies.reduce((sum, c) => sum + c.synergy_impact, 0);
  // Simulated realization: first 2 companies are "realized"
  const realizedSynergy = companies.slice(0, 2).reduce((sum, c) => sum + c.synergy_impact, 0);
  const realizationPct = totalSynergy > 0 ? (realizedSynergy / totalSynergy) * 100 : 0;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <Activity className="h-4 w-4 text-green-500" />
        Synergy Realization Tracker
      </h3>
      <div className="flex items-end gap-4 mb-4">
        <div>
          <div className="text-3xl font-bold text-green-600">{fmtPct(realizationPct)}</div>
          <div className="text-xs text-gray-500">of synergy value realized</div>
        </div>
        <div className="text-sm text-gray-500">
          {fmtDollar(realizedSynergy)} of {fmtDollar(totalSynergy)}
        </div>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-4">
        <div
          className="h-4 rounded-full bg-gradient-to-r from-green-400 to-emerald-500 transition-all duration-700"
          style={{ width: `${realizationPct}%` }}
        />
      </div>
      <div className="mt-4 space-y-2">
        {companies.filter(c => c.synergy_impact > 0).map((c, i) => (
          <div key={c.company_id} className="flex items-center justify-between text-sm">
            <span className="text-gray-700">{c.company_name}</span>
            <div className="flex items-center gap-2">
              <span className="text-green-600 font-medium">+{fmtDollar(c.synergy_impact)}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded ${
                i < 2 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
              }`}>
                {i < 2 ? 'Realized' : 'Projected'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ────────────────────────────────────────────────────────
// Main Dashboard
// ────────────────────────────────────────────────────────

type TabKey = 'overview' | 'synergy' | 'companies' | 'ma_playbooks';

const PortcoCEODashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [portfolio, setPortfolio] = useState<PortfolioResult>(MOCK_PORTFOLIO);
  const [playbooks] = useState<MAPlaybook[]>(MOCK_MA_PLAYBOOKS);

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'overview', label: 'Portfolio Overview', icon: <BarChart3 className="h-4 w-4" /> },
    { key: 'synergy', label: 'Synergy Engine', icon: <Zap className="h-4 w-4" /> },
    { key: 'companies', label: 'Company Detail', icon: <Building2 className="h-4 w-4" /> },
    { key: 'ma_playbooks', label: 'M&A Playbooks', icon: <GitMerge className="h-4 w-4" /> },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-700 to-purple-700 text-white px-8 py-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-indigo-200 font-medium">CS Pulse GrowthPulse</div>
            <h1 className="text-2xl font-bold">PortCo CEO Dashboard</h1>
            <p className="text-indigo-200 text-sm mt-1">{portfolio.portfolio_name} — {portfolio.company_count} Companies</p>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className="text-indigo-200 text-xs">Total ARR</div>
              <div className="text-xl font-bold">{fmtDollar(portfolio.total_arr)}</div>
            </div>
            <div className="text-right">
              <div className="text-indigo-200 text-xs">Portfolio ROI</div>
              <div className="text-xl font-bold">{portfolio.portfolio_roi.toFixed(1)}x</div>
            </div>
            <div className="text-right">
              <div className="text-indigo-200 text-xs">Synergy Uplift</div>
              <div className="text-xl font-bold text-green-300">+{fmtPct(portfolio.synergy_uplift_pct)}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Bar */}
      <div className="bg-white border-b border-gray-200 px-8">
        <div className="flex gap-1">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition ${
                activeTab === t.key
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="px-8 py-6">

        {/* ── Overview Tab ── */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* KPI Row */}
            <div className="grid grid-cols-5 gap-4">
              <KPICard
                icon={<Building2 className="h-4 w-4" />}
                label="Portfolio Companies"
                value={String(portfolio.company_count)}
                sub={`${fmtDollar(portfolio.total_arr)} combined ARR`}
              />
              <KPICard
                icon={<DollarSign className="h-4 w-4" />}
                label="Standalone Impact"
                value={fmtDollar(portfolio.standalone_total_impact)}
                sub={`${portfolio.standalone_roi.toFixed(1)}x ROI`}
              />
              <KPICard
                icon={<Zap className="h-4 w-4" />}
                label="Synergy Impact"
                value={fmtDollar(portfolio.synergy_total_impact)}
                sub={`+${fmtPct(portfolio.synergy_uplift_pct)} uplift`}
                color="text-green-600"
              />
              <KPICard
                icon={<Target className="h-4 w-4" />}
                label="Portfolio Total"
                value={fmtDollar(portfolio.portfolio_total_impact)}
                sub={`${portfolio.portfolio_roi.toFixed(1)}x portfolio ROI`}
                color="text-indigo-600"
              />
              <KPICard
                icon={<TrendingUp className="h-4 w-4" />}
                label="Payback Period"
                value={`${portfolio.payback_months.toFixed(1)} mo`}
                sub="Time to break even"
              />
            </div>

            {/* Two-column: waterfall + realization */}
            <div className="grid grid-cols-2 gap-6">
              <SynergyWaterfall breakdown={portfolio.synergy_breakdown} />
              <SynergyRealizationTracker companies={portfolio.companies} />
            </div>

            {/* Standalone vs Portfolio comparison */}
            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-blue-500" />
                Standalone vs. Portfolio Impact
              </h3>
              <div className="flex items-end gap-8">
                <div className="flex-1">
                  <div className="text-sm text-gray-500 mb-2">Standalone</div>
                  <div className="h-12 bg-gray-200 rounded-lg relative overflow-hidden">
                    <div
                      className="h-full bg-gray-400 rounded-lg transition-all duration-700"
                      style={{ width: `${(portfolio.standalone_total_impact / portfolio.portfolio_total_impact) * 100}%` }}
                    />
                    <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white">
                      {fmtDollar(portfolio.standalone_total_impact)}
                    </span>
                  </div>
                </div>
                <div className="flex-1">
                  <div className="text-sm text-gray-500 mb-2">Portfolio (with Synergies)</div>
                  <div className="h-12 bg-indigo-100 rounded-lg relative overflow-hidden">
                    <div className="h-full bg-indigo-500 rounded-lg w-full" />
                    <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white">
                      {fmtDollar(portfolio.portfolio_total_impact)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Synergy Engine Tab ── */}
        {activeTab === 'synergy' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">5 Synergy Types</h3>
              <p className="text-sm text-gray-500 mb-6">
                Each synergy type follows a geometric decay curve — maximum benefit for the 2nd company, diminishing returns for each additional company.
              </p>
              <div className="grid grid-cols-5 gap-4">
                {Object.entries(SYNERGY_LABELS).map(([type, label]) => {
                  const impact = portfolio.synergy_breakdown[type] || 0;
                  return (
                    <div
                      key={type}
                      className="rounded-lg p-4 border-2 transition"
                      style={{ borderColor: SYNERGY_COLORS[type] }}
                    >
                      <div className="w-8 h-8 rounded-full mb-3 flex items-center justify-center text-white text-xs font-bold"
                        style={{ backgroundColor: SYNERGY_COLORS[type] }}>
                        {label[0]}
                      </div>
                      <div className="font-semibold text-gray-900 text-sm">{label}</div>
                      <div className="text-xl font-bold mt-2" style={{ color: SYNERGY_COLORS[type] }}>
                        {fmtDollar(impact)}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {((impact / (portfolio.synergy_total_impact || 1)) * 100).toFixed(0)}% of total synergy
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Diminishing returns visualization */}
            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <TrendingDown className="h-4 w-4 text-amber-500" />
                Diminishing Returns Curve
              </h3>
              <p className="text-xs text-gray-500 mb-4">
                Each company's marginal synergy contribution decreases as the portfolio grows.
              </p>
              <div className="flex items-end gap-3 h-40">
                {portfolio.companies.map((c, i) => {
                  const maxSynergy = Math.max(...portfolio.companies.map(x => x.synergy_impact), 1);
                  const height = (c.synergy_impact / maxSynergy) * 100;
                  return (
                    <div key={c.company_id} className="flex-1 flex flex-col items-center">
                      <div className="text-xs font-medium text-gray-600 mb-1">{fmtDollar(c.synergy_impact)}</div>
                      <div
                        className="w-full rounded-t-md transition-all duration-500"
                        style={{
                          height: `${Math.max(height, 4)}%`,
                          backgroundColor: i === 0 ? '#d1d5db' : SYNERGY_COLORS['shared_playbooks'],
                          opacity: 1 - i * 0.12,
                        }}
                      />
                      <div className="text-xs text-gray-500 mt-2 text-center truncate w-full">
                        {c.company_name}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <SynergyWaterfall breakdown={portfolio.synergy_breakdown} />
          </div>
        )}

        {/* ── Companies Tab ── */}
        {activeTab === 'companies' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold text-gray-900">Company-Level Detail</h3>
              <span className="text-sm text-gray-500">Click a row to expand synergy breakdown</span>
            </div>
            {portfolio.companies.map((c, i) => (
              <CompanyRow key={c.company_id} company={c} index={i} />
            ))}
          </div>
        )}

        {/* ── M&A Playbooks Tab ── */}
        {activeTab === 'ma_playbooks' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">M&A Integration Playbooks</h3>
                <p className="text-sm text-gray-500">Track customer success integration across acquisition phases</p>
              </div>
              <div className="flex items-center gap-3 text-sm">
                {(['due_diligence', 'day_1', 'first_100_days', 'integration'] as const).map(phase => {
                  const pbs = playbooks.filter(p => p.phase === phase);
                  const allDone = pbs.every(p => p.status === 'completed');
                  const anyInProgress = pbs.some(p => p.status === 'in_progress');
                  return (
                    <div key={phase} className="flex items-center gap-1.5">
                      <div className={`w-3 h-3 rounded-full ${
                        allDone ? 'bg-green-500' : anyInProgress ? 'bg-blue-500 animate-pulse' : 'bg-gray-300'
                      }`} />
                      <span className="text-gray-600">{PHASE_LABELS[phase]}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {(['due_diligence', 'day_1', 'first_100_days', 'integration'] as const).map(phase => {
              const pbs = playbooks.filter(p => p.phase === phase);
              if (pbs.length === 0) return null;
              return (
                <div key={phase}>
                  <h4 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <Shield className="h-4 w-4" />
                    {PHASE_LABELS[phase]}
                  </h4>
                  <div className="grid grid-cols-2 gap-4">
                    {pbs.map(pb => (
                      <MAPlaybookCard key={pb.id} playbook={pb} />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default PortcoCEODashboard;
