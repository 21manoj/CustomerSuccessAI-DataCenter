/**
 * Test Runner — Shared TypeScript interfaces and constants
 *
 * Extracted from DCTestRunner.tsx monolith.
 * Used by all tabs and sub-components.
 */

// ---------------------------------------------------------------------------
// Core Types (Scenario & Run)
// ---------------------------------------------------------------------------

export interface ScenarioMeta {
  id: string;
  name: string;
  group: string;
  description: string;
  est_minutes: number;
}

export interface ScenarioRun {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'pass' | 'fail';
  start_time: string | null;
  end_time: string | null;
  result: {
    status: string;
    message: string;
    duration_seconds: number;
    details?: Record<string, any>;
    errors?: string[];
    api_calls?: number;
    artifacts?: {
      run_dir?: string;
      test_results_md?: string;
      result_json?: string;
      csv_dir?: string;
      csv_files?: string[];
      context_graph_dir?: string;
      context_graph_files?: string[];
    };
  } | null;
  exit_code?: number;
  stdout?: string;
  stderr?: string;
}

export interface RunStatus {
  run_id: string;
  status: 'running' | 'completed';
  customer_id: string | number;
  start_time: string;
  end_time: string | null;
  scenarios: ScenarioRun[];
  summary: RunSummaryStats | null;
}

export interface RunSummaryStats {
  total: number;
  passed: number;
  failed: number;
  duration_seconds: number;
}

export interface RunSummary {
  run_id: string;
  status: string;
  customer_id: string | number;
  start_time: string;
  end_time: string | null;
  scenario_count: number;
  summary: RunSummaryStats | null;
}

// ---------------------------------------------------------------------------
// Advanced Options Types & Defaults
// ---------------------------------------------------------------------------

export interface PatternMix {
  crisis: number;
  churn: number;
  stable: number;
  expansion: number;
}

export interface PillarWeights {
  P1: number;
  P2: number;
  P3: number;
  P4: number;
  P5: number;
}

export type KpiPresetId = 'default' | 'medium' | 'minimal' | 'custom';

export interface KpiPresetDef {
  id: KpiPresetId;
  label: string;
  description: string;
  kpiCount: number;
  enabledKpis: string[];
  enabledPillars: string[];
}

export interface AdvancedOptions {
  numAccounts: number;
  dryRun: boolean;
  seed: number | null;
  industry: string;
  onboardingMode: 'demo' | 'custom';
  showcasePatternMix: PatternMix;
  weights: PillarWeights;
  // KPI Configuration
  kpiPreset: KpiPresetId;
  enabledKpis: string[];
  enabledPillars: string[];
  // Scenario 8: Context Graph
  arcId?: string;
  // Scenario 9: ROI Simulation
  months?: number;
  improvement?: number;
}

export interface RunPreset {
  label: string;
  description: string;
  numAccounts: number;
  industry: string;
  seed: number | null;
}

// ---------------------------------------------------------------------------
// Platform State Types (Tab 2)
// ---------------------------------------------------------------------------

export interface PlatformAccount {
  account_id: number;
  account_name: string;
  health_score: number | null;
  status: string;
  arr: number;
  pillar_scores: Record<string, number | null>;
  context_graph_nodes: number;
  latest_kpi_date: string | null;
}

export interface PlatformState {
  customer_id: number;
  customer_name: string;
  accounts: PlatformAccount[];
  summary: {
    total_accounts: number;
    avg_health: number | null;
    total_arr: number;
    healthy: number;
    at_risk: number;
    critical: number;
    context_graph_enabled: boolean;
    total_cg_nodes: number;
  };
}

// ---------------------------------------------------------------------------
// Analytics Types (Tab 3)
// ---------------------------------------------------------------------------

export interface StoryArc {
  arc_id: string;
  arc_name: string;
  description: string;
  target_audience: string;
  arr_start: number;
  arr_end: number;
}

