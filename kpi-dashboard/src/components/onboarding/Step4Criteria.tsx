/**
 * Step 4: Success Criteria Configuration
 */

import React from 'react';
import { Target } from 'lucide-react';
import { SuccessCriteria } from './OnboardingWizard.types';

interface Step4CriteriaProps {
  data: SuccessCriteria;
  onChange: (data: SuccessCriteria) => void;
}

export const Step4Criteria: React.FC<Step4CriteriaProps> = ({ data, onChange }) => {
  return (
    <div className="space-y-6">
      <div>
        <h4 className="font-medium mb-4 flex items-center gap-2">
          <Target className="w-5 h-5" />
          Health Score Thresholds
        </h4>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm font-medium">Healthy Minimum</span>
              <span className="text-sm font-medium text-green-600">{data.healthy_min}+</span>
            </div>
            <input
              type="range"
              min={60}
              max={90}
              value={data.healthy_min}
              onChange={(e) => onChange({ ...data, healthy_min: Number(e.target.value) })}
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              Accounts above this score are considered healthy
            </p>
          </div>
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm font-medium">At-Risk Minimum</span>
              <span className="text-sm font-medium text-yellow-600">{data.at_risk_min} - {data.healthy_min - 1}</span>
            </div>
            <input
              type="range"
              min={30}
              max={data.healthy_min - 10}
              value={data.at_risk_min}
              onChange={(e) => onChange({ ...data, at_risk_min: Number(e.target.value) })}
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              Accounts in this range need attention
            </p>
          </div>
        </div>
        
        <div className="mt-4 h-6 rounded-full overflow-hidden flex border-2 border-gray-300">
          <div className="bg-red-500" style={{ width: `${data.at_risk_min}%` }} />
          <div className="bg-yellow-500" style={{ width: `${data.healthy_min - data.at_risk_min}%` }} />
          <div className="bg-green-500" style={{ width: `${100 - data.healthy_min}%` }} />
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>0 (Critical)</span>
          <span>{data.at_risk_min}</span>
          <span>{data.healthy_min}</span>
          <span>100 (Excellent)</span>
        </div>
      </div>

      <div className="border-t pt-6">
        <h4 className="font-medium mb-4">Alert Thresholds</h4>
        <div className="grid grid-cols-2 gap-6">
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm">Churn Alert When</span>
              <span className="text-sm font-medium text-red-600">≤ {data.churn_alert}%</span>
            </div>
            <input
              type="range"
              min={30}
              max={80}
              value={data.churn_alert}
              onChange={(e) => onChange({ ...data, churn_alert: Number(e.target.value) })}
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              Alert when health score drops below this threshold
            </p>
          </div>
          <div>
            <div className="flex justify-between mb-2">
              <span className="text-sm">Expansion Alert When</span>
              <span className="text-sm font-medium text-green-600">≥ {data.expansion_alert}%</span>
            </div>
            <input
              type="range"
              min={30}
              max={80}
              value={data.expansion_alert}
              onChange={(e) => onChange({ ...data, expansion_alert: Number(e.target.value) })}
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              Alert when health score exceeds this threshold
            </p>
          </div>
        </div>
      </div>

      <div className="border-t pt-6">
        <h4 className="font-medium mb-4">Prediction Horizon</h4>
        <div>
          <div className="flex justify-between mb-2">
            <span className="text-sm">Predict outcomes for next</span>
            <span className="text-sm font-medium">{data.prediction_horizon} days</span>
          </div>
          <input
            type="range"
            min={30}
            max={180}
            step={30}
            value={data.prediction_horizon}
            onChange={(e) => onChange({ ...data, prediction_horizon: Number(e.target.value) })}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>30 days</span>
            <span>90 days</span>
            <span>180 days</span>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            How far ahead should we predict churn/expansion risks?
          </p>
        </div>
      </div>
    </div>
  );
};
