/**
 * PlaybookCompletionForm — Modal form for closing a playbook execution.
 *
 * Collects outcome (resolved/escalated/timeout), CSM hours actual,
 * revenue protected, and notes. POSTs to /api/dc2s/playbooks/executions/<id>/complete.
 */

import React, { useState } from 'react';
import { CheckCircle, X, AlertTriangle } from 'lucide-react';

interface PlaybookCompletionFormProps {
  executionId: string;
  accountName: string;
  playbookId: string;
  customerId: string;
  onClose: () => void;
  onCompleted?: () => void;
}

const OUTCOMES = [
  { value: 'resolved', label: 'Resolved', color: 'text-green-600' },
  { value: 'escalated', label: 'Escalated', color: 'text-orange-600' },
  { value: 'timeout', label: 'Timeout', color: 'text-red-600' },
  { value: 'manual_close', label: 'Manual Close', color: 'text-gray-600' },
];

const PlaybookCompletionForm: React.FC<PlaybookCompletionFormProps> = ({
  executionId,
  accountName,
  playbookId,
  customerId,
  onClose,
  onCompleted,
}) => {
  const [outcome, setOutcome] = useState('resolved');
  const [notes, setNotes] = useState('');
  const [csmHours, setCsmHours] = useState('');
  const [revenueProtected, setRevenueProtected] = useState('');
  const [revenueExpanded, setRevenueExpanded] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    try {
      const body: Record<string, any> = {
        status: 'completed',
        outcome,
        outcome_notes: notes,
      };
      if (csmHours) body.csm_hours_actual = parseFloat(csmHours);
      if (revenueProtected) body.revenue_protected = parseFloat(revenueProtected);
      if (revenueExpanded) body.revenue_expanded = parseFloat(revenueExpanded);

      const resp = await fetch(`/api/dc2s/playbooks/executions/${executionId}/complete`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Customer-ID': customerId,
        },
        credentials: 'include',
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.error || `Failed (${resp.status})`);
      }
      onCompleted?.();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
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
            <CheckCircle className="w-5 h-5 text-green-600" />
            <h2 className="text-base font-semibold text-gray-900">Close Playbook</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">
          <div className="text-sm text-gray-600">
            <span className="font-medium text-gray-900">{accountName}</span>
            <span className="text-gray-400 ml-2 font-mono text-xs">{playbookId}</span>
          </div>

          {/* Outcome */}
          <div>
            <label className="text-xs font-medium text-gray-700 block mb-1.5">Outcome</label>
            <div className="flex gap-2 flex-wrap">
              {OUTCOMES.map((o) => (
                <button
                  key={o.value}
                  onClick={() => setOutcome(o.value)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition ${
                    outcome === o.value
                      ? 'bg-blue-50 border-blue-300 text-blue-700'
                      : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="text-xs font-medium text-gray-700 block mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="What happened? Key results..."
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none h-16 focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-[10px] font-medium text-gray-500 block mb-1">CSM Hours</label>
              <input
                type="number"
                value={csmHours}
                onChange={(e) => setCsmHours(e.target.value)}
                placeholder="0"
                className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
            </div>
            <div>
              <label className="text-[10px] font-medium text-gray-500 block mb-1">$ Protected</label>
              <input
                type="number"
                value={revenueProtected}
                onChange={(e) => setRevenueProtected(e.target.value)}
                placeholder="0"
                className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
            </div>
            <div>
              <label className="text-[10px] font-medium text-gray-500 block mb-1">$ Expanded</label>
              <input
                type="number"
                value={revenueExpanded}
                onChange={(e) => setRevenueExpanded(e.target.value)}
                placeholder="0"
                className="w-full border border-gray-200 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
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
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded-lg transition">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition disabled:opacity-50"
          >
            {loading ? <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" /> : <CheckCircle className="w-3.5 h-3.5" />}
            Close Playbook
          </button>
        </div>
      </div>
    </div>
  );
};

export default PlaybookCompletionForm;
