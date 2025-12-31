import React from 'react';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Legend
} from 'recharts';

interface CategoryScores {
  reliability: number;
  efficiency: number;
  capacity: number;
  security: number;
  service: number;
}

interface CategoryBreakdownProps {
  scores: CategoryScores;
  benchmarks?: {
    industry: CategoryScores;
    topQuartile: CategoryScores;
  };
}

const CategoryBreakdownRadar: React.FC<CategoryBreakdownProps> = ({ scores, benchmarks }) => {
  const data = [
    { category: 'Reliability', score: scores.reliability, industry: benchmarks?.industry.reliability, topQuartile: benchmarks?.topQuartile.reliability },
    { category: 'Efficiency', score: scores.efficiency, industry: benchmarks?.industry.efficiency, topQuartile: benchmarks?.topQuartile.efficiency },
    { category: 'Capacity', score: scores.capacity, industry: benchmarks?.industry.capacity, topQuartile: benchmarks?.topQuartile.capacity },
    { category: 'Security', score: scores.security, industry: benchmarks?.industry.security, topQuartile: benchmarks?.topQuartile.security },
    { category: 'Service', score: scores.service, industry: benchmarks?.industry.service, topQuartile: benchmarks?.topQuartile.service }
  ];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Category Breakdown</h2>
      
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data}>
          <PolarGrid stroke="#E5E7EB" />
          <PolarAngleAxis
            dataKey="category"
            tick={{ fill: '#6B7280', fontSize: 12 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: '#9CA3AF', fontSize: 10 }}
          />
          <Radar
            name="Current Score"
            dataKey="score"
            stroke="#111827"
            fill="#111827"
            fillOpacity={0.6}
          />
          {benchmarks?.industry && (
            <Radar
              name="Industry Avg"
              dataKey="industry"
              stroke="#3B82F6"
              fill="#3B82F6"
              fillOpacity={0.3}
            />
          )}
          {benchmarks?.topQuartile && (
            <Radar
              name="Top Quartile"
              dataKey="topQuartile"
              stroke="#10B981"
              fill="#10B981"
              fillOpacity={0.2}
            />
          )}
          <Legend />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default CategoryBreakdownRadar;

