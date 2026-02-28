import React, { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, Building2, DollarSign, Users, Target,
  BarChart3, ArrowRight, Activity, Layers, Zap, Settings as SettingsIcon,
  Shield, GitMerge, Plus, Trash2, Save, RefreshCw, Loader2, AlertCircle,
  SlidersHorizontal, ChevronDown, ChevronUp
} from 'lucide-react';
import {
  listPortfolios, getPortfolio, getPortfolioImpact, getPowerOf1Impact,
  getPortfolioConfig, updatePortfolioConfig, createPortfolio,
  addPortfolioCompany, removePortfolioCompany, getAvailableCustomersForPortfolio,
  type PortfolioResult, type PortfolioSummary, type PortfolioCompanyInfo,
  type PortfolioConfig, type CompanyResult, type CostInputs, type SynergyOverride,
  type PowerOf1ImpactResult,
} from '../../utils/portfolioApi';

// ────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────

const fmtDollar = (n: number) => {
  if (Math.abs(n) >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n.toFixed(0)}`;
};

const fmtPct = (n: number) => `${n.toFixed(1)}%`;

/** Format metric value in native unit (days, hrs, % — not $) for Per-Lever display */
const fmtMetricValue = (value: number, unit: string): string => {
  const u = (unit || '').toLowerCase();
  if (u === 'percent') return `${value.toFixed(1)}%`;
  if (u === 'days') return `${value.toFixed(0)} days`;
  if (u === 'hours') return `${value.toFixed(0)} hrs`;
  return `${value} ${unit}`.trim();
};

const SYNERGY_COLORS: Record<string, string> = {
  shared_playbooks: '#6366f1',
  shared_resources: '#10b981',
  vendor_leverage:  '#f59e0b',
  cross_sell:       '#3b82f6',
  benchmarking:     '#8b5cf6',
};

const SYNERGY_LABELS: Record<string, string> = {
  shared_playbooks: 'Shared Playbooks',
  shared_resources: 'Shared Resources',
  vendor_leverage:  'Vendor Leverage',
  cross_sell:       'Cross-Sell',
  benchmarking:     'Benchmarking',
};

const METRIC_DISPLAY: Record<string, { name: string; unit: string; color: string }> = {
  TTFV: { name: 'Time to First Value', unit: 'days', color: '#ef4444' },
  NRR: { name: 'Net Revenue Retention', unit: '%', color: '#22c55e' },
  GRR: { name: 'Gross Revenue Retention', unit: '%', color: '#3b82f6' },
  ticket_resolution_time: { name: 'Ticket Resolution', unit: 'hrs', color: '#f59e0b' },
  product_adoption: { name: 'Product Adoption', unit: '%', color: '#8b5cf6' },
  expansion_rate: { name: 'Expansion Rate', unit: '%', color: '#06b6d4' },
};

// ────────────────────────────────────────────────────────
// Sub-Components
// ────────────────────────────────────────────────────────

const KPICard: React.FC<{
  icon: React.ReactNode; label: string; value: string; sub?: string; color?: string;
}> = ({ icon, label, value, sub, color = 'text-gray-900' }) => (
  <div className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm">
    <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">{icon}{label}</div>
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
        <Layers className="h-4 w-4 text-indigo-500" />Synergy Value Waterfall
      </h3>
      <div className="space-y-3">
        {Object.entries(breakdown).sort(([, a], [, b]) => b - a).map(([type, amount]) => (
          <div key={type}>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-700">{SYNERGY_LABELS[type] || type}</span>
              <span className="font-medium">{fmtDollar(amount)}</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-3">
              <div className="h-3 rounded-full transition-all duration-500"
                style={{ width: `${(amount / total) * 100}%`, backgroundColor: SYNERGY_COLORS[type] || '#94a3b8' }} />
            </div>
          </div>
        ))}
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
      <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition"
        onClick={() => setExpanded(!expanded)}>
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
          {expanded ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
        </div>
      </div>
      {expanded && company.synergies.length > 0 && (
        <div className="bg-gray-50 px-4 pb-4 border-t border-gray-100">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mt-3 mb-2">Synergy Breakdown</div>
          <div className="grid grid-cols-2 gap-2">
            {company.synergies.map((s, i) => (
              <div key={i} className="flex items-center gap-2 bg-white rounded px-3 py-2 text-sm border border-gray-100">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: SYNERGY_COLORS[s.type] || '#94a3b8' }} />
                <span className="text-gray-600">{SYNERGY_LABELS[s.type] || s.type}</span>
                <span className="ml-auto font-medium text-gray-900">{s.multiplier.toFixed(2)}x</span>
                <span className="text-green-600 font-medium">+{fmtDollar(s.dollar_impact)}</span>
              </div>
            ))}
          </div>
          {company.synergy_adjusted_investment < company.standalone_investment && (
            <div className="mt-2 text-xs text-emerald-600">
              Investment reduced {fmtDollar(company.standalone_investment)} {'→'} {fmtDollar(company.synergy_adjusted_investment)} via shared resources
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const SynergyRealizationTracker: React.FC<{ companies: CompanyResult[] }> = ({ companies }) => {
  const withSynergy = companies.filter(c => c.synergy_impact > 0);
  const totalSynergy = withSynergy.reduce((sum, c) => sum + c.synergy_impact, 0);
  const realizedSynergy = withSynergy.slice(0, Math.ceil(withSynergy.length / 2)).reduce((sum, c) => sum + c.synergy_impact, 0);
  const realizationPct = totalSynergy > 0 ? (realizedSynergy / totalSynergy) * 100 : 0;
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <Activity className="h-4 w-4 text-green-500" />Synergy Realization Tracker
      </h3>
      <div className="flex items-end gap-4 mb-4">
        <div>
          <div className="text-3xl font-bold text-green-600">{fmtPct(realizationPct)}</div>
          <div className="text-xs text-gray-500">of synergy value realized</div>
        </div>
        <div className="text-sm text-gray-500">{fmtDollar(realizedSynergy)} of {fmtDollar(totalSynergy)}</div>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-4">
        <div className="h-4 rounded-full bg-gradient-to-r from-green-400 to-emerald-500 transition-all duration-700"
          style={{ width: `${realizationPct}%` }} />
      </div>
      <div className="mt-4 space-y-2">
        {withSynergy.map((c, i) => (
          <div key={c.company_id} className="flex items-center justify-between text-sm">
            <span className="text-gray-700">{c.company_name}</span>
            <div className="flex items-center gap-2">
              <span className="text-green-600 font-medium">+{fmtDollar(c.synergy_impact)}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded ${
                i < Math.ceil(withSynergy.length / 2) ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
              }`}>{i < Math.ceil(withSynergy.length / 2) ? 'Realized' : 'Projected'}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ────────────────────────────────────────────────────────
