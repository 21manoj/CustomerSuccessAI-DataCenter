/**
 * Feature Toggle Admin Panel
 * ==========================
 * Exposes all 12 global feature toggles in the Super Admin Console.
 * Groups by category, shows dependencies, and allows toggling via API.
 *
 * API: GET /api/feature-status, POST /api/feature-toggle
 */

import React, { useState, useEffect, useCallback } from 'react';
import { getApiBaseUrl } from '../../utils/api';

interface FeatureStatus {
  name: string;
  enabled: boolean;
  description?: string;
  version?: string;
  dependencies?: string[];
  sub_toggles?: Record<string, boolean>;
}

interface ToggleGroup {
  label: string;
  color: string;
  features: string[];
}

const TOGGLE_GROUPS: ToggleGroup[] = [
  {
    label: 'Core',
    color: 'blue',
    features: ['FORMAT_DETECTION', 'MULTI_FORMAT_SUPPORT', 'ENHANCED_UPLOAD'],
  },
  {
    label: 'AI & Analysis',
    color: 'purple',
    features: ['EVENT_DRIVEN_RAG', 'CONTINUOUS_LEARNING', 'SIGNAL_ENGINE', 'ASK_AI_V2'],
  },
  {
    label: 'Platform',
    color: 'green',
    features: ['TEMPORAL_ANALYSIS', 'REAL_TIME_INGESTION'],
  },
  {
    label: 'Revenue & Integration',
    color: 'amber',
    features: ['REVENUE_INTELLIGENCE', 'CONTEXT_GRAPH', 'MCP_SERVER'],
  },
];

const FEATURE_DESCRIPTIONS: Record<string, string> = {
  FORMAT_DETECTION: 'Auto-detect and validate file formats during upload',
  EVENT_DRIVEN_RAG: 'Automatic RAG index rebuilds on data changes',
  CONTINUOUS_LEARNING: 'Continuous model learning and weight updates',
  REAL_TIME_INGESTION: 'Real-time data ingestion APIs',
  ENHANCED_UPLOAD: 'Enhanced upload with AI-assisted format detection',
  TEMPORAL_ANALYSIS: 'Temporal analysis and historical trend computation',
  MULTI_FORMAT_SUPPORT: 'Support for multiple file formats (CSV, Excel, JSON)',
  REVENUE_INTELLIGENCE: 'Power of 1 ROI engine and revenue intelligence',
  CONTEXT_GRAPH: 'Context graph knowledge graph with causal chains',
  MCP_SERVER: 'Expose CS Pulse as MCP tool provider for Claude.ai',
  SIGNAL_ENGINE: 'QSIM Signal Engine with LLM enrichment',
  ASK_AI_V2: 'Claude-powered AI assistant with tool use and persona awareness',
};

const FEATURE_DEPS: Record<string, string[]> = {
  EVENT_DRIVEN_RAG: ['REAL_TIME_INGESTION'],
  CONTINUOUS_LEARNING: ['EVENT_DRIVEN_RAG'],
  ENHANCED_UPLOAD: ['FORMAT_DETECTION'],
  MULTI_FORMAT_SUPPORT: ['FORMAT_DETECTION'],
  SIGNAL_ENGINE: ['CONTEXT_GRAPH'],
};

const groupColor = (color: string, active: boolean) => {
  const map: Record<string, string> = {
    blue: active ? 'bg-blue-500/20 text-blue-300 border-blue-500/30' : 'bg-gray-800 text-gray-500 border-gray-700',
    purple: active ? 'bg-purple-500/20 text-purple-300 border-purple-500/30' : 'bg-gray-800 text-gray-500 border-gray-700',
    green: active ? 'bg-green-500/20 text-green-300 border-green-500/30' : 'bg-gray-800 text-gray-500 border-gray-700',
    amber: active ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' : 'bg-gray-800 text-gray-500 border-gray-700',
  };
  return map[color] || map.blue;
};

