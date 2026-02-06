import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  DollarSign,
  Users,
  Activity,
  ChevronDown,
  ChevronUp,
  Download,
  RefreshCw,
  CheckCircle,
  XCircle
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

// ============================================================
// TYPES
// ============================================================

interface Pattern {
  pattern_type: string;
  n_accounts: number;
  avg_starting_health: number;
  avg_ending_health: number;
  health_change: number;
  avg_total_events: number;
  avg_csm_investment: number;
  financial_impact: string;
  success_factors: string[];
  phase_distribution: Record<string, number>;
}

interface EarlyWarningRule {
  rule_id: string;
  description: string;
  confidence: number;
  support: number;
  action: string;
}

// ============================================================
// CONSTANTS
// ============================================================

const PATTERN_COLORS: Record<string, string> = {
  proactive_growth: '#10b981',
  ignored_churn: '#ef4444',
  crisis_recovery: '#f59e0b',
  stable_healthy: '#3b82f6',
  at_risk: '#eab308'
};

const PATTERN_LABELS: Record<string, string> = {
  proactive_growth: 'Proactive Growth',
  ignored_churn: 'Ignored Churn',
  crisis_recovery: 'Crisis Recovery',
  stable_healthy: 'Stable Healthy',
  at_risk: 'At Risk'
};

// ============================================================
// MAIN COMPONENT
// ============================================================

