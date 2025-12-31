import React from 'react';

interface KpiTrendChartProps {
  data: Array<{month: string, value: number, health_status: string, health_score: number}>;
  title: string;
  kpiName: string;
}

const KpiTrendChart: React.FC<KpiTrendChartProps> = ({ data, title, kpiName }) => {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="h-64 flex items-center justify-center text-gray-500">
          No trend data available
        </div>
      </div>
    );
  }

  const maxValue = Math.max(...data.map(d => d.value));
  const minValue = Math.min(...data.map(d => d.value));
  const valueRange = maxValue - minValue || 1;

  const getHealthColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'high': return '#10B981'; // green
      case 'medium': return '#F59E0B'; // yellow
      case 'low': return '#EF4444'; // red
      default: return '#6B7280'; // gray
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="font-semibold text-gray-900 mb-4">{title}</h3>
      <div className="h-64 relative">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-500 pr-2">
          <span>{maxValue.toFixed(1)}</span>
          <span>{((maxValue + minValue) / 2).toFixed(1)}</span>
          <span>{minValue.toFixed(1)}</span>
        </div>
        
        {/* Chart area */}
        <div className="ml-8 h-full relative">
          {/* Grid lines */}
          <div className="absolute inset-0">
            {[0, 0.5, 1].map((ratio) => (
              <div 
                key={ratio}
                className="absolute w-full border-t border-gray-100"
                style={{ top: `${ratio * 100}%` }}
              />
            ))}
          </div>
          
          {/* Trend line */}
          <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            <polyline
              fill="none"
              stroke="#3B82F6"
              strokeWidth="1"
              points={data.map((point, index) => {
                const x = (index / Math.max(1, data.length - 1)) * 100;
                const y = 100 - ((point.value - minValue) / valueRange) * 100;
                return `${x},${y}`;
              }).join(' ')}
            />
            {data.map((point, index) => {
              const x = (index / Math.max(1, data.length - 1)) * 100;
              const y = 100 - ((point.value - minValue) / valueRange) * 100;
              return (
                <circle
                  key={index}
                  cx={x}
                  cy={y}
                  r="1.5"
                  fill={getHealthColor(point.health_status)}
                  className="hover:r-3 transition-all cursor-pointer"
                />
              );
            })}
          </svg>
        </div>
        
        {/* X-axis labels */}
        <div className="absolute bottom-0 left-8 right-0 flex justify-between text-xs text-gray-500">
          {data.map((point, index) => {
            const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const monthNumber = parseInt(point.month.split('-')[1]);
            const monthName = monthNames[monthNumber - 1] || `M${monthNumber}`;
            return (
              <span key={index} className="text-center" style={{ width: `${100/data.length}%` }}>
                {monthName}
              </span>
            );
          })}
        </div>
      </div>
      
      {/* Legend */}
      <div className="mt-4 flex items-center justify-center space-x-4 text-xs">
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span>High</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
          <span>Medium</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
          <span>Low</span>
        </div>
      </div>
    </div>
  );
};

export default KpiTrendChart;



