/**
 * Onboarding Wizard - Configuration and Default Values
 */

import { PillarRanking, EventSeverity, AccountInfo, BusinessContext, SuccessCriteria, DataSource, VerticalType } from './OnboardingWizard.types';

// ============================================================================
// VERTICAL-SPECIFIC CONFIGURATIONS
// ============================================================================

export const SAAS_PILLARS: PillarRanking[] = [
  { id: 'P1_product_usage', label: 'Product Usage', description: 'Active usage and engagement', rank: 1 },
  { id: 'P2_support_engagement', label: 'Support Engagement', description: 'Support ticket quality and resolution', rank: 2 },
  { id: 'P3_customer_sentiment', label: 'Customer Sentiment', description: 'Overall satisfaction and NPS', rank: 3 },
  { id: 'P4_business_outcomes', label: 'Business Outcomes', description: 'Value and ROI delivered', rank: 4 },
  { id: 'P5_relationship_strength', label: 'Relationship Strength', description: 'Executive engagement and advocacy', rank: 5 }
];

export const DATACENTER_PILLARS: PillarRanking[] = [
  { id: 'P1_deployment_velocity', label: 'Deployment Velocity', description: 'Speed of system deployment and adoption', rank: 1 },
  { id: 'P2_operational_stability', label: 'Operational Stability', description: 'System reliability and uptime', rank: 2 },
  { id: 'P3_ai_workload_performance', label: 'AI Workload Performance', description: 'Performance of AI/ML workloads', rank: 3 },
  { id: 'P4_channel_partner_health', label: 'Channel Partner Health', description: 'Engagement with channel partners', rank: 4 },
  { id: 'P5_expansion_readiness', label: 'Expansion Readiness', description: 'Potential for account growth', rank: 5 }
];

export const SAAS_EVENTS: EventSeverity[] = [
  { id: 'login_drop', name: 'Login Drop >30%', severity: 8, type: 'negative' },
  { id: 'feature_abandonment', name: 'Feature Abandonment', severity: 6, type: 'negative' },
  { id: 'support_spike', name: 'Support Ticket Spike', severity: 7, type: 'negative' },
  { id: 'nps_drop', name: 'NPS Drop >10pts', severity: 8, type: 'negative' },
  { id: 'contract_renewal', name: 'Contract Renewal', severity: 7, type: 'positive' },
  { id: 'feature_expansion', name: 'Feature Expansion', severity: 9, type: 'positive' },
  { id: 'qbr', name: 'QBR Completed', severity: 6, type: 'positive' },
  { id: 'expansion', name: 'Expansion Discussion', severity: 8, type: 'positive' }
];

export const DATACENTER_EVENTS: EventSeverity[] = [
  { id: 'critical_outage', name: 'Critical Outage (>4 hours)', severity: 10, type: 'negative' },
  { id: 'deployment_failure', name: 'Deployment Failure', severity: 8, type: 'negative' },
  { id: 'performance_degradation', name: 'Performance Degradation >20%', severity: 7, type: 'negative' },
  { id: 'security_incident', name: 'Security Incident', severity: 9, type: 'negative' },
  { id: 'capacity_expansion', name: 'Capacity Expansion', severity: 8, type: 'positive' },
  { id: 'uptime_milestone', name: '99.9% Uptime Milestone', severity: 9, type: 'positive' },
  { id: 'escalation', name: 'Support Escalation', severity: 8, type: 'negative' },
  { id: 'missed_sla', name: 'Missed SLA', severity: 6, type: 'negative' }
];

export const getPillarsForVertical = (vertical: VerticalType): PillarRanking[] => {
  if (vertical === 'saas') return SAAS_PILLARS;
  if (vertical === 'datacenter') return DATACENTER_PILLARS;
  return [];
};

export const getEventsForVertical = (vertical: VerticalType): EventSeverity[] => {
  if (vertical === 'saas') return SAAS_EVENTS;
  if (vertical === 'datacenter') return DATACENTER_EVENTS;
  return [];
};

