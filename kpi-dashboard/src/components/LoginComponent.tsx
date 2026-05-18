import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye, EyeOff, Mail, ArrowLeft, Sparkles } from 'lucide-react';

interface LoginProps {
  onLogin: (session: {
    customer_id: number;
    customer_name?: string;
    user_id: string;
    user_name: string;
    email: string;
    vertical?: string;
    dashboard_family?: string;
    role?: string;
    customer_uuid?: string;
    user_uuid?: string;
    tier?: 'starter' | 'professional' | 'enterprise';
    entitlements?: Record<string, boolean>;
    allowed_account_ids?: number[] | null;
    allowed_customer_ids?: number[] | null;
    onboarding_state?: 'fresh' | 'data_uploaded' | 'active';
  }) => void;
}

type LoginMode = 'magic-link' | 'password';

const LoginComponent: React.FC<LoginProps> = ({ onLogin }) => {
  const [mode, setMode] = useState<LoginMode>('magic-link');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [magicLinkSent, setMagicLinkSent] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        throw new Error('Backend is not responding correctly. Please wait a moment and try again.');
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Login failed');
      }

      const data = await response.json();
      const sessionVertical = data.vertical || data.user?.vertical || 'saas_premium';
      const dashboardFamily = data.dashboard_family || 'saas';

      const session = {
        customer_id: data.user?.customer_id || data.customer_id || 1,
        customer_name: data.user?.customer_name || data.customer_name || undefined,
        user_id: data.user?.user_id?.toString() || data.user_id?.toString() || '1',
        user_name: data.user?.user_name || data.user_name || 'User',
        email: data.user?.email || data.email || '',
        vertical: sessionVertical,
        dashboard_family: dashboardFamily,
        role: data.user?.role || undefined,
        customer_uuid: data.user?.customer_uuid || undefined,
        user_uuid: data.user?.user_uuid || undefined,
        tier: data.user?.tier || undefined,
        entitlements: data.user?.entitlements || undefined,
        onboarding_state: data.user?.onboarding_state || undefined,
        allowed_account_ids: data.user?.allowed_account_ids || null,
        allowed_customer_ids: data.user?.allowed_customer_ids || null,
      };

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

  const handleMagicLinkRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch('/api/auth/magic-link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to send magic link');
      }

      setMagicLinkSent(true);
      startResendCooldown();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send magic link');
    } finally {
      setIsLoading(false);
    }
  };

  const startResendCooldown = () => {
    setResendCooldown(60);
    const interval = setInterval(() => {
      setResendCooldown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleResend = () => {
    setMagicLinkSent(false);
    setError('');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-6">
        {/* Header */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-2 mb-3">
            <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-emerald-400 font-bold text-lg tracking-wider">CS PULSE</span>
          </div>
          <h2 className="text-2xl font-bold text-white">Revenue Intelligence Platform</h2>
          <p className="mt-1 text-sm text-slate-400">Sign in to your account</p>
        </div>

        {/* Login Card */}
        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl shadow-2xl p-8">

          {/* Magic Link Sent State */}
          {magicLinkSent ? (
            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto">
                <Mail className="w-8 h-8 text-emerald-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">Check your email</h3>
              <p className="text-sm text-slate-400">
                We sent a magic link to <span className="text-white font-medium">{email}</span>.
                Click the link to sign in instantly.
              </p>
              <p className="text-xs text-slate-500">Link expires in 15 minutes.</p>

              <div className="pt-4 space-y-3">
                {resendCooldown > 0 ? (
                  <p className="text-xs text-slate-500">Resend available in {resendCooldown}s</p>
                ) : (
                  <button
                    onClick={handleResend}
                    className="text-sm text-emerald-400 hover:text-emerald-300 font-medium"
                  >
                    Didn't receive it? Send again
                  </button>
                )}

                <button
                  onClick={() => { setMagicLinkSent(false); setMode('password'); }}
                  className="flex items-center gap-1 text-sm text-slate-400 hover:text-slate-300 mx-auto"
                >
                  <ArrowLeft className="w-3 h-3" />
                  Sign in with password instead
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Mode Tabs */}
              <div className="flex mb-6 bg-slate-900/50 rounded-lg p-1">
                <button
                  onClick={() => { setMode('magic-link'); setError(''); }}
                  className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all ${
                    mode === 'magic-link'
                      ? 'bg-emerald-500 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-300'
                  }`}
                >
                  Magic Link
                </button>
                <button
                  onClick={() => { setMode('password'); setError(''); }}
                  className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all ${
                    mode === 'password'
                      ? 'bg-emerald-500 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-300'
                  }`}
                >
                  Password
                </button>
              </div>

              {/* Error */}
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 mb-4">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              )}

              {/* Magic Link Form */}
              {mode === 'magic-link' && (
                <form onSubmit={handleMagicLinkRequest} className="space-y-4">
                  <div>
                    <label htmlFor="magic-email" className="block text-sm font-medium text-slate-300 mb-2">
                      Email Address
                    </label>
                    <input
                      id="magic-email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full px-3 py-2.5 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                      placeholder="you@company.com"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full py-2.5 px-4 rounded-lg text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 focus:ring-offset-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isLoading ? 'Sending...' : 'Send Magic Link'}
                  </button>
                  <p className="text-xs text-slate-500 text-center">
                    No password needed. We'll email you a one-time sign-in link.
                  </p>
                </form>
              )}

              {/* Password Form */}
              {mode === 'password' && (
                <form onSubmit={handlePasswordLogin} className="space-y-4">
                  <div>
                    <label htmlFor="password-email" className="block text-sm font-medium text-slate-300 mb-2">
                      Email Address
                    </label>
                    <input
                      id="password-email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full px-3 py-2.5 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                      placeholder="you@company.com"
                    />
                  </div>
                  <div>
                    <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-2">
                      Password
                    </label>
                    <div className="relative">
                      <input
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="current-password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full px-3 py-2.5 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:ring-2 focus:ring-emerald-500 focus:border-transparent pr-10"
                        placeholder="Enter your password"
                      />
                      <button
                        type="button"
                        className="absolute inset-y-0 right-0 pr-3 flex items-center"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4 text-slate-500" />
                        ) : (
                          <Eye className="h-4 w-4 text-slate-500" />
                        )}
                      </button>
                    </div>
                  </div>
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full py-2.5 px-4 rounded-lg text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 focus:ring-offset-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isLoading ? 'Signing in...' : 'Sign In'}
                  </button>
                </form>
              )}
            </>
          )}
        </div>

        {/* Footer Links */}
        <div className="space-y-3">
          <div className="bg-slate-800/30 border border-slate-700/50 rounded-lg p-4 text-center">
            <p className="text-sm text-slate-400 mb-2">New to CS Pulse?</p>
            <Link
              to="/register"
              className="inline-block py-2 px-6 border border-emerald-500/50 rounded-lg text-sm font-medium text-emerald-400 hover:bg-emerald-500/10 transition-colors"
            >
              Create Account
            </Link>
          </div>
          <p className="text-xs text-slate-600 text-center">
            CS Pulse Revenue Intelligence Platform
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginComponent;
