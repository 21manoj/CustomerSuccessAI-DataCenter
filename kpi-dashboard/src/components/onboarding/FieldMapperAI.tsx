import React, { useState, useEffect } from 'react';
import { FieldMapping, suggestFieldMappings } from '../../utils/onboardingApi';

interface FieldMapperAIProps {
  sourceColumns: string[];
  targetFields: string[];
  vertical: string;
  onMappingChange: (mappings: FieldMapping[]) => void;
  onContinue: () => void;
  onBack: () => void;
}

const FieldMapperAI: React.FC<FieldMapperAIProps> = ({
  sourceColumns,
  targetFields,
  vertical,
  onMappingChange,
  onContinue,
  onBack
}) => {
  const [mappings, setMappings] = useState<FieldMapping[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSuggestions = async () => {
      setLoading(true);
      try {
        const suggested = await suggestFieldMappings(sourceColumns, vertical);
        setMappings(suggested);
        onMappingChange(suggested);
      } catch (error) {
        console.error('Error loading suggestions:', error);
        // Fallback: map each source column to target fields in order
        const fallback: FieldMapping[] = sourceColumns.map((col, i) => ({
          sourceColumn: col,
          targetField: targetFields[i] || targetFields[0] || '',
          confidence: 0
        }));
        setMappings(fallback);
        onMappingChange(fallback);
      }
      setLoading(false);
    };

    loadSuggestions();
  }, [sourceColumns, vertical]);

  const handleTargetChange = (index: number, newTarget: string) => {
    const updated = mappings.map((m, i) =>
      i === index ? { ...m, targetField: newTarget, confidence: 100 } : m
    );
    setMappings(updated);
    onMappingChange(updated);
  };

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 90) {
      return <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">High</span>;
    }
    if (confidence >= 50) {
      return <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">Medium</span>;
    }
    return <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700">Low</span>;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Analyzing your columns...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4 py-12">
      <div className="max-w-3xl w-full bg-white rounded-xl shadow-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Map Your Fields</h2>
        <p className="text-gray-600 mb-6">
          We've matched your columns to our KPI definitions. Review and adjust as needed.
        </p>

        <div className="space-y-3 mb-8 max-h-[28rem] overflow-y-auto">
          <div className="grid grid-cols-12 gap-3 text-xs font-semibold text-gray-500 uppercase px-1 sticky top-0 bg-white pb-2">
            <div className="col-span-4">Your Column</div>
            <div className="col-span-1 text-center">→</div>
            <div className="col-span-5">Maps To</div>
            <div className="col-span-2 text-center">Match</div>
          </div>

          {mappings.map((mapping, index) => (
            <div
              key={index}
              className="grid grid-cols-12 gap-3 items-center bg-gray-50 rounded-lg px-3 py-2"
            >
              <div className="col-span-4 text-sm text-gray-800 font-medium truncate" title={mapping.sourceColumn}>
                {mapping.sourceColumn}
              </div>
              <div className="col-span-1 text-center text-gray-400">→</div>
              <div className="col-span-5">
                <select
                  value={mapping.targetField}
                  onChange={(e) => handleTargetChange(index, e.target.value)}
                  className="w-full text-sm border border-gray-300 rounded-md px-2 py-1.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">-- Skip --</option>
                  {targetFields.map((field) => (
                    <option key={field} value={field}>
                      {field}
                    </option>
                  ))}
                </select>
              </div>
              <div className="col-span-2 text-center">
                {getConfidenceBadge(mapping.confidence)}
              </div>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between border-t border-gray-200 pt-6">
          <button
            onClick={onBack}
            className="px-4 py-2 text-gray-700 hover:text-gray-900"
          >
            &larr; Back
          </button>
          <button
            onClick={onContinue}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Continue &rarr;
          </button>
        </div>
      </div>
    </div>
  );
};

export default FieldMapperAI;
