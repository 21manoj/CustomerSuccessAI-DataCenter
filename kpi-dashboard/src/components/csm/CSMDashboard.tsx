/**
 * CSM Dashboard — Entry Point with Layout Switcher
 * =================================================
 *
 * Provides two CSM-optimized layouts:
 * - Focus Flow: Sequential task queue (Superhuman-inspired)
 * - Cockpit: Kanban board with contextual drawer (Linear-inspired)
 *
 * Layout preference is persisted in localStorage.
 * Includes floating AI chatbot available in both layouts.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Layout, Layers } from 'lucide-react';
import CSMFocusFlow from './CSMFocusFlow';
import CSMCockpit from './CSMCockpit';
import AskAIPortal from '../ai/AskAIPortal';
import { useNotifications } from '../../hooks/useNotifications';
import { useSession } from '../../contexts/SessionContext';
import { getCustomerIdentifier } from '../../utils/api';
import { trackPageView, trackDashboardSwitch } from '../../utils/activityTracker';

type LayoutMode = 'focus' | 'cockpit';

const CSMDashboard: React.FC = () => {
  const { session } = useSession();
  const customerId = getCustomerIdentifier(session);
  const { notifications, unreadCount, urgentAlerts, markAsRead, markAllRead } = useNotifications(customerId);

  const [layout, setLayout] = useState<LayoutMode>(() => {
    return (localStorage.getItem('csm_layout') as LayoutMode) || 'focus';
  });

  const switchLayout = useCallback((mode: LayoutMode) => {
    trackDashboardSwitch(layout, `csm_${mode}`);
    setLayout(mode);
    localStorage.setItem('csm_layout', mode);
  }, [layout]);

  useEffect(() => {
    trackPageView('csm_dashboard', { layout });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="relative min-h-screen">
      {/* Layout Switcher — fixed bottom-left */}
      <div className="fixed bottom-6 left-6 z-40 flex items-center gap-1 bg-white rounded-full shadow-lg border border-gray-200 p-1">
        <button
          onClick={() => switchLayout('focus')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
            layout === 'focus' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
          }`}
          title="Focus Flow — Sequential task queue"
        >
          <Layout className="h-3.5 w-3.5" />
          Focus
        </button>
        <button
          onClick={() => switchLayout('cockpit')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
            layout === 'cockpit' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
          }`}
          title="Cockpit — Kanban board"
        >
          <Layers className="h-3.5 w-3.5" />
          Board
        </button>
      </div>

      {/* Active Layout */}
      {layout === 'focus'
        ? <CSMFocusFlow notifications={notifications} unreadCount={unreadCount} urgentAlerts={urgentAlerts} onMarkRead={markAsRead} onMarkAllRead={markAllRead} />
        : <CSMCockpit notifications={notifications} unreadCount={unreadCount} urgentAlerts={urgentAlerts} onMarkRead={markAsRead} onMarkAllRead={markAllRead} />
      }

      {/* AI Assistant — same AskAIPortal as CRO/CFO */}
      <AskAIPortal persona="vpcs" />
    </div>
  );
};

export default CSMDashboard;
