/**
 * Activity Tracker — Granular click-level logging for Super Admin console.
 *
 * Fires non-blocking POST to /api/activity-logs/track on every significant
 * UI interaction. Never throws, never blocks the UI.
 *
 * Usage:
 *   import { trackEvent, trackPageView, trackClick } from 'utils/activityTracker';
 *
 *   trackPageView('cro_dashboard');
 *   trackClick('account_card', { account_id: 424001 });
 *   trackEvent('dashboard_switch', 'cfo_overview', { from: 'cro' });
 */

type EventType =
  | 'page_view'
  | 'click'
  | 'dashboard_switch'
  | 'filter_change'
  | 'export'
  | 'account_drill'
  | 'playbook_action'
  | 'mcp_query'
  | 'cro_horizon_change'
  | 'cro_period_change';

// Session ID for correlating events within a browser session
const SESSION_ID = `ui_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

// Debounce rapid-fire events (e.g., filter changes)
const recentEvents = new Map<string, number>();
const DEBOUNCE_MS = 1000;

function shouldTrack(key: string): boolean {
  const now = Date.now();
  const last = recentEvents.get(key) || 0;
  if (now - last < DEBOUNCE_MS) return false;
  recentEvents.set(key, now);
  // Clean up old entries periodically
  if (recentEvents.size > 100) {
    recentEvents.forEach((v, k) => {
      if (now - v > 10000) recentEvents.delete(k);
    });
  }
  return true;
}

export function trackEvent(
  eventType: EventType,
  target: string,
  details?: Record<string, unknown>,
): void {
  const key = `${eventType}:${target}`;
  if (!shouldTrack(key)) return;

  // Fire-and-forget — never block the UI
  try {
    const token = localStorage.getItem('token') || '';
    fetch('/api/activity-logs/track', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        event_type: eventType,
        target,
        details: details || {},
        session_id: SESSION_ID,
        resource_type: 'ui',
        timestamp: new Date().toISOString(),
      }),
    }).catch(() => {}); // Swallow errors silently
  } catch {
    // Never fail the UI for tracking
  }
}

/** Track a page view (dashboard load, view switch) */
export function trackPageView(page: string, details?: Record<string, unknown>): void {
  trackEvent('page_view', page, details);
}

/** Track a button/link click */
export function trackClick(target: string, details?: Record<string, unknown>): void {
  trackEvent('click', target, details);
}

/** Track dashboard persona switch */
export function trackDashboardSwitch(from: string, to: string): void {
  trackEvent('dashboard_switch', to, { from });
}

/** Track account drill-down */
export function trackAccountDrill(accountId: number, accountName: string): void {
  trackEvent('account_drill', `account_${accountId}`, { account_id: accountId, account_name: accountName });
}

/** Track filter/sort change */
export function trackFilterChange(filterName: string, value: string): void {
  trackEvent('filter_change', filterName, { value });
}
