/**
 * Data Center Infrastructure Health
 * =================================
 * 
 * Displays infrastructure-specific KPIs (primarily from Pillar 2: Operational Stability):
 * - RMA Frequency
 * - MTBF (Mean Time Between Failures)
 * - Critical Incidents
 * - Alert Response Time
 * - GPU Utilization
 * - Network Latency
 */

import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Server, Activity } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';

// ============================================================
// TYPES
// ============================================================

interface InfrastructureKPI {
  kpi_code: string;
  kpi_name: string;
  current_value: number;
  score: number;
  state: 'healthy' | 'at_risk' | 'critical';
  trend?: number[];
  unit?: string;
}

interface InfrastructureHealthProps {
  tenantId: number;
}

// ============================================================
// MAIN COMPONENT
// ============================================================

const DCInfrastructureHealth: React.FC<InfrastructureHealthProps> = ({ tenantId }) => {
  const [kpis, setKpis] = useState<InfrastructureKPI[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchInfrastructureData();
  }, [tenantId]);

  const fetchInfrastructureData = async () => {
    try {
      setLoading(true);
      setError(null);

      const res = await fetch(`/api/dc2s/accounts/${tenantId}/infra`, { credentials: 'include' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const kpiList: InfrastructureKPI[] = (data.kpis || []).map((k: any) => ({
        kpi_code: k.kpi_code,
        kpi_name: k.kpi_name,
        current_value: k.current_value,
        score: k.score,
        state: k.state as 'healthy' | 'at_risk' | 'critical',
        trend: k.trend,
        unit: k.unit,
      }));
      setKpis(kpiList);
    } catch (err: any) {
      console.error('Error fetching infrastructure data:', err);
      setError(err.message || 'Failed to load infrastructure data');
    } finally {
      setLoading(false);
    }
  };

  const getStateColor = (state: string) => {
    switch (state) {
      case 'healthy': return 'text-green-600 bg-green-50 border-green-200';
      case 'at_risk': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'critical': return 'text-red-600 bg-red-50 border-red-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStateIcon = (state: string) => {
    switch (state) {
      case 'healthy': return <CheckCircle className="w-5 h-5" />;
      case 'at_risk': return <AlertTriangle className="w-5 h-5" />;
      case 'critical': return <AlertTriangle className="w-5 h-5" />;
      default: return <Activity className="w-5 h-5" />;
    }
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <Activity className="w-8 h-8 text-blue-500 animate-pulse mx-auto mb-4" />
        <p className="text-gray-600">Loading infrastructure data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-700">{error}</p>
      </div>
    );
  }

  // Prepare chart data
  const chartData = kpis
    .filter(kpi => kpi.trend && kpi.trend.length > 0)
    .map(kpi => ({
      name: kpi.kpi_name,
      data: kpi.trend!.map((value, index) => ({
        week: `Week ${index + 1}`,
        value,
      })),
    }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-3">
        <Server className="w-6 h-6 text-blue-600" />
        <h3 className="text-lg font-semibold text-gray-900">Infrastructure Health</h3>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {kpis.map((kpi) => (
          <div key={kpi.kpi_code} className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <h4 className="font-medium text-gray-900 text-sm">{kpi.kpi_name}</h4>
                <p className="text-2xl font-bold text-gray-900 mt-2">
                  {kpi.current_value}{kpi.unit || ''}
                </p>
              </div>
              <div className={`p-2 rounded-lg ${getStateColor(kpi.state)}`}>
                {getStateIcon(kpi.state)}
              </div>
            </div>
            
            <div className="mt-3 pt-3 border-t border-gray-100">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">Score</span>
                <span className={`font-semibold ${
                  kpi.score >= 80 ? 'text-green-600' :
                  kpi.score >= 50 ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {kpi.score}/100
                </span>
              </div>
              <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${
                    kpi.score >= 80 ? 'bg-green-500' :
                    kpi.score >= 50 ? 'bg-yellow-500' :
                    'bg-red-500'
                  }`}
                  style={{ width: `${kpi.score}%` }}
                />
              </div>
            </div>

            {/* Trend Chart (mini) */}
            {kpi.trend && kpi.trend.length > 0 && (
              <div className="mt-4 h-16">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={kpi.trend.map((v, i) => ({ week: i + 1, value: v }))}>
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke={kpi.score >= 80 ? '#10b981' : kpi.score >= 50 ? '#f59e0b' : '#ef4444'}
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Overall Infrastructure Status */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h4 className="font-semibold text-gray-900 mb-4">Infrastructure Status Summary</h4>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <CheckCircle className="w-8 h-8 text-green-600 mx-auto mb-2" />
            <p className="text-2xl font-bold text-green-600">
              {kpis.filter(k => k.state === 'healthy').length}
            </p>
            <p className="text-sm text-gray-600">Healthy</p>
          </div>
          <div className="text-center p-4 bg-yellow-50 rounded-lg">
            <AlertTriangle className="w-8 h-8 text-yellow-600 mx-auto mb-2" />
            <p className="text-2xl font-bold text-yellow-600">
              {kpis.filter(k => k.state === 'at_risk').length}
            </p>
            <p className="text-sm text-gray-600">At Risk</p>
          </div>
          <div className="text-center p-4 bg-red-50 rounded-lg">
            <AlertTriangle className="w-8 h-8 text-red-600 mx-auto mb-2" />
            <p className="text-2xl font-bold text-red-600">
              {kpis.filter(k => k.state === 'critical').length}
            </p>
            <p className="text-sm text-gray-600">Critical</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DCInfrastructureHealth;