export interface PowerOf1Result {
  metric_id: string;
  improvement_pct: number;
  arr_basis: number;
  annual_impact: number;
  monthly_impact: number;
  description: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const PRESETS: RunPreset[] = [
  { label: 'Quick Demo', description: '3 accounts, fast feedback', numAccounts: 3, industry: 'Technology', seed: null },
  { label: 'Standard', description: '10 accounts, balanced test', numAccounts: 10, industry: 'Technology', seed: 42 },
  { label: 'Full Load Test', description: '20 accounts, comprehensive', numAccounts: 20, industry: 'Technology', seed: 42 },
];

export const DEFAULT_PATTERN_MIX: PatternMix = { crisis: 0.15, churn: 0.15, stable: 0.50, expansion: 0.20 };
export const DEFAULT_WEIGHTS: PillarWeights = { P1: 0.15, P2: 0.20, P3: 0.25, P4: 0.15, P5: 0.25 };

export const INDUSTRIES = [
  'Technology', 'Financial Services', 'Healthcare', 'Manufacturing',
  'Retail', 'Energy', 'Telecommunications', 'Government', 'Education',
  'Media & Entertainment',
];

export const PILLAR_LABELS: Record<keyof PillarWeights, string> = {
  P1: 'Deployment Velocity', P2: 'Operational Stability', P3: 'AI Workload Performance',
  P4: 'Channel Partner Health', P5: 'Expansion Readiness',
};

// ---------------------------------------------------------------------------
// KPI Catalog — 38 KPIs across 5 pillars (from kpi_definitions.py)
// ---------------------------------------------------------------------------

export const KPI_CATALOG: Record<string, { name: string; pillar: string }> = {
  // P1: Deployment Velocity (8)
  'P1-KPI1': { name: 'Time-to-First-Workload', pillar: 'P1' },
  'P1-KPI2': { name: 'Installation Completion Rate', pillar: 'P1' },
  'P1-KPI3': { name: 'Configuration Accuracy', pillar: 'P1' },
  'P1-KPI4': { name: 'Deployment Cycle Time', pillar: 'P1' },
  'P1-KPI5': { name: 'Hardware Commissioning Time', pillar: 'P1' },
  'P1-KPI6': { name: 'Network Readiness Score', pillar: 'P1' },
  'P1-KPI7': { name: 'Deployment Team Velocity', pillar: 'P1' },
  'P1-KPI8': { name: 'Documentation Completeness', pillar: 'P1' },
  // P2: Operational Stability (8)
  'P2-KPI1': { name: 'RMA Frequency Rate', pillar: 'P2' },
  'P2-KPI2': { name: 'MTBF', pillar: 'P2' },
  'P2-KPI3': { name: 'Critical Incidents (30d)', pillar: 'P2' },
  'P2-KPI4': { name: 'System Uptime %', pillar: 'P2' },
  'P2-KPI5': { name: 'Thermal Management Score', pillar: 'P2' },
  'P2-KPI6': { name: 'Power Efficiency (PUE)', pillar: 'P2' },
  'P2-KPI7': { name: 'Mean Time To Repair', pillar: 'P2' },
  'P2-KPI8': { name: 'Preventive Maintenance', pillar: 'P2' },
  // P3: AI Workload Performance (8)
  'P3-KPI1': { name: 'GPU Utilization Rate', pillar: 'P3' },
  'P3-KPI2': { name: 'Training Job Completion', pillar: 'P3' },
  'P3-KPI3': { name: 'Inference Latency (P95)', pillar: 'P3' },
  'P3-KPI4': { name: 'Model Training Time', pillar: 'P3' },
  'P3-KPI5': { name: 'GPU Memory Efficiency', pillar: 'P3' },
  'P3-KPI6': { name: 'Distributed Training Eff.', pillar: 'P3' },
  'P3-KPI7': { name: 'Workload Diversity Score', pillar: 'P3' },
  'P3-KPI8': { name: 'Batch Processing Throughput', pillar: 'P3' },
  // P4: Channel & Partner Health (6)
  'P4-KPI1': { name: 'Partner Engagement Score', pillar: 'P4' },
  'P4-KPI2': { name: 'VAR Performance Rating', pillar: 'P4' },
  'P4-KPI3': { name: 'Joint QBR Frequency', pillar: 'P4' },
  'P4-KPI4': { name: 'Channel Conflict Score', pillar: 'P4' },
  'P4-KPI5': { name: 'Co-selling Opportunities', pillar: 'P4' },
  'P4-KPI6': { name: 'Partner NPS', pillar: 'P4' },
  // P5: Expansion Readiness (8)
  'P5-KPI1': { name: 'Capacity Utilization Rate', pillar: 'P5' },
  'P5-KPI2': { name: 'Capacity Util. Trajectory', pillar: 'P5' },
  'P5-KPI3': { name: 'Workload Growth Velocity', pillar: 'P5' },
  'P5-KPI4': { name: 'Compute Hour Trend', pillar: 'P5' },
  'P5-KPI5': { name: 'Budget Availability Signals', pillar: 'P5' },
  'P5-KPI6': { name: 'New Use Case Adoption', pillar: 'P5' },
  'P5-KPI7': { name: 'Expansion Probability (90d)', pillar: 'P5' },
  'P5-KPI8': { name: 'Technical Champion Eng.', pillar: 'P5' },
};

export const ALL_KPI_CODES = Object.keys(KPI_CATALOG);
export const ALL_PILLAR_CODES = ['P1', 'P2', 'P3', 'P4', 'P5'];

/** Minimal (12 KPIs) — maps to all 6 Power-of-1 revenue metrics */
export const MINIMAL_KPIS = [
  'P1-KPI1', // TTFV
  'P2-KPI1', // RMA → ticket_resolution_time
  'P2-KPI2', // MTBF → ticket_resolution_time
  'P2-KPI3', // Critical Incidents → ticket_resolution_time
  'P3-KPI2', // Training Job Completion → product_adoption
  'P3-KPI3', // Inference Latency → product_adoption
  'P4-KPI1', // Partner Engagement → GRR
  'P4-KPI2', // VAR Performance → GRR
  'P4-KPI3', // Joint QBR → GRR
  'P5-KPI1', // Capacity Util → expansion_rate
  'P5-KPI2', // Capacity Trajectory → NRR
  'P5-KPI3', // Workload Growth → expansion_rate
];

/** Medium (15 KPIs) — Minimal + 3 key operational KPIs */
export const MEDIUM_KPIS = [
  ...MINIMAL_KPIS,
  'P1-KPI2', // Installation Completion Rate
  'P2-KPI4', // System Uptime %
  'P3-KPI1', // GPU Utilization Rate
];

/** KPI presets for the configuration UI */
export const KPI_PRESETS: KpiPresetDef[] = [
  {
    id: 'default',
    label: 'Default',
    description: 'Full health coverage across 5 pillars',
    kpiCount: 38,
    enabledKpis: ALL_KPI_CODES,
    enabledPillars: ALL_PILLAR_CODES,
  },
  {
    id: 'medium',
    label: 'Medium',
    description: 'Broader coverage, lighter load',
    kpiCount: 15,
    enabledKpis: MEDIUM_KPIS,
    enabledPillars: ALL_PILLAR_CODES,
  },
  {
    id: 'minimal',
    label: 'Minimal',
    description: 'Power-of-1 compliant — maps all 6 revenue metrics',
    kpiCount: 12,
    enabledKpis: MINIMAL_KPIS,
    enabledPillars: ALL_PILLAR_CODES,
  },
  {
    id: 'custom',
    label: 'Custom',
    description: 'Select individual KPIs per pillar',
    kpiCount: 0, // dynamic
    enabledKpis: [],
    enabledPillars: [],
  },
];

/** Derive enabled pillars from a set of enabled KPI codes */
export function derivePillars(kpis: string[]): string[] {
  const pillars = new Set<string>();
  for (const code of kpis) {
    const entry = KPI_CATALOG[code];
    if (entry) pillars.add(entry.pillar);
  }
  return ALL_PILLAR_CODES.filter(p => pillars.has(p));
}

/** Get KPIs grouped by pillar */
export function kpisByPillar(kpis: string[]): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  for (const p of ALL_PILLAR_CODES) result[p] = [];
  for (const code of kpis) {
    const entry = KPI_CATALOG[code];
    if (entry) result[entry.pillar].push(code);
  }
  return result;
}

