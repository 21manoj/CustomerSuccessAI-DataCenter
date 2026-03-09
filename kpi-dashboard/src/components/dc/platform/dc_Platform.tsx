/**
 * Data Center Platform - Main Landing Page
 * =========================================
 * 
 * 10-tab platform for Data Center vertical:
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
  Zap,
  DollarSign,
  Layers,
  FlaskConical,
  ShieldCheck,
  GitBranch
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
import DCPlaybooks from '../playbooks/DCPlaybooks';
import DCApprovalQueue from '../approvals/DCApprovalQueue';
import DCTestRunner from '../test-runner/DCTestRunner';
import DCRevenueIntelligence from '../revenue-intelligence/DCRevenueIntelligence';

// ============================================================
// TYPES
// ============================================================

type TabId = 'executive' | 'tenants' | 'signals' | 'ai-insights' | 'admin-insights' | 'playbooks' | 'approvals' | 'test-runner' | 'revenue-intelligence' | 'data-integration' | 'settings' | 'outcome-roi' | 'portco';

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
  { id: 'playbooks', label: 'Playbooks', icon: Zap, route: '/dc-dashboard/playbooks' },
  { id: 'approvals', label: 'Approval Queue', icon: ShieldCheck, route: '/dc-dashboard/approvals' },
  { id: 'test-runner', label: 'Test Runner', icon: FlaskConical, route: '/dc-dashboard/test-runner' },
  { id: 'outcome-roi', label: 'Outcome ROI', icon: DollarSign, route: '/outcome-roi' },
  { id: 'portco', label: 'Power of 1 (Portfolio CEO)', icon: Layers, route: '/portco-dashboard' },
  { id: 'revenue-intelligence', label: 'Revenue Intelligence', icon: GitBranch, route: '/dc-dashboard/revenue-intelligence' },
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
    if (path.includes('/playbooks')) return 'playbooks';
    if (path.includes('/approvals')) return 'approvals';
    if (path.includes('/test-runner')) return 'test-runner';
    if (path.includes('/revenue-intelligence')) return 'revenue-intelligence';
    if (path === '/outcome-roi') return 'outcome-roi';
    if (path === '/portco-dashboard') return 'portco';
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
        <main className="flex-1 min-w-0 overflow-hidden p-8 bg-gradient-to-br from-gray-50 via-blue-50/30 to-indigo-50/30">
          {activeTab === 'executive' && <ExecutiveDashboard />}
          
          {activeTab === 'tenants' && <DCTenantHub />}
          
          {activeTab === 'signals' && (
            <div className="bg-white rounded-lg shadow-sm p-6">
              {accountId ? (
                <SignalAnalyst accountId={accountId} accountName={`Account ${accountId}`} />
              ) : (
                <div className="text-center py-12">
                  <p className="text-gray-600 mb-4">Please select an account to analyze</p>
                  <p className="text-sm text-gray-500">Go to the Tenants tab and click on an account to view Signal Analyst</p>
                </div>
              )}
            </div>
          )}
          
          {activeTab === 'ai-insights' && (
            <div className="bg-white rounded-lg shadow-sm p-6">
              <RAGAnalysis />
            </div>
          )}
          
          {activeTab === 'admin-insights' && <AdminDashboard />}

          {activeTab === 'playbooks' && <DCPlaybooks />}

          {activeTab === 'approvals' && <DCApprovalQueue />}

          {activeTab === 'test-runner' && <DCTestRunner />}

          {activeTab === 'revenue-intelligence' && <DCRevenueIntelligence />}

          {activeTab === 'data-integration' && <DCDataIntegration />}
          
          {activeTab === 'settings' && <DCSettings />}
        </main>
      </div>
    </div>
  );
};

export default DCPlatform;
