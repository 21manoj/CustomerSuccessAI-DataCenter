import React, { useEffect, useState, useMemo } from 'react';
import { apiCall, getCustomerIdentifier } from '../../../utils/api';
import { useSession } from '../../../contexts/SessionContext';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import {
  AlertTriangle, Activity, Clock, Zap, TrendingDown,
  Users, Shield, ChevronRight, Radio, Target, CheckCircle2,
  ArrowUpRight, ArrowDownRight, Play,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Account {
  id: number;
  name: string;
  arr?: number;
}

interface SignalNode {
  id: string;
  node_type: string;
  subtype?: string;
  label: string;
  severity?: 'critical' | 'warning' | 'info' | 'resolved';
  status?: string;
  revenue_impact?: number;
  created_at?: string;
  updated_at?: string;
  resolved_at?: string;
  metadata?: Record<string, unknown>;
  account_id?: number;
  _account_name?: string;
}

interface SignalEdge {
  id: string;
  source_id: string;
  target_id: string;
  edge_type: string;
  weight?: number;
  metadata?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Constants & Helpers
// ---------------------------------------------------------------------------

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  warning: '#eab308',
  info: '#22d3ee',
  resolved: '#22c55e',
};

const SEVERITY_BG: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  warning: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  info: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  resolved: 'bg-green-500/20 text-green-400 border-green-500/30',
};

const SEVERITY_BORDER: Record<string, string> = {
  critical: 'border-l-red-500',
  warning: 'border-l-yellow-500',
  info: 'border-l-cyan-500',
  resolved: 'border-l-green-500',
};

const SUBTYPE_ACTIONS: Record<string, string> = {
  kpi_breach: 'Review KPI thresholds and trigger relevant playbook',
  usage_decline: 'Schedule EBR to discuss adoption',
  champion_change: 'Identify new sponsor and schedule intro',
  contract_risk: 'Escalate to leadership and prepare retention offer',
  support_escalation: 'Coordinate with support team on resolution timeline',
  nps_drop: 'Launch targeted feedback survey and follow-up campaign',
  expansion_blocker: 'Remove adoption friction and present expansion business case',
  onboarding_delay: 'Re-engage onboarding team and reset milestones',
  executive_disengagement: 'Schedule executive sponsor alignment meeting',
  product_gap: 'Document feature request and connect with product team',
  integration_failure: 'Engage technical team for integration troubleshooting',
  billing_dispute: 'Coordinate with finance to resolve billing concerns',
};

const getRecommendedAction = (subtype?: string): string => {
  if (!subtype) return 'Investigate signal and determine appropriate response';
  return SUBTYPE_ACTIONS[subtype] ?? `Investigate ${subtype.replace(/_/g, ' ')} and determine next steps`;
};

const formatCurrency = (value: number): string => {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
};

