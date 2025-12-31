import React from 'react';

interface TrendChartProps {
  data: Array<{month: string, score: number}>;
  title: string;
}

const TrendChart: React.FC<TrendChartProps> = ({ data, title }) => {
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

  const maxScore = Math.max(...data.map(d => d.score));
  const minScore = Math.min(...data.map(d => d.score));
  const range = maxScore - minScore || 1;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="font-semibold text-gray-900 mb-4">{title}</h3>
      <div className="h-64 relative">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-500 pr-2">
          <span>{Math.round(maxScore)}</span>
          <span>{Math.round((maxScore + minScore) / 2)}</span>
          <span>{Math.round(minScore)}</span>
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
                const y = 100 - ((point.score - minScore) / range) * 100;
                return `${x},${y}`;
              }).join(' ')}
            />
            {data.map((point, index) => {
              const x = (index / Math.max(1, data.length - 1)) * 100;
              const y = 100 - ((point.score - minScore) / range) * 100;
              return (
                <circle
                  key={index}
                  cx={x}
                  cy={y}
                  r="1.5"
                  fill="#3B82F6"
                  className="hover:r-3 transition-all"
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
            const monthName = monthNames[monthNumber - 1] || point.month;
            return (
              <span key={index} className="text-center" style={{ width: `${100/data.length}%` }}>
                {monthName}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default TrendChart;



