/**
 * CS Pulse Executive Dashboard — DC2_S Vertical
 * ===============================================
 *
 * Portfolio-level view optimized for CSM workflow:
 * - Portfolio Health Overview (Healthy/At-Risk/Critical counts + ARR)
 * - At-Risk & Critical accounts front-and-center (user requirement)
 * - Signal Alert sidebar with recent negative signals
 * - Health Trend Chart (portfolio avg over time)
 * - Account Health Cards with DC2_S pillar scores
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../../contexts/SessionContext';
import {
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import {
  AlertTriangle, TrendingUp, TrendingDown, Minus,
  Users, Activity, Target, ChevronRight,
  Calendar, Shield, Zap, Server, CheckCircle,
  XCircle, AlertCircle, Play, Eye, RefreshCw,
  MessageSquare, Bell, Cpu, BarChart3
} from 'lucide-react';

// ============================================================================
// DC2_S PILLAR CONFIG
// ============================================================================

const DC2S_PILLARS = [
  { key: 'P1', label: 'Deployment', icon: <Zap className="w-4 h-4" /> },
  { key: 'P2', label: 'Stability', icon: <Shield className="w-4 h-4" /> },
  { key: 'P3', label: 'AI Workload', icon: <Cpu className="w-4 h-4" /> },
  { key: 'P4', label: 'Partner', icon: <Users className="w-4 h-4" /> },
  { key: 'P5', label: 'Expansion', icon: <BarChart3 className="w-4 h-4" /> },
];

// ============================================================================
// TYPES
// ============================================================================

interface AccountSummary {
  account_id: number;
  account_name: string;
  health_score: number;
  status: 'healthy' | 'risk' | 'critical';
  confidence: string;
  attach_rate: number;
  revenue: number;
  industry: string;
  region: string;
  pillar_scores: Record<string, number>;
  recent_negative_signals: number;
  pattern_type: string;
}

interface PortfolioData {
  total_accounts: number;
  healthy_count: number;
  at_risk_count: number;
  critical_count: number;
  total_arr: number;
  arr_at_risk: number;
  avg_health_score: number;
  accounts: AccountSummary[];
}

interface Signal {
  signal_id: string;
  account_id: number;
  account_name?: string;
  signal_date: string;
  signal_type: string;
  content: string;
  sentiment: string;
  sentiment_score: number;
  stakeholder_level?: string;
}

// ============================================================================
// HELPER COMPONENTS
// ============================================================================

const TrendIndicator: React.FC<{ value?: number }> = ({ value }) => {
  if (!value) return <span className="flex items-center text-gray-500 text-sm"><Minus className="w-4 h-4 mr-1" />Stable</span>;
  if (value > 0) {
    return <span className="flex items-center text-green-600 text-sm"><TrendingUp className="w-4 h-4 mr-1" />+{value.toFixed(1)}</span>;
  }
  return <span className="flex items-center text-red-600 text-sm"><TrendingDown className="w-4 h-4 mr-1" />{value.toFixed(1)}</span>;
};

const HealthBadge: React.FC<{ status: string; score: number }> = ({ status, score }) => {
  const config = {
    healthy: 'bg-green-100 text-green-800',
    risk: 'bg-yellow-100 text-yellow-800',
    critical: 'bg-red-100 text-red-800',
  }[status] || 'bg-gray-100 text-gray-800';

  const label = { healthy: 'Healthy', risk: 'At Risk', critical: 'Critical' }[status] || status;

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${config}`}>
      {label} ({score})
    </span>
  );
};

const ProgressBar: React.FC<{ value: number; color?: string }> = ({ value, color = 'blue' }) => {
  const colorClass = {
    green: 'bg-green-500', yellow: 'bg-yellow-500', red: 'bg-red-500', blue: 'bg-blue-500'
  }[color] || 'bg-blue-500';

  return (
    <div className="w-full bg-gray-200 rounded-full h-2">
      <div className={`h-2 rounded-full ${colorClass}`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
};

const getScoreColor = (score: number) => {
  if (score >= 75) return 'green';
  if (score >= 40) return 'yellow';
  return 'red';
};

// ============================================================================
// PORTFOLIO OVERVIEW
// ============================================================================

const PortfolioOverview: React.FC<{ data: PortfolioData }> = ({ data }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Total Accounts</p>
            <p className="text-3xl font-bold text-gray-900 mt-1">{data.total_accounts}</p>
          </div>
          <div className="bg-blue-50 p-3 rounded-lg">
            <Users className="w-6 h-6 text-blue-600" />
          </div>
        </div>
        <p className="text-sm text-gray-500 mt-3">Avg Health: <span className="font-semibold text-gray-700">{data.avg_health_score}</span></p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <p className="text-sm font-medium text-gray-500 mb-3">Health Distribution</p>
        <div className="flex items-center gap-3">
          <div className="flex-1 text-center">
            <div className="text-2xl font-bold text-green-600">{data.healthy_count}</div>
            <div className="text-xs text-gray-500 mt-1">Healthy</div>
          </div>
          <div className="w-px h-10 bg-gray-200" />
          <div className="flex-1 text-center">
            <div className="text-2xl font-bold text-yellow-600">{data.at_risk_count}</div>
            <div className="text-xs text-gray-500 mt-1">At Risk</div>
          </div>
          <div className="w-px h-10 bg-gray-200" />
          <div className="flex-1 text-center">
            <div className="text-2xl font-bold text-red-600">{data.critical_count}</div>
            <div className="text-xs text-gray-500 mt-1">Critical</div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">ARR at Risk</p>
            <p className="text-3xl font-bold text-red-600 mt-1">
              ${data.arr_at_risk >= 1000000 ? `${(data.arr_at_risk / 1000000).toFixed(1)}M` : `${(data.arr_at_risk / 1000).toFixed(0)}K`}
            </p>
          </div>
          <div className="bg-red-50 p-3 rounded-lg">
            <AlertTriangle className="w-6 h-6 text-red-600" />
          </div>
        </div>
        <p className="text-sm text-gray-500 mt-3">
          {data.total_arr > 0 ? `${((data.arr_at_risk / data.total_arr) * 100).toFixed(0)}% of $${(data.total_arr / 1000000).toFixed(1)}M total` : '—'}
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500">Attach Rate</p>
            <p className="text-3xl font-bold text-blue-600 mt-1">
              {data.accounts.length > 0 ? `${Math.round(data.accounts.reduce((s, a) => s + a.attach_rate, 0) / data.accounts.length * 100)}%` : '—'}
            </p>
          </div>
          <div className="bg-blue-50 p-3 rounded-lg">
            <Target className="w-6 h-6 text-blue-600" />
          </div>
        </div>
        <p className="text-sm text-gray-500 mt-3">KPI coverage across portfolio</p>
      </div>
    </div>
  );
};

// ============================================================================
// SIGNAL ALERTS SIDEBAR
// ============================================================================

const SignalAlertsSidebar: React.FC<{ signals: Signal[]; onViewAccount: (id: number) => void }> = ({ signals, onViewAccount }) => {
  const negativeSignals = signals.filter(s => s.sentiment === 'negative').slice(0, 8);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="p-4 border-b bg-red-50/50 flex items-center justify-between">
        <div className="flex items-center">
          <Bell className="w-5 h-5 text-red-500 mr-2" />
          <h3 className="font-semibold text-gray-900">Signal Alerts</h3>
        </div>
        <span className="text-xs text-red-600 font-medium bg-red-100 px-2 py-0.5 rounded-full">
          {negativeSignals.length} alerts
        </span>
      </div>
      <div className="divide-y max-h-96 overflow-y-auto">
        {negativeSignals.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">
            <CheckCircle className="w-8 h-8 text-green-400 mx-auto mb-2" />
            No negative signals
          </div>
        ) : (
          negativeSignals.map((sig, i) => (
            <div
              key={sig.signal_id || i}
              className="p-3 hover:bg-red-50/30 cursor-pointer transition"
              onClick={() => onViewAccount(sig.account_id)}
            >
              <div className="flex items-start justify-between mb-1">
                <span className="text-xs font-medium text-red-700 bg-red-100 px-1.5 py-0.5 rounded">
                  {sig.signal_type}
                </span>
                <span className="text-xs text-gray-400">{sig.signal_date}</span>
              </div>
              <p className="text-sm font-medium text-gray-900 mb-0.5">{sig.account_name}</p>
              <p className="text-xs text-gray-600 line-clamp-2">{sig.content}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

// ============================================================================
// ACCOUNT HEALTH CARD
// ============================================================================

const AccountHealthCard: React.FC<{
  account: AccountSummary;
  onViewJourney: (id: number) => void;
  onViewDetails: (id: number) => void;
}> = ({ account, onViewJourney, onViewDetails }) => {
  const scoreColor = account.health_score >= 75 ? '#16a34a' : account.health_score >= 40 ? '#ca8a04' : '#dc2626';
  const borderColor = account.status === 'critical' ? 'border-l-red-500' : account.status === 'risk' ? 'border-l-yellow-500' : 'border-l-green-500';

  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-100 border-l-4 ${borderColor} overflow-hidden hover:shadow-md transition-shadow`}>
      {/* Header */}
      <div className="p-4 pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900 truncate">{account.account_name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-gray-500">{account.industry}</span>
              <span className="text-xs text-gray-400">|</span>
              <span className="text-xs text-gray-500">{account.region}</span>
            </div>
          </div>
          <div className="text-right ml-3">
            <div className="text-2xl font-bold" style={{ color: scoreColor }}>{account.health_score}</div>
            <HealthBadge status={account.status} score={account.health_score} />
          </div>
        </div>
      </div>

      {/* Pillar Scores */}
      <div className="px-4 pb-3 space-y-1.5">
        {DC2S_PILLARS.map(pillar => {
          const score = account.pillar_scores[pillar.key] || 0;
          return (
            <div key={pillar.key} className="flex items-center">
              <div className="w-24 flex items-center text-xs text-gray-600">
                {pillar.icon}
                <span className="ml-1.5">{pillar.label}</span>
              </div>
              <div className="flex-1 mx-2">
                <ProgressBar value={score} color={getScoreColor(score)} />
              </div>
              <div className="w-8 text-right text-xs font-medium text-gray-700">{Math.round(score)}</div>
            </div>
          );
        })}
      </div>

      {/* Confidence & Revenue */}
      <div className="px-4 pb-3 flex items-center justify-between text-xs text-gray-500">
        <span>Confidence: <span className="font-medium text-gray-700">{account.confidence}</span></span>
        <span>ARR: <span className="font-medium text-gray-700">${(account.revenue / 1000000).toFixed(1)}M</span></span>
        {account.recent_negative_signals > 0 && (
          <span className="flex items-center text-red-600">
            <AlertTriangle className="w-3 h-3 mr-0.5" />{account.recent_negative_signals} alerts
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="px-4 pb-4 flex gap-2">
        <button
          onClick={() => onViewDetails(account.account_id)}
          className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 text-sm font-medium transition"
        >
          <Eye className="w-4 h-4" />
          Details
        </button>
        <button
          onClick={() => onViewJourney(account.account_id)}
          className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 text-sm font-medium transition"
        >
          <Activity className="w-4 h-4" />
          Journey
        </button>
      </div>
    </div>
  );
};

// ============================================================================
// HEALTH DISTRIBUTION CHART
// ============================================================================

const HealthDistributionChart: React.FC<{ data: PortfolioData }> = ({ data }) => {
  const chartData = [
    { name: 'Healthy', value: data.healthy_count, color: '#16a34a' },
    { name: 'At Risk', value: data.at_risk_count, color: '#ca8a04' },
    { name: 'Critical', value: data.critical_count, color: '#dc2626' },
  ].filter(d => d.value > 0);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Health Distribution</h3>
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={chartData} cx="50%" cy="50%" innerRadius={40} outerRadius={65} paddingAngle={3} dataKey="value">
              {chartData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="flex justify-center gap-4 mt-2">
        {chartData.map(item => (
          <div key={item.name} className="flex items-center text-xs">
            <div className="w-2.5 h-2.5 rounded-full mr-1.5" style={{ backgroundColor: item.color }} />
            <span className="text-gray-600">{item.name}: {item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// MAIN DASHBOARD
// ============================================================================

const ExecutiveDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { session } = useSession();

  const [portfolio, setPortfolio] = useState<PortfolioData>({
    total_accounts: 0, healthy_count: 0, at_risk_count: 0, critical_count: 0,
    total_arr: 0, arr_at_risk: 0, avg_health_score: 0, accounts: [],
  });
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  useEffect(() => {
    if (session?.customer_id) {
      loadDashboardData();
    }
  }, [session?.customer_id]);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      // Single API call for portfolio — includes all accounts with health scores
      const [portfolioRes, signalsRes] = await Promise.all([
        fetch('/api/dc2s/portfolio', { credentials: 'include' }),
        fetch('/api/dc2s/signals/all?limit=50', { credentials: 'include' }),
      ]);

      if (portfolioRes.ok) {
        const data = await portfolioRes.json();
        setPortfolio(data);
      }

      if (signalsRes.ok) {
        const data = await signalsRes.json();
        setSignals(data.signals || []);
      }

      setLastRefresh(new Date());
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleViewJourney = (accountId: number) => {
    navigate(`/journey-v3/${accountId}`);
  };

  const handleViewDetails = (accountId: number) => {
    navigate(`/dc-dashboard/tenants/${accountId}`);
  };

  // Separate accounts by status — show at-risk/critical first (user requirement)
  const criticalAccounts = portfolio.accounts.filter(a => a.status === 'critical');
  const riskAccounts = portfolio.accounts.filter(a => a.status === 'risk');
  const healthyAccounts = portfolio.accounts.filter(a => a.status === 'healthy');
  const attentionAccounts = [...criticalAccounts, ...riskAccounts];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Executive Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">DC2_S Portfolio Health & Intelligence</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">
            Updated {lastRefresh.toLocaleTimeString()}
          </span>
          <button
            onClick={loadDashboardData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {loading && portfolio.total_accounts === 0 ? (
        <div className="text-center py-20">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
          <p className="text-gray-500">Loading portfolio data...</p>
        </div>
      ) : (
        <>
          {/* Portfolio Overview Cards */}
          <PortfolioOverview data={portfolio} />

          {/* Main Content: Accounts needing attention + Signal Alerts */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: At-Risk & Critical Accounts (2 cols) */}
            <div className="lg:col-span-2 space-y-4">
              {attentionAccounts.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <AlertCircle className="w-5 h-5 text-red-500" />
                    <h2 className="text-lg font-semibold text-gray-900">Accounts Needing Attention</h2>
                    <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-medium">
                      {attentionAccounts.length}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {attentionAccounts.map(account => (
                      <AccountHealthCard
                        key={account.account_id}
                        account={account}
                        onViewJourney={handleViewJourney}
                        onViewDetails={handleViewDetails}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Distribution Chart + Healthy Accounts */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <HealthDistributionChart data={portfolio} />

                {/* Healthy Accounts Summary */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <h3 className="text-sm font-semibold text-gray-700">Healthy Accounts</h3>
                  </div>
                  {healthyAccounts.length === 0 ? (
                    <p className="text-sm text-gray-500">No accounts at healthy status</p>
                  ) : (
                    <div className="space-y-2.5">
                      {healthyAccounts.map(acc => (
                        <div
                          key={acc.account_id}
                          className="flex items-center justify-between p-2.5 rounded-lg bg-green-50/50 hover:bg-green-50 cursor-pointer transition"
                          onClick={() => handleViewDetails(acc.account_id)}
                        >
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">{acc.account_name}</p>
                            <p className="text-xs text-gray-500">{acc.industry}</p>
                          </div>
                          <div className="flex items-center gap-2 ml-3">
                            <span className="text-lg font-bold text-green-600">{acc.health_score}</span>
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Right: Signal Alerts Sidebar (1 col) */}
            <div>
              <SignalAlertsSidebar signals={signals} onViewAccount={handleViewDetails} />
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ExecutiveDashboard;
