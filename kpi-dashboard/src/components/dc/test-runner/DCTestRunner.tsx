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
  customer_id: number;
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
  customer_id: number;
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
// API helpers
// ---------------------------------------------------------------------------

const api = {
  async getScenarios(): Promise<ScenarioMeta[]> {
    const res = await fetch('/api/test-runner/scenarios', { credentials: 'include' });
    const data = await res.json();
    return data.scenarios || [];
  },

  async startRun(scenarioIds: string[], customerId: number): Promise<{ run_id: string }> {
    const res = await fetch('/api/test-runner/start', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_ids: scenarioIds, customer_id: customerId }),
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

  // Results — expanded scenario IDs
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  // History
  const [history, setHistory] = useState<RunSummary[]>([]);

  // ------- Load scenarios + history on mount -------
  useEffect(() => {
    api.getScenarios().then(setScenarios).catch(() => {});
    api.getRuns().then(setHistory).catch(() => {});
  }, []);

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

  const handleStart = async () => {
    const cid = parseInt(customerId, 10);
    if (!cid || cid <= 0) {
      setError('Enter a valid customer ID');
      return;
    }
    if (selected.size === 0) {
      setError('Select at least one scenario');
      return;
    }

    setError(null);
    setStarting(true);
    setExpanded(new Set());

    try {
      // Sort selected IDs in canonical order
      const orderedIds = scenarios.map(s => s.id).filter(id => selected.has(id));
      const { run_id } = await api.startRun(orderedIds, cid);
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
