/**
 * EmptyState — Reusable empty-state component for Starter tier
 * =============================================================
 *
 * Renders a friendly, actionable empty state with icon, title,
 * description, and optional CTA buttons. Used across all Starter-visible
 * pages when no data is present yet.
 */

import React from 'react';
import { Upload, ArrowRight } from 'lucide-react';

interface EmptyStateAction {
  label: string;
  onClick: () => void;
  primary?: boolean;
}

interface EmptyStateProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  action?: EmptyStateAction;
  secondaryAction?: EmptyStateAction;
  /** Optional hint text shown below the description */
  hint?: string;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  action,
  secondaryAction,
  hint,
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-8">
      <div className="bg-blue-50 rounded-full p-6 mb-6">
        <Icon className="h-12 w-12 text-blue-400" />
      </div>
      <h3 className="text-xl font-semibold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-500 text-center max-w-md mb-2">{description}</p>
      {hint && (
        <p className="text-sm text-gray-400 text-center max-w-sm mb-6 italic">{hint}</p>
      )}
      {(action || secondaryAction) && (
        <div className="flex items-center space-x-3 mt-4">
          {action && (
            <button
              onClick={action.onClick}
              className={`inline-flex items-center px-5 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                action.primary !== false
                  ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm hover:shadow-md'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {action.label}
              <ArrowRight className="h-4 w-4 ml-2" />
            </button>
          )}
          {secondaryAction && (
            <button
              onClick={secondaryAction.onClick}
              className="inline-flex items-center px-4 py-2.5 rounded-lg text-sm font-medium text-gray-600 hover:text-gray-800 hover:bg-gray-100 transition-all duration-200"
            >
              {secondaryAction.label}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default EmptyState;
