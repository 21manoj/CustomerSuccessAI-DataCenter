import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, Eye, EyeOff } from 'lucide-react';

interface LoginProps {
  onLogin: (session: { 
    customer_id: number; 
    user_id: string; 
    user_name: string; 
    email: string;
    vertical?: string;
  }) => void;
}

const LoginComponent: React.FC<LoginProps> = ({ onLogin }) => {
  const [vertical, setVertical] = useState('saas'); // Default to SaaS
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email, password, vertical })
    });

      // Check content type before parsing
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        throw new Error('Backend is not responding correctly. Please wait a moment and try again.');
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Login failed');
      }

      const data = await response.json();
      
      // Get vertical from response or use the one selected
      const sessionVertical = data.vertical || vertical;
      
      const session = {
        customer_id: data.user?.customer_id || data.customer_id || 1,
        user_id: data.user?.user_id?.toString() || data.user_id?.toString() || '1',
        user_name: data.user?.customer_name || data.user_name || 'User',
        email: data.user?.email || data.email || '',
        vertical: sessionVertical
    };

      // Store vertical in localStorage
      localStorage.setItem('vertical', sessionVertical);
      
      onLogin(session);
    } catch (err) {
      if (err instanceof Error && err.message.includes('JSON')) {
        setError('Backend is starting up. Please wait a few seconds and try again.');
      } else {
        setError(err instanceof Error ? err.message : 'Login failed');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center flex flex-col items-center">
          <h2 className="text-2xl font-bold text-gray-900 text-center">Customer Success Value Management System</h2>
          <p className="mt-2 text-sm text-gray-600 text-center">CS Pulse Growth</p>
        </div>

        <div className="bg-white rounded-xl shadow-lg p-8">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            {/* Vertical Selector */}
            <div>
              <label htmlFor="vertical" className="block text-sm font-medium text-gray-700 mb-2">
                Customer Type
              </label>
              <select
                id="vertical"
                name="vertical"
                value={vertical}
                onChange={(e) => setVertical(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              >
                <option value="saas">SaaS Customer Success</option>
                <option value="datacenter">Data Center</option>
              </select>
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email Address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your email"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-10"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400" />
                  )}
                </button>
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Signing in...' : `Login to ${vertical === 'datacenter' ? 'Data Center' : 'SaaS'} Portal`}
              </button>
            </div>
          </form>

          <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-gray-700 text-center mb-2">New Company?</p>
            <Link
              to="/register"
              className="block w-full py-2 px-4 border border-green-600 rounded-lg text-sm font-medium text-green-700 hover:bg-green-100 text-center"
            >
              Create New Account
            </Link>
          </div>

          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-gray-700 text-center">
              For demo credentials, please email{' '}
              <a 
                href="mailto:support@cspulsegrowth.com" 
                className="text-blue-600 hover:text-blue-800 font-medium underline"
              >
                support@cspulsegrowth.com
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginComponent;
