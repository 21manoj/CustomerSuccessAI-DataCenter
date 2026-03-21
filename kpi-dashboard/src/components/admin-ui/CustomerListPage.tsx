import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Search,
  Plus,
  ChevronLeft,
  ChevronRight,
  Loader2,
  AlertTriangle,
  RefreshCw,
  X,
  Trash2,
  AlertCircle,
} from 'lucide-react';
import {
  fetchCustomers,
  fetchVerticals,
  createCustomer,
  type Customer,
  type VerticalInfo,
  type CreateCustomerPayload,
} from '../../api/adminApi';

// ---------------------------------------------------------------------------
// Create Customer Modal
// ---------------------------------------------------------------------------

interface CreateModalProps {
  verticals: string[];
  onClose: () => void;
  onCreated: (customerId: number, apiKey: string) => void;
}

const CreateCustomerModal: React.FC<CreateModalProps> = ({ verticals, onClose, onCreated }) => {
  const [form, setForm] = useState<CreateCustomerPayload>({
    company_name: '',
    admin_email: '',
    admin_name: '',
    password: '',
    vertical: verticals[0] ?? 'dc2_s',
    tier: 'enterprise',
    domain: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await createCustomer(form);
      onCreated(result.customer_id, result.api_key);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to create customer');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Create Customer</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Company Name *</label>
            <input
              name="company_name"
              value={form.company_name}
              onChange={handleChange}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              placeholder="Acme Corp"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Admin Name *</label>
              <input
                name="admin_name"
                value={form.admin_name}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                placeholder="John Doe"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Admin Email *</label>
              <input
                name="admin_email"
                type="email"
                value={form.admin_email}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                placeholder="admin@acme.com"
              />
            </div>
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
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              placeholder="Min 8 characters"
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Vertical *</label>
              <select
                name="vertical"
                value={form.vertical}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              >
                {verticals.map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tier *</label>
              <select
                name="tier"
                value={form.tier ?? 'enterprise'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              >
                <option value="starter">Starter (10 KPIs)</option>
                <option value="professional">Professional (20 KPIs)</option>
                <option value="enterprise">Enterprise (All KPIs)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Domain</label>
              <input
                name="domain"
                value={form.domain ?? ''}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                placeholder="acme.com"
              />
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
              disabled={submitting}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {submitting && <Loader2 size={14} className="animate-spin" />}
              Create Customer
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// API Key Reveal Modal
// ---------------------------------------------------------------------------

interface ApiKeyRevealProps {
  apiKey: string;
  customerId: number;
  onClose: () => void;
}

const ApiKeyRevealModal: React.FC<ApiKeyRevealProps> = ({ apiKey, customerId, onClose }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
    <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">Customer Created</h3>
      <p className="text-sm text-gray-600 mb-4">
        Customer #{customerId} has been created. Copy the API key below -- it will not be shown again.
      </p>
      <div className="bg-gray-900 text-green-400 rounded-lg px-4 py-3 font-mono text-sm break-all select-all mb-4">
        {apiKey}
      </div>
      <div className="flex justify-end">
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
        >
          Done
        </button>
      </div>
    </div>
  </div>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const PAGE_SIZE = 20;

const CustomerListPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [verticalFilter, setVerticalFilter] = useState('');
  const [verticals, setVerticals] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [showCreate, setShowCreate] = useState(false);
  const [revealKey, setRevealKey] = useState<{ key: string; id: number } | null>(null);

  // Bulk select & cleanup
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [orphans, setOrphans] = useState<any[]>([]);
  const [showOrphans, setShowOrphans] = useState(false);
  const [orphanLoading, setOrphanLoading] = useState(false);

  const toggleSelect = (id: number) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === customers.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(customers.filter(c => c.customer_id !== 1).map(c => c.customer_id)));
    }
  };

  const bulkDelete = async () => {
    if (selected.size === 0) return;
    if (!window.confirm(`Permanently delete ${selected.size} customer(s) and ALL their data? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      const resp = await fetch('/api/admin-ui/customers/bulk-purge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_ids: Array.from(selected) }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setSelected(new Set());
        loadCustomers();
      } else {
        setError(data.error || 'Bulk delete failed');
      }
    } catch (err: any) {
      setError(err.message || 'Bulk delete failed');
    } finally {
      setDeleting(false);
    }
  };

  const detectOrphans = async () => {
    setOrphanLoading(true);
    try {
      const resp = await fetch('/api/admin-ui/customers/orphans');
      const data = await resp.json();
      setOrphans(data.orphans || []);
      setShowOrphans(true);
    } catch {
      setError('Failed to detect orphans');
    } finally {
      setOrphanLoading(false);
    }
  };

  const selectOrphans = () => {
    setSelected(new Set(orphans.map((o: any) => o.customer_id)));
    setShowOrphans(false);
  };

  // Load verticals once
  useEffect(() => {
    fetchVerticals()
      .then((data: VerticalInfo[]) => setVerticals(data.map((v) => v.vertical)))
      .catch(() => {
        /* ignore -- filter will just be empty */
      });
  }, []);

  // Open create modal if navigated with state
  useEffect(() => {
    if ((location.state as any)?.openCreate) {
      setShowCreate(true);
      // Clear the state so refresh doesn't re-open
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  // Fetch customers
  const loadCustomers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchCustomers({
        search: search || undefined,
        vertical: verticalFilter || undefined,
        page,
      });
      setCustomers(result.customers);
      setTotal(result.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load customers');
    } finally {
      setLoading(false);
    }
  }, [search, verticalFilter, page]);

  useEffect(() => {
    loadCustomers();
  }, [loadCustomers]);

  // Debounced search
  const [searchInput, setSearchInput] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const handleCreated = (customerId: number, apiKey: string) => {
    setShowCreate(false);
    setRevealKey({ key: apiKey, id: customerId });
    loadCustomers();
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Customers</h2>
          <p className="text-sm text-gray-500 mt-0.5">{total} total customers</p>
        </div>
        <div className="flex items-center gap-2 self-start">
          {selected.size > 0 && (
            <button
              onClick={bulkDelete}
              disabled={deleting}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50"
            >
              {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
              Delete {selected.size} Selected
            </button>
          )}
          <button
            onClick={detectOrphans}
            disabled={orphanLoading}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-lg hover:bg-amber-100 disabled:opacity-50"
          >
            {orphanLoading ? <Loader2 size={14} className="animate-spin" /> : <AlertCircle size={14} />}
            Find Orphans
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
          >
            <Plus size={16} /> New Customer
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by name or domain..."
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
          />
        </div>
        <select
          value={verticalFilter}
          onChange={(e) => {
            setVerticalFilter(e.target.value);
            setPage(1);
          }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
        >
          <option value="">All Verticals</option>
          {verticals.map((v) => (
            <option key={v} value={v}>{v}</option>
          ))}
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          <AlertTriangle size={16} />
          {error}
          <button
            onClick={loadCustomers}
            className="ml-auto inline-flex items-center gap-1 text-red-600 hover:text-red-800 font-medium"
          >
            <RefreshCw size={14} /> Retry
          </button>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
            <span className="ml-3 text-sm text-gray-500">Loading customers...</span>
          </div>
        ) : customers.length === 0 ? (
          <div className="text-center py-16 text-sm text-gray-400">
            No customers found.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-gray-500 border-b border-gray-100">
                  <th className="px-3 py-3 w-10">
                    <input
                      type="checkbox"
                      checked={selected.size > 0 && selected.size === customers.filter(c => c.customer_id !== 1).length}
                      onChange={toggleSelectAll}
                      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                  </th>
                  <th className="px-4 py-3 font-medium">ID</th>
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Vertical</th>
                  <th className="px-4 py-3 font-medium">Domain</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                  <th className="px-4 py-3 font-medium">Reference</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {customers.map((c) => (
                  <tr
                    key={c.customer_id}
                    className={`hover:bg-indigo-50/50 cursor-pointer transition-colors ${selected.has(c.customer_id) ? 'bg-red-50' : ''}`}
                  >
                    <td className="px-3 py-3" onClick={(e) => e.stopPropagation()}>
                      {c.customer_id !== 1 && (
                        <input
                          type="checkbox"
                          checked={selected.has(c.customer_id)}
                          onChange={() => toggleSelect(c.customer_id)}
                          className="rounded border-gray-300 text-red-600 focus:ring-red-500"
                        />
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs font-mono" onClick={() => navigate(`/admin/customers/${c.customer_id}`)}>
                      {c.customer_id}
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900 whitespace-nowrap" onClick={() => navigate(`/admin/customers/${c.customer_id}`)}>
                      {c.customer_name}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap" onClick={() => navigate(`/admin/customers/${c.customer_id}`)}>
                      <span className="inline-flex px-2 py-0.5 bg-indigo-50 text-indigo-700 text-xs font-medium rounded-full">
                        {c.vertical}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 whitespace-nowrap" onClick={() => navigate(`/admin/customers/${c.customer_id}`)}>{c.domain || '--'}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap" onClick={() => navigate(`/admin/customers/${c.customer_id}`)}>
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3" onClick={() => navigate(`/admin/customers/${c.customer_id}`)}>
                      {c.is_reference && (
                        <span className="inline-flex px-2 py-0.5 bg-amber-50 text-amber-700 text-xs font-medium rounded-full">
                          Ref
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!loading && totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
            <span className="text-sm text-gray-500">
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft size={14} className="mr-1" /> Prev
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="inline-flex items-center px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next <ChevronRight size={14} className="ml-1" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {showCreate && (
        <CreateCustomerModal
          verticals={verticals.length > 0 ? verticals : ['dc2_s', 'saas_premium']}
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}
      {revealKey && (
        <ApiKeyRevealModal
          apiKey={revealKey.key}
          customerId={revealKey.id}
          onClose={() => {
            setRevealKey(null);
            navigate(`/admin/customers/${revealKey.id}`);
          }}
        />
      )}

      {/* Orphan Detection Modal */}
      {showOrphans && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">
                Orphaned Customers ({orphans.length})
              </h3>
              <button onClick={() => setShowOrphans(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <div className="overflow-y-auto flex-1 px-6 py-4">
              {orphans.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-8">No orphaned customers found.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="py-2">ID</th>
                      <th className="py-2">Name</th>
                      <th className="py-2">Accounts</th>
                      <th className="py-2">Users</th>
                      <th className="py-2">Issues</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {orphans.map((o: any) => (
                      <tr key={o.customer_id} className="hover:bg-red-50">
                        <td className="py-2 font-mono text-xs text-gray-400">{o.customer_id}</td>
                        <td className="py-2 font-medium">{o.name}</td>
                        <td className="py-2">{o.accounts}</td>
                        <td className="py-2">{o.users}</td>
                        <td className="py-2">
                          {o.reasons.map((r: string) => (
                            <span key={r} className="inline-flex px-1.5 py-0.5 bg-red-50 text-red-600 text-xs rounded mr-1">
                              {r}
                            </span>
                          ))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            {orphans.length > 0 && (
              <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
                <button
                  onClick={() => setShowOrphans(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={selectOrphans}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
                >
                  Select All {orphans.length} for Deletion
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CustomerListPage;
