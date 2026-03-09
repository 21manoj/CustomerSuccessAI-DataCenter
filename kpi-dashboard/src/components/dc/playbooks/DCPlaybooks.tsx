/**
 * DC Playbooks Command Center
 * ============================
 * Manages all 6 DC playbooks (PB-01 through PB-06) with:
 * - Catalog view grouped by phase
 * - Execution panel with step-level hours tracking
 * - Reports with estimated vs actual hours analysis
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Zap, Play, Clock, CheckCircle, XCircle, AlertTriangle,
  FileText, BarChart3, ChevronRight, Pause, X, Target,
  TrendingUp, Users, Download, ArrowLeft, Loader2
} from 'lucide-react';

// ============================================================
// TYPES
// ============================================================

interface SubComponent {
  id: string;
  name: string;
  description: string;
  estimated_hours: number;
}

interface PlaybookDef {
  id: string;
  name: string;
  description: string;
  trigger_kpis: string[];
  trigger_conditions: Record<string, { operator: string; value: number }>;
  automation_level: string;
  human_approval_required: boolean;
  estimated_impact: string;
  phases: string[];
  estimated_duration_days: number;
  estimated_duration_display: string;
  sub_components: SubComponent[];
  total_estimated_hours: number;
}

interface StepTracking {
  step_id: string;
  name: string;
  description: string;
  estimated_hours: number;
  actual_hours: number | null;
  status: string;
  notes: string;
  started_at: string | null;
  completed_at: string | null;
}

interface Execution {
  execution_id: string;
  playbook_id: string;
  playbook_name: string;
  account_id: number | string;
  account_name: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  steps: StepTracking[];
  total_estimated_hours: number;
  total_actual_hours: number;
  current_step: string | null;
  phase: string;
}

interface ExecutionSummary {
  execution_id: string;
  playbook_id: string;
  playbook_name: string;
  account_id: number | string;
  account_name: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  steps_completed: number;
  total_steps: number;
  total_estimated_hours: number;
  total_actual_hours: number;
  progress: number;
}

interface KpiImpact {
  kpi_code: string;
  kpi_name: string;
  before: number | null;
  after: number | null;
  target: number | null;
  unit: string;
  improvement: string;
  status: string;
}

interface HoursStep {
  step_id: string;
  name: string;
  estimated_hours: number;
  actual_hours: number;
  variance: number;
  status: string;
  notes: string;
}

interface Report {
  execution_id: string;
  playbook_id: string;
  playbook_name: string;
  account_name: string;
  status: string;
  started_at: string;
  completed_at: string;
  duration_days: number;
  executive_summary: string;
  hours_tracking: {
    total_estimated_hours: number;
    total_actual_hours: number;
    variance_hours: number;
    variance_percent: number;
    efficiency_rating: string;
    steps: HoursStep[];
  };
  kpi_impact: {
    trigger_kpis: KpiImpact[];
    health_score_before: number;
    health_score_after: number;
    health_improvement: string;
    financial_impact: string;
  };
  raci_matrix: Record<string, Record<string, string>>;
  exit_criteria: Array<{ criteria: string; status: string; evidence: string }>;
  next_steps: string[];
  learnings: string[];
}

interface AccountOption {
  account_id: number | string;
  account_name: string;
}

// ============================================================
// CONSTANTS
// ============================================================

const PHASE_META: Record<string, { label: string; color: string; bg: string; border: string }> = {
  deployment: { label: 'Deployment', color: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-200' },
  performance: { label: 'Performance', color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200' },
  excellence: { label: 'Excellence', color: 'text-emerald-700', bg: 'bg-emerald-50', border: 'border-emerald-200' },
};

type SubTab = 'catalog' | 'active' | 'reports';

// ============================================================
// MAIN COMPONENT
// ============================================================

const DCPlaybooks: React.FC = () => {
  const [subTab, setSubTab] = useState<SubTab>('catalog');
  const [playbooks, setPlaybooks] = useState<PlaybookDef[]>([]);
  const [executions, setExecutions] = useState<ExecutionSummary[]>([]);
  const [accounts, setAccounts] = useState<AccountOption[]>([]);
  const [loading, setLoading] = useState(true);

  // Execution mode
  const [activeExecution, setActiveExecution] = useState<Execution | null>(null);
  const [startingPlaybook, setStartingPlaybook] = useState<PlaybookDef | null>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<number | string | null>(null);

  // Reports
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);

  // ---- Data Fetching ----

  const fetchPlaybooks = useCallback(async () => {
    try {
      const res = await fetch('/api/dc2s/playbooks');
      if (res.ok) {
        const data = await res.json();
        setPlaybooks(data.playbooks || []);
      }
    } catch (err) {
      console.error('Failed to fetch playbooks:', err);
    }
  }, []);

  const fetchExecutions = useCallback(async () => {
    try {
      const res = await fetch('/api/dc2s/playbooks/executions');
      if (res.ok) {
        const data = await res.json();
        setExecutions(data.executions || []);
      }
    } catch (err) {
      console.error('Failed to fetch executions:', err);
    }
  }, []);

  const fetchAccounts = useCallback(async () => {
    try {
      const res = await fetch('/api/dc2s/accounts');
      if (res.ok) {
        const data = await res.json();
        setAccounts((data.accounts || []).map((a: any) => ({
          account_id: a.account_id,
          account_name: a.account_name,
        })));
      }
    } catch (err) {
      console.error('Failed to fetch accounts:', err);
    }
  }, []);

  useEffect(() => {
    Promise.all([fetchPlaybooks(), fetchExecutions(), fetchAccounts()]).finally(() => setLoading(false));
  }, [fetchPlaybooks, fetchExecutions, fetchAccounts]);

  // Poll active executions
  useEffect(() => {
    const interval = setInterval(fetchExecutions, 10000);
    return () => clearInterval(interval);
  }, [fetchExecutions]);

  // ---- Actions ----

  const handleStartPlaybook = async () => {
    if (!startingPlaybook || !selectedAccountId) return;
    try {
      const res = await fetch('/api/dc2s/playbooks/executions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ playbook_id: startingPlaybook.id, account_id: selectedAccountId }),
      });
      if (res.ok) {
        const data = await res.json();
        setActiveExecution(data.execution);
        setStartingPlaybook(null);
        setSubTab('active');
        fetchExecutions();
      }
    } catch (err) {
      console.error('Failed to start playbook:', err);
    }
  };

  const handleUpdateStep = async (stepId: string, updates: Partial<StepTracking>) => {
    if (!activeExecution) return;
    try {
      const res = await fetch(
        `/api/dc2s/playbooks/executions/${activeExecution.execution_id}/steps/${stepId}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updates),
        }
      );
      if (res.ok) {
        const data = await res.json();
        setActiveExecution(data.execution);
      }
    } catch (err) {
      console.error('Failed to update step:', err);
    }
  };

  const handleCompletePlaybook = async () => {
    if (!activeExecution) return;
    try {
      const res = await fetch(
        `/api/dc2s/playbooks/executions/${activeExecution.execution_id}/complete`,
        { method: 'PUT' }
      );
      if (res.ok) {
        const data = await res.json();
        setActiveExecution(null);
        setSelectedReport(data.report);
        setSubTab('reports');
        fetchExecutions();
      }
    } catch (err) {
      console.error('Failed to complete playbook:', err);
    }
  };

  const handleViewExecution = async (execId: string) => {
    try {
      const res = await fetch(`/api/dc2s/playbooks/executions/${execId}`);
      if (res.ok) {
        const data = await res.json();
        if (data.execution.status === 'completed') {
          // Load report instead
          handleViewReport(execId);
        } else {
          setActiveExecution(data.execution);
        }
      }
    } catch (err) {
      console.error('Failed to load execution:', err);
    }
  };

  const handleViewReport = async (execId: string) => {
    try {
      setLoadingReport(true);
      const res = await fetch(`/api/dc2s/playbooks/executions/${execId}/report`);
      if (res.ok) {
        const data = await res.json();
        setSelectedReport(data.report);
      }
    } catch (err) {
      console.error('Failed to load report:', err);
    } finally {
      setLoadingReport(false);
    }
  };

  // ---- Group playbooks by phase ----

  const groupedPlaybooks: Record<string, PlaybookDef[]> = {};
  for (const pb of playbooks) {
    const primaryPhase = pb.phases[0] || 'deployment';
    if (!groupedPlaybooks[primaryPhase]) groupedPlaybooks[primaryPhase] = [];
    groupedPlaybooks[primaryPhase].push(pb);
  }

  const activeExecutions = executions.filter(e => e.status === 'in-progress');
  const completedExecutions = executions.filter(e => e.status === 'completed');

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-3 text-gray-600">Loading playbooks...</span>
      </div>
    );
  }

  // ============================================================
  // RENDER: Report Modal
  // ============================================================

  if (selectedReport) {
    const r = selectedReport;
    const ht = r.hours_tracking;
    return (
      <div className="space-y-6">
        {/* Back button */}
        <button
          onClick={() => setSelectedReport(null)}
          className="flex items-center text-blue-600 hover:text-blue-800 font-medium"
        >
          <ArrowLeft className="h-4 w-4 mr-1" /> Back to Playbooks
        </button>

        {/* Report Header */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">{r.playbook_name} - Execution Report</h2>
              <div className="flex items-center gap-3 mt-1 text-sm text-gray-600">
                <span className="font-medium">{r.account_name}</span>
                <span>|</span>
                <span>{r.duration_days} days</span>
                <span>|</span>
                <span className="px-2 py-0.5 bg-green-100 text-green-800 rounded text-xs font-medium">{r.status}</span>
              </div>
            </div>
            <button
              onClick={() => alert('Export coming soon')}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
            >
              <Download className="h-4 w-4" /> Export
            </button>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center gap-2">
            <Target className="h-5 w-5 text-blue-600" /> Executive Summary
          </h3>
          <p className="text-gray-700 leading-relaxed">{r.executive_summary}</p>
        </div>

        {/* Hours Tracking Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Clock className="h-5 w-5 text-indigo-600" /> Hours Tracking
          </h3>
          <div className="mb-4 grid grid-cols-4 gap-4">
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <div className="text-2xl font-bold text-gray-900">{ht.total_estimated_hours}h</div>
              <div className="text-xs text-gray-500">Estimated</div>
            </div>
            <div className="p-3 bg-gray-50 rounded-lg text-center">
              <div className="text-2xl font-bold text-gray-900">{ht.total_actual_hours}h</div>
              <div className="text-xs text-gray-500">Actual</div>
            </div>
            <div className={`p-3 rounded-lg text-center ${ht.variance_hours <= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
              <div className={`text-2xl font-bold ${ht.variance_hours <= 0 ? 'text-green-700' : 'text-red-700'}`}>
                {ht.variance_hours > 0 ? '+' : ''}{ht.variance_hours}h
              </div>
              <div className="text-xs text-gray-500">Variance</div>
            </div>
            <div className={`p-3 rounded-lg text-center ${ht.efficiency_rating === 'Under Budget' ? 'bg-green-50' : ht.efficiency_rating === 'On Budget' ? 'bg-blue-50' : 'bg-red-50'}`}>
              <div className={`text-lg font-bold ${ht.efficiency_rating === 'Under Budget' ? 'text-green-700' : ht.efficiency_rating === 'On Budget' ? 'text-blue-700' : 'text-red-700'}`}>
                {ht.efficiency_rating}
              </div>
              <div className="text-xs text-gray-500">{ht.variance_percent > 0 ? '+' : ''}{ht.variance_percent}%</div>
            </div>
          </div>
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Step</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase">Estimated</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase">Actual</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase">Variance</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Notes</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {ht.steps.map((step) => (
                <tr key={step.step_id}>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{step.name}</td>
                  <td className="px-4 py-3 text-sm text-right text-gray-600">{step.estimated_hours}h</td>
                  <td className="px-4 py-3 text-sm text-right text-gray-900 font-medium">{step.actual_hours}h</td>
                  <td className={`px-4 py-3 text-sm text-right font-medium ${step.variance <= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {step.variance > 0 ? '+' : ''}{step.variance}h
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      step.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'
                    }`}>{step.status}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">{step.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* KPI Impact */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-green-600" /> KPI Impact
          </h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500">Health Score</div>
              <div className="text-lg font-bold">
                {r.kpi_impact.health_score_before} → {r.kpi_impact.health_score_after}
                <span className="ml-2 text-sm text-green-600">{r.kpi_impact.health_improvement}</span>
              </div>
            </div>
            {r.kpi_impact.financial_impact && (
              <div className="p-3 bg-green-50 rounded-lg">
                <div className="text-sm text-gray-500">Financial Impact</div>
                <div className="text-lg font-bold text-green-700">{r.kpi_impact.financial_impact}</div>
              </div>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {r.kpi_impact.trigger_kpis.map((ki) => (
              <div key={ki.kpi_code} className="p-4 border border-gray-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-900">{ki.kpi_name}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    ki.status === 'Achieved' || ki.status === 'Exceeded' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>{ki.status}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Before: <strong>{ki.before ?? 'N/A'}</strong></span>
                  <span className="text-gray-500">After: <strong className="text-green-600">{ki.after ?? 'N/A'}</strong></span>
                  <span className="text-gray-500">Target: {ki.target ?? 'N/A'} {ki.unit}</span>
                </div>
                <div className="mt-1 text-sm font-semibold text-blue-600">{ki.improvement}</div>
              </div>
            ))}
          </div>
        </div>

        {/* RACI Matrix */}
        {r.raci_matrix && Object.keys(r.raci_matrix).length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Users className="h-5 w-5 text-purple-600" /> RACI Matrix
            </h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">Activity</th>
                    {Object.keys(Object.values(r.raci_matrix)[0] || {}).map(role => (
                      <th key={role} className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">{role}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {Object.entries(r.raci_matrix).map(([activity, roles]) => (
                    <tr key={activity}>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{activity}</td>
                      {Object.values(roles).map((role, i) => (
                        <td key={i} className="px-4 py-3 text-sm">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            role === 'Responsible' ? 'bg-blue-100 text-blue-800' :
                            role === 'Accountable' ? 'bg-purple-100 text-purple-800' :
                            role === 'Consulted' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-600'
                          }`}>{role}</span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Exit Criteria */}
        {r.exit_criteria && r.exit_criteria.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" /> Exit Criteria
            </h3>
            <div className="space-y-2">
              {r.exit_criteria.map((ec, idx) => (
                <div key={idx} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                  {ec.status === 'Met' ? (
                    <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500 mt-0.5" />
                  )}
                  <div>
                    <p className="font-medium text-gray-900">{ec.criteria}</p>
                    <p className="text-sm text-gray-600">{ec.evidence}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Next Steps & Learnings */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {r.next_steps && r.next_steps.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Next Steps</h3>
              <ul className="space-y-2">
                {r.next_steps.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <span className="text-blue-600 font-bold mt-0.5">→</span>
                    <span className="text-gray-700">{step}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {r.learnings && r.learnings.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Learnings</h3>
              <ul className="space-y-2">
                {r.learnings.map((lr, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <span className="text-amber-500 font-bold mt-0.5">*</span>
                    <span className="text-gray-700">{lr}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ============================================================
  // RENDER: Active Execution Panel
  // ============================================================

  if (activeExecution) {
    const ex = activeExecution;
    const completedSteps = ex.steps.filter(s => s.status === 'completed').length;
    const progress = ex.steps.length > 0 ? Math.round((completedSteps / ex.steps.length) * 100) : 0;
    const allDone = completedSteps === ex.steps.length;

    return (
      <div className="space-y-6">
        <button
          onClick={() => setActiveExecution(null)}
          className="flex items-center text-blue-600 hover:text-blue-800 font-medium"
        >
          <ArrowLeft className="h-4 w-4 mr-1" /> Back to Playbooks
        </button>

        {/* Execution Header */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-gray-900">{ex.playbook_name}</h2>
              <div className="flex items-center gap-3 mt-1 text-sm text-gray-600">
                <span className="font-medium">{ex.account_name}</span>
                <span>|</span>
                <span>Started: {new Date(ex.started_at).toLocaleDateString()}</span>
                <span className="px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded text-xs font-medium">{ex.status}</span>
              </div>
            </div>
            <div className="flex gap-2">
              {allDone && (
                <button
                  onClick={handleCompletePlaybook}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium"
                >
                  <CheckCircle className="h-4 w-4" /> Complete & Generate Report
                </button>
              )}
            </div>
          </div>
          {/* Progress bar */}
          <div className="mt-4">
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600">{completedSteps}/{ex.steps.length} steps completed</span>
              <span className="font-medium text-gray-900">{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div className="bg-blue-600 h-2.5 rounded-full transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
          {/* Hours summary */}
          <div className="mt-4 flex gap-6 text-sm">
            <div>
              <span className="text-gray-500">Estimated:</span>{' '}
              <span className="font-semibold">{ex.total_estimated_hours}h</span>
            </div>
            <div>
              <span className="text-gray-500">Actual so far:</span>{' '}
              <span className="font-semibold">{ex.total_actual_hours}h</span>
            </div>
            <div>
              <span className="text-gray-500">Variance:</span>{' '}
              <span className={`font-semibold ${ex.total_actual_hours - ex.total_estimated_hours <= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {ex.total_actual_hours - ex.total_estimated_hours > 0 ? '+' : ''}
                {(ex.total_actual_hours - ex.total_estimated_hours).toFixed(1)}h
              </span>
            </div>
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-3">
          {ex.steps.map((step, idx) => (
            <div key={step.step_id} className={`bg-white rounded-xl shadow-sm border p-5 ${
              step.status === 'completed' ? 'border-green-200 bg-green-50/30' :
              step.status === 'in-progress' ? 'border-blue-200 bg-blue-50/30' :
              'border-gray-100'
            }`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-xs font-mono text-gray-400">S{idx + 1}</span>
                    <h4 className="font-semibold text-gray-900">{step.name}</h4>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      step.status === 'completed' ? 'bg-green-100 text-green-800' :
                      step.status === 'in-progress' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-600'
                    }`}>{step.status}</span>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">{step.description}</p>
                  <div className="flex items-center gap-4">
                    {/* Status buttons */}
                    {step.status === 'pending' && (
                      <button
                        onClick={() => handleUpdateStep(step.step_id, { status: 'in-progress' })}
                        className="text-xs px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                      >
                        Start
                      </button>
                    )}
                    {step.status === 'in-progress' && (
                      <button
                        onClick={() => handleUpdateStep(step.step_id, { status: 'completed' })}
                        className="text-xs px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
                      >
                        Mark Complete
                      </button>
                    )}
                    {/* Actual hours input */}
                    <div className="flex items-center gap-2">
                      <label className="text-xs text-gray-500">Actual hours:</label>
                      <input
                        type="number"
                        min="0"
                        step="0.5"
                        value={step.actual_hours ?? ''}
                        onChange={(e) => {
                          const val = e.target.value === '' ? null : parseFloat(e.target.value);
                          handleUpdateStep(step.step_id, { actual_hours: val as any });
                        }}
                        className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                        placeholder="0"
                      />
                      <span className="text-xs text-gray-400">/ {step.estimated_hours}h est.</span>
                    </div>
                    {/* Notes */}
                    <input
                      type="text"
                      value={step.notes || ''}
                      onChange={(e) => handleUpdateStep(step.step_id, { notes: e.target.value })}
                      className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                      placeholder="Notes..."
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ============================================================
  // RENDER: Start Playbook Dialog
  // ============================================================

  const startDialog = startingPlaybook && (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-lg p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-bold text-gray-900 mb-2">Start {startingPlaybook.name}</h3>
        <p className="text-sm text-gray-600 mb-4">{startingPlaybook.description}</p>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Select Account</label>
          <select
            value={selectedAccountId || ''}
            onChange={(e) => setSelectedAccountId(e.target.value ? parseInt(e.target.value) : null)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">Choose an account...</option>
            {accounts.map(a => (
              <option key={a.account_id} value={a.account_id}>{a.account_name}</option>
            ))}
          </select>
        </div>
        <div className="text-sm text-gray-500 mb-4">
          <div>Duration: {startingPlaybook.estimated_duration_display}</div>
          <div>Estimated hours: {startingPlaybook.total_estimated_hours}h</div>
          <div>Steps: {startingPlaybook.sub_components.length}</div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => { setStartingPlaybook(null); setSelectedAccountId(null); }}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 text-sm"
          >
            Cancel
          </button>
          <button
            onClick={handleStartPlaybook}
            disabled={!selectedAccountId}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
          >
            Start Playbook
          </button>
        </div>
      </div>
    </div>
  );

  // ============================================================
  // RENDER: Main View with Sub-Tabs
  // ============================================================

  return (
    <div className="space-y-6">
      {startDialog}

      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2">
          <Zap className="h-7 w-7 text-indigo-600" />
          DC Playbook Command Center
        </h2>
        <p className="text-gray-600 text-sm">
          6 data center playbooks across deployment, performance, and excellence phases
        </p>
      </div>

      {/* Sub-tabs */}
      <div className="flex space-x-1 border-b border-gray-200">
        {[
          { id: 'catalog' as SubTab, label: 'Catalog', count: playbooks.length },
          { id: 'active' as SubTab, label: 'Active Executions', count: activeExecutions.length },
          { id: 'reports' as SubTab, label: 'Reports', count: completedExecutions.length },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setSubTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              subTab === tab.id
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {tab.label}
            {tab.count > 0 && (
              <span className={`ml-2 px-1.5 py-0.5 rounded-full text-xs ${
                subTab === tab.id ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'
              }`}>{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* CATALOG TAB */}
      {subTab === 'catalog' && (
        <div className="space-y-8">
          {['deployment', 'performance', 'excellence'].map(phase => {
            const pbs = groupedPlaybooks[phase] || [];
            if (pbs.length === 0) return null;
            const pm = PHASE_META[phase];
            return (
              <div key={phase}>
                <h3 className={`text-lg font-semibold mb-3 ${pm.color}`}>{pm.label} Phase</h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {pbs.map(pb => (
                    <div key={pb.id} className={`bg-white rounded-xl shadow-sm border ${pm.border} p-5 hover:shadow-md transition-shadow`}>
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-mono font-bold text-gray-400">{pb.id}</span>
                            <h4 className="font-semibold text-gray-900">{pb.name}</h4>
                          </div>
                          <p className="text-sm text-gray-600">{pb.description}</p>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs text-gray-500 mb-3">
                        <div><span className="font-medium">Duration:</span> {pb.estimated_duration_display}</div>
                        <div><span className="font-medium">Hours:</span> {pb.total_estimated_hours}h</div>
                        <div><span className="font-medium">Automation:</span> {pb.automation_level}</div>
                        <div><span className="font-medium">Steps:</span> {pb.sub_components.length}</div>
                      </div>
                      <div className="text-xs text-gray-500 mb-2">
                        <span className="font-medium">Triggers:</span>{' '}
                        {pb.trigger_kpis.join(', ')}
                      </div>
                      {pb.estimated_impact && (
                        <div className={`text-xs font-medium ${pm.color} mb-3`}>
                          Impact: {pb.estimated_impact}
                        </div>
                      )}
                      {/* Phases tags */}
                      <div className="flex items-center gap-2 mb-3">
                        {pb.phases.map(p => (
                          <span key={p} className={`px-2 py-0.5 rounded text-xs ${PHASE_META[p]?.bg || 'bg-gray-50'} ${PHASE_META[p]?.color || 'text-gray-600'}`}>
                            {PHASE_META[p]?.label || p}
                          </span>
                        ))}
                        {pb.human_approval_required && (
                          <span className="px-2 py-0.5 rounded text-xs bg-red-50 text-red-700">Approval Required</span>
                        )}
                      </div>
                      <button
                        onClick={() => setStartingPlaybook(pb)}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 text-sm font-medium"
                      >
                        <Play className="h-4 w-4" /> Start Playbook
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ACTIVE EXECUTIONS TAB */}
      {subTab === 'active' && (
        <div className="space-y-4">
          {activeExecutions.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
              <Zap className="h-16 w-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No Active Executions</h3>
              <p className="text-gray-600 text-sm">Start a playbook from the Catalog tab to see it here.</p>
            </div>
          ) : (
            activeExecutions.map(ex => (
              <div
                key={ex.execution_id}
                className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => handleViewExecution(ex.execution_id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-xs font-mono text-gray-400">{ex.playbook_id}</span>
                      <h4 className="font-semibold text-gray-900">{ex.playbook_name}</h4>
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">{ex.account_name}</span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <span>{ex.steps_completed}/{ex.total_steps} steps</span>
                      <span>{ex.total_actual_hours}h / {ex.total_estimated_hours}h</span>
                      <span>Started: {new Date(ex.started_at).toLocaleDateString()}</span>
                    </div>
                    <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                      <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${ex.progress}%` }} />
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* REPORTS TAB */}
      {subTab === 'reports' && (
        <div className="space-y-4">
          {loadingReport && (
            <div className="flex items-center justify-center p-8">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              <span className="ml-3 text-gray-600">Loading report...</span>
            </div>
          )}
          {completedExecutions.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
              <FileText className="h-16 w-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No Reports Yet</h3>
              <p className="text-gray-600 text-sm">Complete a playbook execution to generate a report.</p>
            </div>
          ) : (
            completedExecutions.map(ex => (
              <div
                key={ex.execution_id}
                className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => handleViewReport(ex.execution_id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-xs font-mono text-gray-400">{ex.playbook_id}</span>
                      <h4 className="font-semibold text-gray-900">{ex.playbook_name}</h4>
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">{ex.account_name}</span>
                      <span className="px-2 py-0.5 bg-green-100 text-green-800 text-xs rounded font-medium">Completed</span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <span>{ex.total_actual_hours}h actual / {ex.total_estimated_hours}h estimated</span>
                      {ex.completed_at && <span>Completed: {new Date(ex.completed_at).toLocaleDateString()}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-green-600 text-sm font-medium">View Report</span>
                    <ChevronRight className="h-5 w-5 text-gray-400" />
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default DCPlaybooks;
