import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useParams } from 'react-router-dom';
import { useSession } from './contexts/SessionContext';
import LoginComponent from './components/LoginComponent';
import CSPlatform from './components/CSPlatform';
import Dashboard_dc from './components/Dashboard_dc';
import ExecutiveDashboard from './components/ExecutiveDashboard';
import DCPlatform from './components/dc/platform/dc_Platform';
import { OnboardingWizard } from './components/onboarding/OnboardingWizard';
import RegistrationForm from './components/RegistrationForm';
import JourneyVisualizer from './components/wizard/JourneyVisualizer';
import JourneyDashboardV3 from './components/journey-visualizer/JourneyDashboardV3';
import PortcoCEODashboard from './components/dashboard/PortcoCEODashboard';
import OutcomeROIDashboard from './components/dashboard/OutcomeROIDashboard';
import CRODashboard from './components/dashboard/CRODashboard';
import CFODashboard from './components/dashboard/CFODashboard';
import CSMDashboard from './components/csm/CSMDashboard';
import CSOpsIntegrationDashboard from './components/ops/CSOpsIntegrationDashboard';
import CEODashboard from './components/dashboard/CEODashboard';
import VPCSDashboard from './components/dashboard/VPCSDashboard';
import AESalesDashboard from './components/dashboard/AESalesDashboard';
import JourneyIntelligenceView from './components/journey-visualizer/JourneyIntelligenceView';
import AuctusAIWebsite from './components/AuctusAIWebsite';
import SuperAdminConsole from './components/SuperAdminConsole';
import EntitlementGuard from './components/shared/EntitlementGuard';
import AdminLayout from './components/admin-ui/AdminLayout';
import AdminDashboardPage from './components/admin-ui/AdminDashboardPage';
import CustomerListPage from './components/admin-ui/CustomerListPage';
import CustomerDetailPage from './components/admin-ui/CustomerDetailPage';
import VerticalListPage from './components/admin-ui/VerticalListPage';
import CustomVerticalWizard from './components/admin-ui/CustomVerticalWizard';
import LicenseManagerPage from './components/admin-ui/LicenseManagerPage';
import ActivityLogPage from './components/admin-ui/ActivityLogPage';

// Resolve dashboard route from session's dashboard_family (set by backend at login).
// Data-driven: new verticals work without code changes — backend sets dashboard_family.
const DC_FAMILIES = new Set(['datacenter']);
const getDashboardFamily = (session: any): 'datacenter' | 'saas' => {
  if (session?.dashboard_family) {
    return DC_FAMILIES.has(session.dashboard_family) ? 'datacenter' : 'saas';
  }
  // Fallback: derive from vertical string for sessions created before this change
  const v = (session?.vertical || localStorage.getItem('vertical') || '').toLowerCase().replace(/-/g, '_');
  if (['dc2_s', 'dc2s', 'dc', 'datacenter'].includes(v)) return 'datacenter';
  return 'saas';
};
const getDashboardRoute = (session: any): string => {
  return getDashboardFamily(session) === 'datacenter' ? '/cro-dashboard' : '/saas-dashboard';
};

// Component to redirect legacy /dashboard to appropriate vertical dashboard
const DashboardRedirect: React.FC = () => {
  const { session } = useSession();
  return <Navigate to={getDashboardRoute(session)} replace />;
};

const PrivateRoute: React.FC<{ children: React.ReactNode; vertical?: string }> = ({ children, vertical }) => {
  const { session } = useSession();

  // Check if user is logged in (has valid session)
  if (!session || !session.customer_id || !session.user_id) {
    return <Navigate to="/login" replace />;
  }

  // If vertical is specified, check if it matches the session's dashboard family
  if (vertical) {
    const family = getDashboardFamily(session);
    if (family !== vertical) {
      return <Navigate to={getDashboardRoute(session)} replace />;
    }
  }

  return <>{children}</>;
};

