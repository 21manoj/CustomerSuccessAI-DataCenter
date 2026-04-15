/**
 * ActivePlaybookTracker — Shows in-progress playbook executions on Home view.
 *
 * Polls GET /api/dc2s/playbooks/executions?status=in_progress every 120s.
 * Compact cards with progress, health delta, days active.
 * Click to expand: step checklist, phase badge, next action.
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Play, Clock, TrendingUp, TrendingDown, RefreshCw,
  CheckCircle2, Circle, CircleDot, ChevronDown, ChevronRight, Zap,
} from 'lucide-react';

interface PlaybookStep {
  step_id: string;
  name: string;
  description?: string;
  status: 'pending' | 'in-progress' | 'completed';
  estimated_hours?: number;
  actual_hours?: number;
  started_at?: string;
  completed_at?: string;
  notes?: string;
}

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
  steps?: PlaybookStep[];
  current_step?: string;
  phase?: string;
  progress?: number;
}

interface ActivePlaybookTrackerProps {
  customerId: string;
}

const PHASE_STYLES: Record<string, { bg: string; text: string }> = {
  stabilize: { bg: 'bg-red-100', text: 'text-red-700' },
  rebuild: { bg: 'bg-amber-100', text: 'text-amber-700' },
  secure: { bg: 'bg-green-100', text: 'text-green-700' },
};

function daysSince(iso: string): number {
  return Math.max(0, Math.floor((Date.now() - new Date(iso + 'Z').getTime()) / 86400000));
}

function formatCompact(v: number): string {
  if (v >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `$${Math.round(v / 1e3)}K`;
  return `$${v}`;
}

function StepIcon({ status }: { status: string }) {
  if (status === 'completed') return <CheckCircle2 className="w-3.5 h-3.5 text-green-600 flex-shrink-0" />;
  if (status === 'in-progress') return <CircleDot className="w-3.5 h-3.5 text-blue-600 flex-shrink-0 animate-pulse" />;
  return <Circle className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" />;
}

const ActivePlaybookTracker: React.FC<ActivePlaybookTrackerProps> = ({ customerId }) => {
  const [executions, setExecutions] = useState<ActiveExecution[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const mounted = useRef(true);

  const toggle = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

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
          const progress = ex.progress ?? (
            ex.actions_planned && ex.actions_planned > 0
              ? Math.round((ex.actions_completed || 0) / ex.actions_planned * 100) : 0
          );
          const isExpanded = expandedIds.has(ex.execution_id);
          const steps = ex.steps || [];
          const nextStep = steps.find((s) => s.status === 'pending' || s.status === 'in-progress');
          const phaseStyle = PHASE_STYLES[ex.phase || ''] || { bg: 'bg-gray-100', text: 'text-gray-600' };

          return (
            <div key={ex.execution_id} className="bg-white rounded-lg border border-blue-100 overflow-hidden">
              {/* Collapsed header — always visible */}
              <button
                className="w-full p-3 flex items-center gap-3 hover:bg-blue-50/50 transition-colors text-left"
                onClick={() => toggle(ex.execution_id)}
              >
                {isExpanded
                  ? <ChevronDown className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                  : <ChevronRight className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                }
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900 truncate">{ex.account_name}</span>
                    <span className="text-[10px] font-mono text-blue-500 bg-blue-50 px-1.5 py-0.5 rounded">{ex.playbook_id}</span>
                    {ex.phase && (
                      <span className={`text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded ${phaseStyle.bg} ${phaseStyle.text}`}>
                        {ex.phase}
                      </span>
                    )}
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
                <div className="w-16 flex-shrink-0">
                  <div className="w-full h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${progress}%` }} />
                  </div>
                  <p className="text-[9px] text-gray-400 text-center mt-0.5">{progress}%</p>
                </div>
              </button>

              {/* Expanded: step checklist */}
              {isExpanded && steps.length > 0 && (
                <div className="px-4 pb-3 pt-1 border-t border-blue-50">
                  {/* Next action highlight */}
                  {nextStep && (
                    <div className="flex items-center gap-2 mb-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                      <Zap className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                      <span className="text-xs text-amber-800">
                        <span className="font-semibold">Next:</span> {nextStep.name}
                        {nextStep.estimated_hours ? ` (~${nextStep.estimated_hours}h)` : ''}
                      </span>
                    </div>
                  )}
                  {/* Step list */}
                  <div className="space-y-1.5">
                    {steps.map((step) => (
                      <div
                        key={step.step_id}
                        className={`flex items-start gap-2 py-1 px-2 rounded ${
                          step.status === 'in-progress' ? 'bg-blue-50 border-l-2 border-blue-400' : ''
                        }`}
                      >
                        <StepIcon status={step.status} />
                        <div className="flex-1 min-w-0">
                          <span className={`text-xs ${step.status === 'completed' ? 'text-gray-400 line-through' : 'text-gray-700'}`}>
                            {step.name}
                          </span>
                          {step.actual_hours != null && step.actual_hours > 0 && (
                            <span className="text-[10px] text-gray-400 ml-2">{step.actual_hours}h</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  {/* Summary */}
                  <div className="mt-2 pt-2 border-t border-gray-100 flex items-center justify-between text-[10px] text-gray-400">
                    <span>{ex.actions_completed || 0} of {ex.actions_planned || steps.length} steps complete</span>
                    {ex.current_health != null && (
                      <span>Health: <span className="font-semibold text-gray-600">{ex.current_health.toFixed(0)}</span></span>
                    )}
                  </div>
                </div>
              )}

              {/* Expanded but no steps data */}
              {isExpanded && steps.length === 0 && (
                <div className="px-4 pb-3 pt-1 border-t border-blue-50">
                  <p className="text-xs text-gray-400 italic">No step details available for this playbook.</p>
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
