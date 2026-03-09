/**
 * NodeDetailPanel.tsx
 * ====================
 * Fixed right-side panel showing detailed info about a selected context graph node,
 * including upstream causes and downstream effects via causal chain traversal.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw,
  AlertTriangle,
  X,
  Signal,
  GitBranch,
  Target,
  Users,
  Globe,
  Building,
  ArrowDown,
  ArrowUp,
  Calendar,
  ChevronRight,
} from 'lucide-react';
import { fetchGraphNodes, fetchCausalChain, fmtDollar } from '../../../utils/contextGraphApi';
import type {
  ContextNodeDTO,
  CausalChainItem,
  NodeType,
  RevenueImpactType,
} from '../../../types/contextGraph';
import { NODE_TYPE_CONFIG, REVENUE_TYPE_CONFIG } from '../../../types/contextGraph';

interface NodeDetailPanelProps {
  nodeId: number;
  accountId: number;
  onClose: () => void;
}

const NODE_ICONS: Record<NodeType, React.FC<{ className?: string }>> = {
  SIGNAL: Signal,
  DECISION: GitBranch,
  OUTCOME: Target,
  STAKEHOLDER: Users,
  EXTERNAL_CONTEXT: Globe,
  ACCOUNT: Building,
};

// Fields to skip in properties display
const SKIP_PROPERTIES = new Set([
  'node_id', 'customer_id', 'account_id', 'node_type', 'node_subtype',
  'title', 'revenue_impact', 'revenue_impact_type', 'confidence',
  'occurred_at', 'expires_at', 'tier', 'source_platform', 'source_event_id',
]);

const NodeDetailPanel: React.FC<NodeDetailPanelProps> = ({ nodeId, accountId, onClose }) => {
  const [node, setNode] = useState<ContextNodeDTO | null>(null);
  const [upstreamChain, setUpstreamChain] = useState<CausalChainItem[]>([]);
  const [downstreamChain, setDownstreamChain] = useState<CausalChainItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch the node itself + chains in parallel
      const [nodesRes, upRes, downRes] = await Promise.all([
        fetchGraphNodes(accountId, undefined, undefined, 200),
        fetchCausalChain(nodeId, 'upstream', 4),
        fetchCausalChain(nodeId, 'downstream', 4),
      ]);

      const found = (nodesRes.nodes || []).find((n) => n.node_id === nodeId);
      setNode(found || null);
      setUpstreamChain(upRes.chain || []);
      setDownstreamChain(downRes.chain || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load node details');
    } finally {
      setLoading(false);
    }
  }, [nodeId, accountId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Close on escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const renderChainCard = (item: CausalChainItem, index: number) => {
    const chainNode = item.node;
    const nodeType = (chainNode.node_type || 'SIGNAL') as NodeType;
    const config = NODE_TYPE_CONFIG[nodeType];
    const IconComp = NODE_ICONS[nodeType] || Signal;

    return (
      <div key={`${chainNode.node_id || index}-${index}`}>
        {index > 0 && (
          <div className="flex justify-center py-1">
            <ChevronRight className="w-4 h-4 text-gray-300 rotate-90" />
          </div>
        )}
        <div className={`flex items-start gap-2 p-2.5 rounded-lg border border-gray-200 ${config.bgColor}`}>
          <IconComp className={`w-4 h-4 mt-0.5 flex-shrink-0 ${config.color}`} />
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium text-gray-800 truncate">
              {chainNode.title || 'Untitled'}
            </p>
            {chainNode.occurred_at && (
              <p className="text-xs text-gray-400 mt-0.5">
                {new Date(chainNode.occurred_at).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-white shadow-2xl border-l border-gray-200 z-50 flex flex-col animate-slide-in-right">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 bg-gray-50">
        <h3 className="text-sm font-semibold text-gray-800 truncate pr-4">
          {node?.title || 'Node Details'}
        </h3>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors"
        >
          <X className="w-4 h-4 text-gray-500" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
          </div>
        )}

        {error && (
          <div className="text-center py-8">
            <AlertTriangle className="w-6 h-6 text-yellow-500 mx-auto mb-2" />
            <p className="text-sm text-gray-600">{error}</p>
          </div>
        )}

        {!loading && !error && node && (
          <>
            {/* Type & subtype badges */}
            <div className="flex flex-wrap gap-2">
              <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${NODE_TYPE_CONFIG[node.node_type].bgColor} ${NODE_TYPE_CONFIG[node.node_type].color}`}>
                {NODE_TYPE_CONFIG[node.node_type].label}
              </span>
              {node.node_subtype && (
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                  {node.node_subtype}
                </span>
              )}
            </div>

            {/* Revenue impact */}
            {node.revenue_impact != null && node.revenue_impact !== 0 && (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 border border-gray-200">
                <div>
                  <p className="text-xs text-gray-500 mb-0.5">Revenue Impact</p>
                  <p className={`text-lg font-bold ${
                    node.revenue_impact_type === 'at_risk' ? 'text-red-600' :
                    node.revenue_impact_type === 'expansion' ? 'text-blue-600' :
                    node.revenue_impact_type === 'protected' ? 'text-green-600' :
                    'text-gray-600'
                  }`}>
                    {fmtDollar(node.revenue_impact)}
                  </p>
                </div>
                {node.revenue_impact_type && (
                  <span className={`ml-auto px-2 py-0.5 rounded-full text-xs font-medium ${REVENUE_TYPE_CONFIG[node.revenue_impact_type].bgColor} ${REVENUE_TYPE_CONFIG[node.revenue_impact_type].color}`}>
                    {REVENUE_TYPE_CONFIG[node.revenue_impact_type].label}
                  </span>
                )}
              </div>
            )}

            {/* Confidence */}
            {node.confidence != null && (
              <div>
                <p className="text-xs text-gray-500 mb-1">Confidence</p>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-blue-500 transition-all duration-300"
                      style={{ width: `${Math.min(node.confidence * 100, 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-gray-700">
                    {Math.round(node.confidence * 100)}%
                  </span>
                </div>
              </div>
            )}

            {/* Occurred at */}
            {node.occurred_at && (
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Calendar className="w-4 h-4 text-gray-400" />
                <span>{new Date(node.occurred_at).toLocaleString()}</span>
              </div>
            )}

            {/* Properties */}
            {node.properties && Object.keys(node.properties).length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Properties</p>
                <div className="space-y-1.5">
                  {Object.entries(node.properties)
                    .filter(([key]) => !SKIP_PROPERTIES.has(key))
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between items-start text-sm">
                        <span className="text-gray-500 font-medium min-w-0 truncate mr-2">
                          {key.replace(/_/g, ' ')}
                        </span>
                        <span className="text-gray-800 text-right flex-shrink-0 max-w-[180px] truncate">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Upstream causes */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <ArrowUp className="w-4 h-4 text-amber-500" />
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Upstream Causes ({upstreamChain.length})
                </p>
              </div>
              {upstreamChain.length === 0 ? (
                <p className="text-xs text-gray-400 italic">No upstream causes found</p>
              ) : (
                <div className="space-y-0">
                  {upstreamChain.map((item, idx) => renderChainCard(item, idx))}
                </div>
              )}
            </div>

            {/* Downstream effects */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <ArrowDown className="w-4 h-4 text-blue-500" />
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Downstream Effects ({downstreamChain.length})
                </p>
              </div>
              {downstreamChain.length === 0 ? (
                <p className="text-xs text-gray-400 italic">No downstream effects found</p>
              ) : (
                <div className="space-y-0">
                  {downstreamChain.map((item, idx) => renderChainCard(item, idx))}
                </div>
              )}
            </div>
          </>
        )}

        {!loading && !error && !node && (
          <div className="text-center py-8">
            <p className="text-sm text-gray-500">Node not found</p>
          </div>
        )}
      </div>

      {/* Inline animation style */}
      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
        .animate-slide-in-right {
          animation: slideInRight 0.25s ease-out;
        }
      `}</style>
    </div>
  );
};

export default NodeDetailPanel;
