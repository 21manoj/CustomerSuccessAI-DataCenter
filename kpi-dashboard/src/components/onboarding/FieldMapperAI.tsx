import React, { useState, useEffect } from 'react';
import { CheckCircle, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
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
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  useEffect(() => {
    const loadMappings = async () => {
      setLoading(true);
      try {
        const suggested = await suggestFieldMappings(sourceColumns, vertical);
        setMappings(suggested);
        onMappingChange(suggested);
      } catch (error) {
        console.error('Error loading mappings:', error);
      } finally {
        setLoading(false);
      }
    };

    loadMappings();
  }, [sourceColumns, vertical, onMappingChange]);

  const handleMappingChange = (index: number, targetField: string) => {
    const updated = [...mappings];
    updated[index] = { ...updated[index], targetField };
    setMappings(updated);
    onMappingChange(updated);
  };

  const toggleRow = (index: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedRows(newExpanded);
  };

  const unmappedColumns = sourceColumns.filter(
    col => !mappings.some(m => m.sourceColumn === col)
  );

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 90) return 'text-green-600';
    if (confidence >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 90) return <CheckCircle className="h-4 w-4 text-green-600" />;
    if (confidence >= 70) return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
    return <AlertTriangle className="h-4 w-4 text-red-600" />;
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
      <div className="max-w-4xl w-full bg-white rounded-xl shadow-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">🤖 Verify Field Mapping</h2>
        <p className="text-gray-600 mb-6">We've automatically mapped your columns:</p>

        <div className="space-y-3 mb-6 max-h-96 overflow-y-auto">
          {mappings.map((mapping, index) => (
            <div key={index} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="font-medium text-gray-900">"{mapping.sourceColumn}"</span>
                    <span className="text-gray-400">→</span>
                    <select
                      value={mapping.targetField}
                      onChange={(e) => handleMappingChange(index, e.target.value)}
                      className="px-3 py-1 border border-gray-300 rounded-md text-sm font-medium text-gray-900"
                    >
                      <option value="">[Skip]</option>
                      {targetFields.map(field => (
                        <option key={field} value={field}>{field}</option>
                      ))}
                    </select>
                    <div className={`flex items-center gap-1 ${getConfidenceColor(mapping.confidence)}`}>
                      {getConfidenceIcon(mapping.confidence)}
                      <span className="text-sm font-medium">{mapping.confidence}%</span>
                    </div>
                  </div>
                  
                  {mapping.confidence < 80 && mapping.suggestions && (
                    <div className="ml-8 mt-2">
                      <button
                        onClick={() => toggleRow(index)}
                        className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                      >
                        {expandedRows.has(index) ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                        Did you mean something else?
                      </button>
                      
                      {expandedRows.has(index) && (
                        <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded">
                          <p className="text-sm text-yellow-800 mb-2">
                            Suggested alternatives:
                          </p>
                          <div className="space-y-1">
                            {mapping.suggestions.map((suggestion, idx) => (
                              <button
                                key={idx}
                                onClick={() => handleMappingChange(index, suggestion.field)}
                                className="block w-full text-left px-2 py-1 text-sm text-gray-700 hover:bg-yellow-100 rounded"
                              >
                                "{suggestion.field}" ({suggestion.confidence}% - {suggestion.reason})
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {unmappedColumns.length > 0 && (
          <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
            <h3 className="font-medium text-gray-900 mb-3">
              Unmapped Columns ({unmappedColumns.length}):
            </h3>
            <div className="space-y-2">
              {unmappedColumns.map((col, index) => (
                <div key={index} className="flex items-center gap-3">
                  <span className="text-sm text-gray-700">• "{col}"</span>
                  <select
                    onChange={(e) => {
                      if (e.target.value) {
                        const newMapping: FieldMapping = {
                          sourceColumn: col,
                          targetField: e.target.value,
                          confidence: 50
                        };
                        setMappings([...mappings, newMapping]);
                        onMappingChange([...mappings, newMapping]);
                      }
                    }}
                    className="px-2 py-1 border border-gray-300 rounded text-sm"
                    defaultValue=""
                  >
                    <option value="">[Map to Field ▼]</option>
                    {targetFields.map(field => (
                      <option key={field} value={field}>{field}</option>
                    ))}
                  </select>
                  <button className="text-xs text-gray-500 hover:text-gray-700">[Skip]</button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center justify-between pt-6 border-t border-gray-200">
          <button
            onClick={onBack}
            className="px-4 py-2 text-gray-700 hover:text-gray-900"
          >
            ← Back
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                // Skip unmapped
                onContinue();
              }}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              Skip Unmapped
            </button>
            <button
              onClick={onContinue}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Import {mappings.filter(m => m.targetField).length} Customers →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FieldMapperAI;

