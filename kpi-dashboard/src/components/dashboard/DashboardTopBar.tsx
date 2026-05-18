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
 * Sources, in order of preference, for the displayed customer name + id:
 *   1. Props passed by the parent dashboard (super-admin acting-as override).
 *   2. Resolved from /api/v1/accounts (fires when super admin is acting-as,
 *      OR when the stored session is missing customer_name — self-heals
 *      localStorage written by an older client).
 *   3. session.customer_name / session.customer_id from SessionContext.
 *   4. Last-resort fallback: "Customer <id>".
 */
const DashboardTopBar: React.FC<DashboardTopBarProps> = ({ accent = 'red', customerName: propName, customerId: propId }) => {
  const { session, logout } = useSession();
  const navigate = useNavigate();
  const [resolvedName, setResolvedName] = useState<string | null>(null);
  const [resolvedId, setResolvedId] = useState<number | null>(null);

  // Auto-resolve customer context when either:
  //   (a) session is super admin (customer_id = 1) acting as another tenant, or
  //   (b) session is missing customer_name (e.g. localStorage was written by an
  //       older client that did not persist it — self-heals stale sessions
  //       without forcing a logout).
  useEffect(() => {
    if (!session || propName) return;
    const isSuperAdmin = session.customer_id === 1;
    const missingName = !session.customer_name;
    if (!isSuperAdmin && !missingName) return;

    const headers: HeadersInit = { 'Content-Type': 'application/json' };
    if (isSuperAdmin && session.customer_uuid) {
      headers['X-Customer-ID'] = session.customer_uuid;
    }

    fetch('/api/v1/accounts', { credentials: 'include', headers })
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
