/**
 * Data Center Data Integration Tab
 * =================================
 * 
 * Main component for data upload and management:
 * - Upload Data (drag-drop CSV/XLSX)
 * - Upload History
 * - Templates download
 * - Journey-aware post-upload prompt
 */

import React, { useState, useEffect } from 'react';
import { useSession } from '../../../contexts/SessionContext';
import { useEntitlements } from '../../../hooks/useEntitlement';
import {
  Upload,
  FileText,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Download,
  Calendar,
  X,
  Play,
  Eye,
  ChevronDown,
  ChevronRight,
  Sparkles,
  HelpCircle,
} from 'lucide-react';

// ============================================================
// TYPES
// ============================================================

type UploadMode = 'full_refresh' | 'incremental' | 'upsert' | 'merge';
type SubTab = 'upload' | 'history' | 'templates';
type FileType = 'accounts' | 'kpis' | 'enhanced_signals' | 'products'
  | 'stakeholders' | 'engagement_events' | 'account_business_profiles'
  | 'outcomes' | 'decisions' | 'signal_edges' | 'industry_benchmarks';

interface UploadHistoryItem {
  upload_id: number;
  file_name: string;
  upload_mode: string;
  status: string;
  uploaded_at: string;
  records_count?: number;
}

// ============================================================
// MAIN COMPONENT
// ============================================================

/** Auto-detect file type from CSV headers */
function detectFileType(headers: string[]): FileType | null {
  const headerSet = new Set(headers.map(h => h.toLowerCase().trim()));
  if (headerSet.has('account_id') && (headerSet.has('arr') || headerSet.has('account_name'))) return 'accounts';
  if (headerSet.has('kpi_code') && (headerSet.has('raw_value') || headerSet.has('kpi_id'))) return 'kpis';
  if ((headerSet.has('signal_type') || headerSet.has('signal_category')) && headerSet.has('description')) return 'signals';
  if (headerSet.has('product_id') || headerSet.has('product_name')) return 'products';
  if (headerSet.has('industry') && headerSet.has('employee_count')) return 'profiles';
  if (headerSet.has('stakeholder_id') || headerSet.has('stakeholder_name')) return 'stakeholders';
  if (headerSet.has('engagement_type') || headerSet.has('event_type')) return 'engagement_events';
  return null;
}

/** Starter-friendly file type labels */
const STARTER_FILE_LABELS: Record<string, { label: string; description: string }> = {
  accounts: { label: 'Account List', description: 'Your customer/account list with names and revenue' },
  kpis: { label: 'KPI Measurements', description: 'Health metric values for each account' },
  signals: { label: 'Notes & Signals', description: 'Qualitative notes, meeting summaries, risk flags' },
};

