import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  UserCheck,
  AlertTriangle,
  Key,
  Plus,
  ArrowRight,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import {
  fetchDashboardStats,
  fetchActivityLog,
  type DashboardStats,
  type ActivityEntry,
} from '../../api/adminApi';

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  color: string; // tailwind bg class e.g. "bg-indigo-500"
  onClick?: () => void;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon, color, onClick }) => (
  <button
    onClick={onClick}
    className="flex items-center gap-4 p-5 bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow text-left w-full"
  >
    <div className={`flex items-center justify-center w-12 h-12 rounded-lg text-white ${color}`}>
      {icon}
    </div>
    <div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-sm text-gray-500">{label}</p>
    </div>
  </button>
);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const AdminDashboardPage: React.FC = () => {
  const navigate = useNavigate();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentActivity, setRecentActivity] = useState<ActivityEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, activityData] = await Promise.all([
        fetchDashboardStats(),
        fetchActivityLog({ limit: 8 }),
      ]);
      setStats(statsData);
      setRecentActivity(activityData.entries ?? []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        <span className="ml-3 text-gray-500">Loading dashboard...</span>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Error state
  // -------------------------------------------------------------------------
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertTriangle className="w-10 h-10 text-red-400 mb-3" />
        <p className="text-red-600 font-medium mb-4">{error}</p>
        <button
          onClick={loadData}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
        >
          <RefreshCw size={16} /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Admin Dashboard</h2>
          <p className="text-sm text-gray-500 mt-0.5">Overview of your CS Pulse platform</p>
        </div>
        <button
          onClick={loadData}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Total Customers"
          value={stats?.total_customers ?? 0}
          icon={<Users size={22} />}
          color="bg-indigo-500"
          onClick={() => navigate('/admin/customers')}
        />
        <StatCard
          label="Active Users"
          value={stats?.active_users ?? 0}
          icon={<UserCheck size={22} />}
          color="bg-emerald-500"
        />
        <StatCard
          label="Seat Warnings"
          value={stats?.seat_warnings ?? 0}
          icon={<AlertTriangle size={22} />}
          color={stats?.seat_warnings ? 'bg-amber-500' : 'bg-gray-400'}
          onClick={() => navigate('/admin/licenses')}
        />
        <StatCard
          label="License Alerts"
          value={stats?.license_warnings ?? 0}
          icon={<Key size={22} />}
          color={stats?.license_warnings ? 'bg-red-500' : 'bg-gray-400'}
          onClick={() => navigate('/admin/licenses')}
        />
      </div>

      {/* Quick actions + verticals */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Quick actions */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 lg:col-span-1">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">
            Quick Actions
          </h3>
          <div className="space-y-2">
            <button
              onClick={() => navigate('/admin/customers', { state: { openCreate: true } })}
              className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-indigo-700 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
            >
              <Plus size={16} />
              Add New Customer
            </button>
            <button
              onClick={() => navigate('/admin/licenses')}
              className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-amber-700 bg-amber-50 rounded-lg hover:bg-amber-100 transition-colors"
            >
              <AlertTriangle size={16} />
              View License Warnings
            </button>
            <button
              onClick={() => navigate('/admin/activity')}
              className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-gray-700 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <ArrowRight size={16} />
              View Full Activity Log
            </button>
          </div>
        </div>

        {/* Verticals summary */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 lg:col-span-2">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">
            Active Verticals
          </h3>
          {stats?.verticals && stats.verticals.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {stats.verticals.map((v) => (
                <span
                  key={v}
                  className="inline-flex items-center px-3 py-1.5 bg-indigo-50 text-indigo-700 text-sm font-medium rounded-full"
                >
                  {v}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400">No verticals configured.</p>
          )}
        </div>
      </div>

      {/* Recent activity */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider">
            Recent Activity
          </h3>
          <button
            onClick={() => navigate('/admin/activity')}
            className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
          >
            View all
          </button>
        </div>

        {recentActivity.length === 0 ? (
          <p className="text-sm text-gray-400 py-4 text-center">No recent activity.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-100">
                  <th className="pb-2 pr-4 font-medium">Time</th>
                  <th className="pb-2 pr-4 font-medium">Customer</th>
                  <th className="pb-2 pr-4 font-medium">Action</th>
                  <th className="pb-2 pr-4 font-medium">Description</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {recentActivity.map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="py-2.5 pr-4 text-gray-500 whitespace-nowrap">
                      {new Date(entry.timestamp).toLocaleString()}
                    </td>
                    <td className="py-2.5 pr-4 text-gray-700 whitespace-nowrap">
                      {entry.customer_name ?? '--'}
                    </td>
                    <td className="py-2.5 pr-4 font-medium text-gray-900 whitespace-nowrap">
                      {entry.action}
                    </td>
                    <td className="py-2.5 pr-4 text-gray-600 max-w-xs truncate">
                      {entry.description}
                    </td>
                    <td className="py-2.5">
                      <StatusBadge status={entry.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Status badge helper
// ---------------------------------------------------------------------------

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

export default AdminDashboardPage;
