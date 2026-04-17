import React, { useState, useEffect } from 'react';
import { Key, Plus, Copy, Check, Trash2, Shield, AlertCircle } from 'lucide-react';

interface ApiKey {
  id: number;
  key_prefix: string;
  name: string;
  scopes: string[];
  is_active: boolean;
  last_used_at: string | null;
  created_at: string | null;
  expires_at: string | null;
}

const ApiKeysTab: React.FC = () => {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyScopes, setNewKeyScopes] = useState<string[]>(['read', 'write']);
  const [creating, setCreating] = useState(false);
  const [newKeyValue, setNewKeyValue] = useState('');
  const [copied, setCopied] = useState(false);
  const [revoking, setRevoking] = useState<number | null>(null);

  const fetchKeys = async () => {
    try {
      const res = await fetch('/api/settings/api-keys', { credentials: 'include' });
      if (!res.ok) throw new Error('Failed to load API keys');
      const data = await res.json();
      setKeys(data.api_keys || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load keys');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchKeys(); }, []);

  const handleCreate = async () => {
    if (!newKeyName.trim()) return;
    setCreating(true);
    setError('');
    try {
      const res = await fetch('/api/settings/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name: newKeyName, scopes: newKeyScopes }),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.error || 'Failed to create key');
      }
      const data = await res.json();
      setNewKeyValue(data.api_key);
      setNewKeyName('');
      fetchKeys();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create key');
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (keyId: number) => {
    if (!window.confirm('Revoke this API key? Any integrations using it will stop working.')) return;
    setRevoking(keyId);
    try {
      const res = await fetch(`/api/settings/api-keys/${keyId}/revoke`, {
        method: 'POST',
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed to revoke key');
      fetchKeys();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to revoke');
    } finally {
      setRevoking(null);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const scopeBadge = (scope: string) => {
    const colors: Record<string, string> = {
      read: 'bg-blue-100 text-blue-700',
      write: 'bg-green-100 text-green-700',
      admin: 'bg-purple-100 text-purple-700',
    };
    return (
      <span key={scope} className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colors[scope] || 'bg-gray-100 text-gray-700'}`}>
        {scope}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Key className="w-5 h-5 text-emerald-600" />
            API Keys
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Manage API keys for MCP integrations, Claude.ai connectors, and external tools.
          </p>
        </div>
        <button
          onClick={() => { setShowCreate(true); setNewKeyValue(''); }}
          className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 text-sm font-medium"
        >
          <Plus className="w-4 h-4" />
          Create API Key
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* New Key Created — show once */}
      {newKeyValue && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 space-y-2">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-emerald-600" />
            <span className="text-sm font-semibold text-emerald-800">API Key Created</span>
          </div>
          <p className="text-xs text-emerald-700">
            Copy this key now — it will not be shown again.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 px-3 py-2 bg-white border border-emerald-300 rounded text-sm font-mono text-gray-900 select-all">
              {newKeyValue}
            </code>
            <button
              onClick={() => copyToClipboard(newKeyValue)}
              className="p-2 rounded-lg hover:bg-emerald-100"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4 text-gray-500" />}
            </button>
          </div>
          <p className="text-xs text-emerald-600">
            Use as: <code className="bg-white px-1 rounded">Authorization: Bearer {newKeyValue.substring(0, 16)}...</code>
          </p>
          <button
            onClick={() => setNewKeyValue('')}
            className="text-xs text-emerald-700 hover:text-emerald-900 underline"
          >
            I've saved it, dismiss
          </button>
        </div>
      )}

      {/* Create Modal */}
      {showCreate && !newKeyValue && (
        <div className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm space-y-4">
          <h4 className="text-sm font-semibold text-gray-900">Create New API Key</h4>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Key Name</label>
            <input
              type="text"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              placeholder="e.g., Claude.ai MCP Connector"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Permissions</label>
            <div className="flex gap-4">
              {['read', 'write'].map((scope) => (
                <label key={scope} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={newKeyScopes.includes(scope)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setNewKeyScopes([...newKeyScopes, scope]);
                      } else {
                        setNewKeyScopes(newKeyScopes.filter((s) => s !== scope));
                      }
                    }}
                    className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="capitalize">{scope}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={creating || !newKeyName.trim()}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 text-sm font-medium disabled:opacity-50"
            >
              {creating ? 'Creating...' : 'Create Key'}
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Keys Table */}
      {loading ? (
        <div className="text-sm text-gray-500 text-center py-8">Loading API keys...</div>
      ) : keys.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
          <Key className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500">No API keys yet</p>
          <p className="text-xs text-gray-400 mt-1">Create a key to connect Claude.ai, MCP tools, or external integrations.</p>
        </div>
      ) : (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Key Prefix</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Scopes</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Used</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {keys.map((key) => (
                <tr key={key.id} className={!key.is_active ? 'opacity-50 bg-gray-50' : ''}>
                  <td className="px-4 py-3 font-medium text-gray-900">{key.name}</td>
                  <td className="px-4 py-3 font-mono text-gray-500 text-xs">{key.key_prefix}...</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">{key.scopes.map(scopeBadge)}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{formatDate(key.created_at)}</td>
                  <td className="px-4 py-3 text-gray-500">{formatDate(key.last_used_at)}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      key.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {key.is_active ? 'Active' : 'Revoked'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {key.is_active && (
                      <button
                        onClick={() => handleRevoke(key.id)}
                        disabled={revoking === key.id}
                        className="text-red-500 hover:text-red-700 p-1"
                        title="Revoke key"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Usage Guide */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-blue-800 mb-2">How to use your API key</h4>
        <div className="text-xs text-blue-700 space-y-1">
          <p><strong>Claude.ai MCP Connector:</strong> Add your key as <code className="bg-white px-1 rounded">Authorization: Bearer YOUR_KEY</code> in the connector settings.</p>
          <p><strong>Load Driver:</strong> <code className="bg-white px-1 rounded">python3 cs_pulse_driver.py --api-key YOUR_KEY --customer-id YOUR_ID</code></p>
          <p><strong>cURL:</strong> <code className="bg-white px-1 rounded">curl -H "Authorization: Bearer YOUR_KEY" https://your-server/mcp</code></p>
        </div>
      </div>
    </div>
  );
};

export default ApiKeysTab;
