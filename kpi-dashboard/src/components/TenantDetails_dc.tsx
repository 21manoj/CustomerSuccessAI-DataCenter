/**
 * Data Center Tenant Details Component
 * Detailed view for a specific DC tenant
 */

import React, { useState, useEffect } from 'react';
import { Server, Activity, AlertTriangle, TrendingUp, Calendar } from 'lucide-react';
import HealthScore_dc from './HealthScore_dc';
import KPICard_dc from './KPICard_dc';

interface TenantDetailsProps {
  tenantId: number;
  tenantName?: string;
}

const TenantDetails_dc: React.FC<TenantDetailsProps> = ({ tenantId, tenantName }) => {
  const [tenantData, setTenantData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTenantData();
  }, [tenantId]);

  const loadTenantData = async () => {
    setLoading(true);
    try {
      // Load tenant details
      const response = await fetch(`/api/dc/health-score/${tenantId}`, {
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setTenantData(data);
      }
    } catch (error) {
      console.error('Error loading tenant data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Tenant Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Server className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                {tenantName || tenantData?.account_name || `Tenant ${tenantId}`}
              </h2>
              <p className="text-sm text-gray-500 mt-1">Tenant ID: {tenantId}</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500">Last Updated</p>
            <p className="text-sm font-medium text-gray-900">
              {new Date().toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>

      {/* Health Score */}
      <HealthScore_dc tenantId={tenantId} />

      {/* KPI Cards */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Key Performance Indicators</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <KPICard_dc tenantId={tenantId} />
        </div>
      </div>
    </div>
  );
};

export default TenantDetails_dc;

