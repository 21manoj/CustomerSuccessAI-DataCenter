/**
 * Step 5: Data Sources - Dual Path (Demo Showcase vs Custom CSV Upload)
 *
 * Two onboarding paths:
 * 1. DEMO / SHOWCASE: Generate synthetic data with realistic journey patterns
 *    (crisis->recovery->expansion, crisis->churn) to demonstrate platform value.
 * 2. CUSTOM CSV UPLOAD: User uploads their own CSV files for real deployment.
 */

import React, { useState, useEffect } from 'react';
import { Upload, Link, CheckCircle, X, Eye, AlertCircle, Loader, Download, Sparkles, FileText, Info, Play, ArrowRight, TrendingUp, AlertTriangle, Zap } from 'lucide-react';
import { DataSource, OnboardingMode } from './OnboardingWizard.types';
import { validateCSV, previewCSV, testAPIConnection } from './OnboardingWizard.utils';

interface Step5SourcesProps {
  data: DataSource[];
  onChange: (data: DataSource[]) => void;
  onboardingMode: OnboardingMode;
  onModeChange: (mode: OnboardingMode) => void;
  businessContext?: {
    vertical?: string | null;
    industry?: string;
    company_name?: string;
  };
}

// CSV format specifications
const CSV_FORMATS = {
  accounts: {
    filename: 'accounts.csv',
    required_columns: ['account_id', 'customer_id', 'account_name', 'revenue', 'industry', 'region', 'account_status'],
    optional_columns: ['external_account_id', 'profile_metadata_json'],
    description: 'Account list with basic metadata and profile information'
  },
  kpis: {
    filename: 'kpi_measurements.csv',
    required_columns: ['account_id', 'account_name', 'date', 'kpi_code', 'kpi_name', 'pillar', 'value'],
    optional_columns: ['target', 'operator', 'unit'],
    description: 'Historical KPI measurements over time for trend analysis'
  },
  enhanced_signals: {
    filename: 'enhanced_qualitative_signals.csv',
    required_columns: ['account_id', 'signal_date', 'signal_type', 'content', 'sentiment'],
    optional_columns: ['signal_ref', 'sentiment_score', 'stakeholder_name', 'stakeholder_title', 'causal_chain_ref', 'revenue_impact', 'confidence', 'source_platform'],
    description: 'Qualitative signals from emails, meetings, support tickets, NPS, etc.'
  },
  products: {
    filename: 'products.csv',
    required_columns: ['account_id', 'product_name'],
    optional_columns: ['product_category', 'quantity', 'unit_price', 'deployment_date', 'status'],
    description: 'Product catalog and adoption data'
  }
};

// Demo showcase journey scenarios
const SHOWCASE_JOURNEYS = [
  {
    icon: <AlertTriangle className="w-5 h-5 text-red-500" />,
    name: 'Crisis to Recovery to Expansion',
    description: 'Account hits a critical outage, CSM intervenes proactively, recovery leads to 40% ARR expansion and multi-year renewal.',
    pattern: 'crisis',
    healthArc: '90 -> 35 -> 95',
    color: 'border-red-200 bg-red-50'
  },
  {
    icon: <X className="w-5 h-5 text-orange-500" />,
    name: 'Ignored Signals Lead to Churn',
    description: 'Warning signs go unaddressed - declining KPIs, missed QBRs, support escalations pile up until the customer churns.',
    pattern: 'churn',
    healthArc: '75 -> 40 -> 0 (churned)',
    color: 'border-orange-200 bg-orange-50'
  },
  {
    icon: <TrendingUp className="w-5 h-5 text-green-500" />,
    name: 'Proactive Growth & Expansion',
    description: 'Healthy account with strong KPIs, proactive CSM engagement drives expansion discussions and budget approvals.',
    pattern: 'expansion',
    healthArc: '80 -> 85 -> 96',
    color: 'border-green-200 bg-green-50'
  },
  {
    icon: <Zap className="w-5 h-5 text-blue-500" />,
    name: 'Steady State Operations',
    description: 'Baseline accounts operating normally - consistent KPIs, regular QBRs, standard renewal cycles.',
    pattern: 'stable',
    healthArc: '75 -> 78 -> 80',
    color: 'border-blue-200 bg-blue-50'
  }
];

