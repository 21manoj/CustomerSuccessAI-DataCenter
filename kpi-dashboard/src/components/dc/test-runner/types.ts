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

export interface AdvancedOptions {
  numAccounts: number;
  dryRun: boolean;
  seed: number | null;
  industry: string;
  onboardingMode: 'demo' | 'custom';
  showcasePatternMix: PatternMix;
  weights: PillarWeights;
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
  { label: 'Full Load Test', description: '50 accounts, comprehensive', numAccounts: 50, industry: 'Technology', seed: 42 },
];

export const DEFAULT_PATTERN_MIX: PatternMix = { crisis: 0.15, churn: 0.15, stable: 0.50, expansion: 0.20 };
export const DEFAULT_WEIGHTS: PillarWeights = { P1: 0.15, P2: 0.20, P3: 0.25, P4: 0.15, P5: 0.25 };

export const DEFAULT_OPTIONS: AdvancedOptions = {
  numAccounts: 3,
  dryRun: false,
  seed: null,
  industry: 'Technology',
  onboardingMode: 'demo',
  showcasePatternMix: { ...DEFAULT_PATTERN_MIX },
  weights: { ...DEFAULT_WEIGHTS },
};

export const INDUSTRIES = [
  'Technology', 'Financial Services', 'Healthcare', 'Manufacturing',
  'Retail', 'Energy', 'Telecommunications', 'Government', 'Education',
  'Media & Entertainment',
];

export const PILLAR_LABELS: Record<keyof PillarWeights, string> = {
  P1: 'Deployment Velocity', P2: 'Operational Stability', P3: 'AI Workload Performance',
  P4: 'Channel Partner Health', P5: 'Expansion Readiness',
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
