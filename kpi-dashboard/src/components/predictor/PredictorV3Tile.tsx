/**
 * NRR Predictor v3 — CFO/CRO dashboard tile.
 *
 * Per A6 in PLAN_nrr_predictor_v3.md, this tile leads CFO/CRO dashboards
 * with the offensive (expansion) view, with the defensive (at-risk) view
 * as a companion. UI lead varies by saas_profile:
 *   - saas_enterprise → account-level expansion list (whale shape; per-account
 *     stories of $500K-$1M expansion are CFO-grade)
 *   - saas_smb → portfolio expansion forecast (sum of expected_arr_lift across
 *     all accounts with CI; per-account drill-down secondary)
 *
 * Two-flag rollback:
 *   - FEATURE_PREDICTOR_V3_UI controls whether this tile renders at all
 *     (consumed at the dashboard level, not here)
 *   - FEATURE_PREDICTOR_API can be killed at runtime; the API returns 503
 *     with {fallback:'wizard_b_legacy'}; this tile catches and renders a
 *     fallback notice (parent dashboard renders Wizard B legacy NRR)
 */

import React, { useEffect, useState } from 'react';
import { TrendingUp, AlertTriangle, ShieldOff } from 'lucide-react';
import { apiCall } from '../../utils/api';
import { ForecastWithCI } from '../shared/ForecastWithCI';

// Predictor v3 API enriches every forecast with CI bounds and a disclosure
// string. We pipe these through verbatim — the <ForecastWithCI> component
// renders the warning styling for `placeholder_uncalibrated` and the
// platform's own "do not threshold on the CI bounds" wording.
interface PredictorRankRow {
  account_id: number;
  account_name: string;
  arr: number;
  ranking_score: number;
  expected_nrr: {
    point: number;
    lower_90: number;
    upper_90: number;
    ci_method?: string;
    ci_disclosure?: string;
  };
  term_decomposition: { p_churn_at_horizon: number };
  expansion_outlook: {
    expected_arr_lift: number;
    p_expansion_event_horizon: number;
    expected_size_pct_given_event: number;
    horizon_to_likely_event_months: number | null;
    // Expansion CI fields — top-expansion endpoint returns lower/upper on the
    // expected_arr_lift point estimate alongside ci_method + ci_disclosure.
    ci_lower_arr_lift?: number;
    ci_upper_arr_lift?: number;
    ci_method?: string;
    ci_disclosure?: string;
  };
}

interface Props {
  customerId: number;
  saasProfile: 'saas_enterprise' | 'saas_smb';
  horizon?: 'renewal' | '12mo';
  limit?: number;
}

