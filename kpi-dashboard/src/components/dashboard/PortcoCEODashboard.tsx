import React, { useState, useEffect, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, Building2, DollarSign, Users, Target,
  BarChart3, ArrowRight, Activity, Layers, Zap, Settings as SettingsIcon,
  Shield, GitMerge, Plus, Trash2, Save, RefreshCw, Loader2, AlertCircle,
  SlidersHorizontal, ChevronDown, ChevronUp
} from 'lucide-react';
import {
  listPortfolios, getPortfolio, getPortfolioImpact, getSliderData,
  getPortfolioConfig, updatePortfolioConfig, createPortfolio,
  addPortfolioCompany, removePortfolioCompany,
  type PortfolioResult, type PortfolioSummary, type PortfolioCompanyInfo,
  type SliderData, type SliderPoint, type PortfolioConfig,
  type CompanyResult, type CostInputs, type SynergyOverride,
} from '../../utils/portfolioApi';
import { apiCall } from '../../utils/api';

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
// Power of 1 Slider Component
// ────────────────────────────────────────────────────────

const PowerOf1Slider: React.FC<{ portfolioId: number }> = ({ portfolioId }) => {
  const [sliderData, setSliderData] = useState<SliderData | null>(null);
  const [selectedPct, setSelectedPct] = useState(1.0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getSliderData(portfolioId)
      .then(setSliderData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [portfolioId]);

  if (loading) return <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-indigo-500" /></div>;
  if (!sliderData || sliderData.slider_points.length === 0) {
    return <div className="text-center py-12 text-gray-500">No data available. Add companies to the portfolio first.</div>;
  }

  const currentPoint = sliderData.slider_points.reduce((prev, curr) =>
    Math.abs(curr.improvement_pct - selectedPct) < Math.abs(prev.improvement_pct - selectedPct) ? curr : prev
  );

  const maxImpact = Math.max(...sliderData.slider_points.map(p => p.portfolio_total_impact));

  return (
    <div className="space-y-6">
      {/* Slider Control */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
          <SlidersHorizontal className="h-5 w-5 text-indigo-500" />
          Power of 1 What-If Analysis
        </h3>
        <p className="text-sm text-gray-500 mb-6">
          Slide to see how a uniform improvement across all 6 levers impacts your entire portfolio with synergies.
        </p>

        <div className="flex items-center gap-6">
          <div className="flex-1">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>0.5%</span>
              <span className="font-bold text-indigo-600 text-lg">{selectedPct.toFixed(1)}% improvement</span>
              <span>6.0%</span>
            </div>
            <input
              type="range" min="0.5" max="6.0" step="0.5"
              value={selectedPct}
              onChange={e => setSelectedPct(parseFloat(e.target.value))}
              className="w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>Conservative</span>
              <span>Target</span>
              <span>World Class</span>
            </div>
          </div>
        </div>

        {/* KPI Summary at current slider position */}
        <div className="grid grid-cols-5 gap-4 mt-6">
          <KPICard icon={<Target className="h-4 w-4" />} label="Portfolio Impact"
            value={fmtDollar(currentPoint.portfolio_total_impact)} color="text-indigo-600"
            sub={`${currentPoint.company_count} companies`} />
          <KPICard icon={<TrendingUp className="h-4 w-4" />} label="Portfolio ROI"
            value={`${currentPoint.portfolio_roi.toFixed(1)}x`} color="text-green-600"
            sub={`vs ${currentPoint.standalone_roi.toFixed(1)}x standalone`} />
          <KPICard icon={<Zap className="h-4 w-4" />} label="Synergy Uplift"
            value={`+${fmtPct(currentPoint.synergy_uplift_pct)}`} color="text-green-600"
            sub={fmtDollar(currentPoint.synergy_impact)} />
          <KPICard icon={<DollarSign className="h-4 w-4" />} label="Investment"
            value={fmtDollar(currentPoint.investment)}
            sub="Synergy-adjusted" />
          <KPICard icon={<TrendingUp className="h-4 w-4" />} label="Payback"
            value={`${currentPoint.payback_months.toFixed(1)} mo`}
            sub="Time to break even" />
        </div>
      </div>

      {/* Scaling Curve Visualization */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Non-Linear Scaling Curve</h3>
        <p className="text-xs text-gray-500 mb-4">
          Same investment, exponentially higher returns. The bars show total portfolio impact at each improvement level.
        </p>
        <div className="flex items-end gap-2 h-48">
          {sliderData.slider_points.map(point => {
            const height = maxImpact > 0 ? (point.portfolio_total_impact / maxImpact) * 100 : 0;
            const isSelected = Math.abs(point.improvement_pct - selectedPct) < 0.01;
            return (
              <div key={point.improvement_pct} className="flex-1 flex flex-col items-center cursor-pointer"
                onClick={() => setSelectedPct(point.improvement_pct)}>
                <div className="text-xs font-medium text-gray-600 mb-1">
                  {point.improvement_pct >= 1 ? fmtDollar(point.portfolio_total_impact) : ''}
                </div>
                <div className="w-full flex flex-col justify-end" style={{ height: '160px' }}>
                  {/* Synergy portion */}
                  <div className="w-full rounded-t-sm transition-all duration-300"
                    style={{
                      height: `${maxImpact > 0 ? (point.synergy_impact / maxImpact) * 160 : 0}px`,
                      backgroundColor: isSelected ? '#22c55e' : '#86efac',
                    }} />
                  {/* Standalone portion */}
                  <div className="w-full transition-all duration-300"
                    style={{
                      height: `${maxImpact > 0 ? (point.standalone_impact / maxImpact) * 160 : 0}px`,
                      backgroundColor: isSelected ? '#6366f1' : '#a5b4fc',
                    }} />
                </div>
                <div className={`text-xs mt-1 ${isSelected ? 'font-bold text-indigo-600' : 'text-gray-500'}`}>
                  {point.improvement_pct}%
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
          <div className="flex items-center gap-1"><div className="w-3 h-3 rounded bg-indigo-400" /> Standalone Impact</div>
          <div className="flex items-center gap-1"><div className="w-3 h-3 rounded bg-green-400" /> Synergy Impact</div>
        </div>
      </div>

      {/* Per-Metric Curves */}
      {sliderData.per_metric_curves && Object.keys(sliderData.per_metric_curves).length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Per-Metric Impact at Selected Level ({selectedPct}%)</h3>
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(sliderData.per_metric_curves).map(([metricId, points]) => {
              const meta = METRIC_DISPLAY[metricId] || { name: metricId, unit: '', color: '#6366f1' };
              const selectedPoint = points.reduce((prev, curr) =>
                Math.abs(curr.improvement_pct - selectedPct) < Math.abs(prev.improvement_pct - selectedPct) ? curr : prev,
                points[0]
              );
              const maxMetricImpact = Math.max(...points.map(p => p.total_impact), 1);
              return (
                <div key={metricId} className="rounded-lg border border-gray-100 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: meta.color }} />
                    <span className="text-sm font-medium text-gray-900">{meta.name}</span>
                  </div>
                  <div className="text-xl font-bold" style={{ color: meta.color }}>
                    {fmtDollar(selectedPoint?.total_impact || 0)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {selectedPoint?.roi !== undefined ? `${(selectedPoint.roi * 100).toFixed(0)}% ROI` : ''}
                  </div>
                  <div className="flex items-end gap-1 h-10 mt-2">
                    {points.map(p => (
                      <div key={p.improvement_pct} className="flex-1 rounded-t-sm transition-all"
                        style={{
                          height: `${(p.total_impact / maxMetricImpact) * 40}px`,
                          backgroundColor: meta.color,
                          opacity: Math.abs(p.improvement_pct - selectedPct) < 0.5 ? 1 : 0.3,
                        }} />
                    ))}
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
      apiCall('/api/data-management/customers').then(r => r.ok ? r.json() : { customers: [] }).catch(() => ({ customers: [] })),
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
