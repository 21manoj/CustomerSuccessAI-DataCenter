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

import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useSession } from '../../../contexts/SessionContext';
import { useEntitlements } from '../../../hooks/useEntitlement';
import { classify } from '../../../utils/healthThresholds';
import TenantList_dc from '../../TenantList_dc';
import JourneyDashboardV3 from '../../journey-visualizer/JourneyDashboardV3';
import DCTenantPlacard from './dc_TenantPlacard';
import DCTenantKPIDetails from './dc_TenantKPIDetails';
import DCInfrastructureHealth from './dc_InfrastructureHealth';
import EmptyState from '../../shared/EmptyState';
import { RefreshCw, AlertTriangle, Server, Search, Upload, ArrowUpDown } from 'lucide-react';

// ============================================================
// TYPES
// ============================================================

interface Tenant {
  tenant_id: number | string;
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

type HealthFilter = 'all' | 'healthy' | 'at_risk' | 'critical';
type SortField = 'name' | 'health' | 'arr';

const DCTenantHub: React.FC = () => {
  const { session } = useSession();
  const { tier } = useEntitlements();
  const isStarter = tier === 'starter';
  const navigate = useNavigate();
  const location = useLocation();
  const { accountId } = useParams<{ accountId?: string }>();

  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<number | string | null>(
    accountId || null
  );
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('journey');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [healthFilter, setHealthFilter] = useState<HealthFilter>('all');
  const [sortField, setSortField] = useState<SortField>('health');
  const [sortAsc, setSortAsc] = useState(false); // default: worst health first

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
      setSelectedTenantId(accountId);
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

  const handleSelectTenant = (tenantId: number | string | null) => {
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

  // Filtered + sorted tenants
  const filteredTenants = useMemo(() => {
    let result = [...tenants];

    // Text search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(t =>
        t.tenant_name.toLowerCase().includes(q) ||
        (t.industry && t.industry.toLowerCase().includes(q))
      );
    }

    // Health filter
    if (healthFilter !== 'all') {
      result = result.filter(t => {
        const classification = classify(t.health_score);
        return classification === healthFilter;
      });
    }

    // Sort
    result.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'name':
          cmp = a.tenant_name.localeCompare(b.tenant_name);
          break;
        case 'health':
          cmp = a.health_score - b.health_score;
          break;
        case 'arr':
          cmp = (a.revenue || 0) - (b.revenue || 0);
          break;
      }
      return sortAsc ? cmp : -cmp;
    });

    return result;
  }, [tenants, searchQuery, healthFilter, sortField, sortAsc]);

  // Health distribution counts
  const healthCounts = useMemo(() => {
    const counts = { healthy: 0, at_risk: 0, critical: 0 };
    tenants.forEach(t => {
      const c = classify(t.health_score);
      if (c === 'healthy') counts.healthy++;
      else if (c === 'at_risk') counts.at_risk++;
      else counts.critical++;
    });
    return counts;
  }, [tenants]);

  const handleSortToggle = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(field === 'name'); // Name defaults to A-Z, others descending
    }
  };

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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{isStarter ? 'Accounts' : 'Tenants'}</h2>
          <p className="text-sm text-gray-500 mt-1">
            {tenants.length} {isStarter ? 'account' : 'tenant'}{tenants.length !== 1 ? 's' : ''} found
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
        <>
          {/* Search & Filter Bar */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="flex items-center space-x-4">
              {/* Search */}
              <div className="flex-1 flex items-center bg-gray-50 rounded-lg px-3 py-2">
                <Search className="h-4 w-4 text-gray-400 mr-2" />
                <input
                  type="text"
                  placeholder={`Search ${isStarter ? 'accounts' : 'tenants'}...`}
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="flex-1 bg-transparent text-sm outline-none text-gray-700 placeholder-gray-400"
                />
                {searchQuery && (
                  <button onClick={() => setSearchQuery('')} className="text-gray-400 hover:text-gray-600">
                    <span className="text-xs">Clear</span>
                  </button>
                )}
              </div>

              {/* Sort */}
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => handleSortToggle('health')}
                  className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                    sortField === 'health' ? 'bg-blue-100 text-blue-700' : 'text-gray-500 hover:bg-gray-100'
                  }`}
                >
                  Score {sortField === 'health' && (sortAsc ? '\u2191' : '\u2193')}
                </button>
                <button
                  onClick={() => handleSortToggle('name')}
                  className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                    sortField === 'name' ? 'bg-blue-100 text-blue-700' : 'text-gray-500 hover:bg-gray-100'
                  }`}
                >
                  Name {sortField === 'name' && (sortAsc ? '\u2191' : '\u2193')}
                </button>
              </div>
            </div>

            {/* Health Filter Chips */}
            <div className="flex items-center space-x-2 mt-3">
              {([
                { key: 'all' as HealthFilter, label: 'All', count: tenants.length, color: 'gray' },
                { key: 'critical' as HealthFilter, label: 'Critical', count: healthCounts.critical, color: 'red' },
                { key: 'at_risk' as HealthFilter, label: 'At Risk', count: healthCounts.at_risk, color: 'yellow' },
                { key: 'healthy' as HealthFilter, label: 'Healthy', count: healthCounts.healthy, color: 'green' },
              ]).map(chip => (
                <button
                  key={chip.key}
                  onClick={() => setHealthFilter(chip.key)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    healthFilter === chip.key
                      ? chip.color === 'red' ? 'bg-red-100 text-red-700 ring-1 ring-red-300' :
                        chip.color === 'yellow' ? 'bg-yellow-100 text-yellow-700 ring-1 ring-yellow-300' :
                        chip.color === 'green' ? 'bg-green-100 text-green-700 ring-1 ring-green-300' :
                        'bg-gray-200 text-gray-700 ring-1 ring-gray-300'
                      : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                  }`}
                >
                  {chip.label} ({chip.count})
                </button>
              ))}
            </div>
          </div>

          {/* Filtered results */}
          {filteredTenants.length > 0 ? (
            <TenantList_dc
              tenants={filteredTenants}
              onSelectTenant={handleSelectTenant}
              selectedTenant={selectedTenantId}
            />
          ) : (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <Search className="h-8 w-8 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">No {isStarter ? 'accounts' : 'tenants'} match your search or filter</p>
              <button
                onClick={() => { setSearchQuery(''); setHealthFilter('all'); }}
                className="mt-2 text-sm text-blue-600 hover:text-blue-700"
              >
                Clear filters
              </button>
            </div>
          )}
        </>
      ) : (
        /* Empty state with CTA */
        <EmptyState
          icon={Upload}
          title={`No ${isStarter ? 'Accounts' : 'Tenants'} Found`}
          description={
            isStarter
              ? 'Your accounts will appear here after you upload your data.'
              : 'No tenants found for this customer. Upload data to get started.'
          }
          action={{
            label: 'Upload Data',
            onClick: () => navigate('/dc-dashboard/data-integration'),
          }}
          secondaryAction={{
            label: 'Refresh',
            onClick: fetchTenants,
          }}
        />
      )}
    </div>
  );
};

export default DCTenantHub;
