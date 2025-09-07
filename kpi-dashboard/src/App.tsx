import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { SessionProvider, useSession } from './contexts/SessionContext';
import LoginComponent from './components/LoginComponent';
import CSPlatform from './components/CSPlatform';

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

const AppRoutes: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginRoute />} />
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