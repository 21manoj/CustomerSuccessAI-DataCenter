/**
 * StoryArcsView.tsx
 * ==================
 * Two-panel layout: left = list of story arc templates, right = full arc detail.
 * Shows revenue narrative, phase timeline, cast, decisions, outcomes,
 * and a health trajectory area chart.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw,
  AlertTriangle,
  BookOpen,
  Clock,
  Users,
  Target,
  GitBranch,
  ChevronRight,
  CheckCircle2,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { fetchStoryArcs, fetchStoryArc, fetchAccountStoryArc, fmtDollar } from '../../../utils/contextGraphApi';
import type { StoryArcSummary, StoryArcFull } from '../../../types/contextGraph';

interface StoryArcsViewProps {
  accountId?: number;
}

const AUDIENCE_STYLES: Record<string, { bg: string; text: string }> = {
  CRO: { bg: 'bg-blue-100', text: 'text-blue-800' },
  CFO: { bg: 'bg-green-100', text: 'text-green-800' },
  CEO: { bg: 'bg-purple-100', text: 'text-purple-800' },
};

const PHASE_COLORS = ['#3b82f6', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#6366f1'];

const StoryArcsView: React.FC<StoryArcsViewProps> = ({ accountId }) => {
  const [arcs, setArcs] = useState<StoryArcSummary[]>([]);
  const [selectedArcId, setSelectedArcId] = useState<string | null>(null);
  const [arcDetail, setArcDetail] = useState<StoryArcFull | null>(null);
  const [accountArc, setAccountArc] = useState<StoryArcFull | null>(null);
  const [accountArcLoading, setAccountArcLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load arc summaries
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetchStoryArcs()
      .then((data) => {
        if (cancelled) return;
        setArcs(data);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || 'Failed to load story arcs');
        setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  // Load account-specific story arc when accountId changes
  useEffect(() => {
    if (!accountId) {
      setAccountArc(null);
      return;
    }

    let cancelled = false;
    setAccountArcLoading(true);

    fetchAccountStoryArc(accountId)
      .then((data) => {
        if (cancelled) return;
        setAccountArc(data);
        // Auto-select the account arc on first load
        if (!selectedArcId) {
          setArcDetail(data);
          setSelectedArcId(data.arc_id);
        }
        setAccountArcLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setAccountArc(null);
        setAccountArcLoading(false);
      });

    return () => { cancelled = true; };
  }, [accountId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Load arc detail on selection
  const loadArcDetail = useCallback(async (arcId: string) => {
    // If the account arc is selected, use it directly (already loaded)
    if (accountArc && arcId === accountArc.arc_id) {
      setSelectedArcId(arcId);
      setArcDetail(accountArc);
      return;
    }
    setSelectedArcId(arcId);
    setDetailLoading(true);
    setArcDetail(null);
    try {
      const detail = await fetchStoryArc(arcId);
      setArcDetail(detail);
    } catch (err: any) {
      setError(err.message || 'Failed to load arc detail');
    } finally {
      setDetailLoading(false);
    }
  }, [accountArc]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error && arcs.length === 0) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-8 h-8 text-yellow-500 mx-auto mb-2" />
        <p className="text-gray-600">{error}</p>
      </div>
    );
  }

  if (arcs.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-gray-100 mb-4">
          <BookOpen className="w-7 h-7 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-700 mb-1">No Story Arcs Available</h3>
        <p className="text-sm text-gray-500">Story arc templates have not been configured yet.</p>
      </div>
    );
  }

  // Build health trajectory data for the chart
  const buildHealthTrajectory = (arc: StoryArcFull) => {
    const points: { week: number; health: number; phase: string }[] = [];
    let weekOffset = 0;

    for (const phase of arc.phases || []) {
      const startHealth = phase.health_range?.start ?? 50;
      const endHealth = phase.health_range?.end ?? 50;
      const duration = phase.duration_weeks || 1;

      for (let w = 0; w <= duration; w++) {
        const progress = w / duration;
        const health = Math.round(startHealth + (endHealth - startHealth) * progress);
        points.push({ week: weekOffset + w, health, phase: phase.name });
      }
      weekOffset += duration;
    }
    return points;
  };

  // Calculate total phase duration for the bar
  const totalDuration = arcDetail
    ? (arcDetail.phases || []).reduce((sum, p) => sum + (p.duration_weeks || 0), 0)
    : 0;

  return (
    <div className="flex gap-6 min-h-[500px]">
      {/* Left panel - arc list */}
      <div className="w-80 flex-shrink-0 space-y-3 overflow-y-auto max-h-[calc(100vh-200px)]">
        {/* Account-specific story arc (shown first when available) */}
        {accountArc && (
          <>
            <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              This Account
            </h3>
            <button
              onClick={() => {
                setSelectedArcId(accountArc.arc_id);
                setArcDetail(accountArc);
              }}
              className={`w-full text-left rounded-xl border-2 p-4 transition-all hover:shadow-md ${
                selectedArcId === accountArc.arc_id
                  ? 'border-green-400 ring-2 ring-green-200 shadow-md bg-green-50/50'
                  : 'border-green-200 bg-green-50/30 hover:border-green-300'
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <p className="text-sm font-semibold text-gray-900 leading-tight">{accountArc.arc_name}</p>
                <ChevronRight className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
              </div>

              <p className="text-xs text-green-700 mb-2">
                Built from live context graph data
              </p>

              <div className="flex flex-wrap gap-1.5 mb-2">
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  Live Data
                </span>
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {accountArc.duration_weeks}w
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs text-gray-500">
                <span>{accountArc.num_phases} phases</span>
                <span>{accountArc.num_decisions} decisions</span>
                <span>{accountArc.num_outcomes} outcomes</span>
              </div>

              <div className="mt-2 text-xs text-gray-500">
                ARR: {fmtDollar(accountArc.arr_start)}
              </div>
            </button>
          </>
        )}
        {accountArcLoading && (
          <div className="flex items-center gap-2 py-3 px-4 bg-green-50/30 rounded-xl border border-green-200">
            <RefreshCw className="w-4 h-4 animate-spin text-green-500" />
            <span className="text-xs text-green-600">Loading account story...</span>
          </div>
        )}

        {/* Template arcs */}
        <h3 className="text-sm font-semibold text-gray-700 mb-2 mt-4">Reference Patterns</h3>
        {arcs.map((arc) => {
          const aud = AUDIENCE_STYLES[arc.target_audience] || { bg: 'bg-gray-100', text: 'text-gray-800' };
          return (
            <button
              key={arc.arc_id}
              onClick={() => loadArcDetail(arc.arc_id)}
              className={`w-full text-left bg-white rounded-xl border p-4 transition-all hover:shadow-md ${
                selectedArcId === arc.arc_id
                  ? 'border-blue-400 ring-2 ring-blue-200 shadow-md'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <p className="text-sm font-semibold text-gray-900 leading-tight">{arc.arc_name}</p>
                <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
              </div>

              <div className="flex flex-wrap gap-1.5 mb-2">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${aud.bg} ${aud.text}`}>
                  {arc.target_audience}
                </span>
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {arc.duration_weeks}w
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs text-gray-500">
                <span>{arc.num_phases} phases</span>
                <span>{arc.num_outcomes} outcomes</span>
              </div>

              <div className="mt-2 text-xs text-gray-500">
                {fmtDollar(arc.arr_start)} &rarr; {fmtDollar(arc.arr_end)}
              </div>
            </button>
          );
        })}
      </div>

      {/* Right panel - arc detail */}
      <div className="flex-1 min-w-0">
        {!selectedArcId && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <BookOpen className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-400">Select a story arc to view details</p>
            </div>
          </div>
        )}

        {detailLoading && (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
          </div>
        )}

        {arcDetail && !detailLoading && (
          <div className="space-y-6">
            {/* Arc header */}
            <div>
              <h2 className="text-xl font-bold text-gray-900">{arcDetail.arc_name}</h2>
              {arcDetail.description && (
                <p className="text-sm text-gray-500 mt-1">{arcDetail.description}</p>
              )}
            </div>

            {/* Revenue narrative */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Revenue Narrative</h3>
              <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                {[
                  { label: 'ARR Start', value: fmtDollar(arcDetail.revenue_narrative.arr_start), color: 'text-gray-900' },
                  { label: 'ARR End', value: fmtDollar(arcDetail.revenue_narrative.arr_end), color: 'text-gray-900' },
                  { label: 'Cost of Inaction', value: fmtDollar(arcDetail.revenue_narrative.cost_of_inaction), color: 'text-red-600' },
                  { label: 'ROI of Intervention', value: fmtDollar(arcDetail.revenue_narrative.roi_of_intervention), color: 'text-green-600' },
                  { label: 'Net Revenue Saved', value: fmtDollar(arcDetail.revenue_narrative.net_revenue_saved), color: 'text-blue-600' },
                  { label: 'Intervention Cost', value: fmtDollar(arcDetail.revenue_narrative.intervention_cost), color: 'text-amber-600' },
                ].map((item) => (
                  <div key={item.label} className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-500 mb-1">{item.label}</p>
                    <p className={`text-lg font-bold ${item.color}`}>{item.value}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Phase timeline bar */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Phase Timeline</h3>
              <div className="flex rounded-lg overflow-hidden h-10">
                {(arcDetail.phases || []).map((phase, idx) => {
                  const widthPct = totalDuration > 0
                    ? ((phase.duration_weeks || 0) / totalDuration) * 100
                    : 0;
                  return (
                    <div
                      key={phase.phase_id}
                      className="relative group flex items-center justify-center text-xs font-medium text-white transition-opacity hover:opacity-90"
                      style={{
                        width: `${widthPct}%`,
                        backgroundColor: PHASE_COLORS[idx % PHASE_COLORS.length],
                        minWidth: '40px',
                      }}
                      title={`${phase.name}: ${phase.duration_weeks}w`}
                    >
                      <span className="truncate px-1">{phase.name}</span>
                    </div>
                  );
                })}
              </div>
              <div className="flex justify-between mt-1.5 text-xs text-gray-400">
                <span>Week 0</span>
                <span>Week {totalDuration}</span>
              </div>
            </div>

            {/* Cast table */}
            {arcDetail.cast && arcDetail.cast.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <Users className="w-4 h-4 text-blue-500" />
                  Cast ({arcDetail.cast.length})
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Role</th>
                        <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Title</th>
                        <th className="text-center py-2 px-3 text-xs font-medium text-gray-500 uppercase">Influence</th>
                        <th className="text-left py-2 px-3 text-xs font-medium text-gray-500 uppercase">Engagement</th>
                      </tr>
                    </thead>
                    <tbody>
                      {arcDetail.cast.map((member, idx) => (
                        <tr key={idx} className="border-b border-gray-100 last:border-0">
                          <td className="py-2 px-3 font-medium text-gray-800">{member.role}</td>
                          <td className="py-2 px-3 text-gray-600">{member.title}</td>
                          <td className="py-2 px-3 text-center">
                            <div className="inline-flex items-center gap-1.5">
                              <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                <div
                                  className="h-full rounded-full bg-blue-500"
                                  style={{ width: `${Math.min(member.influence_score * 100, 100)}%` }}
                                />
                              </div>
                              <span className="text-xs text-gray-500">{Math.round(member.influence_score * 100)}</span>
                            </div>
                          </td>
                          <td className="py-2 px-3 text-gray-600">{member.engagement_frequency}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Decisions */}
            {arcDetail.decisions && arcDetail.decisions.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-purple-500" />
                  Decisions ({arcDetail.decisions.length})
                </h3>
                <div className="space-y-3">
                  {arcDetail.decisions.map((dec) => (
                    <div key={dec.decision_id} className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-start justify-between mb-2">
                        <p className="text-sm font-medium text-gray-800">{dec.title}</p>
                        <span className="text-xs text-gray-400 flex-shrink-0 ml-2">Week {dec.week}</span>
                      </div>
                      <div className="space-y-1 mb-2">
                        {(dec.options || []).map((opt, idx) => (
                          <div
                            key={idx}
                            className={`flex items-center gap-2 text-xs px-2.5 py-1.5 rounded ${
                              idx === dec.chosen_option
                                ? 'bg-green-100 text-green-800 font-medium'
                                : 'bg-white text-gray-600 border border-gray-200'
                            }`}
                          >
                            {idx === dec.chosen_option && (
                              <CheckCircle2 className="w-3.5 h-3.5 text-green-600 flex-shrink-0" />
                            )}
                            <span>{opt.option}</span>
                            <span className="ml-auto text-xs opacity-70">{fmtDollar(opt.projected_impact)}</span>
                          </div>
                        ))}
                      </div>
                      {dec.revenue_impact !== 0 && (
                        <p className="text-xs text-gray-500">
                          Revenue impact: <span className="font-medium">{fmtDollar(dec.revenue_impact)}</span>
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Outcomes */}
            {arcDetail.outcomes && arcDetail.outcomes.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                  <Target className="w-4 h-4 text-green-500" />
                  Outcomes ({arcDetail.outcomes.length})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {arcDetail.outcomes.map((out) => (
                    <div key={out.outcome_id} className="bg-gray-50 rounded-lg p-4">
                      <p className="text-sm font-medium text-gray-800 mb-1">{out.title}</p>
                      <div className="flex flex-wrap gap-2 mb-2">
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                          {out.outcome_type}
                        </span>
                        <span className="text-xs text-gray-500">Week {out.realized_week}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold text-green-600">{fmtDollar(out.revenue_value)}</span>
                        <span className="text-xs text-gray-400">
                          {Math.round(out.confidence * 100)}% confidence
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Health trajectory chart */}
            {arcDetail.phases && arcDetail.phases.length > 0 && (
              <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
                <h3 className="text-sm font-semibold text-gray-700 mb-4">Health Trajectory</h3>
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart
                    data={buildHealthTrajectory(arcDetail)}
                    margin={{ top: 5, right: 20, bottom: 5, left: 0 }}
                  >
                    <defs>
                      <linearGradient id="healthGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="week"
                      tick={{ fontSize: 12 }}
                      label={{ value: 'Week', position: 'insideBottom', offset: -2, fontSize: 11 }}
                    />
                    <YAxis
                      domain={[0, 100]}
                      tick={{ fontSize: 12 }}
                      label={{ value: 'Health', angle: -90, position: 'insideLeft', fontSize: 11 }}
                    />
                    <Tooltip
                      contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                      formatter={(value: number, _name: string, props: any) => [
                        `${value}`,
                        `Health (${props.payload.phase})`,
                      ]}
                      labelFormatter={(label) => `Week ${label}`}
                    />
                    <Area
                      type="monotone"
                      dataKey="health"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      fill="url(#healthGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default StoryArcsView;
