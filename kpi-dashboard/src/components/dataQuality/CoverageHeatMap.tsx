import React from 'react';
import ProgressBar from '../shared/ProgressBar';
import StatusBadge from '../shared/StatusBadge';
import { CoverageData } from '../../utils/dataQualityApi';
import { Upload, Mail } from 'lucide-react';

interface CoverageHeatMapProps {
  data: CoverageData[];
}

const CoverageHeatMap: React.FC<CoverageHeatMapProps> = ({ data }) => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'complete':
        return <StatusBadge status="healthy" label="✓" size="sm" />;
      case 'partial':
        return <StatusBadge status="warning" label="⚠️" size="sm" />;
      case 'critical':
        return <StatusBadge status="critical" label="🔴" size="sm" />;
      default:
        return null;
    }
  };

  const getProgressColor = (percent: number) => {
    if (percent >= 90) return '#10B981';
    if (percent >= 50) return '#F59E0B';
    return '#EF4444';
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">📈 KPI Coverage by Account</h2>
      
      <div className="space-y-4">
        {data.map((account, index) => (
          <div key={index} className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="font-medium text-gray-900">{account.accountName}</span>
              <div className="flex items-center gap-2">
                {getStatusBadge(account.status)}
                <span className="text-sm text-gray-600">
                  {account.presentKpis}/{account.totalKpis}
                </span>
              </div>
            </div>
            
            <ProgressBar
              value={account.coveragePercent}
              color={getProgressColor(account.coveragePercent)}
              size="md"
              showLabel={true}
            />
          </div>
        ))}
      </div>

      <div className="mt-6 pt-4 border-t border-gray-200">
        <p className="text-sm text-gray-600 mb-3">Missing Data:</p>
        <div className="flex items-center gap-2">
          <button className="px-3 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 flex items-center gap-2">
            <Upload className="h-4 w-4" />
            Upload
          </button>
          <button className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-200 flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Request from Customer
          </button>
        </div>
      </div>
    </div>
  );
};

export default CoverageHeatMap;

