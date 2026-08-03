/**
 * Data Center Dashboard Component
 * Main dashboard for Data Center vertical
 */

import React, { useState, useEffect } from 'react';
import { useSession } from '../contexts/SessionContext';
import { getCustomerIdentifier } from '../utils/api';
import { Activity, AlertTriangle, Users, Zap, BarChart3, Upload, Target, MessageSquare, Settings, FileText, LogOut, ChevronDown, ChevronRight, TrendingDown, Eye } from 'lucide-react';
import NavLogoutButton from './shared/NavLogoutButton';
import { useNavigate } from 'react-router-dom';
import { classify, classifyColor, classifyLabel } from '../utils/healthThresholds';
import KPICard_dc from './KPICard_dc';
import HealthScore_dc from './HealthScore_dc';
import TenantList_dc from './TenantList_dc';
import AlertBanner_dc from './AlertBanner_dc';
import KPIChart_dc from './KPIChart_dc';
import PlaybookPanel_dc from './PlaybookPanel_dc';
import OpenAIKeySettings from './OpenAIKeySettings';
import RAGAnalysis from './RAGAnalysis';
import SignalAnalyst from './SignalAnalyst';

interface PerformanceSummary {
  summary: {
    total_accounts: number;
    critical_accounts: number;
    at_risk_accounts: number;
    healthy_accounts: number;
    average_health_score: number;
    company_avg_revenue_growth: number;
  };
  accounts_needing_attention: Array<{
    account_id: number | string;
    account_name: string;
    overall_health_score: number;
    category_scores: Record<string, number>;
    focus_areas: Array<{category: string; score: number}>;
    active_playbooks_count: number;
    revenue_growth_pct: number;
  }>;
  healthy_declining_revenue: Array<{
    account_id: number | string;
    account_name: string;
    overall_health_score: number;
    category_scores: Record<string, number>;
    focus_areas: Array<{category: string; score: number}>;
    active_playbooks_count: number;
    revenue_growth_pct: number;
  }>;
}

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
  pillar_scores?: Record<string, number>;
  enabled_pillars?: string[];
}

interface KPI {
  kpi_id: number;
  category: string;
  kpi_parameter: string;
  data: string;
  account_id: number | string;
  account_name?: string;
  upload_id?: number;
  upload_filename?: string;
  // DC-specific fields
  unit?: string;
  target?: number;
  status?: 'healthy' | 'at_risk' | 'critical';
  value?: number;
}

