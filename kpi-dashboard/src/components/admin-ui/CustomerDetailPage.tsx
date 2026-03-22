import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Save,
  Plus,
  Trash2,
  X,
  Copy,
  CheckCircle2,
  XCircle,
  Shield,
  Key,
  User,
  Settings,
  FileText,
  Activity,
  Users,
  Mail,
} from 'lucide-react';
import {
  fetchCustomer,
  updateCustomer,
  deactivateCustomer,
  reactivateCustomer,
  fetchUsers,
  createUser,
  updateUser,
  fetchLicense,
  updateLicense,
  fetchApiKeys,
  generateApiKey,
  revokeApiKey,
  fetchCustomerConfig,
  fetchResolvedConfig,
  updateCustomerConfig,
  deleteCustomerConfig,
  fetchActivityLog,
  fetchCustomerAccounts,
  createPartnerKey,
  fetchPartnerAuditLog,
  type CustomerDetail,
  type UserInfo,
  type LicenseInfo,
  type SeatUsage,
  type ApiKeyInfo,
  type CustomerConfig,
  type ResolvedConfig,
  type CreateUserPayload,
  type ActivityEntry,
  type AccountSummary,
  type PartnerKeyResult,
  type PartnerAuditEntry,
} from '../../api/adminApi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type TabKey = 'info' | 'users' | 'config' | 'license' | 'api-keys' | 'partners' | 'activity';

interface TabDef {
  key: TabKey;
  label: string;
  icon: React.ReactNode;
}

const TABS: TabDef[] = [
  { key: 'info', label: 'Info', icon: <FileText size={16} /> },
  { key: 'users', label: 'Users', icon: <User size={16} /> },
  { key: 'config', label: 'Config', icon: <Settings size={16} /> },
  { key: 'license', label: 'License', icon: <Shield size={16} /> },
  { key: 'api-keys', label: 'API Keys', icon: <Key size={16} /> },
  { key: 'partners', label: 'Partners', icon: <Users size={16} /> },
  { key: 'activity', label: 'Activity', icon: <Activity size={16} /> },
];

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const CustomerDetailPage: React.FC = () => {
  const { customerId: rawId } = useParams<{ customerId: string }>();
  const customerId = Number(rawId);
  const navigate = useNavigate();

  const [customer, setCustomer] = useState<CustomerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('info');

  const loadCustomer = useCallback(async () => {
    if (!customerId || isNaN(customerId)) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCustomer(customerId);
      setCustomer(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load customer');
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    loadCustomer();
  }, [loadCustomer]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        <span className="ml-3 text-gray-500">Loading customer...</span>
      </div>
    );
  }

  if (error || !customer) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertTriangle className="w-10 h-10 text-red-400 mb-3" />
        <p className="text-red-600 font-medium mb-4">{error || 'Customer not found'}</p>
        <button
          onClick={loadCustomer}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
        >
          <RefreshCw size={16} /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Back + Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/admin/customers')}
          className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
        >
          <ArrowLeft size={20} />
        </button>
        <div>
          <h2 className="text-xl font-bold text-gray-900">{customer.customer_name}</h2>
          <p className="text-sm text-gray-500">
            ID {customer.customer_id} &middot; {customer.vertical} &middot; {customer.domain || 'No domain'}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-1 -mb-px overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                activeTab === tab.key
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'info' && (
          <InfoTab customer={customer} onUpdated={loadCustomer} />
        )}
        {activeTab === 'users' && <UsersTab customerId={customerId} />}
        {activeTab === 'config' && <ConfigTab customerId={customerId} />}
        {activeTab === 'license' && <LicenseTab customerId={customerId} />}
        {activeTab === 'api-keys' && <ApiKeysTab customerId={customerId} />}
        {activeTab === 'partners' && <PartnersTab customerId={customerId} />}
        {activeTab === 'activity' && <ActivityTab customerId={customerId} />}
      </div>
    </div>
  );
};

// ===========================================================================
// INFO TAB
// ===========================================================================

