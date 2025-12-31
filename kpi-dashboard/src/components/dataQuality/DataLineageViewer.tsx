import React from 'react';
import { DataLineage } from '../../utils/dataQualityApi';
import { FileText, User, Calendar, ArrowRight } from 'lucide-react';

interface DataLineageViewerProps {
  lineage: DataLineage;
}

const DataLineageViewer: React.FC<DataLineageViewerProps> = ({ lineage }) => {
  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }).format(date);
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        🔍 Data Lineage: {lineage.sourceColumn}
      </h2>

      <div className="space-y-4 mb-6">
        <div className="flex items-start gap-3">
          <FileText className="h-5 w-5 text-gray-400 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-gray-700">Source:</p>
            <p className="text-sm text-gray-900">{lineage.sourceFile}</p>
            <p className="text-sm text-gray-600">Column: "{lineage.sourceColumn}"</p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <User className="h-5 w-5 text-gray-400 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-gray-700">Uploaded:</p>
            <p className="text-sm text-gray-900">{lineage.uploadedBy}</p>
            <p className="text-sm text-gray-600">{formatDate(lineage.uploadedAt)}</p>
          </div>
        </div>
      </div>

      <div className="border-t border-gray-200 pt-4 mb-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Transformations Applied:</h3>
        <div className="space-y-2">
          {lineage.transformations.map((transformation, index) => (
            <div key={index} className="flex items-start gap-3 text-sm">
              <span className="text-gray-500 w-6">{transformation.step}.</span>
              <div className="flex-1">
                <p className="text-gray-700">{transformation.description}</p>
                {transformation.before !== transformation.after && (
                  <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                    <span>{JSON.stringify(transformation.before)}</span>
                    <ArrowRight className="h-3 w-3" />
                    <span>{JSON.stringify(transformation.after)}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-gray-200 pt-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Used in Calculations:</h3>
        <div className="space-y-2">
          {lineage.usedIn.map((usage, index) => (
            <div key={index} className="flex items-center justify-between text-sm">
              <span className="text-gray-700">- {usage.calculation}:</span>
              <span className="text-gray-900 font-medium">{usage.impact}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DataLineageViewer;

