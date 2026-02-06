/**
 * Coverage Trends Component
 * ==========================
 * 
 * Shows KPI coverage trends over time:
 * - Coverage percentage timeline
 * - KPIs that appeared/disappeared
 * - Data quality changes
 */

import React from 'react';

interface WeekData {
  week_number: number;
  date: string;
  coverage_pct?: number;
  data_quality?: number;
  available_kpis?: string[];
}

interface CoverageTrendsProps {
  weeks: WeekData[];
  currentWeek: number;
}

const CoverageTrends: React.FC<CoverageTrendsProps> = ({
  weeks,
  currentWeek
}) => {
  // Get last 12 weeks for trend
  const endIdx = currentWeek;
  const startIdx = Math.max(0, currentWeek - 12);
  const recentWeeks = weeks.slice(startIdx, endIdx);
    // Calculate trend (with safe defaults)
  const firstCoverage = recentWeeks[0]?.coverage_pct ?? 0;
  const lastCoverage = recentWeeks[recentWeeks.length - 1]?.coverage_pct ?? 0;
  const trend = lastCoverage - firstCoverage;
  
  // Helper to safely get numeric value (prevent NaN)
  const safeNumber = (value: number | undefined | null): number => {
    const num = value ?? 0;
    return isNaN(num) ? 0 : num;
  };
  
  // Helper to calculate x position safely (handle division by zero)
  const getXPosition = (idx: number, total: number): number => {
    if (total <= 1) return 50; // Center if only one point
    return (idx / (total - 1)) * 100;
  };
  
  // Helper to calculate y position safely
  const getYPosition = (coverage: number | undefined | null): number => {
    const coverageValue = safeNumber(coverage);
    return 100 - Math.max(0, Math.min(100, coverageValue)); // Clamp between 0-100
  };
  
  // Find KPIs that appeared/disappeared
  const currentWeekData = weeks[currentWeek - 1];
  const previousWeekData = currentWeek > 1 ? weeks[currentWeek - 2] : null;
  
  const newKPIs = currentWeekData?.available_kpis?.filter(
    kpi => !previousWeekData?.available_kpis?.includes(kpi)
  ) || [];
  
  const lostKPIs = previousWeekData?.available_kpis?.filter(
    kpi => !currentWeekData?.available_kpis?.includes(kpi)
  ) || [];
  
  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="border-b border-gray-200 px-6 py-4">
        <h3 className="text-lg font-semibold text-gray-800">
          📈 Coverage Trends
        </h3>
      </div>
      
      <div className="p-6 space-y-4">
        {/* Coverage Trend Chart */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-600">Last 12 Weeks</div>
            <div className={`text-sm font-medium ${
              trend > 0 ? 'text-green-600' : 
              trend < 0 ? 'text-red-600' : 
              'text-gray-600'
            }`}>
              {trend > 0 ? '▲' : trend < 0 ? '▼' : '−'} 
              {Math.abs(trend).toFixed(1)}%
            </div>
          </div>
          
          {/* Mini Chart */}
          <svg className="w-full h-24 bg-gray-50 rounded" viewBox="0 0 100 100">
            {/* Grid lines */}
            {[25, 50, 75].map(y => (
              <line
                key={y}
                x1="0"
                y1={y}
                x2="100"
                y2={y}
                stroke="#e5e7eb"
                strokeWidth="0.5"
              />
            ))}
            
            {/* Trend line */}
            {recentWeeks.length > 0 && (
              <polyline
                points={recentWeeks.map((week, idx) => {
                  const x = getXPosition(idx, recentWeeks.length);
                  const y = getYPosition(week.coverage_pct);
                  return `${x},${y}`;
                }).join(' ')}
                fill="none"
                stroke="#3b82f6"
                strokeWidth="2"
              />
            )}
            
            {/* Data points */}
            {recentWeeks.map((week, idx) => {
              const cx = getXPosition(idx, recentWeeks.length);
              const cy = getYPosition(week.coverage_pct);
              return (
                <circle
                  key={idx}
                  cx={cx}
                  cy={cy}
                  r="2"
                  fill="#3b82f6"
                />
              );
            })}
          </svg>
          
          {/* Y-axis labels */}
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>Week {startIdx + 1}</span>
            <span>Week {currentWeek}</span>
          </div>
        </div>
        
        {/* Current Coverage */}
        <div className="border-t border-gray-200 pt-4">
          <div className="text-sm text-gray-600 mb-2">Current Coverage</div>
          <div className="flex items-center gap-3">
            <div className="flex-1 h-3 bg-gray-100 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-500"
              style={{ width: `${Math.max(0, Math.min(100, safeNumber(currentWeekData?.coverage_pct)))}%` }}
            />
            </div>
            <div className="text-lg font-bold text-gray-800">
              {safeNumber(currentWeekData?.coverage_pct).toFixed(0)}%
            </div>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {currentWeekData?.available_kpis?.length || 0}/35 KPIs tracked
          </div>
        </div>
        
        {/* New KPIs */}
        {newKPIs.length > 0 && (
          <div className="border-t border-gray-200 pt-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-green-600 text-lg">+</span>
              <div className="text-sm font-medium text-gray-700">
                New KPIs This Week
              </div>
            </div>
            <div className="space-y-1">
              {newKPIs.slice(0, 3).map(kpi => (
                <div key={kpi} className="text-sm text-green-600 flex items-center gap-2">
                  <span>✓</span>
                  <span>{formatKPIName(kpi)}</span>
                </div>
              ))}
              {newKPIs.length > 3 && (
                <div className="text-xs text-gray-500 ml-5">
                  +{newKPIs.length - 3} more
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Lost KPIs */}
        {lostKPIs.length > 0 && (
          <div className="border-t border-gray-200 pt-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-red-600 text-lg">−</span>
              <div className="text-sm font-medium text-gray-700">
                Lost KPIs This Week
              </div>
            </div>
            <div className="space-y-1">
              {lostKPIs.slice(0, 3).map(kpi => (
                <div key={kpi} className="text-sm text-red-600 flex items-center gap-2">
                  <span>✗</span>
                  <span>{formatKPIName(kpi)}</span>
                </div>
              ))}
              {lostKPIs.length > 3 && (
                <div className="text-xs text-gray-500 ml-5">
                  +{lostKPIs.length - 3} more
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Coverage Goal */}
        <div className="border-t border-gray-200 pt-4">
          <div className="text-sm text-gray-600 mb-2">Coverage Goal</div>
          <div className="bg-blue-50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-blue-900">
                Target: 40% (Excellent)
              </span>
              <span className="text-sm text-blue-700">
                {(safeNumber(currentWeekData?.coverage_pct) / 40 * 100).toFixed(0)}% to goal
              </span>
            </div>
            <div className="h-2 bg-blue-200 rounded-full overflow-hidden">
              <div 
                className="h-full bg-blue-600"
                style={{ width: `${Math.min(safeNumber(currentWeekData?.coverage_pct) / 40 * 100, 100)}%` }}
              />
            </div>
            <div className="text-xs text-blue-700 mt-2">
              {safeNumber(currentWeekData?.coverage_pct) >= 40 
                ? '✓ Goal achieved!'
                : `Track ${Math.ceil((40 - safeNumber(currentWeekData?.coverage_pct)) / 100 * 35)} more KPIs to reach goal`
              }
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

function formatKPIName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export default CoverageTrends;
