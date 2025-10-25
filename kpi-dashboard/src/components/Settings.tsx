import React, { useState, useEffect } from 'react';

interface FeatureToggle {
  enabled: boolean;
  description: string;
  version: string;
  dependencies: string[];
  environment_required: string;
}

interface FeatureStatus {
  [key: string]: FeatureToggle;
}

interface SettingsProps {
  onClose: () => void;
}

const Settings: React.FC<SettingsProps> = ({ onClose }) => {
  const [featureStatus, setFeatureStatus] = useState<FeatureStatus>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // MCP integration state
  const [mcpEnabled, setMcpEnabled] = useState(false);
  const [mcpConfig, setMcpConfig] = useState({
    salesforce: false,
    servicenow: false,
    surveys: false
  });
  const [mcpStatus, setMcpStatus] = useState<any>(null);
  
  // Playbook trigger settings state
  const [triggerSettings, setTriggerSettings] = useState<Record<string, any>>({
    voc: {
      nps_threshold: 10,
      csat_threshold: 3.6,
      churn_risk_threshold: 0.30,
      health_score_drop_threshold: 10,
      churn_mentions_threshold: 2,
      auto_trigger_enabled: false
    },
    activation: {
      adoption_index_threshold: 60,
      active_users_threshold: 50,
      dau_mau_threshold: 0.25,
      unused_feature_check: true,
      auto_trigger_enabled: false
    },
    sla: {
      sla_breach_threshold: 5,
      response_time_multiplier: 2.0,
      escalation_trend: 'increasing',
      reopen_rate_threshold: 0.20,
      auto_trigger_enabled: false
    },
    renewal: {
      renewal_window_days: 90,
      health_score_threshold: 70,
      engagement_trend: 'declining',
      budget_risk: true,
      auto_trigger_enabled: false
    },
    expansion: {
      health_score_threshold: 80,
      adoption_threshold: 85,
      usage_limit_percentage: 0.80,
      budget_window: 'Q1_Q4',
      auto_trigger_enabled: false
    }
  });

  useEffect(() => {
    fetchFeatureStatus();
    fetchTriggerSettings();
    fetchMCPStatus();
  }, []);

  const fetchFeatureStatus = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/feature-status');
      if (!response.ok) {
        throw new Error('Failed to fetch feature status');
      }
      const data = await response.json();
      setFeatureStatus(data.features);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch feature status');
    } finally {
      setLoading(false);
    }
  };

  const toggleFeature = async (featureName: string, enabled: boolean) => {
    try {
      setSaving(true);
      setError(null);
      
      // Update local state immediately for better UX
      setFeatureStatus(prev => ({
        ...prev,
        [featureName]: {
          ...prev[featureName],
          enabled
        }
      }));

      // Send update to backend
      const response = await fetch('/api/feature-toggle', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          feature: featureName,
          enabled
        })
      });

      if (!response.ok) {
        throw new Error('Failed to update feature toggle');
      }

      setSuccess(`Feature "${featureName}" ${enabled ? 'enabled' : 'disabled'} successfully`);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update feature toggle');
      // Revert local state on error
      setFeatureStatus(prev => ({
        ...prev,
        [featureName]: {
          ...prev[featureName],
          enabled: !enabled
        }
      }));
    } finally {
      setSaving(false);
    }
  };

  const refreshData = async (dataType: string) => {
    try {
      setSaving(true);
      const response = await fetch(`/api/refresh-data/${dataType}`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error(`Failed to refresh ${dataType}`);
      }
      
      setSuccess(`${dataType} refreshed successfully`);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to refresh ${dataType}`);
    } finally {
      setSaving(false);
    }
  };

  const getFeatureIcon = (featureName: string) => {
    const icons: { [key: string]: string } = {
      'format_detection': '🔍',
      'event_driven_rag': '🔄',
      'continuous_learning': '🧠',
      'real_time_ingestion': '⚡',
      'enhanced_upload': '📤',
      'temporal_analysis': '📊',
      'multi_format_support': '📁'
    };
    return icons[featureName] || '⚙️';
  };

  const getFeatureColor = (enabled: boolean) => {
    return enabled ? 'text-green-600' : 'text-gray-400';
  };

  const getToggleColor = (enabled: boolean) => {
    return enabled ? 'bg-green-500' : 'bg-gray-300';
  };

  // Playbook trigger management functions
  const fetchTriggerSettings = async () => {
    try {
      const response = await fetch('/api/playbook-triggers');
      if (response.ok) {
        const data = await response.json();
        console.log('Fetched trigger settings:', data.triggers);
        
        // Merge saved settings with defaults
        const savedSettings = data.triggers || {};
        const mergedSettings = {
          voc: {
            nps_threshold: 10,
            csat_threshold: 3.6,
            churn_risk_threshold: 0.30,
            health_score_drop_threshold: 10,
            churn_mentions_threshold: 2,
            auto_trigger_enabled: false,
            ...savedSettings.voc?.trigger_config
          },
          activation: {
            adoption_index_threshold: 60,
            active_users_threshold: 50,
            dau_mau_threshold: 0.25,
            unused_feature_check: true,
            auto_trigger_enabled: false,
            ...savedSettings.activation?.trigger_config
          },
          sla: {
            sla_breach_threshold: 5,
            response_time_multiplier: 2.0,
            escalation_trend: 'increasing',
            reopen_rate_threshold: 0.20,
            auto_trigger_enabled: false,
            ...savedSettings.sla?.trigger_config
          },
          renewal: {
            renewal_window_days: 90,
            health_score_threshold: 70,
            engagement_trend: 'declining',
            budget_risk: true,
            auto_trigger_enabled: false,
            ...savedSettings.renewal?.trigger_config
          },
          expansion: {
            health_score_threshold: 80,
            adoption_threshold: 85,
            usage_limit_percentage: 0.80,
            budget_window: 'Q1_Q4',
            auto_trigger_enabled: false,
            ...savedSettings.expansion?.trigger_config
          }
        };
        
        setTriggerSettings(mergedSettings);
        console.log('Merged trigger settings:', mergedSettings);
      }
    } catch (err) {
      console.error('Failed to fetch trigger settings:', err);
    }
  };

  const handleTriggerChange = (playbookType: string, field: string, value: any) => {
    setTriggerSettings(prev => ({
      ...prev,
      [playbookType]: {
        ...prev[playbookType],
        [field]: value
      }
    }));
  };

  const saveTriggerSettings = async (playbookType: string) => {
    try {
      setSaving(true);
      const response = await fetch('/api/playbook-triggers', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          playbook_type: playbookType,
          trigger_config: triggerSettings[playbookType]
        })
      });

      if (response.ok) {
        setSuccess(`${playbookType} trigger settings saved successfully`);
        setTimeout(() => setSuccess(null), 3000);
      } else {
        throw new Error('Failed to save trigger settings');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save trigger settings');
    } finally {
      setSaving(false);
    }
  };

  const testTriggerConditions = async (playbookType: string) => {
    try {
      setSaving(true);
      const response = await fetch('/api/playbook-triggers/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          playbook_type: playbookType,
          triggers: triggerSettings[playbookType]
        })
      });

      if (response.ok) {
        const data = await response.json();
        setSuccess(`Trigger test completed: ${data.message}`);
        setTimeout(() => setSuccess(null), 5000);
      } else {
        throw new Error('Failed to test trigger conditions');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to test trigger conditions');
    } finally {
      setSaving(false);
    }
  };

  // ============================================
  // MCP Integration Functions
  // ============================================

  const fetchMCPStatus = async () => {
    try {
      const customerId = sessionStorage.getItem('customer_id') || '1';
      const response = await fetch('/api/features/mcp', {
        headers: {
          'X-Customer-ID': customerId
        }
      });

      if (response.ok) {
        const data = await response.json();
        setMcpEnabled(data.enabled);
        setMcpConfig({
          salesforce: data.salesforce_enabled,
          servicenow: data.servicenow_enabled,
          surveys: data.surveys_enabled
        });
        setMcpStatus(data);
      }
    } catch (err) {
      console.error('Failed to fetch MCP status:', err);
    }
  };

  const toggleMCP = async (enabled: boolean) => {
    try {
      setSaving(true);
      const customerId = sessionStorage.getItem('customer_id') || '1';
      
      // When enabling MCP, automatically enable all systems
      // When disabling MCP, disable all systems
      const newConfig = enabled 
        ? { salesforce: true, servicenow: true, surveys: true }  // Auto-enable all
        : { salesforce: false, servicenow: false, surveys: false };  // Disable all
      
      const response = await fetch('/api/features/mcp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Customer-ID': customerId
        },
        body: JSON.stringify({
          enabled: enabled,
          salesforce_enabled: newConfig.salesforce,
          servicenow_enabled: newConfig.servicenow,
          surveys_enabled: newConfig.surveys
        })
      });

      if (response.ok) {
        setMcpEnabled(enabled);
        setMcpConfig(newConfig);  // Update local state
        setSuccess(`MCP Integration ${enabled ? 'ENABLED' : 'DISABLED'} successfully! ${enabled ? 'All systems enabled.' : ''}`);
        setTimeout(() => setSuccess(null), 5000);
      } else {
        throw new Error('Failed to toggle MCP');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle MCP');
    } finally {
      setSaving(false);
    }
  };

  const toggleMCPSystem = async (system: string, enabled: boolean) => {
    const newConfig = { ...mcpConfig, [system]: enabled };
    setMcpConfig(newConfig);

    if (mcpEnabled) {
      // Save immediately if MCP is enabled
      try {
        setSaving(true);
        const customerId = sessionStorage.getItem('customer_id') || '1';
        
        const response = await fetch('/api/features/mcp', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Customer-ID': customerId
          },
          body: JSON.stringify({
            enabled: mcpEnabled,
            salesforce_enabled: newConfig.salesforce,
            servicenow_enabled: newConfig.servicenow,
            surveys_enabled: newConfig.surveys
          })
        });

        if (response.ok) {
          setSuccess(`${system} ${enabled ? 'enabled' : 'disabled'} successfully!`);
          setTimeout(() => setSuccess(null), 3000);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to update system');
      } finally {
        setSaving(false);
      }
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Loading settings...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-900">System Settings</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Status Messages */}
        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}
        {success && (
          <div className="mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded">
            {success}
          </div>
        )}

        {/* Feature Toggles Section */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            🔧 Feature Toggles
            <span className="ml-2 text-sm text-gray-500">
              (Changes require server restart)
            </span>
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(featureStatus).map(([featureName, config]) => (
              <div key={featureName} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center">
                    <span className="text-2xl mr-3">
                      {getFeatureIcon(featureName)}
                    </span>
                    <div>
                      <h4 className="font-medium text-gray-900 capitalize">
                        {featureName.replace(/_/g, ' ')}
                      </h4>
                      <p className="text-sm text-gray-500">
                        v{config.version} • {config.environment_required}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => toggleFeature(featureName, !config.enabled)}
                    disabled={saving}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      config.enabled ? 'bg-green-500' : 'bg-gray-300'
                    } ${saving ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        config.enabled ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
                
                <p className="text-sm text-gray-600 mb-2">
                  {config.description}
                </p>
                
                {config.dependencies.length > 0 && (
                  <div className="text-xs text-gray-500">
                    <strong>Dependencies:</strong> {config.dependencies.join(', ')}
                  </div>
                )}
                
                <div className={`text-xs font-medium ${
                  config.enabled ? 'text-green-600' : 'text-gray-400'
                }`}>
                  {config.enabled ? '✅ Enabled' : '❌ Disabled'}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* System Actions Section */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            🔄 System Actions
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => refreshData('rag_knowledge_base')}
              disabled={saving}
              className="flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              ) : (
                <span className="mr-2">🧠</span>
              )}
              Rebuild RAG Knowledge Base
            </button>
            
            <button
              onClick={() => refreshData('health_scores')}
              disabled={saving}
              className="flex items-center justify-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              ) : (
                <span className="mr-2">📊</span>
              )}
              Refresh Health Scores
            </button>
            
            <button
              onClick={() => refreshData('customer_data')}
              disabled={saving}
              className="flex items-center justify-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              ) : (
                <span className="mr-2">👥</span>
              )}
              Refresh Customer Data
            </button>
          </div>
        </div>

        {/* System Status Section */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            📊 System Status
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-2">Feature Status</h4>
              <div className="text-sm text-gray-600">
                <div>Total Features: {Object.keys(featureStatus).length}</div>
                <div>Enabled: {Object.values(featureStatus).filter(f => f.enabled).length}</div>
                <div>Disabled: {Object.values(featureStatus).filter(f => !f.enabled).length}</div>
              </div>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="font-medium text-gray-900 mb-2">System Health</h4>
              <div className="text-sm text-gray-600">
                <div className="flex items-center">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                  RAG System: Active
                </div>
                <div className="flex items-center">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                  Database: Connected
                </div>
                <div className="flex items-center">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                  API: Responding
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* KPI Reference Ranges Section */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            📊 KPI Reference Ranges
          </h3>
          
          <div className="bg-gray-50 rounded-lg p-4 mb-4">
            <p className="text-sm text-gray-600 mb-4">
              Configure reference ranges for KPI health scoring. Each KPI is evaluated against these ranges to determine health status:
            </p>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• <strong>Critical Range</strong>: Values indicating immediate attention needed</li>
              <li>• <strong>Risk Range</strong>: Values indicating potential issues</li>
              <li>• <strong>Healthy Range</strong>: Values indicating good performance</li>
            </ul>
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex items-center">
              <div className="text-yellow-600 mr-2">⚠️</div>
              <div>
                <p className="text-sm text-yellow-800">
                  <strong>Note:</strong> KPI reference ranges are managed in the main dashboard under the "Account Health" tab. 
                  Click "Load KPI Reference Ranges" to view and edit calculation details.
                </p>
                <p className="text-xs text-yellow-700 mt-1">
                  Changes to reference ranges automatically update health scores across all accounts.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* MCP Integration Section */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            🔌 External System Integration (MCP)
          </h3>
          
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-lg p-6 mb-4">
            <div className="flex items-start">
              <div className="text-3xl mr-4">✨</div>
              <div className="flex-1">
                <h4 className="text-lg font-semibold text-blue-900 mb-2">AI-Powered Real-Time Integration</h4>
                <p className="text-sm text-blue-800 mb-3">
                  <strong>Beta Feature:</strong> Connect your Customer Success platform to external systems for real-time AI insights.
                  When enabled, AI queries automatically include live data from:
                </p>
                <ul className="text-sm text-blue-800 space-y-1 mb-3">
                  <li>• <strong>Salesforce CRM:</strong> ARR, contracts, opportunities, account data</li>
                  <li>• <strong>ServiceNow ITSM:</strong> Support tickets, SLA breaches, escalations</li>
                  <li>• <strong>Survey Platform:</strong> NPS, CSAT, VoC interviews, CSM assessments</li>
                </ul>
                <div className="bg-blue-100 rounded p-3 mt-3">
                  <p className="text-xs text-blue-900">
                    <strong>⚡ Performance:</strong> Queries enhanced with real-time data typically take 2-5 seconds.
                    <br />
                    <strong>🔄 Rollback:</strong> Toggle OFF anytime for instant rollback to local data only.
                    <br />
                    <strong>🛡️ Safety:</strong> Automatic fallback to local data if external systems unavailable.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Master MCP Toggle */}
          <div className="bg-white border-2 border-gray-200 rounded-lg p-6 mb-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex-1">
                <label className="text-base font-semibold text-gray-900 flex items-center">
                  <span className="text-2xl mr-2">🚀</span>
                  Enable MCP Integration
                </label>
                <p className="text-sm text-gray-600 mt-1">
                  Master switch to enable/disable all external system connections
                </p>
              </div>
              <button
                onClick={() => toggleMCP(!mcpEnabled)}
                disabled={saving}
                className={`relative inline-flex h-8 w-16 items-center rounded-full transition-all duration-300 ${
                  mcpEnabled ? 'bg-gradient-to-r from-green-500 to-green-600 shadow-lg' : 'bg-gray-300'
                } ${saving ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:shadow-xl'}`}
              >
                <span
                  className={`inline-block h-6 w-6 transform rounded-full bg-white shadow-md transition-transform duration-300 ${
                    mcpEnabled ? 'translate-x-9' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Status Indicator */}
            <div className={`p-3 rounded-lg ${mcpEnabled ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'}`}>
              <div className="flex items-center">
                <div className={`h-3 w-3 rounded-full mr-2 ${mcpEnabled ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
                <span className="text-sm font-medium text-gray-700">
                  {mcpEnabled ? '✅ MCP Integration Active - AI queries enhanced with real-time data' : '⚪ Using Local Database Only'}
                </span>
              </div>
            </div>
          </div>

          {/* Individual System Toggles */}
          {mcpEnabled && (
            <div className="bg-white border-2 border-blue-200 rounded-lg p-6">
              <h4 className="text-base font-semibold text-gray-900 mb-4">Connected Systems</h4>
              <p className="text-sm text-gray-600 mb-4">
                Select which external systems to include in AI queries. You can enable/disable individual systems independently.
              </p>
              
              <div className="space-y-4">
                {/* Salesforce Toggle */}
                <div className="flex items-start justify-between p-4 bg-gradient-to-r from-blue-50 to-blue-50 rounded-lg border border-blue-200">
                  <div className="flex-1">
                    <div className="flex items-center mb-1">
                      <span className="text-xl mr-2">☁️</span>
                      <span className="text-sm font-semibold text-gray-900">Salesforce CRM</span>
                      <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${mcpConfig.salesforce ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                        {mcpConfig.salesforce ? 'Connected' : 'Disconnected'}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 ml-7">
                      Provides: Account details, ARR, contracts, opportunities, engagement history
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={mcpConfig.salesforce}
                    onChange={(e) => toggleMCPSystem('salesforce', e.target.checked)}
                    disabled={saving}
                    className="h-5 w-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 cursor-pointer"
                  />
                </div>

                {/* ServiceNow Toggle */}
                <div className="flex items-start justify-between p-4 bg-gradient-to-r from-orange-50 to-orange-50 rounded-lg border border-orange-200">
                  <div className="flex-1">
                    <div className="flex items-center mb-1">
                      <span className="text-xl mr-2">🎫</span>
                      <span className="text-sm font-semibold text-gray-900">ServiceNow ITSM</span>
                      <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${mcpConfig.servicenow ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                        {mcpConfig.servicenow ? 'Connected' : 'Disconnected'}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 ml-7">
                      Provides: Support tickets, incidents, SLA breaches, escalations, response times
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={mcpConfig.servicenow}
                    onChange={(e) => toggleMCPSystem('servicenow', e.target.checked)}
                    disabled={saving}
                    className="h-5 w-5 text-orange-600 rounded focus:ring-2 focus:ring-orange-500 cursor-pointer"
                  />
                </div>

                {/* Survey Platform Toggle */}
                <div className="flex items-start justify-between p-4 bg-gradient-to-r from-purple-50 to-purple-50 rounded-lg border border-purple-200">
                  <div className="flex-1">
                    <div className="flex items-center mb-1">
                      <span className="text-xl mr-2">📋</span>
                      <span className="text-sm font-semibold text-gray-900">Survey & Interview Platform</span>
                      <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${mcpConfig.surveys ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                        {mcpConfig.surveys ? 'Connected' : 'Disconnected'}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 ml-7">
                      Provides: NPS scores, CSAT ratings, VoC interview feedback, CSM relationship assessments
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={mcpConfig.surveys}
                    onChange={(e) => toggleMCPSystem('surveys', e.target.checked)}
                    disabled={saving}
                    className="h-5 w-5 text-purple-600 rounded focus:ring-2 focus:ring-purple-500 cursor-pointer"
                  />
                </div>
              </div>

              {/* Quick Actions */}
              <div className="mt-6 flex gap-3">
                <button
                  onClick={() => {
                    setMcpConfig({ salesforce: true, servicenow: true, surveys: true });
                    toggleMCP(true);
                  }}
                  disabled={saving || mcpEnabled}
                  className="flex-1 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  ✅ Enable All Systems
                </button>
                <button
                  onClick={() => toggleMCP(false)}
                  disabled={saving || !mcpEnabled}
                  className="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  🔄 Disable MCP (Rollback)
                </button>
              </div>
            </div>
          )}

          {/* Warning when disabled */}
          {!mcpEnabled && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-4">
              <div className="flex items-start">
                <div className="text-yellow-600 mr-2">⚠️</div>
                <div className="flex-1">
                  <p className="text-sm text-yellow-800">
                    <strong>MCP Integration is currently disabled.</strong> AI queries use your local KPI database only.
                    Enable MCP to enhance AI with real-time data from Salesforce, ServiceNow, and survey platforms.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Playbook Triggers Section */}
        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            🎯 Playbook Triggers
          </h3>
          
          <div className="bg-gray-50 rounded-lg p-4 mb-4">
            <p className="text-sm text-gray-600 mb-4">
              Configure automatic trigger thresholds for playbook execution. When these conditions are met, playbooks will be automatically suggested or triggered.
            </p>
            
            <div className="bg-white rounded-lg p-4 mb-4 border border-gray-200">
              <h4 className="text-sm font-semibold text-gray-900 mb-3">📚 Available Playbooks & Triggers</h4>
              
              <div className="space-y-3">
                <div className="flex items-start">
                  <span className="text-lg mr-2">🎤</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">VoC Sprint</p>
                    <p className="text-xs text-gray-600">Triggers: NPS &lt; 10, CSAT &lt; 3.6, Churn Risk ≥ 30%, Health Drop ≥ 10 pts</p>
                    <p className="text-xs text-gray-500">Purpose: Surface value gaps and convert to executive-backed actions</p>
                  </div>
                </div>
                
                <div className="flex items-start">
                  <span className="text-lg mr-2">🚀</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">Activation Blitz</p>
                    <p className="text-xs text-gray-600">Triggers: Adoption &lt; 60, Active Users &lt; 50, DAU/MAU &lt; 25%</p>
                    <p className="text-xs text-gray-500">Purpose: Compress time-to-value and drive user engagement</p>
                  </div>
                </div>
                
                <div className="flex items-start">
                  <span className="text-lg mr-2">⚡</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">SLA Stabilizer</p>
                    <p className="text-xs text-gray-600">Triggers: SLA breaches &gt; 5, Response time &gt; 2x, Escalations increasing, Reopen rate &gt; 20%</p>
                    <p className="text-xs text-gray-500">Purpose: Rapid SLA recovery and process stabilization</p>
                  </div>
                </div>
                
                <div className="flex items-start">
                  <span className="text-lg mr-2">🛡️</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">Renewal Safeguard</p>
                    <p className="text-xs text-gray-600">Triggers: Renewal within 90 days, Health &lt; 70, Engagement declining, Champion departed</p>
                    <p className="text-xs text-gray-500">Purpose: Proactive renewal risk mitigation and value demonstration</p>
                  </div>
                </div>
                
                <div className="flex items-start">
                  <span className="text-lg mr-2">📈</span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">Expansion Timing</p>
                    <p className="text-xs text-gray-600">Triggers: Health &gt; 80, Adoption &gt; 85%, Usage &gt; 80%, Budget window open</p>
                    <p className="text-xs text-gray-500">Purpose: Strategic expansion opportunity identification and optimal timing</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* VoC Sprint Triggers */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center mb-4">
              <span className="text-2xl mr-3">🎤</span>
              <div>
                <h4 className="text-lg font-medium text-gray-900">VoC Sprint Triggers</h4>
                <p className="text-sm text-gray-600">Configure thresholds for Voice of Customer Sprint activation</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  NPS Threshold
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={triggerSettings.voc?.nps_threshold || 10}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="10"
                  onChange={(e) => handleTriggerChange('voc', 'nps_threshold', parseFloat(e.target.value) || 10)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if NPS below this value</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  CSAT Threshold
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={triggerSettings.voc?.csat_threshold || 3.6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="3.6"
                  onChange={(e) => handleTriggerChange('voc', 'csat_threshold', parseFloat(e.target.value) || 3.6)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if CSAT below this value</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Churn Risk Threshold
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={triggerSettings.voc?.churn_risk_threshold || 0.30}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0.30"
                  onChange={(e) => handleTriggerChange('voc', 'churn_risk_threshold', parseFloat(e.target.value) || 0.30)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if churn risk above this value</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Health Score Drop Threshold
                </label>
                <input
                  type="number"
                  step="1"
                  value={triggerSettings.voc?.health_score_drop_threshold || 10}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="10"
                  onChange={(e) => handleTriggerChange('voc', 'health_score_drop_threshold', parseInt(e.target.value) || 10)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if health score drops by this many points</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Churn Mentions Threshold
                </label>
                <input
                  type="number"
                  step="1"
                  value={triggerSettings.voc?.churn_mentions_threshold || 2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="2"
                  onChange={(e) => handleTriggerChange('voc', 'churn_mentions_threshold', parseInt(e.target.value) || 2)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if this many churn mentions in last quarter</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Auto-Trigger Enabled
                </label>
                <div className="flex items-center mt-2">
                  <input
                    type="checkbox"
                    checked={triggerSettings.voc?.auto_trigger_enabled || false}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    onChange={(e) => handleTriggerChange('voc', 'auto_trigger_enabled', e.target.checked)}
                  />
                  <span className="ml-2 text-sm text-gray-700">Automatically suggest VoC Sprint when triggers are met</span>
                </div>
              </div>
            </div>

            <div className="mt-4 flex justify-end space-x-3">
              <button
                onClick={() => saveTriggerSettings('voc')}
                disabled={saving}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving...' : 'Save VoC Triggers'}
              </button>
              <button
                onClick={() => testTriggerConditions('voc')}
                disabled={saving}
                className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Test Triggers
              </button>
            </div>
          </div>

          {/* Activation Blitz Triggers */}
          <div className="bg-white border border-gray-200 rounded-lg p-6 mt-6">
            <div className="flex items-center mb-4">
              <span className="text-2xl mr-3">🚀</span>
              <div>
                <h4 className="text-lg font-medium text-gray-900">Activation Blitz Triggers</h4>
                <p className="text-sm text-gray-600">Configure thresholds for Activation Blitz playbook activation</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Adoption Index Threshold
                </label>
                <input
                  type="number"
                  step="1"
                  value={triggerSettings.activation?.adoption_index_threshold || 60}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="60"
                  onChange={(e) => handleTriggerChange('activation', 'adoption_index_threshold', parseInt(e.target.value) || 60)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if adoption index below this value</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Active Users Threshold
                </label>
                <input
                  type="number"
                  step="1"
                  value={triggerSettings.activation?.active_users_threshold || 50}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="50"
                  onChange={(e) => handleTriggerChange('activation', 'active_users_threshold', parseInt(e.target.value) || 50)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if active users below this count</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  DAU/MAU Threshold
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={triggerSettings.activation?.dau_mau_threshold || 0.25}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="0.25"
                  onChange={(e) => handleTriggerChange('activation', 'dau_mau_threshold', parseFloat(e.target.value) || 0.25)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if DAU/MAU ratio below this value</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Unused Feature Check
                </label>
                <div className="flex items-center mt-2">
                  <input
                    type="checkbox"
                    checked={triggerSettings.activation?.unused_feature_check !== false}
                    className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
                    onChange={(e) => handleTriggerChange('activation', 'unused_feature_check', e.target.checked)}
                  />
                  <span className="ml-2 text-sm text-gray-700">Check for unused features in plan</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Auto-Trigger Enabled
                </label>
                <div className="flex items-center mt-2">
                  <input
                    type="checkbox"
                    checked={triggerSettings.activation?.auto_trigger_enabled || false}
                    className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded"
                    onChange={(e) => handleTriggerChange('activation', 'auto_trigger_enabled', e.target.checked)}
                  />
                  <span className="ml-2 text-sm text-gray-700">Automatically suggest Activation Blitz when triggers are met</span>
                </div>
              </div>

              <div className="md:col-span-2 lg:col-span-1">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Target Features
                </label>
                <input
                  type="text"
                  value={triggerSettings.activation?.target_features || ''}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="Feature X, Feature Y"
                  onChange={(e) => handleTriggerChange('activation', 'target_features', e.target.value)}
                />
                <p className="text-xs text-gray-500 mt-1">Specific features to check for usage</p>
              </div>
            </div>

            <div className="mt-4 flex justify-end space-x-3">
              <button
                onClick={() => saveTriggerSettings('activation')}
                disabled={saving}
                className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving...' : 'Save Activation Triggers'}
              </button>
              <button
                onClick={() => testTriggerConditions('activation')}
                disabled={saving}
                className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Test Triggers
              </button>
            </div>
          </div>

          {/* SLA Stabilizer Triggers */}
          <div className="bg-white border border-gray-200 rounded-lg p-6 mt-6">
            <div className="flex items-center mb-4">
              <span className="text-2xl mr-3">⚡</span>
              <div>
                <h4 className="text-lg font-medium text-gray-900">SLA Stabilizer Triggers</h4>
                <p className="text-sm text-gray-600">Configure thresholds for SLA Stabilizer playbook activation</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  SLA Breach Threshold
                </label>
                <input
                  type="number"
                  step="1"
                  value={triggerSettings.sla?.sla_breach_threshold || 5}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  placeholder="5"
                  onChange={(e) => handleTriggerChange('sla', 'sla_breach_threshold', parseInt(e.target.value) || 5)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if breaches exceed this in 30 days</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Response Time Multiplier
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={triggerSettings.sla?.response_time_multiplier || 2.0}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  placeholder="2.0"
                  onChange={(e) => handleTriggerChange('sla', 'response_time_multiplier', parseFloat(e.target.value) || 2.0)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if response time &gt; target × this multiplier</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reopen Rate Threshold
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={triggerSettings.sla?.reopen_rate_threshold || 0.20}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  placeholder="0.20"
                  onChange={(e) => handleTriggerChange('sla', 'reopen_rate_threshold', parseFloat(e.target.value) || 0.20)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if ticket reopen rate above this value</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Auto-Trigger Enabled
                </label>
                <div className="flex items-center mt-2">
                  <input
                    type="checkbox"
                    checked={triggerSettings.sla?.auto_trigger_enabled || false}
                    className="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded"
                    onChange={(e) => handleTriggerChange('sla', 'auto_trigger_enabled', e.target.checked)}
                  />
                  <span className="ml-2 text-sm text-gray-700">Automatically suggest SLA Stabilizer when triggers are met</span>
                </div>
              </div>
            </div>

            <div className="mt-4 flex justify-end space-x-3">
              <button
                onClick={() => saveTriggerSettings('sla')}
                disabled={saving}
                className="bg-orange-600 text-white px-4 py-2 rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving...' : 'Save SLA Triggers'}
              </button>
              <button
                onClick={() => testTriggerConditions('sla')}
                disabled={saving}
                className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Test Triggers
              </button>
            </div>
          </div>

          {/* Renewal Safeguard Triggers */}
          <div className="bg-white border border-gray-200 rounded-lg p-6 mt-6">
            <div className="flex items-center mb-4">
              <span className="text-2xl mr-3">🛡️</span>
              <div>
                <h4 className="text-lg font-medium text-gray-900">Renewal Safeguard Triggers</h4>
                <p className="text-sm text-gray-600">Configure thresholds for Renewal Safeguard playbook activation</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Renewal Window (Days)
                </label>
                <input
                  type="number"
                  step="1"
                  value={triggerSettings.renewal?.renewal_window_days || 90}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="90"
                  onChange={(e) => handleTriggerChange('renewal', 'renewal_window_days', parseInt(e.target.value) || 90)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger when renewal date within this many days</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Health Score Threshold
                </label>
                <input
                  type="number"
                  step="1"
                  value={triggerSettings.renewal?.health_score_threshold || 70}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                  placeholder="70"
                  onChange={(e) => handleTriggerChange('renewal', 'health_score_threshold', parseInt(e.target.value) || 70)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if health score below this value</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Budget Risk Check
                </label>
                <div className="flex items-center mt-2">
                  <input
                    type="checkbox"
                    checked={triggerSettings.renewal?.budget_risk !== false}
                    className="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                    onChange={(e) => handleTriggerChange('renewal', 'budget_risk', e.target.checked)}
                  />
                  <span className="ml-2 text-sm text-gray-700">Check for budget concerns</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Auto-Trigger Enabled
                </label>
                <div className="flex items-center mt-2">
                  <input
                    type="checkbox"
                    checked={triggerSettings.renewal?.auto_trigger_enabled || false}
                    className="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                    onChange={(e) => handleTriggerChange('renewal', 'auto_trigger_enabled', e.target.checked)}
                  />
                  <span className="ml-2 text-sm text-gray-700">Automatically suggest Renewal Safeguard when triggers are met</span>
                </div>
              </div>
            </div>

            <div className="mt-4 flex justify-end space-x-3">
              <button
                onClick={() => saveTriggerSettings('renewal')}
                disabled={saving}
                className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving...' : 'Save Renewal Triggers'}
              </button>
              <button
                onClick={() => testTriggerConditions('renewal')}
                disabled={saving}
                className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Test Triggers
              </button>
            </div>
          </div>

          {/* Expansion Timing Triggers */}
          <div className="bg-white border border-gray-200 rounded-lg p-6 mt-6">
            <div className="flex items-center mb-4">
              <span className="text-2xl mr-3">📈</span>
              <div>
                <h4 className="text-lg font-medium text-gray-900">Expansion Timing Triggers</h4>
                <p className="text-sm text-gray-600">Configure thresholds for Expansion Timing playbook activation</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Health Score Threshold
                </label>
                <input
                  type="number"
                  step="1"
                  value={triggerSettings.expansion?.health_score_threshold || 80}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="80"
                  onChange={(e) => handleTriggerChange('expansion', 'health_score_threshold', parseInt(e.target.value) || 80)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if health score above this value</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Adoption Threshold
                </label>
                <input
                  type="number"
                  step="1"
                  value={triggerSettings.expansion?.adoption_threshold || 85}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="85"
                  onChange={(e) => handleTriggerChange('expansion', 'adoption_threshold', parseInt(e.target.value) || 85)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if adoption above this percentage</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Usage Limit Percentage
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={triggerSettings.expansion?.usage_limit_percentage || 0.80}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="0.80"
                  onChange={(e) => handleTriggerChange('expansion', 'usage_limit_percentage', parseFloat(e.target.value) || 0.80)}
                />
                <p className="text-xs text-gray-500 mt-1">Trigger if usage &gt; this % of plan limits</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Budget Window
                </label>
                <select
                  value={triggerSettings.expansion?.budget_window || 'Q1_Q4'}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                  onChange={(e) => handleTriggerChange('expansion', 'budget_window', e.target.value)}
                >
                  <option value="Q1_Q4">Q1 & Q4</option>
                  <option value="Q1">Q1 Only</option>
                  <option value="Q4">Q4 Only</option>
                  <option value="anytime">Anytime</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">Preferred budget planning windows</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Auto-Trigger Enabled
                </label>
                <div className="flex items-center mt-2">
                  <input
                    type="checkbox"
                    checked={triggerSettings.expansion?.auto_trigger_enabled || false}
                    className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded"
                    onChange={(e) => handleTriggerChange('expansion', 'auto_trigger_enabled', e.target.checked)}
                  />
                  <span className="ml-2 text-sm text-gray-700">Automatically suggest Expansion Timing when triggers are met</span>
                </div>
              </div>
            </div>

            <div className="mt-4 flex justify-end space-x-3">
              <button
                onClick={() => saveTriggerSettings('expansion')}
                disabled={saving}
                className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving...' : 'Save Expansion Triggers'}
              </button>
              <button
                onClick={() => testTriggerConditions('expansion')}
                disabled={saving}
                className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Test Triggers
              </button>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end space-x-4">
          <button
            onClick={fetchFeatureStatus}
            disabled={loading}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
          >
            {loading ? 'Refreshing...' : 'Refresh Status'}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default Settings;