// ============================================================================
// DEFAULT VALUES
// ============================================================================

export const DEFAULT_ACCOUNT: AccountInfo = {
  email: '',
  password: '',
  company_domain: '',
  subscription_plan: 'professional',
  payment_method: 'card'
};

export const DEFAULT_BUSINESS: BusinessContext = {
  company_name: '',
  industry: '',
  segments: [],
  avg_deal_size: 100000,
  contract_model: 'annual',
  csm_model: 'high_touch',
  vertical: null
};

export const DEFAULT_CRITERIA: SuccessCriteria = {
  healthy_min: 70,
  at_risk_min: 50,
  churn_alert: 60,
  expansion_alert: 50,
  prediction_horizon: 90
};

export const getDefaultSources = (vertical: VerticalType): DataSource[] => {
  const baseSources: DataSource[] = [
    { id: 'accounts', name: 'Account List', type: 'file', status: 'pending' },
    { id: 'kpis', name: 'Historical KPIs', type: 'file', status: 'pending' }
  ];

  if (vertical === 'saas') {
    return [
      ...baseSources,
      { id: 'usage_analytics', name: 'Product Usage Analytics', type: 'api', status: 'pending' },
      { id: 'support_tickets', name: 'Support Tickets', type: 'file', status: 'pending' },
      { id: 'nps_surveys', name: 'NPS Surveys', type: 'file', status: 'pending' },
      { id: 'salesforce', name: 'Salesforce', type: 'api', status: 'pending' }
    ];
  } else if (vertical === 'datacenter') {
    return [
      ...baseSources,
      { id: 'qualitative_signals', name: 'Qualitative Signals', type: 'file', status: 'pending' },
      { id: 'products', name: 'Products Catalog', type: 'file', status: 'pending' },
      { id: 'profiles', name: 'Account Profiles', type: 'file', status: 'pending' },
      { id: 'monitoring_metrics', name: 'Monitoring Metrics', type: 'api', status: 'pending' },
      { id: 'zendesk', name: 'Zendesk', type: 'api', status: 'pending' }
    ];
  }

  return baseSources;
};

// ============================================================================
// PLAN CONFIGURATIONS
// ============================================================================

export const SUBSCRIPTION_PLANS = [
  { 
    id: 'free' as const, 
    name: 'Free', 
    price: 0, 
    features: ['Up to 10 accounts', 'Basic reports', 'Community support'] 
  },
  { 
    id: 'starter' as const, 
    name: 'Starter', 
    price: 99, 
    features: ['Up to 100 accounts', 'Standard reports', 'Email support', 'Basic integrations'] 
  },
  { 
    id: 'professional' as const, 
    name: 'Professional', 
    price: 299, 
    features: ['Unlimited accounts', 'Advanced analytics', 'Priority support', 'All integrations', 'Custom thresholds'] 
  },
  { 
    id: 'enterprise' as const, 
    name: 'Enterprise', 
    price: 999, 
    features: ['Everything in Professional', 'Custom integrations', 'Dedicated CSM', 'SLA guarantee', 'On-premise option'] 
  }
];

// ============================================================================
// OPTIONS LISTS
// ============================================================================

export const INDUSTRIES = ['SaaS', 'Hardware', 'Services', 'Healthcare', 'FinTech', 'Manufacturing', 'Other'];

export const SEGMENTS = ['Enterprise', 'Mid-market', 'SMB', 'Startup'];

export const CONTRACT_MODELS = ['Monthly', 'Annual', 'Multi-year'];

export const CSM_MODELS = ['High-touch', 'Tech-touch', 'Digital', 'Hybrid'];

export const TEAM_ROLES = [
  { id: 'admin', label: 'Admin', description: 'Full access to all features' },
  { id: 'csm', label: 'CSM', description: 'Manage accounts and playbooks' },
  { id: 'analyst', label: 'Analyst', description: 'View reports and analytics' },
  { id: 'viewer', label: 'Viewer', description: 'Read-only access' }
];
