/**
 * Test Runner — Standalone Layout
 * ================================
 *
 * Decoupled standalone application at /test-runner.
 * Runs on its OWN backend (port 5099), with its OWN credentials.
 * Completely independent of the main CS Pulse app and Admin UI.
 *
 * Emerald/green color scheme to differentiate from Admin UI (indigo) and
 * main dashboard (blue).
 *
 * Sidebar navigation:
 *   - Scenarios   — Select & run load-driver E2E scenarios
 *   - Platform    — Live customer/account health/ARR view
 *   - Analytics   — ROI, Power-of-1, revenue intelligence
 *   - Data Ops    — Push KPIs, signals, recalculate scores
 *   - Console     — Live stdout/stderr log viewer
 *   - Settings    — Feature flags
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  FlaskConical,
  Database,
  BarChart3,
  Upload,
  Terminal,
  Settings,
  Menu,
  X,
  LogOut,
  ChevronDown,
  Users,
  Lock,
  Loader2,
} from 'lucide-react';

import type { CustomerInfo } from '../dc/test-runner/types';
import { testRunnerApi } from '../dc/test-runner/api';
import ScenariosTab from '../dc/test-runner/tabs/ScenariosTab';
import PlatformStateTab from '../dc/test-runner/tabs/PlatformStateTab';
import AnalyticsTab from '../dc/test-runner/tabs/AnalyticsTab';
import DataOpsTab from '../dc/test-runner/tabs/DataOpsTab';
import SettingsTab, { TEST_RUNNER_FLAGS, getFlagValue, setFlagValue } from '../dc/test-runner/tabs/SettingsTab';
import ConsoleTab from './ConsoleTab';

// ---------------------------------------------------------------------------
// Sidebar navigation items
// ---------------------------------------------------------------------------

interface NavItem {
  label: string;
  to: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Scenarios', to: '/test-runner', icon: <FlaskConical size={18} /> },
  { label: 'Platform State', to: '/test-runner/platform', icon: <Database size={18} /> },
  { label: 'Analytics', to: '/test-runner/analytics', icon: <BarChart3 size={18} /> },
  { label: 'Data Ops', to: '/test-runner/dataops', icon: <Upload size={18} /> },
  { label: 'Console', to: '/test-runner/console', icon: <Terminal size={18} /> },
  { label: 'Settings', to: '/test-runner/settings', icon: <Settings size={18} /> },
];

// ---------------------------------------------------------------------------
// Test Runner Auth state (independent of main app session)
// ---------------------------------------------------------------------------
interface TRAuthState {
  authenticated: boolean;
  email: string;
  name: string;
  role: string;
}

// ---------------------------------------------------------------------------
// Login Form — Test Runner specific
// ---------------------------------------------------------------------------
const TestRunnerLoginForm: React.FC<{ onLogin: (auth: TRAuthState) => void }> = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch('/api/test-runner/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        onLogin({
          authenticated: true,
          email: data.email,
          name: data.name,
          role: data.role,
        });
      } else {
        setError(data.error || 'Login failed');
      }
    } catch {
      setError('Cannot reach Test Runner server (port 5099). Is it running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-100 flex items-center justify-center px-4">
      <div className="max-w-sm w-full">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-emerald-600 rounded-2xl shadow-lg mb-4">
            <FlaskConical className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Test Runner</h1>
          <p className="text-sm text-gray-500 mt-1">Load Driver E2E Scenarios</p>
          <p className="text-xs text-gray-400 mt-0.5">Separate server — port 5099</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              placeholder="tester@cspulse.com"
              required
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              placeholder="Enter password"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
            Sign In to Test Runner
          </button>
        </form>

        <p className="text-center text-xs text-gray-400 mt-4">
          This is a separate application from CS Pulse.
        </p>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Layout Component
// ---------------------------------------------------------------------------

const TestRunnerLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // --- Test Runner Auth (independent of main app) ---
  const [trAuth, setTrAuth] = useState<TRAuthState | null>(null);
  const [authChecking, setAuthChecking] = useState(true);

  // Check auth status on mount
  useEffect(() => {
    fetch('/api/test-runner/auth/status', { credentials: 'include' })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data?.authenticated) {
          setTrAuth({
            authenticated: true,
            email: data.email,
            name: data.name,
            role: data.role,
          });
        }
      })
      .catch(() => {})
      .finally(() => setAuthChecking(false));
  }, []);

  // Customer selection
  const [customerId, setCustomerId] = useState<string>('');
  const [customers, setCustomers] = useState<CustomerInfo[]>([]);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownTriggerRef = useRef<HTMLButtonElement>(null);
  const [dropdownPos, setDropdownPos] = useState<{ top: number; left: number; width: number } | null>(null);

  // Entitlements
  const [entitlements, setEntitlements] = useState<Record<string, boolean>>({});
  const [customerTier, setCustomerTier] = useState<string>('starter');

  // Feature flags
  const [flags, setFlags] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    for (const f of TEST_RUNNER_FLAGS) {
      init[f.key] = getFlagValue(f.key);
    }
    return init;
  });

  const handleFlagChange = useCallback((key: string, value: boolean) => {
    setFlagValue(key, value);
    setFlags(prev => ({ ...prev, [key]: value }));
  }, []);

  // Refresh trigger for Platform State
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Active run ID for console tab
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  // Fetch customers on mount (only when authenticated)
  const fetchCustomers = useCallback(() => {
    if (!trAuth?.authenticated) return;
    testRunnerApi.getCustomers().then(setCustomers).catch(() => {});
  }, [trAuth]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  // Fetch entitlements when customerId changes
  useEffect(() => {
    const cid = customerId?.trim();
    if (!cid) {
      setEntitlements({});
      setCustomerTier('starter');
      return;
    }
    fetch(`/api/entitlements?customer_id=${cid}`, { credentials: 'include' })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data?.entitlements) {
          setEntitlements(data.entitlements);
          setCustomerTier(data.tier || 'starter');
        }
      })
      .catch(() => {
        setEntitlements({});
        setCustomerTier('starter');
      });
  }, [customerId]);

  // Callbacks
  const handleRunComplete = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
    fetchCustomers();
  }, [fetchCustomers]);

  const handleDataPushed = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  const handleLogout = async () => {
    await fetch('/api/test-runner/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {});
    setTrAuth(null);
  };

  // Dropdown positioning
  useEffect(() => {
    if (dropdownOpen && dropdownTriggerRef.current) {
      const rect = dropdownTriggerRef.current.getBoundingClientRect();
      setDropdownPos({
        top: rect.bottom + 4,
        left: rect.left,
        width: Math.max(rect.width, 340),
      });
    }
  }, [dropdownOpen]);

  const selectedCustomer = customers.find(c => String(c.customer_id) === customerId);
  const isNewCustomer = !customerId;
  const effectiveCustomerId = customerId || '';

  // Determine active tab from URL
  const getActiveTab = () => {
    const path = location.pathname;
    if (path === '/test-runner' || path === '/test-runner/scenarios') return 'scenarios';
    if (path.includes('/platform')) return 'platform';
    if (path.includes('/analytics')) return 'analytics';
    if (path.includes('/dataops')) return 'dataops';
    if (path.includes('/console')) return 'console';
    if (path.includes('/settings')) return 'settings';
    return 'scenarios';
  };
  const activeTab = getActiveTab();

  // --- Auth loading state ---
  if (authChecking) {
    return (
      <div className="min-h-screen bg-emerald-50 flex items-center justify-center">
        <div className="flex items-center gap-3 text-emerald-600">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span className="text-sm font-medium">Connecting to Test Runner...</span>
        </div>
      </div>
    );
  }

  // --- Not authenticated → show login ---
  if (!trAuth?.authenticated) {
    return <TestRunnerLoginForm onLogin={setTrAuth} />;
  }

  // Shared link classes
  const baseLinkClasses =
    'flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors';
  const activeLinkClasses = 'bg-emerald-700 text-white';
  const inactiveLinkClasses = 'text-emerald-100 hover:bg-emerald-600 hover:text-white';

  // ---------------------------------------------------------------------------
  // Sidebar content
  // ---------------------------------------------------------------------------
  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-5 border-b border-emerald-600">
        <div>
          <h1 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
            <FlaskConical size={20} />
            Test Runner
          </h1>
          <p className="text-xs text-emerald-200 mt-0.5">Load Driver E2E Scenarios</p>
        </div>
        <button
          className="lg:hidden text-emerald-200 hover:text-white"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close sidebar"
        >
          <X size={20} />
        </button>
      </div>

      {/* Customer selector in sidebar */}
      <div className="px-3 py-3 border-b border-emerald-600">
        <label className="block text-xs font-medium text-emerald-200 mb-1">Customer</label>
        <button
          ref={dropdownTriggerRef}
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="flex items-center gap-2 px-3 py-2 w-full border border-emerald-500 rounded-lg text-sm bg-emerald-700/50 hover:bg-emerald-600/50 text-white text-left"
        >
          <Users className="w-4 h-4 text-emerald-300 flex-shrink-0" />
          <span className="flex-1 truncate text-xs">
            {isNewCustomer
              ? 'New Customer (auto)'
              : selectedCustomer
                ? `${selectedCustomer.customer_id} — ${selectedCustomer.customer_name}`
                : `Customer ${customerId}`
            }
          </span>
          <ChevronDown className="w-3 h-3 text-emerald-300 flex-shrink-0" />
        </button>

        {customerTier && customerId && (
          <span className={`mt-1.5 inline-block px-2 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide ${
            customerTier === 'enterprise' ? 'bg-purple-100 text-purple-800' :
            customerTier === 'professional' ? 'bg-blue-100 text-blue-800' :
            'bg-gray-100 text-gray-600'
          }`}>
            {customerTier}
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/test-runner'}
            onClick={() => setSidebarOpen(false)}
            className={({ isActive }) =>
              `${baseLinkClasses} ${isActive ? activeLinkClasses : inactiveLinkClasses}`
            }
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-emerald-600 space-y-2">
        <div className="px-4 py-2 text-xs text-emerald-200 truncate">
          {trAuth.name} &middot; {trAuth.email}
        </div>
        <button
          onClick={handleLogout}
          className={`${baseLinkClasses} text-emerald-200 hover:bg-red-600 hover:text-white w-full`}
        >
          <LogOut size={18} />
          <span>Sign Out</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar - mobile */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-40 w-64 bg-emerald-800 transform transition-transform duration-200 ease-in-out
          lg:hidden
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {sidebarContent}
      </aside>

      {/* Sidebar - desktop */}
      <aside className="hidden lg:flex lg:flex-col lg:w-64 bg-emerald-800 flex-shrink-0">
        {sidebarContent}
      </aside>

      {/* Customer dropdown portal (rendered outside sidebar to avoid overflow clipping) */}
      {dropdownOpen && dropdownPos && (
        <>
          <div className="fixed inset-0 z-50" onClick={() => setDropdownOpen(false)} />
          <div
            className="fixed bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-80 overflow-auto"
            style={{ top: dropdownPos.top, left: dropdownPos.left, width: dropdownPos.width }}
          >
            {/* New Customer option */}
            <button
              onClick={() => { setCustomerId(''); setDropdownOpen(false); }}
              className={`w-full px-4 py-2.5 text-left text-sm hover:bg-emerald-50 flex items-center gap-3 border-b border-gray-100 ${
                isNewCustomer ? 'bg-emerald-50 text-emerald-700 font-medium' : 'text-gray-700'
              }`}
            >
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 text-emerald-600 text-xs font-bold flex-shrink-0">+</span>
              <div>
                <div>New Customer (auto)</div>
                <div className="text-xs text-gray-400">Onboarding creates a fresh customer</div>
              </div>
            </button>

            {/* Existing customers */}
            {customers.length === 0 && (
              <div className="px-4 py-3 text-sm text-gray-400 italic">No existing customers found</div>
            )}
            {customers.map(c => (
              <button
                key={c.customer_id}
                onClick={() => { setCustomerId(String(c.customer_id)); setDropdownOpen(false); }}
                className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-3 ${
                  String(c.customer_id) === customerId ? 'bg-emerald-50 text-emerald-700 font-medium' : 'text-gray-700'
                }`}
              >
                <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-gray-600 text-xs font-bold flex-shrink-0">
                  {c.customer_id}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="truncate">{c.customer_name}</div>
                  <div className="text-xs text-gray-400">
                    {c.account_count} account{c.account_count !== 1 ? 's' : ''} · {c.vertical}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </>
      )}

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center h-14 px-4 bg-white border-b border-gray-200 flex-shrink-0 lg:px-6">
          <button
            className="lg:hidden mr-3 text-gray-500 hover:text-gray-700"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open sidebar"
          >
            <Menu size={22} />
          </button>
          <FlaskConical className="w-5 h-5 text-emerald-600 mr-2" />
          <span className="text-sm font-medium text-gray-700">Test Runner</span>
          <span className="mx-2 text-gray-300">&middot;</span>
          <span className="text-sm text-gray-500 capitalize">{activeTab}</span>

          {/* Active run indicator */}
          {activeRunId && (
            <span className="ml-auto flex items-center gap-2 text-xs text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              Run: {activeRunId}
            </span>
          )}
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {activeTab === 'scenarios' && (
            <ScenariosTab
              customerId={effectiveCustomerId}
              entitlements={entitlements}
              flags={flags}
              onRunComplete={handleRunComplete}
            />
          )}

          {activeTab === 'platform' && (
            <PlatformStateTab
              customerId={effectiveCustomerId}
              refreshTrigger={refreshTrigger}
            />
          )}

          {activeTab === 'analytics' && (
            <AnalyticsTab
              customerId={effectiveCustomerId}
              entitlements={entitlements}
            />
          )}

          {activeTab === 'dataops' && (
            <DataOpsTab
              customerId={effectiveCustomerId}
              entitlements={entitlements}
              onDataPushed={handleDataPushed}
            />
          )}

          {activeTab === 'console' && (
            <ConsoleTab customerId={effectiveCustomerId} />
          )}

          {activeTab === 'settings' && (
            <SettingsTab
              flags={flags}
              onFlagChange={handleFlagChange}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default TestRunnerLayout;
