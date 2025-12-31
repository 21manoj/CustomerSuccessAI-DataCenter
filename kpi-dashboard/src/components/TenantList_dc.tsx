/**
 * Data Center Tenant List Component
 * Displays list of DC tenants with health status
 */

import React from 'react';
import { Server, CheckCircle, AlertTriangle, XCircle, ChevronRight } from 'lucide-react';

interface Tenant {
  tenant_id: number;
  tenant_name: string;
  health_score: number;
  status: 'healthy' | 'at_risk' | 'critical';
}

interface TenantListProps {
  tenants: Tenant[];
  onSelectTenant: (tenantId: number) => void;
  selectedTenant: number | null;
}

const TenantList_dc: React.FC<TenantListProps> = ({ tenants, onSelectTenant, selectedTenant }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'at_risk':
        return <AlertTriangle className="h-5 w-5 text-yellow-600" />;
      case 'critical':
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Server className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'border-green-200 bg-green-50';
      case 'at_risk':
        return 'border-yellow-200 bg-yellow-50';
      case 'critical':
        return 'border-red-200 bg-red-50';
      default:
        return 'border-gray-200 bg-white';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-green-600';
    if (score >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (tenants.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-12 text-center">
        <Server className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Tenants Found</h3>
        <p className="text-gray-500">Add tenants to get started with Data Center management.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Tenants ({tenants.length})</h2>
      </div>
      <div className="divide-y divide-gray-200">
        {tenants.map((tenant) => (
          <button
            key={tenant.tenant_id}
            onClick={() => onSelectTenant(tenant.tenant_id)}
            className={`w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors ${
              selectedTenant === tenant.tenant_id ? getStatusColor(tenant.status) : ''
            }`}
          >
            <div className="flex items-center gap-4 flex-1">
              {getStatusIcon(tenant.status)}
              <div className="flex-1 text-left">
                <h3 className="text-sm font-medium text-gray-900">{tenant.tenant_name}</h3>
                <p className="text-xs text-gray-500 mt-1">Tenant ID: {tenant.tenant_id}</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className={`text-sm font-semibold ${getScoreColor(tenant.health_score)}`}>
                  {tenant.health_score.toFixed(1)}
                </p>
                <p className="text-xs text-gray-500">Health Score</p>
              </div>
              <ChevronRight className="h-5 w-5 text-gray-400" />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default TenantList_dc;

