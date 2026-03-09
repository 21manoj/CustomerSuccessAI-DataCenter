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
  Shield
} from 'lucide-react';
import { KPIConfigurationSettings } from '../../settings/dc2s/KPIConfigurationSettings';
import { PillarAndKPIWeightManagement } from './PillarAndKPIWeightManagement';
import { KPIRangesTab } from './KPIRangesTab';
import { SystemEventsAndLogManagement } from './SystemEventsAndLogManagement';
import DataQualitySection from './DataQualitySection';
import EntitlementsAdmin from './EntitlementsAdmin';

// ============================================================
// TYPES
// ============================================================

type SubTab = 'weights' | 'kpi-ranges' | 'system-events' | 'general' | 'data' | 'integrations' | 'users' | 'entitlements';

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
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('weights');
  const [pillarWeights, setPillarWeights] = useState<PillarWeight[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
        <p className="text-sm text-gray-500 mt-1">
          Configure platform settings and preferences
        </p>
      </div>

      {/* Sub-tabs */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <nav className="flex space-x-8 px-6 border-b border-gray-200">
          {[
            { id: 'weights' as SubTab, label: 'Pillar and KPI Weight Management', icon: Sliders },
            { id: 'kpi-ranges' as SubTab, label: 'KPI Ranges', icon: Target },
            { id: 'system-events' as SubTab, label: 'System Events and Log Management', icon: Activity },
            { id: 'general' as SubTab, label: 'General Configuration', icon: Settings },
            { id: 'data' as SubTab, label: 'Data Management', icon: Database },
            { id: 'entitlements' as SubTab, label: 'Entitlements', icon: Shield },
            { id: 'integrations' as SubTab, label: 'Integrations', icon: Key },
            { id: 'users' as SubTab, label: 'User Management', icon: Users },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                activeSubTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          ))}
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

          {/* System Events and Log Management */}
          {activeSubTab === 'system-events' && (
            <SystemEventsAndLogManagement />
          )}

          {/* General Configuration - KPI Configuration Settings */}
          {activeSubTab === 'general' && (
            <KPIConfigurationSettings />
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

          {/* Integrations */}
          {activeSubTab === 'integrations' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Integrations</h3>
                <div className="space-y-4">
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      // TODO: Implement API key save functionality
                    }}
                    className="border border-gray-200 rounded-lg p-4"
                  >
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      OpenAI API Key
                    </label>
                    <input
                      type="password"
                      placeholder="sk-..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      autoComplete="off"
                    />
                    <p className="text-xs text-gray-500 mt-2">
                      Used for AI Insights and Signal Analyst
                    </p>
                  </form>
                </div>
              </div>
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
        </div>
      </div>
    </div>
  );
};

export default DCSettings;
