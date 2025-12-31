import React, { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { HealthTrend } from '../../utils/healthScoreApi';

interface HealthTrendChartProps {
  data: HealthTrend[];
  showCategories?: boolean;
  timeRange?: '3m' | '6m' | '12m' | 'all';
}

const HealthTrendChart: React.FC<HealthTrendChartProps> = ({
  data,
  showCategories = false,
  timeRange = '6m'
}) => {
  const [showAllCategories, setShowAllCategories] = useState(showCategories);

  // Filter data based on time range
  const filteredData = (() => {
    const months = timeRange === '3m' ? 3 : timeRange === '6m' ? 6 : timeRange === '12m' ? 12 : data.length;
    return data.slice(-months);
  })();

  const formatTooltip = (value: number) => `${Math.round(value)}/100`;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">
          Monthly Health Trend ({timeRange === '3m' ? 'Last 3 Months' : timeRange === '6m' ? 'Last 6 Months' : timeRange === '12m' ? 'Last 12 Months' : 'All Time'})
        </h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAllCategories(!showAllCategories)}
            className="text-sm px-3 py-1 border border-gray-300 rounded-md hover:bg-gray-50"
          >
            {showAllCategories ? 'Hide Categories' : 'Show Categories'}
          </button>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={filteredData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="month"
            stroke="#6B7280"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            domain={[0, 100]}
            stroke="#6B7280"
            style={{ fontSize: '12px' }}
            label={{ value: 'Health Score', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={formatTooltip}
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #E5E7EB',
              borderRadius: '6px'
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="overallScore"
            stroke="#111827"
            strokeWidth={2}
            dot={{ fill: '#111827', r: 4 }}
            name="Overall Score"
          />
          {showAllCategories && (
            <>
              <Line
                type="monotone"
                dataKey="reliability"
                stroke="#3B82F6"
                strokeWidth={1.5}
                strokeDasharray="5 5"
                dot={{ fill: '#3B82F6', r: 3 }}
                name="Reliability"
              />
              <Line
                type="monotone"
                dataKey="efficiency"
                stroke="#8B5CF6"
                strokeWidth={1.5}
                strokeDasharray="5 5"
                dot={{ fill: '#8B5CF6', r: 3 }}
                name="Efficiency"
              />
              <Line
                type="monotone"
                dataKey="capacity"
                stroke="#EC4899"
                strokeWidth={1.5}
                strokeDasharray="5 5"
                dot={{ fill: '#EC4899', r: 3 }}
                name="Capacity"
              />
              <Line
                type="monotone"
                dataKey="security"
                stroke="#14B8A6"
                strokeWidth={1.5}
                strokeDasharray="5 5"
                dot={{ fill: '#14B8A6', r: 3 }}
                name="Security"
              />
              <Line
                type="monotone"
                dataKey="service"
                stroke="#F97316"
                strokeWidth={1.5}
                strokeDasharray="5 5"
                dot={{ fill: '#F97316', r: 3 }}
                name="Service"
              />
            </>
          )}
        </LineChart>
      </ResponsiveContainer>

      {filteredData.length > 1 && (
        <div className="mt-4 text-sm text-gray-600">
          Portfolio Avg: {Math.round(filteredData[0]?.overallScore || 0)} → {Math.round(filteredData[filteredData.length - 1]?.overallScore || 0)} 
          {' '}
          <span className="text-green-600">
            (↗ +{Math.round((filteredData[filteredData.length - 1]?.overallScore || 0) - (filteredData[0]?.overallScore || 0))} points)
          </span>
        </div>
      )}
    </div>
  );
};

export default HealthTrendChart;

