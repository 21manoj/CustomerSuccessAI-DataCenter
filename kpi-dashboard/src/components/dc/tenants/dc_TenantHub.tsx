/**
 * Data Center Tenant Hub
 * ======================
 * 
 * Main wrapper component for Tenant management:
 * - List view (default): Shows all tenants
 * - Detail view: Shows placard + sub-tabs when tenant selected
 * 
 * Sub-tabs:
 * - Journey Timeline
 * - Infrastructure
 * - KPI Details
 * - Activity History
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useSession } from '../../../contexts/SessionContext';
import TenantList_dc from '../../TenantList_dc';
import JourneyDashboardV3 from '../../journey-visualizer/JourneyDashboardV3';
import DCTenantPlacard from './dc_TenantPlacard';
import DCTenantKPIDetails from './dc_TenantKPIDetails';
import DCInfrastructureHealth from './dc_InfrastructureHealth';
import { RefreshCw, AlertTriangle, Server } from 'lucide-react';

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
  account_status?: string;
  revenue?: number;
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

type SubTab = 'journey' | 'infrastructure' | 'kpis' | 'activity';

// ============================================================
// MAIN COMPONENT
// ============================================================

const DCTenantHub: React.FC = () => {
  const { session } = useSession();
  const navigate = useNavigate();
  const location = useLocation();
  const { accountId } = useParams<{ accountId?: string }>();
  
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<number | null>(
    accountId ? parseInt(accountId) : null
  );
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('journey');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Get sub-tab from URL query params
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tab = params.get('tab') as SubTab;
    if (tab && ['journey', 'infrastructure', 'kpis', 'activity'].includes(tab)) {
      setActiveSubTab(tab);
    }
  }, [location.search]);

  // Update selected tenant from URL
  useEffect(() => {
    if (accountId) {
      const id = parseInt(accountId);
      if (!isNaN(id)) {
        setSelectedTenantId(id);
      }
    } else {
      setSelectedTenantId(null);
    }
  }, [accountId]);

  // Fetch tenants (accounts) from API
  useEffect(() => {
    fetchTenants();
  }, [session?.customer_id]);

  const fetchTenants = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('[DCTenantHub] Fetching tenants...', { 
        customer_id: session?.customer_id,
        hasSession: !!session,
        cookies: document.cookie 
      });
      
      // First check if backend session is valid
      const sessionCheck = await fetch('/api/session/status', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!sessionCheck.ok || !(await sessionCheck.json()).authenticated) {
        console.warn('[DCTenantHub] Backend session invalid, redirecting to login');
        // Redirect to login if session is invalid
        window.location.href = '/login';
        return;
      }
      
      // Use DC2_S accounts API (same as main dashboard) so Tenants tab shows same list
      const response = await fetch('/api/dc2s/accounts', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(session?.customer_id ? { 'X-Customer-ID': String(session.customer_id) } : {}),
        },
      });

      console.log('[DCTenantHub] Response status:', response.status, response.statusText);

      if (!response.ok) {
        if (response.status === 401) {
          console.warn('[DCTenantHub] Session expired, redirecting to login');
          window.location.href = '/login';
          return;
        }
        const errorText = await response.text();
        console.error('[DCTenantHub] Error response:', errorText);
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const accountsArray = data.accounts ?? (Array.isArray(data) ? data : []);
      console.log('[DCTenantHub] Response data:', { total: data.total ?? accountsArray.length, accounts_count: accountsArray.length });

      // Map DC2_S accounts to Tenant interface (same shape as /api/accounts for compatibility)
      const mappedTenants: Tenant[] = accountsArray.map((acc: any) => ({
        tenant_id: acc.account_id,
        tenant_name: acc.account_name,
        health_score: acc.overall_health ?? acc.health_score ?? 0,
        status: getHealthStatus(acc.overall_health ?? acc.health_score ?? 0),
        industry: acc.industry,
        region: acc.region,
        account_status: acc.account_status ?? acc.status ?? 'Active',
        revenue: acc.revenue,
        metadata: acc.metadata ?? {
          account_tier: acc.profile_metadata?.account_tier,
          assigned_csm: acc.profile_metadata?.assigned_csm,
          csm_manager: acc.profile_metadata?.csm_manager,
          products_used: acc.profile_metadata?.products_used,
          engagement: acc.profile_metadata?.engagement ? { lifecycle_stage: acc.profile_metadata.engagement.lifecycle_stage } : {},
          champions: acc.profile_metadata?.champions,
        },
        kpi_count: acc.kpi_count,
        last_measured: acc.last_measured,
      }));

      console.log('[DCTenantHub] Mapped tenants:', mappedTenants.length);
      setTenants(mappedTenants);
    } catch (err: any) {
      console.error('[DCTenantHub] Error fetching tenants:', err);
      setError(err.message || 'Failed to load tenants');
    } finally {
      setLoading(false);
    }
  };

  const getHealthStatus = (score: number): 'healthy' | 'at_risk' | 'critical' => {
    if (score >= 80) return 'healthy';
    if (score >= 50) return 'at_risk';
    return 'critical';
  };

  const handleSelectTenant = (tenantId: number | null) => {
    setSelectedTenantId(tenantId);
    if (tenantId) {
      navigate(`/dc-dashboard/tenants/${tenantId}?tab=${activeSubTab}`);
    } else {
      navigate('/dc-dashboard/tenants');
    }
  };

  const handleSubTabChange = (tab: SubTab) => {
    setActiveSubTab(tab);
    if (selectedTenantId) {
      navigate(`/dc-dashboard/tenants/${selectedTenantId}?tab=${tab}`, { replace: true });
    }
  };

  const selectedTenant = tenants.find(t => t.tenant_id === selectedTenantId);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
        <span className="ml-3 text-gray-600">Loading tenants...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-700 mb-4">{error}</p>
        <button
          onClick={fetchTenants}
          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  // Detail View: Show placard + sub-tabs
  if (selectedTenant) {
    return (
      <div className="space-y-6">
        {/* Tenant Placard (always visible at top) */}
        <DCTenantPlacard tenant={selectedTenant} />

        {/* Sub-tabs Navigation */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          <nav className="flex space-x-8 px-6 border-b border-gray-200">
            {[
              { id: 'journey' as SubTab, label: 'Journey Timeline' },
              { id: 'infrastructure' as SubTab, label: 'Infrastructure' },
              { id: 'kpis' as SubTab, label: 'KPI Details' },
              { id: 'activity' as SubTab, label: 'Activity History' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => handleSubTabChange(tab.id)}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeSubTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          {/* Sub-tab Content */}
          <div className="p-6">
            {activeSubTab === 'journey' && (
              <JourneyDashboardV3 accountId={String(selectedTenant.tenant_id)} />
            )}
            
            {activeSubTab === 'infrastructure' && (
              <DCInfrastructureHealth tenantId={selectedTenant.tenant_id} />
            )}
            
            {activeSubTab === 'kpis' && (
              <DCTenantKPIDetails tenantId={selectedTenant.tenant_id} />
            )}
            
            {activeSubTab === 'activity' && (
              <div className="text-center py-12 text-gray-500">
                <p>Activity History component will be built here</p>
                <p className="text-sm mt-2">Shows tenant activity logs, events, and timeline</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // List View: Show all tenants
  console.log('[DCTenantHub] Rendering list view:', { 
    tenantsCount: tenants.length, 
    loading, 
    error,
    hasSession: !!session 
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Tenants</h2>
          <p className="text-sm text-gray-500 mt-1">
            {tenants.length} tenant{tenants.length !== 1 ? 's' : ''} found
            {session && ` (Customer ${session.customer_id})`}
          </p>
        </div>
        <button
          onClick={fetchTenants}
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center space-x-2"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh</span>
        </button>
      </div>

      {tenants.length > 0 ? (
        <TenantList_dc
          tenants={tenants}
          onSelectTenant={handleSelectTenant}
          selectedTenant={selectedTenantId}
        />
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <Server className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Tenants Found</h3>
          <p className="text-gray-500 mb-4">
            {error 
              ? `Error: ${error}` 
              : 'No tenants found for this customer. Please check your data or contact support.'}
          </p>
          {error && (
            <button
              onClick={fetchTenants}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default DCTenantHub;
