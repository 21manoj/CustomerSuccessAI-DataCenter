/**
 * AnalyticsTab — ROI analysis, Power-of-1, revenue intelligence, CSM actions
 *
 * 4 collapsible sections using existing backend endpoints.
 */

import React, { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  TrendingUp,
  Calculator,
  ShieldAlert,
  ClipboardList,
  AlertCircle,
  Lock,
} from 'lucide-react';

import { POWER_OF_1_METRICS } from '../types';
import { analyticsApi, formatDollars } from '../api';

interface AnalyticsTabProps {
  customerId: string;
  entitlements: Record<string, boolean>;
}

// Collapsible section wrapper
const Section: React.FC<{
  title: string;
  icon: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}> = ({ title, icon, defaultOpen = false, children }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-6 py-4 flex items-center gap-3 text-left hover:bg-gray-50 transition-colors"
      >
        {icon}
        <h3 className="font-semibold text-gray-800 flex-1">{title}</h3>
        {open ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
      </button>
      {open && <div className="px-6 pb-6 border-t border-gray-100 pt-4">{children}</div>}
    </div>
  );
};

const AnalyticsTab: React.FC<AnalyticsTabProps> = ({ customerId, entitlements }) => {
  const hasAdvanced = entitlements['test_runner_advanced'] ?? false;

  if (!hasAdvanced) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <Lock className="w-12 h-12 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-500 font-medium">Analytics requires Professional tier</p>
        <p className="text-sm text-gray-400 mt-1">Upgrade to unlock ROI analysis, Power-of-1, and revenue intelligence</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PortfolioROISection customerId={customerId} />
      <PowerOf1Section customerId={customerId} />
      <RevenueAtRiskSection customerId={customerId} />
      <DailyActionsSection customerId={customerId} />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Section 1: Portfolio ROI Story
// ---------------------------------------------------------------------------

const PortfolioROISection: React.FC<{ customerId: string }> = ({ customerId }) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await analyticsApi.getPortfolioROI(customerId);
      setData(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Section title="Portfolio ROI Story" icon={<TrendingUp className="w-5 h-5 text-blue-600" />} defaultOpen>
      {!data && !loading && !error && (
        <button
          onClick={fetch_}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium transition-colors"
        >
          Load ROI Story
        </button>
      )}

      {loading && (
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading...
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-red-600 text-sm">
          <AlertCircle className="w-4 h-4" />
          {error}
          <button onClick={fetch_} className="text-blue-600 hover:underline ml-2">Retry</button>
        </div>
      )}

      {data && (
        <div className="space-y-4">
          {/* Historical ROI */}
          {data.historical && (
            <div className="bg-blue-50 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-blue-800 mb-2">Historical Performance</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                {data.historical.roi_pct != null && (
                  <div>
                    <span className="text-gray-600">ROI</span>
                    <p className="text-lg font-bold text-blue-700">{data.historical.roi_pct.toFixed(1)}%</p>
                  </div>
                )}
                {data.historical.dollar_impact != null && (
                  <div>
                    <span className="text-gray-600">Dollar Impact</span>
                    <p className="text-lg font-bold text-green-700">{formatDollars(data.historical.dollar_impact)}</p>
                  </div>
                )}
                {data.historical.top_metric && (
                  <div>
                    <span className="text-gray-600">Top Metric</span>
                    <p className="text-lg font-bold text-gray-800">{data.historical.top_metric}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Forward Projection */}
          {data.forward && (
            <div className="bg-green-50 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-green-800 mb-2">Forward Projection</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                {data.forward.projected_roi_pct != null && (
                  <div>
                    <span className="text-gray-600">Projected ROI</span>
                    <p className="text-lg font-bold text-green-700">{data.forward.projected_roi_pct.toFixed(1)}%</p>
                  </div>
                )}
                {data.forward.projected_dollar_impact != null && (
                  <div>
                    <span className="text-gray-600">Projected Impact</span>
                    <p className="text-lg font-bold text-green-700">{formatDollars(data.forward.projected_dollar_impact)}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Raw JSON fallback */}
          {!data.historical && !data.forward && (
            <pre className="bg-gray-50 rounded-lg p-4 text-xs overflow-auto max-h-64">
              {JSON.stringify(data, null, 2)}
            </pre>
          )}

          <button
            onClick={fetch_}
            className="text-sm text-blue-600 hover:underline"
          >
            Refresh
          </button>
        </div>
      )}
    </Section>
  );
};

// ---------------------------------------------------------------------------
// Section 2: Power-of-1 Calculator
// ---------------------------------------------------------------------------

const PowerOf1Section: React.FC<{ customerId: string }> = ({ customerId }) => {
  const [metricId, setMetricId] = useState('NRR');
  const [improvementPct, setImprovementPct] = useState(1.0);
  const [accountArr, setAccountArr] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await analyticsApi.getPowerOf1(
        customerId,
        metricId,
        improvementPct,
        accountArr ? parseFloat(accountArr) : undefined,
      );
      setResult(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Section title="Power-of-1 Calculator" icon={<Calculator className="w-5 h-5 text-purple-600" />}>
      <div className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Metric</label>
            <select
              value={metricId}
              onChange={e => setMetricId(e.target.value)}
              className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-purple-500"
            >
              {POWER_OF_1_METRICS.map(m => (
                <option key={m.id} value={m.id}>{m.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Improvement %</label>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={0.5}
                max={10}
                step={0.5}
                value={improvementPct}
                onChange={e => setImprovementPct(parseFloat(e.target.value))}
                className="flex-1 h-1.5 bg-gray-200 rounded-lg cursor-pointer accent-purple-600"
              />
              <span className="text-sm font-mono text-purple-700 w-10 text-right">{improvementPct}%</span>
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Account ARR <span className="text-gray-400">(optional)</span>
            </label>
            <input
              type="number"
              value={accountArr}
              onChange={e => setAccountArr(e.target.value)}
              placeholder="Portfolio total"
              className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={calculate}
              disabled={loading}
              className="px-4 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Calculate
            </button>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-red-600 text-sm">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {result && (
          <div className="bg-purple-50 rounded-lg p-4">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <span className="text-xs text-gray-500">Annual Impact</span>
                <p className="text-xl font-bold text-purple-700">{formatDollars(result.annual_impact)}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">Monthly Impact</span>
                <p className="text-xl font-bold text-purple-600">{formatDollars(result.monthly_impact)}</p>
              </div>
              <div>
                <span className="text-xs text-gray-500">ARR Basis</span>
                <p className="text-xl font-bold text-gray-700">{formatDollars(result.arr_basis)}</p>
              </div>
            </div>
            <p className="text-sm text-gray-600 mt-3">{result.description}</p>
          </div>
        )}
      </div>
    </Section>
  );
};

// ---------------------------------------------------------------------------
// Section 3: Revenue at Risk
// ---------------------------------------------------------------------------

const RevenueAtRiskSection: React.FC<{ customerId: string }> = ({ customerId }) => {
  const [accountId, setAccountId] = useState('');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = async () => {
    if (!accountId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await analyticsApi.getRevenueAtRisk(customerId, parseInt(accountId, 10));
      setData(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Section title="Revenue at Risk" icon={<ShieldAlert className="w-5 h-5 text-red-600" />}>
      <div className="space-y-4">
        <div className="flex items-end gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Account ID</label>
            <input
              type="number"
              value={accountId}
              onChange={e => setAccountId(e.target.value)}
              placeholder="e.g. 300001"
              className="w-40 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-red-500"
            />
          </div>
          <button
            onClick={fetch_}
            disabled={loading || !accountId}
            className="px-4 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Fetch
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-red-600 text-sm">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {data && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {['protected', 'at_risk', 'expansion', 'lost'].map(key => {
              const val = data[key] ?? data.revenue?.[key] ?? 0;
              const colors: Record<string, string> = {
                protected: 'bg-green-50 text-green-700',
                at_risk: 'bg-red-50 text-red-700',
                expansion: 'bg-blue-50 text-blue-700',
                lost: 'bg-gray-50 text-gray-700',
              };
              return (
                <div key={key} className={`rounded-lg p-4 ${colors[key]}`}>
                  <span className="text-xs font-medium uppercase">{key.replace('_', ' ')}</span>
                  <p className="text-xl font-bold mt-1">{formatDollars(val)}</p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Section>
  );
};

// ---------------------------------------------------------------------------
// Section 4: CSM Daily Actions
// ---------------------------------------------------------------------------

const DailyActionsSection: React.FC<{ customerId: string }> = ({ customerId }) => {
  const [actions, setActions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const fetch_ = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await analyticsApi.getDailyActions(customerId);
      setActions(result.actions || result.data || []);
      setLoaded(true);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Section title="CSM Daily Actions" icon={<ClipboardList className="w-5 h-5 text-indigo-600" />}>
      {!loaded && !loading && !error && (
        <button
          onClick={fetch_}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium transition-colors"
        >
          Load Daily Actions
        </button>
      )}

      {loading && (
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading...
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-red-600 text-sm">
          <AlertCircle className="w-4 h-4" />
          {error}
          <button onClick={fetch_} className="text-blue-600 hover:underline ml-2">Retry</button>
        </div>
      )}

      {loaded && actions.length === 0 && (
        <p className="text-gray-500 text-sm">No daily actions found. Run scenarios to generate data first.</p>
      )}

      {actions.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-3 py-2 text-left font-medium text-gray-600">#</th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">Account</th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">Action</th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">Urgency</th>
                <th className="px-3 py-2 text-right font-medium text-gray-600">Effort (hrs)</th>
                <th className="px-3 py-2 text-right font-medium text-gray-600">ROI Impact</th>
              </tr>
            </thead>
            <tbody>
              {actions.slice(0, 10).map((action: any, i: number) => (
                <tr key={i} className="border-b border-gray-100 last:border-0">
                  <td className="px-3 py-2 text-gray-500">{i + 1}</td>
                  <td className="px-3 py-2 text-gray-800 font-medium">{action.account_name || action.account || '-'}</td>
                  <td className="px-3 py-2 text-gray-700">{action.action || action.description || '-'}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                      action.urgency === 'high' || action.urgency === 'critical'
                        ? 'bg-red-100 text-red-700'
                        : action.urgency === 'medium'
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-gray-100 text-gray-600'
                    }`}>
                      {action.urgency || '-'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right text-gray-600">{action.effort_hours ?? '-'}</td>
                  <td className="px-3 py-2 text-right font-medium text-green-700">
                    {action.roi_impact ? formatDollars(action.roi_impact) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button onClick={fetch_} className="text-sm text-indigo-600 hover:underline mt-2">
            Refresh
          </button>
        </div>
      )}
    </Section>
  );
};

export default AnalyticsTab;
