import React, { useState, useRef, useEffect, useMemo } from 'react';
import { 
  Upload, 
  Database, 
  TrendingUp, 
  Users, 
  MessageSquare, 
  BarChart3, 
  Target, 
  AlertTriangle, 
  CheckCircle, 
  Activity,
  FileText,
  Search,
  Filter,
  Download,
  RefreshCw,
  Zap,
  ArrowUp,
  ArrowDown,
  Minus,
  Eye,
  Calculator,
  LogOut,
  Settings,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import { useSession } from '../contexts/SessionContext';
import RAGAnalysis from './RAGAnalysis';
import SettingsModal from './Settings';
import Playbooks from './Playbooks';
import PlaybookReports from './PlaybookReports';

interface KPI {
  kpi_id: number;
  category: string;
  kpi_parameter: string;
  data: string;
  weight: string | null;
  impact_level: string;
  measurement_frequency: string;
  source_review: string;
  account_id?: number;
  account_name?: string;
}

interface Account {
  account_id: number;
  account_name: string;
  revenue: number;
  industry: string;
  region: string;
  account_status: string;
  health_score: number;
}

interface RollupResult {
  overall_score: number;
  maturity_tier: string;
  category_scores: {
    [key: string]: {
      score: number;
      weight: number;
      kpi_count: number;
      valid_kpi_count: number;
    };
  };
  recommendations: string[];
  health_scores: {
    overall: number;
    enhanced_analysis: {
      category_scores: Array<{
        category: string;
        average_score: number;
        health_status: string;
        color: string;
        kpi_count: number;
        valid_kpi_count: number;
        category_weight: number;
      }>;
      overall_score: {
        overall_score: number;
        health_status: string;
        color: string;
      };
    };
  };
}

const CSPlatform = () => {
  const { session, logout } = useSession();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  const [isUploading, setIsUploading] = useState(false);
  const [showKPITable, setShowKPITable] = useState(false);
  const [rollupResults, setRollupResults] = useState<RollupResult | null>(null);
  const [isCalculatingRollup, setIsCalculatingRollup] = useState(false);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [kpiData, setKpiData] = useState<KPI[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [uploadAccountName, setUploadAccountName] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Cleanup state variables
  const [cleanupDirectory, setCleanupDirectory] = useState('');
  const [isCleanupRunning, setIsCleanupRunning] = useState(false);
  const [cleanupResult, setCleanupResult] = useState<any>(null);
  const [cleanupError, setCleanupError] = useState('');
  
  // Master file upload state variables
  const [categoryWeights, setCategoryWeights] = useState<{[key: string]: number}>({});
  const [masterFileError, setMasterFileError] = useState('');
  const [masterFileSuccess, setMasterFileSuccess] = useState<any>(null);
  const masterFileInputRef = useRef<HTMLInputElement>(null);
  
  // Collapsible categories state
  const [expandedCategories, setExpandedCategories] = useState<{[key: string]: boolean}>({});
  
  // Health trend data state
  const [healthTrendData, setHealthTrendData] = useState<Array<{month: string, score: number}>>([]);
  const [kpiTrendData, setKpiTrendData] = useState<Array<{month: string, value: number, health_status: string, health_score: number}>>([]);
  const [accountHealthTrends, setAccountHealthTrends] = useState<Array<{
    month: string;
    overall_score: number;
    product_usage_score: number;
    support_score: number;
    customer_sentiment_score: number;
    business_outcomes_score: number;
    relationship_strength_score: number;
  }>>([]);
  const [selectedAccountForTrends, setSelectedAccountForTrends] = useState<number | null>(null);
  const [selectedKpiForTrends, setSelectedKpiForTrends] = useState<string | null>(null);
  const [timeSeriesStats, setTimeSeriesStats] = useState<{
    total_data_points: number;
    date_range: { oldest: string; newest: string };
    health_trend_records: number;
    kpi_time_series_records: number;
  } | null>(null);
  const [kpiHealthStatuses, setKpiHealthStatuses] = useState<{[key: number]: {health_status: string, health_color: string, health_score: number}}>({});
  
  // Rollup level tabs state
  const [activeRollupTab, setActiveRollupTab] = useState<'overview' | 'level1' | 'level2' | 'level3' | 'trends'>('overview');
  const [kpiReferenceRanges, setKpiReferenceRanges] = useState<Array<{
    range_id: number;
    kpi_name: string;
    unit: string;
    higher_is_better: boolean;
    critical_range: string;
    risk_range: string;
    healthy_range: string;
    critical_min: number;
    critical_max: number;
    risk_min: number;
    risk_max: number;
    healthy_min: number;
    healthy_max: number;
  }>>([]);

  const [kpiCategories, setKpiCategories] = useState([
    { name: 'Product Usage KPI', count: 0, color: 'bg-emerald-500', weight: 20 },
    { name: 'Support KPI', count: 0, color: 'bg-blue-500', weight: 20 },
    { name: 'Customer Sentiment KPI', count: 0, color: 'bg-yellow-500', weight: 20 },
    { name: 'Business Outcomes KPI', count: 0, color: 'bg-purple-500', weight: 25 },
    { name: 'Relationship Strength KPI', count: 0, color: 'bg-orange-500', weight: 15 }
  ]);

  // Fetch accounts from backend
  const fetchAccounts = async () => {
    if (!session?.customer_id) return;
    
    try {
      const response = await fetch('/api/accounts', {
        headers: {
          'X-Customer-ID': session.customer_id.toString(),
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Accounts API response:', data); // Debug log
        // Transform backend data to match our interface
        const transformedAccounts: Account[] = data.map((acc: any) => ({
          account_id: acc.account_id,
          account_name: acc.account_name,
          revenue: acc.revenue || 0,
          industry: acc.industry || 'Unknown',
          region: acc.region || 'Unknown',
          account_status: acc.account_status || 'active',
          health_score: acc.health_score || Math.floor(Math.random() * 60) + 40, // Fallback score
        }));
        console.log('Transformed accounts:', transformedAccounts); // Debug log
        setAccounts(transformedAccounts);
      } else {
        setError('Failed to fetch accounts');
      }
    } catch (err) {
      setError('Error fetching accounts');
      console.error('Error fetching accounts:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch KPIs from backend
  const fetchKPIs = async () => {
    if (!session?.customer_id) return;
    
          try {
        const response = await fetch('/api/kpis/customer/all', {
          headers: {
            'X-Customer-ID': session.customer_id.toString(),
          },
        });
      
      if (response.ok) {
        const data = await response.json();
        console.log('KPIs API response:', data.length, 'KPIs'); // Debug log
        // Transform backend KPI data to match our interface
        const transformedKPIs: KPI[] = data.map((kpi: any) => ({
          kpi_id: kpi.kpi_id,
          category: kpi.category || 'Uncategorized',
          kpi_parameter: kpi.kpi_parameter,
          data: kpi.data || '0',
          weight: kpi.weight,
          impact_level: kpi.impact_level || 'Medium',
          measurement_frequency: kpi.measurement_frequency || 'Monthly',
          source_review: kpi.source_review || 'System',
          account_id: kpi.account_id,
          account_name: kpi.account_name,
        }));
        console.log('Transformed KPIs:', transformedKPIs.length, 'KPIs'); // Debug log
        setKpiData(transformedKPIs);
      } else {
        setError('Failed to fetch KPIs');
      }
    } catch (err) {
      setError('Error fetching KPIs');
      console.error('Error fetching KPIs:', err);
    }
  };

  useEffect(() => {
    console.log('Session changed:', session); // Debug log
    if (session?.customer_id) {
      console.log('Fetching accounts for customer:', session.customer_id); // Debug log
      fetchAccounts();
      fetchCategoryWeights();
      fetchHealthTrendData();
      fetchKpiHealthStatuses();
      fetchKpiReferenceRanges();
      fetchTimeSeriesStats();
    } else {
      console.log('No customer_id in session'); // Debug log
    }
  }, [session?.customer_id]);

  useEffect(() => {
    if (session?.customer_id) {
      console.log('Fetching KPIs for customer:', session.customer_id); // Debug log
      fetchKPIs();
    }
  }, [session?.customer_id]);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      setError('Please select a file to upload');
      return;
    }
    if (!session?.customer_id || !session?.user_id) {
      setError('Please log in first to upload files');
      return;
    }
    if (!uploadAccountName.trim()) {
      setError('Please enter an account name');
      return;
    }

    setIsUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('account_name', uploadAccountName.trim());
      
      const response = await fetch('/api/upload', {
        method: 'POST',
        headers: {
          'X-Customer-ID': session.customer_id.toString(),
          'X-User-ID': session.user_id.toString(),
        },
        body: formData,
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('Upload successful:', result);
        
        // Show success message
        setError(`Upload successful! Processed ${result.kpi_count} KPIs from ${result.filename}`);
        
        // Refresh data after successful upload (without page reload)
        setTimeout(() => {
          fetchAccounts();
          fetchKPIs();
          setError(''); // Clear success message
        }, 3000);
      } else {
        const errorData = await response.json();
        setError(`Upload failed: ${errorData.error || 'Unknown error'}`);
      }
    } catch (err) {
      setError('Upload error: ' + (err instanceof Error ? err.message : 'Unknown error'));
      console.error('Upload error:', err);
    } finally {
      setIsUploading(false);
    }
  };

  const handleBulkCleanup = async () => {
    if (!cleanupDirectory.trim() || !session?.customer_id) return;
    
    setIsCleanupRunning(true);
    setCleanupError('');
    setCleanupResult(null);
    
    try {
      const response = await fetch('/api/cleanup/bulk-upload', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Customer-ID': session.customer_id.toString(),
          'X-User-ID': session.user_id.toString()
        },
        body: JSON.stringify({ directory_path: cleanupDirectory.trim() })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Cleanup failed: ${response.statusText}`);
      }
      
      const data = await response.json();
      setCleanupResult(data);
      
      // Refresh data after cleanup
      await fetchAccounts();
      await fetchKPIs();
      
    } catch (err) {
      setCleanupError(err instanceof Error ? err.message : 'Failed to perform bulk cleanup');
    } finally {
      setIsCleanupRunning(false);
    }
  };

  const handleMasterFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !session?.customer_id) return;
    
    setMasterFileError('');
    setMasterFileSuccess(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('/api/master-file/upload', {
        method: 'POST',
        headers: {
          'X-Customer-ID': session.customer_id.toString(),
          'X-User-ID': session.user_id.toString(),
        },
        body: formData,
      });
      
      if (response.ok) {
        const result = await response.json();
        setMasterFileSuccess(result);
        setCategoryWeights(result.category_weights);
      } else {
        const errorData = await response.json();
        setMasterFileError(`Upload failed: ${errorData.error || 'Unknown error'}`);
      }
    } catch (err) {
      setMasterFileError('Upload error: ' + (err instanceof Error ? err.message : 'Unknown error'));
    }
  };

  const fetchKpiHealthStatuses = async () => {
    if (!session?.customer_id) return;
    
    try {
      const response = await fetch('/api/health-status/kpis', {
        headers: {
          'X-Customer-ID': session.customer_id.toString(),
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        const statusMap: {[key: number]: {health_status: string, health_color: string, health_score: number}} = {};
        data.health_statuses.forEach((status: any) => {
          statusMap[status.kpi_id] = {
            health_status: status.health_status,
            health_color: status.health_color,
            health_score: status.health_score
          };
        });
        setKpiHealthStatuses(statusMap);
        console.log('Health statuses loaded:', Object.keys(statusMap).length, 'KPIs');
        console.log('Sample health statuses:', Object.keys(statusMap).slice(0, 5).map(id => ({id, status: statusMap[parseInt(id)]})));
      }
    } catch (err) {
      console.error('Error fetching KPI health statuses:', err);
    }
  };

  const fetchKpiReferenceRanges = async () => {
    try {
      const response = await fetch('/api/reference-ranges', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setKpiReferenceRanges(data.reference_ranges);
          console.log('KPI reference ranges loaded from database:', data.reference_ranges.length, 'KPIs');
        } else {
          console.error('Failed to load reference ranges:', data.error);
          setError('Failed to load KPI reference ranges');
        }
      } else {
        console.error('Failed to fetch reference ranges:', response.status);
        setError('Failed to fetch KPI reference ranges');
      }
    } catch (error) {
      console.error('Error fetching KPI reference ranges:', error);
      setError('Error fetching KPI reference ranges');
    }
  };

  const saveKpiReferenceRanges = async () => {
    try {
      const response = await fetch('/api/reference-ranges/bulk-update', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ranges: kpiReferenceRanges.map(range => ({
            range_id: range.range_id,
            critical_min: range.critical_min,
            critical_max: range.critical_max,
            risk_min: range.risk_min,
            risk_max: range.risk_max,
            healthy_min: range.healthy_min,
            healthy_max: range.healthy_max,
            higher_is_better: range.higher_is_better
          }))
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          console.log('KPI reference ranges saved successfully:', data.updated_count, 'ranges updated');
          console.log(`Successfully saved ${data.updated_count} KPI reference ranges`);
          // Refresh the data
          fetchKpiReferenceRanges();
        } else {
          console.error('Failed to save reference ranges:', data.error);
          setError('Failed to save KPI reference ranges');
        }
      } else {
        console.error('Failed to save reference ranges:', response.status);
        setError('Failed to save KPI reference ranges');
      }
    } catch (error) {
      console.error('Error saving KPI reference ranges:', error);
      setError('Error saving KPI reference ranges');
    }
  };

  const updateReferenceRange = (rangeId: number, field: string, value: number | boolean) => {
    setKpiReferenceRanges(prev => 
      prev.map(range => 
        range.range_id === rangeId 
          ? { ...range, [field]: value }
          : range
      )
    );
  };

  // Fallback hardcoded ranges (keep as backup)
  const getFallbackReferenceRanges = () => {
    // For now, return empty array since we're using the API
    // This can be used as a fallback if the API fails
    return [];
  };

  const fetchCategoryWeights = async () => {
    if (!session?.customer_id) return;
    
    try {
      const response = await fetch('/api/master-file/weights', {
        headers: {
          'X-Customer-ID': session.customer_id.toString(),
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setCategoryWeights(data.category_weights);
      }
    } catch (err) {
      console.error('Error fetching category weights:', err);
    }
  };

  const toggleCategory = (categoryName: string) => {
    setExpandedCategories(prev => ({
      ...prev,
      [categoryName]: !prev[categoryName]
    }));
  };

  const fetchHealthTrendData = async (accountId?: number) => {
    if (!session?.customer_id) return;
    
    try {
      const url = accountId 
        ? `/api/health-trends?account_id=${accountId}`
        : '/api/health-trends';
        
      const response = await fetch(url, {
        headers: {
          'X-Customer-ID': session.customer_id.toString(),
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setHealthTrendData(data.trends || []);
      } else {
        // Fallback to sample data if API fails
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const currentMonth = new Date().getMonth();
        const sampleData = months.slice(0, currentMonth + 1).map((month, index) => ({
          month,
          score: Math.round(50 + Math.random() * 30 + (index * 2))
        }));
        setHealthTrendData(sampleData);
      }
    } catch (err) {
      console.error('Error fetching health trend data:', err);
      // Fallback to sample data
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const currentMonth = new Date().getMonth();
      const sampleData = months.slice(0, currentMonth + 1).map((month, index) => ({
        month,
        score: Math.round(50 + Math.random() * 30 + (index * 2))
      }));
      setHealthTrendData(sampleData);
    }
  };

  // Fetch time series statistics
  const fetchTimeSeriesStats = async () => {
    if (!session?.customer_id) return;
    
    try {
      const response = await fetch('/api/time-series/stats', {
        headers: {
          'X-Customer-ID': session.customer_id.toString(),
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setTimeSeriesStats(data);
      }
    } catch (err) {
      console.error('Error fetching time series stats:', err);
    }
  };

  // Fetch KPI trends for a specific KPI and account
  const fetchKpiTrends = async (kpiName: string, accountId: number) => {
    if (!session?.customer_id) return;
    
    try {
      const response = await fetch(
        `/api/time-series/kpi-trends?kpi_name=${encodeURIComponent(kpiName)}&account_id=${accountId}&months=7`,
        {
          headers: {
            'X-Customer-ID': session.customer_id.toString(),
          },
        }
      );
      
      if (response.ok) {
        const data = await response.json();
        setKpiTrendData(data.trends || []);
      }
    } catch (err) {
      console.error('Error fetching KPI trends:', err);
    }
  };

  // Fetch account health trends
  const fetchAccountHealthTrends = async (accountId: number) => {
    if (!session?.customer_id) return;
    
    try {
      const response = await fetch(
        `/api/time-series/account-health?account_id=${accountId}&months=7`,
        {
          headers: {
            'X-Customer-ID': session.customer_id.toString(),
          },
        }
      );
      
      if (response.ok) {
        const data = await response.json();
        setAccountHealthTrends(data.health_trends || []);
      }
    } catch (err) {
      console.error('Error fetching account health trends:', err);
    }
  };

  // Simple trend chart component
  const TrendChart = ({ data, title }: { data: Array<{month: string, score: number}>, title: string }) => {
    if (!data || data.length === 0) {
      return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">{title}</h3>
          <div className="h-64 flex items-center justify-center text-gray-500">
            No trend data available
          </div>
        </div>
      );
    }

    const maxScore = Math.max(...data.map(d => d.score));
    const minScore = Math.min(...data.map(d => d.score));
    const range = maxScore - minScore || 1;

    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="h-64 relative">
          {/* Y-axis labels */}
          <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-500 pr-2">
            <span>{Math.round(maxScore)}</span>
            <span>{Math.round((maxScore + minScore) / 2)}</span>
            <span>{Math.round(minScore)}</span>
          </div>
          
          {/* Chart area */}
          <div className="ml-8 h-full relative">
            {/* Grid lines */}
            <div className="absolute inset-0">
              {[0, 0.5, 1].map((ratio) => (
                <div 
                  key={ratio}
                  className="absolute w-full border-t border-gray-100"
                  style={{ top: `${ratio * 100}%` }}
                />
              ))}
            </div>
            
            {/* Trend line */}
            <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              <polyline
                fill="none"
                stroke="#3B82F6"
                strokeWidth="1"
                points={data.map((point, index) => {
                  const x = (index / Math.max(1, data.length - 1)) * 100;
                  const y = 100 - ((point.score - minScore) / range) * 100;
                  return `${x},${y}`;
                }).join(' ')}
              />
              {data.map((point, index) => {
                const x = (index / Math.max(1, data.length - 1)) * 100;
                const y = 100 - ((point.score - minScore) / range) * 100;
                return (
                  <circle
                    key={index}
                    cx={x}
                    cy={y}
                    r="1.5"
                    fill="#3B82F6"
                    className="hover:r-3 transition-all"
                  />
                );
              })}
            </svg>
          </div>
          
          {/* X-axis labels */}
          <div className="absolute bottom-0 left-8 right-0 flex justify-between text-xs text-gray-500">
            {data.map((point, index) => {
              const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
              const monthNumber = parseInt(point.month.split('-')[1]);
              const monthName = monthNames[monthNumber - 1] || point.month;
              return (
                <span key={index} className="text-center" style={{ width: `${100/data.length}%` }}>
                  {monthName}
                </span>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  // Enhanced KPI trend chart component
  const KpiTrendChart = ({ data, title, kpiName }: { 
    data: Array<{month: string, value: number, health_status: string, health_score: number}>, 
    title: string, 
    kpiName: string 
  }) => {
    if (!data || data.length === 0) {
      return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">{title}</h3>
          <div className="h-64 flex items-center justify-center text-gray-500">
            No trend data available
          </div>
        </div>
      );
    }

    const maxValue = Math.max(...data.map(d => d.value));
    const minValue = Math.min(...data.map(d => d.value));
    const valueRange = maxValue - minValue || 1;

    const getHealthColor = (status: string) => {
      switch (status.toLowerCase()) {
        case 'high': return '#10B981'; // green
        case 'medium': return '#F59E0B'; // yellow
        case 'low': return '#EF4444'; // red
        default: return '#6B7280'; // gray
      }
    };

    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="h-64 relative">
          {/* Y-axis labels */}
          <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-500 pr-2">
            <span>{maxValue.toFixed(1)}</span>
            <span>{((maxValue + minValue) / 2).toFixed(1)}</span>
            <span>{minValue.toFixed(1)}</span>
          </div>
          
          {/* Chart area */}
          <div className="ml-8 h-full relative">
            {/* Grid lines */}
            <div className="absolute inset-0">
              {[0, 0.5, 1].map((ratio) => (
                <div 
                  key={ratio}
                  className="absolute w-full border-t border-gray-100"
                  style={{ top: `${ratio * 100}%` }}
                />
              ))}
            </div>
            
            {/* Trend line */}
            <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              <polyline
                fill="none"
                stroke="#3B82F6"
                strokeWidth="1"
                points={data.map((point, index) => {
                  const x = (index / Math.max(1, data.length - 1)) * 100;
                  const y = 100 - ((point.value - minValue) / valueRange) * 100;
                  return `${x},${y}`;
                }).join(' ')}
              />
              {data.map((point, index) => {
                const x = (index / Math.max(1, data.length - 1)) * 100;
                const y = 100 - ((point.value - minValue) / valueRange) * 100;
                return (
                  <circle
                    key={index}
                    cx={x}
                    cy={y}
                    r="1.5"
                    fill={getHealthColor(point.health_status)}
                    className="hover:r-3 transition-all cursor-pointer"
                  />
                );
              })}
            </svg>
          </div>
          
          {/* X-axis labels */}
          <div className="absolute bottom-0 left-8 right-0 flex justify-between text-xs text-gray-500">
            {data.map((point, index) => {
              const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
              const monthNumber = parseInt(point.month.split('-')[1]);
              const monthName = monthNames[monthNumber - 1] || `M${monthNumber}`;
              return (
                <span key={index} className="text-center" style={{ width: `${100/data.length}%` }}>
                  {monthName}
                </span>
              );
            })}
          </div>
        </div>
        
        {/* Legend */}
        <div className="mt-4 flex items-center justify-center space-x-4 text-xs">
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span>High</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
            <span>Medium</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-red-500 rounded-full"></div>
            <span>Low</span>
          </div>
        </div>
      </div>
    );
  };

  // Account health trends chart component
  const AccountHealthTrendsChart = ({ data, title, accountName }: {
    data: Array<{
      month: string;
      overall_score: number;
      product_usage_score: number;
      support_score: number;
      customer_sentiment_score: number;
      business_outcomes_score: number;
      relationship_strength_score: number;
    }>,
    title: string,
    accountName: string
  }) => {
    if (!data || data.length === 0) {
      return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">{title}</h3>
          <div className="h-64 flex items-center justify-center text-gray-500">
            No trend data available
          </div>
        </div>
      );
    }

    const categories = [
      { key: 'overall_score', label: 'Overall', color: '#3B82F6' },
      { key: 'product_usage_score', label: 'Product Usage', color: '#10B981' },
      { key: 'support_score', label: 'Support', color: '#F59E0B' },
      { key: 'customer_sentiment_score', label: 'Customer Sentiment', color: '#8B5CF6' },
      { key: 'business_outcomes_score', label: 'Business Outcomes', color: '#EF4444' },
      { key: 'relationship_strength_score', label: 'Relationship Strength', color: '#06B6D4' }
    ];

    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">{title}</h3>
        <div className="h-80 relative">
          {/* Y-axis labels */}
          <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-500 pr-2">
            <span>100</span>
            <span>75</span>
            <span>50</span>
            <span>25</span>
            <span>0</span>
          </div>
          
          {/* Chart area */}
          <div className="ml-8 h-full relative">
            {/* Grid lines */}
            <div className="absolute inset-0">
              {[0, 0.25, 0.5, 0.75, 1].map((ratio) => (
                <div 
                  key={ratio}
                  className="absolute w-full border-t border-gray-100"
                  style={{ top: `${ratio * 100}%` }}
                />
              ))}
            </div>
            
            {/* Trend lines for each category */}
            <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              {categories.map((category) => (
                <polyline
                  key={category.key}
                  fill="none"
                  stroke={category.color}
                  strokeWidth="1"
                  points={data.map((point, index) => {
                    const x = (index / Math.max(1, data.length - 1)) * 100;
                    const y = 100 - ((point[category.key as keyof typeof point] as number) / 100) * 100;
                    return `${x},${y}`;
                  }).join(' ')}
                />
              ))}
              
              {/* Data points for overall score */}
              {data.map((point, index) => {
                const x = (index / Math.max(1, data.length - 1)) * 100;
                const y = 100 - (point.overall_score / 100) * 100;
                return (
                  <circle
                    key={index}
                    cx={x}
                    cy={y}
                    r="1"
                    fill="#3B82F6"
                    className="hover:r-2 transition-all cursor-pointer"
                  />
                );
              })}
            </svg>
          </div>
          
          {/* X-axis labels */}
          <div className="absolute bottom-0 left-8 right-0 flex justify-between text-xs text-gray-500">
            {data.map((point, index) => {
              const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
              const monthNumber = parseInt(point.month.split('-')[1]);
              const monthName = monthNames[monthNumber - 1] || `M${monthNumber}`;
              return (
                <span key={index} className="text-center" style={{ width: `${100/data.length}%` }}>
                  {monthName}
                </span>
              );
            })}
          </div>
        </div>
        
        {/* Legend */}
        <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
          {categories.map((category) => (
            <div key={category.key} className="flex items-center space-x-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: category.color }}
              ></div>
              <span>{category.label}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const parseNumericValue = (value: string): number => {
    const cleaned = value.toString().replace(/[%,$,\s]/g, '');
    const parsed = parseFloat(cleaned);
    return isNaN(parsed) ? 0 : parsed;
  };

  const normalizeWeights = (weights: number[]): number[] => {
    const sum = weights.reduce((acc, weight) => acc + weight, 0);
    if (sum === 0) return weights.map(() => 1 / weights.length);
    return weights.map(weight => weight / sum);
  };

  const calculateCategoryScore = (categoryKPIs: KPI[]): { score: number; weight: number; kpi_count: number; valid_kpi_count: number } => {
    if (categoryKPIs.length === 0) return { score: 0, weight: 0, kpi_count: 0, valid_kpi_count: 0 };

    const weights = categoryKPIs.map(kpi => parseFloat(kpi.weight || '0'));
    const normalizedWeights = normalizeWeights(weights);
    const values = categoryKPIs.map(kpi => parseNumericValue(kpi.data));
    
    const weightedSum = normalizedWeights.reduce((acc, weight, index) => acc + weight * values[index], 0);
    const validCount = values.filter(v => v > 0).length;
    
    return {
      score: Math.round(weightedSum * 100) / 100,
      weight: categoryKPIs[0]?.category ? 
        (kpiCategories.find(cat => cat.name === categoryKPIs[0].category)?.weight || 0) : 0,
      kpi_count: categoryKPIs.length,
      valid_kpi_count: validCount
    };
  };

  const calculateCorporateRollup = async (): Promise<void> => {
    if (!session?.customer_id) return;
    
    setIsCalculatingRollup(true);
    
    try {
      // Call backend rollup calculation
      const response = await fetch('/api/corporate/rollup', {
        method: 'GET',
        headers: {
          'X-Customer-ID': session.customer_id.toString(),
          'X-User-ID': session.user_id.toString(),
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        
        // Transform the backend response to match frontend expectations
        const categoryScores: { [key: string]: any } = {};
        
        // Process enhanced analysis if available
        if (data.health_scores?.enhanced_analysis?.category_scores) {
          data.health_scores.enhanced_analysis.category_scores.forEach((cat: any) => {
            categoryScores[cat.category] = {
              score: cat.average_score,
              weight: Math.round(cat.category_weight * 100), // Convert to percentage
              kpi_count: cat.kpi_count,
              valid_kpi_count: cat.valid_kpi_count
            };
          });
        }
        
        // Determine maturity tier based on overall score
        const overallScore = data.health_scores?.overall || 0;
        let maturityTier = 'At Risk';
        if (overallScore >= 80) maturityTier = 'Healthy';
        else if (overallScore < 50) maturityTier = 'Critical';
        
        // Generate recommendations based on score
        let recommendations = [];
        if (overallScore >= 80) {
          recommendations = [
            'Maintain current performance levels',
            'Continue monitoring key metrics',
            'Consider expansion opportunities'
          ];
        } else if (overallScore >= 50) {
          recommendations = [
            'Focus on improving underperforming categories',
            'Implement targeted improvement initiatives',
            'Increase monitoring frequency'
          ];
        } else {
          recommendations = [
            'Immediate action required on critical areas',
            'Review all KPI processes',
            'Consider external consultation'
          ];
        }
        
        setRollupResults({
          overall_score: overallScore,
          maturity_tier: maturityTier,
          category_scores: categoryScores,
          recommendations,
          health_scores: data.health_scores || {
            overall: overallScore,
            enhanced_analysis: {
              category_scores: [],
              overall_score: {
                overall_score: overallScore,
                health_status: maturityTier.toLowerCase(),
                color: 'yellow'
              }
            }
          }
        });
        
        // Update category weights from the response
        if (data.health_scores?.enhanced_analysis?.category_scores) {
          const weights: { [key: string]: number } = {};
          data.health_scores.enhanced_analysis.category_scores.forEach((cat: any) => {
            weights[cat.category] = cat.category_weight; // Keep as decimal (0.3, not 30)
          });
          setCategoryWeights(weights);
        }
        
      } else {
        // Fallback to frontend calculation
        const categoryScores: { [key: string]: any } = {};
        let totalScore = 0;
        
        // Get actual categories from KPI data
        const actualCategories = Array.from(new Set(kpiData.map(kpi => kpi.category)));
        console.log('Actual KPI categories:', actualCategories);
        
        actualCategories.forEach(categoryName => {
          const categoryKPIs = kpiData.filter(kpi => kpi.category === categoryName);
          const result = calculateCategoryScore(categoryKPIs);
          categoryScores[categoryName] = result;
          totalScore += (result.score * result.weight) / 100;
        });
        
        const overallScore = Math.round(totalScore * 100) / 100;
        let maturityTier = 'Critical';
        let recommendations: string[] = [];
        
        if (overallScore >= 75) {
          maturityTier = 'Healthy';
          recommendations = [
            'Excellent performance across all categories',
            'Focus on maintaining current momentum',
            'Consider expansion opportunities'
          ];
        } else if (overallScore >= 50) {
          maturityTier = 'At Risk';
          recommendations = [
            'Address underperforming categories',
            'Review KPI measurement frequency',
            'Implement improvement initiatives'
          ];
        } else {
          maturityTier = 'Critical';
          recommendations = [
            'Immediate action required',
            'Review all KPI processes',
            'Consider external consultation'
          ];
        }
        
        setRollupResults({
          overall_score: overallScore,
          maturity_tier: maturityTier,
          category_scores: categoryScores,
          recommendations,
          health_scores: {
            overall: overallScore,
            enhanced_analysis: {
              category_scores: [],
              overall_score: {
                overall_score: overallScore,
                health_status: maturityTier.toLowerCase(),
                color: 'yellow'
              }
            }
          }
        });
      }
    } catch (err) {
      console.error('Rollup calculation error:', err);
      setError('Failed to calculate rollup');
    } finally {
      setIsCalculatingRollup(false);
    }
  };

  const getHealthColor = (score: number): string => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getMaturityColor = (tier: string): string => {
    switch (tier) {
      case 'Healthy': return 'bg-green-500';
      case 'At Risk': return 'bg-yellow-500';
      case 'Critical': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const handleLogout = () => {
    logout();
  };

  const MetricCard = ({ title, value, change, trend, icon: Icon, color }: {
    title: string;
    value: string;
    change: string;
    trend: 'up' | 'down' | 'stable';
    icon: React.ComponentType<{ className?: string }>;
    color: string;
  }) => (
    <div className="bg-white rounded-xl shadow-lg border-2 border-gray-200/60 p-6 hover:shadow-xl hover:border-blue-300/50 transition-all duration-300 hover:-translate-y-1">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
          <div className="flex items-center mt-3">
            {trend === 'up' && <ArrowUp className="h-4 w-4 text-green-500 mr-1" />}
            {trend === 'down' && <ArrowDown className="h-4 w-4 text-red-500 mr-1" />}
            {trend === 'stable' && <Minus className="h-4 w-4 text-gray-500 mr-1" />}
            <span className={`text-sm font-semibold ${
              trend === 'up' ? 'text-green-600' : 
              trend === 'down' ? 'text-red-600' : 'text-gray-600'
            }`}>
              {change}
            </span>
          </div>
        </div>
        <div className={`p-4 rounded-xl ${color} shadow-md`}>
          <Icon className="h-7 w-7 text-white" />
        </div>
      </div>
    </div>
  );

  const RAGQueryInterface = () => {
    const [query, setQuery] = useState('');
    const [isQuerying, setIsQuerying] = useState(false);
    const [ragResponse, setRagResponse] = useState('');

    const handleRAGQuery = async () => {
      if (!query.trim() || !session?.customer_id) return;
      
      setIsQuerying(true);
      try {
        const response = await fetch('/api/rag/query', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Customer-ID': session.customer_id.toString(),
          },
          body: JSON.stringify({ query }),
        });
        
        if (response.ok) {
          const data = await response.json();
          setRagResponse(data.response || 'No response received');
        } else {
          setRagResponse('Failed to get response');
        }
      } catch (err) {
        setRagResponse('Error querying RAG system');
      } finally {
        setIsQuerying(false);
      }
    };

    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <MessageSquare className="h-5 w-5 mr-2 text-blue-600" />
          AI-Powered Insights
        </h3>
        <div className="space-y-4">
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask about customer health, revenue trends, or any KPI..."
              className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent pl-10"
            />
            <Search className="h-5 w-5 text-gray-400 absolute left-3 top-3.5" />
            <button
              onClick={handleRAGQuery}
              disabled={isQuerying || !query.trim()}
              className="absolute right-2 top-2 px-3 py-1 bg-blue-600 text-white rounded text-sm disabled:opacity-50"
            >
              {isQuerying ? 'Querying...' : 'Ask'}
            </button>
          </div>
          
          {ragResponse && (
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <div className="bg-blue-100 rounded-full p-2">
                  <Zap className="h-4 w-4 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">AI Response</p>
                  <p className="text-sm text-gray-600 mt-1">{ragResponse}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const DataUploadSection = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Upload className="h-5 w-5 mr-2 text-blue-600" />
          Data Integration Hub
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors cursor-pointer"
               onClick={() => fileInputRef.current?.click()}>
            <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-gray-900">Upload CSV/Excel</p>
            <p className="text-xs text-gray-500">Drag & drop or click to upload</p>
          </div>
          
          <div className="border border-gray-200 rounded-lg p-6 text-center bg-gradient-to-br from-green-50 to-emerald-50">
            <Database className="h-8 w-8 text-green-600 mx-auto mb-2" />
            <p className="text-sm font-medium text-gray-900">CRM Integration</p>
            <p className="text-xs text-gray-500">Salesforce, HubSpot, etc.</p>
          </div>
          
          <div className="border border-gray-200 rounded-lg p-6 text-center bg-gradient-to-br from-purple-50 to-indigo-50">
            <RefreshCw className="h-8 w-8 text-purple-600 mx-auto mb-2" />
            <p className="text-sm font-medium text-gray-900">Auto Sync</p>
            <p className="text-xs text-gray-500">FiveTran, Zapier</p>
          </div>
        </div>

        {isUploading && (
          <div className="mb-4">
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>Uploading and processing file...</span>
              <span>Processing...</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div className="bg-blue-600 h-2 rounded-full animate-pulse w-full"></div>
            </div>
          </div>
        )}

        {error && (
          <div className={`mb-4 p-3 rounded-lg ${error.includes('successful') ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
            <p className={`text-sm ${error.includes('successful') ? 'text-green-600' : 'text-red-600'}`}>{error}</p>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileUpload}
          className="hidden"
        />

        {/* Account Health Overview */}
        {accounts.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h4 className="font-semibold text-gray-900 mb-4">Account Health Overview</h4>
            
            {/* Corporate KPIs Summary */}
            <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center justify-between">
                <div>
                  <h5 className="text-sm font-medium text-blue-900">Corporate-Level KPIs</h5>
                  <p className="text-xs text-blue-700">
                    {kpiData.filter(kpi => kpi.account_id === null).length} shared KPIs across all accounts
                  </p>
                </div>
                <button
                  onClick={() => setActiveTab('accounts')}
                  className="text-xs text-blue-600 hover:text-blue-800 underline"
                >
                  View All Corporate KPIs
                </button>
              </div>
            </div>
            
            <div className="space-y-3">
              {accounts.map((account) => (
                <div key={account.account_id} className="border border-gray-200 rounded-lg overflow-hidden">
                  {/* Account Header Button */}
                  <button
                    onClick={() => {
                      if (selectedAccount?.account_id === account.account_id) {
                        setSelectedAccount(null);
                      } else {
                        setSelectedAccount(account);
                      }
                    }}
                    className={`w-full p-3 text-left transition-all hover:bg-gray-50 ${
                      selectedAccount?.account_id === account.account_id 
                        ? 'bg-blue-50 border-blue-500' 
                        : 'bg-white'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className={`w-3 h-3 rounded-full ${
                          account.health_score >= 75 
                            ? 'bg-green-500' 
                            : account.health_score >= 50 
                            ? 'bg-yellow-500' 
                            : 'bg-red-500'
                        }`}></div>
                        <div className="text-left">
                          <p className="text-sm font-medium text-gray-900">{account.account_name}</p>
                          <p className="text-xs text-gray-600">Score: {account.health_score}</p>
                        </div>
                      </div>
                      <span className="text-sm text-gray-500">
                        {selectedAccount?.account_id === account.account_id ? '▼' : '▶'}
                      </span>
                    </div>
                  </button>

                  {/* Expandable KPI Table */}
                  {selectedAccount?.account_id === account.account_id && (
                    <div className="border-t border-gray-200 bg-gray-50 p-3">
                      <div className="mb-3">
                        <h6 className="text-sm font-semibold text-gray-900 mb-1">
                          KPIs for {account.account_name}
                        </h6>
                        <p className="text-xs text-gray-600">
                          {kpiData.filter(kpi => kpi.account_id === account.account_id).length} Account KPIs
                        </p>
                      </div>
                      
                                              <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-gray-200 bg-white rounded text-xs">
                            <thead className="bg-gray-100">
                              <tr>
                                <th className="px-2 py-1 text-left text-xs font-medium text-gray-500">Category</th>
                                <th className="px-2 py-1 text-left text-xs font-medium text-gray-500">KPI Parameter</th>
                                <th className="px-2 py-1 text-left text-xs font-medium text-gray-500">Data</th>
                                <th className="px-2 py-1 text-left text-xs font-medium text-gray-500">Weight</th>
                                <th className="px-2 py-1 text-left text-xs font-medium text-gray-500">Health Status</th>
                              </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                              {kpiData
                                .filter(kpi => kpi.account_id === account.account_id)
                                .slice(0, 5) // Show first 5 account KPIs for compact view
                                .map((kpi) => (
                                  <tr key={kpi.kpi_id} className="hover:bg-gray-50">
                                    <td className="px-2 py-1 whitespace-nowrap text-xs text-gray-900">{kpi.category}</td>
                                    <td className="px-2 py-1 whitespace-nowrap text-xs text-gray-900">{kpi.kpi_parameter}</td>
                                    <td className="px-2 py-1 whitespace-nowrap text-xs text-gray-900">{kpi.data}</td>
                                    <td className="px-2 py-1 whitespace-nowrap text-xs text-gray-900">
                                      {categoryWeights[kpi.category] ? `${Math.round(categoryWeights[kpi.category] * 100)}%` : 'N/A'}
                                    </td>
                                    <td className="px-2 py-1 whitespace-nowrap text-xs">
                                      {kpiHealthStatuses[kpi.kpi_id] ? (
                                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                          kpiHealthStatuses[kpi.kpi_id].health_color === 'green' ? 'bg-green-100 text-green-800' :
                                          kpiHealthStatuses[kpi.kpi_id].health_color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
                                          kpiHealthStatuses[kpi.kpi_id].health_color === 'red' ? 'bg-red-100 text-red-800' :
                                          'bg-gray-100 text-gray-800'
                                        }`}>
                                          {kpiHealthStatuses[kpi.kpi_id].health_status}
                                        </span>
                                      ) : (
                                        <span className="text-gray-400" title={`KPI ID: ${kpi.kpi_id}, Available: ${Object.keys(kpiHealthStatuses).length}`}>
                                          {Object.keys(kpiHealthStatuses).length > 0 ? `Not Found (ID: ${kpi.kpi_id})` : 'Loading...'}
                                        </span>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                            </tbody>
                          </table>
                          {kpiData.filter(kpi => kpi.account_id === account.account_id).length === 0 && (
                            <div className="text-center py-4 text-gray-500">
                              <p className="text-xs">No account-specific KPIs found.</p>
                              <p className="text-xs mt-1">Upload a KPI file with this account name.</p>
                            </div>
                          )}
                          {kpiData.filter(kpi => kpi.account_id === account.account_id).length > 5 && (
                            <p className="text-xs text-gray-500 mt-2 text-center">
                              Showing first 5 KPIs. Go to Accounts tab for full view.
                            </p>
                          )}
                        </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>


    </div>
  );

  const AccountHealthDashboard = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Account Health Dashboard</h2>
        <button 
          onClick={calculateCorporateRollup}
          disabled={isCalculatingRollup}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {isCalculatingRollup ? (
            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Calculator className="h-4 w-4 mr-2" />
          )}
          {isCalculatingRollup ? 'Calculating...' : 'Calculate Corporate Rollup'}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {isLoading ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-center">
            <RefreshCw className="h-8 w-8 text-blue-600 animate-spin mr-3" />
            <span className="text-gray-600">Loading accounts...</span>
          </div>
        </div>
      ) : (
        <>
          {/* Account Heatmap */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Account Health Heatmap</h3>
            {accounts.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Users className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                <p>No accounts found. Upload data to get started.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {accounts.map((account) => (
                  <div key={account.account_id} className="border-2 border-gray-200 rounded-lg overflow-hidden">
                    {/* Account Header Button */}
                    <button
                      onClick={() => {
                        if (selectedAccount?.account_id === account.account_id) {
                          setSelectedAccount(null);
                        } else {
                          setSelectedAccount(account);
                        }
                      }}
                      className={`w-full p-4 text-left transition-all hover:bg-gray-50 ${
                        selectedAccount?.account_id === account.account_id 
                          ? 'bg-blue-50 border-blue-500' 
                          : 'bg-white'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-gray-900">{account.account_name}</h4>
                        <div className="flex items-center space-x-2">
                          <div className={`w-3 h-3 rounded-full ${getHealthColor(account.health_score)}`}></div>
                          <span className="text-sm text-gray-500">
                            {selectedAccount?.account_id === account.account_id ? '▼' : '▶'}
                          </span>
                        </div>
                      </div>
                      <div className="text-sm text-gray-600 space-y-1">
                        <p>Revenue: ${(account.revenue / 1000000).toFixed(1)}M</p>
                        <p>Industry: {account.industry}</p>
                        <p>Health Score: {account.health_score}/100</p>
                      </div>
                      <div className="mt-3 flex items-center text-xs text-blue-600">
                        <Eye className="h-3 w-3 mr-1" />
                        {selectedAccount?.account_id === account.account_id ? 'Hide KPIs' : 'View KPIs'}
                      </div>
                    </button>

                    {/* Expandable KPI Table */}
                    {selectedAccount?.account_id === account.account_id && (
                      <div className="border-t border-gray-200 bg-gray-50 p-4">
                        <div className="mb-4">
                          <h5 className="text-lg font-semibold text-gray-900 mb-2">
                            KPIs for {account.account_name}
                          </h5>
                                                  <p className="text-sm text-gray-600">
                          Showing {kpiData.filter(kpi => kpi.account_id === account.account_id).length} Account KPIs
                        </p>
                        </div>
                        
                                                <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-gray-200 bg-white rounded-lg">
                            <thead className="bg-gray-100">
                              <tr>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">KPI Parameter</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Weight</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Health Status</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Impact Level</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Frequency</th>
                              </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                              {kpiData
                                .filter(kpi => kpi.account_id === account.account_id)
                                .map((kpi) => (
                                  <tr key={kpi.kpi_id} className="hover:bg-gray-50">
                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{kpi.category}</td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{kpi.kpi_parameter}</td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{kpi.data}</td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                      {categoryWeights[kpi.category] ? `${Math.round(categoryWeights[kpi.category] * 100)}%` : 'N/A'}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm">
                                      {kpiHealthStatuses[kpi.kpi_id] ? (
                                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                          kpiHealthStatuses[kpi.kpi_id].health_color === 'green' ? 'bg-green-100 text-green-800' :
                                          kpiHealthStatuses[kpi.kpi_id].health_color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
                                          kpiHealthStatuses[kpi.kpi_id].health_color === 'red' ? 'bg-red-100 text-red-800' :
                                          'bg-gray-100 text-gray-800'
                                        }`}>
                                          {kpiHealthStatuses[kpi.kpi_id].health_status}
                                        </span>
                                      ) : (
                                        <span className="text-gray-400">Loading...</span>
                                      )}
                                    </td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{kpi.impact_level}</td>
                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{kpi.measurement_frequency}</td>
                                  </tr>
                                ))}
                            </tbody>
                          </table>
                          {kpiData.filter(kpi => kpi.account_id === account.account_id).length === 0 && (
                            <div className="text-center py-8 text-gray-500">
                              <p>No account-specific KPIs found for this account.</p>
                              <p className="text-sm mt-1">Upload a KPI file with this account name to see KPIs here.</p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Health Trend Chart */}
          <TrendChart 
            data={healthTrendData} 
            title="Overall Health Trend (Last 12 Months)" 
          />

          {/* Corporate Rollup Results */}
          {rollupResults && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Corporate Rollup Results</h3>
              
              {/* Overall Score */}
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-600">Overall Corporate Score</span>
                  <div className={`px-3 py-1 rounded-full text-sm font-medium text-white ${getMaturityColor(rollupResults.maturity_tier)}`}>
                    {rollupResults.maturity_tier}
                  </div>
                </div>
                <div className="text-3xl font-bold text-gray-900">{rollupResults.overall_score}/100</div>
              </div>

              {/* Category Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {Object.entries(rollupResults.category_scores).map(([category, data]) => (
                  <div key={category} className="p-4 border border-gray-200 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-900">{category}</span>
                      <span className="text-xs text-gray-500">{data.weight}% weight</span>
                    </div>
                    <div className="text-2xl font-bold text-gray-900 mb-2">{data.score}/100</div>
                    <div className="text-xs text-gray-500">
                      {data.valid_kpi_count}/{data.kpi_count} KPIs have data
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                      <div 
                        className={`h-2 rounded-full ${
                          data.score >= 75 ? 'bg-green-500' : 
                          data.score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${data.score}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Recommendations */}
              <div className="p-4 bg-blue-50 rounded-lg">
                <h4 className="font-semibold text-gray-900 mb-2">Recommendations</h4>
                <ul className="space-y-1">
                  {rollupResults.recommendations.map((rec, index) => (
                    <li key={index} className="text-sm text-gray-700 flex items-start">
                      <CheckCircle className="h-4 w-4 text-blue-600 mr-2 mt-0.5 flex-shrink-0" />
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* KPI Table View */}
          {showKPITable && selectedAccount && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  KPIs for {selectedAccount.account_name}
                </h3>
                <button 
                  onClick={() => setShowKPITable(false)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ×
                </button>
              </div>
              
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">KPI Parameter</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Data</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Weight</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Health Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Impact Level</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Frequency</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {kpiData
                      .filter(kpi => !selectedAccount || kpi.account_id === selectedAccount.account_id || kpi.account_id === null)
                      .map((kpi) => (
                        <tr key={kpi.kpi_id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{kpi.category}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{kpi.kpi_parameter}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{kpi.data}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {categoryWeights[kpi.category] ? `${Math.round(categoryWeights[kpi.category] * 100)}%` : 'N/A'}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            {kpiHealthStatuses[kpi.kpi_id] ? (
                              <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                kpiHealthStatuses[kpi.kpi_id].health_color === 'green' ? 'bg-green-100 text-green-800' :
                                kpiHealthStatuses[kpi.kpi_id].health_color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
                                kpiHealthStatuses[kpi.kpi_id].health_color === 'red' ? 'bg-red-100 text-red-800' :
                                'bg-gray-100 text-gray-800'
                              }`}>
                                {kpiHealthStatuses[kpi.kpi_id].health_status}
                              </span>
                            ) : (
                              <span className="text-gray-400">Loading...</span>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{kpi.impact_level}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{kpi.measurement_frequency}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );

  if (!session) {
    return <div>Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-gray-50 to-blue-50/20">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-md px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1">
            {/* Company Logo */}
            <img 
              src="/company-logo.png" 
              alt="Company Logo" 
              className="h-14 w-auto object-contain"
              onError={(e) => {
                e.currentTarget.style.display = 'none';
              }}
            />
            {/* Centered Title */}
            <div className="flex-1 text-center">
              <h1 className="text-xl font-bold text-gray-900">Customer Success Value Management System - A Triad Partner AI Solution</h1>
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
          { id: 'dashboard', label: 'Customer Success Performance Console', icon: BarChart3 },
          { id: 'upload', label: 'Data Integration', icon: Upload },
          { id: 'analytics', label: 'Customer Success Value Analytics', icon: Activity },
          { id: 'accounts', label: 'Account Health', icon: Users },
          { id: 'rag-analysis', label: 'AI Insights', icon: MessageSquare },
          { id: 'insights', label: 'Playbooks', icon: MessageSquare },
          { id: 'settings', label: 'Settings', icon: Settings },
          { id: 'reports', label: 'Reports', icon: FileText }
        ].map(item => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
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
              {/* Header Stats */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <MetricCard 
                  title="Total Accounts"
                  value={accounts.length.toString()}
                  change="Active"
                  trend="stable"
                  icon={Users}
                  color="bg-blue-500"
                />
                <MetricCard 
                  title="Total KPIs"
                  value={kpiData.length.toString()}
                  change="Tracked"
                  trend="stable"
                  icon={Target}
                  color="bg-purple-500"
                />
                <MetricCard 
                  title="Data Coverage"
                  value={`${Math.round((kpiData.filter(k => k.data && k.data !== '0').length / Math.max(kpiData.length, 1)) * 100)}%`}
                  change="Complete"
                  trend="up"
                  icon={Activity}
                  color="bg-green-500"
                />
                <MetricCard 
                  title="Health Score"
                  value={rollupResults ? `${Math.round(rollupResults.overall_score)}/100` : `${Math.round(accounts.reduce((acc, a) => acc + a.health_score, 0) / Math.max(accounts.length, 1))}/100`}
                  change="Average"
                  trend="stable"
                  icon={AlertTriangle}
                  color="bg-orange-500"
                />
              </div>

              {/* Main Dashboard Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-6">
                  {/* Corporate Health Rollup */}
                  <div className="bg-white rounded-xl shadow-lg border-2 border-blue-100/50 p-6 hover:shadow-xl transition-all duration-300">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-bold text-gray-900 flex items-center">
                        <div className="h-1 w-1 bg-blue-600 rounded-full mr-2"></div>
                        Corporate Health Rollup
                      </h3>
                      <button 
                        onClick={calculateCorporateRollup}
                        disabled={isCalculatingRollup}
                        className="px-3 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 disabled:opacity-50"
                      >
                        {isCalculatingRollup ? 'Calculating...' : 'Calculate Rollup'}
                      </button>
                    </div>
                    
                    {rollupResults ? (
                      <div className="space-y-4">
                        <div className="grid grid-cols-3 gap-4">
                          <div className="text-center p-3 bg-gray-50 rounded-lg">
                            <p className="text-sm text-gray-600">Overall Score</p>
                            <p className={`text-2xl font-bold ${getHealthColor(rollupResults.overall_score)}`}>
                              {rollupResults.overall_score.toFixed(1)}
                            </p>
                          </div>
                          <div className="text-center p-3 bg-gray-50 rounded-lg">
                            <p className="text-sm text-gray-600">Maturity Tier</p>
                            <p className={`text-lg font-semibold ${getMaturityColor(rollupResults.maturity_tier)}`}>
                              {rollupResults.maturity_tier}
                            </p>
                          </div>
                          <div className="text-center p-3 bg-gray-50 rounded-lg">
                            <p className="text-sm text-gray-600">Accounts</p>
                            <p className="text-2xl font-bold text-gray-900">{accounts.length}</p>
                          </div>
                        </div>
                        
                        <div className="space-y-3">
                          <h4 className="font-medium text-gray-900">Category Breakdown:</h4>
                          {Object.entries(rollupResults.category_scores).map(([categoryName, categoryData]) => (
                            <div key={categoryName} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                              <span className="text-sm font-medium text-gray-700">{categoryName}</span>
                              <div className="flex items-center space-x-2">
                                <span className={`text-sm font-semibold ${getHealthColor(categoryData.score)}`}>
                                  {categoryData.score.toFixed(1)}
                                </span>
                                <span className="text-xs text-gray-500">({categoryData.weight}%)</span>
                              </div>
                            </div>
                          ))}
                          
                          {/* Rollup Formula Explanation */}
                          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                            <h5 className="font-medium text-gray-900 mb-2">Rollup Formula:</h5>
                            <div className="text-xs text-gray-700 space-y-1">
                              <p>• <strong>Category Score</strong> = Σ(KPI Data × KPI Weight) / Σ(KPI Weights)</p>
                              <p>• <strong>Overall Score</strong> = Σ(Category Score × Category Weight) / 100</p>
                              <p>• <strong>Category Weights</strong>: Product Usage (25%), Customer Success (25%), Business Outcomes (30%), Relationship Strength (20%)</p>
                              <p>• <strong>Maturity Tiers</strong>: Healthy (&gt;=75), At Risk (50-74), Critical (&lt;50)</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-2" />
                        <p className="text-sm text-gray-600">
                          {accounts.length > 0 
                            ? 'Click "Calculate Rollup" to see corporate health overview' 
                            : 'Upload account data to see corporate health overview'
                          }
                        </p>
                      </div>
                    )}
                  </div>

                  {/* KPI Performance Heatmap */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">KPI Performance Heatmap</h3>
                    {kpiData.length > 0 ? (
                      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                        {kpiData.slice(0, 20).map((kpi, i) => (
                          <button
                            key={kpi.kpi_id}
                            onClick={() => {
                              setSelectedAccount(null);
                              setShowKPITable(true);
                              setActiveTab('accounts');
                            }}
                            className={`p-3 rounded-lg border-2 transition-all duration-200 hover:scale-105 hover:shadow-md ${
                              parseFloat(kpi.data || '0') > 70 ? 'border-green-200 bg-green-50 hover:bg-green-100' :
                              parseFloat(kpi.data || '0') > 40 ? 'border-yellow-200 bg-yellow-50 hover:bg-yellow-100' : 'border-red-200 bg-red-50 hover:bg-red-100'
                            }`}
                          >
                            <div className="text-center">
                              <div className={`w-3 h-3 rounded-full mx-auto mb-2 ${
                                parseFloat(kpi.data || '0') > 70 ? 'bg-green-500' : 
                                parseFloat(kpi.data || '0') > 40 ? 'bg-yellow-500' : 'bg-red-500'
                              }`}></div>
                              <p className="text-sm font-medium text-gray-900 truncate">{kpi.kpi_parameter || `KPI ${i + 1}`}</p>
                              <p className="text-xs text-gray-600 mt-1">Value: {kpi.data || 'N/A'}</p>
                              <p className="text-xs text-gray-500">Weight: {kpi.weight || 'N/A'}</p>
                            </div>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <Target className="h-12 w-12 text-gray-400 mx-auto mb-2" />
                        <p className="text-sm text-gray-600">No KPIs available</p>
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-6">
                  {/* Account Health Summary */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Account Health Summary</h3>
                    <div className="space-y-3">
                      {[
                        { name: 'Healthy', count: accounts.filter(a => a.health_score >= 80).length, color: 'bg-green-500' },
                        { name: 'At Risk', count: accounts.filter(a => a.health_score >= 60 && a.health_score < 80).length, color: 'bg-yellow-500' },
                        { name: 'Critical', count: accounts.filter(a => a.health_score < 60).length, color: 'bg-red-500' }
                      ].map((status, index) => (
                        <div key={index} className="flex items-center justify-between">
                          <div className="flex items-center">
                            <div className={`w-3 h-3 rounded-full ${status.color} mr-3`}></div>
                            <span className="text-sm font-medium text-gray-700">{status.name}</span>
                          </div>
                          <span className="text-sm font-bold text-gray-900">{status.count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'upload' && <DataUploadSection />}

          {activeTab === 'analytics' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-900">Corporate Health Overview</h2>
                <div className="flex space-x-3">
                  <button className="flex items-center px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50">
                    <Filter className="h-4 w-4 mr-2" />
                    Filter
                  </button>
                  <button className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                    <Download className="h-4 w-4 mr-2" />
                    Export
                  </button>
                </div>
              </div>

              {/* Rollup Level Tabs */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-100">
                <div className="border-b border-gray-200">
                  <nav className="flex space-x-8 px-6" aria-label="Tabs">
                    {[
                      { id: 'overview', name: 'Overview', description: 'High-level corporate health summary' },
                      { id: 'level1', name: 'Level 1 Rollup', description: 'Individual KPI health scores & calculations' },
                      { id: 'level2', name: 'Level 2 Rollup', description: 'Category-level health scores & weighted averages' },
                      { id: 'level3', name: 'Level 3 Rollup', description: 'Overall corporate health score & final calculations' },
                      { id: 'trends', name: 'Trends', description: 'Historical KPI & health score trends' }
                    ].map((tab) => (
                      <button
                        key={tab.id}
                        onClick={() => setActiveRollupTab(tab.id as any)}
                        className={`py-4 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                          activeRollupTab === tab.id
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        <div className="text-left">
                          <div className="font-semibold">{tab.name}</div>
                          <div className="text-xs text-gray-400 mt-1">{tab.description}</div>
                        </div>
                      </button>
                    ))}
                  </nav>
                </div>
              </div>

              {/* Tab Content */}
              {activeRollupTab === 'overview' && (
                <>
                  {/* Corporate Health Summary */}
                  {rollupResults && (
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Overall Corporate Health</h3>
                      
                      {/* Overall Score */}
                      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-gray-600">Overall Corporate Score</span>
                          <div className={`px-3 py-1 rounded-full text-sm font-medium text-white ${getMaturityColor(rollupResults.maturity_tier)}`}>
                            {rollupResults.maturity_tier}
                          </div>
                        </div>
                        <div className="text-3xl font-bold text-gray-900 mb-2">
                          {Math.round(rollupResults.health_scores.overall)}/100
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-3">
                          <div 
                            className={`h-3 rounded-full ${getMaturityColor(rollupResults.maturity_tier)}`}
                            style={{ width: `${rollupResults.health_scores.overall}%` }}
                          ></div>
                        </div>
                      </div>

                      {/* Category Breakdown */}
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {rollupResults.health_scores.enhanced_analysis.category_scores.map((category: any, index: number) => {
                          const colors = ['bg-emerald-500', 'bg-blue-500', 'bg-purple-500', 'bg-orange-500', 'bg-red-500'];
                          const categoryColor = colors[index % colors.length];
                          
                          return (
                            <div key={index} className="p-4 border border-gray-200 rounded-lg">
                              <div className="flex items-center justify-between mb-2">
                                <h4 className="font-medium text-gray-900 text-sm">{category.category}</h4>
                                <div className={`px-2 py-1 rounded-full text-xs font-medium text-white ${categoryColor}`}>
                                  {Math.round(category.category_weight * 100)}%
                                </div>
                              </div>
                              <div className="text-2xl font-bold text-gray-900 mb-1">
                                {Math.round(category.average_score)}/100
                              </div>
                              <div className="text-xs text-gray-500 mb-2">
                                {category.valid_kpi_count}/{category.kpi_count} KPIs
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-2">
                                <div 
                                  className={`h-2 rounded-full ${categoryColor}`}
                                  style={{ width: `${category.average_score}%` }}
                                ></div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                  
                  {/* Collapsible KPI Categories - Limited View */}
                  <div className="space-y-4 mt-6">
                {Array.from(new Set(kpiData.map(kpi => kpi.category))).map((categoryName, index) => {
                  const categoryKPIs = kpiData.filter(kpi => kpi.category === categoryName);
                  const categoryData = categoryKPIs.filter(k => k.data && k.data !== '0');
                  const colors = ['bg-emerald-500', 'bg-blue-500', 'bg-purple-500', 'bg-orange-500', 'bg-red-500'];
                  const categoryColor = colors[index % colors.length];
                  const isExpanded = expandedCategories[categoryName];
                  
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
                      
                      {/* Collapsible Content - Limited to Top KPIs */}
                      {isExpanded && (
                        <div className="border-t border-gray-100 p-4">
                          <div className="mb-3 text-sm text-gray-600">
                            Showing top 6 KPIs by value (out of {categoryKPIs.length} total)
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {categoryKPIs
                              .sort((a, b) => parseFloat(b.data || '0') - parseFloat(a.data || '0'))
                              .slice(0, 6)
                              .map((kpi) => {
                              const value = parseFloat(kpi.data || '0');
                              const statusColor = value > 70 ? 'border-green-200 bg-green-50' : 
                                                value > 40 ? 'border-yellow-200 bg-yellow-50' : 
                                                'border-red-200 bg-red-50';
                              const dotColor = value > 70 ? 'bg-green-500' : 
                                             value > 40 ? 'bg-yellow-500' : 
                                             'bg-red-500';
                              
                              return (
                                <div 
                                  key={kpi.kpi_id} 
                                  className={`p-3 rounded-lg border-2 transition-all duration-200 hover:scale-105 hover:shadow-md ${statusColor}`}
                                >
                                  <div className="flex items-start justify-between">
                                    <div className="flex-1 min-w-0">
                                      <p className="text-sm font-medium text-gray-900 truncate" title={kpi.kpi_parameter}>
                                        {kpi.kpi_parameter}
                                      </p>
                                      <p className="text-xs text-gray-600 mt-1">Value: {kpi.data || 'N/A'}</p>
                                      <p className="text-xs text-gray-500">Weight: {kpi.weight || 'N/A'}</p>
                                    </div>
                                    <div className={`w-3 h-3 rounded-full ml-2 flex-shrink-0 ${dotColor}`}></div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                          {categoryKPIs.length > 6 && (
                            <div className="mt-3 text-center">
                              <button className="text-sm text-blue-600 hover:text-blue-800">
                                View all {categoryKPIs.length} KPIs in this category
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
                  </div>
                </>
              )}

              {/* Level 1 Rollup Tab - Individual KPI Health Scores */}
              {activeRollupTab === 'level1' && (
                <div className="space-y-6">
                  <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Level 1 Rollup: Individual KPI Health Scores</h3>
                    <p className="text-sm text-gray-600 mb-6">
                      This shows how each individual KPI is scored against its reference ranges using the medical blood test methodology.
                    </p>
                    
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">KPI Name</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Value</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Reference Range</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Health Status</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Health Score</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Impact Weight</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Weighted Score</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {(() => {
                            // Group KPIs by account first, then by category for subtotals
                            const kpisByAccount = kpiData.reduce((acc, kpi) => {
                              const accountName = kpi.account_name || 'Unknown Account';
                              if (!acc[accountName]) {
                                acc[accountName] = {};
                              }
                              if (!acc[accountName][kpi.category]) {
                                acc[accountName][kpi.category] = [];
                              }
                              acc[accountName][kpi.category].push(kpi);
                              return acc;
                            }, {} as {[accountName: string]: {[category: string]: typeof kpiData}});

                            const rows: JSX.Element[] = [];
                            let globalGrandTotalWeightedScore = 0;
                            let globalGrandTotalKpiCount = 0;
                            let globalGrandTotalHealthScore = 0;
                            let globalGrandTotalValidKpis = 0;

                            // Process each account
                            Object.entries(kpisByAccount).forEach(([accountName, accountCategories]) => {
                              // Add account header
                              rows.push(
                                <tr key={`${accountName}-header`} className="bg-gray-100 border-t-4 border-gray-300">
                                  <td className="px-6 py-4 whitespace-nowrap text-lg font-bold text-gray-900" colSpan={8}>
                                    <div className="flex items-center">
                                      <span className="mr-2">🏢</span>
                                      {accountName}
                                    </div>
                                  </td>
                                </tr>
                              );

                              let accountTotalWeightedScore = 0;
                              let accountTotalKpiCount = 0;
                              let accountTotalHealthScore = 0;
                              let accountValidKpis = 0;

                              // Process each category within this account
                              Object.entries(accountCategories).forEach(([category, categoryKpis]) => {
                                let categoryTotalWeightedScore = 0;
                                let categoryTotalHealthScore = 0;
                                let categoryValidKpis = 0;

                                // Add KPIs for this category
                                categoryKpis.forEach((kpi) => {
                                  const healthStatus = kpiHealthStatuses[kpi.kpi_id];
                                  const impactWeight = kpi.impact_level === 'High' ? 3 : kpi.impact_level === 'Medium' ? 2 : 1;
                                  const weightedScore = healthStatus ? healthStatus.health_score * impactWeight : 0;
                                  
                                  if (healthStatus) {
                                    categoryTotalWeightedScore += weightedScore;
                                    categoryTotalHealthScore += healthStatus.health_score;
                                    categoryValidKpis++;
                                  }

                                  rows.push(
                                    <tr key={kpi.kpi_id} className="hover:bg-gray-50">
                                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                        {kpi.kpi_parameter}
                                      </td>
                                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {kpi.category}
                                      </td>
                                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {kpi.data || 'N/A'}
                                      </td>
                                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                        {kpiReferenceRanges.find(r => r.kpi_name === kpi.kpi_parameter) ? 
                                          `Critical: ${kpiReferenceRanges.find(r => r.kpi_name === kpi.kpi_parameter)?.critical_min}-${kpiReferenceRanges.find(r => r.kpi_name === kpi.kpi_parameter)?.critical_max} | Risk: ${kpiReferenceRanges.find(r => r.kpi_name === kpi.kpi_parameter)?.risk_min}-${kpiReferenceRanges.find(r => r.kpi_name === kpi.kpi_parameter)?.risk_max} | Healthy: ${kpiReferenceRanges.find(r => r.kpi_name === kpi.kpi_parameter)?.healthy_min}-${kpiReferenceRanges.find(r => r.kpi_name === kpi.kpi_parameter)?.healthy_max}` :
                                          'N/A'
                                        }
                                      </td>
                                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {healthStatus ? (
                                          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                            healthStatus.health_color === 'green' ? 'bg-green-100 text-green-800' :
                                            healthStatus.health_color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
                                            healthStatus.health_color === 'red' ? 'bg-red-100 text-red-800' :
                                            'bg-gray-100 text-gray-800'
                                          }`}>
                                            {healthStatus.health_status}
                                          </span>
                                        ) : (
                                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                            Loading...
                                          </span>
                                        )}
                                      </td>
                                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {healthStatus ? `${Math.round(healthStatus.health_score)}/100` : 'N/A'}
                                      </td>
                                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {kpi.impact_level} ({impactWeight}x)
                                      </td>
                                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                        {healthStatus ? `${Math.round(weightedScore)}` : 'N/A'}
                                      </td>
                                    </tr>
                                  );
                                });

                                // Add category subtotal row for this account
                                const categoryAverageHealthScore = categoryValidKpis > 0 ? categoryTotalHealthScore / categoryValidKpis : 0;
                                rows.push(
                                  <tr key={`${accountName}-${category}-total`} className="bg-blue-50 border-t-2 border-blue-200">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-blue-900" colSpan={7}>
                                      <div className="flex items-center">
                                        <span className="mr-2">📊</span>
                                        {accountName} - {category} - Total
                                      </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-blue-900">
                                      <div className="text-right">
                                        <div className="font-bold">{Math.round(categoryTotalWeightedScore)}</div>
                                        <div className="text-xs text-blue-600">
                                          {categoryValidKpis}/{categoryKpis.length} KPIs
                                        </div>
                                        <div className="text-xs text-blue-600">
                                          Avg: {Math.round(categoryAverageHealthScore)}/100
                                        </div>
                                      </div>
                                    </td>
                                  </tr>
                                );

                                // Add to account totals
                                accountTotalWeightedScore += categoryTotalWeightedScore;
                                accountTotalKpiCount += categoryKpis.length;
                                accountTotalHealthScore += categoryTotalHealthScore;
                                accountValidKpis += categoryValidKpis;
                              });

                              // Add account grand total row
                              const accountAverageHealthScore = accountValidKpis > 0 ? accountTotalHealthScore / accountValidKpis : 0;
                              rows.push(
                                <tr key={`${accountName}-grand-total`} className="bg-green-50 border-t-4 border-green-300">
                                  <td className="px-6 py-4 whitespace-nowrap text-lg font-bold text-green-900" colSpan={7}>
                                    <div className="flex items-center">
                                      <span className="mr-2">🎯</span>
                                      {accountName} - Grand Total
                                    </div>
                                  </td>
                                  <td className="px-6 py-4 whitespace-nowrap text-lg font-bold text-green-900">
                                    <div className="text-right">
                                      <div className="font-bold text-xl">{Math.round(accountTotalWeightedScore)}</div>
                                      <div className="text-sm text-green-600">
                                        {accountValidKpis}/{accountTotalKpiCount} KPIs
                                      </div>
                                      <div className="text-sm text-green-600">
                                        Overall Avg: {Math.round(accountAverageHealthScore)}/100
                                      </div>
                                    </div>
                                  </td>
                                </tr>
                              );

                              // Add to global totals
                              globalGrandTotalWeightedScore += accountTotalWeightedScore;
                              globalGrandTotalKpiCount += accountTotalKpiCount;
                              globalGrandTotalHealthScore += accountTotalHealthScore;
                              globalGrandTotalValidKpis += accountValidKpis;
                            });

                            // Add global grand total row
                            const globalAverageHealthScore = globalGrandTotalValidKpis > 0 ? globalGrandTotalHealthScore / globalGrandTotalValidKpis : 0;
                            rows.push(
                              <tr key="global-grand-total" className="bg-purple-50 border-t-4 border-purple-300">
                                <td className="px-6 py-4 whitespace-nowrap text-xl font-bold text-purple-900" colSpan={7}>
                                  <div className="flex items-center">
                                    <span className="mr-2">🌟</span>
                                    Global Grand Total (All Accounts)
                                  </div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-xl font-bold text-purple-900">
                                  <div className="text-right">
                                    <div className="font-bold text-2xl">{Math.round(globalGrandTotalWeightedScore)}</div>
                                    <div className="text-sm text-purple-600">
                                      {globalGrandTotalValidKpis}/{globalGrandTotalKpiCount} KPIs
                                    </div>
                                    <div className="text-sm text-purple-600">
                                      Overall Avg: {Math.round(globalAverageHealthScore)}/100
                                    </div>
                                  </div>
                                </td>
                              </tr>
                            );

                            return rows;
                          })()}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* Level 2 Rollup Tab - Category Health Scores */}
              {activeRollupTab === 'level2' && (
                <div className="space-y-6">
                  <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Level 2 Rollup: Category Health Scores</h3>
                    <p className="text-sm text-gray-600 mb-6">
                      This shows how individual KPI scores are aggregated into category-level health scores using weighted averages.
                    </p>
                    
                    {rollupResults && rollupResults.health_scores.enhanced_analysis.category_scores.map((category: any, index: number) => {
                      const colors = ['bg-emerald-500', 'bg-blue-500', 'bg-purple-500', 'bg-orange-500', 'bg-red-500'];
                      const categoryColor = colors[index % colors.length];
                      
                      return (
                        <div key={index} className="mb-6 p-6 border border-gray-200 rounded-lg">
                          <div className="flex items-center justify-between mb-4">
                            <h4 className="text-lg font-semibold text-gray-900">{category.category}</h4>
                            <div className={`px-3 py-1 rounded-full text-sm font-medium text-white ${categoryColor}`}>
                              Category Weight: {Math.round(category.category_weight * 100)}%
                            </div>
                          </div>
                          
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                            <div className="p-4 bg-gray-50 rounded-lg">
                              <div className="text-sm font-medium text-gray-600">Raw Category Score</div>
                              <div className="text-2xl font-bold text-gray-900">{Math.round(category.average_score)}/100</div>
                            </div>
                            <div className="p-4 bg-gray-50 rounded-lg">
                              <div className="text-sm font-medium text-gray-600">Category Weight</div>
                              <div className="text-2xl font-bold text-gray-900">{Math.round(category.category_weight * 100)}%</div>
                            </div>
                            <div className="p-4 bg-gray-50 rounded-lg">
                              <div className="text-sm font-medium text-gray-600">Weighted Category Score</div>
                              <div className="text-2xl font-bold text-gray-900">{Math.round(category.average_score * category.category_weight)}/100</div>
                            </div>
                          </div>
                          
                          <div className="text-sm text-gray-600 mb-2">
                            KPIs in this category: {category.valid_kpi_count}/{category.kpi_count} (Coverage: {Math.round((category.valid_kpi_count / category.kpi_count) * 100)}%)
                          </div>
                          
                          <div className="w-full bg-gray-200 rounded-full h-3">
                            <div 
                              className={`h-3 rounded-full ${categoryColor}`}
                              style={{ width: `${category.average_score}%` }}
                            ></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Level 3 Rollup Tab - Overall Corporate Health */}
              {activeRollupTab === 'level3' && (
                <div className="space-y-6">
                  <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Level 3 Rollup: Overall Corporate Health Score</h3>
                    <p className="text-sm text-gray-600 mb-6">
                      This shows the final calculation of the overall corporate health score from category-level scores.
                    </p>
                    
                    {rollupResults && (
                      <>
                        <div className="mb-6 p-6 bg-gray-50 rounded-lg">
                          <h4 className="text-lg font-semibold text-gray-900 mb-4">Final Corporate Health Score</h4>
                          <div className="text-4xl font-bold text-gray-900 mb-2">
                            {Math.round(rollupResults.health_scores.overall)}/100
                          </div>
                          <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium text-white ${getMaturityColor(rollupResults.maturity_tier)}`}>
                            {rollupResults.maturity_tier}
                          </div>
                        </div>
                        
                        <div className="mb-6">
                          <h4 className="text-lg font-semibold text-gray-900 mb-4">Calculation Breakdown</h4>
                          <div className="space-y-3">
                            {rollupResults.health_scores.enhanced_analysis.category_scores.map((category: any, index: number) => (
                              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                <span className="text-sm font-medium text-gray-900">{category.category}</span>
                                <div className="flex items-center space-x-4">
                                  <span className="text-sm text-gray-600">
                                    {Math.round(category.average_score)} × {Math.round(category.category_weight * 100)}% = {Math.round(category.average_score * category.category_weight)}
                                  </span>
                                </div>
                              </div>
                            ))}
                            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border-2 border-blue-200">
                              <span className="text-sm font-bold text-gray-900">Total Corporate Score</span>
                              <span className="text-sm font-bold text-gray-900">
                                {Math.round(rollupResults.health_scores.overall)}/100
                              </span>
                            </div>
                          </div>
                        </div>
                        
                        <div className="mb-6">
                          <h4 className="text-lg font-semibold text-gray-900 mb-4">Maturity Tier Classification</h4>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className={`p-4 rounded-lg border-2 ${rollupResults.health_scores.overall >= 67 ? 'border-green-500 bg-green-50' : 'border-gray-200 bg-gray-50'}`}>
                              <div className="text-sm font-medium text-gray-600">Healthy</div>
                              <div className="text-lg font-bold text-gray-900">67-100</div>
                              <div className="text-xs text-gray-500">High performance</div>
                            </div>
                            <div className={`p-4 rounded-lg border-2 ${rollupResults.health_scores.overall >= 34 && rollupResults.health_scores.overall < 67 ? 'border-yellow-500 bg-yellow-50' : 'border-gray-200 bg-gray-50'}`}>
                              <div className="text-sm font-medium text-gray-600">At Risk</div>
                              <div className="text-lg font-bold text-gray-900">34-66</div>
                              <div className="text-xs text-gray-500">Medium performance</div>
                            </div>
                            <div className={`p-4 rounded-lg border-2 ${rollupResults.health_scores.overall < 34 ? 'border-red-500 bg-red-50' : 'border-gray-200 bg-gray-50'}`}>
                              <div className="text-sm font-medium text-gray-600">Critical</div>
                              <div className="text-lg font-bold text-gray-900">0-33</div>
                              <div className="text-xs text-gray-500">Low performance</div>
                            </div>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* Trends Tab - Historical KPI & Health Score Trends */}
              {activeRollupTab === 'trends' && (
                <div className="space-y-6">
                  <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Historical Trends Analysis</h3>
                    <p className="text-sm text-gray-600 mb-6">
                      View historical KPI and health score trends over time. Select an account and KPI to analyze trends.
                    </p>
                    
                    {/* Time Series Statistics */}
                    {timeSeriesStats && (
                      <div className="mb-6 p-4 bg-blue-50 rounded-lg">
                        <h4 className="text-sm font-semibold text-blue-900 mb-2">Time Series Data Overview</h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <span className="text-blue-700 font-medium">Total Data Points:</span>
                            <span className="ml-2 text-blue-900 font-bold">{timeSeriesStats.total_data_points?.toLocaleString() || '0'}</span>
                          </div>
                          <div>
                            <span className="text-blue-700 font-medium">Date Range:</span>
                            <span className="ml-2 text-blue-900 font-bold">
                              {timeSeriesStats.date_range ? 
                                `${timeSeriesStats.date_range.oldest} to ${timeSeriesStats.date_range.newest}` : 
                                'N/A'}
                            </span>
                          </div>
                          <div>
                            <span className="text-blue-700 font-medium">Health Trends:</span>
                            <span className="ml-2 text-blue-900 font-bold">{timeSeriesStats.health_trend_records || '0'}</span>
                          </div>
                          <div>
                            <span className="text-blue-700 font-medium">KPI Time Series:</span>
                            <span className="ml-2 text-blue-900 font-bold">{timeSeriesStats.kpi_time_series_records?.toLocaleString() || '0'}</span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Account Selection for Trends */}
                    <div className="mb-6">
                      <label className="block text-sm font-medium text-gray-700 mb-2">Select Account for Analysis</label>
                      <select
                        value={selectedAccountForTrends || ''}
                        onChange={(e) => {
                          const accountId = e.target.value ? parseInt(e.target.value) : null;
                          setSelectedAccountForTrends(accountId);
                          if (accountId) {
                            fetchAccountHealthTrends(accountId);
                          }
                        }}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      >
                        <option value="">Choose an account...</option>
                        {accounts.map((account) => (
                          <option key={account.account_id} value={account.account_id}>
                            {account.account_name}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Account Health Trends Chart */}
                    {selectedAccountForTrends && accountHealthTrends.length > 0 && (
                      <div className="mb-6">
                        <AccountHealthTrendsChart
                          data={accountHealthTrends}
                          title={`Health Score Trends - ${accounts.find(a => a.account_id === selectedAccountForTrends)?.account_name}`}
                          accountName={accounts.find(a => a.account_id === selectedAccountForTrends)?.account_name || ''}
                        />
                      </div>
                    )}

                    {/* KPI Selection for Trends */}
                    {selectedAccountForTrends && (
                      <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Select KPI for Analysis</label>
                        <select
                          value={selectedKpiForTrends || ''}
                          onChange={(e) => {
                            setSelectedKpiForTrends(e.target.value || null);
                            if (e.target.value && selectedAccountForTrends) {
                              fetchKpiTrends(e.target.value, selectedAccountForTrends);
                            }
                          }}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="">Choose a KPI...</option>
                          {kpiData
                            .filter(kpi => kpi.account_id === selectedAccountForTrends)
                            .map((kpi) => (
                              <option key={kpi.kpi_id} value={kpi.kpi_parameter}>
                                {kpi.kpi_parameter}
                              </option>
                            ))}
                        </select>
                      </div>
                    )}

                    {/* KPI Trends Chart */}
                    {selectedKpiForTrends && selectedAccountForTrends && kpiTrendData.length > 0 && (
                      <div className="mb-6">
                        <KpiTrendChart
                          data={kpiTrendData}
                          title={`KPI Trend Analysis - ${selectedKpiForTrends}`}
                          kpiName={selectedKpiForTrends}
                        />
                      </div>
                    )}

                    {/* Instructions */}
                    {(!selectedAccountForTrends || (!accountHealthTrends.length && !kpiTrendData.length)) && (
                      <div className="text-center py-12">
                        <TrendingUp className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">No Trends Selected</h3>
                        <p className="text-gray-500">
                          Select an account and optionally a KPI to view historical trends and analysis.
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'accounts' && <AccountHealthDashboard />}

          {activeTab === 'rag-analysis' && <RAGAnalysis />}

          {activeTab === 'insights' && (
            <Playbooks customerId={session.customer_id} />
          )}

          {activeTab === 'playbooks' && (
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-gray-900">AI-Powered Business Insights</h2>
              <RAGQueryInterface />
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                  <h3 className="font-semibold text-gray-900 mb-4">Growth Opportunities</h3>
                  <div className="space-y-3">
                    {[
                      'Manufacturing module adoption could increase ARR by 23%',
                      'Analytics feature usage correlates with 31% lower churn',
                      'Premium tier upgrade potential identified for 12 accounts'
                    ].map((insight, index) => (
                      <div key={index} className="flex items-start space-x-3 p-3 bg-green-50 rounded-lg">
                        <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                        <p className="text-sm text-gray-700">{insight}</p>
                      </div>
                    ))}
                  </div>
                </div>
                
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                  <h3 className="font-semibold text-gray-900 mb-4">Risk Alerts</h3>
                  <div className="space-y-3">
                    {accounts.filter(a => a.health_score < 70).slice(0, 3).map((account, index) => (
                      <div key={index} className="flex items-start space-x-3 p-3 bg-red-50 rounded-lg">
                        <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium text-gray-700">{account.account_name}</p>
                          <p className="text-xs text-gray-600">Health Score: {account.health_score}/100</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

                  {activeTab === 'settings' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-gray-900">Settings & Configuration</h2>
              <button
                onClick={() => setShowSettings(true)}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <Settings className="h-4 w-4 mr-2" />
                Advanced Settings
              </button>
            </div>
            
            {/* Master KPI Framework Upload */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h4 className="font-semibold text-gray-900 mb-4 flex items-center">
                <Settings className="h-5 w-5 mr-2 text-blue-600" />
                Master KPI Framework Configuration
              </h4>
              <div className="space-y-4">
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-start space-x-3">
                    <div className="bg-blue-100 rounded-full p-2">
                      <FileText className="h-4 w-4 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-blue-900">📋 Master Framework File</p>
                      <p className="text-sm text-blue-700 mt-1">
                        Upload your master KPI framework file (e.g., Maturity-Framework-KPI-loveable.xlsx) 
                        to configure category weights and KPI definitions.
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors cursor-pointer"
                     onClick={() => masterFileInputRef.current?.click()}>
                  <Upload className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm font-medium text-gray-900">Upload Master KPI Framework</p>
                  <p className="text-xs text-gray-500">Drag & drop or click to upload Excel file</p>
                </div>
                
                <input
                  ref={masterFileInputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleMasterFileUpload}
                  className="hidden"
                />
                
                {masterFileError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-sm text-red-600">{masterFileError}</p>
                  </div>
                )}
                
                {masterFileSuccess && (
                  <div className="p-4 bg-green-50 border border-green-200 rounded-md">
                    <h5 className="text-sm font-medium text-green-900 mb-2">✅ Master File Uploaded Successfully</h5>
                    <div className="text-sm text-green-700 space-y-1">
                      <p>• File: {masterFileSuccess.filename}</p>
                      <p>• Category weights extracted and configured</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Current Category Weights */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h4 className="font-semibold text-gray-900 mb-4">Current Category Weights</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(categoryWeights).map(([category, weight]) => (
                  <div key={category} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{category}</p>
                      <p className="text-xs text-gray-500">Category weight</p>
                    </div>
                    <span className="px-3 py-1 text-sm font-medium bg-blue-100 text-blue-700 rounded-full">
                      {(weight * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* KPI Health Status Calculations */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-semibold text-gray-900 flex items-center">
                  <Calculator className="h-5 w-5 mr-2 text-green-600" />
                  KPI Health Status Calculations
                </h4>
                <button
                  onClick={fetchKpiReferenceRanges}
                  className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                >
                  Load KPI Reference Ranges
                </button>
              </div>
              <div className="space-y-4">
                <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-start space-x-3">
                    <div className="bg-green-100 rounded-full p-2">
                      <Activity className="h-4 w-4 text-green-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-green-900">🔬 Medical Blood Test Methodology</p>
                      <p className="text-sm text-green-700 mt-1">
                        Each KPI is evaluated against predefined reference ranges to determine health status:
                        <strong> Healthy (Green)</strong>, <strong>Risk (Yellow)</strong>, or <strong>Critical (Red)</strong>.
                      </p>
                    </div>
                  </div>
                </div>
                
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">KPI Parameter</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Unit</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Critical Min</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Critical Max</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Risk Min</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Risk Max</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Healthy Min</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Healthy Max</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Higher is Better</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {kpiReferenceRanges.length > 0 ? (
                        kpiReferenceRanges.map((kpi, index) => (
                          <tr key={kpi.range_id || index} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm text-gray-900 font-medium">{kpi.kpi_name}</td>
                            <td className="px-4 py-3 text-sm text-gray-500">{kpi.unit}</td>
                            <td className="px-4 py-3 text-sm">
                              <input
                                type="number"
                                value={kpi.critical_min}
                                onChange={(e) => updateReferenceRange(kpi.range_id, 'critical_min', parseFloat(e.target.value) || 0)}
                                className="w-20 px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
                                step="0.01"
                              />
                            </td>
                            <td className="px-4 py-3 text-sm">
                              <input
                                type="number"
                                value={kpi.critical_max}
                                onChange={(e) => updateReferenceRange(kpi.range_id, 'critical_max', parseFloat(e.target.value) || 0)}
                                className="w-20 px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
                                step="0.01"
                              />
                            </td>
                            <td className="px-4 py-3 text-sm">
                              <input
                                type="number"
                                value={kpi.risk_min}
                                onChange={(e) => updateReferenceRange(kpi.range_id, 'risk_min', parseFloat(e.target.value) || 0)}
                                className="w-20 px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-yellow-500"
                                step="0.01"
                              />
                            </td>
                            <td className="px-4 py-3 text-sm">
                              <input
                                type="number"
                                value={kpi.risk_max}
                                onChange={(e) => updateReferenceRange(kpi.range_id, 'risk_max', parseFloat(e.target.value) || 0)}
                                className="w-20 px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-yellow-500"
                                step="0.01"
                              />
                            </td>
                            <td className="px-4 py-3 text-sm">
                              <input
                                type="number"
                                value={kpi.healthy_min}
                                onChange={(e) => updateReferenceRange(kpi.range_id, 'healthy_min', parseFloat(e.target.value) || 0)}
                                className="w-20 px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
                                step="0.01"
                              />
                            </td>
                            <td className="px-4 py-3 text-sm">
                              <input
                                type="number"
                                value={kpi.healthy_max}
                                onChange={(e) => updateReferenceRange(kpi.range_id, 'healthy_max', parseFloat(e.target.value) || 0)}
                                className="w-20 px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-green-500"
                                step="0.01"
                              />
                            </td>
                            <td className="px-4 py-3 text-sm">
                              <select
                                value={kpi.higher_is_better ? 'true' : 'false'}
                                onChange={(e) => updateReferenceRange(kpi.range_id, 'higher_is_better', e.target.value === 'true')}
                                className="px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                              >
                                <option value="true">Yes</option>
                                <option value="false">No</option>
                              </select>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={9} className="px-4 py-8 text-center text-gray-500">
                            Click "Load KPI Reference Ranges" to view and edit calculation details
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                
                <div className="text-center space-x-4">
                  <button 
                    onClick={() => fetchKpiReferenceRanges()}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                  >
                    <Calculator className="h-4 w-4 mr-2" />
                    Load KPI Reference Ranges
                  </button>
                  {kpiReferenceRanges.length > 0 && (
                    <button 
                      onClick={saveKpiReferenceRanges}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      <Database className="h-4 w-4 mr-2" />
                      Save Changes
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Upload Configuration */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h4 className="font-semibold text-gray-900 mb-4">Upload Configuration</h4>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-gray-900">Upload Mode</p>
                    <p className="text-xs text-gray-500">Account-level KPI uploads</p>
                  </div>
                  <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full">
                    Account Rollup
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-gray-900">File Types</p>
                    <p className="text-xs text-gray-500">Excel (.xlsx, .xls) and CSV files</p>
                  </div>
                  <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full">
                    Supported
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'reports' && <PlaybookReports customerId={session.customer_id} />}
        </main>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} />
      )}
    </div>
  );
};

export default CSPlatform;
