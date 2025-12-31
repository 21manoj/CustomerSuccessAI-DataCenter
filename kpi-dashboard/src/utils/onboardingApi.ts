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

// Get available verticals
export const getVerticals = async (): Promise<VerticalOption[]> => {
  // Use the actual SaaS Customer Success framework
  return [
    {
      id: 'saas-customer-success',
      name: 'SaaS Customer Success',
      icon: '🚀',
      description: '59 KPIs across 5 pillars',
      kpiCount: 59,
      categories: ['Product Usage KPI', 'Support KPI', 'Customer Sentiment KPI', 'Business Outcomes KPI', 'Relationship Strength KPI'],
      sampleIndustries: ['SaaS', 'Software', 'Technology', 'Cloud Services']
    }
  ];
};

// Get template for a vertical
export const getTemplate = async (vertical: string): Promise<TemplateInfo> => {
  // Use the actual 59 KPI / 5 Pillar SaaS framework
  const templates: Record<string, TemplateInfo> = {
    'saas-customer-success': {
      vertical: 'saas-customer-success',
      kpis: [
        // Product Usage KPI (14 KPIs)
        { name: 'Time to First Value (TTFV)', category: 'Product Usage KPI' },
        { name: 'Onboarding Completion Rate', category: 'Product Usage KPI' },
        { name: 'Product Activation Rate', category: 'Product Usage KPI' },
        { name: 'Customer Onboarding Satisfaction (CSAT)', category: 'Product Usage KPI' },
        { name: 'Support Requests During Onboarding', category: 'Product Usage KPI' },
        { name: 'Customer Retention Rate', category: 'Product Usage KPI' },
        { name: 'Churn Rate (inverse)', category: 'Product Usage KPI' },
        { name: 'Share of Wallet', category: 'Product Usage KPI' },
        { name: 'Employee Productivity (customer usage patterns)', category: 'Product Usage KPI' },
        { name: 'Operational Efficiency (platform utilization)', category: 'Product Usage KPI' },
        { name: 'Feature Adoption Rate', category: 'Product Usage KPI' },
        { name: 'Training Participation Rate', category: 'Product Usage KPI' },
        { name: 'Knowledge Base Usage', category: 'Product Usage KPI' },
        { name: 'Learning Path Completion Rate', category: 'Product Usage KPI' },
        
        // Support KPI (11 KPIs)
        { name: 'First Response Time', category: 'Support KPI' },
        { name: 'Mean Time to Resolution (MTTR)', category: 'Support KPI' },
        { name: 'Customer Support Satisfaction', category: 'Support KPI' },
        { name: 'Ticket Volume', category: 'Support KPI' },
        { name: 'Ticket Backlog', category: 'Support KPI' },
        { name: 'First Contact Resolution (FCR)', category: 'Support KPI' },
        { name: 'Escalation Rate', category: 'Support KPI' },
        { name: 'Support Cost per Ticket', category: 'Support KPI' },
        { name: 'Case Deflection Rate', category: 'Support KPI' },
        { name: 'Customer Effort Score (CES)', category: 'Support KPI' },
        { name: 'Process Cycle Time', category: 'Support KPI' },
        
        // Customer Sentiment KPI (5 KPIs)
        { name: 'Net Promoter Score (NPS)', category: 'Customer Sentiment KPI' },
        { name: 'Customer Satisfaction (CSAT)', category: 'Customer Sentiment KPI' },
        { name: 'Customer Complaints', category: 'Customer Sentiment KPI' },
        { name: 'Error Rates (affecting customer experience)', category: 'Customer Sentiment KPI' },
        { name: 'Customer sentiment Trends', category: 'Customer Sentiment KPI' },
        
        // Business Outcomes KPI (19 KPIs)
        { name: 'Revenue Growth', category: 'Business Outcomes KPI' },
        { name: 'Customer Lifetime Value (CLV)', category: 'Business Outcomes KPI' },
        { name: 'Upsell and Cross-sell Revenue', category: 'Business Outcomes KPI' },
        { name: 'Cost Savings', category: 'Business Outcomes KPI' },
        { name: 'Return on Investment (ROI)', category: 'Business Outcomes KPI' },
        { name: 'Days Sales Outstanding (DSO)', category: 'Business Outcomes KPI' },
        { name: 'Accounts Receivable Turnover', category: 'Business Outcomes KPI' },
        { name: 'Cash Conversion Cycle (CCC)', category: 'Business Outcomes KPI' },
        { name: 'Invoice Accuracy', category: 'Business Outcomes KPI' },
        { name: 'Payment Terms Compliance', category: 'Business Outcomes KPI' },
        { name: 'Collection Effectiveness Index (CEI)', category: 'Business Outcomes KPI' },
        { name: 'Gross Revenue Retention (GRR)', category: 'Business Outcomes KPI' },
        { name: 'Net Revenue Retention (NRR)', category: 'Business Outcomes KPI' },
        { name: 'Renewal Rate', category: 'Business Outcomes KPI' },
        { name: 'Expansion Revenue Rate', category: 'Business Outcomes KPI' },
        { name: 'Churn by Segment/Persona/Product', category: 'Business Outcomes KPI' },
        { name: 'Key Performance Indicators (KPIs)', category: 'Business Outcomes KPI' },
        { name: 'Operational Cost Savings', category: 'Business Outcomes KPI' },
        { name: 'Cost per Unit', category: 'Business Outcomes KPI' },
        
        // Relationship Strength KPI (10 KPIs)
        { name: 'Business Review Frequency', category: 'Relationship Strength KPI' },
        { name: 'Account Engagement Score', category: 'Relationship Strength KPI' },
        { name: 'Churn Risk Flags Triggered', category: 'Relationship Strength KPI' },
        { name: 'Service Level Agreements (SLAs) compliance', category: 'Relationship Strength KPI' },
        { name: 'On-time Delivery Rates', category: 'Relationship Strength KPI' },
        { name: 'Benchmarking Results', category: 'Relationship Strength KPI' },
        { name: 'Regulatory Compliance', category: 'Relationship Strength KPI' },
        { name: 'Audit Results', category: 'Relationship Strength KPI' },
        { name: 'Cross-functional Task Completion', category: 'Relationship Strength KPI' },
        { name: 'Process Improvement Velocity', category: 'Relationship Strength KPI' }
      ]
    },
  };

  return templates[vertical] || templates['saas-customer-success'];
};

