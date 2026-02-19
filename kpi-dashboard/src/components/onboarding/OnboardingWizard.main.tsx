/**
 * Enhanced Onboarding Wizard - Main Orchestrator
 * 
 * Complete 8-step wizard for new customer onboarding
 */

import React, { useState, useEffect } from 'react';
import {
  Building2, BarChart2, AlertTriangle, Target, Database, CheckCircle,
  ChevronLeft, ChevronRight, X, Rocket, CreditCard, Users, BookOpen,
  Loader2
} from 'lucide-react';

// Types
import { OnboardingData, OnboardingMode } from './OnboardingWizard.types';

// Configuration
import {
  DEFAULT_ACCOUNT,
  DEFAULT_BUSINESS,
  DEFAULT_CRITERIA,
  getDefaultSources,
  getPillarsForVertical,
  getEventsForVertical
} from './OnboardingWizard.config';

// Step Components
import { Step0Account } from './Step0Account';
import { Step1Business } from './Step1Business';
import { Step2Pillars } from './Step2Pillars';
import { Step3Events } from './Step3Events';
import { Step4Criteria } from './Step4Criteria';
import { Step5Sources } from './Step5Sources';
import { Step6Review } from './Step6Review';
import { Step7Team } from './Step7Team';
import { Step8Training } from './Step8Training';

// ============================================================================
// MAIN WIZARD COMPONENT
// ============================================================================

