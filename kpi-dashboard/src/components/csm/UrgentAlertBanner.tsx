/**
 * UrgentAlertBanner — Dismissible red banner for critical notifications.
 *
 * Shows above the main content area in CSM layouts when critical alerts exist.
 * Displays one alert at a time with "N more" indicator.
 */

import React from 'react';
import { AlertTriangle, X } from 'lucide-react';
import type { Notification } from '../../hooks/useNotifications';

interface UrgentAlertBannerProps {
  alerts: Notification[];
  onDismiss: (id: number) => void;
}

const UrgentAlertBanner: React.FC<UrgentAlertBannerProps> = ({ alerts, onDismiss }) => {
  if (alerts.length === 0) return null;

  const top = alerts[0];
  const remaining = alerts.length - 1;

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-2.5 mx-4 mt-2 flex items-center gap-3">
      <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
      <div className="flex-1 min-w-0">
        <span className="text-sm font-medium text-red-800">
          {top.payload?.title || 'Critical Alert'}
        </span>
        {top.payload?.account_name && (
          <span className="text-sm text-red-600 ml-1">— {top.payload.account_name}</span>
        )}
        {top.payload?.summary && (
          <span className="text-xs text-red-500 ml-2 hidden sm:inline">{top.payload.summary.substring(0, 80)}</span>
        )}
        {remaining > 0 && (
          <span className="text-xs text-red-400 ml-2">+{remaining} more</span>
        )}
      </div>
      <button
        onClick={() => onDismiss(top.id)}
        className="p-1 hover:bg-red-100 rounded transition shrink-0"
      >
        <X className="w-3.5 h-3.5 text-red-400" />
      </button>
    </div>
  );
};

export default UrgentAlertBanner;
