import { apiCall } from './api';

export interface QualityMetrics {
  overall: number; // 0-100
  completeness: {
    score: number;
    totalKpis: number;
    presentKpis: number;
  };
  accuracy: {
    score: number;
    outlierCount: number;
    validationErrors: number;
  };
  freshness: {
    score: number;
    staleAccounts: number;
    avgDaysSinceUpdate: number;
  };
  consistency: {
    score: number;
    schemaViolations: number;
    duplicates: number;
  };
  lastUpdated: Date;
  nextRefresh: Date;
}

export interface CoverageData {
  accountName: string;
  totalKpis: number;
  presentKpis: number;
  coveragePercent: number;
  missingKpis: string[];
  status: 'complete' | 'partial' | 'critical';
}

export interface Anomaly {
  id: string;
  accountName: string;
  kpiParameter: string;
  currentValue: number;
  expectedRange: [number, number];
  historicalValues: number[];
  severity: 'high' | 'medium' | 'low';
  suggestedAction: string;
  autoFixAvailable: boolean;
}

export interface PipelineStage {
  name: string;
  status: 'pending' | 'running' | 'complete' | 'error';
  duration: number; // milliseconds
  issues: {
    errors: number;
    warnings: number;
  };
}

export interface PipelineStatus {
  stages: PipelineStage[];
  recordsProcessed: number;
  recordsFailed: number;
  startTime: Date;
  endTime?: Date;
}

export interface DataLineage {
  sourceFile: string;
  sourceColumn: string;
  uploadedBy: string;
  uploadedAt: Date;
  transformations: Array<{
    step: number;
    description: string;
    before: any;
    after: any;
  }>;
  usedIn: Array<{
    calculation: string;
    impact: string;
  }>;
}

