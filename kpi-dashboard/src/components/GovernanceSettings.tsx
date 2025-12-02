import React, { useState, useEffect } from 'react';
import { Shield, Activity, Search, Download, Filter, MessageSquare, Clock } from 'lucide-react';

interface ActivityLog {
  id: number;
  customer_id: number;
  user_id: number | null;
  user_name: string | null;
  action_type: string;
  action_category: string;
  resource_type: string | null;
  resource_id: string | null;
  action_description: string;
  details: any;
  changed_fields: string[];
  before_values: any;
  after_values: any;
  ip_address: string | null;
  user_agent: string | null;
  session_id: string | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

interface ActivitySummary {
  period_days: number;
  start_date: string;
  end_date: string;
  total_activities: number;
  by_action_type: Record<string, number>;
  by_action_category: Record<string, number>;
  by_status: Record<string, number>;
  top_users: Array<{ user_id: number; user_name: string; count: number }>;
}

interface GovernanceSettingsProps {
  isAuthenticated: boolean;
}

const GovernanceSettings: React.FC<GovernanceSettingsProps> = ({ isAuthenticated }) => {
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
  const [dqReport, setDqReport] = useState<{
    summary: {
      total_accounts: number;
      accounts_with_no_products: number;
      accounts_with_duplicates: number;
      accounts_with_out_of_range_percent: number;
      accounts_with_aggregates_in_primary: number;
    };
    details: Array<{
      account_id: number;
      account_name: string;
      products_count: number;
      duplicate_account_level_params: string[];
      percent_out_of_range: Array<{ kpi_id: number; kpi_parameter: string; value: string }>;
      aggregates_in_primary_view: boolean;
    }>;
  } | null>(null);

  useEffect(() => {
    if (!isAuthenticated) return;
    if (activeTab === 'logs') {
      fetchActivityLogs();
      fetchSummary();
    } else if (activeTab === 'dq') {
      fetchDataQuality();
    }
  }, [isAuthenticated, activeTab, filters]);

  const fetchActivityLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      if (filters.action_type) params.append('action_type', filters.action_type);
      if (filters.action_category) params.append('action_category', filters.action_category);
      if (filters.resource_type) params.append('resource_type', filters.resource_type);
      if (filters.user_id) params.append('user_id', filters.user_id);
      if (filters.status) params.append('status', filters.status);
      params.append('limit', '100');
      params.append('offset', '0');
      
      const response = await fetch(`/api/activity-logs?${params.toString()}`, {
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
      } else {
        throw new Error('Failed to fetch activity logs');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch activity logs');
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await fetch(`/api/activity-logs/summary?days=${filters.days}`, {
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        setSummary(data.summary || null);
      }
    } catch (err) {
      console.error('Failed to fetch summary:', err);
    }
  };

  const handleExportLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filters.action_type) params.append('action_type', filters.action_type);
      if (filters.action_category) params.append('action_category', filters.action_category);
      if (filters.resource_type) params.append('resource_type', filters.resource_type);
      if (filters.user_id) params.append('user_id', filters.user_id);
      if (filters.status) params.append('status', filters.status);
      params.append('limit', '10000');
      
      const response = await fetch(`/api/activity-logs/export?${params.toString()}`, {
        credentials: 'include',
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `activity_logs_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } else {
        throw new Error('Failed to export logs');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export logs');
    } finally {
      setLoading(false);
    }
  };

  const handleRagQuery = async () => {
    if (!ragQuery.trim()) {
      setRagError('Please enter a query');
      return;
    }
    
    try {
      setRagLoading(true);
      setRagError(null);
      setRagResponse(null);
      
      const response = await fetch('/api/governance-rag/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          query: ragQuery,
          days: ragDays,
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setRagResponse(data.response || 'No response');
      } else {
        const errorData = await response.json().catch(() => ({ error: 'Failed to query governance data' }));
        throw new Error(errorData.error || 'Failed to query governance data');
      }
    } catch (err) {
      setRagError(err instanceof Error ? err.message : 'Failed to query governance data');
    } finally {
      setRagLoading(false);
    }
  };

  const fetchDataQuality = async () => {
    try {
      setDqLoading(true);
      setDqError(null);
      const response = await fetch('/api/data-quality/report', { credentials: 'include' });
      if (!response.ok) {
        throw new Error('Failed to fetch data quality report');
      }
      const data = await response.json();
      setDqReport(data);
    } catch (err) {
      setDqError(err instanceof Error ? err.message : 'Failed to fetch data quality report');
    } finally {
      setDqLoading(false);
    }
  };

  const fixSeedMissingProducts = async () => {
    try {
      setDqLoading(true);
      setDqError(null);
      const response = await fetch('/api/data-quality/fix/seed-missing-products', {
        method: 'POST',
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Failed to seed missing products');
      await fetchDataQuality();
    } catch (err) {
      setDqError(err instanceof Error ? err.message : 'Failed to seed missing products');
    } finally {
      setDqLoading(false);
    }
  };

  const fixDedupeAccountLevel = async () => {
    try {
      setDqLoading(true);
      setDqError(null);
      const response = await fetch('/api/data-quality/fix/dedupe-account-level', {
        method: 'POST',
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Failed to dedupe account-level KPIs');
      await fetchDataQuality();
    } catch (err) {
      setDqError(err instanceof Error ? err.message : 'Failed to dedupe account-level KPIs');
    } finally {
      setDqLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Shield className="h-5 w-5 mr-2 text-blue-600" />
          Governance & Compliance
        </h3>
        <p className="text-sm text-gray-600">Please log in to access governance features.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
        <Shield className="h-5 w-5 mr-2 text-blue-600" />
        Governance & Compliance
      </h3>
      
      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-6">
        <button
          onClick={() => setActiveTab('logs')}
          className={`px-4 py-2 font-medium text-sm ${
            activeTab === 'logs'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <Activity className="h-4 w-4 inline mr-2" />
          Activity Logs
        </button>
        <button
          onClick={() => setActiveTab('rag')}
          className={`px-4 py-2 font-medium text-sm ${
            activeTab === 'rag'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <MessageSquare className="h-4 w-4 inline mr-2" />
          Governance RAG Query
        </button>
        <button
          onClick={() => setActiveTab('dq')}
          className={`px-4 py-2 font-medium text-sm ${
            activeTab === 'dq'
              ? 'border-b-2 border-blue-600 text-blue-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <Shield className="h-4 w-4 inline mr-2" />
          Data Quality
        </button>
      </div>

      {/* Activity Logs Tab */}
      {activeTab === 'logs' && (
        <div>
          {/* Summary */}
          {summary && (
            <div className="mb-6 p-4 bg-gray-50 rounded-lg">
              <h4 className="font-semibold text-gray-900 mb-3">Activity Summary (Last {summary.period_days} days)</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-gray-600">Total Activities</div>
                  <div className="text-2xl font-bold text-gray-900">{summary.total_activities}</div>
                </div>
                <div>
                  <div className="text-gray-600">By Status</div>
                  <div className="text-xs text-gray-700">
                    {Object.entries(summary.by_status).map(([status, count]) => (
                      <div key={status}>{status}: {count}</div>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-gray-600">Top Categories</div>
                  <div className="text-xs text-gray-700">
                    {Object.entries(summary.by_action_category)
                      .sort((a, b) => b[1] - a[1])
                      .slice(0, 3)
                      .map(([cat, count]) => (
                        <div key={cat}>{cat}: {count}</div>
                      ))}
                  </div>
                </div>
                <div>
                  <div className="text-gray-600">Top Users</div>
                  <div className="text-xs text-gray-700">
                    {summary.top_users.slice(0, 3).map((user) => (
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
                  className="px-4 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Loading...' : 'Apply Filters'}
                </button>
                <button
                  onClick={handleExportLogs}
                  disabled={loading}
                  className="px-4 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50 flex items-center"
                >
                  <Download className="h-3 w-3 mr-1" />
                  Export CSV
                </button>
              </div>
            </div>
          </div>

          {/* Logs List */}
          {error && (
            <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded text-sm">
              {error}
            </div>
          )}

          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-gray-600">Loading activity logs...</p>
            </div>
          ) : logs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No activity logs found</div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {logs.map((log) => (
                <div key={log.id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          log.status === 'success' ? 'bg-green-100 text-green-800' :
                          log.status === 'failure' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {log.status}
                        </span>
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                          {log.action_category}
                        </span>
                        <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-xs">
                          {log.action_type}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-gray-900 mb-1">
                        {log.action_description}
                      </p>
                      <div className="flex items-center gap-4 text-xs text-gray-600">
                        <span>
                          <Clock className="h-3 w-3 inline mr-1" />
                          {new Date(log.created_at).toLocaleString()}
                        </span>
                        {log.user_name && (
                          <span>User: {log.user_name}</span>
                        )}
                        {log.resource_type && log.resource_id && (
                          <span>{log.resource_type} #{log.resource_id}</span>
                        )}
                      </div>
                      {log.changed_fields && log.changed_fields.length > 0 && (
                        <div className="mt-2 text-xs text-gray-600">
                          <strong>Changed:</strong> {log.changed_fields.join(', ')}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Governance RAG Tab */}
      {activeTab === 'rag' && (
        <div>
          <div className="mb-4">
            <p className="text-sm text-gray-600 mb-4">
              Ask questions about user activities, system changes, and compliance. This uses RAG (Retrieval-Augmented Generation) 
              to answer governance questions based on your activity logs.
            </p>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Time Period (days)
              </label>
              <input
                type="number"
                value={ragDays}
                onChange={(e) => setRagDays(parseInt(e.target.value) || 90)}
                min="1"
                max="365"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">Query activity logs from the last N days</p>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Governance Query
              </label>
              <textarea
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                placeholder="e.g., Who edited KPI #123? What configuration changes were made last week? Show me all failed actions in the last month."
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <button
              onClick={handleRagQuery}
              disabled={ragLoading || !ragQuery.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {ragLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Querying...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Query Governance Data
                </>
              )}
            </button>

            {ragError && (
              <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded text-sm">
                {ragError}
              </div>
            )}

            {ragResponse && (
              <div className="mt-4 space-y-3">
                <div className="p-3 rounded-md bg-yellow-50 border border-yellow-300 text-yellow-900 text-sm font-semibold">
                  Enhanced by Playbook execution Feedback
                </div>
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h4 className="font-semibold text-gray-900 mb-2">Response:</h4>
                  <div className="text-sm text-gray-700 whitespace-pre-wrap">{ragResponse}</div>
                </div>
              </div>
            )}
          </div>

          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h4 className="font-semibold text-gray-900 mb-2">Example Queries:</h4>
            <ul className="text-sm text-gray-600 space-y-1 list-disc list-inside">
              <li>"Who edited KPI #123 in the last 30 days?"</li>
              <li>"What configuration changes were made last week?"</li>
              <li>"Show me all failed actions in the last month"</li>
              <li>"Which users made the most changes last week?"</li>
              <li>"What exports were downloaded in the last 7 days?"</li>
              <li>"Show me all settings updates by user John"</li>
            </ul>
          </div>
        </div>
      )}

      {/* Data Quality Tab */}
      {activeTab === 'dq' && (
        <div>
          <div className="mb-4">
            <p className="text-sm text-gray-600">
              Review account data hygiene: duplicates, out-of-range percentages, missing products, and aggregates in primary views.
            </p>
          </div>
          <div className="flex gap-2 mb-4">
            <button
              onClick={fetchDataQuality}
              disabled={dqLoading}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {dqLoading ? 'Refreshing…' : 'Refresh Report'}
            </button>
            <button
              onClick={fixSeedMissingProducts}
              disabled={dqLoading}
              className="px-4 py-2 bg-gray-700 text-white text-sm rounded hover:bg-gray-800 disabled:opacity-50"
            >
              Seed Missing Products
            </button>
            <button
              onClick={fixDedupeAccountLevel}
              disabled={dqLoading}
              className="px-4 py-2 bg-gray-700 text-white text-sm rounded hover:bg-gray-800 disabled:opacity-50"
            >
              Dedupe Account-Level KPIs
            </button>
          </div>
          {dqError && (
            <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded text-sm">
              {dqError}
            </div>
          )}
          {!dqReport ? (
            <div className="text-gray-600 text-sm">No report loaded yet.</div>
          ) : (
            <>
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <h4 className="font-semibold text-gray-900 mb-3">Summary</h4>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                  <div>
                    <div className="text-gray-600">Total Accounts</div>
                    <div className="text-xl font-bold text-gray-900">{dqReport.summary.total_accounts}</div>
                  </div>
                  <div>
                    <div className="text-gray-600">No Products</div>
                    <div className="text-xl font-bold text-gray-900">{dqReport.summary.accounts_with_no_products}</div>
                  </div>
                  <div>
                    <div className="text-gray-600">Duplicates</div>
                    <div className="text-xl font-bold text-gray-900">{dqReport.summary.accounts_with_duplicates}</div>
                  </div>
                  <div>
                    <div className="text-gray-600">% Out of Range</div>
                    <div className="text-xl font-bold text-gray-900">{dqReport.summary.accounts_with_out_of_range_percent}</div>
                  </div>
                  <div>
                    <div className="text-gray-600">Aggregates in Primary</div>
                    <div className="text-xl font-bold text-gray-900">{dqReport.summary.accounts_with_aggregates_in_primary}</div>
                  </div>
                </div>
              </div>
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {dqReport.details.map((acct) => (
                  <div key={acct.account_id} className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-gray-900">{acct.account_name}</div>
                        <div className="text-xs text-gray-600">Account #{acct.account_id}</div>
                      </div>
                      <div className="text-xs text-gray-700">
                        <span className="mr-3">Products: {acct.products_count}</span>
                        <span className={acct.aggregates_in_primary_view ? 'text-red-600' : 'text-green-700'}>
                          Aggregates in Primary: {acct.aggregates_in_primary_view ? 'Yes' : 'No'}
                        </span>
                      </div>
                    </div>
                    {acct.duplicate_account_level_params.length > 0 && (
                      <div className="mt-2 text-xs text-gray-700">
                        <strong>Duplicate parameters:</strong> {acct.duplicate_account_level_params.slice(0, 10).join(', ')}
                        {acct.duplicate_account_level_params.length > 10 && ' …'}
                      </div>
                    )}
                    {acct.percent_out_of_range.length > 0 && (
                      <div className="mt-2 text-xs text-gray-700">
                        <strong>Out-of-range % examples:</strong>{' '}
                        {acct.percent_out_of_range.slice(0, 5).map((p) => `${p.kpi_parameter}=${p.value}`).join(', ')}
                        {acct.percent_out_of_range.length > 5 && ' …'}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default GovernanceSettings;

