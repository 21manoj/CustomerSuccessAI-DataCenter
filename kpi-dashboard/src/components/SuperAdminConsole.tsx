/**
 * Super Admin Console — Standalone Platform Management UI
 * ========================================================
 * Purpose-built admin interface for platform operators to:
 *  - View platform-wide stats (customers, users, accounts)
 *  - Browse and search all customers
 *  - Drill into customer detail (config, accounts, users, API keys)
 *  - Create new customers
 *  - Manage users, tiers, and access
 *
 * Route: /super-admin
 * Auth: Requires session with role='admin' or 'super_admin'
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useSession } from '../contexts/SessionContext';
import { useNavigate } from 'react-router-dom';
import { getApiBaseUrl } from '../utils/api';
import FeatureTogglePanel from './admin/FeatureTogglePanel';
import AccountHealthReset from './admin/AccountHealthReset';
import WeightOverridePanel from './admin/WeightOverridePanel';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DashboardStats {
  total_customers: number;
  active_customers: number;
  total_active_users: number;
  total_active_accounts: number;
}

interface CustomerRow {
  customer_id: number;
  customer_name: string;
  domain: string;
  vertical: string;
  email: string;
  created_at: string | null;
  account_count: number;
  user_count: number;
}

interface CustomerDetail {
  customer: {
    customer_id: number;
    customer_name: string;
    domain: string;
    email: string;
    vertical: string;
    uuid: string;
    created_at: string | null;
  };
  config: {
    vertical: string;
    enabled_kpis: string[] | null;
    pillar_weights: Record<string, number> | null;
    config_version: string;
  } | null;
  accounts: Array<{
    account_id: number;
    account_name: string;
    status: string;
    industry: string;
    region: string;
    revenue: number;
  }>;
  users: Array<{
    user_id: number;
    user_name: string;
    email: string;
    role: string;
    active: boolean;
    last_login: string | null;
    is_contractor: boolean;
    expires_at: string | null;
  }>;
  tier: string;
}

interface ApiKeyInfo {
  id: number;
  key_prefix: string;
  name: string;
  scopes: string[];
  is_active: boolean;
  created_at: string | null;
  expires_at: string | null;
}

interface ActivityEntry {
  id: number;
  action_type: string;
  action_description: string;
  status: string;
  created_at: string | null;
  customer_id: number | null;
}

// ---------------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------------

const BASE = '/api/admin-ui';

/** Format a UTC timestamp (from backend) to local timezone display.
 *  Backend returns naive ISO strings without 'Z' — append Z to force UTC interpretation. */
