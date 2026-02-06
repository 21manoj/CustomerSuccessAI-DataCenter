/**
 * Step 5: Data Sources with Validation and Preview
 * Enhanced with specific CSV format guidance and synthetic file generation
 */

import React, { useState, useEffect } from 'react';
import { Upload, Link, CheckCircle, X, Eye, AlertCircle, Loader, Download, Sparkles, FileText, Info } from 'lucide-react';
import { DataSource } from './OnboardingWizard.types';
import { validateCSV, previewCSV, testAPIConnection } from './OnboardingWizard.utils';

interface Step5SourcesProps {
  data: DataSource[];
  onChange: (data: DataSource[]) => void;
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
  signals: {
    filename: 'qualitative_signals.csv',
    required_columns: ['account_id', 'account_name', 'date', 'signal_type', 'summary', 'sentiment'],
    optional_columns: ['from_contact', 'to_contact', 'subject', 'keywords'],
    description: 'Qualitative signals from emails, meetings, support tickets, etc.'
  },
  products: {
    filename: 'products.csv',
    required_columns: ['id', 'name', 'category'],
    optional_columns: ['description', 'pricing_tier', 'features'],
    description: 'Product catalog with product IDs, names, and categories'
  },
  profiles: {
    filename: 'profiles.csv',
    required_columns: ['account_id', 'account_name', 'health_score', 'lifecycle_stage'],
    optional_columns: ['csm_name', 'arr', 'num_licenses', 'deployment_type', 'data_center_size', 'industry', 'use_case', 'primary_product'],
    description: 'Comprehensive account profiles with health scores, lifecycle stage, and business metrics'
  }
};

