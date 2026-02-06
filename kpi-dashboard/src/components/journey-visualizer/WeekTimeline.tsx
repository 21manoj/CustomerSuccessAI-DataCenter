/**
 * Week Timeline Component
 * ========================
 * 
 * Interactive timeline for navigating through weeks:
 * - Visual health score trend
 * - Week selector
 * - Data quality indicators
 * - Crisis/recovery markers
 */

import React from 'react';

interface WeekData {
  week_number: number;
  date: string;
  health_score: number;
  phase?: string;
  data_quality?: number;
  is_crisis_start?: boolean;
  is_recovery_start?: boolean;
}

interface WeekTimelineProps {
  weeks: WeekData[];
  selectedWeek: number;
  onWeekSelect: (week: number) => void;
}

const WeekTimeline: React.FC<WeekTimelineProps> = ({
  weeks,
  selectedWeek,
  onWeekSelect
}) => {
  // Calculate range to display (show 13 weeks at a time)
  const windowSize = 13;
  const centerWeek = selectedWeek;
  const startIdx = Math.max(0, centerWeek - Math.floor(windowSize / 2));
  const endIdx = Math.min(weeks.length, startIdx + windowSize);
  const visibleWeeks = weeks.slice(startIdx, endIdx);
  
  // Navigation
  const canGoPrevious = selectedWeek > 1;
  const canGoNext = selectedWeek < weeks.length;
  
  const handlePrevious = () => {
    if (canGoPrevious) onWeekSelect(selectedWeek - 1);
  };
  
  const handleNext = () => {
    if (canGoNext) onWeekSelect(selectedWeek + 1);
  };
  
  const handleJumpToWeek = (week: number) => {
    onWeekSelect(week);
  };
  
  return (
    <div className="space-y-4">
      {/* Navigation Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={handlePrevious}
            disabled={!canGoPrevious}
            className={`px-3 py-1 rounded ${
              canGoPrevious 
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            ← Previous
          </button>
          
          <button
            onClick={handleNext}
            disabled={!canGoNext}
            className={`px-3 py-1 rounded ${
              canGoNext 
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            Next →
          </button>
        </div>
        
        <div className="text-sm text-gray-600">
          Week {selectedWeek} of {weeks.length}
        </div>
        
        {/* Quick Jump */}
        <select
          value={selectedWeek}
          onChange={(e) => handleJumpToWeek(parseInt(e.target.value))}
          className="px-3 py-1 border border-gray-300 rounded text-sm"
        >
          {weeks.map(week => (
            <option key={week.week_number} value={week.week_number}>
              Week {week.week_number}
            </option>
          ))}
        </select>
      </div>
      
      {/* Timeline */}
      <div className="relative">
        {/* Health Trend Line */}
        <svg className="w-full h-20 mb-2" viewBox={`0 0 ${visibleWeeks.length * 100} 100`}>
          <polyline
            points={visibleWeeks.map((week, idx) => 
              `${idx * 100 + 50},${100 - week.health_score}`
            ).join(' ')}
            fill="none"
            stroke="#3b82f6"
            strokeWidth="2"
          />
          
          {/* Data points */}
          {visibleWeeks.map((week, idx) => (
            <circle
              key={week.week_number}
              cx={idx * 100 + 50}
              cy={100 - week.health_score}
              r={week.week_number === selectedWeek ? "5" : "3"}
              fill={getPhaseColor(week.phase)}
              stroke="white"
              strokeWidth="1"
              className="cursor-pointer"
              onClick={() => handleJumpToWeek(week.week_number)}
            />
          ))}
        </svg>
        
        {/* Week Markers */}
        <div className="flex justify-between">
          {visibleWeeks.map(week => (
            <div
              key={week.week_number}
              className={`flex flex-col items-center cursor-pointer group flex-1 ${
                week.week_number === selectedWeek ? 'opacity-100' : 'opacity-50'
              }`}
              onClick={() => handleJumpToWeek(week.week_number)}
            >
              {/* Week Number */}
              <div className={`
                text-xs font-medium px-2 py-1 rounded
                ${week.week_number === selectedWeek 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-100 text-gray-600 group-hover:bg-gray-200'
                }
              `}>
                W{week.week_number}
              </div>
              
              {/* Health Score */}
              <div className="text-xs text-gray-500 mt-1">
                {week.health_score.toFixed(0)}
              </div>
              
              {/* Data Quality Indicator */}
              {week.data_quality !== undefined && (
                <div className={`w-2 h-2 rounded-full mt-1 ${
                  week.data_quality >= 0.4 ? 'bg-green-500' :
                  week.data_quality >= 0.3 ? 'bg-blue-500' :
                  'bg-yellow-500'
                }`} title={`${(week.data_quality * 100).toFixed(0)}% coverage`} />
              )}
              
              {/* Pattern Markers */}
              {week.is_crisis_start && (
                <div className="text-red-600 text-lg mt-1" title="Crisis Start">
                  🚨
                </div>
              )}
              {week.is_recovery_start && (
                <div className="text-green-600 text-lg mt-1" title="Recovery Start">
                  ✨
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      
      {/* Legend */}
      <div className="flex items-center justify-center gap-6 text-xs text-gray-600">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <span>Healthy</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
          <span>At-Risk</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <span>Crisis</span>
        </div>
      </div>
    </div>
  );
};

function getPhaseColor(phase?: string): string {
  const colorMap: Record<string, string> = {
    'healthy': '#10b981',
    'at_risk': '#eab308',
    'crisis': '#ef4444',
    'recovery': '#3b82f6',
    'moderate': '#8b5cf6',
  };
  
  return phase ? colorMap[phase] || '#6b7280' : '#6b7280';
}

export default WeekTimeline;
