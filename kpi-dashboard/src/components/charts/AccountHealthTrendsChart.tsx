import React from 'react';

interface AccountHealthTrendsChartProps {
  data: Array<{
    month: string;
    overall_score: number;
    product_usage_score: number;
    support_score: number;
    customer_sentiment_score: number;
    business_outcomes_score: number;
    relationship_strength_score: number;
  }>;
  title: string;
  accountName: string;
}

const AccountHealthTrendsChart: React.FC<AccountHealthTrendsChartProps> = ({ data, title, accountName }) => {
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

  const categories = [
    { key: 'overall_score', label: 'Overall', color: '#3B82F6' },
    { key: 'product_usage_score', label: 'Product Usage', color: '#10B981' },
    { key: 'support_score', label: 'Support', color: '#F59E0B' },
    { key: 'customer_sentiment_score', label: 'Customer Sentiment', color: '#8B5CF6' },
    { key: 'business_outcomes_score', label: 'Business Outcomes', color: '#EF4444' },
    { key: 'relationship_strength_score', label: 'Relationship Strength', color: '#06B6D4' }
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="font-semibold text-gray-900 mb-4">{title}</h3>
      <div className="h-80 relative">
        {/* Y-axis labels */}
        <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-500 pr-2">
          <span>100</span>
          <span>75</span>
          <span>50</span>
          <span>25</span>
          <span>0</span>
        </div>
        
        {/* Chart area */}
        <div className="ml-8 h-full relative">
          {/* Grid lines */}
          <div className="absolute inset-0">
            {[0, 0.25, 0.5, 0.75, 1].map((ratio) => (
              <div 
                key={ratio}
                className="absolute w-full border-t border-gray-100"
                style={{ top: `${ratio * 100}%` }}
              />
            ))}
          </div>
          
          {/* Trend lines for each category */}
          <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
            {categories.map((category) => (
              <polyline
                key={category.key}
                fill="none"
                stroke={category.color}
                strokeWidth="1"
                points={data.map((point, index) => {
                  const x = (index / Math.max(1, data.length - 1)) * 100;
                  const y = 100 - ((point[category.key as keyof typeof point] as number) / 100) * 100;
                  return `${x},${y}`;
                }).join(' ')}
              />
            ))}
            
            {/* Data points for overall score */}
            {data.map((point, index) => {
              const x = (index / Math.max(1, data.length - 1)) * 100;
              const y = 100 - (point.overall_score / 100) * 100;
              return (
                <circle
                  key={index}
                  cx={x}
                  cy={y}
                  r="1"
                  fill="#3B82F6"
                  className="hover:r-2 transition-all cursor-pointer"
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
      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        {categories.map((category) => (
          <div key={category.key} className="flex items-center space-x-2">
            <div 
              className="w-3 h-3 rounded-full" 
              style={{ backgroundColor: category.color }}
            ></div>
            <span>{category.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AccountHealthTrendsChart;



