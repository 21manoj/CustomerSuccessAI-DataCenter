/**
 * useVerticalLabels — React hook for vertical-specific UI nomenclature.
 *
 * Fetches label definitions from GET /api/dc2s/config/nomenclature
 * and provides typed accessors. Customer-level overrides are automatically
 * merged server-side, so the hook always returns the final labels.
 *
 * Usage:
 *   const { labels, entity, nav, pillar, loading } = useVerticalLabels();
 *   <h1>{nav('main_dashboard')}</h1>         // "Data Center Operations Console"
 *   <span>{entity('account')}</span>          // "Tenant"
 *   <span>{pillar('P1', 'display_name')}</span> // "Deployment Velocity"
 */

import { useState, useEffect, useCallback, useMemo } from 'react';

// ─── Type Definitions ───────────────────────────────────────────────

export interface PillarLabels {
  display_name: string;
  short_code: string;
  description: string;
  icon: string;
}

export interface VerticalNomenclature {
  vertical_id: string;
  vertical_display_name: string;
  vertical_short_name: string;
  industry: string;
  entities: Record<string, string>;
  navigation: Record<string, string>;
  health_status: Record<string, string>;
  pillars: Record<string, PillarLabels>;
  playbooks: {
    section_title: string;
    pb_prefix: string;
    labels: Record<string, string>;
  };
  metrics: Record<string, string>;
  table_columns: Record<string, string>;
  search_placeholders: Record<string, string>;
  empty_states: Record<string, string>;
  actions: Record<string, string>;
  tooltips: Record<string, string>;
}

// ─── Default Fallback (generic labels) ──────────────────────────────

const DEFAULT_LABELS: VerticalNomenclature = {
  vertical_id: 'default',
  vertical_display_name: 'Customer Success',
  vertical_short_name: 'CS',
  industry: '',
  entities: {
    customer: 'Customer', customers: 'Customers',
    account: 'Account', accounts: 'Accounts',
    user: 'User', users: 'Users',
    product: 'Product', products: 'Products',
    contract: 'Contract', contracts: 'Contracts',
    renewal: 'Renewal', expansion: 'Expansion',
    churn: 'Churn Risk', onboarding: 'Onboarding',
  },
  navigation: {
    main_dashboard: 'Dashboard', executive_dashboard: 'Executive Dashboard',
    account_list: 'Accounts', account_details: 'Account Details',
    account_health: 'Account Health', product_health: 'Product Health',
    data_integration: 'Data Integration', analytics: 'Analytics',
    ai_insights: 'AI Insights', signal_analyst: 'Signal Analyst',
    playbooks: 'Playbooks', settings: 'Settings',
    roi_analysis: 'ROI Analysis', portfolio_synergy: 'Portfolio Synergy',
    journey_timeline: 'Journey Timeline', revenue_intelligence: 'Revenue Intelligence',
  },
  health_status: {
    healthy: 'Healthy', at_risk: 'At Risk', critical: 'Critical',
    healthy_description: 'On track', at_risk_description: 'Needs attention',
    critical_description: 'Urgent intervention needed',
  },
  pillars: {
    P1: { display_name: 'Pillar 1', short_code: 'P1', description: '', icon: 'circle' },
    P2: { display_name: 'Pillar 2', short_code: 'P2', description: '', icon: 'circle' },
    P3: { display_name: 'Pillar 3', short_code: 'P3', description: '', icon: 'circle' },
    P4: { display_name: 'Pillar 4', short_code: 'P4', description: '', icon: 'circle' },
    P5: { display_name: 'Pillar 5', short_code: 'P5', description: '', icon: 'circle' },
  },
  playbooks: { section_title: 'Playbooks', pb_prefix: 'PB', labels: {} },
  metrics: {
    arr: 'ARR', mrr: 'MRR', nps: 'NPS', csat: 'CSAT',
    csm: 'CSM', health_score: 'Health Score', revenue: 'Revenue',
    ttfv: 'Time to Value', nrr: 'NRR', grr: 'GRR',
  },
  table_columns: {
    name: 'Name', health: 'Health Score', region: 'Region',
    industry: 'Industry', status: 'Status', csm: 'CSM',
    arr: 'ARR', contract_end: 'Contract End', last_activity: 'Last Activity',
  },
  search_placeholders: {
    account_search: 'Search...', kpi_search: 'Search KPIs...',
    playbook_search: 'Search playbooks...',
  },
  empty_states: {
    no_accounts: 'No Data Found', no_kpis: 'No KPI Data',
    no_playbooks: 'No Active Playbooks', no_signals: 'No Signals',
  },
  actions: {
    add_account: 'Add', edit_account: 'Edit', view_details: 'View Details',
    run_playbook: 'Run Playbook', upload_data: 'Upload', export_report: 'Export',
    calibrate_weights: 'Calibrate Weights',
  },
  tooltips: {
    health_score: 'Weighted composite health score (0-100)',
    expansion_probability: 'Predicted expansion probability in next 90 days',
    churn_risk: 'Risk of non-renewal based on current signals',
    pillar_weight: 'Relative importance of this pillar',
  },
};

