/**
 * Data Quality Section
 * Shows KPI range discrepancies: measurements that fall outside defined reference ranges.
 * Onboarding and manual CSV uploads validate against these ranges so invalid data does not enter the system.
 */

import React, { useState, useEffect } from 'react';
import { apiCall } from '../../../utils/api';
import { AlertTriangle, CheckCircle, RefreshCw, BarChart3 } from 'lucide-react';

interface Discrepancy {
  account_id: number;
  account_name: string;
  kpi_code: string;
  kpi_name: string;
  value: number | string;
  expected_min: number | null;
  expected_max: number | null;
  unit: string;
  severity: string;
}

interface Summary {
  total_checked: number;
  out_of_range_count: number;
  accounts_affected: number;
}

interface KpiRangeDiscrepanciesResponse {
  summary: Summary;
  discrepancies: Discrepancy[];
  message?: string;
}

const DataQualitySection: React.FC = () => {
  const [data, setData] = useState<KpiRangeDiscrepanciesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDiscrepancies = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiCall('/api/data-quality/kpi-range-discrepancies');
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.message || `HTTP ${res.status}`);
      }
      const json: KpiRangeDiscrepanciesResponse = await res.json();
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load data quality');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiscrepancies();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500 py-4">
        <RefreshCw className="w-4 h-4 animate-spin" />
        <span>Loading data quality...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-red-700">
          <AlertTriangle className="w-5 h-5" />
          <span>{error}</span>
        </div>
        <button
          onClick={fetchDiscrepancies}
          className="px-3 py-1.5 bg-red-100 text-red-800 rounded hover:bg-red-200 text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  const summary = data?.summary ?? { total_checked: 0, out_of_range_count: 0, accounts_affected: 0 };
  const discrepancies = data?.discrepancies ?? [];
  const hasIssues = summary.out_of_range_count > 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-gray-900 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-blue-600" />
          Data Quality – KPI range alignment
        </h4>
        <button
          onClick={fetchDiscrepancies}
          className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>
      <p className="text-sm text-gray-600">
        Uploaded KPI values are validated against reference ranges. Onboarding and manual CSV uploads
        reject or warn when values fall outside allowed ranges so invalid data does not enter the system.
      </p>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Measurements checked</p>
          <p className="text-xl font-semibold text-gray-900">{summary.total_checked.toLocaleString()}</p>
        </div>
        <div className={`rounded-lg border p-3 ${hasIssues ? 'bg-amber-50 border-amber-200' : 'bg-green-50 border-green-200'}`}>
          <p className="text-xs text-gray-500 uppercase tracking-wide">Out of range</p>
          <p className={`text-xl font-semibold flex items-center gap-1 ${hasIssues ? 'text-amber-800' : 'text-green-800'}`}>
            {hasIssues ? <AlertTriangle className="w-5 h-5" /> : <CheckCircle className="w-5 h-5" />}
            {summary.out_of_range_count.toLocaleString()}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-3">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Accounts affected</p>
          <p className="text-xl font-semibold text-gray-900">{summary.accounts_affected.toLocaleString()}</p>
        </div>
      </div>

      {/* Discrepancies table */}
      {discrepancies.length > 0 ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50/50 overflow-hidden">
          <div className="px-4 py-2 border-b border-amber-200 bg-amber-100">
            <h5 className="font-medium text-amber-900">Discrepancies (value outside allowed range)</h5>
          </div>
          <div className="overflow-x-auto max-h-64 overflow-y-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-100 border-b border-gray-200">
                  <th className="text-left py-2 px-3 font-medium text-gray-700">Account</th>
                  <th className="text-left py-2 px-3 font-medium text-gray-700">KPI</th>
                  <th className="text-left py-2 px-3 font-medium text-gray-700">Value</th>
                  <th className="text-left py-2 px-3 font-medium text-gray-700">Expected range</th>
                  <th className="text-left py-2 px-3 font-medium text-gray-700">Unit</th>
                </tr>
              </thead>
              <tbody>
                {discrepancies.slice(0, 200).map((d, i) => (
                  <tr key={i} className="border-b border-gray-100 hover:bg-amber-50/50">
                    <td className="py-2 px-3">
                      <span className="font-mono text-gray-700">{d.account_id}</span>
                      {d.account_name && <span className="text-gray-500 ml-1">({d.account_name})</span>}
                    </td>
                    <td className="py-2 px-3">
                      <span className="font-medium text-gray-900">{d.kpi_name || d.kpi_code}</span>
                      <span className="text-gray-500 text-xs ml-1">{d.kpi_code}</span>
                    </td>
                    <td className="py-2 px-3 font-mono">{String(d.value)}</td>
                    <td className="py-2 px-3 text-gray-700">
                      {d.expected_min != null && d.expected_max != null
                        ? `[${d.expected_min}, ${d.expected_max}]`
                        : '—'}
                    </td>
                    <td className="py-2 px-3 text-gray-500">{d.unit || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {discrepancies.length > 200 && (
            <p className="text-xs text-gray-500 px-4 py-2 border-t border-amber-200">
              Showing first 200 of {discrepancies.length} discrepancies.
            </p>
          )}
        </div>
      ) : (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 flex items-center gap-2 text-green-800">
          <CheckCircle className="w-5 h-5 flex-shrink-0" />
          <span>
            {summary.total_checked === 0
              ? 'No KPI measurements in the system yet, or no range definitions loaded.'
              : 'All checked KPI values are within their reference ranges.'}
          </span>
        </div>
      )}
    </div>
  );
};

export default DataQualitySection;
