import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  GitBranch, Users, Target, AlertTriangle, Activity,
  ChevronDown, Zap, Shield, Eye, Layers,
  TrendingUp, DollarSign, Brain, Lightbulb, Play,
} from 'lucide-react';
import { apiCall, getCustomerIdentifier } from '../../../utils/api';
import { useSession } from '../../../contexts/SessionContext';
import { fetchGraphNodes, fetchAccountEdges, fetchGraphSummary } from '../../../utils/contextGraphApi';
import type { ContextNodeDTO, ContextEdgeDTO } from '../../../types/contextGraph';

// ─── Types ──────────────────────────────────────────────────────────────────

interface Account {
  account_id: number;
  account_name: string;
  revenue?: number;
  status?: string;
}

interface GraphSummary {
  total_nodes: number;
  total_edges: number;
  nodes_by_type: Record<string, number>;
  revenue: {
    at_risk: number;
    protected: number;
    expansion: number;
    lost: number;
    net_impact: number;
    node_count: number;
  };
}

interface RevenueBreakdown {
  at_risk: number;
  protected: number;
  expansion: number;
  lost: number;
  net_impact: number;
  node_count: number;
}

interface StoryArcPhase {
  phase_id: number;
  name: string;
  duration_weeks: number;
  health_range: { start: number; end: number };
  description: string;
  revenue_impact_type: string;
  plot_points: any[];
}

interface StoryArcCast {
  role: string;
  title: string;
  influence_score: number;
  sentiment_arc: number[];
  engagement_frequency: string;
  appears_in_phase: number[];
}

interface StoryArc {
  arc_id: string;
  arc_name: string;
  description: string;
  duration_weeks: number;
  num_phases: number;
  revenue_narrative: {
    arr_start: number;
    arr_end: number;
    arr_at_risk_peak: number;
    cost_of_inaction: number;
    roi_of_intervention: number;
    intervention_cost: number;
    net_revenue_saved: number;
    time_horizon_weeks: number;
  };
  cast: StoryArcCast[];
  phases: StoryArcPhase[];
  causal_chains: any[];
  decisions: any[];
  outcomes: any[];
}

interface PortfolioSummary {
  total_nodes: number;
  total_edges: number;
  nodes_by_type: Record<string, number>;
  total_at_risk: number;
  total_protected: number;
  total_expansion: number;
  total_lost: number;
  total_net_impact: number;
  accounts_loaded: number;
}

// ─── SVG Layout Types ───────────────────────────────────────────────────────

interface LayoutNode {
  id: string;
  nodeId: number;
  type: string;
  styleKey: string;
  subtype: string | null;
  label: string;
  sub: string;
  x: number;
  y: number;
  revenueImpact: number | null;
  revenueType: string | null;
  occurredAt: string | null;
  raw: ContextNodeDTO;
}

interface LayoutEdge {
  from: string;
  to: string;
  label: string;
  edgeId: number;
}

// ─── Constants ──────────────────────────────────────────────────────────────

const NW = 120;
const NH = 42;
const COL_GAP = 40;
const ROW_GAP = 28;
const HEADER_H = 40;
const PADDING = 20;

const SVG_NODE_STYLES: Record<string, { bg: string; border: string; text: string }> = {
  SIGNAL:           { bg: '#f59e0b', border: '#d97706', text: '#000' },  // amber — user-uploaded
  SIGNAL_SYSTEM:    { bg: '#22d3ee', border: '#06b6d4', text: '#000' },  // cyan — system-generated
  DECISION:         { bg: '#eab308', border: '#ca8a04', text: '#000' },
  OUTCOME:          { bg: '#22c55e', border: '#16a34a', text: '#000' },
  STAKEHOLDER:      { bg: '#a855f7', border: '#7c3aed', text: '#fff' },
  EXTERNAL_CONTEXT: { bg: '#6b7280', border: '#4b5563', text: '#fff' },
};

/** Detect system-generated signal nodes (Wizard A / arc classifier) */
function isSystemSignal(n: ContextNodeDTO): boolean {
  if (n.node_type !== 'SIGNAL') return false;
  if ((n as any).source === 'system') return true;
  if (n.node_subtype === 'arc_detection') return true;
  if (n.properties?.triggered_by) return true;
  return false;
}

function getStyleKey(n: ContextNodeDTO): string {
  if (isSystemSignal(n)) return 'SIGNAL_SYSTEM';
  return n.node_type || 'SIGNAL';
}

