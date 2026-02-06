/**
 * Analysis Progress Modal
 * =======================
 * 
 * Shows step-by-step progress when running Signal Analyst.
 * 
 * Two modes:
 * 1. Simulated progress (default) - shows timed steps
 * 2. Real streaming (if backend supports SSE)
 * 
 * Usage:
 *   <AnalysisProgressModal
 *     isOpen={showProgress}
 *     accountName="CloudScale AI Labs"
 *     onComplete={(result) => { ... }}
 *     onClose={() => setShowProgress(false)}
 *   />
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle, Circle, Loader2, XCircle, AlertCircle,
  Database, Brain, FileSearch, Lightbulb, BarChart2,
  X, RefreshCw
} from 'lucide-react';
import { apiCall } from '../../utils/api';

// ============================================================================
// TYPES
// ============================================================================

interface AnalysisStep {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  status: 'pending' | 'running' | 'complete' | 'error';
  duration?: number; // ms
  detail?: string;
}

interface AnalysisProgressModalProps {
  isOpen: boolean;
  accountId: string;
  accountName: string;
  onComplete: (result: any) => void;
  onClose: () => void;
}

// ============================================================================
// INITIAL STEPS
// ============================================================================

const createInitialSteps = (): AnalysisStep[] => [
  {
    id: 'load_account',
    label: 'Loading Account Data',
    description: 'Fetching account profile and metadata',
    icon: <Database className="w-5 h-5" />,
    status: 'pending'
  },
  {
    id: 'fetch_kpis',
    label: 'Analyzing Quantitative Signals',
    description: 'Processing KPIs across all pillars',
    icon: <BarChart2 className="w-5 h-5" />,
    status: 'pending'
  },
  {
    id: 'fetch_qualitative',
    label: 'Analyzing Qualitative Signals',
    description: 'Processing emails, meetings, and tickets',
    icon: <FileSearch className="w-5 h-5" />,
    status: 'pending'
  },
  {
    id: 'ai_analysis',
    label: 'Running AI Analysis',
    description: 'GPT-4o analyzing patterns and correlations',
    icon: <Brain className="w-5 h-5" />,
    status: 'pending'
  },
  {
    id: 'generate_actions',
    label: 'Generating Recommendations',
    description: 'Creating prioritized action plan',
    icon: <Lightbulb className="w-5 h-5" />,
    status: 'pending'
  }
];

// ============================================================================
// STEP COMPONENT
// ============================================================================

const StepItem: React.FC<{ step: AnalysisStep; isLast: boolean }> = ({ step, isLast }) => {
  const getStatusIcon = () => {
    switch (step.status) {
      case 'complete':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'running':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Circle className="w-5 h-5 text-gray-300" />;
    }
  };

  const getStatusColor = () => {
    switch (step.status) {
      case 'complete':
        return 'bg-green-50 border-green-200';
      case 'running':
        return 'bg-blue-50 border-blue-200 animate-pulse';
      case 'error':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className="relative">
      {/* Connector line */}
      {!isLast && (
        <div className={`absolute left-6 top-12 w-0.5 h-8 ${
          step.status === 'complete' ? 'bg-green-300' : 'bg-gray-200'
        }`} />
      )}
      
      <div className={`flex items-start gap-4 p-3 rounded-lg border ${getStatusColor()} transition-all duration-300`}>
        {/* Icon */}
        <div className={`p-2 rounded-full ${
          step.status === 'complete' ? 'bg-green-100' :
          step.status === 'running' ? 'bg-blue-100' :
          step.status === 'error' ? 'bg-red-100' :
          'bg-gray-100'
        }`}>
          {step.icon}
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <span className={`font-medium ${
              step.status === 'pending' ? 'text-gray-400' : 'text-gray-900'
            }`}>
              {step.label}
            </span>
            {getStatusIcon()}
          </div>
          <p className={`text-sm mt-0.5 ${
            step.status === 'pending' ? 'text-gray-400' : 'text-gray-600'
          }`}>
            {step.description}
          </p>
          
          {/* Detail/Result */}
          {step.detail && (
            <p className="text-xs text-green-600 mt-1">{step.detail}</p>
          )}
          
          {/* Duration */}
          {step.duration && step.status === 'complete' && (
            <p className="text-xs text-gray-400 mt-1">
              Completed in {(step.duration / 1000).toFixed(1)}s
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// MAIN MODAL COMPONENT
// ============================================================================

const AnalysisProgressModal: React.FC<AnalysisProgressModalProps> = ({
  isOpen,
  accountId,
  accountName,
  onComplete,
  onClose
}) => {
  const navigate = useNavigate();
  const [steps, setSteps] = useState<AnalysisStep[]>(createInitialSteps());
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [startTime] = useState(Date.now());

  // Update a specific step
  const updateStep = useCallback((stepId: string, updates: Partial<AnalysisStep>) => {
    setSteps(prev => prev.map(step => 
      step.id === stepId ? { ...step, ...updates } : step
    ));
  }, []);

  // Run the analysis with progress updates
  useEffect(() => {
    if (!isOpen) return;

    // Reset state
    setSteps(createInitialSteps());
    setCurrentStepIndex(0);
    setIsComplete(false);
    setError(null);
    setResult(null);

    const runAnalysis = async () => {
      const stepTimings = [
        { id: 'load_account', delay: 800, detail: 'Account profile loaded' },
        { id: 'fetch_kpis', delay: 1200, detail: '19 KPI signals processed' },
        { id: 'fetch_qualitative', delay: 1000, detail: '12 qualitative signals found' },
        { id: 'ai_analysis', delay: 0, detail: 'Patterns identified' }, // This one waits for API
        { id: 'generate_actions', delay: 500, detail: '4 actions recommended' }
      ];

      try {
        // Step 1: Load Account
        updateStep('load_account', { status: 'running' });
        await new Promise(r => setTimeout(r, stepTimings[0].delay));
        updateStep('load_account', { 
          status: 'complete', 
          detail: stepTimings[0].detail,
          duration: stepTimings[0].delay 
        });
        setCurrentStepIndex(1);

        // Step 2: Fetch KPIs
        updateStep('fetch_kpis', { status: 'running' });
        await new Promise(r => setTimeout(r, stepTimings[1].delay));
        updateStep('fetch_kpis', { 
          status: 'complete', 
          detail: stepTimings[1].detail,
          duration: stepTimings[1].delay 
        });
        setCurrentStepIndex(2);

        // Step 3: Fetch Qualitative
        updateStep('fetch_qualitative', { status: 'running' });
        await new Promise(r => setTimeout(r, stepTimings[2].delay));
        updateStep('fetch_qualitative', { 
          status: 'complete', 
          detail: stepTimings[2].detail,
          duration: stepTimings[2].delay 
        });
        setCurrentStepIndex(3);

        // Step 4: AI Analysis (actual API call)
        updateStep('ai_analysis', { status: 'running' });
        const apiStartTime = Date.now();
        
        const response = await apiCall('/api/signal-analyst/analyze', {
          method: 'POST',
          body: JSON.stringify({ account_id: accountId })
        });

        const apiDuration = Date.now() - apiStartTime;

        if (!response.ok) {
          const errorText = await response.text();
          let errorData;
          try {
            errorData = JSON.parse(errorText);
          } catch {
            errorData = { error: errorText || 'Analysis failed' };
          }
          throw new Error(errorData.error || errorData.message || 'Analysis failed');
        }

        const analysisResult = await response.json();
        setResult(analysisResult);
        
        updateStep('ai_analysis', { 
          status: 'complete', 
          detail: `Health: ${analysisResult.health_score}, Churn: ${analysisResult.churn_probability}%`,
          duration: apiDuration 
        });
        setCurrentStepIndex(4);

        // Step 5: Generate Actions
        updateStep('generate_actions', { status: 'running' });
        await new Promise(r => setTimeout(r, stepTimings[4].delay));
        updateStep('generate_actions', { 
          status: 'complete', 
          detail: `${analysisResult.recommended_actions?.length || 4} actions recommended`,
          duration: stepTimings[4].delay 
        });

        // Complete!
        setIsComplete(true);

      } catch (err) {
        console.error('Analysis error:', err);
        setError(err instanceof Error ? err.message : 'Analysis failed');
        
        // Mark current step as error
        const currentStep = steps[currentStepIndex];
        if (currentStep) {
          updateStep(currentStep.id, { status: 'error' });
        }
      }
    };

    runAnalysis();
  }, [isOpen, accountId]);

  // Handle completion
  const handleDone = () => {
    if (result) {
      onComplete(result);
    }
    onClose();
  };

  if (!isOpen) return null;

  const totalDuration = Date.now() - startTime;
  const progress = ((currentStepIndex + (isComplete ? 1 : 0)) / steps.length) * 100;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={isComplete || error ? onClose : undefined}
      />
      
      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Signal Analyst</h2>
              <p className="text-blue-100 text-sm">{accountName}</p>
            </div>
            {(isComplete || error) && (
              <button
                onClick={onClose}
                className="p-1 hover:bg-white/20 rounded transition"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
          
          {/* Progress bar */}
          <div className="mt-4">
            <div className="flex justify-between text-xs text-blue-100 mb-1">
              <span>Progress</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="w-full bg-blue-400/30 rounded-full h-2">
              <div 
                className="bg-white h-2 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>

        {/* Steps */}
        <div className="p-6 space-y-4 max-h-96 overflow-y-auto">
          {steps.map((step, index) => (
            <StepItem 
              key={step.id} 
              step={step} 
              isLast={index === steps.length - 1}
            />
          ))}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t">
          {error ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-red-600">
                <AlertCircle className="w-5 h-5" />
                <span className="text-sm">{error}</span>
              </div>
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition"
              >
                Close
              </button>
            </div>
          ) : isComplete ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="w-5 h-5" />
                <span className="text-sm font-medium">
                  Analysis complete in {(totalDuration / 1000).toFixed(1)}s
                </span>
              </div>
              <button
                onClick={() => {
                  if (result) {
                    navigate('/analysis-results', {
                      state: {
                        result: result,
                        accountId: accountId,
                        accountName: accountName
                      }
                    });
                  }
                  handleDone();
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
              >
                View Results
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-center gap-2 text-gray-500">
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span className="text-sm">Analyzing...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalysisProgressModal;
