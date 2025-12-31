import React from 'react';
import ProgressBar from '../shared/ProgressBar';
import { QualityMetrics } from '../../utils/dataQualityApi';
import { CheckCircle, AlertTriangle, Clock } from 'lucide-react';

interface QualityScoreDashboardProps {
  metrics: QualityMetrics;
}

const QualityScoreDashboard: React.FC<QualityScoreDashboardProps> = ({ metrics }) => {
  const getQualityStatus = (score: number) => {
    if (score >= 90) return { label: 'Excellent', color: '#10B981', icon: '🟢' };
    if (score >= 75) return { label: 'Good', color: '#84CC16', icon: '🟡' };
    if (score >= 60) return { label: 'Fair', color: '#F59E0B', icon: '🟠' };
    return { label: 'Poor', color: '#EF4444', icon: '🔴' };
  };

  const overallStatus = getQualityStatus(metrics.overall);

  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }).format(date);
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-gray-900">📊 Data Quality Score</h2>
        <div className="flex items-center gap-2">
          <span className="text-2xl">{overallStatus.icon}</span>
          <span className="text-sm font-semibold" style={{ color: overallStatus.color }}>
            {overallStatus.label}
          </span>
        </div>
      </div>

      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-3xl font-bold text-gray-900">{metrics.overall}/100</span>
        </div>
        <ProgressBar
          value={metrics.overall}
          color={overallStatus.color}
          size="lg"
          showLabel={false}
        />
      </div>

      <div className="space-y-4">
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Completeness</span>
            <div className="flex items-center gap-2">
              {metrics.completeness.score >= 90 ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
              )}
              <span className="text-sm font-semibold text-gray-700">{metrics.completeness.score}%</span>
            </div>
          </div>
          <ProgressBar
            value={metrics.completeness.score}
            color="#10B981"
            size="sm"
            showLabel={false}
          />
          <p className="text-xs text-gray-500 mt-1">
            ✓ {metrics.completeness.presentKpis}/{metrics.completeness.totalKpis} KPIs
          </p>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Accuracy</span>
            <div className="flex items-center gap-2">
              {metrics.accuracy.outlierCount > 0 ? (
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
              ) : (
                <CheckCircle className="h-4 w-4 text-green-600" />
              )}
              <span className="text-sm font-semibold text-gray-700">{metrics.accuracy.score}%</span>
            </div>
          </div>
          <ProgressBar
            value={metrics.accuracy.score}
            color={metrics.accuracy.score >= 90 ? '#10B981' : '#F59E0B'}
            size="sm"
            showLabel={false}
          />
          <p className="text-xs text-gray-500 mt-1">
            {metrics.accuracy.outlierCount > 0 ? (
              <span className="text-yellow-600">⚠️ {metrics.accuracy.outlierCount} outliers detected</span>
            ) : (
              <span className="text-green-600">✓ No outliers</span>
            )}
          </p>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Freshness</span>
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-gray-600" />
              <span className="text-sm font-semibold text-gray-700">{metrics.freshness.score}%</span>
            </div>
          </div>
          <ProgressBar
            value={metrics.freshness.score}
            color={metrics.freshness.score >= 90 ? '#10B981' : '#F59E0B'}
            size="sm"
            showLabel={false}
          />
          <p className="text-xs text-gray-500 mt-1">
            {metrics.freshness.staleAccounts > 0 ? (
              <span className="text-yellow-600">⏰ {metrics.freshness.staleAccounts} accounts stale</span>
            ) : (
              <span className="text-green-600">✓ All accounts up to date</span>
            )}
          </p>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Consistency</span>
            <div className="flex items-center gap-2">
              {metrics.consistency.score >= 95 ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
              )}
              <span className="text-sm font-semibold text-gray-700">{metrics.consistency.score}%</span>
            </div>
          </div>
          <ProgressBar
            value={metrics.consistency.score}
            color="#10B981"
            size="sm"
            showLabel={false}
          />
          <p className="text-xs text-gray-500 mt-1">
            {metrics.consistency.schemaViolations === 0 ? (
              <span className="text-green-600">✓ Schema validated</span>
            ) : (
              <span className="text-yellow-600">⚠️ {metrics.consistency.schemaViolations} violations</span>
            )}
          </p>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-gray-200 flex items-center justify-between text-xs text-gray-500">
        <span>Last Updated: {formatDate(metrics.lastUpdated)}</span>
        <span>Next Refresh: {formatDate(metrics.nextRefresh)}</span>
      </div>
    </div>
  );
};

export default QualityScoreDashboard;

