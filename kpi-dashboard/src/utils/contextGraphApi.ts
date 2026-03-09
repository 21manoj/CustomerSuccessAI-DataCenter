/**
 * Context Graph API Client
 * ========================
 * Wraps apiCall() for all context graph, story arc, and benchmark endpoints.
 */

import { apiCall } from './api';
import type {
  ContextGraphToggle,
  GraphSummaryResponse,
  GraphNodesResponse,
  CausalChainResponse,
  EgoGraphResponse,
  RevenueBreakdown,
  NodeType,
  StoryArcSummary,
  StoryArcFull,
  IndustryBenchmark,
  ContextEdgeDTO,
} from '../types/contextGraph';

// ── Feature Toggle ──

export async function fetchContextGraphToggle(): Promise<ContextGraphToggle> {
  const res = await apiCall('/api/features/context-graph');
  if (!res.ok) throw new Error(`Feature toggle fetch failed: ${res.status}`);
  return res.json();
}

// ── Graph Summary ──

export async function fetchGraphSummary(accountId: number): Promise<GraphSummaryResponse> {
  const res = await apiCall(`/api/context-graph/summary?account_id=${accountId}`);
  if (!res.ok) throw new Error(`Graph summary failed: ${res.status}`);
  return res.json();
}

// ── Graph Nodes ──

export async function fetchGraphNodes(
  accountId: number,
  nodeType?: NodeType,
  nodeSubtype?: string,
  limit: number = 100,
): Promise<GraphNodesResponse> {
  const params = new URLSearchParams({ account_id: String(accountId), limit: String(limit) });
  if (nodeType) params.set('node_type', nodeType);
  if (nodeSubtype) params.set('node_subtype', nodeSubtype);
  const res = await apiCall(`/api/context-graph/nodes?${params}`);
  if (!res.ok) throw new Error(`Graph nodes failed: ${res.status}`);
  return res.json();
}

// ── Graph Edges ──

export async function fetchGraphEdges(
  nodeId: number,
  direction: 'both' | 'incoming' | 'outgoing' = 'both',
): Promise<{ status: string; node_id: number; direction: string; count: number; edges: ContextEdgeDTO[] }> {
  const res = await apiCall(`/api/context-graph/edges/${nodeId}?direction=${direction}`);
  if (!res.ok) throw new Error(`Graph edges failed: ${res.status}`);
  return res.json();
}

// ── Causal Chain ──

export async function fetchCausalChain(
  nodeId: number,
  direction: 'upstream' | 'downstream' = 'downstream',
  maxDepth: number = 5,
): Promise<CausalChainResponse> {
  const res = await apiCall(`/api/context-graph/chain/${nodeId}?direction=${direction}&max_depth=${maxDepth}`);
  if (!res.ok) throw new Error(`Causal chain failed: ${res.status}`);
  return res.json();
}

// ── Ego Graph ──

export async function fetchEgoGraph(
  nodeId: number,
  accountId: number,
): Promise<EgoGraphResponse> {
  const res = await apiCall(`/api/context-graph/ego/${nodeId}?account_id=${accountId}`);
  if (!res.ok) throw new Error(`Ego graph failed: ${res.status}`);
  return res.json();
}

// ── Revenue Breakdown ──

export async function fetchRevenueBreakdown(accountId: number): Promise<RevenueBreakdown> {
  const res = await apiCall(`/api/context-graph/revenue?account_id=${accountId}`);
  if (!res.ok) throw new Error(`Revenue breakdown failed: ${res.status}`);
  const data = await res.json();
  return data as RevenueBreakdown;
}

// ── Story Arcs ──

export async function fetchStoryArcs(): Promise<StoryArcSummary[]> {
  const res = await apiCall('/api/story-arcs');
  if (!res.ok) throw new Error(`Story arcs failed: ${res.status}`);
  const data = await res.json();
  return data.arcs || [];
}

export async function fetchStoryArc(arcId: string): Promise<StoryArcFull> {
  const res = await apiCall(`/api/story-arcs/${arcId}`);
  if (!res.ok) throw new Error(`Story arc ${arcId} failed: ${res.status}`);
  const data = await res.json();
  return data.arc;
}

export async function fetchAccountStoryArc(accountId: number): Promise<StoryArcFull> {
  const res = await apiCall(`/api/story-arcs/account/${accountId}`);
  if (!res.ok) throw new Error(`Account story arc failed: ${res.status}`);
  const data = await res.json();
  return data.arc;
}

// ── Industry Benchmarks ──

export async function fetchIndustryBenchmarks(kpiName?: string): Promise<IndustryBenchmark[]> {
  const params = kpiName ? `?kpi_name=${encodeURIComponent(kpiName)}` : '';
  const res = await apiCall(`/api/industry-benchmarks${params}`);
  if (!res.ok) throw new Error(`Benchmarks failed: ${res.status}`);
  const data = await res.json();
  return data.benchmarks || [];
}

// ── Helper: Format currency ──

export function fmtDollar(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

export function fmtNumber(value: number): string {
  return value.toLocaleString('en-US');
}