const TYPE_PRIORITY: Record<string, number> = {
  STAKEHOLDER: 0,
  SIGNAL: 1,
  DECISION: 2,
  OUTCOME: 3,
  EXTERNAL_CONTEXT: 4,
};

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatCompact(value: number): string {
  if (value === 0) return '$0';
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (abs >= 1_000_000_000) return `${sign}$${(abs / 1_000_000_000).toFixed(1)}B`;
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(0)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

const NODE_TYPE_COLORS: Record<string, { bg: string; text: string; border: string; dot: string; hex: string }> = {
  SIGNAL:           { bg: 'bg-amber-500/15',   text: 'text-amber-400',   border: 'border-amber-500/40',   dot: 'bg-amber-400',   hex: '#f59e0b' },
  SIGNAL_SYSTEM:    { bg: 'bg-cyan-500/15',    text: 'text-cyan-400',    border: 'border-cyan-500/40',    dot: 'bg-cyan-400',    hex: '#22d3ee' },
  STAKEHOLDER:      { bg: 'bg-purple-500/15',  text: 'text-purple-400',  border: 'border-purple-500/40',  dot: 'bg-purple-400',  hex: '#a855f7' },
  DECISION:         { bg: 'bg-yellow-500/15',  text: 'text-yellow-400',  border: 'border-yellow-500/40',  dot: 'bg-yellow-400',  hex: '#eab308' },
  OUTCOME:          { bg: 'bg-green-500/15',   text: 'text-green-400',   border: 'border-green-500/40',   dot: 'bg-green-400',   hex: '#22c55e' },
  EXTERNAL_CONTEXT: { bg: 'bg-gray-500/15',    text: 'text-gray-400',    border: 'border-gray-500/40',    dot: 'bg-gray-400',    hex: '#6b7280' },
};

function getNodeColor(type: string) {
  return NODE_TYPE_COLORS[type] || NODE_TYPE_COLORS.EXTERNAL_CONTEXT;
}

// ─── SVG Layout Algorithm (ported from ContextGraphExplorer) ────────────────

function layoutNodes(nodes: ContextNodeDTO[]): LayoutNode[] {
  if (nodes.length === 0) return [];

  const byType: Record<string, ContextNodeDTO[]> = {};
  for (const n of nodes) {
    const t = n.node_type || 'SIGNAL';
    if (!byType[t]) byType[t] = [];
    byType[t].push(n);
  }

  const sortedTypes = Object.keys(byType).sort(
    (a, b) => (TYPE_PRIORITY[a] ?? 9) - (TYPE_PRIORITY[b] ?? 9)
  );

  for (const t of sortedTypes) {
    byType[t].sort((a, b) => {
      const da = a.occurred_at ? new Date(a.occurred_at).getTime() : 0;
      const db = b.occurred_at ? new Date(b.occurred_at).getTime() : 0;
      return da - db;
    });
  }

  const result: LayoutNode[] = [];

  // Stakeholders: horizontal row at top
  const stakeholders = byType['STAKEHOLDER'] || [];
  const stakeholderY = HEADER_H + PADDING;
  const stakeholderStartX = PADDING;
  stakeholders.forEach((n, i) => {
    result.push(makeLayoutNode(n, stakeholderStartX + i * (NW + COL_GAP), stakeholderY));
  });

  // Other types: vertical lanes
  const nonStakeholderTypes = sortedTypes.filter(t => t !== 'STAKEHOLDER');
  const laneStartY = stakeholders.length > 0
    ? stakeholderY + NH + ROW_GAP + 20
    : HEADER_H + PADDING;

  nonStakeholderTypes.forEach((type, colIdx) => {
    const laneX = PADDING + colIdx * (NW + COL_GAP);
    const nodesInLane = byType[type] || [];
    nodesInLane.forEach((n, rowIdx) => {
      const y = laneStartY + rowIdx * (NH + ROW_GAP);
      result.push(makeLayoutNode(n, laneX, y));
    });
  });

  return result;
}

function makeLayoutNode(n: ContextNodeDTO, x: number, y: number): LayoutNode {
  const dateStr = n.occurred_at
    ? new Date(n.occurred_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : '';
  const titleTrunc = (n.title || '').length > 20
    ? (n.title || '').substring(0, 19) + '\u2026'
    : (n.title || '');

  const isStakeholder = n.node_type === 'STAKEHOLDER';
  const label = isStakeholder ? titleTrunc : dateStr;
  const sub = isStakeholder
    ? (n.node_subtype || n.properties?.department || '')
    : titleTrunc;

  let revSub = sub;
  if (n.node_type === 'OUTCOME' && n.revenue_impact) {
    revSub = `${formatCompact(Math.abs(n.revenue_impact))} ${n.revenue_impact_type || ''}\n${sub}`;
  }

  return {
    id: `n${n.node_id}`,
    nodeId: n.node_id,
    type: n.node_type,
    styleKey: getStyleKey(n),
    subtype: n.node_subtype,
    label,
    sub: revSub,
    x,
    y,
    revenueImpact: n.revenue_impact,
    revenueType: n.revenue_impact_type,
    occurredAt: n.occurred_at,
    raw: n,
  };
}

function mapEdges(edges: ContextEdgeDTO[], nodeIds: Set<number>): LayoutEdge[] {
  return edges
    .filter(e => nodeIds.has(e.from_node_id) && nodeIds.has(e.to_node_id))
    .map(e => ({
      from: `n${e.from_node_id}`,
      to: `n${e.to_node_id}`,
      label: e.edge_type || '',
      edgeId: e.edge_id,
    }));
}

function getCenter(node: LayoutNode) {
  return { cx: node.x + NW / 2, cy: node.y + NH / 2 };
}

// ─── SVG Sub-Components ─────────────────────────────────────────────────────

const NodeShape: React.FC<{
  node: LayoutNode;
  dimmed: boolean;
  onClick: (node: LayoutNode) => void;
}> = ({ node, dimmed, onClick }) => {
  const s = SVG_NODE_STYLES[node.styleKey] || SVG_NODE_STYLES.SIGNAL;
  const isSysSignal = node.styleKey === 'SIGNAL_SYSTEM';
  const { x, y } = node;
  const cx = x + NW / 2;
  const cy = y + NH / 2;

  return (
    <g
      onClick={() => onClick(node)}
      style={{ cursor: 'pointer', opacity: dimmed ? 0.15 : 1, transition: 'opacity 0.2s' }}
    >
      {node.type === 'STAKEHOLDER' ? (
        <circle cx={cx} cy={cy} r={24} fill={s.bg} stroke={s.border} strokeWidth={2} />
      ) : node.type === 'DECISION' ? (
        <polygon
          points={`${cx},${y} ${x + NW},${cy} ${cx},${y + NH} ${x},${cy}`}
          fill={s.bg} stroke={s.border} strokeWidth={2}
        />
      ) : (
        <rect
          x={x} y={y} width={NW} height={NH} rx={7}
          fill={s.bg} stroke={s.border}
          strokeWidth={node.type === 'OUTCOME' ? 3 : 2}
        />
      )}
      <text
        x={cx} y={cy - 8} textAnchor="middle"
        fill={s.text} fontSize={9} fontWeight={800}
        fontFamily="'Courier New', monospace"
      >
        {node.label}
      </text>
      <foreignObject x={x + 3} y={cy + 1} width={NW - 6} height={24}>
        <div
          style={{
            fontSize: 8, color: s.text, textAlign: 'center',
            lineHeight: 1.3, fontFamily: 'monospace',
            whiteSpace: 'pre-wrap', opacity: 0.9,
            overflow: 'hidden',
          }}
        >
          {node.sub}
        </div>
      </foreignObject>
    </g>
  );
};

const EdgeLine: React.FC<{
  edge: LayoutEdge;
  nodes: LayoutNode[];
  dimmed: boolean;
}> = ({ edge, nodes, dimmed }) => {
  const fn = nodes.find(n => n.id === edge.from);
  const tn = nodes.find(n => n.id === edge.to);
  if (!fn || !tn) return null;

  const { cx: x1, cy: y1 } = getCenter(fn);
  const { cx: x2, cy: y2 } = getCenter(tn);
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const markerId = `arr-${edge.from}-${edge.to}`;
  const color = dimmed ? '#333' : '#555';
  const dash =
    edge.label === 'INVOLVES' ? '5,4'
    : edge.label === 'INDICATES' ? '3,3'
    : '0';

  return (
    <g style={{ opacity: dimmed ? 0.1 : 1, transition: 'opacity 0.2s' }}>
      <defs>
        <marker id={markerId} markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L7,3 z" fill={color} />
        </marker>
      </defs>
      <line
        x1={x1} y1={y1} x2={x2} y2={y2}
        stroke={color} strokeWidth={1.5}
        strokeDasharray={dash}
        markerEnd={`url(#${markerId})`}
      />
      <text x={mx} y={my - 5} textAnchor="middle" fill={color} fontSize={8} fontFamily="monospace">
        {edge.label}
      </text>
    </g>
  );
};

// ─── SVG Legend ──────────────────────────────────────────────────────────────

const GraphLegend: React.FC = () => {
  const items: { type: string; label: string; shape: string }[] = [
    { type: 'STAKEHOLDER', label: 'Stakeholder', shape: 'circle' },
    { type: 'SIGNAL', label: 'Signal', shape: 'rect' },
    { type: 'SIGNAL_SYSTEM', label: 'System Signal', shape: 'rect' },
    { type: 'DECISION', label: 'Decision', shape: 'diamond' },
    { type: 'OUTCOME', label: 'Outcome', shape: 'rect' },
    { type: 'EXTERNAL_CONTEXT', label: 'External', shape: 'rect' },
  ];

  return (
    <div className="flex items-center gap-4 px-4 py-2 mb-2">
      {items.map(item => {
        const s = SVG_NODE_STYLES[item.type];
        return (
          <div key={item.type} className="flex items-center gap-1.5 text-xs text-gray-400">
            {item.shape === 'circle' ? (
              <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: s.bg }} />
            ) : item.shape === 'diamond' ? (
              <span className="w-3 h-3 flex-shrink-0" style={{
                background: s.bg,
                transform: 'rotate(45deg)',
                borderRadius: 1,
              }} />
            ) : (
              <span className="w-3 h-3 rounded-sm flex-shrink-0" style={{ background: s.bg }} />
            )}
            {item.label}
          </div>
        );
      })}
    </div>
  );
};

