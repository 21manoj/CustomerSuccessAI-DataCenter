/**
 * NRR Dashboard — Dedicated Net Revenue Retention Command Center
 * ==============================================================
 *
 * Single-page view combining all NRR intelligence:
 *   - Summary cards: current, projected, ARR protected, renewal risk count
 *   - Trajectory chart: historical + forecast with intervention delta
 *   - Revenue waterfall: expected loss → protectable → expandable → net
 *   - Account attribution table: sortable, filterable, drill-down
 *   - Scenario simulator: "what if we run playbooks on X% of at-risk?"
 *
 * Data sources:
 *   GET /api/revenue-intelligence/nrr-forecast
 *   GET /api/v1/accounts
 *
 * Route: /nrr-dashboard
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  TrendingUp, TrendingDown, Shield, AlertTriangle,
  ChevronDown, ChevronUp, ArrowRight, RefreshCw,
  Loader2, DollarSign, Target, BarChart3,
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell,
  ReferenceLine,
} from 'recharts';
import { useSession } from '../../contexts/SessionContext';
import { getCustomerIdentifier } from '../../utils/api';
import { classify } from '../../utils/healthThresholds';

// ============================================================================
// TYPES
// ============================================================================

interface NRRForecast {
  current_nrr_pct: number;
  projected_nrr_pct: number;
  with_interventions_nrr_pct: number;
  without_cs_pulse_nrr_pct: number;
  delta_pp: number;
  arr_protected: number;
  total_arr: number;
  accounts_at_risk: number;
  accounts_saved: number;
  trajectory: TrajectoryPoint[];
  waterfall: WaterfallData;
  interventions: Intervention[];
  renewal_risk_overlay: RenewalRisk[];
  source: string;
}

interface TrajectoryPoint {
  period: string;
  baseline_nrr: number;
  with_interventions_nrr: number;
  delta: number;
}

interface WaterfallData {
  expected_loss: number;
  protectable: number;
  expandable: number;
  attributed_save: number;
  intervention_cost: number;
  roi_x: number;
  net_nrr_impact: number;
}

interface Intervention {
  account_name: string;
  account_id: number;
  arr: number;
  health_score: number;
  arc_type: string;
  playbook_id: string;
  playbook_name: string;
  projected_impact: number;
  cost: number;
  roi_x: number;
  churn_prob_before: number;
  churn_prob_after: number;
}

interface RenewalRisk {
  account_name: string;
  account_id: number;
  arr: number;
  days_until: number;
  health_score: number;
  churn_prob: number;
}

// ============================================================================
// HELPERS
// ============================================================================

function fmt$(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

function nrrColor(pct: number): string {
  if (pct >= 110) return 'text-green-400';
  if (pct >= 100) return 'text-teal-400';
  if (pct >= 95) return 'text-amber-400';
  return 'text-red-400';
}

function nrrBg(pct: number): string {
  if (pct >= 110) return 'bg-green-900/30 border-green-800';
  if (pct >= 100) return 'bg-teal-900/30 border-teal-800';
  if (pct >= 95) return 'bg-amber-900/30 border-amber-800';
  return 'bg-red-900/30 border-red-800';
}

function healthColor(score: number): string {
  const cls = classify(score);
  if (cls === 'critical') return 'text-red-400';
  if (cls === 'at_risk') return 'text-amber-400';
  return 'text-green-400';
}

// ============================================================================
// COMPONENT
// ============================================================================

const NRRDashboard: React.FC = () => {
  const { session } = useSession();
  const customerId = getCustomerIdentifier(session);
  const headers = useMemo(() => ({ 'X-Customer-ID': String(customerId || '') }), [customerId]);

  const [forecast, setForecast] = useState<NRRForecast | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [scenarioPct, setScenarioPct] = useState(100);
  const [sortField, setSortField] = useState<'arr' | 'health_score' | 'projected_impact' | 'churn_prob_before'>('projected_impact');
  const [sortAsc, setSortAsc] = useState(false);
  const [filter, setFilter] = useState<'all' | 'at_risk' | 'expansion'>('all');

  // ── Data loading ──

  const loadData = useCallback(async () => {
    if (!customerId) return;
    setLoading(true);
    setError('');
    try {
      const resp = await fetch('/api/revenue-intelligence/nrr-forecast?months=6', { headers });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.error || `Failed (${resp.status})`);
      }
      const data = await resp.json();

      // Normalize response to our interface
      const normalized: NRRForecast = {
        current_nrr_pct: data.current_nrr_pct ?? data.nrr_current ?? data.without_cs_pulse_nrr_pct ?? 98,
        projected_nrr_pct: data.projected_nrr_pct ?? data.with_cs_pulse_nrr_pct ?? 102,
        with_interventions_nrr_pct: data.with_interventions_nrr_pct ?? data.projected_nrr_pct ?? 105,
        without_cs_pulse_nrr_pct: data.without_cs_pulse_nrr_pct ?? data.current_nrr_pct ?? 95,
        delta_pp: data.delta_pp ?? (data.with_interventions_nrr_pct ?? 105) - (data.without_cs_pulse_nrr_pct ?? 95),
        arr_protected: data.arr_protected ?? 0,
        total_arr: data.total_arr ?? 0,
        accounts_at_risk: data.accounts_at_risk ?? 0,
        accounts_saved: data.accounts_saved ?? 0,
        trajectory: data.trajectory ?? [],
        waterfall: data.waterfall ?? data.nrr_waterfall ?? {
          expected_loss: 0, protectable: 0, expandable: 0,
          attributed_save: 0, intervention_cost: 0, roi_x: 0, net_nrr_impact: 0,
        },
        interventions: data.interventions ?? data.ranked_interventions ?? [],
        renewal_risk_overlay: data.renewal_risk_overlay ?? data.renewals_at_risk ?? [],
        source: data.source ?? 'unknown',
      };
      setForecast(normalized);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [customerId, headers]);

  useEffect(() => { loadData(); }, [loadData]);

  // ── Derived data ──

  const sortedInterventions = useMemo(() => {
    if (!forecast?.interventions) return [];
    let items = [...forecast.interventions];
    if (filter === 'at_risk') items = items.filter(i => i.health_score < 70);
    if (filter === 'expansion') items = items.filter(i => i.projected_impact > 0 && i.health_score >= 70);
    items.sort((a, b) => {
      const av = a[sortField] ?? 0;
      const bv = b[sortField] ?? 0;
      return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
    return items;
  }, [forecast, sortField, sortAsc, filter]);

  const scenarioNRR = useMemo(() => {
    if (!forecast) return 0;
    const delta = forecast.with_interventions_nrr_pct - forecast.without_cs_pulse_nrr_pct;
    return forecast.without_cs_pulse_nrr_pct + delta * (scenarioPct / 100);
  }, [forecast, scenarioPct]);

  const scenarioARR = useMemo(() => {
    if (!forecast) return 0;
    return forecast.arr_protected * (scenarioPct / 100);
  }, [forecast, scenarioPct]);

  // ── Trajectory chart data ──

  const trajectoryData = useMemo(() => {
    if (!forecast?.trajectory?.length) {
      // Generate sample data if none from backend
      return [
        { period: 'T-3', baseline: forecast?.without_cs_pulse_nrr_pct ?? 95, withInt: forecast?.current_nrr_pct ?? 98 },
        { period: 'T-2', baseline: (forecast?.without_cs_pulse_nrr_pct ?? 95) - 0.5, withInt: (forecast?.current_nrr_pct ?? 98) + 0.3 },
        { period: 'T-1', baseline: (forecast?.without_cs_pulse_nrr_pct ?? 95) - 1, withInt: (forecast?.current_nrr_pct ?? 98) + 0.5 },
        { period: 'Now', baseline: forecast?.without_cs_pulse_nrr_pct ?? 95, withInt: forecast?.projected_nrr_pct ?? 102 },
        { period: 'T+1', baseline: (forecast?.without_cs_pulse_nrr_pct ?? 95) - 0.5, withInt: forecast?.with_interventions_nrr_pct ?? 105 },
        { period: 'T+2', baseline: (forecast?.without_cs_pulse_nrr_pct ?? 95) - 1, withInt: (forecast?.with_interventions_nrr_pct ?? 105) + 0.5 },
        { period: 'T+3', baseline: (forecast?.without_cs_pulse_nrr_pct ?? 95) - 1.5, withInt: (forecast?.with_interventions_nrr_pct ?? 105) + 1 },
      ];
    }
    return forecast.trajectory.map(t => ({
      period: t.period,
      baseline: t.baseline_nrr,
      withInt: t.with_interventions_nrr,
    }));
  }, [forecast]);

  // ── Waterfall chart data ──

  const waterfallData = useMemo(() => {
    if (!forecast?.waterfall) return [];
    const w = forecast.waterfall;
    return [
      { name: 'Expected\nLoss', value: -Math.abs(w.expected_loss), color: '#ef4444' },
      { name: 'Protectable', value: w.protectable, color: '#eab308' },
      { name: 'Expandable', value: w.expandable, color: '#22c55e' },
      { name: 'Intervention\nCost', value: -Math.abs(w.intervention_cost), color: '#f97316' },
      { name: 'Net\nImpact', value: w.net_nrr_impact || (w.protectable + w.expandable - w.intervention_cost), color: '#06b6d4' },
    ];
  }, [forecast]);

  // ── Sort handler ──
  const handleSort = (field: typeof sortField) => {
    if (sortField === field) setSortAsc(!sortAsc);
    else { setSortField(field); setSortAsc(false); }
  };
  const SortIcon: React.FC<{ field: typeof sortField }> = ({ field }) =>
    sortField === field ? (sortAsc ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />) : null;

  // ── Loading/Error states ──

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0f1419] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 text-teal-400 animate-spin mx-auto mb-3" />
          <p className="text-gray-400 text-sm">Loading NRR forecast...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0f1419] flex items-center justify-center">
        <div className="bg-red-950/30 border border-red-800 rounded-xl p-6 max-w-md text-center">
          <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-red-300 mb-2">NRR Forecast Unavailable</h3>
          <p className="text-sm text-gray-400 mb-4">{error}</p>
          <button onClick={loadData} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm flex items-center gap-2 mx-auto">
            <RefreshCw className="h-4 w-4" /> Retry
          </button>
        </div>
      </div>
    );
  }

  const f = forecast!;

  return (
    <div className="min-h-screen bg-[#0f1419] text-white">
      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">NRR Forecast</h1>
            <p className="text-gray-500 text-sm mt-0.5">
              Net Revenue Retention intelligence &middot; Source: {f.source === 'wizard_b_cached' ? 'Wizard B' : 'Live calculation'}
            </p>
          </div>
          <button onClick={loadData} className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs flex items-center gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
        </div>

        {/* ── Section 1: Summary Cards ── */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className={`rounded-xl border p-4 ${nrrBg(f.current_nrr_pct)}`}>
            <div className="text-xs text-gray-400 mb-1">Current NRR</div>
            <div className={`text-3xl font-bold ${nrrColor(f.current_nrr_pct)}`}>
              {f.current_nrr_pct.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500 mt-1">Without interventions</div>
          </div>
          <div className={`rounded-xl border p-4 ${nrrBg(f.with_interventions_nrr_pct)}`}>
            <div className="text-xs text-gray-400 mb-1">Projected NRR</div>
            <div className={`text-3xl font-bold ${nrrColor(f.with_interventions_nrr_pct)}`}>
              {f.with_interventions_nrr_pct.toFixed(1)}%
            </div>
            <div className="flex items-center gap-1 text-xs mt-1">
              {f.delta_pp > 0 ? <TrendingUp className="h-3 w-3 text-green-400" /> : <TrendingDown className="h-3 w-3 text-red-400" />}
              <span className={f.delta_pp > 0 ? 'text-green-400' : 'text-red-400'}>
                {f.delta_pp > 0 ? '+' : ''}{f.delta_pp.toFixed(1)}pp with interventions
              </span>
            </div>
          </div>
          <div className="rounded-xl border border-gray-700 bg-gray-900/40 p-4">
            <div className="text-xs text-gray-400 mb-1">ARR Protected</div>
            <div className="text-3xl font-bold text-cyan-400">{fmt$(f.arr_protected)}</div>
            <div className="text-xs text-gray-500 mt-1">
              {f.accounts_saved > 0 ? `${f.accounts_saved} accounts saved` : 'From active playbooks'}
            </div>
          </div>
          <div className="rounded-xl border border-gray-700 bg-gray-900/40 p-4">
            <div className="text-xs text-gray-400 mb-1">Renewal Risk</div>
            <div className="text-3xl font-bold text-amber-400">{f.accounts_at_risk}</div>
            <div className="text-xs text-gray-500 mt-1">
              Accounts below health threshold
            </div>
          </div>
        </div>

        {/* ── Section 2: Trajectory Chart ── */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="col-span-2 bg-gray-900/60 border border-gray-800 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-4">NRR Trajectory</h3>
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={trajectoryData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="period" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                <YAxis domain={['dataMin - 3', 'dataMax + 3']} tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
                <Tooltip
                  contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px', fontSize: 12 }}
                  formatter={(v: number) => [`${v.toFixed(1)}%`]}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Area type="monotone" dataKey="baseline" name="Without CS Pulse" stroke="#ef4444" fill="#ef444420" strokeWidth={2} />
                <Area type="monotone" dataKey="withInt" name="With Interventions" stroke="#22c55e" fill="#22c55e20" strokeWidth={2} />
                <ReferenceLine y={100} stroke="#6b7280" strokeDasharray="4 4" label={{ value: '100%', fill: '#6b7280', fontSize: 10 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* ── Section 3: Revenue Waterfall ── */}
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-4">Revenue Waterfall</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={waterfallData} layout="vertical" margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => fmt$(Math.abs(v))} />
                <YAxis dataKey="name" type="category" width={70} tick={{ fill: '#9ca3af', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px', fontSize: 12 }}
                  formatter={(v: number) => [fmt$(Math.abs(v))]}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {waterfallData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            {f.waterfall.roi_x > 0 && (
              <div className="text-center mt-2 text-xs text-gray-400">
                ROI: <span className="text-cyan-400 font-semibold">{f.waterfall.roi_x.toFixed(1)}x</span> return on intervention cost
              </div>
            )}
          </div>
        </div>

        {/* ── Section 5: Scenario Simulator ── */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Scenario Simulator</h3>
          <div className="flex items-center gap-6">
            <div className="flex-1">
              <label className="text-xs text-gray-500 block mb-1">
                Execute playbooks on <span className="text-white font-medium">{scenarioPct}%</span> of at-risk accounts
              </label>
              <input
                type="range" min={0} max={100} step={5} value={scenarioPct}
                onChange={(e) => setScenarioPct(Number(e.target.value))}
                className="w-full h-1.5 bg-gray-700 rounded-full appearance-none cursor-pointer accent-teal-500"
              />
              <div className="flex justify-between text-[10px] text-gray-600 mt-1">
                <span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span>
              </div>
            </div>
            <div className="text-center px-6 border-l border-gray-700">
              <div className="text-xs text-gray-500">Projected NRR</div>
              <div className={`text-2xl font-bold ${nrrColor(scenarioNRR)}`}>{scenarioNRR.toFixed(1)}%</div>
            </div>
            <div className="text-center px-6 border-l border-gray-700">
              <div className="text-xs text-gray-500">ARR Protected</div>
              <div className="text-2xl font-bold text-cyan-400">{fmt$(scenarioARR)}</div>
            </div>
          </div>
        </div>

        {/* ── Section 4: Account Attribution Table ── */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-300">Account Attribution</h3>
            <div className="flex gap-1">
              {(['all', 'at_risk', 'expansion'] as const).map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                    filter === f ? 'bg-teal-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  {f === 'all' ? 'All' : f === 'at_risk' ? 'At Risk' : 'Expansion'}
                </button>
              ))}
            </div>
          </div>

          {sortedInterventions.length === 0 ? (
            <p className="text-xs text-gray-500 text-center py-8">No intervention data available. Run Wizard B to generate forecasts.</p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-700 text-gray-500">
                  <th className="text-left py-2 px-2">Account</th>
                  <th className="text-right py-2 px-2 cursor-pointer select-none" onClick={() => handleSort('health_score')}>
                    <span className="flex items-center justify-end gap-1">Health <SortIcon field="health_score" /></span>
                  </th>
                  <th className="text-right py-2 px-2 cursor-pointer select-none" onClick={() => handleSort('arr')}>
                    <span className="flex items-center justify-end gap-1">ARR <SortIcon field="arr" /></span>
                  </th>
                  <th className="text-right py-2 px-2 cursor-pointer select-none" onClick={() => handleSort('churn_prob_before')}>
                    <span className="flex items-center justify-end gap-1">Churn Prob <SortIcon field="churn_prob_before" /></span>
                  </th>
                  <th className="text-right py-2 px-2 cursor-pointer select-none" onClick={() => handleSort('projected_impact')}>
                    <span className="flex items-center justify-end gap-1">Impact <SortIcon field="projected_impact" /></span>
                  </th>
                  <th className="text-left py-2 px-2">Arc</th>
                  <th className="text-left py-2 px-2">Playbook</th>
                  <th className="text-right py-2 px-2">ROI</th>
                </tr>
              </thead>
              <tbody>
                {sortedInterventions.map((item, i) => (
                  <tr key={item.account_id || i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-2 px-2 font-medium text-gray-200">{item.account_name}</td>
                    <td className={`py-2 px-2 text-right font-medium ${healthColor(item.health_score)}`}>
                      {item.health_score?.toFixed(0)}
                    </td>
                    <td className="py-2 px-2 text-right text-gray-300">{fmt$(item.arr)}</td>
                    <td className="py-2 px-2 text-right text-amber-400">
                      {item.churn_prob_before != null ? `${(item.churn_prob_before * 100).toFixed(0)}%` : '-'}
                    </td>
                    <td className="py-2 px-2 text-right text-cyan-400 font-medium">{fmt$(item.projected_impact)}</td>
                    <td className="py-2 px-2 text-gray-500">{item.arc_type?.replace(/_/g, ' ') || '-'}</td>
                    <td className="py-2 px-2 text-gray-400">{item.playbook_name || item.playbook_id || '-'}</td>
                    <td className="py-2 px-2 text-right text-green-400 font-medium">
                      {item.roi_x != null ? `${item.roi_x.toFixed(1)}x` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Renewal risk overlay */}
        {f.renewal_risk_overlay.length > 0 && (
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4 mt-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">Upcoming Renewals at Risk</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {f.renewal_risk_overlay.slice(0, 8).map((r, i) => (
                <div key={r.account_id || i} className="bg-gray-800/60 rounded-lg p-3">
                  <div className="text-sm font-medium text-gray-200 truncate">{r.account_name}</div>
                  <div className="flex items-center justify-between mt-1 text-xs">
                    <span className="text-gray-500">{fmt$(r.arr)}</span>
                    <span className={healthColor(r.health_score)}>{r.health_score?.toFixed(0)}</span>
                  </div>
                  <div className="text-[10px] text-amber-400 mt-1">
                    {r.days_until != null ? `${r.days_until}d to renewal` : ''}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default NRRDashboard;
