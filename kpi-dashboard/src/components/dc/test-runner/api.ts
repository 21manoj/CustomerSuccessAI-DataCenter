/**
 * Test Runner — API helper module
 *
 * Centralized fetch calls for all Test Runner tabs.
 * Uses typed responses from ./types.ts.
 */

import type {
  ScenarioMeta,
  AdvancedOptions,
  RunStatus,
  RunSummary,
  PlatformState,
  StoryArc,
  PowerOf1Result,
  CustomerInfo,
  SimulationStatus,
} from './types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

export function formatDuration(seconds: number): string {
  if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  return `${(seconds / 60).toFixed(1)}m`;
}

export function formatTime(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleTimeString();
}

/** Format dollar amounts with K/M suffixes */
export function formatDollars(amount: number): string {
  if (Math.abs(amount) >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
  if (Math.abs(amount) >= 1_000) return `$${(amount / 1_000).toFixed(0)}K`;
  return `$${amount.toFixed(0)}`;
}

// ---------------------------------------------------------------------------
// Existing Test Runner API
// ---------------------------------------------------------------------------

export const testRunnerApi = {
  async getScenarios(): Promise<ScenarioMeta[]> {
    const res = await fetch('/api/test-runner/scenarios', { credentials: 'include' });
    const data = await res.json();
    return data.scenarios || [];
  },

  async startRun(
    scenarioIds: string[],
    customerId: string | number,
    options?: AdvancedOptions,
  ): Promise<{ run_id: string }> {
    const body: Record<string, any> = {
      scenario_ids: scenarioIds,
      customer_id: customerId,
    };

    if (options) {
      body.options = {
        num_accounts: options.numAccounts,
        dry_run: options.dryRun,
        seed: options.seed,
        industry: options.industry,
        onboarding_mode: options.onboardingMode,
        showcase_pattern_mix: options.showcasePatternMix,
        weights: options.weights,
        // Scenario 8: Context Graph
        ...(options.arcId ? { arc_id: options.arcId } : {}),
        // Scenario 9: ROI Simulation
        ...(options.months ? { months: options.months } : {}),
        ...(options.improvement ? { improvement: options.improvement } : {}),
      };
    }

    const res = await fetch('/api/test-runner/start', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Failed to start run');
    }
    return res.json();
  },

  async getStatus(runId: string): Promise<RunStatus> {
    const res = await fetch(`/api/test-runner/status/${runId}`, { credentials: 'include' });
    return res.json();
  },

  async getRuns(): Promise<RunSummary[]> {
    const res = await fetch('/api/test-runner/runs', { credentials: 'include' });
    const data = await res.json();
    return data.runs || [];
  },

  async deleteRun(runId: string): Promise<void> {
    await fetch(`/api/test-runner/runs/${runId}`, { method: 'DELETE', credentials: 'include' });
  },

  async getCustomers(): Promise<CustomerInfo[]> {
    const res = await fetch('/api/test-runner/customers', { credentials: 'include' });
    if (!res.ok) return [];
    const data = await res.json();
    return data.customers || [];
  },
};

// ---------------------------------------------------------------------------
// Platform State API (Tab 2)
// ---------------------------------------------------------------------------

export const platformApi = {
  async getState(customerId: string | number): Promise<PlatformState> {
    const res = await fetch(`/api/test-runner/platform-state?customer_id=${customerId}`, {
      credentials: 'include',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Failed to fetch platform state' }));
      throw new Error(err.error || 'Failed to fetch platform state');
    }
    return res.json();
  },

  async getStoryArcs(): Promise<StoryArc[]> {
    const res = await fetch('/api/test-runner/story-arcs', { credentials: 'include' });
    if (!res.ok) return [];
    const data = await res.json();
    return data.arcs || [];
  },
};

// ---------------------------------------------------------------------------
// Analytics API (Tab 3) — wraps existing endpoints with X-Customer-ID
// ---------------------------------------------------------------------------

export const analyticsApi = {
  async getPortfolioROI(customerId: string | number): Promise<any> {
    const res = await fetch('/api/outcome-roi/story', {
      credentials: 'include',
      headers: { 'X-Customer-ID': String(customerId) },
    });
    if (!res.ok) throw new Error('Failed to fetch ROI story');
    return res.json();
  },

  async getPowerOf1(
    customerId: string | number,
    metricId: string,
    improvementPct: number = 1.0,
    accountArr?: number,
  ): Promise<PowerOf1Result> {
    const params = new URLSearchParams({
      customer_id: String(customerId),
      metric_id: metricId,
      improvement_pct: String(improvementPct),
    });
    if (accountArr) params.set('account_arr', String(accountArr));

    const res = await fetch(`/api/test-runner/power-of-1?${params}`, {
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Failed to calculate Power-of-1');
    return res.json();
  },

  async getRevenueAtRisk(customerId: string | number, accountId: number): Promise<any> {
    const res = await fetch(`/api/context-graph/revenue?account_id=${accountId}`, {
      credentials: 'include',
      headers: { 'X-Customer-ID': String(customerId) },
    });
    if (!res.ok) throw new Error('Failed to fetch revenue at risk');
    return res.json();
  },

  async getDailyActions(customerId: string | number): Promise<any> {
    const res = await fetch('/api/dc2s/daily-actions', {
      credentials: 'include',
      headers: { 'X-Customer-ID': String(customerId) },
    });
    if (!res.ok) throw new Error('Failed to fetch daily actions');
    return res.json();
  },
};

// ---------------------------------------------------------------------------
// Data Ops API (Tab 4) — wraps existing ingestion endpoints
// ---------------------------------------------------------------------------

export const dataOpsApi = {
  async pushKPIs(
    customerId: string | number,
    kpis: Array<{
      account_id: number;
      kpi_code: string;
      measured_at: string;
      value: number;
      target: number;
    }>,
  ): Promise<any> {
    const res = await fetch('/api/data-ingestion/kpis', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-Customer-ID': String(customerId),
      },
      body: JSON.stringify({ kpis }),
    });
    if (!res.ok) throw new Error('Failed to push KPIs');
    return res.json();
  },

  async pushSignals(
    customerId: string | number,
    signals: Array<{
      account_id: number;
      signal_date: string;
      signal_type: string;
      content: string;
      severity: string;
    }>,
  ): Promise<any> {
    const res = await fetch('/api/data-ingestion/signals', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-Customer-ID': String(customerId),
      },
      body: JSON.stringify({ signals }),
    });
    if (!res.ok) throw new Error('Failed to push signals');
    return res.json();
  },

  async recalculateScores(
    customerId: string | number,
    month?: string,
  ): Promise<any> {
    const body: Record<string, any> = {};
    if (month) body.month = month;

    const res = await fetch('/api/dc2s/scores/calculate', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-Customer-ID': String(customerId),
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error('Failed to recalculate scores');
    return res.json();
  },
};

// ---------------------------------------------------------------------------
// Simulation API (continuous KPI injection)
// ---------------------------------------------------------------------------

export const simulationApi = {
  async start(
    customerId: string | number,
    intervalSeconds: number = 10,
    numDays: number = 90,
    driftProfile: string = 'mixed',
  ): Promise<any> {
    const res = await fetch('/api/test-runner/simulate/start', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        customer_id: customerId,
        interval_seconds: intervalSeconds,
        num_days: numDays,
        drift_profile: driftProfile,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Failed to start simulation' }));
      throw new Error(err.error || 'Failed to start simulation');
    }
    return res.json();
  },

  async stop(customerId: string | number): Promise<any> {
    const res = await fetch('/api/test-runner/simulate/stop', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_id: customerId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Failed to stop simulation' }));
      throw new Error(err.error || 'Failed to stop simulation');
    }
    return res.json();
  },

  async status(customerId: string | number): Promise<SimulationStatus> {
    const res = await fetch(`/api/test-runner/simulate/status?customer_id=${customerId}`, {
      credentials: 'include',
    });
    if (!res.ok) {
      return { is_running: false, status: 'idle', customer_id: Number(customerId), current_day: 0, num_days: 0, elapsed_seconds: 0 };
    }
    return res.json();
  },
};
