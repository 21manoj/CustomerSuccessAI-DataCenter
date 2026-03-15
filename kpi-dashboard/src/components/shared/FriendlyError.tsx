/**
 * FriendlyError — User-friendly error message component
 * =======================================================
 *
 * Replaces technical error messages with plain-English, actionable alternatives.
 * Used across Starter-tier pages for better UX.
 *
 * Usage:
 *   <FriendlyError error={error} onRetry={() => retry()} />
 */

import React from 'react';
import { AlertTriangle, RefreshCw, ArrowRight, WifiOff, Lock, FileWarning } from 'lucide-react';

interface FriendlyErrorProps {
  /** The raw error (string, Error object, or status code) */
  error: string | Error | number;
  /** Optional retry handler */
  onRetry?: () => void;
  /** Optional navigation action */
  onNavigate?: { label: string; onClick: () => void };
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
}

/** Map common errors to friendly messages */
function getFriendlyMessage(error: string | Error | number): {
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
} {
  const errorStr = typeof error === 'number'
    ? `HTTP ${error}`
    : error instanceof Error
      ? error.message
      : error;

  const lower = errorStr.toLowerCase();

  // 403 / Forbidden → Upgrade prompt
  if (lower.includes('403') || lower.includes('forbidden') || lower.includes('upgrade')) {
    return {
      title: 'Feature not available on your plan',
      description: 'This feature is available on a higher plan. Talk to your admin about upgrading.',
      icon: Lock,
      color: 'amber',
    };
  }

  // 404 / Not found
  if (lower.includes('404') || lower.includes('not found')) {
    return {
      title: 'Not found',
      description: "We couldn't find what you're looking for. It may have been moved or deleted.",
      icon: FileWarning,
      color: 'gray',
    };
  }

  // No data
  if (lower.includes('no data') || lower.includes('no customer') || lower.includes('no accounts') || lower.includes('customer_id')) {
    return {
      title: 'No data uploaded yet',
      description: 'Upload your account list to get started. Health scores will appear after your first data upload.',
      icon: FileWarning,
      color: 'blue',
    };
  }

  // CSV / Schema errors
  if (lower.includes('csv') || lower.includes('schema') || lower.includes('column') || lower.includes('invalid')) {
    return {
      title: 'File format issue',
      description: "Some columns don't match what we expected. Check your column headers against the template.",
      icon: FileWarning,
      color: 'amber',
    };
  }

  // Connection errors
  if (lower.includes('connection') || lower.includes('network') || lower.includes('refused') || lower.includes('timeout') || lower.includes('fetch')) {
    return {
      title: 'Connection issue',
      description: 'Having trouble connecting to the server. Try refreshing in a few seconds.',
      icon: WifiOff,
      color: 'red',
    };
  }

  // 401 / Auth
  if (lower.includes('401') || lower.includes('unauthorized') || lower.includes('session')) {
    return {
      title: 'Session expired',
      description: 'Your session has expired. Please log in again to continue.',
      icon: Lock,
      color: 'amber',
    };
  }

  // Default
  return {
    title: 'Something went wrong',
    description: 'An unexpected error occurred. Try refreshing the page.',
    icon: AlertTriangle,
    color: 'red',
  };
}

const colorClasses: Record<string, { bg: string; border: string; title: string; desc: string; icon: string }> = {
  red: { bg: 'bg-red-50', border: 'border-red-200', title: 'text-red-900', desc: 'text-red-700', icon: 'text-red-500' },
  amber: { bg: 'bg-amber-50', border: 'border-amber-200', title: 'text-amber-900', desc: 'text-amber-700', icon: 'text-amber-500' },
  blue: { bg: 'bg-blue-50', border: 'border-blue-200', title: 'text-blue-900', desc: 'text-blue-700', icon: 'text-blue-500' },
  gray: { bg: 'bg-gray-50', border: 'border-gray-200', title: 'text-gray-900', desc: 'text-gray-600', icon: 'text-gray-400' },
};

const FriendlyError: React.FC<FriendlyErrorProps> = ({
  error,
  onRetry,
  onNavigate,
  size = 'md',
}) => {
  const { title, description, icon: Icon, color } = getFriendlyMessage(error);
  const c = colorClasses[color] || colorClasses.red;

  const padding = size === 'sm' ? 'p-3' : size === 'lg' ? 'p-6' : 'p-4';
  const iconSize = size === 'sm' ? 'h-4 w-4' : size === 'lg' ? 'h-6 w-6' : 'h-5 w-5';

  return (
    <div className={`${c.bg} border ${c.border} rounded-lg ${padding}`}>
      <div className="flex items-start space-x-3">
        <Icon className={`${iconSize} ${c.icon} flex-shrink-0 mt-0.5`} />
        <div className="flex-1">
          <p className={`font-medium ${c.title} ${size === 'sm' ? 'text-sm' : ''}`}>{title}</p>
          <p className={`${c.desc} mt-1 ${size === 'sm' ? 'text-xs' : 'text-sm'}`}>{description}</p>
          {(onRetry || onNavigate) && (
            <div className="flex items-center space-x-3 mt-3">
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="inline-flex items-center text-sm text-gray-600 hover:text-gray-800 bg-white px-3 py-1.5 rounded-md border border-gray-200 transition-colors"
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" /> Try again
                </button>
              )}
              {onNavigate && (
                <button
                  onClick={onNavigate.onClick}
                  className="inline-flex items-center text-sm text-blue-600 hover:text-blue-700 transition-colors"
                >
                  {onNavigate.label} <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FriendlyError;
