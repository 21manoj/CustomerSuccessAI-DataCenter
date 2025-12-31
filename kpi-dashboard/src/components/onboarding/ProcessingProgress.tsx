import React, { useEffect, useState } from 'react';
import { CheckCircle, Clock, AlertCircle } from 'lucide-react';
import { ProcessingStatus, getProcessingStatus } from '../../utils/onboardingApi';
import ProgressBar from '../shared/ProgressBar';

interface ProcessingProgressProps {
  sessionId: string;
  onComplete: (status: ProcessingStatus) => void;
}

const ProcessingProgress: React.FC<ProcessingProgressProps> = ({
  sessionId,
  onComplete
}) => {
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [polling, setPolling] = useState(true);

  useEffect(() => {
    const pollStatus = async () => {
      try {
        const currentStatus = await getProcessingStatus(sessionId);
        setStatus(currentStatus);
        
        // Check if all stages are complete
        const allComplete = currentStatus.stages.every(s => s.status === 'complete');
        if (allComplete) {
          setPolling(false);
          onComplete(currentStatus);
        }
      } catch (error) {
        console.error('Error polling status:', error);
      }
    };

    // Initial poll
    pollStatus();

    // Poll every 2 seconds
    const interval = setInterval(pollStatus, 2000);

    return () => clearInterval(interval);
  }, [sessionId, onComplete]);

  if (!status) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Starting processing...</p>
        </div>
      </div>
    );
  }

  const getStatusIcon = (stageStatus: string) => {
    switch (stageStatus) {
      case 'complete':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'running':
        return <Clock className="h-5 w-5 text-blue-600 animate-spin" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return '';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4 py-12">
      <div className="max-w-2xl w-full bg-white rounded-xl shadow-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">⚙️ Processing Your Data...</h2>

        <div className="space-y-4 mb-6">
          {status.stages.map((stage, index) => (
            <div key={index} className="flex items-center gap-4">
              <div className="flex-shrink-0">
                {getStatusIcon(stage.status)}
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className={`font-medium ${
                    stage.status === 'complete' ? 'text-green-700' :
                    stage.status === 'running' ? 'text-blue-700' :
                    stage.status === 'error' ? 'text-red-700' :
                    'text-gray-500'
                  }`}>
                    {stage.status === 'running' && '⏳ '}
                    {stage.status === 'complete' && '✓ '}
                    {stage.name}
                  </span>
                  {stage.duration && (
                    <span className="text-sm text-gray-500">({formatDuration(stage.duration)})</span>
                  )}
                </div>
                {stage.message && (
                  <p className="text-sm text-gray-600">{stage.message}</p>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="mb-6">
          <ProgressBar
            value={status.overallProgress}
            color="#3B82F6"
            size="lg"
            showLabel={true}
            label={`${status.overallProgress}% complete`}
          />
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">
              {status.recordsProcessed} customers
            </span>
            <span className="text-gray-600">
              {status.recordsProcessed * 14} KPIs
            </span>
            <span className={status.errors > 0 ? 'text-red-600' : 'text-green-600'}>
              {status.errors} errors
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProcessingProgress;