const formatDate = (iso: string): string => {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

const daysSince = (iso: string): number => {
  const ms = Date.now() - new Date(iso).getTime();
  return Math.max(0, Math.floor(ms / 86400000));
};

const weekKey = (iso: string): string => {
  const d = new Date(iso);
  const oneJan = new Date(d.getFullYear(), 0, 1);
  const weekNum = Math.ceil(((d.getTime() - oneJan.getTime()) / 86400000 + oneJan.getDay() + 1) / 7);
  return `${d.getFullYear()}-W${String(weekNum).padStart(2, '0')}`;
};

const weekLabel = (key: string): string => {
  const [year, wPart] = key.split('-W');
  return `Week ${parseInt(wPart, 10)}, ${year}`;
};

// ---------------------------------------------------------------------------
// Skeleton Components
// ---------------------------------------------------------------------------

const SkeletonBanner: React.FC = () => (
  <div className="bg-gradient-to-r from-[#1a1f2e] to-[#0f1419] border border-gray-700/50 rounded-xl p-6 animate-pulse border-l-4 border-l-cyan-500/50">
    <div className="h-5 w-96 bg-gray-700 rounded" />
  </div>
);

const SkeletonCard: React.FC<{ wide?: boolean }> = ({ wide }) => (
  <div className={`bg-[#1a1f2e] border border-gray-700/50 rounded-xl p-5 animate-pulse ${wide ? 'col-span-full' : ''}`}>
    <div className="h-3 w-24 bg-gray-700 rounded mb-3" />
    <div className="h-7 w-16 bg-gray-700 rounded" />
  </div>
);

const SkeletonActionCard: React.FC = () => (
  <div className="bg-[#1a1f2e] border border-gray-700/50 rounded-xl p-5 animate-pulse border-l-4 border-l-gray-700">
    <div className="h-4 w-48 bg-gray-700 rounded mb-3" />
    <div className="h-3 w-32 bg-gray-700 rounded mb-2" />
    <div className="h-3 w-64 bg-gray-700 rounded" />
  </div>
);

const SkeletonTimeline: React.FC = () => (
  <div className="bg-[#1a1f2e] border border-gray-700/50 rounded-xl p-6 animate-pulse space-y-6">
    {[1, 2, 3].map((i) => (
      <div key={i} className="flex gap-4 items-start">
        <div className="w-3 h-3 rounded-full bg-gray-700 mt-1.5" />
        <div className="flex-1 space-y-2">
          <div className="h-3 w-48 bg-gray-700 rounded" />
          <div className="h-3 w-32 bg-gray-700 rounded" />
        </div>
      </div>
    ))}
  </div>
);

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const DarkTooltip: React.FC<{ active?: boolean; payload?: Array<{ value: number; payload: { name: string } }> }> = ({
  active,
  payload,
}) => {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  return (
    <div className="bg-[#1a1f2e] border border-gray-700/50 rounded-lg px-3 py-2 text-sm shadow-xl">
      <p className="text-white font-medium">{item.payload.name}</p>
      <p className="text-gray-400">{item.value} signal{item.value !== 1 ? 's' : ''}</p>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Right-panel mini stat card (compact version of MetricCard)
// ---------------------------------------------------------------------------

interface MiniStatProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  accentClass?: string;
  sub?: string;
  subPositive?: boolean;
}

const MiniStat: React.FC<MiniStatProps> = ({ icon, label, value, accentClass = 'text-cyan-400', sub, subPositive }) => (
  <div className="bg-[#1a1f2e] border border-gray-700/50 rounded-lg p-3.5">
    <div className="flex items-center gap-2 mb-1.5">
      <div className={`p-1.5 rounded-md bg-gray-800/80 ${accentClass}`}>{icon}</div>
      <span className="text-gray-500 text-[10px] uppercase tracking-wider font-medium leading-tight">{label}</span>
    </div>
    <p className={`text-lg font-bold ${accentClass}`}>{value}</p>
    {sub && (
      <p className={`text-[10px] mt-0.5 ${subPositive ? 'text-green-400' : 'text-gray-500'}`}>{sub}</p>
    )}
  </div>
);

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const SignalTimelineView: React.FC = () => {
  const { session } = useSession();

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [signals, setSignals] = useState<SignalNode[]>([]);
  const [edges, setEdges] = useState<Record<string, SignalEdge[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredSignal, setHoveredSignal] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);

  // ---- Data Fetch ----
  useEffect(() => {
    let cancelled = false;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      const customerId = getCustomerIdentifier(session);
      const headers: Record<string, string> = { 'X-Customer-ID': customerId };

      try {
        const acctRes = await apiCall('/api/accounts', { headers });
        if (!acctRes.ok) throw new Error(`Accounts API returned ${acctRes.status}`);
        const acctData = await acctRes.json();
        const acctList: Account[] = Array.isArray(acctData) ? acctData : acctData.accounts ?? [];
        if (cancelled) return;
        setAccounts(acctList);

        const signalPromises = acctList.map(async (acct) => {
          try {
            const res = await apiCall(
              `/api/context-graph/nodes?account_id=${acct.id}&node_type=SIGNAL`,
              { headers },
            );
            if (!res.ok) return [];
            const data = await res.json();
            const nodes: SignalNode[] = Array.isArray(data) ? data : data.nodes ?? [];
            return nodes.map((n) => ({ ...n, account_id: acct.id, _account_name: acct.name }));
          } catch {
            return [];
          }
        });

        const allSignalArrays = await Promise.all(signalPromises);
        if (cancelled) return;
        const allSignals = allSignalArrays.flat();
        setSignals(allSignals);

        const edgeMap: Record<string, SignalEdge[]> = {};
        const batchSize = 10;
        for (let i = 0; i < allSignals.length; i += batchSize) {
          const batch = allSignals.slice(i, i + batchSize);
          const edgeResults = await Promise.all(
            batch.map(async (sig) => {
              try {
                const res = await apiCall(`/api/context-graph/edges/${sig.id}`, { headers });
                if (!res.ok) return { id: sig.id, edges: [] as SignalEdge[] };
                const data = await res.json();
                const e: SignalEdge[] = Array.isArray(data) ? data : data.edges ?? [];
                return { id: sig.id, edges: e };
              } catch {
                return { id: sig.id, edges: [] as SignalEdge[] };
              }
            }),
          );
          if (cancelled) return;
          edgeResults.forEach(({ id, edges: e }) => {
            edgeMap[id] = e;
          });
        }
        setEdges(edgeMap);
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load signal data');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchData();
    return () => { cancelled = true; };
  }, [session]);

  // ---- Derived Data ----

  const activeSignals = useMemo(
    () => signals.filter((s) => s.severity !== 'resolved'),
    [signals],
  );

  const revenueAtRisk = useMemo(
    () => activeSignals.reduce((sum, s) => sum + (s.revenue_impact ?? 0), 0),
    [activeSignals],
  );

  const affectedAccountIds = useMemo(() => {
    const ids = new Set(activeSignals.map((s) => s.account_id).filter(Boolean));
    return ids.size;
  }, [activeSignals]);

  const avgResolutionDays = useMemo(() => {
    const resolved = signals.filter((s) => s.resolved_at && s.created_at);
    if (!resolved.length) return 0;
    const totalMs = resolved.reduce((sum, s) => {
      return sum + (new Date(s.resolved_at!).getTime() - new Date(s.created_at!).getTime());
    }, 0);
    return Math.round(totalMs / resolved.length / 86400000);
  }, [signals]);

  const signalToActionRatio = useMemo(() => {
    if (signals.length === 0) return 0;
    const withPlaybook = signals.filter((s) => {
      const sigEdges = edges[s.id] ?? [];
      return sigEdges.some((e) => e.edge_type === 'triggered_playbook' || e.edge_type === 'triggers');
    });
    return Math.round((withPlaybook.length / signals.length) * 100);
  }, [signals, edges]);

  // Top 3 priority signals for action cards
  const prioritySignals = useMemo(() => {
    const severityOrder: Record<string, number> = { critical: 0, warning: 1, info: 2, resolved: 3 };
    return [...activeSignals]
      .sort((a, b) => {
        const sevDiff = (severityOrder[a.severity ?? 'info'] ?? 2) - (severityOrder[b.severity ?? 'info'] ?? 2);
        if (sevDiff !== 0) return sevDiff;
        return (b.revenue_impact ?? 0) - (a.revenue_impact ?? 0);
      })
      .slice(0, 3);
  }, [activeSignals]);

  // Filtered signals for timeline (respects severity filter)
  const filteredSignals = useMemo(() => {
    if (!severityFilter) return signals;
    return signals.filter((s) => s.severity === severityFilter);
  }, [signals, severityFilter]);

  // Timeline grouped by week
  const timelineGroups = useMemo(() => {
    const sorted = [...filteredSignals]
      .filter((s) => s.created_at)
      .sort((a, b) => new Date(b.created_at!).getTime() - new Date(a.created_at!).getTime());

    const groups: Record<string, SignalNode[]> = {};
    sorted.forEach((s) => {
      const key = weekKey(s.created_at!);
      if (!groups[key]) groups[key] = [];
      groups[key].push(s);
    });
    return Object.entries(groups).sort(([a], [b]) => b.localeCompare(a));
  }, [filteredSignals]);

  // Signal type distribution
  const signalsByType = useMemo(() => {
    const counts: Record<string, number> = {};
    signals.forEach((s) => {
      const type = s.subtype ?? 'unknown';
      counts[type] = (counts[type] ?? 0) + 1;
    });
    return Object.entries(counts)
      .map(([name, count]) => ({ name: name.replace(/_/g, ' '), count }))
      .sort((a, b) => b.count - a.count);
  }, [signals]);

  // Account vulnerability map
  const accountVulnerability = useMemo(() => {
    const acctSignals: Record<number, { name: string; total: number; critical: number; warning: number; info: number; revenue: number; types: Set<string> }> = {};
    signals.forEach((s) => {
      const aid = s.account_id ?? 0;
      if (!acctSignals[aid]) {
        const acct = accounts.find((a) => a.id === aid);
        acctSignals[aid] = { name: acct?.name ?? `Account ${aid}`, total: 0, critical: 0, warning: 0, info: 0, revenue: 0, types: new Set() };
      }
      const entry = acctSignals[aid];
      if (s.severity !== 'resolved') {
        entry.total++;
        if (s.severity === 'critical') entry.critical++;
        else if (s.severity === 'warning') entry.warning++;
        else entry.info++;
        entry.revenue += s.revenue_impact ?? 0;
      }
      if (s.subtype) entry.types.add(s.subtype);
    });
    return Object.entries(acctSignals)
      .map(([id, data]) => ({ accountId: Number(id), ...data, typeCount: data.types.size }))
      .sort((a, b) => b.total - a.total);
  }, [signals, accounts]);

  const hasPlaybookAction = (signalId: string): boolean => {
    const sigEdges = edges[signalId] ?? [];
    return sigEdges.some((e) => e.edge_type === 'triggered_playbook' || e.edge_type === 'triggers');
  };

  const barColors = ['#ef4444', '#eab308', '#22d3ee', '#22c55e', '#a855f7', '#f97316', '#6366f1', '#ec4899'];

  // Severity counts for quick-filter badges
  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = { critical: 0, warning: 0, info: 0, resolved: 0 };
    signals.forEach((s) => {
      const sev = s.severity ?? 'info';
      counts[sev] = (counts[sev] ?? 0) + 1;
    });
    return counts;
  }, [signals]);

  // ---- Render: Loading ----
  if (loading) {
    return (
      <div className="flex h-full">
        <div className="flex-1 overflow-y-auto">
          <div className="p-6 max-w-[1200px] space-y-6">
            <SkeletonBanner />
            <div className="space-y-4">
              {[1, 2, 3].map((i) => <SkeletonActionCard key={i} />)}
            </div>
            <SkeletonTimeline />
          </div>
        </div>
        <div className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 space-y-4">
          {[1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)}
        </div>
      </div>
    );
  }

  // ---- Render: Error ----
  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center">
          <AlertTriangle className="w-12 h-12 text-yellow-400 mb-4" />
          <p className="text-white text-lg font-semibold mb-2">Unable to load signals</p>
          <p className="text-gray-400 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  // ---- Render: Empty ----
  if (signals.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center">
          <Shield className="w-16 h-16 text-green-400 mb-4" />
          <p className="text-white text-xl font-semibold mb-2">No signals detected</p>
          <p className="text-gray-400">Your accounts are healthy. Signal intelligence is actively monitoring.</p>
        </div>
      </div>
    );
  }

  // ---- Render: Main (2-panel layout) ----
  return (
    <div className="flex h-full">

      {/* ================================================================
          LEFT: MAIN CONTENT
          ================================================================ */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-[1200px] space-y-8">

          {/* SECTION 1: MISSION BANNER */}
          <div className="bg-gradient-to-r from-[#1a1f2e] to-[#0f1419] border border-gray-700/50 rounded-xl p-5 border-l-4 border-l-cyan-500">
            <div className="flex items-center gap-4">
              <div className="p-2.5 rounded-lg bg-cyan-500/10">
                <Radio className="w-6 h-6 text-cyan-400" />
              </div>
              <div className="flex-1 min-w-0">
                <h1 className="text-xl font-bold text-white">
                  Signal Intelligence
                  <span className="text-gray-400 font-normal text-base ml-3">
                    {activeSignals.length} active signal{activeSignals.length !== 1 ? 's' : ''} affecting{' '}
                    <span className="text-yellow-400 font-semibold">{formatCurrency(revenueAtRisk)}</span> revenue across{' '}
                    <span className="text-cyan-400 font-semibold">{affectedAccountIds}</span> account{affectedAccountIds !== 1 ? 's' : ''}
                  </span>
                </h1>
              </div>
            </div>
          </div>

          {/* SECTION 2: WHAT NEEDS ATTENTION NOW (Priority Action Cards) */}
          {prioritySignals.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Target className="w-4 h-4 text-red-400" />
                What Needs Attention Now
              </h2>
              <div className="space-y-3">
                {prioritySignals.map((signal) => {
                  const severity = signal.severity ?? 'info';
                  const borderClass = SEVERITY_BORDER[severity] ?? 'border-l-cyan-500';
                  const days = signal.created_at ? daysSince(signal.created_at) : 0;
                  const action = getRecommendedAction(signal.subtype);
                  const hasAction = hasPlaybookAction(signal.id);

                  return (
                    <div
                      key={signal.id}
                      className={`bg-[#1a1f2e] border border-gray-700/50 rounded-xl p-5 border-l-4 ${borderClass} hover:border-gray-600 transition-colors`}
                    >
                      <div className="flex items-start gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-3 flex-wrap mb-2">
                            <span className="text-white font-semibold text-sm">{signal.label}</span>
                            <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold uppercase tracking-wider ${SEVERITY_BG[severity]}`}>
                              {severity}
                            </span>
                            {hasAction && (
                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30 font-semibold uppercase tracking-wider">
                                Playbook Active
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
                            {signal._account_name && (
                              <span className="flex items-center gap-1">
                                <Users className="w-3 h-3" />
                                {signal._account_name}
                              </span>
                            )}
                            {signal.revenue_impact != null && signal.revenue_impact > 0 && (
                              <span className="text-yellow-400 font-semibold">
                                {formatCurrency(signal.revenue_impact)} at risk
                              </span>
                            )}
                            {days > 0 && (
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {days}d since detected
                              </span>
                            )}
                          </div>
                          <div className="flex items-start gap-2 bg-[#0f1419] rounded-lg px-3 py-2">
                            <Play className="w-3.5 h-3.5 text-cyan-400 mt-0.5 flex-shrink-0" />
                            <p className="text-xs text-gray-300">
                              <span className="text-cyan-400 font-medium">Recommended:</span>{' '}
                              {action}
                            </p>
                          </div>
                        </div>
                        <ChevronRight className="w-5 h-5 text-gray-600 flex-shrink-0 mt-1" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* SECTION 3: SIGNAL TIMELINE (Chronological) */}
          <div className="bg-[#1a1f2e] border border-gray-700/50 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <Activity className="w-5 h-5 text-cyan-400" />
              Signal Timeline
              {severityFilter && (
                <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold uppercase ${SEVERITY_BG[severityFilter]}`}>
                  {severityFilter}
                </span>
              )}
              {severityFilter && (
                <button
                  onClick={() => setSeverityFilter(null)}
                  className="text-xs text-gray-500 hover:text-gray-300 ml-1"
                >
                  clear
                </button>
              )}
            </h2>

            <div className="space-y-8 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
              {timelineGroups.length === 0 && (
                <p className="text-gray-500 text-sm text-center py-8">No signals match the current filter.</p>
              )}
              {timelineGroups.map(([week, weekSignals]) => (
                <div key={week}>
                  <div className="flex items-center gap-3 mb-4">
                    <p className="text-gray-400 text-xs uppercase tracking-wider font-semibold">{weekLabel(week)}</p>
                    <div className="flex-1 h-px bg-gray-700/50" />
                    <span className="text-gray-600 text-xs">{weekSignals.length} signal{weekSignals.length !== 1 ? 's' : ''}</span>
                  </div>
                  <div className="relative border-l-2 border-gray-700/50 ml-3 space-y-3">
                    {weekSignals.map((signal) => {
                      const severity = signal.severity ?? 'info';
                      const dotColor = SEVERITY_COLORS[severity] ?? SEVERITY_COLORS.info;
                      const isHovered = hoveredSignal === signal.id;
                      const hasAction = hasPlaybookAction(signal.id);

                      return (
                        <div
                          key={signal.id}
                          className="relative pl-7"
                          onMouseEnter={() => setHoveredSignal(signal.id)}
                          onMouseLeave={() => setHoveredSignal(null)}
                        >
                          {/* Dot */}
                          <div
                            className="absolute left-[-5px] top-3 w-2.5 h-2.5 rounded-full border-2 border-[#1a1f2e]"
                            style={{ backgroundColor: dotColor }}
                          />

                          <div
                            className={`bg-[#151a27] rounded-lg p-4 border transition-colors ${
                              isHovered ? 'border-gray-600' : 'border-gray-700/30'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold uppercase ${SEVERITY_BG[severity]}`}>
                                    {severity}
                                  </span>
                                  <span className="text-white font-medium text-sm truncate">{signal.label}</span>
                                  {hasAction && (
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400 flex items-center gap-1">
                                      <CheckCircle2 className="w-2.5 h-2.5" />
                                      Action taken
                                    </span>
                                  )}
                                </div>
                                <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-500">
                                  {signal.created_at && <span>{formatDate(signal.created_at)}</span>}
                                  {signal._account_name && (
                                    <span className="flex items-center gap-1">
                                      <Users className="w-3 h-3" />
                                      {signal._account_name}
                                    </span>
                                  )}
                                  {signal.subtype && (
                                    <span className="text-gray-600">{signal.subtype.replace(/_/g, ' ')}</span>
                                  )}
                                </div>
                              </div>
                              {signal.revenue_impact != null && signal.revenue_impact > 0 && (
                                <span className="text-yellow-400 text-sm font-semibold whitespace-nowrap">
                                  {formatCurrency(signal.revenue_impact)}
                                </span>
                              )}
                            </div>

                            {/* Hover details */}
                            {isHovered && (
                              <div className="mt-3 pt-3 border-t border-gray-700/50 text-xs text-gray-400 space-y-1">
                                {signal.status && <p>Status: <span className="text-gray-300">{signal.status}</span></p>}
                                {edges[signal.id]?.length > 0 && (
                                  <p>
                                    Connected nodes:{' '}
                                    <span className="text-gray-300">{edges[signal.id].length} connection{edges[signal.id].length !== 1 ? 's' : ''}</span>
                                  </p>
                                )}
                                {signal.resolved_at && (
                                  <p>Resolved: <span className="text-green-400">{formatDate(signal.resolved_at)}</span></p>
                                )}
                                <p className="text-cyan-400/80">
                                  Recommended: {getRecommendedAction(signal.subtype)}
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* ================================================================
          RIGHT: CONTEXT PANEL
          ================================================================ */}
      <div className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 overflow-y-auto flex flex-col gap-5">

        {/* Signal Health Stats (4 mini cards stacked) */}
        <div>
          <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-3">Signal Health</h3>
          <div className="grid grid-cols-2 gap-2">
            <MiniStat
              icon={<Activity className="w-3.5 h-3.5" />}
              label="Active"
              value={activeSignals.length}
              accentClass="text-cyan-400"
              sub={signals.length > activeSignals.length ? `${signals.length - activeSignals.length} resolved` : undefined}
              subPositive={true}
            />
            <MiniStat
              icon={<TrendingDown className="w-3.5 h-3.5" />}
              label="At Risk"
              value={formatCurrency(revenueAtRisk)}
              accentClass="text-red-400"
            />
            <MiniStat
              icon={<Clock className="w-3.5 h-3.5" />}
              label="Avg Resolution"
              value={avgResolutionDays > 0 ? `${avgResolutionDays}d` : 'N/A'}
              accentClass="text-yellow-400"
              sub={avgResolutionDays > 0 ? (avgResolutionDays <= 14 ? 'Within target' : 'Above target') : undefined}
              subPositive={avgResolutionDays > 0 && avgResolutionDays <= 14}
            />
            <MiniStat
              icon={<Target className="w-3.5 h-3.5" />}
              label="Action Ratio"
              value={`${signalToActionRatio}%`}
              accentClass={signalToActionRatio >= 60 ? 'text-green-400' : signalToActionRatio >= 30 ? 'text-yellow-400' : 'text-red-400'}
              sub={signalToActionRatio >= 60 ? 'Strong coverage' : 'Needs improvement'}
              subPositive={signalToActionRatio >= 60}
            />
          </div>
        </div>

        {/* Account Vulnerability (sorted by signal density) */}
        <div>
          <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <Shield className="w-3 h-3 text-gray-500" />
            Account Vulnerability
          </h3>
          {accountVulnerability.length > 0 ? (
            <div className="space-y-2.5 max-h-[280px] overflow-y-auto pr-1 custom-scrollbar">
              {accountVulnerability.map((acct) => {
                const maxTotal = accountVulnerability[0]?.total ?? 1;
                const barWidth = Math.max(8, (acct.total / maxTotal) * 100);

                return (
                  <div key={acct.accountId}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-300 font-medium truncate max-w-[140px]">{acct.name}</span>
                      <div className="flex items-center gap-2 text-[10px]">
                        {acct.revenue > 0 && (
                          <span className="text-yellow-400 font-medium">{formatCurrency(acct.revenue)}</span>
                        )}
                        <span className="text-gray-600">{acct.total}</span>
                      </div>
                    </div>
                    {/* Stacked severity bar */}
                    <div className="h-4 bg-gray-800/50 rounded-full overflow-hidden flex">
                      {acct.critical > 0 && (
                        <div
                          className="h-full bg-red-500/70 flex items-center justify-center"
                          style={{ width: `${(acct.critical / acct.total) * barWidth}%` }}
                          title={`${acct.critical} critical`}
                        >
                          <span className="text-[8px] text-white font-bold">{acct.critical}</span>
                        </div>
                      )}
                      {acct.warning > 0 && (
                        <div
                          className="h-full bg-yellow-500/70 flex items-center justify-center"
                          style={{ width: `${(acct.warning / acct.total) * barWidth}%` }}
                          title={`${acct.warning} warning`}
                        >
                          <span className="text-[8px] text-gray-900 font-bold">{acct.warning}</span>
                        </div>
                      )}
                      {acct.info > 0 && (
                        <div
                          className="h-full bg-cyan-500/70 flex items-center justify-center"
                          style={{ width: `${(acct.info / acct.total) * barWidth}%` }}
                          title={`${acct.info} info`}
                        >
                          <span className="text-[8px] text-white font-bold">{acct.info}</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-gray-600 text-xs">No account data</p>
          )}

          {/* Legend */}
          {accountVulnerability.length > 0 && (
            <div className="flex items-center gap-3 mt-3 pt-2 border-t border-gray-700/30">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-red-500/70" />
                <span className="text-[9px] text-gray-600">Critical</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-yellow-500/70" />
                <span className="text-[9px] text-gray-600">Warning</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-cyan-500/70" />
                <span className="text-[9px] text-gray-600">Info</span>
              </div>
            </div>
          )}
        </div>

        {/* Signal Distribution (horizontal bars) */}
        <div>
          <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <Zap className="w-3 h-3 text-gray-500" />
            Signal Distribution
          </h3>
          {signalsByType.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(140, signalsByType.length * 28)}>
              <BarChart data={signalsByType} layout="vertical" margin={{ left: 4, right: 8, top: 2, bottom: 2 }}>
                <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis
                  dataKey="name"
                  type="category"
                  tick={{ fill: '#9ca3af', fontSize: 9 }}
                  axisLine={false}
                  tickLine={false}
                  width={90}
                />
                <Tooltip content={<DarkTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                <Bar dataKey="count" radius={[0, 3, 3, 0]} barSize={16}>
                  {signalsByType.map((_, idx) => (
                    <Cell key={idx} fill={barColors[idx % barColors.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-600 text-xs">No type data</p>
          )}
        </div>

        {/* Quick Filters (severity buttons) */}
        <div>
          <h3 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-3">Quick Filters</h3>
          <div className="flex flex-wrap gap-1.5">
            {(['critical', 'warning', 'info', 'resolved'] as const).map((sev) => {
              const isActive = severityFilter === sev;
              const count = severityCounts[sev] ?? 0;
              return (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(isActive ? null : sev)}
                  className={`text-[10px] px-2.5 py-1 rounded-full border font-semibold uppercase tracking-wider transition-colors ${
                    isActive
                      ? SEVERITY_BG[sev]
                      : 'bg-gray-800/50 text-gray-500 border-gray-700/50 hover:border-gray-600'
                  }`}
                >
                  {sev} ({count})
                </button>
              );
            })}
          </div>
        </div>

      </div>
    </div>
  );
};

export default SignalTimelineView;