export const Step5Sources: React.FC<Step5SourcesProps> = ({ data, onChange, onboardingMode, onModeChange, businessContext }) => {
  const [previewSource, setPreviewSource] = useState<string | null>(null);
  const [apiConfigSource, setApiConfigSource] = useState<string | null>(null);
  const [showFormatInfo, setShowFormatInfo] = useState<string | null>(null);
  const [customerId, setCustomerId] = useState<string>('');
  const [accountIdRange, setAccountIdRange] = useState<{start: number, end: number} | null>(null);

  // Fetch next available customer ID on mount (read-only, system-generated)
  useEffect(() => {
    const fetchNextCustomerId = async () => {
      try {
        const response = await fetch('/api/onboarding/next-customer-id', {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          setCustomerId(data.next_customer_id.toString());
          setAccountIdRange(data.account_id_range);
        }
      } catch (error) {
        console.error('Error fetching next customer ID:', error);
      }
    };
    fetchNextCustomerId();
  }, []);

  const handleFileUpload = async (id: string, file: File) => {
    // Set to validating state
    const newData = data.map((source) =>
      source.id === id ? { ...source, status: 'validating' as const, filename: file.name } : source
    );
    onChange(newData);

    try {
      // Validate CSV
      const requiredColumns = id === 'accounts' ? ['account_id', 'customer_id', 'account_name'] : undefined;
      const validation = await validateCSV(file, requiredColumns);

      // Preview first 5 rows
      const preview = await previewCSV(file, 5);

      // Update source with validation results
      const updatedData = newData.map((source) =>
        source.id === id
          ? {
              ...source,
              status: validation.valid ? ('uploaded' as const) : ('error' as const),
              rows: validation.row_count,
              file: validation.valid ? file : undefined,  // Store File object for upload
              preview,
              validation
            }
          : source
      );
      onChange(updatedData);
    } catch (error) {
      const updatedData = newData.map((source) =>
        source.id === id
          ? {
              ...source,
              status: 'error' as const,
              validation: {
                valid: false,
                errors: [error instanceof Error ? error.message : 'Validation failed'],
                warnings: []
              }
            }
          : source
      );
      onChange(updatedData);
    }
  };

  const handleConnectAPI = async (id: string) => {
    const source = data.find(s => s.id === id);
    if (!source || !source.api_config) return;

    const newData = data.map((s) =>
      s.id === id ? { ...s, status: 'validating' as const } : s
    );
    onChange(newData);

    try {
      const result = await testAPIConnection({
        endpoint: source.api_config.endpoint || '',
        api_key: source.api_config.api_key,
        auth_type: source.api_config.auth_type
      });

      const updatedData = newData.map((s) =>
        s.id === id
          ? {
              ...s,
              status: result.success ? ('connected' as const) : ('error' as const),
              api_config: {
                ...s.api_config!,
                connected_at: result.success ? new Date().toISOString() : undefined
              },
              validation: {
                valid: result.success,
                errors: result.success ? [] : [result.message],
                warnings: []
              }
            }
          : s
      );
      onChange(updatedData);
    } catch (error) {
      const updatedData = newData.map((s) =>
        s.id === id
          ? {
              ...s,
              status: 'error' as const,
              validation: {
                valid: false,
                errors: [error instanceof Error ? error.message : 'Connection failed'],
                warnings: []
              }
            }
          : s
      );
      onChange(updatedData);
    }

    setApiConfigSource(null);
  };

  const handleSkip = (id: string) => {
    const newData = data.map((source) =>
      source.id === id ? { ...source, status: 'skipped' as const } : source
    );
    onChange(newData);
  };

  const handleDownloadTemplate = (fileType: 'accounts' | 'kpis' | 'enhanced_signals' | 'products') => {
    const format = CSV_FORMATS[fileType];
    const headers = [...format.required_columns, ...format.optional_columns].join(',');
    const exampleRows = getExampleRows(fileType);

    const csvContent = `${headers}\n${exampleRows}`;
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = format.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  const getExampleRows = (fileType: 'accounts' | 'kpis' | 'enhanced_signals' | 'products'): string => {
    if (fileType === 'accounts') {
      return '10001,1,Example Account 1,500000,Technology,US-West,active,EXT-10001,"{""assigned_csm"": ""John Doe"", ""account_tier"": ""Enterprise""}"';
    } else if (fileType === 'kpis') {
      return '10001,Example Account 1,2024-01-01,P1-KPI1,System Uptime,P1,99.5,99.9,>,%';
    } else if (fileType === 'enhanced_signals') {
      return '10001,Example Account 1,2024-01-15,email,customer@example.com,csm@example.com,Monthly check-in,positive';
    } else {
      return 'DC-GPU-H100,DGX H100 Systems,Compute\nDC-COOL-LQ,Liquid Cooling Solutions,Infrastructure';
    }
  };

  const fileSources = data.filter((s) => s.type === 'file');
  const apiSources = data.filter((s) => s.type === 'api');

  // Map source IDs to CSV format specs
  const getCSVFormat = (sourceId: string) => {
    if (sourceId === 'accounts') return CSV_FORMATS.accounts;
    if (sourceId === 'kpis') return CSV_FORMATS.kpis;
    if (sourceId === 'signals' || sourceId === 'qualitative_signals' || sourceId === 'enhanced_signals') return CSV_FORMATS.enhanced_signals;
    if (sourceId === 'products') return CSV_FORMATS.products;
    return null;
  };

  return (
    <div className="space-y-6">
      {/* ================================================================ */}
      {/* PATH SELECTOR: Demo Showcase vs Custom CSV Upload                */}
      {/* ================================================================ */}
      <div>
        <h4 className="font-medium mb-2">Choose Your Onboarding Path</h4>
        <p className="text-sm text-gray-600 mb-4">
          Start with a demo to explore the platform, or upload your own data for a production deployment.
        </p>

        <div className="grid grid-cols-2 gap-4">
          {/* Demo / Showcase Path */}
          <button
            onClick={() => onModeChange('demo')}
            className={`relative border-2 rounded-xl p-5 text-left transition-all ${
              onboardingMode === 'demo'
                ? 'border-purple-500 bg-purple-50 ring-2 ring-purple-200'
                : 'border-gray-200 bg-white hover:border-purple-300 hover:bg-purple-50/50'
            }`}
          >
            {onboardingMode === 'demo' && (
              <div className="absolute top-3 right-3">
                <CheckCircle className="w-5 h-5 text-purple-600" />
              </div>
            )}
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Sparkles className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <h5 className="font-semibold text-gray-900">Demo / Showcase</h5>
                <span className="text-xs text-purple-600 font-medium">Recommended for first-time users</span>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-3">
              Generate realistic synthetic data with showcase journey patterns. See how the platform detects risks, predicts churn, and drives expansion.
            </p>
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <span>10 accounts</span>
              <span>12 months data</span>
              <span>4 journey types</span>
            </div>
          </button>

          {/* Custom CSV Upload Path */}
          <button
            onClick={() => onModeChange('custom')}
            className={`relative border-2 rounded-xl p-5 text-left transition-all ${
              onboardingMode === 'custom'
                ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                : 'border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50/50'
            }`}
          >
            {onboardingMode === 'custom' && (
              <div className="absolute top-3 right-3">
                <CheckCircle className="w-5 h-5 text-blue-600" />
              </div>
            )}
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Upload className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h5 className="font-semibold text-gray-900">Custom CSV Upload</h5>
                <span className="text-xs text-blue-600 font-medium">For production deployments</span>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-3">
              Upload your own account data, KPI measurements, and signals. The platform will analyze your real customer portfolio.
            </p>
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <span>Your accounts</span>
              <span>Your KPIs</span>
              <span>Real insights</span>
            </div>
          </button>
        </div>
      </div>

      {/* ================================================================ */}
      {/* DEMO PATH: Showcase Journey Preview                              */}
      {/* ================================================================ */}
      {onboardingMode === 'demo' && (
        <>
          {/* Demo Configuration Summary */}
          <div className="border rounded-lg p-5 bg-purple-50/50">
            <h4 className="font-medium mb-3 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-600" />
              Demo Configuration
            </h4>

            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <label className="text-xs font-medium text-gray-500">Company</label>
                <div className="mt-1 px-3 py-2 bg-white border border-gray-200 rounded-md text-sm text-gray-700">
                  {businessContext?.company_name || 'Demo Company'}
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500">Customer ID</label>
                <div className="mt-1 px-3 py-2 bg-white border border-gray-200 rounded-md text-sm text-gray-700">
                  {customerId || 'Loading...'}
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500">Account IDs</label>
                <div className="mt-1 px-3 py-2 bg-white border border-gray-200 rounded-md text-sm text-gray-700">
                  {accountIdRange ? `${accountIdRange.start} - ${accountIdRange.end}` : 'Auto-assigned'}
                </div>
              </div>
            </div>

            <div className="p-3 bg-white border border-purple-200 rounded-lg mb-4">
              <p className="text-sm text-gray-700 mb-1 font-medium">What gets generated:</p>
              <ul className="text-xs text-gray-600 space-y-1">
                <li>- <strong>10 accounts</strong> with 12 months of KPI data (15 KPIs across 5 pillars)</li>
                <li>- <strong>Qualitative signals</strong> (emails, QBR notes, escalations, milestones)</li>
                <li>- <strong>Journey patterns</strong> demonstrating crisis recovery, churn risk, expansion, and steady-state</li>
                <li>- <strong>CSM action tracking</strong> with response times, costs, and business impact</li>
              </ul>
            </div>
          </div>

          {/* Showcase Journey Patterns */}
          <div>
            <h4 className="font-medium mb-3 flex items-center gap-2">
              <Play className="w-5 h-5 text-purple-600" />
              Showcase Journey Patterns
            </h4>
            <p className="text-sm text-gray-600 mb-3">
              These journey patterns demonstrate the core value proposition - how proactive CSM intervention saves accounts and drives growth.
            </p>

            <div className="grid grid-cols-2 gap-3">
              {SHOWCASE_JOURNEYS.map((journey) => (
                <div key={journey.pattern} className={`border rounded-lg p-4 ${journey.color}`}>
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5">{journey.icon}</div>
                    <div>
                      <h5 className="font-medium text-sm text-gray-900">{journey.name}</h5>
                      <p className="text-xs text-gray-600 mt-1">{journey.description}</p>
                      <div className="mt-2 flex items-center gap-1">
                        <span className="text-xs font-mono text-gray-500">Health: {journey.healthArc}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-xs text-amber-800">
                <strong>Core Value Prop:</strong> The platform shows how proactive intervention in the "Crisis to Recovery"
                scenario saves the account and drives 40% ARR expansion, while the "Ignored Signals" scenario shows the
                cost of inaction. This is the "before/after" that resonates with CS leaders.
              </p>
            </div>
          </div>
        </>
      )}

      {/* ================================================================ */}
      {/* CUSTOM PATH: CSV Upload Interface                                */}
      {/* ================================================================ */}
      {onboardingMode === 'custom' && (
        <>
          {/* Header */}
          <div>
            <h4 className="font-medium mb-1 flex items-center gap-2">
              <Upload className="w-5 h-5" />
              Data File Uploads
            </h4>
            <p className="text-sm text-gray-600">
              Upload CSV files with your account and KPI data. Download templates to see the expected format.
            </p>
          </div>

          {/* File Uploads */}
          <div>
            <div className="space-y-3">
              {fileSources.map((source) => {
                const csvFormat = getCSVFormat(source.id);
                return (
                  <div key={source.id} className="border rounded-lg p-4 bg-white">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3 flex-1">
                        {source.status === 'uploaded' ? (
                          <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
                        ) : source.status === 'error' ? (
                          <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" />
                        ) : source.status === 'validating' ? (
                          <Loader className="w-5 h-5 text-blue-500 animate-spin mt-0.5" />
                        ) : source.status === 'skipped' ? (
                          <X className="w-5 h-5 text-gray-400 mt-0.5" />
                        ) : (
                          <div className="w-5 h-5 border-2 border-gray-300 rounded mt-0.5" />
                        )}
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-medium">{source.name}</p>
                            {(source.id === 'accounts' || source.id === 'kpis') && (
                              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">Required</span>
                            )}
                          </div>

                          {/* CSV Format Info */}
                          {csvFormat && (
                            <div className="mt-2">
                              <div className="flex items-center gap-2 mb-1">
                                <FileText className="w-3 h-3 text-gray-500" />
                                <span className="text-xs font-medium text-gray-700">Format: {csvFormat.filename}</span>
                                <button
                                  onClick={() => setShowFormatInfo(showFormatInfo === source.id ? null : source.id)}
                                  className="text-xs text-blue-600 hover:text-blue-800"
                                >
                                  {showFormatInfo === source.id ? 'Hide format' : 'Show format'}
                                </button>
                              </div>

                              {showFormatInfo === source.id && (
                                <div className="mt-2 p-3 bg-blue-50 rounded-lg border border-blue-200">
                                  <p className="text-xs text-gray-700 mb-2">{csvFormat.description}</p>
                                  <div className="text-xs">
                                    <p className="font-medium text-gray-900 mb-1">Required columns:</p>
                                    <p className="text-gray-600 font-mono">{csvFormat.required_columns.join(', ')}</p>
                                    {csvFormat.optional_columns.length > 0 && (
                                      <>
                                        <p className="font-medium text-gray-900 mt-2 mb-1">Optional columns:</p>
                                        <p className="text-gray-600 font-mono">{csvFormat.optional_columns.join(', ')}</p>
                                      </>
                                    )}
                                  </div>
                                  <button
                                    onClick={() => {
                                      if (source.id === 'accounts') handleDownloadTemplate('accounts');
                                      else if (source.id === 'kpis') handleDownloadTemplate('kpis');
                                      else if (source.id === 'signals' || source.id === 'qualitative_signals' || source.id === 'enhanced_signals') handleDownloadTemplate('enhanced_signals');
                                      else if (source.id === 'products') handleDownloadTemplate('products');
                                    }}
                                    className="mt-2 text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                                  >
                                    <Download className="w-3 h-3" />
                                    Download template CSV
                                  </button>
                                </div>
                              )}
                            </div>
                          )}

                          {source.status === 'uploaded' && source.filename && (
                            <p className="text-xs text-gray-500 mt-1">{source.filename} - {source.rows} rows</p>
                          )}
                          {source.validation && (
                            <div className="mt-2">
                              {source.validation.errors.map((error, i) => (
                                <p key={i} className="text-xs text-red-600">Warning: {error}</p>
                              ))}
                              {source.validation.warnings.map((warning, i) => (
                                <p key={i} className="text-xs text-yellow-600">Info: {warning}</p>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {source.status === 'uploaded' && source.preview && (
                          <button
                            onClick={() => setPreviewSource(previewSource === source.id ? null : source.id)}
                            className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200 flex items-center gap-1"
                          >
                            <Eye className="w-4 h-4" />
                            Preview
                          </button>
                        )}
                        {source.status !== 'uploaded' && source.status !== 'validating' && (
                          <>
                            <label className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700 flex items-center gap-1">
                              <Upload className="w-4 h-4" />
                              Upload {csvFormat?.filename || 'File'}
                              <input
                                type="file"
                                accept=".csv"
                                className="hidden"
                                onChange={(e) => {
                                  if (e.target.files?.[0]) {
                                    handleFileUpload(source.id, e.target.files[0]);
                                  }
                                }}
                              />
                            </label>
                            {source.id !== 'accounts' && source.id !== 'kpis' && (
                              <button
                                onClick={() => handleSkip(source.id)}
                                className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-200 rounded"
                              >
                                Skip
                              </button>
                            )}
                          </>
                        )}
                        {source.status === 'uploaded' && (
                          <span className="text-sm text-green-600 font-medium">Uploaded</span>
                        )}
                        {source.status === 'validating' && (
                          <span className="text-sm text-blue-600">Validating...</span>
                        )}
                      </div>
                    </div>
                    {/* Preview Table */}
                    {previewSource === source.id && source.preview && (
                      <div className="mt-4 border rounded-lg overflow-hidden">
                        <div className="bg-gray-50 px-4 py-2 text-sm font-medium border-b">
                          Preview (first 5 rows)
                        </div>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead className="bg-gray-100">
                              <tr>
                                {Object.keys(source.preview[0] || {}).map((key) => (
                                  <th key={key} className="px-3 py-2 text-left border-b">
                                    {key}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {source.preview.map((row, i) => (
                                <tr key={i} className="border-b">
                                  {Object.values(row).map((cell, j) => (
                                    <td key={j} className="px-3 py-2">
                                      {String(cell)}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* API Connections */}
          <div className="border-t pt-6">
            <h4 className="font-medium mb-3 flex items-center gap-2">
              <Link className="w-5 h-5" />
              API Connections (Optional)
            </h4>
            <div className="space-y-2">
              {apiSources.map((source) => (
                <div key={source.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1">
                      {source.status === 'connected' ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : source.status === 'error' ? (
                        <AlertCircle className="w-5 h-5 text-red-500" />
                      ) : source.status === 'validating' ? (
                        <Loader className="w-5 h-5 text-blue-500 animate-spin" />
                      ) : source.status === 'skipped' ? (
                        <X className="w-5 h-5 text-gray-400" />
                      ) : (
                        <div className="w-5 h-5 border-2 border-gray-300 rounded" />
                      )}
                      <p className="font-medium">{source.name}</p>
                      {source.validation && source.validation.errors.length > 0 && (
                        <p className="text-xs text-red-600">{source.validation.errors[0]}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {source.status === 'pending' && (
                        <>
                          <button
                            onClick={() => setApiConfigSource(apiConfigSource === source.id ? null : source.id)}
                            className="px-3 py-1.5 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                          >
                            Configure
                          </button>
                          <button
                            onClick={() => handleSkip(source.id)}
                            className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-200 rounded"
                          >
                            Skip
                          </button>
                        </>
                      )}
                      {source.status === 'connected' && (
                        <span className="text-sm text-green-600">Connected</span>
                      )}
                      {source.status === 'validating' && (
                        <span className="text-sm text-blue-600">Testing...</span>
                      )}
                    </div>
                  </div>
                  {/* API Configuration Form */}
                  {apiConfigSource === source.id && (
                    <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-3">
                      <div>
                        <label className="block text-sm font-medium mb-1">API Endpoint *</label>
                        <input
                          type="text"
                          value={source.api_config?.endpoint || ''}
                          onChange={(e) => {
                            const newData = data.map((s) =>
                              s.id === source.id
                                ? {
                                    ...s,
                                    api_config: {
                                      ...s.api_config,
                                      endpoint: e.target.value,
                                      auth_type: s.api_config?.auth_type || 'api_key'
                                    }
                                  }
                                : s
                            );
                            onChange(newData);
                          }}
                          className="w-full px-3 py-2 border rounded-lg text-sm"
                          placeholder="https://api.example.com/v1"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">API Key *</label>
                        <input
                          type="password"
                          value={source.api_config?.api_key || ''}
                          onChange={(e) => {
                            const newData = data.map((s) =>
                              s.id === source.id
                                ? {
                                    ...s,
                                    api_config: { ...s.api_config, api_key: e.target.value }
                                  }
                                : s
                            );
                            onChange(newData);
                          }}
                          className="w-full px-3 py-2 border rounded-lg text-sm"
                          placeholder="Enter your API key"
                        />
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleConnectAPI(source.id)}
                          disabled={!source.api_config?.endpoint || !source.api_config?.api_key}
                          className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                        >
                          Test Connection
                        </button>
                        <button
                          onClick={() => setApiConfigSource(null)}
                          className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
