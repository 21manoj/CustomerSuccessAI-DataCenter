import { apiCall } from './api';

export interface VerticalOption {
  id: string;
  name: string;
  icon: string;
  description: string;
  kpiCount: number;
  categories: string[];
  sampleIndustries: string[];
}

export interface TemplateInfo {
  vertical: string;
  kpis: Array<{
    name: string;
    category: string;
    description?: string;
  }>;
}

export interface FieldMapping {
  sourceColumn: string;
  targetField: string;
  confidence: number;
  suggestions?: Array<{
    field: string;
    confidence: number;
    reason: string;
  }>;
}

export interface ProcessingStatus {
  stages: Array<{
    name: string;
    status: 'pending' | 'running' | 'complete' | 'error';
    duration?: number;
    message?: string;
  }>;
  overallProgress: number;
  recordsProcessed: number;
  errors: number;
}

export interface ImportSummary {
  customersImported: number;
  kpisProcessed: number;
  healthyAccounts: number;
  atRiskAccounts: number;
  criticalAccounts: number;
  portfolioHealth: number;
  priorityActions: number;
}

// Get available verticals — Data Center only
export const getVerticals = async (): Promise<VerticalOption[]> => {
  return [
    {
      id: 'datacenter',
      name: 'Data Center Infrastructure',
      icon: '\uD83C\uDFED',
      description: '31 KPIs across 5 pillars',
      kpiCount: 31,
      categories: [
        'Infrastructure & Performance',
        'Service Delivery',
        'Customer Sentiment',
        'Business Outcomes',
        'Relationship Strength'
      ],
      sampleIndustries: ['Colocation', 'Managed Hosting', 'Cloud Infrastructure', 'Hybrid DC']
    }
  ];
};

// Get template for Data Center vertical — mirrors kpi_definitions_dc.py (31 KPIs)
export const getTemplate = async (vertical: string): Promise<TemplateInfo> => {
  const templates: Record<string, TemplateInfo> = {
    'datacenter': {
      vertical: 'datacenter',
      kpis: [
        // Infrastructure & Performance (11 KPIs)
        { name: 'Server Uptime %', category: 'Infrastructure & Performance', description: 'Target: 99.9%' },
        { name: 'Network Latency', category: 'Infrastructure & Performance', description: 'Target: 5.0 ms' },
        { name: 'Power Utilization %', category: 'Infrastructure & Performance', description: 'Target: 70%' },
        { name: 'Rack Utilization %', category: 'Infrastructure & Performance', description: 'Target: 70%' },
        { name: 'Bandwidth Utilization %', category: 'Infrastructure & Performance', description: 'Target: 70%' },
        { name: 'Provisioning Time', category: 'Infrastructure & Performance', description: 'Target: 8 hours' },
        { name: 'Backup Success Rate %', category: 'Infrastructure & Performance', description: 'Target: 99%' },
        { name: 'Environmental Alerts', category: 'Infrastructure & Performance', description: 'Target: ≤5 count' },
        { name: 'Security Incidents', category: 'Infrastructure & Performance', description: 'Target: 0' },
        { name: 'Cooling Efficiency (PUE)', category: 'Infrastructure & Performance', description: 'Target: 1.5 ratio' },
        { name: 'Usage Growth Velocity %', category: 'Infrastructure & Performance', description: 'Target: 5%' },

        // Service Delivery (6 KPIs)
        { name: 'MTTR', category: 'Service Delivery', description: 'Target: 8 hours' },
        { name: 'Support Satisfaction', category: 'Service Delivery', description: 'Target: 4.0 score' },
        { name: 'Ticket Volume', category: 'Service Delivery', description: 'Target: ≤10 count' },
        { name: 'Customer Effort Score', category: 'Service Delivery', description: 'Target: 3.0 score' },
        { name: 'SLA Breach Count', category: 'Service Delivery', description: 'Target: 0' },
        { name: 'Remote Hands Response Time', category: 'Service Delivery', description: 'Target: 30 min' },

        // Customer Sentiment (3 KPIs)
        { name: 'NPS', category: 'Customer Sentiment', description: 'Target: 50' },
        { name: 'CSAT', category: 'Customer Sentiment', description: 'Target: 4.2 score' },
        { name: 'Complaints', category: 'Customer Sentiment', description: 'Target: ≤2 count' },

        // Business Outcomes (6 KPIs)
        { name: 'CLV', category: 'Business Outcomes', description: 'Target: 3x ARR' },
        { name: 'ROI %', category: 'Business Outcomes', description: 'Target: 200%' },
        { name: 'GRR', category: 'Business Outcomes', description: 'Target: 90%' },
        { name: 'NRR', category: 'Business Outcomes', description: 'Target: 105%' },
        { name: 'Payment Health Score', category: 'Business Outcomes', description: 'Target: 85 score' },
        { name: 'Service Breadth Score', category: 'Business Outcomes', description: 'Target: 43 score' },

        // Relationship Strength (5 KPIs)
        { name: 'QBR Frequency', category: 'Relationship Strength', description: 'Target: 4/year' },
        { name: 'Account Engagement', category: 'Relationship Strength', description: 'Target: 70 score' },
        { name: 'Executive Engagement', category: 'Relationship Strength', description: 'Target: 60 score' },
        { name: 'Renewal Probability', category: 'Relationship Strength', description: 'Target: 85%' },
        { name: 'Multi-Site Deployment', category: 'Relationship Strength', description: 'Target: 2 sites' },
      ]
    },
  };

  return templates[vertical] || templates['datacenter'];
};

