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
import {
  Upload,
  FileText,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Download,
  Calendar,
  X,
  Play
} from 'lucide-react';

// ============================================================
// TYPES
// ============================================================

type UploadMode = 'full_refresh' | 'incremental' | 'upsert' | 'merge';
type SubTab = 'upload' | 'history' | 'templates';
type FileType = 'accounts' | 'kpis' | 'signals' | 'products' | 'profiles' | 'customers';

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

const DCDataIntegration: React.FC = () => {
  const { session } = useSession();
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

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFiles(Array.from(e.target.files));
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
        <h2 className="text-2xl font-bold text-gray-900">Data Integration</h2>
        <p className="text-sm text-gray-500 mt-1">
          Upload and manage your data files
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
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select File Type <span className="text-red-500">*</span>
                </label>
                <select
                  value={selectedFileType}
                  onChange={(e) => setSelectedFileType(e.target.value as FileType)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">-- Select file type --</option>
                  <option value="accounts">Accounts (accounts.csv)</option>
                  <option value="kpis">KPIs (kpi_measurements.csv)</option>
                  <option value="signals">Signals (qualitative_signals.csv)</option>
                  <option value="products">Products (products.csv)</option>
                  <option value="profiles">Profiles (account_profiles.csv)</option>
                  <option value="customers">Customers (customers.csv)</option>
                </select>
                <p className="text-xs text-gray-500 mt-2">
                  Choose the type of data file you're uploading
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
                  Supported: accounts.csv, kpis.csv, signals.csv, products.csv, profiles.csv, customers.csv
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
                        {uploadResult.message}
                      </p>
                      {uploadResult.success && uploadResult.accounts !== undefined && (
                        <p className="text-sm text-green-700 mt-1">
                          Accounts: {uploadResult.accounts} • KPIs: {uploadResult.kpis}
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
            <div className="space-y-4">
              <p className="text-sm text-gray-600 mb-4">
                Download CSV templates for data upload
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  { type: 'accounts', name: 'accounts.csv', desc: 'Account information template' },
                  { type: 'kpis', name: 'kpi_measurements.csv', desc: 'KPI measurements template' },
                  { type: 'signals', name: 'qualitative_signals.csv', desc: 'Qualitative signals template' },
                  { type: 'products', name: 'products.csv', desc: 'Product catalog template' },
                  { type: 'profiles', name: 'account_profiles.csv', desc: 'Account profiles template' },
                  { type: 'customers', name: 'customers.csv', desc: 'Customer/tenant data template' },
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

                  return (
                    <div key={template.type} className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <FileText className="w-5 h-5 text-gray-400" />
                        <button 
                          onClick={handleDownload}
                          className="text-blue-600 hover:text-blue-700 transition-colors"
                          title={`Download ${template.name}`}
                        >
                          <Download className="w-4 h-4" />
                        </button>
                      </div>
                      <p className="text-sm font-medium text-gray-900">{template.name}</p>
                      <p className="text-xs text-gray-500 mt-1">{template.desc}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DCDataIntegration;
