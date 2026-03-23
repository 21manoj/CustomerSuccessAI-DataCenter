import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Bell, X, ChevronDown, Search, Check, XCircle,
  Flame, Clock, TrendingUp, AlertTriangle, Users,
  BarChart3, FileText, Home, Columns, Building2,
  RefreshCw, Loader2, ChevronRight, Calendar,
  Mail, Sparkles, Phone, Shield, ExternalLink,
  MessageSquare, History, Ticket, Eye, Play,
  ArrowUpRight, ArrowDownRight, CheckCircle2
} from 'lucide-react';
import { useSession } from '../../contexts/SessionContext';
import { classify, classifyColor } from '../../utils/healthThresholds';

// ─── Types ──────────────────────────────────────────────────────────────────

interface Account {
  id: number;
  name: string;
  health_score: number;
  arr: number;
  status: string;
  renewal_date: string | null;
  last_contact: string | null;
  days_to_renewal?: number;
  expansion_probability?: number;
  champion?: string;
  pillar_scores?: Record<string, number>;
}

interface DailyAction {
  id: number;
  account_id: number;
  account_name: string;
  action: string;
  urgency: 'critical' | 'high' | 'medium' | 'low' | 'opportunity';
  impact_score: number;
  playbook?: string;
  effort_hours?: number;
  projected_impact?: number;
}

interface Signal {
  id: number;
  date: string;
  type: string;
  subtype?: string;
  title: string;
  description: string;
  severity?: string;
}

interface Stakeholder {
  id: number;
  name: string;
  role: string;
  influence_score?: number;
  engagement_level?: string;
  email?: string;
}

interface SupportTicket {
  id: number;
  title: string;
  priority: string;
  status: string;
  created_at: string;
}

interface Approval {
  id: number;
  type: string;
  account_name: string;
  description: string;
  submitted_at: string;
}

interface CompletedItem {
  id: number;
  action: string;
  account_name: string;
  completed_at: string;
}

type TabKey = 'home' | 'board' | 'accounts' | 'reports';
type DrawerTab = 'overview' | 'signals' | 'people' | 'tickets' | 'history' | 'notes';
type GroupBy = 'urgency' | 'health' | 'arr';
type SortBy = 'impact' | 'arr' | 'renewal' | 'health';

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatARR(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const diff = new Date(dateStr).getTime() - Date.now();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

function daysSince(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const diff = Date.now() - new Date(dateStr).getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24));
}