// DEFAULT_OPTIONS must be defined after ALL_KPI_CODES / ALL_PILLAR_CODES
export const DEFAULT_OPTIONS: AdvancedOptions = {
  numAccounts: 3,
  dryRun: false,
  seed: null,
  industry: 'Technology',
  onboardingMode: 'demo',
  showcasePatternMix: { ...DEFAULT_PATTERN_MIX },
  weights: { ...DEFAULT_WEIGHTS },
  kpiPreset: 'default',
  enabledKpis: [...ALL_KPI_CODES],
  enabledPillars: [...ALL_PILLAR_CODES],
};

export const POWER_OF_1_METRICS = [
  { id: 'NRR', label: 'Net Revenue Retention' },
  { id: 'GRR', label: 'Gross Revenue Retention' },
  { id: 'product_adoption', label: 'Product Adoption' },
  { id: 'expansion_rate', label: 'Expansion Rate' },
  { id: 'ticket_resolution_time', label: 'Ticket Resolution Time' },
  { id: 'TTFV', label: 'Time to First Value' },
];

// ---------------------------------------------------------------------------
// Customer Info (for dropdown)
// ---------------------------------------------------------------------------

export interface CustomerInfo {
  customer_id: number;
  customer_name: string;
  vertical: string;
  account_count: number;
}

// ---------------------------------------------------------------------------
// Simulation Types
// ---------------------------------------------------------------------------

export interface SimulationStatus {
  is_running: boolean;
  status: 'idle' | 'running' | 'completed' | 'stopped' | 'error';
  customer_id: number;
  current_day: number;
  num_days: number;
  current_date?: string;
  interval_seconds?: number;
  drift_profile?: string;
  kpis_injected?: number;
  last_inject_ok?: boolean;
  elapsed_seconds: number;
  error?: string | null;
  start_time?: string;
}

export const DRIFT_PROFILES = [
  { id: 'mixed', label: 'Mixed (default)', description: 'Blend of stable, expansion, churn, crisis' },
  { id: 'stable', label: 'Stable', description: 'Small noise around baseline' },
  { id: 'expansion', label: 'Expansion', description: 'Gradual improvement toward targets' },
  { id: 'churn', label: 'Churn', description: 'Gradual degradation (up to 40% drop)' },
  { id: 'crisis', label: 'Crisis', description: 'Sharp degradation (up to 70% drop)' },
];
