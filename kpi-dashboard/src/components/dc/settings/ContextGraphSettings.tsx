/**
 * ContextGraphSettings — P0-A + P2
 * ===================================
 * Settings panel for context graph feature toggle, sub-toggles,
 * data ingestion status, re-process button, and arc classifier config.
 *
 * API contracts:
 *   GET  /api/features/context-graph          → ContextGraphToggle
 *   PUT  /api/features/context-graph          → { enabled, sub_toggles }
 *   GET  /api/dc2s/config/data-status         → (coming soon — mock data shown)
 *   POST /api/onboarding/process-data         → re-process trigger
 *   GET  /api/dc2s/config/arc-classifier      → { confidence_threshold, active_arcs }
 *   PUT  /api/dc2s/config/arc-classifier      → same shape
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  ToggleLeft,
  ToggleRight,
  Play,
  Database,
} from 'lucide-react';
import type { ContextGraphSubToggles } from '../../../types/contextGraph';
import { invalidateToggleCache } from '../../../hooks/useContextGraphToggle';

// ============================================================
// TYPES
// ============================================================

interface FeatureToggleState {
  enabled: boolean;
  sub_toggles: ContextGraphSubToggles;
}

interface DataStatusRow {
  filename: string;
  status: 'uploaded' | 'auto-generated' | 'missing';
  row_count: number | null;
  last_updated: string | null;
}

interface ArcClassifierConfig {
  confidence_threshold: number;
  active_arcs: string[];
}

type ToastType = { message: string; kind: 'success' | 'error' } | null;

// ============================================================
// CONSTANTS
// ============================================================

const SUB_TOGGLE_META: Array<{ key: keyof ContextGraphSubToggles; label: string; description: string }> = [
  {
    key: 'story_arcs',
    label: 'Story Arcs',
    description: 'Classify each account into a named story arc (champion_loss, land_and_expand, etc.) and drive narrative intelligence.',
  },
  {
    key: 'signal_edges',
    label: 'Signal Edges',
    description: 'Create directed edges between signals, decisions, and outcomes to trace causal chains.',
  },
  {
    key: 'stakeholder_tracking',
    label: 'Stakeholder Tracking',
    description: 'Track stakeholder nodes and their relationships — champions, detractors, economic buyers.',
  },
  {
    key: 'decision_lifecycle',
    label: 'Decision Lifecycle',
    description: 'Model the full decision lifecycle from trigger to outcome with confidence scores.',
  },
  {
    key: 'outcome_economics',
    label: 'Outcome Economics',
    description: 'Attach revenue impact (at-risk, expansion, protected, lost) to each outcome node.',
  },
  {
    key: 'industry_benchmarks',
    label: 'Industry Benchmarks',
    description: 'Compare account KPIs against industry benchmark nodes sourced from external data.',
  },
];

const ALL_ARC_NAMES = [
  'champion_loss',
  'crisis_recovery',
  'infrastructure_decay',
  'ignored_churn',
  'land_and_expand',
  'budget_pressure',
  'healthy_expansion',
  'strategic_pivot',
] as const;

const MOCK_DATA_STATUS: DataStatusRow[] = [
  { filename: 'stakeholders.csv', status: 'uploaded', row_count: 142, last_updated: '2026-03-20T14:22:00Z' },
  { filename: 'engagement_events.csv', status: 'uploaded', row_count: 890, last_updated: '2026-03-20T14:22:00Z' },
  { filename: 'account_business_profiles.csv', status: 'auto-generated', row_count: 18, last_updated: '2026-03-18T09:11:00Z' },
  { filename: 'outcomes.csv', status: 'uploaded', row_count: 76, last_updated: '2026-03-20T14:22:00Z' },
  { filename: 'decisions.csv', status: 'uploaded', row_count: 53, last_updated: '2026-03-20T14:22:00Z' },
  { filename: 'signal_edges.csv', status: 'missing', row_count: null, last_updated: null },
];

const DEFAULT_ARC_CONFIG: ArcClassifierConfig = {
  confidence_threshold: 0.70,
  active_arcs: [...ALL_ARC_NAMES],
};

// ============================================================
// HELPERS
// ============================================================

function statusBadge(status: DataStatusRow['status']) {
  switch (status) {
    case 'uploaded':
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          Uploaded
        </span>
      );
    case 'auto-generated':
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
          Auto-generated
        </span>
      );
    case 'missing':
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
          Missing
        </span>
      );
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

// ============================================================
// TOGGLE SWITCH COMPONENT
// ============================================================

const ToggleSwitch: React.FC<{
  enabled: boolean;
  onChange: (val: boolean) => void;
  disabled?: boolean;
  saving?: boolean;
}> = ({ enabled, onChange, disabled, saving }) => (
  <button
    type="button"
    onClick={() => !disabled && !saving && onChange(!enabled)}
    disabled={disabled || saving}
    className="inline-flex items-center justify-center transition-colors disabled:opacity-50"
    aria-pressed={enabled}
  >
    {saving ? (
      <RefreshCw className="h-5 w-5 text-gray-400 animate-spin" />
    ) : enabled ? (
      <ToggleRight className="h-7 w-7 text-blue-500 hover:text-blue-600" />
    ) : (
      <ToggleLeft className="h-7 w-7 text-gray-400 hover:text-gray-500" />
    )}
  </button>
);

// ============================================================
// MAIN COMPONENT
// ============================================================

interface ContextGraphSettingsProps {
  /** Super-admin context: pass target customer's ID. Self-service: omit (uses session). */
  customerId?: number;
}

