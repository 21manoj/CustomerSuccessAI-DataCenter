import React, { useEffect, useState } from 'react';

type WorkflowConfig = {
  workflow_system: string;
  n8n_instance_type: string;
  n8n_base_url: string;
  n8n_webhook_url: string;
  enabled_playbooks: string[];
  config: Record<string, any>;
  n8n_api_key?: string;
};

type WorkflowConfigResponse = {
  configured: boolean;
  config: (WorkflowConfig & {
    n8n_api_key_present?: boolean;
    webhook_last_rotated?: string | null;
  }) | null;
  webhook_secret?: string;
};

const DEFAULT_CONFIG: WorkflowConfig = {
  workflow_system: 'google_sheets_stub',
  n8n_instance_type: 'cloud_n8n',
  n8n_base_url: '',
  n8n_webhook_url: '',
  enabled_playbooks: ['ttfv_fast_track', 'ttfv_onboarding_rescue'],
  config: { sheet_id: '' }
};

const enabledPlaybooksToString = (value: string[]) => value.join(', ');
const enabledPlaybooksFromString = (value: string) =>
  value
    .split(',')
    .map(v => v.trim())
    .filter(Boolean);

interface Props {
  isAuthenticated: boolean;
}

const PlaybookAutomationSettings: React.FC<Props> = ({ isAuthenticated }) => {
  const [config, setConfig] = useState<WorkflowConfig>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [webhookSecret, setWebhookSecret] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [apiKeyPresent, setApiKeyPresent] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const run = async () => {
      setLoading(true);
      try {
        const response = await fetch('/api/workflow/config', {
          credentials: 'include',
        });

        if (response.status === 401) {
          if (isMounted) {
            setConfig(DEFAULT_CONFIG);
            setError('Please log in to configure playbook automation.');
          }
          return;
        }

        try {
          const data: WorkflowConfigResponse = await response.json();
          if (isMounted) {
            if (data.config) {
              setConfig({
                workflow_system: data.config.workflow_system || DEFAULT_CONFIG.workflow_system,
                n8n_instance_type: data.config.n8n_instance_type || DEFAULT_CONFIG.n8n_instance_type,
                n8n_base_url: data.config.n8n_base_url || '',
                n8n_webhook_url: data.config.n8n_webhook_url || '',
                enabled_playbooks: data.config.enabled_playbooks || DEFAULT_CONFIG.enabled_playbooks,
                config: data.config.config || DEFAULT_CONFIG.config,
              });
              setApiKeyPresent(data.config.n8n_api_key_present || false);
              setWebhookSecret(null);
              setError(null);
            } else {
              setConfig(DEFAULT_CONFIG);
              setApiKeyPresent(false);
            }
          }
        } catch (parseErr) {
          if (isMounted) {
            setError('Backend returned an unexpected response. Please log in again.');
          }
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to load configuration');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    run();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleInputChange = (field: keyof WorkflowConfig, value: string) => {
    setConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleEnabledPlaybooksChange = (value: string) => {
    setConfig(prev => ({
      ...prev,
      enabled_playbooks: enabledPlaybooksFromString(value)
    }));
  };

  const handleConfigJsonChange = (value: string) => {
    try {
      const parsed = value ? JSON.parse(value) : {};
      setConfig(prev => ({
        ...prev,
        config: parsed
      }));
      setError(null);
    } catch (err) {
      setError('Config JSON must be valid JSON');
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      setWebhookSecret(null);

      const response = await fetch('/api/workflow/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          ...config,
          n8n_api_key: config.n8n_api_key
        })
      });

      if (response.status === 401) {
        setError('Please log in to access this resource');
        return;
      }

      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
          const data = await response.json();
          throw new Error(data.message || data.error || 'Failed to save configuration');
        } else {
          throw new Error(`Server returned ${response.status}. Please log in again.`);
        }
      }

      const data: WorkflowConfigResponse = await response.json();
      if (data.webhook_secret) {
        setWebhookSecret(data.webhook_secret);
      }
      // Update API key presence status if config is returned
      if (data.config) {
        setApiKeyPresent(data.config.n8n_api_key_present || false);
      }
      // Clear the API key field after saving (for security)
      if (config.n8n_api_key) {
        setConfig(prev => ({ ...prev, n8n_api_key: '' }));
      }
      setSuccess('Playbook automation settings saved successfully');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleRotateSecret = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      setWebhookSecret(null);

      const response = await fetch('/api/workflow/config/rotate-secret', {
        method: 'POST',
        credentials: 'include'
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.message || 'Failed to rotate webhook secret');
      }

      const data = await response.json();
      setWebhookSecret(data.webhook_secret);
      setSuccess('Webhook secret rotated. Update your n8n credentials.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rotate webhook secret');
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    try {
      setTesting(true);
      setTestResult(null);
      setError(null);

      if (!config.n8n_webhook_url) {
        setTestResult('Please enter a webhook URL first');
        return;
      }

      const response = await fetch('/api/workflow/config/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          n8n_webhook_url: config.n8n_webhook_url,
          webhook_secret: webhookSecret || undefined
        })
      });

      // Check if response is JSON
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        throw new Error(`Backend returned HTML instead of JSON. Status: ${response.status}. This might be a login redirect or error page.`);
      }

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || data.message || 'Connection test failed');
      }

      setTestResult('Connection successful ✅');
    } catch (err) {
      setTestResult(err instanceof Error ? err.message : 'Connection test failed');
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md border border-slate-200">
      <div className="px-6 py-4 border-b border-slate-200 bg-blue-50">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
              <span role="img" aria-label="workflow">🔄</span>
              n8n Workflow Integration
            </h3>
            <p className="text-sm text-slate-600 mt-1">
              <strong>Optional:</strong> Configure external workflow automation for advanced integrations. 
              Core playbooks run independently without n8n. This configuration is only needed if you want to 
              hand off playbooks to external workflow engines like n8n, Jira, or Asana.
            </p>
            <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
              <strong>Note:</strong> Internal playbook execution does not require this configuration. 
              Playbooks work perfectly for demos without any external automation setup.
            </div>
          </div>
        </div>
      </div>

      <div className="px-6 py-4 space-y-4">
        {!isAuthenticated ? (
          <div className="text-sm text-slate-600">
            Please log in to configure playbook automation.
          </div>
        ) : loading ? (
          <div className="text-sm text-slate-600">Loading current configuration…</div>
        ) : (
          <>
            {error && (
              <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {success && (
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm px-4 py-3 rounded-lg">
                {success}
              </div>
            )}

            {webhookSecret && (
              <div className="bg-amber-50 border border-amber-200 text-amber-700 text-sm px-4 py-3 rounded-lg">
                <p className="font-medium">Webhook Secret (copy into n8n and store securely):</p>
                <code className="block mt-2 bg-white border border-amber-100 rounded px-2 py-1 text-slate-800 break-all">
                  {webhookSecret}
                </code>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Workflow System
                </label>
                <input
                  type="text"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={config.workflow_system}
                  onChange={(e) => handleInputChange('workflow_system', e.target.value)}
                  placeholder="e.g. google_sheets_stub, jira, asana"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  n8n Instance Type
                </label>
                <select
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={config.n8n_instance_type}
                  onChange={(e) => handleInputChange('n8n_instance_type', e.target.value)}
                >
                  <option value="cloud_n8n">n8n Cloud (Managed)</option>
                  <option value="self_hosted">Self-hosted (AWS/GCP/Azure)</option>
                  <option value="existing">Existing n8n Instance</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  n8n Base URL
                </label>
                <input
                  type="url"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={config.n8n_base_url}
                  onChange={(e) => handleInputChange('n8n_base_url', e.target.value)}
                  placeholder="https://your-n8n-instance/"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Webhook URL
                </label>
                <input
                  type="url"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={config.n8n_webhook_url}
                  onChange={(e) => handleInputChange('n8n_webhook_url', e.target.value)}
                  placeholder="https://your-n8n-instance/webhook/playbook"
                  required
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Enabled Playbooks (comma separated)
                </label>
                <input
                  type="text"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={enabledPlaybooksToString(config.enabled_playbooks)}
                  onChange={(e) => handleEnabledPlaybooksChange(e.target.value)}
                  placeholder="ttfv_fast_track, ttfv_onboarding_rescue"
                />
                <p className="text-xs text-slate-500 mt-1">
                  More playbooks can be added later (GRR, NRR, Adoption, Support, Revenue).
                </p>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  n8n API Key {apiKeyPresent && <span className="text-xs text-green-600">(currently set)</span>}
                </label>
                <input
                  type="password"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={config.n8n_api_key || ''}
                  onChange={(e) => handleInputChange('n8n_api_key', e.target.value)}
                  placeholder={apiKeyPresent ? "Enter new key to update (leave empty to keep current)" : "Only needed if your n8n webhook requires bearer token authentication"}
                />
                {apiKeyPresent ? (
                  <p className="text-xs text-slate-500 mt-1">
                    ✓ API key is configured. Enter a new key above to update it, or leave empty to keep the current key.
                  </p>
                ) : (
                  <p className="text-xs text-slate-500 mt-1">
                    Optional: Only needed if your n8n webhook requires Bearer token authentication. 
                    Get it from n8n Settings → API (for n8n API) or your webhook's custom auth token.
                    Most local webhooks don't require this.
                  </p>
                )}
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Additional Config (JSON)
                </label>
                <textarea
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={4}
                  value={JSON.stringify(config.config, null, 2)}
                  onChange={(e) => handleConfigJsonChange(e.target.value)}
                  placeholder='{ "sheet_id": "..." }'
                />
              </div>
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              <button
                className="inline-flex items-center px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium shadow hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Saving…' : 'Save Settings'}
              </button>

              <button
                className="inline-flex items-center px-4 py-2 rounded-lg bg-amber-500 text-white text-sm font-medium shadow hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleRotateSecret}
                disabled={saving}
              >
                Rotate Webhook Secret
              </button>

              <button
                className="inline-flex items-center px-4 py-2 rounded-lg border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleTestConnection}
                disabled={testing || !config.n8n_webhook_url}
              >
                {testing ? 'Testing…' : 'Test Connection'}
              </button>
            </div>

            {testResult && (
              <div className="text-sm mt-2 text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
                {testResult}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default PlaybookAutomationSettings;

