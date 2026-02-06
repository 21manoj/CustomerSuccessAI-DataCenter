import React, { useState, useEffect } from 'react';
import { useCustomerConfig } from '../../../hooks/useCustomerConfig';
import { PillarWeightsEditor } from './PillarWeightsEditor';
import { KPIWeightsEditor } from './KPIWeightsEditor';
import { KPISelectionPanel } from './KPISelectionPanel';
import { AddCustomKPIModal } from './AddCustomKPIModal';

export const KPIConfigurationSettings: React.FC = () => {
  const {
    config,
    loading,
    error,
    updateConfig,
    updatePillarWeights,
    addCustomKPI,
    deleteCustomKPI
  } = useCustomerConfig();

  const [activeTab, setActiveTab] = useState<'pillars' | 'kpis' | 'weights'>('pillars');
  const [showAddKPIModal, setShowAddKPIModal] = useState(false);
  const [unsavedChanges, setUnsavedChanges] = useState(false);
  const [selectedPillarForKPI, setSelectedPillarForKPI] = useState<string>('AI');

  const [localPillarWeights, setLocalPillarWeights] = useState<{ AI: number; CH: number; DV: number; EX: number; OS: number } | null>(null);
  const [localEnabledKPIs, setLocalEnabledKPIs] = useState<string[]>([]);
  const [localKpiWeights, setLocalKpiWeights] = useState<Record<string, Record<string, number>>>({});

  useEffect(() => {
    if (config) {
      setLocalPillarWeights(config.pillar_weights);
      setLocalEnabledKPIs(config.enabled_kpis || []);
      setLocalKpiWeights(config.kpi_weights && Object.keys(config.kpi_weights).length > 0
        ? JSON.parse(JSON.stringify(config.kpi_weights))
        : {});
    }
  }, [config]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">Loading configuration...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-md">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  if (!config || !localPillarWeights) return null;

  const handleSaveChanges = async () => {
    const result = await updateConfig({
      pillar_weights: localPillarWeights,
      enabled_kpis: localEnabledKPIs,
      kpi_weights: Object.keys(localKpiWeights).length > 0 ? localKpiWeights : undefined
    });

    if (result.success) {
      setUnsavedChanges(false);
      alert('Configuration saved successfully!');
    } else {
      alert(`Error: ${result.error}`);
    }
  };

  // Convert config data for components
  const catalogKPIs = Object.entries(config.kpi_definitions || {})
    .filter(([code]) => !code.startsWith('CUSTOM-'))
    .map(([code, def]) => ({ code, definition: def }));

  const customKPIs = Object.entries(config.kpi_definitions || {})
    .filter(([code]) => code.startsWith('CUSTOM-'))
    .map(([code, def]) => ({ code, definition: def }));

  const handleAddCustomKPI = (pillar?: string) => {
    if (pillar) {
      setSelectedPillarForKPI(pillar);
    }
    setShowAddKPIModal(true);
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">KPI Configuration</h1>
        <p className="text-gray-600 mt-2">
          Customize your health scoring model and KPI tracking
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('pillars')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'pillars'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            1. Pillar Weights
          </button>
          <button
            onClick={() => setActiveTab('kpis')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'kpis'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            2. Select KPIs
          </button>
          <button
            onClick={() => setActiveTab('weights')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'weights'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            3. KPI Weights
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        {activeTab === 'pillars' && (
          <PillarWeightsEditor
            weights={localPillarWeights}
            onChange={(weights) => {
              setLocalPillarWeights(weights);
              setUnsavedChanges(true);
            }}
          />
        )}

        {activeTab === 'kpis' && (
          <KPISelectionPanel
            catalogKPIs={catalogKPIs}
            customKPIs={customKPIs}
            enabledKPIs={localEnabledKPIs}
            onChange={(kpis) => {
              setLocalEnabledKPIs(kpis);
              setUnsavedChanges(true);
            }}
            onAddCustomKPI={(pillar) => handleAddCustomKPI(pillar)}
            onEditCustomKPI={(code) => {
              // TODO: Implement edit modal
              console.log('Edit KPI:', code);
            }}
            onDeleteCustomKPI={async (code) => {
              if (window.confirm(`Delete custom KPI ${code}?`)) {
                const result = await deleteCustomKPI(code);
                if (result.success) {
                  setUnsavedChanges(true);
                }
              }
            }}
          />
        )}

        {activeTab === 'weights' && (
          <KPIWeightsEditor
            kpiWeights={localKpiWeights}
            kpiDefinitions={config.kpi_definitions || {}}
            onChange={(weights) => {
              setLocalKpiWeights(weights);
              setUnsavedChanges(true);
            }}
          />
        )}
      </div>

      {/* Save Button */}
      {unsavedChanges && (
        <div className="fixed bottom-0 left-0 right-0 bg-yellow-50 border-t border-yellow-200 p-4 shadow-lg">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <p className="text-yellow-800">
              ⚠️ You have unsaved changes
            </p>
            <div className="space-x-3">
              <button
                onClick={() => {
                  if (config) {
                    setLocalPillarWeights(config.pillar_weights);
                    setLocalEnabledKPIs(config.enabled_kpis || []);
                    setLocalKpiWeights(config.kpi_weights && Object.keys(config.kpi_weights).length > 0
                      ? JSON.parse(JSON.stringify(config.kpi_weights))
                      : {});
                  }
                  setUnsavedChanges(false);
                }}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Discard
              </button>
              <button
                onClick={handleSaveChanges}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Custom KPI Modal */}
      <AddCustomKPIModal
        isOpen={showAddKPIModal}
        onClose={() => setShowAddKPIModal(false)}
        onSave={async (kpiCode, definition) => {
          const result = await addCustomKPI(kpiCode, definition);
          if (result.success) {
            setUnsavedChanges(true);
          }
          return result;
        }}
        defaultPillar={selectedPillarForKPI}
      />
    </div>
  );
};
