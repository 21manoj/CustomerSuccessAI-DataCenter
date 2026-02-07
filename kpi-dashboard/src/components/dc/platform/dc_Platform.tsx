/**
 * Data Center Platform - Main Landing Page
 * =========================================
 * 
 * 7-tab platform for Data Center vertical:
 * 1. Executive Dashboard
 * 2. Tenants (Hub with Placard)
 * 3. Signal Analyst
 * 4. AI Insights (RAG)
 * 5. Admin Insights (Wizard B & C)
 * 6. Data Integration
 * 7. Settings
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import {
  BarChart3,
  Users,
  MessageSquare,
  Brain,
  Upload,
  Settings,
  LogOut,
  Activity,
  Zap
} from 'lucide-react';
import { useSession } from '../../../contexts/SessionContext';

// Import tab components
import ExecutiveDashboard from '../../dashboard/ExecutiveDashboard';
import SignalAnalyst from '../../SignalAnalyst'; // Keep original location for now
import RAGAnalysis from '../../RAGAnalysis'; // Keep original location for now
import AdminDashboard from '../../admin/AdminDashboard';

// DC-specific components
import DCTenantHub from '../tenants/dc_TenantHub';
import DCDataIntegration from '../data-integration/dc_DataIntegration';
import DCSettings from '../settings/dc_Settings';

// ============================================================
// SIGNAL OVERVIEW (no-account-selected view)
// ============================================================

const SignalOverview: React.FC = () => {
  const [signals, setSignals] = React.useState<any[]>([]);
  const [summary, setSummary] = React.useState<any>({});
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch('/api/dc2s/signals/all?limit=30', { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          setSignals(data.signals || []);
          setSummary(data.sentiment_summary || {});
        }
      } catch (e) { console.error(e); }
      setLoading(false);
    };
    load();
  }, []);

  if (loading) return <div className="text-center py-12 text-gray-500">Loading signals...</div>;

  const sentimentColor = (s: string) =>
    s === 'positive' ? 'bg-green-100 text-green-800' :
    s === 'negative' ? 'bg-red-100 text-red-800' :
    'bg-gray-100 text-gray-700';

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-900 mb-4">Signal Analyst - All Accounts</h2>
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-green-50 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-green-600">{summary.positive || 0}</div>
          <div className="text-sm text-green-700">Positive</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-gray-600">{summary.neutral || 0}</div>
          <div className="text-sm text-gray-700">Neutral</div>
        </div>
        <div className="bg-red-50 rounded-lg p-4 text-center">
          <div className="text-2xl font-bold text-red-600">{summary.negative || 0}</div>
          <div className="text-sm text-red-700">Negative</div>
        </div>
      </div>
      <div className="space-y-3">
        {signals.map((sig: any, i: number) => (
          <div key={sig.signal_id || i} className="flex items-start gap-3 p-3 border rounded-lg hover:bg-gray-50">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${sentimentColor(sig.sentiment)}`}>
              {sig.sentiment}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="font-medium text-sm text-gray-900">{sig.account_name}</span>
                <span className="text-xs text-gray-400">{sig.signal_date}</span>
              </div>
              <p className="text-sm text-gray-600">{sig.content}</p>
            </div>
            <span className="text-xs text-gray-400 whitespace-nowrap">{sig.signal_type}</span>
          </div>
        ))}
        {signals.length === 0 && <p className="text-gray-500 text-center py-8">No signals found</p>}
      </div>
    </div>
  );
};

// ============================================================
// TYPES
// ============================================================

type TabId = 'executive' | 'tenants' | 'signals' | 'ai-insights' | 'admin-insights' | 'data-integration' | 'settings';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  route: string;
}

// ============================================================
// TAB CONFIGURATION
// ============================================================

const TABS: Tab[] = [
  { id: 'executive', label: 'Executive Dashboard', icon: BarChart3, route: '/dc-dashboard' },
  { id: 'tenants', label: 'Tenants', icon: Users, route: '/dc-dashboard/tenants' },
  { id: 'signals', label: 'Signal Analyst', icon: MessageSquare, route: '/dc-dashboard/signal-analyst' },
  { id: 'ai-insights', label: 'AI Insights', icon: Brain, route: '/dc-dashboard/ai-insights' },
  { id: 'admin-insights', label: 'Admin Insights', icon: Activity, route: '/dc-dashboard/admin-insights' },
  { id: 'data-integration', label: 'Data Integration', icon: Upload, route: '/dc-dashboard/data-integration' },
  { id: 'settings', label: 'Settings', icon: Settings, route: '/dc-dashboard/settings' }
];

// ============================================================
// MAIN COMPONENT
// ============================================================

const DCPlatform: React.FC = () => {
  const { session, logout } = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const { accountId } = useParams<{ accountId?: string }>();
  
  // Determine active tab from route
  const getActiveTabFromRoute = (): TabId => {
    const path = location.pathname;
    // Check for exact matches first, then includes
    if (path === '/dc-dashboard/tenants' || path.startsWith('/dc-dashboard/tenants/')) return 'tenants';
    if (path.includes('/signal-analyst')) return 'signals';
    if (path.includes('/ai-insights')) return 'ai-insights';
    if (path.includes('/admin-insights')) return 'admin-insights';
    if (path.includes('/data-integration')) return 'data-integration';
    if (path.includes('/settings')) return 'settings';
    return 'executive'; // Default
  };
  
  const [activeTab, setActiveTab] = useState<TabId>(getActiveTabFromRoute());

  // Update active tab when route changes
  useEffect(() => {
    setActiveTab(getActiveTabFromRoute());
  }, [location.pathname]);

  const handleTabClick = (tab: Tab) => {
    // Update active tab immediately for instant UI feedback
    setActiveTab(tab.id);
    // Navigate to the tab's route
    navigate(tab.route, { replace: false });
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!session) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-gray-50 to-blue-50/20">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-md px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1">
            {/* Centered Title */}
            <div className="flex-1 text-center">
              <h1 className="text-xl font-bold text-gray-900">Data Center Operations Platform - CS Pulse DC2_S</h1>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className="text-sm text-gray-600">Welcome, {session.user_name}</span>
            <button 
              onClick={handleLogout}
              className="flex items-center px-3 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Left Sidebar Navigation */}
        <nav className="w-64 bg-gradient-to-b from-slate-50 to-slate-100 border-r border-slate-200 shadow-sm px-4 py-6">
          <div className="space-y-2">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => handleTabClick(tab)}
                className={`w-full flex items-center px-4 py-3 rounded-lg text-left transition-all duration-200 ${
                  activeTab === tab.id 
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md transform scale-105' 
                    : 'text-gray-700 hover:bg-white hover:shadow-sm hover:text-blue-600'
                }`}
              >
                <tab.icon className={`h-5 w-5 mr-3 ${activeTab === tab.id ? 'text-white' : ''}`} />
                <span className="font-medium text-sm">{tab.label}</span>
              </button>
            ))}
          </div>
        </nav>

        {/* Main Content Area */}
        <main className="flex-1 p-8 bg-gradient-to-br from-gray-50 via-blue-50/30 to-indigo-50/30">
          {activeTab === 'executive' && <ExecutiveDashboard />}
          
          {activeTab === 'tenants' && <DCTenantHub />}
          
          {activeTab === 'signals' && (
            <div className="bg-white rounded-lg shadow-sm p-6">
              {accountId ? (
                <SignalAnalyst accountId={parseInt(accountId)} accountName={`Account ${accountId}`} />
              ) : (
                <SignalOverview />
              )}
            </div>
          )}
          
          {activeTab === 'ai-insights' && (
            <div className="bg-white rounded-lg shadow-sm p-6">
              <RAGAnalysis />
            </div>
          )}
          
          {activeTab === 'admin-insights' && <AdminDashboard />}
          
          {activeTab === 'data-integration' && <DCDataIntegration />}
          
          {activeTab === 'settings' && <DCSettings />}
        </main>
      </div>
    </div>
  );
};

export default DCPlatform;
