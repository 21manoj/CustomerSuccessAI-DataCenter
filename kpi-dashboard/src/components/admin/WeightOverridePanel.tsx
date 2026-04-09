/**
 * Weight Override Panel — Admin escalation tool
 * ===============================================
 * Allows super admin to directly set pillar/KPI weights for a customer,
 * bypassing Wizard C. Shows current source (admin_override / wizard_c / default).
 *
 * API: POST /api/admin/customers/<id>/override-weights
 *      POST /api/admin/customers/<id>/reset-weights
 *      GET  /api/admin/wizard-c/weights/current
 */

import React, { useState, useEffect, useCallback } from 'react';
import { getApiBaseUrl } from '../../utils/api';

interface PillarWeight {
  code: string;
  name: string;
  weight: number;
}

// Vertical-aware pillar names
const _getPillarName = (code: string): string => {
  try {
    const pl = JSON.parse(localStorage.getItem('pillar_labels') || '{}');
    return pl[code] || code;
  } catch { return code; }
};

const DEFAULT_PILLARS: PillarWeight[] = [
  { code: 'P1', name: _getPillarName('P1') || 'Pillar 1', weight: 0.15 },
  { code: 'P2', name: _getPillarName('P2') || 'Pillar 2', weight: 0.20 },
  { code: 'P3', name: _getPillarName('P3') || 'Pillar 3', weight: 0.25 },
  { code: 'P4', name: _getPillarName('P4') || 'Pillar 4', weight: 0.15 },
  { code: 'P5', name: _getPillarName('P5') || 'Pillar 5', weight: 0.25 },
];

const WeightOverridePanel: React.FC<{ customerId: number }> = ({ customerId }) => {
  const [pillars, setPillars] = useState<PillarWeight[]>(DEFAULT_PILLARS);
  const [source, setSource] = useState<string>('loading');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const loadWeights = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${getApiBaseUrl()}/api/admin/wizard-c/weights/current`, { credentials: 'include' });
      if (!res.ok) throw new Error(`${res.status}`);
      const data = await res.json();
      setSource(data.source || 'unknown');

      if (data.weights) {
        const loaded = Object.entries(data.weights).map(([code, val]: [string, any]) => ({
          code,
          name: val.name || code,
          weight: val.weight ?? val,
        }));
        if (loaded.length > 0) setPillars(loaded);
      }
    } catch (e: any) {
      setError(`Failed to load weights: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadWeights(); }, [loadWeights]);

  const total = pillars.reduce((s, p) => s + p.weight, 0);
  const isValid = Math.abs(total - 1.0) < 0.02;

  const updateWeight = (code: string, value: number) => {
    setPillars((prev) => prev.map((p) => p.code === code ? { ...p, weight: value } : p));
  };

  const saveWeights = async () => {
    if (!reason.trim()) {
      setError('Reason is required');
      return;
    }
    if (!isValid) {
      setError(`Weights must sum to 1.0 (currently ${total.toFixed(3)})`);
      return;
    }

    setSaving(true);
    setError('');
    setSuccessMsg('');

    try {
      const pillarWeights: Record<string, number> = {};
      pillars.forEach((p) => { pillarWeights[p.code] = Math.round(p.weight * 1000) / 1000; });

      const res = await fetch(`${getApiBaseUrl()}/api/admin/customers/${customerId}/override-weights`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ pillar_weights: pillarWeights, reason }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `${res.status}`);
      }
      setSource('admin_override');
      setSuccessMsg('Weights saved successfully');
      setReason('');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const resetToDefaults = async () => {
    setSaving(true);
    setError('');
    setSuccessMsg('');

    try {
      const res = await fetch(`${getApiBaseUrl()}/api/admin/customers/${customerId}/reset-weights`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ reason: reason || 'Reset to catalog defaults' }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || `${res.status}`);
      }
      setPillars(DEFAULT_PILLARS);
      setSource('catalog_default');
      setSuccessMsg('Weights reset to catalog defaults');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const sourceLabel = (s: string) => {
    const map: Record<string, [string, string]> = {
      admin_override: ['Admin Override', 'bg-amber-900/40 text-amber-300'],
      learned: ['Wizard C Calibrated', 'bg-blue-900/40 text-blue-300'],
      bootstrap: ['Bootstrap Default', 'bg-gray-800 text-gray-400'],
      catalog_default: ['Catalog Default', 'bg-gray-800 text-gray-400'],
      loading: ['Loading...', 'bg-gray-800 text-gray-500'],
    };
    const [label, cls] = map[s] || ['Unknown', 'bg-gray-800 text-gray-500'];
    return <span className={`px-2 py-0.5 rounded text-xs ${cls}`}>{label}</span>;
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-8 justify-center text-gray-400 text-sm">
        <div className="animate-spin h-4 w-4 border-2 border-blue-400 border-t-transparent rounded-full" />
        Loading weights...
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Weight Override</h3>
          <p className="text-xs text-gray-400 mt-1">
            Source: {sourceLabel(source)} | Customer #{customerId}
          </p>
        </div>
        <button
          onClick={resetToDefaults}
          disabled={saving}
          className="px-3 py-1.5 bg-gray-800 text-gray-300 rounded-lg text-xs hover:bg-gray-700 disabled:opacity-50"
        >
          Reset to Defaults
        </button>
      </div>

      {error && (
        <div className="mb-4 px-3 py-2 bg-red-900/30 border border-red-700/50 rounded-lg text-red-300 text-sm">{error}</div>
      )}
      {successMsg && (
        <div className="mb-4 px-3 py-2 bg-green-900/30 border border-green-700/50 rounded-lg text-green-300 text-sm">{successMsg}</div>
      )}

      {/* Pillar weight sliders */}
      <div className="space-y-4 mb-6">
        {pillars.map((p) => (
          <div key={p.code} className="bg-gray-800/50 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <div>
                <span className="text-sm font-mono text-gray-300">{p.code}</span>
                <span className="text-sm text-gray-500 ml-2">{p.name}</span>
              </div>
              <span className="text-sm font-mono text-white">{(p.weight * 100).toFixed(1)}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={0.5}
              step={0.01}
              value={p.weight}
              onChange={(e) => updateWeight(p.code, parseFloat(e.target.value))}
              className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
          </div>
        ))}
      </div>

      {/* Total indicator */}
      <div className={`flex items-center justify-between px-3 py-2 rounded-lg mb-4 text-sm ${
        isValid ? 'bg-green-900/20 border border-green-700/30 text-green-400' : 'bg-red-900/20 border border-red-700/30 text-red-400'
      }`}>
        <span>Total</span>
        <span className="font-mono">{(total * 100).toFixed(1)}% {isValid ? '' : '(must be 100%)'}</span>
      </div>

      {/* Reason + Save */}
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Reason (required)</label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Customer requested higher P3 weight for GPU focus"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600"
          />
        </div>
        <button
          onClick={saveWeights}
          disabled={saving || !isValid || !reason.trim()}
          className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : 'Save Weight Override'}
        </button>
      </div>
    </div>
  );
};

export default WeightOverridePanel;
