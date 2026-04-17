import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { CheckCircle, XCircle, Loader2, Sparkles } from 'lucide-react';

interface MagicLinkVerifyProps {
  onLogin: (session: {
    customer_id: number;
    user_id: string;
    user_name: string;
    email: string;
    vertical?: string;
    dashboard_family?: string;
    role?: string;
    customer_uuid?: string;
    user_uuid?: string;
  }) => void;
}

const MagicLinkVerify: React.FC<MagicLinkVerifyProps> = ({ onLogin }) => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setStatus('error');
      setErrorMessage('No token provided. Please request a new magic link.');
      return;
    }

    const verify = async () => {
      try {
        const response = await fetch(`/api/auth/verify-magic-link?token=${encodeURIComponent(token)}`, {
          credentials: 'include',
        });

        const data = await response.json();

        if (!response.ok) {
          setStatus('error');
          setErrorMessage(data.message || 'Verification failed');
          return;
        }

        setStatus('success');

        // Build session from verify response (same shape as login)
        const session = {
          customer_id: data.user?.customer_id || 1,
          user_id: data.user?.user_id?.toString() || '1',
          user_name: data.user?.user_name || data.user?.customer_name || 'User',
          email: data.user?.email || '',
          vertical: data.vertical || 'saas_premium',
          dashboard_family: data.dashboard_family || 'saas',
          role: data.user?.role || undefined,
          customer_uuid: data.user?.customer_uuid || undefined,
          user_uuid: data.user?.user_uuid || undefined,
        };

        localStorage.setItem('vertical', session.vertical || '');

        // Brief delay to show success state, then redirect
        setTimeout(() => onLogin(session), 1500);
      } catch (err) {
        setStatus('error');
        setErrorMessage('Network error. Please try again.');
      }
    };

    verify();
  }, [searchParams, onLogin]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="flex items-center justify-center gap-2 mb-3">
            <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="text-emerald-400 font-bold text-lg tracking-wider">CS PULSE</span>
          </div>
        </div>

        <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl shadow-2xl p-8">
          {status === 'verifying' && (
            <div className="text-center space-y-4">
              <Loader2 className="w-12 h-12 text-emerald-400 animate-spin mx-auto" />
              <h3 className="text-lg font-semibold text-white">Verifying magic link...</h3>
              <p className="text-sm text-slate-400">Please wait while we sign you in.</p>
            </div>
          )}

          {status === 'success' && (
            <div className="text-center space-y-4">
              <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto" />
              <h3 className="text-lg font-semibold text-white">You're signed in!</h3>
              <p className="text-sm text-slate-400">Redirecting to your dashboard...</p>
            </div>
          )}

          {status === 'error' && (
            <div className="text-center space-y-4">
              <XCircle className="w-12 h-12 text-red-400 mx-auto" />
              <h3 className="text-lg font-semibold text-white">Link expired or invalid</h3>
              <p className="text-sm text-slate-400">{errorMessage}</p>
              <div className="pt-4">
                <Link
                  to="/login"
                  className="inline-block py-2.5 px-6 rounded-lg text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-500 transition-colors"
                >
                  Request a new magic link
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MagicLinkVerify;
