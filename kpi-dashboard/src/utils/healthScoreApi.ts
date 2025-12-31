import { apiCall } from './api';

export interface HealthScoreData {
  accountId: number;
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
  accountId: number;
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
      return String(parsed.customer_id || '');
    }
  } catch (e) {
    // Ignore
  }
  return null;
};

// Get health score for a specific account
export const getAccountHealthScore = async (accountId: number): Promise<HealthScoreData> => {
  const customerId = getCustomerId();
  const response = await apiCall(`/api/accounts/${accountId}`, {
    method: 'GET',
    headers: customerId ? { 'X-Customer-ID': customerId } : {}
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch account health score');
  }
  
  const account = await response.json();
  
  // Get health trends for trend calculation
  const trendsResponse = await apiCall(`/api/health-trends?account_id=${accountId}`, {
    method: 'GET',
    headers: customerId ? { 'X-Customer-ID': customerId } : {}
  });
  
  const trendsData = trendsResponse.ok ? await trendsResponse.json() : { trends: [] };
  
  // Calculate category scores (mock for now - would come from actual KPI data)
  const categoryScores = {
    reliability: account.health_score ? account.health_score * 0.95 : 85,
    efficiency: account.health_score ? account.health_score * 0.88 : 80,
    capacity: account.health_score ? account.health_score * 0.85 : 75,
    security: account.health_score ? account.health_score * 1.0 : 90,
    service: account.health_score ? account.health_score * 0.96 : 88
  };
  
  // Calculate trends
  const previousMonth = trendsData.trends?.[trendsData.trends.length - 2];
  const currentMonth = trendsData.trends?.[trendsData.trends.length - 1];
  const overallTrend = previousMonth && currentMonth 
    ? ((currentMonth.score - previousMonth.score) / previousMonth.score) * 100 
    : 0;
  
  return {
    accountId: account.account_id,
    healthScore: account.health_score || 75,
    categoryScores,
    trends: {
      overall: overallTrend,
      categories: {
        reliability: 3,
        efficiency: -2,
        capacity: 0,
        security: 0,
        service: 1
      }
    },
    riskCount: account.health_score < 70 ? 2 : account.health_score < 85 ? 1 : 0,
    healthyMetrics: account.health_score > 85 ? 12 : account.health_score > 70 ? 8 : 5
  };
};

// Get portfolio overview
export const getPortfolioOverview = async (): Promise<PortfolioOverview> => {
  const customerId = getCustomerId();
  const response = await apiCall('/api/accounts', {
    method: 'GET',
    headers: customerId ? { 'X-Customer-ID': customerId } : {}
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch portfolio overview');
  }
  
  const accounts = await response.json();
  
  // Categorize accounts
  const healthy = accounts.filter((a: any) => (a.health_score || 0) >= 80);
  const atRisk = accounts.filter((a: any) => (a.health_score || 0) >= 60 && (a.health_score || 0) < 80);
  const critical = accounts.filter((a: any) => (a.health_score || 0) < 60);
  
  // Calculate averages
  const avgHealthy = healthy.length > 0 
    ? healthy.reduce((sum: number, a: any) => sum + (a.health_score || 0), 0) / healthy.length 
    : 0;
  const avgAtRisk = atRisk.length > 0 
    ? atRisk.reduce((sum: number, a: any) => sum + (a.health_score || 0), 0) / atRisk.length 
    : 0;
  const avgCritical = critical.length > 0 
    ? critical.reduce((sum: number, a: any) => sum + (a.health_score || 0), 0) / critical.length 
    : 0;
  
  // Mock top risks (would come from actual analysis)
  const topRisks = [
    { description: 'PUE > 1.6 (efficiency concern)', affectedCount: 12, severity: 'high' as const },
    { description: 'Power capacity < 15% (expansion needed)', affectedCount: 5, severity: 'medium' as const },
    { description: 'Security incidents this month', affectedCount: 3, severity: 'high' as const }
  ];
  
  return {
    healthyCount: healthy.length,
    atRiskCount: atRisk.length,
    criticalCount: critical.length,
    averageScores: {
      healthy: Math.round(avgHealthy),
      atRisk: Math.round(avgAtRisk),
      critical: Math.round(avgCritical)
    },
    trends: {
      healthy: 5,
      atRisk: -8,
      critical: 0
    },
    topRisks
  };
};

// Get health trends
export const getHealthTrends = async (accountId?: number, months: number = 6): Promise<HealthTrend[]> => {
  const customerId = getCustomerId();
  const url = accountId 
    ? `/api/health-trends?account_id=${accountId}`
    : '/api/health-trends';
  
  const response = await apiCall(url, {
    method: 'GET',
    headers: customerId ? { 'X-Customer-ID': customerId } : {}
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch health trends');
  }
  
  const data = await response.json();
  const trends = data.trends || [];
  
  // Map to expected format
  return trends.slice(-months).map((t: any) => ({
    month: t.month,
    overallScore: t.score,
    reliability: t.score * 0.95,
    efficiency: t.score * 0.88,
    capacity: t.score * 0.85,
    security: t.score * 1.0,
    service: t.score * 0.96
  }));
};

// Get smart actions
export const getSmartActions = async (): Promise<SmartAction[]> => {
  // This would come from playbook recommendations API
  // For now, return mock data
  return [
    {
      id: '1',
      urgency: 'critical',
      title: 'Schedule review with Argo AI',
      description: 'Uptime dropped to 98.5%, 3 security incidents',
      accountId: 1,
      accountName: 'Argo AI',
      actions: [
        { label: 'Schedule Meeting', type: 'schedule', handler: () => {} },
        { label: 'View Playbook', type: 'playbook', handler: () => {} }
      ]
    },
    {
      id: '2',
      urgency: 'high',
      title: 'Capacity planning for Scale AI',
      description: '82% rack utilization, trending to constraint in 3mo',
      accountId: 2,
      accountName: 'Scale AI',
      actions: [
        { label: 'Run Capacity Analysis', type: 'analysis', handler: () => {} },
        { label: 'Prepare Proposal', type: 'template', handler: () => {} }
      ]
    },
    {
      id: '3',
      urgency: 'opportunity',
      title: 'Expansion talk with DeepMind Research',
      description: 'Health score 92%, GPU utilization 78%',
      accountId: 3,
      accountName: 'DeepMind Research',
      actions: [
        { label: 'View Expansion Template', type: 'template', handler: () => {} },
        { label: 'Book QBR', type: 'schedule', handler: () => {} }
      ]
    }
  ];
};

