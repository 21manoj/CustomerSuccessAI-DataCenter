/**
 * Test Runner UI — Tabbed shell for driving load-driver scenarios,
 * viewing platform state, running analytics, and pushing data.
 *
 * Tabs:
 *  1. Scenarios   — Select & run load-driver E2E scenarios + simulation mode
 *  2. Platform State — Live customer/account health/ARR/pillar view
 *  3. Analytics   — ROI, Power-of-1, revenue intelligence, daily actions
 *  4. Data Ops    — Push KPIs, push signals, recalculate scores
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  FlaskConical,
  Database,
  BarChart3,
  Upload,
  ChevronDown,
  Users,
} from 'lucide-react';

import type { CustomerInfo } from './types';
import { testRunnerApi } from './api';
import ScenariosTab from './tabs/ScenariosTab';
import PlatformStateTab from './tabs/PlatformStateTab';
import AnalyticsTab from './tabs/AnalyticsTab';
import DataOpsTab from './tabs/DataOpsTab';

// ---------------------------------------------------------------------------
// Tab definition
// ---------------------------------------------------------------------------

type TabId = 'scenarios' | 'platform' | 'analytics' | 'dataops';

interface TabDef {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const TABS: TabDef[] = [
  { id: 'scenarios', label: 'Scenarios', icon: <FlaskConical className="w-4 h-4" /> },
  { id: 'platform', label: 'Platform State', icon: <Database className="w-4 h-4" /> },
  { id: 'analytics', label: 'Analytics', icon: <BarChart3 className="w-4 h-4" /> },
  { id: 'dataops', label: 'Data Ops', icon: <Upload className="w-4 h-4" /> },
];

const NEW_CUSTOMER_VALUE = '__new__';

// ---------------------------------------------------------------------------
// Main Component (Tabbed Shell)
// ---------------------------------------------------------------------------

const DCTestRunner: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('scenarios');
  // Customer selection: '' = New Customer (auto), or a numeric string for existing
  const [customerId, setCustomerId] = useState<string>('');
  const [customers, setCustomers] = useState<CustomerInfo[]>([]);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  // Entitlements — controls feature visibility across tabs
  const [entitlements, setEntitlements] = useState<Record<string, boolean>>({});
  const [customerTier, setCustomerTier] = useState<string>('starter');

  // Refresh trigger for Platform State tab (incremented after scenario run / data push)
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Fetch existing customers on mount
  const fetchCustomers = useCallback(() => {
    testRunnerApi.getCustomers().then(setCustomers).catch(() => {});
  }, []);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  // Fetch entitlements whenever customerId changes (skip for new customer)
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

  // Callbacks to trigger Platform State refresh + customer list refresh
  const handleRunComplete = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
    fetchCustomers(); // Refresh customer list (may have new customer from onboarding)
  }, [fetchCustomers]);

  const handleDataPushed = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  // Determine the selected customer info for display
  const selectedCustomer = customers.find(c => String(c.customer_id) === customerId);
  const isNewCustomer = !customerId;
  const effectiveCustomerId = customerId || ''; // Empty string = new customer (backend will auto-generate)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <FlaskConical className="h-7 w-7 text-indigo-600" />
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Test Runner</h2>
          <p className="text-sm text-gray-500">Drive load-driver E2E scenarios against CS Pulse via HTTP</p>
        </div>

        {/* Customer dropdown — shared across all tabs */}
        <div className="ml-auto flex items-center gap-3">
          <div className="relative">
            <label className="block text-xs font-medium text-gray-500 mb-0.5">Customer</label>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white hover:bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-w-[280px] text-left"
            >
              <Users className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <span className="flex-1 truncate">
                {isNewCustomer
                  ? 'New Customer (auto)'
                  : selectedCustomer
                    ? `${selectedCustomer.customer_id} — ${selectedCustomer.customer_name}`
                    : `Customer ${customerId}`
                }
              </span>
              {selectedCustomer && (
                <span className="text-xs text-gray-400 flex-shrink-0">
                  {selectedCustomer.account_count} acct{selectedCustomer.account_count !== 1 ? 's' : ''}
                </span>
              )}
              <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
            </button>

            {dropdownOpen && (
              <>
                {/* Click-away backdrop */}
                <div className="fixed inset-0 z-30" onClick={() => setDropdownOpen(false)} />

                <div className="absolute right-0 mt-1 w-[380px] bg-white border border-gray-200 rounded-lg shadow-lg z-40 max-h-80 overflow-auto">
                  {/* New Customer option */}
                  <button
                    onClick={() => {
                      setCustomerId('');
                      setDropdownOpen(false);
                    }}
                    className={`w-full px-4 py-2.5 text-left text-sm hover:bg-blue-50 flex items-center gap-3 border-b border-gray-100 ${
                      isNewCustomer ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'
                    }`}
                  >
                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-600 text-xs font-bold flex-shrink-0">+</span>
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
                      onClick={() => {
                        setCustomerId(String(c.customer_id));
                        setDropdownOpen(false);
                      }}
                      className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-3 ${
                        String(c.customer_id) === customerId ? 'bg-indigo-50 text-indigo-700 font-medium' : 'text-gray-700'
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
          </div>

          {customerTier && customerId && (
            <span className={`px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide ${
              customerTier === 'enterprise' ? 'bg-purple-100 text-purple-800' :
              customerTier === 'professional' ? 'bg-blue-100 text-blue-800' :
              'bg-gray-100 text-gray-600'
            }`}>
              {customerTier}
            </span>
          )}
        </div>
      </div>

      {/* Tab Bar */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-0 -mb-px">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'scenarios' && (
        <ScenariosTab
          customerId={effectiveCustomerId}
          entitlements={entitlements}
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
    </div>
  );
};

export default DCTestRunner;