function healthBadgeClasses(score: number): string {
  const cat = classify(score);
  if (cat === 'critical') return 'bg-red-100 text-red-700';
  if (cat === 'at_risk') return 'bg-amber-100 text-amber-700';
  return 'bg-emerald-100 text-emerald-700';
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

// ─── Kanban Card ────────────────────────────────────────────────────────────

interface KanbanCardProps {
  account: Account;
  action?: DailyAction;
  column: 'fire' | 'week' | 'opportunity';
  onClick: (account: Account) => void;
}

const KanbanCard: React.FC<KanbanCardProps> = ({ account, action, column, onClick }) => {
  const dtr = daysUntil(account.renewal_date);
  const dsc = daysSince(account.last_contact);

  const actionLabel = useMemo(() => {
    if (column === 'fire') return 'Escalate';
    if (column === 'opportunity') return 'Draft Proposal';
    if (action?.playbook) return 'Run PB';
    return 'Schedule';
  }, [column, action]);

  const actionColor = useMemo(() => {
    if (column === 'fire') return 'bg-red-600 hover:bg-red-700 text-white';
    if (column === 'opportunity') return 'bg-emerald-600 hover:bg-emerald-700 text-white';
    return 'bg-blue-600 hover:bg-blue-700 text-white';
  }, [column]);

  return (
    <div
      className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md hover:border-blue-300 transition-all cursor-pointer p-3"
      onClick={() => onClick(account)}
    >
      <div className="flex items-center justify-between mb-1.5">
        <span className="font-semibold text-sm text-gray-900 truncate mr-2">{account.name}</span>
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${healthBadgeClasses(account.health_score)}`}>
          {account.health_score}
        </span>
      </div>
      <div className="text-xs text-gray-500 mb-2">
        {column === 'opportunity' && account.expansion_probability != null ? (
          <span>{formatARR(account.arr)} &middot; {Math.round(account.expansion_probability * 100)}% expansion</span>
        ) : dtr != null ? (
          <span>{formatARR(account.arr)} &middot; {dtr}d to renewal</span>
        ) : dsc != null ? (
          <span>{formatARR(account.arr)} &middot; {dsc}d since contact</span>
        ) : (
          <span>{formatARR(account.arr)}</span>
        )}
      </div>
      <button
        className={`text-xs px-2.5 py-1 rounded font-medium ${actionColor}`}
        onClick={(e) => { e.stopPropagation(); }}
      >
        {actionLabel}
      </button>
    </div>
  );
};

// ─── Drawer ─────────────────────────────────────────────────────────────────

interface DrawerProps {
  account: Account | null;
  open: boolean;
  onClose: () => void;
  customerId: string;
  headers: Record<string, string>;
}

const AccountDrawer: React.FC<DrawerProps> = ({ account, open, onClose, customerId, headers }) => {
  const [tab, setTab] = useState<DrawerTab>('overview');
  const [signals, setSignals] = useState<Signal[]>([]);
  const [people, setPeople] = useState<Stakeholder[]>([]);
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [historyItems, setHistoryItems] = useState<DailyAction[]>([]);
  const [notes, setNotes] = useState('');
  const [loadingDetail, setLoadingDetail] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!account || !open) return;
    setTab('overview');
    setNotes('');
    setLoadingDetail(true);

    const fetchDetails = async () => {
      try {
        const [sigRes, recRes] = await Promise.allSettled([
          fetch(`/api/dc2s/alerts/${account.id}`, { headers }),
          fetch(`/api/dc2s/recommendations/${account.id}`, { headers }),
        ]);

        if (sigRes.status === 'fulfilled' && sigRes.value.ok) {
          const data = await sigRes.value.json();
          setSignals(data.signals || data.alerts || []);
          setPeople(data.stakeholders || []);
          setTickets(data.tickets || []);
        }
        if (recRes.status === 'fulfilled' && recRes.value.ok) {
          const data = await recRes.value.json();
          setHistoryItems(data.history || data.recommendations || []);
        }
      } catch {
        // fail silently, empty states handle display
      } finally {
        setLoadingDetail(false);
      }
    };

    fetchDetails();
  }, [account, open, headers]);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    if (open) window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!account) return null;

  const drawerTabs: { key: DrawerTab; label: string; icon: React.ReactNode }[] = [
    { key: 'overview', label: 'Overview', icon: <Eye className="w-3.5 h-3.5" /> },
    { key: 'signals', label: 'Signals', icon: <AlertTriangle className="w-3.5 h-3.5" /> },
    { key: 'people', label: 'People', icon: <Users className="w-3.5 h-3.5" /> },
    { key: 'tickets', label: 'Tickets', icon: <Ticket className="w-3.5 h-3.5" /> },
    { key: 'history', label: 'History', icon: <History className="w-3.5 h-3.5" /> },
    { key: 'notes', label: 'Notes', icon: <MessageSquare className="w-3.5 h-3.5" /> },
  ];

  const pillarNames: Record<string, string> = {
    P1: 'AI/ML Performance',
    P2: 'Infrastructure',
    P3: 'Cloud & DevOps',
    P4: 'Customer Engagement',
    P5: 'Commercial',
  };

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-black/20 z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Drawer panel */}
      <div
        ref={drawerRef}
        className={`fixed top-0 right-0 h-full w-[400px] bg-white shadow-2xl z-50 flex flex-col transform transition-transform duration-300 ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <div>
            <h3 className="font-semibold text-gray-900">{account.name}</h3>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${healthBadgeClasses(account.health_score)}`}>
              Health: {account.health_score}
            </span>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 px-2 overflow-x-auto">
          {drawerTabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex items-center gap-1 px-3 py-2 text-xs font-medium whitespace-nowrap border-b-2 transition ${
                tab === t.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loadingDetail ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : (
            <>
              {/* Overview Tab */}
              {tab === 'overview' && (
                <div className="space-y-4">
                  {/* Health bar */}
                  <div>
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>Health Score</span>
                      <span className="font-medium" style={{ color: classifyColor(account.health_score) }}>
                        {account.health_score}/100
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="h-2 rounded-full transition-all"
                        style={{
                          width: `${account.health_score}%`,
                          backgroundColor: classifyColor(account.health_score),
                        }}
                      />
                    </div>
                  </div>

                  {/* Pillar breakdown */}
                  <div>
                    <h4 className="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">Pillar Breakdown</h4>
                    <div className="space-y-1.5">
                      {account.pillar_scores
                        ? Object.entries(account.pillar_scores).map(([key, score]) => (
                            <div key={key} className="flex items-center gap-2">
                              <span className="text-xs text-gray-500 w-28 truncate">{pillarNames[key] || key}</span>
                              <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                                <div
                                  className="h-1.5 rounded-full"
                                  style={{
                                    width: `${score}%`,
                                    backgroundColor: classifyColor(score),
                                  }}
                                />
                              </div>
                              <span className="text-xs font-medium text-gray-600 w-8 text-right">{score}</span>
                            </div>
                          ))
                        : ['P1', 'P2', 'P3', 'P4', 'P5'].map((p) => (
                            <div key={p} className="flex items-center gap-2">
                              <span className="text-xs text-gray-500 w-28">{pillarNames[p]}</span>
                              <div className="flex-1 bg-gray-100 rounded-full h-1.5" />
                              <span className="text-xs text-gray-400 w-8 text-right">--</span>
                            </div>
                          ))}
                    </div>
                  </div>

                  {/* Champion info */}
                  <div>
                    <h4 className="text-xs font-semibold text-gray-700 mb-1 uppercase tracking-wide">Champion</h4>
                    <p className="text-sm text-gray-800">{account.champion || 'Not identified'}</p>
                  </div>

                  {/* Contract details */}
                  <div>
                    <h4 className="text-xs font-semibold text-gray-700 mb-1 uppercase tracking-wide">Contract</h4>
                    <div className="text-sm text-gray-600 space-y-1">
                      <div className="flex justify-between">
                        <span>ARR</span>
                        <span className="font-medium text-gray-900">{formatARR(account.arr)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Status</span>
                        <span className="font-medium text-gray-900 capitalize">{account.status}</span>
                      </div>
                      {account.renewal_date && (
                        <div className="flex justify-between">
                          <span>Renewal</span>
                          <span className="font-medium text-gray-900">
                            {new Date(account.renewal_date).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Signals Tab */}
              {tab === 'signals' && (
                <div className="space-y-2">
                  {signals.length === 0 ? (
                    <p className="text-sm text-gray-400 text-center py-8">No recent signals</p>
                  ) : (
                    signals.map((s) => (
                      <div key={s.id} className="border border-gray-100 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`w-2 h-2 rounded-full ${
                            s.severity === 'critical' ? 'bg-red-500' :
                            s.severity === 'high' ? 'bg-amber-500' :
                            s.severity === 'low' ? 'bg-emerald-500' : 'bg-gray-400'
                          }`} />
                          <span className="text-xs font-medium text-gray-900">{s.title}</span>
                        </div>
                        <p className="text-xs text-gray-500 line-clamp-2">{s.description}</p>
                        <span className="text-xs text-gray-400 mt-1 block">
                          {new Date(s.date).toLocaleDateString()}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* People Tab */}
              {tab === 'people' && (
                <div className="space-y-2">
                  {people.length === 0 ? (
                    <p className="text-sm text-gray-400 text-center py-8">No stakeholders found</p>
                  ) : (
                    people.map((p) => (
                      <div key={p.id} className="flex items-center justify-between border border-gray-100 rounded-lg p-3">
                        <div>
                          <span className="text-sm font-medium text-gray-900">{p.name}</span>
                          <span className="text-xs text-gray-500 block">{p.role}</span>
                        </div>
                        <div className="text-right">
                          {p.influence_score != null && (
                            <span className="text-xs font-medium text-blue-600">Influence: {p.influence_score}</span>
                          )}
                          {p.engagement_level && (
                            <span className="text-xs text-gray-400 block capitalize">{p.engagement_level}</span>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Tickets Tab */}
              {tab === 'tickets' && (
                <div className="space-y-2">
                  {tickets.length === 0 ? (
                    <p className="text-sm text-gray-400 text-center py-8">No open tickets</p>
                  ) : (
                    tickets.map((t) => (
                      <div key={t.id} className="border border-gray-100 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-900 truncate mr-2">{t.title}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            t.priority === 'critical' ? 'bg-red-100 text-red-700' :
                            t.priority === 'high' ? 'bg-amber-100 text-amber-700' :
                            'bg-gray-100 text-gray-600'
                          }`}>
                            {t.priority}
                          </span>
                        </div>
                        <div className="flex justify-between text-xs text-gray-400">
                          <span className="capitalize">{t.status}</span>
                          <span>{new Date(t.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* History Tab */}
              {tab === 'history' && (
                <div className="space-y-2">
                  {historyItems.length === 0 ? (
                    <p className="text-sm text-gray-400 text-center py-8">No playbook history</p>
                  ) : (
                    historyItems.map((h) => (
                      <div key={h.id} className="flex items-start gap-2 border border-gray-100 rounded-lg p-3">
                        <Play className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
                        <div>
                          <span className="text-sm font-medium text-gray-900">{h.action}</span>
                          {h.playbook && <span className="text-xs text-gray-500 block">{h.playbook}</span>}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Notes Tab */}
              {tab === 'notes' && (
                <div>
                  <textarea
                    className="w-full h-48 border border-gray-200 rounded-lg p-3 text-sm text-gray-800 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Add CSM notes for this account..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                  />
                  <p className="text-xs text-gray-400 mt-1">Notes are saved locally for this session.</p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Drawer action buttons */}
        <div className="border-t border-gray-200 p-3 flex items-center gap-2">
          <div className="relative group flex-1">
            <button className="w-full flex items-center justify-center gap-1 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 rounded-lg transition">
              <Play className="w-3.5 h-3.5" />
              Run Playbook
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
          </div>
          <button className="flex items-center gap-1 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium px-3 py-2 rounded-lg transition">
            <Mail className="w-3.5 h-3.5" />
            Draft Email
          </button>
          <button className="flex items-center gap-1 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium px-3 py-2 rounded-lg transition">
            <Sparkles className="w-3.5 h-3.5" />
            Ask AI
          </button>
        </div>
      </div>
    </>
  );
};

// ─── Main Component ─────────────────────────────────────────────────────────

const CSMCockpit: React.FC = () => {
  const { session } = useSession();
  const customerId = session?.customer_id?.toString() || '';
  const headers = useMemo(() => ({ 'X-Customer-ID': customerId }), [customerId]);

  // Nav state
  const [activeTab, setActiveTab] = useState<TabKey>('board');

  // Data state
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [actions, setActions] = useState<DailyAction[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [completedToday, setCompletedToday] = useState<CompletedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Board controls
  const [groupBy, setGroupBy] = useState<GroupBy>('urgency');
  const [sortBy, setSortBy] = useState<SortBy>('impact');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  // Drawer
  const [drawerAccount, setDrawerAccount] = useState<Account | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Account table search
  const [searchQuery, setSearchQuery] = useState('');

  // ── Data loading ──────────────────────────────────────────────────────

  const loadData = useCallback(async () => {
    if (!customerId) return;
    setLoading(true);
    setError(null);

    try {
      const [acctRes, actRes] = await Promise.allSettled([
        fetch('/api/dc2s/accounts', { headers }),
        fetch('/api/dc2s/daily-actions', { headers }),
      ]);

      if (acctRes.status === 'fulfilled' && acctRes.value.ok) {
        const data = await acctRes.value.json();
        const raw: any[] = data.accounts || data || [];
        // Map backend field names to component interface
        setAccounts((Array.isArray(raw) ? raw : []).map((a: any) => ({
          ...a,
          id: a.id ?? a.account_id,
          name: a.name ?? a.account_name ?? '',
          health_score: a.health_score ?? a.overall_health ?? 0,
          arr: a.arr ?? a.revenue ?? 0,
          status: a.status ?? a.account_status ?? '',
          pillar_scores: a.pillar_scores ?? {},
        })));
      } else {
        throw new Error('Failed to load accounts');
      }

      if (actRes.status === 'fulfilled' && actRes.value.ok) {
        const data = await actRes.value.json();
        const raw: any[] = data.actions || data || [];
        setActions((Array.isArray(raw) ? raw : []).map((a: any) => ({
          ...a,
          id: a.id ?? a.rank ?? 0,
          action: a.action || a.action_title || a.action_description || '',
          impact_score: a.impact_score ?? a.priority_index ?? 0,
          projected_impact: a.projected_impact ?? a.roi_projected_impact ?? 0,
        })));
      }

      // Load approvals (endpoint optional — may not exist)
      try {
        const appRes = await fetch('/api/approvals/pending', { headers });
        if (appRes.ok) {
          const data = await appRes.json();
          const appList = data.approvals || data.data || [];
          setApprovals(Array.isArray(appList) ? appList : []);
        } else {
          setApprovals([]);
        }
      } catch {
        setApprovals([]);
      }

      // Mock completed today (no dedicated API)
      setCompletedToday([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [customerId, headers]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Computed values ───────────────────────────────────────────────────

  const totalARR = useMemo(() => accounts.reduce((s, a) => s + (a.arr || 0), 0), [accounts]);

  const renewals30d = useMemo(
    () => accounts.filter((a) => {
      const d = daysUntil(a.renewal_date);
      return d !== null && d >= 0 && d <= 30;
    }).length,
    [accounts]
  );

  const criticalCount = useMemo(() => accounts.filter((a) => classify(a.health_score) === 'critical').length, [accounts]);
  const atRiskCount = useMemo(() => accounts.filter((a) => classify(a.health_score) === 'at_risk').length, [accounts]);
  const healthyCount = useMemo(() => accounts.filter((a) => classify(a.health_score) === 'healthy').length, [accounts]);

  // Column bucketing
  const actionsByAccount = useMemo(() => {
    const map: Record<number, DailyAction> = {};
    for (const a of actions) {
      if (!map[a.account_id] || a.impact_score > map[a.account_id].impact_score) {
        map[a.account_id] = a;
      }
    }
    return map;
  }, [actions]);

  const filteredAccounts = useMemo(() => {
    let list = [...accounts];
    if (filterStatus === 'critical') list = list.filter((a) => classify(a.health_score) === 'critical');
    else if (filterStatus === 'at_risk') list = list.filter((a) => classify(a.health_score) === 'at_risk');
    else if (filterStatus === 'healthy') list = list.filter((a) => classify(a.health_score) === 'healthy');
    return list;
  }, [accounts, filterStatus]);

  const sortFn = useCallback(
    (a: Account, b: Account) => {
      if (sortBy === 'impact') {
        const ia = actionsByAccount[a.id]?.impact_score || 0;
        const ib = actionsByAccount[b.id]?.impact_score || 0;
        return ib - ia;
      }
      if (sortBy === 'arr') return (b.arr || 0) - (a.arr || 0);
      if (sortBy === 'health') return a.health_score - b.health_score;
      if (sortBy === 'renewal') {
        const da = daysUntil(a.renewal_date) ?? 9999;
        const db = daysUntil(b.renewal_date) ?? 9999;
        return da - db;
      }
      return 0;
    },
    [sortBy, actionsByAccount]
  );

  const fireAccounts = useMemo(
    () => filteredAccounts
      .filter((a) => {
        const act = actionsByAccount[a.id];
        return classify(a.health_score) === 'critical' || act?.urgency === 'critical';
      })
      .sort(sortFn),
    [filteredAccounts, actionsByAccount, sortFn]
  );

  const weekAccounts = useMemo(
    () => filteredAccounts
      .filter((a) => {
        const act = actionsByAccount[a.id];
        return (
          classify(a.health_score) === 'at_risk' &&
          !fireAccounts.some((f) => f.id === a.id)
        ) || (act?.urgency === 'high' && !fireAccounts.some((f) => f.id === a.id));
      })
      .sort(sortFn),
    [filteredAccounts, actionsByAccount, fireAccounts, sortFn]
  );

  const opportunityAccounts = useMemo(
    () => filteredAccounts
      .filter((a) => {
        return (
          classify(a.health_score) === 'healthy' &&
          !fireAccounts.some((f) => f.id === a.id) &&
          !weekAccounts.some((w) => w.id === a.id)
        );
      })
      .sort(sortFn),
    [filteredAccounts, fireAccounts, weekAccounts, sortFn]
  );

  // Account table filtering
  const tableAccounts = useMemo(() => {
    let list = [...accounts];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter((a) => a.name.toLowerCase().includes(q));
    }
    return list.sort((a, b) => a.health_score - b.health_score);
  }, [accounts, searchQuery]);

  // Top 5 priority actions for Home
  const topActions = useMemo(() => actions.slice(0, 5), [actions]);

  // ── Handlers ──────────────────────────────────────────────────────────

  const openDrawer = useCallback((account: Account) => {
    setDrawerAccount(account);
    setDrawerOpen(true);
  }, []);

  const closeDrawer = useCallback(() => {
    setDrawerOpen(false);
    setTimeout(() => setDrawerAccount(null), 300);
  }, []);

  const handleApprove = useCallback((id: number) => {
    setApprovals((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const handleReject = useCallback((id: number) => {
    setApprovals((prev) => prev.filter((a) => a.id !== id));
  }, []);

  // ── Nav tabs ──────────────────────────────────────────────────────────

  const navTabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'home', label: 'Home', icon: <Home className="w-4 h-4" /> },
    { key: 'board', label: 'Board', icon: <Columns className="w-4 h-4" /> },
    { key: 'accounts', label: 'Accounts', icon: <Building2 className="w-4 h-4" /> },
    { key: 'reports', label: 'Reports', icon: <BarChart3 className="w-4 h-4" /> },
  ];

  // ── Render helpers ────────────────────────────────────────────────────

  const renderColumn = (
    title: string,
    accounts: Account[],
    column: 'fire' | 'week' | 'opportunity',
    accentColor: string,
    bgTint: string,
    icon: React.ReactNode
  ) => (
    <div className="flex-1 min-w-0 flex flex-col">
      <div className={`rounded-t-lg border-t-2 ${accentColor} ${bgTint} px-3 py-2 flex items-center justify-between`}>
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-semibold text-gray-800">{title}</span>
        </div>
        <span className="text-xs font-medium text-gray-500 bg-white rounded-full px-2 py-0.5">
          {accounts.length}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-2 p-2 bg-gray-50/50 border-x border-b border-gray-200 rounded-b-lg min-h-[200px] max-h-[calc(100vh-340px)]">
        {accounts.length === 0 ? (
          <p className="text-xs text-gray-400 text-center py-8">No accounts</p>
        ) : (
          accounts.map((acct) => (
            <KanbanCard
              key={acct.id}
              account={acct}
              action={actionsByAccount[acct.id]}
              column={column}
              onClick={openDrawer}
            />
          ))
        )}
      </div>
    </div>
  );

  // ── Dropdown component ────────────────────────────────────────────────

  const Dropdown: React.FC<{
    label: string;
    value: string;
    options: { value: string; label: string }[];
    onChange: (v: string) => void;
  }> = ({ label, value, options, onChange }) => (
    <div className="relative">
      <label className="text-xs text-gray-500 mr-1">{label}:</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 appearance-none pr-6 cursor-pointer"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
      <ChevronDown className="w-3 h-3 text-gray-400 absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none mt-2" />
    </div>
  );

  // ── Main render ───────────────────────────────────────────────────────

  if (!customerId) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <Shield className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Please log in to access the CSM Cockpit.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 overflow-hidden">
      {/* ── Top Navigation ─────────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200 px-4 py-0 flex items-center justify-between h-12 shrink-0">
        {/* Left: Logo + tabs */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-gray-900 text-sm">CS Pulse</span>
          </div>
          <nav className="flex items-center gap-1">
            {navTabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setActiveTab(t.key)}
                className={`flex items-center gap-1.5 px-3 py-3 text-sm font-medium border-b-2 transition ${
                  activeTab === t.key
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Right: notifications + avatar */}
        <div className="flex items-center gap-3">
          <button className="relative p-1.5 hover:bg-gray-100 rounded-lg transition">
            <Bell className="w-5 h-5 text-gray-500" />
            {(approvals.length > 0 || criticalCount > 0) && (
              <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                {approvals.length + criticalCount}
              </span>
            )}
          </button>
          <div className="w-8 h-8 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-semibold">
            {session?.user_name
              ? session.user_name
                  .split(' ')
                  .map((n) => n[0])
                  .join('')
                  .toUpperCase()
                  .slice(0, 2)
              : 'CS'}
          </div>
        </div>
      </header>

      {/* ── Portfolio Summary Strip ────────────────────────────────────── */}
      {activeTab === 'board' && (
        <div className="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between shrink-0">
          <div className="text-sm text-gray-600">
            <span className="font-semibold text-gray-900">{accounts.length}</span> accounts
            <span className="mx-1.5 text-gray-300">|</span>
            <span className="font-semibold text-gray-900">{formatARR(totalARR)}</span> ARR
            <span className="mx-1.5 text-gray-300">|</span>
            <span className="font-semibold text-gray-900">{renewals30d}</span> renewals in 30d
          </div>
          <div className="flex items-center gap-3">
            <Dropdown
              label="Filter"
              value={filterStatus}
              options={[
                { value: 'all', label: 'All' },
                { value: 'critical', label: 'Critical' },
                { value: 'at_risk', label: 'At-Risk' },
                { value: 'healthy', label: 'Healthy' },
              ]}
              onChange={(v) => setFilterStatus(v)}
            />
            <Dropdown
              label="Group by"
              value={groupBy}
              options={[
                { value: 'urgency', label: 'Urgency' },
                { value: 'health', label: 'Health' },
                { value: 'arr', label: 'ARR' },
              ]}
              onChange={(v) => setGroupBy(v as GroupBy)}
            />
            <Dropdown
              label="Sort"
              value={sortBy}
              options={[
                { value: 'impact', label: 'Impact' },
                { value: 'arr', label: 'ARR' },
                { value: 'renewal', label: 'Renewal' },
                { value: 'health', label: 'Health' },
              ]}
              onChange={(v) => setSortBy(v as SortBy)}
            />
            <button
              onClick={loadData}
              className="p-1.5 hover:bg-gray-100 rounded-lg transition"
              title="Refresh data"
            >
              <RefreshCw className={`w-4 h-4 text-gray-500 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      )}

      {/* ── Main Content ──────────────────────────────────────────────── */}
      <main className="flex-1 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Loader2 className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-3" />
              <p className="text-sm text-gray-500">Loading portfolio data...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-3" />
              <p className="text-sm text-gray-700 font-medium mb-2">Failed to load data</p>
              <p className="text-xs text-gray-500 mb-4">{error}</p>
              <button
                onClick={loadData}
                className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition"
              >
                Retry
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* ── HOME VIEW ──────────────────────────────────────────── */}
            {activeTab === 'home' && (
              <div className="p-6 max-w-5xl mx-auto overflow-y-auto h-full">
                <h1 className="text-2xl font-bold text-gray-900 mb-1">
                  {getGreeting()}, {session?.user_name?.split(' ')[0] || 'there'}
                </h1>
                <p className="text-sm text-gray-500 mb-6">
                  Here is your portfolio overview for today.
                </p>

                {/* Metric cards */}
                <div className="grid grid-cols-4 gap-4 mb-8">
                  <div className="bg-white rounded-xl border border-gray-200 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
                        <Flame className="w-4 h-4 text-red-600" />
                      </div>
                      <span className="text-xs text-gray-500 font-medium">Critical</span>
                    </div>
                    <span className="text-2xl font-bold text-gray-900">{criticalCount}</span>
                    <span className="text-xs text-gray-400 ml-1">accounts</span>
                  </div>
                  <div className="bg-white rounded-xl border border-gray-200 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-8 h-8 bg-amber-100 rounded-lg flex items-center justify-center">
                        <AlertTriangle className="w-4 h-4 text-amber-600" />
                      </div>
                      <span className="text-xs text-gray-500 font-medium">At-Risk</span>
                    </div>
                    <span className="text-2xl font-bold text-gray-900">{atRiskCount}</span>
                    <span className="text-xs text-gray-400 ml-1">accounts</span>
                  </div>
                  <div className="bg-white rounded-xl border border-gray-200 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      </div>
                      <span className="text-xs text-gray-500 font-medium">Healthy</span>
                    </div>
                    <span className="text-2xl font-bold text-gray-900">{healthyCount}</span>
                    <span className="text-xs text-gray-400 ml-1">accounts</span>
                  </div>
                  <div className="bg-white rounded-xl border border-gray-200 p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                        <Calendar className="w-4 h-4 text-blue-600" />
                      </div>
                      <span className="text-xs text-gray-500 font-medium">Renewals (30d)</span>
                    </div>
                    <span className="text-2xl font-bold text-gray-900">{renewals30d}</span>
                    <span className="text-xs text-gray-400 ml-1">upcoming</span>
                  </div>
                </div>

                {/* Priority actions */}
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <h2 className="text-sm font-semibold text-gray-900 mb-3">Top Priority Actions</h2>
                  {topActions.length === 0 ? (
                    <p className="text-sm text-gray-400 text-center py-6">No priority actions today.</p>
                  ) : (
                    <div className="space-y-2">
                      {topActions.map((a, i) => (
                        <div
                          key={a.id}
                          className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition cursor-pointer"
                          onClick={() => {
                            const acct = accounts.find((ac) => ac.id === a.account_id);
                            if (acct) openDrawer(acct);
                          }}
                        >
                          <span className="w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold shrink-0">
                            {i + 1}
                          </span>
                          <div className="flex-1 min-w-0">
                            <span className="text-sm font-medium text-gray-900 block truncate">{a.action}</span>
                            <span className="text-xs text-gray-500">{a.account_name}</span>
                          </div>
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                            a.urgency === 'critical' ? 'bg-red-100 text-red-700' :
                            a.urgency === 'high' ? 'bg-amber-100 text-amber-700' :
                            a.urgency === 'opportunity' ? 'bg-emerald-100 text-emerald-700' :
                            'bg-gray-100 text-gray-600'
                          }`}>
                            {a.urgency}
                          </span>
                          <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── BOARD VIEW ─────────────────────────────────────────── */}
            {activeTab === 'board' && (
              <div className="flex flex-col h-full">
                {/* Kanban columns */}
                <div className="flex-1 overflow-hidden px-4 py-3">
                  <div className="flex gap-4 h-full">
                    {renderColumn(
                      'FIRE',
                      fireAccounts,
                      'fire',
                      'border-red-500',
                      'bg-red-50/50',
                      <Flame className="w-4 h-4 text-red-500" />
                    )}
                    {renderColumn(
                      'THIS WEEK',
                      weekAccounts,
                      'week',
                      'border-amber-500',
                      'bg-amber-50/50',
                      <Clock className="w-4 h-4 text-amber-500" />
                    )}
                    {renderColumn(
                      'OPPORTUNITIES',
                      opportunityAccounts,
                      'opportunity',
                      'border-emerald-500',
                      'bg-emerald-50/50',
                      <TrendingUp className="w-4 h-4 text-emerald-500" />
                    )}
                  </div>
                </div>

                {/* Bottom bar */}
                <div className="bg-white border-t border-gray-200 px-4 py-2.5 grid grid-cols-2 gap-4 shrink-0">
                  {/* Approvals */}
                  <div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Approvals</span>
                      {approvals.length > 0 && (
                        <span className="text-[10px] font-bold bg-amber-100 text-amber-700 rounded-full px-1.5 py-0.5">
                          {approvals.length}
                        </span>
                      )}
                    </div>
                    {approvals.length === 0 ? (
                      <p className="text-xs text-gray-400">No pending approvals</p>
                    ) : (
                      <div className="space-y-1 max-h-20 overflow-y-auto">
                        {approvals.slice(0, 3).map((ap) => (
                          <div key={ap.id} className="flex items-center justify-between text-xs">
                            <span className="text-gray-700 truncate mr-2">
                              {ap.type} &mdash; {ap.account_name}
                            </span>
                            <div className="flex gap-1 shrink-0">
                              <button
                                onClick={() => handleApprove(ap.id)}
                                className="p-0.5 bg-emerald-100 hover:bg-emerald-200 text-emerald-700 rounded transition"
                                title="Approve"
                              >
                                <Check className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => handleReject(ap.id)}
                                className="p-0.5 bg-red-100 hover:bg-red-200 text-red-700 rounded transition"
                                title="Reject"
                              >
                                <XCircle className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Completed today */}
                  <div>
                    <span className="text-xs font-semibold text-gray-700 uppercase tracking-wide block mb-1.5">
                      Completed Today
                    </span>
                    {completedToday.length === 0 ? (
                      <p className="text-xs text-gray-400">No completed actions yet</p>
                    ) : (
                      <div className="space-y-1 max-h-20 overflow-y-auto">
                        {completedToday.map((c) => (
                          <div key={c.id} className="flex items-center gap-1.5 text-xs text-gray-600">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                            <span className="truncate">{c.action} &mdash; {c.account_name}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* ── ACCOUNTS VIEW ──────────────────────────────────────── */}
            {activeTab === 'accounts' && (
              <div className="p-4 h-full overflow-y-auto">
                <div className="max-w-6xl mx-auto">
                  {/* Search */}
                  <div className="mb-4 relative">
                    <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      placeholder="Search accounts..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-9 pr-4 py-2 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  {/* Table */}
                  <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-100">
                          <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Name</th>
                          <th className="text-center text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Health</th>
                          <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Status</th>
                          <th className="text-right text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">ARR</th>
                          <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Renewal</th>
                          <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3">Last Contact</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tableAccounts.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="text-center text-sm text-gray-400 py-12">
                              {searchQuery ? 'No accounts match your search.' : 'No accounts found.'}
                            </td>
                          </tr>
                        ) : (
                          tableAccounts.map((acct) => (
                            <tr
                              key={acct.id}
                              className="border-b border-gray-50 hover:bg-gray-50 transition cursor-pointer"
                              onClick={() => openDrawer(acct)}
                            >
                              <td className="px-4 py-3">
                                <span className="text-sm font-medium text-gray-900">{acct.name}</span>
                              </td>
                              <td className="px-4 py-3 text-center">
                                <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${healthBadgeClasses(acct.health_score)}`}>
                                  {acct.health_score}
                                </span>
                              </td>
                              <td className="px-4 py-3">
                                <span className="text-sm text-gray-600 capitalize">{acct.status}</span>
                              </td>
                              <td className="px-4 py-3 text-right">
                                <span className="text-sm font-medium text-gray-900">{formatARR(acct.arr)}</span>
                              </td>
                              <td className="px-4 py-3">
                                {acct.renewal_date ? (
                                  <span className="text-sm text-gray-600">
                                    {new Date(acct.renewal_date).toLocaleDateString()}
                                  </span>
                                ) : (
                                  <span className="text-sm text-gray-400">--</span>
                                )}
                              </td>
                              <td className="px-4 py-3">
                                {acct.last_contact ? (
                                  <span className="text-sm text-gray-600">
                                    {daysSince(acct.last_contact)}d ago
                                  </span>
                                ) : (
                                  <span className="text-sm text-gray-400">--</span>
                                )}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* ── REPORTS VIEW ───────────────────────────────────────── */}
            {activeTab === 'reports' && (
              <div className="p-6 max-w-5xl mx-auto overflow-y-auto h-full">
                <h2 className="text-lg font-bold text-gray-900 mb-4">Reports</h2>

                {/* Metric cards */}
                <div className="grid grid-cols-4 gap-4 mb-8">
                  <div className="bg-white rounded-xl border border-gray-200 p-4">
                    <span className="text-xs text-gray-500 font-medium block mb-1">Playbooks Completed</span>
                    <div className="flex items-end gap-1">
                      <span className="text-2xl font-bold text-gray-900">12</span>
                      <span className="text-xs text-gray-400 mb-1">this month</span>
                    </div>
                    <div className="flex items-center text-xs text-emerald-600 mt-1">
                      <ArrowUpRight className="w-3 h-3" />
                      <span>+20% vs last month</span>
                    </div>
                  </div>
                  <div className="bg-white rounded-xl border border-gray-200 p-4">
                    <span className="text-xs text-gray-500 font-medium block mb-1">Accounts Saved</span>
                    <div className="flex items-end gap-1">
                      <span className="text-2xl font-bold text-gray-900">3</span>
                      <span className="text-xs text-gray-400 mb-1">this quarter</span>
                    </div>
                    <div className="flex items-center text-xs text-emerald-600 mt-1">
                      <ArrowUpRight className="w-3 h-3" />
                      <span>$420K retained</span>
                    </div>
                  </div>
                  <div className="bg-white rounded-xl border border-gray-200 p-4">
                    <span className="text-xs text-gray-500 font-medium block mb-1">NPS Delta</span>
                    <div className="flex items-end gap-1">
                      <span className="text-2xl font-bold text-gray-900">+8</span>
                      <span className="text-xs text-gray-400 mb-1">points</span>
                    </div>
                    <div className="flex items-center text-xs text-emerald-600 mt-1">
                      <ArrowUpRight className="w-3 h-3" />
                      <span>Trending up</span>
                    </div>
                  </div>
                  <div className="bg-white rounded-xl border border-gray-200 p-4">
                    <span className="text-xs text-gray-500 font-medium block mb-1">Expansion Pipeline</span>
                    <div className="flex items-end gap-1">
                      <span className="text-2xl font-bold text-gray-900">{formatARR(850000)}</span>
                    </div>
                    <div className="flex items-center text-xs text-amber-600 mt-1">
                      <ArrowDownRight className="w-3 h-3" />
                      <span>5 opportunities</span>
                    </div>
                  </div>
                </div>

                {/* Weekly bar chart */}
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <h3 className="text-sm font-semibold text-gray-900 mb-4">Actions Completed Per Week</h3>
                  <div className="flex items-end gap-3 h-40">
                    {[
                      { label: 'W1', value: 8 },
                      { label: 'W2', value: 14 },
                      { label: 'W3', value: 11 },
                      { label: 'W4', value: 18 },
                    ].map((w) => {
                      const maxVal = 20;
                      const pct = Math.min((w.value / maxVal) * 100, 100);
                      return (
                        <div key={w.label} className="flex-1 flex flex-col items-center gap-1">
                          <span className="text-xs font-medium text-gray-700">{w.value}</span>
                          <div className="w-full bg-gray-100 rounded-t-md relative" style={{ height: '120px' }}>
                            <div
                              className="absolute bottom-0 left-0 right-0 bg-blue-500 rounded-t-md transition-all"
                              style={{ height: `${pct}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500">{w.label}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* ── Account Drawer ────────────────────────────────────────────── */}
      <AccountDrawer
        account={drawerAccount}
        open={drawerOpen}
        onClose={closeDrawer}
        customerId={customerId}
        headers={headers}
      />
    </div>
  );
};

export default CSMCockpit;
