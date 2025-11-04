import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { SessionProvider, useSession } from './contexts/SessionContext';
import LoginComponent from './components/LoginComponent';
import CSPlatform from './components/CSPlatform';
import RegistrationForm from './components/RegistrationForm';
import { TrendingUp } from 'lucide-react';

const PrivateRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { session } = useSession();

  // Check if user is logged in (has valid session)
  if (!session || !session.customer_id || !session.user_id) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

const LoginRoute: React.FC = () => {
  const { session, login } = useSession();

  // If user is already logged in, redirect to dashboard
  if (session && session.customer_id && session.user_id) {
    return <Navigate to="/dashboard" replace />;
  }

  return <LoginComponent onLogin={login} />;
};

const RegisterRoute: React.FC = () => {
  const { session } = useSession();

  // If already logged in, redirect to dashboard
  if (session && session.customer_id && session.user_id) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center flex flex-col items-center">
          <div className="mx-auto mb-6">
            <img 
              src="/company-logo.png" 
              alt="Company Logo" 
              className="h-32 w-auto object-contain"
              onError={(e) => {
                e.currentTarget.style.display = 'none';
                const fallback = e.currentTarget.nextElementSibling as HTMLElement;
                if (fallback) fallback.style.display = 'flex';
              }}
            />
            <div className="h-24 w-24 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl items-center justify-center mx-auto" style={{display: 'none'}}>
              <TrendingUp className="h-12 w-12 text-white mx-auto" />
            </div>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 text-center">Customer Success Value Management System</h2>
          <p className="mt-2 text-sm text-gray-600 text-center">A Triad Partner AI Solution</p>
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
        <Route
          path="/dashboard"
          element={
            <PrivateRoute>
              <CSPlatform />
            </PrivateRoute>
          }
        />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
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