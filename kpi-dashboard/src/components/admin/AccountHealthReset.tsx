/**
 * Account Health Reset — Admin escalation tool
 * ==============================================
 * Allows super admin to recalculate health scores for a specific account
 * or all accounts of a customer. Shows dry-run preview before applying.
 *
 * API: POST /api/admin/accounts/<id>/reset-health
 *      POST /api/admin/customers/<id>/reset-all-health
 */

import React, { useState } from 'react';
import { getApiBaseUrl } from '../../utils/api';

interface ResetResult {
  account_id: number;
  account_name: string;
  current_health: number | null;
  new_health: number | null;
  new_status: string | null;
  delta: number | null;
  months_recalculated: number;
  message: string;
}

const AccountHealthReset: React.FC<{ customerId: number }> = ({ customerId }) => {
  const [accountId, setAccountId] = useState('');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<ResetResult | null>(null);
  const [result, setResult] = useState<ResetResult | null>(null);
  const [error, setError] = useState('');
  const [mode, setMode] = useState<'single' | 'all'>('single');

  const runDryRun = async () => {
    if (mode === 'single' && !accountId.trim()) {
      setError('Enter an account ID');
      return;
    }
    setLoading(true);
    setError('');
    setPreview(null);
    setResult(null);

    try {
      const url = mode === 'single'
        ? `${getApiBaseUrl()}/api/admin/accounts/${accountId}/reset-health`
        : `${getApiBaseUrl()}/api/admin/customers/${customerId}/reset-all-health`;

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ dry_run: true, reason }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `${res.status}`);
      }
      const data = await res.json();
      setPreview(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const applyReset = async () => {
    if (!reason.trim()) {
      setError('Reason is required before applying');
      return;
    }
    setLoading(true);
    setError('');

    try {
      const url = mode === 'single'
        ? `${getApiBaseUrl()}/api/admin/accounts/${accountId}/reset-health`
        : `${getApiBaseUrl()}/api/admin/customers/${customerId}/reset-all-health`;

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ dry_run: false, reason }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `${res.status}`);
      }
      const data = await res.json();
      setResult(data);
      setPreview(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const statusColor = (status: string | null) => {
    if (!status) return 'text-gray-400';
    if (status === 'healthy') return 'text-green-400';
    if (status === 'at_risk') return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-4">Health Score Reset</h3>
      <p className="text-sm text-gray-400 mb-6">
        Recalculate health scores from existing KPI data. Use when scores are stale, corrupted, or after weight changes.
      </p>

      {/* Mode selector */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => { setMode('single'); setPreview(null); setResult(null); }}
          className={`px-3 py-1.5 rounded-lg text-sm ${mode === 'single' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}`}
        >
          Single Account
        </button>
        <button
          onClick={() => { setMode('all'); setPreview(null); setResult(null); }}
          className={`px-3 py-1.5 rounded-lg text-sm ${mode === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'}`}
        >
          All Accounts
        </button>
      </div>

      {/* Inputs */}
      <div className="space-y-3 mb-4">
        {mode === 'single' && (
          <div>
            <label className="block text-xs text-gray-500 mb-1">Account ID</label>
            <input
              type="number"
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              placeholder="e.g. 1234"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600"
            />
          </div>
        )}
        <div>
          <label className="block text-xs text-gray-500 mb-1">Reason (required to apply)</label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Wizard C applied wrong weights, recalculating"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={runDryRun}
          disabled={loading}
          className="px-4 py-2 bg-gray-700 text-white rounded-lg text-sm hover:bg-gray-600 disabled:opacity-50"
        >
          {loading ? 'Calculating...' : 'Preview (Dry Run)'}
        </button>
        {preview && (
          <button
            onClick={applyReset}
            disabled={loading || !reason.trim()}
            className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm hover:bg-amber-500 disabled:opacity-50"
          >
            Apply Reset
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 px-3 py-2 bg-red-900/30 border border-red-700/50 rounded-lg text-red-300 text-sm">{error}</div>
      )}

      {/* Preview */}
      {preview && (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4 mb-4">
          <h4 className="text-sm font-medium text-yellow-400 mb-3">Dry Run Preview</h4>
          {mode === 'single' ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Account</span>
                <span className="text-white">{preview.account_name} (#{preview.account_id})</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Current Health</span>
                <span className="text-white">{preview.current_health ?? 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">New Health</span>
                <span className={statusColor(preview.new_status)}>{preview.new_health ?? 'N/A'} ({preview.new_status})</span>
              </div>
              {preview.delta !== null && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Delta</span>
                  <span className={preview.delta >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {preview.delta >= 0 ? '+' : ''}{preview.delta}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-400">Months</span>
                <span className="text-white">{preview.months_recalculated}</span>
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-300">
              {(preview as any).accounts_processed} accounts would be recalculated
            </div>
          )}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="bg-green-900/20 border border-green-700/50 rounded-xl p-4">
          <h4 className="text-sm font-medium text-green-400 mb-2">Reset Applied</h4>
          <p className="text-sm text-gray-300">{result.message || 'Health scores recalculated successfully'}</p>
          {mode === 'single' && result.new_health !== null && (
            <p className="text-sm text-gray-400 mt-1">
              New health: <span className={statusColor(result.new_status)}>{result.new_health} ({result.new_status})</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default AccountHealthReset;
