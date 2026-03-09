/**
 * Approval Queue UI — Ring 1 Platform Component
 * ===============================================
 *
 * CSM-facing screen for the human-in-the-loop agent pipeline.
 * Shows pending approval requests (confidence 60-84%) that need human decision.
 *
 * Backend: /api/approvals/* (approval_queue.py)
 * Thresholds:
 *   ≥85% confidence → auto-executed (no human needed)
 *   60-84% confidence → pending (shown here)
 *   <60% confidence → auto-rejected
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
  X,
  DollarSign,
  Zap,
  Activity,
  Inbox,
  History,
  ArrowUpDown,
  ChevronDown,
} from 'lucide-react';
import { useSession } from '../../../contexts/SessionContext';
import { getCustomerIdentifier } from '../../../utils/api';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../shared/Tabs';

// ============================================================
// TYPES
// ============================================================

interface ApprovalItem {
  request_id: number;
  customer_id: number;
  account_id: string;
  agent_id: string;
  action_type: string;
  action_payload: Record<string, any> | null;
  playbook_id: string | null;
  predicted_outcome: string | null;
  confidence: number;
  reasoning: string | null;
  dollar_impact: number | null;
  status: string;
  decided_by: string | null;
  decided_at: string | null;
  decision_notes: string | null;
  created_at: string;
  customer_uuid?: string;
  account_uuid?: string;
}

interface ApprovalStats {
  total: number;
  pending: number;
  auto_executed: number;
  approved: number;
  rejected: number;
  total_dollar_impact: number;
  avg_confidence: number;
}

type SortField = 'confidence' | 'dollar_impact' | 'created_at';
type SortDirection = 'asc' | 'desc';
type HistoryFilter = 'all' | 'approved' | 'rejected' | 'auto_executed' | 'auto_rejected';

// ============================================================
// HELPERS
// ============================================================

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

const formatDollars = (amount: number | null): string => {
  if (amount == null) return 'N/A';
  return currencyFormatter.format(amount);
};

const formatDate = (iso: string | null): string => {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
};

const confidencePercent = (c: number): number => Math.round(c * 100);

const confidenceColor = (c: number): string => {
  const pct = c * 100;
  if (pct >= 80) return 'bg-green-500';
  if (pct >= 70) return 'bg-yellow-500';
  return 'bg-red-500';
};

const confidenceTextColor = (c: number): string => {
  const pct = c * 100;
  if (pct >= 80) return 'text-green-700';
  if (pct >= 70) return 'text-yellow-700';
  return 'text-red-700';
};

const outcomeClasses: Record<string, string> = {
  churn: 'bg-red-100 text-red-800',
  expansion: 'bg-green-100 text-green-800',
  stable: 'bg-blue-100 text-blue-800',
};

const statusClasses: Record<string, string> = {
  pending: 'bg-orange-100 text-orange-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  auto_executed: 'bg-blue-100 text-blue-800',
  auto_rejected: 'bg-gray-100 text-gray-600',
  expired: 'bg-yellow-100 text-yellow-800',
};

const statusLabel = (s: string): string =>
  s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

// ============================================================
// MAIN COMPONENT
// ============================================================

const DCApprovalQueue: React.FC = () => {
  const { session } = useSession();

  // Data
  const [stats, setStats] = useState<ApprovalStats | null>(null);
  const [pending, setPending] = useState<ApprovalItem[]>([]);
  const [history, setHistory] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // UI
  const [subTab, setSubTab] = useState<string>('pending');
  const [sortField, setSortField] = useState<SortField>('confidence');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [historyFilter, setHistoryFilter] = useState<HistoryFilter>('all');

  // Action modal
  const [actionModal, setActionModal] = useState<{
    item: ApprovalItem;
    action: 'approve' | 'reject';
  } | null>(null);
  const [actionNotes, setActionNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  // Toast
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // ---- API Helpers ----

  const headers = useCallback((): Record<string, string> => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' };
    if (session) {
      h['X-Customer-ID'] = getCustomerIdentifier(session);
    }
    return h;
  }, [session]);

  const fetchStats = useCallback(async () => {
    try {
      const r = await fetch('/api/approvals/stats', { credentials: 'include', headers: headers() });
      if (r.ok) {
        const data = await r.json();
        setStats(data.stats ?? data);
      }
    } catch (e) {
      console.error('[ApprovalQueue] Failed to fetch stats:', e);
    }
  }, [headers]);

  const fetchPending = useCallback(async () => {
    try {
      const r = await fetch('/api/approvals/pending', { credentials: 'include', headers: headers() });
      if (r.ok) {
        const data = await r.json();
        setPending(data.pending ?? []);
      }
    } catch (e) {
      console.error('[ApprovalQueue] Failed to fetch pending:', e);
    }
  }, [headers]);

  const fetchHistory = useCallback(async () => {
    try {
      const r = await fetch('/api/approvals/history?limit=100', { credentials: 'include', headers: headers() });
      if (r.ok) {
        const data = await r.json();
        setHistory(data.history ?? []);
      }
    } catch (e) {
      console.error('[ApprovalQueue] Failed to fetch history:', e);
    }
  }, [headers]);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([fetchStats(), fetchPending(), fetchHistory()]);
    } catch (e: any) {
      setError(e.message || 'Failed to load approval data');
    } finally {
      setLoading(false);
    }
  }, [fetchStats, fetchPending, fetchHistory]);

  // Initial load
  useEffect(() => {
    fetchAll();
  }, []);

  // 30-second polling (pending + stats only — history is less urgent)
  useEffect(() => {
    const interval = setInterval(() => {
      fetchPending();
      fetchStats();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchPending, fetchStats]);

  // ---- Approve/Reject ----

  const handleAction = async () => {
    if (!actionModal) return;
    setActionLoading(true);
    try {
      const r = await fetch(
        `/api/approvals/${actionModal.item.request_id}/${actionModal.action}`,
        {
          method: 'POST',
          credentials: 'include',
          headers: headers(),
          body: JSON.stringify({ notes: actionNotes || undefined }),
        }
      );
      if (r.ok) {
        setToast({
          message: `Request #${actionModal.item.request_id} ${actionModal.action === 'approve' ? 'approved' : 'rejected'} successfully`,
          type: 'success',
        });
        setActionModal(null);
        setActionNotes('');
        // Refresh all data
        fetchPending();
        fetchStats();
        fetchHistory();
      } else {
        const data = await r.json().catch(() => ({}));
        setToast({ message: data.error || `Failed to ${actionModal.action}`, type: 'error' });
      }
    } catch (err) {
      setToast({ message: 'Network error — please try again', type: 'error' });
    } finally {
      setActionLoading(false);
    }
  };

  // ---- Sorting ----

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(d => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection(field === 'confidence' ? 'asc' : 'desc');
    }
  };

  const sortedPending = [...pending].sort((a, b) => {
    const dir = sortDirection === 'asc' ? 1 : -1;
    if (sortField === 'confidence') return (a.confidence - b.confidence) * dir;
    if (sortField === 'dollar_impact') return ((a.dollar_impact || 0) - (b.dollar_impact || 0)) * dir;
    return (new Date(a.created_at).getTime() - new Date(b.created_at).getTime()) * dir;
  });

  // ---- History Filter ----

  const filteredHistory = historyFilter === 'all'
    ? history
    : history.filter(h => h.status === historyFilter);

  // ---- Render ----

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
        <span className="ml-3 text-gray-600">Loading approval queue...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-700 mb-4">{error}</p>
        <button onClick={fetchAll} className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div
          className={`p-3 rounded-lg flex items-center justify-between ${
            toast.type === 'success'
              ? 'bg-green-50 border border-green-200 text-green-800'
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}
        >
          <div className="flex items-center">
            {toast.type === 'success' ? (
              <CheckCircle className="w-4 h-4 mr-2" />
            ) : (
              <XCircle className="w-4 h-4 mr-2" />
            )}
            <span className="text-sm font-medium">{toast.message}</span>
          </div>
          <button onClick={() => setToast(null)} className="ml-4">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <ShieldCheck className="w-7 h-7 text-blue-600" />
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Approval Queue</h2>
            <p className="text-sm text-gray-500">
              Review agent recommendations that need human decision (60-84% confidence)
            </p>
          </div>
        </div>
        <button
          onClick={fetchAll}
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center space-x-2"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Clock className="w-4 h-4 text-orange-500" />
              <span className="text-xs text-gray-500 uppercase font-medium">Pending Review</span>
            </div>
            <div className="text-3xl font-bold text-orange-600">{stats.pending}</div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Zap className="w-4 h-4 text-blue-500" />
              <span className="text-xs text-gray-500 uppercase font-medium">Auto-Executed</span>
            </div>
            <div className="text-3xl font-bold text-blue-600">{stats.auto_executed}</div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            <div className="flex items-center space-x-2 mb-2">
              <DollarSign className="w-4 h-4 text-green-500" />
              <span className="text-xs text-gray-500 uppercase font-medium">Total $ Impact</span>
            </div>
            <div className="text-3xl font-bold text-green-600">
              {formatDollars(stats.total_dollar_impact)}
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Activity className="w-4 h-4 text-purple-500" />
              <span className="text-xs text-gray-500 uppercase font-medium">Avg Confidence</span>
            </div>
            <div className={`text-3xl font-bold ${confidenceTextColor(stats.avg_confidence)}`}>
              {stats.avg_confidence > 0 ? `${confidencePercent(stats.avg_confidence)}%` : '—'}
            </div>
          </div>
        </div>
      )}

      {/* Sub-Tabs: Pending / History */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <Tabs value={subTab} onValueChange={setSubTab}>
          <TabsList>
            <TabsTrigger value="pending">
              Pending Queue {pending.length > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-orange-100 text-orange-700 text-xs rounded-full">
                  {pending.length}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="history">
              History {history.length > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">
                  {history.length}
                </span>
              )}
            </TabsTrigger>
          </TabsList>

          {/* ========== PENDING TAB ========== */}
          <TabsContent value="pending" className="p-6">
            {sortedPending.length === 0 ? (
              <div className="text-center py-16">
                <Inbox className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-600 mb-2">No Pending Approvals</h3>
                <p className="text-sm text-gray-400">
                  All agent recommendations have been processed. New items will appear here
                  when the agent identifies actions with 60-84% confidence.
                </p>
              </div>
            ) : (
              <>
                {/* Sort Controls */}
                <div className="flex items-center gap-2 mb-5">
                  <ArrowUpDown className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-500">Sort by:</span>
                  {[
                    { field: 'confidence' as SortField, label: 'Confidence' },
                    { field: 'dollar_impact' as SortField, label: 'Dollar Impact' },
                    { field: 'created_at' as SortField, label: 'Date' },
                  ].map(opt => (
                    <button
                      key={opt.field}
                      onClick={() => toggleSort(opt.field)}
                      className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                        sortField === opt.field
                          ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium'
                          : 'border-gray-200 text-gray-500 hover:border-gray-400'
                      }`}
                    >
                      {opt.label}
                      {sortField === opt.field && (
                        <span className="ml-1">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                      )}
                    </button>
                  ))}
                </div>

                {/* Pending Cards */}
                <div className="space-y-4">
                  {sortedPending.map(item => (
                    <div
                      key={item.request_id}
                      className="border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow bg-white"
                    >
                      {/* Card Header */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center space-x-3">
                          <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded font-medium">
                            {item.agent_id}
                          </span>
                          <span className="text-sm font-semibold text-gray-900">
                            Account {item.account_id}
                          </span>
                          {item.predicted_outcome && (
                            <span
                              className={`text-xs px-2 py-1 rounded-full font-medium ${
                                outcomeClasses[item.predicted_outcome] || 'bg-gray-100 text-gray-600'
                              }`}
                            >
                              {item.predicted_outcome}
                            </span>
                          )}
                        </div>
                        <div className="text-right">
                          <div className={`text-lg font-bold ${confidenceTextColor(item.confidence)}`}>
                            {confidencePercent(item.confidence)}%
                          </div>
                          <div className="text-xs text-gray-400">confidence</div>
                        </div>
                      </div>

                      {/* Confidence Gauge */}
                      <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                        <div
                          className={`h-2 rounded-full ${confidenceColor(item.confidence)}`}
                          style={{ width: `${confidencePercent(item.confidence)}%` }}
                        />
                      </div>

                      {/* Details Grid */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3 text-sm">
                        <div>
                          <p className="text-xs text-gray-400">Dollar Impact</p>
                          <p className="font-semibold text-gray-900">{formatDollars(item.dollar_impact)}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-400">Action Type</p>
                          <p className="font-medium text-gray-700">{statusLabel(item.action_type)}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-400">Playbook</p>
                          <p className="font-medium text-gray-700">{item.playbook_id || '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-400">Created</p>
                          <p className="font-medium text-gray-700">{formatDate(item.created_at)}</p>
                        </div>
                      </div>

                      {/* Reasoning */}
                      {item.reasoning && (
                        <div className="bg-gray-50 rounded-lg p-3 mb-4">
                          <p className="text-xs text-gray-400 mb-1">Agent Reasoning</p>
                          <p className="text-sm text-gray-700 leading-relaxed">{item.reasoning}</p>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex items-center justify-end space-x-3 pt-3 border-t border-gray-100">
                        <button
                          onClick={() => {
                            setActionModal({ item, action: 'reject' });
                            setActionNotes('');
                          }}
                          className="px-4 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors flex items-center"
                        >
                          <XCircle className="w-4 h-4 mr-1.5" />
                          Reject
                        </button>
                        <button
                          onClick={() => {
                            setActionModal({ item, action: 'approve' });
                            setActionNotes('');
                          }}
                          className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors flex items-center"
                        >
                          <CheckCircle className="w-4 h-4 mr-1.5" />
                          Approve
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </TabsContent>

          {/* ========== HISTORY TAB ========== */}
          <TabsContent value="history" className="p-6">
            {/* Filter */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <History className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-500">Filter:</span>
                <select
                  value={historyFilter}
                  onChange={e => setHistoryFilter(e.target.value as HistoryFilter)}
                  className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Decisions</option>
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                  <option value="auto_executed">Auto-Executed</option>
                  <option value="auto_rejected">Auto-Rejected</option>
                </select>
              </div>
              <span className="text-xs text-gray-400">
                {filteredHistory.length} item{filteredHistory.length !== 1 ? 's' : ''}
              </span>
            </div>

            {filteredHistory.length === 0 ? (
              <div className="text-center py-16">
                <History className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-600 mb-2">No History</h3>
                <p className="text-sm text-gray-400">
                  {historyFilter === 'all'
                    ? 'No approval decisions have been made yet.'
                    : `No items with status "${statusLabel(historyFilter)}".`}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Confidence</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">$ Impact</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Decided By</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredHistory.map(item => (
                      <tr key={item.request_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                          {formatDate(item.decided_at || item.created_at)}
                        </td>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 whitespace-nowrap">
                          {item.account_id}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                          {statusLabel(item.action_type)}
                        </td>
                        <td className="px-4 py-3 text-sm whitespace-nowrap">
                          <span className={`font-medium ${confidenceTextColor(item.confidence)}`}>
                            {confidencePercent(item.confidence)}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900 whitespace-nowrap">
                          {formatDollars(item.dollar_impact)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                              statusClasses[item.status] || 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {statusLabel(item.status)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                          {item.decided_by || '—'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">
                          {item.decision_notes || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>

      {/* ========== ACTION MODAL ========== */}
      {actionModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              {actionModal.action === 'approve' ? (
                <>
                  <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                  Approve Request #{actionModal.item.request_id}
                </>
              ) : (
                <>
                  <XCircle className="w-5 h-5 text-red-600 mr-2" />
                  Reject Request #{actionModal.item.request_id}
                </>
              )}
            </h3>

            {/* Summary */}
            <div className="bg-gray-50 rounded-lg p-3 mb-4 text-sm space-y-1">
              <p>
                <span className="text-gray-500">Account:</span>{' '}
                <span className="font-medium">{actionModal.item.account_id}</span>
              </p>
              <p>
                <span className="text-gray-500">Confidence:</span>{' '}
                <span className={`font-medium ${confidenceTextColor(actionModal.item.confidence)}`}>
                  {confidencePercent(actionModal.item.confidence)}%
                </span>
              </p>
              <p>
                <span className="text-gray-500">Dollar Impact:</span>{' '}
                <span className="font-medium">{formatDollars(actionModal.item.dollar_impact)}</span>
              </p>
              {actionModal.item.predicted_outcome && (
                <p>
                  <span className="text-gray-500">Predicted Outcome:</span>{' '}
                  <span className="font-medium capitalize">{actionModal.item.predicted_outcome}</span>
                </p>
              )}
            </div>

            {/* Notes */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Notes (optional)
              </label>
              <textarea
                value={actionNotes}
                onChange={e => setActionNotes(e.target.value)}
                placeholder={
                  actionModal.action === 'approve'
                    ? 'Add any context for the approval...'
                    : 'Reason for rejection...'
                }
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            {/* Buttons */}
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setActionModal(null);
                  setActionNotes('');
                }}
                disabled={actionLoading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleAction}
                disabled={actionLoading}
                className={`px-4 py-2 text-sm font-medium text-white rounded-lg disabled:opacity-50 flex items-center ${
                  actionModal.action === 'approve'
                    ? 'bg-green-600 hover:bg-green-700'
                    : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {actionLoading ? (
                  <RefreshCw className="w-4 h-4 mr-1.5 animate-spin" />
                ) : actionModal.action === 'approve' ? (
                  <CheckCircle className="w-4 h-4 mr-1.5" />
                ) : (
                  <XCircle className="w-4 h-4 mr-1.5" />
                )}
                {actionLoading
                  ? 'Processing...'
                  : actionModal.action === 'approve'
                  ? 'Confirm Approve'
                  : 'Confirm Reject'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DCApprovalQueue;
