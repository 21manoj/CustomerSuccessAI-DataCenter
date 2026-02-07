import React from 'react';
import { FieldMapping } from '../../utils/onboardingApi';

interface FieldMapperAIProps {
  sourceColumns?: string[];
  targetFields?: string[];
  vertical?: string;
  onMappingChange?: (mappings: FieldMapping[]) => void;
  onContinue?: () => void;
  onBack?: () => void;
  [key: string]: any;
}

const FieldMapperAI: React.FC<FieldMapperAIProps> = ({ sourceColumns, targetFields, onContinue, onBack }) => {
  return (
    <div className="p-6 border rounded-lg bg-gray-50 text-center">
      <p className="text-sm text-gray-500 mb-4">AI Field Mapper — maps uploaded columns to KPI targets</p>
      <div className="flex gap-3 justify-center">
        {onBack && <button onClick={onBack} className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">Back</button>}
        {onContinue && <button onClick={onContinue} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Continue</button>}
      </div>
    </div>
  );
};

export default FieldMapperAI;
