/**
 * BenchmarksView.tsx
 * ===================
 * Industry benchmarks heatmap table + radar chart comparing account
 * performance against industry percentiles.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  RefreshCw,
  AlertTriangle,
  BarChart3,
  Globe,
} from 'lucide-react';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';
import { fetchIndustryBenchmarks, fetchGraphNodes } from '../../../utils/contextGraphApi';
import type { IndustryBenchmark, ContextNodeDTO } from '../../../types/contextGraph';

interface BenchmarksViewProps {
  accountId: number;
}

const BenchmarksView: React.FC<BenchmarksViewProps> = ({ accountId }) => {
  const [benchmarks, setBenchmarks] = useState<IndustryBenchmark[]>([]);
  const [contextNodes, setContextNodes] = useState<ContextNodeDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [bmData, nodesData] = await Promise.all([
        fetchIndustryBenchmarks(),
        fetchGraphNodes(accountId, 'EXTERNAL_CONTEXT', undefined, 50),
      ]);
      setBenchmarks(bmData);
      setContextNodes(nodesData.nodes || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load benchmarks');
    } finally {
      setLoading(false);
    }
  }, [accountId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Build a lookup of account percentiles from context graph nodes
  const accountPercentiles = useMemo(() => {
    const map: Record<string, number> = {};
    for (const node of contextNodes) {
      const props = node.properties || {};
      const kpi = props.kpi_code || props.kpi_name || node.title;
      const pct = props.account_percentile ?? props.percentile;
      if (kpi && pct != null) {
        map[kpi.toLowerCase()] = Number(pct);
      }
    }
    return map;
  }, [contextNodes]);

  // Unique industries
  const industries = useMemo(() => {
    const set = new Set(benchmarks.map((b) => b.industry));
    return Array.from(set);
  }, [benchmarks]);

  // Cell color based on comparison to percentiles
  const cellColor = (value: number | null, p50: number, p75: number): string => {
    if (value == null) return 'bg-gray-50 text-gray-400';
    if (value >= p75) return 'bg-green-100 text-green-800';
    if (value >= p50) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  // Build radar data (limit to 8 KPIs for readability)
  const radarData = useMemo(() => {
    const kpiMap: Record<string, { kpi: string; account: number; p50: number }> = {};

    for (const bm of benchmarks) {
      const key = bm.kpi_name.toLowerCase();
      const acctPct = accountPercentiles[key];
      if (acctPct != null) {
        kpiMap[key] = {
          kpi: bm.kpi_name.length > 20 ? bm.kpi_name.slice(0, 18) + '..' : bm.kpi_name,
          account: acctPct,
          p50: bm.percentile_50,
        };
      }
    }

    return Object.values(kpiMap).slice(0, 8);
  }, [benchmarks, accountPercentiles]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-8 h-8 text-yellow-500 mx-auto mb-2" />
        <p className="text-gray-600">{error}</p>
      </div>
    );
  }

  if (benchmarks.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-4">
          <Globe className="w-7 h-7 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-700 mb-1">No Benchmarks Available</h3>
        <p className="text-sm text-gray-500">Industry benchmark data has not been loaded yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary stats */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3 bg-white rounded-xl border border-gray-200 px-5 py-3 shadow-sm">
          <BarChart3 className="w-5 h-5 text-blue-500" />
          <div>
            <p className="text-xs text-gray-500">Total Benchmarks</p>
            <p className="text-lg font-bold text-gray-900">{benchmarks.length}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 bg-white rounded-xl border border-gray-200 px-5 py-3 shadow-sm">
          <Globe className="w-5 h-5 text-green-500" />
          <div>
            <p className="text-xs text-gray-500">Industries Covered</p>
            <p className="text-lg font-bold text-gray-900">{industries.length}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 bg-white rounded-xl border border-gray-200 px-5 py-3 shadow-sm">
          <BarChart3 className="w-5 h-5 text-purple-500" />
          <div>
            <p className="text-xs text-gray-500">Account Data Points</p>
            <p className="text-lg font-bold text-gray-900">{Object.keys(accountPercentiles).length}</p>
          </div>
        </div>
      </div>

      {/* Heatmap table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700">Benchmark Heatmap</h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Cell colors: <span className="text-green-700">green</span> = above P75,{' '}
            <span className="text-yellow-700">yellow</span> = P50-P75,{' '}
            <span className="text-red-700">red</span> = below P50
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider min-w-[200px]">
                  KPI
                </th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Industry
                </th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  P25
                </th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  P50
                </th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  P75
                </th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  P90
                </th>
                <th className="text-center py-3 px-4 text-xs font-semibold text-blue-600 uppercase tracking-wider bg-blue-50">
                  Account
                </th>
              </tr>
            </thead>
            <tbody>
              {benchmarks.map((bm, idx) => {
                const acctValue = accountPercentiles[bm.kpi_name.toLowerCase()] ?? null;
                const acctCellStyle = cellColor(acctValue, bm.percentile_50, bm.percentile_75);

                return (
                  <tr key={bm.id || idx} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                    <td className="py-2.5 px-4 font-medium text-gray-800">{bm.kpi_name}</td>
                    <td className="py-2.5 px-4 text-center text-gray-600">{bm.industry}</td>
                    <td className="py-2.5 px-4 text-center font-mono text-gray-600">
                      {bm.percentile_25.toFixed(1)}
                    </td>
                    <td className="py-2.5 px-4 text-center font-mono text-gray-600">
                      {bm.percentile_50.toFixed(1)}
                    </td>
                    <td className="py-2.5 px-4 text-center font-mono text-gray-600">
                      {bm.percentile_75.toFixed(1)}
                    </td>
                    <td className="py-2.5 px-4 text-center font-mono text-gray-600">
                      {bm.percentile_90.toFixed(1)}
                    </td>
                    <td className="py-2.5 px-4 text-center">
                      {acctValue != null ? (
                        <span className={`inline-block px-2.5 py-1 rounded-md text-xs font-bold ${acctCellStyle}`}>
                          {acctValue.toFixed(1)}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-300">--</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Radar chart */}
      {radarData.length >= 3 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Account vs Industry P50</h3>
          <ResponsiveContainer width="100%" height={360}>
            <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="75%">
              <PolarGrid stroke="#e5e7eb" />
              <PolarAngleAxis
                dataKey="kpi"
                tick={{ fontSize: 11, fill: '#6b7280' }}
              />
              <PolarRadiusAxis
                angle={30}
                domain={[0, 100]}
                tick={{ fontSize: 10, fill: '#9ca3af' }}
              />
              <Radar
                name="Account"
                dataKey="account"
                stroke="#2563eb"
                fill="#2563eb"
                fillOpacity={0.2}
                strokeWidth={2}
              />
              <Radar
                name="Industry P50"
                dataKey="p50"
                stroke="#16a34a"
                fill="#16a34a"
                fillOpacity={0.1}
                strokeWidth={2}
                strokeDasharray="4 4"
              />
              <Legend
                wrapperStyle={{ fontSize: '12px' }}
              />
              <Tooltip
                contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                formatter={(value: number, name: string) => [value.toFixed(1), name]}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default BenchmarksView;
