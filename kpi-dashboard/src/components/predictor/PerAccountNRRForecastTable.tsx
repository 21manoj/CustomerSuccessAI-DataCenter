/**
 * Per-Account NRR Forecast Table.
 *
 * Sortable, color-graded table of every account's Predictor v3 12-month
 * NRR forecast. Drives the "drill-down" half of Layer 1 of the
 * Predictor v3 surface plan — the PredictorV3Tile gives top-5 expansion +
 * top-5 at-risk; this gives the full N-account view with sort.
 *
 * Reads top-expansion + top-at-risk endpoints with limit=100, dedupes,
 * and produces a single combined view.
 */

import React, { useEffect, useState, useMemo } from 'react';
import { ArrowUpDown, TrendingUp, AlertTriangle } from 'lucide-react';
import { apiCall } from '../../utils/api';
import { ForecastWithCI } from '../shared/ForecastWithCI';

interface AccountForecastRow {
  account_id: number;
  account_name: string;
  arr: number;
  // Predictor v3 carries CI bounds + a methodology disclosure on every NRR
  // and expansion forecast — propagate them through so the UI can render
  // them inline (CFO-10 May 17 FDE eval gap).
  expected_nrr: {
    point: number;
    lower_90: number;
    upper_90: number;
    ci_method?: string;
    ci_disclosure?: string;
  };
  term_decomposition: {
    p_churn_at_horizon: number;
    p_survive_at_horizon: number;
    e_contract_pct_given_survive: number;
    e_expand_pct_given_survive: number;
  };
  expansion_outlook?: {
    expected_arr_lift: number;
    p_expansion_event_horizon: number;
    expected_size_pct_given_event: number;
    horizon_to_likely_event_months: number | null;
    ci_lower_arr_lift?: number;
    ci_upper_arr_lift?: number;
    ci_method?: string;
    ci_disclosure?: string;
  };
  calibration_id?: string;
  calibrated_at?: string;
  forecast_arr_loss?: number;
}

type SortField = 'nrr' | 'arr' | 'name' | 'expansion_lift' | 'churn_risk';
type SortDir = 'asc' | 'desc';

interface Props {
  customerId: number;
  horizon?: 'renewal' | '12mo';
}

