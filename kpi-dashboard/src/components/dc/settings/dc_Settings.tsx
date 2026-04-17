/**
 * Data Center Settings Tab
 * ========================
 * 
 * Configuration and management:
 * - General Configuration (Pillar Weights, KPI Definitions)
 * - Data Management (Upload, Wizard A trigger)
 * - Integrations (API Keys, External Sources)
 * - User Management
 */

import React, { useState, useEffect } from 'react';
import { useSession } from '../../../contexts/SessionContext';
import {
  Settings,
  Database,
  Key,
  Users,
  RefreshCw,
  Save,
  AlertTriangle,
  CheckCircle,
  Target,
  Activity,
  Sliders,
  BarChart2,
  Clock,
  User,
  Shield,
  Lock,
  Network,
  Wand2,
} from 'lucide-react';
import { useEntitlements, getRequiredTier, tierLabel } from '../../../hooks/useEntitlement';
import { KPIConfigurationSettings } from '../../settings/dc2s/KPIConfigurationSettings';
import { PillarAndKPIWeightManagement } from './PillarAndKPIWeightManagement';
import { KPIRangesTab } from './KPIRangesTab';
import { SystemEventsAndLogManagement } from './SystemEventsAndLogManagement';
import DataQualitySection from './DataQualitySection';
import EntitlementsAdmin from './EntitlementsAdmin';
import SecurityKeysPanel from './SecurityKeysPanel';
import ApiKeysTab from '../../settings/ApiKeysTab';
import ContextGraphSettings from './ContextGraphSettings';
import WizardsTab from './WizardsTab';
import HealthThresholdsCard from './HealthThresholdsCard';
import LLMBudgetCard from './LLMBudgetCard';

// ============================================================
// TYPES
// ============================================================

type SubTab = 'weights' | 'kpi-ranges' | 'context-graph' | 'wizards' | 'system-events' | 'general' | 'data' | 'integrations' | 'users' | 'entitlements' | 'security';

interface PillarWeight {
  pillar: string;
  name: string;
  weight: number;
}

// ============================================================
// MAIN COMPONENT
// ============================================================

