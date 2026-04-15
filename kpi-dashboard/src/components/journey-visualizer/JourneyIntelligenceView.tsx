/**
 * Journey Intelligence View — 3 Independent Graphs
 *
 *   Graph 1 (blue):   KPI Health — structural truth from KPIs only, no decay
 *   Graph 2 (amber):  Signal Score — independent signal-only score (0-100), recency-decayed
 *   Graph 3 (green):  Composite — weighted blend of decayed KPI + decayed Signal (70/30)
 *
 * The GAP between Graph 1 and Graph 3 shows "what KPIs alone miss."
 * Graph 2 shows the qualitative evidence surface independently.
 *
 * API: GET /api/journey-intelligence/<account_id>
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Activity, ChevronDown, AlertTriangle, TrendingUp, TrendingDown, Zap, Info } from 'lucide-react';

// ── Types ──

interface ScorePoint { month: string; score: number; }
interface SignalScorePoint extends ScorePoint { signal_count: number; active_signals?: { type: string; score: number; recency: number }[]; }
interface CompositePoint extends ScorePoint { kpi_component: number; signal_component: number; signal_influence: number; }
interface Signal { date: string; type: string; sentiment: string; signal_score: number; weight: number; health_at_time: number; title?: string; }
interface PlaybookExec { triggered_at: string | null; closed_at: string | null; playbook_id: string; playbook_name?: string; outcome?: string; health_at_trigger?: number; health_at_close?: number; triggered_by?: string; }
interface AccountOption { account_id: number; account_name: string; health: number | null; arr: number; signal_count: number; }

interface JourneyData {
  account_id: number;
  account_name: string;
  arr: number;
  time_range: { start: string; end: string };
  lambda: number;
  half_life_days: number;
  signal_blend_ratio: number;
  kpi_only: ScorePoint[];
  signal_score: SignalScorePoint[];
  signal_score_raw: ScorePoint[];
  composite: CompositePoint[];
  signals: Signal[];
  playbook_executions: PlaybookExec[];
  thresholds: { healthy: number; at_risk: number };
}

// ── Chart Constants ──

const CHART_W = 900;
const CHART_H = 400;
const PAD = { top: 30, right: 30, bottom: 60, left: 55 };
const INNER_W = CHART_W - PAD.left - PAD.right;
const INNER_H = CHART_H - PAD.top - PAD.bottom;

// ── Colors ──
const COLOR_KPI = '#60a5fa';       // blue
const COLOR_SIGNAL = '#f59e0b';    // amber (decayed)
const COLOR_SIGNAL_RAW = '#ef4444'; // red (raw, no decay)
const COLOR_COMPOSITE = '#34d399'; // green
const COLOR_KPI_DIM = '#1e3a5f';
const COLOR_SIGNAL_DIM = '#92400e';
const COLOR_SIGNAL_RAW_DIM = '#7f1d1d';
const COLOR_COMPOSITE_DIM = '#065f46';
const COLOR_PLAYBOOK = '#14b8a6';  // teal for playbook markers

// ── Helpers ──

const formatDate = (iso: string) => {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
};

const formatDateFull = (iso: string) => {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const formatARR = (n: number) => n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : `$${(n / 1e3).toFixed(0)}K`;

const signalLabel = (type: string) => type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

// ── Component ──

const JourneyIntelligenceView: React.FC = () => {
  const [accounts, setAccounts] = useState<AccountOption[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [data, setData] = useState<JourneyData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);

  useEffect(() => {
    fetch('/api/journey-intelligence/accounts', { credentials: 'include' })
      .then(r => r.json())
      .then(d => {
        const list = d.accounts || [];
        setAccounts(list);
        if (list.length > 0) setSelectedId(list[0].account_id);
      })
      .catch(() => setError('Failed to load accounts'));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setLoading(true);
    setError(null);
    fetch(`/api/journey-intelligence/${selectedId}`, { credentials: 'include' })
      .then(r => r.json())
      .then(d => {
        if (d.error) { setError(d.error); setData(null); }
        else setData(d);
      })
      .catch(() => setError('Failed to load journey data'))
      .finally(() => setLoading(false));
  }, [selectedId]);

  const { scaleX, scaleY, timeLabels } = useMemo(() => {
    if (!data || !data.kpi_only.length) return { scaleX: () => 0, scaleY: () => 0, timeLabels: [] };
    const months = data.kpi_only.map(p => new Date(p.month).getTime());
    const minT = Math.min(...months);
    const maxT = Math.max(...months);
    const rangeT = maxT - minT || 1;
    return {
      scaleX: (iso: string) => PAD.left + ((new Date(iso).getTime() - minT) / rangeT) * INNER_W,
      scaleY: (score: number) => PAD.top + INNER_H - (Math.max(0, Math.min(100, score)) / 100) * INNER_H,
      timeLabels: data.kpi_only.map(p => ({ x: PAD.left + ((new Date(p.month).getTime() - minT) / rangeT) * INNER_W, label: formatDate(p.month) })),
    };
  }, [data]);

  const buildPath = useCallback((points: ScorePoint[]) => {
    if (!points.length) return '';
    return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(p.month)} ${scaleY(p.score)}`).join(' ');
  }, [scaleX, scaleY]);

  const selectedAccount = accounts.find(a => a.account_id === selectedId);

  if (error && !data) {
    return (
      <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-4" />
          <p className="text-lg text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Activity className="w-6 h-6 text-emerald-400" />
          <h1 className="text-2xl font-bold">Journey Intelligence</h1>
        </div>

        {/* Account Selector */}
        <div className="relative">
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg px-4 py-2 text-sm transition-colors"
          >
            <span className="text-gray-300">{selectedAccount?.account_name || 'Select account'}</span>
            {selectedAccount && <span className="text-gray-500 text-xs">{formatARR(selectedAccount.arr)}</span>}
            <ChevronDown className="w-4 h-4 text-gray-500" />
          </button>
          {showDropdown && (
            <div className="absolute right-0 top-full mt-1 w-80 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 max-h-72 overflow-y-auto">
              {accounts.map(a => (
                <button
                  key={a.account_id}
                  onClick={() => { setSelectedId(a.account_id); setShowDropdown(false); }}
                  className={`w-full text-left px-4 py-2.5 hover:bg-gray-700 flex items-center justify-between text-sm ${a.account_id === selectedId ? 'bg-gray-700' : ''}`}
                >
                  <div>
                    <span className="text-gray-200">{a.account_name}</span>
                    <span className="ml-2 text-gray-500 text-xs">{formatARR(a.arr)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {a.signal_count > 0 && <span className="text-xs text-amber-400">{a.signal_count} signals</span>}
                    {a.health !== null && (
                      <span className={`text-xs font-semibold ${a.health >= 70 ? 'text-emerald-400' : a.health >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                        {a.health.toFixed(0)}
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-emerald-400" />
        </div>
      )}

      {data && !loading && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-5 gap-4 mb-6">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">KPI Health</p>
              <p className="text-2xl font-bold mt-1" style={{ color: COLOR_KPI }}>
                {data.kpi_only[data.kpi_only.length - 1]?.score.toFixed(1)}
              </p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Signal Score</p>
              <p className="text-2xl font-bold mt-1" style={{ color: COLOR_SIGNAL }}>
                {data.signal_score[data.signal_score.length - 1]?.score.toFixed(1)}
              </p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Composite (DNA)</p>
              <p className="text-2xl font-bold mt-1" style={{ color: COLOR_COMPOSITE }}>
                {data.composite[data.composite.length - 1]?.score.toFixed(1)}
              </p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Signal Influence</p>
              {(() => {
                const inf = data.composite[data.composite.length - 1]?.signal_influence || 0;
                return (
                  <p className={`text-2xl font-bold mt-1 ${inf >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {inf >= 0 ? '+' : ''}{inf.toFixed(1)}
                  </p>
                );
              })()}
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wide">Signals / Playbooks</p>
              <p className="text-2xl font-bold text-gray-300 mt-1">
                {data.signals.length} / {data.playbook_executions.length}
              </p>
            </div>
          </div>

          {/* Chart */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-200">Health Score Journey</h2>
              <div className="flex items-center gap-1 text-xs text-gray-500">
                <Info className="w-3 h-3" />
                <span>Blend: {Math.round((data.signal_blend_ratio || 0.3) * 100)}% signal / {Math.round((1 - (data.signal_blend_ratio || 0.3)) * 100)}% KPI | Decay: {data.half_life_days}d half-life</span>
              </div>
            </div>

            <svg
              viewBox={`0 0 ${CHART_W} ${CHART_H}`}
              className="w-full"
              style={{ maxHeight: '420px' }}
              onMouseLeave={() => setHoveredIdx(null)}
            >
              {/* Threshold bands */}
              <rect x={PAD.left} y={scaleY(100)} width={INNER_W} height={scaleY(data.thresholds.healthy) - scaleY(100)} fill="rgba(16,185,129,0.06)" />
              <rect x={PAD.left} y={scaleY(data.thresholds.healthy)} width={INNER_W} height={scaleY(data.thresholds.at_risk) - scaleY(data.thresholds.healthy)} fill="rgba(245,158,11,0.06)" />
              <rect x={PAD.left} y={scaleY(data.thresholds.at_risk)} width={INNER_W} height={scaleY(0) - scaleY(data.thresholds.at_risk)} fill="rgba(239,68,68,0.06)" />

              {/* Threshold lines */}
              <line x1={PAD.left} x2={PAD.left + INNER_W} y1={scaleY(data.thresholds.healthy)} y2={scaleY(data.thresholds.healthy)} stroke="rgba(16,185,129,0.3)" strokeDasharray="4 4" />
              <line x1={PAD.left} x2={PAD.left + INNER_W} y1={scaleY(data.thresholds.at_risk)} y2={scaleY(data.thresholds.at_risk)} stroke="rgba(239,68,68,0.3)" strokeDasharray="4 4" />
              <text x={PAD.left + 4} y={scaleY(data.thresholds.healthy) - 4} fill="rgba(16,185,129,0.5)" fontSize="9">Healthy ({data.thresholds.healthy})</text>
              <text x={PAD.left + 4} y={scaleY(data.thresholds.at_risk) - 4} fill="rgba(239,68,68,0.5)" fontSize="9">At-Risk ({data.thresholds.at_risk})</text>

              {/* Y-axis labels */}
              {[0, 20, 40, 60, 80, 100].map(v => (
                <g key={v}>
                  <text x={PAD.left - 8} y={scaleY(v) + 4} fill="#6b7280" fontSize="10" textAnchor="end">{v}</text>
                  <line x1={PAD.left} x2={PAD.left + INNER_W} y1={scaleY(v)} y2={scaleY(v)} stroke="rgba(75,85,99,0.15)" />
                </g>
              ))}

              {/* X-axis labels */}
              {timeLabels.map((tl, i) => (
                <text key={i} x={tl.x} y={CHART_H - PAD.bottom + 18} fill="#6b7280" fontSize="10" textAnchor="middle">{tl.label}</text>
              ))}

              {/* Playbook execution spans */}
              {data.playbook_executions.map((pb, i) => {
                if (!pb.triggered_at) return null;
                const x1 = scaleX(pb.triggered_at);
                const x2 = pb.closed_at ? scaleX(pb.closed_at) : x1 + 20;
                return (
                  <g key={`pb-${i}`}>
                    <rect x={x1} y={PAD.top} width={Math.max(x2 - x1, 4)} height={INNER_H} fill="rgba(20,184,166,0.08)" rx={2} />
                    <line x1={x1} x2={x1} y1={PAD.top} y2={PAD.top + INNER_H} stroke="rgba(20,184,166,0.3)" strokeDasharray="2 2" />
                    <text x={x1 + 3} y={CHART_H - PAD.bottom + 34} fill="rgba(20,184,166,0.6)" fontSize="8" transform={`rotate(-30, ${x1 + 3}, ${CHART_H - PAD.bottom + 34})`}>
                      {pb.playbook_id}
                    </text>
                  </g>
                );
              })}

              {/* Gap fill between KPI-only and Composite */}
              {data.kpi_only.length > 1 && (
                <path
                  d={
                    data.kpi_only.map((p, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(p.month)} ${scaleY(p.score)}`).join(' ') +
                    ' ' +
                    [...data.composite].reverse().map((p, i) => `${i === 0 ? 'L' : 'L'} ${scaleX(p.month)} ${scaleY(p.score)}`).join(' ') +
                    ' Z'
                  }
                  fill="rgba(52,211,153,0.1)"
                />
              )}

              {/* Graph 2a: Signal Score Raw (red, dotted — no decay) */}
              <path d={buildPath(data.signal_score_raw)} fill="none" stroke={COLOR_SIGNAL_RAW} strokeWidth={1.5} strokeDasharray="3 3" opacity={0.6} />

              {/* Graph 2b: Signal Score Decayed (amber, dashed) */}
              <path d={buildPath(data.signal_score)} fill="none" stroke={COLOR_SIGNAL} strokeWidth={2} strokeDasharray="6 3" />

              {/* Graph 1: KPI-only (blue solid) */}
              <path d={buildPath(data.kpi_only)} fill="none" stroke={COLOR_KPI} strokeWidth={2.5} />

              {/* Graph 3: Composite (green solid) */}
              <path d={buildPath(data.composite)} fill="none" stroke={COLOR_COMPOSITE} strokeWidth={2.5} />

              {/* Data points on KPI-only */}
              {data.kpi_only.map((p, i) => (
                <circle
                  key={`kpi-${i}`} cx={scaleX(p.month)} cy={scaleY(p.score)}
                  r={hoveredIdx === i ? 5 : 3} fill={COLOR_KPI} stroke={COLOR_KPI_DIM} strokeWidth={1}
                  onMouseEnter={() => setHoveredIdx(i)} style={{ cursor: 'pointer' }}
                />
              ))}

              {/* Data points on Signal Score Raw */}
              {data.signal_score_raw.map((p, i) => (
                <circle
                  key={`raw-${i}`} cx={scaleX(p.month)} cy={scaleY(p.score)}
                  r={hoveredIdx === i ? 3.5 : 2} fill={COLOR_SIGNAL_RAW} stroke={COLOR_SIGNAL_RAW_DIM} strokeWidth={1} opacity={0.7}
                  onMouseEnter={() => setHoveredIdx(i)} style={{ cursor: 'pointer' }}
                />
              ))}

              {/* Data points on Signal Score Decayed */}
              {data.signal_score.map((p, i) => (
                <circle
                  key={`sig-${i}`} cx={scaleX(p.month)} cy={scaleY(p.score)}
                  r={hoveredIdx === i ? 4 : 2.5} fill={COLOR_SIGNAL} stroke={COLOR_SIGNAL_DIM} strokeWidth={1}
                  onMouseEnter={() => setHoveredIdx(i)} style={{ cursor: 'pointer' }}
                />
              ))}

              {/* Data points on Composite */}
              {data.composite.map((p, i) => (
                <circle
                  key={`comp-${i}`} cx={scaleX(p.month)} cy={scaleY(p.score)}
                  r={hoveredIdx === i ? 5 : 3} fill={COLOR_COMPOSITE} stroke={COLOR_COMPOSITE_DIM} strokeWidth={1}
                  onMouseEnter={() => setHoveredIdx(i)} style={{ cursor: 'pointer' }}
                />
              ))}

              {/* Signal event markers */}
              {data.signals.map((sig, i) => {
                const x = scaleX(sig.date);
                const y = scaleY(sig.signal_score);
                const isPositive = sig.signal_score >= 50;
                return (
                  <g key={`sig-marker-${i}`}>
                    <polygon
                      points={isPositive
                        ? `${x},${y - 7} ${x - 5},${y + 3} ${x + 5},${y + 3}`
                        : `${x},${y + 7} ${x - 5},${y - 3} ${x + 5},${y - 3}`
                      }
                      fill={isPositive ? '#10b981' : '#ef4444'}
                      opacity={0.8}
                    />
                  </g>
                );
              })}

              {/* Playbook execution markers (⚡ diamond at trigger date) */}
              {data.playbook_executions.map((pb, i) => {
                if (!pb.triggered_at) return null;
                const x = scaleX(pb.triggered_at);
                const trigHealth = pb.health_at_trigger || 70;
                const y = scaleY(trigHealth);
                return (
                  <g key={`pb-marker-${i}`}>
                    {/* Diamond shape */}
                    <polygon
                      points={`${x},${y - 8} ${x + 6},${y} ${x},${y + 8} ${x - 6},${y}`}
                      fill={COLOR_PLAYBOOK}
                      stroke="#0d9488"
                      strokeWidth={1.5}
                      opacity={0.9}
                    />
                    {/* ⚡ inside diamond */}
                    <text x={x} y={y + 3} textAnchor="middle" fill="#fff" fontSize="8" fontWeight="bold">⚡</text>
                  </g>
                );
              })}

              {/* Hover tooltip */}
              {hoveredIdx !== null && data.kpi_only[hoveredIdx] && (
                <g>
                  <line
                    x1={scaleX(data.kpi_only[hoveredIdx].month)} x2={scaleX(data.kpi_only[hoveredIdx].month)}
                    y1={PAD.top} y2={PAD.top + INNER_H} stroke="rgba(255,255,255,0.2)" strokeDasharray="3 3"
                  />
                  <foreignObject
                    x={Math.min(scaleX(data.kpi_only[hoveredIdx].month) + 10, CHART_W - 200)}
                    y={PAD.top + 10} width={190} height={155}
                  >
                    <div className="bg-gray-800 border border-gray-700 rounded-lg p-2.5 text-xs shadow-xl">
                      <p className="font-semibold text-gray-300 mb-1.5">{formatDate(data.kpi_only[hoveredIdx].month)}</p>
                      <div className="flex justify-between mb-1">
                        <span style={{ color: COLOR_KPI }}>KPI Health:</span>
                        <span className="font-bold" style={{ color: COLOR_KPI }}>{data.kpi_only[hoveredIdx].score.toFixed(1)}</span>
                      </div>
                      <div className="flex justify-between mb-1">
                        <span style={{ color: COLOR_SIGNAL_RAW }}>Signal (raw):</span>
                        <span className="font-bold" style={{ color: COLOR_SIGNAL_RAW }}>{data.signal_score_raw[hoveredIdx]?.score.toFixed(1)}</span>
                      </div>
                      <div className="flex justify-between mb-1">
                        <span style={{ color: COLOR_SIGNAL }}>Signal (decayed):</span>
                        <span className="font-bold" style={{ color: COLOR_SIGNAL }}>{data.signal_score[hoveredIdx]?.score.toFixed(1)}</span>
                      </div>
                      <div className="flex justify-between mb-1">
                        <span style={{ color: COLOR_COMPOSITE }}>Composite:</span>
                        <span className="font-bold" style={{ color: COLOR_COMPOSITE }}>{data.composite[hoveredIdx]?.score.toFixed(1)}</span>
                      </div>
                      {data.composite[hoveredIdx]?.signal_influence !== 0 && (
                        <div className="flex justify-between border-t border-gray-700 pt-1 mt-1">
                          <span className="text-gray-400">Signal influence:</span>
                          <span className={`font-bold ${(data.composite[hoveredIdx]?.signal_influence || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {(data.composite[hoveredIdx]?.signal_influence || 0) >= 0 ? '+' : ''}
                            {data.composite[hoveredIdx]?.signal_influence.toFixed(1)}
                          </span>
                        </div>
                      )}
                    </div>
                  </foreignObject>
                </g>
              )}
            </svg>

            {/* Legend */}
            <div className="flex items-center gap-6 mt-3 px-2">
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5" style={{ backgroundColor: COLOR_KPI }} />
                <span className="text-xs text-gray-400">KPI Health (no decay)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5" style={{ backgroundColor: COLOR_SIGNAL_RAW, borderTop: '1.5px dotted #ef4444' }} />
                <span className="text-xs text-gray-400">Signal (raw)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5" style={{ backgroundColor: COLOR_SIGNAL, borderTop: '1.5px dashed #f59e0b' }} />
                <span className="text-xs text-gray-400">Signal (decayed)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5" style={{ backgroundColor: COLOR_COMPOSITE }} />
                <span className="text-xs text-gray-400">Composite ({Math.round((data.signal_blend_ratio || 0.3) * 100)}% signal)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-0 h-0 border-l-[4px] border-r-[4px] border-b-[7px] border-l-transparent border-r-transparent border-b-emerald-500" />
                <span className="text-xs text-gray-400">Positive signal</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-0 h-0 border-l-[4px] border-r-[4px] border-t-[7px] border-l-transparent border-r-transparent border-t-red-500" />
                <span className="text-xs text-gray-400">Negative signal</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rotate-45 bg-teal-500 rounded-sm" />
                <span className="text-xs text-gray-400">Playbook ⚡</span>
              </div>
            </div>
          </div>

          {/* Signal Timeline Table */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mt-6">
            <h3 className="text-sm font-semibold text-gray-300 mb-3">Signal Timeline</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-800">
                    <th className="text-left py-2 px-2">Date</th>
                    <th className="text-left py-2 px-2">Signal</th>
                    <th className="text-center py-2 px-2">Sentiment</th>
                    <th className="text-right py-2 px-2">Signal Score</th>
                    <th className="text-right py-2 px-2">Weight</th>
                    <th className="text-right py-2 px-2">KPI at Time</th>
                  </tr>
                </thead>
                <tbody>
                  {data.signals.map((sig, i) => (
                    <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/50">
                      <td className="py-2 px-2 text-gray-400">{formatDate(sig.date)}</td>
                      <td className="py-2 px-2 text-gray-200">{signalLabel(sig.type)}</td>
                      <td className="py-2 px-2 text-center">
                        {sig.signal_score >= 50
                          ? <TrendingUp className="w-3.5 h-3.5 text-emerald-400 inline" />
                          : <TrendingDown className="w-3.5 h-3.5 text-red-400 inline" />
                        }
                      </td>
                      <td className={`py-2 px-2 text-right font-semibold ${sig.signal_score >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {sig.signal_score}
                      </td>
                      <td className="py-2 px-2 text-right text-gray-400">{sig.weight.toFixed(1)}x</td>
                      <td className="py-2 px-2 text-right text-gray-300">{sig.health_at_time.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Playbook Executions */}
          {data.playbook_executions.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mt-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Playbook Executions</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {data.playbook_executions.map((pb, i) => (
                  <div key={i} className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3 flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <Zap className="w-3.5 h-3.5 text-teal-400" />
                        <span className="text-sm font-medium text-gray-200">{pb.playbook_name || pb.playbook_id}</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {pb.triggered_at ? formatDateFull(pb.triggered_at) : '?'} → {pb.closed_at ? formatDateFull(pb.closed_at) : 'Open'}
                        {pb.triggered_by && <span className="ml-1 text-gray-600">({pb.triggered_by})</span>}
                      </p>
                    </div>
                    <div className="text-right">
                      {pb.health_at_trigger !== null && pb.health_at_close !== null && (
                        <p className="text-xs">
                          <span className="text-gray-400">{pb.health_at_trigger?.toFixed(0)}</span>
                          <span className="text-gray-600 mx-1">→</span>
                          <span className={`font-semibold ${(pb.health_at_close || 0) > (pb.health_at_trigger || 0) ? 'text-emerald-400' : 'text-red-400'}`}>
                            {pb.health_at_close?.toFixed(0)}
                          </span>
                        </p>
                      )}
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${pb.outcome === 'resolved' ? 'bg-emerald-900/50 text-emerald-400' : pb.outcome === 'timeout' ? 'bg-red-900/50 text-red-400' : 'bg-gray-700 text-gray-400'}`}>
                        {pb.outcome || 'in-progress'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default JourneyIntelligenceView;
