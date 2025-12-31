import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export interface TrendIndicatorProps {
  value: number;
  previousValue: number;
  format?: 'percent' | 'number' | 'currency';
  showIcon?: boolean;
}

const TrendIndicator: React.FC<TrendIndicatorProps> = ({
  value,
  previousValue,
  format = 'percent',
  showIcon = true
}) => {
  const change = value - previousValue;
  const changePercent = previousValue !== 0 ? (change / previousValue) * 100 : 0;
  
  const direction = change > 0 ? 'up' : change < 0 ? 'down' : 'neutral';
  const isPositive = change > 0;

  const formatValue = (val: number): string => {
    switch (format) {
      case 'percent':
        return `${Math.abs(val).toFixed(1)}%`;
      case 'currency':
        return `$${Math.abs(val).toFixed(2)}`;
      default:
        return Math.abs(val).toFixed(1);
    }
  };

  const icons = {
    up: <TrendingUp className="h-4 w-4" />,
    down: <TrendingDown className="h-4 w-4" />,
    neutral: <Minus className="h-4 w-4" />
  };

  const colorClass = isPositive ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-gray-600';

  return (
    <div className={`flex items-center gap-1 ${colorClass}`}>
      {showIcon && icons[direction]}
      <span className="text-sm font-medium">
        {direction === 'up' ? '↗' : direction === 'down' ? '↘' : '→'} {formatValue(changePercent)}
      </span>
    </div>
  );
};

export default TrendIndicator;

