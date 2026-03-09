/**
 * Data Center Tenant KPI Details
 * ===============================
 * 
 * Displays KPI details with full 3-level weight transparency:
 * - Level 1: KPI → Pillar Score (L1 weights)
 * - Level 2: Pillar → Account Score (L2 weights)
 * - Level 3: Final Health Score
 * 
 * Shows reference ranges and calculation breakdowns.
 */

import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { useSession } from '../../../contexts/SessionContext';
import { apiCall } from '../../../utils/api';
import { DEFAULT_PILLAR_WEIGHTS, PILLAR_META } from '../../../utils/pillarDefaults';

// ============================================================
// TYPES
// ============================================================

interface KPIReferenceRange {
  kpi_code: string;
  healthy_min: number;
  healthy_max: number;
  risk_min: number;
  risk_max: number;
  critical_min: number;
  critical_max: number;
}

interface KPI {
  kpi_code: string;
  kpi_name: string;
  pillar: string;
  current_value: number;
  score: number;
  l1_weight: number;
  state: 'healthy' | 'at_risk' | 'critical';
  reference_range?: KPIReferenceRange;
}

interface Pillar {
  pillar_code: string;
  pillar_name: string;
  score: number;
  l2_weight: number;
  contribution: number;
  kpis: KPI[];
}

interface TenantKPIDetailsProps {
  tenantId: number | string;
}

// ============================================================
// MAIN COMPONENT
// ============================================================

