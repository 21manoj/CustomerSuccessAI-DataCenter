import React from 'react';
import { VerticalOption } from '../../utils/onboardingApi';

interface VerticalSelectorProps {
  verticals: VerticalOption[];
  selectedVertical: string | null;
  onSelect: (verticalId: string) => void;
  onCustom: () => void;
}

const VerticalSelector: React.FC<VerticalSelectorProps> = ({
  verticals,
  selectedVertical,
  onSelect,
  onCustom
}) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4 py-12">
      <div className="max-w-4xl w-full">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">👋 Welcome to CS Pulse Growth!</h1>
          <p className="text-lg text-gray-600">Let's get you started with the SaaS Customer Success framework.</p>
        </div>

        <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6 text-center">
            What type of customers do you manage?
          </h2>

          <div className="grid grid-cols-1 gap-6 mb-6">
            {verticals.map((vertical) => (
              <button
                key={vertical.id}
                onClick={() => onSelect(vertical.id)}
                className={`p-8 rounded-lg border-2 transition-all duration-200 text-left hover:shadow-lg ${
                  selectedVertical === vertical.id
                    ? 'border-blue-600 bg-blue-50 shadow-md'
                    : 'border-gray-200 bg-white hover:border-blue-300'
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className="text-5xl">{vertical.icon}</div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-gray-900 mb-2">{vertical.name}</h3>
                    <p className="text-sm text-gray-600 mb-4">{vertical.description}</p>
                    <div className="flex items-center gap-4 text-sm text-gray-500 mb-3">
                      <span className="font-medium">{vertical.kpiCount} KPIs</span>
                      <span className="font-medium">{vertical.categories.length} Pillars</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {vertical.categories.map((cat, idx) => (
                        <span key={idx} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                          {cat.replace(' KPI', '')}
                        </span>
                      ))}
                    </div>
                    {selectedVertical === vertical.id && (
                      <div className="mt-4 pt-4 border-t border-blue-200">
                        <p className="text-sm font-medium text-blue-600">✓ Selected - Ready to continue</p>
                      </div>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>

          <div className="text-center mt-4">
            <p className="text-sm text-gray-500">
              This framework includes 59 KPIs across 5 pillars: Product Usage, Support, Customer Sentiment, Business Outcomes, and Relationship Strength
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VerticalSelector;

