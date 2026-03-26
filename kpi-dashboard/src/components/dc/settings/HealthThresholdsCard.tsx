/**
 * HealthThresholdsCard — P1-A
 * ============================
 * Card to view and edit health score threshold boundaries.
 *
 * API contracts:
 *   GET /api/dc2s/config/health-thresholds → { critical_max, at_risk_min, healthy_min }
 *   PUT /api/dc2s/config/health-thresholds ← { critical_max, at_risk_min, healthy_min }
 *
 * Semantics:
 *   score < critical_max           → Critical   (0–49 default)
 *   critical_max ≤ score < healthy_min → At-risk  (50–69 default)
 *   score ≥ healthy_min            → Healthy    (70–100 default)
 */

import React, { useState, useEffect } from 'react';
import { RefreshCw, CheckCircle, AlertCircle, Save } from 'lucide-react';

// ============================================================
// TYPES
// ============================================================

interface ThresholdValues {
  critical_max: number;   // upper boundary of Critical zone (exclusive — score < critical_max)
  at_risk_min: number;    // lower boundary of At-risk zone (same as critical_max)
  healthy_min: number;    // lower boundary of Healthy zone
}

// ============================================================
// DEFAULTS
// ============================================================

const DEFAULT_THRESHOLDS: ThresholdValues = {
  critical_max: 50,
  at_risk_min: 50,
  healthy_min: 70,
};

// ============================================================
// PREVIEW BAR
// ============================================================

const ThresholdPreviewBar: React.FC<{ criticalMax: number; healthyMin: number }> = ({
  criticalMax,
  healthyMin,
}) => {
  const criticalPct = criticalMax;
  const atRiskPct = healthyMin - criticalMax;
  const healthyPct = 100 - healthyMin;

  return (
    <div className="mt-3">
      <div className="flex h-6 rounded-lg overflow-hidden border border-gray-200 text-xs font-medium text-white">
        <div
          className="flex items-center justify-center bg-red-500 transition-all duration-300"
          style={{ width: `${criticalPct}%` }}
          title={`Critical: 0–${criticalMax - 1}`}
        >
          {criticalPct >= 10 && `0–${criticalMax - 1}`}
        </div>
        <div
          className="flex items-center justify-center bg-amber-400 transition-all duration-300"
          style={{ width: `${atRiskPct}%` }}
          title={`At-risk: ${criticalMax}–${healthyMin - 1}`}
        >
          {atRiskPct >= 10 && `${criticalMax}–${healthyMin - 1}`}
        </div>
        <div
          className="flex items-center justify-center bg-green-500 transition-all duration-300"
          style={{ width: `${healthyPct}%` }}
          title={`Healthy: ${healthyMin}–100`}
        >
          {healthyPct >= 10 && `${healthyMin}–100`}
        </div>
      </div>
      <div className="flex justify-between text-xs text-gray-400 mt-1 px-0.5">
        <span className="text-red-500 font-medium">Critical</span>
        <span className="text-amber-500 font-medium">At-risk</span>
        <span className="text-green-500 font-medium">Healthy</span>
      </div>
    </div>
  );
};

// ============================================================
// MAIN COMPONENT
// ============================================================

interface HealthThresholdsCardProps {
  /** Super-admin context: pass target customer's ID. Self-service: omit (uses session). */
  customerId?: number;
}

