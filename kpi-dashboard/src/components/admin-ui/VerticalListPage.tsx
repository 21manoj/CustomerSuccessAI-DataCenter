import React, { useEffect, useState, useCallback } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Layers,
  Target,
} from 'lucide-react';
import {
  fetchVerticals,
  type VerticalInfo,
} from '../../api/adminApi';

// ---------------------------------------------------------------------------
// Pillar KPI Detail (fetched on expand)
// ---------------------------------------------------------------------------

interface PillarDetail {
  name: string;
  weight_l2: number;
  kpi_count: number;
  kpis: Record<string, {
    name: string;
    weight_l1: number;
    unit: string;
    higher_is_better: boolean;
    target: { operator?: string; value?: number } | number;
    ranges: Record<string, { min: number; max: number }>;
    frequency: string;
  }>;
}

// ---------------------------------------------------------------------------
// Vertical Card
// ---------------------------------------------------------------------------

const VerticalCard: React.FC<{ info: VerticalInfo }> = ({ info }) => {
  const [expanded, setExpanded] = useState(false);
  const [pillarDetails, setPillarDetails] = useState<Record<string, PillarDetail> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedPillar, setExpandedPillar] = useState<string | null>(null);

  const loadDetails = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/admin-ui/verticals/${encodeURIComponent(info.vertical)}/templates`, { credentials: 'include' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setPillarDetails(data.pillars ?? null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load details');
    } finally {
      setLoading(false);
    }
  }, [info.vertical]);

  const handleToggle = () => {
    if (!expanded && !pillarDetails) loadDetails();
    setExpanded((p) => !p);
  };

  const weightColor = (w: number) => {
    if (w >= 0.25) return 'bg-indigo-100 text-indigo-800';
    if (w >= 0.15) return 'bg-blue-50 text-blue-700';
    return 'bg-gray-100 text-gray-600';
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      {/* Header */}
      <button
        onClick={handleToggle}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {expanded ? <ChevronDown size={18} className="text-gray-400" /> : <ChevronRight size={18} className="text-gray-400" />}
          <Layers size={18} className="text-indigo-500" />
          <div className="text-left">
            <span className="text-base font-semibold text-gray-900">{info.label}</span>
            <span className="ml-2 text-xs text-gray-400 font-mono">({info.vertical})</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium bg-indigo-50 text-indigo-700 rounded-full">
            {info.pillar_count} pillars
          </span>
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium bg-emerald-50 text-emerald-700 rounded-full">
            {info.kpi_count} KPIs
          </span>
        </div>
      </button>

      {/* Summary row — always visible */}
      {!expanded && info.pillar_names && (
        <div className="px-5 pb-4 flex flex-wrap gap-2">
          {Object.entries(info.pillar_names).sort().map(([pid, name]) => (
            <span key={pid} className="inline-flex items-center gap-1 text-xs text-gray-500">
              <span className="font-mono font-semibold text-gray-700">{pid}</span>
              {name}
              <span className={`ml-1 px-1.5 py-0.5 rounded-full text-xs font-semibold ${weightColor((info.default_weights ?? {})[pid] ?? 0.2)}`}>
                {(((info.default_weights ?? {})[pid] ?? 0.2) * 100).toFixed(0)}%
              </span>
            </span>
          ))}
        </div>
      )}

      {/* Expanded — full KPI catalog */}
      {expanded && (
        <div className="border-t border-gray-100 px-5 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
              <span className="ml-2 text-sm text-gray-500">Loading KPI catalog...</span>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-8 gap-2 text-sm text-red-600">
              <AlertTriangle size={16} /> {error}
              <button onClick={loadDetails} className="text-indigo-600 hover:text-indigo-700 font-medium ml-2">Retry</button>
            </div>
          ) : pillarDetails ? (
            <div className="space-y-3">
              {Object.entries(pillarDetails).sort().map(([pid, pillar]) => (
                <div key={pid} className="border border-gray-100 rounded-lg overflow-hidden">
                  {/* Pillar header */}
                  <button
                    onClick={() => setExpandedPillar(expandedPillar === pid ? null : pid)}
                    className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      {expandedPillar === pid ? <ChevronDown size={14} className="text-gray-400" /> : <ChevronRight size={14} className="text-gray-400" />}
                      <span className="font-mono font-bold text-sm text-indigo-700">{pid}</span>
                      <span className="text-sm font-medium text-gray-800">{pillar.name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${weightColor(pillar.weight_l2)}`}>
                        {(pillar.weight_l2 * 100).toFixed(0)}% weight
                      </span>
                      <span className="text-xs text-gray-400">{pillar.kpi_count} KPIs</span>
                    </div>
                  </button>

                  {/* KPI table */}
                  {expandedPillar === pid && (
                    <div className="px-4 py-3">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-xs font-medium text-gray-400 uppercase">
                            <th className="pb-2 pr-3">Code</th>
                            <th className="pb-2 pr-3">Name</th>
                            <th className="pb-2 pr-3 text-right">Weight</th>
                            <th className="pb-2 pr-3 text-center">Direction</th>
                            <th className="pb-2 pr-3">Target</th>
                            <th className="pb-2 pr-3">Healthy</th>
                            <th className="pb-2 pr-3">Risk</th>
                            <th className="pb-2">Critical</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                          {Object.entries(pillar.kpis).sort().map(([code, kpi]) => {
                            const target = typeof kpi.target === 'object' ? kpi.target : { value: kpi.target };
                            const healthy = kpi.ranges?.healthy;
                            const risk = kpi.ranges?.risk;
                            const critical = kpi.ranges?.critical;
                            return (
                              <tr key={code} className="hover:bg-gray-50">
                                <td className="py-2 pr-3 font-mono text-xs font-semibold text-gray-700">{code}</td>
                                <td className="py-2 pr-3 text-gray-800">{kpi.name}</td>
                                <td className="py-2 pr-3 text-right font-semibold text-gray-600">{(kpi.weight_l1 * 100).toFixed(0)}%</td>
                                <td className="py-2 pr-3 text-center">
                                  <span className={`text-xs px-1.5 py-0.5 rounded ${kpi.higher_is_better ? 'bg-green-50 text-green-700' : 'bg-orange-50 text-orange-700'}`}>
                                    {kpi.higher_is_better ? '\u2191 higher' : '\u2193 lower'}
                                  </span>
                                </td>
                                <td className="py-2 pr-3 text-xs text-gray-600">
                                  {target.operator ?? '>'} {target.value ?? '--'} {kpi.unit}
                                </td>
                                <td className="py-2 pr-3 text-xs text-green-600">
                                  {healthy ? `${healthy.min}\u2013${healthy.max}` : '--'}
                                </td>
                                <td className="py-2 pr-3 text-xs text-yellow-600">
                                  {risk ? `${risk.min}\u2013${risk.max}` : '--'}
                                </td>
                                <td className="py-2 text-xs text-red-600">
                                  {critical ? `${critical.min}\u2013${critical.max}` : '--'}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ))}

              {/* Weight total */}
              <div className="flex items-center justify-between px-4 py-2 bg-gray-50 rounded-lg text-xs text-gray-500">
                <span>Total pillar weights</span>
                <span className="font-semibold">
                  {Object.values(pillarDetails).reduce((s, p) => s + p.weight_l2, 0).toFixed(2)} (should be 1.00)
                </span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400 py-8 text-center">No catalog data available.</p>
          )}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

const VerticalListPage: React.FC = () => {
  const [verticals, setVerticals] = useState<VerticalInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setVerticals(await fetchVerticals());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load verticals');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        <span className="ml-3 text-gray-500">Loading verticals...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <AlertTriangle className="w-10 h-10 text-red-400 mb-3" />
        <p className="text-red-600 font-medium mb-4">{error}</p>
        <button
          onClick={load}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
        >
          <RefreshCw size={16} /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold text-gray-900">Vertical KPI Catalogs</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          KPI definitions, pillar weights, scoring ranges, and targets per vertical
        </p>
      </div>

      {verticals.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center text-gray-400 text-sm">
          No verticals configured.
        </div>
      ) : (
        <div className="space-y-3">
          {verticals.map((v) => (
            <VerticalCard key={v.vertical} info={v} />
          ))}
        </div>
      )}
    </div>
  );
};

export default VerticalListPage;
