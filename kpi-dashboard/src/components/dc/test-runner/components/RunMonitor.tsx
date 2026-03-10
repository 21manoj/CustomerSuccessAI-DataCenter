/**
 * RunMonitor — Active run progress display with expandable per-scenario results
 *
 * Extracted from DCTestRunner.tsx lines 772-953.
 */

import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';

import type { RunStatus } from '../types';
import { formatDuration, formatTime } from '../api';
import StatusBadge from './StatusBadge';

interface RunMonitorProps {
  activeRun: RunStatus;
}

const RunMonitor: React.FC<RunMonitorProps> = ({ activeRun }) => {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const isRunning = activeRun.status === 'running';
  const completedCount =
    activeRun.scenarios.filter(s => s.status === 'pass' || s.status === 'fail').length;
  const totalCount = activeRun.scenarios.length;
  const progressPct = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const toggleExpanded = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
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
  );
};

export default RunMonitor;