export const Step5Sources: React.FC<Step5SourcesProps> = ({ data, onChange, businessContext }) => {
  const [previewSource, setPreviewSource] = useState<string | null>(null);
  const [apiConfigSource, setApiConfigSource] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [showFormatInfo, setShowFormatInfo] = useState<string | null>(null);
  const [customerId, setCustomerId] = useState<string>('');
  const [showConfirmation, setShowConfirmation] = useState(false);
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

  const handleGenerateSampleFiles = () => {
    // Validate customer ID before showing confirmation (read-only, system-generated)
    if (!customerId) {
      alert('Please wait for Customer ID to be generated.');
      return;
    }
    setShowConfirmation(true);
  };

  const confirmGeneration = async () => {
    setShowConfirmation(false);
    setGenerating(true);
    try {
      const response = await fetch('/api/onboarding/generate-sample-files', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          customer_id: parseInt(customerId, 10),
          vertical: 'dc2_s',  // Fixed for Data Center
          industry: businessContext?.industry || 'Technology',
          company_name: businessContext?.company_name || 'Demo Customer',
          num_accounts: 10,
          num_months: 12  // Fixed to 12 months
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Failed to generate sample files' }));
        throw new Error(errorData.message || 'Failed to generate sample files');
      }

      // Download the ZIP file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `onboarding_sample_files_${new Date().toISOString().split('T')[0]}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      alert('✅ Sample files downloaded successfully!\n\n📋 Next steps:\n1. Extract the ZIP file\n2. Review DEMO_MANIFEST.md for demo scenarios\n3. Upload the CSV files using the buttons below');
    } catch (error: any) {
      console.error('Error generating sample files:', error);
      alert(`❌ Failed to generate sample files: ${error.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadTemplate = (fileType: 'accounts' | 'kpis' | 'signals' | 'products' | 'profiles') => {
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

  const getExampleRows = (fileType: 'accounts' | 'kpis' | 'signals' | 'products' | 'profiles'): string => {
    if (fileType === 'accounts') {
      return '10001,1,Example Account 1,500000,Technology,US-West,active,EXT-10001,"{""assigned_csm"": ""John Doe"", ""account_tier"": ""Enterprise""}"';
    } else if (fileType === 'kpis') {
      return '10001,Example Account 1,2024-01-01,P1-KPI1,System Uptime,P1,99.5,99.9,>,%';
    } else if (fileType === 'signals') {
      return '10001,Example Account 1,2024-01-15,email,customer@example.com,csm@example.com,Monthly check-in,positive';
    } else if (fileType === 'products') {
      return 'DC-GPU-H100,DGX H100 Systems,Compute\nDC-COOL-LQ,Liquid Cooling Solutions,Infrastructure';
    } else {
      return '10001,Example Account 1,Emily Watson,88,expansion,1900198.60,159,On-Premise,Small';
    }
  };

  const fileSources = data.filter((s) => s.type === 'file');
  const apiSources = data.filter((s) => s.type === 'api');

  // Map source IDs to CSV format specs
  const getCSVFormat = (sourceId: string) => {
    if (sourceId === 'accounts') return CSV_FORMATS.accounts;
    if (sourceId === 'kpis') return CSV_FORMATS.kpis;
    if (sourceId === 'signals' || sourceId === 'qualitative_signals') return CSV_FORMATS.signals;
    if (sourceId === 'products') return CSV_FORMATS.products;
    if (sourceId === 'profiles') return CSV_FORMATS.profiles;
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Sample Data Configuration Section */}
      <div className="border rounded-lg p-6 bg-gray-50">
        <h4 className="font-medium mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5" />
          Sample Data Configuration
        </h4>
        
        <div className="grid grid-cols-2 gap-4 mb-4">
          {/* Read-Only Fields */}
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-gray-500">Company Name</label>
              <div className="mt-1 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm text-gray-700">
                {businessContext?.company_name || 'Not set'}
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500">Industry</label>
              <div className="mt-1 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm text-gray-700">
                {businessContext?.industry || 'Not set'}
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500">Vertical</label>
              <div className="mt-1 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm text-gray-700">
                DC2_S (Data Center)
              </div>
            </div>
          </div>
          
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-gray-500">Time Period</label>
              <div className="mt-1 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm text-gray-700">
                12 months (fixed)
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500">Number of Accounts</label>
              <div className="mt-1 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm text-gray-700">
                10 accounts
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500">Customer ID</label>
              <div className="mt-1 px-3 py-2 bg-white border border-gray-300 rounded-md text-sm text-gray-700">
                {customerId || 'Loading...'}
              </div>
              {customerId && accountIdRange && (
                <div className="mt-1 text-xs text-gray-500">
                  Account IDs: {accountIdRange.start} - {accountIdRange.end}
                </div>
              )}
              {customerId && (
                <div className="mt-1 text-xs text-gray-400">
                  System-generated (read-only)
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="pt-4 border-t">
          <button
            onClick={handleGenerateSampleFiles}
            disabled={generating || !customerId}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {generating ? (
              <>
                <Loader className="w-4 h-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Generate Sample Files
              </>
            )}
          </button>
          <p className="mt-2 text-xs text-gray-500">
            Default pillar weights will be applied. You can adjust weights later in Settings.
          </p>
        </div>
      </div>

      {/* Confirmation Dialog */}
      {showConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Confirm Data Generation</h3>
            <p className="text-sm text-gray-600 mb-4">You're about to generate sample data with:</p>
            <ul className="space-y-2 text-sm mb-4">
              <li><strong>Company:</strong> {businessContext?.company_name || 'Demo Customer'}</li>
              <li><strong>Industry:</strong> {businessContext?.industry || 'Technology'}</li>
              <li><strong>Customer ID:</strong> {customerId} (system-generated)</li>
              {accountIdRange && (
                <li><strong>Account IDs:</strong> {accountIdRange.start} - {accountIdRange.end}</li>
              )}
              <li><strong>Accounts:</strong> 10 with varied journey scenarios</li>
              <li><strong>Time Period:</strong> 12 months (Jan 2024 - Dec 2024)</li>
            </ul>
            <div className="p-3 bg-blue-50 border border-blue-200 rounded text-xs text-blue-800 mb-4">
              Default pillar weights will be applied. You can adjust weights later in Settings.
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirmation(false)}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmGeneration}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
              >
                Generate
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div>
        <h4 className="font-medium mb-1 flex items-center gap-2">
          <Upload className="w-5 h-5" />
          Data File Uploads
        </h4>
        <p className="text-sm text-gray-600">
          Upload CSV files with your account and KPI data. You can generate sample files to see the expected format.
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
                        {source.id === 'accounts' && (
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
                                  else if (source.id === 'signals' || source.id === 'qualitative_signals') handleDownloadTemplate('signals');
                                  else if (source.id === 'products') handleDownloadTemplate('products');
                                  else if (source.id === 'profiles') handleDownloadTemplate('profiles');
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
                        <p className="text-xs text-gray-500 mt-1">{source.filename} • {source.rows} rows</p>
                      )}
                      {source.validation && (
                        <div className="mt-2">
                          {source.validation.errors.map((error, i) => (
                            <p key={i} className="text-xs text-red-600">⚠️ {error}</p>
                          ))}
                          {source.validation.warnings.map((warning, i) => (
                            <p key={i} className="text-xs text-yellow-600">ℹ️ {warning}</p>
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
                        {source.id !== 'accounts' && (
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
                      <span className="text-sm text-green-600 font-medium">✓ Uploaded</span>
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
                    <span className="text-sm text-green-600">✓ Connected</span>
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
    </div>
  );
};

