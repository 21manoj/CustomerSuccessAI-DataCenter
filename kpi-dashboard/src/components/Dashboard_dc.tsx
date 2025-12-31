/**
 * Data Center Dashboard Component
 * Main dashboard for Data Center vertical
 */

import React, { useState, useEffect } from 'react';
import { useSession } from '../contexts/SessionContext';
import { Server, Activity, AlertTriangle, TrendingUp, Users, Zap, BarChart3, Upload, Target, MessageSquare, Settings, FileText, LogOut, ChevronDown, ChevronRight, TrendingDown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import KPICard_dc from './KPICard_dc';
import HealthScore_dc from './HealthScore_dc';
import TenantList_dc from './TenantList_dc';
import AlertBanner_dc from './AlertBanner_dc';
import KPIChart_dc from './KPIChart_dc';
import PlaybookPanel_dc from './PlaybookPanel_dc';

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
    account_id: number;
    account_name: string;
    overall_health_score: number;
    category_scores: Record<string, number>;
    focus_areas: Array<{category: string; score: number}>;
    active_playbooks_count: number;
    revenue_growth_pct: number;
  }>;
  healthy_declining_revenue: Array<{
    account_id: number;
    account_name: string;
    overall_health_score: number;
    category_scores: Record<string, number>;
    focus_areas: Array<{category: string; score: number}>;
    active_playbooks_count: number;
    revenue_growth_pct: number;
  }>;
}

interface Tenant {
  tenant_id: number;
  tenant_name: string;
  health_score: number;
  status: 'healthy' | 'at_risk' | 'critical';
}

interface KPI {
  kpi_id: number;
  category: string;
  kpi_parameter: string;
  data: string;
  account_id: number;
  account_name?: string;
  upload_id?: number;
  upload_filename?: string;
}

