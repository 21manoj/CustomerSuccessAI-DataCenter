/**
 * System Events and Log Management Tab
 * =====================================
 * 
 * Similar to SaaS GovernanceSettings but for DC2_S
 * - Activity Logs
 * - System Events
 * - Log Management
 */

import React, { useState, useEffect } from 'react';
import { useSession } from '../../../contexts/SessionContext';
import { getCustomerIdentifier } from '../../../utils/api';
import { Activity, MessageSquare, Shield, Filter, RefreshCw } from 'lucide-react';

interface ActivityLog {
  log_id: number;
  timestamp: string;
  action_type: string;
  action_category: string;
  resource_type: string;
  resource_id: number;
  user_id: number;
  user_name: string;
  status: 'success' | 'failure' | 'partial';
  details: string;
}

interface ActivitySummary {
  total_activities: number;
  period_days: number;
  by_status: { [status: string]: number };
  by_action_category: { [category: string]: number };
  top_users: Array<{ user_id: number; user_name: string; count: number }>;
}

export const SystemEventsAndLogManagement: React.FC = () => {
  const { session } = useSession();
  const [activeTab, setActiveTab] = useState<'logs' | 'rag' | 'dq'>('logs');
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [summary, setSummary] = useState<ActivitySummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [filters, setFilters] = useState({
    action_type: '',
    action_category: '',
    resource_type: '',
    user_id: '',
    status: '',
    days: 30,
  });
  
  // RAG Query
  const [ragQuery, setRagQuery] = useState('');
  const [ragResponse, setRagResponse] = useState<string | null>(null);
  const [ragLoading, setRagLoading] = useState(false);
  const [ragError, setRagError] = useState<string | null>(null);
  const [ragDays, setRagDays] = useState(90);

  // Data Quality
  const [dqLoading, setDqLoading] = useState(false);
  const [dqError, setDqError] = useState<string | null>(null);
  const [dqReport, setDqReport] = useState<any>(null);

  useEffect(() => {
    if (activeTab === 'logs') {
      fetchActivityLogs();
      fetchSummary();
    } else if (activeTab === 'dq') {
      fetchDataQuality();
    }
  }, [activeTab, filters]);

  const fetchActivityLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const queryParams = new URLSearchParams({
        days: filters.days.toString(),
        ...(filters.action_type && { action_type: filters.action_type }),
        ...(filters.action_category && { action_category: filters.action_category }),
        ...(filters.resource_type && { resource_type: filters.resource_type }),
        ...(filters.user_id && { user_id: filters.user_id }),
        ...(filters.status && { status: filters.status }),
      });

      const response = await fetch(`/api/activity-logs?${queryParams}`, {
        credentials: 'include',
        headers: {
          'X-Customer-ID': getCustomerIdentifier(session)
        }
      });

      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
      } else {
        setError('Failed to load activity logs');
      }
    } catch (err) {
      setError('Error fetching activity logs');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await fetch(`/api/activity-logs/summary?days=${filters.days}`, {
        credentials: 'include',
        headers: {
          'X-Customer-ID': getCustomerIdentifier(session)
        }
      });

      if (response.ok) {
        const data = await response.json();
        setSummary(data.summary || null);
      }
    } catch (err) {
      console.error('Error fetching summary:', err);
    }
  };

  const fetchDataQuality = async () => {
    setDqLoading(true);
    setDqError(null);
    try {
      const response = await fetch('/api/data-quality/report', {
        credentials: 'include',
        headers: {
          'X-Customer-ID': getCustomerIdentifier(session)
        }
      });

      if (response.ok) {
        const data = await response.json();
        setDqReport(data.report || null);
      } else {
        setDqError('Failed to load data quality report');
      }
    } catch (err) {
      setDqError('Error fetching data quality report');
      console.error('Error:', err);
    } finally {
      setDqLoading(false);
    }
  };

  const executeRAGQuery = async () => {
    if (!ragQuery.trim()) return;
    
    setRagLoading(true);
    setRagError(null);
    setRagResponse(null);

    try {
      const response = await fetch('/api/governance-rag/query', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-Customer-ID': getCustomerIdentifier(session)
        },
        body: JSON.stringify({
          query: ragQuery,
          days: ragDays
        })
      });

      if (response.ok) {
        const data = await response.json();
        setRagResponse(data.answer || data.response || 'No response');
      } else {
        const errorData = await response.json().catch(() => ({}));
        setRagError(errorData.error || 'Failed to execute RAG query');
      }
    } catch (err) {
      setRagError('Error executing RAG query');
      console.error('Error:', err);
    } finally {
      setRagLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center">
          <Shield className="h-5 w-5 mr-2 text-blue-600" />
          System Events and Log Management
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Monitor system activity, query governance data, and review data quality
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab('logs')}
          className={`px-4 py-2 font-medium text-sm flex items-center ${
            activeTab === 'logs'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <Activity className="h-4 w-4 mr-2" />
          Activity Logs
        </button>
        <button
          onClick={() => setActiveTab('rag')}
          className={`px-4 py-2 font-medium text-sm flex items-center ${
            activeTab === 'rag'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <MessageSquare className="h-4 w-4 mr-2" />
          Governance RAG Query
        </button>
        <button
          onClick={() => setActiveTab('dq')}
          className={`px-4 py-2 font-medium text-sm flex items-center ${
            activeTab === 'dq'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <Shield className="h-4 w-4 mr-2" />
          Data Quality
        </button>
      </div>

      {/* Activity Logs Tab */}
      {activeTab === 'logs' && (
        <div>
          {/* Summary */}
          {summary && summary.total_activities != null && (
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-3">
                Activity Summary (Last {summary.period_days} days)
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-gray-600">Total Activities</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.total_activities}</div>
                </div>
                <div>
                  <div className="text-gray-600">By Status</div>
                  <div className="text-xs text-gray-700">
                    {summary.by_status && typeof summary.by_status === 'object' &&
                      Object.entries(summary.by_status).map(([status, count]) => (
                        <div key={status}>{status}: {String(count)}</div>
                      ))}
                  </div>
                </div>
                <div>
                  <div className="text-gray-600">Top Categories</div>
                  <div className="text-xs text-gray-700">
                    {summary.by_action_category && typeof summary.by_action_category === 'object' &&
                      Object.entries(summary.by_action_category)
                        .sort((a, b) => Number(b[1]) - Number(a[1]))
                        .slice(0, 3)
                        .map(([cat, count]) => (
                          <div key={cat}>{cat}: {String(count)}</div>
                        ))}
                  </div>
                </div>
                <div>
                  <div className="text-gray-600">Top Users</div>
                  <div className="text-xs text-gray-700">
                    {Array.isArray(summary.top_users) &&
                      summary.top_users.slice(0, 3).map((user) => (
                        <div key={user.user_id}>{user.user_name}: {user.count}</div>
                      ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Filters */}
          <div className="mb-4 p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center mb-3">
              <Filter className="h-4 w-4 mr-2 text-gray-600" />
              <h4 className="font-semibold text-gray-900">Filters</h4>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Action Type</label>
                <input
                  type="text"
                  value={filters.action_type}
                  onChange={(e) => setFilters({ ...filters, action_type: e.target.value })}
                  placeholder="e.g., kpi_edit"
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Category</label>
                <input
                  type="text"
                  value={filters.action_category}
                  onChange={(e) => setFilters({ ...filters, action_category: e.target.value })}
                  placeholder="e.g., data_modification"
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Status</label>
                <select
                  value={filters.status}
                  onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                >
                  <option value="">All</option>
                  <option value="success">Success</option>
                  <option value="failure">Failure</option>
                  <option value="partial">Partial</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Days</label>
                <input
                  type="number"
                  value={filters.days}
                  onChange={(e) => setFilters({ ...filters, days: parseInt(e.target.value) || 30 })}
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                />
              </div>
              <div className="col-span-2 flex items-end gap-2">
                <button
                  onClick={fetchActivityLogs}
                  disabled={loading}
                  className="px-4 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 flex items-center"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="h-3 w-3 mr-2 animate-spin" />
                      Loading...
                    </>
                  ) : (
                    <>
                      <Filter className="h-3 w-3 mr-2" />
                      Apply Filters
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Logs Table */}
          {loading ? (
            <div className="text-center py-8 text-gray-500">Loading activity logs...</div>
          ) : logs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Activity className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p>No activity logs found for the selected filters</p>
            </div>
          ) : (
            <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Resource</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Details</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {logs.map((log) => (
                      <tr key={log.log_id} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-900">
                          {new Date(log.timestamp).toLocaleString()}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900">{log.user_name}</td>
                        <td className="px-4 py-3 text-sm">
                          <div className="font-medium text-gray-900">{log.action_type}</div>
                          <div className="text-xs text-gray-500">{log.action_category}</div>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900">
                          {log.resource_type} #{log.resource_id}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            log.status === 'success'
                              ? 'bg-green-100 text-green-800'
                              : log.status === 'failure'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }`}>
                            {log.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">
                          {typeof log.details === 'string' ? log.details : JSON.stringify(log.details)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Governance RAG Query Tab */}
      {activeTab === 'rag' && (
        <div>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Query Governance Data
            </label>
            <div className="flex space-x-2">
              <input
                type="text"
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                placeholder="e.g., What accounts had KPI changes in the last 90 days?"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                onKeyPress={(e) => e.key === 'Enter' && executeRAGQuery()}
              />
              <select
                value={ragDays}
                onChange={(e) => setRagDays(parseInt(e.target.value))}
                className="px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value={30}>Last 30 days</option>
                <option value={60}>Last 60 days</option>
                <option value={90}>Last 90 days</option>
                <option value={180}>Last 180 days</option>
              </select>
              <button
                onClick={executeRAGQuery}
                disabled={ragLoading || !ragQuery.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center"
              >
                {ragLoading ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Querying...
                  </>
                ) : (
                  <>
                    <MessageSquare className="h-4 w-4 mr-2" />
                    Query
                  </>
                )}
              </button>
            </div>
          </div>

          {ragError && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-4">
              <p className="text-red-600">{ragError}</p>
            </div>
          )}

          {ragResponse && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-2">Response:</h4>
              <p className="text-gray-700 whitespace-pre-wrap">{ragResponse}</p>
            </div>
          )}
        </div>
      )}

      {/* Data Quality Tab */}
      {activeTab === 'dq' && (
        <div>
          {dqLoading ? (
            <div className="text-center py-8 text-gray-500">Loading data quality report...</div>
          ) : dqError ? (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-600">{dqError}</p>
            </div>
          ) : dqReport ? (
            <div className="space-y-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <h4 className="font-semibold text-gray-900 mb-3">Data Quality Summary</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-gray-600">Total Accounts</div>
                    <div className="text-xl font-bold text-gray-900">{dqReport.summary?.total_accounts || 0}</div>
                  </div>
                  <div>
                    <div className="text-gray-600">No Products</div>
                    <div className="text-xl font-bold text-yellow-600">{dqReport.summary?.accounts_with_no_products || 0}</div>
                  </div>
                  <div>
                    <div className="text-gray-600">Duplicates</div>
                    <div className="text-xl font-bold text-orange-600">{dqReport.summary?.accounts_with_duplicates || 0}</div>
                  </div>
                  <div>
                    <div className="text-gray-600">Out of Range</div>
                    <div className="text-xl font-bold text-red-600">{dqReport.summary?.accounts_with_out_of_range_percent || 0}</div>
                  </div>
                </div>
              </div>

              {dqReport.details && dqReport.details.length > 0 && (
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3">Account Details</h4>
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {dqReport.details.map((acct: any) => (
                      <div key={acct.account_id} className="p-4 border border-gray-200 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="font-semibold text-gray-900">{acct.account_name}</div>
                            <div className="text-xs text-gray-600">Account #{acct.account_id}</div>
                          </div>
                          <div className="text-xs text-gray-700">
                            <span className="mr-3">Products: {acct.products_count}</span>
                          </div>
                        </div>
                        {acct.duplicate_account_level_params?.length > 0 && (
                          <div className="mt-2 text-xs text-gray-700">
                            <strong>Duplicate parameters:</strong> {acct.duplicate_account_level_params.slice(0, 10).join(', ')}
                            {acct.duplicate_account_level_params.length > 10 && ' …'}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Shield className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p>No data quality report available</p>
              <button
                onClick={fetchDataQuality}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Generate Report
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
