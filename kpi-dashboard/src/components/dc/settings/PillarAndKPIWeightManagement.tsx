/**
 * Pillar and KPI Weight Management Tab
 * =====================================
 * 
 * Config-aware weight management:
 * - Display current pillar weights (read-only for now)
 * - Display current KPI weights per pillar (read-only for now)
 * - Show change history trail (last 5 changes with timestamp and username)
 * - Note: Initial weights may be updated by Wizard C after learning
 */

import React, { useState, useEffect, useRef } from 'react';
import { useCustomerConfig } from '../../../hooks/useCustomerConfig';
import { useSession } from '../../../contexts/SessionContext';
import { Sliders, Clock, User, Brain, AlertCircle } from 'lucide-react';
import { DEFAULT_PILLAR_WEIGHTS } from '../../../utils/pillarDefaults';

interface WeightChangeHistory {
  change_id: number;
  changed_at: string;
  changed_by: string;
  change_type: 'pillar_weights' | 'kpi_weights' | 'wizard_c_update';
  pillar?: string;
  kpi_code?: string;
  old_value: number;
  new_value: number;
  source: 'manual' | 'wizard_c' | 'system';
}

const PILLAR_INFO = {
  AI: { name: 'AI Workload Performance', color: 'bg-blue-500', icon: '🖥️' },
  CH: { name: 'Channel & Partner Health', color: 'bg-green-500', icon: '🤝' },
  DV: { name: 'Deployment Velocity', color: 'bg-yellow-500', icon: '🚀' },
  EX: { name: 'Expansion Readiness', color: 'bg-purple-500', icon: '📈' },
  OS: { name: 'Operational Stability', color: 'bg-red-500', icon: '🛡️' }
};

