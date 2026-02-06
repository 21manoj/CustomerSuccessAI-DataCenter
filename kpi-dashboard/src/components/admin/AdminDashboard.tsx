import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Settings, 
  AlertTriangle, 
  CheckCircle, 
  Activity,
  BarChart3,
  RefreshCw,
  Download,
  Brain,
  Scale,
  Eye
} from 'lucide-react';
import WizardBInsights from './WizardBInsights';
import WizardCWeights from './WizardCWeights';

// ============================================================
// TYPES
// ============================================================

interface AdminSummary {
  wizard_b: {
    total_patterns: number;
    total_accounts: number;
    last_analysis: string | null;
  };
  wizard_c: {
    current_accuracy: number;
    weight_source: string;
    last_calibration: string | null;
  };
  status: string;
}

// ============================================================
// MAIN COMPONENT
// ============================================================

const AdminDashboard: React.FC = () => {
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'wizard-b' | 'wizard-c'>('overview');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAdminSummary();
  }, []);

  const fetchAdminSummary = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/admin/summary');
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      setSummary(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching admin summary:', err);
      setError('Failed to load admin dashboard. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading Admin Insights...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-2xl w-full">
          <div className="flex items-start space-x-4">
            <AlertTriangle className="w-12 h-12 text-yellow-500 flex-shrink-0" />
            <div className="flex-1">
              <h2 className="text-xl font-bold text-gray-900 mb-2">Setup Required</h2>
              <p className="text-gray-600 mb-4">{error}</p>
              <div className="bg-gray-50 rounded-lg p-4 mb-4">
                <p className="text-sm font-semibold text-gray-700 mb-2">Quick Setup:</p>
                <ol className="text-sm text-gray-600 space-y-1 list-decimal list-inside">
                  <li>Verify <code className="bg-gray-200 px-1 rounded">admin_api.py</code> is in backend/</li>
                  <li>Register blueprint in <code className="bg-gray-200 px-1 rounded">app.py</code></li>
                  <li>Restart the Flask server</li>
                </ol>
              </div>
              <button
                onClick={fetchAdminSummary}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center space-x-2"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Retry</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Brain className="w-8 h-8 text-purple-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Admin Insights</h1>
              <p className="text-sm text-gray-500">Platform Intelligence & Calibration</p>
            </div>
          </div>
          <button
            onClick={fetchAdminSummary}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center space-x-2"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white border-b border-gray-200 px-6">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
              activeTab === 'overview'
                ? 'border-purple-500 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Eye className="w-4 h-4" />
            <span>Overview</span>
          </button>
          <button
            onClick={() => setActiveTab('wizard-b')}
            className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
              activeTab === 'wizard-b'
                ? 'border-purple-500 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span>Pattern Analysis</span>
            <span className="bg-purple-100 text-purple-800 text-xs px-2 py-0.5 rounded-full">
              Wizard B
            </span>
          </button>
          <button
            onClick={() => setActiveTab('wizard-c')}
            className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
              activeTab === 'wizard-c'
                ? 'border-purple-500 text-purple-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Scale className="w-4 h-4" />
            <span>Weight Calibration</span>
            <span className="bg-purple-100 text-purple-800 text-xs px-2 py-0.5 rounded-full">
              Wizard C
            </span>
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {activeTab === 'overview' && summary && (
          <OverviewTab summary={summary} onNavigate={setActiveTab} />
        )}
        {activeTab === 'wizard-b' && <WizardBInsights />}
        {activeTab === 'wizard-c' && <WizardCWeights />}
      </div>
    </div>
  );
};

// ============================================================
// OVERVIEW TAB
// ============================================================

interface OverviewTabProps {
  summary: AdminSummary;
  onNavigate: (tab: 'overview' | 'wizard-b' | 'wizard-c') => void;
}

const OverviewTab: React.FC<OverviewTabProps> = ({ summary, onNavigate }) => {
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Patterns Card */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <BarChart3 className="w-6 h-6 text-blue-600" />
            </div>
            <span className="text-sm text-gray-500">Wizard B</span>
          </div>
          <h3 className="text-3xl font-bold text-gray-900 mb-1">
            {summary.wizard_b.total_patterns}
          </h3>
          <p className="text-sm text-gray-500 mb-2">Patterns Detected</p>
          <p className="text-xs text-gray-400">
            {summary.wizard_b.total_accounts} accounts analyzed
          </p>
        </div>

        {/* Accuracy Card */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
            <span className="text-sm text-gray-500">Wizard C</span>
          </div>
          <h3 className="text-3xl font-bold text-gray-900 mb-1">
            {(summary.wizard_c.current_accuracy * 100).toFixed(0)}%
          </h3>
          <p className="text-sm text-gray-500 mb-2">Model Accuracy</p>
          <p className="text-xs text-gray-400">
            Source: {summary.wizard_c.weight_source}
          </p>
        </div>

        {/* Last Analysis Card */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-purple-100 rounded-lg">
              <Activity className="w-6 h-6 text-purple-600" />
            </div>
            <span className="text-sm text-gray-500">Last Run</span>
          </div>
          <h3 className="text-lg font-bold text-gray-900 mb-1">
            {formatDate(summary.wizard_b.last_analysis)}
          </h3>
          <p className="text-sm text-gray-500 mb-2">Pattern Analysis</p>
          <p className="text-xs text-gray-400">
            Calibration: {formatDate(summary.wizard_c.last_calibration)}
          </p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={() => onNavigate('wizard-b')}
            className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <BarChart3 className="w-5 h-5 text-blue-600" />
              </div>
              <div className="text-left">
                <p className="font-medium text-gray-900">View Patterns</p>
                <p className="text-sm text-gray-500">Analyze customer behavior patterns</p>
              </div>
            </div>
            <span className="text-gray-400">→</span>
          </button>

          <button
            onClick={() => onNavigate('wizard-c')}
            className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <Scale className="w-5 h-5 text-green-600" />
              </div>
              <div className="text-left">
                <p className="font-medium text-gray-900">Calibrate Weights</p>
                <p className="text-sm text-gray-500">Optimize health scoring model</p>
              </div>
            </div>
            <span className="text-gray-400">→</span>
          </button>
        </div>
      </div>

      {/* System Health */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">System Health</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {summary.wizard_b.total_patterns > 0 ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-yellow-500" />
              )}
              <span className="text-gray-700">Wizard B (Pattern Analyzer)</span>
            </div>
            <span className={`text-sm font-medium ${
              summary.wizard_b.total_patterns > 0 ? 'text-green-600' : 'text-yellow-600'
            }`}>
              {summary.wizard_b.total_patterns > 0 ? 'Active' : 'Pending Analysis'}
            </span>
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {summary.wizard_c.weight_source === 'learned' ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-yellow-500" />
              )}
              <span className="text-gray-700">Wizard C (Weight Optimizer)</span>
            </div>
            <span className={`text-sm font-medium ${
              summary.wizard_c.weight_source === 'learned' ? 'text-green-600' : 'text-yellow-600'
            }`}>
              {summary.wizard_c.weight_source === 'learned' ? 'Optimized' : 'Using Defaults'}
            </span>
          </div>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span className="text-gray-700">Signal Analyst</span>
            </div>
            <span className="text-sm text-green-600 font-medium">Active</span>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span className="text-gray-700">RAG System</span>
            </div>
            <span className="text-sm text-green-600 font-medium">Active</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
