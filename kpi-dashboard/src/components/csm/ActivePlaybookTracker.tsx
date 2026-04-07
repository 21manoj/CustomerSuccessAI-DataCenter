/**
 * ActivePlaybookTracker — Shows in-progress playbook executions on Home view.
 *
 * Polls GET /api/dc2s/playbooks/executions?status=in_progress every 120s.
 * Compact cards with progress, health delta, days active.
 */

import React, { useState, useEffect, useRef } from 'react';
import { Play, Clock, TrendingUp, TrendingDown, Minus, RefreshCw } from 'lucide-react';
import { classifyColor } from '../../utils/healthThresholds';

interface ActiveExecution {
  execution_id: string;
  account_id: number;
  account_name: string;
  playbook_id: string;
  playbook_name?: string;
  status: string;
  triggered_at: string;
  health_at_trigger?: number;
  current_health?: number;
  arr?: number;
  actions_planned?: number;
  actions_completed?: number;
}

interface ActivePlaybookTrackerProps {
  customerId: string;
}

function daysSince(iso: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(iso + 'Z').getTime()) / 86400000));
}

function formatCompact(v: number): string {
  if (v >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `$${Math.round(v / 1e3)}K`;
  return `$${v}`;
}

const ActivePlaybookTracker: React.FC<ActivePlaybookTrackerProps> = ({ customerId }) => {
  const [executions, setExecutions] = useState<ActiveExecution[]>([]);
  const [loading, setLoading] = useState(false);
  const mounted = useRef(true);

  const fetchActive = async () => {
    try {
      setLoading(true);
      const resp = await fetch('/api/dc2s/playbooks/executions?status=in_progress', {
        headers: { 'X-Customer-ID': customerId },
        credentials: 'include',
      });
      if (!resp.ok) return;
      const data = await resp.json();
      if (!mounted.current) return;
      const list = data.executions || data.active_playbooks || [];
      setExecutions(Array.isArray(list) ? list : []);
    } catch {
      // Silent
    } finally {
      if (mounted.current) setLoading(false);
    }
  };

  useEffect(() => {
    mounted.current = true;
    fetchActive();
    const interval = setInterval(fetchActive, 120000);
    return () => { mounted.current = false; clearInterval(interval); };
  }, [customerId]);

  if (executions.length === 0) return null;

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Play className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-semibold text-blue-800 uppercase tracking-wide">
            Active Playbooks ({executions.length})
          </h3>
        </div>
        <button onClick={fetchActive} className="p-1 hover:bg-blue-100 rounded">
          <RefreshCw className={`w-3.5 h-3.5 text-blue-400 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
      <div className="space-y-2">
        {executions.map((ex) => {
          const days = daysSince(ex.triggered_at);
          const healthDelta = ex.current_health && ex.health_at_trigger
            ? ex.current_health - ex.health_at_trigger : 0;
          const progress = ex.actions_planned && ex.actions_planned > 0
            ? Math.round((ex.actions_completed || 0) / ex.actions_planned * 100) : 0;

          return (
            <div key={ex.execution_id} className="bg-white rounded-lg border border-blue-100 p-3 flex items-center gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 truncate">{ex.account_name}</span>
                  <span className="text-[10px] font-mono text-blue-500 bg-blue-50 px-1.5 py-0.5 rounded">{ex.playbook_id}</span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" /> Day {days}
                  </span>
                  {ex.arr && <span>{formatCompact(ex.arr)}</span>}
                  {healthDelta !== 0 && (
                    <span className={`flex items-center gap-0.5 ${healthDelta > 0 ? 'text-green-600' : 'text-red-500'}`}>
                      {healthDelta > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      {healthDelta > 0 ? '+' : ''}{healthDelta.toFixed(0)}
                    </span>
                  )}
                </div>
              </div>
              {/* Progress bar */}
              {ex.actions_planned && ex.actions_planned > 0 && (
                <div className="w-16">
                  <div className="w-full h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${progress}%` }} />
                  </div>
                  <p className="text-[9px] text-gray-400 text-center mt-0.5">{progress}%</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ActivePlaybookTracker;