export const PillarAndKPIWeightManagement: React.FC = () => {
  const { config, loading, error } = useCustomerConfig();
  const { session } = useSession();
  const [changeHistory, setChangeHistory] = useState<WeightChangeHistory[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [expandedPillar, setExpandedPillar] = useState<string | null>(null);
  const hasExpandedKpiOnce = useRef(false);

  useEffect(() => {
    fetchChangeHistory();
  }, []);

  // Expand first pillar that has KPIs once so user immediately sees KPI data (not only Pillar)
  useEffect(() => {
    if (hasExpandedKpiOnce.current || !config?.kpi_weights || Object.keys(config.kpi_weights).length === 0) return;
    const firstPillarWithKpis = (Object.keys(PILLAR_INFO) as Array<keyof typeof PILLAR_INFO>).find(
      (code) => (config.kpi_weights?.[code] && Object.keys(config.kpi_weights[code]).length > 0)
    );
    if (firstPillarWithKpis) {
      setExpandedPillar(firstPillarWithKpis);
      hasExpandedKpiOnce.current = true;
    }
  }, [config?.kpi_weights]);

  const fetchChangeHistory = async () => {
    setLoadingHistory(true);
    try {
      const { apiCall } = await import('../../../utils/api');
      const response = await apiCall('/api/dc2s/config/weight-history', {
        method: 'GET'
      }).catch(() => null); // Silently catch network errors

      if (response && response.ok) {
        const data = await response.json();
        setChangeHistory(data.history || []);
      } else {
        // Endpoint returns empty array if no history - that's fine
        setChangeHistory([]);
      }
    } catch (err) {
      // Silently handle errors - use empty array
      console.debug('Weight history endpoint not available, using empty array');
      setChangeHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">Loading weight configuration...</div>
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

  if (!config) {
    return (
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
        <p className="text-yellow-800">No configuration found. Please complete onboarding first.</p>
      </div>
    );
  }

  const pillarWeights = config.pillar_weights || DEFAULT_PILLAR_WEIGHTS;
  const kpiWeights = config.kpi_weights || {};
  const totalPillarWeight = (Object.values(pillarWeights) as number[]).reduce((a, b) => a + b, 0);

  const weightsSource = config.weights_source || 'bootstrap';
  const weightsUpdatedAt = config.weights_updated_at;
  const hasKpiWeights = Object.keys(kpiWeights).length > 0;

  const formatWeightsUpdatedAt = (iso: string | null | undefined) => {
    if (!iso) return null;
    try {
      const d = new Date(iso);
      return isNaN(d.getTime()) ? iso : d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
    } catch {
      return iso;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center">
          <Sliders className="h-5 w-5 mr-2 text-blue-600" />
          Pillar and KPI Weight Management
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Read-only view of current pillar (L2) and KPI (L1) weights from a single source — either bootstrap config or Wizard C learned weights.
        </p>
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
            <span className="text-sm font-medium text-blue-800">
              Source: {weightsSource === 'learned' ? 'Learned (Wizard C)' : 'Bootstrap'}
            </span>
          </div>
          {weightsUpdatedAt != null && (
            <div className="bg-gray-100 border border-gray-200 rounded-lg px-3 py-2">
              <span className="text-sm text-gray-700">
                Last updated: {formatWeightsUpdatedAt(weightsUpdatedAt) ?? weightsUpdatedAt}
              </span>
            </div>
          )}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
            <div className="flex items-start">
              <AlertCircle className="h-4 w-4 text-gray-600 mr-2 mt-0.5 shrink-0" />
              <div className="text-sm text-gray-700">
                <strong>Read-Only.</strong> To override weights, use Settings → General Configuration.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Pillar Weights Section */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h4 className="text-md font-semibold text-gray-900 mb-4">Pillar Weights (L2)</h4>
        <p className="text-sm text-gray-600 mb-4">
          Overall contribution of each pillar to health score calculation
        </p>

        <div className="space-y-4">
          {Object.entries(PILLAR_INFO).map(([code, info]) => {
            const weight = pillarWeights[code as keyof typeof pillarWeights] || 0;
            const percentage = Math.round(weight * 100);

            return (
              <div key={code} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl">{info.icon}</span>
                    <div>
                      <div className="font-medium text-gray-900">{info.name}</div>
                      <div className="text-xs text-gray-500">Pillar Code: {code}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-gray-900">{percentage}%</div>
                    <div className="text-xs text-gray-500">Weight: {weight.toFixed(4)}</div>
                  </div>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full ${info.color} transition-all`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <div className={`mt-4 p-3 rounded-lg ${
          Math.abs(totalPillarWeight - 1) < 0.01 
            ? 'bg-green-50 border border-green-200' 
            : 'bg-yellow-50 border border-yellow-200'
        }`}>
          <div className="flex items-center justify-between">
            <span className="font-medium text-gray-900">Total Pillar Weight:</span>
            <span className={`text-xl font-bold ${
              Math.abs(totalPillarWeight - 1) < 0.01 ? 'text-green-600' : 'text-yellow-600'
            }`}>
              {(totalPillarWeight * 100).toFixed(2)}%
            </span>
          </div>
          {Math.abs(totalPillarWeight - 1) >= 0.01 && (
            <p className="text-sm text-yellow-700 mt-1">
              ⚠️ Pillar weights should sum to 100%
            </p>
          )}
        </div>
      </div>

      {/* KPI Weights Section — always visible so user sees both Pillar and KPI data */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h4 className="text-md font-semibold text-gray-900 mb-4">KPI Weights (L1)</h4>
        <p className="text-sm text-gray-600 mb-4">
          Individual KPI weights within each pillar (from {weightsSource === 'learned' ? 'Wizard C' : 'bootstrap'}).
        </p>

        <div className="space-y-3">
          {Object.entries(PILLAR_INFO).map(([pillarCode, pillarInfo]) => {
            const pillarKPIs = kpiWeights[pillarCode] || {};
            const kpiEntries = Object.entries(pillarKPIs);
            
            if (kpiEntries.length === 0 && !hasKpiWeights) {
              return null;
            }

            return (
              <div key={pillarCode} className="border border-gray-200 rounded-lg">
                <button
                  onClick={() => setExpandedPillar(expandedPillar === pillarCode ? null : pillarCode)}
                  className="w-full flex items-center justify-between p-4 hover:bg-gray-50"
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xl">{pillarInfo.icon}</span>
                    <div>
                      <div className="font-medium text-gray-900">{pillarInfo.name}</div>
                      <div className="text-xs text-gray-500">
                        {kpiEntries.length} KPI{kpiEntries.length !== 1 ? 's' : ''} configured
                      </div>
                    </div>
                  </div>
                  <span className="text-gray-400">
                    {expandedPillar === pillarCode ? '▼' : '▶'}
                  </span>
                </button>

                {expandedPillar === pillarCode && (
                  <div className="px-4 pb-4 border-t bg-gray-50">
                    <div className="space-y-2 mt-3">
                      {kpiEntries.length === 0 ? (
                        <p className="text-sm text-gray-500 py-2">No KPI weights for this pillar.</p>
                      ) : kpiEntries.map(([kpiCode, weight]) => {
                        const percentage = Math.round(weight * 100);
                        return (
                          <div key={kpiCode} className="flex items-center justify-between p-2 bg-white rounded border border-gray-200">
                            <div className="flex-1">
                              <div className="font-medium text-sm text-gray-900">{kpiCode}</div>
                              <div className="text-xs text-gray-500">
                                {config.kpi_definitions?.[kpiCode]?.name || 'KPI Definition'}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-lg font-bold text-gray-900">{percentage}%</div>
                              <div className="text-xs text-gray-500">Weight: {weight.toFixed(4)}</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {!hasKpiWeights && (
          <div className="text-center py-8 text-gray-500">
            <p>No KPI weights loaded yet.</p>
            <p className="text-sm mt-1">Complete onboarding or run Wizard C (Admin Insights → Weight Calibration) to load bootstrap or learned KPI weights.</p>
          </div>
        )}
      </div>

      {/* Change History Section */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h4 className="text-md font-semibold text-gray-900 mb-4 flex items-center">
          <Clock className="h-4 w-4 mr-2 text-gray-600" />
          Change History (Last 5 Changes)
        </h4>
        <p className="text-sm text-gray-600 mb-4">
          Track recent weight changes, including automatic updates from Wizard C learning system
        </p>

        {loadingHistory ? (
          <div className="text-center py-8 text-gray-500">Loading history...</div>
        ) : changeHistory.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <p>No weight changes recorded yet.</p>
            <p className="text-sm mt-1">Change history will appear here when weights are updated.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {changeHistory.slice(0, 5).map((change) => (
              <div
                key={change.change_id}
                className={`p-4 rounded-lg border ${
                  change.source === 'wizard_c'
                    ? 'bg-purple-50 border-purple-200'
                    : change.source === 'manual'
                    ? 'bg-blue-50 border-blue-200'
                    : 'bg-gray-50 border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      {change.source === 'wizard_c' && (
                        <Brain className="h-4 w-4 text-purple-600" />
                      )}
                      {change.source === 'manual' && (
                        <User className="h-4 w-4 text-blue-600" />
                      )}
                      <span className="font-medium text-gray-900">
                        {change.change_type === 'pillar_weights'
                          ? `Pillar Weight: ${change.pillar || 'All'}`
                          : change.change_type === 'kpi_weights'
                          ? `KPI Weight: ${change.kpi_code}`
                          : 'Wizard C Update'}
                      </span>
                      <span className={`px-2 py-0.5 text-xs rounded-full ${
                        change.source === 'wizard_c'
                          ? 'bg-purple-100 text-purple-800'
                          : change.source === 'manual'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {change.source === 'wizard_c' ? 'Wizard C' : change.source === 'manual' ? 'Manual' : 'System'}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600">
                      <div className="flex items-center space-x-4">
                        <span className="flex items-center">
                          <User className="h-3 w-3 mr-1" />
                          {change.changed_by}
                        </span>
                        <span className="flex items-center">
                          <Clock className="h-3 w-3 mr-1" />
                          {new Date(change.changed_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-gray-600">
                      <span className="line-through text-red-600">{change.old_value.toFixed(4)}</span>
                      {' → '}
                      <span className="text-green-600 font-semibold">{change.new_value.toFixed(4)}</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      Δ {((change.new_value - change.old_value) * 100).toFixed(2)}%
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {changeHistory.length > 5 && (
          <div className="mt-4 text-center">
            <button className="text-sm text-blue-600 hover:text-blue-800">
              View All History →
            </button>
          </div>
        )}
      </div>

      {/* Info Box */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="flex items-start">
          <AlertCircle className="h-5 w-5 text-gray-600 mr-2 mt-0.5" />
          <div className="text-sm text-gray-700">
            <p className="font-medium mb-1">About Weight Updates:</p>
            <ul className="list-disc list-inside space-y-1 text-gray-600">
              <li>Initial weights are set during customer onboarding</li>
              <li>Wizard C learning system may automatically adjust weights based on outcomes</li>
              <li>All weight changes are logged with timestamp and source</li>
              <li>Weight editing will be enabled in a future update</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
