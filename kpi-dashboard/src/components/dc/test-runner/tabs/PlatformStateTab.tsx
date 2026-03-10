/**
 * PlatformStateTab — Live view of customer/account state in the platform
 *
 * Shows: summary cards, account table with health/pillars/CG nodes.
 * Fetches from GET /api/test-runner/platform-state?customer_id=X
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Database,
  RefreshCw,
  Loader2,
  AlertCircle,
  Server,
  Heart,
  DollarSign,
  GitBranch,
} from 'lucide-react';

import type { PlatformState } from '../types';
import { platformApi, formatDollars } from '../api';
import { classify } from '../../../../utils/healthThresholds';

interface PlatformStateTabProps {
  customerId: string;
  refreshTrigger?: number;
}

const PlatformStateTab: React.FC<PlatformStateTabProps> = ({ customerId, refreshTrigger }) => {
  const [state, setState] = useState<PlatformState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchState = useCallback(async () => {
    const cid = customerId?.trim();
    if (!cid) {
      setState(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await platformApi.getState(cid);
      setState(data);
    } catch (e: any) {
      setError(e.message || 'Failed to fetch platform state');
      setState(null);
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    fetchState();
  }, [fetchState, refreshTrigger]);

  // Helper: health color based on thresholds
  const healthColor = (score: number | null) => {
    if (score === null) return 'text-gray-400';
    const status = classify(score);
    return status === 'critical' ? 'text-red-600' : status === 'at_risk' ? 'text-amber-600' : 'text-green-600';
  };

  const healthBg = (score: number | null) => {
    if (score === null) return 'bg-gray-100';
    const status = classify(score);
    return status === 'critical' ? 'bg-red-50' : status === 'at_risk' ? 'bg-amber-50' : 'bg-green-50';
  };

  if (!customerId?.trim()) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <Database className="w-12 h-12 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-500">Enter a Customer ID above to view platform state</p>
      </div>
    );
  }

  if (loading && !state) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
        <p className="text-gray-500">Loading platform state...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <AlertCircle className="w-12 h-12 text-red-300 mx-auto mb-3" />
        <p className="text-red-600 font-medium">{error}</p>
        <p className="text-sm text-gray-500 mt-2">Run Scenario 1 (Customer Onboarding) to create data for this customer</p>
        <button
          onClick={fetchState}
          className="mt-4 px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!state || state.accounts.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <Database className="w-12 h-12 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-500 font-medium">No accounts found</p>
        <p className="text-sm text-gray-400 mt-1">Run Scenario 1 (Customer Onboarding) to create accounts and load data</p>
      </div>
    );
  }

  const { summary } = state;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-gray-500 text-xs font-medium uppercase tracking-wide mb-1">
            <Server className="w-3.5 h-3.5" />
            Accounts
          </div>
          <p className="text-2xl font-bold text-gray-900">{summary.total_accounts}</p>
        </div>

        <div className={`rounded-lg shadow-sm border border-gray-200 p-4 ${healthBg(summary.avg_health)}`}>
          <div className="flex items-center gap-2 text-gray-500 text-xs font-medium uppercase tracking-wide mb-1">
            <Heart className="w-3.5 h-3.5" />
            Avg Health
          </div>
          <p className={`text-2xl font-bold ${healthColor(summary.avg_health)}`}>
            {summary.avg_health !== null ? summary.avg_health.toFixed(1) : 'N/A'}
          </p>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-gray-500 text-xs font-medium uppercase tracking-wide mb-1">
            <DollarSign className="w-3.5 h-3.5" />
            Total ARR
          </div>
          <p className="text-2xl font-bold text-gray-900">{formatDollars(summary.total_arr)}</p>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-1">Status Distribution</div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-green-600 font-semibold">{summary.healthy} <span className="text-xs font-normal">Healthy</span></span>
            <span className="text-amber-600 font-semibold">{summary.at_risk} <span className="text-xs font-normal">At-Risk</span></span>
            <span className="text-red-600 font-semibold">{summary.critical} <span className="text-xs font-normal">Critical</span></span>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-gray-500 text-xs font-medium uppercase tracking-wide mb-1">
            <GitBranch className="w-3.5 h-3.5" />
            Context Graph
          </div>
          <p className="text-2xl font-bold text-gray-900">{summary.total_cg_nodes}</p>
          <p className="text-xs text-gray-400">
            {summary.context_graph_enabled ? 'Enabled' : 'Not enabled'}
          </p>
        </div>
      </div>

      {/* Account Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">
            Accounts — {state.customer_name} (ID: {state.customer_id})
          </h3>
          <button
            onClick={fetchState}
            disabled={loading}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            Refresh
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-4 py-2 text-left font-medium text-gray-600">Account</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Health</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Status</th>
                <th className="px-4 py-2 text-right font-medium text-gray-600">ARR</th>
                <th className="px-4 py-2 text-center font-medium text-gray-600">P1</th>
                <th className="px-4 py-2 text-center font-medium text-gray-600">P2</th>
                <th className="px-4 py-2 text-center font-medium text-gray-600">P3</th>
                <th className="px-4 py-2 text-center font-medium text-gray-600">P4</th>
                <th className="px-4 py-2 text-center font-medium text-gray-600">P5</th>
                <th className="px-4 py-2 text-center font-medium text-gray-600">CG Nodes</th>
                <th className="px-4 py-2 text-left font-medium text-gray-600">Latest</th>
              </tr>
            </thead>
            <tbody>
              {state.accounts.map(acct => (
                <tr key={acct.account_id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <div className="font-medium text-gray-800">{acct.account_name}</div>
                    <div className="text-xs text-gray-400">ID: {acct.account_id}</div>
                  </td>
                  <td className={`px-4 py-2 font-semibold ${healthColor(acct.health_score)}`}>
                    {acct.health_score !== null ? acct.health_score.toFixed(1) : '-'}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                      acct.status === 'critical' ? 'bg-red-100 text-red-700' :
                      acct.status === 'at_risk' ? 'bg-amber-100 text-amber-700' :
                      acct.status === 'healthy' ? 'bg-green-100 text-green-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {acct.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right font-mono text-gray-700">
                    {formatDollars(acct.arr)}
                  </td>
                  {['P1', 'P2', 'P3', 'P4', 'P5'].map(pillar => {
                    const score = acct.pillar_scores?.[pillar] ?? null;
                    return (
                      <td key={pillar} className={`px-4 py-2 text-center text-xs font-mono ${healthColor(score)}`}>
                        {score !== null ? (typeof score === 'number' ? score.toFixed(0) : score) : '-'}
                      </td>
                    );
                  })}
                  <td className="px-4 py-2 text-center text-gray-600">
                    {acct.context_graph_nodes > 0 ? (
                      <span className="inline-flex items-center gap-1">
                        <GitBranch className="w-3 h-3 text-purple-500" />
                        {acct.context_graph_nodes}
                      </span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-xs text-gray-500">
                    {acct.latest_kpi_date
                      ? new Date(acct.latest_kpi_date).toLocaleDateString()
                      : '-'
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default PlatformStateTab;
