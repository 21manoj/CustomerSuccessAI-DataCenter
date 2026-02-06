import React, { useState } from 'react';
import { KPIDefinition } from '../../../hooks/useCustomerConfig';

interface KPISelectionPanelProps {
  catalogKPIs: { code: string; definition: KPIDefinition }[];
  customKPIs: { code: string; definition: KPIDefinition }[];
  enabledKPIs: string[];
  onChange: (enabledKPIs: string[]) => void;
  onAddCustomKPI: (pillar?: string) => void;
  onEditCustomKPI: (kpiCode: string) => void;
  onDeleteCustomKPI: (kpiCode: string) => void;
}

export const KPISelectionPanel: React.FC<KPISelectionPanelProps> = ({
  catalogKPIs,
  customKPIs,
  enabledKPIs,
  onChange,
  onAddCustomKPI,
  onEditCustomKPI,
  onDeleteCustomKPI
}) => {
  const [expandedPillars, setExpandedPillars] = useState<Set<string>>(
    new Set(['AI', 'CH', 'DV', 'EX', 'OS'])
  );

  const togglePillar = (pillar: string) => {
    const newExpanded = new Set(expandedPillars);
    if (newExpanded.has(pillar)) {
      newExpanded.delete(pillar);
    } else {
      newExpanded.add(pillar);
    }
    setExpandedPillars(newExpanded);
  };

  const toggleKPI = (kpiCode: string) => {
    if (enabledKPIs.includes(kpiCode)) {
      onChange(enabledKPIs.filter(k => k !== kpiCode));
    } else {
      onChange([...enabledKPIs, kpiCode]);
    }
  };

  const groupKPIsByPillar = () => {
    const grouped: { [pillar: string]: { catalog: any[]; custom: any[] } } = {
      AI: { catalog: [], custom: [] },
      CH: { catalog: [], custom: [] },
      DV: { catalog: [], custom: [] },
      EX: { catalog: [], custom: [] },
      OS: { catalog: [], custom: [] }
    };

    catalogKPIs.forEach(kpi => {
      const pillar = kpi.definition.pillar;
      if (pillar in grouped) {
        grouped[pillar].catalog.push(kpi);
      }
    });

    customKPIs.forEach(kpi => {
      const pillar = kpi.definition.pillar;
      if (pillar in grouped) {
        grouped[pillar].custom.push(kpi);
      }
    });

    return grouped;
  };

  const pillarGroups = groupKPIsByPillar();

  const PILLAR_NAMES = {
    AI: '🖥️ AI Workload Performance',
    CH: '❤️ Customer Health',
    DV: '🚀 Deployment Velocity',
    EX: '📈 Expansion & Growth',
    OS: '🛡️ Operational Stability'
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Select KPIs to Track
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Choose which KPIs to measure (from catalog or add your own)
        </p>
      </div>

      {Object.entries(pillarGroups).map(([pillar, kpis]) => {
        const isExpanded = expandedPillars.has(pillar);
        const enabledCount = [...kpis.catalog, ...kpis.custom]
          .filter(k => enabledKPIs.includes(k.code)).length;
        const totalCount = kpis.catalog.length + kpis.custom.length;

        return (
          <div key={pillar} className="border rounded-lg overflow-hidden">
            <button
              onClick={() => togglePillar(pillar)}
              className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between"
            >
              <div className="flex items-center space-x-3">
                <span className="text-xl">{PILLAR_NAMES[pillar as keyof typeof PILLAR_NAMES]}</span>
                <span className="text-sm text-gray-600">
                  {enabledCount} / {totalCount} selected
                </span>
              </div>
              <span className="text-gray-400">
                {isExpanded ? '▼' : '▶'}
              </span>
            </button>

            {isExpanded && (
              <div className="p-4 space-y-3">
                {/* Catalog KPIs */}
                {kpis.catalog.length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-gray-500 uppercase mb-2">
                      Catalog KPIs
                    </div>
                    {kpis.catalog.map(kpi => (
                      <label
                        key={kpi.code}
                        className="flex items-start space-x-3 p-2 hover:bg-gray-50 rounded cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={enabledKPIs.includes(kpi.code)}
                          onChange={() => toggleKPI(kpi.code)}
                          className="mt-1 h-4 w-4 text-blue-600 rounded"
                        />
                        <div className="flex-1">
                          <div className="font-medium text-gray-900">
                            {kpi.definition.name}
                          </div>
                          <div className="text-sm text-gray-600">
                            {kpi.definition.description}
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            Target: {kpi.definition.target} {kpi.definition.unit}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                )}

                {/* Custom KPIs */}
                {kpis.custom.length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-gray-500 uppercase mb-2">
                      Custom KPIs
                    </div>
                    {kpis.custom.map(kpi => (
                      <div
                        key={kpi.code}
                        className="flex items-start space-x-3 p-2 hover:bg-gray-50 rounded"
                      >
                        <input
                          type="checkbox"
                          checked={enabledKPIs.includes(kpi.code)}
                          onChange={() => toggleKPI(kpi.code)}
                          className="mt-1 h-4 w-4 text-blue-600 rounded"
                        />
                        <div className="flex-1">
                          <div className="font-medium text-gray-900">
                            {kpi.definition.name}
                            <span className="ml-2 text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded">
                              Custom
                            </span>
                          </div>
                          <div className="text-sm text-gray-600">
                            {kpi.definition.description}
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            Target: {kpi.definition.target} {kpi.definition.unit}
                          </div>
                        </div>
                        <div className="flex space-x-2">
                          <button
                            onClick={() => onEditCustomKPI(kpi.code)}
                            className="text-sm text-blue-600 hover:text-blue-800"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => onDeleteCustomKPI(kpi.code)}
                            className="text-sm text-red-600 hover:text-red-800"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Add Custom KPI Button */}
                <button
                  onClick={() => onAddCustomKPI(pillar)}
                  className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-blue-500 hover:text-blue-600 transition-colors"
                >
                  + Add Custom KPI to {pillar}
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