const WizardBInsights: React.FC = () => {
  const [patterns, setPatterns] = useState<Record<string, Pattern> | null>(null);
  const [earlyWarnings, setEarlyWarnings] = useState<EarlyWarningRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedPattern, setExpandedPattern] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const handleTriggerWizardB = async () => {
    if (!window.confirm('This will run pattern analysis on the latest Wizard A output. This may take 1-2 minutes. Continue?')) {
      return;
    }

    try {
      setTriggering(true);
      setError(null);

      // Check session first
      const sessionCheck = await fetch('/api/session/status', {
        credentials: 'include',
      });

      if (!sessionCheck.ok || !(await sessionCheck.json()).authenticated) {
        alert('Please log in to access this resource');
        window.location.href = '/login';
        return;
      }

      const response = await fetch('/api/data/trigger-wizard-b', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      // Try to parse response as JSON, but handle non-JSON responses
      let data;
      try {
        data = await response.json();
      } catch (e) {
        // If response is not JSON, create a generic error
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}: ${response.statusText}`);
        }
        throw new Error('Invalid response from server');
      }

      if (!response.ok) {
        // Handle different error status codes
        if (response.status === 404) {
          throw new Error('Endpoint not found. Please ensure the backend server is running and restarted after the latest changes.');
        } else if (response.status === 401) {
          throw new Error('Authentication required. Please log in again.');
        } else if (response.status === 500) {
          throw new Error(data.message || data.error || 'Server error occurred. Check backend logs for details.');
        } else {
          throw new Error(data.message || data.error || `Request failed with status ${response.status}`);
        }
      }

      alert(`Wizard B completed successfully! Pattern analysis finished in ${data.duration_seconds}s`);
      
      // Refresh data
      await fetchData();
      
    } catch (err: any) {
      console.error('Error triggering Wizard B:', err);
      alert(`Failed to trigger Wizard B: ${err.message}`);
      setError(err.message);
    } finally {
      setTriggering(false);
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch patterns
      const patternsRes = await fetch('/api/admin/wizard-b/patterns', {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!patternsRes.ok) {
        if (patternsRes.status === 401) {
          setError('Authentication required. Please log in again.');
          return;
        }
        throw new Error('Failed to fetch patterns');
      }
      
      const patternsData = await patternsRes.json();
      setPatterns(patternsData.patterns || {});

      // Fetch early warnings
      const warningsRes = await fetch('/api/admin/wizard-b/early-warnings', {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!warningsRes.ok) {
        if (warningsRes.status === 401) {
          setError('Authentication required. Please log in again.');
          return;
        }
        throw new Error('Failed to fetch warnings');
      }
      
      const warningsData = await warningsRes.json();
      setEarlyWarnings(warningsData.rules || []);

      setError(null);
    } catch (err) {
      console.error('Error fetching Wizard B data:', err);
      setError('Failed to load pattern analysis data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-700 mb-4">{error}</p>
        <button
          onClick={fetchData}
          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  const patternList = patterns ? Object.entries(patterns) : [];
  const hasPatterns = patternList.length > 0;

  // Prepare chart data
  const pieData = patternList.map(([key, pattern]) => ({
    name: PATTERN_LABELS[key] || key,
    value: pattern.n_accounts,
    color: PATTERN_COLORS[key] || '#6b7280'
  }));

  const barData = patternList.map(([key, pattern]) => ({
    name: PATTERN_LABELS[key] || key,
    'Starting Health': pattern.avg_starting_health,
    'Ending Health': pattern.avg_ending_health,
    fill: PATTERN_COLORS[key] || '#6b7280'
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Pattern Analysis</h2>
          <p className="text-sm text-gray-500">
            Insights from Wizard B behavioral pattern detection
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={handleTriggerWizardB}
            disabled={triggering}
            className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {triggering ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4 mr-2" />
                Run Pattern Analysis
              </>
            )}
          </button>
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center space-x-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {!hasPatterns ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center">
          <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-yellow-800 mb-2">No Patterns Detected</h3>
          <p className="text-yellow-700 mb-4">
            Run Wizard B pattern analysis to detect customer behavior patterns.
          </p>
          <p className="text-sm text-yellow-600">
            Navigate to Settings → Data Management → Run Pattern Analysis
          </p>
        </div>
      ) : (
        <>
          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Pie Chart */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Pattern Distribution</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Bar Chart */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Health Score Comparison</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={barData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, 100]} />
                  <YAxis type="category" dataKey="name" width={120} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="Starting Health" fill="#94a3b8" />
                  <Bar dataKey="Ending Health" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Pattern Cards */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Pattern Details</h3>
            {patternList.map(([key, pattern]) => (
              <PatternCard
                key={key}
                patternKey={key}
                pattern={pattern}
                expanded={expandedPattern === key}
                onToggle={() => setExpandedPattern(expandedPattern === key ? null : key)}
              />
            ))}
          </div>

          {/* Early Warning Rules */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
              <span>Early Warning Rules</span>
            </h3>
            {earlyWarnings.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No early warning rules detected yet.</p>
            ) : (
              <div className="space-y-3">
                {earlyWarnings.map((rule) => (
                  <div key={rule.rule_id} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className="text-xs font-mono bg-gray-100 px-2 py-0.5 rounded">
                            {rule.rule_id}
                          </span>
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            rule.confidence >= 0.8 ? 'bg-green-100 text-green-800' :
                            rule.confidence >= 0.6 ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {(rule.confidence * 100).toFixed(0)}% confidence
                          </span>
                        </div>
                        <p className="text-gray-900 font-medium">{rule.description}</p>
                        <p className="text-sm text-gray-500 mt-1">
                          <strong>Action:</strong> {rule.action}
                        </p>
                      </div>
                      <span className="text-xs text-gray-400">
                        {rule.support} cases
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

// ============================================================
// PATTERN CARD COMPONENT
// ============================================================

interface PatternCardProps {
  patternKey: string;
  pattern: Pattern;
  expanded: boolean;
  onToggle: () => void;
}

const PatternCard: React.FC<PatternCardProps> = ({ patternKey, pattern, expanded, onToggle }) => {
  const color = PATTERN_COLORS[patternKey] || '#6b7280';
  const label = PATTERN_LABELS[patternKey] || patternKey;
  const healthChange = pattern.avg_ending_health - pattern.avg_starting_health;
  const isPositive = healthChange >= 0;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center space-x-4">
          <div
            className="w-4 h-4 rounded-full"
            style={{ backgroundColor: color }}
          />
          <div className="text-left">
            <h4 className="font-semibold text-gray-900">{label}</h4>
            <p className="text-sm text-gray-500">{pattern.n_accounts} accounts</p>
          </div>
        </div>
        <div className="flex items-center space-x-6">
          <div className="text-right">
            <p className="text-sm text-gray-500">Health Change</p>
            <p className={`font-semibold flex items-center ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
              {isPositive ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
              {isPositive ? '+' : ''}{healthChange.toFixed(1)}
            </p>
          </div>
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-6 pb-6 border-t border-gray-100">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">Starting Health</p>
              <p className="text-lg font-semibold text-gray-900">
                {pattern.avg_starting_health.toFixed(1)}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">Ending Health</p>
              <p className="text-lg font-semibold text-gray-900">
                {pattern.avg_ending_health.toFixed(1)}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">Avg Events</p>
              <p className="text-lg font-semibold text-gray-900">
                {pattern.avg_total_events.toFixed(0)}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">CSM Investment</p>
              <p className="text-lg font-semibold text-gray-900">
                {pattern.avg_csm_investment.toFixed(1)}h
              </p>
            </div>
          </div>

          {/* Success Factors */}
          {pattern.success_factors && pattern.success_factors.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Success Factors</p>
              <div className="flex flex-wrap gap-2">
                {pattern.success_factors.map((factor, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center px-3 py-1 rounded-full text-xs bg-green-100 text-green-800"
                  >
                    <CheckCircle className="w-3 h-3 mr-1" />
                    {factor}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Financial Impact */}
          {pattern.financial_impact && (
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>Financial Impact:</strong> {pattern.financial_impact}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default WizardBInsights;
