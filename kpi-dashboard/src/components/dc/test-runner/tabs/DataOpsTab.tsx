/**
 * DataOpsTab — Push KPIs, push signals, recalculate scores
 *
 * Enables incremental data operations against the platform.
 */

import React, { useState } from 'react';
import {
  Upload,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Plus,
  Trash2,
  RefreshCw,
  Lock,
  MessageSquare,
  BarChart3,
} from 'lucide-react';

import { dataOpsApi } from '../api';

interface DataOpsTabProps {
  customerId: string;
  entitlements: Record<string, boolean>;
  onDataPushed?: () => void;
}

// KPI codes (P-format only per project convention)
const KPI_CODES = [
  'P1-KPI1', 'P1-KPI2', 'P1-KPI3', 'P1-KPI4', 'P1-KPI5', 'P1-KPI6', 'P1-KPI7', 'P1-KPI8',
  'P2-KPI1', 'P2-KPI2', 'P2-KPI3', 'P2-KPI4', 'P2-KPI5', 'P2-KPI6', 'P2-KPI7', 'P2-KPI8',
  'P3-KPI1', 'P3-KPI2', 'P3-KPI3', 'P3-KPI4', 'P3-KPI5', 'P3-KPI6', 'P3-KPI7',
  'P4-KPI1', 'P4-KPI2', 'P4-KPI3', 'P4-KPI4', 'P4-KPI5', 'P4-KPI6', 'P4-KPI7',
  'P5-KPI1', 'P5-KPI2', 'P5-KPI3', 'P5-KPI4', 'P5-KPI5', 'P5-KPI6', 'P5-KPI7', 'P5-KPI8',
];

const SIGNAL_TYPES = [
  'churn_risk', 'expansion_opportunity', 'champion_loss', 'support_escalation',
  'executive_change', 'usage_decline', 'nps_drop', 'competitive_threat',
  'renewal_risk', 'adoption_milestone',
];

const SEVERITIES = ['low', 'medium', 'high', 'critical'];

interface KPIRow {
  account_id: string;
  kpi_code: string;
  measured_at: string;
  value: string;
  target: string;
}

interface SignalRow {
  account_id: string;
  signal_date: string;
  signal_type: string;
  content: string;
  severity: string;
}

const emptyKPI = (): KPIRow => ({
  account_id: '',
  kpi_code: 'P1-KPI1',
  measured_at: new Date().toISOString().slice(0, 10),
  value: '',
  target: '',
});

const emptySignal = (): SignalRow => ({
  account_id: '',
  signal_date: new Date().toISOString().slice(0, 10),
  signal_type: 'churn_risk',
  content: '',
  severity: 'medium',
});

