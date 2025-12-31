import React from 'react';
import { CheckCircle, BarChart3, AlertTriangle, Target, ArrowRight } from 'lucide-react';
import { ImportSummary } from '../../utils/onboardingApi';
import { useNavigate } from 'react-router-dom';

interface SuccessSummaryProps {
  summary: ImportSummary;
  onAction: (action: 'dashboard' | 'alerts' | 'assistant' | 'tour') => void;
}

const SuccessSummary: React.FC<SuccessSummaryProps> = ({ summary, onAction }) => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4 py-12">
      <div className="max-w-2xl w-full bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">🎉</div>
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Success! Your data is ready.</h2>
        </div>

        <div className="space-y-3 mb-8">
          <div className="flex items-center gap-3 text-gray-700">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <span>{summary.customersImported} customers imported</span>
          </div>
          <div className="flex items-center gap-3 text-gray-700">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <span>{summary.kpisProcessed} KPIs processed</span>
          </div>
          <div className="flex items-center gap-3 text-gray-700">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <span>{summary.healthyAccounts} healthy accounts identified</span>
          </div>
          <div className="flex items-center gap-3 text-gray-700">
            <CheckCircle className="h-5 w-5 text-yellow-600" />
            <span>{summary.atRiskAccounts} accounts need attention</span>
          </div>
          <div className="flex items-center gap-3 text-gray-700">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <span>{summary.priorityActions} high-priority actions created</span>
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8 text-center">
          <p className="text-sm text-gray-600 mb-2">📊 Your portfolio health score:</p>
          <p className="text-4xl font-bold text-blue-700">{summary.portfolioHealth}/100</p>
        </div>

        <div className="mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">What would you like to do next?</h3>
          <div className="space-y-3">
            <button
              onClick={() => {
                onAction('dashboard');
                navigate('/executive-dashboard');
              }}
              className="w-full flex items-center justify-between p-4 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
            >
              <div className="flex items-center gap-3">
                <BarChart3 className="h-5 w-5 text-blue-600" />
                <span className="font-medium text-gray-900">View Dashboard</span>
              </div>
              <span className="text-sm text-gray-600">See your health scores</span>
            </button>
            
            <button
              onClick={() => {
                onAction('alerts');
                navigate('/dashboard');
              }}
              className="w-full flex items-center justify-between p-4 bg-yellow-50 border border-yellow-200 rounded-lg hover:bg-yellow-100 transition-colors"
            >
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-yellow-600" />
                <span className="font-medium text-gray-900">Review Alerts</span>
              </div>
              <span className="text-sm text-gray-600">Check critical accounts</span>
            </button>
            
            <button
              onClick={() => {
                onAction('assistant');
                navigate('/dashboard');
              }}
              className="w-full flex items-center justify-between p-4 bg-purple-50 border border-purple-200 rounded-lg hover:bg-purple-100 transition-colors"
            >
              <div className="flex items-center gap-3">
                <Target className="h-5 w-5 text-purple-600" />
                <span className="font-medium text-gray-900">Explore AI Assistant</span>
              </div>
              <span className="text-sm text-gray-600">Ask questions</span>
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between pt-6 border-t border-gray-200">
          <button
            onClick={() => onAction('tour')}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            Take a Quick Tour
          </button>
          <button
            onClick={() => {
              onAction('dashboard');
              navigate('/executive-dashboard');
            }}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
          >
            Go to Dashboard
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default SuccessSummary;

