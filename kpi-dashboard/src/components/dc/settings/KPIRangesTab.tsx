/**
 * KPI Ranges Tab
 * ==============
 *
 * Displays KPI reference ranges from Data Center (DC2_S) vertical definitions.
 * Uses /api/dc2s/config/kpi-ranges so the UI shows the correct Data Center ranges,
 * not the legacy /api/kpi-reference-ranges (SaaS table).
 */

import React, { useState, useEffect } from 'react';
import { useSession } from '../../../contexts/SessionContext';
import { Target, Activity, RefreshCw, AlertCircle } from 'lucide-react';

interface KPIRange {
  range_id?: number;
  kpi_name: string;
  kpi_code?: string;
  unit: string;
  critical_min: number;
  critical_max: number;
  risk_min: number;
  risk_max: number;
  healthy_min: number;
  healthy_max: number;
  higher_is_better: boolean;
  source?: string;
}

export const KPIRangesTab: React.FC = () => {
  const { session } = useSession();
  const [kpiRanges, setKpiRanges] = useState<KPIRange[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceLabel, setSourceLabel] = useState<string>('');

  useEffect(() => {
    fetchKPIRanges();
  }, []);

  const fetchKPIRanges = async () => {
    setLoading(true);
    setError(null);
    try {
      // Data Center: use DC2_S definitions (correct ranges for data center)
      const response = await fetch('/api/dc2s/config/kpi-ranges', {
        credentials: 'include',
        headers: {
          'X-Customer-ID': session?.customer_id?.toString() || ''
        }
      });

      if (response.ok) {
        const data = await response.json();
        setKpiRanges(data.ranges || []);
        setSourceLabel(data.source || 'Data Center (DC2_S) definitions');
      } else {
        const err = await response.json().catch(() => ({}));
        setError(err.message || 'Failed to load KPI reference ranges');
        setKpiRanges([]);
      }
    } catch (err) {
      setError('Error fetching KPI reference ranges');
      console.error('Error:', err);
      setKpiRanges([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2 flex items-center">
          <Target className="h-5 w-5 mr-2 text-blue-600" />
          KPI Reference Ranges (Data Center)
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Reference ranges from Data Center (DC2_S) vertical definitions. Each KPI is evaluated
          against these ranges for health status and data quality validation. Read-only.
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Methodology Info */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <div className="bg-green-100 rounded-full p-2">
            <Activity className="h-4 w-4 text-green-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-green-900">Data Center Health Assessment Methodology</p>
            <p className="text-sm text-green-700 mt-1">
              Each KPI is evaluated against predefined reference ranges: <strong>Healthy (Green)</strong>,{' '}
              <strong>Risk (Yellow)</strong>, or <strong>Critical (Red)</strong>. These ranges are defined in the
              Data Center vertical and used for scoring and data quality checks.
            </p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600">
          {kpiRanges.length > 0 ? (
            <span>
              {kpiRanges.length} KPI range{kpiRanges.length !== 1 ? 's' : ''} from {sourceLabel}
            </span>
          ) : (
            <span>No KPI ranges loaded.</span>
          )}
        </div>
        <button
          onClick={fetchKPIRanges}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center"
        >
          {loading ? (
            <>
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              Loading...
            </>
          ) : (
            <>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </>
          )}
        </button>
      </div>

      {/* KPI Ranges Table (read-only) */}
      {kpiRanges.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    KPI Code / Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Unit
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-red-600 uppercase tracking-wider">
                    Critical Range
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-yellow-600 uppercase tracking-wider">
                    Risk Range
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-green-600 uppercase tracking-wider">
                    Healthy Range
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Higher is Better
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {kpiRanges.map((kpi, index) => (
                  <tr key={kpi.kpi_code || index} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">
                      <span className="font-mono text-gray-800">{kpi.kpi_code}</span>
                      <div className="text-gray-600 font-medium">{kpi.kpi_name}</div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">{kpi.unit}</td>
                    <td className="px-4 py-3 text-sm text-center text-red-700">
                      {kpi.critical_min} – {kpi.critical_max}
                    </td>
                    <td className="px-4 py-3 text-sm text-center text-yellow-700">
                      {kpi.risk_min} – {kpi.risk_max}
                    </td>
                    <td className="px-4 py-3 text-sm text-center text-green-700">
                      {kpi.healthy_min} – {kpi.healthy_max}
                    </td>
                    <td className="px-4 py-3 text-sm text-center text-gray-600">
                      {kpi.higher_is_better ? 'Yes' : 'No'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {kpiRanges.length === 0 && !loading && (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
          <Target className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-2">No KPI reference ranges loaded</p>
          <p className="text-sm text-gray-500">
            Click Refresh to load Data Center (DC2_S) KPI ranges
          </p>
        </div>
      )}
    </div>
  );
};
