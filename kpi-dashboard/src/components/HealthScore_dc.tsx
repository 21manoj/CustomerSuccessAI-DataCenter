/**
 * Data Center Health Score Component
 * Displays health score for a DC tenant
 */

import React, { useState, useEffect } from 'react';
import { Activity, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { useSession } from '../contexts/SessionContext';

interface HealthScoreProps {
  tenantId: number | null;
}

const HealthScore_dc: React.FC<HealthScoreProps> = ({ tenantId }) => {
  const { session } = useSession();
  const [healthData, setHealthData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState<string>('aggregate'); // 'aggregate' or '1'-'7'

  useEffect(() => {
    if (tenantId) {
      loadHealthScore();
    }
  }, [tenantId, selectedMonth]);

  const loadHealthScore = async () => {
    if (!tenantId) return;
    
    setLoading(true);
    try {
      const url = `/api/dc/health-score/${tenantId}?month=${selectedMonth}`;
      const response = await fetch(url, {
        credentials: 'include',
        headers: {
          'X-Customer-ID': session?.customer_id?.toString() || '',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setHealthData(data);
      }
    } catch (error) {
      console.error('Error loading health score:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (!healthData) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-500 text-center">Select a tenant to view health score</p>
      </div>
    );
  }

  const score = healthData.overall_score || 0;
  const status = healthData.health_status || 'unknown';
  const categoryScores = healthData.category_scores || {};

  const getStatusIcon = () => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-8 w-8 text-green-600" />;
      case 'at_risk':
        return <AlertTriangle className="h-8 w-8 text-yellow-600" />;
      case 'critical':
        return <XCircle className="h-8 w-8 text-red-600" />;
      default:
        return <Activity className="h-8 w-8 text-gray-600" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'at_risk':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'critical':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getScoreColor = () => {
    if (score >= 70) return 'text-green-600';
    if (score >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Health Score</h2>
          <p className="text-sm text-gray-500 mt-1">{healthData.account_name || 'Tenant'}</p>
        </div>
        {getStatusIcon()}
      </div>

      {/* Month Selection */}
      <div className="mb-6 pb-4 border-b border-gray-200">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Month
        </label>
        <select
          value={selectedMonth}
          onChange={(e) => setSelectedMonth(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="aggregate">Aggregate (Average across all months)</option>
          <option value="1">Month 1</option>
          <option value="2">Month 2</option>
          <option value="3">Month 3</option>
          <option value="4">Month 4</option>
          <option value="5">Month 5</option>
          <option value="6">Month 6</option>
          <option value="7">Month 7</option>
        </select>
        {healthData.is_aggregate && (
          <p className="text-xs text-gray-500 mt-2">
            Showing average health score across all {healthData.kpi_count || 0} KPIs from all months
          </p>
        )}
        {!healthData.is_aggregate && healthData.month && (
          <p className="text-xs text-gray-500 mt-2">
            Showing health score for Month {healthData.month} ({healthData.kpi_count || 0} KPIs)
          </p>
        )}
      </div>

      {/* Overall Score */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-600">Overall Score</span>
          <span className={`text-2xl font-bold ${getScoreColor()}`}>
            {score.toFixed(1)}
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-4">
          <div
            className={`h-4 rounded-full transition-all ${
              score >= 70 ? 'bg-green-600' : score >= 50 ? 'bg-yellow-600' : 'bg-red-600'
            }`}
            style={{ width: `${Math.min(100, score)}%` }}
          />
        </div>
      </div>

      {/* Category Breakdown */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-3">Category Breakdown</h3>
        <div className="space-y-3">
          {Object.entries(categoryScores).map(([category, data]: [string, any]) => (
            <div key={category} className="flex items-center justify-between">
              <span className="text-sm text-gray-600 flex-1">{category}</span>
              <div className="flex items-center gap-3 flex-1">
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      data.score >= 70 ? 'bg-green-600' : data.score >= 50 ? 'bg-yellow-600' : 'bg-red-600'
                    }`}
                    style={{ width: `${Math.min(100, data.score)}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-900 w-12 text-right">
                  {data.score?.toFixed(1) || '0.0'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Status Badge */}
      <div className={`mt-6 p-3 rounded-lg border ${getStatusColor()}`}>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium capitalize">{status.replace('_', ' ')}</span>
        </div>
      </div>
    </div>
  );
};

export default HealthScore_dc;