// Get overall quality metrics
export const getQualityMetrics = async (): Promise<QualityMetrics> => {
  const response = await apiCall('/api/data-quality/report', {
    method: 'GET'
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch quality metrics');
  }
  
  const data = await response.json();
  const summary = data.summary || {};
  const details = data.details || [];
  
  // Calculate overall quality score
  const totalAccounts = summary.total_accounts || 1;
  const accountsWithIssues = (summary.accounts_with_duplicates || 0) + 
                            (summary.accounts_with_out_of_range_percent || 0) +
                            (summary.accounts_with_aggregates_in_primary || 0);
  
  const overallScore = Math.max(0, 100 - (accountsWithIssues / totalAccounts) * 30);
  
  // Calculate completeness (mock for now)
  const totalKpis = details.reduce((sum: number, d: any) => sum + (d.total_kpis || 0), 0);
  const presentKpis = totalKpis * 0.96; // 96% completeness
  
  // Calculate accuracy (mock)
  const outlierCount = summary.accounts_with_out_of_range_percent || 0;
  const accuracyScore = Math.max(0, 100 - (outlierCount * 2));
  
  // Calculate freshness (mock)
  const staleAccounts = 3;
  const freshnessScore = Math.max(0, 100 - (staleAccounts * 4));
  
  // Calculate consistency
  const duplicates = summary.accounts_with_duplicates || 0;
  const consistencyScore = Math.max(0, 100 - (duplicates * 2));
  
  return {
    overall: Math.round(overallScore),
    completeness: {
      score: 96,
      totalKpis: Math.round(totalKpis),
      presentKpis: Math.round(presentKpis)
    },
    accuracy: {
      score: Math.round(accuracyScore),
      outlierCount,
      validationErrors: 0
    },
    freshness: {
      score: Math.round(freshnessScore),
      staleAccounts,
      avgDaysSinceUpdate: 2.5
    },
    consistency: {
      score: Math.round(consistencyScore),
      schemaViolations: 0,
      duplicates
    },
    lastUpdated: new Date(),
    nextRefresh: new Date(Date.now() + 22 * 60 * 60 * 1000) // 22 hours from now
  };
};

// Get coverage data
export const getCoverageData = async (): Promise<CoverageData[]> => {
  const response = await apiCall('/api/data-quality/report', {
    method: 'GET'
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch coverage data');
  }
  
  const data = await response.json();
  const details = data.details || [];
  
  // Mock coverage calculation (would come from actual KPI data)
  return details.map((detail: any, index: number) => {
    const totalKpis = 14; // Standard data center KPIs
    const presentKpis = totalKpis - (index % 5); // Vary coverage
    const coveragePercent = (presentKpis / totalKpis) * 100;
    
    return {
      accountName: detail.account_name || `Account ${detail.account_id}`,
      totalKpis,
      presentKpis,
      coveragePercent: Math.round(coveragePercent),
      missingKpis: [],
      status: coveragePercent >= 90 ? 'complete' : coveragePercent >= 50 ? 'partial' : 'critical'
    };
  });
};

// Get anomalies
export const getAnomalies = async (): Promise<Anomaly[]> => {
  // Mock data - would come from actual anomaly detection API
  return [
    {
      id: '1',
      accountName: 'Scale AI',
      kpiParameter: 'PUE',
      currentValue: 2.8,
      expectedRange: [1.4, 1.8],
      historicalValues: [1.58, 1.61, 1.59],
      severity: 'high',
      suggestedAction: 'Data entry error or sensor malfunction',
      autoFixAvailable: true
    },
    {
      id: '2',
      accountName: 'Waymo',
      kpiParameter: 'Uptime %',
      currentValue: 102,
      expectedRange: [95, 100],
      historicalValues: [99.5, 99.7, 99.6],
      severity: 'high',
      suggestedAction: 'Fix to 100%',
      autoFixAvailable: true
    },
    {
      id: '3',
      accountName: 'DeepMind',
      kpiParameter: 'Missing KPIs',
      currentValue: 15,
      expectedRange: [0, 2],
      historicalValues: [0, 0, 0],
      severity: 'medium',
      suggestedAction: 'Upload missing data',
      autoFixAvailable: false
    }
  ];
};

// Get pipeline status (mock for now)
export const getPipelineStatus = async (uploadId?: string): Promise<PipelineStatus> => {
  // Mock pipeline status
  return {
    stages: [
      { name: 'Upload', status: 'complete', duration: 2100, issues: { errors: 0, warnings: 0 } },
      { name: 'Validate', status: 'complete', duration: 800, issues: { errors: 0, warnings: 2 } },
      { name: 'Transform', status: 'complete', duration: 1200, issues: { errors: 0, warnings: 0 } },
      { name: 'Calculate', status: 'complete', duration: 1900, issues: { errors: 0, warnings: 0 } },
      { name: 'Ready', status: 'complete', duration: 0, issues: { errors: 0, warnings: 0 } }
    ],
    recordsProcessed: 490,
    recordsFailed: 0,
    startTime: new Date(Date.now() - 6000),
    endTime: new Date()
  };
};

// Get data lineage (mock for now)
export const getDataLineage = async (accountId: number, kpiParameter: string): Promise<DataLineage> => {
  return {
    sourceFile: 'datacenter_upload_2024-12-07.csv',
    sourceColumn: 'Infrastructure Uptime',
    uploadedBy: 'sarah.chen@company.com',
    uploadedAt: new Date('2024-12-07T10:30:00'),
    transformations: [
      {
        step: 1,
        description: 'Converted "99.95%" → 99.95 (float)',
        before: '99.95%',
        after: 99.95
      },
      {
        step: 2,
        description: 'Validated: 95.0 ≤ value ≤ 100.0 ✓',
        before: 99.95,
        after: 99.95
      },
      {
        step: 3,
        description: 'Stored in: kpis.data (timestamp: 2024-12-07)',
        before: 99.95,
        after: 99.95
      }
    ],
    usedIn: [
      {
        calculation: 'Reliability Score',
        impact: '94/100'
      },
      {
        calculation: 'Overall Health Score',
        impact: '92/100'
      },
      {
        calculation: 'Trend Analysis',
        impact: '+3% MoM'
      }
    ]
  };
};

