/**
 * useNotifications — Poll /api/notifications/unread for push notifications.
 *
 * Used by CSMDashboard to provide notification state to both Focus Flow and Cockpit.
 * Polling interval: 60s (configurable). Fire-and-forget — never fails the UI.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface Notification {
  id: number;
  customer_id: number;
  account_id?: number;
  type: 'signal_insight' | 'playbook_triggered' | 'urgent_alert' | 'weight_calibration_changed';
  priority: 'normal' | 'high' | 'critical';
  payload: Record<string, any>;
  created_at: string;
  read_at: string | null;
  is_read: boolean;
}

interface UseNotificationsReturn {
  notifications: Notification[];
  unreadCount: number;
  urgentAlerts: Notification[];
  loading: boolean;
  markAsRead: (id: number) => Promise<void>;
  markAllRead: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useNotifications(
  customerId: string | number | undefined,
  pollIntervalMs: number = 60000,
): UseNotificationsReturn {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const mounted = useRef(true);

  const headers: Record<string, string> = {
    'X-Customer-ID': String(customerId || ''),
  };

  const fetchUnread = useCallback(async () => {
    if (!customerId) return;
    try {
      setLoading(true);
      const resp = await fetch('/api/notifications/unread?limit=20', {
        headers,
        credentials: 'include',
      });
      if (!resp.ok) return;
      const data = await resp.json();
      if (!mounted.current) return;
      setNotifications(data.notifications || []);
      setUnreadCount(data.count || 0);
    } catch {
      // Silent — never fail the UI for notifications
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [customerId]);

  // Initial fetch + polling
  useEffect(() => {
    mounted.current = true;
    fetchUnread();
    const interval = setInterval(fetchUnread, pollIntervalMs);
    return () => {
      mounted.current = false;
      clearInterval(interval);
    };
  }, [fetchUnread, pollIntervalMs]);

  const markAsRead = useCallback(async (id: number) => {
    try {
      await fetch(`/api/notifications/${id}/read`, {
        method: 'PUT',
        headers: { ...headers, 'Content-Type': 'application/json' },
        credentials: 'include',
      });
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // Silent
    }
  }, [customerId]);

  const markAllRead = useCallback(async () => {
    try {
      await Promise.all(
        notifications.map((n) =>
          fetch(`/api/notifications/${n.id}/read`, {
            method: 'PUT',
            headers: { ...headers, 'Content-Type': 'application/json' },
            credentials: 'include',
          }).catch(() => {}),
        ),
      );
      setNotifications([]);
      setUnreadCount(0);
    } catch {
      // Silent
    }
  }, [notifications, customerId]);

  const urgentAlerts = notifications.filter((n) => n.priority === 'critical');

  return {
    notifications,
    unreadCount,
    urgentAlerts,
    loading,
    markAsRead,
    markAllRead,
    refresh: fetchUnread,
  };
}
