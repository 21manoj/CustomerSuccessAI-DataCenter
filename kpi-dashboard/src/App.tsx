import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { SessionProvider, useSession } from './contexts/SessionContext';
import LoginComponent from './components/LoginComponent';
import CSPlatform from './components/CSPlatform';
import Dashboard_dc from './components/Dashboard_dc';
import ExecutiveDashboard from './components/ExecutiveDashboard';
import OnboardingWizard from './components/onboarding/OnboardingWizard';
import RegistrationForm from './components/RegistrationForm';
import { TrendingUp } from 'lucide-react';

// Component to redirect legacy /dashboard to appropriate vertical dashboard
const DashboardRedirect: React.FC = () => {
  const { session } = useSession();
  const vertical = session?.vertical || localStorage.getItem('vertical') || 'saas';
  const dashboardRoute = vertical === 'datacenter' ? '/dc-dashboard' : '/saas-dashboard';
  return <Navigate to={dashboardRoute} replace />;
};

const PrivateRoute: React.FC<{ children: React.ReactNode; vertical?: string }> = ({ children, vertical }) => {
  const { session } = useSession();

  // Check if user is logged in (has valid session)
  if (!session || !session.customer_id || !session.user_id) {
    return <Navigate to="/login" replace />;
  }

  // If vertical is specified, check if it matches the session vertical
  if (vertical) {
    const sessionVertical = session.vertical || localStorage.getItem('vertical') || 'saas';
    
    if (sessionVertical !== vertical) {
      // Redirect to correct dashboard based on session vertical
      const correctRoute = sessionVertical === 'datacenter' ? '/dc-dashboard' : '/saas-dashboard';
      return <Navigate to={correctRoute} replace />;
    }
  }

  return <>{children}</>;
};

const LoginRoute: React.FC = () => {
  const { session, login } = useSession();
  const navigate = useNavigate();

  // If user is already logged in, redirect to appropriate dashboard based on vertical
  if (session && session.customer_id && session.user_id) {
    const vertical = session.vertical || localStorage.getItem('vertical') || 'saas';
    const dashboardRoute = vertical === 'datacenter' ? '/dc-dashboard' : '/saas-dashboard';
    return <Navigate to={dashboardRoute} replace />;
  }

  return (
    <LoginComponent
      onLogin={(newSession) => {
        login(newSession);
        // Route to appropriate dashboard based on vertical
        const vertical = newSession.vertical || 'saas';
        const dashboardRoute = vertical === 'datacenter' ? '/dc-dashboard' : '/saas-dashboard';
        navigate(dashboardRoute);
      }}
    />
  );
};

const RegisterRoute: React.FC = () => {
  const { session } = useSession();

  // If already logged in, redirect to appropriate dashboard based on vertical
  if (session && session.customer_id && session.user_id) {
    const vertical = session.vertical || localStorage.getItem('vertical') || 'saas';
    const dashboardRoute = vertical === 'datacenter' ? '/dc-dashboard' : '/saas-dashboard';
    return <Navigate to={dashboardRoute} replace />;
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
    <Router>
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
        <Route path="/register" element={<RegisterRoute />} />
        
        {/* Data Center Dashboard */}
        <Route
          path="/dc-dashboard"
          element={
            <PrivateRoute vertical="datacenter">
              <Dashboard_dc />
            </PrivateRoute>
          }
        />
        
        {/* SaaS Dashboard */}
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
        
        {/* Onboarding - accessible from both verticals */}
        <Route
          path="/onboarding"
          element={
            <PrivateRoute>
              <OnboardingWizard />
            </PrivateRoute>
          }
        />
        
        <Route path="/" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
};

const App: React.FC = () => {
  return (
    <SessionProvider>
      <AppRoutes />
    </SessionProvider>
  );
};

export default App; 