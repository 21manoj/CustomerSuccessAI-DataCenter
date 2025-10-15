/**
 * Playbooks Types Definition
 * 
 * Core TypeScript interfaces and types for the Playbooks system
 */

export interface PlaybookStep {
  id: string;
  title: string;
  description: string;
  type: 'action' | 'decision' | 'automation' | 'manual';
  status: PlaybookStatus;
  dependencies?: string[];
  estimatedTime?: number; // in minutes
  data?: Record<string, any>;
}

// VoC Sprint specific data structures
export interface VoCTriggerData {
  nps_threshold: number;
  csat_threshold: number;
  churn_risk_threshold: number;
  health_score_drop_threshold: number;
  churn_mentions_threshold: number;
}

export interface VoCRAGData {
  rag_prompt: string;
  output_format: {
    top_5_themes: string;
    customer_quotes: string;
    fastest_actions: string;
    kpi_impact: string;
  };
}

// Activation Blitz specific data structures
export interface ActivationTriggerData {
  adoption_index_threshold: number;
  active_users_threshold: number;
  dau_mau_threshold: number;
  unused_feature_check: boolean;
  target_features?: string;
}

export interface ActivationRAGData {
  rag_prompt: string;
  output_format: {
    activation_plan: string;
    in_app_steps: string;
    email_sequence: string;
    kpi_targets: string;
    success_metrics: string;
  };
}

export interface Playbook {
  id: string;
  name: string;
  description: string;
  category: 'voc-sprint' | 'activation-blitz' | 'sla-stabilizer' | 'renewal-safeguard' | 'expansion-timing';
  steps: PlaybookStep[];
  estimatedDuration: number; // in minutes
  prerequisites?: string[];
  successCriteria?: string[];
  tags: string[];
  version: string;
  lastUpdated: string;
  author: string;
}

export interface PlaybookExecution {
  id: string;
  playbookId: string;
  accountId?: number;
  customerId: number;
  status: PlaybookStatus;
  currentStep?: string;
  startedAt: string;
  completedAt?: string;
  results: PlaybookResult[];
  context?: {
    customerId?: number;
    accountId?: number;
    accountName?: string;
    userId?: number;
    userName?: string;
    timestamp?: string;
    metadata?: Record<string, any>;
  };
  metadata: Record<string, any>;
}

export interface PlaybookResult {
  stepId: string;
  status: PlaybookStatus;
  completedAt: string;
  data?: Record<string, any>;
  notes?: string;
  attachments?: string[];
}

export interface PlaybookContext {
  customerId: number;
  accountId?: number;
  accountName?: string;
  userId: number;
  userName: string;
  timestamp: string;
  metadata: Record<string, any>;
}

export type PlaybookStatus = 
  | 'not-started'
  | 'in-progress' 
  | 'completed'
  | 'failed'
  | 'paused'
  | 'cancelled';

export interface PlaybookDefinition {
  id: string;
  name: string;
  description: string;
  category: string;
  icon?: string;
  color?: string;
  steps: PlaybookStep[];
  estimatedDuration: number;
  prerequisites?: string[];
  successCriteria?: string[];
  tags: string[];
  version: string;
  lastUpdated: string;
  author: string;
}

// API Response Types
export interface PlaybookListResponse {
  playbooks: PlaybookDefinition[];
  total: number;
}

export interface PlaybookExecutionResponse {
  execution: PlaybookExecution;
  playbook: PlaybookDefinition;
}

export interface PlaybookStepResponse {
  step: PlaybookStep;
  canExecute: boolean;
  dependencies: PlaybookStep[];
}
