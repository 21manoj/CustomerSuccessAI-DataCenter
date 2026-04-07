/**
 * PlaybookStartModal — Confirmation modal for starting a playbook execution.
 *
 * Shows playbook details + account context. On confirm, POSTs to
 * /api/dc2s/playbooks/executions to create a PlaybookExecution record.
 */

import React, { useState } from 'react';
import { Play, X, Clock, Users, AlertTriangle } from 'lucide-react';
import { classifyColor } from '../../utils/healthThresholds';

interface Playbook {
  playbook_id: string;
  playbook_name?: string;
  name?: string;
  description?: string;
  estimated_hours?: number;
  estimated_duration_display?: string;
  urgency?: string;
}

interface Account {
  account_id: number;
  account_name: string;
  health_score: number;
  arr?: number;
}

interface PlaybookStartModalProps {
  playbook: Playbook;
  account: Account;
  customerId: string | number;
  onClose: () => void;
  onStarted?: (executionId: string) => void;
}

function formatCompact(v: number): string {
  if (v >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `$${Math.round(v / 1e3)}K`;
  return `$${v}`;
}

const PlaybookStartModal: React.FC<PlaybookStartModalProps> = ({
  playbook,
  account,
  customerId,
  onClose,
  onStarted,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const pbName = playbook.playbook_name || playbook.name || playbook.playbook_id;

  const handleStart = async () => {
    setLoading(true);
    setError('');
    try {
      const resp = await fetch('/api/dc2s/playbooks/executions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Customer-ID': String(customerId),
        },
        credentials: 'include',
        body: JSON.stringify({
          playbookId: playbook.playbook_id,
          context: {
            accountId: account.account_id,
            accountName: account.account_name,
            customerId: Number(customerId),
            metadata: { triggered_from: 'csm_dashboard', priority: playbook.urgency || 'medium' },
          },
        }),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.error || `Failed (${resp.status})`);
      }
      const data = await resp.json();
      onStarted?.(data.execution_id || data.id || '');
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start playbook');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Play className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-semibold text-gray-900">Start Playbook</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">
          {/* Playbook info */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900">{pbName}</h3>
            {playbook.description && (
              <p className="text-xs text-gray-500 mt-1">{playbook.description}</p>
            )}
            <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
              {playbook.estimated_hours && (
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" /> {playbook.estimated_hours}h estimated
                </span>
              )}
              {playbook.estimated_duration_display && (
                <span>{playbook.estimated_duration_display}</span>
              )}
              <span className="font-mono text-gray-300">{playbook.playbook_id}</span>
            </div>
          </div>

          {/* Account info */}
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-900">{account.account_name}</span>
              <span className="text-sm font-semibold" style={{ color: classifyColor(account.health_score) }}>
                {account.health_score}
              </span>
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
              {account.arr && <span>{formatCompact(account.arr)} ARR</span>}
              <span>Health: {account.health_score}/100</span>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 px-3 py-2 rounded">
              <AlertTriangle className="w-3.5 h-3.5" /> {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-gray-100 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded-lg transition"
          >
            Cancel
          </button>
          <button
            onClick={handleStart}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition disabled:opacity-50"
          >
            {loading ? (
              <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
            ) : (
              <Play className="w-3.5 h-3.5" />
            )}
            Start Execution
          </button>
        </div>
      </div>
    </div>
  );
};

export default PlaybookStartModal;
