import React from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, Building2 } from 'lucide-react';
import { useSession } from '../../contexts/SessionContext';

interface DashboardTopBarProps {
  /** Accent color for the left border: 'red' | 'emerald' | 'purple' | 'teal' | 'amber' */
  accent?: string;
}

const ACCENT_COLORS: Record<string, string> = {
  red: 'border-red-500',
  emerald: 'border-emerald-500',
  purple: 'border-purple-500',
  teal: 'border-teal-500',
  amber: 'border-amber-500',
  cyan: 'border-cyan-500',
};

/**
 * Shared top bar for all persona dashboards.
 * Shows: Customer Name | Customer ID | User Name | Logout
 */
const DashboardTopBar: React.FC<DashboardTopBarProps> = ({ accent = 'red' }) => {
  const { session, logout } = useSession();
  const navigate = useNavigate();

  const handleLogout = () => {
    fetch('/api/logout', { method: 'POST' }).catch(() => {});
    logout();
    navigate('/login');
  };

  if (!session) return null;

  const borderClass = ACCENT_COLORS[accent] || ACCENT_COLORS.red;

  return (
    <div className={`flex items-center justify-between px-6 py-2 bg-[#0d1117] border-b border-gray-800 border-l-2 ${borderClass}`}>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-semibold text-white">
            {session.customer_name || `Customer ${session.customer_id}`}
          </span>
        </div>
        <span className="text-xs text-gray-600">|</span>
        <span className="text-xs text-gray-500 font-mono">
          ID: {session.customer_id}
        </span>
      </div>

      <div className="flex items-center gap-4">
        <span className="text-xs text-gray-500">
          {session.user_name}
        </span>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" />
          Logout
        </button>
      </div>
    </div>
  );
};

export default DashboardTopBar;