// Power of 1 — 6 independent levers
// ────────────────────────────────────────────────────────

const LEVER_IDS = ['TTFV', 'NRR', 'GRR', 'ticket_resolution_time', 'product_adoption', 'expansion_rate'];

const defaultLeverPcts: Record<string, number> = Object.fromEntries(LEVER_IDS.map(id => [id, 1.0]));

const PowerOf1Slider: React.FC<{ portfolioId: number }> = ({ portfolioId }) => {
  const [leverPcts, setLeverPcts] = useState<Record<string, number>>(defaultLeverPcts);
  const [impact, setImpact] = useState<PowerOf1ImpactResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchImpact = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPowerOf1Impact(portfolioId, leverPcts);
      setImpact(data);
    } catch (e: any) {
      setError(e?.message || 'Failed to load impact');
      setImpact(null);
    } finally {
      setLoading(false);
    }
  }, [portfolioId, leverPcts]);

  useEffect(() => {
    const t = setTimeout(fetchImpact, 300);
    return () => clearTimeout(t);
  }, [fetchImpact]);

  const setLever = (metricId: string, value: number) => {
    setLeverPcts(prev => ({ ...prev, [metricId]: value }));
  };

  if (error && !impact) {
    return (
      <div className="text-center py-12 text-amber-600">
        <AlertCircle className="h-8 w-8 mx-auto mb-2" />
        <p>{error}</p>
        <button onClick={fetchImpact} className="mt-2 text-indigo-600 text-sm">Retry</button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 6 lever sliders */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
          <SlidersHorizontal className="h-5 w-5 text-indigo-500" />
          Power of 1 — 6 Levers
        </h3>
        <p className="text-sm text-gray-500 mb-6">
          Set improvement % per lever; not all levers move in lockstep. ROI and investment recalculate from your choices.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {LEVER_IDS.map(metricId => {
            const meta = METRIC_DISPLAY[metricId] || { name: metricId, unit: '', color: '#6366f1' };
            const value = leverPcts[metricId] ?? 1.0;
            return (
              <div key={metricId} className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: meta.color }} />
                    <span className="text-sm font-medium text-gray-900">{meta.name}</span>
                  </div>
                  <span className="text-sm font-semibold text-indigo-600">{value.toFixed(1)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="6"
                  step="0.5"
                  value={value}
                  onChange={e => setLever(metricId, parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                />
              </div>
            );
          })}
        </div>

        {/* KPI Summary */}
        {loading && !impact && (
          <div className="flex items-center justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-indigo-500" /></div>
        )}
        {impact && (
          <div className="grid grid-cols-5 gap-4 mt-6">
            <KPICard icon={<Target className="h-4 w-4" />} label="Portfolio Impact"
              value={fmtDollar(impact.portfolio_total_impact)} color="text-indigo-600"
              sub={`${impact.company_count} companies`} />
            <KPICard icon={<TrendingUp className="h-4 w-4" />} label="Portfolio ROI"
              value={`${impact.portfolio_roi.toFixed(1)}x`} color="text-green-600"
              sub={`vs ${impact.standalone_roi.toFixed(1)}x standalone`} />
            <KPICard icon={<Zap className="h-4 w-4" />} label="Synergy Uplift"
              value={`+${fmtPct(impact.synergy_uplift_pct)}`} color="text-green-600"
              sub={fmtDollar(impact.synergy_total_impact)} />
            <KPICard icon={<DollarSign className="h-4 w-4" />} label="Investment"
              value={fmtDollar(impact.synergy_adjusted_investment)}
              sub="Synergy-adjusted" />
            <KPICard icon={<TrendingUp className="h-4 w-4" />} label="Payback"
              value={`${impact.payback_months.toFixed(1)} mo`}
              sub="Time to break even" />
          </div>
        )}
      </div>

      {/* Per-lever impact breakdown */}
      {impact?.per_metric_impacts && Object.keys(impact.per_metric_impacts).length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Per-Lever Impact at Current Settings</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {LEVER_IDS.map(metricId => {
              const meta = METRIC_DISPLAY[metricId] || { name: metricId, unit: '', color: '#6366f1' };
              const m = impact.per_metric_impacts[metricId];
              if (!m) return null;
              const unit = m.unit ?? meta.unit ?? '';
              const hasNative = typeof m.baseline === 'number' && typeof m.new_value === 'number' && unit;
              return (
                <div key={metricId} className="rounded-lg border border-gray-100 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: meta.color }} />
                    <span className="text-sm font-medium text-gray-900">{meta.name}</span>
                  </div>
                  <div className="text-xs text-gray-500 mb-1">{m.improvement_pct.toFixed(1)}% improvement</div>
                  {hasNative && (
                    <div className="text-sm font-semibold text-gray-800 mb-1" style={{ color: meta.color }}>
                      {fmtMetricValue(m.baseline!, unit)} → {fmtMetricValue(m.new_value!, unit)}
                    </div>
                  )}
                  <div className="text-sm font-bold" style={{ color: meta.color }}>
                    Impact: {fmtDollar(m.total_impact)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {typeof m.roi === 'number' ? `${(m.roi * 100).toFixed(0)}% ROI` : ''}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

// ────────────────────────────────────────────────────────
// Settings Tab Component
// ────────────────────────────────────────────────────────

const PortfolioSettings: React.FC<{
  portfolioId: number;
  companies: PortfolioCompanyInfo[];
  onRefresh: () => void;
}> = ({ portfolioId, companies, onRefresh }) => {
  const [config, setConfig] = useState<PortfolioConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [availableCustomers, setAvailableCustomers] = useState<Array<{ customer_id: number; customer_name: string }>>([]);
  const [newCustomerId, setNewCustomerId] = useState('');
  const [costInputs, setCostInputs] = useState<CostInputs>({});
  const [roleRates, setRoleRates] = useState<Record<string, number>>({});
  const [synergyOverrides, setSynergyOverrides] = useState<Record<string, SynergyOverride>>({});
  const [message, setMessage] = useState('');

  useEffect(() => {
    Promise.all([
      getPortfolioConfig(portfolioId),
      getAvailableCustomersForPortfolio().catch(() => ({ customers: [] })),
    ]).then(([cfg, custData]) => {
      setConfig(cfg);
      setCostInputs(cfg.cost_inputs);
      setRoleRates(cfg.role_rate_overrides);
      setSynergyOverrides(cfg.synergy_overrides);
      setAvailableCustomers(custData.customers || []);
    }).catch(console.error).finally(() => setLoading(false));
  }, [portfolioId]);

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      await updatePortfolioConfig(portfolioId, {
        cost_inputs: costInputs,
        role_rate_overrides: roleRates,
        synergy_overrides: synergyOverrides,
      });
      setMessage('Configuration saved successfully');
      onRefresh();
    } catch (err: any) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleAddCompany = async () => {
    if (!newCustomerId) return;
    try {
      await addPortfolioCompany(portfolioId, { customer_id: parseInt(newCustomerId) });
      setNewCustomerId('');
      onRefresh();
    } catch (err: any) {
      setMessage(`Error: ${err.message}`);
    }
  };

  const handleRemoveCompany = async (customerId: number) => {
    try {
      await removePortfolioCompany(portfolioId, customerId);
      onRefresh();
    } catch (err: any) {
      setMessage(`Error: ${err.message}`);
    }
  };

  if (loading) return <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-indigo-500" /></div>;

  return (
    <div className="space-y-6">
      {message && (
        <div className={`p-3 rounded-lg text-sm ${message.startsWith('Error') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
          {message}
        </div>
      )}

      {/* Company Management */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Building2 className="h-4 w-4 text-indigo-500" />Portfolio Companies
        </h3>
        <div className="space-y-2 mb-4">
          {companies.map(c => (
            <div key={c.customer_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div>
                <div className="font-medium text-gray-900">{c.customer_name}</div>
                <div className="text-xs text-gray-500">ARR: {fmtDollar(c.arr)} | {c.account_count} accounts | {c.vertical || 'general'}</div>
              </div>
              <button onClick={() => handleRemoveCompany(c.customer_id)}
                className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded transition">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500 mb-2">Companies listed have Power of 1 enabled in CS Pulse and at least one account (for ARR).</p>
        <div className="flex gap-2">
          <select value={newCustomerId} onChange={e => setNewCustomerId(e.target.value)}
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500">
            <option value="">Select a company to add...</option>
            {availableCustomers
              .filter(c => !companies.some(pc => pc.customer_id === c.customer_id))
              .map(c => (
                <option key={c.customer_id} value={c.customer_id}>{c.customer_name}</option>
              ))}
          </select>
          <button onClick={handleAddCompany} disabled={!newCustomerId}
            className="flex items-center gap-1 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-indigo-700 transition">
            <Plus className="h-4 w-4" />Add
          </button>
        </div>
      </div>

      {/* Cost Inputs */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-green-500" />Investment & Cost Inputs
        </h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Total Investment ($)</label>
            <input type="number" value={costInputs.total_investment || ''}
              onChange={e => setCostInputs({ ...costInputs, total_investment: parseFloat(e.target.value) || 0 })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">CS Initiatives ($)</label>
            <input type="number" value={costInputs.cs_initiatives || ''}
              onChange={e => setCostInputs({ ...costInputs, cs_initiatives: parseFloat(e.target.value) || 0 })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Platform Cost ($)</label>
            <input type="number" value={costInputs.platform_cost || ''}
              onChange={e => setCostInputs({ ...costInputs, platform_cost: parseFloat(e.target.value) || 0 })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500" />
          </div>
        </div>
      </div>

      {/* Role Hourly Rates */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Users className="h-4 w-4 text-blue-500" />Role Hourly Rates ($/hr)
        </h3>
        <div className="grid grid-cols-5 gap-4">
          {Object.entries(roleRates).map(([role, rate]) => (
            <div key={role}>
              <label className="block text-xs text-gray-500 mb-1 capitalize">{role.replace('_', ' ')}</label>
              <input type="number" value={rate}
                onChange={e => setRoleRates({ ...roleRates, [role]: parseFloat(e.target.value) || 0 })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500" />
            </div>
          ))}
        </div>
      </div>

      {/* Synergy Overrides */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Zap className="h-4 w-4 text-amber-500" />Synergy Parameters
        </h3>
        <div className="grid grid-cols-5 gap-4">
          {Object.entries(synergyOverrides).map(([type, override]) => (
            <div key={type} className="space-y-2">
              <div className="text-xs font-medium text-gray-700">{SYNERGY_LABELS[type] || type}</div>
              <div>
                <label className="block text-xs text-gray-400">Base Lift %</label>
                <input type="number" step="0.5" value={override.base_lift_pct}
                  onChange={e => setSynergyOverrides({
                    ...synergyOverrides,
                    [type]: { ...override, base_lift_pct: parseFloat(e.target.value) || 0 },
                  })}
                  className="w-full border border-gray-300 rounded-lg px-2 py-1 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-gray-400">Decay Rate</label>
                <input type="number" step="0.05" min="0" max="1" value={override.decay_rate}
                  onChange={e => setSynergyOverrides({
                    ...synergyOverrides,
                    [type]: { ...override, decay_rate: parseFloat(e.target.value) || 0 },
                  })}
                  className="w-full border border-gray-300 rounded-lg px-2 py-1 text-sm" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Resource Pool Summary */}
      {config?.resource_pool && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Resource Pool Summary</h3>
          <div className="grid grid-cols-5 gap-3">
            {config.resource_pool.roles.map(role => (
              <div key={role.role} className="p-3 bg-gray-50 rounded-lg">
                <div className="text-xs font-medium text-gray-700">{role.display_name}</div>
                <div className="text-lg font-bold text-gray-900">{role.annual_hours.toLocaleString()} hrs</div>
                <div className="text-xs text-gray-500">{role.fte} FTE | ${role.hourly_rate}/hr</div>
                <div className="text-xs text-gray-400">{role.description}</div>
              </div>
            ))}
          </div>
          <div className="mt-3 flex gap-6 text-sm text-gray-600">
            <span>Total: <strong>{config.resource_pool.totals.total_hours.toLocaleString()} hours</strong></span>
            <span>FTE: <strong>{config.resource_pool.totals.total_fte}</strong></span>
            <span>Annual Cost: <strong>{fmtDollar(config.resource_pool.totals.total_annual_cost)}</strong></span>
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="flex justify-end">
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition disabled:opacity-50">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save Configuration
        </button>
      </div>
    </div>
  );
};

// ────────────────────────────────────────────────────────
// Portfolio Selector (for first-time or multi-portfolio use)
// ────────────────────────────────────────────────────────

const PortfolioSelector: React.FC<{ onSelect: (id: number) => void }> = ({ onSelect }) => {
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');

  useEffect(() => {
    listPortfolios()
      .then(data => setPortfolios(data.portfolios))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleCreate = async () => {
    if (!newName) return;
    setCreating(true);
    try {
      const result = await createPortfolio({ portfolio_name: newName });
      onSelect(result.portfolio_id);
    } catch (err) {
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-lg w-full bg-white rounded-xl shadow-lg p-8">
        <h2 className="text-xl font-bold text-gray-900 mb-2">PortCo CEO Dashboard</h2>
        <p className="text-sm text-gray-500 mb-6">Select a portfolio or create a new one to get started.</p>

        {portfolios.length > 0 && (
          <div className="space-y-2 mb-6">
            {portfolios.map(p => (
              <button key={p.portfolio_id} onClick={() => onSelect(p.portfolio_id)}
                className="w-full text-left p-4 border border-gray-200 rounded-lg hover:border-indigo-400 hover:bg-indigo-50 transition">
                <div className="font-semibold text-gray-900">{p.portfolio_name}</div>
                <div className="text-xs text-gray-500">{p.company_count} companies | {fmtDollar(p.total_arr)} ARR</div>
              </button>
            ))}
          </div>
        )}

        <div className="border-t border-gray-200 pt-4">
          <div className="text-sm font-medium text-gray-700 mb-2">Create New Portfolio</div>
          <div className="flex gap-2">
            <input type="text" value={newName} onChange={e => setNewName(e.target.value)}
              placeholder="Portfolio name..." className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500" />
            <button onClick={handleCreate} disabled={!newName || creating}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-indigo-700 transition">
              {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Create'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ────────────────────────────────────────────────────────
// Main Dashboard
// ────────────────────────────────────────────────────────

type TabKey = 'overview' | 'power_of_1' | 'synergy' | 'companies' | 'settings';

const PortcoCEODashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [portfolioId, setPortfolioId] = useState<number | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioResult | null>(null);
  const [companies, setCompanies] = useState<PortfolioCompanyInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [improvementPct, setImprovementPct] = useState(1.0);

  const loadPortfolio = useCallback(async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const [detail, impact] = await Promise.all([
        getPortfolio(id),
        getPortfolioImpact(id, improvementPct),
      ]);
      setCompanies(detail.companies);
      setPortfolio(impact);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [improvementPct]);

  useEffect(() => {
    if (portfolioId) loadPortfolio(portfolioId);
  }, [portfolioId, loadPortfolio]);

  // Auto-select first portfolio on mount
  useEffect(() => {
    listPortfolios().then(data => {
      if (data.portfolios.length > 0) {
        setPortfolioId(data.portfolios[0].portfolio_id);
      }
    }).catch(() => {});
  }, []);

  if (!portfolioId) return <PortfolioSelector onSelect={setPortfolioId} />;

  if (loading && !portfolio) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500 mx-auto mb-4" />
          <p className="text-gray-500">Loading portfolio data...</p>
        </div>
      </div>
    );
  }

  if (error && !portfolio) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertCircle className="h-8 w-8 text-amber-500 mx-auto mb-4" />
          <p className="text-gray-700 font-medium mb-2">Could not load portfolio</p>
          <p className="text-gray-500 text-sm mb-4">{error}</p>
          <button onClick={() => loadPortfolio(portfolioId)}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm">Retry</button>
        </div>
      </div>
    );
  }

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'overview', label: 'Portfolio Overview', icon: <BarChart3 className="h-4 w-4" /> },
    { key: 'power_of_1', label: 'Power of 1', icon: <SlidersHorizontal className="h-4 w-4" /> },
    { key: 'synergy', label: 'Synergy Engine', icon: <Zap className="h-4 w-4" /> },
    { key: 'companies', label: 'Company Detail', icon: <Building2 className="h-4 w-4" /> },
    { key: 'settings', label: 'Settings', icon: <SettingsIcon className="h-4 w-4" /> },
  ];

  const p = portfolio;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-700 to-purple-700 text-white px-8 py-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-indigo-200 font-medium">CS Pulse GrowthPulse</div>
            <h1 className="text-2xl font-bold">PortCo CEO Dashboard</h1>
            <p className="text-indigo-200 text-sm mt-1">
              {p?.portfolio_name || 'Loading...'} — {p?.company_count || 0} Companies
            </p>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className="text-indigo-200 text-xs">Total ARR</div>
              <div className="text-xl font-bold">{p ? fmtDollar(p.total_arr) : '...'}</div>
            </div>
            <div className="text-right">
              <div className="text-indigo-200 text-xs">Portfolio ROI</div>
              <div className="text-xl font-bold">{p ? `${p.portfolio_roi.toFixed(1)}x` : '...'}</div>
            </div>
            <div className="text-right">
              <div className="text-indigo-200 text-xs">Synergy Uplift</div>
              <div className="text-xl font-bold text-green-300">
                {p ? `+${fmtPct(p.synergy_uplift_pct)}` : '...'}
              </div>
            </div>
            <button onClick={() => loadPortfolio(portfolioId)}
              className="p-2 rounded-lg hover:bg-white/10 transition" title="Refresh">
              <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Tab Bar */}
      <div className="bg-white border-b border-gray-200 px-8">
        <div className="flex gap-1">
          {tabs.map(t => (
            <button key={t.key} onClick={() => setActiveTab(t.key)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition ${
                activeTab === t.key
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}>
              {t.icon}{t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="px-8 py-6">

        {/* ── Overview Tab ── */}
        {activeTab === 'overview' && p && (
          <div className="space-y-6">
            <div className="grid grid-cols-5 gap-4">
              <KPICard icon={<Building2 className="h-4 w-4" />} label="Portfolio Companies"
                value={String(p.company_count)} sub={`${fmtDollar(p.total_arr)} combined ARR`} />
              <KPICard icon={<DollarSign className="h-4 w-4" />} label="Standalone Impact"
                value={fmtDollar(p.standalone_total_impact)} sub={`${p.standalone_roi.toFixed(1)}x ROI`} />
              <KPICard icon={<Zap className="h-4 w-4" />} label="Synergy Impact"
                value={fmtDollar(p.synergy_total_impact)} sub={`+${fmtPct(p.synergy_uplift_pct)} uplift`} color="text-green-600" />
              <KPICard icon={<Target className="h-4 w-4" />} label="Portfolio Total"
                value={fmtDollar(p.portfolio_total_impact)} sub={`${p.portfolio_roi.toFixed(1)}x portfolio ROI`} color="text-indigo-600" />
              <KPICard icon={<TrendingUp className="h-4 w-4" />} label="Payback Period"
                value={`${p.payback_months.toFixed(1)} mo`} sub="Time to break even" />
            </div>

            <div className="grid grid-cols-2 gap-6">
              <SynergyWaterfall breakdown={p.synergy_breakdown} />
              <SynergyRealizationTracker companies={p.companies} />
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-blue-500" />Standalone vs. Portfolio Impact
              </h3>
              <div className="flex items-end gap-8">
                <div className="flex-1">
                  <div className="text-sm text-gray-500 mb-2">Standalone</div>
                  <div className="h-12 bg-gray-200 rounded-lg relative overflow-hidden">
                    <div className="h-full bg-gray-400 rounded-lg transition-all duration-700"
                      style={{ width: `${p.portfolio_total_impact > 0 ? (p.standalone_total_impact / p.portfolio_total_impact) * 100 : 0}%` }} />
                    <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white">
                      {fmtDollar(p.standalone_total_impact)}
                    </span>
                  </div>
                </div>
                <div className="flex-1">
                  <div className="text-sm text-gray-500 mb-2">Portfolio (with Synergies)</div>
                  <div className="h-12 bg-indigo-100 rounded-lg relative overflow-hidden">
                    <div className="h-full bg-indigo-500 rounded-lg w-full" />
                    <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white">
                      {fmtDollar(p.portfolio_total_impact)}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Investment Summary */}
            {p.investment_summary && (
              <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
                <h3 className="text-sm font-semibold text-gray-900 mb-4">Shared Investment Model</h3>
                <div className="grid grid-cols-4 gap-4">
                  <div className="p-3 bg-indigo-50 rounded-lg">
                    <div className="text-xs text-gray-500">Total Investment (per co)</div>
                    <div className="text-lg font-bold text-indigo-700">{fmtDollar(p.investment_summary.total_investment)}</div>
                  </div>
                  <div className="p-3 bg-green-50 rounded-lg">
                    <div className="text-xs text-gray-500">CS Initiatives (80%)</div>
                    <div className="text-lg font-bold text-green-700">{fmtDollar(p.investment_summary.cs_initiatives)}</div>
                  </div>
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <div className="text-xs text-gray-500">Platform Cost (20%)</div>
                    <div className="text-lg font-bold text-blue-700">{fmtDollar(p.investment_summary.platform_cost)}</div>
                  </div>
                  <div className="p-3 bg-purple-50 rounded-lg">
                    <div className="text-xs text-gray-500">Combined Impact</div>
                    <div className="text-lg font-bold text-purple-700">{fmtDollar(p.portfolio_total_impact)}</div>
                    <div className="text-xs text-purple-500">across {p.company_count} companies</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Power of 1 Tab ── */}
        {activeTab === 'power_of_1' && portfolioId && (
          <PowerOf1Slider portfolioId={portfolioId} />
        )}

        {/* ── Synergy Engine Tab ── */}
        {activeTab === 'synergy' && p && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">5 Synergy Types</h3>
              <p className="text-sm text-gray-500 mb-6">
                Each synergy type follows a geometric decay curve — maximum benefit for the 2nd company, diminishing returns for each additional company.
              </p>
              <div className="grid grid-cols-5 gap-4">
                {Object.entries(SYNERGY_LABELS).map(([type, label]) => {
                  const impact = p.synergy_breakdown[type] || 0;
                  return (
                    <div key={type} className="rounded-lg p-4 border-2 transition" style={{ borderColor: SYNERGY_COLORS[type] }}>
                      <div className="w-8 h-8 rounded-full mb-3 flex items-center justify-center text-white text-xs font-bold"
                        style={{ backgroundColor: SYNERGY_COLORS[type] }}>{label[0]}</div>
                      <div className="font-semibold text-gray-900 text-sm">{label}</div>
                      <div className="text-xl font-bold mt-2" style={{ color: SYNERGY_COLORS[type] }}>{fmtDollar(impact)}</div>
                      <div className="text-xs text-gray-400 mt-1">
                        {p.synergy_total_impact > 0 ? ((impact / p.synergy_total_impact) * 100).toFixed(0) : 0}% of total synergy
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <TrendingDown className="h-4 w-4 text-amber-500" />Diminishing Returns Curve
              </h3>
              <p className="text-xs text-gray-500 mb-4">
                Each company's marginal synergy contribution decreases as the portfolio grows.
              </p>
              <div className="flex items-end gap-3 h-40">
                {p.companies.map((c, i) => {
                  const maxSynergy = Math.max(...p.companies.map(x => x.synergy_impact), 1);
                  const height = (c.synergy_impact / maxSynergy) * 100;
                  return (
                    <div key={c.company_id} className="flex-1 flex flex-col items-center">
                      <div className="text-xs font-medium text-gray-600 mb-1">{fmtDollar(c.synergy_impact)}</div>
                      <div className="w-full rounded-t-md transition-all duration-500"
                        style={{
                          height: `${Math.max(height, 4)}%`,
                          backgroundColor: i === 0 ? '#d1d5db' : SYNERGY_COLORS['shared_playbooks'],
                          opacity: 1 - i * 0.12,
                        }} />
                      <div className="text-xs text-gray-500 mt-2 text-center truncate w-full">{c.company_name}</div>
                    </div>
                  );
                })}
              </div>
            </div>

            <SynergyWaterfall breakdown={p.synergy_breakdown} />
          </div>
        )}

        {/* ── Companies Tab ── */}
        {activeTab === 'companies' && p && (
          <div className="space-y-3">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold text-gray-900">Company-Level Detail</h3>
              <span className="text-sm text-gray-500">Click a row to expand synergy breakdown</span>
            </div>
            {p.companies.map((c, i) => (
              <CompanyRow key={c.company_id} company={c} index={i} />
            ))}
          </div>
        )}

        {/* ── Settings Tab ── */}
        {activeTab === 'settings' && portfolioId && (
          <PortfolioSettings
            portfolioId={portfolioId}
            companies={companies}
            onRefresh={() => loadPortfolio(portfolioId)}
          />
        )}
      </div>
    </div>
  );
};

export default PortcoCEODashboard;
