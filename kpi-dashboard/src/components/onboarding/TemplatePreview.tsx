import React from 'react';
import { TemplateInfo } from '../../utils/onboardingApi';

interface TemplatePreviewProps {
  template: TemplateInfo;
  vertical: string;
  onSkip: () => void;
  onContinue: () => void;
}

const TemplatePreview: React.FC<TemplatePreviewProps> = ({
  template,
  vertical,
  onSkip,
  onContinue
}) => {
  // Group KPIs by category
  const grouped = template.kpis.reduce<Record<string, typeof template.kpis>>((acc, kpi) => {
    if (!acc[kpi.category]) {
      acc[kpi.category] = [];
    }
    acc[kpi.category].push(kpi);
    return acc;
  }, {});

  const categories = Object.keys(grouped);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4 py-12">
      <div className="max-w-4xl w-full">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            KPI Template Preview
          </h2>
          <p className="text-gray-600 mb-6">
            {template.kpis.length} KPIs across {categories.length} pillars for{' '}
            <span className="font-medium capitalize">{vertical.replace(/-/g, ' ')}</span>
          </p>

          <div className="space-y-6 mb-8">
            {categories.map((category) => (
              <div key={category}>
                <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-blue-500" />
                  {category}
                  <span className="text-sm font-normal text-gray-500">
                    ({grouped[category].length} KPIs)
                  </span>
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {grouped[category].map((kpi) => (
                    <div
                      key={kpi.name}
                      className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-2"
                    >
                      <span className="text-sm text-gray-800">{kpi.name}</span>
                      {kpi.description && (
                        <span className="text-xs text-gray-500 ml-2 whitespace-nowrap">
                          {kpi.description}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between border-t border-gray-200 pt-6">
            <button
              onClick={onSkip}
              className="px-4 py-2 text-gray-700 hover:text-gray-900"
            >
              Skip Preview
            </button>
            <button
              onClick={onContinue}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Continue to Upload &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TemplatePreview;