const DCTenantKPIDetails: React.FC<TenantKPIDetailsProps> = ({ tenantId }) => {
  const { session } = useSession();
  const [pillars, setPillars] = useState<Pillar[]>([]);
  const [overallHealth, setOverallHealth] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedPillar, setExpandedPillar] = useState<string | null>(null);

  useEffect(() => {
    if (tenantId) {
      fetchKPIDetails();
    }
  }, [tenantId]);

  const fetchKPIDetails = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch KPIs for this account (returns pillar P1-P5 from DC2_S catalog)
      const kpisResponse = await apiCall(`/api/dc2s/accounts/${tenantId}/kpis`, {
        method: 'GET'
      });

      if (!kpisResponse.ok) {
        throw new Error(`Failed to fetch KPIs: ${kpisResponse.status}`);
      }

      const kpisData = await kpisResponse.json();
      const kpis = kpisData.kpis || [];

      // DC2_S: Use health-score API (has real data); scores/account/:id/latest uses HealthScore table (often empty for DC2_S)
      let pillarScores: any[] = [];
      let healthScore = 0;
      // Derive P-code weights from the canonical DB-code defaults
      const pillarWeightsDefault: Record<string, number> = Object.fromEntries(
        Object.entries(PILLAR_META).map(([pCode, meta]) => [
          pCode,
          DEFAULT_PILLAR_WEIGHTS[meta.code as keyof typeof DEFAULT_PILLAR_WEIGHTS] ?? 0.20,
        ])
      );
      let pillarWeights: Record<string, number> = { ...pillarWeightsDefault };

      const healthScoreResponse = await apiCall(`/api/dc2s/health-score/${tenantId}`, { method: 'GET' });
      if (healthScoreResponse.ok) {
        const healthData = await healthScoreResponse.json();
        healthScore = Number(healthData.overall_score) || 0;
        const categoryScores = healthData.category_scores || {};
        pillarScores = Object.entries(categoryScores).map(([pillar_code, data]: [string, any]) => ({
          pillar_code,
          pillar_score: data?.score ?? 0,
          weight: data?.weight ?? pillarWeightsDefault[pillar_code] ?? 0.2
        }));
        pillarWeights = Object.fromEntries(
          Object.entries(categoryScores).map(([code, data]: [string, any]) => [
            code,
            typeof data?.weight === 'number' ? data.weight : pillarWeightsDefault[code] ?? 0.2
          ])
        );
      } else {
        // Fallback: try generic scores API (SaaS HealthScore table)
        const scoresResponse = await apiCall(`/api/dc2s/scores/account/${tenantId}/latest`, { method: 'GET' });
        if (scoresResponse.ok) {
          const scoresData = await scoresResponse.json();
          pillarScores = scoresData.pillar_scores || [];
          healthScore = scoresData.health_score?.overall_score || 0;
        }
        try {
          const configResponse = await apiCall('/api/dc2s/config/', { method: 'GET' });
          if (configResponse.ok) {
            const config = await configResponse.json();
            if (config.pillar_weights && typeof config.pillar_weights === 'object') {
              Object.assign(pillarWeights, config.pillar_weights);
            }
          }
        } catch (e) {
          console.warn('Could not fetch pillar weights from config, using defaults');
        }
      }

      // DC2_S pillar codes P1-P5 and display names (from centralized PILLAR_META)
      const pillarNames: Record<string, string> = Object.fromEntries(
        Object.entries(PILLAR_META).map(([code, meta]) => [code, meta.name])
      );

      // Fetch enabled pillars from accounts endpoint
      let enabledPillars: Set<string> = new Set(['P1', 'P2', 'P3', 'P4', 'P5']);
      try {
        const accountsResp = await apiCall('/api/dc2s/accounts', { method: 'GET' });
        if (accountsResp.ok) {
          const accountsData = await accountsResp.json();
          const ep = accountsData.enabled_pillars;
          if (Array.isArray(ep) && ep.length > 0) {
            enabledPillars = new Set(ep);
          }
        }
      } catch (e) {
        // use defaults
      }

      // Group KPIs by pillar (API returns pillar P1, P2, ... P5)
      const kpisByPillar: Record<string, any[]> = {};
      kpis.forEach((kpi: any) => {
        const pillar = kpi.pillar || kpi.category || 'Uncategorized';
        if (!kpisByPillar[pillar]) {
          kpisByPillar[pillar] = [];
        }
        kpisByPillar[pillar].push(kpi);
      });

      // Build pillar structure — only show enabled pillars
      const pillarCodes = ['P1', 'P2', 'P3', 'P4', 'P5'].filter(p => enabledPillars.has(p));
      const pillarsData: Pillar[] = pillarCodes.map(pillarCode => {
        const pillarScore = pillarScores.find((p: any) => p.pillar_code === pillarCode);
        const score = pillarScore ? parseFloat(pillarScore.pillar_score || 0) : 0;
        const l2Weight = pillarWeights[pillarCode] ?? pillarWeightsDefault[pillarCode] ?? 0.2;
        const pillarKPIs = kpisByPillar[pillarCode] || [];

        // Calculate KPI scores and weights
        const kpiDetails: KPI[] = pillarKPIs.map((kpi: any) => {
          // Determine state based on status or value vs target
          let state: 'healthy' | 'at_risk' | 'critical' = 'healthy';
          if (kpi.status === 'critical' || kpi.status === 'at_risk') {
            state = kpi.status as any;
          } else if (kpi.target && kpi.value !== undefined) {
            const percentage = (kpi.value / kpi.target) * 100;
            if (percentage < 70) state = 'critical';
            else if (percentage < 90) state = 'at_risk';
          }

          // Get KPI score from scores API if available
          const kpiScoreData = pillarScore?.kpi_details?.find((k: any) => k.kpi_code === kpi.kpi_code);
          const kpiScore = kpiScoreData ? parseFloat(kpiScoreData.kpi_score || 0) : (state === 'healthy' ? 85 : state === 'at_risk' ? 60 : 40);
          
          // Calculate L1 weight (equal distribution for now, or from config)
          const totalKPIsInPillar = pillarKPIs.length;
          const l1Weight = totalKPIsInPillar > 0 ? 1.0 / totalKPIsInPillar : 0;

          return {
            kpi_code: kpi.kpi_code || kpi.kpi_parameter,
            kpi_name: kpi.kpi_parameter || kpi.kpi_name || kpi.kpi_code,
            pillar: pillarCode,
            current_value: parseFloat(kpi.value || kpi.data || 0),
            score: Math.round(kpiScore),
            l1_weight: l1Weight,
            state: state,
            reference_range: kpi.target ? {
              kpi_code: kpi.kpi_code || kpi.kpi_parameter,
              healthy_min: kpi.target * 0.9,
              healthy_max: kpi.target * 1.1,
              risk_min: kpi.target * 0.7,
              risk_max: kpi.target * 0.9,
              critical_min: 0,
              critical_max: kpi.target * 0.7
            } : undefined
          };
        });

        return {
          pillar_code: pillarCode,
          pillar_name: pillarNames[pillarCode] || pillarCode,
          score: Math.round(score),
          l2_weight: l2Weight,
          contribution: score * l2Weight,
          kpis: kpiDetails
        };
      });

      setPillars(pillarsData);
      
      // Calculate overall health from pillar contributions
      const total = pillarsData.reduce((sum, p) => sum + p.contribution, 0);
      setOverallHealth(total || healthScore);
    } catch (err: any) {
      console.error('Error fetching KPI details:', err);
      setError(err.message || 'Failed to load KPI details');
    } finally {
      setLoading(false);
    }
  };

  const getStateColor = (state: string) => {
    switch (state) {
      case 'healthy': return 'text-green-600 bg-green-50 border-green-200';
      case 'at_risk': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'critical': return 'text-red-600 bg-red-50 border-red-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStateIcon = (state: string) => {
    switch (state) {
      case 'healthy': return <CheckCircle className="w-4 h-4" />;
      case 'at_risk': return <AlertTriangle className="w-4 h-4" />;
      case 'critical': return <AlertTriangle className="w-4 h-4" />;
      default: return <Info className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Loading KPI details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-700">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overall Health Summary */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 border border-blue-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Overall Health: {overallHealth.toFixed(1)}/100
        </h3>
        <p className="text-sm text-gray-600 mb-4">
          Calculation: {pillars.map(p => `(P${p.pillar_code.slice(1)}×${(p.l2_weight * 100).toFixed(0)}%)`).join(' + ')}
        </p>
        <div className="text-xs text-gray-500 space-y-1">
          {pillars.map(p => (
            <div key={p.pillar_code}>
              ({p.pillar_name}: {p.score.toFixed(0)}×{p.l2_weight.toFixed(2)}) = {p.contribution.toFixed(1)} points
            </div>
          ))}
        </div>
      </div>

      {/* Pillar Breakdown */}
      {pillars.map((pillar) => (
        <div key={pillar.pillar_code} className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          {/* Pillar Header */}
          <button
            onClick={() => setExpandedPillar(expandedPillar === pillar.pillar_code ? null : pillar.pillar_code)}
            className="w-full p-4 text-left hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-semibold text-gray-900">
                  {pillar.pillar_code}: {pillar.pillar_name}
                </h4>
                <p className="text-sm text-gray-500 mt-1">
                  Score: {pillar.score.toFixed(0)} • L2 Weight: {(pillar.l2_weight * 100).toFixed(0)}% • 
                  Contribution: {pillar.contribution.toFixed(1)} points
                </p>
              </div>
              <div className={`px-3 py-1 rounded-full text-xs font-medium flex items-center space-x-1 ${
                pillar.score >= 80 ? 'bg-green-100 text-green-800' :
                pillar.score >= 50 ? 'bg-yellow-100 text-yellow-800' :
                'bg-red-100 text-red-800'
              }`}>
                {pillar.score >= 80 ? '✅ HEALTHY' : pillar.score >= 50 ? '⚠️ AT RISK' : '🔴 CRITICAL'}
              </div>
            </div>
          </button>

          {/* Expanded KPI Details */}
          {expandedPillar === pillar.pillar_code && pillar.kpis.length > 0 && (
            <div className="border-t border-gray-100 p-4 bg-gray-50">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-2 px-3 font-medium text-gray-700">KPI</th>
                      <th className="text-left py-2 px-3 font-medium text-gray-700">Value</th>
                      <th className="text-left py-2 px-3 font-medium text-gray-700">Score</th>
                      <th className="text-left py-2 px-3 font-medium text-gray-700">L1 Weight</th>
                      <th className="text-left py-2 px-3 font-medium text-gray-700">State</th>
                      <th className="text-left py-2 px-3 font-medium text-gray-700">Range</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pillar.kpis.map((kpi) => (
                      <tr key={kpi.kpi_code} className="border-b border-gray-100">
                        <td className="py-3 px-3 font-medium text-gray-900">{kpi.kpi_name}</td>
                        <td className="py-3 px-3 text-gray-700">{kpi.current_value}</td>
                        <td className="py-3 px-3 font-semibold">{kpi.score}</td>
                        <td className="py-3 px-3 text-gray-600">{(kpi.l1_weight * 100).toFixed(1)}%</td>
                        <td className="py-3 px-3">
                          <span className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs ${getStateColor(kpi.state)}`}>
                            {getStateIcon(kpi.state)}
                            <span>{kpi.state.toUpperCase()}</span>
                          </span>
                        </td>
                        <td className="py-3 px-3 text-xs text-gray-500">
                          {kpi.reference_range ? (
                            <span>
                              Healthy: {kpi.reference_range.healthy_min}-{kpi.reference_range.healthy_max} • 
                              Risk: {kpi.reference_range.risk_min}-{kpi.reference_range.risk_max} • 
                              Critical: &gt;{kpi.reference_range.critical_min}
                            </span>
                          ) : 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 p-3 bg-blue-50 rounded-lg text-xs text-blue-800">
                <strong>Pillar Score Calculation:</strong> {' '}
                {pillar.kpis.map(kpi => `${kpi.kpi_name} (${kpi.score}×${(kpi.l1_weight * 100).toFixed(1)}%)`).join(' + ')} = {pillar.score.toFixed(0)}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default DCTenantKPIDetails;
