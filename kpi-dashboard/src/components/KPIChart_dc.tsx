/**
 * Data Center KPI Chart Component
 * Displays KPI trends and visualizations for DC tenants using real API data
 */

import React, { useState, useEffect, useCallback } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import { TrendingUp, Activity, AlertCircle } from 'lucide-react';
import { useSession } from '../contexts/SessionContext';
import { getCustomerIdentifier } from '../utils/api';

// Pillar colors for chart lines
const PILLAR_COLORS: Record<string, string> = {
  'AI': '#8b5cf6',  // Purple
  'OS': '#3b82f6',  // Blue
  'DV': '#10b981',  // Green
  'CH': '#f59e0b',  // Amber
  'EX': '#ef4444',  // Red
};

const KPI_COLORS = [
  '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16',
  '#06b6d4', '#e11d48',
];

interface KPIChartProps {
  tenantId: number | string | null;
  kpiId?: string;
  timeRange?: '7d' | '30d' | '90d' | '180d';
}

interface TimeSeriesPoint {
  period: string;
  [kpiCode: string]: any;
}

interface KPISummary {
  name: string;
  pillar: string;
  unit: string;
  target: number | null;
}

const KPIChart_dc: React.FC<KPIChartProps> = ({ tenantId, kpiId, timeRange = '90d' }) => {
  const { session } = useSession();
  const [chartData, setChartData] = useState<any[]>([]);
  const [kpiSummary, setKpiSummary] = useState<Record<string, KPISummary>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedKpis, setSelectedKpis] = useState<string[]>([]);
  const [availableKpis, setAvailableKpis] = useState<string[]>([]);

  const loadChartData = useCallback(async () => {
    if (!tenantId) return;

    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        range: timeRange,
        granularity: 'weekly',
      });
      if (kpiId) {
        params.set('kpi_code', kpiId);
      }

      const response = await fetch(
        `/api/dc2s/accounts/${tenantId}/kpis/timeseries?${params.toString()}`,
        {
          credentials: 'include',
          headers: {
            'X-Customer-ID': getCustomerIdentifier(session),
          },
        }
      );

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();

      if (!data.timeseries || data.timeseries.length === 0) {
        setChartData([]);
        setError('No KPI data available for this time range.');
        return;
      }

      // Transform timeseries into flat chart data
      const kpiCodes = Object.keys(data.kpi_summary || {});
      setKpiSummary(data.kpi_summary || {});
      setAvailableKpis(kpiCodes);

      // Auto-select first 5 KPIs if none selected
      if (selectedKpis.length === 0) {
        setSelectedKpis(kpiCodes.slice(0, 5));
      }

      const transformed = data.timeseries.map((point: TimeSeriesPoint) => {
        const row: any = { period: point.period };
        for (const code of kpiCodes) {
          if (point[code]) {
            row[code] = point[code].value;
            row[`${code}_target`] = point[code].target;
          }
        }
        return row;
      });

      setChartData(transformed);
    } catch (err: any) {
      console.error('Error loading KPI timeseries:', err);
      setError(err.message || 'Failed to load KPI data');
    } finally {
      setLoading(false);
    }
  }, [tenantId, kpiId, timeRange, session]);

  useEffect(() => {
    if (tenantId) {
      setSelectedKpis([]);  // Reset selection on tenant change
      loadChartData();
    }
  }, [tenantId, kpiId, timeRange, loadChartData]);

  const toggleKpi = (code: string) => {
    setSelectedKpis(prev =>
      prev.includes(code)
        ? prev.filter(c => c !== code)
        : [...prev, code]
    );
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (!tenantId) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center py-12">
          <Activity className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">Select a tenant to view KPI trends</p>
        </div>
      </div>
    );
  }

  if (error && chartData.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center py-12">
          <AlertCircle className="h-12 w-12 text-yellow-400 mx-auto mb-4" />
          <p className="text-gray-500">{error}</p>
          <p className="text-xs text-gray-400 mt-2">Data may still be loading. Try again in a moment.</p>
        </div>
      </div>
    );
  }

  // Compute average target for reference line
  const avgTarget = selectedKpis.reduce((sum, code) => {
    const target = kpiSummary[code]?.target;
    return sum + (target || 0);
  }, 0) / Math.max(selectedKpis.length, 1);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">KPI Trend</h3>
          <p className="text-sm text-gray-500 mt-1">
            Last {timeRange} &middot; Weekly average &middot; {selectedKpis.length}/{availableKpis.length} KPIs shown
          </p>
        </div>
        <TrendingUp className="h-6 w-6 text-blue-600" />
      </div>

      {/* KPI selection chips */}
      <div className="flex flex-wrap gap-1.5 mb-4 max-h-20 overflow-y-auto">
        {availableKpis.map((code, idx) => {
          const isSelected = selectedKpis.includes(code);
          const summary = kpiSummary[code];
          const pillarCode = code.split('-')[0];
          const color = PILLAR_COLORS[pillarCode] || KPI_COLORS[idx % KPI_COLORS.length];
          return (
            <button
              key={code}
              onClick={() => toggleKpi(code)}
              className={`text-xs px-2 py-1 rounded-full border transition-all ${
                isSelected
                  ? 'border-transparent text-white shadow-sm'
                  : 'border-gray-300 text-gray-500 bg-white hover:bg-gray-50'
              }`}
              style={isSelected ? { backgroundColor: color } : {}}
              title={summary?.name || code}
            >
              {code}
            </button>
          );
        })}
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="period"
            tick={{ fontSize: 11 }}
            tickFormatter={(val) => {
              // Format "2025-W04" → "W4"
              if (val.includes('-W')) return val.split('-W')[1].replace(/^0/, 'W');
              return val;
            }}
          />
          <YAxis tick={{ fontSize: 11 }} domain={[0, 'auto']} />
          <Tooltip
            contentStyle={{ fontSize: 12 }}
            formatter={(value: number, name: string) => {
              const summary = kpiSummary[name];
              const displayName = summary?.name || name;
              return [value?.toFixed(1), displayName];
            }}
          />
          <Legend
            formatter={(value: string) => {
              const summary = kpiSummary[value];
              return summary?.name?.substring(0, 25) || value;
            }}
            wrapperStyle={{ fontSize: 11 }}
          />
          {avgTarget > 0 && (
            <ReferenceLine
              y={avgTarget}
              stroke="#ef4444"
              strokeDasharray="5 5"
              label={{ value: `Target: ${avgTarget.toFixed(0)}`, position: 'right', fontSize: 10, fill: '#ef4444' }}
            />
          )}
          {selectedKpis.map((code, idx) => {
            const pillarCode = code.split('-')[0];
            const color = PILLAR_COLORS[pillarCode] || KPI_COLORS[idx % KPI_COLORS.length];
            return (
              <Line
                key={code}
                type="monotone"
                dataKey={code}
                stroke={color}
                strokeWidth={2}
                dot={{ r: 3 }}
                activeDot={{ r: 5 }}
                name={code}
                connectNulls
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default KPIChart_dc;
