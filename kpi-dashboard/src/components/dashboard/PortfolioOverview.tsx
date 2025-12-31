import React from 'react';
import MetricCard from '../shared/MetricCard';
import StatusBadge from '../shared/StatusBadge';
import { PortfolioOverview as PortfolioOverviewType } from '../../utils/healthScoreApi';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface PortfolioOverviewProps {
  data: PortfolioOverviewType;
}

const PortfolioOverview: React.FC<PortfolioOverviewProps> = ({ data }) => {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Portfolio Overview</h2>
      
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <StatusBadge status="healthy" label={`Healthy (${data.healthyCount})`} size="sm" />
            <span className="text-sm text-green-600 flex items-center gap-1">
              <TrendingUp className="h-4 w-4" />
              {data.trends.healthy > 0 ? '+' : ''}{data.trends.healthy}%
            </span>
          </div>
          <div className="text-2xl font-bold text-green-700">Avg Score: {data.averageScores.healthy}</div>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <StatusBadge status="warning" label={`At-Risk (${data.atRiskCount})`} size="sm" />
            <span className="text-sm text-yellow-600 flex items-center gap-1">
              <TrendingDown className="h-4 w-4" />
              {data.trends.atRisk}%
            </span>
          </div>
          <div className="text-2xl font-bold text-yellow-700">Avg Score: {data.averageScores.atRisk}</div>
        </div>

        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <StatusBadge status="critical" label={`Critical (${data.criticalCount})`} size="sm" />
            <span className="text-sm text-red-600">Need Action</span>
          </div>
          <div className="text-2xl font-bold text-red-700">Avg Score: {data.averageScores.critical}</div>
        </div>
      </div>

      <div className="border-t border-gray-200 pt-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Top Risks Across Portfolio:</h3>
        <div className="space-y-2">
          {data.topRisks.map((risk, index) => (
            <div key={index} className="flex items-start gap-2 text-sm">
              <span className="text-yellow-600">⚠️</span>
              <span className="text-gray-700">
                <span className="font-medium">{risk.affectedCount} customers:</span> {risk.description}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default PortfolioOverview;

