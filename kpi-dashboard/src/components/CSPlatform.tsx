import React, { useState, useRef, useEffect, useMemo } from 'react';
import { 
  Upload, 
  Database, 
  TrendingUp,
  TrendingDown,
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
import PlaybookAutomationSettings from './PlaybookAutomationSettings';
import OpenAIKeySettings from './OpenAIKeySettings';
import GovernanceSettings from './GovernanceSettings';
import Playbooks from './Playbooks';
import PlaybookReports from './PlaybookReports';
import AccountHealthHeatmap from './AccountHealthHeatmap';

interface Product {
  product_id: number;
  account_id: number;
  product_name: string;
  product_sku?: string;
  product_type?: string;
  revenue?: number;
  status: string;
  created_at?: string;
  updated_at?: string;
}

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
  product_id?: number | null; // Explicitly nullable to prevent type coercion issues
  aggregation_type?: string;
  product_name?: string | null;
}

interface Account {
  account_id: number;
  account_name: string;
  revenue: number;
  industry: string;
  region: string;
  account_status: string;
  health_score: number;
  external_account_id?: string;
  profile_metadata?: {
    account_tier?: string;
    assigned_csm?: string;
    csm_manager?: string;
    products_used?: string;
    engagement?: {
      lifecycle_stage?: string;
      onboarding_status?: string;
    };
    champions?: Array<{
      primary_champion_name?: string;
      champion_title?: string;
      champion_email?: string;
      champion_status?: string;
    }>;
  };
  products_used?: string[];
  primary_champion_name?: string;
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
  const [accountSnapshot, setAccountSnapshot] = useState<any | null>(null);
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);
  
  // Account Health Dashboard tab state
  const [accountHealthTab, setAccountHealthTab] = useState<'list' | 'finviz'>(() => {
    // Check if we're in local development
    const isLocalDev = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1' ||
                       window.location.hostname === '' ||
                       process.env.NODE_ENV === 'development';
    
    // Allow Finviz tab if local dev OR if explicitly enabled via env var
    const canUseFinviz = isLocalDev || process.env.REACT_APP_ENABLE_FINVIZ === 'true';
    
    // Check localStorage for saved preference
    const saved = localStorage.getItem('account_health_tab');
    if (saved === 'finviz' && canUseFinviz) {
      return 'finviz';
    }
    
    // Default to list view
    return 'list';
  });
  
  // Settings UI preferences (persisted in localStorage)
  const [kpiHealthSectionOpen, setKpiHealthSectionOpen] = useState(() => {
    const saved = localStorage.getItem('settings_kpi_health_section_open');
    return saved === 'true';
  });
  
  const toggleKpiHealthSection = () => {
    const newState = !kpiHealthSectionOpen;
    setKpiHealthSectionOpen(newState);
    localStorage.setItem('settings_kpi_health_section_open', String(newState));
  };

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
  
  // Multi-product state
  const [products, setProducts] = useState<{[accountId: number]: Product[]}>({});
  const [selectedProduct, setSelectedProduct] = useState<{accountId: number, productId: number | null} | null>(null);
  const [viewMode, setViewMode] = useState<'account' | 'product'>('account');
  
  // Cleanup state variables
  const [cleanupDirectory, setCleanupDirectory] = useState('');
  const [isCleanupRunning, setIsCleanupRunning] = useState(false);
  const [cleanupResult, setCleanupResult] = useState<any>(null);
  const [cleanupError, setCleanupError] = useState('');
  
  // Master file upload state variables
  const [categoryWeights, setCategoryWeights] = useState<{[key: string]: number}>({});
  const [masterFileError, setMasterFileError] = useState('');
  const [masterFileSuccess, setMasterFileSuccess] = useState<any>(null);
  const [isExporting, setIsExporting] = useState(false);
  const masterFileInputRef = useRef<HTMLInputElement>(null);
  const [profileUploading, setProfileUploading] = useState(false);
  const [profileErrors, setProfileErrors] = useState<any[] | null>(null);
  
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
  
  // Customer Performance Summary state
  const [perfSummary, setPerfSummary] = useState<{
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
  } | null>(null);

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
        credentials: 'include', // Include session cookies for authentication
        headers: {
          'X-Customer-ID': session.customer_id.toString(), // Keep for backward compatibility
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Accounts API response:', data); // Debug log
        
        // Handle both old format (direct array) and new format ({accounts: []})
        const accountsArray = Array.isArray(data) ? data : (data.accounts || []);
        console.log('Accounts array:', accountsArray); // Debug log
        
        // Transform backend data to match our interface
        const transformedAccounts: Account[] = accountsArray.map((acc: any) => ({
          account_id: acc.account_id,
          account_name: acc.account_name,
          revenue: acc.revenue || 0,
          industry: acc.industry || 'Unknown',
          region: acc.region || 'Unknown',
          account_status: acc.account_status || 'active',
          health_score: acc.health_score || Math.floor(Math.random() * 60) + 40, // Fallback score
          external_account_id: acc.external_account_id,
          profile_metadata: acc.profile_metadata,
          products_used: acc.products_used || [],
          primary_champion_name: acc.primary_champion_name,
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
          credentials: 'include',
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
          product_id: kpi.product_id,
          aggregation_type: kpi.aggregation_type,
          product_name: kpi.product_name,
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

  // Deduplicate KPIs by parameter name - keep only the latest KPI per parameter per account
  const deduplicatedKpiData = useMemo(() => {
    const kpiMap = new Map<string, KPI>();
    
    // Sort by kpi_id descending to keep the latest (highest ID) for each parameter
    const sortedKPIs = [...kpiData].sort((a, b) => (b.kpi_id || 0) - (a.kpi_id || 0));
    
    for (const kpi of sortedKPIs) {
      // Create a unique key: account_id + kpi_parameter + (product_id or 'account')
      const productKey = kpi.product_id ? `product_${kpi.product_id}` : 'account';
      const key = `${kpi.account_id}_${kpi.kpi_parameter}_${productKey}`;
      
      // Only add if we haven't seen this combination before
      if (!kpiMap.has(key)) {
        kpiMap.set(key, kpi);
      }
    }
    
    return Array.from(kpiMap.values());
  }, [kpiData]);

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
      fetchPerformanceSummary();
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

  // Fetch account snapshot for more context
  const fetchAccountSnapshot = async (accountId: number) => {
    if (!session?.customer_id) return;
    
    setLoadingSnapshot(true);
    try {
      const response = await fetch(`/api/account-snapshots/latest?account_id=${accountId}`, {
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.status === 'success' && data.snapshot) {
          setAccountSnapshot(data.snapshot);
        } else {
          // No snapshot exists, create one automatically
          console.log('No snapshot found, creating one automatically...');
          const createResponse = await fetch('/api/account-snapshots/create', {
            method: 'POST',
            credentials: 'include',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              account_id: accountId,
              snapshot_type: 'manual',
              reason: 'User clicked account in Health tab'
            }),
          });
          
          if (createResponse.ok) {
            const createData = await createResponse.json();
            if (createData.snapshots && createData.snapshots.length > 0) {
              // Fetch the newly created snapshot
              const newSnapshotResponse = await fetch(`/api/account-snapshots/latest?account_id=${accountId}`, {
                credentials: 'include',
              });
              if (newSnapshotResponse.ok) {
                const newSnapshotData = await newSnapshotResponse.json();
                if (newSnapshotData.status === 'success' && newSnapshotData.snapshot) {
                  setAccountSnapshot(newSnapshotData.snapshot);
                }
              }
            }
          }
        }
      }
    } catch (err) {
      console.error('Error fetching account snapshot:', err);
    } finally {
      setLoadingSnapshot(false);
    }
  };

  // Fetch products for all accounts
  const fetchProducts = async (accountId: number) => {
    if (!session?.customer_id) return;
    
    try {
      const response = await fetch(`/api/accounts/${accountId}/products`, {
        credentials: 'include',
        headers: {
          'X-Customer-ID': session.customer_id.toString(),
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setProducts(prev => ({
          ...prev,
          [accountId]: data
        }));
      }
    } catch (err) {
      console.error('Error fetching products:', err);
    }
  };

  // Fetch products when accounts are loaded
  useEffect(() => {
    if (accounts.length > 0 && session?.customer_id) {
      accounts.forEach(account => {
        fetchProducts(account.account_id);
      });
    }
  }, [accounts, session?.customer_id]);

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
        credentials: 'include',
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

  const fetchPerformanceSummary = async () => {
    try {
      const response = await fetch('/api/customer-performance/summary', {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Performance summary response:', data); // Debug log
        if (data.status === 'success') {
          setPerfSummary(data);
        } else {
          console.error('Performance summary returned non-success status:', data);
        }
      } else {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        console.error('Performance summary API error:', response.status, errorData);
      }
    } catch (error) {
      console.error('Error fetching performance summary:', error);
    }
  };
  
  const fetchKpiReferenceRanges = async () => {
    try {
      const cacheBuster = `?_=${Date.now()}`;
      const response = await fetch(`/api/kpi-reference-ranges${cacheBuster}`, {
        method: 'GET',
        credentials: 'include', // Include session cookies for authentication
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache',
        },
      });

      if (response.ok) {
        const data = await response.json();
        console.log('KPI Reference Ranges response:', data); // Debug log
        if (data.ranges) {
          setKpiReferenceRanges(data.ranges);
          console.log('KPI reference ranges loaded from database:', data.ranges.length, 'KPIs');
        } else {
          console.error('Failed to load reference ranges:', data.error);
          setError('Failed to load KPI reference ranges');
        }
      } else {
        console.error('Failed to fetch reference ranges:', response.status);
        setError(`Failed to fetch KPI reference ranges: ${response.status}`);
      }
    } catch (error) {
      console.error('Error fetching KPI reference ranges:', error);
      setError('Error fetching KPI reference ranges');
    }
  };

  const saveKpiReferenceRanges = async () => {
    try {
      const response = await fetch('/api/kpi-reference-ranges/bulk-update', {
        method: 'POST',
        credentials: 'include', // Include session cookies for authentication
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
        // Treat either success flag or presence of updated_count/status success as success
        if (data.success === true || data.status === 'success' || typeof data.updated_count === 'number') {
          console.log('KPI reference ranges saved successfully:', data.updated_count, 'ranges updated');
          // Refresh the data
          fetchKpiReferenceRanges();
        } else {
          console.error('Failed to save reference ranges:', data.error || data.message);
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
        credentials: 'include',
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
        credentials: 'include',
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
        credentials: 'include',
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
        credentials: 'include',
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

  const getHealthStatus = (score: number | null | undefined): { status: string; color: string } => {
    if (score === null || score === undefined) {
      return { status: 'Unknown', color: 'gray' };
    }
    if (score >= 75) {
      return { status: 'Healthy', color: 'green' };
    } else if (score >= 50) {
      return { status: 'At Risk', color: 'yellow' };
    } else {
      return { status: 'Critical', color: 'red' };
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
          credentials: 'include',
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
                    onClick={async () => {
                      if (selectedAccount?.account_id === account.account_id) {
                        setSelectedAccount(null);
                        setAccountSnapshot(null);
                      } else {
                        setSelectedAccount(account);
                        // Fetch account snapshot for more context
                        await fetchAccountSnapshot(account.account_id);
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

                  {/* Expandable Account Details with Snapshot Context */}
                  {selectedAccount?.account_id === account.account_id && (
                    <div className="border-t border-gray-200 bg-gray-50 p-3">
                      {/* Account Snapshot Context Section */}
                      {accountSnapshot && (
                        <div className="mb-4 p-4 bg-white rounded-lg border border-blue-200 shadow-sm">
                          <div className="flex items-center justify-between mb-3">
                            <h6 className="text-sm font-semibold text-blue-900">
                              📸 Account Snapshot Context
                            </h6>
                            <span className="text-xs text-gray-500">
                              {new Date(accountSnapshot.snapshot_timestamp).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                            {accountSnapshot.health_score_trend && (
                              <div>
                                <p className="text-gray-500 mb-1">Health Trend</p>
                                <p className={`font-medium ${
                                  accountSnapshot.health_score_trend === 'improving' ? 'text-green-600' :
                                  accountSnapshot.health_score_trend === 'declining' ? 'text-red-600' :
                                  'text-gray-600'
                                }`}>
                                  {accountSnapshot.health_score_trend === 'improving' ? '↑ Improving' :
                                   accountSnapshot.health_score_trend === 'declining' ? '↓ Declining' :
                                   '→ Stable'}
                                </p>
                              </div>
                            )}
                            {accountSnapshot.revenue_change_percent !== null && accountSnapshot.revenue_change_percent !== undefined && (
                              <div>
                                <p className="text-gray-500 mb-1">Revenue Change</p>
                                <p className={`font-medium ${
                                  accountSnapshot.revenue_change_percent > 0 ? 'text-green-600' : 'text-red-600'
                                }`}>
                                  {accountSnapshot.revenue_change_percent > 0 ? '↑' : '↓'} {Math.abs(accountSnapshot.revenue_change_percent).toFixed(1)}%
                                </p>
                              </div>
                            )}
                            {accountSnapshot.playbooks_running_count !== undefined && (
                              <div>
                                <p className="text-gray-500 mb-1">Playbooks</p>
                                <p className="font-medium text-gray-900">
                                  {accountSnapshot.playbooks_running_count} running, {accountSnapshot.playbooks_completed_count} completed
                                </p>
                              </div>
                            )}
                            {accountSnapshot.critical_kpis_count !== undefined && accountSnapshot.total_kpis !== undefined && (
                              <div>
                                <p className="text-gray-500 mb-1">KPI Status</p>
                                <p className="font-medium text-gray-900">
                                  {accountSnapshot.critical_kpis_count}/{accountSnapshot.total_kpis} critical
                                </p>
                              </div>
                            )}
                          </div>
                          {accountSnapshot.recent_csm_note_ids && accountSnapshot.recent_csm_note_ids.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-gray-200">
                              <p className="text-xs text-gray-500 mb-1">Recent CSM Activity</p>
                              <p className="text-xs text-gray-700">
                                {accountSnapshot.recent_csm_note_ids.length} recent note(s) available
                              </p>
                            </div>
                          )}
                          {accountSnapshot.recent_playbook_report_ids && accountSnapshot.recent_playbook_report_ids.length > 0 && (
                            <div className="mt-2">
                              <p className="text-xs text-gray-500 mb-1">Recent Playbook Reports</p>
                              <p className="text-xs text-gray-700">
                                {accountSnapshot.recent_playbook_report_ids.length} recent report(s) available
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                      {loadingSnapshot && (
                        <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                          <p className="text-xs text-blue-700">Loading account snapshot context...</p>
                        </div>
                      )}
                      <div className="mb-3">
                        <h6 className="text-sm font-semibold text-gray-900 mb-1">
                          KPIs for {account.account_name}
                        </h6>
                        <p className="text-xs text-gray-600">
                          {(() => {
                            const allAccountKPIs = deduplicatedKpiData.filter(kpi => kpi.account_id === account.account_id);
                            const profileProducts = account.profile_metadata?.products_used;
                            const accountProductsList = profileProducts && profileProducts.trim() 
                              ? profileProducts.split(',').map(p => p.trim()).filter(p => p)
                              : (account.products_used || []);
                            const accountProductKPIs = deduplicatedKpiData.filter(kpi => 
                              kpi.account_id === account.account_id && kpi.product_id !== null && kpi.product_id !== undefined
                            );
                            const hasProducts = accountProductsList.length > 0 || accountProductKPIs.length > 0;
                            
                            if (!hasProducts) {
                              return `${allAccountKPIs.filter(kpi => !kpi.product_id).length} KPIs`;
                            }
                            
                            const productKPIs = allAccountKPIs.filter(kpi => kpi.product_id !== null && kpi.product_id !== undefined);
                            const productLevelParameters = new Set(productKPIs.map(kpi => kpi.kpi_parameter));
                            const accountLevelKPIs = allAccountKPIs.filter(kpi => 
                              (kpi.product_id === null || kpi.product_id === undefined) && !productLevelParameters.has(kpi.kpi_parameter)
                            );
                            return `${productKPIs.length + accountLevelKPIs.length} KPIs`;
                          })()}
                        </p>
                      </div>
                      
                                              <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-gray-200 bg-white rounded text-xs">
                            <thead className="bg-gray-100">
                              <tr>
                                <th className="px-2 py-1 text-left text-xs font-medium text-gray-500">Product</th>
                                <th className="px-2 py-1 text-left text-xs font-medium text-gray-500">Category</th>
                                <th className="px-2 py-1 text-left text-xs font-medium text-gray-500">KPI Parameter</th>
                                <th className="px-2 py-1 text-left text-xs font-medium text-gray-500">Data</th>
                                <th className="px-2 py-1 text-left text-xs font-medium text-gray-500">Weight</th>
                                <th className="px-2 py-1 text-left text-xs font-medium text-gray-500">Health Status</th>
                              </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                              {(() => {
                                // Get all KPIs for this account
                                const allAccountKPIs = deduplicatedKpiData.filter(kpi => kpi.account_id === account.account_id);
                                
                                // Check if account has products (from profile metadata, products_used array, or product-level KPIs)
                                const profileProducts = account.profile_metadata?.products_used;
                                const accountProductsList = profileProducts && profileProducts.trim() 
                                  ? profileProducts.split(',').map(p => p.trim()).filter(p => p)
                                  : (account.products_used || []);
                                const accountProductKPIs = allAccountKPIs.filter(kpi => 
                                  kpi.product_id !== null && kpi.product_id !== undefined
                                );
                                const hasProducts = accountProductsList.length > 0 || accountProductKPIs.length > 0;
                                
                                if (!hasProducts) {
                                  // Account has no products - show only account-level KPIs
                                  return allAccountKPIs.filter(kpi => kpi.product_id === null || kpi.product_id === undefined);
                                }
                                
                                // Account has products (1, 2, 3, or more) - show uniform format
                                // Get all product-level KPIs (for any number of products)
                                const productKPIs = allAccountKPIs.filter(kpi => 
                                  kpi.product_id !== null && kpi.product_id !== undefined
                                );
                                
                                // Get account-level KPIs
                                // For parameters that have product-level KPIs, only show account-level if:
                                // 1. It's an aggregate (aggregation_type is set), OR
                                // 2. There are NO product-level KPIs for that parameter
                                const productLevelParameters = new Set(
                                  productKPIs.map(kpi => kpi.kpi_parameter).filter(p => p)
                                );
                                
                                const accountLevelKPIs = allAccountKPIs.filter(kpi => {
                                  if (kpi.product_id !== null && kpi.product_id !== undefined) return false; // Skip product-level KPIs here
                                  
                                  // If this parameter has product-level KPIs, only show if it's an aggregate
                                  if (productLevelParameters.has(kpi.kpi_parameter)) {
                                    return kpi.aggregation_type !== null && kpi.aggregation_type !== undefined;
                                  }
                                  
                                  // Otherwise, show all account-level KPIs
                                  return true;
                                });
                                
                                // Combine: product-level KPIs first, then account-level KPIs
                                // This ensures uniform display for accounts with 1, 2, 3, or more products
                                return [...productKPIs, ...accountLevelKPIs];
                              })().map((kpi) => (
                                  <tr key={kpi.kpi_id} className="hover:bg-gray-50">
                                    <td className="px-2 py-1 whitespace-nowrap text-xs text-gray-900">
                                      {kpi.product_name ? (
                                        <span className="font-medium text-blue-600">{kpi.product_name}</span>
                                      ) : (
                                        <span className="text-gray-500 italic">Account Level</span>
                                      )}
                                    </td>
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
                          {deduplicatedKpiData.filter(kpi => kpi.account_id === account.account_id).length === 0 && (
                            <div className="text-center py-4 text-gray-500">
                              <p className="text-xs">No KPIs found for this account.</p>
                              <p className="text-xs mt-1">Upload a KPI file with this account name.</p>
                            </div>
                          )}
                          {deduplicatedKpiData.filter(kpi => kpi.account_id === account.account_id).length > 5 && (
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

  const ProductHealthDashboard = () => {
    const [selectedProduct, setSelectedProduct] = useState<string | null>(null);
    const [productFilter, setProductFilter] = useState<string>('');
    const [sortColumn, setSortColumn] = useState<string | null>(null);
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

    // Helper function to normalize product names for consistent grouping
    // Normalizes to lowercase and trims whitespace for matching
    const normalizeProductName = (name: string): string => {
      return name.trim().toLowerCase();
    };
    
    // Helper function to calculate simple similarity (for fuzzy matching typos)
    // Returns a value between 0 and 1, where 1 is an exact match
    const similarity = (str1: string, str2: string): number => {
      const s1 = normalizeProductName(str1);
      const s2 = normalizeProductName(str2);
      if (s1 === s2) return 1.0;
      
      // Simple Levenshtein-like check for single character differences
      // Check if one string is contained in the other (for typos like "platfom" vs "platform")
      if (s1.length > 3 && s2.length > 3) {
        const longer = s1.length > s2.length ? s1 : s2;
        const shorter = s1.length > s2.length ? s2 : s1;
        if (longer.includes(shorter) || shorter.includes(longer)) {
          // If one contains the other and lengths are close (difference <= 2 chars), likely a typo
          if (Math.abs(longer.length - shorter.length) <= 2) {
            return 0.95; // High similarity for likely typos
          }
        }
      }
      
      // Check character overlap
      let matches = 0;
      const minLen = Math.min(s1.length, s2.length);
      for (let i = 0; i < minLen; i++) {
        if (s1[i] === s2[i]) matches++;
      }
      return matches / Math.max(s1.length, s2.length);
    };
    
    // Helper function to find existing group key (case-insensitive, handles typos/variations)
    const findGroupKey = (productName: string, groups: { [key: string]: any }): string | null => {
      const normalized = normalizeProductName(productName);
      // First try exact match
      for (const key in groups) {
        if (normalizeProductName(key) === normalized) {
          return key;
        }
      }
      // Then try fuzzy match for typos (similarity > 0.9)
      for (const key in groups) {
        const sim = similarity(productName, key);
        if (sim > 0.9) {
          return key; // Return the existing key (preserves original spelling)
        }
      }
      return null;
    };
    
    // Group products by product name across all accounts
    // Priority: 1) Customer profile data, 2) Product-level KPIs
    // Products are merged by name (normalized) to avoid duplicates
    const productGroups = useMemo(() => {
      const groups: { [productName: string]: { accounts: Account[], kpis: KPI[], totalRevenue: number, displayName: string } } = {};
      
      // Step 1: Collect products from customer profile data (profile_metadata.products_used)
      accounts.forEach(account => {
        // Priority 1: profile_metadata.products_used (string from customer profile upload)
        const profileProducts = account.profile_metadata?.products_used;
        if (profileProducts && profileProducts.trim()) {
          // Parse comma-separated products
          const productNames = profileProducts.split(',').map(p => p.trim()).filter(p => p);
          productNames.forEach(productName => {
            const normalizedKey = normalizeProductName(productName);
            const existingKey = findGroupKey(productName, groups);
            const groupKey = existingKey || normalizedKey;
            
            if (!groups[groupKey]) {
              groups[groupKey] = {
                accounts: [],
                kpis: [],
                totalRevenue: 0,
                displayName: productName // Use original name for display
              };
            }
            // Add account if not already added
            if (!groups[groupKey].accounts.find(a => a.account_id === account.account_id)) {
              groups[groupKey].accounts.push(account);
              groups[groupKey].totalRevenue += account.revenue || 0;
            }
          });
        } else {
          // Fallback: products_used array (from Product table)
          const productNames = account.products_used || [];
          productNames.forEach(productName => {
            const normalizedKey = normalizeProductName(productName);
            const existingKey = findGroupKey(productName, groups);
            const groupKey = existingKey || normalizedKey;
            
            if (!groups[groupKey]) {
              groups[groupKey] = {
                accounts: [],
                kpis: [],
                totalRevenue: 0,
                displayName: productName // Use original name for display
              };
            }
            // Add account if not already added
            if (!groups[groupKey].accounts.find(a => a.account_id === account.account_id)) {
              groups[groupKey].accounts.push(account);
              groups[groupKey].totalRevenue += account.revenue || 0;
            }
          });
        }
      });
      
      // Step 2: Add product-level KPIs to existing groups (or create new groups if needed)
      // This merges products from KPIs with products from profile data
      const productKPIs = deduplicatedKpiData.filter(kpi => 
        kpi.product_id !== null && 
        kpi.product_id !== undefined && 
        kpi.product_name && 
        kpi.product_name.trim() !== ''
      );
      
      console.log(`DEBUG: Found ${productKPIs.length} product-level KPIs`);
      
      productKPIs.forEach(kpi => {
        const productName = kpi.product_name!.trim();
        const normalizedKey = normalizeProductName(productName);
        
        // Try to find existing group by matching normalized names
        let groupKey = findGroupKey(productName, groups);
        
        // If no match found, check all existing groups for similar names
        if (!groupKey) {
          for (const key in groups) {
            const keyNormalized = normalizeProductName(key);
            if (keyNormalized === normalizedKey) {
              groupKey = key;
              break;
            }
          }
        }
        
        // If still no match, use normalized key (create new group)
        if (!groupKey) {
          groupKey = normalizedKey;
        }
        
        if (!groups[groupKey]) {
          groups[groupKey] = {
            accounts: [],
            kpis: [],
            totalRevenue: 0,
            displayName: productName // Use original name for display
          };
        }
        
        // Add KPI if not already added
        if (!groups[groupKey].kpis.find(k => k.kpi_id === kpi.kpi_id)) {
          groups[groupKey].kpis.push(kpi);
        }
        
        // Add account if not already added (in case account wasn't in profile data)
        const account = accounts.find(a => a.account_id === kpi.account_id);
        if (account && !groups[groupKey].accounts.find(a => a.account_id === account.account_id)) {
          groups[groupKey].accounts.push(account);
          groups[groupKey].totalRevenue += account.revenue || 0;
        }
      });
      
      console.log(`DEBUG: Product groups after adding KPIs:`, Object.keys(groups).map(key => ({
        key,
        displayName: groups[key].displayName,
        kpiCount: groups[key].kpis.length,
        accountCount: groups[key].accounts.length
      })));
      
      return groups;
    }, [kpiData, accounts]);

    const filteredProducts = useMemo(() => {
      if (!productFilter) return Object.keys(productGroups);
      return Object.keys(productGroups).filter(name => 
        name.toLowerCase().includes(productFilter.toLowerCase())
      );
    }, [productGroups, productFilter]);

    // Calculate average health score for a product based on its KPIs
    // Priority: 1) Product-level KPIs (KPIs with product_id set)
    //           2) Account-level "Product Usage KPI" category KPIs from accounts using that product
    //              BUT only if the account has only one product (account-level = product-level in that case)
    // Note: productName is the normalized key from productGroups
    const getProductHealthScore = (productName: string): number => {
      // productName is already a normalized key from productGroups
      const group = productGroups[productName];
      if (!group) return 0;
      
      let total = 0;
      let count = 0;
      
      // NEW LOGIC: Always use product-level KPIs if account has ANY products
      // Only fall back to account-level KPIs if account has NO products
      const normalizedProductName = normalizeProductName(productName);
      
      // Step 1: Try to find product-level KPIs for this specific product
      const productLevelKPIs = deduplicatedKpiData.filter(kpi => {
        if (!kpi.product_id || !kpi.product_name) return false;
        const kpiProductName = normalizeProductName(kpi.product_name.trim());
        return kpiProductName === normalizedProductName;
      });
      
      if (productLevelKPIs.length > 0) {
        // Use product-level KPIs (even if account has only one product)
        productLevelKPIs.forEach(kpi => {
          const hs = kpiHealthStatuses[kpi.kpi_id];
          if (hs && typeof hs.health_score === 'number') {
            total += hs.health_score;
            count += 1;
          }
        });
      } else {
        // Step 2: Fallback to account-level KPIs ONLY if account has NO products
        group.accounts.forEach(account => {
          // Get all products for this account
          const profileProducts = account.profile_metadata?.products_used;
          const accountProductsList = profileProducts && profileProducts.trim() 
            ? profileProducts.split(',').map(p => p.trim()).filter(p => p)
            : (account.products_used || []);
          
          // Check if account has any product-level KPIs
          const accountProductKPIs = deduplicatedKpiData.filter(kpi => 
            kpi.account_id === account.account_id && kpi.product_id
          );
          const hasProducts = accountProductsList.length > 0 || accountProductKPIs.length > 0;
          
          // Only use account-level KPIs if account has NO products
          if (!hasProducts) {
            // Account has no products - use account-level KPIs
            const accountKPIs = deduplicatedKpiData.filter(kpi => 
              kpi.account_id === account.account_id && 
              !kpi.product_id // Account-level only
            );
            
            // Use product-relevant categories
            const productRelevantKPIs = accountKPIs.filter(kpi => 
              kpi.category === 'Adoption & Engagement' || 
              kpi.category === 'Product Value' ||
              kpi.category === 'Product Usage KPI'
            );
            
            const kpisToUse = productRelevantKPIs.length > 0 ? productRelevantKPIs : accountKPIs;
            
            kpisToUse.forEach(kpi => {
              const hs = kpiHealthStatuses[kpi.kpi_id];
              if (hs && typeof hs.health_score === 'number') {
                total += hs.health_score;
                count += 1;
              }
            });
          }
          // If account has products but no product-level KPIs yet, skip (will be created later)
        });
      }
      
      if (count === 0) return 0;
      return Math.round(total / count);
    };

    // Handle column sorting
    const handleSort = (column: string) => {
      if (sortColumn === column) {
        // Toggle direction if same column
        setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
      } else {
        // New column, default to ascending
        setSortColumn(column);
        setSortDirection('asc');
      }
    };

    // Sort KPIs based on selected column and direction
    const getSortedKPIs = (kpis: KPI[]): KPI[] => {
      if (!sortColumn) return kpis;

      const sorted = [...kpis].sort((a, b) => {
        let aValue: any;
        let bValue: any;

        switch (sortColumn) {
          case 'account':
            aValue = accounts.find(acc => acc.account_id === a.account_id)?.account_name || '';
            bValue = accounts.find(acc => acc.account_id === b.account_id)?.account_name || '';
            break;
          case 'category':
            aValue = a.category || '';
            bValue = b.category || '';
            break;
          case 'kpi_parameter':
            aValue = a.kpi_parameter || '';
            bValue = b.kpi_parameter || '';
            break;
          case 'data':
            // Try to parse as number, fallback to string
            aValue = parseFloat(a.data) || a.data || '';
            bValue = parseFloat(b.data) || b.data || '';
            break;
          case 'health_status':
            const aHealth = kpiHealthStatuses[a.kpi_id]?.health_status || '';
            const bHealth = kpiHealthStatuses[b.kpi_id]?.health_status || '';
            // Sort by health status priority: green > yellow > red > unknown
            const healthPriority: { [key: string]: number } = {
              'High': 3,
              'Medium': 2,
              'Low': 1,
              '': 0
            };
            aValue = healthPriority[aHealth] ?? 0;
            bValue = healthPriority[bHealth] ?? 0;
            break;
          case 'impact_level':
            aValue = a.impact_level || '';
            bValue = b.impact_level || '';
            break;
          default:
            return 0;
        }

        // Compare values
        if (typeof aValue === 'number' && typeof bValue === 'number') {
          return aValue - bValue;
        }
        const aStr = String(aValue).toLowerCase();
        const bStr = String(bValue).toLowerCase();
        if (aStr < bStr) return -1;
        if (aStr > bStr) return 1;
        return 0;
      });

      return sortDirection === 'asc' ? sorted : sorted.reverse();
    };

    // Render sort icon
    const renderSortIcon = (column: string) => {
      if (sortColumn !== column) {
        return <span className="text-gray-400 ml-1">↕</span>;
      }
      return sortDirection === 'asc' ? (
        <ArrowUp className="h-3 w-3 ml-1 inline text-blue-600" />
      ) : (
        <ArrowDown className="h-3 w-3 ml-1 inline text-blue-600" />
      );
    };

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Product Health Dashboard</h2>
          <div className="flex items-center space-x-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search products..."
                value={productFilter}
                onChange={(e) => setProductFilter(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {isLoading ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-center justify-center">
              <RefreshCw className="h-8 w-8 text-blue-600 animate-spin mr-3" />
              <span className="text-gray-600">Loading products...</span>
            </div>
          </div>
        ) : filteredProducts.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <div className="text-center py-8 text-gray-500">
              <Target className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p>No products found. {productFilter ? 'Try a different search term.' : 'Products will appear here when product-level KPIs are available.'}</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredProducts.map((productName) => {
              const group = productGroups[productName];
              const healthScore = getProductHealthScore(productName);
              const isExpanded = selectedProduct === productName;
              const displayName = group?.displayName || productName;
              
              // Count only product-level KPIs for this specific product
              // First try group.kpis (already matched), then search all KPI data as fallback
              let productLevelKPICount = group.kpis.filter(kpi => 
                kpi.product_id !== null && 
                kpi.product_id !== undefined && 
                kpi.product_name
              ).length;
              
              // Always search all KPI data to find matching product KPIs (even if group.kpis is empty)
              // This ensures we find product-level KPIs for accounts with products
              const allProductKPIs = deduplicatedKpiData.filter(kpi => {
                if (!kpi.product_id || kpi.product_id === null || kpi.product_id === undefined || !kpi.product_name) return false;
                // Match by normalized product name
                const kpiProductName = normalizeProductName(kpi.product_name.trim());
                const targetProductName = normalizeProductName(productName);
                const displayNameNormalized = normalizeProductName(displayName);
                return kpiProductName === targetProductName || kpiProductName === displayNameNormalized;
              });
              
              // Use the count from all product KPIs (more accurate)
              if (allProductKPIs.length > 0) {
                productLevelKPICount = allProductKPIs.length;
              }
              
              return (
                <div key={productName} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                  <button
                    onClick={() => setSelectedProduct(isExpanded ? null : productName)}
                    className={`w-full p-6 text-left transition-all hover:bg-gray-50 ${
                      isExpanded ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <Target className="h-5 w-5 text-blue-600" />
                          <h3 className="text-lg font-semibold text-gray-900">{displayName}</h3>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            healthScore >= 80 ? 'bg-green-100 text-green-800' :
                            healthScore >= 70 ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            Health: {healthScore}/100
                          </span>
                        </div>
                        <div className="grid grid-cols-3 gap-4 mt-3 text-sm text-gray-600">
                          <div>
                            <span className="font-medium">Accounts:</span> {group.accounts.length}
                          </div>
                          <div>
                            <span className="font-medium">KPIs:</span> {productLevelKPICount}
                          </div>
                          <div>
                            <span className="font-medium">Total Revenue:</span> ${(group.totalRevenue / 1000000).toFixed(1)}M
                          </div>
                        </div>
                        <div className="mt-3">
                          <p className="text-xs text-gray-500">
                            Accounts: {group.accounts.map(a => a.account_name).join(', ')}
                          </p>
                        </div>
                      </div>
                      <div className="ml-4">
                        <span className="text-gray-400 text-sm">
                          {isExpanded ? '▼' : '▶'}
                        </span>
                      </div>
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="border-t border-gray-200 bg-gray-50 p-6">
                      <div className="mb-4">
                        <h4 className="text-md font-semibold text-gray-900 mb-2">
                          KPIs for {displayName}
                        </h4>
                        <p className="text-sm text-gray-600">
                          Showing {productLevelKPICount} Product-Level KPIs across {group.accounts.length} accounts
                        </p>
                      </div>

                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200 bg-white rounded-lg">
                          <thead className="bg-gray-100">
                            <tr>
                              <th 
                                className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-200 select-none"
                                onClick={() => handleSort('account')}
                              >
                                Account{renderSortIcon('account')}
                              </th>
                              <th 
                                className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-200 select-none"
                                onClick={() => handleSort('category')}
                              >
                                Category{renderSortIcon('category')}
                              </th>
                              <th 
                                className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-200 select-none"
                                onClick={() => handleSort('kpi_parameter')}
                              >
                                KPI Parameter{renderSortIcon('kpi_parameter')}
                              </th>
                              <th 
                                className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-200 select-none"
                                onClick={() => handleSort('data')}
                              >
                                Data{renderSortIcon('data')}
                              </th>
                              <th 
                                className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-200 select-none"
                                onClick={() => handleSort('health_status')}
                              >
                                Health Status{renderSortIcon('health_status')}
                              </th>
                              <th 
                                className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-200 select-none"
                                onClick={() => handleSort('impact_level')}
                              >
                                Impact Level{renderSortIcon('impact_level')}
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {getSortedKPIs((() => {
                              // Always search all KPI data for matching product KPIs
                              // This ensures we find product-level KPIs even if group.kpis is empty
                              const productKPIs = deduplicatedKpiData.filter(kpi => {
                                if (!kpi.product_id || kpi.product_id === null || kpi.product_id === undefined || !kpi.product_name) return false;
                                const kpiProductName = normalizeProductName(kpi.product_name.trim());
                                const targetProductName = normalizeProductName(productName);
                                const displayNameNormalized = normalizeProductName(displayName);
                                return kpiProductName === targetProductName || kpiProductName === displayNameNormalized;
                              });
                              
                              // If we found product-level KPIs, use them
                              if (productKPIs.length > 0) {
                                return productKPIs;
                              }
                              
                              // Fallback: If no product-level KPIs, check if account has products
                              // If account has products but no product KPIs, return empty (will be created)
                              // Only show account-level KPIs if account has NO products
                              const accountsWithThisProduct = group.accounts;
                              const fallbackKPIs: KPI[] = [];
                              
                              accountsWithThisProduct.forEach(account => {
                                const profileProducts = account.profile_metadata?.products_used;
                                const accountProductsList = profileProducts && profileProducts.trim() 
                                  ? profileProducts.split(',').map(p => p.trim()).filter(p => p)
                                  : (account.products_used || []);
                                
                                const accountProductKPIs = deduplicatedKpiData.filter(kpi => 
                                  kpi.account_id === account.account_id && kpi.product_id
                                );
                                const hasProducts = accountProductsList.length > 0 || accountProductKPIs.length > 0;
                                
                                // Only use account-level KPIs if account has NO products
                                if (!hasProducts) {
                                  const accountKPIs = deduplicatedKpiData.filter(kpi => 
                                    kpi.account_id === account.account_id && 
                                    !kpi.product_id
                                  );
                                  fallbackKPIs.push(...accountKPIs);
                                }
                              });
                              
                              return fallbackKPIs;
                            })()).map((kpi) => {
                              const account = accounts.find(a => a.account_id === kpi.account_id);
                              return (
                                <tr key={kpi.kpi_id} className="hover:bg-gray-50">
                                  <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                    <span className="font-medium">{account?.account_name || `Account ${kpi.account_id}`}</span>
                                  </td>
                                  <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{kpi.category}</td>
                                  <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{kpi.kpi_parameter}</td>
                                  <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{kpi.data}</td>
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
                                </tr>
                              );
                            })}
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
    );
  };

  const AccountHealthDashboard = () => {
    // Check if Finviz tab should be available
    const isLocalDev = window.location.hostname === 'localhost' || 
                       window.location.hostname === '127.0.0.1' ||
                       window.location.hostname === '';
    const canUseFinviz = isLocalDev || process.env.REACT_APP_ENABLE_FINVIZ === 'true';

    return (
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
            {/* Tab Navigation */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="border-b border-gray-200">
                <nav className="flex -mb-px">
                  <button
                    onClick={() => {
                      setAccountHealthTab('list');
                      localStorage.setItem('account_health_tab', 'list');
                    }}
                    className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                      accountHealthTab === 'list'
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    List View
                  </button>
                  {canUseFinviz && (
                    <button
                      onClick={() => {
                        setAccountHealthTab('finviz');
                        localStorage.setItem('account_health_tab', 'finviz');
                      }}
                      className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                        accountHealthTab === 'finviz'
                          ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      Finviz Heatmap
                    </button>
                  )}
                </nav>
              </div>

              <div className="p-6">
                {accounts.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Users className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>No accounts found. Upload data to get started.</p>
                  </div>
                ) : accountHealthTab === 'finviz' ? (
              // Finviz-style heatmap view
              <>
                <AccountHealthHeatmap
                  accounts={accounts}
                  selectedAccountId={selectedAccount?.account_id || null}
                  onAccountClick={async (account) => {
                    if (account === null) {
                      setSelectedAccount(null);
                      setAccountSnapshot(null);
                    } else if (selectedAccount?.account_id === account.account_id) {
                      setSelectedAccount(null);
                      setAccountSnapshot(null);
                    } else {
                      setSelectedAccount(account);
                      // Fetch account snapshot for more context
                      await fetchAccountSnapshot(account.account_id);
                    }
                  }}
                />
                
                {/* Show Account Summary Card when account is selected in heatmap view */}
                {selectedAccount && (() => {
                  const account = accounts.find(a => a.account_id === selectedAccount.account_id);
                  if (!account) return null;
                  
                  return (
                    <div className="mt-6 bg-white rounded-lg border-2 border-gray-200 overflow-hidden">
                      {/* Account Snapshot Context Banner */}
                      {accountSnapshot && (
                        <div className="p-3 bg-blue-50 border-b border-blue-200">
                          <div className="flex items-center justify-between mb-2">
                            <h6 className="text-xs font-semibold text-blue-900">
                              📸 Snapshot Context ({new Date(accountSnapshot.snapshot_timestamp).toLocaleDateString()})
                            </h6>
                            <div className="flex items-center space-x-3 text-xs">
                              {accountSnapshot.health_score_trend && (
                                <span className={`${
                                  accountSnapshot.health_score_trend === 'improving' ? 'text-green-600' :
                                  accountSnapshot.health_score_trend === 'declining' ? 'text-red-600' :
                                  'text-gray-600'
                                }`}>
                                  {accountSnapshot.health_score_trend === 'improving' ? '↑ Improving' :
                                   accountSnapshot.health_score_trend === 'declining' ? '↓ Declining' :
                                   '→ Stable'}
                                </span>
                              )}
                              {accountSnapshot.revenue_change_percent !== null && accountSnapshot.revenue_change_percent !== undefined && (
                                <span className={accountSnapshot.revenue_change_percent > 0 ? 'text-green-600' : 'text-red-600'}>
                                  Revenue: {accountSnapshot.revenue_change_percent > 0 ? '↑' : '↓'} {Math.abs(accountSnapshot.revenue_change_percent).toFixed(1)}%
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center space-x-4 text-xs text-gray-600">
                            {accountSnapshot.playbooks_running_count !== undefined && (
                              <span>Playbooks: {accountSnapshot.playbooks_running_count} running</span>
                            )}
                            {accountSnapshot.critical_kpis_count !== undefined && (
                              <span>Critical KPIs: {accountSnapshot.critical_kpis_count}/{accountSnapshot.total_kpis}</span>
                            )}
                          </div>
                        </div>
                      )}
                      {loadingSnapshot && (
                        <div className="p-2 bg-blue-50 border-b border-blue-200">
                          <p className="text-xs text-blue-700">Loading snapshot context...</p>
                        </div>
                      )}
                      {/* Account Header */}
                      <div className="p-4">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-semibold text-gray-900 text-lg">{account.account_name}</h4>
                          <div className="flex items-center space-x-2">
                            <div className={`w-3 h-3 rounded-full ${
                              getHealthStatus(account.health_score).color === 'green' ? 'bg-green-500' :
                              getHealthStatus(account.health_score).color === 'yellow' ? 'bg-yellow-500' :
                              'bg-red-500'
                            }`}></div>
                            <span className="text-sm text-gray-500">
                              ▼
                            </span>
                          </div>
                        </div>
                        
                        {/* Account Details Grid - Matching List View Format */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                          {/* Health Score with Status */}
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Health Score</p>
                            {(() => {
                              const healthStatus = getHealthStatus(account.health_score);
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
                                    {account.health_score?.toFixed(0) || 'N/A'}
                                  </span>
                                </div>
                              );
                            })()}
                          </div>
                          
                          {/* Assigned CSM */}
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Assigned CSM</p>
                            <p className="font-medium text-gray-900">{account.profile_metadata?.assigned_csm || 'N/A'}</p>
                          </div>
                          
                          {/* Revenue */}
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Revenue</p>
                            <p className="font-medium text-gray-900">${(account.revenue / 1000000).toFixed(1)}M</p>
                          </div>
                          
                          {/* View KPIs Link */}
                          <div className="flex items-end">
                            <div className="flex items-center text-xs text-blue-600">
                              <Eye className="h-3 w-3 mr-1" />
                              <span>View KPIs</span>
                            </div>
                          </div>
                          
                          {/* Region */}
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Region</p>
                            <p className="font-medium text-gray-900">{account.region || 'N/A'}</p>
                          </div>
                          
                          {/* CSM Manager */}
                          <div>
                            <p className="text-xs text-gray-500 mb-1">CSM Manager</p>
                            <p className="font-medium text-gray-900">{account.profile_metadata?.csm_manager || 'N/A'}</p>
                          </div>
                          
                          {/* Industry */}
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Industry</p>
                            <p className="font-medium text-gray-900">{account.industry || 'N/A'}</p>
                          </div>
                          
                          {/* Status */}
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Status</p>
                            <p className="font-medium text-gray-900 capitalize">{account.account_status || 'N/A'}</p>
                          </div>
                          
                          {/* Products Used */}
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Products Used</p>
                            <p className="font-medium text-gray-900">
                              {(() => {
                                const profileProducts = account.profile_metadata?.products_used;
                                if (profileProducts && profileProducts.trim()) {
                                  return profileProducts;
                                }
                                if (account.products_used && account.products_used.length > 0) {
                                  return account.products_used.join(', ');
                                }
                                return 'N/A';
                              })()}
                            </p>
                          </div>
                          
                          {/* Lifecycle */}
                          {account.profile_metadata?.engagement?.lifecycle_stage && (
                            <div>
                              <p className="text-xs text-gray-500 mb-1">Lifecycle</p>
                              <p className="font-medium text-gray-900">{account.profile_metadata.engagement.lifecycle_stage}</p>
                            </div>
                          )}
                          
                          {/* Account Tier */}
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Account Tier</p>
                            <p className="font-medium text-gray-900">{account.profile_metadata?.account_tier || 'N/A'}</p>
                          </div>
                          
                          {/* Champion Name */}
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Champion Name</p>
                            <p className="font-medium text-gray-900">
                              {account.primary_champion_name || 
                               account.profile_metadata?.champions?.[0]?.primary_champion_name || 
                               'N/A'}
                            </p>
                          </div>
                        </div>
                        
                        {/* Additional Info Row */}
                        <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-500 grid grid-cols-2 md:grid-cols-3 gap-2">
                          <p>Revenue: ${(account.revenue / 1000000).toFixed(1)}M</p>
                          <p>Industry: {account.industry || 'N/A'}</p>
                          {account.profile_metadata?.engagement?.lifecycle_stage && (
                            <p>Lifecycle: {account.profile_metadata.engagement.lifecycle_stage}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })()}
                
                {/* Show KPI table when account is selected in heatmap view */}
                {selectedAccount && (() => {
                  const account = accounts.find(a => a.account_id === selectedAccount.account_id);
                  if (!account) return null;
                  
                  return (
                    <div className="mt-6 border-t-2 border-gray-300 pt-6">
                      <div className="mb-4">
                        <h5 className="text-lg font-semibold text-gray-900 mb-2">
                          KPIs for {account.account_name}
                        </h5>
                        <p className="text-sm text-gray-600">
                          {(() => {
                            const allAccountKPIs = deduplicatedKpiData.filter(kpi => kpi.account_id === account.account_id);
                            const profileProducts = account.profile_metadata?.products_used;
                            const accountProductsList = profileProducts && profileProducts.trim() 
                              ? profileProducts.split(',').map(p => p.trim()).filter(p => p)
                              : (account.products_used || []);
                            const accountProductKPIs = deduplicatedKpiData.filter(kpi => 
                              kpi.account_id === account.account_id && kpi.product_id !== null && kpi.product_id !== undefined
                            );
                            const hasProducts = accountProductsList.length > 0 || accountProductKPIs.length > 0;
                            
                            if (!hasProducts) {
                              const accountLevelCount = allAccountKPIs.filter(kpi => kpi.product_id === null || kpi.product_id === undefined).length;
                              return `Showing ${accountLevelCount} Account-level KPIs`;
                            }
                            
                            const productKPIs = allAccountKPIs.filter(kpi => kpi.product_id !== null && kpi.product_id !== undefined);
                            const productLevelParameters = new Set(productKPIs.map(kpi => kpi.kpi_parameter));
                            const accountLevelKPIs = allAccountKPIs.filter(kpi => 
                              (kpi.product_id === null || kpi.product_id === undefined) && !productLevelParameters.has(kpi.kpi_parameter)
                            );
                            const totalDisplayed = productKPIs.length + accountLevelKPIs.length;
                            
                            return `Showing ${totalDisplayed} KPIs (${productKPIs.length} Product-level, ${accountLevelKPIs.length} Account-level)`;
                          })()}
                        </p>
                      </div>
                      
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200 bg-white rounded-lg">
                          <thead className="bg-gray-100">
                            <tr>
                              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Product</th>
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
                            {(() => {
                              // Get all KPIs for this account
                              const allAccountKPIs = deduplicatedKpiData.filter(kpi => kpi.account_id === account.account_id);
                              
                              // Check if account has products (from profile metadata, products_used array, or product-level KPIs)
                              const profileProducts = account.profile_metadata?.products_used;
                              const accountProductsList = profileProducts && profileProducts.trim() 
                                ? profileProducts.split(',').map(p => p.trim()).filter(p => p)
                                : (account.products_used || []);
                              const accountProductKPIs = allAccountKPIs.filter(kpi => 
                                kpi.product_id !== null && kpi.product_id !== undefined
                              );
                              const hasProducts = accountProductsList.length > 0 || accountProductKPIs.length > 0;
                              
                              if (!hasProducts) {
                                // Account has no products - show only account-level KPIs
                                return allAccountKPIs.filter(kpi => kpi.product_id === null || kpi.product_id === undefined);
                              }
                              
                              // Account has products (1, 2, 3, or more) - show uniform format
                              // Get all product-level KPIs (for any number of products)
                              const productKPIs = allAccountKPIs.filter(kpi => 
                                kpi.product_id !== null && kpi.product_id !== undefined
                              );
                              
                              // Get account-level KPIs
                              // For parameters that have product-level KPIs, only show account-level if:
                              // 1. It's an aggregate (aggregation_type is set), OR
                              // 2. There are NO product-level KPIs for that parameter
                              const productLevelParameters = new Set(
                                productKPIs.map(kpi => kpi.kpi_parameter).filter(p => p)
                              );
                              
                              const accountLevelKPIs = allAccountKPIs.filter(kpi => {
                                if (kpi.product_id !== null && kpi.product_id !== undefined) return false; // Skip product-level KPIs here
                                
                                // If this parameter has product-level KPIs, only show if it's an aggregate
                                if (productLevelParameters.has(kpi.kpi_parameter)) {
                                  return kpi.aggregation_type !== null && kpi.aggregation_type !== undefined;
                                }
                                
                                // Otherwise, show all account-level KPIs
                                return true;
                              });
                              
                              // Combine: product-level KPIs first, then account-level KPIs
                              // This ensures uniform display for accounts with 1, 2, 3, or more products
                              return [...productKPIs, ...accountLevelKPIs];
                            })().map((kpi) => (
                              <tr key={kpi.kpi_id} className="hover:bg-gray-50">
                                <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                  {kpi.product_name ? (
                                    <span className="font-medium text-blue-600">{kpi.product_name}</span>
                                  ) : (
                                    <span className="text-gray-500 italic">Account Level</span>
                                  )}
                                </td>
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
                        {deduplicatedKpiData.filter(kpi => kpi.account_id === account.account_id).length === 0 && (
                          <div className="text-center py-8 text-gray-500">
                            <p>No KPIs found for this account.</p>
                            <p className="text-sm mt-1">Upload a KPI file with this account name to see KPIs here.</p>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })()}
              </>
            ) : (
              // Original list view (default)
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
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-semibold text-gray-900 text-lg">{account.account_name}</h4>
                        <div className="flex items-center space-x-2">
                          <div className={`w-3 h-3 rounded-full ${getHealthColor(account.health_score)}`}></div>
                          <span className="text-sm text-gray-500">
                            {selectedAccount?.account_id === account.account_id ? '▼' : '▶'}
                          </span>
                        </div>
                      </div>
                      
                      {/* Account Details Grid */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                        {/* Health Score with Status */}
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Health Score</p>
                          {(() => {
                            const healthStatus = getHealthStatus(account.health_score);
                            return (
                              <div className="flex items-center space-x-2">
                                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                  healthStatus.color === 'green' ? 'bg-green-100 text-green-800' :
                                  healthStatus.color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
                                  healthStatus.color === 'red' ? 'bg-red-100 text-red-800' :
                                  'bg-gray-100 text-gray-800'
                                }`}>
                                  {healthStatus.status}
                                </span>
                                <span className="font-semibold text-gray-900">
                                  {account.health_score?.toFixed(0) || 'N/A'}
                                </span>
                              </div>
                            );
                          })()}
                        </div>
                        
                        {/* Region */}
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Region</p>
                          <p className="font-medium text-gray-900">{account.region || 'N/A'}</p>
                        </div>
                        
                        {/* Status */}
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Status</p>
                          <p className="font-medium text-gray-900 capitalize">{account.account_status || 'N/A'}</p>
                        </div>
                        
                        {/* Account Tier */}
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Account Tier</p>
                          <p className="font-medium text-gray-900">{account.profile_metadata?.account_tier || 'N/A'}</p>
                        </div>
                        
                        {/* Assigned CSM */}
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Assigned CSM</p>
                          <p className="font-medium text-gray-900">{account.profile_metadata?.assigned_csm || 'N/A'}</p>
                        </div>
                        
                        {/* CSM Manager */}
                        <div>
                          <p className="text-xs text-gray-500 mb-1">CSM Manager</p>
                          <p className="font-medium text-gray-900">{account.profile_metadata?.csm_manager || 'N/A'}</p>
                        </div>
                        
                        {/* Products Used */}
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Products Used</p>
                          <p className="font-medium text-gray-900">
                            {(() => {
                              // Priority 1: profile_metadata.products_used (from customer profile upload)
                              const profileProducts = account.profile_metadata?.products_used;
                              if (profileProducts && profileProducts.trim()) {
                                return profileProducts;
                              }
                              // Priority 2: products_used array (from Product table)
                              if (account.products_used && account.products_used.length > 0) {
                                return account.products_used.join(', ');
                              }
                              return 'N/A';
                            })()}
                          </p>
                        </div>
                        
                        {/* Champion Name */}
                        <div>
                          <p className="text-xs text-gray-500 mb-1">Champion Name</p>
                          <p className="font-medium text-gray-900">
                            {account.primary_champion_name || 
                             account.profile_metadata?.champions?.[0]?.primary_champion_name || 
                             'N/A'}
                          </p>
                        </div>
                      </div>
                      
                      {/* Additional Info Row */}
                      <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-500 grid grid-cols-2 md:grid-cols-3 gap-2">
                        <p>Revenue: ${(account.revenue / 1000000).toFixed(1)}M</p>
                        <p>Industry: {account.industry}</p>
                        {account.profile_metadata?.engagement?.lifecycle_stage && (
                          <p>Lifecycle: {account.profile_metadata.engagement.lifecycle_stage}</p>
                        )}
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
                          {(() => {
                            const allAccountKPIs = deduplicatedKpiData.filter(kpi => kpi.account_id === account.account_id);
                            const profileProducts = account.profile_metadata?.products_used;
                            const accountProductsList = profileProducts && profileProducts.trim() 
                              ? profileProducts.split(',').map(p => p.trim()).filter(p => p)
                              : (account.products_used || []);
                            const accountProductKPIs = deduplicatedKpiData.filter(kpi => 
                              kpi.account_id === account.account_id && kpi.product_id !== null && kpi.product_id !== undefined
                            );
                            const hasProducts = accountProductsList.length > 0 || accountProductKPIs.length > 0;
                            
                            if (!hasProducts) {
                              const accountLevelCount = allAccountKPIs.filter(kpi => kpi.product_id === null || kpi.product_id === undefined).length;
                              return `Showing ${accountLevelCount} Account-level KPIs`;
                            }
                            
                            const productKPIs = allAccountKPIs.filter(kpi => kpi.product_id !== null && kpi.product_id !== undefined);
                            const productLevelParameters = new Set(productKPIs.map(kpi => kpi.kpi_parameter));
                            const accountLevelKPIs = allAccountKPIs.filter(kpi => 
                              (kpi.product_id === null || kpi.product_id === undefined) && !productLevelParameters.has(kpi.kpi_parameter)
                            );
                            const totalDisplayed = productKPIs.length + accountLevelKPIs.length;
                            
                            return `Showing ${totalDisplayed} KPIs (${productKPIs.length} Product-level, ${accountLevelKPIs.length} Account-level)`;
                          })()}
                        </p>
                        </div>
                        
                                                <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-gray-200 bg-white rounded-lg">
                            <thead className="bg-gray-100">
                              <tr>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Product</th>
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
                              {(() => {
                                // Get all KPIs for this account
                                const allAccountKPIs = deduplicatedKpiData.filter(kpi => kpi.account_id === account.account_id);
                                
                                // Check if account has products (from profile metadata, products_used array, or product-level KPIs)
                                const profileProducts = account.profile_metadata?.products_used;
                                const accountProductsList = profileProducts && profileProducts.trim() 
                                  ? profileProducts.split(',').map(p => p.trim()).filter(p => p)
                                  : (account.products_used || []);
                                const accountProductKPIs = allAccountKPIs.filter(kpi => 
                                  kpi.product_id !== null && kpi.product_id !== undefined
                                );
                                const hasProducts = accountProductsList.length > 0 || accountProductKPIs.length > 0;
                                
                                if (!hasProducts) {
                                  // Account has no products - show only account-level KPIs
                                  return allAccountKPIs.filter(kpi => kpi.product_id === null || kpi.product_id === undefined);
                                }
                                
                                // Account has products (1, 2, 3, or more) - show uniform format
                                // Get all product-level KPIs (for any number of products)
                                const productKPIs = allAccountKPIs.filter(kpi => 
                                  kpi.product_id !== null && kpi.product_id !== undefined
                                );
                                
                                // Get account-level KPIs
                                // For parameters that have product-level KPIs, only show account-level if:
                                // 1. It's an aggregate (aggregation_type is set), OR
                                // 2. There are NO product-level KPIs for that parameter
                                const productLevelParameters = new Set(
                                  productKPIs.map(kpi => kpi.kpi_parameter).filter(p => p)
                                );
                                
                                const accountLevelKPIs = allAccountKPIs.filter(kpi => {
                                  if (kpi.product_id !== null && kpi.product_id !== undefined) return false; // Skip product-level KPIs here
                                  
                                  // If this parameter has product-level KPIs, only show if it's an aggregate
                                  if (productLevelParameters.has(kpi.kpi_parameter)) {
                                    return kpi.aggregation_type !== null && kpi.aggregation_type !== undefined;
                                  }
                                  
                                  // Otherwise, show all account-level KPIs
                                  return true;
                                });
                                
                                // Combine: product-level KPIs first, then account-level KPIs
                                // This ensures uniform display for accounts with 1, 2, 3, or more products
                                return [...productKPIs, ...accountLevelKPIs];
                              })().map((kpi) => (
                                  <tr key={kpi.kpi_id} className="hover:bg-gray-50">
                                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                      {kpi.product_name ? (
                                        <span className="font-medium text-blue-600">{kpi.product_name}</span>
                                      ) : (
                                        <span className="text-gray-500 italic">Account Level</span>
                                      )}
                                    </td>
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
                          {deduplicatedKpiData.filter(kpi => kpi.account_id === account.account_id).length === 0 && (
                            <div className="text-center py-8 text-gray-500">
                              <p>No KPIs found for this account.</p>
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

            {/* Products Section */}
            {selectedAccount && products[selectedAccount.account_id] && products[selectedAccount.account_id].length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <Target className="h-5 w-5 mr-2 text-blue-600" />
                  Products ({products[selectedAccount.account_id].length})
                </h3>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => {
                      setViewMode(viewMode === 'account' ? 'product' : 'account');
                      setSelectedProduct(null);
                    }}
                    className={`px-3 py-1 text-sm rounded-lg ${
                      viewMode === 'account' 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    Account View
                  </button>
                  <button
                    onClick={() => {
                      setViewMode('product');
                    }}
                    className={`px-3 py-1 text-sm rounded-lg ${
                      viewMode === 'product' 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    Product View
                  </button>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                {products[selectedAccount.account_id].map((product) => (
                  <div
                    key={product.product_id}
                    onClick={() => {
                      setSelectedProduct({accountId: selectedAccount.account_id, productId: product.product_id});
                      setViewMode('product');
                    }}
                    className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
                      selectedProduct?.productId === product.product_id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold text-gray-900">{product.product_name}</h4>
                      <span className={`text-xs px-2 py-1 rounded ${
                        product.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {product.status}
                      </span>
                    </div>
                    {product.product_type && (
                      <p className="text-xs text-gray-500 mb-2">{product.product_type}</p>
                    )}
                    {product.revenue && product.revenue > 0 && (
                      <p className="text-sm font-medium text-gray-700">
                        Revenue: ${product.revenue.toLocaleString()}
                      </p>
                    )}
                    {product.product_sku && (
                      <p className="text-xs text-gray-400 mt-1">SKU: {product.product_sku}</p>
                    )}
                  </div>
                ))}
              </div>
              
              {selectedProduct && selectedProduct.productId && (
                <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-800">
                    Viewing KPIs for: <strong>{products[selectedAccount.account_id].find(p => p.product_id === selectedProduct.productId)?.product_name}</strong>
                  </p>
                </div>
              )}
            </div>
          )}

          {/* KPI Table View */}
          {showKPITable && selectedAccount && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  {viewMode === 'product' && selectedProduct?.productId
                    ? `KPIs for ${products[selectedAccount.account_id]?.find(p => p.product_id === selectedProduct.productId)?.product_name || 'Product'}`
                    : `KPIs for ${selectedAccount.account_name}`}
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
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Product</th>
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
                      .filter(kpi => {
                        if (!selectedAccount) return false;
                        if (viewMode === 'product' && selectedProduct?.productId) {
                          return kpi.product_id === selectedProduct.productId;
                        }
                        // Account-level view: show account-level KPIs only (no product_id)
                        return (kpi.account_id === selectedAccount.account_id || kpi.account_id === null) && !kpi.product_id;
                      })
                      .map((kpi) => (
                        <tr key={kpi.kpi_id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {kpi.product_name ? (
                              <span className="font-medium text-blue-600">{kpi.product_name}</span>
                            ) : (
                              <span className="text-gray-500 italic">Account Level</span>
                            )}
                          </td>
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
  };

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
          { id: 'products', label: 'Product Health', icon: Target },
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
                  {/* Accounts Needing Attention - Main focus area */}
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
                        {/* Summary Stats */}
                        <div className="grid grid-cols-3 gap-2 mb-4 p-3 bg-gray-50 rounded-lg">
                          <div className="text-center">
                            <div className="text-xs text-gray-600">Critical</div>
                            <div className="text-xs text-gray-500">&lt; 70</div>
                            <div className="text-lg font-bold text-red-600">{perfSummary.summary.critical_accounts}</div>
                          </div>
                          <div className="text-center">
                            <div className="text-xs text-gray-600">At Risk</div>
                            <div className="text-xs text-gray-500">70-79</div>
                            <div className="text-lg font-bold text-yellow-600">{perfSummary.summary.at_risk_accounts}</div>
                          </div>
                          <div className="text-center">
                            <div className="text-xs text-gray-600">Healthy</div>
                            <div className="text-xs text-gray-500">≥ 80</div>
                            <div className="text-lg font-bold text-green-600">{perfSummary.summary.healthy_accounts}</div>
                          </div>
                        </div>
                        
                        {/* Account Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                          {perfSummary.accounts_needing_attention.map((account, idx) => (
                            <div key={account.account_id} className="border border-gray-200 rounded-lg p-4 hover:border-orange-300 transition-colors">
                              <div className="flex items-start justify-between mb-3">
                                <div className="flex-1">
                                  <h4 className="font-semibold text-gray-900 text-sm">{account.account_name}</h4>
                                  <div className="flex items-center mt-1 space-x-2">
                                    <div className={`px-2 py-0.5 rounded text-xs font-medium ${
                                      account.overall_health_score >= 80 ? 'bg-green-100 text-green-800' :
                                      account.overall_health_score >= 70 ? 'bg-yellow-100 text-yellow-800' :
                                      'bg-red-100 text-red-800'
                                    }`}>
                                      Score: {account.overall_health_score.toFixed(0)}
                                    </div>
                                    <div className="px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-800">
                                      {account.active_playbooks_count} playbooks
                                    </div>
                                  </div>
                                </div>
                              </div>
                              
                              {/* Revenue Trend */}
                              <div className="mb-3 p-2 bg-gray-50 rounded">
                                <div className="flex items-center justify-between text-xs">
                                  <span className="text-gray-600">Revenue Trend:</span>
                                  <span className={`font-bold ${
                                    account.revenue_growth_pct > 0 ? 'text-green-600' :
                                    account.revenue_growth_pct < 0 ? 'text-red-600' :
                                    'text-gray-600'
                                  }`}>
                                    {account.revenue_growth_pct > 0 ? '↑' : account.revenue_growth_pct < 0 ? '↓' : '→'} {Math.abs(account.revenue_growth_pct).toFixed(1)}%
                                  </span>
                                </div>
                              </div>
                              
                              {/* Focus Areas */}
                              <div className="space-y-2">
                                <div className="text-xs font-medium text-gray-600">Focus Areas (Lowest 2):</div>
                                {account.focus_areas.map((area, areaIdx) => (
                                  <div key={areaIdx} className="flex items-center justify-between text-xs">
                                    <span className="text-gray-700">{area.category}</span>
                                    <span className={`font-semibold ${
                                      area.score >= 80 ? 'text-green-600' :
                                      area.score >= 70 ? 'text-yellow-600' :
                                      'text-red-600'
                                    }`}>
                                      {area.score.toFixed(0)}
                                    </span>
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
                  
                  {/* Revenue Decline Alert - Moved from right panel */}
                  {perfSummary && perfSummary.healthy_declining_revenue && perfSummary.healthy_declining_revenue.length > 0 && (
                    <div className="bg-white rounded-xl shadow-sm border border-red-200 p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                          <TrendingDown className="h-5 w-5 mr-2 text-red-500" />
                          Revenue Decline Alert
                        </h3>
                        <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full font-medium">
                          Healthy KPIs
                        </span>
                      </div>
                      
                      <div className="mb-3 p-2 bg-red-50 rounded text-xs text-red-700">
                        ⚠️ These accounts have healthy KPI scores (≥80) but declining revenue (Company avg: {perfSummary.summary.company_avg_revenue_growth > 0 ? '+' : ''}{perfSummary.summary.company_avg_revenue_growth.toFixed(1)}%)
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {perfSummary.healthy_declining_revenue.map((account, idx) => (
                          <div key={account.account_id} className="border border-red-200 rounded-lg p-3 bg-red-50/30">
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex-1">
                                <h4 className="font-semibold text-gray-900 text-sm">{account.account_name}</h4>
                                <div className="flex items-center mt-1 space-x-2">
                                  <div className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                                    Health: {account.overall_health_score.toFixed(0)}
                                  </div>
                                  <div className="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                                    Revenue ↓ {Math.abs(account.revenue_growth_pct).toFixed(1)}%
                                  </div>
                                </div>
                              </div>
                            </div>
                            
                            <div className="text-xs text-gray-600 mt-2">
                              <div className="font-medium mb-1">Investigate:</div>
                              {account.focus_areas.slice(0, 2).map((area, areaIdx) => (
                                <div key={areaIdx} className="flex items-center justify-between">
                                  <span>• {area.category}</span>
                                  <span className="font-semibold">{area.score.toFixed(0)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="space-y-6">
                  {/* Corporate Health Rollup - Condensed */}
                  <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-bold text-gray-900">Corporate Health</h3>
                      <button 
                        onClick={calculateCorporateRollup}
                        disabled={isCalculatingRollup}
                        className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50"
                      >
                        {isCalculatingRollup ? 'Calculating...' : 'Refresh'}
                      </button>
                    </div>
                    
                    {rollupResults ? (
                      <div className="space-y-3">
                        {/* Top Row - Miniature Stats */}
                        <div className="grid grid-cols-3 gap-2">
                          <div className="text-center p-2 bg-blue-50 rounded">
                            <p className="text-xs text-gray-600">Score</p>
                            <p className="text-lg font-bold text-gray-900">{rollupResults.overall_score.toFixed(1)}</p>
                          </div>
                          <div className="text-center p-2 bg-purple-50 rounded">
                            <p className="text-xs text-gray-600">Tier</p>
                            <p className="text-xs font-semibold text-gray-900">{rollupResults.maturity_tier}</p>
                          </div>
                          <div className="text-center p-2 bg-green-50 rounded">
                            <p className="text-xs text-gray-600">Accounts</p>
                            <p className="text-lg font-bold text-gray-900">{accounts.length}</p>
                          </div>
                        </div>
                        
                        {/* Category Breakdown with Color Bars */}
                        <div className="space-y-2">
                          <p className="text-xs font-medium text-gray-600">Categories:</p>
                          {Object.entries(rollupResults.category_scores).map(([categoryName, categoryData]) => (
                            <div key={categoryName} className="space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="text-xs text-gray-700 truncate">{categoryName.split(' ')[0]}</span>
                                <span className="text-xs font-semibold text-gray-900">{categoryData.score.toFixed(0)}</span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-1.5">
                                <div 
                                  className={`h-1.5 rounded-full ${
                                    categoryData.score >= 75 ? 'bg-green-500' : 
                                    categoryData.score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                                  }`}
                                  style={{ width: `${categoryData.score}%` }}
                                ></div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-6">
                        <BarChart3 className="h-8 w-8 text-gray-400 mx-auto mb-2" />
                        <p className="text-xs text-gray-600">Click Refresh</p>
                      </div>
                    )}
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
                          // Use backend-provided color (green/yellow/red) not hardcoded colors
                          const healthColor = category.color === 'green' ? 'bg-green-500' : 
                                             category.color === 'yellow' ? 'bg-yellow-500' : 
                                             category.color === 'red' ? 'bg-red-500' : 'bg-gray-500';
                          const healthBadge = category.color === 'green' ? 'bg-green-100 text-green-800' : 
                                             category.color === 'yellow' ? 'bg-yellow-100 text-yellow-800' : 
                                             category.color === 'red' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800';
                          
                          return (
                            <div key={index} className="p-4 border border-gray-200 rounded-lg">
                              <div className="flex items-center justify-between mb-2">
                                <h4 className="font-medium text-gray-900 text-sm">{category.category}</h4>
                                <div className={`px-2 py-1 rounded-full text-xs font-medium ${healthBadge}`}>
                                  {category.health_status.toUpperCase()}
                                </div>
                              </div>
                              <div className="text-2xl font-bold text-gray-900 mb-1">
                                {Math.round(category.average_score)}/100
                              </div>
                              <div className="text-xs text-gray-500 mb-2">
                                {category.valid_kpi_count}/{category.kpi_count} KPIs • Weight: {Math.round(category.category_weight * 100)}%
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-2">
                                <div 
                                  className={`h-2 rounded-full ${healthColor}`}
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

          {activeTab === 'products' && <ProductHealthDashboard />}

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
            </div>
            
            {/* Master KPI Framework Upload (collapsible) */}
            <details className="bg-white rounded-xl shadow-sm border border-gray-100" open>
              <summary className="cursor-pointer px-6 py-4 flex items-center justify-between">
                <span className="flex items-center font-semibold text-gray-900">
                  <Settings className="h-5 w-5 mr-2 text-blue-600" />
                  Master KPI Framework Configuration
                </span>
                <span className="text-xs text-gray-500">Click to expand/collapse</span>
              </summary>
              <div className="p-6 border-t border-gray-100 space-y-4">
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
                
                <div
                  className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors cursor-pointer"
                  onClick={() => masterFileInputRef.current?.click()}
                >
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
            </details>


            {/* Inline Advanced Settings (collapsible sections) */}
            <div className="space-y-4">
              <details className="bg-white rounded-xl shadow-sm border border-gray-100">
                <summary className="cursor-pointer px-4 py-3 font-semibold text-gray-900 flex items-center">
                  <Settings className="h-5 w-5 mr-2 text-blue-600" />
                  Playbook Automation
                </summary>
                <div className="p-4">
                  <PlaybookAutomationSettings isAuthenticated={Boolean(session)} />
                </div>
              </details>
              <details className="bg-white rounded-xl shadow-sm border border-gray-100">
                <summary className="cursor-pointer px-4 py-3 font-semibold text-gray-900 flex items-center">
                  <Settings className="h-5 w-5 mr-2 text-blue-600" />
                  OpenAI API Key
                </summary>
                <div className="p-4">
                  <OpenAIKeySettings isAuthenticated={Boolean(session)} />
                </div>
              </details>
              <details className="bg-white rounded-xl shadow-sm border border-gray-100">
                <summary className="cursor-pointer px-4 py-3 font-semibold text-gray-900 flex items-center">
                  <Settings className="h-5 w-5 mr-2 text-blue-600" />
                  Governance & Compliance
                </summary>
                <div className="p-4">
                  <GovernanceSettings isAuthenticated={Boolean(session)} />
                </div>
              </details>
            </div>

            {/* Data Export (Save to Excel) */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h4 className="font-semibold text-gray-900 mb-4">Data Export (Excel)</h4>
              <p className="text-sm text-gray-600 mb-4">
                Download all account data including KPIs, products, and configuration in Excel format.
              </p>
              <button
                onClick={async () => {
                  const fileName = `Account_Data_Export_${new Date().toISOString().split('T')[0]}.xlsx`;
                  try {
                    setIsExporting(true);
                    setError('');
                    // Use relative URL for same-origin requests (works for both local and AWS)
                    const apiUrl = '/api/export/all-account-data';
                    const response = await fetch(apiUrl, {
                      method: 'GET',
                      credentials: 'include',
                      headers: {
                        'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                      }
                    });
                    if (!response.ok) {
                      const contentType = response.headers.get('content-type');
                      if (contentType && contentType.includes('application/json')) {
                        const errData = await response.json();
                        throw new Error(errData.error || `Failed to export data: ${response.status}`);
                      }
                      const errText = await response.text();
                      throw new Error(`Failed to export data: ${response.status}. ${errText.substring(0, 120)}`);
                    }
                    const blob = await response.blob();
                    if (blob.size === 0) {
                      throw new Error('Downloaded file is empty. Please try again.');
                    }
                    // File System Access API when available
                    // @ts-ignore
                    if (typeof window !== 'undefined' && 'showSaveFilePicker' in window) {
                      // @ts-ignore
                      const fileHandle = await (window as any).showSaveFilePicker({
                        suggestedName: fileName,
                        types: [{
                          description: 'Excel files',
                          accept: {
                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
                          }
                        }]
                      });
                      const writable = await fileHandle.createWritable();
                      await writable.write(blob);
                      await writable.close();
                      return;
                    }
                    // Fallback: normal browser download
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = fileName;
                    document.body.appendChild(a);
                    a.click();
                    setTimeout(() => {
                      document.body.removeChild(a);
                      window.URL.revokeObjectURL(url);
                    }, 1000);
                  } catch (e: any) {
                    setError(e?.message || 'Failed to export account data');
                  } finally {
                    setIsExporting(false);
                  }
                }}
                disabled={isExporting}
                className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {isExporting ? 'Exporting…' : (
                  <>
                    <Download className="h-4 w-4 mr-2" />
                    Save Account Data to Excel
                  </>
                )}
              </button>
            </div>

            {/* Data Rehydration (Restore from Excel) */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h4 className="font-semibold text-gray-900 mb-4">Data Rehydration (Restore from Backup)</h4>
              <p className="text-sm text-gray-600 mb-4">
                <strong className="text-red-600">WARNING:</strong> This will <strong>REPLACE ALL EXISTING DATA</strong> for this tenant with data from the exported Excel file. 
                All current accounts, products, and KPIs will be deleted before importing. 
                Only use files exported from this system (with version and timestamp in filename).
              </p>
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  
                  // Check filename format (should contain version and timestamp)
                  const fileName = file.name;
                  if (!fileName.includes('_v') || !fileName.match(/\d{8}_\d{6}/)) {
                    if (!window.confirm(
                      `Warning: File "${fileName}" does not appear to be a valid export file (missing version/timestamp).\n\n` +
                      `Valid export files should have format: Account_Data_Export_v1_YYYYMMDD_HHMMSS.xlsx\n\n` +
                      `Do you want to proceed anyway?`
                    )) {
                      if (e.target) e.target.value = '';
                      return;
                    }
                  }
                  
                  if (!window.confirm(
                    `⚠️ CRITICAL WARNING ⚠️\n\n` +
                    `This will DELETE ALL existing accounts, products, and KPIs for this tenant and replace them with data from "${fileName}".\n\n` +
                    `This action cannot be undone!\n\n` +
                    `Are you absolutely sure you want to proceed?`
                  )) {
                    if (e.target) e.target.value = '';
                    return;
                  }
                  
                  const formData = new FormData();
                  formData.append('file', file);
                  
                  setIsExporting(true); // Reuse loading state
                  setError('');
                  
                  try {
                    const response = await fetch('/api/rehydrate/import', {
                      method: 'POST',
                      credentials: 'include',
                      body: formData,
                    });
                    
                    const data = await response.json();
                    
                    if (!response.ok) {
                      throw new Error(data.error || `Rehydration failed: ${response.status}`);
                    }
                    
                    // Show success message with results
                    const results = data.results || {};
                    const successMsg = `Rehydration completed successfully!\n\n` +
                      `Deleted: ${results.accounts_deleted || 0} accounts, ${results.products_deleted || 0} products, ${results.kpis_deleted || 0} KPIs\n` +
                      `Created: ${results.accounts_created || 0} accounts, ${results.products_created || 0} products, ${results.kpis_created || 0} KPIs\n` +
                      (results.export_timestamp ? `Export Date: ${results.export_timestamp}\n` : '') +
                      (results.errors && results.errors.length > 0 ? `\nErrors: ${results.errors.length}` : '');
                    
                    alert(successMsg);
                    
                    if (results.errors && results.errors.length > 0) {
                      console.error('Rehydration errors:', results.errors);
                    }
                    
                    // Refresh page to show new data
                    window.location.reload();
                  } catch (err: any) {
                    setError(err?.message || 'Failed to rehydrate data');
                    alert(`Rehydration failed: ${err?.message || 'Unknown error'}`);
                  } finally {
                    setIsExporting(false);
                    if (e.target) e.target.value = '';
                  }
                }}
                disabled={isExporting}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-red-600 file:text-white hover:file:bg-red-700 disabled:opacity-50"
              />
              <p className="text-xs text-gray-500 mt-2">
                Select an exported Excel file (format: Account_Data_Export_v1_YYYYMMDD_HHMMSS.xlsx)
              </p>
            </div>

            {/* Customer Profile Upload */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h4 className="font-semibold text-gray-900 mb-4">Customer Profile Upload</h4>
              <p className="text-sm text-gray-600 mb-3">
                Upload the <code>CS_GrowthPulse_CustomerProfile_*.xlsx</code> file to populate account profile, champions, and engagement data for this tenant.
                Values are validated against the <strong>Reference Data</strong> sheet before applying.
              </p>
              <input
                type="file"
                accept=".xlsx,.xls"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  if (!session?.customer_id) {
                    setError('No active tenant session found');
                    return;
                  }
                  const formData = new FormData();
                  formData.append('file', file);
                  setProfileUploading(true);
                  setProfileErrors(null);
                  setError('');
                  try {
                    const res = await fetch('/api/customer-profile/upload', {
                      method: 'POST',
                      credentials: 'include',
                      body: formData,
                    });
                    const data = await res.json();
                    if (!res.ok || data.status !== 'success') {
                      if (data?.errors) {
                        setProfileErrors(data.errors);
                        setError(data.message || 'Customer profile validation failed');
                      } else {
                        setError(data.message || 'Failed to upload customer profile');
                      }
                    } else {
                      setError('');
                    }
                  } catch (err: any) {
                    setError(err?.message || 'Failed to upload customer profile');
                  } finally {
                    setProfileUploading(false);
                    if (e.target) e.target.value = '';
                  }
                }}
                disabled={profileUploading}
                className="block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              {profileUploading && (
                <p className="mt-2 text-sm text-gray-500">Uploading and validating profile data…</p>
              )}
              {profileErrors && profileErrors.length > 0 && (
                <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded">
                  <p className="text-sm font-semibold text-red-700 mb-2">
                    Validation issues found ({profileErrors.length}). Showing first 5:
                  </p>
                  <ul className="text-xs text-red-700 list-disc list-inside space-y-1 max-h-40 overflow-y-auto">
                    {profileErrors.slice(0, 5).map((err, idx) => (
                      <li key={idx}>
                        [{err.sheet}] {err.account} – <strong>{err.field}</strong>: “{err.value}” not in allowed{' '}
                        {Array.isArray(err.allowed) ? err.allowed.join(', ') : ''}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* KPI Health Status Calculations (collapsible, collapsed by default, last section) */}
            <details 
              className="bg-white rounded-xl shadow-sm border border-gray-100" 
              open={kpiHealthSectionOpen}
              onToggle={toggleKpiHealthSection}
            >
              <summary className="cursor-pointer px-6 py-4 flex items-center justify-between">
                <span className="flex items-center font-semibold text-gray-900">
                  <Calculator className="h-5 w-5 mr-2 text-green-600" />
                  KPI Health Status Calculations
                </span>
                <span className="text-xs text-gray-500">Click to expand/collapse</span>
              </summary>
              <div className="p-6 border-t border-gray-100">
                <div className="flex items-center justify-between mb-4">
                  <div />
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
            </details>
          </div>
        )}

        {activeTab === 'reports' && <PlaybookReports customerId={session.customer_id} />}
        </main>
      </div>

      {/* Settings Modal */}
      {/* Advanced Settings modal removed to avoid duplication; all sections are inline above */}
    </div>
  );
};

export default CSPlatform;