const LoginRoute: React.FC = () => {
  const { session, login } = useSession();
  const navigate = useNavigate();

  // If user is already logged in, redirect to appropriate dashboard
  if (session && session.customer_id && session.user_id) {
    return <Navigate to={getDashboardRoute(session)} replace />;
  }

  return (
    <LoginComponent
      onLogin={(newSession) => {
        login(newSession);
        // Fresh accounts (no data yet) go straight to the onboarding wizard
        if (newSession.onboarding_state === 'fresh') {
          navigate('/onboarding');
          return;
        }
        navigate(getDashboardRoute(newSession));
      }}
    />
  );
};

const RegisterRoute: React.FC = () => {
  const { session } = useSession();

  // If already logged in, redirect to appropriate dashboard
  if (session && session.customer_id && session.user_id) {
    return <Navigate to={getDashboardRoute(session)} replace />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center flex flex-col items-center">
          <h2 className="text-2xl font-bold text-gray-900 text-center">Customer Success Value Management System</h2>
          <p className="mt-2 text-sm text-gray-600 text-center">CS Pulse Growth</p>
        </div>

        <RegisterFormComponent />
      </div>
    </div>
  );
};

const OnboardingWizardRoute: React.FC = () => {
  return <OnboardingWizard />;
};

const RegisterFormComponent: React.FC = () => {
  const navigate = useNavigate();

  return (
    <RegistrationForm
      onSuccess={() => {
        window.location.href = '/login';
      }}
      onCancel={() => navigate('/login')}
    />
  );
};

