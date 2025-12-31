import React from 'react';
import { Download, FileText, ChevronRight } from 'lucide-react';
import { TemplateInfo } from '../../utils/onboardingApi';
import { downloadSampleTemplate } from '../../utils/onboardingApi';

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
  const handleDownload = async () => {
    await downloadSampleTemplate(vertical);
  };

  const categories = Array.from(new Set(template.kpis.map(k => k.category)));

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4 py-12">
      <div className="max-w-3xl w-full bg-white rounded-xl shadow-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          📊 {template.vertical.charAt(0).toUpperCase() + template.vertical.slice(1)} Customer Success Template
        </h2>
        
        <p className="text-gray-600 mb-6">
          This template includes {template.kpis.length} key metrics:
        </p>

        <div className="space-y-4 mb-6 max-h-96 overflow-y-auto">
          {categories.map((category) => {
            const categoryKpis = template.kpis.filter(k => k.category === category);
            return (
              <div key={category} className="border border-gray-200 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-2">{category}</h3>
                <div className="space-y-1">
                  {categoryKpis.map((kpi, index) => (
                    <div key={index} className="flex items-center text-sm text-gray-700">
                      <span className="text-green-600 mr-2">✓</span>
                      <span>{kpi.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex items-center justify-between pt-6 border-t border-gray-200">
          <div className="flex items-center gap-3">
            <button
              onClick={handleDownload}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              <Download className="h-4 w-4" />
              Download Sample CSV
            </button>
            <button
              onClick={onSkip}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center gap-2"
            >
              <FileText className="h-4 w-4" />
              View Full Details
            </button>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={onSkip}
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Already have data? → Skip to Upload
            </button>
            <button
              onClick={onContinue}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
            >
              Continue
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TemplatePreview;

