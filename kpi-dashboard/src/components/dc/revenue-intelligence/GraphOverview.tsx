/**
 * GraphOverview.tsx
 * =================
 * Shows graph summary metrics, node-type and revenue breakdowns as charts,
 * and a lane diagram of all context graph nodes organized by type.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw,
  AlertTriangle,
  Activity,
  GitBranch,
  DollarSign,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { fetchGraphSummary, fetchGraphNodes, fmtDollar, fmtNumber } from '../../../utils/contextGraphApi';
import type {
  GraphSummaryResponse,
  ContextNodeDTO,
  NodeType,
  RevenueImpactType,
} from '../../../types/contextGraph';
import { NODE_TYPE_CONFIG, REVENUE_COLORS } from '../../../types/contextGraph';
import NodeDetailPanel from './NodeDetailPanel';

interface GraphOverviewProps {
  accountId: number;
}

const NODE_TYPE_CHART_COLORS: Record<string, string> = {
  SIGNAL: '#d97706',
  SIGNAL_SYSTEM: '#06B6D4',
  DECISION: '#9333ea',
  OUTCOME: '#16a34a',
  STAKEHOLDER: '#2563eb',
  EXTERNAL_CONTEXT: '#6b7280',
  ACCOUNT: '#475569',
};

const NODE_TYPE_LABELS: Record<string, string> = {
  SIGNAL: 'Signal',
  SIGNAL_SYSTEM: 'System Signal',
  DECISION: 'Decision',
  OUTCOME: 'Outcome',
  STAKEHOLDER: 'Stakeholder',
  EXTERNAL_CONTEXT: 'External',
  ACCOUNT: 'Account',
};

const GraphOverview: React.FC<GraphOverviewProps> = ({ accountId }) => {
  const [summary, setSummary] = useState<GraphSummaryResponse | null>(null);
  const [nodes, setNodes] = useState<ContextNodeDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, nodesData] = await Promise.all([
        fetchGraphSummary(accountId),
        fetchGraphNodes(accountId, undefined, undefined, 200),
      ]);
      setSummary(summaryData);
      setNodes(nodesData.nodes || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load graph data');
    } finally {
      setLoading(false);
    }
  }, [accountId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

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

  if (!summary) return null;

  const revenue = summary.revenue;

  // Prepare chart data — split SIGNAL into user-uploaded vs system-generated
  const nodeTypeDataRaw: Record<string, number> = {};
  for (const n of nodes) {
    const src = (n as any).source;
    const isSys = n.node_type === 'SIGNAL' && (
      src === 'system' || n.node_subtype === 'arc_detection' || n.properties?.triggered_by
    );
    const key = isSys ? 'SIGNAL_SYSTEM' : n.node_type;
    nodeTypeDataRaw[key] = (nodeTypeDataRaw[key] || 0) + 1;
  }
  for (const [type, count] of Object.entries(summary.nodes_by_type || {})) {
    if (type !== 'SIGNAL' && !nodeTypeDataRaw[type]) {
      nodeTypeDataRaw[type] = count || 0;
    }
  }
  const nodeTypeData = Object.entries(nodeTypeDataRaw).map(([type, count]) => ({
    type: NODE_TYPE_LABELS[type] || NODE_TYPE_CONFIG[type as NodeType]?.label || type,
    count: count || 0,
    fill: NODE_TYPE_CHART_COLORS[type] || '#6b7280',
  }));

  const revenueData = [
    { label: 'At Risk', value: Math.abs(revenue.at_risk), fill: REVENUE_COLORS.at_risk },
    { label: 'Protected', value: revenue.protected, fill: REVENUE_COLORS.protected },
    { label: 'Expansion', value: revenue.expansion, fill: REVENUE_COLORS.expansion },
    { label: 'Lost', value: Math.abs(revenue.lost), fill: REVENUE_COLORS.lost },
  ];

  // Group nodes by type for lanes
  const laneTypes: NodeType[] = ['SIGNAL', 'DECISION', 'OUTCOME', 'STAKEHOLDER'];
  const nodesByType: Record<string, ContextNodeDTO[]> = {};
  for (const nt of laneTypes) {
    nodesByType[nt] = nodes
      .filter((n) => n.node_type === nt)
      .sort((a, b) => {
        const dateA = a.occurred_at ? new Date(a.occurred_at).getTime() : 0;
        const dateB = b.occurred_at ? new Date(b.occurred_at).getTime() : 0;
        return dateA - dateB;
      });
  }

  const truncate = (text: string, maxLen: number) =>
    text.length > maxLen ? text.slice(0, maxLen) + '...' : text;

  return (
    <div className="space-y-6 relative max-w-full overflow-hidden">
      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-blue-50 rounded-lg">
              <Activity className="w-5 h-5 text-blue-600" />
            </div>
            <span className="text-sm font-medium text-gray-500">Total Nodes</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{fmtNumber(summary.total_nodes)}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-purple-50 rounded-lg">
              <GitBranch className="w-5 h-5 text-purple-600" />
            </div>
            <span className="text-sm font-medium text-gray-500">Total Edges</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{fmtNumber(summary.total_edges)}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-red-50 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <span className="text-sm font-medium text-gray-500">Revenue at Risk</span>
          </div>
          <p className="text-2xl font-bold text-red-600">{fmtDollar(Math.abs(revenue.at_risk))}</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-green-50 rounded-lg">
              <DollarSign className="w-5 h-5 text-green-600" />
            </div>
            <span className="text-sm font-medium text-gray-500">Net Impact</span>
          </div>
          <p className={`text-2xl font-bold ${revenue.net_impact >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {fmtDollar(revenue.net_impact)}
          </p>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Node type breakdown */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Node Type Breakdown</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={nodeTypeData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="type" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                formatter={(value: number) => [fmtNumber(value), 'Count']}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {nodeTypeData.map((entry, idx) => (
                  <Cell key={idx} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Revenue waterfall */}
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Revenue Breakdown</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={revenueData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => fmtDollar(v)} />
              <Tooltip
                contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                formatter={(value: number) => [fmtDollar(value), 'Revenue']}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {revenueData.map((entry, idx) => (
                  <Cell key={idx} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Lane diagram */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Context Graph Lanes</h3>
        <div className="space-y-4">
          {laneTypes.map((laneType) => {
            const config = NODE_TYPE_CONFIG[laneType];
            const laneNodes = nodesByType[laneType] || [];
            const borderColor =
              laneType === 'SIGNAL' ? 'border-l-amber-500' :
              laneType === 'DECISION' ? 'border-l-purple-500' :
              laneType === 'OUTCOME' ? 'border-l-green-500' :
              'border-l-blue-500';

            return (
              <div
                key={laneType}
                className={`border-l-4 ${borderColor} bg-gray-50 rounded-r-lg p-4`}
              >
                <div className="flex items-center gap-2 mb-3">
                  <span className={`text-xs font-bold uppercase tracking-wider ${config.color}`}>
                    {config.label}
                  </span>
                  <span className="text-xs text-gray-400">({laneNodes.length})</span>
                </div>

                {laneNodes.length === 0 ? (
                  <p className="text-xs text-gray-400 italic">No {config.label.toLowerCase()} nodes</p>
                ) : (
                  <div className="flex gap-3 overflow-x-auto pb-2 min-w-0">
                    {laneNodes.map((node) => {
                      const src = (node as any).source;
                      const isSysNode = node.node_type === 'SIGNAL' && (
                        src === 'system' || node.node_subtype === 'arc_detection' || node.properties?.triggered_by
                      );
                      return (
                      <button
                        key={node.node_id}
                        onClick={() => setSelectedNodeId(node.node_id)}
                        className={`flex-shrink-0 rounded-lg border p-3 text-left transition-all hover:shadow-md min-w-[180px] max-w-[220px] ${
                          selectedNodeId === node.node_id ? 'ring-2 ring-blue-500 border-blue-400' : 'border-gray-200'
                        } ${isSysNode ? 'bg-cyan-50 border-cyan-300 border-dashed hover:border-cyan-400' : 'bg-white hover:border-blue-300'}`}
                      >
                        {isSysNode && (
                          <span className="text-[9px] font-bold uppercase tracking-wider text-cyan-600 bg-cyan-100 px-1.5 py-0.5 rounded mb-1 inline-block">
                            System
                          </span>
                        )}
                        <p className="text-sm font-medium text-gray-800 leading-tight">
                          {truncate(node.title, 40)}
                        </p>
                        {node.occurred_at && (
                          <p className="text-xs text-gray-400 mt-1">
                            {new Date(node.occurred_at).toLocaleDateString()}
                          </p>
                        )}
                        {node.revenue_impact != null && node.revenue_impact !== 0 && (
                          <span
                            className={`inline-block mt-1.5 text-xs font-semibold px-2 py-0.5 rounded-full ${
                              node.revenue_impact_type === 'at_risk'
                                ? 'bg-red-100 text-red-700'
                                : node.revenue_impact_type === 'expansion'
                                ? 'bg-blue-100 text-blue-700'
                                : node.revenue_impact_type === 'protected'
                                ? 'bg-green-100 text-green-700'
                                : 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            {fmtDollar(node.revenue_impact)}
                          </span>
                        )}
                      </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Node detail panel */}
      {selectedNodeId !== null && (
        <NodeDetailPanel
          nodeId={selectedNodeId}
          accountId={accountId}
          onClose={() => setSelectedNodeId(null)}
        />
      )}
    </div>
  );
};

export default GraphOverview;
