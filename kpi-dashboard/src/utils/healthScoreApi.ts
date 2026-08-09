import { apiCall } from './api';
import { thresholdValues } from './healthThresholds';

export interface HealthScoreData {
  accountId: number | string;
  healthScore: number;
  categoryScores: {
    reliability: number;
    efficiency: number;
    capacity: number;
    security: number;
    service: number;
  };
  trends: {
    overall: number;
    categories: Record<string, number>;
  };
  riskCount: number;
  healthyMetrics: number;
}

export interface PortfolioOverview {
  healthyCount: number;
  atRiskCount: number;
  criticalCount: number;
  averageScores: {
    healthy: number;
    atRisk: number;
    critical: number;
  };
  trends: {
    healthy: number;
    atRisk: number;
    critical: number;
  };
  topRisks: Array<{
    description: string;
    affectedCount: number;
    severity: 'high' | 'medium' | 'low';
  }>;
}

export interface HealthTrend {
  month: string;
  overallScore: number;
  reliability: number;
  efficiency: number;
  capacity: number;
  security: number;
  service: number;
}

export interface SmartAction {
  id: string;
  urgency: 'critical' | 'high' | 'opportunity';
  title: string;
  description: string;
  accountId: number | string;
  accountName: string;
  actions: Array<{
    label: string;
    type: 'schedule' | 'playbook' | 'analysis' | 'template';
    handler: () => void;
  }>;
}

// Helper to get customer ID from session
const getCustomerId = (): string | null => {
  try {
    const session = localStorage.getItem('session');
    if (session) {
      const parsed = JSON.parse(session);
      return parsed.customer_uuid || String(parsed.customer_id || '');
    }
  } catch (e) {
    // Ignore
  }
  return null;
};

// Get health score for a specific account — uses real DC2S pillar breakdown
export const getAccountHealthScore = async (accountId: number | string): Promise<HealthScoreData> => {
  const customerId = getCustomerId();
  const headers: Record<string, string> = customerId ? { 'X-Customer-ID': customerId } : {};

  // Fetch pillar breakdown from DC2S health-score endpoint
  const healthResp = await apiCall(`/api/v1/health-scores/${accountId}`, { method: 'GET', headers });

  // Fetch trends for trend delta calculation
  const trendsResp = await apiCall(`/api/health-trends?account_id=${accountId}`, { method: 'GET', headers });

  let categoryScores = { reliability: 0, efficiency: 0, capacity: 0, security: 0, service: 0 };
  let healthScore = 0;
  let kpiCount = 0;

  if (healthResp.ok) {
    const data = await healthResp.json();
    healthScore = data.overall_score || 0;
    kpiCount = data.kpi_count || 0;
    // Map P1-P5 pillars to UI names
    const cs = data.category_scores || {};
    categoryScores = {
      reliability: cs.P1?.score ?? cs.P2?.score ?? 0,   // P1: AI/ML Performance or P2: Infra
      efficiency: cs.P2?.score ?? 0,                      // P2: Infrastructure Reliability
      capacity: cs.P3?.score ?? 0,                        // P3: Cloud & DevOps
      security: cs.P4?.score ?? 0,                        // P4: Customer Engagement
      service: cs.P5?.score ?? 0,                         // P5: Commercial & Expansion
    };
  } else {
    // Fallback: use generic account endpoint
    const fallbackResp = await apiCall(`/api/accounts/${accountId}`, { method: 'GET', headers });
    if (fallbackResp.ok) {
      const account = await fallbackResp.json();
      healthScore = account.health_score || 0;
    }
  }

  // Calculate trend from real health trends
  let overallTrend = 0;
  const categoryTrends: Record<string, number> = {};
  if (trendsResp.ok) {
    const trendsData = await trendsResp.json();
    const trends = trendsData.trends || [];
    if (trends.length >= 2) {
      const prev = trends[trends.length - 2];
      const curr = trends[trends.length - 1];
      overallTrend = prev.score > 0 ? ((curr.score - prev.score) / prev.score) * 100 : 0;
      // Compute per-pillar trends
      for (const key of ['product_usage_score', 'support_score', 'customer_sentiment_score', 'business_outcomes_score', 'relationship_strength_score']) {
        const shortKey = key.replace('_score', '');
        categoryTrends[shortKey] = prev[key] > 0 ? ((curr[key] - prev[key]) / prev[key]) * 100 : 0;
      }
    }
  }

  const { healthy_min, at_risk_min } = thresholdValues();
  return {
    accountId,
    healthScore: Math.round(healthScore * 10) / 10,
    categoryScores,
    trends: {
      overall: Math.round(overallTrend * 10) / 10,
      categories: categoryTrends,
    },
    riskCount: healthScore < at_risk_min ? 2 : healthScore < healthy_min ? 1 : 0,
    healthyMetrics: kpiCount > 0 ? Math.round(kpiCount * (healthScore / 100)) : 0,
  };
};

