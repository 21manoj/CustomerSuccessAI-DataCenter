/**
 * Shared error state for all executive dashboards.
 *
 * Distinguishes auth-expired (401) from other errors and shows the
 * appropriate CTA — "Log in again" for auth, "Retry" otherwise. Keeps
 * dashboards lean and consistent.
 *
 * Usage:
 *   <DashboardErrorState
 *     dashboardLabel="CFO dashboard"
 *     errorMessage={error}
 *     errorStatus={errorStatus}
 *   />
 */
import React from 'react';
import { AlertTriangle, LogIn, RotateCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface Props {
  /** Human-readable dashboard name (e.g. "CFO dashboard"). */
  dashboardLabel: string;
  /** Error message from the fetch catch block. */
  errorMessage: string | null;
  /** HTTP status code if known (used to detect 401 auth-expired). */
  errorStatus: number | null;
}

export const DashboardErrorState: React.FC<Props> = ({
  dashboardLabel,
  errorMessage,
  errorStatus,
}) => {
  const navigate = useNavigate();
  const isAuthExpired = errorStatus === 401;

  const handleRetry = () => window.location.reload();
  const handleRelogin = () => {
    // Preserve where the user wanted to go so they land back here after login.
    const returnTo = encodeURIComponent(window.location.pathname);
    navigate(`/login?return_to=${returnTo}`);
  };

  return (
    <div className="flex h-screen bg-[#0f1419] text-white font-['Inter',sans-serif] items-center justify-center">
      <div className="text-center max-w-md">
        <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">
          {isAuthExpired ? 'Session Expired' : 'Unable to Load Dashboard'}
        </h2>
        <p className="text-gray-400 text-sm mb-5">
          {isAuthExpired
            ? `Your session has expired. Please log in again to view the ${dashboardLabel}.`
            : errorMessage ||
              `Unable to load ${dashboardLabel} data. Please check your connection and try again.`}
        </p>
        <div className="flex justify-center gap-3">
          {isAuthExpired ? (
            <button
              onClick={handleRelogin}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-500 transition-colors"
            >
              <LogIn className="w-4 h-4" /> Log in again
            </button>
          ) : (
            <>
              <button
                onClick={handleRetry}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-500 transition-colors"
              >
                <RotateCw className="w-4 h-4" /> Retry
              </button>
              <button
                onClick={handleRelogin}
                className="flex items-center gap-2 px-4 py-2 bg-transparent border border-gray-600 text-gray-300 rounded-lg text-sm hover:border-emerald-500 hover:text-emerald-400 transition-colors"
              >
                <LogIn className="w-4 h-4" /> Log in again
              </button>
            </>
          )}
        </div>
        {errorStatus && (
          <div className="mt-4 text-[10px] text-gray-600">
            Status: {errorStatus}
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardErrorState;
