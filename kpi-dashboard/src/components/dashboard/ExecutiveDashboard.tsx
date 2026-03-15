/**
 * CS Pulse Executive Dashboard
 * =============================
 * 
 * Full-featured dashboard with:
 * - Portfolio Health Overview (Healthy/At-Risk/Critical)
 * - Smart Actions Panel with AI recommendations
 * - Account Health Cards with trend indicators
 * - Health Trend Charts
 * - Signal Analyst Integration
 * - Journey Visualizer Links
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { classify, classifyColor, classifyBadgeClass, classifyLabel, thresholdValues, getThresholds } from '../../utils/healthThresholds';
import { useSession } from '../../contexts/SessionContext';
import { useEntitlements } from '../../hooks/useEntitlement';
import { getCustomerIdentifier } from '../../utils/api';
import InfoTooltip from '../shared/InfoTooltip';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import {
  AlertTriangle, TrendingUp, TrendingDown, Minus,
  Users, DollarSign, Activity, Target, ChevronRight,
  Calendar, Clock, Shield, Zap, Server, CheckCircle,
  XCircle, AlertCircle, Play, Eye, RefreshCw,
  ListChecks, ArrowRight, BarChart2, Upload, X as XIcon,
  Sparkles, Rocket
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface AccountHealth {
  account_id: string;
  account_name: string;
  health_score: number;
  health_trend: 'improving' | 'stable' | 'declining';
  churn_probability: number;
  expansion_probability: number;
  pattern_type: string;
  pillar_scores: {
    reliability: number;
    efficiency: number;
    capacity: number;
    security: number;
    service: number;
  };
  last_analysis: string;
  recommended_actions: string[];
  /** True when score is the backend placeholder (50) because no KPI/health-trend data exists */
  isPlaceholderScore?: boolean;
}

interface SmartAction {
  id: string;
  urgency: 'critical' | 'high' | 'opportunity';
  account_id: string;
  account_name: string;
  title: string;
  description: string;
  action_type: string;
  due_date?: string;
}

interface DailyAction {
  id: string;
  rank: number;
  account_id: number | string;
  account_name: string;
  action_title: string;
  action_description: string;
  action_type: string;
  related_playbook_id: string | null;
  urgency: 'critical' | 'high' | 'opportunity' | 'medium';
  impact_score: number;
  effort_score: number;
  priority_index: number;
  account_health: number;
  estimated_hours: number;
  estimated_duration_display: string;
  roi_metric_id?: string;
  roi_metric_name?: string;
  roi_projected_impact?: number;
  roi_impact_type?: string;
  // Cost bridge fields (optional — present for playbook actions)
  manual_hours?: number;
  automated_hours?: number;
  automation_pct?: number;
  manual_cost?: number;
  cost_without_platform?: number;
  platform_savings_per_run?: number;
  roi_per_run?: number;
}

interface DailyActionsSummary {
  total_actions: number;
  critical_count: number;
  high_count: number;
  opportunity_count: number;
  total_estimated_hours: number;
  total_roi_projected_impact?: number;
  roi_metrics_involved?: string[];
}

interface PortfolioSummary {
  total_accounts: number;
  healthy_count: number;
  at_risk_count: number;
  critical_count: number;
  total_arr: number;
  arr_at_risk: number;
  expansion_pipeline: number;
  avg_health_score: number;
  health_trend: number; // % change
}

// ============================================================================
// MOCK DATA (Replace with API calls)
// ============================================================================

const MOCK_PORTFOLIO: PortfolioSummary = {
  total_accounts: 3,
  healthy_count: 1,
  at_risk_count: 1,
  critical_count: 1,
  total_arr: 2500000,
  arr_at_risk: 450000,
  expansion_pipeline: 380000,
  avg_health_score: 72,
  health_trend: 3.2
};

const MOCK_ACCOUNTS: AccountHealth[] = [
  {
    account_id: '10001',
    account_name: 'CloudScale AI Labs',
    health_score: 92,
    health_trend: 'improving',
    churn_probability: 8,
    expansion_probability: 85,
    pattern_type: 'expansion',
    pillar_scores: { reliability: 94, efficiency: 88, capacity: 92, security: 96, service: 90 },
    last_analysis: '2026-01-13T10:30:00Z',
    recommended_actions: ['Schedule QBR', 'Discuss Phase 2 expansion']
  },
  {
    account_id: '10003',
    account_name: 'Quantum Computing Corp',
    health_score: 45,
    health_trend: 'declining',
    churn_probability: 78,
    expansion_probability: 5,
    pattern_type: 'churn',
    pillar_scores: { reliability: 42, efficiency: 55, capacity: 38, security: 50, service: 40 },
    last_analysis: '2026-01-13T10:30:00Z',
    recommended_actions: ['Executive escalation', 'Emergency support review', 'Discount negotiation']
  },
  {
    account_id: '10007',
    account_name: 'Legacy Manufacturing Corp',
    health_score: 68,
    health_trend: 'stable',
    churn_probability: 35,
    expansion_probability: 25,
    pattern_type: 'recovery',
    pillar_scores: { reliability: 72, efficiency: 65, capacity: 70, security: 68, service: 65 },
    last_analysis: '2026-01-13T10:30:00Z',
    recommended_actions: ['Continue monitoring', 'Schedule health check']
  }
];

const MOCK_ACTIONS: SmartAction[] = [
  {
    id: '1',
    urgency: 'critical',
    account_id: '10003',
    account_name: 'Quantum Computing Corp',
    title: 'Executive Escalation Required',
    description: 'Churn probability at 78%. Health score dropped 15 points in 2 weeks.',
    action_type: 'escalation',
    due_date: '2026-01-14'
  },
  {
    id: '2',
    urgency: 'high',
    account_id: '10007',
    account_name: 'Legacy Manufacturing Corp',
    title: 'Schedule Health Check',
    description: 'Account recovering but needs attention. Last contact 21 days ago.',
    action_type: 'meeting',
    due_date: '2026-01-17'
  },
  {
    id: '3',
    urgency: 'opportunity',
    account_id: '10001',
    account_name: 'CloudScale AI Labs',
    title: 'Expansion Opportunity',
    description: 'Health score 92%, expansion probability 85%. Ready for Phase 2 discussion.',
    action_type: 'expansion',
    due_date: '2026-01-20'
  }
];

