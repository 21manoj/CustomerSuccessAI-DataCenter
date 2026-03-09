/**
 * Test Runner UI — Drive load-driver scenarios from the browser
 *
 * Sections:
 *  A. Scenario selector (checkboxes + customer ID)
 *  B. Run controls (start button)
 *  C. Active run monitor (polling progress)
 *  D. Results panel (per-scenario details)
 *  E. Run history table
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  FlaskConical,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  ChevronDown,
  ChevronRight,
  Trash2,
  RefreshCw,
  AlertTriangle,
  SlidersHorizontal,
  Lock,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ScenarioMeta {
  id: string;
  name: string;
  group: string;
  description: string;
  est_minutes: number;
}

interface ScenarioRun {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'pass' | 'fail';
  start_time: string | null;
  end_time: string | null;
  result: {
    status: string;
    message: string;
    duration_seconds: number;
    details?: Record<string, any>;
    errors?: string[];
    api_calls?: number;
  } | null;
  exit_code?: number;
  stderr?: string;
}

interface RunStatus {
  run_id: string;
  status: 'running' | 'completed';
  customer_id: string | number;
  start_time: string;
  end_time: string | null;
  scenarios: ScenarioRun[];
  summary: {
    total: number;
    passed: number;
    failed: number;
    duration_seconds: number;
  } | null;
}

interface RunSummary {
  run_id: string;
  status: string;
  customer_id: string | number;
  start_time: string;
  end_time: string | null;
  scenario_count: number;
  summary: {
    total: number;
    passed: number;
    failed: number;
    duration_seconds: number;
  } | null;
}

// ---------------------------------------------------------------------------
// Advanced Options Types & Defaults
// ---------------------------------------------------------------------------

interface PatternMix {
  crisis: number;
  churn: number;
  stable: number;
  expansion: number;
}

interface PillarWeights {
  AI: number;
  CH: number;
  DV: number;
  EX: number;
  OS: number;
}

interface AdvancedOptions {
  numAccounts: number;
  dryRun: boolean;
  seed: number | null;
  industry: string;
  onboardingMode: 'demo' | 'custom';
  showcasePatternMix: PatternMix;
  weights: PillarWeights;
}

interface RunPreset {
  label: string;
  description: string;
  numAccounts: number;
  industry: string;
  seed: number | null;
}

const PRESETS: RunPreset[] = [
  { label: 'Quick Demo', description: '3 accounts, fast feedback', numAccounts: 3, industry: 'Technology', seed: null },
  { label: 'Standard', description: '10 accounts, balanced test', numAccounts: 10, industry: 'Technology', seed: 42 },
  { label: 'Full Load Test', description: '50 accounts, comprehensive', numAccounts: 50, industry: 'Technology', seed: 42 },
];

const DEFAULT_PATTERN_MIX: PatternMix = { crisis: 0.15, churn: 0.15, stable: 0.50, expansion: 0.20 };
const DEFAULT_WEIGHTS: PillarWeights = { AI: 0.10, CH: 0.30, DV: 0.30, EX: 0.05, OS: 0.25 };

const DEFAULT_OPTIONS: AdvancedOptions = {
  numAccounts: 3,
  dryRun: false,
  seed: null,
  industry: 'Technology',
  onboardingMode: 'demo',
  showcasePatternMix: { ...DEFAULT_PATTERN_MIX },
  weights: { ...DEFAULT_WEIGHTS },
};

const INDUSTRIES = [
  'Technology', 'Financial Services', 'Healthcare', 'Manufacturing',
  'Retail', 'Energy', 'Telecommunications', 'Government', 'Education',
  'Media & Entertainment',
];

const PILLAR_LABELS: Record<keyof PillarWeights, string> = {
  AI: 'AI Intelligence', CH: 'Customer Health', DV: 'Data Value',
  EX: 'Experience', OS: 'Operational Scale',
};

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

const api = {
  async getScenarios(): Promise<ScenarioMeta[]> {
    const res = await fetch('/api/test-runner/scenarios', { credentials: 'include' });
    const data = await res.json();
    return data.scenarios || [];
  },

  async startRun(scenarioIds: string[], customerId: string | number, options?: AdvancedOptions): Promise<{ run_id: string }> {
    const body: Record<string, any> = {
      scenario_ids: scenarioIds,
      customer_id: customerId,
    };

    if (options) {
      body.options = {
        num_accounts: options.numAccounts,
        dry_run: options.dryRun,
        seed: options.seed,
        industry: options.industry,
        onboarding_mode: options.onboardingMode,
        showcase_pattern_mix: options.showcasePatternMix,
        weights: options.weights,
      };
    }

    const res = await fetch('/api/test-runner/start', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Failed to start run');
    }
    return res.json();
  },

  async getStatus(runId: string): Promise<RunStatus> {
    const res = await fetch(`/api/test-runner/status/${runId}`, { credentials: 'include' });
    return res.json();
  },

  async getRuns(): Promise<RunSummary[]> {
    const res = await fetch('/api/test-runner/runs', { credentials: 'include' });
    const data = await res.json();
    return data.runs || [];
  },

  async deleteRun(runId: string): Promise<void> {
    await fetch(`/api/test-runner/runs/${runId}`, { method: 'DELETE', credentials: 'include' });
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDuration(seconds: number): string {
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  return `${(seconds / 60).toFixed(1)}m`;
}

function formatTime(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleTimeString();
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-600',
    running: 'bg-blue-100 text-blue-700',
    pass: 'bg-green-100 text-green-700',
    fail: 'bg-red-100 text-red-700',
    success: 'bg-green-100 text-green-700',
    failure: 'bg-red-100 text-red-700',
    completed: 'bg-green-100 text-green-700',
  };
  const icons: Record<string, React.ReactNode> = {
    pending: <Clock className="w-3.5 h-3.5" />,
    running: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
    pass: <CheckCircle2 className="w-3.5 h-3.5" />,
    fail: <XCircle className="w-3.5 h-3.5" />,
    success: <CheckCircle2 className="w-3.5 h-3.5" />,
    failure: <XCircle className="w-3.5 h-3.5" />,
    completed: <CheckCircle2 className="w-3.5 h-3.5" />,
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${styles[status] || 'bg-gray-100 text-gray-600'}`}>
      {icons[status]}
      {status.toUpperCase()}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const DCTestRunner: React.FC = () => {
  // Scenario list
  const [scenarios, setScenarios] = useState<ScenarioMeta[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [customerId, setCustomerId] = useState<string>('500');

  // Active run
  const [activeRun, setActiveRun] = useState<RunStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // Advanced options
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [options, setOptions] = useState<AdvancedOptions>({ ...DEFAULT_OPTIONS });

  // Entitlements — controls feature visibility
  const [entitlements, setEntitlements] = useState<Record<string, boolean>>({});
  const [customerTier, setCustomerTier] = useState<string>('starter');

  const hasAdvancedEntitlement = entitlements['test_runner_advanced'] ?? false;

  // Results — expanded scenario IDs
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  // History
  const [history, setHistory] = useState<RunSummary[]>([]);

  // ------- Load scenarios + history + entitlements on mount -------
  useEffect(() => {
    api.getScenarios().then(setScenarios).catch(() => {});
    api.getRuns().then(setHistory).catch(() => {});
  }, []);

  // Fetch entitlements whenever customerId changes
  useEffect(() => {
    const cid = customerId?.trim();
    if (!cid) return;

    fetch(`/api/entitlements?customer_id=${cid}`, { credentials: 'include' })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data?.entitlements) {
          setEntitlements(data.entitlements);
          setCustomerTier(data.tier || 'starter');
        }
      })
      .catch(() => {
        // Entitlements API not available — default to all allowed
        setEntitlements({});
        setCustomerTier('starter');
      });
  }, [customerId]);

  // ------- Polling -------
  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback((runId: string) => {
    stopPolling();
    const poll = async () => {
      try {
        const status = await api.getStatus(runId);
        setActiveRun(status);
        if (status.status === 'completed') {
          stopPolling();
          // Refresh history
          api.getRuns().then(setHistory).catch(() => {});
        }
      } catch {
        // Ignore transient errors
      }
    };
    // Poll immediately then every 3s
    poll();
    pollRef.current = setInterval(poll, 3000);
  }, [stopPolling]);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  // ------- Actions -------
  const toggleScenario = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === scenarios.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(scenarios.map(s => s.id)));
    }
  };

  // ------- Advanced Options helpers -------
  const setOption = <K extends keyof AdvancedOptions>(key: K, value: AdvancedOptions[K]) => {
    setOptions(prev => ({ ...prev, [key]: value }));
  };

  const applyPreset = (preset: RunPreset) => {
    setOptions(prev => ({
      ...prev,
      numAccounts: preset.numAccounts,
      industry: preset.industry,
      seed: preset.seed,
    }));
  };

  const patternMixTotal = Object.values(options.showcasePatternMix).reduce((a, b) => a + b, 0);
  const weightsTotal = Object.values(options.weights).reduce((a, b) => a + b, 0);
  const patternMixValid = Math.abs(patternMixTotal - 1.0) < 0.02;
  const weightsValid = Math.abs(weightsTotal - 1.0) < 0.02;

  // Scenario-aware booleans
  const hasOnboarding = selected.has('1');
  const hasCleanup = selected.has('4');

  const handleStart = async () => {
    const cid = customerId?.trim();
    if (!cid) {
      setError('Enter a valid customer ID');
      return;
    }
    if (selected.size === 0) {
      setError('Select at least one scenario');
      return;
    }

    // Validate advanced options when panel is open
    if (showAdvanced && hasOnboarding) {
      if (!patternMixValid) {
        setError(`Journey pattern mix must sum to 1.0 (currently ${patternMixTotal.toFixed(2)})`);
        return;
      }
      if (!weightsValid) {
        setError(`Pillar weights must sum to 1.0 (currently ${weightsTotal.toFixed(2)})`);
        return;
      }
    }

    setError(null);
    setStarting(true);
    setExpanded(new Set());

    try {
      // Sort selected IDs in canonical order
      const orderedIds = scenarios.map(s => s.id).filter(id => selected.has(id));
      const { run_id } = await api.startRun(orderedIds, cid, showAdvanced ? options : undefined);
      startPolling(run_id);
    } catch (e: any) {
      setError(e.message || 'Failed to start');
    } finally {
      setStarting(false);
    }
  };

  const handleDeleteHistory = async (runId: string) => {
    await api.deleteRun(runId);
    setHistory(prev => prev.filter(r => r.run_id !== runId));
  };

  const toggleExpanded = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // ------- Derived state -------
  const isRunning = activeRun?.status === 'running';
  const completedCount = activeRun?.scenarios.filter(s => s.status === 'pass' || s.status === 'fail').length || 0;
  const totalCount = activeRun?.scenarios.length || 0;
  const progressPct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  // ------- Render -------
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <FlaskConical className="h-7 w-7 text-indigo-600" />
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Test Runner</h2>
          <p className="text-sm text-gray-500">Drive load-driver E2E scenarios against CS Pulse via HTTP</p>
        </div>
        {customerTier && (
          <span className={`ml-auto px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wide ${
            customerTier === 'enterprise' ? 'bg-purple-100 text-purple-800' :
            customerTier === 'professional' ? 'bg-blue-100 text-blue-800' :
            'bg-gray-100 text-gray-600'
          }`}>
            {customerTier}
          </span>
        )}
      </div>

      {/* ============================================================ */}
      {/* A. Scenario Selector + B. Run Controls                        */}
      {/* ============================================================ */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">Select Scenarios</h3>
          <button
            onClick={toggleAll}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            {selected.size === scenarios.length ? 'Deselect All' : 'Select All'}
          </button>
        </div>

        <div className="px-6 py-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          {scenarios.map(s => (
            <label
              key={s.id}
              className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                selected.has(s.id)
                  ? 'border-blue-300 bg-blue-50/50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <input
                type="checkbox"
                checked={selected.has(s.id)}
                onChange={() => toggleScenario(s.id)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900 text-sm">
                    {s.id}. {s.name}
                  </span>
                  <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">
                    {s.group}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{s.description}</p>
                <p className="text-xs text-gray-400 mt-0.5">~{s.est_minutes} min</p>
              </div>
            </label>
          ))}
        </div>

        {/* ── Advanced Options ── */}
        <div className="border-t border-gray-100">
          <button
            onClick={() => hasAdvancedEntitlement && setShowAdvanced(!showAdvanced)}
            className={`w-full px-6 py-3 flex items-center justify-between text-sm font-medium transition-colors ${
              hasAdvancedEntitlement
                ? 'text-gray-600 hover:bg-gray-50 cursor-pointer'
                : 'text-gray-400 cursor-not-allowed'
            }`}
            title={hasAdvancedEntitlement ? undefined : 'Upgrade to Professional tier to unlock Advanced Options'}
          >
            <span className="flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4" />
              Advanced Options
              {!hasAdvancedEntitlement && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-xs font-medium">
                  <Lock className="w-3 h-3" />
                  Professional
                </span>
              )}
            </span>
            {hasAdvancedEntitlement && (
              showAdvanced
                ? <ChevronDown className="w-4 h-4" />
                : <ChevronRight className="w-4 h-4" />
            )}
          </button>

          {showAdvanced && hasAdvancedEntitlement && (
            <div className="px-6 pb-4 space-y-5">

              {/* Presets */}
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                  Presets
                </label>
                <div className="flex gap-2 flex-wrap">
                  {PRESETS.map(p => (
                    <button
                      key={p.label}
                      onClick={() => applyPreset(p)}
                      className={`px-3 py-1.5 rounded-md border text-xs font-medium transition-colors ${
                        options.numAccounts === p.numAccounts
                          ? 'border-blue-400 bg-blue-50 text-blue-700'
                          : 'border-gray-200 text-gray-700 hover:bg-blue-50 hover:border-blue-300'
                      }`}
                      title={p.description}
                    >
                      {p.label} ({p.numAccounts})
                    </button>
                  ))}
                </div>
              </div>

              {/* Global Options */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">Num Accounts</label>
                  <input
                    type="number"
                    value={options.numAccounts}
                    onChange={e => setOption('numAccounts', Math.max(1, parseInt(e.target.value, 10) || 3))}
                    min={1}
                    max={200}
                    className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Seed <span className="text-gray-400">(optional)</span>
                  </label>
                  <input
                    type="number"
                    value={options.seed ?? ''}
                    onChange={e => setOption('seed', e.target.value ? parseInt(e.target.value, 10) : null)}
                    placeholder="random"
                    className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Scenario 1: Onboarding Options */}
              {hasOnboarding && (
                <div className="border border-blue-200 bg-blue-50/30 rounded-lg p-4 space-y-4">
                  <h4 className="text-sm font-semibold text-blue-800 flex items-center gap-2">
                    <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-xs font-bold">1</span>
                    Onboarding Options
                  </h4>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Industry</label>
                      <select
                        value={options.industry}
                        onChange={e => setOption('industry', e.target.value)}
                        className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                      >
                        {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">Mode</label>
                      <div className="flex gap-4 mt-1.5">
                        {(['demo', 'custom'] as const).map(mode => (
                          <label key={mode} className="flex items-center gap-1.5 text-sm cursor-pointer">
                            <input
                              type="radio"
                              name="onboarding_mode"
                              checked={options.onboardingMode === mode}
                              onChange={() => setOption('onboardingMode', mode)}
                              className="text-blue-600 focus:ring-blue-500"
                            />
                            {mode === 'demo' ? 'Demo (synthetic)' : 'Custom (user CSVs)'}
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Journey Pattern Mix */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-xs font-medium text-gray-500">Journey Pattern Mix</label>
                      <span className={`text-xs font-mono ${patternMixValid ? 'text-green-600' : 'text-red-600'}`}>
                        Total: {patternMixTotal.toFixed(2)} {patternMixValid ? '✓' : '(must = 1.0)'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {(Object.keys(DEFAULT_PATTERN_MIX) as Array<keyof PatternMix>).map(key => (
                        <div key={key}>
                          <div className="flex items-center justify-between mb-0.5">
                            <span className="text-xs text-gray-600 capitalize">{key}</span>
                            <span className="text-xs font-mono text-gray-500">
                              {(options.showcasePatternMix[key] * 100).toFixed(0)}%
                            </span>
                          </div>
                          <input
                            type="range"
                            min={0}
                            max={100}
                            step={5}
                            value={options.showcasePatternMix[key] * 100}
                            onChange={e => {
                              const newMix = { ...options.showcasePatternMix };
                              newMix[key] = parseInt(e.target.value, 10) / 100;
                              setOption('showcasePatternMix', newMix);
                            }}
                            className="w-full h-1.5 bg-gray-200 rounded-lg cursor-pointer accent-blue-600"
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Pillar Weights */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-xs font-medium text-gray-500">Pillar Weights (DC2_S)</label>
                      <span className={`text-xs font-mono ${weightsValid ? 'text-green-600' : 'text-red-600'}`}>
                        Total: {weightsTotal.toFixed(2)} {weightsValid ? '✓' : '(must = 1.0)'}
                      </span>
                    </div>
                    <div className="grid grid-cols-5 gap-3">
                      {(Object.keys(DEFAULT_WEIGHTS) as Array<keyof PillarWeights>).map(key => (
                        <div key={key}>
                          <div className="flex items-center justify-between mb-0.5">
                            <span className="text-xs font-bold text-gray-600" title={PILLAR_LABELS[key]}>{key}</span>
                            <span className="text-xs font-mono text-gray-500">
                              {(options.weights[key] * 100).toFixed(0)}%
                            </span>
                          </div>
                          <input
                            type="range"
                            min={0}
                            max={100}
                            step={5}
                            value={options.weights[key] * 100}
                            onChange={e => {
                              const newW = { ...options.weights };
                              newW[key] = parseInt(e.target.value, 10) / 100;
                              setOption('weights', newW);
                            }}
                            className="w-full h-1.5 bg-gray-200 rounded-lg cursor-pointer accent-blue-600"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Scenario 4: Cleanup Options */}
              {hasCleanup && (
                <div className="border border-amber-200 bg-amber-50/30 rounded-lg p-4">
                  <h4 className="text-sm font-semibold text-amber-800 flex items-center gap-2 mb-2">
                    <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-100 text-amber-700 text-xs font-bold">4</span>
                    Cleanup Options
                  </h4>
                  <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={options.dryRun}
                      onChange={e => setOption('dryRun', e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                    />
                    Dry Run (preview only — do not delete)
                  </label>
                  <p className="text-xs text-gray-500 mt-1 ml-6">
                    Shows what would be deleted without actually removing any data
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Controls row */}
        <div className="px-6 py-4 border-t border-gray-100 flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Customer ID:</label>
            <input
              type="number"
              value={customerId}
              onChange={e => setCustomerId(e.target.value)}
              className="w-24 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              min="1"
              disabled={isRunning}
            />
          </div>

          <button
            onClick={handleStart}
            disabled={isRunning || starting || selected.size === 0}
            className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm transition-colors"
          >
            {starting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {starting ? 'Starting...' : isRunning ? 'Running...' : 'Run Selected'}
          </button>

          <span className="text-sm text-gray-500">
            {selected.size} scenario{selected.size !== 1 ? 's' : ''} selected
          </span>

          {error && (
            <div className="flex items-center gap-1 text-sm text-red-600">
              <AlertTriangle className="w-4 h-4" />
              {error}
            </div>
          )}
        </div>
      </div>

      {/* ============================================================ */}
      {/* C. Active Run Monitor + D. Results Panel                      */}
      {/* ============================================================ */}
      {activeRun && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h3 className="font-semibold text-gray-800">
                  Run: {activeRun.run_id}
                </h3>
                <StatusBadge status={activeRun.status} />
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-500">
                <span>Customer: {activeRun.customer_id}</span>
                <span>Started: {formatTime(activeRun.start_time)}</span>
                {activeRun.summary && (
                  <span>Duration: {formatDuration(activeRun.summary.duration_seconds)}</span>
                )}
              </div>
            </div>

            {/* Progress bar */}
            {isRunning && (
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                  <span>{completedCount} of {totalCount} scenarios</span>
                  <span>{progressPct}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 rounded-full h-2 transition-all duration-500"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              </div>
            )}

            {/* Summary badges */}
            {activeRun.summary && (
              <div className="mt-3 flex items-center gap-4 text-sm">
                <span className="flex items-center gap-1 text-green-700">
                  <CheckCircle2 className="w-4 h-4" />
                  {activeRun.summary.passed} passed
                </span>
                <span className="flex items-center gap-1 text-red-700">
                  <XCircle className="w-4 h-4" />
                  {activeRun.summary.failed} failed
                </span>
                <span className="text-gray-500">
                  Total: {formatDuration(activeRun.summary.duration_seconds)}
                </span>
              </div>
            )}
          </div>

          {/* Per-scenario rows */}
          <div className="divide-y divide-gray-100">
            {activeRun.scenarios.map(s => (
              <div key={s.id}>
                {/* Row header */}
                <div
                  className="px-6 py-3 flex items-center gap-3 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => s.result && toggleExpanded(s.id)}
                >
                  {s.result ? (
                    expanded.has(s.id)
                      ? <ChevronDown className="w-4 h-4 text-gray-400" />
                      : <ChevronRight className="w-4 h-4 text-gray-400" />
                  ) : (
                    <div className="w-4 h-4" />
                  )}

                  <StatusBadge status={s.status} />

                  <span className="font-medium text-sm text-gray-800">
                    {s.id}. {s.name}
                  </span>

                  <span className="ml-auto text-xs text-gray-500">
                    {s.result
                      ? formatDuration(s.result.duration_seconds)
                      : s.status === 'running'
                        ? 'in progress...'
                        : 'waiting'
                    }
                  </span>
                </div>

                {/* Expanded detail */}
                {expanded.has(s.id) && s.result && (
                  <div className="px-6 pb-4 pl-16">
                    <div className="bg-gray-50 rounded-lg p-4 text-sm space-y-2">
                      <p><span className="font-medium text-gray-700">Message:</span> {s.result.message}</p>

                      {s.result.api_calls != null && (
                        <p><span className="font-medium text-gray-700">API Calls:</span> {s.result.api_calls}</p>
                      )}

                      {/* Details table */}
                      {s.result.details && Object.keys(s.result.details).length > 0 && (
                        <div className="mt-2">
                          <p className="font-medium text-gray-700 mb-1">Details:</p>
                          <div className="bg-white rounded border border-gray-200 overflow-hidden">
                            <table className="w-full text-xs">
                              <tbody>
                                {Object.entries(s.result.details)
                                  .filter(([k]) => k !== 'complete_response' && k !== 'test_results')
                                  .map(([key, value]) => (
                                    <tr key={key} className="border-b border-gray-100 last:border-0">
                                      <td className="px-3 py-1.5 font-medium text-gray-600 whitespace-nowrap">{key}</td>
                                      <td className="px-3 py-1.5 text-gray-800 break-all">
                                        {typeof value === 'object'
                                          ? JSON.stringify(value).slice(0, 120)
                                          : String(value)
                                        }
                                      </td>
                                    </tr>
                                  ))
                                }
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {/* Individual test results (for tenant isolation etc.) */}
                      {s.result.details?.test_results && (
                        <div className="mt-2">
                          <p className="font-medium text-gray-700 mb-1">Individual Tests:</p>
                          <div className="bg-white rounded border border-gray-200 overflow-hidden">
                            <table className="w-full text-xs">
                              <thead>
                                <tr className="bg-gray-50 border-b border-gray-200">
                                  <th className="px-3 py-1.5 text-left font-medium text-gray-600">#</th>
                                  <th className="px-3 py-1.5 text-left font-medium text-gray-600">Test</th>
                                  <th className="px-3 py-1.5 text-left font-medium text-gray-600">Result</th>
                                  <th className="px-3 py-1.5 text-left font-medium text-gray-600">Detail</th>
                                </tr>
                              </thead>
                              <tbody>
                                {(s.result.details.test_results as any[]).map((t: any, i: number) => (
                                  <tr key={i} className="border-b border-gray-100 last:border-0">
                                    <td className="px-3 py-1.5 text-gray-500">{i + 1}</td>
                                    <td className="px-3 py-1.5 text-gray-800">{t.test}</td>
                                    <td className="px-3 py-1.5">
                                      {t.passed
                                        ? <CheckCircle2 className="w-3.5 h-3.5 text-green-600" />
                                        : <XCircle className="w-3.5 h-3.5 text-red-600" />
                                      }
                                    </td>
                                    <td className="px-3 py-1.5 text-gray-600 truncate max-w-xs">{t.detail || ''}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {/* Errors */}
                      {s.result.errors && s.result.errors.length > 0 && (
                        <div className="mt-2">
                          <p className="font-medium text-red-700 mb-1">Errors:</p>
                          <ul className="list-disc list-inside text-red-600 text-xs space-y-0.5">
                            {s.result.errors.map((err, i) => (
                              <li key={i}>{err}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {s.stderr && (
                        <div className="mt-2">
                          <p className="font-medium text-red-700 mb-1">Stderr:</p>
                          <pre className="bg-red-50 text-red-800 text-xs p-2 rounded overflow-x-auto">{s.stderr}</pre>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* E. Run History                                                */}
      {/* ============================================================ */}
      {history.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">Run History</h3>
            <button
              onClick={() => api.getRuns().then(setHistory).catch(() => {})}
              className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Run ID</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Status</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Customer</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Scenarios</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Result</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Duration</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Started</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600"></th>
                </tr>
              </thead>
              <tbody>
                {history.map(run => (
                  <tr
                    key={run.run_id}
                    className="border-b border-gray-100 last:border-0 hover:bg-gray-50 cursor-pointer"
                    onClick={() => {
                      // Load full run details
                      api.getStatus(run.run_id).then(setActiveRun).catch(() => {});
                    }}
                  >
                    <td className="px-4 py-2 font-mono text-xs text-gray-700">{run.run_id}</td>
                    <td className="px-4 py-2"><StatusBadge status={run.status} /></td>
                    <td className="px-4 py-2 text-gray-700">{run.customer_id}</td>
                    <td className="px-4 py-2 text-gray-700">{run.scenario_count}</td>
                    <td className="px-4 py-2">
                      {run.summary ? (
                        <span>
                          <span className="text-green-700">{run.summary.passed}P</span>
                          {' / '}
                          <span className="text-red-700">{run.summary.failed}F</span>
                        </span>
                      ) : '-'}
                    </td>
                    <td className="px-4 py-2 text-gray-500">
                      {run.summary ? formatDuration(run.summary.duration_seconds) : '-'}
                    </td>
                    <td className="px-4 py-2 text-gray-500 text-xs">
                      {new Date(run.start_time).toLocaleString()}
                    </td>
                    <td className="px-4 py-2">
                      <button
                        onClick={e => { e.stopPropagation(); handleDeleteHistory(run.run_id); }}
                        className="text-gray-400 hover:text-red-500 transition-colors"
                        title="Delete run"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default DCTestRunner;