// ─── Skeleton Loader ────────────────────────────────────────────────────────

const SkeletonCard: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 animate-pulse ${className}`}>
    <div className="h-4 bg-gray-700/50 rounded w-1/3 mb-3" />
    <div className="h-8 bg-gray-700/50 rounded w-2/3 mb-2" />
    <div className="h-3 bg-gray-700/30 rounded w-1/2" />
  </div>
);

const SkeletonTable: React.FC = () => (
  <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 animate-pulse">
    <div className="h-5 bg-gray-700/50 rounded w-1/4 mb-4" />
    {[...Array(5)].map((_, i) => (
      <div key={i} className="flex gap-4 mb-3">
        <div className="h-4 bg-gray-700/30 rounded w-1/6" />
        <div className="h-4 bg-gray-700/30 rounded w-1/3" />
        <div className="h-4 bg-gray-700/30 rounded w-1/6" />
        <div className="h-4 bg-gray-700/30 rounded w-1/6" />
        <div className="h-4 bg-gray-700/30 rounded w-1/12" />
      </div>
    ))}
  </div>
);

// ─── Main Component ─────────────────────────────────────────────────────────

const ContextGraphView: React.FC = () => {
  const { session } = useSession();
  const customerId = getCustomerIdentifier(session);

  // ── State ──
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);
  const [summary, setSummary] = useState<GraphSummary | null>(null);
  const [graphNodes, setGraphNodes] = useState<ContextNodeDTO[]>([]);
  const [graphEdges, setGraphEdges] = useState<ContextEdgeDTO[]>([]);
  const [revenue, setRevenue] = useState<RevenueBreakdown | null>(null);
  const [storyArc, setStoryArc] = useState<StoryArc | null>(null);

  const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummary | null>(null);

  const [loading, setLoading] = useState(true);
  const [accountLoading, setAccountLoading] = useState(false);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [svgSelected, setSvgSelected] = useState<string | null>(null);

  const [sortField, setSortField] = useState<string>('occurred_at');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [accountDropdownOpen, setAccountDropdownOpen] = useState(false);

  // ── Fetch accounts ──
  useEffect(() => {
    const fetchAccounts = async () => {
      try {
        setLoading(true);
        const resp = await apiCall('/api/accounts');
        const data = await resp.json();
        const accts: Account[] = data.accounts || data || [];
        setAccounts(accts);
        if (accts.length > 0 && !selectedAccountId) {
          setSelectedAccountId(accts[0].account_id);
        }
      } catch (err: any) {
        setError('Failed to load accounts');
        console.error('Account fetch error:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchAccounts();
  }, [customerId]);

  // ── Fetch PORTFOLIO-WIDE summaries (aggregate across all accounts) ──
  useEffect(() => {
    if (accounts.length === 0) return;

    const fetchPortfolioSummaries = async () => {
      setPortfolioLoading(true);
      try {
        const results = await Promise.allSettled(
          accounts.map(acct => fetchGraphSummary(acct.account_id))
        );

        const agg: PortfolioSummary = {
          total_nodes: 0,
          total_edges: 0,
          nodes_by_type: {},
          total_at_risk: 0,
          total_protected: 0,
          total_expansion: 0,
          total_lost: 0,
          total_net_impact: 0,
          accounts_loaded: 0,
        };

        for (const r of results) {
          if (r.status !== 'fulfilled') continue;
          const d = r.value;
          if (d.status !== 'success') continue;
          agg.accounts_loaded += 1;
          agg.total_nodes += d.total_nodes || 0;
          agg.total_edges += d.total_edges || 0;
          if (d.nodes_by_type) {
            for (const [type, count] of Object.entries(d.nodes_by_type)) {
              agg.nodes_by_type[type] = (agg.nodes_by_type[type] || 0) + (count || 0);
            }
          }
          if (d.revenue) {
            agg.total_at_risk += d.revenue.at_risk || 0;
            agg.total_protected += d.revenue.protected || 0;
            agg.total_expansion += d.revenue.expansion || 0;
            agg.total_lost += d.revenue.lost || 0;
            agg.total_net_impact += d.revenue.net_impact || 0;
          }
        }

        setPortfolioSummary(agg);
      } catch (err) {
        console.error('Portfolio summary aggregation error:', err);
      } finally {
        setPortfolioLoading(false);
      }
    };

    fetchPortfolioSummaries();
  }, [accounts]);

  // ── Fetch account-specific data (for main panel) ──
  const fetchAccountData = useCallback(async (accountId: number) => {
    setAccountLoading(true);
    setError(null);
    setSvgSelected(null);

    try {
      const [summaryResp, nodesResp, edgesResp, revenueResp, arcResp] = await Promise.allSettled([
        apiCall(`/api/context-graph/summary?account_id=${accountId}`),
        fetchGraphNodes(accountId, undefined, undefined, 200),
        fetchAccountEdges(accountId, 500),
        apiCall(`/api/context-graph/revenue?account_id=${accountId}`),
        apiCall(`/api/story-arcs/account/${accountId}`),
      ]);

      if (summaryResp.status === 'fulfilled') {
        const d = await (summaryResp.value as any).json();
        if (d.status === 'success') setSummary(d);
      }

      if (nodesResp.status === 'fulfilled') {
        const d = nodesResp.value as any;
        setGraphNodes(d.nodes || []);
      }

      if (edgesResp.status === 'fulfilled') {
        const d = edgesResp.value as any;
        setGraphEdges(d.edges || []);
      }

      if (revenueResp.status === 'fulfilled') {
        const d = await (revenueResp.value as any).json();
        if (d.status === 'success') {
          setRevenue({
            at_risk: d.at_risk || 0,
            protected: d.protected || 0,
            expansion: d.expansion || 0,
            lost: d.lost || 0,
            net_impact: d.net_impact || 0,
            node_count: d.node_count || 0,
          });
        }
      }

      if (arcResp.status === 'fulfilled') {
        const d = await (arcResp.value as any).json();
        if (d.status === 'ok' && d.arc) setStoryArc(d.arc);
        else setStoryArc(null);
      }
    } catch (err: any) {
      setError('Failed to load context graph data');
      console.error('Context graph fetch error:', err);
    } finally {
      setAccountLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedAccountId) {
      fetchAccountData(selectedAccountId);
    }
  }, [selectedAccountId, fetchAccountData]);

  // ── Computed: SVG layout from graphNodes/graphEdges ──
  // Strategy: Balanced selection — guaranteed quota per type so every node type
  // is well-represented and chains are complete (STAKEHOLDER → SIGNAL → DECISION → OUTCOME)
  const svgLayout = useMemo(() => {
    if (!graphNodes.length) return { nodes: [], edges: [], svgW: 600, svgH: 300 };

    // Step 1: Build edge lookup for traversal
    const edgesByNode = new Map<number, number[]>();
    for (const e of graphEdges) {
      if (!edgesByNode.has(e.from_node_id)) edgesByNode.set(e.from_node_id, []);
      if (!edgesByNode.has(e.to_node_id)) edgesByNode.set(e.to_node_id, []);
      edgesByNode.get(e.from_node_id)!.push(e.to_node_id);
      edgesByNode.get(e.to_node_id)!.push(e.from_node_id);
    }

    // Step 2: Group by type
    const byType: Record<string, ContextNodeDTO[]> = {};
    for (const n of graphNodes) {
      if (!byType[n.node_type]) byType[n.node_type] = [];
      byType[n.node_type].push(n);
    }
    // Sort each type group by revenue impact (highest first)
    for (const t of Object.keys(byType)) {
      byType[t].sort((a, b) => Math.abs(b.revenue_impact || 0) - Math.abs(a.revenue_impact || 0));
    }

    // Step 3: Balanced quota — ensure every type is represented
    // ALL outcomes + ALL stakeholders + top N decisions + top N signals
    const allOutcomes = byType['OUTCOME'] || [];
    const allStakeholders = byType['STAKEHOLDER'] || [];
    const allDecisions = byType['DECISION'] || [];
    const allSignals = byType['SIGNAL'] || [];
    const allExternal = byType['EXTERNAL_CONTEXT'] || [];

    // Take all outcomes and stakeholders (these are few)
    const selected: ContextNodeDTO[] = [...allOutcomes, ...allStakeholders];
    const selectedIds = new Set(selected.map(n => n.node_id));

    // Calculate remaining budget for signals & decisions
    const budget = 35; // total node budget
    const remaining = budget - selected.length;
    // Split remaining: 40% signals, 40% decisions, 20% external
    const signalQuota = Math.max(6, Math.floor(remaining * 0.4));
    const decisionQuota = Math.max(4, Math.floor(remaining * 0.4));
    const externalQuota = Math.max(2, Math.floor(remaining * 0.2));

    // Prefer signals/decisions that are CONNECTED to our outcomes
    const connectedToOutcome = new Set<number>();
    for (const o of allOutcomes) {
      for (const nid of (edgesByNode.get(o.node_id) || [])) {
        connectedToOutcome.add(nid);
      }
    }

    // Pick signals: connected-to-outcome first, then by revenue
    const connSignals = allSignals.filter(n => connectedToOutcome.has(n.node_id));
    const otherSignals = allSignals.filter(n => !connectedToOutcome.has(n.node_id));
    const pickedSignals = [...connSignals, ...otherSignals]
      .filter(n => !selectedIds.has(n.node_id))
      .slice(0, signalQuota);
    for (const n of pickedSignals) { selected.push(n); selectedIds.add(n.node_id); }

    // Pick decisions: connected-to-outcome first
    const connDecisions = allDecisions.filter(n => connectedToOutcome.has(n.node_id));
    const otherDecisions = allDecisions.filter(n => !connectedToOutcome.has(n.node_id));
    const pickedDecisions = [...connDecisions, ...otherDecisions]
      .filter(n => !selectedIds.has(n.node_id))
      .slice(0, decisionQuota);
    for (const n of pickedDecisions) { selected.push(n); selectedIds.add(n.node_id); }

    // Pick external context
    const pickedExternal = allExternal
      .filter(n => !selectedIds.has(n.node_id))
      .slice(0, externalQuota);
    for (const n of pickedExternal) { selected.push(n); selectedIds.add(n.node_id); }

    const finalIds = new Set(selected.map(n => n.node_id));
    const nodes = layoutNodes(selected);
    const edges = mapEdges(graphEdges, finalIds);

    let maxX = 600;
    let maxY = 300;
    for (const n of nodes) {
      maxX = Math.max(maxX, n.x + NW + PADDING);
      maxY = Math.max(maxY, n.y + NH + PADDING);
    }
    return { nodes, edges, svgW: maxX, svgH: maxY };
  }, [graphNodes, graphEdges]);

  // ── SVG selection logic ──
  const svgConnectedEdges = svgSelected
    ? svgLayout.edges.filter(e => e.from === svgSelected || e.to === svgSelected)
    : [];
  const svgConnectedIds = new Set(svgConnectedEdges.flatMap(e => [e.from, e.to]));

  const isNodeDimmed = (id: string) => !!svgSelected && !svgConnectedIds.has(id);
  const isEdgeDimmed = (e: LayoutEdge) => !!svgSelected && !svgConnectedEdges.includes(e);

  // ── Computed: revenue "because" explanations ──
  const revenueBecause = useMemo(() => {
    // Risk: count all negative signals + at-risk/lost outcomes
    const riskOutcomes = graphNodes.filter(n => n.revenue_impact_type === 'at_risk' || n.revenue_impact_type === 'lost');
    const riskSignals = graphNodes.filter(n => n.node_type === 'SIGNAL' && n.node_subtype?.match(/champion_loss|budget_cut|escalation|usage_decline|competitor|downgrade|churn|critical_incident/));
    const allRiskNodes = riskOutcomes.length > 0 ? riskOutcomes : riskSignals;

    // Protected: count decisions + protected outcomes
    const protectedOutcomes = graphNodes.filter(n => n.revenue_impact_type === 'protected');
    const decisions = graphNodes.filter(n => n.node_type === 'DECISION');
    const protectedCount = protectedOutcomes.length || decisions.length;

    // Expansion: count positive outcomes + positive signals
    const expansionOutcomes = graphNodes.filter(n => n.revenue_impact_type === 'expansion');
    const growthSignals = graphNodes.filter(n => n.node_type === 'SIGNAL' && n.node_subtype?.match(/expansion|upsell|adoption|growth|renewal_confirmed/));
    const expansionCount = expansionOutcomes.length || growthSignals.length;

    const topRisk = [...riskOutcomes, ...riskSignals].sort((a, b) => Math.abs(b.revenue_impact || 0) - Math.abs(a.revenue_impact || 0))[0];
    const topProtected = [...protectedOutcomes, ...decisions].sort((a, b) => Math.abs(b.revenue_impact || 0) - Math.abs(a.revenue_impact || 0))[0];
    const topExpansion = [...expansionOutcomes, ...growthSignals].sort((a, b) => Math.abs(b.revenue_impact || 0) - Math.abs(a.revenue_impact || 0))[0];

    return {
      risk: topRisk ? `Because: ${topRisk.title}` : (graphNodes.length > 0 ? 'Health-score based risk estimate' : 'No primary cause identified'),
      riskCount: allRiskNodes.length,
      protected: topProtected ? `Protected by: ${topProtected.title}` : (decisions.length > 0 ? `${decisions.length} active decisions` : 'No interventions recorded'),
      protectedCount: protectedCount,
      expansion: topExpansion ? `Driven by: ${topExpansion.title}` : (growthSignals.length > 0 ? `${growthSignals.length} growth signals detected` : 'Monitoring for expansion signals'),
      expansionCount: expansionCount,
    };
  }, [graphNodes]);

  // ── Computed: portfolio node type breakdown ──
  const portfolioNodesByType = useMemo(() => {
    if (!portfolioSummary?.nodes_by_type) return [];
    return Object.entries(portfolioSummary.nodes_by_type).map(([type, count]) => ({
      type: type.replace('_', ' '),
      rawType: type,
      count,
      fill: getNodeColor(type).hex,
    }));
  }, [portfolioSummary]);

  // ── Computed: portfolio graph density ──
  const portfolioGraphDensity = useMemo(() => {
    if (!portfolioSummary) return 0;
    const n = portfolioSummary.total_nodes;
    const e = portfolioSummary.total_edges;
    if (n < 2 || e === 0) return 0;
    // Use edge-to-node ratio (more intuitive than theoretical max density)
    // Typical healthy graph: 0.5-2.0 edges per node
    return e / n;
  }, [portfolioSummary]);

  // ── Computed: sorted nodes for deep dive grid ──
  const sortedNodes = useMemo(() => {
    return [...graphNodes].sort((a, b) => {
      let valA: any, valB: any;
      switch (sortField) {
        case 'node_type': valA = a.node_type; valB = b.node_type; break;
        case 'title': valA = a.title || ''; valB = b.title || ''; break;
        case 'occurred_at': valA = a.occurred_at || ''; valB = b.occurred_at || ''; break;
        case 'revenue_impact': valA = a.revenue_impact || 0; valB = b.revenue_impact || 0; break;
        case 'confidence': valA = a.confidence || 0; valB = b.confidence || 0; break;
        default: valA = a.occurred_at || ''; valB = b.occurred_at || '';
      }
      if (typeof valA === 'string') {
        const cmp = valA.localeCompare(valB as string);
        return sortDir === 'asc' ? cmp : -cmp;
      }
      return sortDir === 'asc' ? (valA as number) - (valB as number) : (valB as number) - (valA as number);
    });
  }, [graphNodes, sortField, sortDir]);

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const selectedAccount = accounts.find(a => a.account_id === selectedAccountId);

  // ── Sentiment helpers ──
  const sentimentColor = (val: number) => {
    if (val >= 0.6) return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
    if (val >= 0.4) return 'bg-gray-500/20 text-gray-400 border-gray-500/40';
    return 'bg-red-500/20 text-red-400 border-red-500/40';
  };

  const sentimentLabel = (val: number) => {
    if (val >= 0.6) return 'Positive';
    if (val >= 0.4) return 'Neutral';
    return 'Negative';
  };

  // ── Computed: current phase index for story arc ──
  const currentPhaseIndex = useMemo(() => {
    if (!storyArc?.phases?.length) return 0;
    return Math.min(Math.floor(storyArc.phases.length * 0.6), storyArc.phases.length - 1);
  }, [storyArc]);

  // ── Computed: next best action from story arc ──
  const nextBestAction = useMemo(() => {
    if (!storyArc) return null;
    const phase = storyArc.phases?.[currentPhaseIndex];
    if (!phase) return null;
    if (phase.plot_points?.length) {
      const nextPlot = phase.plot_points[0];
      return typeof nextPlot === 'string' ? nextPlot : nextPlot?.description || nextPlot?.name || null;
    }
    if (phase.revenue_impact_type === 'at_risk') return 'Schedule executive business review to address declining health';
    if (phase.revenue_impact_type === 'expansion') return 'Present expansion proposal with ROI analysis';
    return 'Maintain regular cadence and monitor signals';
  }, [storyArc, currentPhaseIndex]);

  // ── Total revenue across selected account for banner ──
  const totalRevenueExplained = useMemo(() => {
    if (!revenue) return 0;
    return Math.abs(revenue.at_risk) + Math.abs(revenue.protected) + Math.abs(revenue.expansion);
  }, [revenue]);

  // ── Portfolio total revenue for banner ──
  const portfolioTotalRevenue = useMemo(() => {
    if (!portfolioSummary) return 0;
    return Math.abs(portfolioSummary.total_at_risk) + Math.abs(portfolioSummary.total_protected) + Math.abs(portfolioSummary.total_expansion);
  }, [portfolioSummary]);

  // ── Loading State ──
  if (loading) {
    return (
      <div className="h-full bg-[#0f1419] p-6 space-y-6">
        <SkeletonCard className="h-24" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
        <SkeletonCard className="h-48" />
        <SkeletonCard className="h-64" />
        <SkeletonTable />
      </div>
    );
  }

  // ── Error State ──
  if (error && !accounts.length) {
    return (
      <div className="h-full bg-[#0f1419] flex items-center justify-center">
        <div className="bg-[#1a1f2e] rounded-xl border border-red-500/30 p-8 max-w-md text-center">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-white text-lg font-semibold mb-2">Failed to Load</h3>
          <p className="text-gray-400 text-sm mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-lg text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ── Empty State ──
  if (!accounts.length) {
    return (
      <div className="h-full bg-[#0f1419] flex items-center justify-center">
        <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-8 max-w-md text-center">
          <Brain className="w-12 h-12 text-gray-500 mx-auto mb-4" />
          <h3 className="text-white text-lg font-semibold mb-2">No Accounts Found</h3>
          <p className="text-gray-400 text-sm">
            Context graph data will appear once accounts are onboarded with graph-enabled data.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full bg-[#0f1419] text-white font-['Inter',sans-serif]">

      {/* ═══════════════════════════════════════════════════════════════════════ */}
      {/* MAIN CONTENT                                                          */}
      {/* ═══════════════════════════════════════════════════════════════════════ */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-[1200px] space-y-6">

          {/* ── Account loading indicator ── */}
          {accountLoading && (
            <div className="flex items-center gap-3 px-4 py-3 bg-violet-500/10 border border-violet-500/20 rounded-lg">
              <div className="w-4 h-4 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-violet-300">Loading context graph for {selectedAccount?.account_name}...</span>
            </div>
          )}

          {/* ── Viewing indicator ── */}
          {selectedAccount && !accountLoading && (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Eye className="w-3.5 h-3.5" />
              <span>Viewing: <span className="text-violet-400 font-medium">{selectedAccount.account_name}</span></span>
            </div>
          )}

          {/* ═══ SECTION 1: MISSION BANNER ═══ */}
          <div
            className="rounded-2xl p-6 relative overflow-hidden"
            style={{
              background: 'linear-gradient(135deg, #1a1025 0%, #0f1419 40%, #1a1025 100%)',
            }}
          >
            <div className="absolute inset-0 opacity-20"
              style={{
                background: 'radial-gradient(ellipse at 20% 50%, rgba(139, 92, 246, 0.3) 0%, transparent 70%), radial-gradient(ellipse at 80% 50%, rgba(124, 58, 237, 0.15) 0%, transparent 70%)',
              }}
            />
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl bg-violet-500/20 border border-violet-500/30 flex items-center justify-center">
                  <Brain className="w-5 h-5 text-violet-400" />
                </div>
                <h1 className="text-2xl font-bold text-white">Causal Intelligence</h1>
              </div>
              <p className="text-violet-200/70 text-base mb-3 max-w-2xl">
                Understanding why your accounts behave the way they do
              </p>
              <div className="flex flex-wrap items-center gap-4 text-sm">
                <span className="text-gray-400">
                  <span className="text-violet-300 font-semibold">{portfolioSummary?.total_nodes ?? 0}</span> total nodes
                </span>
                <span className="text-gray-600">|</span>
                <span className="text-gray-400">
                  across <span className="text-violet-300 font-semibold">{accounts.length}</span> account{accounts.length !== 1 ? 's' : ''}
                </span>
                <span className="text-gray-600">|</span>
                <span className="text-gray-400">
                  <span className="text-violet-300 font-semibold">{formatCompact(portfolioTotalRevenue)}</span> revenue explained
                </span>
              </div>
            </div>
          </div>

          {/* ═══ SECTION 2: REVENUE STORY ═══ */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <DollarSign className="w-5 h-5 text-gray-400" />
              <h2 className="text-lg font-semibold text-white">Revenue Story</h2>
              {selectedAccount && (
                <span className="text-xs text-gray-500 ml-1">({selectedAccount.account_name})</span>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Revenue at Risk */}
              <div className="bg-[#1a1f2e] rounded-xl border border-red-500/20 p-5 relative overflow-hidden group hover:border-red-500/40 transition-all">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-600 to-red-400" />
                <div className="flex items-center gap-2 text-red-400 text-sm mb-3">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="font-medium">Revenue at Risk</span>
                </div>
                <div className="text-3xl font-bold text-red-400 mb-1">
                  {revenue ? formatCompact(revenue.at_risk) : '--'}
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
                  <span>{revenueBecause.riskCount} contributing signal{revenueBecause.riskCount !== 1 ? 's' : ''}</span>
                  {revenue?.lost ? (
                    <>
                      <span className="text-gray-700">|</span>
                      <span className="text-red-500/80">{formatCompact(revenue.lost)} already lost</span>
                    </>
                  ) : null}
                </div>
                <div className="text-xs text-red-300/60 italic truncate" title={revenueBecause.risk}>
                  {revenueBecause.risk}
                </div>
              </div>

              {/* Revenue Protected */}
              <div className="bg-[#1a1f2e] rounded-xl border border-emerald-500/20 p-5 relative overflow-hidden group hover:border-emerald-500/40 transition-all">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-600 to-emerald-400" />
                <div className="flex items-center gap-2 text-emerald-400 text-sm mb-3">
                  <Shield className="w-4 h-4" />
                  <span className="font-medium">Revenue Protected</span>
                </div>
                <div className="text-3xl font-bold text-emerald-400 mb-1">
                  {revenue ? formatCompact(revenue.protected) : '--'}
                </div>
                <div className="text-xs text-gray-500 mb-3">
                  {revenueBecause.protectedCount} intervention{revenueBecause.protectedCount !== 1 ? 's' : ''} active
                </div>
                <div className="text-xs text-emerald-300/60 italic truncate" title={revenueBecause.protected}>
                  {revenueBecause.protected}
                </div>
              </div>

              {/* Expansion Opportunity */}
              <div className="bg-[#1a1f2e] rounded-xl border border-cyan-500/20 p-5 relative overflow-hidden group hover:border-cyan-500/40 transition-all">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-600 to-cyan-400" />
                <div className="flex items-center gap-2 text-cyan-400 text-sm mb-3">
                  <TrendingUp className="w-4 h-4" />
                  <span className="font-medium">Expansion Opportunity</span>
                </div>
                <div className="text-3xl font-bold text-cyan-400 mb-1">
                  {revenue ? formatCompact(revenue.expansion) : '--'}
                </div>
                <div className="text-xs text-gray-500 mb-3">
                  {revenueBecause.expansionCount} growth signal{revenueBecause.expansionCount !== 1 ? 's' : ''}
                </div>
                <div className="text-xs text-cyan-300/60 italic truncate" title={revenueBecause.expansion}>
                  {revenueBecause.expansion}
                </div>
              </div>
            </div>
          </div>

          {/* ═══ SECTION 3: SVG GRAPH VISUALIZATION (replaces causal chains) ═══ */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Zap className="w-5 h-5 text-yellow-400" />
              <h2 className="text-lg font-semibold text-white">Context Graph</h2>
              <span className="text-xs text-gray-500 ml-1">
                {svgLayout.nodes.length} nodes, {svgLayout.edges.length} edges
                {graphNodes.length > svgLayout.nodes.length && ` (${svgLayout.nodes.length} key nodes of ${graphNodes.length})`}
              </span>
            </div>

            {svgLayout.nodes.length > 0 ? (
              <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
                {/* Legend */}
                <GraphLegend />

                {/* SVG Canvas — constrained height with scroll */}
                <div className="overflow-auto" style={{ maxHeight: 500 }}>
                  <svg
                    width={svgLayout.svgW}
                    height={svgLayout.svgH}
                    viewBox={`0 0 ${svgLayout.svgW} ${svgLayout.svgH}`}
                    style={{ minHeight: 200, background: '#111720' }}
                    onClick={(e) => {
                      if ((e.target as SVGElement).tagName === 'svg') setSvgSelected(null);
                    }}
                  >
                    {/* Edges first (behind nodes) */}
                    {svgLayout.edges.map((e, i) => (
                      <EdgeLine key={i} edge={e} nodes={svgLayout.nodes} dimmed={isEdgeDimmed(e)} />
                    ))}
                    {/* Nodes */}
                    {svgLayout.nodes.map(n => (
                      <NodeShape
                        key={n.id}
                        node={n}
                        dimmed={isNodeDimmed(n.id)}
                        onClick={(node) => setSvgSelected(prev => prev === node.id ? null : node.id)}
                      />
                    ))}
                  </svg>
                </div>

                {/* Selected node detail bar */}
                {svgSelected && (() => {
                  const activeNode = svgLayout.nodes.find(n => n.id === svgSelected);
                  if (!activeNode) return null;
                  const s = SVG_NODE_STYLES[activeNode.styleKey] || SVG_NODE_STYLES.SIGNAL;
                  return (
                    <div className="px-4 py-3 border-t border-gray-700/50 bg-[#0f1419] flex items-start gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                            style={{ background: s.bg }}
                          />
                          <span className="text-xs text-gray-500 uppercase tracking-wide">
                            {activeNode.type}
                            {activeNode.subtype ? ` / ${activeNode.subtype}` : ''}
                          </span>
                        </div>
                        <div className="text-sm font-semibold text-white truncate">
                          {activeNode.raw.title}
                        </div>
                        {activeNode.occurredAt && (
                          <div className="text-xs text-gray-500 mt-0.5">
                            {new Date(activeNode.occurredAt).toLocaleDateString('en-US', {
                              year: 'numeric', month: 'long', day: 'numeric',
                            })}
                          </div>
                        )}
                      </div>
                      {activeNode.revenueImpact != null && (
                        <div className="text-right flex-shrink-0">
                          <div className="text-sm font-bold" style={{ color: s.bg }}>
                            {formatCompact(Math.abs(activeNode.revenueImpact))}
                          </div>
                          <div className="text-xs text-gray-500">{activeNode.revenueType || 'impact'}</div>
                        </div>
                      )}
                      <div className="flex-shrink-0">
                        <span className="text-xs text-gray-500">
                          {svgConnectedEdges.length} connection{svgConnectedEdges.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                      <button
                        onClick={() => setSvgSelected(null)}
                        className="text-xs text-gray-500 hover:text-gray-300 border border-gray-700 rounded px-2 py-1 flex-shrink-0"
                      >
                        Clear
                      </button>
                    </div>
                  );
                })()}
              </div>
            ) : (
              <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/30 p-6 flex items-center gap-3">
                <GitBranch className="w-5 h-5 text-gray-500" />
                <span className="text-sm text-gray-500">
                  No graph data available. Nodes appear when context graph CSVs are ingested for this account.
                </span>
              </div>
            )}
          </div>

          {/* ═══ SECTION 4: STORY ARCS IN PROGRESS ═══ */}
          {storyArc && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-5 h-5 text-violet-400" />
                <h2 className="text-lg font-semibold text-white">Story Arcs in Progress</h2>
              </div>

              <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 space-y-5">
                {/* Arc header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 rounded-lg bg-violet-500/15 border border-violet-500/30 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <Play className="w-4 h-4 text-violet-400" />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-white">{storyArc.arc_name}</h3>
                      <p className="text-sm text-gray-400 mt-0.5 max-w-2xl">{storyArc.description}</p>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0 ml-4">
                    <div className="text-xs text-gray-500 uppercase tracking-wide">Duration</div>
                    <div className="text-sm text-gray-300 font-mono">{storyArc.duration_weeks}w</div>
                  </div>
                </div>

                {/* Phase progression bar */}
                {storyArc.phases?.length > 0 && (
                  <div>
                    <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Phase Progression</div>
                    <div className="flex gap-1 w-full">
                      {storyArc.phases.map((phase, idx) => {
                        const widthPct = (phase.duration_weeks / storyArc.duration_weeks) * 100;
                        const isCurrent = idx === currentPhaseIndex;
                        const isPast = idx < currentPhaseIndex;
                        const healthAvg = (phase.health_range.start + phase.health_range.end) / 2;
                        const barColor = healthAvg >= 70 ? 'bg-emerald-500' : healthAvg >= 50 ? 'bg-yellow-500' : 'bg-red-500';

                        return (
                          <div
                            key={phase.phase_id}
                            className="group relative"
                            style={{ width: `${widthPct}%`, minWidth: '50px' }}
                          >
                            <div className={`h-8 ${barColor} rounded transition-all ${
                              isCurrent ? 'opacity-100 ring-2 ring-white/30' : isPast ? 'opacity-50' : 'opacity-25'
                            }`} />
                            <div className={`text-[10px] mt-1 truncate text-center ${
                              isCurrent ? 'text-white font-medium' : 'text-gray-500'
                            }`}>
                              {phase.name}
                            </div>
                            {/* Tooltip */}
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10">
                              <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs whitespace-nowrap shadow-xl">
                                <div className="text-white font-medium">{phase.name}</div>
                                <div className="text-gray-400">{phase.duration_weeks}w | Health: {phase.health_range.start}-{phase.health_range.end}</div>
                                <div className="text-gray-500 max-w-[200px] whitespace-normal">{phase.description}</div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Revenue narrative row */}
                {storyArc.revenue_narrative && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-[#0f1419] rounded-lg p-3">
                      <div className="text-xs text-gray-500">ARR Start</div>
                      <div className="text-sm font-semibold text-white">{formatCompact(storyArc.revenue_narrative.arr_start)}</div>
                    </div>
                    <div className="bg-[#0f1419] rounded-lg p-3">
                      <div className="text-xs text-gray-500">Peak at Risk</div>
                      <div className="text-sm font-semibold text-red-400">{formatCompact(storyArc.revenue_narrative.arr_at_risk_peak)}</div>
                    </div>
                    <div className="bg-[#0f1419] rounded-lg p-3">
                      <div className="text-xs text-gray-500">Net Revenue Saved</div>
                      <div className="text-sm font-semibold text-emerald-400">{formatCompact(storyArc.revenue_narrative.net_revenue_saved)}</div>
                    </div>
                    <div className="bg-[#0f1419] rounded-lg p-3">
                      <div className="text-xs text-gray-500">ROI of Intervention</div>
                      <div className="text-sm font-semibold text-violet-400">{storyArc.revenue_narrative.roi_of_intervention?.toFixed(1)}x</div>
                    </div>
                  </div>
                )}

                {/* Next Best Action */}
                {nextBestAction && (
                  <div className="bg-violet-500/10 border border-violet-500/20 rounded-lg px-4 py-3 flex items-center gap-3">
                    <Lightbulb className="w-4 h-4 text-violet-400 flex-shrink-0" />
                    <div>
                      <div className="text-xs text-violet-400 font-medium uppercase tracking-wide mb-0.5">Next Best Action</div>
                      <div className="text-sm text-violet-200">{nextBestAction}</div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* No story arc fallback */}
          {!storyArc && !accountLoading && selectedAccountId && (
            <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/30 p-5 flex items-center gap-3">
              <Eye className="w-5 h-5 text-gray-500" />
              <span className="text-sm text-gray-500">
                No story arc data available for this account. Arcs are generated when sufficient context graph signals exist.
              </span>
            </div>
          )}

        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════ */}
      {/* RIGHT CONTEXT PANEL                                                   */}
      {/* ═══════════════════════════════════════════════════════════════════════ */}
      <div className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 overflow-y-auto flex flex-col gap-5">

        {/* ── Portfolio Total Label ── */}
        <div className="text-center">
          <div className="text-[10px] text-violet-400 uppercase tracking-widest font-semibold">Portfolio Total</div>
          <div className="text-xs text-gray-500 mt-0.5">
            {portfolioSummary
              ? `${portfolioSummary.accounts_loaded} account${portfolioSummary.accounts_loaded !== 1 ? 's' : ''} aggregated`
              : portfolioLoading ? 'Loading...' : '--'}
          </div>
        </div>

        {/* ── Graph Stats (4 mini cards) - PORTFOLIO-WIDE ── */}
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-2">
            <Activity className="w-3.5 h-3.5" />
            Graph Stats
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-[#1a1f2e] rounded-lg border border-gray-700/40 p-3">
              <div className="text-[10px] text-gray-500 uppercase tracking-wide">Nodes</div>
              <div className="text-lg font-bold text-white">{portfolioSummary?.total_nodes ?? 0}</div>
            </div>
            <div className="bg-[#1a1f2e] rounded-lg border border-gray-700/40 p-3">
              <div className="text-[10px] text-gray-500 uppercase tracking-wide">Edges</div>
              <div className="text-lg font-bold text-white">{portfolioSummary?.total_edges ?? 0}</div>
            </div>
            <div className="bg-[#1a1f2e] rounded-lg border border-gray-700/40 p-3">
              <div className="text-[10px] text-gray-500 uppercase tracking-wide">Edges/Node</div>
              <div className="text-lg font-bold text-white">{portfolioGraphDensity.toFixed(1)}</div>
            </div>
            <div className="bg-[#1a1f2e] rounded-lg border border-gray-700/40 p-3">
              <div className="text-[10px] text-gray-500 uppercase tracking-wide">Accounts</div>
              <div className="text-lg font-bold text-white">{portfolioSummary?.accounts_loaded ?? 0}</div>
            </div>
          </div>
        </div>

        {/* ── Portfolio Revenue Summary ── */}
        {portfolioSummary && (portfolioSummary.total_at_risk > 0 || portfolioSummary.total_protected > 0 || portfolioSummary.total_expansion > 0) && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-2">
              <DollarSign className="w-3.5 h-3.5" />
              Portfolio Revenue
            </div>
            <div className="space-y-2">
              {portfolioSummary.total_at_risk > 0 && (
                <div className="bg-[#1a1f2e] rounded-lg border border-red-500/20 px-3 py-2 flex items-center justify-between">
                  <span className="text-xs text-red-400">At Risk</span>
                  <span className="text-sm font-bold text-red-400">{formatCompact(portfolioSummary.total_at_risk)}</span>
                </div>
              )}
              {portfolioSummary.total_protected > 0 && (
                <div className="bg-[#1a1f2e] rounded-lg border border-emerald-500/20 px-3 py-2 flex items-center justify-between">
                  <span className="text-xs text-emerald-400">Protected</span>
                  <span className="text-sm font-bold text-emerald-400">{formatCompact(portfolioSummary.total_protected)}</span>
                </div>
              )}
              {portfolioSummary.total_expansion > 0 && (
                <div className="bg-[#1a1f2e] rounded-lg border border-cyan-500/20 px-3 py-2 flex items-center justify-between">
                  <span className="text-xs text-cyan-400">Expansion</span>
                  <span className="text-sm font-bold text-cyan-400">{formatCompact(portfolioSummary.total_expansion)}</span>
                </div>
              )}
              {portfolioSummary.total_net_impact !== 0 && (
                <div className="bg-[#1a1f2e] rounded-lg border border-gray-700/40 px-3 py-2 flex items-center justify-between">
                  <span className="text-xs text-gray-400">Net Impact</span>
                  <span className="text-sm font-bold text-white">{formatCompact(portfolioSummary.total_net_impact)}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Node Type Breakdown (PORTFOLIO-WIDE colored mini bars) ── */}
        {portfolioNodesByType.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-2">
              <Layers className="w-3.5 h-3.5" />
              Node Types
            </div>
            <div className="space-y-2">
              {portfolioNodesByType.map(({ type, count, fill }) => {
                const total = portfolioNodesByType.reduce((s, n) => s + n.count, 0);
                const pct = total > 0 ? (count / total) * 100 : 0;
                return (
                  <div key={type}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="flex items-center gap-1.5 text-gray-400">
                        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: fill }} />
                        {type}
                      </span>
                      <span className="text-gray-500 font-mono">{count}</span>
                    </div>
                    <div className="w-full bg-gray-800 rounded-full h-1.5">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{ width: `${pct}%`, backgroundColor: fill }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Account Selector (dropdown) ── */}
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-2">
            <Target className="w-3.5 h-3.5" />
            Account
          </div>
          <div className="relative">
            <button
              onClick={() => setAccountDropdownOpen(!accountDropdownOpen)}
              className="w-full flex items-center justify-between bg-[#1a1f2e] border border-gray-700/50 rounded-lg px-3 py-2.5 text-left hover:border-violet-500/40 transition-colors"
            >
              <span className="text-white text-sm truncate">
                {selectedAccount ? selectedAccount.account_name : 'Select Account'}
              </span>
              <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform flex-shrink-0 ${accountDropdownOpen ? 'rotate-180' : ''}`} />
            </button>
            {accountDropdownOpen && (
              <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-[#1a1f2e] border border-gray-700/50 rounded-lg shadow-xl max-h-60 overflow-y-auto">
                {accounts.map(acct => (
                  <button
                    key={acct.account_id}
                    onClick={() => {
                      setSelectedAccountId(acct.account_id);
                      setAccountDropdownOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2.5 text-sm hover:bg-white/5 transition-colors ${
                      acct.account_id === selectedAccountId ? 'bg-violet-500/10 text-violet-400' : 'text-gray-300'
                    }`}
                  >
                    <span className="block truncate">{acct.account_name}</span>
                    {acct.revenue ? (
                      <span className="text-xs text-gray-500">{formatCompact(acct.revenue)} ARR</span>
                    ) : null}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Account Node Grid (compact scrollable table) ── */}
        {graphNodes.length > 0 && selectedAccountId && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-2">
              <GitBranch className="w-3.5 h-3.5" />
              Node Inventory ({graphNodes.length})
            </div>
            <div className="bg-[#1a1f2e] rounded-lg border border-gray-700/40 overflow-hidden">
              <div className="max-h-[360px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-[#1a1f2e] z-10">
                    <tr className="border-b border-gray-700/50">
                      {[
                        { field: 'node_type', label: 'Type' },
                        { field: 'title', label: 'Title' },
                        { field: 'revenue_impact', label: 'Rev.' },
                        { field: 'confidence', label: 'Conf' },
                      ].map(col => (
                        <th
                          key={col.field}
                          onClick={() => handleSort(col.field)}
                          className="px-2 py-2 text-left text-[10px] text-gray-500 uppercase tracking-wide cursor-pointer hover:text-gray-300 transition-colors select-none"
                        >
                          <span className="flex items-center gap-0.5">
                            {col.label}
                            {sortField === col.field && (
                              <span className="text-violet-400">{sortDir === 'asc' ? '\u2191' : '\u2193'}</span>
                            )}
                          </span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sortedNodes.map(node => {
                      const sk = getStyleKey(node);
                      const color = getNodeColor(sk);
                      const displayType = sk === 'SIGNAL_SYSTEM' ? 'SYS' : node.node_type.replace('_', ' ').slice(0, 6);
                      return (
                        <tr
                          key={node.node_id}
                          className="border-b border-gray-700/20 hover:bg-white/[0.02] transition-colors"
                        >
                          <td className="px-2 py-1.5">
                            <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${color.bg} ${color.text}`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${color.dot}`} />
                              {displayType}
                            </span>
                          </td>
                          <td className="px-2 py-1.5 text-gray-300 max-w-[120px] truncate" title={node.title}>
                            {node.title || '--'}
                          </td>
                          <td className="px-2 py-1.5">
                            {node.revenue_impact != null ? (
                              <span className={
                                node.revenue_impact_type === 'at_risk' || node.revenue_impact_type === 'lost'
                                  ? 'text-red-400'
                                  : node.revenue_impact_type === 'expansion'
                                    ? 'text-cyan-400'
                                    : 'text-emerald-400'
                              }>
                                {formatCompact(node.revenue_impact)}
                              </span>
                            ) : (
                              <span className="text-gray-600">--</span>
                            )}
                          </td>
                          <td className="px-2 py-1.5">
                            {node.confidence != null ? (
                              <div className="flex items-center gap-1">
                                <div className="w-8 bg-gray-800 rounded-full h-1">
                                  <div
                                    className="h-full rounded-full bg-violet-500"
                                    style={{ width: `${node.confidence * 100}%` }}
                                  />
                                </div>
                                <span className="text-[10px] text-gray-500 font-mono">{(node.confidence * 100).toFixed(0)}%</span>
                              </div>
                            ) : (
                              <span className="text-gray-600">--</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Empty nodes in right panel */}
        {!graphNodes.length && !accountLoading && selectedAccountId && (
          <div className="text-center py-6">
            <Layers className="w-8 h-8 text-gray-600 mx-auto mb-2" />
            <h3 className="text-gray-400 text-sm font-medium mb-1">No Graph Nodes</h3>
            <p className="text-xs text-gray-500">
              Upload context graph CSVs to populate.
            </p>
          </div>
        )}

        {/* ── Key Actors (sentiment pills) ── */}
        {storyArc && storyArc.cast && storyArc.cast.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-2">
              <Users className="w-3.5 h-3.5" />
              Key Actors ({storyArc.cast.length})
            </div>
            <div className="flex flex-col gap-2">
              {storyArc.cast.map((member, idx) => {
                const avgSentiment = member.sentiment_arc.length
                  ? member.sentiment_arc.reduce((a, b) => a + b, 0) / member.sentiment_arc.length
                  : 0.5;
                return (
                  <div
                    key={idx}
                    className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs border ${sentimentColor(avgSentiment)}`}
                  >
                    <div className="flex flex-col min-w-0">
                      <span className="font-medium truncate">{member.title}</span>
                      <span className="text-[10px] opacity-60">{member.role}</span>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                      <span className="opacity-80">{sentimentLabel(avgSentiment)}</span>
                      <span className="opacity-50 font-mono">{(member.influence_score * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default ContextGraphView;
