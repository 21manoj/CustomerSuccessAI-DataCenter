import React from 'react';
import { PipelineStatus } from '../../utils/dataQualityApi';
import { CheckCircle, Clock, XCircle, AlertCircle } from 'lucide-react';

interface ValidationPipelineProps {
  pipeline: PipelineStatus;
}

const ValidationPipeline: React.FC<ValidationPipelineProps> = ({ pipeline }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'complete':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'running':
        return <Clock className="h-5 w-5 text-blue-600 animate-spin" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const totalIssues = pipeline.stages.reduce(
    (sum, stage) => sum + stage.issues.errors + stage.issues.warnings,
    0
  );

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">📋 Data Processing Pipeline</h2>

      <div className="space-y-4 mb-6">
        {pipeline.stages.map((stage, index) => (
          <div key={index} className="flex items-center gap-4">
            <div className="flex-shrink-0">
              {getStatusIcon(stage.status)}
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-gray-900">{stage.name}</span>
                {stage.duration > 0 && (
                  <span className="text-sm text-gray-500">({formatDuration(stage.duration)})</span>
                )}
              </div>
              {stage.issues.errors > 0 || stage.issues.warnings > 0 ? (
                <div className="flex items-center gap-2 text-xs">
                  {stage.issues.errors > 0 && (
                    <span className="text-red-600">{stage.issues.errors} error{stage.issues.errors > 1 ? 's' : ''}</span>
                  )}
                  {stage.issues.warnings > 0 && (
                    <span className="text-yellow-600">{stage.issues.warnings} warning{stage.issues.warnings > 1 ? 's' : ''}</span>
                  )}
                </div>
              ) : (
                <span className="text-xs text-green-600">✓ Complete</span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-gray-200 pt-4 space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Issues Found:</span>
          <span className="font-medium text-gray-900">
            {pipeline.stages.reduce((sum, s) => sum + s.issues.warnings, 0)} warnings,{' '}
            {pipeline.stages.reduce((sum, s) => sum + s.issues.errors, 0)} errors
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Records Processed:</span>
          <span className="font-medium text-gray-900">{pipeline.recordsProcessed}</span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Records Failed:</span>
          <span className={`font-medium ${pipeline.recordsFailed > 0 ? 'text-red-600' : 'text-green-600'}`}>
            {pipeline.recordsFailed}
          </span>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200 flex items-center gap-2">
        <button className="px-3 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700">
          View Detailed Report
        </button>
        <button className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-200">
          Download Log
        </button>
      </div>
    </div>
  );
};

export default ValidationPipeline;