const DCSettings: React.FC = () => {
  const { session } = useSession();
  const { check: checkEntitlement, tier } = useEntitlements();
  const isStarter = tier === 'starter';
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('weights');
  const [pillarWeights, setPillarWeights] = useState<PillarWeight[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // Quick Setup vs Advanced view toggle (Starter only)
  const [advancedView, setAdvancedView] = useState(false);

  useEffect(() => {
    if (activeSubTab === 'general') {
      fetchPillarWeights();
    }
  }, [activeSubTab]);

  const fetchPillarWeights = async () => {
    try {
      // TODO: Fetch from API: GET /api/admin/wizard-c/weights/current
      const response = await fetch('/api/admin/wizard-c/weights/current');
      if (response.ok) {
        const data = await response.json();
        if (data.weights) {
          const weights: PillarWeight[] = Object.entries(data.weights).map(([key, value]: [string, any]) => ({
            pillar: key,
            name: value.name,
            weight: value.weight,
          }));
          setPillarWeights(weights);
        }
      }
    } catch (err) {
      console.error('Error fetching pillar weights:', err);
      // Use defaults
      setPillarWeights([
        { pillar: 'P1', name: 'Deployment Velocity', weight: 0.15 },
        { pillar: 'P2', name: 'Operational Stability', weight: 0.20 },
        { pillar: 'P3', name: 'AI Workload Performance', weight: 0.25 },
        { pillar: 'P4', name: 'Channel & Partner Health', weight: 0.15 },
        { pillar: 'P5', name: 'Expansion Readiness', weight: 0.25 },
      ]);
    }
  };

  const handleSaveWeights = async () => {
    setSaving(true);
    setSaveMessage(null);
    
    try {
      // TODO: Save to API: POST /api/settings/pillar-weights
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
      setSaveMessage('Pillar weights saved successfully');
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (err) {
      setSaveMessage('Failed to save pillar weights');
    } finally {
      setSaving(false);
    }
  };

  const handleTriggerWizardA = async () => {
    if (!window.confirm('This will regenerate journey timelines from the latest data. This may take 1-2 minutes. Continue?')) {
      return;
    }
    
    try {
      setLoading(true);
      
      // Check if user is authenticated first
      const sessionCheck = await fetch('/api/session/status', {
        method: 'GET',
        credentials: 'include'
      });
      
      if (sessionCheck.ok) {
        const sessionData = await sessionCheck.json();
        if (!sessionData.authenticated) {
          alert('Session expired. Please log in again.');
          window.location.href = '/login';
          return;
        }
      }
      
      const response = await fetch('/api/data/trigger-wizard-a', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        // Handle authentication errors specifically
        if (response.status === 401) {
          alert('Session expired. Please log in again.');
          window.location.href = '/login';
          return;
        }
        throw new Error(data.message || 'Failed to trigger Wizard A');
      }
      
      alert(`✅ ${data.message}\n\nDuration: ${data.duration_seconds}s`);
      // Optionally refresh the page or reload journey data
      window.location.reload();
    } catch (err) {
      console.error('Error triggering Wizard A:', err);
      alert(`Failed to trigger Wizard A: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  // Starter-friendly sub-tab labels
  const subTabLabels: Record<string, string> = isStarter ? {
    'weights': 'Score Weights',
    'kpi-ranges': 'Score Boundaries',
    'context-graph': 'Context Graph',
    'wizards': 'Wizards',
    'system-events': 'System Events',
    'general': 'KPI Definitions',
    'data': 'Data & Upload',
    'entitlements': 'Entitlements',
    'integrations': 'Integrations',
    'users': 'Users',
  } : {};

  const getSubTabLabel = (id: string, defaultLabel: string) =>
    isStarter ? (subTabLabels[id] || defaultLabel) : defaultLabel;

  // ── Starter Quick Setup Card View ──
  if (isStarter && !advancedView) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
            <p className="text-sm text-gray-500 mt-1">Quick setup for your CS Pulse configuration</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Score Boundaries Card */}
          <button
            onClick={() => { setActiveSubTab('kpi-ranges'); setAdvancedView(true); }}
            className="bg-white rounded-xl border border-gray-200 p-6 text-left hover:shadow-md hover:border-blue-200 transition-all group"
          >
            <div className="flex items-center space-x-3 mb-3">
              <div className="bg-blue-50 rounded-lg p-2 group-hover:bg-blue-100 transition-colors">
                <Target className="h-5 w-5 text-blue-600" />
              </div>
              <h3 className="font-semibold text-gray-900">Score Boundaries</h3>
            </div>
            <p className="text-sm text-gray-500 mb-2">Set what counts as healthy, at-risk, or critical</p>
            <span className="inline-flex items-center text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
              <CheckCircle className="h-3 w-3 mr-1" /> Using defaults
            </span>
          </button>

          {/* Score Weights Card */}
          <button
            onClick={() => { setActiveSubTab('weights'); setAdvancedView(true); }}
            className="bg-white rounded-xl border border-gray-200 p-6 text-left hover:shadow-md hover:border-blue-200 transition-all group"
          >
            <div className="flex items-center space-x-3 mb-3">
              <div className="bg-purple-50 rounded-lg p-2 group-hover:bg-purple-100 transition-colors">
                <Sliders className="h-5 w-5 text-purple-600" />
              </div>
              <h3 className="font-semibold text-gray-900">Score Weights</h3>
            </div>
            <p className="text-sm text-gray-500 mb-2">Control how much each area affects health scores</p>
            <span className="inline-flex items-center text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
              <CheckCircle className="h-3 w-3 mr-1" /> Using defaults
            </span>
          </button>

          {/* KPI Definitions Card */}
          <button
            onClick={() => { setActiveSubTab('general'); setAdvancedView(true); }}
            className="bg-white rounded-xl border border-gray-200 p-6 text-left hover:shadow-md hover:border-blue-200 transition-all group"
          >
            <div className="flex items-center space-x-3 mb-3">
              <div className="bg-amber-50 rounded-lg p-2 group-hover:bg-amber-100 transition-colors">
                <Settings className="h-5 w-5 text-amber-600" />
              </div>
              <h3 className="font-semibold text-gray-900">KPI Definitions</h3>
            </div>
            <p className="text-sm text-gray-500 mb-2">View and manage your 10 active KPIs</p>
            <span className="inline-flex items-center text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
              10 KPIs active
            </span>
          </button>

          {/* User Management Card */}
          <button
            onClick={() => { setActiveSubTab('users'); setAdvancedView(true); }}
            className="bg-white rounded-xl border border-gray-200 p-6 text-left hover:shadow-md hover:border-blue-200 transition-all group"
          >
            <div className="flex items-center space-x-3 mb-3">
              <div className="bg-teal-50 rounded-lg p-2 group-hover:bg-teal-100 transition-colors">
                <Users className="h-5 w-5 text-teal-600" />
              </div>
              <h3 className="font-semibold text-gray-900">User Management</h3>
            </div>
            <p className="text-sm text-gray-500 mb-2">Manage team access and permissions</p>
            <span className="inline-flex items-center text-xs text-gray-500 bg-gray-50 px-2 py-0.5 rounded-full">
              1 user
            </span>
          </button>
        </div>

        <button
          onClick={() => setAdvancedView(true)}
          className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
        >
          Switch to Advanced View →
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
          <p className="text-sm text-gray-500 mt-1">
            Configure platform settings and preferences
          </p>
        </div>
        {isStarter && advancedView && (
          <button
            onClick={() => setAdvancedView(false)}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            ← Back to Quick Setup
          </button>
        )}
      </div>

      {/* Sub-tabs */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <nav className="flex space-x-8 px-6 border-b border-gray-200 overflow-x-auto">
          {([
            { id: 'weights' as SubTab, label: 'Weights', icon: Sliders, requiredFeature: undefined as string | undefined, adminOnly: false },
            { id: 'kpi-ranges' as SubTab, label: 'KPI Ranges', icon: Target, requiredFeature: undefined as string | undefined, adminOnly: false },
            { id: 'context-graph' as SubTab, label: 'Context Graph', icon: Network, requiredFeature: undefined as string | undefined, adminOnly: false },
            { id: 'wizards' as SubTab, label: 'Wizards', icon: Wand2, requiredFeature: undefined as string | undefined, adminOnly: false },
            { id: 'system-events' as SubTab, label: 'System Events', icon: Activity, requiredFeature: 'signal_analyst' as string | undefined, adminOnly: false },
            { id: 'general' as SubTab, label: 'General Config', icon: Settings, requiredFeature: undefined as string | undefined, adminOnly: false },
            { id: 'data' as SubTab, label: 'Data Management', icon: Database, requiredFeature: undefined as string | undefined, adminOnly: false },
            { id: 'entitlements' as SubTab, label: 'Entitlements', icon: Shield, requiredFeature: undefined as string | undefined, adminOnly: true },
            { id: 'integrations' as SubTab, label: 'API Keys', icon: Key, requiredFeature: undefined as string | undefined, adminOnly: false },
            { id: 'users' as SubTab, label: 'Users', icon: Users, requiredFeature: undefined as string | undefined, adminOnly: false },
            { id: 'security' as SubTab, label: 'Security & Keys', icon: Shield, requiredFeature: undefined as string | undefined, adminOnly: true },
          ]).map(tab => {
            const featureGated = tab.requiredFeature ? !checkEntitlement(tab.requiredFeature) : false;
            const adminGated = tab.adminOnly && session?.role !== 'super_admin' && session?.role !== 'admin';
            const locked = featureGated || !!adminGated;
            const requiredTierKey = tab.requiredFeature ? getRequiredTier(tab.requiredFeature) : null;
            return (
              <button
                key={tab.id}
                onClick={() => !locked && setActiveSubTab(tab.id)}
                disabled={locked}
                title={locked && requiredTierKey ? `Upgrade to ${tierLabel(requiredTierKey)}` : undefined}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 whitespace-nowrap ${
                  locked
                    ? 'border-transparent text-gray-300 cursor-not-allowed'
                    : activeSubTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                <span>{getSubTabLabel(tab.id, tab.label)}</span>
                {locked && <Lock className="w-3 h-3" />}
              </button>
            );
          })}
        </nav>

        {/* Sub-tab Content */}
        <div className="p-6">
          {/* Pillar and KPI Weight Management */}
          {activeSubTab === 'weights' && (
            <PillarAndKPIWeightManagement />
          )}

          {/* KPI Ranges */}
          {activeSubTab === 'kpi-ranges' && (
            <KPIRangesTab />
          )}

          {/* Context Graph Settings */}
          {activeSubTab === 'context-graph' && (
            <ContextGraphSettings />
          )}

          {/* Wizards */}
          {activeSubTab === 'wizards' && (
            <WizardsTab />
          )}

          {/* System Events and Log Management */}
          {activeSubTab === 'system-events' && (
            <SystemEventsAndLogManagement />
          )}

          {/* General Configuration - KPI Configuration Settings + Health Thresholds + AI Budget */}
          {activeSubTab === 'general' && (
            <div className="space-y-6">
              <HealthThresholdsCard />
              <LLMBudgetCard readOnly />
              <KPIConfigurationSettings />
            </div>
          )}

          {/* Data Management */}
          {activeSubTab === 'data' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Data Management</h3>
                <div className="space-y-4">
                  <button
                    onClick={() => window.location.href = '/dc-dashboard/data-integration'}
                    className="w-full p-4 border border-gray-200 rounded-lg hover:bg-gray-50 text-left flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-3">
                      <Database className="w-5 h-5 text-blue-600" />
                      <div>
                        <p className="font-medium text-gray-900">Upload New CSV Data</p>
                        <p className="text-sm text-gray-500">Upload accounts, KPIs, or signals data</p>
                      </div>
                    </div>
                    <span className="text-gray-400">→</span>
                  </button>

                  <button
                    onClick={handleTriggerWizardA}
                    className="w-full p-4 border border-gray-200 rounded-lg hover:bg-gray-50 text-left flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-3">
                      <RefreshCw className="w-5 h-5 text-purple-600" />
                      <div>
                        <p className="font-medium text-gray-900">Re-run Journey Generator (Wizard A)</p>
                        <p className="text-sm text-gray-500">Regenerate journey timelines from latest data</p>
                      </div>
                    </div>
                    <span className="text-gray-400">→</span>
                  </button>
                </div>
              </div>
              {/* Data Quality – KPI range discrepancies */}
              <div className="border border-gray-200 rounded-lg p-6 bg-white">
                <DataQualitySection />
              </div>
            </div>
          )}

          {/* Entitlements & Feature Flags */}
          {activeSubTab === 'entitlements' && (
            <EntitlementsAdmin />
          )}

          {/* Integrations — API Keys + External Connections */}
          {activeSubTab === 'integrations' && (
            <div className="space-y-8">
              <ApiKeysTab />
            </div>
          )}

          {/* User Management */}
          {activeSubTab === 'users' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">User Management</h3>
                <p className="text-sm text-gray-500">
                  User management features will be implemented here
                </p>
              </div>
            </div>
          )}

          {/* Security & Keys */}
          {activeSubTab === 'security' && (
            <SecurityKeysPanel />
          )}
        </div>
      </div>
    </div>
  );
};

export default DCSettings;
