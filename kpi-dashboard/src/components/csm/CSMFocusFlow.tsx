/**
 * CSM Focus Flow Dashboard (Layout 2)
 * =====================================
 *
 * Light-themed task-centric dashboard for Customer Success Managers.
 * Left icon rail navigation with five views:
 *   - Home: greeting, summary chips, top priority actions
 *   - Actions (default): sequential task queue with full account context
 *   - Accounts: sortable portfolio table
 *   - Approvals: pending playbook approvals with inline actions
 *   - Calendar: upcoming renewals sorted by date
 *
 * API integration via X-Customer-ID header pattern.
 * Health thresholds from centralized utils/healthThresholds.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Home, Zap, BookOpen, CheckSquare, Calendar,
  TrendingUp, TrendingDown, Minus, AlertTriangle,
  Clock, User, FileText, ChevronLeft, ChevronRight,
  SkipForward, Loader2, RefreshCw, ArrowUpDown,
  ChevronDown, ChevronUp, Sparkles, Mail, Phone,
  Shield, AlertCircle, CheckCircle, XCircle, Search,
} from 'lucide-react';
import {
  classify, classifyColor, classifyLabel, classifyBadgeClass,
} from '../../utils/healthThresholds';
import { useSession } from '../../contexts/SessionContext';
import { getCustomerIdentifier } from '../../utils/api';
import {
  MOCK_ACCOUNTS, MOCK_ACTIONS, MOCK_APPROVALS,
  MOCK_ACCOUNT_DETAIL, MOCK_RECOMMENDATIONS,
} from './mockData';
import NotificationBell from './NotificationBell';
import UrgentAlertBanner from './UrgentAlertBanner';
import PlaybookStartModal from './PlaybookStartModal';

// ============================================================================
// TYPES
// ============================================================================

type ViewId = 'home' | 'actions' | 'accounts' | 'approvals' | 'calendar';

interface DailyAction {
  rank: number;
  account_id: number;
  account_name: string;
  action: string;
  playbook_id: string;
  urgency: 'critical' | 'high' | 'medium' | 'opportunity';
  estimated_hours: number;
  projected_impact: number;
  metric_id?: string;
  arr?: number;
  health_score?: number;
  churn_risk?: number;
}

interface AccountSummary {
  account_id: number;
  account_name: string;
  health_score: number;
  trend?: number;
  arr?: number;
  status?: string;
  renewal_date?: string;
  classification?: string;
}

interface AccountDetail {
  account_id: number;
  account_name: string;
  health_score: number;
  trend?: number;
  pillar_scores?: Record<string, number>;
  champion?: { name: string; title: string; last_contact_days?: number };
  contract?: { arr: number; renewal_date: string };
  signals?: Array<{ date: string; summary: string; type?: string }>;
  open_tickets?: number;
}

interface Signal {
  date: string;
  summary: string;
  type?: string;
  severity?: string;
}

interface Recommendation {
  playbook_id: string;
  playbook_name: string;
  description: string;
  projected_impact?: number;
}

interface Approval {
  id: number | string;
  playbook_id: string;
  playbook_name: string;
  account_id: number;
  account_name: string;
  projected_impact: number;
  requested_by: string;
  requested_at: string;
  status: 'pending' | 'approved' | 'rejected';
}

// ============================================================================
// NAV CONFIG
// ============================================================================

const NAV_ITEMS: { id: ViewId; icon: React.ElementType; label: string }[] = [
  { id: 'home', icon: Home, label: 'Home' },
  { id: 'actions', icon: Zap, label: 'Actions' },
  { id: 'accounts', icon: BookOpen, label: 'Accounts' },
  { id: 'approvals', icon: CheckSquare, label: 'Approvals' },
  { id: 'calendar', icon: Calendar, label: 'Renewals' },
];

const PILLAR_LABELS: Record<string, string> = {
  P1: 'P1', P2: 'P2', P3: 'P3', P4: 'P4', P5: 'P5',
};

// ============================================================================
// HELPERS
// ============================================================================

function formatCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function urgencyColor(u: string): string {
  switch (u) {
    case 'critical': return 'bg-red-100 text-red-700 border-red-200';
    case 'high': return 'bg-amber-100 text-amber-700 border-amber-200';
    case 'opportunity': return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    default: return 'bg-blue-100 text-blue-700 border-blue-200';
  }
}

function urgencyDot(u: string): string {
  switch (u) {
    case 'critical': return 'bg-red-500';
    case 'high': return 'bg-amber-500';
    case 'opportunity': return 'bg-emerald-500';
    default: return 'bg-blue-500';
  }
}

function daysUntil(dateStr: string): number {
  const target = new Date(dateStr);
  const now = new Date();
  return Math.ceil((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

function renewalColorClass(days: number): string {
  if (days < 30) return 'text-red-600 bg-red-50';
  if (days < 90) return 'text-amber-600 bg-amber-50';
  return 'text-emerald-600 bg-emerald-50';
}

function greetingText(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

function healthBarColor(score: number): string {
  const c = classify(score);
  if (c === 'healthy') return 'bg-emerald-500';
  if (c === 'at_risk') return 'bg-amber-500';
  return 'bg-red-500';
}

function trendIcon(trend?: number) {
  if (!trend || trend === 0) return <Minus className="w-4 h-4 text-gray-400" />;
  if (trend > 0) return <TrendingUp className="w-4 h-4 text-emerald-500" />;
  return <TrendingDown className="w-4 h-4 text-red-500" />;
}

function trendLabel(trend?: number): string {
  if (!trend || trend === 0) return 'Stable';
  if (trend > 0) return `Improving (+${trend.toFixed(1)})`;
  return `Declining (${trend.toFixed(1)})`;
}

// ============================================================================
// SKELETON COMPONENTS
// ============================================================================

const SkeletonCard: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`bg-white rounded-xl shadow-sm border border-gray-200 p-6 animate-pulse ${className}`}>
    <div className="h-4 bg-gray-200 rounded w-1/3 mb-4" />
    <div className="h-3 bg-gray-100 rounded w-full mb-2" />
    <div className="h-3 bg-gray-100 rounded w-2/3 mb-2" />
    <div className="h-3 bg-gray-100 rounded w-1/2" />
  </div>
);

const SkeletonRow: React.FC = () => (
  <div className="flex items-center gap-4 px-4 py-3 animate-pulse">
    <div className="h-3 bg-gray-200 rounded w-1/4" />
    <div className="h-3 bg-gray-100 rounded w-16" />
    <div className="h-3 bg-gray-100 rounded w-20" />
    <div className="h-3 bg-gray-100 rounded w-24" />
  </div>
);

const EmptyState: React.FC<{ icon: React.ElementType; title: string; subtitle: string }> = ({
  icon: Icon, title, subtitle,
}) => (
  <div className="flex flex-col items-center justify-center py-16 text-center">
    <div className="w-14 h-14 rounded-full bg-gray-100 flex items-center justify-center mb-4">
      <Icon className="w-7 h-7 text-gray-400" />
    </div>
    <p className="text-gray-700 font-medium text-lg">{title}</p>
    <p className="text-gray-400 text-sm mt-1 max-w-sm">{subtitle}</p>
  </div>
);

const ErrorBanner: React.FC<{ message: string; onRetry?: () => void }> = ({ message, onRetry }) => (
  <div className="mx-4 my-4 bg-red-50 border border-red-200 rounded-lg px-4 py-3 flex items-center gap-3">
    <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
    <span className="text-red-700 text-sm flex-1">{message}</span>
    {onRetry && (
      <button onClick={onRetry} className="text-red-600 hover:text-red-800 text-sm font-medium flex items-center gap-1">
        <RefreshCw className="w-4 h-4" /> Retry
      </button>
    )}
  </div>
);

// ============================================================================
// MAIN COMPONENT
// ============================================================================

interface CSMFocusFlowProps {
  notifications?: import('../../hooks/useNotifications').Notification[];
  unreadCount?: number;
  urgentAlerts?: import('../../hooks/useNotifications').Notification[];
  onMarkRead?: (id: number) => void;
  onMarkAllRead?: () => void;
}

const CSMFocusFlow: React.FC<CSMFocusFlowProps> = ({ notifications = [], unreadCount = 0, urgentAlerts = [], onMarkRead = () => {}, onMarkAllRead = () => {} }) => {
  const { session } = useSession();
  const customerId = getCustomerIdentifier(session);

  // Navigation
  const [activeView, setActiveView] = useState<ViewId>('actions');

  // Data states
  const [actions, setActions] = useState<DailyAction[]>([]);
  const [accounts, setAccounts] = useState<AccountSummary[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [accountDetail, setAccountDetail] = useState<AccountDetail | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);

  // Queue state
  const [currentIdx, setCurrentIdx] = useState(0);

  // Loading / error
  const [loadingActions, setLoadingActions] = useState(false);
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [loadingApprovals, setLoadingApprovals] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Playbook start modal
  const [playbookModal, setPlaybookModal] = useState<{ playbook: any; account: any } | null>(null);

  // CSM filter
  const [csmFilter, setCsmFilter] = useState<string>('');
  const [csmNames, setCsmNames] = useState<string[]>([]);

  // Accounts table sort
  const [sortField, setSortField] = useState<'account_name' | 'health_score' | 'arr'>('health_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const headers = useMemo(() => ({ 'X-Customer-ID': customerId }), [customerId]);

  // ---- DATA FETCHERS ----

  const fetchActions = useCallback(async () => {
    setLoadingActions(true);
    setError(null);
    try {
      const url = csmFilter
        ? `/api/dc2s/daily-actions?csm_name=${encodeURIComponent(csmFilter)}`
        : '/api/dc2s/daily-actions';
      const res = await fetch(url, { headers });
      if (!res.ok) throw new Error(`Actions: ${res.status}`);
      const data = await res.json();
      const raw: any[] = data.actions || data.data || data || [];
      // Map backend field names to component interface
      const list: DailyAction[] = (Array.isArray(raw) ? raw : []).map((a: any) => ({
        ...a,
        action: a.action || a.action_title || a.action_description || '',
        health_score: a.health_score ?? a.account_health ?? a.overall_health ?? 0,
        projected_impact: a.projected_impact ?? a.roi_projected_impact ?? 0,
        arr: a.arr ?? a.revenue ?? 0,
      }));
      setActions(list.length > 0 ? list : MOCK_ACTIONS);
      setCurrentIdx(0);
    } catch {
      setActions(MOCK_ACTIONS);
      setCurrentIdx(0);
    } finally {
      setLoadingActions(false);
    }
  }, [headers, csmFilter]);

  const fetchAccounts = useCallback(async () => {
    setLoadingAccounts(true);
    setError(null);
    try {
      const res = await fetch('/api/dc2s/accounts', { headers });
      if (!res.ok) throw new Error(`Accounts: ${res.status}`);
      const data = await res.json();
      const raw: any[] = data.accounts || data.data || data || [];
      // Map backend field names to component interface
      const list: AccountSummary[] = (Array.isArray(raw) ? raw : []).map((a: any) => ({
        ...a,
        health_score: a.health_score ?? a.overall_health ?? 0,
        arr: a.arr ?? a.revenue ?? 0,
        status: a.status ?? a.account_status ?? '',
      }));
      setAccounts(list.length > 0 ? list : MOCK_ACCOUNTS);
    } catch {
      setAccounts(MOCK_ACCOUNTS);
    } finally {
      setLoadingAccounts(false);
    }
  }, [headers]);

  const fetchApprovals = useCallback(async () => {
    setLoadingApprovals(true);
    try {
      const res = await fetch('/api/approvals/pending', { headers });
      if (!res.ok) throw new Error(`Approvals: ${res.status}`);
      const data = await res.json();
      const list: Approval[] = data.approvals || data.data || data || [];
      const result = Array.isArray(list) ? list : [];
      setApprovals(result.length > 0 ? result : MOCK_APPROVALS);
    } catch {
      setApprovals(MOCK_APPROVALS);
    } finally {
      setLoadingApprovals(false);
    }
  }, [headers]);

  const fetchAccountDetail = useCallback(async (accountId: number) => {
    setLoadingDetail(true);
    setAccountDetail(null);
    setSignals([]);
    setRecommendations([]);
    try {
      const [detailRes, healthRes, recsRes] = await Promise.allSettled([
        fetch(`/api/dc2s/accounts/${accountId}`, { headers }),
        fetch(`/api/dc2s/health-score/${accountId}`, { headers }),
        fetch(`/api/dc2s/recommendations/${accountId}`, { headers }),
      ]);

      // Build account detail from both endpoints
      let detail: any = {};
      if (detailRes.status === 'fulfilled' && detailRes.value.ok) {
        const d = await detailRes.value.json();
        detail = d.account || d.data || d || {};
      }
      if (healthRes.status === 'fulfilled' && healthRes.value.ok) {
        const h = await healthRes.value.json();
        detail.health_score = h.overall_score ?? h.health_score ?? detail.overall_health ?? 0;
        detail.pillar_scores = h.category_scores
          ? Object.fromEntries(Object.entries(h.category_scores).map(([k, v]: [string, any]) => [k, v?.score ?? v]))
          : detail.pillar_scores ?? {};
      }
      // Map field names
      detail.health_score = detail.health_score ?? detail.overall_health ?? 0;
      detail.contract = detail.contract || { arr: detail.arr ?? detail.revenue ?? 0, renewal_date: detail.renewal_date };
      // Extract signals from metadata or qualitative_signals if present
      const metaSignals = detail.metadata?.recent_signals || detail.signals || [];
      setAccountDetail(detail);

      // Fetch qualitative signals for this account as alerts
      try {
        const sigRes = await fetch(`/api/health-trends?account_id=${accountId}`, { headers });
        if (sigRes.ok) {
          const sigData = await sigRes.json();
          const trends = sigData.trends || [];
          // Convert trends to signal-like format for display
          const sigList = trends.slice(-3).map((t: any) => ({
            date: t.month ? `2026-${t.month}-01` : null,
            summary: `Health: ${Math.round(t.score)} | P1: ${Math.round(t.product_usage_score ?? 0)} P3: ${Math.round(t.customer_sentiment_score ?? 0)} P5: ${Math.round(t.relationship_strength_score ?? 0)}`,
            type: t.score < 50 ? 'risk' : t.score < 70 ? 'warning' : 'positive',
          }));
          setSignals(metaSignals.length > 0 ? metaSignals.slice(0, 5) : sigList);
        } else {
          setSignals(metaSignals.slice(0, 5));
        }
      } catch {
        setSignals(metaSignals.slice(0, 5));
      }

      if (recsRes.status === 'fulfilled' && recsRes.value.ok) {
        const r = await recsRes.value.json();
        const recList = r.recommendations || r.playbooks || r.data || [];
        setRecommendations(Array.isArray(recList) ? recList.slice(0, 4) : []);
      }
    } catch {
      // Fall back to mock detail if all API calls failed
      const mockDetail = (MOCK_ACCOUNT_DETAIL as any)[accountId];
      if (mockDetail) {
        setAccountDetail(mockDetail);
        setSignals(mockDetail.signals || []);
        setRecommendations((MOCK_RECOMMENDATIONS as any)[accountId] || []);
      }
    } finally {
      setLoadingDetail(false);
    }
  }, [headers]);

  // ---- EFFECTS ----

  // Fetch CSM names for filter dropdown
  useEffect(() => {
    const fetchCsmNames = async () => {
      try {
        const res = await fetch('/api/dc2s/team-capacity', { headers });
        if (res.ok) {
          const data = await res.json();
          if (data.csm_names?.length) setCsmNames(data.csm_names);
        }
      } catch { /* optional — filter just won't show */ }
    };
    fetchCsmNames();
  }, [headers]);

  useEffect(() => {
    fetchActions();
    fetchAccounts();
  }, [fetchActions, fetchAccounts]);

  useEffect(() => {
    if (activeView === 'approvals') fetchApprovals();
  }, [activeView, fetchApprovals]);

  // Load detail when the current action changes
  const currentAction = actions[currentIdx] || null;
  useEffect(() => {
    if (currentAction?.account_id) {
      fetchAccountDetail(currentAction.account_id);
    }
  }, [currentAction?.account_id, fetchAccountDetail]);

  // ---- SORTED ACCOUNTS ----

  const sortedAccounts = useMemo(() => {
    const sorted = [...accounts].sort((a, b) => {
      let av: any, bv: any;
      switch (sortField) {
        case 'account_name':
          av = (a.account_name || '').toLowerCase();
          bv = (b.account_name || '').toLowerCase();
          return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
        case 'arr':
          av = a.arr || 0;
          bv = b.arr || 0;
          return sortDir === 'asc' ? av - bv : bv - av;
        default: // health_score
          av = a.health_score ?? 100;
          bv = b.health_score ?? 100;
          return sortDir === 'asc' ? av - bv : bv - av;
      }
    });
    return sorted;
  }, [accounts, sortField, sortDir]);

  // ---- SUMMARY STATS ----

  const stats = useMemo(() => {
    let critical = 0, atRisk = 0, healthy = 0, renewing = 0;
    accounts.forEach((a) => {
      const c = classify(a.health_score ?? 70);
      if (c === 'critical') critical++;
      else if (c === 'at_risk') atRisk++;
      else healthy++;
      if (a.renewal_date && daysUntil(a.renewal_date) <= 30) renewing++;
    });
    return { critical, atRisk, healthy, renewing };
  }, [accounts]);

  // ---- HANDLERS ----

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const goToAccountActions = (accountId: number) => {
    const idx = actions.findIndex((a) => a.account_id === accountId);
    if (idx >= 0) {
      setCurrentIdx(idx);
      setActiveView('actions');
    } else {
      // No action for this account, just switch view and load detail
      fetchAccountDetail(accountId);
      setActiveView('actions');
    }
  };

  const handleComplete = () => {
    if (currentIdx < actions.length - 1) setCurrentIdx(currentIdx + 1);
  };

  const handlePrev = () => {
    if (currentIdx > 0) setCurrentIdx(currentIdx - 1);
  };

  const handleSkip = () => {
    if (currentIdx < actions.length - 1) setCurrentIdx(currentIdx + 1);
  };

  const handleSnooze = () => {
    // Remove from local list and advance
    const updated = actions.filter((_, i) => i !== currentIdx);
    setActions(updated);
    if (currentIdx >= updated.length && updated.length > 0) {
      setCurrentIdx(updated.length - 1);
    }
  };

  const handleApprove = (id: number | string) => {
    setApprovals((prev) => prev.map((a) => (a.id === id ? { ...a, status: 'approved' as const } : a)));
    // Fire-and-forget API call
    fetch(`/api/approvals/${id}/approve`, { method: 'POST', headers }).catch(() => {});
  };

  const handleReject = (id: number | string) => {
    setApprovals((prev) => prev.map((a) => (a.id === id ? { ...a, status: 'rejected' as const } : a)));
    fetch(`/api/approvals/${id}/reject`, { method: 'POST', headers }).catch(() => {});
  };

  // ============================================================================
  // RENDER: ICON RAIL
  // ============================================================================

  const renderRail = () => (
    <nav className="w-12 bg-gray-900 flex flex-col items-center py-4 gap-1 flex-shrink-0">
      {NAV_ITEMS.map(({ id, icon: Icon, label }) => {
        const active = activeView === id;
        return (
          <button
            key={id}
            onClick={() => setActiveView(id)}
            title={label}
            className={`
              relative w-10 h-10 flex items-center justify-center rounded-lg transition-colors
              ${active ? 'bg-gray-800 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50'}
            `}
          >
            {active && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-blue-500 rounded-r" />
            )}
            <Icon className="w-5 h-5" />
          </button>
        );
      })}
    </nav>
  );

  // ============================================================================
  // RENDER: HOME VIEW
  // ============================================================================

  const renderHome = () => {
    const userName = session?.user_name || 'CSM';
    const topActions = actions.slice(0, 3);

    return (
      <div className="p-6 max-w-4xl mx-auto">
        {/* Greeting */}
        <h1 className="text-2xl font-bold text-gray-900 mb-1">
          {greetingText()}, {userName}
        </h1>
        <p className="text-gray-500 text-sm mb-6">
          Here is your portfolio summary for today.
        </p>

        {/* Summary chips */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          <SummaryChip
            label="Critical"
            count={stats.critical}
            colorClass="bg-red-50 text-red-700 border-red-200"
            icon={AlertTriangle}
          />
          <SummaryChip
            label="At Risk"
            count={stats.atRisk}
            colorClass="bg-amber-50 text-amber-700 border-amber-200"
            icon={AlertCircle}
          />
          <SummaryChip
            label="Healthy"
            count={stats.healthy}
            colorClass="bg-emerald-50 text-emerald-700 border-emerald-200"
            icon={CheckCircle}
          />
          <SummaryChip
            label="Renewals <30d"
            count={stats.renewing}
            colorClass="bg-blue-50 text-blue-700 border-blue-200"
            icon={Calendar}
          />
        </div>

        {/* Top Priority Actions */}
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Top Priority Actions</h2>
        {loadingActions ? (
          <div className="space-y-3">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : topActions.length === 0 ? (
          <EmptyState
            icon={CheckCircle}
            title="All clear!"
            subtitle="No priority actions for today. Great job keeping your portfolio healthy."
          />
        ) : (
          <div className="space-y-3">
            {topActions.map((action, i) => (
              <button
                key={action.rank || i}
                onClick={() => { setCurrentIdx(i); setActiveView('actions'); }}
                className="w-full text-left bg-white rounded-xl shadow-sm border border-gray-200 p-4 hover:border-blue-300 hover:shadow transition-all"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${urgencyColor(action.urgency)}`}>
                        {action.urgency}
                      </span>
                      <span className="text-sm font-semibold text-gray-900 truncate">
                        {action.account_name}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 line-clamp-1">{action.action}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    {action.arr && (
                      <p className="text-xs text-gray-500">{formatCurrency(action.arr)} ARR</p>
                    )}
                    {action.projected_impact ? (
                      <p className="text-xs font-medium text-emerald-600">
                        +{formatCurrency(action.projected_impact)} impact
                      </p>
                    ) : null}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  };

  // ============================================================================
  // RENDER: ACTIONS VIEW (QUEUE)
  // ============================================================================

  const renderActions = () => {
    if (loadingActions && actions.length === 0) {
      return (
        <div className="flex-1 flex flex-col">
          <div className="p-6 space-y-4">
            <SkeletonCard className="h-16" />
            <SkeletonCard className="h-64" />
          </div>
        </div>
      );
    }

    if (actions.length === 0) {
      return (
        <EmptyState
          icon={Zap}
          title="No actions in the queue"
          subtitle="When the platform detects actions for your portfolio, they will appear here."
        />
      );
    }

    const action = currentAction!;
    const detail = accountDetail;
    const healthScore = detail?.health_score ?? action.health_score ?? 0;
    const arr = detail?.contract?.arr ?? action.arr ?? 0;
    const churn = action.churn_risk ?? 0;

    return (
      <div className="flex-1 flex flex-col min-h-0">
        {/* Urgent Alert Banner */}
        <UrgentAlertBanner alerts={urgentAlerts} onDismiss={onMarkRead} />

        {/* Queue Header */}
        <div className="flex-shrink-0 px-6 pt-5 pb-3 border-b border-gray-200 bg-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-gray-400 tracking-wider">
                TODAY'S QUEUE &gt;&gt; {currentIdx + 1}/{actions.length}
              </span>
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${urgencyColor(action.urgency)}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${urgencyDot(action.urgency)}`} />
                {action.urgency}
              </span>
              {/* CSM filter dropdown */}
              {csmNames.length > 1 && (
                <select
                  value={csmFilter}
                  onChange={(e) => setCsmFilter(e.target.value)}
                  className="text-xs bg-white border border-gray-200 rounded px-2 py-1 text-gray-600 focus:outline-none focus:ring-1 focus:ring-blue-300"
                >
                  <option value="">All CSMs</option>
                  {csmNames.map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
              )}
            </div>
            <div className="flex items-center gap-4 text-xs text-gray-500">
              {arr > 0 && <span className="font-medium">{formatCurrency(arr)} ARR</span>}
              {churn > 0 && <span className="text-red-600">{churn > 1 ? Math.round(churn) : (churn * 100).toFixed(0)}% churn risk</span>}
              <span
                className="font-semibold"
                style={{ color: classifyColor(healthScore) }}
              >
                Health: {healthScore}
              </span>
              <NotificationBell
                notifications={notifications}
                unreadCount={unreadCount}
                onMarkRead={onMarkRead}
                onMarkAllRead={onMarkAllRead}
              />
            </div>
          </div>
          <h2 className="text-lg font-bold text-gray-900 mt-1">{action.account_name}</h2>
          <p className="text-sm text-gray-600 mt-0.5">{action.action}</p>
        </div>

        {/* Scrollable Context */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {loadingDetail ? (
            <SkeletonCard className="h-64" />
          ) : (
            <>
              {/* Account Context Card */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
                {/* Health bar */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-gray-700">Health Score</span>
                    <span
                      className="text-sm font-bold"
                      style={{ color: classifyColor(healthScore) }}
                    >
                      {healthScore}
                    </span>
                  </div>
                  <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${healthBarColor(healthScore)}`}
                      style={{ width: `${Math.min(healthScore, 100)}%` }}
                    />
                  </div>
                  <div className="flex items-center gap-1.5 mt-1.5">
                    {trendIcon(detail?.trend)}
                    <span className="text-xs text-gray-500">{trendLabel(detail?.trend)}</span>
                  </div>
                </div>

                {/* Pillar scores */}
                {detail?.pillar_scores && Object.keys(detail.pillar_scores).length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-4">
                    {Object.entries(detail.pillar_scores).map(([key, score]) => (
                      <span
                        key={key}
                        className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${classifyBadgeClass(score)}`}
                      >
                        {PILLAR_LABELS[key] || key}: {Math.round(score)}
                      </span>
                    ))}
                  </div>
                )}

                {/* Champion info */}
                {detail?.champion && (
                  <div className="flex items-center gap-2 py-2 border-t border-gray-100 text-sm">
                    <User className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-700 font-medium">{detail.champion.name}</span>
                    {detail.champion.title && (
                      <span className="text-gray-400">{detail.champion.title}</span>
                    )}
                    {detail.champion.last_contact_days != null && (
                      <span className="text-gray-400 ml-auto text-xs">
                        Last contact: {detail.champion.last_contact_days}d ago
                      </span>
                    )}
                  </div>
                )}

                {/* Contract line */}
                {detail?.contract && (
                  <div className="flex items-center gap-2 py-2 border-t border-gray-100 text-sm">
                    <FileText className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-700">
                      {formatCurrency(detail.contract.arr)} ARR
                    </span>
                    {detail.contract.renewal_date && (
                      <>
                        <span className="text-gray-300">|</span>
                        <span className="text-gray-500">
                          Renewal: {detail.contract.renewal_date}
                        </span>
                        <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${renewalColorClass(daysUntil(detail.contract.renewal_date))}`}>
                          {daysUntil(detail.contract.renewal_date)}d
                        </span>
                      </>
                    )}
                  </div>
                )}

                {/* Recent Signals */}
                {signals.length > 0 && (
                  <div className="pt-3 border-t border-gray-100 mt-2">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Recent Signals
                    </p>
                    <ul className="space-y-1.5">
                      {signals.map((sig, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <span className="text-gray-400 text-xs mt-0.5 flex-shrink-0 w-16">
                            {sig.date ? new Date(sig.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '--'}
                          </span>
                          <span className="text-gray-700">{sig.summary}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Open Tickets */}
                {detail?.open_tickets != null && detail.open_tickets > 0 && (
                  <div className="flex items-center gap-2 pt-3 border-t border-gray-100 mt-2 text-sm">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    <span className="text-gray-700">
                      {detail.open_tickets} open ticket{detail.open_tickets > 1 ? 's' : ''}
                    </span>
                  </div>
                )}
              </div>

              {/* Recommended Actions */}
              {recommendations.length > 0 && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                    Recommended Actions
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {recommendations.map((rec, i) => (
                      <button
                        key={i}
                        className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-blue-300 transition-colors"
                        title={rec.description}
                        onClick={() => setPlaybookModal({
                          playbook: rec,
                          account: { account_id: action.account_id, account_name: action.account_name, health_score: healthScore, arr: arr },
                        })}
                      >
                        <Zap className="w-3.5 h-3.5 text-blue-500" />
                        {rec.playbook_name || `Run ${rec.playbook_id}`}
                      </button>
                    ))}
                    <button className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
                      <Mail className="w-3.5 h-3.5 text-gray-400" />
                      Draft Email
                    </button>
                    <button className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
                      <Phone className="w-3.5 h-3.5 text-gray-400" />
                      Schedule QBR
                    </button>
                    <button className="inline-flex items-center gap-1.5 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg text-sm font-medium text-blue-700 hover:bg-blue-100 transition-colors">
                      <Sparkles className="w-3.5 h-3.5" />
                      Ask AI
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Sticky Navigation Footer */}
        <div className="flex-shrink-0 px-6 py-3 bg-white border-t border-gray-200 flex items-center justify-between gap-2">
          <button
            onClick={handlePrev}
            disabled={currentIdx === 0}
            className="inline-flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium text-gray-600 bg-white border border-gray-200 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" /> Prev
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={handleSnooze}
              className="inline-flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium text-gray-500 bg-white border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              <Clock className="w-4 h-4" /> Snooze 1d
            </button>
            <button
              onClick={handleSkip}
              disabled={currentIdx >= actions.length - 1}
              className="inline-flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium text-gray-500 bg-white border border-gray-200 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Skip <SkipForward className="w-4 h-4" />
            </button>
          </div>

          <button
            onClick={handleComplete}
            disabled={currentIdx >= actions.length - 1 && actions.length > 0}
            className="inline-flex items-center gap-1 px-4 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            Complete & Next <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  };

  // ============================================================================
  // RENDER: ACCOUNTS VIEW
  // ============================================================================

  const SortHeader: React.FC<{
    label: string;
    field: typeof sortField;
    className?: string;
  }> = ({ label, field, className = '' }) => (
    <button
      onClick={() => handleSort(field)}
      className={`flex items-center gap-1 text-xs font-semibold uppercase tracking-wider text-gray-500 hover:text-gray-700 ${className}`}
    >
      {label}
      {sortField === field ? (
        sortDir === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
      ) : (
        <ArrowUpDown className="w-3 h-3 text-gray-300" />
      )}
    </button>
  );

  const renderAccounts = () => (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex-shrink-0 px-6 pt-5 pb-3 border-b border-gray-200 bg-white">
        <h2 className="text-lg font-bold text-gray-900">My Accounts</h2>
        <p className="text-sm text-gray-500">{accounts.length} accounts in your portfolio</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loadingAccounts && accounts.length === 0 ? (
          <div className="p-4 space-y-2">
            {[...Array(6)].map((_, i) => <SkeletonRow key={i} />)}
          </div>
        ) : accounts.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title="No accounts found"
            subtitle="Your portfolio accounts will appear here once data is loaded."
          />
        ) : (
          <table className="w-full">
            <thead className="sticky top-0 bg-gray-50 z-10">
              <tr className="border-b border-gray-200">
                <th className="text-left px-6 py-3">
                  <SortHeader label="Account" field="account_name" />
                </th>
                <th className="text-left px-4 py-3">
                  <SortHeader label="Health" field="health_score" />
                </th>
                <th className="text-center px-4 py-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Trend
                  </span>
                </th>
                <th className="text-right px-4 py-3">
                  <SortHeader label="ARR" field="arr" className="justify-end" />
                </th>
                <th className="text-center px-6 py-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Status
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedAccounts.map((acct) => {
                const c = classify(acct.health_score ?? 70);
                return (
                  <tr
                    key={acct.account_id}
                    onClick={() => goToAccountActions(acct.account_id)}
                    className="border-b border-gray-100 hover:bg-blue-50/40 cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-3 text-sm font-medium text-gray-900">
                      {acct.account_name}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: classifyColor(acct.health_score ?? 70) }}
                        />
                        <span className="text-sm font-medium text-gray-800">
                          {acct.health_score ?? '--'}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {trendIcon(acct.trend)}
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-gray-700">
                      {acct.arr ? formatCurrency(acct.arr) : '--'}
                    </td>
                    <td className="px-6 py-3 text-center">
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${classifyBadgeClass(acct.health_score ?? 70)}`}>
                        {classifyLabel(acct.health_score ?? 70)}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );

  // ============================================================================
  // RENDER: APPROVALS VIEW
  // ============================================================================

  const renderApprovals = () => (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex-shrink-0 px-6 pt-5 pb-3 border-b border-gray-200 bg-white">
        <h2 className="text-lg font-bold text-gray-900">Pending Approvals</h2>
        <p className="text-sm text-gray-500">
          {approvals.filter((a) => a.status === 'pending').length} pending review
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-3">
        {loadingApprovals ? (
          <div className="space-y-3">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : approvals.length === 0 ? (
          <EmptyState
            icon={CheckSquare}
            title="No pending approvals"
            subtitle="Playbook approvals requiring your review will appear here."
          />
        ) : (
          approvals.map((appr) => (
            <div
              key={appr.id}
              className={`bg-white rounded-xl shadow-sm border p-4 transition-opacity ${
                appr.status !== 'pending' ? 'opacity-60 border-gray-100' : 'border-gray-200'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-semibold text-gray-900">
                      {appr.playbook_name || appr.playbook_id}
                    </span>
                    {appr.status !== 'pending' && (
                      <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                        appr.status === 'approved'
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-red-100 text-red-700'
                      }`}>
                        {appr.status}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600">
                    Account: <span className="font-medium">{appr.account_name}</span>
                  </p>
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                    {appr.projected_impact > 0 && (
                      <span className="text-emerald-600 font-medium">
                        +{formatCurrency(appr.projected_impact)} projected
                      </span>
                    )}
                    <span>Requested by {appr.requested_by}</span>
                  </div>
                </div>

                {appr.status === 'pending' && (
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => handleApprove(appr.id)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 transition-colors"
                    >
                      <CheckCircle className="w-4 h-4" /> Approve
                    </button>
                    <button
                      onClick={() => handleReject(appr.id)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium text-red-600 bg-white border border-red-200 hover:bg-red-50 transition-colors"
                    >
                      <XCircle className="w-4 h-4" /> Reject
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );

  // ============================================================================
  // RENDER: CALENDAR (RENEWALS) VIEW
  // ============================================================================

  const renewalAccounts = useMemo(() => {
    return accounts
      .filter((a) => a.renewal_date)
      .sort((a, b) => {
        const da = new Date(a.renewal_date!).getTime();
        const db = new Date(b.renewal_date!).getTime();
        return da - db;
      });
  }, [accounts]);

  const renderCalendar = () => (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="flex-shrink-0 px-6 pt-5 pb-3 border-b border-gray-200 bg-white">
        <h2 className="text-lg font-bold text-gray-900">Upcoming Renewals</h2>
        <p className="text-sm text-gray-500">{renewalAccounts.length} accounts with renewal dates</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-2">
        {loadingAccounts && accounts.length === 0 ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => <SkeletonRow key={i} />)}
          </div>
        ) : renewalAccounts.length === 0 ? (
          <EmptyState
            icon={Calendar}
            title="No renewal dates found"
            subtitle="Accounts with renewal dates will appear here sorted chronologically."
          />
        ) : (
          renewalAccounts.map((acct) => {
            const days = daysUntil(acct.renewal_date!);
            return (
              <div
                key={acct.account_id}
                onClick={() => goToAccountActions(acct.account_id)}
                className="bg-white rounded-xl shadow-sm border border-gray-200 px-5 py-3 flex items-center gap-4 hover:border-blue-300 hover:shadow cursor-pointer transition-all"
              >
                {/* Days badge */}
                <div className={`flex-shrink-0 w-16 text-center py-1.5 rounded-lg text-sm font-bold ${renewalColorClass(days)}`}>
                  {days}d
                </div>

                {/* Account info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-gray-900 truncate">{acct.account_name}</p>
                  <p className="text-xs text-gray-400">
                    Renewal: {acct.renewal_date ? new Date(acct.renewal_date).toLocaleDateString('en-US', {
                      month: 'short', day: 'numeric', year: 'numeric',
                    }) : 'TBD'}
                  </p>
                </div>

                {/* ARR */}
                <div className="flex-shrink-0 text-right">
                  <p className="text-sm font-medium text-gray-700">
                    {acct.arr ? formatCurrency(acct.arr) : '--'}
                  </p>
                </div>

                {/* Health */}
                <div className="flex-shrink-0 flex items-center gap-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: classifyColor(acct.health_score ?? 70) }}
                  />
                  <span className="text-sm font-medium text-gray-700">
                    {acct.health_score ?? '--'}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );

  // ============================================================================
  // MAIN LAYOUT
  // ============================================================================

  const viewContent = () => {
    switch (activeView) {
      case 'home': return renderHome();
      case 'actions': return renderActions();
      case 'accounts': return renderAccounts();
      case 'approvals': return renderApprovals();
      case 'calendar': return renderCalendar();
      default: return renderActions();
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Left icon rail */}
      {renderRail()}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {error && <ErrorBanner message={error} onRetry={() => { fetchActions(); fetchAccounts(); }} />}
        {viewContent()}
      </div>

      {/* Playbook Start Modal */}
      {playbookModal && (
        <PlaybookStartModal
          playbook={playbookModal.playbook}
          account={playbookModal.account}
          customerId={customerId}
          onClose={() => setPlaybookModal(null)}
          onStarted={() => setPlaybookModal(null)}
        />
      )}
    </div>
  );
};

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

const SummaryChip: React.FC<{
  label: string;
  count: number;
  colorClass: string;
  icon: React.ElementType;
}> = ({ label, count, colorClass, icon: Icon }) => (
  <div className={`flex items-center gap-3 px-4 py-3 rounded-xl border ${colorClass}`}>
    <Icon className="w-5 h-5 flex-shrink-0" />
    <div>
      <p className="text-2xl font-bold leading-none">{count}</p>
      <p className="text-xs mt-0.5 opacity-80">{label}</p>
    </div>
  </div>
);

export default CSMFocusFlow;