const MOCK_TREND_DATA = [
  { month: 'Aug', healthy: 1, atRisk: 1, critical: 1, avgScore: 65 },
  { month: 'Sep', healthy: 1, atRisk: 1, critical: 1, avgScore: 67 },
  { month: 'Oct', healthy: 1, atRisk: 2, critical: 0, avgScore: 69 },
  { month: 'Nov', healthy: 2, atRisk: 1, critical: 0, avgScore: 71 },
  { month: 'Dec', healthy: 1, atRisk: 1, critical: 1, avgScore: 70 },
  { month: 'Jan', healthy: 1, atRisk: 1, critical: 1, avgScore: 72 }
];

// ============================================================================
// HELPER COMPONENTS
// ============================================================================

const TrendIndicator: React.FC<{ trend: string; value?: number }> = ({ trend, value }) => {
  if (trend === 'improving') {
    return (
      <span className="flex items-center text-green-600 text-sm">
        <TrendingUp className="w-4 h-4 mr-1" />
        {value ? `+${value}%` : 'Improving'}
      </span>
    );
  }
  if (trend === 'declining') {
    return (
      <span className="flex items-center text-red-600 text-sm">
        <TrendingDown className="w-4 h-4 mr-1" />
        {value ? `${value}%` : 'Declining'}
      </span>
    );
  }
  return (
    <span className="flex items-center text-gray-500 text-sm">
      <Minus className="w-4 h-4 mr-1" />
      Stable
    </span>
  );
};

