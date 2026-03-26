/**
 * ContextGraphExplorer.tsx
 * =======================
 * Interactive SVG visualization of the context graph for an account.
 * Fetches nodes + edges from the API, auto-layouts them by type/date,
 * and supports click-to-highlight with a detail side panel.
 *
 * Data-driven: works for ANY account, not just hardcoded demo data.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { RefreshCw } from 'lucide-react';
import { fetchGraphNodes, fetchAccountEdges, fetchRevenueBreakdown, fmtDollar } from '../../../utils/contextGraphApi';
import type { ContextNodeDTO, ContextEdgeDTO, RevenueBreakdown, NodeType } from '../../../types/contextGraph';

// ── Constants ──

const NW = 160;   // node width
const NH = 56;    // node height
const COL_GAP = 60;
const ROW_GAP = 40;
const HEADER_H = 52;
const PADDING = 30;

const STYLES: Record<string, { bg: string; border: string; text: string }> = {
  SIGNAL:           { bg: '#FFA500', border: '#cc8400', text: '#000' },
  SIGNAL_SYSTEM:    { bg: '#06B6D4', border: '#0891B2', text: '#000' },  // cyan for system-generated
  DECISION:         { bg: '#4169E1', border: '#2a4db5', text: '#fff' },
  OUTCOME:          { bg: '#2E8B57', border: '#1e6b40', text: '#fff' },
  STAKEHOLDER:      { bg: '#8B5CF6', border: '#6d3fd4', text: '#fff' },
  EXTERNAL_CONTEXT: { bg: '#6B7280', border: '#4B5563', text: '#fff' },
};

/** Determine if a signal node is system-generated (Wizard A / arc classifier) */
function isSystemSignal(n: ContextNodeDTO): boolean {
  if (n.node_type !== 'SIGNAL') return false;
  const src = (n as any).source;
  if (src === 'system') return true;
  if (n.node_subtype === 'arc_detection') return true;
  if (n.properties?.triggered_by) return true;
  return false;
}

/** Get the visual style key for a node (splits SIGNAL into two sub-types) */
function getStyleKey(n: ContextNodeDTO): string {
  if (isSystemSignal(n)) return 'SIGNAL_SYSTEM';
  return n.node_type || 'SIGNAL';
}

// Column assignment: stakeholders at top, then chronological lanes by type
const TYPE_PRIORITY: Record<string, number> = {
  STAKEHOLDER: 0,
  SIGNAL: 1,
  DECISION: 2,
  OUTCOME: 3,
  EXTERNAL_CONTEXT: 4,
};

// ── Types ──