const Dashboard_dc: React.FC = () => {
  const { session, logout } = useSession();
  const navigate = useNavigate();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [kpiData, setKpiData] = useState<KPI[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<number | string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'tenants' | 'kpis' | 'analytics' | 'rag-analysis' | 'alerts' | 'upload' | 'reports' | 'settings' | 'insights'>('dashboard');
  const [expandedCategories, setExpandedCategories] = useState<{[key: string]: boolean}>({});
  const [categoryPages, setCategoryPages] = useState<{[key: string]: number}>({});
  const itemsPerPage = 50;
  // DC KPIs don't use monthly data - removed selectedMonth state
  const [tenantKPIs, setTenantKPIs] = useState<KPI[]>([]);
  const [loadingTenantKPIs, setLoadingTenantKPIs] = useState(false);
  const [perfSummary, setPerfSummary] = useState<PerformanceSummary | null>(null);

  useEffect(() => {
    if (session?.customer_id) {
      loadDashboardData();
      fetchPerformanceSummary();
    }
    // Note: loadDashboardData and fetchPerformanceSummary are stable functions
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.customer_id]);

  const fetchPerformanceSummary = async () => {
    if (!session?.customer_id) return;
    
    try {
      const response = await fetch('/api/customer-performance/summary', {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-Customer-ID': getCustomerIdentifier(session),
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.status === 'success') {
          setPerfSummary(data);
        }
      }
    } catch (error) {
      console.error('Error fetching performance summary:', error);
    }
  };

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Load tenants (accounts) - use DC-specific endpoint
      const accountsResponse = await fetch('/api/dc2s/accounts', {
        credentials: 'include',
        headers: {
          'X-Customer-ID': getCustomerIdentifier(session),
        },
      });

      if (accountsResponse.ok) {
        const accountsData = await accountsResponse.json();
        const accountsArray = Array.isArray(accountsData) ? accountsData : (accountsData.accounts || []);
        
        // Transform to tenants format with full profile data (matching SaaS Account Health Dashboard)
        const tenantsData: Tenant[] = accountsArray.map((acc: any) => ({
          tenant_id: acc.account_id,
          tenant_name: acc.account_name,
          health_score: acc.overall_health || acc.health_score || 0,
          status: (acc.status === 'risk' ? 'at_risk' : acc.status || (acc.overall_health >= 80 ? 'healthy' : acc.overall_health >= 50 ? 'at_risk' : 'critical')),
          industry: acc.industry,
          region: acc.region,
          account_status: acc.account_status || 'Active',
          metadata: acc.metadata || {},
          kpi_count: acc.kpi_count,
          last_measured: acc.last_measured,
          pillar_scores: acc.pillar_scores || {},
          enabled_pillars: acc.enabled_pillars || accountsData.enabled_pillars || [],
        }));
        
        setTenants(tenantsData);
        console.log('✅ Loaded tenants with profile data:', tenantsData.length);
      }

      // Load KPIs - use DC-specific endpoint
      const kpisResponse = await fetch('/api/dc2s/kpis/all', {
        credentials: 'include',
        headers: {
          'X-Customer-ID': getCustomerIdentifier(session),
        },
      });

      if (kpisResponse.ok) {
        const kpisData = await kpisResponse.json();
        // Transform DC KPIs to match KPI interface (compatible with SaaS format)
        const transformedKPIs: KPI[] = kpisData.map((kpi: any) => ({
          kpi_id: kpi.kpi_id,
          category: kpi.category || kpi.pillar || 'Uncategorized',
          kpi_parameter: kpi.kpi_parameter || kpi.kpi_code,
          data: kpi.data || '0',
          account_id: kpi.account_id,
          account_name: kpi.account_name,
          upload_id: kpi.upload_id || null,
          upload_filename: kpi.upload_filename || null,
        }));
        setKpiData(transformedKPIs);
        console.log('Loaded DC KPIs:', transformedKPIs.length);
      }
    } catch (err) {
      console.error('Error loading dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const toggleCategory = (categoryName: string) => {
    setExpandedCategories(prev => ({
      ...prev,
      [categoryName]: !prev[categoryName]
    }));
  };

  // DC KPIs use measured_at timestamps, not monthly uploads - removed getMonthFromFilename

  // Fetch KPIs for selected tenant
  useEffect(() => {
    if (selectedTenant && session?.customer_id) {
      fetchTenantKPIs();
    } else {
      setTenantKPIs([]);
    }
    // Note: fetchTenantKPIs is a stable function
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTenant, session?.customer_id]);

  const fetchTenantKPIs = async () => {
    if (!selectedTenant || !session?.customer_id) return;
    
    try {
      setLoadingTenantKPIs(true);
      // Use DC-specific endpoint for tenant KPIs
      const response = await fetch(`/api/dc2s/accounts/${selectedTenant}/kpis`, {
        credentials: 'include',
        headers: {
          'X-Customer-ID': getCustomerIdentifier(session),
        },
      });

      if (response.ok) {
        const kpisData = await response.json();
        console.log('✅ Fetched KPIs for tenant:', selectedTenant, 'Total:', kpisData.kpis?.length || 0);
        console.log('✅ KPIs data structure:', {
          hasKpis: !!kpisData.kpis,
          kpisLength: kpisData.kpis?.length,
          total: kpisData.total,
          accountName: kpisData.account_name
        });
        
        // Transform DC2S KPI format to match KPI interface (endpoint now returns SaaS-compatible format)
        const tenantKPIsData: KPI[] = (kpisData.kpis || []).map((kpi: any) => {
          return {
            kpi_id: kpi.kpi_id,
            category: kpi.category || kpi.pillar || 'Uncategorized',
            kpi_parameter: kpi.kpi_parameter || kpi.kpi_code,
            data: kpi.data || String(kpi.value || '0'),
            account_id: kpi.account_id,
            account_name: kpisData.account_name || '',
            upload_id: null,
            upload_filename: null, // DC KPIs don't have upload filenames - they use measured_at
            // Additional DC-specific fields
            unit: kpi.unit || '',
            target: kpi.target,
            status: kpi.status, // healthy/at_risk/critical
            value: kpi.value,
          };
        });
        console.log('✅ Transformed tenant KPIs:', tenantKPIsData.length);
        console.log('✅ Sample transformed KPI:', tenantKPIsData[0]);
        setTenantKPIs(tenantKPIsData);
      } else {
        const errorText = await response.text();
        console.error('❌ KPIs endpoint error:', response.status, errorText);
        setTenantKPIs([]);
      }
    } catch (error) {
      console.error('Error loading tenant KPIs:', error);
    } finally {
      setLoadingTenantKPIs(false);
    }
  };

  // DC KPIs don't have monthly uploads like SaaS - they use measured_at timestamps
  // Show all KPIs regardless of month selection (since there's only one measurement per KPI)
  const filteredTenantKPIs = tenantKPIs;
  
  console.log('Total tenant KPIs:', tenantKPIs.length, '(DC KPIs show all measurements, not filtered by month)');

  const healthyCount = tenants.filter(t => t.status === 'healthy').length;
  const atRiskCount = tenants.filter(t => t.status === 'at_risk').length;
  const criticalCount = tenants.filter(t => t.status === 'critical').length;
  const avgHealthScore = tenants.length > 0 
    ? tenants.reduce((sum, t) => sum + t.health_score, 0) / tenants.length 
    : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <Activity className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
          <p className="text-gray-600">Loading Data Center Dashboard...</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return <div>Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-gray-50 to-blue-50/20">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-md px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1">
            <div className="flex-1 text-center">
              <h1 className="text-xl font-bold text-gray-900">Customer Success Value Management System - CS Pulse Growth</h1>
              <p className="text-sm text-gray-500 mt-1">Data Center Dashboard</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <span className="text-sm text-gray-600">Welcome, {session.user_name}</span>
            <button 
              onClick={handleLogout}
              className="flex items-center px-3 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg"
            >
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <nav className="w-64 bg-gradient-to-b from-slate-50 to-slate-100 border-r border-slate-200 shadow-sm px-4 py-6 flex flex-col min-h-[calc(100vh-73px)]">
          <div className="space-y-2 flex-1">
            {[
              { id: 'dashboard', label: 'Data Center Dashboard', icon: BarChart3 },
              { id: 'tenants', label: 'Tenants', icon: Users },
              { id: 'kpis', label: 'KPIs', icon: Target },
              { id: 'analytics', label: 'Analytics', icon: Activity },
              { id: 'rag-analysis', label: 'AI Insights', icon: MessageSquare },
              { id: 'insights', label: 'CS AI Agents', icon: Zap },
              { id: 'alerts', label: 'Alerts', icon: AlertTriangle },
              { id: 'upload', label: 'Data Integration', icon: Upload },
              { id: 'reports', label: 'Reports', icon: FileText },
              { id: 'settings', label: 'Settings', icon: Settings },
            ].map(item => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id as any)}
                className={`w-full flex items-center px-4 py-3 rounded-lg text-left transition-all duration-200 ${
                  activeTab === item.id 
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md transform scale-105' 
                    : 'text-gray-700 hover:bg-white hover:shadow-sm hover:text-blue-600'
                }`}
              >
                <item.icon className={`h-5 w-5 mr-3 ${activeTab === item.id ? 'text-white' : ''}`} />
                <span className="font-medium text-sm">{item.label}</span>
              </button>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-slate-200">
            <NavLogoutButton variant="light-sidebar" />
          </div>
        </nav>

        {/* Main Content */}
        <main className="flex-1 p-8 bg-gradient-to-br from-gray-50 via-blue-50/30 to-indigo-50/30">
          {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Average Health Score</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">
                      {avgHealthScore.toFixed(1)}
                    </p>
                  </div>
                  <Activity className="h-12 w-12 text-blue-600" />
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Healthy</p>
                    <p className="text-3xl font-bold text-green-600 mt-2">{healthyCount}</p>
                  </div>
                  <Zap className="h-12 w-12 text-green-600" />
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">At Risk</p>
                    <p className="text-3xl font-bold text-yellow-600 mt-2">{atRiskCount}</p>
                  </div>
                  <AlertTriangle className="h-12 w-12 text-yellow-600" />
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Critical</p>
                    <p className="text-3xl font-bold text-red-600 mt-2">{criticalCount}</p>
                  </div>
                  <AlertTriangle className="h-12 w-12 text-red-600" />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                {/* Accounts Needing Attention - Ported from SaaS */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                      <AlertTriangle className="h-5 w-5 mr-2 text-orange-500" />
                      Accounts Needing Attention
                    </h3>
                    <span className="text-xs text-gray-500">Last 3 months</span>
                  </div>
                  
                  <p className="text-sm text-orange-600 mb-4">
                    ⚠️ These accounts have issues with maintaining healthy scores
                  </p>
                  
                  {perfSummary && perfSummary.accounts_needing_attention.length > 0 ? (
                    <div className="space-y-4">
                      <div className="grid grid-cols-3 gap-2 mb-4 p-3 bg-gray-50 rounded-lg">
                        <div className="text-center">
                          <div className="text-xs text-gray-600">Critical</div>
                          <div className="text-lg font-bold text-red-600">{perfSummary.summary.critical_accounts}</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-gray-600">At Risk</div>
                          <div className="text-lg font-bold text-yellow-600">{perfSummary.summary.at_risk_accounts}</div>
                        </div>
                        <div className="text-center">
                          <div className="text-xs text-gray-600">Healthy</div>
                          <div className="text-lg font-bold text-green-600">{perfSummary.summary.healthy_accounts}</div>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {perfSummary.accounts_needing_attention.map((account) => (
                          <div key={account.account_id} className="border border-gray-200 rounded-lg p-4 hover:border-orange-300 transition-colors cursor-pointer" onClick={() => {setSelectedTenant(account.account_id); setActiveTab('tenants');}}>
                            <h4 className="font-semibold text-gray-900 text-sm mb-2 truncate">{account.account_name}</h4>
                            <div className="flex items-center mb-3 space-x-2">
                              <div className={`px-2 py-0.5 rounded text-xs font-medium ${
                                account.overall_health_score >= 80 ? 'bg-green-100 text-green-800' :
                                account.overall_health_score >= 70 ? 'bg-yellow-100 text-yellow-800' :
                                'bg-red-100 text-red-800'
                              }`}>
                                Score: {account.overall_health_score.toFixed(0)}
                              </div>
                            </div>
                            
                            <div className="space-y-1">
                              {account.focus_areas.map((area, idx) => (
                                <div key={idx} className="flex items-center justify-between text-xs">
                                  <span className="text-gray-600 truncate mr-2">{area.category}</span>
                                  <span className={`font-semibold`} style={{ color: classifyColor(area.score) }}>{area.score.toFixed(0)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Users className="h-12 w-12 text-gray-400 mx-auto mb-2" />
                      <p className="text-sm text-gray-600">Loading account summary...</p>
                    </div>
                  )}
                </div>

                {/* Revenue Decline Alert */}
                {perfSummary && perfSummary.healthy_declining_revenue && perfSummary.healthy_declining_revenue.length > 0 && (
                  <div className="bg-white rounded-xl shadow-sm border border-red-200 p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                        <TrendingDown className="h-5 w-5 mr-2 text-red-500" />
                        Revenue Decline Alert
                      </h3>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {perfSummary.healthy_declining_revenue.map((account) => (
                        <div key={account.account_id} className="border border-red-200 rounded-lg p-3 bg-red-50/30">
                          <h4 className="font-semibold text-gray-900 text-sm mb-1 truncate">{account.account_name}</h4>
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-medium text-green-700 bg-green-100 px-1.5 py-0.5 rounded">H: {account.overall_health_score.toFixed(0)}</span>
                            <span className="text-xs font-medium text-red-700 bg-red-100 px-1.5 py-0.5 rounded">Rev: {account.revenue_growth_pct.toFixed(1)}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-6">
                <HealthScore_dc tenantId={selectedTenant} />
                <AlertBanner_dc tenantId={selectedTenant} />
              </div>
            </div>

            {/* KPI Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <KPIChart_dc tenantId={selectedTenant} />
            </div>

            {/* Playbooks */}
            <PlaybookPanel_dc tenantId={selectedTenant} />
          </div>
        )}

        {activeTab === 'insights' && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">CS AI Agents (Playbooks)</h2>
            <PlaybookPanel_dc tenantId={selectedTenant} />
          </div>
        )}

        {activeTab === 'tenants' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-gray-900">Tenant Health Dashboard</h2>
            </div>

            {/* Tenant List with Profile Cards */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="p-6">
                {tenants.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Users className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>No tenants found. Upload data to get started.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {tenants.map((tenant) => {
                      const isSelected = selectedTenant === tenant.tenant_id;
                      
                      return (
                        <div key={tenant.tenant_id} className="border-2 border-gray-200 rounded-lg overflow-hidden">
                          {/* Tenant Header Button */}
                          <button
                            onClick={() => {
                              if (isSelected) {
                                setSelectedTenant(null);
                              } else {
                                setSelectedTenant(tenant.tenant_id);
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
                                <div className={`w-3 h-3 rounded-full ${
                                  tenant.health_score >= 80 ? 'bg-green-500' :
                                  tenant.health_score >= 60 ? 'bg-yellow-500' :
                                  'bg-red-500'
                                }`}></div>
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
                                {(() => {
                                  const cls = classify(tenant.health_score);
                                  const healthStatus = cls === 'healthy' ? { status: 'Healthy', color: 'green' } :
                                                       cls === 'at_risk' ? { status: 'At Risk', color: 'yellow' } :
                                                       { status: 'Critical', color: 'red' };
                                  return (
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
                                  );
                                })()}
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

                          {/* Expandable KPI Table */}
                          {isSelected && (
                            <div className="border-t border-gray-200 bg-gray-50 p-4">
                              <div className="mb-4">
                                <h5 className="text-lg font-semibold text-gray-900 mb-2">
                                  KPIs for {tenant.tenant_name}
                                </h5>
                                <p className="text-sm text-gray-600">
                                  Showing {filteredTenantKPIs.length} KPIs
                                </p>
                              </div>
                              
                              {loadingTenantKPIs ? (
                                <div className="text-center py-8">
                                  <Activity className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
                                  <p className="text-gray-600">Loading KPIs...</p>
                                </div>
                              ) : filteredTenantKPIs.length === 0 ? (
                                <div className="text-center py-8">
                                  <Target className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                                  <p className="text-gray-600 mb-2">No KPIs found for this tenant</p>
                                </div>
                              ) : (
                                <div className="overflow-x-auto">
                                  <table className="min-w-full divide-y divide-gray-200 bg-white rounded-lg">
                                    <thead className="bg-gray-100">
                                      <tr>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">KPI Parameter</th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Value</th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Target</th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Unit</th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                      </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                      {filteredTenantKPIs.map((kpi) => (
                                        <tr key={kpi.kpi_id} className="hover:bg-gray-50">
                                          <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{kpi.category}</td>
                                          <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{kpi.kpi_parameter}</td>
                                          <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{kpi.data}</td>
                                          <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                            {kpi.target !== undefined ? `${kpi.target}${kpi.unit ? ` ${kpi.unit}` : ''}` : 'N/A'}
                                          </td>
                                          <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{kpi.unit || 'N/A'}</td>
                                          <td className="px-4 py-2 whitespace-nowrap text-sm">
                                            {kpi.status && (
                                              <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                                kpi.status === 'healthy' ? 'bg-green-100 text-green-800' :
                                                kpi.status === 'at_risk' ? 'bg-yellow-100 text-yellow-800' :
                                                'bg-red-100 text-red-800'
                                              }`}>
                                                {kpi.status.charAt(0).toUpperCase() + kpi.status.slice(1)}
                                              </span>
                                            )}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Data Center Analytics</h2>
              <p className="text-gray-600 mb-6">Customer Success Value Analytics for Data Center tenants</p>
              
              {/* Health Score Trends */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Health Score Trends</h3>
                {selectedTenant ? (
                  <div className="space-y-4">
                    <HealthScore_dc tenantId={selectedTenant} />
                  </div>
                ) : (
                  <div className="text-center py-8 bg-gray-50 rounded-lg">
                    <Activity className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600">Select a tenant to view health score trends</p>
                  </div>
                )}
              </div>

              {/* Tenant Performance Summary */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Tenant Performance Summary</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="text-sm font-medium text-green-800 mb-1">Healthy Tenants</div>
                    <div className="text-2xl font-bold text-green-900">{healthyCount}</div>
                  </div>
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <div className="text-sm font-medium text-yellow-800 mb-1">At Risk Tenants</div>
                    <div className="text-2xl font-bold text-yellow-900">{atRiskCount}</div>
                  </div>
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <div className="text-sm font-medium text-red-800 mb-1">Critical Tenants</div>
                    <div className="text-2xl font-bold text-red-900">{criticalCount}</div>
                  </div>
                </div>
              </div>

              {/* KPI Coverage Analytics */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">KPI Coverage Analytics</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-gray-600">Total KPIs</div>
                      <div className="text-xl font-bold text-gray-900">{kpiData.length}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">KPIs with Data</div>
                      <div className="text-xl font-bold text-green-600">
                        {kpiData.filter(k => k.data && k.data !== '0' && k.data !== '').length}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Coverage</div>
                      <div className="text-xl font-bold text-blue-600">
                        {kpiData.length > 0 
                          ? Math.round((kpiData.filter(k => k.data && k.data !== '0' && k.data !== '').length / kpiData.length) * 100)
                          : 0}%
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Tenants Tracked</div>
                      <div className="text-xl font-bold text-purple-600">{tenants.length}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Signal Analyst AI-Powered Analysis */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="mb-4">
                <h2 className="text-xl font-bold text-gray-900 mb-2">AI-Powered Account Analysis</h2>
                <p className="text-gray-600">
                  Get AI-powered insights about account churn risk, expansion opportunities, and recommended actions
                </p>
              </div>
              {selectedTenant ? (
                <SignalAnalyst
                  accountId={selectedTenant}
                  accountName={tenants.find(t => t.tenant_id === selectedTenant)?.tenant_name || `Tenant #${selectedTenant}`}
                />
              ) : (
                <div className="text-center py-8 bg-gray-50 rounded-lg">
                  <Activity className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600 mb-2">Select a tenant to run AI-powered analysis</p>
                  <p className="text-sm text-gray-500">
                    Go to the Tenants tab and select a tenant to view AI analysis
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'rag-analysis' && (
          <RAGAnalysis />
        )}

        {activeTab === 'reports' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">CS AI Agent Execution Reports</h2>
              <p className="text-gray-600 mb-6">Reports for Data Center AI agent executions</p>
              
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center">
                <FileText className="h-12 w-12 text-blue-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No AI Agent Executions Yet</h3>
                <p className="text-gray-600 mb-4">
                  Data Center uses a recommendations-only model for CS AI Agents.
                </p>
                <p className="text-sm text-gray-500">
                  View recommended AI agents in the "CS AI Agents" tab. Since DC uses pillar-based recommendations
                  rather than executable playbooks, execution reports are not applicable.
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'kpis' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">KPI Overview</h2>
              <div className="mb-4">
                <p className="text-sm text-gray-600">
                  Total KPIs: <span className="font-semibold">{kpiData.length}</span>
                </p>
                <p className="text-sm text-gray-600">
                  Tenants with KPIs: <span className="font-semibold">{new Set(kpiData.map(k => k.account_id)).size}</span>
                </p>
              </div>
              
              {selectedTenant ? (
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    KPIs for {tenants.find(t => t.tenant_id === selectedTenant)?.tenant_name}
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <KPICard_dc tenantId={selectedTenant} />
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Target className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600">Select a tenant to view KPIs</p>
                </div>
              )}

              {/* Collapsible KPI Categories */}
              {kpiData.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">All KPIs by Category</h3>
                  <div className="space-y-4">
                    {Array.from(new Set(kpiData.map(kpi => kpi.category))).map((categoryName, index) => {
                      const categoryKPIs = kpiData.filter(kpi => kpi.category === categoryName);
                      const categoryData = categoryKPIs.filter(k => k.data && k.data !== '0' && k.data !== '');
                      const colors = ['bg-emerald-500', 'bg-blue-500', 'bg-purple-500', 'bg-orange-500', 'bg-red-500'];
                      const categoryColor = colors[index % colors.length];
                      const isExpanded = expandedCategories[categoryName];
                      
                      // Pagination for this category
                      const currentPage = categoryPages[categoryName] || 1;
                      const startIndex = (currentPage - 1) * itemsPerPage;
                      const endIndex = startIndex + itemsPerPage;
                      const paginatedKPIs = categoryKPIs.slice(startIndex, endIndex);
                      const totalPages = Math.ceil(categoryKPIs.length / itemsPerPage);
                      
                      const setPage = (page: number) => {
                        setCategoryPages(prev => ({
                          ...prev,
                          [categoryName]: page
                        }));
                      };
                      
                      return (
                        <div key={index} className="bg-white rounded-xl shadow-sm border border-gray-100">
                          {/* Category Header */}
                          <div 
                            className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                            onClick={() => toggleCategory(categoryName)}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-3">
                                {isExpanded ? (
                                  <ChevronDown className="h-5 w-5 text-gray-500" />
                                ) : (
                                  <ChevronRight className="h-5 w-5 text-gray-500" />
                                )}
                                <h3 className="font-semibold text-gray-900">{categoryName}</h3>
                              </div>
                              <div className="flex items-center space-x-3">
                                <div className="text-sm text-gray-500">
                                  {categoryData.length}/{categoryKPIs.length} KPIs with data
                                </div>
                                <div className={`px-3 py-1 rounded-full text-xs font-medium text-white ${categoryColor}`}>
                                  {categoryKPIs.length} KPIs
                                </div>
                              </div>
                            </div>
                            
                            {/* Progress Bar */}
                            <div className="mt-3">
                              <div className="w-full bg-gray-200 rounded-full h-2">
                                <div 
                                  className={`h-2 rounded-full ${categoryColor}`}
                                  style={{ width: `${Math.round((categoryData.length / Math.max(categoryKPIs.length, 1)) * 100)}%` }}
                                ></div>
                              </div>
                              <div className="text-xs text-gray-500 mt-1">
                                Coverage: {Math.round((categoryData.length / Math.max(categoryKPIs.length, 1)) * 100)}%
                              </div>
                            </div>
                          </div>
                          
                          {/* Collapsible Content - Table View */}
                          {isExpanded && (
                            <div className="border-t border-gray-100 p-4">
                              <div className="overflow-x-auto">
                                <table className="min-w-full divide-y divide-gray-200">
                                  <thead className="bg-gray-50">
                                    <tr>
                                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account</th>
                                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">KPI Parameter</th>
                                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Value</th>
                                    </tr>
                                  </thead>
                                  <tbody className="bg-white divide-y divide-gray-200">
                                    {paginatedKPIs.map((kpi) => (
                                      <tr key={kpi.kpi_id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                          {kpi.account_name || `Account ${kpi.account_id}`}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{kpi.kpi_parameter}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{kpi.data}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                              
                              {/* Pagination */}
                              {categoryKPIs.length > itemsPerPage && (
                                <div className="mt-4 flex items-center justify-between">
                                  <div className="text-sm text-gray-600">
                                    Showing {startIndex + 1} to {Math.min(endIndex, categoryKPIs.length)} of {categoryKPIs.length} KPIs
                                  </div>
                                  <div className="flex items-center space-x-2">
                                    <button
                                      onClick={() => setPage(Math.max(1, currentPage - 1))}
                                      disabled={currentPage === 1}
                                      className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                      Previous
                                    </button>
                                    <span className="text-sm text-gray-700">
                                      Page {currentPage} of {totalPages}
                                    </span>
                                    <button
                                      onClick={() => setPage(Math.min(totalPages, currentPage + 1))}
                                      disabled={currentPage === totalPages}
                                      className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                      Next
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'upload' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Data Integration</h2>
            <p className="text-gray-600">Upload KPI data for Data Center tenants</p>
            <div className="mt-4 p-4 border-2 border-dashed border-gray-300 rounded-lg text-center">
              <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-600">File upload functionality coming soon</p>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Settings & Configuration</h2>
              <p className="text-gray-600 mb-6">Data Center configuration settings</p>
              
              {/* OpenAI API Key Settings */}
              <details className="bg-white rounded-xl shadow-sm border border-gray-100 mb-4" open>
                <summary className="cursor-pointer px-4 py-3 font-semibold text-gray-900 flex items-center">
                  <Settings className="h-5 w-5 mr-2 text-blue-600" />
                  OpenAI API Key
                </summary>
                <div className="p-4 border-t border-gray-100">
                  <OpenAIKeySettings isAuthenticated={Boolean(session)} />
                </div>
              </details>

              {/* DC-Specific Settings */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Data Center Settings</h3>
                <div className="space-y-4">
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-900 mb-2">
                      <strong>Data Center Vertical Configuration</strong>
                    </p>
                    <p className="text-sm text-blue-700">
                      Data Center settings are automatically configured based on your tenant's vertical type (dc2_s).
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'alerts' && (
          <AlertBanner_dc tenantId={selectedTenant} />
        )}
        </main>
      </div>
    </div>
  );
};

export default Dashboard_dc;

