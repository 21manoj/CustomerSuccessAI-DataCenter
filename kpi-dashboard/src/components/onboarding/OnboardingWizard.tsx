/**
 * Onboarding Wizard — Multi-CSV Upload Flow
 * ==========================================
 *
 * 4-step wizard aligned with the 2-stage onboarding model:
 *   Step 1: Welcome — customer info, what to expect
 *   Step 2: Month 1 CSVs — accounts.csv (enriched), kpi_measurements.csv, signals, outcomes
 *   Step 3: Month 2+ CSVs — engagement_events, industry_benchmarks (optional)
 *   Step 4: Process — trigger pipeline, poll for completion, link to dashboard
 *
 * Backend endpoints used:
 *   POST /api/onboarding/upload        (FormData: file + file_type)
 *   POST /api/onboarding/process-data  (JSON: { customer_id })
 *   GET  /api/onboarding/status/<cid>  (poll for pipeline completion)
 *   GET  /api/onboarding/templates/<t> (download CSV template)
 *
 * Route: /onboarding (App.tsx)
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle, Upload, Loader2, AlertTriangle, Download,
  ChevronRight, FileSpreadsheet, ArrowRight, RefreshCw, X,
} from 'lucide-react';
import { useSession } from '../../contexts/SessionContext';
import { getCustomerIdentifier } from '../../utils/api';

// ── File definitions ──

interface FileDef {
  key: string;
  label: string;
  desc: string;
}

const REQUIRED_FILES: FileDef[] = [
  { key: 'accounts.csv', label: 'Accounts (Enriched)', desc: 'Accounts with ARR, champion, products, contract dates, firmographic data (30 columns)' },
  { key: 'kpi_measurements.csv', label: 'KPI Measurements', desc: 'Monthly KPI data points per account per pillar' },
  { key: 'enhanced_qualitative_signals.csv', label: 'Qualitative Signals', desc: 'NPS scores, support escalations, champion changes, sentiment signals' },
  { key: 'outcomes.csv', label: 'Outcomes (CRM History)', desc: 'Renewal/churn/expansion history from Salesforce — provides revenue proof baseline' },
];

const OPTIONAL_FILES: FileDef[] = [
  { key: 'engagement_events.csv', label: 'Engagement Events', desc: 'Meeting/QBR/call logs from CRM (available Month 2+)' },
  { key: 'industry_benchmarks.csv', label: 'Industry Benchmarks', desc: 'Platform-supplied vertical benchmarks (optional)' },
];

type Step = 1 | 2 | 3 | 4;

interface UploadState {
  status: 'idle' | 'uploading' | 'success' | 'error';
  rows?: number;
  message?: string;
}

// ── Component ──

export const OnboardingWizard: React.FC = () => {
  const { session } = useSession();
  const navigate = useNavigate();
  const customerId = getCustomerIdentifier(session);

  const [step, setStep] = useState<Step>(1);
  const [uploads, setUploads] = useState<Record<string, UploadState>>({});
  const [processing, setProcessing] = useState(false);
  const [processResult, setProcessResult] = useState<any>(null);
  const [error, setError] = useState('');

  // Upload a single CSV file
  const uploadFile = useCallback(async (fileKey: string, file: File) => {
    setUploads(prev => ({ ...prev, [fileKey]: { status: 'uploading' } }));
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('file_type', fileKey);

      const resp = await fetch('/api/onboarding/upload', { method: 'POST', body: formData });
      const data = await resp.json().catch(() => ({}));

      if (!resp.ok) {
        setUploads(prev => ({
          ...prev,
          [fileKey]: { status: 'error', message: data.error || data.message || `Upload failed (${resp.status})` },
        }));
        return;
      }

      setUploads(prev => ({
        ...prev,
        [fileKey]: {
          status: 'success',
          rows: data.rows_loaded || data.rows || data.records_loaded || 0,
          message: data.message || 'Uploaded',
        },
      }));
    } catch (e: any) {
      setUploads(prev => ({ ...prev, [fileKey]: { status: 'error', message: e.message } }));
    }
  }, []);

  // Download CSV template
  const downloadTemplate = useCallback(async (fileKey: string) => {
    try {
      const resp = await fetch(`/api/onboarding/templates/${fileKey}`);
      if (!resp.ok) return;
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileKey;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Silent fail — template download is best-effort
    }
  }, []);

  // Process data pipeline
  const processData = useCallback(async () => {
    setProcessing(true);
    setError('');
    try {
      const resp = await fetch('/api/onboarding/process-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_id: customerId }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        setError(err.error || err.message || 'Processing failed');
        setProcessing(false);
        return;
      }

      // Poll for completion
      const poll = async () => {
        try {
          const sr = await fetch(`/api/onboarding/status/${customerId}`);
          if (sr.ok) {
            const status = await sr.json();
            if (status.status === 'success' || status.status === 'completed') {
              setProcessResult(status);
              setProcessing(false);
              return;
            }
            if (status.status === 'error' || status.status === 'failed') {
              setError(status.error || status.message || 'Processing failed');
              setProcessing(false);
              return;
            }
          }
        } catch { /* continue polling */ }
        setTimeout(poll, 3000);
      };
      setTimeout(poll, 2000);
    } catch (e: any) {
      setError(e.message);
      setProcessing(false);
    }
  }, [customerId]);

  const requiredDone = REQUIRED_FILES.every(f => uploads[f.key]?.status === 'success');
  const uploadCount = Object.values(uploads).filter(u => u.status === 'success').length;

  // ── File upload card ──

  const FileCard = ({ def, required }: { def: FileDef; required?: boolean }) => {
    const u = uploads[def.key];
    const inputId = `upload-${def.key.replace(/\./g, '-')}`;
    return (
      <div className={`border rounded-lg p-4 transition-colors ${
        u?.status === 'success' ? 'border-green-700 bg-green-950/20' :
        u?.status === 'error' ? 'border-red-700 bg-red-950/20' :
        'border-gray-700 bg-gray-900/40 hover:border-gray-600'
      }`}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <FileSpreadsheet className="h-4 w-4 text-gray-400 flex-shrink-0" />
              <span className="text-sm font-medium text-white">{def.label}</span>
              {required && <span className="text-[10px] px-1.5 py-0.5 bg-amber-900/50 text-amber-300 rounded font-medium">Required</span>}
            </div>
            <p className="text-xs text-gray-500 mt-1">{def.desc}</p>
            <div className="flex items-center gap-3 mt-1.5">
              <span className="text-[10px] text-gray-600 font-mono">{def.key}</span>
              <button
                onClick={() => downloadTemplate(def.key)}
                className="text-[10px] text-teal-500 hover:text-teal-400 flex items-center gap-0.5"
              >
                <Download className="h-3 w-3" /> Template
              </button>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {u?.status === 'success' && (
              <span className="flex items-center gap-1 text-xs text-green-400">
                <CheckCircle className="h-4 w-4" />
                {u.rows ? `${u.rows} rows` : 'Done'}
              </span>
            )}
            {u?.status === 'uploading' && <Loader2 className="h-4 w-4 text-teal-400 animate-spin" />}
            {u?.status === 'error' && (
              <span className="text-xs text-red-400 max-w-[180px] truncate" title={u.message}>{u.message}</span>
            )}
            <label htmlFor={inputId} className={`cursor-pointer px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              u?.status === 'success' ? 'bg-gray-800 text-gray-400 hover:bg-gray-700' : 'bg-teal-600 text-white hover:bg-teal-500'
            }`}>
              {u?.status === 'success' ? 'Replace' : 'Upload'}
            </label>
            <input
              id={inputId}
              type="file"
              accept=".csv,.tsv"
              className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadFile(def.key, f); e.target.value = ''; }}
            />
          </div>
        </div>
      </div>
    );
  };

  // ── Step bar ──

  const steps = [
    { n: 1, label: 'Welcome' },
    { n: 2, label: 'Month 1 Data' },
    { n: 3, label: 'Month 2+ (Optional)' },
    { n: 4, label: 'Process' },
  ];

  return (
    <div className="min-h-screen bg-[#0f1419] text-white">
      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">CS Pulse Onboarding</h1>
            <p className="text-gray-500 text-sm mt-0.5">Upload your data to generate health scores and insights</p>
          </div>
          <button onClick={() => navigate('/')} className="text-gray-500 hover:text-gray-300"><X className="h-5 w-5" /></button>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-1.5 mb-8">
          {steps.map((s, i) => (
            <React.Fragment key={s.n}>
              <button
                onClick={() => { if (s.n <= step || (s.n === 3 && requiredDone) || (s.n === 4 && requiredDone)) setStep(s.n as Step); }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                  step === s.n ? 'bg-teal-600 text-white shadow-lg shadow-teal-900/30'
                    : step > s.n ? 'bg-green-900/40 text-green-300'
                    : 'bg-gray-800/80 text-gray-500'
                }`}
              >
                {step > s.n ? <CheckCircle className="h-3.5 w-3.5" /> : <span className="w-4 text-center">{s.n}</span>}
                <span className="hidden sm:inline">{s.label}</span>
              </button>
              {i < steps.length - 1 && <ChevronRight className="h-3 w-3 text-gray-700" />}
            </React.Fragment>
          ))}
        </div>

        {/* ── Step 1: Welcome ── */}
        {step === 1 && (
          <div className="space-y-6">
            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-3">Welcome to CS Pulse</h2>
              <p className="text-sm text-gray-400 leading-relaxed">
                We need two files to get started: your <strong className="text-white">accounts list</strong> (with ARR and renewal dates)
                and <strong className="text-white">KPI measurements</strong> (monthly metrics per account).
                Everything else — signals, stakeholders, products — is optional but improves accuracy.
              </p>
              <div className="grid grid-cols-3 gap-3 mt-5 text-xs">
                <div className="bg-gray-800/60 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-teal-400">2</div>
                  <div className="text-gray-500 mt-0.5">Required files</div>
                </div>
                <div className="bg-gray-800/60 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-gray-300">6</div>
                  <div className="text-gray-500 mt-0.5">Optional files</div>
                </div>
                <div className="bg-gray-800/60 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-gray-300">~5 min</div>
                  <div className="text-gray-500 mt-0.5">Total time</div>
                </div>
              </div>
            </div>
            <button
              onClick={() => setStep(2)}
              className="w-full py-3 bg-teal-600 hover:bg-teal-500 rounded-xl font-medium flex items-center justify-center gap-2 transition-colors"
            >
              Start Upload <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* ── Step 2: Month 1 CSVs ── */}
        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">Month 1 Data</h2>
              <p className="text-sm text-gray-500 mt-0.5">
                Upload these 4 files for full onboarding — health scoring, context graph, and revenue proof.
                Accounts.csv is enriched (30 columns: products, champion, contract, firmographic).
              </p>
            </div>
            <div className="space-y-3">
              {REQUIRED_FILES.map(f => <FileCard key={f.key} def={f} required />)}
            </div>
            <div className="flex justify-between pt-4">
              <button onClick={() => setStep(1)} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">Back</button>
              <button
                onClick={() => setStep(3)}
                disabled={!requiredDone}
                className={`px-6 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors ${
                  requiredDone ? 'bg-teal-600 hover:bg-teal-500 text-white' : 'bg-gray-800 text-gray-500 cursor-not-allowed'
                }`}
              >
                Next: Month 2+ Data <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* ── Step 3: Month 2+ CSVs ── */}
        {step === 3 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">Month 2+ Data (Optional)</h2>
              <p className="text-sm text-gray-500 mt-0.5">
                These files enrich your context graph as CRM integrations come online.
                Skip for now — you can upload them later from Settings.
              </p>
            </div>
            <div className="space-y-3">
              {OPTIONAL_FILES.map(f => <FileCard key={f.key} def={f} />)}
            </div>
            <div className="flex justify-between pt-4">
              <button onClick={() => setStep(2)} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">Back</button>
              <button
                onClick={() => setStep(4)}
                className="px-6 py-2 bg-teal-600 hover:bg-teal-500 rounded-xl text-sm font-medium flex items-center gap-2"
              >
                Process Data <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* ── Step 4: Process ── */}
        {step === 4 && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold">Process Your Data</h2>

            {/* Upload summary */}
            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-medium text-gray-300">Upload Summary</h3>
                <span className="text-xs text-gray-500">{uploadCount} file{uploadCount !== 1 ? 's' : ''} uploaded</span>
              </div>
              <div className="space-y-1">
                {Object.entries(uploads).filter(([, v]) => v.status === 'success').map(([key, v]) => (
                  <div key={key} className="flex items-center gap-2 text-xs">
                    <CheckCircle className="h-3 w-3 text-green-400 flex-shrink-0" />
                    <span className="text-gray-300 font-mono">{key}</span>
                    {v.rows ? <span className="text-gray-500">({v.rows.toLocaleString()} rows)</span> : null}
                  </div>
                ))}
              </div>
            </div>

            {error && (
              <div className="bg-red-950/30 border border-red-800 rounded-lg p-3 flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5 flex-shrink-0" />
                <span className="text-sm text-red-300">{error}</span>
              </div>
            )}

            {processResult ? (
              <div className="bg-green-950/20 border border-green-800 rounded-xl p-8 text-center">
                <CheckCircle className="h-12 w-12 text-green-400 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-green-300 mb-2">Onboarding Complete!</h3>
                <p className="text-sm text-gray-400 mb-6">Health scores calculated. Your dashboard is ready.</p>
                <div className="flex justify-center gap-3">
                  <button onClick={() => navigate('/dc-dashboard')} className="px-5 py-2.5 bg-teal-600 hover:bg-teal-500 rounded-lg text-sm font-medium transition-colors">
                    Go to Dashboard
                  </button>
                  <button onClick={() => navigate('/dc-dashboard/csm')} className="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm transition-colors">
                    CSM View
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex justify-between">
                <button onClick={() => setStep(3)} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm">Back</button>
                <button
                  onClick={processData}
                  disabled={processing}
                  className={`px-6 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 transition-colors ${
                    processing ? 'bg-gray-700 text-gray-400 cursor-wait' : 'bg-teal-600 hover:bg-teal-500 text-white'
                  }`}
                >
                  {processing ? (
                    <><Loader2 className="h-4 w-4 animate-spin" /> Processing...</>
                  ) : (
                    <><RefreshCw className="h-4 w-4" /> Calculate Health Scores</>
                  )}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default OnboardingWizard;
