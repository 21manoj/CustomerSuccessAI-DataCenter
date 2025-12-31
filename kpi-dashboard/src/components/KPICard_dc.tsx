/**
 * Data Center KPI Card Component
 * Displays individual KPI metrics for DC tenants
 */

import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';
import { useSession } from '../contexts/SessionContext';

interface KPICardProps {
  tenantId: number | null;
  kpiId?: string;
  kpiName?: string;
  value?: number;
  unit?: string;
  target?: number;
  pillar?: string;
}

const KPICard_dc: React.FC<KPICardProps> = ({ tenantId, kpiId, kpiName, value, unit, target, pillar }) => {
  const { session } = useSession();
  const [kpiData, setKpiData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (tenantId) {
      loadKPIData();
    }
  }, [tenantId, kpiId]);

  const loadKPIData = async () => {
    if (!tenantId) return;
    
    setLoading(true);
    try {
      // Load KPI data for tenant
      const response = await fetch(`/api/dc/kpis`, {
        credentials: 'include',
        headers: {
          'X-Customer-ID': session?.customer_id?.toString() || '',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setKpiData(data);
      }
    } catch (error) {
      console.error('Error loading KPI data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-4 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
        <div className="h-8 bg-gray-200 rounded w-1/2"></div>
      </div>
    );
  }

  const displayValue = value !== undefined ? value : kpiData?.value || 0;
  const displayName = kpiName || kpiData?.kpi_name || 'KPI';
  const displayUnit = unit || kpiData?.unit || '';
  const displayTarget = target !== undefined ? target : kpiData?.target || 0;
  const displayPillar = pillar || kpiData?.pillar || '';

  // Calculate trend (mock for now)
  const trend = displayValue > displayTarget ? 'up' : displayValue < displayTarget ? 'down' : 'stable';
  const trendValue = displayTarget > 0 ? ((displayValue - displayTarget) / displayTarget * 100) : 0;

  const getStatusColor = () => {
    if (displayValue >= displayTarget * 0.9) return 'text-green-600';
    if (displayValue >= displayTarget * 0.7) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500 mb-1">{displayPillar}</p>
          <h3 className="text-lg font-semibold text-gray-900">{displayName}</h3>
        </div>
        {trend !== 'stable' && (
          <div className={`flex items-center gap-1 ${getStatusColor()}`}>
            {trend === 'up' ? (
              <TrendingUp className="h-5 w-5" />
            ) : (
              <TrendingDown className="h-5 w-5" />
            )}
          </div>
        )}
      </div>

      <div className="mb-4">
        <div className="flex items-baseline gap-2">
          <span className={`text-3xl font-bold ${getStatusColor()}`}>
            {displayValue.toLocaleString()}
          </span>
          {displayUnit && (
            <span className="text-sm text-gray-500">{displayUnit}</span>
          )}
        </div>
        {displayTarget > 0 && (
          <p className="text-sm text-gray-500 mt-1">
            Target: {displayTarget.toLocaleString()} {displayUnit}
          </p>
        )}
      </div>

      {trendValue !== 0 && (
        <div className="flex items-center gap-2 text-sm">
          <span className={trend === 'up' ? 'text-green-600' : 'text-red-600'}>
            {trend === 'up' ? '+' : ''}{trendValue.toFixed(1)}%
          </span>
          <span className="text-gray-500">vs target</span>
        </div>
      )}

      {displayValue < displayTarget * 0.7 && (
        <div className="mt-4 flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded p-2">
          <AlertTriangle className="h-4 w-4" />
          <span>Below target threshold</span>
        </div>
      )}
    </div>
  );
};

export default KPICard_dc;

