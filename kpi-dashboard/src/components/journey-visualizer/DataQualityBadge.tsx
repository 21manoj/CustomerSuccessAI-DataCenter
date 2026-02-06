/**
 * Data Quality Badge Component
 * ==============================
 * 
 * Shows data quality indicators:
 * - Coverage percentage
 * - Quality level (excellent/good/low)
 * - Number of tracked KPIs
 * - List of missing KPIs (expandable)
 */

import React from 'react';

interface DataQualityBadgeProps {
  coverage: number;
  dataQuality: number;
  missingKPIs: string[];
  showMissing?: boolean;
  onToggleMissing?: () => void;
}

const DataQualityBadge: React.FC<DataQualityBadgeProps> = ({
  coverage,
  dataQuality,
  missingKPIs,
  showMissing = false,
  onToggleMissing
}) => {
  // Determine quality level
  const qualityLevel = 
    coverage >= 40 ? 'excellent' :
    coverage >= 30 ? 'good' :
    'low';
  
  const totalKPIs = 35; // Total available KPIs
  const trackedKPIs = totalKPIs - missingKPIs.length;
  
  // Color schemes
  const colors = {
    excellent: {
      bg: 'bg-green-100',
      text: 'text-green-800',
      border: 'border-green-300',
      icon: '✅'
    },
    good: {
      bg: 'bg-blue-100',
      text: 'text-blue-800',
      border: 'border-blue-300',
      icon: '✓'
    },
    low: {
      bg: 'bg-yellow-100',
      text: 'text-yellow-800',
      border: 'border-yellow-300',
      icon: '⚠️'
    }
  };
  
  const theme = colors[qualityLevel];
  
  return (
    <div className={`border-l-4 ${theme.border} ${theme.bg} p-4 rounded-r-lg`}>
      <div className="flex items-center justify-between">
        {/* Quality Level */}
        <div className="flex items-center gap-3">
          <span className="text-2xl">{theme.icon}</span>
          <div>
            <div className={`font-semibold ${theme.text}`}>
              Data Quality: {qualityLevel.toUpperCase()}
            </div>
            <div className={`text-sm ${theme.text} opacity-75`}>
              {trackedKPIs}/35 KPIs tracked ({coverage.toFixed(1)}% coverage)
            </div>
          </div>
        </div>
        
        {/* Coverage Bar */}
        <div className="flex items-center gap-3">
          <div className="w-32 h-3 bg-white rounded-full overflow-hidden">
            <div 
              className={`h-full ${theme.bg} border-r-2 ${theme.border}`}
              style={{ width: `${coverage}%` }}
            />
          </div>
          <div className={`text-sm font-bold ${theme.text}`}>
            {coverage.toFixed(0)}%
          </div>
        </div>
      </div>
      
      {/* Missing KPIs Section */}
      {missingKPIs.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-300">
          <button
            onClick={onToggleMissing}
            className={`text-sm ${theme.text} hover:underline flex items-center gap-2`}
          >
            <span>{showMissing ? '▼' : '▶'}</span>
            <span>{missingKPIs.length} KPIs not tracked</span>
          </button>
          
          {showMissing && (
            <div className="mt-2 pl-6">
              <ul className="text-sm text-gray-700 space-y-1">
                {missingKPIs.slice(0, 10).map((kpi, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-gray-400">•</span>
                    <span>{formatKPIName(kpi)}</span>
                  </li>
                ))}
                {missingKPIs.length > 10 && (
                  <li className="text-gray-500 italic">
                    ... and {missingKPIs.length - 10} more
                  </li>
                )}
              </ul>
              
              {/* Improvement Suggestion */}
              {qualityLevel === 'low' && (
                <div className="mt-3 p-2 bg-white rounded text-xs text-gray-600">
                  <div className="font-medium mb-1">💡 Improve Data Quality:</div>
                  <div>Track {Math.ceil((30 - coverage) / 100 * 35)} more KPIs to reach "Good" quality (30% coverage)</div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

function formatKPIName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export default DataQualityBadge;
