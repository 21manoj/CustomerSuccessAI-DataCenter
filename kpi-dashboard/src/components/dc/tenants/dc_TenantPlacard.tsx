/**
 * Data Center Tenant Placard
 * ===========================
 * 
 * Summary card displayed at top of tenant detail view.
 * Shows:
 * - Tenant name, logo
 * - Overall health score and status
 * - 5 pillar mini-gauges
 * - Key metrics (ARR, Renewal, CSM)
 * - Quick actions
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus,
  MessageSquare,
  Brain,
  Play,
  ChevronDown,
  ChevronUp,
  BarChart3
} from 'lucide-react';

// ============================================================
// TYPES
// ============================================================

interface Tenant {
  tenant_id: number;
  tenant_name: string;
  health_score: number;
  status: 'healthy' | 'at_risk' | 'critical';
  industry?: string;
  region?: string;
  revenue?: number;
  metadata?: {
    assigned_csm?: string;
    products_used?: string;
  };
}

interface PillarScore {
  pillar: string;
  name: string;
  score: number;
  weight: number;
}

interface TenantPlacardProps {
  tenant: Tenant;
}

// ============================================================
// MAIN COMPONENT
// ============================================================

const DCTenantPlacard: React.FC<TenantPlacardProps> = ({ tenant }) => {
  const navigate = useNavigate();
  const [pillarScores, setPillarScores] = useState<PillarScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    fetchPillarScores();
  }, [tenant.tenant_id]);

  const fetchPillarScores = async () => {
    try {
      setLoading(true);
      // TODO: Replace with actual API endpoint when available
      // For now, use default pillar structure
      const defaultPillars: PillarScore[] = [
        { pillar: 'P1', name: 'Deployment Velocity', score: 85, weight: 0.15 },
        { pillar: 'P2', name: 'Operational Stability', score: 45, weight: 0.20 },
        { pillar: 'P3', name: 'AI Workload Performance', score: 78, weight: 0.25 },
        { pillar: 'P4', name: 'Channel & Partner Health', score: 82, weight: 0.15 },
        { pillar: 'P5', name: 'Expansion Readiness', score: 68, weight: 0.25 },
      ];
      
      // TODO: Fetch from /api/journey/:accountId/pillars when available
      setPillarScores(defaultPillars);
    } catch (err) {
      console.error('Error fetching pillar scores:', err);
    } finally {
      setLoading(false);
    }
  };

  const getHealthColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getHealthStatusBadge = (score: number) => {
    if (score >= 80) return { label: 'HEALTHY', color: 'bg-green-100 text-green-800' };
    if (score >= 50) return { label: 'AT RISK', color: 'bg-yellow-100 text-yellow-800' };
    return { label: 'CRITICAL', color: 'bg-red-100 text-red-800' };
  };

  const getTrendIcon = (score: number) => {
    // TODO: Calculate actual trend from historical data
    if (score >= 80) return <TrendingUp className="w-4 h-4 text-green-600" />;
    if (score >= 50) return <Minus className="w-4 h-4 text-yellow-600" />;
    return <TrendingDown className="w-4 h-4 text-red-600" />;
  };

  const healthBadge = getHealthStatusBadge(tenant.health_score);

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* Header - Collapsible */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full p-6 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center space-x-4 flex-1">
          {/* Logo placeholder */}
          <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-lg">
            {tenant.tenant_name.charAt(0).toUpperCase()}
          </div>

          <div className="flex-1">
            <div className="flex items-center space-x-3">
              <h3 className="text-xl font-bold text-gray-900">{tenant.tenant_name}</h3>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${healthBadge.color}`}>
                {healthBadge.label}
              </span>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              {tenant.industry || 'N/A'} • {tenant.region || 'N/A'}
            </p>
          </div>

          <div className="flex items-center space-x-4">
            {/* Health Score */}
            <div className="text-right">
              <p className="text-xs text-gray-500">Health Score</p>
              <div className="flex items-center space-x-1">
                {getTrendIcon(tenant.health_score)}
                <span className={`text-2xl font-bold ${getHealthColor(tenant.health_score)}`}>
                  {tenant.health_score?.toFixed(0) || 'N/A'}
                </span>
              </div>
            </div>

            {collapsed ? (
              <ChevronDown className="w-5 h-5 text-gray-400" />
            ) : (
              <ChevronUp className="w-5 h-5 text-gray-400" />
            )}
          </div>
        </div>
      </button>

      {/* Expanded Content */}
      {!collapsed && (
        <div className="px-6 pb-6 border-t border-gray-100">
          {/* 5 Pillar Mini-Gauges */}
          <div className="mt-4 mb-6">
            <p className="text-sm font-medium text-gray-700 mb-3">Pillar Scores</p>
            <div className="grid grid-cols-5 gap-3">
              {pillarScores.map((pillar) => (
                <div key={pillar.pillar} className="text-center">
                  <div className="relative w-16 h-16 mx-auto mb-2">
                    <svg className="transform -rotate-90 w-16 h-16">
                      <circle
                        cx="32"
                        cy="32"
                        r="28"
                        stroke="#e5e7eb"
                        strokeWidth="4"
                        fill="none"
                      />
                      <circle
                        cx="32"
                        cy="32"
                        r="28"
                        stroke={pillar.score >= 80 ? '#10b981' : pillar.score >= 50 ? '#f59e0b' : '#ef4444'}
                        strokeWidth="4"
                        fill="none"
                        strokeDasharray={`${(pillar.score / 100) * 175.9} 175.9`}
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-xs font-bold text-gray-900">{pillar.score}</span>
                    </div>
                  </div>
                  <p className="text-xs font-medium text-gray-700">{pillar.pillar}</p>
                  <p className="text-xs text-gray-500">{pillar.name}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">ARR</p>
              <p className="text-lg font-semibold text-gray-900">
                {tenant.revenue ? `$${(tenant.revenue / 1000000).toFixed(1)}M` : 'N/A'}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">Renewal</p>
              <p className="text-lg font-semibold text-gray-900">45 days</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-gray-500 mb-1">CSM</p>
              <p className="text-lg font-semibold text-gray-900">
                {tenant.metadata?.assigned_csm || 'Unassigned'}
              </p>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex space-x-3">
            <button 
              onClick={() => navigate(`/journey-v3/${tenant.tenant_id}`)}
              className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              <BarChart3 className="w-4 h-4" />
              <span>View Journey</span>
            </button>
            <button className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              <MessageSquare className="w-4 h-4" />
              <span>Signal Analyst</span>
            </button>
            <button className="flex items-center space-x-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700">
              <Brain className="w-4 h-4" />
              <span>RAG Query</span>
            </button>
            <button className="flex items-center space-x-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
              <Play className="w-4 h-4" />
              <span>Run Playbook</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DCTenantPlacard;
