import React from 'react';
import { KPIDefinition } from '../../../hooks/useCustomerConfig';

const PILLAR_ORDER = ['AI', 'CH', 'DV', 'EX', 'OS'] as const;
const PILLAR_INFO: Record<string, { name: string; icon: string; sliderColor: string }> = {
  AI: { name: 'AI Workload Performance', icon: '🖥️', sliderColor: 'bg-blue-500' },
  CH: { name: 'Channel & Partner Health', icon: '🤝', sliderColor: 'bg-green-500' },
  DV: { name: 'Deployment Velocity', icon: '🚀', sliderColor: 'bg-yellow-500' },
  EX: { name: 'Expansion Readiness', icon: '📈', sliderColor: 'bg-purple-500' },
  OS: { name: 'Operational Stability', icon: '🛡️', sliderColor: 'bg-red-500' }
};

export interface KPIWeightsEditorProps {
  kpiWeights: Record<string, Record<string, number>>;
  kpiDefinitions: Record<string, KPIDefinition>;
  onChange: (weights: Record<string, Record<string, number>>) => void;
}

export const KPIWeightsEditor: React.FC<KPIWeightsEditorProps> = ({
  kpiWeights,
  kpiDefinitions,
  onChange
}) => {
  const handleKpiWeightChange = (pillarCode: string, kpiCode: string, value: number) => {
    const next = JSON.parse(JSON.stringify(kpiWeights)) as Record<string, Record<string, number>>;
    if (!next[pillarCode]) next[pillarCode] = {};
    next[pillarCode][kpiCode] = value / 100;
    onChange(next);
  };

  const hasAnyWeights = PILLAR_ORDER.some(
    (p) => kpiWeights[p] && Object.keys(kpiWeights[p]).length > 0
  );

  if (!hasAnyWeights) {
    return (
      <div>
        <p className="text-gray-600 mb-4">
          Adjust KPI weights (L1) within each pillar. Weights under a pillar typically sum to 100%.
        </p>
        <p className="text-gray-500">
          No KPI weights loaded yet. Complete onboarding or run Wizard C weight calibration (Admin
          Insights → Weight Calibration) to populate weights from bootstrap or learned data, then
          you can override them here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">KPI Weights (L1)</h3>
        <p className="text-sm text-gray-600 mb-4">
          Adjust how much each KPI contributes within its pillar. Weights under each pillar should
          sum to 100%.
        </p>
      </div>

      {PILLAR_ORDER.map((pillarCode) => {
        const kpis = kpiWeights[pillarCode] || {};
        const entries = Object.entries(kpis);
        if (entries.length === 0) return null;

        const pillarTotal = entries.reduce((sum, [, w]) => sum + w, 0);
        const info = PILLAR_INFO[pillarCode] || { name: `Pillar ${pillarCode}`, icon: '📊', sliderColor: 'bg-gray-500' };

        return (
          <div key={pillarCode} className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="px-4 py-3 font-medium text-gray-900 flex items-center justify-between bg-gray-50 border-b border-gray-200">
              <span className="flex items-center gap-2">
                <span className="text-xl">{info.icon}</span>
                {info.name}
              </span>
              <span className="text-sm font-normal text-gray-600">
                Pillar total: {(pillarTotal * 100).toFixed(1)}%
              </span>
            </div>
            <div className="divide-y divide-gray-100">
              {entries.map(([kpiCode, weight]) => {
                const def = kpiDefinitions[kpiCode];
                const label = def?.name || kpiCode;
                const pct = Math.round(weight * 100);
                return (
                  <div key={kpiCode} className="px-4 py-3 flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-gray-900 text-sm">{label}</div>
                        <div className="text-xs text-gray-500">{kpiCode}</div>
                      </div>
                      <span className="text-sm font-semibold text-gray-900 tabular-nums">
                        {pct}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={pct}
                      onChange={(e) =>
                        handleKpiWeightChange(pillarCode, kpiCode, Number(e.target.value))
                      }
                      className={`w-full h-2 rounded-lg appearance-none cursor-pointer ${info.sliderColor}`}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
};
