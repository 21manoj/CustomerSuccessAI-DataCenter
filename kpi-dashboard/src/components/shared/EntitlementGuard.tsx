/**
 * EntitlementGuard — Route-level entitlement gating
 * ===================================================
 * Wraps dashboard routes to check feature entitlements.
 * Shows an upgrade prompt instead of a blank/broken page.
 *
 * Usage:
 *   <EntitlementGuard feature="revenue_intelligence">
 *     <CRODashboard />
 *   </EntitlementGuard>
 */

import React from 'react';
import { useEntitlement, tierLabel } from '../../hooks/useEntitlement';
import { useNavigate } from 'react-router-dom';

interface Props {
  feature: string;
  children: React.ReactNode;
}

const EntitlementGuard: React.FC<Props> = ({ feature, children }) => {
  const { allowed, requiredTier } = useEntitlement(feature);
  const navigate = useNavigate();

  if (allowed) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="bg-white border border-gray-200 rounded-2xl shadow-lg p-10 max-w-md text-center">
        <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-5">
          <svg className="w-8 h-8 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m0 0v2m0-2h2m-2 0H10m5-7V7a5 5 0 00-10 0v4a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Feature Locked</h2>
        <p className="text-gray-500 mb-1 text-sm">
          This dashboard requires the{' '}
          <span className="font-semibold text-gray-700">{requiredTier ? tierLabel(requiredTier) : 'Professional'}</span>{' '}
          tier or higher.
        </p>
        <p className="text-gray-400 text-xs mb-6">
          Contact your administrator to upgrade your subscription.
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={() => navigate(-1)}
            className="px-5 py-2 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Go Back
          </button>
          <button
            onClick={() => navigate('/dc-dashboard/settings')}
            className="px-5 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-500 transition-colors"
          >
            View Settings
          </button>
        </div>
      </div>
    </div>
  );
};

export default EntitlementGuard;