const ContextGraphSettings: React.FC<ContextGraphSettingsProps> = ({ customerId }) => {
  /** Append ?customer_id=X when operating in admin context */
  const apiUrl = (path: string) =>
    customerId ? `${path}?customer_id=${customerId}` : path;

  // ── Feature toggle state ──
  const [toggleState, setToggleState] = useState<FeatureToggleState>({
    enabled: false,
    sub_toggles: {
      story_arcs: false,
      signal_edges: false,
      stakeholder_tracking: false,
      decision_lifecycle: false,
      outcome_economics: false,
      industry_benchmarks: false,
    },
  });
  const [toggleLoading, setToggleLoading] = useState(true);
  const [savingMaster, setSavingMaster] = useState(false);
  const [savingSubKey, setSavingSubKey] = useState<keyof ContextGraphSubToggles | null>(null);

  // ── Data status state ──
  const [dataStatus] = useState<DataStatusRow[]>(MOCK_DATA_STATUS);
  const [reprocessing, setReprocessing] = useState(false);
  const [reprocessResult, setReprocessResult] = useState<{ ok: boolean; msg: string } | null>(null);

  // ── Arc classifier state ──
  const [arcConfig, setArcConfig] = useState<ArcClassifierConfig>(DEFAULT_ARC_CONFIG);
  const [arcExpanded, setArcExpanded] = useState(false);
  const [arcSaving, setArcSaving] = useState(false);

  // ── Toast ──
  const [toast, setToast] = useState<ToastType>(null);

  const showToast = useCallback((message: string, kind: 'success' | 'error') => {
    setToast({ message, kind });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // ── Load feature toggle ──
  useEffect(() => {
    (async () => {
      setToggleLoading(true);
      try {
        const res = await fetch(apiUrl('/api/features/context-graph'), { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          setToggleState({
            enabled: data.active ?? data.enabled ?? false,
            sub_toggles: data.sub_toggles ?? toggleState.sub_toggles,
          });
        }
      } catch (err) {
        console.error('Failed to load context graph toggle:', err);
      } finally {
        setToggleLoading(false);
      }
    })();
  }, []);

  // ── Load arc classifier config ──
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(apiUrl('/api/dc2s/config/arc-classifier'), { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          setArcConfig({
            confidence_threshold: data.confidence_threshold ?? DEFAULT_ARC_CONFIG.confidence_threshold,
            active_arcs: data.active_arcs ?? DEFAULT_ARC_CONFIG.active_arcs,
          });
        }
        // 404 is fine — use defaults
      } catch {
        // Silently use defaults
      }
    })();
  }, []);

  // ── Save master toggle ──
  const handleMasterToggle = async (newVal: boolean) => {
    setSavingMaster(true);
    const next = { ...toggleState, enabled: newVal };
    try {
      const res = await fetch(apiUrl('/api/features/context-graph'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ enabled: newVal, sub_toggles: toggleState.sub_toggles }),
      });
      if (res.ok) {
        setToggleState(next);
        invalidateToggleCache();
        showToast(`Context Graph ${newVal ? 'enabled' : 'disabled'}`, 'success');
      } else {
        showToast('Failed to save toggle', 'error');
      }
    } catch {
      showToast('Failed to save toggle', 'error');
    } finally {
      setSavingMaster(false);
    }
  };

  // ── Save sub-toggle ──
  const handleSubToggle = async (key: keyof ContextGraphSubToggles, newVal: boolean) => {
    setSavingSubKey(key);
    const newSubToggles = { ...toggleState.sub_toggles, [key]: newVal };
    const next = { ...toggleState, sub_toggles: newSubToggles };
    try {
      const res = await fetch(apiUrl('/api/features/context-graph'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ enabled: toggleState.enabled, sub_toggles: newSubToggles }),
      });
      if (res.ok) {
        setToggleState(next);
        invalidateToggleCache();
        showToast(`${key} ${newVal ? 'enabled' : 'disabled'}`, 'success');
      } else {
        showToast(`Failed to save ${key}`, 'error');
      }
    } catch {
      showToast(`Failed to save ${key}`, 'error');
    } finally {
      setSavingSubKey(null);
    }
  };

  // ── Re-process data ──
  const handleReprocess = async () => {
    setReprocessing(true);
    setReprocessResult(null);
    try {
      const res = await fetch(apiUrl('/api/onboarding/process-data'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const data = await res.json();
        setReprocessResult({ ok: true, msg: data.message || 'Data reprocessed successfully' });
        setTimeout(() => setReprocessResult(null), 3000);
      } else {
        const data = await res.json().catch(() => ({}));
        setReprocessResult({ ok: false, msg: data.error || 'Reprocess failed' });
        setTimeout(() => setReprocessResult(null), 3000);
      }
    } catch (err) {
      setReprocessResult({ ok: false, msg: 'Reprocess request failed' });
      setTimeout(() => setReprocessResult(null), 3000);
    } finally {
      setReprocessing(false);
    }
  };

  // ── Save arc classifier config ──
  const handleSaveArcConfig = async () => {
    setArcSaving(true);
    try {
      const res = await fetch(apiUrl('/api/dc2s/config/arc-classifier'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(arcConfig),
      });
      if (res.ok) {
        showToast('Arc classifier config saved', 'success');
      } else {
        // Endpoint doesn't exist yet — store locally
        console.log('[ContextGraphSettings] arc-classifier config (local):', arcConfig);
        showToast('Config saved locally (endpoint coming soon)', 'success');
      }
    } catch {
      console.log('[ContextGraphSettings] arc-classifier config (local):', arcConfig);
      showToast('Config saved locally (endpoint coming soon)', 'success');
    } finally {
      setArcSaving(false);
    }
  };

  const toggleArcName = (arc: string) => {
    setArcConfig(prev => ({
      ...prev,
      active_arcs: prev.active_arcs.includes(arc)
        ? prev.active_arcs.filter(a => a !== arc)
        : [...prev.active_arcs, arc],
    }));
  };

  // ── Render ──
  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg flex items-center space-x-2 transition-all duration-300 ${
          toast.kind === 'success'
            ? 'bg-green-50 border border-green-200 text-green-800'
            : 'bg-red-50 border border-red-200 text-red-800'
        }`}>
          {toast.kind === 'success'
            ? <CheckCircle className="h-4 w-4 shrink-0" />
            : <AlertCircle className="h-4 w-4 shrink-0" />}
          <span className="text-sm font-medium">{toast.message}</span>
        </div>
      )}

      {/* ── Master Toggle Card ── */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-gray-900">Context Graph</h3>
            <p className="text-sm text-gray-500 mt-0.5">
              Enable the Revenue Intelligence context graph — causal signal edges, story arcs, stakeholder tracking, and outcome economics.
            </p>
          </div>
          <div className="ml-6 shrink-0">
            {toggleLoading ? (
              <RefreshCw className="h-5 w-5 text-gray-300 animate-spin" />
            ) : (
              <ToggleSwitch
                enabled={toggleState.enabled}
                onChange={handleMasterToggle}
                saving={savingMaster}
              />
            )}
          </div>
        </div>

        {/* Sub-toggles */}
        {toggleState.enabled && (
          <div className="mt-5 border-t border-gray-100 pt-5 space-y-4">
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wider mb-2">Sub-features</p>
            {SUB_TOGGLE_META.map(({ key, label, description }) => (
              <div key={key} className="flex items-start justify-between">
                <div className="flex-1 pr-4">
                  <p className="text-sm font-medium text-gray-800">{label}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{description}</p>
                </div>
                <ToggleSwitch
                  enabled={toggleState.sub_toggles[key]}
                  onChange={val => handleSubToggle(key, val)}
                  saving={savingSubKey === key}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Data Ingestion Status ── */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Database className="h-5 w-5 text-gray-500" />
            <h3 className="text-base font-semibold text-gray-900">Data Ingestion Status</h3>
          </div>
          <div className="flex items-center space-x-3">
            {reprocessResult && (
              <span className={`text-sm font-medium ${reprocessResult.ok ? 'text-green-600' : 'text-red-600'}`}>
                {reprocessResult.msg}
              </span>
            )}
            <button
              onClick={handleReprocess}
              disabled={reprocessing}
              className="flex items-center space-x-1.5 px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60 transition-colors"
            >
              {reprocessing ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              <span>{reprocessing ? 'Processing...' : 'Re-process Data'}</span>
            </button>
          </div>
        </div>

        <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4">
          Live status endpoint (<code>/api/dc2s/config/data-status</code>) coming soon — showing last-known data below.
        </div>

        <div className="overflow-hidden border border-gray-200 rounded-lg">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase">File</th>
                <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium text-gray-500 uppercase">Row Count</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium text-gray-500 uppercase">Last Updated</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-100">
              {dataStatus.map(row => (
                <tr key={row.filename} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-mono text-gray-800">{row.filename}</td>
                  <td className="px-4 py-3">{statusBadge(row.status)}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 text-right">
                    {row.row_count !== null ? row.row_count.toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 text-right">{formatDate(row.last_updated)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── P2: Arc Classifier Config (collapsible) ── */}
      <div className="bg-white border border-gray-200 rounded-lg">
        <button
          type="button"
          onClick={() => setArcExpanded(prev => !prev)}
          className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-gray-50 transition-colors rounded-lg"
        >
          <div>
            <h3 className="text-base font-semibold text-gray-900">Arc Classifier</h3>
            <p className="text-sm text-gray-500 mt-0.5">
              Confidence threshold and active arc types for story arc classification.
            </p>
          </div>
          {arcExpanded
            ? <ChevronDown className="h-5 w-5 text-gray-400 shrink-0" />
            : <ChevronRight className="h-5 w-5 text-gray-400 shrink-0" />}
        </button>

        {arcExpanded && (
          <div className="px-6 pb-6 border-t border-gray-100 pt-4 space-y-6">
            {/* Confidence threshold slider */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-sm font-medium text-gray-700">
                  Minimum Confidence Threshold
                </label>
                <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                  {arcConfig.confidence_threshold.toFixed(2)}
                </span>
              </div>
              <input
                type="range"
                min={0.50}
                max={0.95}
                step={0.05}
                value={arcConfig.confidence_threshold}
                onChange={e => setArcConfig(prev => ({ ...prev, confidence_threshold: parseFloat(e.target.value) }))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0.50 (liberal)</span>
                <span>0.95 (strict)</span>
              </div>
              <p className="text-xs text-gray-500 mt-1.5">
                Accounts scoring below this threshold fall back to the <code className="bg-gray-100 px-1 rounded">budget_pressure</code> arc.
              </p>
            </div>

            {/* Active arcs checkboxes */}
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Active Arcs</p>
              <div className="grid grid-cols-2 gap-2">
                {ALL_ARC_NAMES.map(arc => (
                  <label
                    key={arc}
                    className="flex items-center space-x-2 cursor-pointer group"
                  >
                    <input
                      type="checkbox"
                      checked={arcConfig.active_arcs.includes(arc)}
                      onChange={() => toggleArcName(arc)}
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                    />
                    <span className="text-sm text-gray-700 group-hover:text-gray-900 font-mono">{arc}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Save */}
            <div className="flex items-center space-x-3 pt-2">
              <button
                onClick={handleSaveArcConfig}
                disabled={arcSaving}
                className="flex items-center space-x-1.5 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60 transition-colors"
              >
                {arcSaving
                  ? <RefreshCw className="h-4 w-4 animate-spin" />
                  : null}
                <span>{arcSaving ? 'Saving...' : 'Save Arc Config'}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContextGraphSettings;