const DCDataIntegration: React.FC = () => {
  const { session } = useSession();
  const { tier } = useEntitlements();
  const isStarter = tier === 'starter';
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('upload');
  const [uploadMode, setUploadMode] = useState<UploadMode>('incremental');
  const [selectedFileType, setSelectedFileType] = useState<FileType | ''>('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [showWizardPrompt, setShowWizardPrompt] = useState(false);
  const [uploadHistory, setUploadHistory] = useState<UploadHistoryItem[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [viewModal, setViewModal] = useState<{ filename: string; content: string } | null>(null);
  // Starter: show advanced file types toggle
  const [showAdvancedTypes, setShowAdvancedTypes] = useState(false);
  // Auto-detected file type
  const [autoDetectedType, setAutoDetectedType] = useState<FileType | null>(null);

  useEffect(() => {
    if (activeSubTab === 'history') {
      fetchUploadHistory();
    }
  }, [activeSubTab]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  /** Try to auto-detect file type from a CSV file's headers */
  const tryAutoDetect = (file: File) => {
    if (!file.name.endsWith('.csv')) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      if (!text) return;
      const firstLine = text.split('\n')[0];
      if (!firstLine) return;
      const headers = firstLine.split(',');
      const detected = detectFileType(headers);
      if (detected) {
        setAutoDetectedType(detected);
        if (!selectedFileType) {
          setSelectedFileType(detected);
        }
      }
    };
    reader.readAsText(file.slice(0, 2048)); // Read only first 2KB
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files);
      setSelectedFiles(files);
      // Auto-detect from first file
      if (files[0]) tryAutoDetect(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      setSelectedFiles(files);
      if (files[0]) tryAutoDetect(files[0]);
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      alert('Please select at least one file');
      return;
    }

    if (!selectedFileType) {
      alert('Please select a file type');
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setUploadResult(null);
    setShowWizardPrompt(false);

    try {
      // Upload files one by one (API expects one file at a time)
      const results = [];
      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('file_type', selectedFileType);
        formData.append('upload_mode', uploadMode);

        const response = await fetch('/api/onboarding/upload', {
          method: 'POST',
          credentials: 'include',
          body: formData,
        });
        
        const data = await response.json();
        results.push({ file: file.name, success: response.ok, data });
        
        // Update progress
        setUploadProgress(Math.round(((i + 1) / selectedFiles.length) * 100));
      }

      // Check if all uploads succeeded
      const allSuccess = results.every(r => r.success);
      const failedUploads = results.filter(r => !r.success);
      
      if (allSuccess) {
        setUploadResult({
          success: true,
          message: `Successfully uploaded ${results.length} file(s)`,
          accounts: results[0]?.data?.accounts_processed || 0,
          kpis: results[0]?.data?.kpis_processed || 0,
        });
        setShowWizardPrompt(true);
        setSelectedFiles([]);
        setSelectedFileType('');
        setUploadProgress(100);
      } else {
        const errorMessages = failedUploads.map(r => 
          `${r.file}: ${r.data?.message || r.data?.error || 'Upload failed'}`
        ).join('\n');
        setUploadResult({
          success: false,
          message: `Some uploads failed:\n${errorMessages}`,
        });
      }
    } catch (err: any) {
      console.error('Upload error:', err);
      setUploadResult({
        success: false,
        message: err.message || 'Upload failed',
      });
    } finally {
      setUploading(false);
      setTimeout(() => setUploadProgress(0), 2000);
    }
  };

  const fetchUploadHistory = async () => {
    try {
      // TODO: Replace with actual API endpoint: GET /api/data/upload-history
      // For now, use mock data
      const mockHistory: UploadHistoryItem[] = [
        {
          upload_id: 1,
          file_name: 'accounts.csv',
          upload_mode: 'incremental',
          status: 'completed',
          uploaded_at: new Date().toISOString(),
          records_count: 30,
        },
        {
          upload_id: 2,
          file_name: 'kpis.csv',
          upload_mode: 'upsert',
          status: 'completed',
          uploaded_at: new Date(Date.now() - 86400000).toISOString(),
          records_count: 11700,
        },
      ];
      setUploadHistory(mockHistory);
    } catch (err) {
      console.error('Error fetching upload history:', err);
    }
  };

  const handleTriggerWizardA = async () => {
    try {
      setShowWizardPrompt(false);
      
      const response = await fetch('/api/data/trigger-wizard-a', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to trigger Wizard A');
      }
      
      alert(`✅ ${data.message}\n\nDuration: ${data.duration_seconds}s`);
      // Optionally refresh data or reload page
      window.location.reload();
    } catch (err) {
      console.error('Error triggering Wizard A:', err);
      alert(`Failed to trigger Wizard A: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">{isStarter ? 'Upload Data' : 'Data Integration'}</h2>
        <p className="text-sm text-gray-500 mt-1">
          {isStarter ? 'Upload your CSV files to populate health scores' : 'Upload and manage your data files'}
        </p>
      </div>

      {/* Sub-tabs */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <nav className="flex space-x-8 px-6 border-b border-gray-200">
          {[
            { id: 'upload' as SubTab, label: 'Upload Data' },
            { id: 'history' as SubTab, label: 'Upload History' },
            { id: 'templates' as SubTab, label: 'Templates' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeSubTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Sub-tab Content */}
        <div className="p-6">
          {/* Upload Tab */}
          {activeSubTab === 'upload' && (
            <div className="space-y-6">
              {/* File Type Selector */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                {/* Auto-detect banner */}
                {autoDetectedType && selectedFileType === autoDetectedType && (
                  <div className="mb-3 flex items-center space-x-2 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
                    <Sparkles className="h-4 w-4 text-blue-500" />
                    <span className="text-sm text-blue-700">
                      We detected this as <strong>{STARTER_FILE_LABELS[autoDetectedType]?.label || autoDetectedType}</strong>.
                    </span>
                    <button
                      onClick={() => { setAutoDetectedType(null); setSelectedFileType(''); }}
                      className="text-xs text-blue-500 hover:text-blue-700 underline ml-auto"
                    >
                      Change
                    </button>
                  </div>
                )}

                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {isStarter ? 'What are you uploading?' : 'Select File Type'} <span className="text-red-500">*</span>
                </label>
                <select
                  value={selectedFileType}
                  onChange={(e) => { setSelectedFileType(e.target.value as FileType); setAutoDetectedType(null); }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">-- Select file type --</option>
                  {isStarter && !showAdvancedTypes ? (
                    <>
                      <option value="accounts">Account List (accounts.csv)</option>
                      <option value="kpis">KPI Measurements (kpi_measurements.csv)</option>
                      <option value="enhanced_signals">Signals (enhanced_qualitative_signals.csv)</option>
                    </>
                  ) : (
                    <>
                      <optgroup label="Core Data (4 files)">
                        <option value="accounts">{isStarter ? 'Account List' : 'Accounts'} (accounts.csv)</option>
                        <option value="kpis">{isStarter ? 'KPI Measurements' : 'KPIs'} (kpi_measurements.csv)</option>
                        <option value="enhanced_signals">Signals (enhanced_qualitative_signals.csv)</option>
                        <option value="products">Products (products.csv)</option>
                      </optgroup>
                      <optgroup label="Context Graph — Customer Provided (4 files)">
                        <option value="stakeholders">Stakeholders (stakeholders.csv)</option>
                        <option value="engagement_events">Engagement Events (engagement_events.csv)</option>
                        <option value="account_business_profiles">Business Profiles &amp; CSM Info (account_business_profiles.csv)</option>
                        <option value="outcomes">Outcomes (outcomes.csv)</option>
                      </optgroup>
                      <optgroup label="Context Graph — Auto-generated (2 files)">
                        <option value="decisions">Decisions (decisions.csv)</option>
                        <option value="signal_edges">Signal Edges (signal_edges.csv)</option>
                      </optgroup>
                      <optgroup label="Context Graph — Platform-curated (1 file)">
                        <option value="industry_benchmarks">Industry Benchmarks (industry_benchmarks.csv)</option>
                      </optgroup>
                    </>
                  )}
                </select>
                {isStarter && !showAdvancedTypes && (
                  <button
                    onClick={() => setShowAdvancedTypes(true)}
                    className="flex items-center text-xs text-gray-400 hover:text-gray-600 mt-2 transition-colors"
                  >
                    <ChevronRight className="h-3 w-3 mr-1" /> Show Advanced Types
                  </button>
                )}
                {isStarter && showAdvancedTypes && (
                  <button
                    onClick={() => setShowAdvancedTypes(false)}
                    className="flex items-center text-xs text-gray-400 hover:text-gray-600 mt-2 transition-colors"
                  >
                    <ChevronDown className="h-3 w-3 mr-1" /> Show Fewer Types
                  </button>
                )}
                <p className="text-xs text-gray-500 mt-2">
                  {isStarter
                    ? "Not sure which to pick? Start with Account List \u2014 it's the foundation for everything else."
                    : 'Choose the type of data file you\'re uploading'}
                </p>
              </div>

              {/* Drag & Drop Zone */}
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
                  dragActive
                    ? 'border-blue-500 bg-blue-50'
                    : selectedFileType
                    ? 'border-gray-300 bg-gray-50 hover:border-gray-400'
                    : 'border-gray-200 bg-gray-50 opacity-50 cursor-not-allowed'
                }`}
              >
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-lg font-medium text-gray-900 mb-2">
                  Drag & drop CSV/XLSX files here
                </p>
                <p className="text-sm text-gray-500 mb-4">
                  or click to browse
                </p>
                <p className="text-xs text-gray-400 mb-4">
                  Core: accounts.csv, kpi_measurements.csv, enhanced_qualitative_signals.csv, products.csv
                </p>
                {selectedFileType && (
                  <p className="text-xs text-blue-600 mb-4 font-medium">
                    Selected type: {selectedFileType}
                  </p>
                )}
                <input
                  type="file"
                  multiple
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileSelect}
                  disabled={!selectedFileType}
                  className="hidden"
                  id="file-upload"
                />
                <label
                  htmlFor="file-upload"
                  className={`inline-block px-4 py-2 rounded-lg cursor-pointer ${
                    selectedFileType
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  }`}
                >
                  {selectedFileType ? `Select ${selectedFileType} File(s)` : 'Select File Type First'}
                </label>
              </div>

              {/* Selected Files */}
              {selectedFiles.length > 0 && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    Selected Files ({selectedFiles.length})
                  </p>
                  <div className="space-y-2">
                    {selectedFiles.map((file, index) => (
                      <div key={index} className="flex items-center justify-between bg-white p-2 rounded">
                        <div className="flex items-center space-x-2">
                          <FileText className="w-4 h-4 text-gray-400" />
                          <span className="text-sm text-gray-700">{file.name}</span>
                          <span className="text-xs text-gray-500">
                            ({(file.size / 1024).toFixed(1)} KB)
                          </span>
                        </div>
                        <button
                          onClick={() => setSelectedFiles(selectedFiles.filter((_, i) => i !== index))}
                          className="text-gray-400 hover:text-red-600"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Upload Mode Selector */}
              <div className="bg-white border border-gray-200 rounded-lg p-4">
                <p className="text-sm font-medium text-gray-700 mb-3">Upload Mode</p>
                <div className="space-y-2">
                  {[
                    { value: 'full_refresh' as UploadMode, label: 'Full Refresh', desc: 'Replace all existing data' },
                    { value: 'incremental' as UploadMode, label: 'Incremental', desc: 'Append/update existing data' },
                    { value: 'upsert' as UploadMode, label: 'Upsert', desc: 'Add new, update existing (by account_id)' },
                    { value: 'merge' as UploadMode, label: 'Merge', desc: 'Smart merge with conflict resolution' },
                  ].map(mode => (
                    <label key={mode.value} className="flex items-start space-x-3 cursor-pointer">
                      <input
                        type="radio"
                        name="upload_mode"
                        value={mode.value}
                        checked={uploadMode === mode.value}
                        onChange={() => setUploadMode(mode.value)}
                        className="mt-1"
                      />
                      <div>
                        <p className="text-sm font-medium text-gray-900">{mode.label}</p>
                        <p className="text-xs text-gray-500">{mode.desc}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Upload Progress */}
              {uploading && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-blue-900">Uploading...</span>
                    <span className="text-sm text-blue-700">{uploadProgress}%</span>
                  </div>
                  <div className="w-full bg-blue-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Upload Result */}
              {uploadResult && (
                <div className={`rounded-lg p-4 ${
                  uploadResult.success
                    ? 'bg-green-50 border border-green-200'
                    : 'bg-red-50 border border-red-200'
                }`}>
                  <div className="flex items-start space-x-3">
                    {uploadResult.success ? (
                      <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <p className={`font-medium ${
                        uploadResult.success ? 'text-green-900' : 'text-red-900'
                      }`}>
                        {uploadResult.success && isStarter
                          ? `Data uploaded! Your health scores will appear in ${isStarter ? 'Accounts' : 'Tenants'}.`
                          : uploadResult.message}
                      </p>
                      {uploadResult.success && uploadResult.accounts !== undefined && (
                        <p className="text-sm text-green-700 mt-1">
                          Accounts: {uploadResult.accounts} {uploadResult.kpis ? `\u2022 KPIs: ${uploadResult.kpis}` : ''}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Journey-Aware Prompt */}
              {showWizardPrompt && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
                  <div className="flex items-start space-x-3 mb-4">
                    <AlertTriangle className="w-6 h-6 text-yellow-600 flex-shrink-0" />
                    <div className="flex-1">
                      <h3 className="font-semibold text-yellow-900 mb-2">
                        Journey Update Required
                      </h3>
                      <p className="text-sm text-yellow-800 mb-4">
                        New data has been staged. To incorporate into journey timelines and health scores, you need to run Wizard A.
                      </p>
                      <div className="flex space-x-3">
                        <button
                          onClick={handleTriggerWizardA}
                          className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 flex items-center space-x-2"
                        >
                          <Play className="w-4 h-4" />
                          <span>Run Wizard A (Recommended)</span>
                        </button>
                        <button
                          onClick={() => setShowWizardPrompt(false)}
                          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                        >
                          Skip for Now
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Upload Button */}
              <button
                onClick={handleUpload}
                disabled={selectedFiles.length === 0 || !selectedFileType || uploading}
                className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
              >
                {uploading ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    <span>Uploading...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-5 h-5" />
                    <span>Validate & Upload</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* History Tab */}
          {activeSubTab === 'history' && (
            <div className="space-y-4">
              {uploadHistory.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p>No upload history found</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">File Name</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Mode</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Status</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Records</th>
                        <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Uploaded</th>
                      </tr>
                    </thead>
                    <tbody>
                      {uploadHistory.map((item) => (
                        <tr key={item.upload_id} className="border-b border-gray-100 hover:bg-gray-50">
                          <td className="py-3 px-4 text-sm text-gray-900">{item.file_name}</td>
                          <td className="py-3 px-4 text-sm text-gray-600 capitalize">{item.upload_mode}</td>
                          <td className="py-3 px-4">
                            <span className={`text-xs px-2 py-1 rounded-full ${
                              item.status === 'completed'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-yellow-100 text-yellow-800'
                            }`}>
                              {item.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-sm text-gray-600">
                            {item.records_count?.toLocaleString() || 'N/A'}
                          </td>
                          <td className="py-3 px-4 text-sm text-gray-600">
                            {new Date(item.uploaded_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Templates Tab */}
          {activeSubTab === 'templates' && (
            <div className="space-y-6">
              <div>
                <h4 className="text-sm font-semibold text-gray-900 mb-1">Core Data Templates</h4>
                <p className="text-xs text-gray-500 mb-3">
                  Standard CSV templates for accounts, KPIs, signals, and profiles
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[
                    { type: 'accounts', name: 'accounts.csv', desc: 'Account information template' },
                    { type: 'kpis', name: 'kpi_measurements.csv', desc: 'KPI measurements template' },
                    { type: 'enhanced_signals', name: 'enhanced_qualitative_signals.csv', desc: 'Qualitative signals template' },
                    { type: 'products', name: 'products.csv', desc: 'Product catalog template' },
                  ].map((template) => {
                  const handleDownload = async () => {
                    try {
                      const response = await fetch(`/api/onboarding/templates/${template.type}`, {
                        credentials: 'include',
                      });

                      if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = template.name;
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                      } else {
                        const error = await response.json();
                        alert(`Failed to download template: ${error.message || 'Unknown error'}`);
                      }
                    } catch (err) {
                      console.error('Download error:', err);
                      alert('Failed to download template. Please try again.');
                    }
                  };

                  const handleView = async () => {
                    try {
                      const response = await fetch(`/api/onboarding/templates/${template.type}?view=true`, {
                        credentials: 'include',
                      });
                      if (response.ok) {
                        const data = await response.json();
                        setViewModal({ filename: template.name, content: data.content });
                      } else {
                        const error = await response.json();
                        alert(`Failed to view template: ${error.message || 'Unknown error'}`);
                      }
                    } catch (err) {
                      console.error('View error:', err);
                      alert('Failed to view template. Please try again.');
                    }
                  };

                  return (
                    <div key={template.type} className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <FileText className="w-5 h-5 text-gray-400" />
                        <div className="flex items-center gap-2">
                          <button
                            onClick={handleView}
                            className="text-gray-500 hover:text-blue-600 transition-colors"
                            title={`View ${template.name}`}
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={handleDownload}
                            className="text-blue-600 hover:text-blue-700 transition-colors"
                            title={`Download ${template.name}`}
                          >
                            <Download className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      <p className="text-sm font-medium text-gray-900">{template.name}</p>
                      <p className="text-xs text-gray-500 mt-1">{template.desc}</p>
                    </div>
                  );
                })}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-gray-900 mb-1">Context Graph Templates</h4>
                <p className="text-xs text-gray-500 mb-3">
                  Templates for stakeholders, decisions, outcomes, and signal relationships used by Revenue Intelligence
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[
                    { type: 'stakeholders', name: 'stakeholders.csv', desc: 'Stakeholder nodes — name, title, role, influence' },
                    { type: 'engagement_events', name: 'engagement_events.csv', desc: 'Engagement signals — meetings, calls, escalations' },
                    { type: 'account_business_profiles', name: 'account_business_profiles.csv', desc: 'Account context, CSM assignments, champion info' },
                    { type: 'outcomes', name: 'outcomes.csv', desc: 'Revenue outcomes — type, value, status' },
                  ].map((template) => {
                    const handleDownload = async () => {
                      try {
                        const response = await fetch(`/api/onboarding/templates/${template.type}`, {
                          credentials: 'include',
                        });

                        if (response.ok) {
                          const blob = await response.blob();
                          const url = window.URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = template.name;
                          document.body.appendChild(a);
                          a.click();
                          window.URL.revokeObjectURL(url);
                          document.body.removeChild(a);
                        } else {
                          const error = await response.json();
                          alert(`Failed to download template: ${error.message || 'Unknown error'}`);
                        }
                      } catch (err) {
                        console.error('Download error:', err);
                        alert('Failed to download template. Please try again.');
                      }
                    };

                    const handleView = async () => {
                      try {
                        const response = await fetch(`/api/onboarding/templates/${template.type}?view=true`, {
                          credentials: 'include',
                        });
                        if (response.ok) {
                          const data = await response.json();
                          setViewModal({ filename: template.name, content: data.content });
                        } else {
                          const error = await response.json();
                          alert(`Failed to view template: ${error.message || 'Unknown error'}`);
                        }
                      } catch (err) {
                        console.error('View error:', err);
                        alert('Failed to view template. Please try again.');
                      }
                    };

                    return (
                      <div key={template.type} className="border border-purple-200 rounded-lg p-4 hover:border-purple-400 transition-colors bg-purple-50/30">
                        <div className="flex items-center justify-between mb-2">
                          <FileText className="w-5 h-5 text-purple-400" />
                          <div className="flex items-center gap-2">
                            <button
                              onClick={handleView}
                              className="text-gray-500 hover:text-purple-600 transition-colors"
                              title={`View ${template.name}`}
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            <button
                              onClick={handleDownload}
                              className="text-purple-600 hover:text-purple-700 transition-colors"
                              title={`Download ${template.name}`}
                            >
                              <Download className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                        <p className="text-sm font-medium text-gray-900">{template.name}</p>
                        <p className="text-xs text-gray-500 mt-1">{template.desc}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Template View Modal */}
      {viewModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-blue-500" />
                <h3 className="text-lg font-semibold text-gray-900">{viewModal.filename}</h3>
              </div>
              <button
                onClick={() => setViewModal(null)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* CSV Table Preview */}
            <div className="flex-1 overflow-auto p-6">
              {(() => {
                const lines = viewModal.content.trim().split('\n');
                if (lines.length === 0) return <p className="text-gray-500">Empty template</p>;

                const headers = lines[0].split(',');
                const rows = lines.slice(1).map(line => {
                  // Simple CSV parse (handles basic cases)
                  const values: string[] = [];
                  let current = '';
                  let inQuotes = false;
                  for (const char of line) {
                    if (char === '"') {
                      inQuotes = !inQuotes;
                    } else if (char === ',' && !inQuotes) {
                      values.push(current.trim());
                      current = '';
                    } else {
                      current += char;
                    }
                  }
                  values.push(current.trim());
                  return values;
                });

                return (
                  <div className="overflow-x-auto border border-gray-200 rounded-lg">
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50">
                          {headers.map((h, i) => (
                            <th key={i} className="px-3 py-2 text-left text-xs font-semibold text-gray-700 border-b border-gray-200 whitespace-nowrap">
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((row, ri) => (
                          <tr key={ri} className={ri % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                            {row.map((cell, ci) => (
                              <td key={ci} className="px-3 py-2 text-gray-700 border-b border-gray-100 whitespace-nowrap max-w-xs truncate" title={cell}>
                                {cell}
                              </td>
                            ))}
                          </tr>
                        ))}
                        {rows.length === 0 && (
                          <tr>
                            <td colSpan={headers.length} className="px-3 py-4 text-center text-gray-400 italic">
                              No sample data rows (headers only)
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                );
              })()}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200 bg-gray-50 rounded-b-xl">
              <p className="text-xs text-gray-500">
                {viewModal.content.trim().split('\n').length - 1} sample row(s)
              </p>
              <button
                onClick={() => setViewModal(null)}
                className="px-4 py-1.5 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 text-sm transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DCDataIntegration;
