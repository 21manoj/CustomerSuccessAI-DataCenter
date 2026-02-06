/**
 * Analysis Results Page
 * =====================
 * 
 * Displays detailed Signal Analyst results after running analysis.
 * Shows health scores, risk drivers, growth drivers, and recommended actions.
 */

import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, TrendingUp, TrendingDown, AlertTriangle,
  CheckCircle, XCircle, Target, Activity, Shield,
  Lightbulb, Calendar, Users, DollarSign
} from 'lucide-react';
import {
  BarChart, Bar, PieChart, Pie, Cell, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';

interface SignalAnalystResult {
  analysis_id?: string;
  timestamp?: string;
  account_id: string;
  health_score: number;
  churn_probability: number;
  expansion_probability: number;
  confidence: number;
  confidence_level?: 'high' | 'medium' | 'low';
  predicted_outcome?: string;
  risk_drivers?: Array<{
    driver: string;
    impact: number | string;
    trend?: string;
    evidence?: string[];
    supporting_signals?: string[];
  }>;
  growth_drivers?: Array<{
    driver: string;
    potential: number;
    readiness?: string;
    evidence?: string[];
    supporting_signals?: string[];
  }>;
  recommended_actions?: Array<{
    action: string;
    priority: 'critical' | 'high' | 'medium' | 'low';
    timeline_days?: number;
    expected_impact?: string;
    playbook_id?: string;
  }>;
  signals_analyzed?: {
    quantitative?: number;
    qualitative?: number;
    historical?: number;
  };
  model_used?: string;
  analysis_duration_ms?: number;
}

const AnalysisResultsPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const result = location.state?.result as SignalAnalystResult | null;
  const accountName = location.state?.accountName || 'Account';
  const accountId = location.state?.accountId || '';

  if (!result) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">No Analysis Results</h2>
          <p className="text-gray-600 mb-4">No analysis results found. Please run analysis first.</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const getHealthColor = (score: number) => {
    if (score >= 70) return 'text-green-600';
    if (score >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getHealthBgColor = (score: number) => {
    if (score >= 70) return 'bg-green-100';
    if (score >= 50) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'bg-red-600 text-white';
      case 'high': return 'bg-orange-500 text-white';
      case 'medium': return 'bg-yellow-500 text-white';
      default: return 'bg-gray-400 text-white';
    }
  };

  const churnExpansionData = [
    { name: 'Churn Risk', value: result.churn_probability, fill: '#ef4444' },
    { name: 'Expansion Potential', value: result.expansion_probability, fill: '#22c55e' }
  ];

  const riskDriversData = (result.risk_drivers || []).map(driver => ({
    driver: driver.driver,
    impact: typeof driver.impact === 'number' ? driver.impact : 
            driver.impact === 'high' ? 70 : driver.impact === 'medium' ? 50 : 30
  }));

  const growthDriversData = (result.growth_drivers || []).map(driver => ({
    driver: driver.driver,
    potential: driver.potential
  }));

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 hover:bg-gray-100 rounded"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-xl font-bold">Signal Analyst Results</h1>
                <p className="text-sm text-gray-500">{accountName} • Account ID: {accountId}</p>
              </div>
            </div>
            {result.timestamp && (
              <div className="text-sm text-gray-500">
                {new Date(result.timestamp).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-600">Health Score</span>
              <Activity className="w-5 h-5 text-gray-400" />
            </div>
            <div className={`text-3xl font-bold ${getHealthColor(result.health_score)}`}>
              {result.health_score}
            </div>
            <div className={`mt-2 px-2 py-1 rounded text-xs w-fit ${getHealthBgColor(result.health_score)}`}>
              {result.health_score >= 70 ? 'Healthy' : result.health_score >= 50 ? 'At Risk' : 'Critical'}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-600">Churn Risk</span>
              <TrendingDown className="w-5 h-5 text-red-400" />
            </div>
            <div className={`text-3xl font-bold ${result.churn_probability > 50 ? 'text-red-600' : 'text-gray-700'}`}>
              {result.churn_probability}%
            </div>
            <div className="text-xs text-gray-500 mt-2">
              {result.churn_probability > 50 ? 'High Risk' : result.churn_probability > 30 ? 'Moderate Risk' : 'Low Risk'}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-600">Expansion Potential</span>
              <TrendingUp className="w-5 h-5 text-green-400" />
            </div>
            <div className={`text-3xl font-bold ${result.expansion_probability > 50 ? 'text-green-600' : 'text-gray-700'}`}>
              {result.expansion_probability}%
            </div>
            <div className="text-xs text-gray-500 mt-2">
              {result.expansion_probability > 50 ? 'High Potential' : result.expansion_probability > 30 ? 'Moderate Potential' : 'Low Potential'}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-600">Confidence</span>
              <Shield className="w-5 h-5 text-blue-400" />
            </div>
            <div className="text-3xl font-bold text-blue-600">
              {Math.round((result.confidence || 0) * 100)}%
            </div>
            <div className="text-xs text-gray-500 mt-2 capitalize">
              {result.confidence_level || 'medium'} confidence
            </div>
          </div>
        </div>

        {/* Churn vs Expansion Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Risk vs Opportunity</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={churnExpansionData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {churnExpansionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Risk Drivers */}
        {result.risk_drivers && result.risk_drivers.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              Risk Drivers
            </h2>
            <div className="h-64 mb-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={riskDriversData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="driver" angle={-45} textAnchor="end" height={100} />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Bar dataKey="impact" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-3">
              {result.risk_drivers.map((driver, i) => (
                <div key={i} className="border-l-4 border-red-500 pl-4 py-2">
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-medium">{driver.driver}</h3>
                    <span className="text-sm text-gray-500">
                      Impact: {typeof driver.impact === 'number' ? driver.impact : driver.impact}
                    </span>
                  </div>
                  {driver.evidence && driver.evidence.length > 0 && (
                    <ul className="text-sm text-gray-600 mt-1 space-y-1">
                      {driver.evidence.map((evidence, j) => (
                        <li key={j} className="flex items-start gap-2">
                          <span className="text-red-500">•</span>
                          <span>{evidence}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Growth Drivers */}
        {result.growth_drivers && result.growth_drivers.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-500" />
              Growth Drivers
            </h2>
            <div className="h-64 mb-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={growthDriversData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="driver" angle={-45} textAnchor="end" height={100} />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Bar dataKey="potential" fill="#22c55e" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-3">
              {result.growth_drivers.map((driver, i) => (
                <div key={i} className="border-l-4 border-green-500 pl-4 py-2">
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-medium">{driver.driver}</h3>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-500">
                        Potential: {driver.potential}%
                      </span>
                      {driver.readiness && (
                        <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded">
                          {driver.readiness}
                        </span>
                      )}
                    </div>
                  </div>
                  {driver.evidence && driver.evidence.length > 0 && (
                    <ul className="text-sm text-gray-600 mt-1 space-y-1">
                      {driver.evidence.map((evidence, j) => (
                        <li key={j} className="flex items-start gap-2">
                          <span className="text-green-500">•</span>
                          <span>{evidence}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommended Actions */}
        {result.recommended_actions && result.recommended_actions.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-yellow-500" />
              Recommended Actions
            </h2>
            <div className="space-y-4">
              {result.recommended_actions.map((action, i) => (
                <div key={i} className="border rounded-lg p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <h3 className="font-medium mb-1">{action.action}</h3>
                      {action.expected_impact && (
                        <p className="text-sm text-gray-600">{action.expected_impact}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-1 rounded ${getPriorityColor(action.priority)}`}>
                        {action.priority.toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-gray-500 mt-2">
                    {action.timeline_days && (
                      <span className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {action.timeline_days} days
                      </span>
                    )}
                    {action.playbook_id && (
                      <span className="flex items-center gap-1">
                        <Target className="w-4 h-4" />
                        {action.playbook_id}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Analysis Metadata */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Analysis Details</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            {result.signals_analyzed && (
              <>
                <div>
                  <span className="text-gray-600">Quantitative Signals:</span>
                  <div className="font-semibold">{result.signals_analyzed.quantitative || 0}</div>
                </div>
                <div>
                  <span className="text-gray-600">Qualitative Signals:</span>
                  <div className="font-semibold">{result.signals_analyzed.qualitative || 0}</div>
                </div>
                <div>
                  <span className="text-gray-600">Historical Data Points:</span>
                  <div className="font-semibold">{result.signals_analyzed.historical || 0}</div>
                </div>
              </>
            )}
            {result.model_used && (
              <div>
                <span className="text-gray-600">Model:</span>
                <div className="font-semibold">{result.model_used}</div>
              </div>
            )}
            {result.analysis_duration_ms && (
              <div>
                <span className="text-gray-600">Duration:</span>
                <div className="font-semibold">{(result.analysis_duration_ms / 1000).toFixed(1)}s</div>
              </div>
            )}
            {result.predicted_outcome && (
              <div>
                <span className="text-gray-600">Predicted Outcome:</span>
                <div className="font-semibold capitalize">
                  {result.predicted_outcome.replace('_', ' ')}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-4">
          <button
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            Back to Dashboard
          </button>
          <button
            onClick={() => navigate(`/journey-v3/${accountId}`)}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            View Journey Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};

export default AnalysisResultsPage;