interface OnboardingWizardProps {
  onComplete: (data: OnboardingData) => void;
  onCancel: () => void;
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ onComplete, onCancel }) => {
  const [step, setStep] = useState(0);
  const [account, setAccount] = useState(DEFAULT_ACCOUNT);
  const [business, setBusiness] = useState(DEFAULT_BUSINESS);
  const [pillars, setPillars] = useState(getPillarsForVertical(null));
  const [events, setEvents] = useState(getEventsForVertical(null));
  const [criteria, setCriteria] = useState(DEFAULT_CRITERIA);
  const [sources, setSources] = useState(getDefaultSources(null));
  const [team, setTeam] = useState<any[]>([]);
  const [skipTraining, setSkipTraining] = useState(false);
  const [onboardingMode, setOnboardingMode] = useState<OnboardingMode>('demo');

  // Processing state
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState('');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const [customerId, setCustomerId] = useState<number | null>(null);
  const [userId, setUserId] = useState<number | null>(null);

  // Update pillars and events when vertical changes
  useEffect(() => {
    if (business.vertical) {
      setPillars(getPillarsForVertical(business.vertical));
      setEvents(getEventsForVertical(business.vertical));
      setSources(getDefaultSources(business.vertical));
    }
  }, [business.vertical]);

  const steps = [
    { num: 0, title: 'Account & Billing', icon: <CreditCard className="w-5 h-5" /> },
    { num: 1, title: 'Business Context', icon: <Building2 className="w-5 h-5" /> },
    { num: 2, title: 'KPI Priorities', icon: <BarChart2 className="w-5 h-5" /> },
    { num: 3, title: 'Event Severity', icon: <AlertTriangle className="w-5 h-5" /> },
    { num: 4, title: 'Success Criteria', icon: <Target className="w-5 h-5" /> },
    { num: 5, title: 'Data Sources', icon: <Database className="w-5 h-5" /> },
    { num: 6, title: 'Review', icon: <CheckCircle className="w-5 h-5" /> },
    { num: 7, title: 'Team Setup', icon: <Users className="w-5 h-5" /> },
    { num: 8, title: 'Training', icon: <BookOpen className="w-5 h-5" /> }
  ];

  const canProceed = (): boolean => {
    switch (step) {
      case 0:
        return !!(
          account.email &&
          account.password.length >= 8 &&
          account.company_domain &&
          account.subscription_plan
        );
      case 1:
        return !!(
          business.vertical &&
          business.company_name &&
          business.industry &&
          business.segments.length > 0
        );
      case 5:
        // Demo mode: no file uploads required (synthetic data generated automatically)
        // Custom mode: accounts.csv and kpis.csv must be uploaded
        if (onboardingMode === 'demo') return true;
        return (
          sources.find((s) => s.id === 'accounts')?.status === 'uploaded' &&
          sources.find((s) => s.id === 'kpis')?.status === 'uploaded'
        );
      default:
        return true;
    }
  };

  // Helper: Convert pillar rankings to weight object
  const convertPillarsToWeights = (pillars: any[]): Record<string, number> => {
    const weights: Record<string, number> = {};
    
    pillars.forEach(pillar => {
      // Use inverse rank weighting
      const totalRanks = pillars.length;
      const inverseRank = totalRanks - pillar.rank + 1;
      weights[pillar.id] = inverseRank;
    });
    
    // Normalize to sum to 1.0
    const total = Object.values(weights).reduce((sum, w) => sum + w, 0);
    Object.keys(weights).forEach(key => {
      weights[key] = Number((weights[key] / total).toFixed(4));
    });
    
    return weights;
  };

  // Helper: Sleep function for delays
  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

  // Helper: Retry function for API calls
  const retryFetch = async (
    url: string,
    options: RequestInit,
    maxRetries: number = 3,
    retryDelay: number = 1000
  ): Promise<Response> => {
    let lastError: Error | null = null;
    let lastResponse: Response | null = null;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const response = await fetch(url, options);
        lastResponse = response;
        
        // Success - return immediately
        if (response.ok) {
          return response;
        }
        
        // 4xx errors (client errors) - retry once, then fail
        if (response.status >= 400 && response.status < 500) {
          if (attempt < maxRetries) {
            console.warn(`Attempt ${attempt} failed with client error ${response.status}, retrying once...`);
            await sleep(retryDelay * attempt);
            continue;
          }
          // Last attempt failed with client error, return response
          return response;
        }
        
        // 5xx errors (server errors) - retry with exponential backoff
        if (response.status >= 500) {
          if (attempt < maxRetries) {
            console.warn(`Attempt ${attempt} failed with server error ${response.status}, retrying...`);
            await sleep(retryDelay * attempt);
            continue;
          }
          // Last attempt, return response even if failed
          return response;
        }
        
        // Other status codes - return as-is
        return response;
      } catch (error: any) {
        lastError = error;
        // Network errors - retry with exponential backoff
        if (attempt < maxRetries) {
          console.warn(`Attempt ${attempt} failed with network error: ${error.message}, retrying...`);
          await sleep(retryDelay * attempt);
          continue;
        }
        // Last attempt failed, throw error
        throw error;
      }
    }
    
    // If we have a response from last attempt, return it
    if (lastResponse) {
      return lastResponse;
    }
    
    // If we have an error, throw it
    if (lastError) {
      throw lastError;
    }
    
    throw new Error('Failed after all retry attempts');
  };

  // Map vertical from frontend to backend format
  const getBackendVertical = (vertical: string | null): string => {
    if (vertical === 'datacenter') return 'dc2_s';
    if (vertical === 'saas') return 'saas';
    return 'dc2_s'; // Default
  };

  // Map vertical to dashboard route
  const getDashboardRoute = (vertical: string | null): string => {
    if (vertical === 'datacenter') return '/dc-dashboard';
    if (vertical === 'saas') return '/saas-dashboard';
    return '/dc-dashboard'; // Default
  };

  const handleComplete = async () => {
    setIsProcessing(true);
    setProcessingError(null);
    setProcessingProgress(0);

    const isDemo = onboardingMode === 'demo';

    try {
      // ============================================================
      // STEP 1: Complete Onboarding (Create Customer/User/Config)
      // In demo mode: also generates synthetic CSV files
      // In custom mode: creates DB records only, user uploads CSVs
      // ============================================================
      setProcessingStep(isDemo
        ? 'Creating account & generating demo data...'
        : 'Creating your account...');
      setProcessingProgress(10);

      const weights = convertPillarsToWeights(pillars);
      const backendVertical = getBackendVertical(business.vertical);

      const completePayload: Record<string, any> = {
        company_name: business.company_name,
        company_email: account.email,
        admin_name: account.email.split('@')[0],
        admin_email: account.email,
        admin_password: account.password,
        vertical: backendVertical,
        weights: weights,
        onboarding_mode: onboardingMode,
        num_accounts: isDemo ? 10 : 3,
        team: team.map(t => ({
          name: t.name,
          email: t.email,
          role: t.role
        }))
      };

      // Demo mode: include showcase pattern mix for journey generation
      if (isDemo) {
        completePayload.showcase_pattern_mix = JSON.stringify({
          crisis: 0.30,
          churn: 0.20,
          stable: 0.25,
          expansion: 0.25
        });
      }

      console.log(`Step 1: Calling /api/onboarding/complete (mode: ${onboardingMode})`, completePayload);

      const completeResponse = await retryFetch('/api/onboarding/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(completePayload)
      });

      if (!completeResponse.ok) {
        const errorData = await completeResponse.json();
        throw new Error(errorData.message || errorData.error || 'Failed to create account');
      }

      const completeResult = await completeResponse.json();
      const newCustomerId = completeResult.customer_id;
      const newUserId = completeResult.user_id;

      setCustomerId(newCustomerId);
      setUserId(newUserId);

      console.log('Step 1 complete:', {
        customer_id: newCustomerId,
        user_id: newUserId,
        mode: onboardingMode,
        csv_generated: completeResult.csv_files_generated
      });
      setProcessingProgress(isDemo ? 30 : 20);

      // ============================================================
      // STEP 2: Provision workspace (no-op, handled by /complete)
      // ============================================================
      setProcessingStep('Setting up workspace...');

      await fetch('/api/onboarding/provision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ customer_id: newCustomerId, vertical: backendVertical })
      });
      // No-op endpoint, always succeeds - ignore result
      console.log('Step 2 complete: workspace ready (handled by /complete)');
      setProcessingProgress(isDemo ? 35 : 30);

      // ============================================================
      // STEP 3: Upload CSV Files (Custom mode only)
      // Demo mode: CSVs already generated by /complete
      // ============================================================
      if (!isDemo) {
        const uploadedFiles = sources.filter(s => s.status === 'uploaded' && s.file);

        if (uploadedFiles.length === 0) {
          throw new Error('No files uploaded. Please upload at least accounts.csv and kpi_measurements.csv');
        }

        for (let i = 0; i < uploadedFiles.length; i++) {
          const source = uploadedFiles[i];
          const progress = 30 + ((i / uploadedFiles.length) * 20); // 30-50%
          setProcessingStep(`Uploading ${source.name}... (${i + 1}/${uploadedFiles.length})`);
          setProcessingProgress(progress);

          const formData = new FormData();
          formData.append('file', source.file!);
          formData.append('file_type', source.id);
          formData.append('customer_id', newCustomerId.toString());

          console.log(`Step 3.${i + 1}: Uploading ${source.id}`, source.name);

          const uploadResponse = await retryFetch('/api/onboarding/upload', {
            method: 'POST',
            credentials: 'include',
            body: formData
          }, 2);

          if (!uploadResponse.ok) {
            const errorData = await uploadResponse.json();
            throw new Error(`Failed to upload ${source.name}: ${errorData.message || 'Unknown error'}`);
          }

          const uploadResult = await uploadResponse.json();
          console.log(`Step 3.${i + 1} complete:`, uploadResult);
        }
      } else {
        console.log('Step 3 skipped: demo mode uses synthetic CSVs from /complete');
      }

      setProcessingProgress(isDemo ? 40 : 50);

      // ============================================================
      // STEP 4: Process Data + Generate Journeys
      // Demo mode: uses showcase pattern mix (30% crisis, 20% churn,
      //   25% stable, 25% expansion) to create compelling narratives
      // Custom mode: uses default balanced pattern mix
      // ============================================================
      setProcessingStep(isDemo
        ? 'Generating showcase journeys (this may take 2-3 minutes)...'
        : 'Processing your data (this may take 2-3 minutes)...');

      const processPayload: Record<string, any> = {
        customer_id: newCustomerId,
        onboarding_mode: onboardingMode,
        skip_validation: false,
        skip_wizard_b: false,
        skip_wizard_c: false
      };

      // Demo: use showcase pattern mix emphasizing crisis/churn for value prop demo
      if (isDemo) {
        processPayload.pattern_mix = JSON.stringify({
          crisis: 0.30,
          churn: 0.20,
          stable: 0.25,
          expansion: 0.25
        });
      }

      console.log('Step 4: Calling /api/onboarding/process-data', processPayload);

      const processResponse = await fetch('/api/onboarding/process-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(processPayload)
      });

      if (!processResponse.ok) {
        const errorData = await processResponse.json();
        throw new Error(errorData.message || 'Failed to process data');
      }

      const processResult = await processResponse.json();
      console.log('Step 4 complete:', processResult);
      console.log('   Steps completed:', processResult.steps_completed);

      setProcessingProgress(90);

      // ============================================================
      // STEP 5: Finalize (journey API registration - no-op)
      // ============================================================
      setProcessingStep('Finalizing setup...');

      await fetch('/api/onboarding/register-journey-api', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ customer_id: newCustomerId })
      });
      // No-op endpoint, always succeeds - ignore result
      console.log('Step 5 complete: journeys are DB-based');

      setProcessingProgress(100);
      setProcessingStep(isDemo
        ? 'Demo ready! Redirecting to dashboard...'
        : 'Setup complete! Redirecting to dashboard...');

      // ============================================================
      // STEP 6: Success! Prepare Data and Redirect
      // ============================================================
      const onboardingData: OnboardingData = {
        account,
        business,
        pillars,
        events,
        criteria,
        sources,
        team,
        skip_training: skipTraining,
        onboarding_mode: onboardingMode
      };

      await sleep(1000);

      onComplete(onboardingData);

      const dashboardRoute = getDashboardRoute(business.vertical);
      console.log(`Onboarding complete (${onboardingMode} mode)! Redirecting to ${dashboardRoute}`);
      window.location.href = dashboardRoute;

    } catch (error: any) {
      console.error('Onboarding error:', error);
      setProcessingError(error.message || 'An unexpected error occurred');
      setIsProcessing(false);
    }
  };

  const totalSteps = steps.length;
  const isLastStep = step === totalSteps - 1;
  const isFirstStep = step === 0;

  return (
    <>
      {/* ============================================================ */}
      {/* PROCESSING OVERLAY */}
      {/* ============================================================ */}
      {isProcessing && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[60]">
          <div className="bg-white rounded-xl p-8 max-w-md w-full mx-4">
            <div className="text-center">
              {/* Progress Spinner */}
              <div className="relative w-24 h-24 mx-auto mb-6">
                <svg className="transform -rotate-90 w-24 h-24">
                  <circle
                    cx="48"
                    cy="48"
                    r="44"
                    stroke="#E5E7EB"
                    strokeWidth="8"
                    fill="none"
                  />
                  <circle
                    cx="48"
                    cy="48"
                    r="44"
                    stroke="#3B82F6"
                    strokeWidth="8"
                    fill="none"
                    strokeDasharray={`${2 * Math.PI * 44}`}
                    strokeDashoffset={`${2 * Math.PI * 44 * (1 - processingProgress / 100)}`}
                    className="transition-all duration-500"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-2xl font-bold text-blue-600">{processingProgress}%</span>
                </div>
              </div>
              
              {/* Status Message */}
              <h3 className="text-xl font-bold mb-2 text-gray-900">
                {onboardingMode === 'demo' ? 'Setting Up Demo Environment' : 'Setting Up Your Account'}
              </h3>
              <p className="text-gray-600 mb-6">{processingStep}</p>
              
              {/* Progress Stages - adapt to onboarding mode */}
              <div className="text-left space-y-2 mb-6">
                {onboardingMode === 'demo' ? (
                  <>
                    <div className={`flex items-center gap-2 text-sm ${processingProgress >= 30 ? 'text-green-600' : 'text-gray-400'}`}>
                      {processingProgress >= 30 ? '✓' : '○'} Create account & generate demo data
                    </div>
                    <div className={`flex items-center gap-2 text-sm ${processingProgress >= 35 ? 'text-green-600' : 'text-gray-400'}`}>
                      {processingProgress >= 35 ? '✓' : '○'} Setup workspace
                    </div>
                    <div className={`flex items-center gap-2 text-sm ${processingProgress >= 40 ? 'text-green-600' : 'text-gray-400'}`}>
                      {processingProgress >= 40 ? '✓' : '○'} Load data into database
                    </div>
                    <div className={`flex items-center gap-2 text-sm ${processingProgress >= 90 ? 'text-green-600' : 'text-gray-400'}`}>
                      {processingProgress >= 90 ? '✓' : '○'} Generate showcase journeys
                    </div>
                    <div className={`flex items-center gap-2 text-sm ${processingProgress >= 100 ? 'text-green-600' : 'text-gray-400'}`}>
                      {processingProgress >= 100 ? '✓' : '○'} Demo ready
                    </div>
                  </>
                ) : (
                  <>
                    <div className={`flex items-center gap-2 text-sm ${processingProgress >= 20 ? 'text-green-600' : 'text-gray-400'}`}>
                      {processingProgress >= 20 ? '✓' : '○'} Create account
                    </div>
                    <div className={`flex items-center gap-2 text-sm ${processingProgress >= 30 ? 'text-green-600' : 'text-gray-400'}`}>
                      {processingProgress >= 30 ? '✓' : '○'} Setup workspace
                    </div>
                    <div className={`flex items-center gap-2 text-sm ${processingProgress >= 50 ? 'text-green-600' : 'text-gray-400'}`}>
                      {processingProgress >= 50 ? '✓' : '○'} Upload CSV files
                    </div>
                    <div className={`flex items-center gap-2 text-sm ${processingProgress >= 90 ? 'text-green-600' : 'text-gray-400'}`}>
                      {processingProgress >= 90 ? '✓' : '○'} Process data & generate journeys
                    </div>
                    <div className={`flex items-center gap-2 text-sm ${processingProgress >= 100 ? 'text-green-600' : 'text-gray-400'}`}>
                      {processingProgress >= 100 ? '✓' : '○'} Finalize setup
                    </div>
                  </>
                )}
              </div>
              
              {/* Error Display */}
              {processingError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                  <p className="text-sm text-red-800 font-medium mb-2">Error occurred:</p>
                  <p className="text-sm text-red-600">{processingError}</p>
                  <button
                    onClick={() => {
                      setProcessingError(null);
                      setIsProcessing(false);
                      setProcessingProgress(0);
                    }}
                    className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm w-full"
                  >
                    Try Again
                  </button>
                </div>
              )}
              
              {/* Info */}
              {processingProgress >= 40 && processingProgress < 90 && !processingError && (
                <p className="text-xs text-gray-500">
                  ⏳ Processing may take 2-3 minutes for large datasets
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* MAIN WIZARD */}
      {/* ============================================================ */}
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold">Customer Onboarding Wizard</h2>
              <p className="text-blue-100 text-sm">Step {step + 1} of {totalSteps}</p>
            </div>
            <button onClick={onCancel} className="p-1 hover:bg-white/20 rounded">
              <X className="w-5 h-5" />
            </button>
          </div>
          
          {/* Progress Bar */}
          <div className="flex items-center gap-1 mt-4">
            {steps.map((s) => (
              <div key={s.num} className="flex-1">
                <div className={`h-1 rounded-full ${
                  s.num < step ? 'bg-white' :
                  s.num === step ? 'bg-white/70' :
                  'bg-white/30'
                }`} />
              </div>
            ))}
          </div>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center justify-center gap-4 py-4 border-b bg-gray-50 overflow-x-auto">
          {steps.map((s) => (
            <div
              key={s.num}
              className={`flex items-center gap-2 whitespace-nowrap ${
                s.num === step ? 'text-blue-600' :
                s.num < step ? 'text-green-600' :
                'text-gray-400'
              }`}
            >
              {s.num < step ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                s.icon
              )}
              <span className={`text-sm ${s.num === step ? 'font-medium' : ''}`}>
                {s.title}
              </span>
            </div>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {step === 0 && <Step0Account data={account} onChange={setAccount} />}
          {step === 1 && <Step1Business data={business} onChange={setBusiness} />}
          {step === 2 && <Step2Pillars data={pillars} onChange={setPillars} />}
          {step === 3 && <Step3Events data={events} onChange={setEvents} />}
          {step === 4 && <Step4Criteria data={criteria} onChange={setCriteria} />}
          {step === 5 && <Step5Sources data={sources} onChange={setSources} onboardingMode={onboardingMode} onModeChange={setOnboardingMode} businessContext={business} />}
          {step === 6 && <Step6Review data={{ account, business, pillars, events, criteria, sources, team, skip_training: skipTraining, onboarding_mode: onboardingMode }} />}
          {step === 7 && <Step7Team data={team} onChange={setTeam} />}
          {step === 8 && <Step8Training skipTraining={skipTraining} onSkipChange={setSkipTraining} />}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t flex items-center justify-between">
          <button
            onClick={() => setStep(step - 1)}
            disabled={isFirstStep}
            className={`px-4 py-2 rounded flex items-center gap-2 ${
              isFirstStep
                ? 'text-gray-400 cursor-not-allowed'
                : 'text-gray-600 hover:bg-gray-200'
            }`}
          >
            <ChevronLeft className="w-4 h-4" />
            Back
          </button>
          
          <div className="flex items-center gap-3">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded"
            >
              Cancel
            </button>
            
            {!isLastStep ? (
              <button
                onClick={() => setStep(step + 1)}
                disabled={!canProceed()}
                className={`px-4 py-2 rounded flex items-center gap-2 ${
                  canProceed()
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={handleComplete}
                disabled={isProcessing}
                className={`px-6 py-2 rounded flex items-center gap-2 ${
                  isProcessing
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-green-600 hover:bg-green-700'
                } text-white`}
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Rocket className="w-4 h-4" />
                    Complete Setup
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
    </>
  );
};

export default OnboardingWizard;
