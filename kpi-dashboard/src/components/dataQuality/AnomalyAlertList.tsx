import React from 'react';
import { Anomaly } from '../../utils/dataQualityApi';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

interface AnomalyAlertListProps {
  anomalies: Anomaly[];
  onFix?: (anomaly: Anomaly) => void;
  onIgnore?: (anomaly: Anomaly) => void;
  onReview?: (anomaly: Anomaly) => void;
}

const AnomalyAlertList: React.FC<AnomalyAlertListProps> = ({
  anomalies,
  onFix,
  onIgnore,
  onReview
}) => {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'medium':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'low':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high':
        return <XCircle className="h-5 w-5" />;
      case 'medium':
        return <AlertTriangle className="h-5 w-5" />;
      default:
        return <AlertTriangle className="h-5 w-5" />;
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">🚨 Data Anomalies Detected ({anomalies.length})</h2>
      </div>

      <div className="space-y-4">
        {anomalies.map((anomaly) => (
          <div
            key={anomaly.id}
            className={`border rounded-lg p-4 ${getSeverityColor(anomaly.severity)}`}
          >
            <div className="flex items-start gap-3 mb-2">
              {getSeverityIcon(anomaly.severity)}
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold">{anomaly.accountName}:</span>
                  <span className="font-medium">{anomaly.kpiParameter}</span>
                  <span className="text-sm">
                    jumped from {anomaly.historicalValues[anomaly.historicalValues.length - 1]} → {anomaly.currentValue}
                  </span>
                </div>
                <p className="text-sm mb-2">
                  Historical: {anomaly.historicalValues.join(', ')} → sudden spike
                </p>
                <p className="text-sm font-medium mb-3">
                  Likely: {anomaly.suggestedAction}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 ml-8">
              {anomaly.autoFixAvailable && (
                <button
                  onClick={() => onFix?.(anomaly)}
                  className="px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm font-medium hover:bg-gray-50"
                >
                  Auto-Correct
                </button>
              )}
              <button
                onClick={() => onReview?.(anomaly)}
                className="px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm font-medium hover:bg-gray-50"
              >
                Flag for Review
              </button>
              <button
                onClick={() => onIgnore?.(anomaly)}
                className="px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm font-medium hover:bg-gray-50"
              >
                Ignore
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AnomalyAlertList;

