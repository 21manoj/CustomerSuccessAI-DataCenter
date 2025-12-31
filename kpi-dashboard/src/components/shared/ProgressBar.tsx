import React from 'react';

export interface ProgressBarProps {
  value: number; // 0-100
  max?: number;
  color?: string;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
  label?: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  color,
  showLabel = true,
  size = 'md',
  animated = true,
  label
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
  
  const sizeClasses = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4'
  };

  const defaultColor = percentage >= 80 ? '#10B981' : percentage >= 60 ? '#F59E0B' : '#EF4444';

  return (
    <div className="w-full">
      {label && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm text-gray-600">{label}</span>
          {showLabel && <span className="text-sm font-medium text-gray-700">{Math.round(percentage)}%</span>}
        </div>
      )}
      <div className={`w-full bg-gray-200 rounded-full overflow-hidden ${sizeClasses[size]}`}>
        <div
          className={`h-full rounded-full transition-all duration-500 ${animated ? 'ease-out' : ''}`}
          style={{
            width: `${percentage}%`,
            backgroundColor: color || defaultColor
          }}
        />
      </div>
    </div>
  );
};

export default ProgressBar;