interface LayoutNode {
  id: string;
  nodeId: number;
  type: string;
  styleKey: string;           // visual style key (e.g. 'SIGNAL_SYSTEM' for system-gen)
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

// ── Props ──

interface ContextGraphExplorerProps {
  accountId: number;
}

// ── Layout algorithm ──

function layoutNodes(nodes: ContextNodeDTO[]): LayoutNode[] {
  if (nodes.length === 0) return [];

  // Group by type
  const byType: Record<string, ContextNodeDTO[]> = {};
  for (const n of nodes) {
    const t = n.node_type || 'SIGNAL';
    if (!byType[t]) byType[t] = [];
    byType[t].push(n);
  }

  // Sort types by priority
  const sortedTypes = Object.keys(byType).sort(
    (a, b) => (TYPE_PRIORITY[a] ?? 9) - (TYPE_PRIORITY[b] ?? 9)
  );

  // Within each type, sort by occurred_at
  for (const t of sortedTypes) {
    byType[t].sort((a, b) => {
      const da = a.occurred_at ? new Date(a.occurred_at).getTime() : 0;
      const db = b.occurred_at ? new Date(b.occurred_at).getTime() : 0;
      return da - db;
    });
  }

  // Assign column index per type (horizontal lanes)
  // Stakeholders get a dedicated top row; others get vertical lanes
  const result: LayoutNode[] = [];

  // --- Stakeholders: horizontal row at top ---
  const stakeholders = byType['STAKEHOLDER'] || [];
  const stakeholderY = HEADER_H + PADDING;
  const stakeholderStartX = PADDING;
  stakeholders.forEach((n, i) => {
    result.push(makeLayoutNode(n, stakeholderStartX + i * (NW + COL_GAP), stakeholderY));
  });

  // --- Other types: vertical lanes ---
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
  const titleTrunc = (n.title || '').length > 30
    ? (n.title || '').substring(0, 29) + '\u2026'
    : (n.title || '');

  // For stakeholders, show name as label + role as sub
  const isStakeholder = n.node_type === 'STAKEHOLDER';
  const label = isStakeholder ? titleTrunc : dateStr;
  const sub = isStakeholder
    ? (n.node_subtype || n.properties?.department || '')
    : titleTrunc;

  // Revenue annotation for outcome nodes
  let revSub = sub;
  if (n.node_type === 'OUTCOME' && n.revenue_impact) {
    revSub = `${fmtDollar(Math.abs(n.revenue_impact))} ${n.revenue_impact_type || ''}\n${sub}`;
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

// ── SVG Sub-components ──

function getCenter(node: LayoutNode) {
  return { cx: node.x + NW / 2, cy: node.y + NH / 2 };
}

function NodeShape({
  node,
  dimmed,
  onClick,
}: {
  node: LayoutNode;
  dimmed: boolean;
  onClick: (node: LayoutNode) => void;
}) {
  const s = STYLES[node.styleKey] || STYLES.SIGNAL;
  const { x, y } = node;
  const cx = x + NW / 2;
  const cy = y + NH / 2;
  const opacity = dimmed ? 0.2 : 1;
  const isSysSignal = node.styleKey === 'SIGNAL_SYSTEM';

  return (
    <g
      onClick={() => onClick(node)}
      style={{ cursor: 'pointer', opacity, transition: 'opacity 0.2s' }}
    >
      {node.type === 'STAKEHOLDER' ? (
        <circle cx={cx} cy={cy} r={32} fill={s.bg} stroke={s.border} strokeWidth={2} />
      ) : node.type === 'DECISION' ? (
        <polygon
          points={`${cx},${y} ${x + NW},${cy} ${cx},${y + NH} ${x},${cy}`}
          fill={s.bg} stroke={s.border} strokeWidth={2}
        />
      ) : (
        <rect
          x={x} y={y} width={NW} height={NH} rx={isSysSignal ? 14 : 7}
          fill={s.bg} stroke={s.border}
          strokeWidth={node.type === 'OUTCOME' ? 3 : 2}
          strokeDasharray={isSysSignal ? '6 3' : undefined}
        />
      )}
      {isSysSignal && (
        <text x={x + NW - 6} y={y + 10} textAnchor="end"
              fill="#000" fontSize={8} fontWeight={700} fontFamily="monospace" opacity={0.7}>
          SYS
        </text>
      )}
      <text
        x={cx} y={cy - 8} textAnchor="middle"
        fill={s.text} fontSize={11} fontWeight={800}
        fontFamily="'Courier New', monospace"
      >
        {node.label}
      </text>
      <foreignObject x={x + 4} y={cy + 2} width={NW - 8} height={34}>
        <div
          style={{
            fontSize: 9, color: s.text, textAlign: 'center',
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
}

function EdgeLine({
  edge,
  nodes,
  dimmed,
}: {
  edge: LayoutEdge;
  nodes: LayoutNode[];
  dimmed: boolean;
}) {
  const fn = nodes.find(n => n.id === edge.from);
  const tn = nodes.find(n => n.id === edge.to);
  if (!fn || !tn) return null;

  const { cx: x1, cy: y1 } = getCenter(fn);
  const { cx: x2, cy: y2 } = getCenter(tn);
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const markerId = `arr-${edge.from}-${edge.to}`;
  const color = dimmed ? '#333' : '#666';
  const dash =
    edge.label === 'INVOLVES' ? '5,4'
    : edge.label === 'INDICATES' ? '3,3'
    : '0';

  return (
    <g style={{ opacity: dimmed ? 0.12 : 1, transition: 'opacity 0.2s' }}>
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
}

// ── Revenue summary cards ──

function RevenueSidebar({ revenue }: { revenue: RevenueBreakdown | null }) {
  if (!revenue) return null;
  const cards: { label: string; value: number; color: string }[] = [];
  if (revenue.protected > 0) cards.push({ label: 'Protected', value: revenue.protected, color: '#2E8B57' });
  if (revenue.expansion > 0) cards.push({ label: 'Expansion', value: revenue.expansion, color: '#4169E1' });
  if (revenue.at_risk > 0)   cards.push({ label: 'At Risk', value: revenue.at_risk, color: '#dc2626' });
  if (revenue.lost > 0)      cards.push({ label: 'Lost', value: revenue.lost, color: '#6B7280' });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 16 }}>
      {cards.map(c => (
        <div
          key={c.label}
          style={{
            padding: '12px', background: '#161b22', borderRadius: 8,
            borderLeft: `3px solid ${c.color}`,
          }}
        >
          <div style={{ color: c.color, fontWeight: 800, fontSize: 13 }}>{fmtDollar(c.value)}</div>
          <div style={{ fontSize: 10, marginTop: 3, color: '#8b949e' }}>{c.label}</div>
        </div>
      ))}
      {revenue.net_impact > 0 && (
        <div style={{ padding: '10px 12px', borderTop: '1px solid #21262d', marginTop: 4 }}>
          <div style={{ fontSize: 10, color: '#8b949e' }}>Net Impact</div>
          <div style={{ fontWeight: 800, fontSize: 14, color: '#e6edf3' }}>{fmtDollar(revenue.net_impact)}</div>
        </div>
      )}
    </div>
  );
}

// ── Main component ──

const ContextGraphExplorer: React.FC<ContextGraphExplorerProps> = ({ accountId }) => {
  const [rawNodes, setRawNodes] = useState<ContextNodeDTO[]>([]);
  const [rawEdges, setRawEdges] = useState<ContextEdgeDTO[]>([]);
  const [revenue, setRevenue] = useState<RevenueBreakdown | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  // ── Fetch data ──
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSelected(null);
    try {
      const [nodesResp, edgesResp, revResp] = await Promise.all([
        fetchGraphNodes(accountId, undefined, undefined, 200),
        fetchAccountEdges(accountId, 500),
        fetchRevenueBreakdown(accountId),
      ]);
      setRawNodes(nodesResp.nodes || []);
      setRawEdges(edgesResp.edges || []);
      setRevenue(revResp);
    } catch (err: any) {
      setError(err.message || 'Failed to load graph data');
    } finally {
      setLoading(false);
    }
  }, [accountId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Layout ──
  const layoutData = useMemo(() => {
    const nodes = layoutNodes(rawNodes);
    const nodeIdSet = new Set(rawNodes.map(n => n.node_id));
    const edges = mapEdges(rawEdges, nodeIdSet);

    // Compute SVG dimensions
    let maxX = 800;
    let maxY = 600;
    for (const n of nodes) {
      maxX = Math.max(maxX, n.x + NW + PADDING);
      maxY = Math.max(maxY, n.y + NH + PADDING);
    }
    return { nodes, edges, svgW: maxX, svgH: maxY };
  }, [rawNodes, rawEdges]);

  // ── Selection ──
  const connectedEdges = selected
    ? layoutData.edges.filter(e => e.from === selected || e.to === selected)
    : [];
  const connectedIds = new Set(connectedEdges.flatMap(e => [e.from, e.to]));
  const activeNode = layoutData.nodes.find(n => n.id === selected);

  const isNodeDimmed = (id: string) => !!selected && !connectedIds.has(id);
  const isEdgeDimmed = (e: LayoutEdge) => !!selected && !connectedEdges.includes(e);

  // ── Type counts for legend (split signals into user vs system) ──
  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const n of rawNodes) {
      const key = getStyleKey(n);
      counts[key] = (counts[key] || 0) + 1;
    }
    return counts;
  }, [rawNodes]);

  // ── Loading / error states ──
  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
                    height: '100%', background: '#0d1117', color: '#e6edf3' }}>
        <RefreshCw style={{ width: 32, height: 32, animation: 'spin 1s linear infinite' }} />
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center',
                    justifyContent: 'center', height: '100%', background: '#0d1117',
                    color: '#e6edf3', gap: 12 }}>
        <div style={{ color: '#f59e0b', fontSize: 14 }}>{error}</div>
        <button
          onClick={loadData}
          style={{ background: '#21262d', border: '1px solid #30363d', color: '#8b949e',
                   padding: '6px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (layoutData.nodes.length === 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
                    height: '100%', background: '#0d1117', color: '#8b949e', fontSize: 14 }}>
        No context graph data for this account
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', height: '100%', background: '#0d1117',
                  color: '#e6edf3', fontFamily: 'monospace' }}>
      {/* Graph area */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {/* Header */}
        <div style={{
          padding: '12px 24px 10px', borderBottom: '1px solid #21262d',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <div style={{ fontSize: 10, color: '#8b949e', letterSpacing: 2, textTransform: 'uppercase' }}>
              Account #{accountId}
            </div>
            <div style={{ fontSize: 18, fontWeight: 800 }}>Context Graph Explorer</div>
          </div>
          <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
            {Object.entries(STYLES).map(([type, s]) => {
              const count = typeCounts[type];
              if (!count) return null;
              const LEGEND_LABELS: Record<string, string> = {
                SIGNAL: 'Signal',
                SIGNAL_SYSTEM: 'System Signal',
                DECISION: 'Decision',
                OUTCOME: 'Outcome',
                STAKEHOLDER: 'Stakeholder',
                EXTERNAL_CONTEXT: 'External',
              };
              const isSys = type === 'SIGNAL_SYSTEM';
              return (
                <span key={type} style={{ display: 'flex', alignItems: 'center', gap: 5,
                                          fontSize: 10, color: '#8b949e' }}>
                  <span style={{
                    width: 10, height: 10,
                    borderRadius: type === 'STAKEHOLDER' ? '50%' : (isSys ? 5 : 2),
                    background: s.bg, display: 'inline-block',
                    border: isSys ? '1px dashed #0891B2' : undefined,
                  }} />
                  {LEGEND_LABELS[type] || type} ({count})
                </span>
              );
            })}
            <button
              onClick={loadData}
              title="Refresh"
              style={{ background: 'none', border: 'none', color: '#8b949e',
                       cursor: 'pointer', padding: 4 }}
            >
              <RefreshCw style={{ width: 14, height: 14 }} />
            </button>
          </div>
        </div>

        {/* SVG canvas */}
        <svg
          width={layoutData.svgW}
          height={layoutData.svgH}
          onClick={(e) => {
            if ((e.target as SVGElement).tagName === 'svg') setSelected(null);
          }}
        >
          {layoutData.edges.map((e, i) => (
            <EdgeLine key={i} edge={e} nodes={layoutData.nodes} dimmed={isEdgeDimmed(e)} />
          ))}
          {layoutData.nodes.map(n => (
            <NodeShape
              key={n.id}
              node={n}
              dimmed={isNodeDimmed(n.id)}
              onClick={(node) => setSelected(prev => prev === node.id ? null : node.id)}
            />
          ))}
        </svg>
      </div>

      {/* Side panel */}
      <div style={{
        width: 260, borderLeft: '1px solid #21262d', padding: 20,
        background: '#0d1117', overflowY: 'auto',
      }}>
        {activeNode ? (
          <>
            <div style={{ fontSize: 9, color: '#8b949e', textTransform: 'uppercase',
                          letterSpacing: 2, marginBottom: 6 }}>
              {activeNode.type}
              {activeNode.subtype ? ` \u00b7 ${activeNode.subtype}` : ''}
            </div>
            <div style={{ fontSize: 15, fontWeight: 800,
                          color: (STYLES[activeNode.type] || STYLES.SIGNAL).bg,
                          marginBottom: 4 }}>
              {activeNode.label}
            </div>
            <div style={{ fontSize: 12, color: '#c9d1d9', lineHeight: 1.6,
                          whiteSpace: 'pre-wrap', marginBottom: 4 }}>
              {activeNode.raw.title}
            </div>
            {activeNode.occurredAt && (
              <div style={{ fontSize: 10, color: '#8b949e', marginBottom: 14 }}>
                {new Date(activeNode.occurredAt).toLocaleDateString('en-US', {
                  year: 'numeric', month: 'long', day: 'numeric',
                })}
              </div>
            )}
            {activeNode.revenueImpact != null && (
              <div style={{
                padding: '8px 10px', background: '#161b22', borderRadius: 6,
                borderLeft: `3px solid ${(STYLES[activeNode.type] || STYLES.SIGNAL).bg}`,
                marginBottom: 14,
              }}>
                <div style={{ fontSize: 13, fontWeight: 800, color: '#e6edf3' }}>
                  {fmtDollar(Math.abs(activeNode.revenueImpact))}
                </div>
                <div style={{ fontSize: 10, color: '#8b949e' }}>
                  {activeNode.revenueType || 'impact'}
                </div>
              </div>
            )}

            <div style={{ fontSize: 9, color: '#8b949e', textTransform: 'uppercase',
                          letterSpacing: 2, marginBottom: 10 }}>
              Connections ({connectedEdges.length})
            </div>
            {connectedEdges.map((e, i) => {
              const otherId = e.from === selected ? e.to : e.from;
              const other = layoutData.nodes.find(n => n.id === otherId);
              const dir = e.from === selected ? '\u2192' : '\u2190';
              return other ? (
                <div
                  key={i}
                  style={{
                    marginBottom: 10, padding: '8px 10px', background: '#161b22',
                    borderRadius: 6,
                    borderLeft: `3px solid ${(STYLES[other.type] || STYLES.SIGNAL).bg}`,
                    cursor: 'pointer',
                  }}
                  onClick={() => setSelected(otherId)}
                >
                  <div style={{ fontSize: 9, color: '#8b949e', marginBottom: 3 }}>
                    {dir} {e.label}
                  </div>
                  <div style={{ fontSize: 11, fontWeight: 700 }}>{other.raw.title}</div>
                  <div style={{ fontSize: 10, color: '#8b949e' }}>
                    {other.occurredAt
                      ? new Date(other.occurredAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                      : other.subtype || ''}
                  </div>
                </div>
              ) : null;
            })}
            <button
              onClick={() => setSelected(null)}
              style={{
                marginTop: 10, width: '100%', background: 'transparent',
                border: '1px solid #30363d', color: '#8b949e', padding: '6px 0',
                borderRadius: 6, cursor: 'pointer', fontSize: 11,
              }}
            >
              Clear Selection
            </button>
          </>
        ) : (
          <div style={{ fontSize: 12, color: '#8b949e', lineHeight: 1.7 }}>
            <div style={{ fontWeight: 800, color: '#e6edf3', marginBottom: 8, fontSize: 13 }}>
              Explore the graph
            </div>
            <div style={{ marginBottom: 6 }}>
              {layoutData.nodes.length} nodes &middot; {layoutData.edges.length} edges
            </div>
            Click any node to highlight its connections and see details.
            <RevenueSidebar revenue={revenue} />
          </div>
        )}
      </div>
    </div>
  );
};

export default ContextGraphExplorer;