// Download sample CSV template
export const downloadSampleTemplate = async (vertical: string): Promise<void> => {
  const template = await getTemplate(vertical);

  // Create CSV header
  const headers = ['Account Name', ...template.kpis.map(k => k.name)];
  const csvContent = [
    headers.join(','),
    // Add sample row with realistic DC values
    ['Sample DC Tenant', '99.95', '3.2', '72', '68', '65', '4', '99.5', '2', '0', '1.4', '8',
     '6', '4.2', '8', '2.8', '0', '25',
     '55', '4.3', '1',
     '150000', '220', '92', '108', '88', '45',
     '4', '75', '65', '88', '2'
    ].join(',')
  ].join('\n');

  // Create blob and download
  const blob = new Blob([csvContent], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `CS_Pulse_${vertical}_Template.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};

// Suggest field mappings
export const suggestFieldMappings = async (
  sourceColumns: string[],
  vertical: string
): Promise<FieldMapping[]> => {
  const template = await getTemplate(vertical);
  const targetFields = template.kpis.map(k => k.name);

  const mappings: FieldMapping[] = sourceColumns.map(sourceCol => {
    const normalizedSource = sourceCol.toLowerCase().trim();

    // Find best match
    let bestMatch = targetFields[0];
    let bestConfidence = 0;

    for (const target of targetFields) {
      const normalizedTarget = target.toLowerCase();

      // Exact match
      if (normalizedSource === normalizedTarget) {
        bestMatch = target;
        bestConfidence = 99;
        break;
      }

      // Contains match
      if (normalizedSource.includes(normalizedTarget) || normalizedTarget.includes(normalizedSource)) {
        const confidence = Math.min(95, (normalizedSource.length + normalizedTarget.length) / 2);
        if (confidence > bestConfidence) {
          bestMatch = target;
          bestConfidence = confidence;
        }
      }

      // Partial word match
      const sourceWords = normalizedSource.split(/[\s_-]+/);
      const targetWords = normalizedTarget.split(/[\s_-]+/);
      const commonWords = sourceWords.filter(w => w.length > 2 && targetWords.includes(w));
      if (commonWords.length > 0) {
        const confidence = (commonWords.length / Math.max(sourceWords.length, targetWords.length)) * 100;
        if (confidence > bestConfidence) {
          bestMatch = target;
          bestConfidence = confidence;
        }
      }
    }

    return {
      sourceColumn: sourceCol,
      targetField: bestMatch,
      confidence: Math.round(bestConfidence),
      suggestions: bestConfidence < 80 ? [
        { field: bestMatch, confidence: Math.round(bestConfidence), reason: 'Best match found' }
      ] : undefined
    };
  });

  return mappings;
};

// Upload file and get processing status
export const uploadFile = async (
  file: File,
  fieldMappings: FieldMapping[],
  sessionId: string,
  accountName?: string,
  vertical?: string
): Promise<{ uploadId: string; sessionId: string }> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('mappings', JSON.stringify(fieldMappings));
  formData.append('session_id', sessionId);

  // Pass vertical to backend for UUID generation
  if (vertical) {
    formData.append('vertical', vertical);
  }

  // Backend expects account_name for upload
  if (accountName) {
    formData.append('account_name', accountName);
  } else {
    // Extract account name from first row of CSV if available
    try {
      const text = await file.text();
      const lines = text.split(/\r?\n/).filter(line => line.trim());
      if (lines.length > 1) {
        const firstDataRow = lines[1].split(',').map(col => col.trim().replace(/^"|"$/g, ''));
        if (firstDataRow.length > 0 && firstDataRow[0]) {
          formData.append('account_name', firstDataRow[0]);
        }
      }
    } catch (e) {
      formData.append('account_name', 'DC Onboarding Import');
    }
  }

  const customerId = getCustomerId();
  const userId = getUserId();

  const response = await apiCall('/api/upload', {
    method: 'POST',
    headers: {
      ...(customerId ? { 'X-Customer-ID': customerId } : {}),
      ...(userId ? { 'X-User-ID': userId } : {})
    },
    body: formData
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: 'Failed to upload file' }));
    throw new Error(errorData.error || 'Failed to upload file');
  }

  const data = await response.json();
  return {
    uploadId: data.upload_id || sessionId,
    sessionId: sessionId
  };
};

// Get processing status from backend (falls back to simulated progress if no endpoint)
export const getProcessingStatus = async (sessionId: string): Promise<ProcessingStatus> => {
  try {
    const customerId = getCustomerId();
    const response = await apiCall(`/api/upload/status/${sessionId}`, {
      method: 'GET',
      headers: {
        ...(customerId ? { 'X-Customer-ID': customerId } : {})
      }
    });

    if (response.ok) {
      return await response.json();
    }
  } catch {
    // Backend endpoint may not exist yet — fall through to simulated progress
  }

  // Simulated completion: upload already processed synchronously on POST,
  // so report all stages complete to advance the wizard
  return {
    stages: [
      { name: 'Validating data structure', status: 'complete', duration: 800 },
      { name: 'Mapping fields to DC KPIs', status: 'complete', duration: 1200 },
      { name: 'Calculating health scores', status: 'complete', duration: 2400 },
      { name: 'Generating DC insights', status: 'complete', duration: 1800 },
      { name: 'Creating dashboard', status: 'complete', duration: 600 }
    ],
    overallProgress: 100,
    recordsProcessed: 0,
    errors: 0
  };
};

// Get import summary from backend (falls back to upload metadata if no endpoint)
export const getImportSummary = async (uploadId: string): Promise<ImportSummary> => {
  try {
    const customerId = getCustomerId();
    const response = await apiCall(`/api/upload/summary/${uploadId}`, {
      method: 'GET',
      headers: {
        ...(customerId ? { 'X-Customer-ID': customerId } : {})
      }
    });

    if (response.ok) {
      return await response.json();
    }
  } catch {
    // Backend endpoint may not exist yet — fall through to defaults
  }

  // Return zeros so the user knows no real data was returned
  return {
    customersImported: 0,
    kpisProcessed: 0,
    healthyAccounts: 0,
    atRiskAccounts: 0,
    criticalAccounts: 0,
    portfolioHealth: 0,
    priorityActions: 0
  };
};

// Helper to get customer ID
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

// Helper to get user ID
const getUserId = (): string | null => {
  try {
    const session = localStorage.getItem('session');
    if (session) {
      const parsed = JSON.parse(session);
      return String(parsed.user_id || '');
    }
  } catch (e) {
    // Ignore
  }
  return null;
};
