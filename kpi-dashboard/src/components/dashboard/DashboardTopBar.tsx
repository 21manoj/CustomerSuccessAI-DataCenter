import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, Building2 } from 'lucide-react';
import { useSession } from '../../contexts/SessionContext';

interface DashboardTopBarProps {
  /** Accent color for the left border: 'red' | 'emerald' | 'purple' | 'teal' | 'amber' */
  accent?: string;
  /** Override customer name displayed (e.g., when super admin views another customer) */
  customerName?: string;
  /** Override customer ID displayed */
  customerId?: number;
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
 *
 * When super admin (customer_id=1) is logged in and X-Customer-ID header
 * points to a different customer, auto-resolves the actual customer name
 * so the header doesn't show "CS Pulse Admin" or "Customer 1".
 */
const DashboardTopBar: React.FC<DashboardTopBarProps> = ({ accent = 'red', customerName: propName, customerId: propId }) => {
  const { session, logout } = useSession();
  const navigate = useNavigate();
  const [resolvedName, setResolvedName] = useState<string | null>(null);
  const [resolvedId, setResolvedId] = useState<number | null>(null);

  // Auto-resolve customer context for super admin sessions
  useEffect(() => {
    if (!session || propName) return;
    // Only resolve if session is super admin (customer_id = 1)
    if (session.customer_id !== 1) return;

    // Try to get real customer context from the accounts endpoint
    const headers: HeadersInit = { 'Content-Type': 'application/json' };
    if (session.customer_uuid) {
      headers['X-Customer-ID'] = session.customer_uuid;
    }

    fetch('/api/dc2s/accounts', { credentials: 'include', headers })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data?.customer_name) {
          setResolvedName(data.customer_name);
          setResolvedId(data.customer_id);
        }
      })
      .catch(() => {});
  }, [session, propName]);

  const handleLogout = () => {
    fetch('/api/logout', { method: 'POST' }).catch(() => {});
    logout();
    navigate('/login');
  };

  if (!session) return null;

  const displayName = propName || resolvedName || session.customer_name || `Customer ${propId || resolvedId || session.customer_id}`;
  const displayId = propId || resolvedId || session.customer_id;
  const borderClass = ACCENT_COLORS[accent] || ACCENT_COLORS.red;

  return (
    <div className={`flex items-center justify-between px-6 py-2 bg-[#0d1117] border-b border-gray-800 border-l-2 ${borderClass}`}>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-semibold text-white">
            {displayName}
          </span>
        </div>
        <span className="text-xs text-gray-600">|</span>
        <span className="text-xs text-gray-500 font-mono">
          ID: {displayId}
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
