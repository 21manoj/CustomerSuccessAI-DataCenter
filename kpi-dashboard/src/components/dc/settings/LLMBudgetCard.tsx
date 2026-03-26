/**
 * LLMBudgetCard — AI Budget Management
 * ======================================
 * Shared component for both self-service (read-only) and super admin (editable) contexts.
 *
 * API contracts:
 *   GET  /api/llm-usage/budget-config?customer_id=N   -> current budget limits
 *   PUT  /api/llm-usage/budget-config                 <- update budget limits
 *   GET  /api/llm-usage/budget-status?customer_id=N   -> usage gauges
 *   GET  /api/llm-usage/recent?customer_id=N&limit=10 -> recent usage log
 */

import React, { useState, useEffect } from 'react';
import { RefreshCw, CheckCircle, AlertCircle, Save, Zap } from 'lucide-react';

// ============================================================
// TYPES
// ============================================================

interface BudgetConfig {
  daily_calls: number;
  daily_usd: number;
  monthly_usd: number;
  max_proactive_per_run: number;
  is_custom: boolean;
}

interface BudgetStatus {
  daily: {
    calls_used: number;
    calls_limit: number;
    calls_pct: number;
    spend_usd: number;
    spend_limit_usd: number;
    spend_pct: number;
  };
  monthly: {
    calls_used: number;
    spend_usd: number;
    spend_limit_usd: number;
    spend_pct: number;
  };
  circuit_breaker: {
    daily_calls_status: string;
    daily_spend_status: string;
    monthly_spend_status: string;
  };
}

interface UsageEntry {
  module: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  success: boolean;
  error_message: string | null;
  timestamp: string;
}

interface LLMBudgetCardProps {
  /** Super-admin context: pass target customer ID. Self-service: omit (uses session). */
  customerId?: number;
  /** Force read-only mode (self-service default). */
  readOnly?: boolean;
}

// ============================================================
// HELPERS
// ============================================================

const DEFAULT_CONFIG: BudgetConfig = {
  daily_calls: 200,
  daily_usd: 10.0,
  monthly_usd: 200.0,
  max_proactive_per_run: 50,
  is_custom: false,
};

/** Color class based on usage percentage: green < 60%, yellow 60-80%, red > 80%. */
const pctColor = (pct: number): string => {
  if (pct >= 80) return 'text-red-500';
  if (pct >= 60) return 'text-amber-500';
  return 'text-green-500';
};

const pctBgColor = (pct: number): string => {
  if (pct >= 80) return 'bg-red-500';
  if (pct >= 60) return 'bg-amber-500';
  return 'bg-green-500';
};

const pctBgLight = (pct: number): string => {
  if (pct >= 80) return 'bg-red-100';
  if (pct >= 60) return 'bg-amber-100';
  return 'bg-green-100';
};

const statusBadge = (status: string): { label: string; cls: string } => {
  if (status === 'blocked') return { label: 'Blocked', cls: 'bg-red-100 text-red-700' };
  if (status === 'warning') return { label: 'Warning', cls: 'bg-amber-100 text-amber-700' };
  return { label: 'OK', cls: 'bg-green-100 text-green-700' };
};

// ============================================================
// USAGE GAUGE
// ============================================================

const UsageGauge: React.FC<{
  label: string;
  used: number;
  limit: number;
  pct: number;
  format?: 'number' | 'usd';
}> = ({ label, used, limit, pct, format = 'number' }) => {
  const displayUsed = format === 'usd' ? `$${used.toFixed(2)}` : used.toLocaleString();
  const displayLimit = format === 'usd' ? `$${limit.toFixed(2)}` : limit.toLocaleString();
  const clampedPct = Math.min(pct, 100);

  return (
    <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className={`text-sm font-semibold ${pctColor(pct)}`}>{pct.toFixed(1)}%</span>
      </div>
      <div className={`w-full h-2.5 rounded-full ${pctBgLight(pct)}`}>
        <div
          className={`h-2.5 rounded-full transition-all duration-500 ${pctBgColor(pct)}`}
          style={{ width: `${clampedPct}%` }}
        />
      </div>
      <p className="text-xs text-gray-500 mt-1.5">
        {displayUsed} / {displayLimit}
      </p>
    </div>
  );
};

// ============================================================
// MAIN COMPONENT
// ============================================================

