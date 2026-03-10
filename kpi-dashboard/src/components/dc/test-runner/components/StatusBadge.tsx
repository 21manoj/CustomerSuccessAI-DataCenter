/**
 * StatusBadge — Reusable status indicator chip
 */

import React from 'react';
import {
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
} from 'lucide-react';

const STYLES: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-600',
  running: 'bg-blue-100 text-blue-700',
  pass: 'bg-green-100 text-green-700',
  fail: 'bg-red-100 text-red-700',
  success: 'bg-green-100 text-green-700',
  failure: 'bg-red-100 text-red-700',
  completed: 'bg-green-100 text-green-700',
};

const ICONS: Record<string, React.ReactNode> = {
  pending: <Clock className="w-3.5 h-3.5" />,
  running: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
  pass: <CheckCircle2 className="w-3.5 h-3.5" />,
  fail: <XCircle className="w-3.5 h-3.5" />,
  success: <CheckCircle2 className="w-3.5 h-3.5" />,
  failure: <XCircle className="w-3.5 h-3.5" />,
  completed: <CheckCircle2 className="w-3.5 h-3.5" />,
};

interface StatusBadgeProps {
  status: string;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
        STYLES[status] || 'bg-gray-100 text-gray-600'
      }`}
    >
      {ICONS[status]}
      {status.toUpperCase()}
    </span>
  );
};

export default StatusBadge;