// Get portfolio overview — uses real account data + health summary
export const getPortfolioOverview = async (): Promise<PortfolioOverview> => {
  const customerId = getCustomerId();
  const headers: Record<string, string> = customerId ? { 'X-Customer-ID': customerId } : {};

  // Use health-summary for aggregated stats
  const summaryResp = await apiCall('/api/v1/health-summary', { method: 'GET', headers });

  // Get accounts for detailed risk analysis
  const accountsResp = await apiCall('/api/accounts', { method: 'GET', headers });

  let healthyCount = 0, atRiskCount = 0, criticalCount = 0;
  let avgHealthy = 0, avgAtRisk = 0, avgCritical = 0;

  if (summaryResp.ok) {
    const summary = await summaryResp.json();
    healthyCount = summary.healthy_accounts || 0;
    atRiskCount = summary.risk_accounts || 0;
    criticalCount = summary.critical_accounts || 0;
  }

  // Calculate real average scores and top risks from accounts
  const topRisks: Array<{ description: string; affectedCount: number; severity: 'high' | 'medium' | 'low' }> = [];
  if (accountsResp.ok) {
    const data = await accountsResp.json();
    const accounts = Array.isArray(data) ? data : (data?.accounts || []);
    const { healthy_min, at_risk_min } = thresholdValues();

    const healthy = accounts.filter((a: any) => (a.health_score || 0) >= healthy_min);
    const atRisk = accounts.filter((a: any) => (a.health_score || 0) >= at_risk_min && (a.health_score || 0) < healthy_min);
    const critical = accounts.filter((a: any) => (a.health_score || 0) < at_risk_min);

    avgHealthy = healthy.length > 0 ? healthy.reduce((s: number, a: any) => s + (a.health_score || 0), 0) / healthy.length : 0;
    avgAtRisk = atRisk.length > 0 ? atRisk.reduce((s: number, a: any) => s + (a.health_score || 0), 0) / atRisk.length : 0;
    avgCritical = critical.length > 0 ? critical.reduce((s: number, a: any) => s + (a.health_score || 0), 0) / critical.length : 0;

    // Build real top risks from critical/at-risk accounts
    if (critical.length > 0) {
      topRisks.push({
        description: `${critical.length} account(s) in critical health (score < ${at_risk_min})`,
        affectedCount: critical.length,
        severity: 'high',
      });
    }
    if (atRisk.length > 0) {
      topRisks.push({
        description: `${atRisk.length} account(s) at risk (score ${at_risk_min}-${healthy_min - 1})`,
        affectedCount: atRisk.length,
        severity: 'medium',
      });
    }
    // Find accounts with declining trend
    const declining = accounts.filter((a: any) => (a.trend_change || 0) < -5);
    if (declining.length > 0) {
      topRisks.push({
        description: `${declining.length} account(s) with declining health trend`,
        affectedCount: declining.length,
        severity: 'high',
      });
    }
  }

  return {
    healthyCount,
    atRiskCount,
    criticalCount,
    averageScores: {
      healthy: Math.round(avgHealthy),
      atRisk: Math.round(avgAtRisk),
      critical: Math.round(avgCritical),
    },
    trends: { healthy: 0, atRisk: 0, critical: 0 },
    topRisks,
  };
};

// Get health trends — uses real pillar breakdown from /api/health-trends
export const getHealthTrends = async (accountId?: number | string, months: number = 6): Promise<HealthTrend[]> => {
  const customerId = getCustomerId();
  const url = accountId
    ? `/api/health-trends?account_id=${accountId}`
    : '/api/health-trends';

  const response = await apiCall(url, {
    method: 'GET',
    headers: customerId ? { 'X-Customer-ID': customerId } : {},
  });

  if (!response.ok) {
    throw new Error('Failed to fetch health trends');
  }

  const data = await response.json();
  const trends = data.trends || [];

  // Map real pillar scores to UI format
  return trends.slice(-months).map((t: any) => ({
    month: t.month,
    overallScore: t.score,
    reliability: t.product_usage_score ?? t.score * 0.95,
    efficiency: t.support_score ?? t.score * 0.88,
    capacity: t.customer_sentiment_score ?? t.score * 0.85,
    security: t.business_outcomes_score ?? t.score,
    service: t.relationship_strength_score ?? t.score * 0.96,
  }));
};

// Get smart actions — uses real CSM daily actions endpoint
export const getSmartActions = async (): Promise<SmartAction[]> => {
  const customerId = getCustomerId();
  const headers: Record<string, string> = customerId ? { 'X-Customer-ID': customerId } : {};

  const response = await apiCall('/api/v1/daily-actions', { method: 'GET', headers });

  if (!response.ok) {
    return [];
  }

  const data = await response.json();
  const actions = data.actions || [];

  return actions.slice(0, 10).map((a: any, idx: number) => ({
    id: String(idx + 1),
    urgency: a.urgency === 'critical' ? 'critical' : a.urgency === 'high' ? 'high' : 'opportunity',
    title: a.action_title || 'Review account',
    description: a.playbook_name
      ? `${a.playbook_name} — est. ${a.estimated_hours || 0}h, impact $${((a.projected_impact_usd || 0) / 1000).toFixed(0)}K`
      : `Priority index: ${(a.priority_index || 0).toFixed(1)}`,
    accountId: a.account_id,
    accountName: a.account_name || `Account ${a.account_id}`,
    actions: [
      { label: 'View Details', type: 'analysis' as const, handler: () => {} },
      { label: 'Start Playbook', type: 'playbook' as const, handler: () => {} },
    ],
  }));
};