const DataOpsTab: React.FC<DataOpsTabProps> = ({ customerId, entitlements, onDataPushed }) => {
  const hasAdvanced = entitlements['test_runner_advanced'] ?? false;

  if (!hasAdvanced) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <Lock className="w-12 h-12 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-500 font-medium">Data Operations requires Professional tier</p>
        <p className="text-sm text-gray-400 mt-1">Upgrade to push KPIs, signals, and recalculate scores</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PushKPISection customerId={customerId} onSuccess={onDataPushed} />
      <PushSignalSection customerId={customerId} onSuccess={onDataPushed} />
      <RecalculateSection customerId={customerId} onSuccess={onDataPushed} />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Section 1: Push KPI Data
// ---------------------------------------------------------------------------

const PushKPISection: React.FC<{ customerId: string; onSuccess?: () => void }> = ({ customerId, onSuccess }) => {
  const [rows, setRows] = useState<KPIRow[]>([emptyKPI()]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const updateRow = (i: number, field: keyof KPIRow, value: string) => {
    setRows(prev => prev.map((r, idx) => idx === i ? { ...r, [field]: value } : r));
  };

  const addRow = () => setRows(prev => [...prev, emptyKPI()]);
  const removeRow = (i: number) => setRows(prev => prev.filter((_, idx) => idx !== i));

  const push = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const kpis = rows
        .filter(r => r.account_id && r.value)
        .map(r => ({
          account_id: parseInt(r.account_id, 10),
          kpi_code: r.kpi_code,
          measured_at: r.measured_at,
          value: parseFloat(r.value),
          target: parseFloat(r.target) || 0,
        }));

      if (kpis.length === 0) {
        setError('Add at least one valid KPI row (Account ID + Value required)');
        setLoading(false);
        return;
      }

      const res = await dataOpsApi.pushKPIs(customerId, kpis);
      setResult(res);
      onSuccess?.();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-3">
        <Upload className="w-5 h-5 text-blue-600" />
        <h3 className="font-semibold text-gray-800">Push KPI Data</h3>
      </div>
      <div className="px-6 py-4 space-y-3">
        {rows.map((row, i) => (
          <div key={i} className="grid grid-cols-6 gap-2 items-end">
            <div>
              {i === 0 && <label className="block text-xs font-medium text-gray-500 mb-1">Account ID</label>}
              <input
                type="number"
                value={row.account_id}
                onChange={e => updateRow(i, 'account_id', e.target.value)}
                placeholder="300001"
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              {i === 0 && <label className="block text-xs font-medium text-gray-500 mb-1">KPI Code</label>}
              <select
                value={row.kpi_code}
                onChange={e => updateRow(i, 'kpi_code', e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm bg-white focus:ring-2 focus:ring-blue-500"
              >
                {KPI_CODES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              {i === 0 && <label className="block text-xs font-medium text-gray-500 mb-1">Date</label>}
              <input
                type="date"
                value={row.measured_at}
                onChange={e => updateRow(i, 'measured_at', e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              {i === 0 && <label className="block text-xs font-medium text-gray-500 mb-1">Value</label>}
              <input
                type="number"
                step="any"
                value={row.value}
                onChange={e => updateRow(i, 'value', e.target.value)}
                placeholder="85.5"
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              {i === 0 && <label className="block text-xs font-medium text-gray-500 mb-1">Target</label>}
              <input
                type="number"
                step="any"
                value={row.target}
                onChange={e => updateRow(i, 'target', e.target.value)}
                placeholder="90"
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              {rows.length > 1 && (
                <button
                  onClick={() => removeRow(i)}
                  className="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                  title="Remove row"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        ))}

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={addRow}
            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            <Plus className="w-3.5 h-3.5" /> Add Row
          </button>
          <button
            onClick={push}
            disabled={loading}
            className="px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Push KPIs
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-red-600 text-sm">
            <AlertCircle className="w-4 h-4" /> {error}
          </div>
        )}
        {result && (
          <div className="flex items-center gap-2 text-green-600 text-sm">
            <CheckCircle2 className="w-4 h-4" />
            KPIs pushed successfully
            {result.inserted != null && <span className="text-gray-500">({result.inserted} records)</span>}
          </div>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Section 2: Push Qualitative Signals
// ---------------------------------------------------------------------------

const PushSignalSection: React.FC<{ customerId: string; onSuccess?: () => void }> = ({ customerId, onSuccess }) => {
  const [rows, setRows] = useState<SignalRow[]>([emptySignal()]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const updateRow = (i: number, field: keyof SignalRow, value: string) => {
    setRows(prev => prev.map((r, idx) => idx === i ? { ...r, [field]: value } : r));
  };

  const addRow = () => setRows(prev => [...prev, emptySignal()]);
  const removeRow = (i: number) => setRows(prev => prev.filter((_, idx) => idx !== i));

  const push = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const signals = rows
        .filter(r => r.account_id && r.content)
        .map(r => ({
          account_id: parseInt(r.account_id, 10),
          signal_date: r.signal_date,
          signal_type: r.signal_type,
          content: r.content,
          severity: r.severity,
        }));

      if (signals.length === 0) {
        setError('Add at least one signal (Account ID + Content required)');
        setLoading(false);
        return;
      }

      const res = await dataOpsApi.pushSignals(customerId, signals);
      setResult(res);
      onSuccess?.();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-3">
        <MessageSquare className="w-5 h-5 text-amber-600" />
        <h3 className="font-semibold text-gray-800">Push Qualitative Signals</h3>
      </div>
      <div className="px-6 py-4 space-y-3">
        {rows.map((row, i) => (
          <div key={i} className="grid grid-cols-6 gap-2 items-end">
            <div>
              {i === 0 && <label className="block text-xs font-medium text-gray-500 mb-1">Account ID</label>}
              <input
                type="number"
                value={row.account_id}
                onChange={e => updateRow(i, 'account_id', e.target.value)}
                placeholder="300001"
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-amber-500"
              />
            </div>
            <div>
              {i === 0 && <label className="block text-xs font-medium text-gray-500 mb-1">Date</label>}
              <input
                type="date"
                value={row.signal_date}
                onChange={e => updateRow(i, 'signal_date', e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-amber-500"
              />
            </div>
            <div>
              {i === 0 && <label className="block text-xs font-medium text-gray-500 mb-1">Type</label>}
              <select
                value={row.signal_type}
                onChange={e => updateRow(i, 'signal_type', e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm bg-white focus:ring-2 focus:ring-amber-500"
              >
                {SIGNAL_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              {i === 0 && <label className="block text-xs font-medium text-gray-500 mb-1">Content</label>}
              <input
                type="text"
                value={row.content}
                onChange={e => updateRow(i, 'content', e.target.value)}
                placeholder="Describe the signal..."
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-amber-500"
              />
            </div>
            <div className="flex items-center gap-1">
              {i === 0 && <label className="block text-xs font-medium text-gray-500 mb-1 w-full">Severity</label>}
              <select
                value={row.severity}
                onChange={e => updateRow(i, 'severity', e.target.value)}
                className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm bg-white focus:ring-2 focus:ring-amber-500"
              >
                {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              {rows.length > 1 && (
                <button
                  onClick={() => removeRow(i)}
                  className="p-1.5 text-gray-400 hover:text-red-500 transition-colors flex-shrink-0"
                  title="Remove"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        ))}

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={addRow}
            className="flex items-center gap-1 text-sm text-amber-600 hover:text-amber-800 font-medium"
          >
            <Plus className="w-3.5 h-3.5" /> Add Signal
          </button>
          <button
            onClick={push}
            disabled={loading}
            className="px-4 py-1.5 bg-amber-600 text-white rounded-lg hover:bg-amber-700 text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Push Signals
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-red-600 text-sm">
            <AlertCircle className="w-4 h-4" /> {error}
          </div>
        )}
        {result && (
          <div className="flex items-center gap-2 text-green-600 text-sm">
            <CheckCircle2 className="w-4 h-4" />
            Signals pushed successfully
          </div>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Section 3: Recalculate Scores
// ---------------------------------------------------------------------------

const RecalculateSection: React.FC<{ customerId: string; onSuccess?: () => void }> = ({ customerId, onSuccess }) => {
  const [month, setMonth] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const recalculate = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await dataOpsApi.recalculateScores(customerId, month || undefined);
      setResult(res);
      onSuccess?.();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-3">
        <BarChart3 className="w-5 h-5 text-green-600" />
        <h3 className="font-semibold text-gray-800">Recalculate Health Scores</h3>
      </div>
      <div className="px-6 py-4 space-y-4">
        <div className="flex items-end gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Month <span className="text-gray-400">(optional — leave blank for latest)</span>
            </label>
            <input
              type="month"
              value={month}
              onChange={e => setMonth(e.target.value)}
              className="w-48 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500"
            />
          </div>
          <button
            onClick={recalculate}
            disabled={loading}
            className="px-4 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            Recalculate
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-red-600 text-sm">
            <AlertCircle className="w-4 h-4" /> {error}
          </div>
        )}

        {result && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-green-600 text-sm">
              <CheckCircle2 className="w-4 h-4" />
              Scores recalculated successfully
            </div>
            {result.accounts && (
              <div className="bg-green-50 rounded-lg p-3">
                <p className="text-sm text-green-800">
                  {result.accounts.length || Object.keys(result.accounts).length} account(s) updated
                </p>
              </div>
            )}
            {result.message && (
              <p className="text-sm text-gray-600">{result.message}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DataOpsTab;
