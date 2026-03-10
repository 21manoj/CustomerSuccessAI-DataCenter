/**
 * DCRevenueIntelligence.tsx
 * ========================
 * Main container for the Revenue Intelligence UI.
 * Shows sub-tabs (Graph Overview, Stakeholder Map, Story Arcs, Benchmarks)
 * conditionally based on context graph feature toggles.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { RefreshCw, AlertTriangle, TrendingUp, ChevronDown } from 'lucide-react';
import { useSession } from '../../../contexts/SessionContext';
import { useContextGraphToggle } from '../../../hooks/useContextGraphToggle';
import { apiCall } from '../../../utils/api';
import GraphOverview from './GraphOverview';
import StakeholderMap from './StakeholderMap';
import StoryArcsView from './StoryArcsView';
import BenchmarksView from './BenchmarksView';
import ContextGraphExplorer from './ContextGraphExplorer';

interface Account {
  account_id: number;
  account_name: string;
  health_score?: number;
  revenue?: number;
}

type SubTab = 'graph' | 'explorer' | 'stakeholders' | 'arcs' | 'benchmarks';

const DCRevenueIntelligence: React.FC = () => {
  const { session } = useSession();
  const { active, subToggles, loading: toggleLoading, error: toggleError } = useContextGraphToggle();

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<SubTab>('graph');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch accounts
  useEffect(() => {
    if (!active) return;

    let cancelled = false;
    setLoading(true);

    apiCall('/api/accounts')
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to fetch accounts: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (cancelled) return;
        const accts: Account[] = data.accounts || data || [];
        setAccounts(accts);
        if (accts.length > 0 && !selectedAccountId) {
          setSelectedAccountId(accts[0].account_id);
        }
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message);
        setLoading(false);
      });

    return () => { cancelled = true; };
  }, [active]); // eslint-disable-line react-hooks/exhaustive-deps

  // Build visible tabs
  const visibleTabs = useMemo(() => {
    const tabs: { key: SubTab; label: string }[] = [
      { key: 'graph', label: 'Graph Overview' },
      { key: 'explorer', label: 'Graph Explorer' },
    ];
    if (subToggles.stakeholder_tracking) {
      tabs.push({ key: 'stakeholders', label: 'Stakeholder Map' });
    }
    if (subToggles.story_arcs) {
      tabs.push({ key: 'arcs', label: 'Story Arcs' });
    }
    if (subToggles.industry_benchmarks) {
      tabs.push({ key: 'benchmarks', label: 'Benchmarks' });
    }
    return tabs;
  }, [subToggles]);

  // Ensure active tab is valid
  useEffect(() => {
    const tabKeys = visibleTabs.map((t) => t.key);
    if (!tabKeys.includes(activeTab)) {
      setActiveTab('graph');
    }
  }, [visibleTabs, activeTab]);

  // Toggle loading
  if (toggleLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  // Feature not enabled
  if (!active) {
    return (
      <div className="text-center py-16">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 mb-4">
          <TrendingUp className="w-8 h-8 text-gray-400" />
        </div>
        <h2 className="text-xl font-semibold text-gray-700 mb-2">Context Graph is not enabled</h2>
        <p className="text-gray-500 max-w-md mx-auto">
          Revenue Intelligence requires the Context Graph feature to be enabled.
          Contact your administrator to activate it in Settings.
        </p>
        {toggleError && (
          <p className="text-sm text-red-500 mt-4">Toggle check error: {toggleError}</p>
        )}
      </div>
    );
  }

  // Accounts loading
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-8 h-8 text-yellow-500 mx-auto mb-2" />
        <p className="text-gray-600">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Revenue Intelligence</h1>
          <p className="text-sm text-gray-500 mt-1">
            Context graph insights across signals, decisions, stakeholders, and outcomes
          </p>
        </div>

        {/* Account selector */}
        <div className="relative">
          <select
            value={selectedAccountId ?? ''}
            onChange={(e) => setSelectedAccountId(Number(e.target.value))}
            className="appearance-none bg-white border border-gray-300 rounded-lg px-4 py-2.5 pr-10 text-sm font-medium text-gray-700 shadow-sm hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-w-[240px]"
          >
            {accounts.map((acct) => (
              <option key={acct.account_id} value={acct.account_id}>
                {acct.account_name} (ID: {acct.account_id})
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
      </div>

      {/* Sub-tab buttons */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-1" aria-label="Revenue Intelligence tabs">
          {visibleTabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${
                activeTab === tab.key
                  ? 'bg-white text-blue-600 border border-b-0 border-gray-200 -mb-px'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div className="min-h-[400px]">
        {activeTab === 'graph' && selectedAccountId && (
          <GraphOverview accountId={selectedAccountId} />
        )}
        {activeTab === 'explorer' && (
          <div className="rounded-lg overflow-hidden border border-gray-200" style={{ height: '80vh' }}>
            <ContextGraphExplorer />
          </div>
        )}
        {activeTab === 'stakeholders' && selectedAccountId && (
          <StakeholderMap accountId={selectedAccountId} />
        )}
        {activeTab === 'arcs' && (
          <StoryArcsView accountId={selectedAccountId ?? undefined} />
        )}
        {activeTab === 'benchmarks' && selectedAccountId && (
          <BenchmarksView accountId={selectedAccountId} />
        )}
      </div>
    </div>
  );
};

export default DCRevenueIntelligence;
