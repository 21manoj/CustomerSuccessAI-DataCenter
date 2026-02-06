import React, { useState, useEffect } from 'react';
import VerticalSelector from './VerticalSelector';
import TemplatePreview from './TemplatePreview';
import SmartUploadZone from './SmartUploadZone';
import FieldMapperAI from './FieldMapperAI';
import ProcessingProgress from './ProcessingProgress';
import SuccessSummary from './SuccessSummary';
import {
  getVerticals,
  getTemplate,
  uploadFile,
  getImportSummary,
  VerticalOption,
  TemplateInfo,
  FieldMapping,
  ProcessingStatus,
  ImportSummary
} from '../../utils/onboardingApi';
import { useSession } from '../../contexts/SessionContext';
import { useNavigate } from 'react-router-dom';

type OnboardingStep =
  | 'vertical-selection'
  | 'template-preview'
  | 'upload'
  | 'field-mapping'
  | 'processing'
  | 'success';

const WIZARD_STEPS: OnboardingStep[] = [
  'vertical-selection',
  'template-preview',
  'upload',
  'field-mapping',
  'processing',
  'success'
];

// Parse a CSV line handling quoted values and escaped quotes ("")
const parseCSVLine = (line: string): string[] => {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];

    if (char === '"') {
      if (inQuotes && i + 1 < line.length && line[i + 1] === '"') {
        // Escaped quote inside quoted field
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      result.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current.trim());
  return result;
};