const HealthThresholdsCard: React.FC<HealthThresholdsCardProps> = ({ customerId }) => {
  const apiUrl = (path: string) =>
    customerId ? `${path}?customer_id=${customerId}` : path;
  const [values, setValues] = useState<ThresholdValues>(DEFAULT_THRESHOLDS);
  const [localValues, setLocalValues] = useState<ThresholdValues>(DEFAULT_THRESHOLDS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const showResult = (ok: boolean, msg: string) => {
    setResult({ ok, msg });
    setTimeout(() => setResult(null), 3000);
  };

  // ── Load current thresholds ──
  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await fetch(apiUrl('/api/dc2s/config/health-thresholds'), { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          const loaded: ThresholdValues = {
            critical_max: data.critical_max ?? DEFAULT_THRESHOLDS.critical_max,
            at_risk_min: data.at_risk_min ?? DEFAULT_THRESHOLDS.at_risk_min,
            healthy_min: data.healthy_min ?? DEFAULT_THRESHOLDS.healthy_min,
          };
          setValues(loaded);
          setLocalValues(loaded);
        }
      } catch {
        // Use defaults silently
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Keep at_risk_min in sync with critical_max (they're the same boundary)
  const setCriticalMax = (v: number) => {
    setLocalValues(prev => ({ ...prev, critical_max: v, at_risk_min: v }));
  };

  const setHealthyMin = (v: number) => {
    setLocalValues(prev => ({ ...prev, healthy_min: v }));
  };

  // ── Validation ──
  const isValid = localValues.critical_max > 0
    && localValues.healthy_min > localValues.critical_max
    && localValues.healthy_min < 100;

  const validationMsg = !isValid
    ? localValues.critical_max <= 0
      ? 'Critical boundary must be > 0'
      : localValues.healthy_min <= localValues.critical_max
        ? 'Healthy boundary must be greater than Critical boundary'
        : 'Healthy boundary must be < 100'
    : null;

  // ── Save ──
  const handleSave = async () => {
    if (!isValid) return;
    setSaving(true);
    try {
      const res = await fetch(apiUrl('/api/dc2s/config/health-thresholds'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(localValues),
      });
      if (res.ok) {
        setValues(localValues);
        showResult(true, 'Thresholds saved');
      } else {
        const data = await res.json().catch(() => ({}));
        showResult(false, data.error || 'Failed to save thresholds');
      }
    } catch {
      showResult(false, 'Network error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center space-x-2 text-gray-400 text-sm">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span>Loading health thresholds...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-base font-semibold text-gray-900 mb-1">Health Score Thresholds</h3>
      <p className="text-sm text-gray-500 mb-4">
        Set the score boundaries that classify accounts as Critical, At-risk, or Healthy.
        Changes apply to all future health score calculations.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        {/* Critical boundary */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Critical boundary <span className="text-gray-400 font-normal">(score below this = Critical)</span>
          </label>
          <input
            type="number"
            min={1}
            max={localValues.healthy_min - 1}
            value={localValues.critical_max}
            onChange={e => setCriticalMax(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
          <p className="text-xs text-red-500 mt-1">
            Scores 0–{localValues.critical_max - 1} shown in red
          </p>
        </div>

        {/* Healthy boundary */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Healthy boundary <span className="text-gray-400 font-normal">(score at or above = Healthy)</span>
          </label>
          <input
            type="number"
            min={localValues.critical_max + 1}
            max={99}
            value={localValues.healthy_min}
            onChange={e => setHealthyMin(Number(e.target.value))}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
          <p className="text-xs text-green-600 mt-1">
            Scores {localValues.healthy_min}–100 shown in green
          </p>
        </div>
      </div>

      {/* Preview bar */}
      <ThresholdPreviewBar
        criticalMax={localValues.critical_max}
        healthyMin={localValues.healthy_min}
      />

      {/* Validation / result feedback */}
      {validationMsg && (
        <p className="mt-3 text-sm text-red-600 flex items-center space-x-1">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{validationMsg}</span>
        </p>
      )}

      {/* Note */}
      <p className="mt-3 text-xs text-gray-400">
        At-risk zone: scores {localValues.critical_max}–{localValues.healthy_min - 1} (amber)
      </p>

      {/* Save row */}
      <div className="mt-4 flex items-center space-x-3">
        <button
          onClick={handleSave}
          disabled={saving || !isValid}
          className="flex items-center space-x-1.5 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-60 transition-colors"
        >
          {saving
            ? <RefreshCw className="h-4 w-4 animate-spin" />
            : <Save className="h-4 w-4" />}
          <span>{saving ? 'Saving...' : 'Save Thresholds'}</span>
        </button>
        {result && (
          <span className={`flex items-center space-x-1 text-sm font-medium ${result.ok ? 'text-green-600' : 'text-red-600'}`}>
            {result.ok
              ? <CheckCircle className="h-4 w-4" />
              : <AlertCircle className="h-4 w-4" />}
            <span>{result.msg}</span>
          </span>
        )}
      </div>
    </div>
  );
};

export default HealthThresholdsCard;
