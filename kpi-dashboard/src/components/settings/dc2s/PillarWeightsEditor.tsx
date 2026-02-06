import React, { useState, useEffect } from 'react';
import { PillarWeights } from '../../../hooks/useCustomerConfig';

interface PillarWeightsEditorProps {
  weights: PillarWeights;
  onChange: (weights: PillarWeights) => void;
}

const PILLAR_INFO = {
  AI: {
    name: 'AI Workload Performance',
    description: 'GPU utilization, compute efficiency',
    icon: '🖥️',
    color: 'bg-blue-500'
  },
  CH: {
    name: 'Customer Health',
    description: 'Satisfaction, adoption, engagement',
    icon: '❤️',
    color: 'bg-green-500'
  },
  DV: {
    name: 'Deployment Velocity',
    description: 'Time to deploy, scaling speed',
    icon: '🚀',
    color: 'bg-yellow-500'
  },
  EX: {
    name: 'Expansion & Growth',
    description: 'Revenue impact, ROI, strategic value',
    icon: '📈',
    color: 'bg-purple-500'
  },
  OS: {
    name: 'Operational Stability',
    description: 'Uptime, costs, reliability',
    icon: '🛡️',
    color: 'bg-red-500'
  }
};

export const PillarWeightsEditor: React.FC<PillarWeightsEditorProps> = ({ 
  weights, 
  onChange 
}) => {
  const [localWeights, setLocalWeights] = useState<PillarWeights>(weights);
  const [total, setTotal] = useState<number>(100);

  useEffect(() => {
    setLocalWeights(weights);
  }, [weights]);

  useEffect(() => {
    const sum = Object.values(localWeights).reduce((a, b) => a + b, 0);
    setTotal(Math.round(sum * 100));
  }, [localWeights]);

  const handleWeightChange = (pillar: keyof PillarWeights, value: number) => {
    const newWeights = { ...localWeights, [pillar]: value / 100 };
    setLocalWeights(newWeights);
    onChange(newWeights);
  };

  const isValid = Math.abs(total - 100) < 1;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Pillar Importance
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Adjust how much each pillar contributes to overall health score (must sum to 100%)
        </p>
      </div>

      <div className="space-y-6">
        {Object.entries(PILLAR_INFO).map(([code, info]) => (
          <div key={code} className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">{info.icon}</span>
                <div>
                  <div className="font-medium text-gray-900">{info.name}</div>
                  <div className="text-sm text-gray-500">{info.description}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-gray-900">
                  {Math.round(localWeights[code as keyof PillarWeights] * 100)}%
                </div>
              </div>
            </div>
            
            <input
              type="range"
              min="10"
              max="40"
              value={localWeights[code as keyof PillarWeights] * 100}
              onChange={(e) => handleWeightChange(code as keyof PillarWeights, Number(e.target.value))}
              className={`w-full h-2 rounded-lg appearance-none cursor-pointer ${info.color}`}
            />
            
            <div className="flex justify-between text-xs text-gray-500">
              <span>10%</span>
              <span>40%</span>
            </div>
          </div>
        ))}
      </div>

      <div className={`p-4 rounded-lg ${isValid ? 'bg-green-50' : 'bg-red-50'}`}>
        <div className="flex items-center justify-between">
          <span className="font-medium text-gray-900">Total:</span>
          <span className={`text-2xl font-bold ${isValid ? 'text-green-600' : 'text-red-600'}`}>
            {total}%
          </span>
        </div>
        {!isValid && (
          <p className="text-sm text-red-600 mt-2">
            ⚠️ Pillar weights must sum to exactly 100%
          </p>
        )}
      </div>
    </div>
  );
};
