/**
 * RunHistory — Table of past test runs with click-to-load details
 *
 * Extracted from DCTestRunner.tsx lines 959-1028.
 */

import React from 'react';
import { Trash2, RefreshCw } from 'lucide-react';

import type { RunSummary, RunStatus } from '../types';
import { formatDuration, testRunnerApi } from '../api';
import StatusBadge from './StatusBadge';

interface RunHistoryProps {
  history: RunSummary[];
  setHistory: React.Dispatch<React.SetStateAction<RunSummary[]>>;
  setActiveRun: React.Dispatch<React.SetStateAction<RunStatus | null>>;
}

const RunHistory: React.FC<RunHistoryProps> = ({ history, setHistory, setActiveRun }) => {
  const handleDelete = async (e: React.MouseEvent, runId: string) => {
    e.stopPropagation();
    await testRunnerApi.deleteRun(runId);
    setHistory(prev => prev.filter(r => r.run_id !== runId));
  };

  const handleRefresh = () => {
    testRunnerApi.getRuns().then(setHistory).catch(() => {});
  };

  if (history.length === 0) return null;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">Run History</h3>
        <button
          onClick={handleRefresh}
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
                  testRunnerApi.getStatus(run.run_id).then(setActiveRun).catch(() => {});
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
                    onClick={e => handleDelete(e, run.run_id)}
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
  );
};

export default RunHistory;