const InfoTab: React.FC<{ customer: CustomerDetail; onUpdated: () => void }> = ({
  customer,
  onUpdated,
}) => {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    customer_name: customer.customer_name,
    domain: customer.domain,
  });
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const handleSave = async () => {
    setSaving(true);
    setMsg(null);
    try {
      await updateCustomer(customer.customer_id, form);
      setEditing(false);
      setMsg('Saved successfully');
      onUpdated();
    } catch (err: unknown) {
      setMsg(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async () => {
    setActionLoading(true);
    setMsg(null);
    try {
      if (customer.is_reference) {
        // Reference customers cannot be deactivated -- treat as already active
        setMsg('Reference customers cannot be deactivated');
      } else {
        // We check a rough heuristic: the presence of a deactivated timestamp
        // isn't part of the Customer interface, so we use a toggle approach.
        await deactivateCustomer(customer.customer_id);
        setMsg('Customer deactivated');
      }
      onUpdated();
    } catch (err: unknown) {
      // If deactivate fails, try reactivate
      try {
        await reactivateCustomer(customer.customer_id);
        setMsg('Customer reactivated');
        onUpdated();
      } catch {
        setMsg(err instanceof Error ? err.message : 'Action failed');
      }
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 max-w-2xl">
      <h3 className="text-base font-semibold text-gray-900 mb-4">Customer Information</h3>

      <div className="space-y-4">
        <FieldRow label="Customer ID" value={String(customer.customer_id)} />
        <FieldRow label="Vertical" value={customer.vertical} />
        <FieldRow label="Created" value={new Date(customer.created_at).toLocaleString()} />
        <FieldRow
          label="Reference"
          value={customer.is_reference ? 'Yes' : 'No'}
        />

        {editing ? (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                value={form.customer_name}
                onChange={(e) => setForm((f) => ({ ...f, customer_name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Domain</label>
              <input
                value={form.domain}
                onChange={(e) => setForm((f) => ({ ...f, domain: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleSave}
                disabled={saving}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                Save
              </button>
              <button
                onClick={() => setEditing(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </>
        ) : (
          <>
            <FieldRow label="Name" value={customer.customer_name} />
            <FieldRow label="Domain" value={customer.domain || '--'} />
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => setEditing(true)}
                className="px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100"
              >
                Edit
              </button>
              <button
                onClick={handleToggleActive}
                disabled={actionLoading}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 disabled:opacity-50"
              >
                {actionLoading && <Loader2 size={14} className="animate-spin" />}
                Deactivate / Reactivate
              </button>
            </div>
          </>
        )}

        {msg && (
          <p className="text-sm text-gray-600 bg-gray-50 px-3 py-2 rounded-lg">{msg}</p>
        )}
      </div>
    </div>
  );
};

const FieldRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="flex items-start">
    <span className="w-32 flex-shrink-0 text-sm font-medium text-gray-500">{label}</span>
    <span className="text-sm text-gray-900">{value}</span>
  </div>
);

// ===========================================================================
// USERS TAB
// ===========================================================================

const UsersTab: React.FC<{ customerId: number }> = ({ customerId }) => {
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setUsers(await fetchUsers(customerId));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleToggleActive = async (user: UserInfo) => {
    try {
      await updateUser(user.user_id, { active: !user.active });
      load();
    } catch {
      /* silent retry on next refresh */
    }
  };

  if (loading) return <TabLoading label="users" />;
  if (error) return <TabError message={error} onRetry={load} />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-900">Users ({users.length})</h3>
        <button
          onClick={() => setShowAdd(true)}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
        >
          <Plus size={14} /> Add User
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-gray-500 border-b border-gray-100">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Email</th>
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Active</th>
              <th className="px-4 py-3 font-medium">Last Login</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {users.map((u) => (
              <tr key={u.user_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{u.user_name}</td>
                <td className="px-4 py-3 text-gray-600">{u.email}</td>
                <td className="px-4 py-3">
                  <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-indigo-50 text-indigo-700">
                    {u.role}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {u.active ? (
                    <CheckCircle2 size={16} className="text-green-500" />
                  ) : (
                    <XCircle size={16} className="text-gray-300" />
                  )}
                </td>
                <td className="px-4 py-3 text-gray-500">
                  {u.last_login ? new Date(u.last_login).toLocaleString() : 'Never'}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => handleToggleActive(u)}
                    className={`text-xs font-medium px-2 py-1 rounded ${
                      u.active
                        ? 'text-red-600 bg-red-50 hover:bg-red-100'
                        : 'text-green-600 bg-green-50 hover:bg-green-100'
                    }`}
                  >
                    {u.active ? 'Deactivate' : 'Activate'}
                  </button>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  No users found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showAdd && (
        <AddUserModal
          customerId={customerId}
          onClose={() => setShowAdd(false)}
          onCreated={() => {
            setShowAdd(false);
            load();
          }}
        />
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Add User Modal
// ---------------------------------------------------------------------------

const AddUserModal: React.FC<{
  customerId: number;
  onClose: () => void;
  onCreated: () => void;
}> = ({ customerId, onClose, onCreated }) => {
  const [form, setForm] = useState<CreateUserPayload>({
    user_name: '',
    email: '',
    role: 'viewer',
    password: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      await createUser(customerId, form);
      onCreated();
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create user');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Add User</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              name="user_name"
              value={form.user_name}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Role *</label>
            <select
              name="role"
              value={form.role}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            >
              <option value="admin">Admin</option>
              <option value="csm">CSM</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password *</label>
            <input
              name="password"
              type="password"
              value={form.password}
              onChange={handleChange}
              required
              minLength={8}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          {submitError && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{submitError}</p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {submitting && <Loader2 size={14} className="animate-spin" />}
              Create User
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ===========================================================================
// CONFIG TAB
// ===========================================================================

const ConfigTab: React.FC<{ customerId: number }> = ({ customerId }) => {
  const [configs, setConfigs] = useState<CustomerConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [resolved, setResolved] = useState<ResolvedConfig | null>(null);
  const [editJson, setEditJson] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setConfigs(await fetchCustomerConfig(customerId));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load config');
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSelectConfig = async (configType: string) => {
    setSelected(configType);
    setSaveMsg(null);
    try {
      const res = await fetchResolvedConfig(customerId, configType);
      setResolved(res);
      setEditJson(JSON.stringify(res.config, null, 2));
    } catch {
      setResolved(null);
      setEditJson('');
    }
  };

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      const parsed = JSON.parse(editJson);
      await updateCustomerConfig(customerId, selected, parsed);
      setSaveMsg('Config saved');
      load();
    } catch (err: unknown) {
      setSaveMsg(err instanceof Error ? err.message : 'Invalid JSON or save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (configType: string) => {
    if (!window.confirm(`Delete override for "${configType}"? The customer will fall back to the vertical template.`)) return;
    try {
      await deleteCustomerConfig(customerId, configType);
      setSelected(null);
      setResolved(null);
      load();
    } catch {
      /* silent */
    }
  };

  if (loading) return <TabLoading label="config" />;
  if (error) return <TabError message={error} onRetry={load} />;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Config list */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3">
          Config Overrides ({configs.length})
        </h3>
        {configs.length === 0 ? (
          <p className="text-sm text-gray-400">No overrides. Using vertical templates.</p>
        ) : (
          <ul className="space-y-1">
            {configs.map((c) => (
              <li key={c.config_type}>
                <button
                  onClick={() => handleSelectConfig(c.config_type)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selected === c.config_type
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {c.config_type}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Editor + diff */}
      <div className="lg:col-span-2 space-y-4">
        {selected && resolved ? (
          <>
            {/* Side-by-side diff */}
            {resolved.template_config && (
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                    Template (base)
                  </h4>
                  <pre className="text-xs text-gray-600 overflow-auto max-h-64 bg-gray-50 rounded-lg p-3">
                    {JSON.stringify(resolved.template_config, null, 2)}
                  </pre>
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                  <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                    Customer Override
                  </h4>
                  <pre className="text-xs text-gray-600 overflow-auto max-h-64 bg-gray-50 rounded-lg p-3">
                    {JSON.stringify(resolved.config, null, 2)}
                  </pre>
                </div>
              </div>
            )}

            {/* JSON editor */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-semibold text-gray-700">
                  Edit: {selected}
                </h4>
                <div className="flex gap-2">
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                    Save
                  </button>
                  <button
                    onClick={() => handleDelete(selected)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100"
                  >
                    <Trash2 size={14} /> Delete Override
                  </button>
                </div>
              </div>
              <textarea
                value={editJson}
                onChange={(e) => setEditJson(e.target.value)}
                rows={16}
                spellCheck={false}
                className="w-full font-mono text-xs p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none resize-y"
              />
              {saveMsg && (
                <p className="text-sm mt-2 text-gray-600 bg-gray-50 px-3 py-2 rounded-lg">{saveMsg}</p>
              )}
            </div>
          </>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center text-gray-400 text-sm">
            Select a config override from the list to view and edit.
          </div>
        )}
      </div>
    </div>
  );
};

// ===========================================================================
// LICENSE TAB
// ===========================================================================

const LicenseTab: React.FC<{ customerId: number }> = ({ customerId }) => {
  const [license, setLicense] = useState<(LicenseInfo & SeatUsage) | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<LicenseInfo>>({});
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchLicense(customerId);
      setLicense(data);
      setForm({
        license_type: data.license_type,
        max_seats: data.max_seats,
        max_accounts: data.max_accounts,
        license_end: data.license_end,
        auto_renew: data.auto_renew,
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load license');
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg(null);
    try {
      await updateLicense(customerId, form);
      setSaveMsg('License updated');
      setEditing(false);
      load();
    } catch (err: unknown) {
      setSaveMsg(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <TabLoading label="license" />;
  if (error) return <TabError message={error} onRetry={load} />;
  if (!license) return <p className="text-gray-400 text-sm">No license data.</p>;

  const seatPct = license.utilization_pct;

  return (
    <div className="max-w-2xl space-y-6">
      {/* License card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-4">
        <h3 className="text-base font-semibold text-gray-900">License</h3>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <FieldRow label="Type" value={license.license_type} />
          <FieldRow label="Auto-Renew" value={license.auto_renew ? 'Yes' : 'No'} />
          <FieldRow label="Start" value={new Date(license.license_start).toLocaleDateString()} />
          <FieldRow label="End" value={new Date(license.license_end).toLocaleDateString()} />
          <FieldRow label="Max Accounts" value={license.max_accounts != null ? String(license.max_accounts) : 'Unlimited'} />
        </div>

        {/* Seat usage bar */}
        <div>
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-gray-600 font-medium">Seat Usage</span>
            <span className="text-gray-500">
              {license.used} / {license.max} ({seatPct.toFixed(0)}%)
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all ${
                seatPct >= 90 ? 'bg-red-500' : seatPct >= 75 ? 'bg-amber-500' : 'bg-green-500'
              }`}
              style={{ width: `${Math.min(100, seatPct)}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 mt-1">{license.available} seats available</p>
        </div>

        {/* Edit form */}
        {editing ? (
          <div className="space-y-3 pt-2 border-t border-gray-100">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">License Type</label>
                <input
                  value={form.license_type ?? ''}
                  onChange={(e) => setForm((f) => ({ ...f, license_type: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Max Seats</label>
                <input
                  type="number"
                  value={form.max_seats ?? 0}
                  onChange={(e) => setForm((f) => ({ ...f, max_seats: Number(e.target.value) }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">End Date</label>
                <input
                  type="date"
                  value={form.license_end ? form.license_end.slice(0, 10) : ''}
                  onChange={(e) => setForm((f) => ({ ...f, license_end: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={form.auto_renew ?? false}
                    onChange={(e) => setForm((f) => ({ ...f, auto_renew: e.target.checked }))}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  Auto-Renew
                </label>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleSave}
                disabled={saving}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                Save
              </button>
              <button
                onClick={() => setEditing(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setEditing(true)}
            className="px-4 py-2 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100"
          >
            Edit License
          </button>
        )}

        {saveMsg && (
          <p className="text-sm text-gray-600 bg-gray-50 px-3 py-2 rounded-lg">{saveMsg}</p>
        )}
      </div>
    </div>
  );
};

// ===========================================================================
// API KEYS TAB
// ===========================================================================

const ApiKeysTab: React.FC<{ customerId: number }> = ({ customerId }) => {
  const [keys, setKeys] = useState<ApiKeyInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showGenerate, setShowGenerate] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setKeys(await fetchApiKeys(customerId));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load API keys');
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleRevoke = async (keyId: number) => {
    if (!window.confirm('Revoke this API key? This cannot be undone.')) return;
    try {
      await revokeApiKey(keyId);
      load();
    } catch {
      /* silent */
    }
  };

  if (loading) return <TabLoading label="API keys" />;
  if (error) return <TabError message={error} onRetry={load} />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-900">API Keys ({keys.length})</h3>
        <button
          onClick={() => setShowGenerate(true)}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
        >
          <Plus size={14} /> Generate Key
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-gray-500 border-b border-gray-100">
              <th className="px-4 py-3 font-medium">Prefix</th>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Scopes</th>
              <th className="px-4 py-3 font-medium">Active</th>
              <th className="px-4 py-3 font-medium">Last Used</th>
              <th className="px-4 py-3 font-medium">Created</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {keys.map((k) => (
              <tr key={k.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-gray-900">{k.key_prefix}...</td>
                <td className="px-4 py-3 text-gray-700">{k.name}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {k.scopes.map((s) => (
                      <span key={s} className="inline-flex px-1.5 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                        {s}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3">
                  {k.is_active ? (
                    <CheckCircle2 size={16} className="text-green-500" />
                  ) : (
                    <XCircle size={16} className="text-gray-300" />
                  )}
                </td>
                <td className="px-4 py-3 text-gray-500">
                  {k.last_used_at ? new Date(k.last_used_at).toLocaleString() : 'Never'}
                </td>
                <td className="px-4 py-3 text-gray-500">
                  {new Date(k.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3">
                  {k.is_active && (
                    <button
                      onClick={() => handleRevoke(k.id)}
                      className="text-xs font-medium px-2 py-1 rounded text-red-600 bg-red-50 hover:bg-red-100"
                    >
                      Revoke
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {keys.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  No API keys generated.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Generate key modal */}
      {showGenerate && (
        <GenerateKeyModal
          customerId={customerId}
          onClose={() => setShowGenerate(false)}
          onGenerated={(key) => {
            setShowGenerate(false);
            setNewKey(key);
            load();
          }}
        />
      )}

      {/* Show new key once */}
      {newKey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">API Key Generated</h3>
            <p className="text-sm text-gray-600 mb-4">
              Copy this key now -- it will not be shown again.
            </p>
            <div className="flex items-center gap-2 bg-gray-900 text-green-400 rounded-lg px-4 py-3 font-mono text-sm break-all">
              <span className="flex-1 select-all">{newKey}</span>
              <button
                onClick={() => navigator.clipboard.writeText(newKey)}
                className="text-gray-400 hover:text-white flex-shrink-0"
                title="Copy to clipboard"
              >
                <Copy size={16} />
              </button>
            </div>
            <div className="flex justify-end mt-4">
              <button
                onClick={() => setNewKey(null)}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Generate Key Modal
// ---------------------------------------------------------------------------

const AVAILABLE_SCOPES = ['read', 'write', 'admin', 'ingest', 'export'];

const GenerateKeyModal: React.FC<{
  customerId: number;
  onClose: () => void;
  onGenerated: (key: string) => void;
}> = ({ customerId, onClose, onGenerated }) => {
  const [name, setName] = useState('');
  const [scopes, setScopes] = useState<string[]>(['read']);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const toggleScope = (scope: string) => {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope],
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await generateApiKey(customerId, { name, scopes });
      onGenerated(result.key);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to generate key');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Generate API Key</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Key Name *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              placeholder="e.g. Load Driver Key"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Scopes *</label>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_SCOPES.map((scope) => (
                <label
                  key={scope}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg cursor-pointer border transition-colors ${
                    scopes.includes(scope)
                      ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                      : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={scopes.includes(scope)}
                    onChange={() => toggleScope(scope)}
                    className="sr-only"
                  />
                  {scope}
                </label>
              ))}
            </div>
          </div>
          {submitError && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{submitError}</p>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || scopes.length === 0}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {submitting && <Loader2 size={14} className="animate-spin" />}
              Generate
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ===========================================================================
// PARTNERS TAB
// ===========================================================================

const PARTNER_TIERS = [
  { value: 'reseller', label: 'Reseller' },
  { value: 'technology_partner', label: 'Technology Partner' },
  { value: 'direct_enterprise', label: 'Direct Enterprise' },
  { value: 'referral', label: 'Referral' },
];

const PartnersTab: React.FC<{ customerId: number }> = ({ customerId }) => {
  // Existing partner keys
  const [keys, setKeys] = useState<ApiKeyInfo[]>([]);
  const [accounts, setAccounts] = useState<AccountSummary[]>([]);
  const [auditLogs, setAuditLogs] = useState<PartnerAuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New partner form
  const [showForm, setShowForm] = useState(false);
  const [partnerName, setPartnerName] = useState('');
  const [partnerEmail, setPartnerEmail] = useState('');
  const [partnerTier, setPartnerTier] = useState('reseller');
  const [selectedAccounts, setSelectedAccounts] = useState<number[]>([]);
  const [sendEmail, setSendEmail] = useState(true);
  const [durationDays, setDurationDays] = useState(365);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Result
  const [result, setResult] = useState<PartnerKeyResult | null>(null);
  const [copied, setCopied] = useState(false);

  // Audit log view
  const [showAudit, setShowAudit] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [allKeys, accts] = await Promise.all([
        fetchApiKeys(customerId),
        fetchCustomerAccounts(customerId),
      ]);
      // Filter to partner keys only
      setKeys(allKeys.filter((k) => k.partner_tier));
      setAccounts(accts);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load partner data');
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  const loadAudit = useCallback(async () => {
    try {
      const data = await fetchPartnerAuditLog({ customer_id: customerId, limit: 50 });
      setAuditLogs(data.logs);
    } catch {
      /* silent */
    }
  }, [customerId]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleAccount = (id: number) => {
    setSelectedAccounts((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id],
    );
  };

  const selectAll = () => setSelectedAccounts(accounts.map((a) => a.account_id));
  const selectNone = () => setSelectedAccounts([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedAccounts.length === 0) {
      setSubmitError('Select at least one account for partner access');
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await createPartnerKey(customerId, {
        partner_name: partnerName,
        partner_email: partnerEmail,
        partner_tier: partnerTier,
        allowed_account_ids: selectedAccounts,
        scopes: ['read'],
        duration_days: durationDays,
        send_email: sendEmail,
      });
      setResult(res);
      setShowForm(false);
      load(); // Refresh partner keys list
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create partner key');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopyKey = () => {
    if (result?.key) {
      navigator.clipboard.writeText(result.key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) return <TabLoading label="partner data" />;
  if (error) return <TabError message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900">
            Partner Access ({keys.length} active keys)
          </h3>
          <p className="text-sm text-gray-500 mt-0.5">
            Manage partner API keys scoped to P4 (Channel & Partner Health) data
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setShowAudit(!showAudit); if (!showAudit) loadAudit(); }}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <Activity size={14} /> Audit Log
          </button>
          <button
            onClick={() => { setShowForm(true); setResult(null); }}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
          >
            <Plus size={14} /> Enable Partner
          </button>
        </div>
      </div>

      {/* Result banner — shown once after key creation */}
      {result && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 space-y-3">
          <div className="flex items-start gap-3">
            <CheckCircle2 size={20} className="text-green-600 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-green-900">
                Partner key created for {result.partner_name}
              </h4>
              <p className="text-sm text-green-700 mt-1">
                Tier: {result.key_info.partner_tier} &bull;
                Accounts: {result.allowed_accounts.map((a) => a.name).join(', ')}
                {result.email_sent && (
                  <span className="ml-2 inline-flex items-center gap-1 text-green-600">
                    <Mail size={12} /> Email sent to {result.partner_email}
                  </span>
                )}
              </p>
              <div className="mt-2 flex items-center gap-2">
                <code className="bg-green-100 px-3 py-1.5 rounded text-sm font-mono text-green-800 select-all">
                  {result.key}
                </code>
                <button onClick={handleCopyKey} className="text-green-600 hover:text-green-800">
                  {copied ? <CheckCircle2 size={16} /> : <Copy size={16} />}
                </button>
              </div>
              <p className="text-xs text-green-600 mt-1">
                Save this key — it cannot be retrieved after closing this banner.
              </p>
            </div>
            <button onClick={() => setResult(null)} className="text-green-400 hover:text-green-600">
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Active partner keys table */}
      {keys.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-gray-500 border-b border-gray-100">
                <th className="px-4 py-3 font-medium">Partner</th>
                <th className="px-4 py-3 font-medium">Tier</th>
                <th className="px-4 py-3 font-medium">Prefix</th>
                <th className="px-4 py-3 font-medium">Accounts</th>
                <th className="px-4 py-3 font-medium">Scopes</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Last Used</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {keys.map((k) => (
                <tr key={k.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{k.name.replace('Partner: ', '')}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-purple-50 text-purple-700">
                      {k.partner_tier}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-500">{k.key_prefix}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {k.allowed_account_ids ? `${k.allowed_account_ids.length} accounts` : 'All'}
                  </td>
                  <td className="px-4 py-3">
                    {(k.scopes ?? []).map((s) => (
                      <span key={s} className="inline-flex px-1.5 py-0.5 text-xs rounded bg-gray-100 text-gray-600 mr-1">
                        {s}
                      </span>
                    ))}
                  </td>
                  <td className="px-4 py-3">
                    {k.is_active ? (
                      <span className="text-green-600 flex items-center gap-1"><CheckCircle2 size={14} /> Active</span>
                    ) : (
                      <span className="text-red-500 flex items-center gap-1"><XCircle size={14} /> Revoked</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}
                  </td>
                  <td className="px-4 py-3">
                    {k.is_active && (
                      <button
                        onClick={async () => {
                          if (!window.confirm(`Revoke partner key for "${k.name.replace('Partner: ', '')}"?`)) return;
                          await revokeApiKey(k.id);
                          load();
                        }}
                        className="text-red-500 hover:text-red-700 text-xs font-medium"
                      >
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {keys.length === 0 && !showForm && (
        <div className="text-center py-12 bg-gray-50 rounded-xl border border-dashed border-gray-200">
          <Users size={32} className="mx-auto text-gray-400 mb-3" />
          <p className="text-gray-500 text-sm">No partner keys configured yet</p>
          <button
            onClick={() => setShowForm(true)}
            className="mt-3 text-sm text-indigo-600 hover:text-indigo-700 font-medium"
          >
            Enable your first partner
          </button>
        </div>
      )}

      {/* Partner audit log */}
      {showAudit && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <h4 className="font-semibold text-gray-900 mb-3">Partner Audit Log</h4>
          {auditLogs.length === 0 ? (
            <p className="text-sm text-gray-500">No partner audit entries yet.</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {auditLogs.map((log) => (
                <div key={log.id} className="flex items-start gap-3 text-xs border-b border-gray-50 pb-2">
                  <span className="text-gray-400 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                  <span className="inline-flex px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 font-medium">
                    {log.action_type}
                  </span>
                  <span className="text-gray-600 flex-1">{log.action_description}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Enable Partner Form (modal-style inline) */}
      {showForm && (
        <div className="bg-white rounded-xl shadow-sm border border-indigo-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-base font-semibold text-gray-900">Enable Partner Access</h4>
            <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600">
              <X size={18} />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Step 1: Partner info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Partner Name *</label>
                <input
                  value={partnerName}
                  onChange={(e) => setPartnerName(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                  placeholder="e.g. Acme Partners"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Partner Email *</label>
                <input
                  type="email"
                  value={partnerEmail}
                  onChange={(e) => setPartnerEmail(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                  placeholder="ops@acmepartners.com"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Partner Tier *</label>
                <select
                  value={partnerTier}
                  onChange={(e) => setPartnerTier(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                >
                  {PARTNER_TIERS.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Key Duration (days)</label>
                <input
                  type="number"
                  value={durationDays}
                  onChange={(e) => setDurationDays(parseInt(e.target.value) || 365)}
                  min={1}
                  max={730}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
                />
              </div>
            </div>

            {/* Step 2: Account selection */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  Select Accounts for Partner Access *
                  <span className="text-gray-400 font-normal ml-1">
                    ({selectedAccounts.length} of {accounts.length} selected)
                  </span>
                </label>
                <div className="flex gap-2 text-xs">
                  <button type="button" onClick={selectAll} className="text-indigo-600 hover:underline">
                    Select All
                  </button>
                  <span className="text-gray-300">|</span>
                  <button type="button" onClick={selectNone} className="text-indigo-600 hover:underline">
                    Clear
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 max-h-60 overflow-y-auto border border-gray-200 rounded-lg p-3">
                {accounts.map((acct) => (
                  <label
                    key={acct.account_id}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors ${
                      selectedAccounts.includes(acct.account_id)
                        ? 'bg-indigo-50 border border-indigo-200'
                        : 'bg-white border border-gray-100 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedAccounts.includes(acct.account_id)}
                      onChange={() => toggleAccount(acct.account_id)}
                      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <div className="flex-1 min-w-0">
                      <span className="font-medium text-gray-900 truncate block">{acct.account_name}</span>
                      {acct.arr && (
                        <span className="text-xs text-gray-400">
                          ${(acct.arr / 1e6).toFixed(1)}M ARR
                        </span>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Step 3: Email & submit */}
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={sendEmail}
                  onChange={(e) => setSendEmail(e.target.checked)}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                <Mail size={14} className="text-gray-400" />
                Send API key via email to partner
              </label>
            </div>

            {submitError && (
              <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{submitError}</p>
            )}

            <div className="flex justify-end gap-3 pt-2 border-t border-gray-100">
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting || selectedAccounts.length === 0}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {submitting && <Loader2 size={14} className="animate-spin" />}
                Enable Partner Access
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};


// ===========================================================================
// ACTIVITY TAB
// ===========================================================================

const ActivityTab: React.FC<{ customerId: number }> = ({ customerId }) => {
  const [entries, setEntries] = useState<ActivityEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchActivityLog({ customer_id: customerId, page, limit: 20 });
      setEntries(data.entries ?? []);
      setTotal(data.total ?? 0);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load activity');
    } finally {
      setLoading(false);
    }
  }, [customerId, page]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <TabLoading label="activity" />;
  if (error) return <TabError message={error} onRetry={load} />;

  const totalPages = Math.max(1, Math.ceil(total / 20));

  return (
    <div className="space-y-4">
      <h3 className="text-base font-semibold text-gray-900">Activity Log</h3>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-gray-500 border-b border-gray-100">
              <th className="px-4 py-3 font-medium">Time</th>
              <th className="px-4 py-3 font-medium">User</th>
              <th className="px-4 py-3 font-medium">Action</th>
              <th className="px-4 py-3 font-medium">Description</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {entries.map((e) => (
              <tr key={e.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 text-gray-500 whitespace-nowrap">
                  {new Date(e.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-2.5 text-gray-700">{e.user_name ?? '--'}</td>
                <td className="px-4 py-2.5 font-medium text-gray-900">{e.action}</td>
                <td className="px-4 py-2.5 text-gray-600 max-w-xs truncate">{e.description}</td>
                <td className="px-4 py-2.5">
                  <StatusBadge status={e.status} />
                </td>
              </tr>
            ))}
            {entries.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                  No activity recorded.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ===========================================================================
// Shared helpers
// ===========================================================================

const TabLoading: React.FC<{ label: string }> = ({ label }) => (
  <div className="flex items-center justify-center py-16">
    <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
    <span className="ml-3 text-sm text-gray-500">Loading {label}...</span>
  </div>
);

const TabError: React.FC<{ message: string; onRetry: () => void }> = ({ message, onRetry }) => (
  <div className="flex flex-col items-center justify-center py-16 text-center">
    <AlertTriangle className="w-8 h-8 text-red-400 mb-2" />
    <p className="text-red-600 font-medium mb-3">{message}</p>
    <button
      onClick={onRetry}
      className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
    >
      <RefreshCw size={14} /> Retry
    </button>
  </div>
);

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  let classes = 'inline-flex px-2 py-0.5 text-xs font-medium rounded-full';
  switch (status.toLowerCase()) {
    case 'success':
      classes += ' bg-green-100 text-green-700';
      break;
    case 'error':
    case 'failed':
      classes += ' bg-red-100 text-red-700';
      break;
    case 'warning':
      classes += ' bg-amber-100 text-amber-700';
      break;
    default:
      classes += ' bg-gray-100 text-gray-600';
  }
  return <span className={classes}>{status}</span>;
};

export default CustomerDetailPage;
