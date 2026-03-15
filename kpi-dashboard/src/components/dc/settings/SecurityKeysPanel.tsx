/**
 * SecurityKeysPanel
 * =================
 * Manages API keys, contractor access, and security audit log.
 * Visible only to super_admin and admin roles.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useSession } from '../../../contexts/SessionContext';
import {
  Key, Shield, Users, Clock, AlertTriangle, CheckCircle, Copy, Eye, EyeOff,
  Plus, XCircle, RefreshCw, User, Lock
} from 'lucide-react';
import {
  ApiKeyInfo, ContractorInfo, ActivityEntry,
  fetchApiKeys, generateApiKey, revokeApiKey,
  fetchContractors, createContractorAccess, revokeContractorAccess,
  fetchSecurityLog,
} from '../../../api/adminApi';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isExpired(expiresAt: string | null): boolean {
  if (!expiresAt) return false;
  return new Date(expiresAt) < new Date();
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleDateString();
}

function generateRandomPassword(length = 16): string {
  const upper = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
  const lower = 'abcdefghijklmnopqrstuvwxyz';
  const digits = '0123456789';
  const special = '!@#$%&*';
  const all = upper + lower + digits + special;
  const arr = new Uint8Array(length);
  crypto.getRandomValues(arr);
  // Guarantee at least one of each required character type
  const result = Array.from(arr, (v) => all[v % all.length]);
  result[0] = upper[arr[0] % upper.length];
  result[1] = lower[arr[1] % lower.length];
  result[2] = digits[arr[2] % digits.length];
  result[3] = special[arr[3] % special.length];
  // Shuffle the first 4 guaranteed chars into random positions
  for (let i = result.length - 1; i > 0; i--) {
    const j = arr[i] % (i + 1);
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result.join('');
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface StatusDotProps {
  color: 'green' | 'red' | 'gray';
  label: string;
}

const StatusDot: React.FC<StatusDotProps> = ({ color, label }) => {
  const dotColor = color === 'green' ? 'bg-green-500' : color === 'red' ? 'bg-red-500' : 'bg-gray-400';
  const textColor = color === 'green' ? 'text-green-700' : color === 'red' ? 'text-red-700' : 'text-gray-500';
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${textColor}`}>
      <span className={`w-2 h-2 rounded-full ${dotColor}`} />
      {label}
    </span>
  );
};

function keyStatus(key: ApiKeyInfo): { color: 'green' | 'red' | 'gray'; label: string } {
  if (!key.is_active) return { color: 'gray', label: 'Revoked' };
  if (isExpired(key.expires_at)) return { color: 'red', label: 'Expired' };
  return { color: 'green', label: 'Active' };
}

function contractorStatus(c: ContractorInfo): { color: 'green' | 'red' | 'gray'; label: string } {
  if (!c.active) return { color: 'gray', label: 'Revoked' };
  if (isExpired(c.expires_at)) return { color: 'red', label: 'Expired' };
  return { color: 'green', label: 'Active' };
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const SecurityKeysPanel: React.FC = () => {
  const { session } = useSession();
  const customerId = session?.customer_id;

  // Data
  const [apiKeys, setApiKeys] = useState<ApiKeyInfo[]>([]);
  const [contractors, setContractors] = useState<ContractorInfo[]>([]);
  const [securityLog, setSecurityLog] = useState<ActivityEntry[]>([]);

  // Modals
  const [showCreateKeyModal, setShowCreateKeyModal] = useState(false);
  const [showCreateContractorModal, setShowCreateContractorModal] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<{ type: 'key' | 'contractor'; id: number; name: string } | null>(null);

  // Revealed new key
  const [newKeyRevealed, setNewKeyRevealed] = useState<string | null>(null);

  // Loading / error
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [loadingContractors, setLoadingContractors] = useState(false);
  const [loadingLog, setLoadingLog] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // -----------------------------------------------------------------------
  // Data fetching
  // -----------------------------------------------------------------------

  const loadAll = useCallback(async () => {
    if (!customerId) return;
    setError(null);

    setLoadingKeys(true);
    setLoadingContractors(true);
    setLoadingLog(true);

    try {
      const [keys, cons, logs] = await Promise.all([
        fetchApiKeys(customerId).catch(() => [] as ApiKeyInfo[]),
        fetchContractors(customerId).catch(() => [] as ContractorInfo[]),
        fetchSecurityLog(customerId, 20).catch(() => [] as ActivityEntry[]),
      ]);
      setApiKeys(keys);
      setContractors(cons);
      setSecurityLog(logs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load security data');
    } finally {
      setLoadingKeys(false);
      setLoadingContractors(false);
      setLoadingLog(false);
    }
  }, [customerId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const refreshLog = useCallback(async () => {
    if (!customerId) return;
    setLoadingLog(true);
    try {
      const logs = await fetchSecurityLog(customerId, 20);
      setSecurityLog(logs);
    } catch {
      // silent
    } finally {
      setLoadingLog(false);
    }
  }, [customerId]);

  // -----------------------------------------------------------------------
  // Revoke handler
  // -----------------------------------------------------------------------

  const handleRevoke = async () => {
    if (!revokeTarget) return;
    try {
      if (revokeTarget.type === 'key') {
        await revokeApiKey(revokeTarget.id);
      } else {
        await revokeContractorAccess(revokeTarget.id);
      }
      setRevokeTarget(null);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Revoke failed');
      setRevokeTarget(null);
    }
  };

  // -----------------------------------------------------------------------
  // Copy helper
  // -----------------------------------------------------------------------

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // fallback – ignore
    }
  };

  // -----------------------------------------------------------------------
  // Render guard
  // -----------------------------------------------------------------------

  if (!customerId) {
    return (
      <div className="text-center py-12 text-gray-500">
        No customer selected. Please log in.
      </div>
    );
  }

  const role = session?.role;
  if (role !== 'super_admin' && role !== 'admin') {
    return (
      <div className="text-center py-12 text-gray-500">
        <Shield className="w-8 h-8 mx-auto mb-2 text-gray-400" />
        You do not have permission to view this page.
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Global error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-2 text-sm text-red-700">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-600">
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* ================================================================ */}
      {/* API Keys Section                                                  */}
      {/* ================================================================ */}
      <section className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Key className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">API Keys</h3>
          </div>
          <button
            onClick={() => { setNewKeyRevealed(null); setShowCreateKeyModal(true); }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" /> Create Key
          </button>
        </div>

        <div className="overflow-x-auto">
          {loadingKeys ? (
            <div className="p-6 text-center text-gray-500 text-sm">Loading API keys...</div>
          ) : apiKeys.length === 0 ? (
            <div className="p-6 text-center text-gray-400 text-sm">No API keys found.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <th className="px-6 py-3">Name</th>
                  <th className="px-6 py-3">Prefix</th>
                  <th className="px-6 py-3">Scopes</th>
                  <th className="px-6 py-3">Expires</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {apiKeys.map((key) => {
                  const st = keyStatus(key);
                  return (
                    <tr key={key.id} className="hover:bg-gray-50">
                      <td className="px-6 py-3 font-medium text-gray-900">{key.name}</td>
                      <td className="px-6 py-3 font-mono text-gray-600">{key.key_prefix}...</td>
                      <td className="px-6 py-3 text-gray-600">{(key.scopes ?? []).join(', ')}</td>
                      <td className="px-6 py-3 text-gray-600">{key.expires_at ? formatDate(key.expires_at) : 'Never'}</td>
                      <td className="px-6 py-3"><StatusDot color={st.color} label={st.label} /></td>
                      <td className="px-6 py-3">
                        {key.is_active && !isExpired(key.expires_at) && (
                          <button
                            onClick={() => setRevokeTarget({ type: 'key', id: key.id, name: key.name })}
                            className="text-red-600 hover:text-red-800 text-xs font-medium"
                          >
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* ================================================================ */}
      {/* Contractors Section                                               */}
      {/* ================================================================ */}
      <section className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-purple-600" />
            <h3 className="text-lg font-semibold text-gray-900">Contractors / Testers</h3>
          </div>
          <button
            onClick={() => setShowCreateContractorModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 text-white text-sm font-medium rounded-lg hover:bg-purple-700 transition-colors"
          >
            <Plus className="w-4 h-4" /> Create Contractor
          </button>
        </div>

        <div className="overflow-x-auto">
          {loadingContractors ? (
            <div className="p-6 text-center text-gray-500 text-sm">Loading contractors...</div>
          ) : contractors.length === 0 ? (
            <div className="p-6 text-center text-gray-400 text-sm">No contractors found.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <th className="px-6 py-3">Name</th>
                  <th className="px-6 py-3">Email</th>
                  <th className="px-6 py-3">Role</th>
                  <th className="px-6 py-3">Expires</th>
                  <th className="px-6 py-3">Accounts</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {contractors.map((c) => {
                  const st = contractorStatus(c);
                  const accountDisplay = c.allowed_account_ids
                    ? c.allowed_account_ids.join(', ')
                    : 'All';
                  return (
                    <tr key={c.user_id} className="hover:bg-gray-50">
                      <td className="px-6 py-3 font-medium text-gray-900">{c.user_name}</td>
                      <td className="px-6 py-3 text-gray-600">{c.email}</td>
                      <td className="px-6 py-3 text-gray-600 capitalize">{c.role}</td>
                      <td className="px-6 py-3 text-gray-600">{formatDate(c.expires_at)}</td>
                      <td className="px-6 py-3 text-gray-600">{accountDisplay}</td>
                      <td className="px-6 py-3"><StatusDot color={st.color} label={st.label} /></td>
                      <td className="px-6 py-3">
                        {c.active && !isExpired(c.expires_at) && (
                          <button
                            onClick={() => setRevokeTarget({ type: 'contractor', id: c.user_id, name: c.user_name })}
                            className="text-red-600 hover:text-red-800 text-xs font-medium"
                          >
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* ================================================================ */}
      {/* Security Log Section                                              */}
      {/* ================================================================ */}
      <section className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-gray-600" />
            <h3 className="text-lg font-semibold text-gray-900">Security Log</h3>
          </div>
          <button
            onClick={refreshLog}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-gray-600 text-sm font-medium rounded-lg hover:bg-gray-100 transition-colors border border-gray-300"
          >
            <RefreshCw className={`w-4 h-4 ${loadingLog ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>

        <div className="overflow-x-auto">
          {loadingLog ? (
            <div className="p-6 text-center text-gray-500 text-sm">Loading security log...</div>
          ) : securityLog.length === 0 ? (
            <div className="p-6 text-center text-gray-400 text-sm">No security events found.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <th className="px-6 py-3">Time</th>
                  <th className="px-6 py-3">Action</th>
                  <th className="px-6 py-3">Description</th>
                  <th className="px-6 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {securityLog.map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="px-6 py-3 text-gray-600 whitespace-nowrap">{formatDate(entry.timestamp)}</td>
                    <td className="px-6 py-3 font-medium text-gray-900">{entry.action}</td>
                    <td className="px-6 py-3 text-gray-600">{entry.description}</td>
                    <td className="px-6 py-3">
                      {entry.status === 'success' ? (
                        <span className="inline-flex items-center gap-1 text-green-700 text-xs font-medium">
                          <CheckCircle className="w-3.5 h-3.5" /> Success
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-red-700 text-xs font-medium">
                          <AlertTriangle className="w-3.5 h-3.5" /> {entry.status}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* ================================================================ */}
      {/* Create Key Modal                                                  */}
      {/* ================================================================ */}
      {showCreateKeyModal && (
        <CreateKeyModal
          customerId={customerId}
          onClose={() => setShowCreateKeyModal(false)}
          onCreated={async (fullKey) => {
            setNewKeyRevealed(fullKey);
            setShowCreateKeyModal(false);
            await loadAll();
          }}
        />
      )}

      {/* Revealed key after creation */}
      {newKeyRevealed && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-3">API Key Created</h4>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-3">
              <p className="text-xs text-green-700 mb-2 font-medium">Copy this key now. It will not be shown again.</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-sm font-mono text-green-900 break-all select-all">{newKeyRevealed}</code>
                <button
                  onClick={() => copyToClipboard(newKeyRevealed)}
                  className="p-1.5 bg-green-100 rounded hover:bg-green-200 transition-colors"
                  title="Copy to clipboard"
                >
                  <Copy className="w-4 h-4 text-green-700" />
                </button>
              </div>
            </div>
            <div className="flex items-start gap-2 text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>Store this key securely. If you lose it, you will need to create a new one.</span>
            </div>
            <button
              onClick={() => setNewKeyRevealed(null)}
              className="w-full py-2 bg-gray-800 text-white text-sm font-medium rounded-lg hover:bg-gray-900 transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      )}

      {/* ================================================================ */}
      {/* Create Contractor Modal                                           */}
      {/* ================================================================ */}
      {showCreateContractorModal && (
        <CreateContractorModal
          customerId={customerId}
          onClose={() => setShowCreateContractorModal(false)}
          onCreated={async () => {
            setShowCreateContractorModal(false);
            await loadAll();
          }}
        />
      )}

      {/* ================================================================ */}
      {/* Revoke Confirmation Modal                                         */}
      {/* ================================================================ */}
      {revokeTarget && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <h4 className="text-lg font-semibold text-gray-900">Confirm Revoke</h4>
                <p className="text-sm text-gray-500">This action cannot be undone.</p>
              </div>
            </div>
            <p className="text-sm text-gray-700 mb-6">
              Are you sure you want to revoke{' '}
              <span className="font-medium">{revokeTarget.name}</span>
              ? {revokeTarget.type === 'key'
                ? 'The API key will stop working immediately.'
                : 'The contractor will lose all access and any associated API keys will be revoked.'}
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setRevokeTarget(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleRevoke}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
              >
                Revoke
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ==========================================================================
// Create Key Modal
// ==========================================================================

interface CreateKeyModalProps {
  customerId: number;
  onClose: () => void;
  onCreated: (fullKey: string) => void;
}

const DURATION_OPTIONS = [
  { label: '30 days', value: 30 },
  { label: '60 days', value: 60 },
  { label: '90 days', value: 90 },
  { label: '1 year', value: 365 },
  { label: 'Never', value: 0 },
];

const CreateKeyModal: React.FC<CreateKeyModalProps> = ({ customerId, onClose, onCreated }) => {
  const [keyName, setKeyName] = useState('');
  const [scopes, setScopes] = useState<Record<string, boolean>>({ read: true, write: false, admin: false });
  const [durationDays, setDurationDays] = useState(90);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleScope = (scope: string) => {
    setScopes((prev) => ({ ...prev, [scope]: !prev[scope] }));
  };

  const handleCreate = async () => {
    if (!keyName.trim()) {
      setError('Key name is required.');
      return;
    }
    const selectedScopes = Object.entries(scopes).filter(([, v]) => v).map(([k]) => k);
    if (selectedScopes.length === 0) {
      setError('Select at least one scope.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const result = await generateApiKey(customerId, {
        name: keyName.trim(),
        scopes: selectedScopes,
        duration_days: durationDays || undefined,
      });
      onCreated(result.key);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create API key');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Create API Key</h4>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" /> {error}
          </div>
        )}

        {/* Name */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Key Name</label>
          <input
            type="text"
            value={keyName}
            onChange={(e) => setKeyName(e.target.value)}
            placeholder="e.g. CI/CD Pipeline"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
        </div>

        {/* Scopes */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Scopes</label>
          <div className="flex gap-4">
            {['read', 'write', 'admin'].map((scope) => (
              <label key={scope} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={scopes[scope] ?? false}
                  onChange={() => toggleScope(scope)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="capitalize">{scope}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Duration */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-1">Duration</label>
          <select
            value={durationDays}
            onChange={(e) => setDurationDays(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          >
            {DURATION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={submitting}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {submitting ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ==========================================================================
// Create Contractor Modal
// ==========================================================================

interface CreateContractorModalProps {
  customerId: number;
  onClose: () => void;
  onCreated: () => void;
}

const CONTRACTOR_DURATION_OPTIONS = [
  { label: '30 days', value: 30 },
  { label: '60 days', value: 60 },
  { label: '90 days', value: 90 },
];

const CreateContractorModal: React.FC<CreateContractorModalProps> = ({ customerId, onClose, onCreated }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [role, setRole] = useState('viewer');
  const [durationDays, setDurationDays] = useState(30);
  const [allAccounts, setAllAccounts] = useState(true);
  const [accountIdsText, setAccountIdsText] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdCreds, setCreatedCreds] = useState<{ email: string; password: string; expires_at: string } | null>(null);

  const isTester = role === 'tester';
  const accessLabel = isTester ? 'Customer Access' : 'Account Access';

  const handleGeneratePassword = () => {
    const pw = generateRandomPassword(16);
    setPassword(pw);
    setShowPassword(true);
  };

  const handleCreate = async () => {
    if (!name.trim()) { setError('Name is required.'); return; }
    if (!email.trim()) { setError('Email is required.'); return; }
    if (!password.trim()) { setError('Password is required.'); return; }

    let parsedIds: number[] | null = null;
    if (!allAccounts && accountIdsText.trim()) {
      const parts = accountIdsText.split(',').map((s) => s.trim()).filter(Boolean);
      parsedIds = parts.map(Number).filter((n) => !isNaN(n) && n > 0);
      if (parsedIds.length === 0) {
        setError('Please enter valid numeric IDs separated by commas.');
        return;
      }
    }

    setSubmitting(true);
    setError(null);
    try {
      const result = await createContractorAccess(customerId, {
        contractor_name: name.trim(),
        contractor_email: email.trim(),
        password: password,
        role,
        duration_days: durationDays,
        ...(isTester
          ? { allowed_customer_ids: allAccounts ? null : parsedIds }
          : { allowed_account_ids: allAccounts ? null : parsedIds }),
        notes: notes.trim() || undefined,
      });
      setCreatedCreds({ email: result.email, password, expires_at: result.expires_at });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create contractor');
    } finally {
      setSubmitting(false);
    }
  };

  const copyCredentials = () => {
    if (!createdCreds) return;
    const text = `Email: ${createdCreds.email}\nPassword: ${password}\nExpires: ${formatDate(createdCreds.expires_at)}`;
    navigator.clipboard.writeText(text).catch(() => { /* ignore */ });
  };

  // Success view
  if (createdCreds) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-3">Contractor Created</h4>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-3">
            <p className="text-xs text-green-700 mb-2 font-medium">Share these credentials securely. The password will not be shown again.</p>
            <div className="space-y-1 font-mono text-sm text-green-900">
              <div><span className="text-green-600">Email:</span> {createdCreds.email}</div>
              <div><span className="text-green-600">Password:</span> {password}</div>
              <div><span className="text-green-600">Expires:</span> {formatDate(createdCreds.expires_at)}</div>
            </div>
            <button
              onClick={copyCredentials}
              className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 bg-green-100 text-green-700 text-xs font-medium rounded hover:bg-green-200 transition-colors"
            >
              <Copy className="w-3.5 h-3.5" /> Copy Credentials
            </button>
          </div>
          <button
            onClick={onCreated}
            className="w-full py-2 bg-gray-800 text-white text-sm font-medium rounded-lg hover:bg-gray-900 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <h4 className="text-lg font-semibold text-gray-900 mb-4">Create Contractor / Tester Access</h4>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" /> {error}
          </div>
        )}

        {/* Name */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Contractor Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Jane Doe"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none"
          />
        </div>

        {/* Email */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="contractor@example.com"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none"
          />
        </div>

        {/* Password */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter or generate a password"
                className="w-full px-3 py-2 pr-9 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <button
              type="button"
              onClick={handleGeneratePassword}
              className="px-3 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors whitespace-nowrap"
            >
              Generate
            </button>
          </div>
        </div>

        {/* Role */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none"
          >
            <option value="viewer">Viewer</option>
            <option value="csm">CSM</option>
            <option value="tester">Tester</option>
          </select>
        </div>

        {/* Duration */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Duration</label>
          <select
            value={durationDays}
            onChange={(e) => setDurationDays(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none"
          >
            {CONTRACTOR_DURATION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Account / Customer Access */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">{accessLabel}</label>
          <div className="flex items-center gap-3 mb-2">
            <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={allAccounts}
                onChange={(e) => setAllAccounts(e.target.checked)}
                className="rounded border-gray-300 text-purple-600 focus:ring-purple-500"
              />
              {isTester ? 'All Customers' : 'All Accounts'}
            </label>
          </div>
          {!allAccounts && (
            <input
              type="text"
              value={accountIdsText}
              onChange={(e) => setAccountIdsText(e.target.value)}
              placeholder={isTester ? 'e.g. 1, 2, 3' : 'e.g. 101, 102, 103'}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none"
            />
          )}
        </div>

        {/* Notes */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="Any additional context..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none resize-none"
          />
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={submitting}
            className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
          >
            {submitting ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SecurityKeysPanel;