// ─── Cache (module-level singleton) ─────────────────────────────────

let _cache: VerticalNomenclature | null = null;
let _cacheVertical: string | null = null;
let _fetchPromise: Promise<VerticalNomenclature> | null = null;

async function fetchLabels(vertical?: string): Promise<VerticalNomenclature> {
  const qs = vertical ? `?vertical=${encodeURIComponent(vertical)}` : '';
  const url = `/api/dc2s/config/nomenclature${qs}`;

  if (_cache && _cacheVertical === (vertical || 'auto')) {
    return _cache;
  }

  if (_fetchPromise) return _fetchPromise;

  _fetchPromise = fetch(url, { credentials: 'include' })
    .then(async (res) => {
      if (!res.ok) return DEFAULT_LABELS;
      const data = await res.json();
      const merged: VerticalNomenclature = { ...DEFAULT_LABELS, ...data };
      _cache = merged;
      _cacheVertical = vertical || 'auto';
      return merged;
    })
    .catch(() => DEFAULT_LABELS)
    .finally(() => { _fetchPromise = null; });

  return _fetchPromise;
}

/** Invalidate the cached nomenclature (call after customer saves overrides). */
export function invalidateNomenclatureCache(): void {
  _cache = null;
  _cacheVertical = null;
}

// ─── Hook ───────────────────────────────────────────────────────────

export interface UseVerticalLabelsResult {
  labels: VerticalNomenclature;
  loading: boolean;
  error: string | null;

  /** Get entity label: entity('account') → "Tenant" */
  entity: (key: string) => string;

  /** Get navigation label: nav('main_dashboard') → "Data Center Operations Console" */
  nav: (key: string) => string;

  /** Get pillar field: pillar('P1', 'display_name') → "Deployment Velocity" */
  pillar: (pillarCode: string, field?: keyof PillarLabels) => string;

  /** Get health status label: status('healthy') → "HEALTHY" */
  status: (key: string) => string;

  /** Get playbook label: playbook('PB-01') → "Deployment Acceleration" */
  playbook: (code: string) => string;

  /** Get metric label: metric('nrr') → "Net Revenue Retention" */
  metric: (key: string) => string;

  /** Get table column header: column('name') → "Tenant Name" */
  column: (key: string) => string;

  /** Get action label: action('add_account') → "Add Tenant" */
  action: (key: string) => string;

  /** Get tooltip: tooltip('health_score') → "Weighted composite..." */
  tooltip: (key: string) => string;

  /** Get search placeholder: search('account_search') → "Search tenants..." */
  search: (key: string) => string;

  /** Get empty state message: empty('no_accounts') → "No Tenants Found" */
  empty: (key: string) => string;
}

export function useVerticalLabels(vertical?: string): UseVerticalLabelsResult {
  const [labels, setLabels] = useState<VerticalNomenclature>(_cache || DEFAULT_LABELS);
  const [loading, setLoading] = useState(!_cache);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchLabels(vertical)
      .then((data) => {
        if (!cancelled) {
          setLabels(data);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message);
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [vertical]);

  // Memoized accessors
  const entity = useCallback((key: string) => labels.entities[key] || key, [labels]);
  const nav = useCallback((key: string) => labels.navigation[key] || key, [labels]);
  const pillar = useCallback(
    (code: string, f: keyof PillarLabels = 'display_name') =>
      labels.pillars[code]?.[f] || code,
    [labels],
  );
  const status = useCallback((key: string) => labels.health_status[key] || key, [labels]);
  const playbook = useCallback(
    (code: string) => labels.playbooks.labels[code] || code,
    [labels],
  );
  const metric = useCallback((key: string) => labels.metrics[key] || key, [labels]);
  const column = useCallback((key: string) => labels.table_columns[key] || key, [labels]);
  const action = useCallback((key: string) => labels.actions[key] || key, [labels]);
  const tooltip = useCallback((key: string) => labels.tooltips[key] || key, [labels]);
  const search = useCallback((key: string) => labels.search_placeholders[key] || key, [labels]);
  const empty = useCallback((key: string) => labels.empty_states[key] || key, [labels]);

  return useMemo(() => ({
    labels, loading, error,
    entity, nav, pillar, status, playbook, metric, column, action, tooltip, search, empty,
  }), [labels, loading, error, entity, nav, pillar, status, playbook, metric, column, action, tooltip, search, empty]);
}

export default useVerticalLabels;