const OnboardingWizard: React.FC = () => {
  const { session } = useSession();
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState<OnboardingStep>('vertical-selection');
  const [verticals, setVerticals] = useState<VerticalOption[]>([]);
  const [selectedVertical, setSelectedVertical] = useState<string | null>(null);
  const [template, setTemplate] = useState<TemplateInfo | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [sourceColumns, setSourceColumns] = useState<string[]>([]);
  const [fieldMappings, setFieldMappings] = useState<FieldMapping[]>([]);
  const [sessionId, setSessionId] = useState<string>('');
  const [uploadId, setUploadId] = useState<string>('');
  const [importSummary, setImportSummary] = useState<ImportSummary | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    if (session?.customer_id) {
      loadVerticals();
    } else {
      navigate('/login');
    }
  }, [session, navigate]);

  const loadVerticals = async () => {
    try {
      const verticalsData = await getVerticals();
      setVerticals(verticalsData);
    } catch (error) {
      console.error('Error loading verticals:', error);
    }
  };

  const handleVerticalSelect = async (verticalId: string) => {
    setSelectedVertical(verticalId);
    try {
      const templateData = await getTemplate(verticalId);
      setTemplate(templateData);
      setCurrentStep('template-preview');
    } catch (error) {
      console.error('Error loading template:', error);
    }
  };

  const handleCustomKPIs = () => {
    handleVerticalSelect('datacenter');
  };

  const handleFileSelect = async (file: File) => {
    setUploadedFile(file);

    // Only parse headers from CSV text files
    const extension = file.name.split('.').pop()?.toLowerCase();
    if (extension === 'xlsx' || extension === 'xls') {
      // Excel files: the backend handles parsing, so skip client-side header extraction
      // and go straight to field mapping with template KPI names as source columns
      if (template) {
        setSourceColumns(template.kpis.map(k => k.name));
      }
      setCurrentStep('field-mapping');
      return;
    }

    // CSV parsing
    try {
      const text = await file.text();
      const lines = text.split(/\r?\n/).filter(line => line.trim());

      if (lines.length > 0) {
        const columns = parseCSVLine(lines[0]);
        setSourceColumns(columns);
      }
    } catch (error) {
      console.error('Error parsing file:', error);
      // If parsing fails, use template KPI names as fallback
      if (template) {
        setSourceColumns(template.kpis.map(k => k.name));
      }
    }

    setCurrentStep('field-mapping');
  };

  const handleFieldMappingContinue = async () => {
    if (!uploadedFile) return;

    // Generate unique session ID
    const newSessionId = `onboarding_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    setSessionId(newSessionId);
    setUploadError(null);

    try {
      const result = await uploadFile(
        uploadedFile,
        fieldMappings,
        newSessionId,
        undefined,
        selectedVertical || 'datacenter'
      );
      setUploadId(result.uploadId);
      setCurrentStep('processing');
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadError(error instanceof Error ? error.message : 'Failed to upload file. Please try again.');
    }
  };

  const handleProcessingComplete = async (status: ProcessingStatus) => {
    try {
      const summary = await getImportSummary(uploadId);
      setImportSummary(summary);
      setCurrentStep('success');
    } catch (error) {
      console.error('Error getting summary:', error);
      setImportSummary({
        customersImported: 0,
        kpisProcessed: 0,
        healthyAccounts: 0,
        atRiskAccounts: 0,
        criticalAccounts: 0,
        portfolioHealth: 0,
        priorityActions: 0
      });
      setCurrentStep('success');
    }
  };

  const handleAction = (action: 'dashboard' | 'alerts' | 'assistant' | 'tour') => {
    switch (action) {
      case 'dashboard':
        navigate('/executive-dashboard');
        break;
      case 'alerts':
        navigate('/dashboard');
        break;
      case 'assistant':
        navigate('/dashboard');
        break;
      case 'tour':
        console.log('Starting product tour');
        break;
    }
  };

  const handleBack = () => {
    const currentIndex = WIZARD_STEPS.indexOf(currentStep);
    if (currentIndex > 0) {
      setCurrentStep(WIZARD_STEPS[currentIndex - 1]);
    }
  };

  const getStepNumber = (step: OnboardingStep): number => {
    return WIZARD_STEPS.indexOf(step) + 1;
  };

  // Displayable steps (exclude 'success' from progress bar)
  const displaySteps = WIZARD_STEPS.length - 1; // 5 steps shown

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Progress Indicator */}
      {currentStep !== 'success' && (
        <div className="bg-white border-b border-gray-200 px-8 py-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-600">
                Step {Math.min(getStepNumber(currentStep), displaySteps)} of {displaySteps}
              </span>
              <span className="text-sm text-gray-500">
                {Math.round((Math.min(getStepNumber(currentStep), displaySteps) / displaySteps) * 100)}% Complete
              </span>
            </div>
            <div className="flex items-center gap-2">
              {Array.from({ length: displaySteps }).map((_, index) => {
                const stepNum = index + 1;
                const currentNum = Math.min(getStepNumber(currentStep), displaySteps);
                const isActive = stepNum === currentNum;
                const isComplete = stepNum < currentNum;

                return (
                  <React.Fragment key={index}>
                    <div className={`flex-1 h-2 rounded-full ${
                      isComplete ? 'bg-green-500' :
                      isActive ? 'bg-blue-500' :
                      'bg-gray-200'
                    }`} />
                    {index < displaySteps - 1 && (
                      <div className={`w-2 h-2 rounded-full ${
                        isComplete ? 'bg-green-500' :
                        isActive ? 'bg-blue-500' :
                        'bg-gray-200'
                      }`} />
                    )}
                  </React.Fragment>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Step Content */}
      {currentStep === 'vertical-selection' && (
        <VerticalSelector
          verticals={verticals}
          selectedVertical={selectedVertical}
          onSelect={handleVerticalSelect}
          onCustom={handleCustomKPIs}
        />
      )}

      {currentStep === 'template-preview' && template && selectedVertical && (
        <TemplatePreview
          template={template}
          vertical={selectedVertical}
          onSkip={() => setCurrentStep('upload')}
          onContinue={() => setCurrentStep('upload')}
        />
      )}

      {currentStep === 'upload' && (
        <SmartUploadZone
          onFileSelect={handleFileSelect}
          acceptedFormats={['.csv', '.xlsx', '.xls']}
          maxSizeBytes={10 * 1024 * 1024}
          showPreview={true}
          onBack={handleBack}
        />
      )}

      {currentStep === 'field-mapping' && uploadedFile && selectedVertical && (
        <FieldMapperAI
          sourceColumns={sourceColumns}
          targetFields={template?.kpis.map(k => k.name) || []}
          vertical={selectedVertical}
          onMappingChange={setFieldMappings}
          onContinue={handleFieldMappingContinue}
          onBack={() => setCurrentStep('upload')}
        />
      )}

      {currentStep === 'field-mapping' && uploadError && (
        <div className="max-w-4xl mx-auto px-4 mt-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-600">{uploadError}</p>
          </div>
        </div>
      )}

      {currentStep === 'processing' && sessionId && (
        <ProcessingProgress
          sessionId={sessionId}
          onComplete={handleProcessingComplete}
        />
      )}

      {currentStep === 'success' && importSummary && (
        <SuccessSummary
          summary={importSummary}
          onAction={handleAction}
        />
      )}
    </div>
  );
};

export default OnboardingWizard;
