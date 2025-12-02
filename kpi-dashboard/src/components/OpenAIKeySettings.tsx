import React, { useState, useEffect } from 'react';
import { Key, Eye, EyeOff, CheckCircle, XCircle } from 'lucide-react';

interface OpenAIKeySettingsProps {
  isAuthenticated: boolean;
}

const OpenAIKeySettings: React.FC<OpenAIKeySettingsProps> = ({ isAuthenticated }) => {
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      fetchKeyStatus();
    }
  }, [isAuthenticated]);

  const fetchKeyStatus = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/openai-key', {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setHasKey(data.has_key || false);
      }
    } catch (err) {
      console.error('Error fetching OpenAI key status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!apiKey.trim()) {
      setError('Please enter an OpenAI API key');
      return;
    }

    if (!apiKey.startsWith('sk-')) {
      setError('Invalid API key format. OpenAI API keys should start with "sk-"');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      const response = await fetch('/api/openai-key', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ api_key: apiKey.trim() }),
      });

      if (response.ok) {
        const data = await response.json();
        setSuccess(data.message || 'OpenAI API key saved successfully! Changes take effect immediately.');
        setHasKey(true);
        setApiKey(''); // Clear input after successful save
        setTimeout(() => setSuccess(null), 5000);
      } else {
        const errorData = await response.json().catch(() => ({ error: 'Failed to save API key' }));
        setError(errorData.error || errorData.message || 'Failed to save API key');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save API key');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to remove your OpenAI API key? RAG queries will stop working until you add a new key.')) {
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      const response = await fetch('/api/openai-key', {
        method: 'DELETE',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        setSuccess('OpenAI API key removed successfully');
        setHasKey(false);
        setApiKey('');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        const errorData = await response.json().catch(() => ({ error: 'Failed to remove API key' }));
        setError(errorData.error || errorData.message || 'Failed to remove API key');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove API key');
    } finally {
      setSaving(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-800">Please log in to configure your OpenAI API key.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <Key className="h-5 w-5 text-blue-600" />
          OpenAI API Key Configuration
        </h3>
        <p className="text-sm text-gray-600 mt-1">
          Configure your OpenAI API key for RAG (AI-powered) queries. Changes take effect immediately - no server restart needed!
        </p>
      </div>

      {/* Status Indicator */}
      <div className={`p-4 rounded-lg border ${hasKey ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'}`}>
        <div className="flex items-center gap-2">
          {hasKey ? (
            <>
              <CheckCircle className="h-5 w-5 text-green-600" />
              <span className="text-sm font-medium text-green-800">OpenAI API key is configured</span>
            </>
          ) : (
            <>
              <XCircle className="h-5 w-5 text-yellow-600" />
              <span className="text-sm font-medium text-yellow-800">OpenAI API key is not configured</span>
            </>
          )}
        </div>
        {hasKey && (
          <p className="text-xs text-green-700 mt-2">
            Your API key is encrypted and stored securely. RAG queries are ready to use.
          </p>
        )}
        {!hasKey && (
          <p className="text-xs text-yellow-700 mt-2">
            Add your OpenAI API key below to enable AI-powered RAG queries. Get your key from{' '}
            <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="underline">
              OpenAI Platform
            </a>.
          </p>
        )}
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-sm text-green-800">{success}</p>
        </div>
      )}

      {/* API Key Input */}
      <div className="space-y-2">
        <label htmlFor="openai-key" className="block text-sm font-medium text-gray-700">
          OpenAI API Key
        </label>
        <div className="relative">
          <input
            id="openai-key"
            type={showKey ? 'text' : 'password'}
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={hasKey ? 'Enter new key to update...' : 'sk-...'}
            className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={saving || loading}
          />
          <button
            type="button"
            onClick={() => setShowKey(!showKey)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
            disabled={saving || loading}
          >
            {showKey ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
          </button>
        </div>
        <p className="text-xs text-gray-500">
          Your API key is encrypted and stored securely. Only you can see or update it.
        </p>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={saving || loading || !apiKey.trim()}
          className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {saving ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              Saving...
            </>
          ) : (
            <>
              <Key className="h-4 w-4" />
              {hasKey ? 'Update API Key' : 'Save API Key'}
            </>
          )}
        </button>
        {hasKey && (
          <button
            onClick={handleDelete}
            disabled={saving || loading}
            className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Remove
          </button>
        )}
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-medium text-blue-900 mb-2">💡 How it works:</h4>
        <ul className="text-xs text-blue-800 space-y-1 list-disc list-inside">
          <li>Your API key is encrypted and stored per customer (multi-tenant safe)</li>
          <li>Changes take effect immediately - no server restart needed</li>
          <li>Each customer can have their own API key</li>
          <li>If no customer key is set, the system falls back to a global environment variable</li>
        </ul>
      </div>
    </div>
  );
};

export default OpenAIKeySettings;

