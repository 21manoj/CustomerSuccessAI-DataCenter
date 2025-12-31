import React from 'react';

export interface StatusBadgeProps {
  status: 'healthy' | 'warning' | 'critical' | 'unknown';
  label?: string;
  size?: 'sm' | 'md' | 'lg';
}

const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  size = 'md'
}) => {
  const statusConfig = {
    healthy: {
      color: 'bg-green-100 text-green-800 border-green-200',
      icon: '🟢',
      defaultLabel: 'Healthy'
    },
    warning: {
      color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      icon: '🟡',
      defaultLabel: 'At Risk'
    },
    critical: {
      color: 'bg-red-100 text-red-800 border-red-200',
      icon: '🔴',
      defaultLabel: 'Critical'
    },
    unknown: {
      color: 'bg-gray-100 text-gray-800 border-gray-200',
      icon: '⚪',
      defaultLabel: 'Unknown'
    }
  };

  const config = statusConfig[status];
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5'
  };

  return (
    <span className={`inline-flex items-center gap-1 rounded-full border font-medium ${config.color} ${sizeClasses[size]}`}>
      <span>{config.icon}</span>
      <span>{label || config.defaultLabel}</span>
    </span>
  );
};

export default StatusBadge;