function fmtDate(dateStr: string | null, includeTime = true): string {
  if (!dateStr) return '—';
  // Append Z if missing to force UTC interpretation
  const utcStr = dateStr.endsWith('Z') ? dateStr : dateStr + 'Z';
  const d = new Date(utcStr);
  if (isNaN(d.getTime())) return dateStr;
  return includeTime
    ? d.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const resp = await fetch(`${baseUrl}${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers as Record<string, string>) },
    ...options,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ error: resp.statusText }));
    throw new Error(body.error || `Request failed: ${resp.status}`);
  }
  if (resp.status === 204) return undefined as unknown as T;
  return resp.json();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

type View = 'dashboard' | 'customers' | 'customer-detail' | 'create-customer' | 'activity-log' | 'feature-toggles' | 'escalation-tools';

const SuperAdminConsole: React.FC = () => {
  const { session, logout } = useSession();
  const navigate = useNavigate();

  const [view, setView] = useState<View>('dashboard');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [customers, setCustomers] = useState<CustomerRow[]>([]);
  const [customerTotal, setCustomerTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerDetail | null>(null);
  const [apiKeys, setApiKeys] = useState<ApiKeyInfo[]>([]);
  const [activityLog, setActivityLog] = useState<ActivityEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Create customer form
  const [newCustomer, setNewCustomer] = useState({
    company_name: '', admin_email: '', admin_name: '', password: '',
    vertical: 'dc2_s', tier: 'starter', domain: '', num_accounts: 3,
  });

  // Load dashboard stats
  const loadStats = useCallback(async () => {
    try {
      const data = await api<{ overview: DashboardStats }>('/dashboard/stats');
      setStats(data.overview);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  // Load customers
  const loadCustomers = useCallback(async (searchTerm?: string) => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (searchTerm) params.set('search', searchTerm);
      params.set('per_page', '50');
      const data = await api<{ customers: CustomerRow[]; pagination: { total: number } }>(`/customers?${params}`);
      setCustomers(data.customers);
      setCustomerTotal(data.pagination.total);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load customer detail
  const loadCustomerDetail = useCallback(async (cid: number) => {
    try {
      setLoading(true);
      setError('');
      const data = await api<CustomerDetail>(`/customers/${cid}`);
      setSelectedCustomer(data);
      // Load API keys
      try {
        const keyData = await api<{ api_keys: ApiKeyInfo[] }>(`/customers/${cid}/api-keys`);
        setApiKeys(keyData.api_keys || []);
      } catch { setApiKeys([]); }
      setView('customer-detail');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load activity log
  const loadActivityLog = useCallback(async () => {
    try {
      const data = await api<{ activity_logs: ActivityEntry[] }>('/activity-log?per_page=50');
      setActivityLog(data.activity_logs || []);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  // Create customer
  const handleCreateCustomer = async () => {
    try {
      setLoading(true);
      setError('');
      const result = await api<{ customer_id: number; message: string }>('/customers', {
        method: 'POST',
        body: JSON.stringify(newCustomer),
      });
      setSuccessMsg(result.message);
      setNewCustomer({ company_name: '', admin_email: '', admin_name: '', password: '', vertical: 'dc2_s', tier: 'starter', domain: '', num_accounts: 3 });
      // Navigate to the new customer
      await loadCustomerDetail(result.customer_id);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Create API key
  const handleCreateApiKey = async (cid: number) => {
    try {
      setError('');
      const result = await api<{ key: string }>(`/customers/${cid}/api-keys`, {
        method: 'POST',
        body: JSON.stringify({ name: `Key for ${cid}`, scopes: ['read', 'write'], duration_days: 365 }),
      });
      const mcpUrl = `${window.location.origin}/mcp/${result.key}`;
      setSuccessMsg(`API Key created: ${result.key}\n\nMCP URL (paste into Claude.ai):\n${mcpUrl}`);
      // Reload keys
      const keyData = await api<{ api_keys: ApiKeyInfo[] }>(`/customers/${cid}/api-keys`);
      setApiKeys(keyData.api_keys || []);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => {
    loadStats();
    loadCustomers();
  }, [loadStats, loadCustomers]);

  // Auth gate
  if (!session || !['admin', 'super_admin'].includes(session.role || '')) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="bg-gray-900 border border-red-700/50 rounded-xl p-8 max-w-md text-center">
          <div className="text-red-400 text-5xl mb-4">&#128274;</div>
          <h2 className="text-xl font-bold text-white mb-2">Access Denied</h2>
          <p className="text-gray-400 mb-6">Super Admin or Admin role required.</p>
          <button onClick={() => navigate('/login')} className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500">
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">SA</div>
          <h1 className="text-lg font-bold text-white">CS Pulse — Super Admin Console</h1>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-400">{session.email} ({session.role})</span>
          <button onClick={() => navigate('/dc-dashboard')} className="text-xs px-3 py-1.5 bg-gray-800 text-gray-300 rounded hover:bg-gray-700">
            Dashboard
          </button>
          <button onClick={() => { logout(); navigate('/login'); }} className="text-xs px-3 py-1.5 bg-red-900/50 text-red-300 rounded hover:bg-red-800/50">
            Logout
          </button>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <nav className="w-56 bg-gray-900 border-r border-gray-800 min-h-[calc(100vh-64px)] p-4 space-y-1">
          {([
            ['dashboard', 'Dashboard', '\u25A0'],
            ['customers', 'Customers', '\uD83D\uDC65'],
            ['create-customer', 'New Customer', '\u2795'],
            ['feature-toggles', 'Feature Toggles', '\u2699'],
            ['escalation-tools', 'Escalation Tools', '\u26A1'],
            ['activity-log', 'Activity Log', '\uD83D\uDCC4'],
          ] as [View, string, string][]).map(([v, label, icon]) => (
            <button
              key={v}
              onClick={() => {
                setView(v);
                setError('');
                setSuccessMsg('');
                if (v === 'customers') loadCustomers(search);
                if (v === 'activity-log') loadActivityLog();
              }}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center gap-2 transition-colors ${
                view === v ? 'bg-blue-600/20 text-blue-400 font-medium' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
              }`}
            >
              <span>{icon}</span>
              {label}
            </button>
          ))}
        </nav>

        {/* Main Content */}
        <main className="flex-1 p-6 max-w-6xl">
          {/* Alerts */}
          {error && (
            <div className="mb-4 p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-300 text-sm flex justify-between">
              <span>{error}</span>
              <button onClick={() => setError('')} className="text-red-400 hover:text-red-200">x</button>
            </div>
          )}
          {successMsg && (
            <div className="mb-4 p-3 bg-green-900/30 border border-green-700/50 rounded-lg text-green-300 text-sm flex justify-between">
              <span>{successMsg}</span>
              <button onClick={() => setSuccessMsg('')} className="text-green-400 hover:text-green-200">x</button>
            </div>
          )}

          {/* Dashboard View */}
          {view === 'dashboard' && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-6">Platform Overview</h2>
              <div className="grid grid-cols-4 gap-4 mb-8">
                {[
                  { label: 'Total Customers', value: stats?.total_customers ?? '—', color: 'blue' },
                  { label: 'Active Customers', value: stats?.active_customers ?? '—', color: 'green' },
                  { label: 'Active Users', value: stats?.total_active_users ?? '—', color: 'violet' },
                  { label: 'Active Accounts', value: stats?.total_active_accounts ?? '—', color: 'amber' },
                ].map((card) => (
                  <div key={card.label} className={`bg-gray-900 border border-gray-800 rounded-xl p-5`}>
                    <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{card.label}</p>
                    <p className={`text-3xl font-bold text-${card.color}-400`}>{card.value}</p>
                  </div>
                ))}
              </div>

              {/* Quick customer list */}
              <h3 className="text-lg font-semibold text-white mb-3">Recent Customers</h3>
              <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase">
                      <th className="text-left px-4 py-3">ID</th>
                      <th className="text-left px-4 py-3">Name</th>
                      <th className="text-left px-4 py-3">Vertical</th>
                      <th className="text-left px-4 py-3">Accounts</th>
                      <th className="text-left px-4 py-3">Users</th>
                      <th className="text-left px-4 py-3">Created</th>
                      <th className="px-4 py-3"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {customers.slice(0, 10).map((c) => (
                      <tr key={c.customer_id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                        <td className="px-4 py-3 text-gray-400 font-mono">{c.customer_id}</td>
                        <td className="px-4 py-3 text-white font-medium">{c.customer_name}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded text-xs ${c.vertical === 'dc2_s' ? 'bg-violet-900/40 text-violet-300' : 'bg-blue-900/40 text-blue-300'}`}>
                            {c.vertical || 'saas'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-400">{c.account_count}</td>
                        <td className="px-4 py-3 text-gray-400">{c.user_count}</td>
                        <td className="px-4 py-3 text-gray-500 text-xs">{fmtDate(c.created_at, false)}</td>
                        <td className="px-4 py-3">
                          <button onClick={() => loadCustomerDetail(c.customer_id)} className="text-xs text-blue-400 hover:text-blue-300">
                            View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Customers List View */}
          {view === 'customers' && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-white">Customers ({customerTotal})</h2>
                <button onClick={() => setView('create-customer')} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-500">
                  + New Customer
                </button>
              </div>

              {/* Search */}
              <div className="mb-4">
                <input
                  type="text"
                  placeholder="Search customers..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && loadCustomers(search)}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 text-sm focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase">
                      <th className="text-left px-4 py-3">ID</th>
                      <th className="text-left px-4 py-3">Name</th>
                      <th className="text-left px-4 py-3">Email</th>
                      <th className="text-left px-4 py-3">Vertical</th>
                      <th className="text-left px-4 py-3">Accounts</th>
                      <th className="text-left px-4 py-3">Users</th>
                      <th className="text-left px-4 py-3">Created</th>
                      <th className="px-4 py-3"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {customers.map((c) => (
                      <tr key={c.customer_id} className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer" onClick={() => loadCustomerDetail(c.customer_id)}>
                        <td className="px-4 py-3 text-gray-400 font-mono">{c.customer_id}</td>
                        <td className="px-4 py-3 text-white font-medium">{c.customer_name}</td>
                        <td className="px-4 py-3 text-gray-400">{c.email}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded text-xs ${c.vertical === 'dc2_s' ? 'bg-violet-900/40 text-violet-300' : 'bg-blue-900/40 text-blue-300'}`}>
                            {c.vertical || 'saas'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-gray-400">{c.account_count}</td>
                        <td className="px-4 py-3 text-gray-400">{c.user_count}</td>
                        <td className="px-4 py-3 text-gray-500 text-xs">{fmtDate(c.created_at, false)}</td>
                        <td className="px-4 py-3">
                          <button className="text-xs text-blue-400 hover:text-blue-300">View</button>
                        </td>
                      </tr>
                    ))}
                    {customers.length === 0 && (
                      <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-500">No customers found</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Customer Detail View */}
          {view === 'customer-detail' && selectedCustomer && (
            <div>
              <button onClick={() => { setView('customers'); loadCustomers(search); }} className="text-sm text-gray-400 hover:text-blue-400 mb-4 inline-block">
                &larr; Back to Customers
              </button>

              <div className="flex items-center gap-4 mb-6">
                <h2 className="text-2xl font-bold text-white">{selectedCustomer.customer.customer_name}</h2>
                <span className="text-xs font-mono text-gray-500">ID: {selectedCustomer.customer.customer_id}</span>
                <span className={`px-2 py-0.5 rounded text-xs ${
                  selectedCustomer.tier === 'enterprise' ? 'bg-amber-900/40 text-amber-300' :
                  selectedCustomer.tier === 'professional' ? 'bg-blue-900/40 text-blue-300' :
                  'bg-gray-800 text-gray-400'
                }`}>
                  {selectedCustomer.tier}
                </span>
              </div>

              {/* Customer Info Cards */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                  <p className="text-xs text-gray-500 uppercase mb-2">Details</p>
                  <div className="space-y-1 text-sm">
                    <p><span className="text-gray-500">Email:</span> <span className="text-gray-300">{selectedCustomer.customer.email}</span></p>
                    <p><span className="text-gray-500">Domain:</span> <span className="text-gray-300">{selectedCustomer.customer.domain || '—'}</span></p>
                    <p><span className="text-gray-500">Vertical:</span> <span className="text-gray-300">{selectedCustomer.customer.vertical}</span></p>
                    <p><span className="text-gray-500">UUID:</span> <span className="text-gray-400 font-mono text-xs">{selectedCustomer.customer.uuid || '—'}</span></p>
                    <p><span className="text-gray-500">Created:</span> <span className="text-gray-300">{fmtDate(selectedCustomer.customer.created_at, false)}</span></p>
                  </div>
                </div>

                <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                  <p className="text-xs text-gray-500 uppercase mb-2">Config</p>
                  {selectedCustomer.config ? (
                    <div className="space-y-1 text-sm">
                      <p><span className="text-gray-500">Version:</span> <span className="text-gray-300">{selectedCustomer.config.config_version}</span></p>
                      <p><span className="text-gray-500">Enabled KPIs:</span> <span className="text-gray-300">{selectedCustomer.config.enabled_kpis?.length ?? 'All'}</span></p>
                      {selectedCustomer.config.pillar_weights && (
                        <div className="mt-2">
                          <p className="text-gray-500 text-xs mb-1">Pillar Weights:</p>
                          {Object.entries(selectedCustomer.config.pillar_weights).map(([k, v]) => (
                            <span key={k} className="inline-block mr-2 mb-1 px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-300">{k}: {(v * 100).toFixed(0)}%</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-sm">No config set</p>
                  )}
                </div>

                <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                  <p className="text-xs text-gray-500 uppercase mb-2">Summary</p>
                  <div className="space-y-1 text-sm">
                    <p><span className="text-gray-500">Accounts:</span> <span className="text-green-400 font-medium">{selectedCustomer.accounts.length}</span></p>
                    <p><span className="text-gray-500">Users:</span> <span className="text-blue-400 font-medium">{selectedCustomer.users.length}</span></p>
                    <p><span className="text-gray-500">API Keys:</span> <span className="text-violet-400 font-medium">{apiKeys.length}</span></p>
                    <p><span className="text-gray-500">Tier:</span> <span className="text-amber-400 font-medium capitalize">{selectedCustomer.tier}</span></p>
                  </div>
                </div>
              </div>

              {/* Accounts Table */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-white mb-3">Accounts ({selectedCustomer.accounts.length})</h3>
                <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase">
                        <th className="text-left px-4 py-2">ID</th>
                        <th className="text-left px-4 py-2">Name</th>
                        <th className="text-left px-4 py-2">Status</th>
                        <th className="text-left px-4 py-2">Industry</th>
                        <th className="text-left px-4 py-2">Region</th>
                        <th className="text-right px-4 py-2">Revenue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedCustomer.accounts.map((a) => (
                        <tr key={a.account_id} className="border-b border-gray-800/50">
                          <td className="px-4 py-2 text-gray-400 font-mono">{a.account_id}</td>
                          <td className="px-4 py-2 text-white">{a.account_name}</td>
                          <td className="px-4 py-2">
                            <span className={`px-2 py-0.5 rounded text-xs ${a.status === 'active' ? 'bg-green-900/40 text-green-300' : 'bg-gray-800 text-gray-500'}`}>
                              {a.status}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-gray-400">{a.industry || '—'}</td>
                          <td className="px-4 py-2 text-gray-400">{a.region || '—'}</td>
                          <td className="px-4 py-2 text-right text-gray-400">${a.revenue?.toLocaleString() || '0'}</td>
                        </tr>
                      ))}
                      {selectedCustomer.accounts.length === 0 && (
                        <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-500">No accounts</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Users Table */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-white mb-3">Users ({selectedCustomer.users.length})</h3>
                <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase">
                        <th className="text-left px-4 py-2">ID</th>
                        <th className="text-left px-4 py-2">Name</th>
                        <th className="text-left px-4 py-2">Email</th>
                        <th className="text-left px-4 py-2">Role</th>
                        <th className="text-left px-4 py-2">Status</th>
                        <th className="text-left px-4 py-2">Last Login</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedCustomer.users.map((u) => (
                        <tr key={u.user_id} className="border-b border-gray-800/50">
                          <td className="px-4 py-2 text-gray-400 font-mono">{u.user_id}</td>
                          <td className="px-4 py-2 text-white">{u.user_name}</td>
                          <td className="px-4 py-2 text-gray-400">{u.email}</td>
                          <td className="px-4 py-2">
                            <span className={`px-2 py-0.5 rounded text-xs ${
                              u.role === 'admin' || u.role === 'super_admin' ? 'bg-amber-900/40 text-amber-300' :
                              u.is_contractor ? 'bg-orange-900/40 text-orange-300' :
                              'bg-gray-800 text-gray-400'
                            }`}>
                              {u.role}{u.is_contractor ? ' (contractor)' : ''}
                            </span>
                          </td>
                          <td className="px-4 py-2">
                            <span className={`px-2 py-0.5 rounded text-xs ${u.active ? 'bg-green-900/40 text-green-300' : 'bg-red-900/40 text-red-300'}`}>
                              {u.active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-gray-500 text-xs">{fmtDate(u.last_login)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* API Keys */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold text-white">API Keys ({apiKeys.length})</h3>
                  <button
                    onClick={() => handleCreateApiKey(selectedCustomer.customer.customer_id)}
                    className="text-xs px-3 py-1.5 bg-violet-600 text-white rounded hover:bg-violet-500"
                  >
                    + Generate Key
                  </button>
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase">
                        <th className="text-left px-4 py-2">ID</th>
                        <th className="text-left px-4 py-2">Name</th>
                        <th className="text-left px-4 py-2">Key Prefix</th>
                        <th className="text-left px-4 py-2">Scopes</th>
                        <th className="text-left px-4 py-2">Status</th>
                        <th className="text-left px-4 py-2">Expires</th>
                        <th className="text-left px-4 py-2">MCP URL</th>
                      </tr>
                    </thead>
                    <tbody>
                      {apiKeys.map((k) => (
                        <tr key={k.id} className="border-b border-gray-800/50">
                          <td className="px-4 py-2 text-gray-400 font-mono">{k.id}</td>
                          <td className="px-4 py-2 text-white">{k.name}</td>
                          <td className="px-4 py-2 text-gray-400 font-mono">{k.key_prefix}...</td>
                          <td className="px-4 py-2">
                            {k.scopes?.map((s) => (
                              <span key={s} className="inline-block mr-1 px-1.5 py-0.5 bg-gray-800 rounded text-xs text-gray-400">{s}</span>
                            ))}
                          </td>
                          <td className="px-4 py-2">
                            <span className={`px-2 py-0.5 rounded text-xs ${k.is_active ? 'bg-green-900/40 text-green-300' : 'bg-red-900/40 text-red-300'}`}>
                              {k.is_active ? 'Active' : 'Revoked'}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-gray-500 text-xs">{fmtDate(k.expires_at, false)}</td>
                          <td className="px-4 py-2">
                            {k.is_active && (
                              <span className="text-xs text-gray-600 font-mono" title="Full MCP URL shown at key creation time">
                                /mcp/{k.key_prefix}...
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                      {apiKeys.length === 0 && (
                        <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-500">No API keys</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Create Customer View */}
          {view === 'create-customer' && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-6">Create New Customer</h2>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-2xl">
                <div className="grid grid-cols-2 gap-4">
                  <div className="col-span-2">
                    <label className="block text-xs text-gray-500 uppercase mb-1">Company Name *</label>
                    <input
                      type="text"
                      value={newCustomer.company_name}
                      onChange={(e) => setNewCustomer({ ...newCustomer, company_name: e.target.value })}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:border-blue-500 focus:outline-none"
                      placeholder="Acme Corp"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 uppercase mb-1">Admin Email *</label>
                    <input
                      type="email"
                      value={newCustomer.admin_email}
                      onChange={(e) => setNewCustomer({ ...newCustomer, admin_email: e.target.value })}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:border-blue-500 focus:outline-none"
                      placeholder="admin@acme.com"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 uppercase mb-1">Admin Name</label>
                    <input
                      type="text"
                      value={newCustomer.admin_name}
                      onChange={(e) => setNewCustomer({ ...newCustomer, admin_name: e.target.value })}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:border-blue-500 focus:outline-none"
                      placeholder="Admin"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 uppercase mb-1">Password *</label>
                    <input
                      type="password"
                      value={newCustomer.password}
                      onChange={(e) => setNewCustomer({ ...newCustomer, password: e.target.value })}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:border-blue-500 focus:outline-none"
                      placeholder="Min 8 chars, upper+lower+digit"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 uppercase mb-1">Domain</label>
                    <input
                      type="text"
                      value={newCustomer.domain}
                      onChange={(e) => setNewCustomer({ ...newCustomer, domain: e.target.value })}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:border-blue-500 focus:outline-none"
                      placeholder="acme.com"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 uppercase mb-1">Vertical</label>
                    <select
                      value={newCustomer.vertical}
                      onChange={(e) => setNewCustomer({ ...newCustomer, vertical: e.target.value })}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:border-blue-500 focus:outline-none"
                    >
                      <option value="dc2_s">Data Center (DC2_S)</option>
                      <option value="saas">SaaS</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 uppercase mb-1">Tier</label>
                    <select
                      value={newCustomer.tier}
                      onChange={(e) => setNewCustomer({ ...newCustomer, tier: e.target.value })}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:border-blue-500 focus:outline-none"
                    >
                      <option value="starter">Starter</option>
                      <option value="professional">Professional</option>
                      <option value="enterprise">Enterprise</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 uppercase mb-1">Number of Accounts</label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={newCustomer.num_accounts}
                      onChange={(e) => setNewCustomer({ ...newCustomer, num_accounts: parseInt(e.target.value) || 3 })}
                      className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="mt-6 flex gap-3">
                  <button
                    onClick={handleCreateCustomer}
                    disabled={loading || !newCustomer.company_name || !newCustomer.admin_email || !newCustomer.password}
                    className="px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Creating...' : 'Create Customer'}
                  </button>
                  <button onClick={() => setView('customers')} className="px-6 py-2.5 bg-gray-800 text-gray-300 rounded-lg text-sm hover:bg-gray-700">
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Feature Toggles View */}
          {view === 'feature-toggles' && <FeatureTogglePanel />}

          {/* Escalation Tools View */}
          {view === 'escalation-tools' && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-6">Escalation Tools</h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                  <AccountHealthReset customerId={selectedCustomer?.customer?.customer_id || 0} />
                </div>
                <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                  <WeightOverridePanel customerId={selectedCustomer?.customer?.customer_id || 0} />
                </div>
              </div>
              {!selectedCustomer && (
                <p className="text-sm text-gray-500 mt-4">
                  Tip: Select a customer from the Customers tab first to use customer-specific tools.
                </p>
              )}
            </div>
          )}

          {/* Activity Log View */}
          {view === 'activity-log' && (
            <div>
              <h2 className="text-2xl font-bold text-white mb-6">Activity Log</h2>
              <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase">
                      <th className="text-left px-4 py-3">Time</th>
                      <th className="text-left px-4 py-3">Action</th>
                      <th className="text-left px-4 py-3">Description</th>
                      <th className="text-left px-4 py-3">Customer</th>
                      <th className="text-left px-4 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activityLog.map((entry) => (
                      <tr key={entry.id} className="border-b border-gray-800/50">
                        <td className="px-4 py-2 text-gray-500 text-xs whitespace-nowrap">
                          {fmtDate(entry.created_at)}
                        </td>
                        <td className="px-4 py-2">
                          <span className="px-2 py-0.5 bg-gray-800 rounded text-xs text-gray-300">{entry.action_type}</span>
                        </td>
                        <td className="px-4 py-2 text-gray-300 text-xs max-w-md truncate">{entry.action_description}</td>
                        <td className="px-4 py-2 text-gray-400 font-mono">{entry.customer_id || '—'}</td>
                        <td className="px-4 py-2">
                          <span className={`px-2 py-0.5 rounded text-xs ${entry.status === 'success' ? 'bg-green-900/40 text-green-300' : 'bg-red-900/40 text-red-300'}`}>
                            {entry.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {activityLog.length === 0 && (
                      <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No activity logged yet</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default SuperAdminConsole;
