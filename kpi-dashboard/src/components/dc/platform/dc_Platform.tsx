/**
 * Data Center Platform - Main Landing Page
 * =========================================
 *
 * Tier-aware platform with Starter UX simplification:
 * - Starter: 5 tabs with friendly labels, hidden locked tabs behind "Explore More"
 * - Professional/Enterprise: Full 13-tab view with lock icons on inaccessible tabs
 *
 * Tabs:
 * 1. Portfolio Overview (Executive Dashboard)
 * 2. Accounts (Tenants)
 * 3. Signal Analyst
 * 4. AI Insights (RAG)
 * 5. Insights (Admin/Wizard B & C)
 * 6. Upload Data (Data Integration)
 * 7. Settings
 * + Playbooks, Approvals, Test Runner, Outcome ROI, Portfolio, Revenue Intelligence
 */

import React, { useState, useEffect, useCallback } from 'react';
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
  GitBranch,
  Lock,
  ChevronDown,
  ChevronRight,
  Sun,
  Moon,
  Sunrise,
  Sunset,
  Search,
  X,
  Command,
} from 'lucide-react';
import { useSession } from '../../../contexts/SessionContext';
import { useEntitlements, tierLabel, getRequiredTier } from '../../../hooks/useEntitlement';
import ProductTour, { STARTER_TOUR_STEPS } from '../../shared/ProductTour';
import NavLogoutButton from '../../shared/NavLogoutButton';
import KPIGlossaryDrawer from '../../shared/KPIGlossaryDrawer';

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

type TabId = 'executive' | 'tenants' | 'signals' | 'ai-insights' | 'admin-insights' | 'playbooks' | 'approvals' | 'test-runner' | 'journey-intelligence' | 'revenue-intelligence' | 'data-integration' | 'settings' | 'outcome-roi' | 'portco';

interface Tab {
  id: TabId;
  label: string;
  /** CSM-friendly label used for Starter tier (optional) */
  starterLabel?: string;
  icon: React.ComponentType<{ className?: string }>;
  route: string;
  /** Feature gate — if set, tab requires this entitlement (from entitlements.py). */
  requiredFeature?: string;
}

// ============================================================
// HELPERS
// ============================================================

/** Get time-of-day greeting with emoji */
function getGreeting(): { text: string; icon: React.ComponentType<{ className?: string }> } {
  const hour = new Date().getHours();
  if (hour < 6)  return { text: 'Good night',      icon: Moon };
  if (hour < 12) return { text: 'Good morning',    icon: Sunrise };
  if (hour < 17) return { text: 'Good afternoon',  icon: Sun };
  if (hour < 21) return { text: 'Good evening',    icon: Sunset };
  return { text: 'Good night', icon: Moon };
}

/** Extract first name from full name */
function firstName(name: string): string {
  return name.split(' ')[0] || name;
}

// ============================================================
// TAB CONFIGURATION — with feature gates + starter labels
// ============================================================
// Feature gates map to entitlements.py FEATURE_CATALOG entries.
// Ungated tabs (no requiredFeature) are visible to all tiers.

const TABS: Tab[] = [
  { id: 'executive',             label: 'Executive Dashboard',        starterLabel: 'Portfolio Overview', icon: BarChart3,     route: '/dc-dashboard',                          requiredFeature: 'dashboards' },
  { id: 'tenants',               label: 'Tenants',                    starterLabel: 'Accounts',           icon: Users,         route: '/dc-dashboard/tenants',                  requiredFeature: 'health_scores' },
  { id: 'signals',               label: 'Signal Analyst',             icon: MessageSquare, route: '/dc-dashboard/signal-analyst',            requiredFeature: 'signal_analyst' },
  { id: 'ai-insights',           label: 'AI Insights',                icon: Brain,         route: '/dc-dashboard/ai-insights',              requiredFeature: 'rag_queries' },
  { id: 'admin-insights',        label: 'Admin Insights',             starterLabel: 'Insights',           icon: Activity,      route: '/dc-dashboard/admin-insights' },
  { id: 'playbooks',             label: 'Playbooks',                  icon: Zap,           route: '/dc-dashboard/playbooks',                requiredFeature: 'playbook_triggers' },
  { id: 'approvals',             label: 'Approval Queue',             icon: ShieldCheck,   route: '/dc-dashboard/approvals',                requiredFeature: 'approval_queue' },
  { id: 'test-runner',           label: 'Test Runner',                icon: FlaskConical,  route: '/test-runner',                           requiredFeature: 'test_runner_advanced' },
  { id: 'outcome-roi',           label: 'Outcome ROI',                starterLabel: 'ROI Analysis',       icon: DollarSign,    route: '/outcome-roi',                           requiredFeature: 'power_of_1' },
  { id: 'portco',                label: 'Power of 1 (Portfolio CEO)', starterLabel: 'Portfolio Synergy',  icon: Layers,        route: '/portco-dashboard',                      requiredFeature: 'portfolio_synergy' },
  { id: 'journey-intelligence',   label: 'Journey Intelligence',        icon: Activity,      route: '/dc-dashboard/journey-intelligence',     requiredFeature: 'health_scores' },
  { id: 'revenue-intelligence',  label: 'Revenue Intelligence',       icon: GitBranch,     route: '/dc-dashboard/revenue-intelligence',     requiredFeature: 'revenue_intelligence' },
  { id: 'data-integration',      label: 'Data Integration',           starterLabel: 'Upload Data',        icon: Upload,        route: '/dc-dashboard/data-integration',         requiredFeature: 'data_upload' },
  { id: 'settings',              label: 'Settings',                   icon: Settings,      route: '/dc-dashboard/settings' },
];