// Download sample CSV template
export const downloadSampleTemplate = async (vertical: string): Promise<void> => {
  const template = await getTemplate(vertical);
  
  // Create CSV header
  const headers = ['Account Name', ...template.kpis.map(k => k.name)];
  const csvContent = [
    headers.join(','),
    // Add sample row
    ['Sample Account', ...template.kpis.map(() => '0')].join(',')
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
  
  // Simple matching algorithm (would be AI-powered in production)
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
      
      // Partial match
      const sourceWords = normalizedSource.split(/\s+/);
      const targetWords = normalizedTarget.split(/\s+/);
      const commonWords = sourceWords.filter(w => targetWords.includes(w));
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
  accountName?: string
): Promise<{ uploadId: string; sessionId: string }> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('mappings', JSON.stringify(fieldMappings));
  formData.append('session_id', sessionId);
  
  // Backend expects account_name for upload
  if (accountName) {
    formData.append('account_name', accountName);
  } else {
    // Extract account name from first row of CSV if available
    try {
      const text = await file.text();
      const lines = text.split(/\r?\n/).filter(line => line.trim());
      if (lines.length > 1) {
        // Try to get account name from first data row
        const firstDataRow = lines[1].split(',').map(col => col.trim().replace(/^"|"$/g, ''));
        if (firstDataRow.length > 0 && firstDataRow[0]) {
          formData.append('account_name', firstDataRow[0]);
        }
      }
    } catch (e) {
      // If we can't parse, use a default
      formData.append('account_name', 'Onboarding Import');
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

// Get processing status
export const getProcessingStatus = async (sessionId: string): Promise<ProcessingStatus> => {
  // Mock processing status - would poll backend
  return {
    stages: [
      { name: 'Validating data structure', status: 'complete', duration: 1200 },
      { name: 'Cleaning and transforming', status: 'complete', duration: 2100 },
      { name: 'Calculating health scores', status: 'running', duration: 3800 },
      { name: 'Generating insights', status: 'pending' },
      { name: 'Creating dashboard', status: 'pending' }
    ],
    overallProgress: 65,
    recordsProcessed: 35,
    errors: 0
  };
};

// Get import summary
export const getImportSummary = async (uploadId: string): Promise<ImportSummary> => {
  // Mock summary - would come from backend
  return {
    customersImported: 35,
    kpisProcessed: 490,
    healthyAccounts: 21,
    atRiskAccounts: 12,
    criticalAccounts: 2,
    portfolioHealth: 79,
    priorityActions: 2
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

