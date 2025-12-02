/**
 * n8n Workflow Settings Component
 * 
 * FUTURE IMPLEMENTATION: Separate UI for configuring n8n workflow integration
 * This is optional and does not affect core playbook execution.
 */

import React, { useState, useEffect } from 'react';
import { useSession } from '../contexts/SessionContext';
import { Zap, CheckCircle, XCircle, ExternalLink } from 'lucide-react';

interface N8NPlaybookMapping {
  playbook_id: string;
  playbook_name: string;
  enabled: boolean;
  n8n_workflow_url: string;
  n8n_workflow_id?: string;
  auto_trigger: boolean;
}

const PLAYBOOKS = [
  { id: 'voc-sprint', name: 'VoC Sprint' },
  { id: 'activation-blitz', name: 'Activation Blitz' },
  { id: 'sla-stabilizer', name: 'SLA Stabilizer' },
  { id: 'renewal-safeguard', name: 'Renewal Safeguard' },
  { id: 'expansion-timing', name: 'Expansion Timing' },
];

export default function N8NWorkflowSettings() {
  const { session } = useSession();
  const [mappings, setMappings] = useState<N8NPlaybookMapping[]>([]);
  const [globalEnabled, setGlobalEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (session?.customer_id) {
      fetchMappings();
    }
  }, [session]);

  const fetchMappings = async () => {
    try {
      setLoading(true);
      // FUTURE: Replace with actual endpoint
      // const response = await fetch('/api/n8n/playbooks/mappings', {
      //   headers: { 'X-Customer-ID': session!.customer_id.toString() }
      // });
      // const data = await response.json();
      
      // For now, initialize with defaults
      const defaultMappings: N8NPlaybookMapping[] = PLAYBOOKS.map(pb => ({
        playbook_id: pb.id,
        playbook_name: pb.name,
        enabled: false,
        n8n_workflow_url: '',
        auto_trigger: false,
      }));
      setMappings(defaultMappings);
    } catch (err) {
      setError('Failed to load n8n workflow mappings');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleMapping = (playbookId: string, enabled: boolean) => {
    // Prevent toggling if global is disabled
    if (!globalEnabled && enabled) {
      return;
    }
    setMappings(prev => prev.map(m => 
      m.playbook_id === playbookId ? { ...m, enabled, ...(enabled ? {} : { n8n_workflow_url: '', auto_trigger: false }) } : m
    ));
  };

  const handleUpdateMapping = (playbookId: string, field: keyof N8NPlaybookMapping, value: any) => {
    // Prevent updates if global is disabled
    if (!globalEnabled) {
      return;
    }
    setMappings(prev => prev.map(m => 
      m.playbook_id === playbookId ? { ...m, [field]: value } : m
    ));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      
      // Simulate save delay to test toggle behavior
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // FUTURE: Replace with actual endpoint
      // const response = await fetch('/api/n8n/playbooks/mappings', {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //     'X-Customer-ID': session!.customer_id.toString()
      //   },
      //   body: JSON.stringify({ mappings, global_enabled: globalEnabled })
      // });
      
      setSuccess('n8n workflow mappings saved successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to save n8n workflow mappings');
      setTimeout(() => setError(null), 5000);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="text-sm text-gray-600">Loading n8n workflow settings...</div>;
  }

  return (
    <div className="bg-white rounded-xl shadow-md border border-slate-200">
      <div className="px-6 py-4 border-b border-slate-200 bg-blue-50">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <Zap className="h-5 w-5 text-blue-600" />
              n8n Workflow Integration
            </h3>
            <p className="text-sm text-slate-600 mt-1">
              Map playbooks to n8n workflows. Core playbooks work independently without this configuration.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 pt-2 border-t border-blue-100">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={globalEnabled}
              onChange={(e) => {
                const newValue = e.target.checked;
                setGlobalEnabled(newValue);
                // When disabling global, also disable all individual playbook mappings
                if (!newValue) {
                  setMappings(prev => prev.map(m => ({ ...m, enabled: false, auto_trigger: false })));
                }
              }}
              disabled={saving}
              className="h-5 w-5 text-blue-600 rounded border-gray-300 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <span className={`text-sm font-semibold ${saving ? 'text-gray-500' : 'text-slate-900'}`}>
              Enable n8n Integration
            </span>
          </label>
        </div>
      </div>

      <div className="px-6 py-4 space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-3 rounded-lg">
            {success}
          </div>
        )}

        {!globalEnabled && (
          <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 text-sm px-4 py-3 rounded-lg">
            <strong>Note:</strong> n8n integration is disabled. Core playbooks will run normally without n8n workflows. 
            Toggle above to enable and configure per-playbook mappings.
          </div>
        )}

        {/* Always show playbook cards, but disable when global toggle is off */}
        <div className="space-y-4">
          {globalEnabled && (
            <div className="text-sm text-slate-600 mb-4">
              Configure which playbooks should hand off to n8n workflows. Each playbook can have its own n8n workflow URL.
            </div>
          )}

          {mappings.map((mapping) => (
              <div key={mapping.playbook_id} className={`border rounded-lg p-4 ${globalEnabled ? 'border-slate-200 bg-white' : 'border-gray-200 bg-gray-50 opacity-60'}`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h4 className="font-medium text-slate-900">{mapping.playbook_name}</h4>
                    {mapping.enabled && globalEnabled ? (
                      <span className="flex items-center gap-1 text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                        <CheckCircle className="h-3 w-3" />
                        Enabled
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                        <XCircle className="h-3 w-3" />
                        Disabled
                      </span>
                    )}
                  </div>
                  <label className={`flex items-center gap-2 ${globalEnabled ? 'cursor-pointer' : 'cursor-not-allowed'}`}>
                    <input
                      type="checkbox"
                      checked={mapping.enabled}
                      onChange={(e) => handleToggleMapping(mapping.playbook_id, e.target.checked)}
                      disabled={!globalEnabled}
                      className="h-5 w-5 text-blue-600 rounded border-gray-300 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                    <span className={`text-sm ${globalEnabled ? 'text-slate-700' : 'text-gray-500'}`}>
                      Enable n8n handoff
                    </span>
                  </label>
                </div>

                {mapping.enabled && globalEnabled && (
                  <div className="space-y-3 mt-4 pl-4 border-l-2 border-blue-200">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        n8n Workflow URL
                      </label>
                      <input
                        type="url"
                        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        value={mapping.n8n_workflow_url}
                        onChange={(e) => handleUpdateMapping(mapping.playbook_id, 'n8n_workflow_url', e.target.value)}
                        placeholder="https://your-n8n-instance/webhook/voc-sprint"
                      />
                      <p className="text-xs text-slate-500 mt-1">
                        The webhook URL from your n8n workflow
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={mapping.auto_trigger}
                        onChange={(e) => handleUpdateMapping(mapping.playbook_id, 'auto_trigger', e.target.checked)}
                        className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                      />
                      <label className="text-sm text-slate-700">
                        Auto-trigger n8n workflow when playbook starts
                      </label>
                    </div>
                  </div>
                )}
              </div>
            ))}

          {globalEnabled && (
            <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
              >
                {saving ? 'Saving...' : 'Save n8n Mappings'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

