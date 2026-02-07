import React from 'react';

interface TemplatePreviewProps {
  template?: any;
  vertical?: string;
  onSelect?: (template: any) => void;
  onSkip?: () => void;
  onContinue?: () => void;
  [key: string]: any;
}

const TemplatePreview: React.FC<TemplatePreviewProps> = ({ template, onContinue, onSkip }) => {
  return (
    <div className="p-6 border rounded-lg bg-gray-50 text-center">
      <p className="text-sm text-gray-500 mb-4">Template preview — Gold template selected</p>
      <div className="flex gap-3 justify-center">
        {onSkip && <button onClick={onSkip} className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 text-sm">Skip</button>}
        {onContinue && <button onClick={onContinue} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm">Continue</button>}
      </div>
    </div>
  );
};

export default TemplatePreview;