const AppRoutes: React.FC = () => {
  return (
    <Router
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
        <Route path="/register" element={<RegisterRoute />} />
        
        {/* Data Center Dashboard Routes with sub-paths - MUST come BEFORE /dc-dashboard */}
        {/* More specific routes first to prevent /dc-dashboard from matching sub-routes */}
        <Route
          path="/dc-dashboard/tenants/:accountId"
          element={
            <PrivateRoute vertical="datacenter">
              <DCPlatform />
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/tenants"
          element={
            <PrivateRoute vertical="datacenter">
              <DCPlatform />
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/signal-analyst"
          element={
            <PrivateRoute vertical="datacenter">
              <DCPlatform />
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/ai-insights"
          element={
            <PrivateRoute vertical="datacenter">
              <DCPlatform />
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/admin-insights"
          element={
            <PrivateRoute vertical="datacenter">
              <DCPlatform />
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/playbooks"
          element={
            <PrivateRoute vertical="datacenter">
              <DCPlatform />
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/approvals"
          element={
            <PrivateRoute vertical="datacenter">
              <DCPlatform />
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/test-runner"
          element={
            <PrivateRoute vertical="datacenter">
              <DCPlatform />
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/revenue-intelligence"
          element={
            <PrivateRoute vertical="datacenter">
              <DCPlatform />
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/journey-intelligence"
          element={
            <PrivateRoute vertical="datacenter">
              <JourneyIntelligenceView />
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/csm"
          element={
            <PrivateRoute vertical="datacenter">
              <CSMDashboard />
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/cro"
          element={
            <PrivateRoute vertical="datacenter">
              <EntitlementGuard feature="revenue_intelligence"><CRODashboard /></EntitlementGuard>
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/cfo"
          element={
            <PrivateRoute vertical="datacenter">
              <EntitlementGuard feature="revenue_intelligence"><CFODashboard /></EntitlementGuard>
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/ops"
          element={
            <PrivateRoute vertical="datacenter">
              <EntitlementGuard feature="dashboards"><CSOpsIntegrationDashboard /></EntitlementGuard>
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/ceo"
          element={
            <PrivateRoute vertical="datacenter">
              <EntitlementGuard feature="revenue_intelligence"><CEODashboard /></EntitlementGuard>
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/vpcs"
          element={
            <PrivateRoute vertical="datacenter">
              <EntitlementGuard feature="dashboards"><VPCSDashboard /></EntitlementGuard>
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/sales"
          element={
            <PrivateRoute vertical="datacenter">
              <EntitlementGuard feature="dashboards"><AESalesDashboard /></EntitlementGuard>
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/data-integration"
          element={
            <PrivateRoute vertical="datacenter">
              <DCPlatform />
            </PrivateRoute>
          }
        />
        <Route
          path="/dc-dashboard/settings"
          element={
            <PrivateRoute vertical="datacenter">
              <DCPlatform />
            </PrivateRoute>
          }
        />
        
        {/* Data Center Dashboard - New 7-tab Platform (base route - must come AFTER sub-routes) */}
        <Route
          path="/dc-dashboard"
          element={
            <PrivateRoute vertical="datacenter">
              <DCPlatform />
            </PrivateRoute>
          }
        />
        
        {/* Short persona routes — clean URLs for demos, accessible to ALL verticals */}
        {/* CRO/CFO require revenue_intelligence entitlement; others require base dashboards */}
        <Route path="/cro" element={<PrivateRoute><EntitlementGuard feature="revenue_intelligence"><CRODashboard /></EntitlementGuard></PrivateRoute>} />
        <Route path="/cfo" element={<PrivateRoute><EntitlementGuard feature="revenue_intelligence"><CFODashboard /></EntitlementGuard></PrivateRoute>} />
        <Route path="/ceo" element={<PrivateRoute><EntitlementGuard feature="revenue_intelligence"><CEODashboard /></EntitlementGuard></PrivateRoute>} />
        <Route path="/csm" element={<PrivateRoute><EntitlementGuard feature="dashboards"><CSMDashboard /></EntitlementGuard></PrivateRoute>} />
        <Route path="/vpcs" element={<PrivateRoute><EntitlementGuard feature="dashboards"><VPCSDashboard /></EntitlementGuard></PrivateRoute>} />
        <Route path="/ops" element={<PrivateRoute><EntitlementGuard feature="dashboards"><CSOpsIntegrationDashboard /></EntitlementGuard></PrivateRoute>} />
        <Route path="/sales" element={<PrivateRoute><EntitlementGuard feature="dashboards"><AESalesDashboard /></EntitlementGuard></PrivateRoute>} />

        {/* Data Center Dashboard - Legacy (keep for backward compatibility) */}
        <Route
          path="/dc-dashboard-legacy"
          element={
            <PrivateRoute vertical="datacenter">
              <Dashboard_dc />
            </PrivateRoute>
          }
        />
        
        {/* SaaS Persona Dashboard Routes */}
        <Route path="/saas-dashboard/csm" element={<PrivateRoute vertical="saas"><EntitlementGuard feature="dashboards"><CSMDashboard /></EntitlementGuard></PrivateRoute>} />
        <Route path="/saas-dashboard/vpcs" element={<PrivateRoute vertical="saas"><EntitlementGuard feature="dashboards"><VPCSDashboard /></EntitlementGuard></PrivateRoute>} />
        <Route path="/saas-dashboard/cro" element={<PrivateRoute vertical="saas"><EntitlementGuard feature="revenue_intelligence"><CRODashboard /></EntitlementGuard></PrivateRoute>} />
        <Route path="/saas-dashboard/cfo" element={<PrivateRoute vertical="saas"><EntitlementGuard feature="revenue_intelligence"><CFODashboard /></EntitlementGuard></PrivateRoute>} />
        <Route path="/saas-dashboard/ceo" element={<PrivateRoute vertical="saas"><EntitlementGuard feature="revenue_intelligence"><CEODashboard /></EntitlementGuard></PrivateRoute>} />
        <Route path="/saas-dashboard/sales" element={<PrivateRoute vertical="saas"><EntitlementGuard feature="dashboards"><AESalesDashboard /></EntitlementGuard></PrivateRoute>} />
        <Route path="/saas-dashboard/ops" element={<PrivateRoute vertical="saas"><EntitlementGuard feature="dashboards"><CSOpsIntegrationDashboard /></EntitlementGuard></PrivateRoute>} />

        {/* SaaS Dashboard — base platform (must come AFTER sub-routes) */}
        <Route
          path="/saas-dashboard"
          element={
            <PrivateRoute vertical="saas">
              <CSPlatform />
            </PrivateRoute>
          }
        />
        
        {/* Legacy route - redirect to appropriate vertical dashboard */}
        <Route
          path="/dashboard"
          element={
            <PrivateRoute>
              <DashboardRedirect />
            </PrivateRoute>
          }
        />
        
        {/* Executive Dashboard - accessible from both verticals */}
        <Route
          path="/executive-dashboard"
          element={
            <PrivateRoute>
              <ExecutiveDashboard />
            </PrivateRoute>
          }
        />

        {/* CRO Dashboard - Revenue Intelligence view */}
        <Route
          path="/cro-dashboard"
          element={
            <PrivateRoute>
              <CRODashboard />
            </PrivateRoute>
          }
        />

        {/* CFO Dashboard - Investment Intelligence view */}
        <Route
          path="/cfo-dashboard"
          element={
            <PrivateRoute>
              <CFODashboard />
            </PrivateRoute>
          }
        />
        
        {/* PortCo CEO Dashboard - PE portfolio synergy view */}
        <Route
          path="/portco-dashboard"
          element={
            <PrivateRoute>
              <EntitlementGuard feature="portfolio_synergy"><PortcoCEODashboard /></EntitlementGuard>
            </PrivateRoute>
          }
        />

        {/* Outcome ROI Dashboard - Historical proof + Forward projection */}
        <Route
          path="/outcome-roi"
          element={
            <PrivateRoute>
              <OutcomeROIDashboard />
            </PrivateRoute>
          }
        />

        {/* Onboarding - accessible from both verticals */}
        <Route
          path="/onboarding"
          element={
            <PrivateRoute>
              <OnboardingWizardRoute />
            </PrivateRoute>
          }
        />
        
        {/* Journey Visualizer - Wizard A/B Dashboard */}
        <Route
          path="/journey-visualizer"
          element={
            <PrivateRoute>
              <JourneyVisualizer />
            </PrivateRoute>
          }
        />
        
        {/* Journey - Account-specific journey view (alias for journey-v3) */}
        <Route
          path="/journey/:accountId"
          element={
            <PrivateRoute>
              <JourneyDashboardV3 />
            </PrivateRoute>
          }
        />

        {/* Journey V3 - Account-specific journey view */}
        <Route
          path="/journey-v3/:accountId"
          element={
            <PrivateRoute>
              <JourneyDashboardV3 />
            </PrivateRoute>
          }
        />
        
        {/* Super Admin Console — standalone platform management UI */}
        <Route
          path="/super-admin"
          element={
            <PrivateRoute>
              <SuperAdminConsole />
            </PrivateRoute>
          }
        />

        {/* Admin Console — full management UI with sidebar layout */}
        <Route
          path="/admin"
          element={
            <PrivateRoute>
              <AdminLayout />
            </PrivateRoute>
          }
        >
          <Route index element={<AdminDashboardPage />} />
          <Route path="customers" element={<CustomerListPage />} />
          <Route path="customers/:id" element={<CustomerDetailPage />} />
          <Route path="verticals" element={<VerticalListPage />} />
          <Route path="custom-vertical" element={<CustomVerticalWizard />} />
          <Route path="licenses" element={<LicenseManagerPage />} />
          <Route path="activity" element={<ActivityLogPage />} />
        </Route>

        {/* Public marketing website */}
        <Route path="/website" element={<AuctusAIWebsite />} />

        <Route path="/" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
};

const App: React.FC = () => {
  return <AppRoutes />;
};

export default App;