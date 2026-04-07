/**
 * NotificationBell — Bell icon with unread badge + dropdown panel.
 *
 * Renders in CSM dashboard header (both Cockpit and FocusFlow).
 * Shows notifications sorted by priority (critical first).
 */

import React, { useState, useRef, useEffect } from 'react';
import { Bell, AlertTriangle, Zap, Sparkles, X, CheckCheck } from 'lucide-react';
import type { Notification } from '../../hooks/useNotifications';

interface NotificationBellProps {
  notifications: Notification[];
  unreadCount: number;
  onMarkRead: (id: number) => void;
  onMarkAllRead: () => void;
}

const TYPE_ICONS: Record<string, React.ReactNode> = {
  urgent_alert: <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />,
  playbook_triggered: <Zap className="w-4 h-4 text-blue-500 shrink-0" />,
  signal_insight: <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />,
};

const PRIORITY_DOT: Record<string, string> = {
  critical: 'bg-red-500',
  high: 'bg-amber-400',
  normal: 'bg-gray-300',
};

function timeAgo(iso: string): string {
  const secs = Math.floor((Date.now() - new Date(iso + 'Z').getTime()) / 1000);
  if (secs < 60) return 'just now';
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

const NotificationBell: React.FC<NotificationBellProps> = ({
  notifications,
  unreadCount,
  onMarkRead,
  onMarkAllRead,
}) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Click-away to close
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    if (open) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      {/* Bell button */}
      <button
        onClick={() => setOpen(!open)}
        className="relative p-1.5 hover:bg-gray-100 rounded-lg transition"
      >
        <Bell className="w-5 h-5 text-gray-500" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 top-10 w-80 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100">
            <span className="text-sm font-semibold text-gray-900">
              Notifications {unreadCount > 0 && `(${unreadCount})`}
            </span>
            <div className="flex items-center gap-2">
              {notifications.length > 0 && (
                <button
                  onClick={() => { onMarkAllRead(); setOpen(false); }}
                  className="text-[10px] text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  <CheckCheck className="w-3 h-3" /> Mark all read
                </button>
              )}
              <button onClick={() => setOpen(false)}>
                <X className="w-4 h-4 text-gray-400 hover:text-gray-600" />
              </button>
            </div>
          </div>

          {/* Notification list */}
          <div className="max-h-72 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="py-8 text-center text-sm text-gray-400">
                No notifications
              </div>
            ) : (
              notifications.map((n) => (
                <button
                  key={n.id}
                  onClick={() => { onMarkRead(n.id); }}
                  className="flex items-start gap-3 px-4 py-3 w-full text-left hover:bg-gray-50 border-b border-gray-50 transition"
                >
                  {/* Priority dot */}
                  <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${PRIORITY_DOT[n.priority] || PRIORITY_DOT.normal}`} />
                  {/* Type icon */}
                  {TYPE_ICONS[n.type] || TYPE_ICONS.signal_insight}
                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-900 truncate">
                      {n.payload?.title || n.type.replace(/_/g, ' ')}
                    </p>
                    {n.payload?.summary && (
                      <p className="text-[11px] text-gray-500 line-clamp-2 mt-0.5">
                        {n.payload.summary}
                      </p>
                    )}
                    <div className="flex items-center gap-2 mt-1">
                      {n.payload?.account_name && (
                        <span className="text-[10px] text-gray-400">{n.payload.account_name}</span>
                      )}
                      <span className="text-[10px] text-gray-300">{timeAgo(n.created_at)}</span>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