const Dashboard_dc: React.FC = () => {
  const { session, logout } = useSession();
  const navigate = useNavigate();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [kpiData, setKpiData] = useState<KPI[]>([]);
  const [selectedTenant, setSelectedTenant] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'tenants' | 'kpis' | 'alerts' | 'upload' | 'settings' | 'insights'>('dashboard');
  const [expandedCategories, setExpandedCategories] = useState<{[key: string]: boolean}>({});
  const [categoryPages, setCategoryPages] = useState<{[key: string]: number}>({});
  const itemsPerPage = 50;
  const [selectedMonth, setSelectedMonth] = useState<number>(7); // Default to latest month (7)
  const [tenantKPIs, setTenantKPIs] = useState<KPI[]>([]);
  const [loadingTenantKPIs, setLoadingTenantKPIs] = useState(false);
  const [perfSummary, setPerfSummary] = useState<PerformanceSummary | null>(null);

  useEffect(() => {
    if (session?.customer_id) {
      loadDashboardData();
      fetchPerformanceSummary();
    }
  }, [session]);

  const fetchPerformanceSummary = async () => {
    if (!session?.customer_id) return;
    
    try {
      const response = await fetch('/api/customer-performance/summary', {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-Customer-ID': session.customer_id.toString(),
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
      
      // Load tenants (accounts)
      const accountsResponse = await fetch('/api/accounts', {
        credentials: 'include',
        headers: {
          'X-Customer-ID': session?.customer_id?.toString() || '',
        },
      });

      if (accountsResponse.ok) {
        const accountsData = await accountsResponse.json();
        const accountsArray = Array.isArray(accountsData) ? accountsData : (accountsData.accounts || []);
        
        // Transform to tenants format
        const tenantsData: Tenant[] = accountsArray.map((acc: any) => ({
          tenant_id: acc.account_id,
          tenant_name: acc.account_name,
          health_score: acc.health_score || 0,
          status: acc.health_score >= 70 ? 'healthy' : acc.health_score >= 50 ? 'at_risk' : 'critical'
        }));
        
        setTenants(tenantsData);
      }

      // Load KPIs
      const kpisResponse = await fetch('/api/kpis/customer/all', {
        credentials: 'include',
        headers: {
          'X-Customer-ID': session?.customer_id?.toString() || '',
        },
      });

      if (kpisResponse.ok) {
        const kpisData = await kpisResponse.json();
        const transformedKPIs: KPI[] = kpisData.map((kpi: any) => ({
          kpi_id: kpi.kpi_id,
          category: kpi.category || 'Uncategorized',
          kpi_parameter: kpi.kpi_parameter,
          data: kpi.data || '0',
          account_id: kpi.account_id,
          account_name: kpi.account_name,
          upload_id: kpi.upload_id,
          upload_filename: kpi.upload_filename || kpi.original_filename,
        }));
        setKpiData(transformedKPIs);
        console.log('Loaded KPIs:', transformedKPIs.length);
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error);
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

  // Extract month number from upload filename (e.g., "Month_1.csv" -> 1)
  const getMonthFromFilename = (filename: string | undefined): number | null => {
    if (!filename) return null;
    const match = filename.match(/Month[_\s](\d+)/i);
    return match ? parseInt(match[1]) : null;
  };

  // Fetch KPIs for selected tenant
  useEffect(() => {
    if (selectedTenant && session?.customer_id) {
      fetchTenantKPIs();
    } else {
      setTenantKPIs([]);
    }
  }, [selectedTenant, session?.customer_id]);

  const fetchTenantKPIs = async () => {
    if (!selectedTenant || !session?.customer_id) return;
    
    try {
      setLoadingTenantKPIs(true);
      const response = await fetch('/api/kpis/customer/all', {
        credentials: 'include',
        headers: {
          'X-Customer-ID': session.customer_id.toString(),
        },
      });

      if (response.ok) {
        const kpisData = await response.json();
        console.log('Fetched KPIs for tenant:', selectedTenant, 'Total:', kpisData.length);
        const tenantKPIsData: KPI[] = kpisData
          .filter((kpi: any) => kpi.account_id === selectedTenant)
          .map((kpi: any) => {
            const uploadFilename = kpi.upload_filename || kpi.original_filename;
            const month = getMonthFromFilename(uploadFilename);
            console.log('KPI:', kpi.kpi_parameter, 'Filename:', uploadFilename, 'Month:', month);
            return {
              kpi_id: kpi.kpi_id,
              category: kpi.category || 'Uncategorized',
              kpi_parameter: kpi.kpi_parameter,
              data: kpi.data || '0',
              account_id: kpi.account_id,
              account_name: kpi.account_name,
              upload_id: kpi.upload_id,
              upload_filename: uploadFilename,
            };
          });
        console.log('Filtered tenant KPIs:', tenantKPIsData.length);
        setTenantKPIs(tenantKPIsData);
      }
    } catch (error) {
      console.error('Error loading tenant KPIs:', error);
    } finally {
      setLoadingTenantKPIs(false);
    }
  };

  // Filter tenant KPIs by selected month
  const filteredTenantKPIs = tenantKPIs.filter(kpi => {
    const kpiMonth = getMonthFromFilename(kpi.upload_filename);
    const matches = kpiMonth === selectedMonth;
    if (!matches && kpiMonth !== null) {
      console.log(`KPI ${kpi.kpi_parameter}: Month ${kpiMonth} !== Selected ${selectedMonth}`);
    }
    return matches;
  });
  
  console.log('Selected month:', selectedMonth, 'Total tenant KPIs:', tenantKPIs.length, 'Filtered:', filteredTenantKPIs.length);

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
        <nav className="w-64 bg-gradient-to-b from-slate-50 to-slate-100 border-r border-slate-200 shadow-sm px-4 py-6">
          <div className="space-y-2">
            {[
              { id: 'dashboard', label: 'Data Center Dashboard', icon: BarChart3 },
              { id: 'tenants', label: 'Tenants', icon: Users },
              { id: 'kpis', label: 'KPIs', icon: Target },
              { id: 'insights', label: 'CS AI Agents', icon: Zap },
              { id: 'alerts', label: 'Alerts', icon: AlertTriangle },
              { id: 'upload', label: 'Data Integration', icon: Upload },
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
                                  <span className={`font-semibold ${area.score < 70 ? 'text-red-600' : 'text-yellow-600'}`}>{area.score.toFixed(0)}</span>
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
            {/* Month Slider */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Select Month</h3>
                <span className="text-sm font-medium text-blue-600">Month {selectedMonth} of 7</span>
              </div>
              <input
                type="range"
                min="1"
                max="7"
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-2">
                <span>Month 1</span>
                <span>Month 2</span>
                <span>Month 3</span>
                <span>Month 4</span>
                <span>Month 5</span>
                <span>Month 6</span>
                <span>Month 7</span>
              </div>
            </div>

            {/* Tenant List */}
            <TenantList_dc
              tenants={tenants}
              onSelectTenant={setSelectedTenant}
              selectedTenant={selectedTenant}
            />

            {/* Tenant KPIs Display */}
            {selectedTenant && (
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    KPIs for {tenants.find(t => t.tenant_id === selectedTenant)?.tenant_name} - Month {selectedMonth}
                  </h3>
                  {loadingTenantKPIs && (
                    <Activity className="h-5 w-5 animate-spin text-blue-600" />
                  )}
                </div>

                {loadingTenantKPIs ? (
                  <div className="text-center py-8">
                    <Activity className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
                    <p className="text-gray-600">Loading KPIs...</p>
                  </div>
                ) : filteredTenantKPIs.length === 0 ? (
                  <div className="text-center py-8">
                    <Target className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600 mb-2">No KPIs found for Month {selectedMonth}</p>
                    <p className="text-xs text-gray-500">
                      Total tenant KPIs: {tenantKPIs.length} | 
                      Available months: {Array.from(new Set(tenantKPIs.map(k => getMonthFromFilename(k.upload_filename)).filter(m => m !== null))).sort().join(', ')}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {Array.from(new Set(filteredTenantKPIs.map(kpi => kpi.category))).map((categoryName, index) => {
                      const categoryKPIs = filteredTenantKPIs.filter(kpi => kpi.category === categoryName);
                      const categoryData = categoryKPIs.filter(k => k.data && k.data !== '0' && k.data !== '');
                      const colors = ['bg-emerald-500', 'bg-blue-500', 'bg-purple-500', 'bg-orange-500', 'bg-red-500'];
                      const categoryColor = colors[index % colors.length];
                      const categoryKey = `tenant-${selectedTenant}-${categoryName}`;
                      const isExpanded = expandedCategories[categoryKey];
                      
                      return (
                        <div key={index} className="bg-white rounded-xl shadow-sm border border-gray-100">
                          {/* Category Header */}
                          <div 
                            className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                            onClick={() => toggleCategory(categoryKey)}
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
                                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">KPI Parameter</th>
                                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Value</th>
                                    </tr>
                                  </thead>
                                  <tbody className="bg-white divide-y divide-gray-200">
                                    {categoryKPIs.map((kpi) => (
                                      <tr key={kpi.kpi_id} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{kpi.kpi_parameter}</td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{kpi.data}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
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
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Settings</h2>
            <p className="text-gray-600">Data Center configuration settings</p>
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

