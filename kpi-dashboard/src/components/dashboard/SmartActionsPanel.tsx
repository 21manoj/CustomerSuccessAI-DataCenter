import React from 'react';
import { Calendar, BookOpen, BarChart3, FileText } from 'lucide-react';
import { SmartAction } from '../../utils/healthScoreApi';

interface SmartActionsPanelProps {
  actions: SmartAction[];
  onActionClick: (action: SmartAction, actionType: string) => void;
}

const SmartActionsPanel: React.FC<SmartActionsPanelProps> = ({ actions, onActionClick }) => {
  const urgencyConfig = {
    critical: {
      color: 'bg-red-50 border-red-200',
      icon: '🔴',
      label: 'URGENT'
    },
    high: {
      color: 'bg-yellow-50 border-yellow-200',
      icon: '🟡',
      label: 'THIS WEEK'
    },
    opportunity: {
      color: 'bg-green-50 border-green-200',
      icon: '🟢',
      label: 'OPPORTUNITY'
    }
  };

  const actionIcons = {
    schedule: <Calendar className="h-4 w-4" />,
    playbook: <BookOpen className="h-4 w-4" />,
    analysis: <BarChart3 className="h-4 w-4" />,
    template: <FileText className="h-4 w-4" />
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">💡 Smart Actions for Today</h2>
      
      <div className="space-y-4">
        {actions.map((action) => {
          const config = urgencyConfig[action.urgency];
          return (
            <div
              key={action.id}
              className={`border rounded-lg p-4 ${config.color}`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span>{config.icon}</span>
                    <span className="text-xs font-semibold text-gray-700">{config.label}:</span>
                    <span className="text-sm font-semibold text-gray-900">{action.title}</span>
                  </div>
                  <p className="text-sm text-gray-600 ml-6">→ {action.description}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-2 ml-6 mt-3">
                {action.actions.map((act, index) => (
                  <button
                    key={index}
                    onClick={() => onActionClick(action, act.type)}
                    className="px-3 py-1.5 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-1.5 transition-colors"
                  >
                    {actionIcons[act.type]}
                    {act.label}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default SmartActionsPanel;

