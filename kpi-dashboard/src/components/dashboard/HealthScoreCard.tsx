import React from 'react';
import { Zap, Settings, BarChart3, Shield, Target } from 'lucide-react';
import ProgressBar from '../shared/ProgressBar';
import TrendIndicator from '../shared/TrendIndicator';
import { HealthScoreData } from '../../utils/healthScoreApi';

export interface HealthScoreCardProps {
  accountId: number;
  accountName: string;
  healthScore: number;
  categoryScores: {
    reliability: number;
    efficiency: number;
    capacity: number;
    security: number;
    service: number;
  };
  trends: {
    overall: number;
    categories: Record<string, number>;
  };
  riskCount: number;
  healthyMetrics: number;
}

const categoryIcons = {
  reliability: <Zap className="h-4 w-4" />,
  efficiency: <Settings className="h-4 w-4" />,
  capacity: <BarChart3 className="h-4 w-4" />,
  security: <Shield className="h-4 w-4" />,
  service: <Target className="h-4 w-4" />
};

const categoryColors = {
  reliability: '#3B82F6',
  efficiency: '#8B5CF6',
  capacity: '#EC4899',
  security: '#14B8A6',
  service: '#F97316'
};

const HealthScoreCard: React.FC<HealthScoreCardProps> = ({
  accountName,
  healthScore,
  categoryScores,
  trends,
  riskCount,
  healthyMetrics
}) => {
  const getHealthColor = (score: number) => {
    if (score >= 80) return '#10B981';
    if (score >= 60) return '#F59E0B';
    return '#EF4444';
  };

  const getTrendDirection = (value: number): 'up' | 'down' | 'neutral' => {
    if (value > 0) return 'up';
    if (value < 0) return 'down';
    return 'neutral';
  };

  const getTrendSymbol = (value: number) => {
    if (value > 0) return '↗';
    if (value < 0) return '↘';
    return '→';
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{accountName}</h2>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-3xl font-bold" style={{ color: getHealthColor(healthScore) }}>
              Health: {Math.round(healthScore)}/100
            </span>
            {trends.overall !== 0 && (
              <span className="text-sm text-gray-600">
                {getTrendSymbol(trends.overall)} {Math.abs(trends.overall).toFixed(1)}% this month
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-3 mb-4">
        {Object.entries(categoryScores).map(([key, score]) => {
          const trend = trends.categories[key] || 0;
          const categoryName = key.charAt(0).toUpperCase() + key.slice(1);
          return (
            <div key={key} className="flex items-center gap-3">
              <div className="flex items-center gap-2 w-32">
                <span className="text-gray-600">{categoryIcons[key as keyof typeof categoryIcons]}</span>
                <span className="text-sm font-medium text-gray-700">{categoryName}</span>
              </div>
              <div className="flex-1">
                <ProgressBar
                  value={score}
                  color={categoryColors[key as keyof typeof categoryColors]}
                  showLabel={false}
                  size="sm"
                />
              </div>
              <div className="flex items-center gap-2 w-24">
                <span className="text-sm font-semibold text-gray-700">{Math.round(score)}%</span>
                <span className={`text-xs ${trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-gray-500'}`}>
                  {getTrendSymbol(trend)} {Math.abs(trend)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-gray-200">
        <div className="flex items-center gap-4">
          {riskCount > 0 && (
            <span className="text-sm text-red-600 font-medium">
              ⚠️ {riskCount} Action{riskCount > 1 ? 's' : ''} Required
            </span>
          )}
          {healthyMetrics > 0 && (
            <span className="text-sm text-green-600 font-medium">
              ✓ {healthyMetrics} Metric{healthyMetrics > 1 ? 's' : ''} Healthy
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default HealthScoreCard;

