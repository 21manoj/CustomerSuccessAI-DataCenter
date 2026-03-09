/**
 * Data Center Tenant List Component
 * Displays list of DC tenants with customer profile cards (matching SaaS Account Health Dashboard)
 */

import React from 'react';
import { Eye, Server, Users } from 'lucide-react';

interface Tenant {
  tenant_id: number | string;
  tenant_name: string;
  health_score: number;
  status: 'healthy' | 'at_risk' | 'critical' | 'risk';
  industry?: string;
  region?: string;
  account_status?: string;
  metadata?: {
    account_tier?: string;
    assigned_csm?: string;
    csm_manager?: string;
    products_used?: string;
    engagement?: {
      lifecycle_stage?: string;
    };
    champions?: Array<{
      primary_champion_name?: string;
    }>;
  };
  kpi_count?: number;
  last_measured?: string;
}

interface TenantListProps {
  tenants: Tenant[];
  onSelectTenant: (tenantId: number | string | null) => void;
  selectedTenant: number | string | null;
}

const TenantList_dc: React.FC<TenantListProps> = ({ tenants, onSelectTenant, selectedTenant }) => {
  const getHealthStatus = (score: number) => {
    if (score >= 70) return { status: 'Healthy', color: 'green' };
    if (score >= 50) return { status: 'At Risk', color: 'yellow' };
    return { status: 'Critical', color: 'red' };
  };

  const getHealthColor = (score: number) => {
    if (score >= 70) return 'bg-green-500';
    if (score >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
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
    <div className="space-y-4">
      {tenants.map((tenant) => {
        const healthStatus = getHealthStatus(tenant.health_score);
        const isSelected = selectedTenant === tenant.tenant_id;
        
        return (
          <div key={tenant.tenant_id} className="border-2 border-gray-200 rounded-lg overflow-hidden">
            {/* Tenant Header Button */}
            <button
              onClick={() => {
                if (isSelected) {
                  onSelectTenant(null);
                } else {
                  onSelectTenant(tenant.tenant_id);
                }
              }}
              className={`w-full p-4 text-left transition-all hover:bg-gray-50 ${
                isSelected 
                  ? 'bg-blue-50 border-blue-500' 
                  : 'bg-white'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold text-gray-900 text-lg">{tenant.tenant_name}</h4>
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${getHealthColor(tenant.health_score)}`}></div>
                  <span className="text-sm text-gray-500">
                    {isSelected ? '▼' : '▶'}
                  </span>
                </div>
              </div>
              
              {/* Tenant Details Grid - Matching SaaS Format */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                {/* Health Score with Status */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Health Score</p>
                  <div className="flex items-center space-x-2">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      healthStatus.color === 'green' ? 'bg-green-100 text-green-800' :
                      healthStatus.color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {healthStatus.status}
                    </span>
                    <span className="font-semibold text-gray-900">
                      {tenant.health_score?.toFixed(0) || 'N/A'}
                    </span>
                  </div>
                </div>
                
                {/* Region */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Region</p>
                  <p className="font-medium text-gray-900">{tenant.region || 'N/A'}</p>
                </div>
                
                {/* Status */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Status</p>
                  <p className="font-medium text-gray-900 capitalize">{tenant.account_status || 'N/A'}</p>
                </div>
                
                {/* Account Tier */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Account Tier</p>
                  <p className="font-medium text-gray-900">{tenant.metadata?.account_tier || 'N/A'}</p>
                </div>
                
                {/* Assigned CSM */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Assigned CSM</p>
                  <p className="font-medium text-gray-900">{tenant.metadata?.assigned_csm || 'N/A'}</p>
                </div>
                
                {/* CSM Manager */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">CSM Manager</p>
                  <p className="font-medium text-gray-900">{tenant.metadata?.csm_manager || 'N/A'}</p>
                </div>
                
                {/* Products Used */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Products Used</p>
                  <p className="font-medium text-gray-900">{tenant.metadata?.products_used || 'N/A'}</p>
                </div>
                
                {/* Champion Name */}
                <div>
                  <p className="text-xs text-gray-500 mb-1">Champion Name</p>
                  <p className="font-medium text-gray-900">
                    {tenant.metadata?.champions?.[0]?.primary_champion_name || 'N/A'}
                  </p>
                </div>
              </div>
              
              {/* Additional Info Row */}
              <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-500 grid grid-cols-2 md:grid-cols-3 gap-2">
                <p>Industry: {tenant.industry || 'N/A'}</p>
                {tenant.metadata?.engagement?.lifecycle_stage && (
                  <p>Lifecycle: {tenant.metadata.engagement.lifecycle_stage}</p>
                )}
                {tenant.kpi_count !== undefined && (
                  <p>KPIs: {tenant.kpi_count}</p>
                )}
              </div>
              
              {/* View KPIs Link */}
              <div className="mt-3 flex items-center text-xs text-blue-600">
                <Eye className="h-3 w-3 mr-1" />
                {isSelected ? 'Hide KPIs' : 'View KPIs'}
              </div>
            </button>
          </div>
        );
      })}
    </div>
  );
};

export default TenantList_dc;

