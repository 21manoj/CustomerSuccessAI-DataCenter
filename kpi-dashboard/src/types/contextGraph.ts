/**
 * Context Graph TypeScript Interfaces
 * ====================================
 * Types for context graph nodes, edges, story arcs, feature toggles,
 * and all API response shapes.
 */

// ── Core Enums ──

export type NodeType = 'SIGNAL' | 'STAKEHOLDER' | 'DECISION' | 'OUTCOME' | 'EXTERNAL_CONTEXT' | 'ACCOUNT';

export type EdgeType =
  | 'CAUSED_BY' | 'INDICATES' | 'LED_TO' | 'CORRELATES_WITH'
  | 'INVOLVES' | 'BELONGS_TO' | 'BENCHMARKED_BY' | 'SOURCED_FROM' | 'SUPERSEDES';

export type RevenueImpactType = 'at_risk' | 'protected' | 'expansion' | 'lost';

/**
 * Provenance vocabulary — see backend utils/provenance.py.
 *   observed  — CSV upload / SoR sync (asserted by customer)
 *   inferred  — runtime detection over real signals (signal_analyst,
 *               urgent_scanner, LLM Tier-1, push_intelligence)
 *   synthetic — arc-template fabrication (Wizard A, demo seeders)
 *
 * UI uses this to render trust badges. `synthetic` rows should carry a
 * "model-generated" badge so users don't mistake narrative scaffolding
 * for asserted facts.
 */
export type ProvenanceSource = 'observed' | 'inferred' | 'synthetic';

// ── Node & Edge DTOs ──

export interface ContextNodeDTO {
  node_id: number;
  customer_id: number;
  account_id: number;
  node_type: NodeType;
  node_subtype: string | null;
  /** Optional: qualitative_signals / wizard signals may expose sentiment (e.g. positive | negative). */
  sentiment?: string | null;
  tier: number;                    // 1=permanent, 2=decaying, 3=ephemeral
  title: string;
  properties: Record<string, any>;
  revenue_impact: number | null;
  revenue_impact_type: RevenueImpactType | null;
  confidence: number | null;
  /** Provenance — see ProvenanceSource. Optional for backwards-compat with pre-migration responses. */
  source?: ProvenanceSource;
  source_platform: string | null;
  source_event_id: string | null;
  occurred_at: string | null;      // ISO-8601
  expires_at: string | null;
}

export interface ContextEdgeDTO {
  edge_id: number;
  from_node_id: number;
  to_node_id: number;
  edge_type: EdgeType;
  weight: number | null;
  confidence: number | null;
  revenue_impact: number | null;
  revenue_impact_type: RevenueImpactType | null;
  properties: Record<string, any>;
  /** Provenance — see ProvenanceSource. */
  source?: ProvenanceSource;
  source_platform: string | null;
  created_by: string | null;
  occurred_at: string | null;
}

// ── API Response Shapes ──

export interface RevenueBreakdown {
  at_risk: number;
  protected: number;
  expansion: number;
  lost: number;
  net_impact: number;
  node_count: number;
}

export interface GraphSummaryResponse {
  status: string;
  account_id: number;
  total_nodes: number;
  total_edges: number;
  nodes_by_type: Partial<Record<NodeType, number>>;
  revenue: RevenueBreakdown;
}

export interface GraphNodesResponse {
  status: string;
  account_id: number;
  count: number;
  nodes: ContextNodeDTO[];
}

export interface CausalChainItem {
  node: Record<string, any>;  // Serialized node data
  edge: Record<string, any>;  // Serialized edge data
  depth: number;
}

export interface CausalChainResponse {
  status: string;
  node_id: number;
  direction: 'upstream' | 'downstream';
  max_depth: number;
  chain_length: number;
  chain: CausalChainItem[];
}

export interface EgoGraphResponse {
  status: string;
  center: Record<string, any>;
  nodes: ContextNodeDTO[];
  edges: ContextEdgeDTO[];
  revenue_at_risk: number;
}

// ── Feature Toggle ──

export interface ContextGraphSubToggles {
  story_arcs: boolean;
  signal_edges: boolean;
  stakeholder_tracking: boolean;
  decision_lifecycle: boolean;
  outcome_economics: boolean;
  industry_benchmarks: boolean;
}

export interface ContextGraphToggle {
  global_enabled: boolean;
  customer_enabled: boolean;
  active: boolean;
  sub_toggles: ContextGraphSubToggles;
  description: string;
  updated_at: string | null;
  status: string;
}

// ── Story Arcs ──