const FeatureTogglePanel: React.FC = () => {
  const [features, setFeatures] = useState<Record<string, FeatureStatus>>({});
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const loadFeatures = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`${getApiBaseUrl()}/api/feature-status`, { credentials: 'include' });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      // API may return { features: {...} } or flat object
      const featureMap: Record<string, FeatureStatus> = {};
      const raw = data.features || data;
      if (typeof raw === 'object') {
        for (const [name, val] of Object.entries(raw)) {
          if (typeof val === 'object' && val !== null) {
            featureMap[name] = { name, ...(val as any) };
          } else if (typeof val === 'boolean') {
            featureMap[name] = { name, enabled: val };
          }
        }
      }
      setFeatures(featureMap);
    } catch (e: any) {
      setError(`Failed to load feature toggles: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadFeatures(); }, [loadFeatures]);

  const toggleFeature = async (featureName: string, enabled: boolean) => {
    setToggling(featureName);
    setError('');
    setSuccessMsg('');
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/feature-toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ feature: featureName, enabled }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || data.message || `${res.status}`);
      }
      setFeatures((prev) => ({
        ...prev,
        [featureName]: { ...prev[featureName], name: featureName, enabled },
      }));
      setSuccessMsg(`${featureName} ${enabled ? 'enabled' : 'disabled'}`);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (e: any) {
      setError(`Failed to toggle ${featureName}: ${e.message}`);
    } finally {
      setToggling(null);
    }
  };

  const isEnabled = (name: string) => features[name]?.enabled ?? false;

  const hasMissingDeps = (name: string): string[] => {
    const deps = FEATURE_DEPS[name] || [];
    return deps.filter((d) => !isEnabled(d));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin h-6 w-6 border-2 border-blue-400 border-t-transparent rounded-full" />
        <span className="ml-3 text-gray-400">Loading feature toggles...</span>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">Feature Toggles</h2>
          <p className="text-sm text-gray-400 mt-1">
            {Object.values(features).filter((f) => f.enabled).length} of {Object.keys(features).length} features enabled
          </p>
        </div>
        <button
          onClick={loadFeatures}
          className="px-3 py-1.5 bg-gray-800 text-gray-300 rounded-lg text-sm hover:bg-gray-700"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 px-4 py-2 bg-red-900/30 border border-red-700/50 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}
      {successMsg && (
        <div className="mb-4 px-4 py-2 bg-green-900/30 border border-green-700/50 rounded-lg text-green-300 text-sm">
          {successMsg}
        </div>
      )}

      <div className="space-y-6">
        {TOGGLE_GROUPS.map((group) => {
          const enabledCount = group.features.filter((f) => isEnabled(f)).length;
          return (
            <div key={group.label} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              {/* Group header */}
              <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${groupColor(group.color, enabledCount > 0)}`}>
                    {group.label}
                  </span>
                  <span className="text-xs text-gray-500">
                    {enabledCount}/{group.features.length} enabled
                  </span>
                </div>
              </div>

              {/* Feature rows */}
              <div className="divide-y divide-gray-800/50">
                {group.features.map((featureName) => {
                  const enabled = isEnabled(featureName);
                  const missingDeps = hasMissingDeps(featureName);
                  const deps = FEATURE_DEPS[featureName];
                  const isToggling = toggling === featureName;

                  return (
                    <div
                      key={featureName}
                      className="px-4 py-3 flex items-center justify-between hover:bg-gray-800/30 transition-colors"
                    >
                      <div className="flex-1 min-w-0 mr-4">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-mono text-gray-200">{featureName}</span>
                          {missingDeps.length > 0 && (
                            <span className="px-1.5 py-0.5 bg-yellow-900/30 border border-yellow-700/40 rounded text-[10px] text-yellow-400">
                              Missing deps
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {FEATURE_DESCRIPTIONS[featureName] || features[featureName]?.description || ''}
                        </p>
                        {deps && deps.length > 0 && (
                          <p className="text-[10px] text-gray-600 mt-0.5">
                            Requires: {deps.map((d) => (
                              <span key={d} className={isEnabled(d) ? 'text-green-600' : 'text-red-500'}>
                                {d}{' '}
                              </span>
                            ))}
                          </p>
                        )}
                      </div>

                      {/* Toggle switch */}
                      <button
                        onClick={() => toggleFeature(featureName, !enabled)}
                        disabled={isToggling}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 ${
                          enabled ? 'bg-blue-600' : 'bg-gray-700'
                        } ${isToggling ? 'opacity-50 cursor-wait' : 'cursor-pointer'}`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            enabled ? 'translate-x-6' : 'translate-x-1'
                          }`}
                        />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Context Graph Sub-Toggles */}
      {isEnabled('CONTEXT_GRAPH') && features['CONTEXT_GRAPH']?.sub_toggles && (
        <div className="mt-6 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800">
            <span className="text-sm font-medium text-gray-200">Context Graph Sub-Toggles</span>
          </div>
          <div className="divide-y divide-gray-800/50">
            {Object.entries(features['CONTEXT_GRAPH'].sub_toggles || {}).map(([name, enabled]) => (
              <div key={name} className="px-4 py-2.5 flex items-center justify-between hover:bg-gray-800/30">
                <span className="text-sm text-gray-300 font-mono">{name}</span>
                <span className={`px-2 py-0.5 rounded text-xs ${enabled ? 'bg-green-900/40 text-green-300' : 'bg-gray-800 text-gray-500'}`}>
                  {enabled ? 'ON' : 'OFF'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FeatureTogglePanel;
