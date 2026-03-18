/**
 * ConsoleTab — Live stdout/stderr streaming viewer for test runs.
 *
 * Polls /api/test-runner/console/<run_id> every 1s for incremental output.
 * Shows a terminal-style dark panel with auto-scrolling, ANSI-aware rendering,
 * and toggle for stdout vs stderr.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Terminal,
  AlertTriangle,
  Loader2,
  Trash2,
  ChevronDown,
  Pause,
  Play,
  Download,
} from 'lucide-react';

interface ConsoleTabProps {
  customerId: string;
}

interface RunEntry {
  run_id: string;
  status: string;
  customer_id: string | number;
  start_time: string;
  scenario_count: number;
  summary?: { passed: number; failed: number };
}

interface ConsoleData {
  run_id: string;
  status: string;
  scenarios: Array<{
    id: string;
    name: string;
    status: string;
    stdout: string;
    stderr: string;
    stdout_offset: number;
    stderr_offset: number;
  }>;
}

// Strip ANSI escape codes for plain text display
function stripAnsi(str: string): string {
  // eslint-disable-next-line no-control-regex
  return str.replace(/\u001b\[[0-9;]*m/g, '');
}

const ConsoleTab: React.FC<ConsoleTabProps> = ({ customerId }) => {
  const [runs, setRuns] = useState<RunEntry[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [consoleData, setConsoleData] = useState<ConsoleData | null>(null);
  const [showStderr, setShowStderr] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [paused, setPaused] = useState(false);
  const logRef = useRef<HTMLPreElement>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch run list
  useEffect(() => {
    const fetchRuns = () => {
      fetch('/api/test-runner/runs', { credentials: 'include' })
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.runs) {
            setRuns(data.runs);
            // Auto-select the most recent running run
            if (!selectedRunId) {
              const running = data.runs.find((r: RunEntry) => r.status === 'running');
              if (running) {
                setSelectedRunId(running.run_id);
              } else if (data.runs.length > 0) {
                setSelectedRunId(data.runs[0].run_id);
              }
            }
          }
        })
        .catch(() => {});
    };

    fetchRuns();
    const interval = setInterval(fetchRuns, 5000);
    return () => clearInterval(interval);
  }, [selectedRunId]);

  // Poll console output for selected run
  useEffect(() => {
    if (!selectedRunId || paused) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }

    const fetchConsole = () => {
      fetch(`/api/test-runner/console/${selectedRunId}`, { credentials: 'include' })
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data) {
            setConsoleData(data);
          }
        })
        .catch(() => {});
    };

    fetchConsole();
    pollRef.current = setInterval(fetchConsole, 1000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [selectedRunId, paused]);

  // Auto-scroll
  useEffect(() => {
    if (autoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [consoleData, autoScroll, showStderr]);

  // Handle scroll — pause auto-scroll if user scrolls up
  const handleScroll = useCallback(() => {
    if (!logRef.current) return;
    const el = logRef.current;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
    setAutoScroll(atBottom);
  }, []);

  // Build combined output string
  const getOutput = () => {
    if (!consoleData?.scenarios) return '';
    return consoleData.scenarios
      .map(s => {
        const output = showStderr ? s.stderr : s.stdout;
        if (!output) return '';
        const header = `━━━ Scenario ${s.id}: ${s.name} [${s.status}] ━━━`;
        return `${header}\n${stripAnsi(output)}`;
      })
      .filter(Boolean)
      .join('\n\n');
  };

  // Download log
  const handleDownload = () => {
    const content = getOutput();
    if (!content) return;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedRunId || 'console'}_${showStderr ? 'stderr' : 'stdout'}.log`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const output = getOutput();
  const isRunActive = consoleData?.status === 'running';

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-emerald-600" />
          <h3 className="text-lg font-semibold text-gray-900">Console Output</h3>
        </div>

        {/* Run selector */}
        <div className="relative">
          <select
            value={selectedRunId || ''}
            onChange={e => { setSelectedRunId(e.target.value); setConsoleData(null); }}
            className="appearance-none pl-3 pr-8 py-1.5 border border-gray-300 rounded-lg text-sm bg-white cursor-pointer focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
          >
            <option value="">Select a run...</option>
            {runs.map(r => (
              <option key={r.run_id} value={r.run_id}>
                {r.run_id} ({r.status}) — CID {r.customer_id}
              </option>
            ))}
          </select>
          <ChevronDown className="w-4 h-4 text-gray-400 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>

        {/* Stdout / Stderr toggle */}
        <div className="flex rounded-lg border border-gray-200 overflow-hidden text-xs">
          <button
            onClick={() => setShowStderr(false)}
            className={`px-3 py-1.5 font-medium transition-colors ${
              !showStderr ? 'bg-emerald-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            stdout
          </button>
          <button
            onClick={() => setShowStderr(true)}
            className={`px-3 py-1.5 font-medium transition-colors ${
              showStderr ? 'bg-red-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            stderr
          </button>
        </div>

        {/* Controls */}
        <div className="ml-auto flex items-center gap-2">
          {isRunActive && (
            <span className="flex items-center gap-1.5 text-xs text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full">
              <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
              Live
            </span>
          )}

          <button
            onClick={() => setPaused(!paused)}
            className="p-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-700"
            title={paused ? 'Resume polling' : 'Pause polling'}
          >
            {paused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
          </button>

          <button
            onClick={handleDownload}
            className="p-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-700"
            title="Download log"
            disabled={!output}
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Scenario status chips */}
      {consoleData?.scenarios && consoleData.scenarios.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {consoleData.scenarios.map(s => (
            <span
              key={s.id}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                s.status === 'pass' ? 'bg-green-100 text-green-700' :
                s.status === 'fail' ? 'bg-red-100 text-red-700' :
                s.status === 'running' ? 'bg-blue-100 text-blue-700' :
                'bg-gray-100 text-gray-600'
              }`}
            >
              {s.status === 'running' && <Loader2 className="w-3 h-3 animate-spin" />}
              {s.status === 'fail' && <AlertTriangle className="w-3 h-3" />}
              {s.id}. {s.name}
            </span>
          ))}
        </div>
      )}

      {/* Terminal panel */}
      <div className="bg-gray-900 rounded-xl border border-gray-700 shadow-lg overflow-hidden">
        {/* Terminal title bar */}
        <div className="flex items-center gap-2 px-4 py-2 bg-gray-800 border-b border-gray-700">
          <div className="flex gap-1.5">
            <span className="w-3 h-3 rounded-full bg-red-500" />
            <span className="w-3 h-3 rounded-full bg-yellow-500" />
            <span className="w-3 h-3 rounded-full bg-green-500" />
          </div>
          <span className="text-xs text-gray-400 font-mono ml-2">
            {selectedRunId || 'no run selected'} — {showStderr ? 'stderr' : 'stdout'}
          </span>
          {!autoScroll && (
            <button
              onClick={() => {
                setAutoScroll(true);
                if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
              }}
              className="ml-auto text-xs text-yellow-400 hover:text-yellow-300"
            >
              ↓ Scroll to bottom
            </button>
          )}
        </div>

        {/* Log content */}
        <pre
          ref={logRef}
          onScroll={handleScroll}
          className={`p-4 overflow-auto font-mono text-xs leading-relaxed whitespace-pre-wrap break-words ${
            showStderr ? 'text-red-400' : 'text-green-400'
          }`}
          style={{ minHeight: '400px', maxHeight: 'calc(100vh - 320px)' }}
        >
          {output || (
            <span className="text-gray-500">
              {selectedRunId
                ? isRunActive
                  ? 'Waiting for output...'
                  : 'No output available for this run.'
                : 'Select a run to view console output.'
              }
            </span>
          )}
          {isRunActive && output && (
            <span className="animate-pulse text-gray-500">▊</span>
          )}
        </pre>
      </div>
    </div>
  );
};

export default ConsoleTab;