export interface StoryArcSummary {
  arc_id: string;
  arc_name: string;
  target_audience: 'CRO' | 'CFO' | 'CEO';
  duration_weeks: number;
  arr_start: number;
  arr_end: number;
  roi_of_intervention: number;
  num_phases: number;
  num_decisions: number;
  num_causal_chains: number;
  num_outcomes: number;
  intelligence_dimensions: string[];
}

export interface StoryArcPhase {
  phase_id: number;
  name: string;
  duration_weeks: number;
  health_range: { start: number; end: number };
  description: string;
  revenue_impact_type: string;
  plot_points: StoryArcPlotPoint[];
}

export interface StoryArcPlotPoint {
  week_offset: number;
  event_type: string;
  description: string;
  sentiment_shift: number;
  revenue_impact: number;
  generates_node_type: NodeType;
  kpi_impacts: Array<{ kpi_code: string; direction: string; magnitude: string }>;
}

export interface StoryArcCastMember {
  role: string;
  title: string;
  influence_score: number;
  sentiment_arc: number[];
  engagement_frequency: string;
  appears_in_phase: number[];
}

export interface StoryArcFull extends StoryArcSummary {
  description: string;
  revenue_narrative: {
    arr_start: number;
    arr_end: number;
    arr_at_risk_peak: number;
    roi_of_intervention: number;
    cost_of_inaction: number;
    time_horizon_weeks: number;
    intervention_cost: number;
    net_revenue_saved: number;
  };
  cast: StoryArcCastMember[];
  phases: StoryArcPhase[];
  causal_chains: Array<{
    chain_id: string;
    name: string;
    revenue_impact: number;
    links: Array<{
      from_event: string;
      to_event: string;
      edge_type: EdgeType;
      lag_weeks: number;
      confidence: number;
    }>;
  }>;
  decisions: Array<{
    decision_id: string;
    title: string;
    week: number;
    phase_id: number;
    decision_maker_role: string;
    options: Array<{ option: string; projected_impact: number; risk_level: string }>;
    chosen_option: number;
    revenue_impact: number;
    outcome_description: string;
  }>;
  outcomes: Array<{
    outcome_id: string;
    title: string;
    outcome_type: string;
    revenue_value: number;
    confidence: number;
    realized_week: number;
  }>;
  industry_benchmarks: Array<{
    kpi_code: string;
    benchmark_source: string;
    industry_p25: number;
    industry_p50: number;
    industry_p75: number;
    account_percentile: number;
  }>;
}

// ── Industry Benchmarks ──

export interface IndustryBenchmark {
  id: number;
  kpi_name: string;
  industry: string;
  company_size: string;
  percentile_25: number;
  percentile_50: number;
  percentile_75: number;
  percentile_90: number;
  sample_size: number;
  data_source: string;
  last_updated: string | null;
}

// ── UI Helpers ──

export const NODE_TYPE_CONFIG: Record<NodeType, { icon: string; color: string; bgColor: string; label: string }> = {
  SIGNAL:           { icon: 'Signal',    color: 'text-amber-600',  bgColor: 'bg-amber-50',  label: 'Signal' },
  DECISION:         { icon: 'GitBranch', color: 'text-purple-600', bgColor: 'bg-purple-50', label: 'Decision' },
  OUTCOME:          { icon: 'Target',    color: 'text-green-600',  bgColor: 'bg-green-50',  label: 'Outcome' },
  STAKEHOLDER:      { icon: 'Users',     color: 'text-blue-600',   bgColor: 'bg-blue-50',   label: 'Stakeholder' },
  EXTERNAL_CONTEXT: { icon: 'Globe',     color: 'text-gray-600',   bgColor: 'bg-gray-50',   label: 'External' },
  ACCOUNT:          { icon: 'Building',  color: 'text-slate-600',  bgColor: 'bg-slate-50',  label: 'Account' },
};

export const REVENUE_TYPE_CONFIG: Record<RevenueImpactType, { color: string; bgColor: string; label: string }> = {
  at_risk:   { color: 'text-red-700',   bgColor: 'bg-red-50',   label: 'At Risk' },
  protected: { color: 'text-green-700', bgColor: 'bg-green-50', label: 'Protected' },
  expansion: { color: 'text-blue-700',  bgColor: 'bg-blue-50',  label: 'Expansion' },
  lost:      { color: 'text-gray-700',  bgColor: 'bg-gray-50',  label: 'Lost' },
};

export const REVENUE_COLORS: Record<RevenueImpactType, string> = {
  at_risk:   '#dc2626',
  protected: '#16a34a',
  expansion: '#2563eb',
  lost:      '#6b7280',
};
