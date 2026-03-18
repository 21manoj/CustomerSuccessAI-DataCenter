import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Loader2,
  AlertTriangle,
  RefreshCw,
  Save,
  X,
} from 'lucide-react';
import {
  fetchLicenseWarnings,
  updateLicense,
  type LicenseWarning,
} from '../../api/adminApi';

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<string, string> = {
  expired: 'bg-red-100 text-red-700',
  expiring_soon: 'bg-amber-100 text-amber-700',
  over_limit: 'bg-orange-100 text-orange-700',
  ok: 'bg-green-100 text-green-700',
};

const STATUS_LABELS: Record<string, string> = {
  expired: 'Expired',
  expiring_soon: 'Expiring Soon',
  over_limit: 'Over Seat Limit',
  ok: 'OK',
};

const StatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <span
    className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
      STATUS_STYLES[status] ?? 'bg-gray-100 text-gray-600'
    }`}
  >
    {STATUS_LABELS[status] ?? status}
  </span>
);

// ---------------------------------------------------------------------------
// Quick Edit Modal
// ---------------------------------------------------------------------------

interface QuickEditProps {
  warning: LicenseWarning;
  onClose: () => void;
  onSaved: () => void;
}

const QuickEditModal: React.FC<QuickEditProps> = ({ warning, onClose, onSaved }) => {
  const [maxSeats, setMaxSeats] = useState(warning.seats_max);
  const [licenseEnd, setLicenseEnd] = useState(warning.license_end?.slice(0, 10) ?? '');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    try {
      await updateLicense(warning.customer_id, {
        max_seats: maxSeats,
        license_end: licenseEnd,
      });
      onSaved();
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : 'Failed to update license');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Quick Edit License</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSave} className="px-6 py-4 space-y-4">
          <p className="text-sm text-gray-600 font-medium">{warning.customer_name}</p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Seats</label>
            <input
              type="number"
              value={maxSeats}
              onChange={(e) => setMaxSeats(Number(e.target.value))}
              min={1}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">License End Date</label>
            <input
              type="date"
              value={licenseEnd}
              onChange={(e) => setLicenseEnd(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            />
          </div>
          {saveError && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{saveError}</p>
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
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Seat usage bar (inline in table)
// ---------------------------------------------------------------------------

const SeatBar: React.FC<{ used: number; max: number }> = ({ used, max }) => {
  const pct = max > 0 ? (used / max) * 100 : 0;
  const color = pct >= 100 ? 'bg-red-500' : pct >= 80 ? 'bg-amber-500' : 'bg-green-500';

  return (
    <div className="flex items-center gap-2 min-w-[140px]">
      <div className="flex-1 bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 whitespace-nowrap">
        {used}/{max}
      </span>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Sort order for urgency
// ---------------------------------------------------------------------------

const STATUS_PRIORITY: Record<string, number> = {
  expired: 0,
  expiring_soon: 1,
  over_limit: 2,
  ok: 3,
};

function sortByUrgency(a: LicenseWarning, b: LicenseWarning): number {
  const pa = STATUS_PRIORITY[a.status] ?? 99;
  const pb = STATUS_PRIORITY[b.status] ?? 99;
  if (pa !== pb) return pa - pb;
  // Secondary sort: days remaining ascending (null = infinite → end)
  const da = a.days_remaining ?? 99999;
  const db = b.days_remaining ?? 99999;
  return da - db;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const LicenseManagerPage: React.FC = () => {
  const navigate = useNavigate();
  const [warnings, setWarnings] = useState<LicenseWarning[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editTarget, setEditTarget] = useState<LicenseWarning | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchLicenseWarnings();
      setWarnings([...data].sort(sortByUrgency));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load license data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        <span className="ml-3 text-gray-500">Loading license data...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertTriangle className="w-10 h-10 text-red-400 mb-3" />
        <p className="text-red-600 font-medium mb-4">{error}</p>
        <button
          onClick={load}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
        >
          <RefreshCw size={16} /> Retry
        </button>
      </div>
    );
  }

  // Summary counts
  const expired = warnings.filter((w) => w.status === 'expired').length;
  const expiringSoon = warnings.filter((w) => w.status === 'expiring_soon').length;
  const overLimit = warnings.filter((w) => w.status === 'over_limit').length;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">License Manager</h2>
          <p className="text-sm text-gray-500 mt-0.5">{warnings.length} customers</p>
        </div>
        <button
          onClick={load}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Summary chips */}
      <div className="flex flex-wrap gap-3">
        {expired > 0 && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-red-50 text-red-700 rounded-full">
            <AlertTriangle size={14} /> {expired} expired
          </span>
        )}
        {expiringSoon > 0 && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-amber-50 text-amber-700 rounded-full">
            {expiringSoon} expiring soon
          </span>
        )}
        {overLimit > 0 && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-orange-50 text-orange-700 rounded-full">
            {overLimit} over seat limit
          </span>
        )}
        {expired === 0 && expiringSoon === 0 && overLimit === 0 && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-green-50 text-green-700 rounded-full">
            All licenses healthy
          </span>
        )}
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-gray-500 border-b border-gray-100">
              <th className="px-4 py-3 font-medium">Customer</th>
              <th className="px-4 py-3 font-medium">License Type</th>
              <th className="px-4 py-3 font-medium">Seats</th>
              <th className="px-4 py-3 font-medium">Expiry</th>
              <th className="px-4 py-3 font-medium">Days Left</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {warnings.map((w) => (
              <tr key={w.customer_id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <button
                    onClick={() => navigate(`/admin/customers/${w.customer_id}`)}
                    className="font-medium text-indigo-600 hover:text-indigo-700"
                  >
                    {w.customer_name}
                  </button>
                </td>
                <td className="px-4 py-3 text-gray-700">{w.license_type}</td>
                <td className="px-4 py-3">
                  <SeatBar used={w.seats_used} max={w.seats_max} />
                </td>
                <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                  {w.license_end ? new Date(w.license_end).toLocaleDateString() : '--'}
                </td>
                <td className="px-4 py-3 text-gray-500">
                  {w.days_remaining != null ? w.days_remaining : '--'}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={w.status} />
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => setEditTarget(w)}
                    className="text-xs font-medium px-2.5 py-1 rounded text-indigo-600 bg-indigo-50 hover:bg-indigo-100"
                  >
                    Edit
                  </button>
                </td>
              </tr>
            ))}
            {warnings.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  No license data available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Quick edit modal */}
      {editTarget && (
        <QuickEditModal
          warning={editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={() => {
            setEditTarget(null);
            load();
          }}
        />
      )}
    </div>
  );
};

export default LicenseManagerPage;