// ============================================================
// MAIN COMPONENT
// ============================================================

// ============================================================
// COMMAND PALETTE (Cmd+K / Ctrl+K)
// ============================================================

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  tabs: Tab[];
  isStarter: boolean;
  onSelect: (tab: Tab) => void;
  isTabAccessible: (tab: Tab) => boolean;
}

const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose, tabs, isStarter, onSelect, isTabAccessible }) => {
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (isOpen) setQuery('');
  }, [isOpen]);

  if (!isOpen) return null;

  const getTabLabel = (tab: Tab) => isStarter && tab.starterLabel ? tab.starterLabel : tab.label;

  const filteredTabs = tabs.filter(tab => {
    if (!isTabAccessible(tab)) return false;
    const label = getTabLabel(tab).toLowerCase();
    return label.includes(query.toLowerCase());
  });

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24" onClick={onClose}>
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />
      <div
        className="relative bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden border border-gray-200"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center px-4 py-3 border-b border-gray-100">
          <Search className="h-5 w-5 text-gray-400 mr-3" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Go to..."
            className="flex-1 outline-none text-sm text-gray-900 placeholder-gray-400"
            onKeyDown={e => {
              if (e.key === 'Escape') onClose();
              if (e.key === 'Enter' && filteredTabs.length > 0) {
                onSelect(filteredTabs[0]);
                onClose();
              }
            }}
          />
          <kbd className="hidden sm:inline-flex items-center px-2 py-0.5 text-xs text-gray-400 bg-gray-100 rounded">
            ESC
          </kbd>
        </div>
        <div className="max-h-64 overflow-y-auto py-2">
          {filteredTabs.length === 0 ? (
            <p className="text-sm text-gray-400 px-4 py-3 text-center">No matching pages</p>
          ) : (
            filteredTabs.map((tab, idx) => (
              <button
                key={tab.id}
                onClick={() => { onSelect(tab); onClose(); }}
                className="w-full flex items-center px-4 py-2.5 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-700 transition-colors"
              >
                <tab.icon className="h-4 w-4 mr-3 text-gray-400" />
                <span className="flex-1 text-left">{getTabLabel(tab)}</span>
                <kbd className="text-xs text-gray-300">{isStarter ? `\u2318${idx + 1}` : ''}</kbd>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================================
// MAIN COMPONENT
// ============================================================

const DCPlatform: React.FC = () => {
  const { session, logout } = useSession();
  const { check: checkEntitlement, tier, tierLabel: currentTierLabel } = useEntitlements();
  const navigate = useNavigate();
  const location = useLocation();
  const { accountId } = useParams<{ accountId?: string }>();

  const isStarter = tier === 'starter';

  // "Explore More" expander state (Starter only)
  const [exploreExpanded, setExploreExpanded] = useState(false);
  // Command palette state
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  // Track page transition
  const [transitioning, setTransitioning] = useState(false);
  // Product tour state (Starter only)
  const [showTour, setShowTour] = useState(() => {
    if (!isStarter) return false;
    return localStorage.getItem('tour_completed') !== 'true';
  });
  // KPI Glossary drawer
  const [glossaryOpen, setGlossaryOpen] = useState(false);

  // Check if a tab is accessible based on entitlements
  const isTabAccessible = (tab: Tab): boolean => {
    if (!tab.requiredFeature) return true; // ungated
    return checkEntitlement(tab.requiredFeature);
  };

  /** Get the display label for a tab — uses starterLabel for Starter tier */
  const getTabLabel = (tab: Tab): string => {
    return isStarter && tab.starterLabel ? tab.starterLabel : tab.label;
  };

  // Determine active tab from route
  const getActiveTabFromRoute = (): TabId => {
    const path = location.pathname;
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
    return 'executive';
  };

  const [activeTab, setActiveTab] = useState<TabId>(getActiveTabFromRoute());

  // Update active tab when route changes
  useEffect(() => {
    setActiveTab(getActiveTabFromRoute());
  }, [location.pathname]);

  // Keyboard shortcuts: Cmd/Ctrl+K for command palette, ? for KPI glossary
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(prev => !prev);
      }
      // ? key toggles KPI glossary (but not when typing in inputs)
      if (e.key === '?' && !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as HTMLElement)?.tagName)) {
        e.preventDefault();
        setGlossaryOpen(prev => !prev);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleTabClick = (tab: Tab) => {
    if (!isTabAccessible(tab)) return;
    // Page transition animation
    setTransitioning(true);
    setTimeout(() => setTransitioning(false), 150);
    setActiveTab(tab.id);
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

  // Split tabs into accessible vs locked (for Starter "Explore More")
  const accessibleTabs = TABS.filter(t => isTabAccessible(t));
  const lockedTabs = TABS.filter(t => !isTabAccessible(t));
  const greeting = getGreeting();
  const GreetingIcon = greeting.icon;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-gray-50 to-blue-50/20">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-md px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1">
            <div className="flex-1 text-center">
              <h1 className="text-xl font-bold text-gray-900">
                {isStarter ? 'CS Pulse' : 'Data Center Operations Platform - CS Pulse DC2_S'}
              </h1>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            {/* KPI Glossary button */}
            <button
              onClick={() => setGlossaryOpen(true)}
              title="KPI Glossary (press ?)"
              className="flex items-center px-2 py-1 text-xs text-gray-400 bg-gray-50 border border-gray-200 rounded-md hover:bg-gray-100 transition-colors"
            >
              ?
            </button>
            {/* Cmd+K hint */}
            <button
              onClick={() => setCommandPaletteOpen(true)}
              className="hidden sm:flex items-center px-2 py-1 text-xs text-gray-400 bg-gray-50 border border-gray-200 rounded-md hover:bg-gray-100 transition-colors"
            >
              <Command className="h-3 w-3 mr-1" />K
            </button>
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
        <nav className="w-64 bg-gradient-to-b from-slate-50 to-slate-100 border-r border-slate-200 shadow-sm px-4 py-6 flex flex-col min-h-[calc(100vh-73px)]">
          {/* Personalized greeting (Starter) or Tier badge (Pro/Ent) */}
          <div className="mb-4 px-4">
            {isStarter ? (
              <div className="mb-1">
                <div className="flex items-center space-x-1.5 text-gray-700 mb-0.5">
                  <GreetingIcon className="h-4 w-4 text-amber-500" />
                  <span className="text-sm font-medium">{greeting.text}, {firstName(session.user_name)}</span>
                </div>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                  Starter Plan
                </span>
              </div>
            ) : (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                tier === 'enterprise' ? 'bg-purple-100 text-purple-800' :
                tier === 'professional' ? 'bg-blue-100 text-blue-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {currentTierLabel} Plan
              </span>
            )}
          </div>

          {/* Tab buttons */}
          <div className="space-y-1 flex-1">
            {isStarter ? (
              <>
                {/* Starter: show only accessible tabs with data-tour attributes */}
                {accessibleTabs.map(tab => {
                  // Map tab IDs to data-tour identifiers for product tour targeting
                  const tourAttr: Record<string, string> = {
                    'executive': 'portfolio-overview',
                    'tenants': 'account-cards',
                    'data-integration': 'tab-upload',
                    'settings': 'tab-settings',
                  };
                  return (
                    <button
                      key={tab.id}
                      onClick={() => handleTabClick(tab)}
                      data-tour={tourAttr[tab.id] || undefined}
                      className={`w-full flex items-center px-4 py-3 rounded-lg text-left transition-all duration-200 ${
                        activeTab === tab.id
                          ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md transform scale-[1.02]'
                          : 'text-gray-700 hover:bg-white hover:shadow-sm hover:text-blue-600'
                      }`}
                    >
                      <tab.icon className={`h-5 w-5 mr-3 ${activeTab === tab.id ? 'text-white' : ''}`} />
                      <span className="font-medium text-sm">{getTabLabel(tab)}</span>
                    </button>
                  );
                })}

                {/* Explore More expander */}
                {lockedTabs.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-slate-200">
                    <button
                      onClick={() => setExploreExpanded(!exploreExpanded)}
                      className="w-full flex items-center px-4 py-2 text-xs font-medium text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      {exploreExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5 mr-2" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5 mr-2" />
                      )}
                      Explore More Features
                    </button>
                    {exploreExpanded && (
                      <div className="space-y-1 mt-1">
                        {lockedTabs.map(tab => {
                          const requiredTierName = tab.requiredFeature ? getRequiredTier(tab.requiredFeature) : null;
                          return (
                            <div
                              key={tab.id}
                              title={requiredTierName ? `Available on ${tierLabel(requiredTierName)}` : undefined}
                              className="w-full flex items-center px-4 py-2 rounded-lg opacity-50 cursor-default text-gray-400"
                            >
                              <tab.icon className="h-4 w-4 mr-3 text-gray-300" />
                              <span className="text-xs flex-1">{getTabLabel(tab)}</span>
                              <span className="text-[10px] text-gray-300 mr-1">
                                {requiredTierName === 'professional' ? 'Pro' : 'Ent'}
                              </span>
                              <Lock className="h-3 w-3 text-gray-300" />
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </>
            ) : (
              /* Professional/Enterprise: show all tabs with lock icons */
              TABS.map(tab => {
                const accessible = isTabAccessible(tab);
                const requiredTierName = tab.requiredFeature ? getRequiredTier(tab.requiredFeature) : null;
                return (
                  <button
                    key={tab.id}
                    onClick={() => handleTabClick(tab)}
                    disabled={!accessible}
                    title={!accessible && requiredTierName ? `Upgrade to ${tierLabel(requiredTierName)} to unlock` : undefined}
                    className={`w-full flex items-center px-4 py-3 rounded-lg text-left transition-all duration-200 ${
                      !accessible
                        ? 'opacity-50 cursor-not-allowed text-gray-400'
                        : activeTab === tab.id
                          ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md transform scale-[1.02]'
                          : 'text-gray-700 hover:bg-white hover:shadow-sm hover:text-blue-600'
                    }`}
                  >
                    <tab.icon className={`h-5 w-5 mr-3 ${activeTab === tab.id ? 'text-white' : !accessible ? 'text-gray-300' : ''}`} />
                    <span className="font-medium text-sm flex-1">{tab.label}</span>
                    {!accessible && <Lock className="h-3.5 w-3.5 text-gray-400 ml-1" />}
                  </button>
                );
              })
            )}
          </div>
          <div className="mt-4 pt-4 border-t border-slate-200">
            <NavLogoutButton variant="light-sidebar" />
          </div>
        </nav>

        {/* Main Content Area — with fade transition */}
        <main className={`flex-1 min-w-0 overflow-hidden p-8 bg-gradient-to-br from-gray-50 via-blue-50/30 to-indigo-50/30 transition-opacity duration-200 ${
          transitioning ? 'opacity-0' : 'opacity-100'
        }`}>
          {activeTab === 'executive' && <ExecutiveDashboard />}

          {activeTab === 'tenants' && <DCTenantHub />}

          {activeTab === 'signals' && (
            <div className="bg-white rounded-lg shadow-sm p-6">
              {accountId ? (
                <SignalAnalyst accountId={accountId} accountName={`Account ${accountId}`} />
              ) : (
                <div className="text-center py-12">
                  <p className="text-gray-600 mb-4">Please select an account to analyze</p>
                  <p className="text-sm text-gray-500">
                    Go to the {isStarter ? 'Accounts' : 'Tenants'} tab and click on an account to view Signal Analyst
                  </p>
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

          {activeTab === 'revenue-intelligence' && <DCRevenueIntelligence />}

          {activeTab === 'data-integration' && <DCDataIntegration />}

          {activeTab === 'settings' && <DCSettings />}
        </main>
      </div>

      {/* Command Palette (Cmd+K) */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        tabs={TABS}
        isStarter={isStarter}
        onSelect={handleTabClick}
        isTabAccessible={isTabAccessible}
      />

      {/* KPI Glossary Drawer */}
      <KPIGlossaryDrawer
        isOpen={glossaryOpen}
        onClose={() => setGlossaryOpen(false)}
      />

      {/* Product Tour (Starter only — auto-launches on first login) */}
      {showTour && (
        <ProductTour
          steps={STARTER_TOUR_STEPS}
          onComplete={() => setShowTour(false)}
          storageKey="tour_completed"
        />
      )}
    </div>
  );
};

export default DCPlatform;
