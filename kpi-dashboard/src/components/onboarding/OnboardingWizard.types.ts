/**
 * Onboarding Wizard - TypeScript Type Definitions
 */

export type VerticalType = 'saas' | 'datacenter' | null;
export type OnboardingMode = 'demo' | 'custom';

export interface AccountInfo {
  email: string;
  password: string;
  company_domain: string;
  subscription_plan: 'free' | 'starter' | 'professional' | 'enterprise';
  payment_method?: 'card' | 'invoice' | 'none';
}

export interface BusinessContext {
  company_name: string;
  industry: string;
  segments: string[];
  avg_deal_size: number;
  contract_model: string;
  csm_model: string;
  vertical: VerticalType;
}

export interface PillarRanking {
  id: string;
  label: string;
  description: string;
  rank: number;
  kpis?: string[];
}

export interface EventSeverity {
  id: string;
  name: string;
  severity: number;
  type: 'negative' | 'positive';
}

export interface SuccessCriteria {
  healthy_min: number;
  at_risk_min: number;
  churn_alert: number;
  expansion_alert: number;
  prediction_horizon: number;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  row_count?: number;
  columns?: string[];
}

export interface DataSource {
  id: string;
  name: string;
  type: 'file' | 'api';
  status: 'pending' | 'uploaded' | 'connected' | 'skipped' | 'validating' | 'error';
  rows?: number;
  filename?: string;
  file?: File;  // Store File object for upload
  preview?: any[];
  validation?: ValidationResult;
  api_config?: {
    endpoint?: string;
    api_key?: string;
    auth_type?: string;
    connected_at?: string;
  };
}

export interface TeamMember {
  email: string;
  name: string;
  role: 'admin' | 'csm' | 'analyst' | 'viewer';
  invited: boolean;
  invited_at?: string;
}

export interface OnboardingData {
  account: AccountInfo;
  business: BusinessContext;
  pillars: PillarRanking[];
  events: EventSeverity[];
  criteria: SuccessCriteria;
  sources: DataSource[];
  team: TeamMember[];
  skip_training: boolean;
  onboarding_mode: OnboardingMode;
}
