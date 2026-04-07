import React, { useEffect, useState, useCallback } from 'react';
import { formatDateTime } from '../../utils/formatDate';
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Filter,
  X,
} from 'lucide-react';
import {
  fetchActivityLog,
  fetchCustomers,
  type ActivityEntry,
  type Customer,
} from '../../api/adminApi';

// ---------------------------------------------------------------------------
// Action type badge — color-coded
// ---------------------------------------------------------------------------

const ACTION_COLORS: Record<string, string> = {
  login: 'bg-blue-100 text-blue-700',
  logout: 'bg-gray-100 text-gray-600',
  entitlement_rejected: 'bg-amber-100 text-amber-700',
  page_view: 'bg-indigo-100 text-indigo-700',
  click: 'bg-indigo-100 text-indigo-600',
  dashboard_switch: 'bg-purple-100 text-purple-700',
  export: 'bg-teal-100 text-teal-700',
  data_upload: 'bg-green-100 text-green-700',
  wizard_run: 'bg-violet-100 text-violet-700',
  config_change: 'bg-orange-100 text-orange-700',
  security: 'bg-red-100 text-red-700',
  playbook_action: 'bg-pink-100 text-pink-700',
};

const ActionBadge: React.FC<{ action: string }> = ({ action }) => {
  const classes = ACTION_COLORS[action] ?? 'bg-gray-100 text-gray-600';
  return (
    <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${classes}`}>
      {action.replace(/_/g, ' ')}
    </span>
  );
};

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  let classes = 'inline-flex px-2 py-0.5 text-xs font-medium rounded-full';
  switch (status.toLowerCase()) {
    case 'success':
      classes += ' bg-green-100 text-green-700';
      break;
    case 'error':
    case 'failed':
      classes += ' bg-red-100 text-red-700';
      break;
    case 'warning':
      classes += ' bg-amber-100 text-amber-700';
      break;
    default:
      classes += ' bg-gray-100 text-gray-600';
  }
  return <span className={classes}>{status}</span>;
};

// ---------------------------------------------------------------------------
// Common action types for the filter dropdown
// ---------------------------------------------------------------------------

const ACTION_TYPE_OPTIONS = [
  { value: '', label: 'All Actions' },
  { value: 'entitlement_rejected', label: 'Entitlement Rejected' },
  { value: 'login', label: 'Login' },
  { value: 'logout', label: 'Logout' },
  { value: 'page_view', label: 'Page View' },
  { value: 'data_upload', label: 'Data Upload' },
  { value: 'wizard_run', label: 'Wizard Run' },
  { value: 'config_change', label: 'Config Change' },
  { value: 'export', label: 'Export' },
  { value: 'playbook_action', label: 'Playbook Action' },
];

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const PAGE_SIZE = 25;

const ActivityLogPage: React.FC = () => {
  const [entries, setEntries] = useState<ActivityEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [showFilters, setShowFilters] = useState(false);
  const [customerFilter, setCustomerFilter] = useState<number | undefined>(undefined);
  const [actionTypeFilter, setActionTypeFilter] = useState('');
  const [searchText, setSearchText] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [customers, setCustomers] = useState<Customer[]>([]);

  // Load customer list once for the filter dropdown
  useEffect(() => {
    fetchCustomers({ page: 1 })
      .then((data) => setCustomers(data.customers ?? []))
      .catch(() => {
        /* ignore -- filter dropdown will just be empty */
      });
  }, []);

  const activeFilterCount = [
    customerFilter !== undefined,
    actionTypeFilter !== '',
    searchText !== '',
    dateFrom !== '',
    dateTo !== '',
  ].filter(Boolean).length;

  const clearFilters = () => {
    setCustomerFilter(undefined);
    setActionTypeFilter('');
    setSearchText('');
    setDateFrom('');
    setDateTo('');
    setPage(1);
  };

  // Fetch activity
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchActivityLog({
        customer_id: customerFilter,
        action_type: actionTypeFilter || undefined,
        search: searchText || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        page,
        limit: PAGE_SIZE,
      });
      setEntries(data.entries ?? []);
      setTotal(data.total ?? 0);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load activity log');
    } finally {
      setLoading(false);
    }
  }, [customerFilter, actionTypeFilter, searchText, dateFrom, dateTo, page]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Activity Log</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {total} total entries{activeFilterCount > 0 ? ` (${activeFilterCount} filter${activeFilterCount > 1 ? 's' : ''} active)` : ''}
          </p>
        </div>
        <div className="flex gap-2 self-start">
          <button
            onClick={() => setShowFilters((prev) => !prev)}
            className={`inline-flex items-center gap-2 px-3 py-2 text-sm border rounded-lg transition-colors ${
              showFilters || activeFilterCount > 0
                ? 'bg-indigo-50 border-indigo-200 text-indigo-700'
                : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            <Filter size={14} />
            Filters
            {activeFilterCount > 0 && (
              <span className="inline-flex items-center justify-center w-4 h-4 text-xs bg-indigo-600 text-white rounded-full">
                {activeFilterCount}
              </span>
            )}
          </button>
          <button
            onClick={load}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Filters panel */}
      {showFilters && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <div className="flex flex-wrap gap-4 items-end">
            {/* Search */}
            <div className="min-w-[220px] flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Search</label>
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={searchText}
                  onChange={(e) => { setSearchText(e.target.value); setPage(1); }}
                  placeholder="Search descriptions..."
                  className="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
            </div>

            {/* Customer filter */}
            <div className="min-w-[180px]">
              <label className="block text-xs font-medium text-gray-600 mb-1">Customer</label>
              <select
                value={customerFilter ?? ''}
                onChange={(e) => {
                  const val = e.target.value;
                  setCustomerFilter(val ? Number(val) : undefined);
                  setPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              >
                <option value="">All Customers</option>
                {customers.map((c) => (
                  <option key={c.customer_id} value={c.customer_id}>
                    {c.customer_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Action type filter */}
            <div className="min-w-[180px]">
              <label className="block text-xs font-medium text-gray-600 mb-1">Action Type</label>
              <select
                value={actionTypeFilter}
                onChange={(e) => { setActionTypeFilter(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              >
                {ACTION_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {/* Date from */}
            <div className="min-w-[150px]">
              <label className="block text-xs font-medium text-gray-600 mb-1">From</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>

            {/* Date to */}
            <div className="min-w-[150px]">
              <label className="block text-xs font-medium text-gray-600 mb-1">To</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>

            {/* Clear */}
            {activeFilterCount > 0 && (
              <button
                onClick={clearFilters}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                <X size={13} /> Clear All
              </button>
            )}
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          <AlertTriangle size={16} />
          {error}
          <button
            onClick={load}
            className="ml-auto inline-flex items-center gap-1 text-red-600 hover:text-red-800 font-medium"
          >
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
            <span className="ml-3 text-sm text-gray-500">Loading activity...</span>
          </div>
        ) : entries.length === 0 ? (
          <div className="text-center py-16 text-sm text-gray-400">No activity entries found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-gray-500 border-b border-gray-100">
                  <th className="px-4 py-3 font-medium">Time</th>
                  <th className="px-4 py-3 font-medium">Customer</th>
                  <th className="px-4 py-3 font-medium">User</th>
                  <th className="px-4 py-3 font-medium">Action</th>
                  <th className="px-4 py-3 font-medium">Description</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {entries.map((entry) => (
                  <tr
                    key={entry.id}
                    className={`hover:bg-gray-50 ${entry.action === 'entitlement_rejected' ? 'bg-amber-50/40' : ''}`}
                  >
                    <td className="px-4 py-2.5 text-gray-500 whitespace-nowrap">
                      {formatDateTime(entry.timestamp)}
                    </td>
                    <td className="px-4 py-2.5 text-gray-700 whitespace-nowrap">
                      {entry.customer_name ?? (entry.customer_id ? `#${entry.customer_id}` : '--')}
                    </td>
                    <td className="px-4 py-2.5 text-gray-600 whitespace-nowrap">
                      {entry.user_name ?? '--'}
                    </td>
                    <td className="px-4 py-2.5 whitespace-nowrap">
                      <ActionBadge action={entry.action} />
                    </td>
                    <td className="px-4 py-2.5 text-gray-600 max-w-sm truncate" title={entry.description}>
                      {entry.description}
                    </td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={entry.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!loading && totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <span className="text-sm text-gray-500">
              Page {page} of {totalPages} ({total} entries)
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft size={14} className="mr-1" /> Prev
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next <ChevronRight size={14} className="ml-1" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ActivityLogPage;