const HealthBadge: React.FC<{ score: number }> = ({ score }) => {
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${classifyBadgeClass(score)}`}>
      {classifyLabel(score)}
    </span>
  );
};

const ProgressBar: React.FC<{ value: number; color?: string }> = ({ value, color = 'blue' }) => {
  const colorClass = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500'
  }[color] || 'bg-blue-500';
  
  return (
    <div className="w-full bg-gray-200 rounded-full h-2">
      <div
        className={`h-2 rounded-full ${colorClass}`}
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
};

// ============================================================================
// MAIN COMPONENTS
// ============================================================================

// Portfolio Summary Cards
const PortfolioOverview: React.FC<{ summary: PortfolioSummary }> = ({ summary }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      {/* Total Accounts */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500 flex items-center">
              Total Accounts
            </p>
            <p className="text-2xl font-bold">{summary.total_accounts}</p>
          </div>
          <Users className="w-10 h-10 text-blue-500 opacity-50" />
        </div>
        <div className="mt-2 flex items-center text-sm">
          <span className="text-green-600 flex items-center">
            Avg Health: {summary.avg_health_score}
            <InfoTooltip text="Overall health from 0-100. Green (70+) is healthy, yellow (50-69) needs attention, red (below 50) is critical." position="right" />
          </span>
          <TrendIndicator trend="improving" value={summary.health_trend} />
        </div>
      </div>

      {/* Health Distribution */}
      <div className="bg-white rounded-lg shadow p-4">
        <p className="text-sm text-gray-500 mb-2">Health Distribution</p>
        <div className="flex items-center gap-2">
          <div className="flex-1 text-center">
            <div className="text-xl font-bold text-green-600">{summary.healthy_count}</div>
            <div className="text-xs text-gray-500">Healthy</div>
          </div>
          <div className="flex-1 text-center border-l border-r">
            <div className="text-xl font-bold text-yellow-600">{summary.at_risk_count}</div>
            <div className="text-xs text-gray-500">At Risk</div>
          </div>
          <div className="flex-1 text-center">
            <div className="text-xl font-bold text-red-600">{summary.critical_count}</div>
            <div className="text-xs text-gray-500">Critical</div>
          </div>
        </div>
      </div>

      {/* ARR at Risk */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500 flex items-center">
              ARR at Risk
              <InfoTooltip text="Annual Recurring Revenue from accounts scoring below 50. This is your churn exposure." />
            </p>
            <p className="text-2xl font-bold text-red-600">
              ${(summary.arr_at_risk / 1000).toFixed(0)}K
            </p>
          </div>
          <AlertTriangle className="w-10 h-10 text-red-500 opacity-50" />
        </div>
        <div className="mt-2 text-sm text-gray-500">
          {summary.total_arr > 0 
            ? `${((summary.arr_at_risk / summary.total_arr) * 100).toFixed(1)}% of total ARR`
            : '0% of total ARR'}
        </div>
      </div>

      {/* Expansion Pipeline */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">Expansion Pipeline</p>
            <p className="text-2xl font-bold text-green-600">
              ${(summary.expansion_pipeline / 1000).toFixed(0)}K
            </p>
          </div>
          <Target className="w-10 h-10 text-green-500 opacity-50" />
        </div>
        <div className="mt-2 text-sm text-gray-500">
          {summary.healthy_count} accounts ready
        </div>
      </div>
    </div>
  );
};

// Smart Actions Panel
const SmartActionsPanel: React.FC<{ actions: SmartAction[]; onAction: (action: SmartAction) => void }> = ({ actions, onAction }) => {
  const urgencyConfig = {
    critical: {
      bg: 'bg-red-50 border-red-200',
      icon: <XCircle className="w-5 h-5 text-red-600" />,
      badge: 'bg-red-100 text-red-800'
    },
    high: {
      bg: 'bg-yellow-50 border-yellow-200',
      icon: <AlertCircle className="w-5 h-5 text-yellow-600" />,
      badge: 'bg-yellow-100 text-yellow-800'
    },
    opportunity: {
      bg: 'bg-green-50 border-green-200',
      icon: <CheckCircle className="w-5 h-5 text-green-600" />,
      badge: 'bg-green-100 text-green-800'
    }
  };

  return (
    <div className="bg-white rounded-lg shadow mb-6">
      <div className="p-4 border-b flex items-center justify-between">
        <div className="flex items-center">
          <Zap className="w-5 h-5 text-yellow-500 mr-2" />
          <h2 className="text-lg font-semibold">Smart Actions</h2>
        </div>
        <span className="text-sm text-gray-500">{actions.length} actions pending</span>
      </div>
      
      <div className="divide-y">
        {actions.map(action => {
          const config = urgencyConfig[action.urgency];
          return (
            <div
              key={action.id}
              className={`p-4 ${config.bg} border-l-4 hover:bg-opacity-75 cursor-pointer transition`}
              onClick={() => onAction(action)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start">
                  <div className="mr-3 mt-1">{config.icon}</div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${config.badge}`}>
                        {action.urgency.toUpperCase()}
                      </span>
                      <span className="text-sm text-gray-600">{action.account_name}</span>
                    </div>
                    <h3 className="font-medium text-gray-900">{action.title}</h3>
                    <p className="text-sm text-gray-600 mt-1">{action.description}</p>
                    {action.due_date && (
                      <div className="flex items-center mt-2 text-xs text-gray-500">
                        <Calendar className="w-3 h-3 mr-1" />
                        Due: {new Date(action.due_date).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-gray-400" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Analysis report modal content type (matches SignalAnalystOutput)
interface AnalysisReport {
  account_id?: string;
  health_score?: number;
  churn_probability?: number;
  expansion_probability?: number;
  predicted_outcome?: string;
  reasoning?: string;
  key_insights?: string[];
  recommended_actions?: Array<{ action?: string; title?: string; priority?: string; owner?: string }>;
  risk_drivers?: Array<{ driver?: string; impact?: string }>;
  growth_drivers?: Array<{ driver?: string; impact?: string }>;
  time_to_event?: string;
  [key: string]: unknown;
}

// Account Health Card
const AccountHealthCard: React.FC<{ 
  account: AccountHealth; 
  onViewJourney: (id: string) => void;
  onRunAnalysis: (id: string) => void;
  isAnalyzing?: boolean;
  report?: AnalysisReport | null;
  onShowReport?: (report: AnalysisReport) => void;
}> = ({ account, onViewJourney, onRunAnalysis, isAnalyzing = false, report, onShowReport }) => {
  const pillars = [
    { key: 'reliability', label: 'Reliability', icon: <Server className="w-4 h-4" /> },
    { key: 'efficiency', label: 'Efficiency', icon: <Zap className="w-4 h-4" /> },
    { key: 'capacity', label: 'Capacity', icon: <Activity className="w-4 h-4" /> },
    { key: 'security', label: 'Security', icon: <Shield className="w-4 h-4" /> },
    { key: 'service', label: 'Service', icon: <Clock className="w-4 h-4" /> }
  ];

  const getScoreColor = (score: number) => classify(score) === 'healthy' ? 'green' : classify(score) === 'at_risk' ? 'yellow' : 'red';

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b bg-gray-50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900">{account.account_name}</h3>
            <p className="text-sm text-gray-500">Account ID: {account.account_id}</p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold" style={{
              color: classifyColor(account.health_score)
            }}>
              {account.health_score}
            </div>
            <HealthBadge score={account.health_score} />
            {account.isPlaceholderScore && (
              <p className="text-xs text-amber-600 mt-1" title="No KPI or health-trend data; score is a placeholder. Upload KPIs to see real scores.">
                No KPI data
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="p-4">
        {/* Trend & Probabilities */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="text-center">
            <p className="text-xs text-gray-500 mb-1">Trend</p>
            <TrendIndicator trend={account.health_trend} />
          </div>
          <div className="text-center border-l border-r">
            <p className="text-xs text-gray-500 mb-1">Churn Risk</p>
            <span className={`font-semibold ${
              account.churn_probability > 50 ? 'text-red-600' : 'text-gray-900'
            }`}>
              {account.churn_probability}%
            </span>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 mb-1">Expansion</p>
            <span className={`font-semibold ${
              account.expansion_probability > 50 ? 'text-green-600' : 'text-gray-900'
            }`}>
              {account.expansion_probability}%
            </span>
          </div>
        </div>

        {/* Pillar Scores */}
        <div className="space-y-2 mb-4">
          {pillars.map(pillar => {
            const score = account.pillar_scores[pillar.key as keyof typeof account.pillar_scores];
            return (
              <div key={pillar.key} className="flex items-center">
                <div className="w-24 flex items-center text-xs text-gray-600">
                  {pillar.icon}
                  <span className="ml-1">{pillar.label}</span>
                </div>
                <div className="flex-1 mx-2">
                  <ProgressBar value={score} color={getScoreColor(score)} />
                </div>
                <div className="w-8 text-right text-xs font-medium">{score}</div>
              </div>
            );
          })}
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <button
              onClick={() => onViewJourney(account.account_id)}
              disabled={isAnalyzing}
              className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-blue-50 text-blue-700 rounded hover:bg-blue-100 disabled:opacity-50 text-sm"
            >
              <Eye className="w-4 h-4" />
              View Journey
            </button>
            <button
              onClick={() => onRunAnalysis(account.account_id)}
              disabled={isAnalyzing}
              className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-green-50 text-green-700 rounded hover:bg-green-100 disabled:opacity-50 text-sm"
            >
              {isAnalyzing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Analyzing…
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Run Analysis
                </>
              )}
            </button>
          </div>
          {report && onShowReport && (
            <button
              onClick={() => onShowReport(report)}
              className="w-full flex items-center justify-center gap-1 px-3 py-2 bg-indigo-50 text-indigo-700 rounded hover:bg-indigo-100 text-sm"
            >
              <Eye className="w-4 h-4" />
              See detailed report
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// Health Trend Chart
const HealthTrendChart: React.FC<{ data: typeof MOCK_TREND_DATA }> = ({ data }) => {
  return (
    <div className="bg-white rounded-lg shadow p-4 mb-6">
      <h2 className="text-lg font-semibold mb-4">Portfolio Health Trend</h2>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Area
              type="monotone"
              dataKey="avgScore"
              stroke="#3b82f6"
              fill="#93c5fd"
              name="Avg Health Score"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// Distribution Pie Chart
const HealthDistributionChart: React.FC<{ summary: PortfolioSummary }> = ({ summary }) => {
  const data = [
    { name: 'Healthy', value: summary.healthy_count, color: '#16a34a' },
    { name: 'At Risk', value: summary.at_risk_count, color: '#ca8a04' },
    { name: 'Critical', value: summary.critical_count, color: '#dc2626' }
  ];

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h2 className="text-lg font-semibold mb-4">Health Distribution</h2>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={40}
              outerRadius={70}
              paddingAngle={2}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="flex justify-center gap-4 mt-2">
        {data.map(item => (
          <div key={item.name} className="flex items-center text-sm">
            <div className="w-3 h-3 rounded-full mr-1" style={{ backgroundColor: item.color }} />
            <span>{item.name}: {item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// DAILY CSM ACTIONS PANEL
// ============================================================================

const URGENCY_CONFIG = {
  critical: { bg: 'bg-red-50 border-red-200', text: 'text-red-700', badge: 'bg-red-100 text-red-800', dot: 'bg-red-500' },
  high: { bg: 'bg-amber-50 border-amber-200', text: 'text-amber-700', badge: 'bg-amber-100 text-amber-800', dot: 'bg-amber-500' },
  opportunity: { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700', badge: 'bg-emerald-100 text-emerald-800', dot: 'bg-emerald-500' },
  medium: { bg: 'bg-blue-50 border-blue-200', text: 'text-blue-700', badge: 'bg-blue-100 text-blue-800', dot: 'bg-blue-500' },
};

const DailyActionsPanel: React.FC<{
  actions: DailyAction[];
  summary: DailyActionsSummary;
  filter: 'all' | 'critical' | 'high' | 'opportunity';
  onFilterChange: (f: 'all' | 'critical' | 'high' | 'opportunity') => void;
  loading: boolean;
  onStartPlaybook: (action: DailyAction) => void;
  onViewAccount: (accountId: number | string) => void;
}> = ({ actions, summary, filter, onFilterChange, loading, onStartPlaybook, onViewAccount }) => {
  const filtered = filter === 'all' ? actions : actions.filter(a => a.urgency === filter);
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  return (
    <div className="bg-white rounded-lg shadow mb-6">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-100 rounded-lg">
              <ListChecks className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">CSM Daily Actions</h2>
              <p className="text-xs text-gray-500">{today}</p>
            </div>
          </div>
          {/* Filter chips */}
          <div className="flex gap-1.5">
            {(['all', 'critical', 'high', 'opportunity'] as const).map(f => (
              <button
                key={f}
                onClick={() => onFilterChange(f)}
                className={`px-3 py-1 text-xs rounded-full font-medium transition-colors ${
                  filter === f
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
                {f !== 'all' && (
                  <span className="ml-1">
                    ({f === 'critical' ? summary.critical_count : f === 'high' ? summary.high_count : summary.opportunity_count})
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-4 gap-3 px-5 py-3 bg-gray-50/50 border-b border-gray-100">
        <div className="text-center">
          <p className="text-xl font-bold text-gray-900">{summary.total_actions}</p>
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Actions</p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-red-600">{summary.critical_count}</p>
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Critical</p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-indigo-600">{summary.total_estimated_hours}h</p>
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Est. Hours</p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold text-emerald-600">
            {summary.total_roi_projected_impact ? `$${(summary.total_roi_projected_impact / 1000).toFixed(0)}K` : '$0'}
          </p>
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">ROI Impact</p>
        </div>
      </div>

      {/* Action list */}
      <div className="max-h-[400px] overflow-y-auto divide-y divide-gray-50">
        {loading ? (
          <div className="py-8 text-center text-gray-400 text-sm">Loading daily actions...</div>
        ) : filtered.length === 0 ? (
          <div className="py-8 text-center text-gray-400 text-sm">
            {filter === 'all' ? 'No actions needed today. Great job!' : `No ${filter} actions.`}
          </div>
        ) : (
          filtered.map(action => {
            const cfg = URGENCY_CONFIG[action.urgency] || URGENCY_CONFIG.medium;
            return (
              <div key={action.id} className={`flex items-center gap-3 px-5 py-3 hover:bg-gray-50/80 transition-colors ${cfg.bg} border-l-4`}>
                {/* Rank */}
                <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gray-800 text-white flex items-center justify-center text-xs font-bold">
                  {action.rank}
                </div>

                {/* Urgency dot + Account health */}
                <div className="flex-shrink-0 flex flex-col items-center gap-0.5">
                  <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${cfg.badge}`}>
                    {action.urgency}
                  </span>
                  <div className="relative w-8 h-8">
                    <svg className="w-8 h-8 -rotate-90" viewBox="0 0 36 36">
                      <circle cx="18" cy="18" r="14" fill="none" stroke="#e5e7eb" strokeWidth="3" />
                      <circle
                        cx="18" cy="18" r="14" fill="none"
                        stroke={classifyColor(action.account_health)}
                        strokeWidth="3" strokeDasharray={`${(Math.max(0, action.account_health) / 100) * 88} 88`} strokeLinecap="round"
                      />
                    </svg>
                    <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold">{Math.max(0, Math.round(action.account_health))}</span>
                  </div>
                </div>

                {/* Main content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onViewAccount(action.account_id)}
                      className="text-xs text-indigo-600 hover:underline font-medium truncate"
                    >
                      {action.account_name}
                    </button>
                    {action.roi_metric_name && (
                      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[9px] font-medium rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {action.roi_metric_name}
                        {action.roi_projected_impact ? ` +$${(action.roi_projected_impact / 1000).toFixed(0)}K` : ''}
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-gray-900 truncate">{action.action_title}</p>
                  <p className="text-xs text-gray-500 truncate">{action.action_description}</p>
                </div>

                {/* Impact / Effort bars */}
                <div className="flex-shrink-0 w-20 space-y-1">
                  <div>
                    <div className="flex items-center justify-between text-[9px] text-gray-500">
                      <span>Impact</span><span>{action.impact_score}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full bg-green-500" style={{ width: `${Math.min(100, action.impact_score)}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between text-[9px] text-gray-500">
                      <span>Effort</span><span>{action.effort_score}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full bg-blue-400" style={{ width: `${Math.min(100, action.effort_score)}%` }} />
                    </div>
                  </div>
                </div>

                {/* Duration + cost context + action button */}
                <div className="flex-shrink-0 text-right space-y-1">
                  {action.manual_hours != null && action.automated_hours != null ? (
                    <>
                      <p className="text-[10px] text-gray-500">
                        {action.manual_hours}h manual + {action.automated_hours}h auto &middot; {action.estimated_duration_display}
                      </p>
                      {action.manual_cost != null && action.roi_per_run != null && (
                        <p className="text-[10px] text-indigo-500 font-medium">
                          ${action.manual_cost.toLocaleString()}/run &middot; {action.roi_per_run.toFixed(2)}x ROI
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="text-[10px] text-gray-500">{action.estimated_hours}h &middot; {action.estimated_duration_display}</p>
                  )}
                  <button
                    onClick={() => onStartPlaybook(action)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded bg-indigo-600 text-white hover:bg-indigo-700 transition-colors"
                  >
                    {action.action_type === 'playbook' ? (
                      <><Play className="w-3 h-3" /> Start</>
                    ) : action.action_type === 'expansion' ? (
                      <><ArrowRight className="w-3 h-3" /> Call</>
                    ) : action.action_type === 'qbr' ? (
                      <><Calendar className="w-3 h-3" /> Schedule</>
                    ) : (
                      <><Eye className="w-3 h-3" /> Review</>
                    )}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

// ============================================================================
// MAIN DASHBOARD COMPONENT
// ============================================================================

const ExecutiveDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { session } = useSession();
  const { tier } = useEntitlements();
  const isStarter = tier === 'starter';

  // Welcome banner dismissed state (persisted in localStorage)
  const [welcomeDismissed, setWelcomeDismissed] = useState(() =>
    localStorage.getItem('starter_welcome_dismissed') === 'true'
  );

  const dismissWelcome = () => {
    setWelcomeDismissed(true);
    localStorage.setItem('starter_welcome_dismissed', 'true');
  };

  // State - Initialize with empty arrays instead of mock data
  const [portfolio, setPortfolio] = useState<PortfolioSummary>({
    total_accounts: 0,
    healthy_count: 0,
    at_risk_count: 0,
    critical_count: 0,
    total_arr: 0,
    arr_at_risk: 0,
    expansion_pipeline: 0,
    avg_health_score: 0,
    health_trend: 0
  });
  const [accounts, setAccounts] = useState<AccountHealth[]>([]);
  const [actions, setActions] = useState<SmartAction[]>([]);
  const [trendData, setTrendData] = useState(MOCK_TREND_DATA);
  const [loading, setLoading] = useState(true); // Start with loading=true
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [analyzingAccountId, setAnalyzingAccountId] = useState<string | null>(null);
  const [reportByAccountId, setReportByAccountId] = useState<Record<string, AnalysisReport>>({});
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportModalContent, setReportModalContent] = useState<AnalysisReport | null>(null);
  const [dailyActions, setDailyActions] = useState<DailyAction[]>([]);
  const [dailySummary, setDailySummary] = useState<DailyActionsSummary>({ total_actions: 0, critical_count: 0, high_count: 0, opportunity_count: 0, total_estimated_hours: 0, total_roi_projected_impact: 0, roi_metrics_involved: [] });
  const [dailyFilter, setDailyFilter] = useState<'all' | 'critical' | 'high' | 'opportunity'>('all');
  const [dailyLoading, setDailyLoading] = useState(false);

  // Load real data from APIs
  useEffect(() => {
    loadDashboardData();
  }, [session?.customer_id]);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      if (!session?.customer_id) {
        console.warn('No customer_id in session, cannot load dashboard data');
        return;
      }
      
      // Load accounts from accounts API (filters by customer_id automatically)
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      
      // Add customer ID header
      headers['X-Customer-ID'] = getCustomerIdentifier(session);
      
      const accountsResponse = await fetch('/api/accounts', {
        credentials: 'include',
        headers,
      });
      
      if (accountsResponse.ok) {
        const accountsData = await accountsResponse.json();
        const accountsArray = Array.isArray(accountsData) ? accountsData : (accountsData.accounts || []);
        
        if (accountsArray.length > 0) {
          // Fetch health trends for each account to get health scores
          // The /api/health-trends endpoint returns { trends: [...], total_months: ... }
          // We'll fetch trends for each account individually
          let healthTrendsMap: Record<number, any> = {};
          
          // Fetch health trends for each account
          for (const acc of accountsArray) {
            try {
              const healthTrendsResponse = await fetch(`/api/health-trends?account_id=${acc.account_id}`, {
                credentials: 'include',
                headers,
              });
              
              if (healthTrendsResponse.ok) {
                const trendsData = await healthTrendsResponse.json();
                // Get the latest trend (last in the array - trends are in chronological order)
                if (trendsData.trends && Array.isArray(trendsData.trends) && trendsData.trends.length > 0) {
                  // Trends are in chronological order, get the last one (most recent)
                  const latestTrend = trendsData.trends[trendsData.trends.length - 1];
                  healthTrendsMap[acc.account_id] = {
                    overall_health_score: latestTrend.score, // API returns 'score' not 'overall_health_score'
                    reliability_score: latestTrend.product_usage_score || null,
                    efficiency_score: latestTrend.support_score || null,
                    capacity_score: latestTrend.customer_sentiment_score || null,
                    security_score: latestTrend.business_outcomes_score || null,
                    service_score: latestTrend.relationship_strength_score || null,
                    // API doesn't return year/month, so we'll use current date for last_analysis
                    year: latestTrend.year || null,
                    month: latestTrend.month || null
                  };
                }
              }
            } catch (error) {
              console.warn(`Failed to fetch health trends for account ${acc.account_id}:`, error);
            }
          }
          
          // Transform accounts to health accounts
          const healthAccounts: AccountHealth[] = accountsArray.map((acc: any) => {
            const latestTrend = healthTrendsMap[acc.account_id];
            // Use trend score, account health_score, or default to 70
            const healthScore = latestTrend?.overall_health_score || acc.health_score || 70;
            
            // Calculate trend (compare with previous month if available)
            let healthTrend: 'improving' | 'declining' | 'stable' = 'stable';
            if (latestTrend) {
              // Try to get previous month trend
              const prevMonth = latestTrend.month > 1 ? latestTrend.month - 1 : 12;
              const prevYear = latestTrend.month > 1 ? latestTrend.year : latestTrend.year - 1;
              // For now, default to stable - could enhance to fetch previous month
              healthTrend = 'stable';
            }
            
            // Calculate probabilities based on health score
            const cls = classify(healthScore);
            const churnProb = cls === 'critical' ? 80 : cls === 'at_risk' ? 40 : 15;
            const expansionProb = cls === 'healthy' ? 75 : cls === 'at_risk' ? 30 : 5;
            
            // Get pillar scores from health trend if available, otherwise use defaults
            const pillarScores = latestTrend ? {
              reliability: latestTrend.reliability_score || 70,
              efficiency: latestTrend.efficiency_score || 70,
              capacity: latestTrend.capacity_score || 70,
              security: latestTrend.security_score || 70,
              service: latestTrend.service_score || 70
            } : {
              reliability: Math.round(healthScore * 0.95),
              efficiency: Math.round(healthScore * 0.88),
              capacity: Math.round(healthScore * 0.85),
              security: Math.round(healthScore * 1.0),
              service: Math.round(healthScore * 0.96)
            };
            
            // Safely create last_analysis date
            let lastAnalysisDate: string;
            if (latestTrend && latestTrend.year != null && latestTrend.month != null) {
              try {
                // Convert to numbers if they're strings, otherwise use as-is
                const year = typeof latestTrend.year === 'string' ? parseInt(latestTrend.year, 10) : Number(latestTrend.year);
                const month = typeof latestTrend.month === 'string' ? parseInt(latestTrend.month, 10) : Number(latestTrend.month);
                
                // Validate year and month are valid numbers
                if (!isNaN(year) && !isNaN(month) && year > 0 && year < 10000 && month >= 1 && month <= 12) {
                  const date = new Date(year, month - 1); // JavaScript months are 0-indexed
                  if (!isNaN(date.getTime())) {
                    lastAnalysisDate = date.toISOString();
                  } else {
                    lastAnalysisDate = new Date().toISOString();
                  }
                } else {
                  lastAnalysisDate = new Date().toISOString();
                }
              } catch (e) {
                console.warn(`Invalid date for account ${acc.account_id}:`, latestTrend.year, latestTrend.month, e);
                lastAnalysisDate = new Date().toISOString();
              }
            } else {
              lastAnalysisDate = new Date().toISOString();
            }
            
            const isPlaceholderScore = !latestTrend && (healthScore === 50 || acc.health_score === 50);
            return {
              account_id: String(acc.account_id),
              account_name: acc.account_name || `Account ${acc.account_id}`,
              health_score: Math.round(healthScore),
              health_trend: healthTrend,
              churn_probability: churnProb,
              expansion_probability: expansionProb,
              pattern_type: 'unknown', // Could be determined from journey data if available
              pillar_scores: pillarScores,
              last_analysis: lastAnalysisDate,
              recommended_actions: [],
              isPlaceholderScore
            };
          });
          
          setAccounts(healthAccounts);
          
          // Update portfolio summary
          const { healthy_min, at_risk_min } = thresholdValues();
          const healthy = healthAccounts.filter(a => a.health_score >= healthy_min).length;
          const atRisk = healthAccounts.filter(a => a.health_score >= at_risk_min && a.health_score < healthy_min).length;
          const critical = healthAccounts.filter(a => a.health_score < at_risk_min).length;
          const avgScore = healthAccounts.length > 0 
            ? healthAccounts.reduce((sum, a) => sum + a.health_score, 0) / healthAccounts.length 
            : 0;
          
          // Calculate total ARR
          const totalArr = accountsArray.reduce((sum: number, acc: any) => sum + (acc.revenue || 0), 0);
          const arrAtRisk = accountsArray
            .filter((acc: any) => {
              const accHealth = healthAccounts.find(a => String(a.account_id) === String(acc.account_id));
              return accHealth && accHealth.health_score < 80;
            })
            .reduce((sum: number, acc: any) => sum + (acc.revenue || 0), 0);
          
          setPortfolio(prev => ({
            ...prev,
            total_accounts: healthAccounts.length,
            healthy_count: healthy,
            at_risk_count: atRisk,
            critical_count: critical,
            avg_health_score: Math.round(avgScore),
            total_arr: totalArr,
            arr_at_risk: arrAtRisk,
            expansion_pipeline: accountsArray
              .filter((acc: any) => {
                const accHealth = healthAccounts.find(a => String(a.account_id) === String(acc.account_id));
                return accHealth && accHealth.expansion_probability > 50;
              })
              .reduce((sum: number, acc: any) => sum + (acc.revenue || 0), 0)
          }));
        } else {
          console.warn('No accounts found for customer', session.customer_id);
          // Clear accounts and reset portfolio when no accounts found
          setAccounts([]);
          setPortfolio(prev => ({
            ...prev,
            total_accounts: 0,
            healthy_count: 0,
            at_risk_count: 0,
            critical_count: 0,
            avg_health_score: 0,
            total_arr: 0,
            arr_at_risk: 0,
            expansion_pipeline: 0
          }));
        }
      } else {
        console.error('Failed to fetch accounts:', accountsResponse.status, accountsResponse.statusText);
        // Clear accounts on error
        setAccounts([]);
        setPortfolio(prev => ({
          ...prev,
          total_accounts: 0,
          healthy_count: 0,
          at_risk_count: 0,
          critical_count: 0,
          avg_health_score: 0,
          total_arr: 0,
          arr_at_risk: 0,
          expansion_pipeline: 0
        }));
      }
      
      // Load CSM Daily Actions (DC vertical)
      try {
        setDailyLoading(true);
        const dailyRes = await fetch('/api/dc2s/daily-actions', {
          credentials: 'include',
          headers,
        });
        if (dailyRes.ok) {
          const dailyData = await dailyRes.json();
          setDailyActions(dailyData.actions || []);
          setDailySummary(dailyData.summary || { total_actions: 0, critical_count: 0, high_count: 0, opportunity_count: 0, total_estimated_hours: 0 });
        }
      } catch (dailyErr) {
        console.warn('Failed to load daily actions:', dailyErr);
      } finally {
        setDailyLoading(false);
      }

      setLastRefresh(new Date());
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      // Keep mock data on error
    } finally {
      setLoading(false);
    }
  };

  const handleViewJourney = (accountId: string) => {
    // Navigate to journey page - opens in same window
    navigate(`/journey-v3/${accountId}`, { replace: false });
  };

  const handleRunAnalysis = async (accountId: string) => {
    // Prevent multiple simultaneous analyses
    if (analyzingAccountId) {
      return;
    }

    setAnalyzingAccountId(accountId);
    
    try {
      const response = await fetch('/api/signal-analyst/analyze', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        credentials: 'include', // Include session cookies for authentication
        body: JSON.stringify({ 
          account_id: accountId,
          analysis_type: 'comprehensive'
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: `HTTP ${response.status}: ${response.statusText}` }));
        throw new Error(errorData.error || `Analysis failed with status ${response.status}`);
      }

      const result = await response.json();
      const healthScore = Number(result.health_score);
      const churnProb = Number(result.churn_probability);
      const expansionProb = result.expansion_probability != null ? Number(result.expansion_probability) : undefined;

      setReportByAccountId(prev => ({ ...prev, [accountId]: result }));

      setAccounts(prev => prev.map(acc => {
        if (acc.account_id === accountId) {
          const expansionVal: number = Number.isFinite(expansionProb) ? expansionProb as number : (acc.expansion_probability ?? 0);
          return {
            ...acc,
            health_score: Number.isFinite(healthScore) ? healthScore : acc.health_score,
            churn_probability: Number.isFinite(churnProb) ? churnProb : acc.churn_probability,
            expansion_probability: expansionVal,
            recommended_actions: (result.recommended_actions ?? []).map((a: { action?: string; title?: string }) =>
              typeof a === 'string' ? a : (a.action || a.title || '')
            ).filter(Boolean) as string[] || acc.recommended_actions,
            last_analysis: new Date().toISOString()
          };
        }
        return acc;
      }));

      const summary = result.reasoning
        ? result.reasoning.substring(0, 200) + (result.reasoning.length > 200 ? '...' : '')
        : result.key_insights?.join('\n• ') || 'Analysis completed successfully.';
      alert(`Analysis complete.\n\nHealth Score: ${result.health_score ?? 'N/A'}\nChurn Risk: ${result.churn_probability ?? 'N/A'}%\nExpansion: ${result.expansion_probability ?? 'N/A'}%\n\nClick "See detailed report" on this card for the full report.`);
    } catch (error) {
      console.error('Error running analysis:', error);
      const errorMessage = error instanceof Error ? error.message : 'Analysis failed. Please try again.';
      alert(`Analysis Failed\n\n${errorMessage}\n\nPlease check:\n- You are logged in\n- Account ID is valid\n- Backend services are running`);
    } finally {
      setAnalyzingAccountId(null);
    }
  };

  const handleActionClick = (action: SmartAction) => {
    if (action.action_type === 'expansion' || action.action_type === 'meeting') {
      navigate(`/journey-v3/${action.account_id}`);
    } else {
      handleRunAnalysis(action.account_id);
    }
  };

  const handleShowReport = (report: AnalysisReport) => {
    setReportModalContent(report);
    setShowReportModal(true);
  };

  const handleDailyActionStart = (action: DailyAction) => {
    if (action.action_type === 'playbook' && action.related_playbook_id) {
      navigate('/dc-dashboard/playbooks');
    } else if (action.action_type === 'expansion') {
      navigate(`/journey-v3/${action.account_id}`);
    } else {
      navigate(`/dc-dashboard/tenants/${action.account_id}`);
    }
  };

  const handleViewDailyAccount = (accountId: number | string) => {
    navigate(`/dc-dashboard/tenants/${accountId}`);
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Welcome Banner (Starter, first visit only) */}
        {isStarter && !welcomeDismissed && (
          <div className="mb-6 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-6 relative">
            <button
              onClick={dismissWelcome}
              className="absolute top-3 right-3 text-gray-400 hover:text-gray-600"
              aria-label="Dismiss"
            >
              <XIcon className="h-4 w-4" />
            </button>
            <div className="flex items-start space-x-4">
              <div className="bg-blue-100 rounded-full p-3">
                <Rocket className="h-6 w-6 text-blue-600" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 mb-1">
                  Welcome, {session?.user_name?.split(' ')[0] || 'there'}! Here's your quick start:
                </h3>
                <ol className="text-sm text-gray-600 space-y-1 mb-4">
                  <li className="flex items-center">
                    <span className="bg-blue-100 text-blue-700 rounded-full w-5 h-5 flex items-center justify-center text-xs font-bold mr-2">1</span>
                    Upload your data
                    <button onClick={() => navigate('/dc-dashboard/data-integration')} className="ml-2 text-blue-600 hover:text-blue-700 text-xs font-medium underline">Upload Now</button>
                  </li>
                  <li className="flex items-center">
                    <span className="bg-blue-100 text-blue-700 rounded-full w-5 h-5 flex items-center justify-center text-xs font-bold mr-2">2</span>
                    Review your accounts
                    <button onClick={() => navigate('/dc-dashboard/tenants')} className="ml-2 text-blue-600 hover:text-blue-700 text-xs font-medium underline">View Accounts</button>
                  </li>
                  <li className="flex items-center">
                    <span className="bg-blue-100 text-blue-700 rounded-full w-5 h-5 flex items-center justify-center text-xs font-bold mr-2">3</span>
                    Check your daily actions (shown below)
                  </li>
                </ol>
                <button
                  onClick={dismissWelcome}
                  className="text-xs text-gray-400 hover:text-gray-600"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {isStarter ? 'Portfolio Overview' : 'CS Pulse Dashboard'}
            </h1>
            <p className="text-gray-600">
              {isStarter ? 'Your accounts at a glance' : 'Portfolio Health & Intelligence'}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-500">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </span>
            <button
              onClick={loadDashboardData}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Portfolio Overview */}
        <div data-tour="health-scores">
          <PortfolioOverview summary={portfolio} />
        </div>

        {/* Data quality: all placeholder scores = no KPI/health-trend data */}
        {accounts.length > 0 && accounts.every(a => a.isPlaceholderScore) && (
          <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm text-amber-800">
              <strong>Health scores are placeholders.</strong> No KPI or health-trend data has been uploaded for these accounts. Upload KPI data (Settings → Data or CSV upload) and run health rollup to see real pillar and health scores.
            </p>
          </div>
        )}

        {/* CSM Daily Actions — prioritised morning TODO */}
        <div data-tour="smart-actions">
        <DailyActionsPanel
          actions={dailyActions}
          summary={dailySummary}
          filter={dailyFilter}
          onFilterChange={setDailyFilter}
          loading={dailyLoading}
          onStartPlaybook={handleDailyActionStart}
          onViewAccount={handleViewDailyAccount}
        />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Smart Actions - 2 columns */}
          <div className="lg:col-span-2">
            <SmartActionsPanel actions={actions} onAction={handleActionClick} />
            <HealthTrendChart data={trendData} />
          </div>

          {/* Distribution Chart - 1 column */}
          <div>
            <HealthDistributionChart summary={portfolio} />
          </div>
        </div>

        {/* Account Cards */}
        <div className="mb-6">
          <h2 className="text-lg font-semibold mb-4">Account Health Cards</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {accounts.map(account => (
              <AccountHealthCard
                key={account.account_id}
                account={account}
                onViewJourney={handleViewJourney}
                onRunAnalysis={handleRunAnalysis}
                isAnalyzing={analyzingAccountId === account.account_id}
                report={reportByAccountId[account.account_id] ?? null}
                onShowReport={handleShowReport}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Detailed Report Modal */}
      {showReportModal && reportModalContent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setShowReportModal(false)}>
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="p-4 border-b flex justify-between items-center">
              <h3 className="text-lg font-semibold">Analysis Report</h3>
              <button className="p-2 text-gray-500 hover:text-gray-700" onClick={() => setShowReportModal(false)} aria-label="Close">×</button>
            </div>
            <div className="p-4 overflow-y-auto flex-1 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><span className="text-gray-500">Health Score</span><p className="font-semibold">{reportModalContent.health_score ?? '—'}</p></div>
                <div><span className="text-gray-500">Churn Probability</span><p className="font-semibold">{reportModalContent.churn_probability != null ? `${reportModalContent.churn_probability}%` : '—'}</p></div>
                <div><span className="text-gray-500">Expansion Probability</span><p className="font-semibold">{reportModalContent.expansion_probability != null ? `${reportModalContent.expansion_probability}%` : '—'}</p></div>
                <div><span className="text-gray-500">Predicted Outcome</span><p className="font-semibold">{reportModalContent.predicted_outcome ?? '—'}</p></div>
              </div>
              {reportModalContent.reasoning && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-1">Reasoning</h4>
                  <p className="text-sm text-gray-600 whitespace-pre-wrap">{reportModalContent.reasoning}</p>
                </div>
              )}
              {reportModalContent.key_insights?.length ? (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-1">Key Insights</h4>
                  <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">{reportModalContent.key_insights.map((s, i) => <li key={i}>{s}</li>)}</ul>
                </div>
              ) : null}
              {reportModalContent.recommended_actions?.length ? (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-1">Recommended Actions</h4>
                  <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                    {reportModalContent.recommended_actions.map((a, i) => (
                      <li key={i}>{typeof a === 'string' ? a : (a.action || a.title || '')} {typeof a === 'object' && a.priority ? `(${a.priority})` : ''}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {reportModalContent.risk_drivers?.length ? (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-1">Risk Drivers</h4>
                  <ul className="list-disc list-inside text-sm text-gray-600">{reportModalContent.risk_drivers.map((r, i) => <li key={i}>{r.driver ?? ''}</li>)}</ul>
                </div>
              ) : null}
              {reportModalContent.growth_drivers?.length ? (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-1">Growth Drivers</h4>
                  <ul className="list-disc list-inside text-sm text-gray-600">{reportModalContent.growth_drivers.map((g, i) => <li key={i}>{g.driver ?? ''}</li>)}</ul>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExecutiveDashboard;