const LLMBudgetCard: React.FC<LLMBudgetCardProps> = ({ customerId, readOnly }) => {
  const isEditable = customerId != null && !readOnly;

  const apiUrl = (path: string) =>
    customerId ? `${path}?customer_id=${customerId}` : path;

  const [config, setConfig] = useState<BudgetConfig>(DEFAULT_CONFIG);
  const [localConfig, setLocalConfig] = useState<BudgetConfig>(DEFAULT_CONFIG);
  const [status, setStatus] = useState<BudgetStatus | null>(null);
  const [entries, setEntries] = useState<UsageEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const showResult = (ok: boolean, msg: string) => {
    setResult({ ok, msg });
    setTimeout(() => setResult(null), 3000);
  };

  // ── Fetch all data on mount ──
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [configRes, statusRes, recentRes] = await Promise.all([
          fetch(apiUrl('/api/llm-usage/budget-config'), { credentials: 'include' }),
          fetch(apiUrl('/api/llm-usage/budget-status'), { credentials: 'include' }),
          fetch(apiUrl('/api/llm-usage/recent') + (customerId ? '&limit=10' : '?limit=10'), { credentials: 'include' }),
        ]);

        if (configRes.ok) {
          const data = await configRes.json();
          const loaded: BudgetConfig = {
            daily_calls: data.daily_calls ?? DEFAULT_CONFIG.daily_calls,
            daily_usd: data.daily_usd ?? DEFAULT_CONFIG.daily_usd,
            monthly_usd: data.monthly_usd ?? DEFAULT_CONFIG.monthly_usd,
            max_proactive_per_run: data.max_proactive_per_run ?? DEFAULT_CONFIG.max_proactive_per_run,
            is_custom: data.is_custom ?? false,
          };
          setConfig(loaded);
          setLocalConfig(loaded);
        }

        if (statusRes.ok) {
          const data = await statusRes.json();
          setStatus(data);
        }

        if (recentRes.ok) {
          const data = await recentRes.json();
          setEntries(data.entries || []);
        }
      } catch {
        // Use defaults silently
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [customerId]);

  // ── Save config ──
  const handleSave = async () => {
    if (!isEditable) return;
    setSaving(true);
    try {
      const res = await fetch('/api/llm-usage/budget-config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          customer_id: customerId,
          daily_calls: localConfig.daily_calls,
          daily_usd: localConfig.daily_usd,
          monthly_usd: localConfig.monthly_usd,
          max_proactive_per_run: localConfig.max_proactive_per_run,
        }),
      });
      if (res.ok) {
        setConfig({ ...localConfig, is_custom: true });
        showResult(true, 'Budget config saved');
      } else {
        const data = await res.json().catch(() => ({}));
        showResult(false, data.error || 'Failed to save');
      }
    } catch {
      showResult(false, 'Network error');
    } finally {
      setSaving(false);
    }
  };

  const hasChanges =
    localConfig.daily_calls !== config.daily_calls ||
    localConfig.daily_usd !== config.daily_usd ||
    localConfig.monthly_usd !== config.monthly_usd ||
    localConfig.max_proactive_per_run !== config.max_proactive_per_run;

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center space-x-2 text-gray-400 text-sm">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span>Loading AI budget data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center space-x-2 mb-1">
        <Zap className="h-5 w-5 text-purple-600" />
        <h3 className="text-base font-semibold text-gray-900">AI Budget & Usage</h3>
        {!config.is_custom && (
          <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">Using defaults</span>
        )}
      </div>
      <p className="text-sm text-gray-500 mb-5">
        Monitor LLM API usage and {isEditable ? 'configure' : 'view'} budget limits.
      </p>

      {/* ── Usage Gauges ── */}
      {status && (
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Current Usage</h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <UsageGauge
              label="Daily Calls"
              used={status.daily.calls_used}
              limit={status.daily.calls_limit}
              pct={status.daily.calls_pct}
            />
            <UsageGauge
              label="Daily Spend"
              used={status.daily.spend_usd}
              limit={status.daily.spend_limit_usd}
              pct={status.daily.spend_pct}
              format="usd"
            />
            <UsageGauge
              label="Monthly Spend"
              used={status.monthly.spend_usd}
              limit={status.monthly.spend_limit_usd}
              pct={status.monthly.spend_pct}
              format="usd"
            />
          </div>

          {/* Circuit breaker status badges */}
          {status.circuit_breaker && (
            <div className="flex items-center space-x-2 mt-3">
              <span className="text-xs text-gray-500">Circuit breaker:</span>
              {(['daily_calls_status', 'daily_spend_status', 'monthly_spend_status'] as const).map((key) => {
                const s = statusBadge(status.circuit_breaker[key]);
                const labels: Record<string, string> = {
                  daily_calls_status: 'Calls',
                  daily_spend_status: 'Daily $',
                  monthly_spend_status: 'Monthly $',
                };
                return (
                  <span key={key} className={`text-xs px-2 py-0.5 rounded-full font-medium ${s.cls}`}>
                    {labels[key]}: {s.label}
                  </span>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Budget Configuration ── */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3">
          Budget Limits {!isEditable && <span className="text-gray-400 font-normal">(read-only)</span>}
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Daily Call Limit</label>
            <input
              type="number"
              min={1}
              value={localConfig.daily_calls}
              onChange={e => setLocalConfig(prev => ({ ...prev, daily_calls: Number(e.target.value) }))}
              disabled={!isEditable}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none disabled:bg-gray-50 disabled:text-gray-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Daily USD Limit</label>
            <div className="relative">
              <span className="absolute left-3 top-2 text-gray-400 text-sm">$</span>
              <input
                type="number"
                min={0}
                step={0.5}
                value={localConfig.daily_usd}
                onChange={e => setLocalConfig(prev => ({ ...prev, daily_usd: Number(e.target.value) }))}
                disabled={!isEditable}
                className="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none disabled:bg-gray-50 disabled:text-gray-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Monthly USD Limit</label>
            <div className="relative">
              <span className="absolute left-3 top-2 text-gray-400 text-sm">$</span>
              <input
                type="number"
                min={0}
                step={1}
                value={localConfig.monthly_usd}
                onChange={e => setLocalConfig(prev => ({ ...prev, monthly_usd: Number(e.target.value) }))}
                disabled={!isEditable}
                className="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none disabled:bg-gray-50 disabled:text-gray-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Max Proactive Calls / Run</label>
            <input
              type="number"
              min={1}
              value={localConfig.max_proactive_per_run}
              onChange={e => setLocalConfig(prev => ({ ...prev, max_proactive_per_run: Number(e.target.value) }))}
              disabled={!isEditable}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none disabled:bg-gray-50 disabled:text-gray-500"
            />
          </div>
        </div>

        {/* Save button (super admin only) */}
        {isEditable && (
          <div className="mt-4 flex items-center space-x-3">
            <button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className="flex items-center space-x-1.5 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60 transition-colors"
            >
              {saving
                ? <RefreshCw className="h-4 w-4 animate-spin" />
                : <Save className="h-4 w-4" />}
              <span>{saving ? 'Saving...' : 'Save Budget Config'}</span>
            </button>
            {result && (
              <span className={`flex items-center space-x-1 text-sm font-medium ${result.ok ? 'text-green-600' : 'text-red-600'}`}>
                {result.ok
                  ? <CheckCircle className="h-4 w-4" />
                  : <AlertCircle className="h-4 w-4" />}
                <span>{result.msg}</span>
              </span>
            )}
          </div>
        )}
      </div>

      {/* ── Recent Usage Table ── */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">Recent LLM Calls</h4>
        {entries.length === 0 ? (
          <p className="text-sm text-gray-400 italic">No LLM usage recorded yet.</p>
        ) : (
          <div className="overflow-x-auto border border-gray-200 rounded-lg">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Module</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Model</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Tokens</th>
                  <th className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase">Cost</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {entries.map((entry, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-3 py-2 text-gray-800 font-medium whitespace-nowrap">{entry.module}</td>
                    <td className="px-3 py-2 text-gray-600 whitespace-nowrap">
                      <span className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">{entry.model}</span>
                    </td>
                    <td className="px-3 py-2 text-right text-gray-600 whitespace-nowrap">
                      {(entry.tokens_in + entry.tokens_out).toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-right text-gray-600 whitespace-nowrap">
                      ${entry.cost_usd.toFixed(4)}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {entry.success ? (
                        <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">OK</span>
                      ) : (
                        <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full" title={entry.error_message || ''}>
                          Failed
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-gray-500 text-xs whitespace-nowrap">
                      {entry.timestamp
                        ? new Date(entry.timestamp).toLocaleString(undefined, {
                            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                          })
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default LLMBudgetCard;