function formatCompactDollars(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    const m = value / 1_000_000;
    return `$${m % 1 === 0 ? m.toFixed(0) : m.toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    const k = value / 1_000;
    return `$${k % 1 === 0 ? k.toFixed(0) : k.toFixed(1)}K`;
  }
  return `$${Math.round(value)}`;
}

function nrrColor(nrrPoint: number): string {
  if (nrrPoint >= 1.0) return 'text-emerald-400';
  if (nrrPoint >= 0.85) return 'text-amber-400';
  return 'text-red-400';
}

function nrrBarColor(nrrPoint: number): string {
  if (nrrPoint >= 1.0) return 'bg-emerald-400';
  if (nrrPoint >= 0.85) return 'bg-amber-400';
  return 'bg-red-400';
}

export const PerAccountNRRForecastTable: React.FC<Props> = ({ customerId, horizon = '12mo' }) => {
  const [rows, setRows] = useState<AccountForecastRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<SortField>('nrr');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // Pull both top-expansion + top-at-risk with high limit. The endpoints
        // return per-account predictions in different sort orders; we dedupe
        // by account_id to get the complete portfolio.
        const [exp, risk]: [any, any] = await Promise.all([
          apiCall(`/api/v1/predictor/customer/${customerId}/top-expansion-opportunities?horizon=${horizon}&limit=100`),
          apiCall(`/api/v1/predictor/customer/${customerId}/top-at-risk-accounts?horizon=${horizon}&limit=100`),
        ]);
        if (cancelled) return;

        const byId = new Map<number, AccountForecastRow>();
        for (const r of (exp?.results || [])) byId.set(r.account_id, r);
        for (const r of (risk?.results || [])) {
          // Merge — at-risk endpoint may have richer term_decomposition
          const existing = byId.get(r.account_id);
          if (existing) {
            byId.set(r.account_id, { ...existing, ...r, expansion_outlook: existing.expansion_outlook || r.expansion_outlook });
          } else {
            byId.set(r.account_id, r);
          }
        }
        setRows(Array.from(byId.values()));
      } catch (e: any) {
        if (cancelled) return;
        setError(e?.message || 'predictor request failed');
      }
    })();
    return () => { cancelled = true; };
  }, [customerId, horizon]);

  const sorted = useMemo(() => {
    if (!rows) return [];
    const sortKey = (r: AccountForecastRow) => {
      switch (sortField) {
        case 'arr':            return r.arr;
        case 'nrr':            return r.expected_nrr?.point ?? 0;
        case 'name':           return r.account_name?.toLowerCase() || '';
        case 'expansion_lift': return r.expansion_outlook?.expected_arr_lift ?? 0;
        case 'churn_risk':     return r.term_decomposition?.p_churn_at_horizon ?? 0;
        default:               return 0;
      }
    };
    const dir = sortDir === 'asc' ? 1 : -1;
    return [...rows].sort((a, b) => {
      const ka = sortKey(a), kb = sortKey(b);
      if (ka < kb) return -1 * dir;
      if (ka > kb) return 1 * dir;
      return 0;
    });
  }, [rows, sortField, sortDir]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir(field === 'name' ? 'asc' : 'desc');
    }
  };

  if (error) {
    return (
      <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 text-xs text-gray-500">
        Per-account forecast unavailable: {error}
      </div>
    );
  }

  if (!rows) {
    return (
      <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 text-xs text-gray-500">
        Loading per-account forecasts…
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 text-xs text-gray-500">
        No per-account predictions available. Wizard D may not have run yet for this tenant.
      </div>
    );
  }

  const displayed = showAll ? sorted : sorted.slice(0, 10);
  const totalArr = rows.reduce((s, r) => s + r.arr, 0);
  const activeAccounts = rows.filter(r => r.arr > 0).length;
  const arrWeightedNrr = totalArr > 0
    ? (rows.reduce((s, r) => s + (r.arr * (r.expected_nrr?.point ?? 0)), 0) / totalArr) * 100
    : 0;

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden mb-6">
      <div className="px-5 py-4 border-b border-gray-700/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-semibold text-white uppercase tracking-wide">
            Per-Account NRR Forecast
          </h3>
          <span className="text-[10px] text-gray-500 ml-2">
            Predictor v3 · {horizon} horizon · {rows.length} accounts ({activeAccounts} active) · portfolio ARR-weighted: {arrWeightedNrr.toFixed(1)}%
          </span>
        </div>
        <button
          onClick={() => setShowAll(s => !s)}
          className="text-[10px] px-3 py-1 rounded border border-gray-700 hover:border-purple-400 hover:text-purple-300 transition-colors text-gray-400"
        >
          {showAll ? `Show top 10` : `Show all ${rows.length}`}
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700/50 bg-[#131826]">
              <th className="text-left px-3 py-2.5 text-[9px] font-semibold text-gray-500 uppercase tracking-wider">
                <button onClick={() => handleSort('name')} className="hover:text-purple-300 inline-flex items-center gap-1">
                  Account <ArrowUpDown className="w-2.5 h-2.5" />
                </button>
              </th>
              <th className="text-right px-3 py-2.5 text-[9px] font-semibold text-gray-500 uppercase tracking-wider">
                <button onClick={() => handleSort('arr')} className="hover:text-purple-300 inline-flex items-center gap-1">
                  ARR <ArrowUpDown className="w-2.5 h-2.5" />
                </button>
              </th>
              <th className="text-right px-3 py-2.5 text-[9px] font-semibold text-gray-500 uppercase tracking-wider">
                <button onClick={() => handleSort('nrr')} className="hover:text-purple-300 inline-flex items-center gap-1">
                  NRR Forecast (12mo) <ArrowUpDown className="w-2.5 h-2.5" />
                </button>
              </th>
              <th className="text-right px-3 py-2.5 text-[9px] font-semibold text-gray-500 uppercase tracking-wider">
                <button onClick={() => handleSort('churn_risk')} className="hover:text-purple-300 inline-flex items-center gap-1">
                  P(churn) <ArrowUpDown className="w-2.5 h-2.5" />
                </button>
              </th>
              <th className="text-right px-3 py-2.5 text-[9px] font-semibold text-gray-500 uppercase tracking-wider">
                <button onClick={() => handleSort('expansion_lift')} className="hover:text-purple-300 inline-flex items-center gap-1">
                  Expansion ARR Lift <ArrowUpDown className="w-2.5 h-2.5" />
                </button>
              </th>
              <th className="text-left px-3 py-2.5 text-[9px] font-semibold text-gray-500 uppercase tracking-wider">Method</th>
            </tr>
          </thead>
          <tbody>
            {displayed.map((r) => {
              const nrrPoint = r.expected_nrr?.point ?? 0;
              const churnPoint = r.term_decomposition?.p_churn_at_horizon ?? 0;
              const expLift = r.expansion_outlook?.expected_arr_lift ?? 0;
              const isChurned = r.arr === 0;
              return (
                <tr key={r.account_id} className="border-b border-gray-800/50 hover:bg-[#131826] transition-colors">
                  <td className="px-3 py-2 text-gray-200 font-medium">
                    {r.account_name}
                    {isChurned && <AlertTriangle className="inline-block w-3 h-3 ml-1 text-red-400" />}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-300 font-mono text-[11px]">
                    {formatCompactDollars(r.arr)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {/* CFO-10 (May 17 FDE eval): NRR forecast renders with 90% CI bounds
                        + (i) disclosure tooltip inline. ForecastWithCI handles the
                        warning styling when ci_method='placeholder_uncalibrated'.
                        The micro-bar visual stays right of the CI for at-a-glance
                        color grading. */}
                    <div className="inline-flex items-center gap-2 justify-end">
                      <ForecastWithCI
                        point={nrrPoint}
                        lower={r.expected_nrr?.lower_90}
                        upper={r.expected_nrr?.upper_90}
                        format="percent"
                        ciMethod={r.expected_nrr?.ci_method}
                        ciDisclosure={r.expected_nrr?.ci_disclosure}
                        pointClassName={`font-semibold ${nrrColor(nrrPoint)}`}
                      />
                      <div className="inline-block w-16 h-1.5 bg-gray-800 rounded">
                        <div
                          className={`h-full rounded ${nrrBarColor(nrrPoint)}`}
                          style={{ width: `${Math.min(100, Math.max(0, nrrPoint * 100))}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right text-gray-400 font-mono text-[11px]">
                    {(churnPoint * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-[11px]">
                    {expLift > 0 ? (
                      // CFO-10: expansion ARR lift renders with CI bounds + (i)
                      // disclosure. ForecastWithCI degrades to point-only when
                      // ci_lower/upper are absent (older API versions).
                      <ForecastWithCI
                        point={expLift}
                        lower={r.expansion_outlook?.ci_lower_arr_lift}
                        upper={r.expansion_outlook?.ci_upper_arr_lift}
                        format="currency"
                        ciMethod={r.expansion_outlook?.ci_method}
                        ciDisclosure={r.expansion_outlook?.ci_disclosure}
                        pointClassName="text-emerald-400"
                      />
                    ) : (
                      <span className="text-gray-600">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-left">
                    {isChurned ? (
                      <code className="text-[9px] text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded">churned</code>
                    ) : (
                      <code className="text-[9px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                        calibrated
                      </code>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="px-5 py-3 bg-[#0d1119] border-t border-gray-800/50 text-[10px] text-gray-500">
        Sorted by {sortField} ({sortDir}). Click any column to re-sort.
        Predictor v3 GLMM · 4 sub-models (hazard, contraction, expansion_event, expansion_size).
        Hover the per-row method tag in the future for calibration drill-down.
      </div>
    </div>
  );
};

export default PerAccountNRRForecastTable;