export const PredictorV3Tile: React.FC<Props> = ({
  customerId,
  saasProfile,
  horizon = '12mo',
  limit = 5,
}) => {
  const [expansion, setExpansion] = useState<PredictorRankRow[] | null>(null);
  const [atRisk, setAtRisk] = useState<PredictorRankRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [killed, setKilled] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [exp, risk]: [any, any] = await Promise.all([
          apiCall(`/api/v1/predictor/customer/${customerId}/top-expansion-opportunities?horizon=${horizon}&limit=${limit}`),
          apiCall(`/api/v1/predictor/customer/${customerId}/top-at-risk-accounts?horizon=${horizon}&limit=${limit}`),
        ]);
        if (cancelled) return;

        // Kill-switch detection: API returns 503 with body {error:'predictor_disabled', fallback:'wizard_b_legacy'}
        if (exp?.error === 'predictor_disabled' || risk?.error === 'predictor_disabled') {
          setKilled(true);
          return;
        }

        setExpansion(exp?.results || []);
        setAtRisk(risk?.results || []);
      } catch (e: any) {
        if (cancelled) return;
        setError(e?.message || 'predictor request failed');
      }
    })();
    return () => { cancelled = true; };
  }, [customerId, saasProfile, horizon, limit]);

  if (killed) {
    return (
      <div className="rounded-lg border border-amber-700 bg-amber-950/40 p-3 text-amber-200 text-xs flex items-center gap-2">
        <ShieldOff className="w-4 h-4" />
        <span>
          Predictor v3 is currently disabled (API kill-switch). Dashboard is
          rendering Wizard B legacy NRR. <span className="text-amber-400">Fallback active</span>
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-red-200 text-xs">
        Predictor v3: {error}
      </div>
    );
  }

  if (!expansion || !atRisk) {
    return <div className="text-gray-500 text-xs animate-pulse">Loading predictor v3 forecast…</div>;
  }

  const fmtUsd = (v: number) =>
    v >= 1_000_000 ? `$${(v / 1_000_000).toFixed(2)}M` :
    v >= 1_000 ? `$${(v / 1_000).toFixed(0)}K` :
    `$${v.toFixed(0)}`;
  const fmtPct = (v: number, digits = 1) => `${(v * 100).toFixed(digits)}%`;

  // A6 lead by profile
  const leadingExpansion = saasProfile === 'saas_smb';

  // Portfolio aggregate for saas_smb tile lead
  const totalLift = expansion.reduce((s, r) => s + r.expansion_outlook.expected_arr_lift, 0);

  return (
    <div className="space-y-4">
      {/* ── A6 lead tile ──────────────────────────────────────── */}
      {leadingExpansion ? (
        <div className="rounded-lg border border-emerald-700/40 bg-emerald-950/20 p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold text-emerald-100">
              Forward {horizon === '12mo' ? '12-month' : 'renewal-horizon'} expansion
            </h3>
          </div>
          <div className="text-3xl font-bold text-emerald-200">{fmtUsd(totalLift)}</div>
          <div className="text-xs text-emerald-400/80">
            across top {expansion.length} expansion opportunities · {expansion.length > 0 && `${fmtPct(expansion[0].expansion_outlook.p_expansion_event_horizon)} avg event probability`}
          </div>
        </div>
      ) : (
        // saas_enterprise — leads with per-account expansion list, no aggregate tile
        <div className="text-xs uppercase tracking-wider text-gray-400">Top expansion opportunities</div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        {/* ── Expansion column ─────────────────────────────────── */}
        <div className="rounded-lg border border-emerald-800/30 bg-gray-900/50 p-3">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <h4 className="text-xs uppercase tracking-wider text-emerald-300/80">Top expansion opportunities</h4>
          </div>
          <div className="space-y-1">
            {expansion.length === 0 && <div className="text-gray-500 text-xs">No expansion opportunities</div>}
            {expansion.map(row => (
              <div key={`exp-${row.account_id}`} className="flex justify-between items-center text-sm py-1 border-b border-gray-800/30 last:border-0">
                <div>
                  <div className="text-gray-100">{row.account_name}</div>
                  <div className="text-xs text-gray-500">
                    {fmtPct(row.expansion_outlook.p_expansion_event_horizon)} P(event)
                    {row.expansion_outlook.horizon_to_likely_event_months !== null &&
                      ` · ~${row.expansion_outlook.horizon_to_likely_event_months}mo`}
                  </div>
                </div>
                <div className="text-right">
                  {/* CRO-3 (May 17 FDE eval): expansion ARR lift now renders with
                      lower/upper CI bounds + (i) disclosure tooltip. The leading
                      "+" sign stays as a visual cue for expansion direction. */}
                  <div className="text-emerald-300 font-semibold flex items-center justify-end gap-1">
                    <span>+</span>
                    <ForecastWithCI
                      point={row.expansion_outlook.expected_arr_lift}
                      lower={row.expansion_outlook.ci_lower_arr_lift}
                      upper={row.expansion_outlook.ci_upper_arr_lift}
                      format="currency"
                      ciMethod={row.expansion_outlook.ci_method}
                      ciDisclosure={row.expansion_outlook.ci_disclosure}
                    />
                  </div>
                  {/* CRO-8 / CFO-10: NRR forecast now renders with CI. */}
                  <div className="text-xs text-gray-500 flex items-center justify-end gap-1">
                    <span>NRR</span>
                    <ForecastWithCI
                      point={row.expected_nrr.point}
                      lower={row.expected_nrr.lower_90}
                      upper={row.expected_nrr.upper_90}
                      format="percent"
                      ciMethod={row.expected_nrr.ci_method}
                      ciDisclosure={row.expected_nrr.ci_disclosure}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── At-risk column ──────────────────────────────────── */}
        <div className="rounded-lg border border-red-800/30 bg-gray-900/50 p-3">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <h4 className="text-xs uppercase tracking-wider text-red-300/80">Top at-risk accounts</h4>
          </div>
          <div className="space-y-1">
            {atRisk.length === 0 && <div className="text-gray-500 text-xs">No at-risk accounts</div>}
            {atRisk.map(row => (
              <div key={`risk-${row.account_id}`} className="flex justify-between items-center text-sm py-1 border-b border-gray-800/30 last:border-0">
                <div>
                  <div className="text-gray-100">{row.account_name}</div>
                  <div className="text-xs text-gray-500">
                    {fmtPct(row.term_decomposition.p_churn_at_horizon)} churn risk
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-red-300 font-semibold">−{fmtUsd(row.ranking_score)}</div>
                  {/* CRO-8 / CFO-10: NRR forecast with CI on at-risk rows. The
                      Spica Labs verification check (98.8% (93.8% – 103.8%))
                      lives in this exact tile slot. */}
                  <div className="text-xs text-gray-500 flex items-center justify-end gap-1">
                    <span>NRR</span>
                    <ForecastWithCI
                      point={row.expected_nrr.point}
                      lower={row.expected_nrr.lower_90}
                      upper={row.expected_nrr.upper_90}
                      format="percent"
                      ciMethod={row.expected_nrr.ci_method}
                      ciDisclosure={row.expected_nrr.ci_disclosure}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="text-[10px] text-gray-600 italic">
        NRR Predictor v3 ({saasProfile === 'saas_enterprise' ? 'enterprise' : 'SMB'} profile, {horizon} horizon).
        Forward-looking expected NRR with 90% CI bounds shown inline. Replaces Wizard B's realized-NRR ledger when active.
        Hover (i) on any forecast for CI methodology + calibration notes.
      </div>
    </div>
  );
};

export default PredictorV3Tile;
