/**
 * Test Runner UI — Tabbed shell for driving load-driver scenarios,
 * viewing platform state, running analytics, and pushing data.
 *
 * Tabs:
 *  1. Scenarios   — Select & run load-driver E2E scenarios
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
} from 'lucide-react';

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

// ---------------------------------------------------------------------------
// Main Component (Tabbed Shell)
// ---------------------------------------------------------------------------

const DCTestRunner: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('scenarios');
  const [customerId, setCustomerId] = useState<string>('500');

  // Entitlements — controls feature visibility across tabs
  const [entitlements, setEntitlements] = useState<Record<string, boolean>>({});
  const [customerTier, setCustomerTier] = useState<string>('starter');

  // Refresh trigger for Platform State tab (incremented after scenario run / data push)
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Fetch entitlements whenever customerId changes
  useEffect(() => {
    const cid = customerId?.trim();
    if (!cid) return;

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

  // Callbacks to trigger Platform State refresh
  const handleRunComplete = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  const handleDataPushed = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <FlaskConical className="h-7 w-7 text-indigo-600" />
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Test Runner</h2>
          <p className="text-sm text-gray-500">Drive load-driver E2E scenarios against CS Pulse via HTTP</p>
        </div>

        {/* Customer ID input — shared across all tabs */}
        <div className="ml-auto flex items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Customer ID:</label>
            <input
              type="number"
              value={customerId}
              onChange={e => setCustomerId(e.target.value)}
              className="w-24 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              min="1"
            />
          </div>

          {customerTier && (
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
          customerId={customerId}
          entitlements={entitlements}
          onRunComplete={handleRunComplete}
        />
      )}

      {activeTab === 'platform' && (
        <PlatformStateTab
          customerId={customerId}
          refreshTrigger={refreshTrigger}
        />
      )}

      {activeTab === 'analytics' && (
        <AnalyticsTab
          customerId={customerId}
          entitlements={entitlements}
        />
      )}

      {activeTab === 'dataops' && (
        <DataOpsTab
          customerId={customerId}
          entitlements={entitlements}
          onDataPushed={handleDataPushed}
        />
      )}
    </div>
  );
};

export default DCTestRunner;
