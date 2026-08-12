/**
 * AccountsView - Portfolio Health: Goals -> Insights -> Actions
 * =============================================================
 * 2-panel layout: Main content (left) + Right context panel (sticky).
 * Matches the CRO overview pattern to reduce vertical scrolling and
 * keep portfolio context always visible.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  AlertTriangle, Search, ChevronDown, ChevronRight, Shield, DollarSign,
  Activity, Target, Clock, BookOpen, ArrowUpRight, BarChart3, LayoutGrid,
  TrendingUp, TrendingDown, Users,
} from 'lucide-react';
import { classify, classifyColor, thresholdValues } from '../../../utils/healthThresholds';
import { apiCall, getCustomerIdentifier } from '../../../utils/api';
import { useSession } from '../../../contexts/SessionContext';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Account {
  account_id: number | string;
  account_name: string;
  health_score: number;
  arr: number;
  status: string;
  signal_count?: number;
  days_since_intervention?: number;
}

interface PillarScores {
  P1: number;
  P2: number;
  P3: number;
  P4: number;
  P5: number;
  P6: number; // datacenter_v1 (GPU-rental neocloud) 6th pillar; 0 for 5-pillar verticals (never rendered — not in their PILLAR_KEYS)
}

type PillarKey = keyof PillarScores;
type SortField = 'health_score' | 'arr' | 'account_name' | 'status';
type SortDir = 'asc' | 'desc';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STATUS_COLORS: Record<string, string> = {
  healthy: '#16a34a',
  at_risk: '#ca8a04',
  critical: '#dc2626',
};

const STATUS_LABELS: Record<string, string> = {
  healthy: 'Healthy',
  at_risk: 'At Risk',
  critical: 'Critical',
};

const _vert = () => (localStorage.getItem('vertical') || 'dc2_s').toLowerCase().replace(/-/g, '_');
// Pillar columns are vertical-aware: datacenter_v1 has 6, others have 5.
// (Computed at module load; the page reloads on customer switch.)
const PILLAR_KEYS: PillarKey[] = (_vert() === 'datacenter_v1'
  ? ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']
  : ['P1', 'P2', 'P3', 'P4', 'P5']) as PillarKey[];

// Vertical-aware pillar names (resolved at render time from localStorage)
const _PILLAR_NAMES_MAP: Record<string, Record<string, string>> = {
  dc2_s: { P1: 'Deployment Velocity', P2: 'Operational Stability', P3: 'AI Workload Perf', P4: 'Channel & Partner', P5: 'Expansion Readiness' },
  datacenter_v1: { P1: 'Revenue & Economics', P2: 'Utilization & Goodput', P3: 'Reliability & SLA', P4: 'Power & Facility', P5: 'Commercial & Expansion', P6: 'Provisioning' },
  saas_premium: { P1: 'Product Adoption', P2: 'Customer Engagement', P3: 'Sentiment & Support', P4: 'Partner Health', P5: 'Revenue & Growth' },
  saas: { P1: 'Product Adoption', P2: 'Customer Engagement', P3: 'Sentiment & Support', P4: 'Partner Health', P5: 'Revenue & Growth' },
};
const _PILLAR_SHORT_MAP: Record<string, Record<string, string>> = {
  dc2_s: { P1: 'Deploy', P2: 'Ops', P3: 'AI Perf', P4: 'Channel', P5: 'Expand' },
  datacenter_v1: { P1: 'Revenue', P2: 'Util', P3: 'Reliab', P4: 'Power', P5: 'Commercial', P6: 'Provision' },
  saas_premium: { P1: 'Adoption', P2: 'Engage', P3: 'Sentiment', P4: 'Partner', P5: 'Revenue' },
  saas: { P1: 'Adoption', P2: 'Engage', P3: 'Sentiment', P4: 'Partner', P5: 'Revenue' },
};
const PILLAR_NAMES: Record<PillarKey, string> = new Proxy({} as Record<PillarKey, string>, {
  get: (_, key: string) => (_PILLAR_NAMES_MAP[_vert()] || _PILLAR_NAMES_MAP['dc2_s'])[key as PillarKey] || key,
});
const PILLAR_SHORT: Record<PillarKey, string> = new Proxy({} as Record<PillarKey, string>, {
  get: (_, key: string) => (_PILLAR_SHORT_MAP[_vert()] || _PILLAR_SHORT_MAP['dc2_s'])[key as PillarKey] || key,
});

const PILLAR_PLAYBOOK: Record<string, string> = {
  P1: 'PB-01', P2: 'PB-02', P3: 'PB-03', P4: 'PB-06', P5: 'PB-04', P6: 'PB-01',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtCurrency(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

function statusOrder(status: string): number {
  if (status === 'critical') return 0;
  if (status === 'at_risk') return 1;
  return 2;
}

function lowestPillar(pillars: PillarScores): { key: PillarKey; score: number } {
  let minKey: PillarKey = 'P1';
  let minVal = pillars.P1;
  for (const k of PILLAR_KEYS) {
    if (pillars[k] < minVal) { minVal = pillars[k]; minKey = k; }
  }
  return { key: minKey, score: minVal };
}

// ---------------------------------------------------------------------------
// Skeleton loaders
// ---------------------------------------------------------------------------

const Skel = ({ cls }: { cls: string }) => <div className={`bg-gray-700 rounded animate-pulse ${cls}`} />;

function SkeletonBlock({ rows }: { rows: string[] }) {
  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 animate-pulse space-y-3">
      {rows.map((c, i) => <Skel key={i} cls={c} />)}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CollapsibleSection({ title, count, color, defaultOpen, children }: {
  title: string; count: number; color: string; defaultOpen: boolean; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  if (count === 0) return null;
  const Arrow = open ? ChevronDown : ChevronRight;
  return (
    <div className="mb-4">
      <button type="button" onClick={() => setOpen(!open)}
        className="flex items-center gap-2 mb-3 w-full text-left">
        <Arrow className="w-4 h-4 text-gray-400" />
        <span className="text-sm font-semibold" style={{ color }}>{title}</span>
        <span className="text-xs font-medium px-2 py-0.5 rounded-full"
          style={{ backgroundColor: `${color}20`, color }}>{count}</span>
      </button>
      {open && children}
    </div>
  );
}

function ActionCard({ account, pillars, accentColor, onClick }: {
  account: Account; pillars?: PillarScores; accentColor: string; onClick: () => void;
}) {
  const lowest = pillars ? lowestPillar(pillars) : null;

  const daysText = account.days_since_intervention != null
    ? `${account.days_since_intervention}d since last action` : 'No recent actions';
  return (
    <button type="button" onClick={onClick}
      className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 text-left hover:border-opacity-80 transition-all w-full group"
      style={{ borderLeftWidth: 4, borderLeftColor: accentColor }}>
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1 min-w-0 mr-3">
          <h4 className="text-sm font-semibold text-white truncate">{account.account_name}</h4>
          <span className="text-xs text-gray-400">{fmtCurrency(account.arr)} ARR</span>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold" style={{ color: accentColor }}>{account.health_score}</div>
          <div className="text-[10px] text-gray-500 uppercase">Health</div>
        </div>
      </div>
      {lowest && (
        <div className="flex items-center gap-4 mb-3">
          <div className="flex items-center gap-1.5">
            <Target className="w-3.5 h-3.5 text-gray-500" />
            <span className="text-xs text-gray-400">Lowest: <span className="text-white font-medium">{PILLAR_SHORT[lowest.key]}: {Math.round(lowest.score * 10) / 10}</span></span>
          </div>
          <div className="flex items-center gap-1.5">
            <BookOpen className="w-3.5 h-3.5 text-gray-500" />
            <span className="text-xs text-gray-400">Run <span className="text-blue-400 font-medium">{PILLAR_PLAYBOOK[lowest.key]}</span></span>
          </div>
        </div>
      )}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-gray-500" />
          <span className="text-xs text-gray-400">{daysText}</span>
        </div>
        <ArrowUpRight className="w-4 h-4 text-gray-600 group-hover:text-blue-400 transition-colors" />
      </div>
    </button>
  );
}

function AccountGridCard({ account, pillars, onClick }: {
  account: Account; pillars?: PillarScores; onClick: () => void;
}) {
  const status = classify(account.health_score);
  const barColor = classifyColor(account.health_score);

  const lowest = pillars ? lowestPillar(pillars) : null;
  const risk = lowest && lowest.score < thresholdValues().healthy_min ? `${PILLAR_SHORT[lowest.key]}: ${(Math.round(lowest.score * 10) / 10).toFixed(1)}` : null;
  return (
    <button type="button" onClick={onClick}
      className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-5 text-left hover:border-blue-500/50 transition-colors w-full">
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-sm font-semibold text-white truncate pr-2">{account.account_name}</h3>
        <span className="text-xs text-gray-400 whitespace-nowrap">{fmtCurrency(account.arr)}</span>
      </div>
      <div className="mb-3">
        <div className="flex justify-between items-center mb-1">
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
            style={{ backgroundColor: `${STATUS_COLORS[status]}20`, color: STATUS_COLORS[status] }}>{STATUS_LABELS[status]}</span>
          <span className="text-xs font-medium" style={{ color: barColor }}>{account.health_score}</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-1.5">
          <div className="h-1.5 rounded-full transition-all"
            style={{ width: `${Math.min(account.health_score, 100)}%`, backgroundColor: barColor }} />
        </div>
      </div>
      {pillars && (
        <div className="mb-3 flex gap-1">
          {PILLAR_KEYS.map((key) => {
            const val = Math.round((pillars[key] ?? 0) * 10) / 10;
            return (
              <div key={key} className="flex-1" title={`${PILLAR_SHORT[key]}: ${val.toFixed(1)}`}>
                <div className="w-full bg-gray-700 rounded-full h-1">
                  <div className="h-1 rounded-full" style={{ width: `${Math.min(val, 100)}%`, backgroundColor: classifyColor(val) }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
      {risk && <div className="flex items-center gap-1 text-xs text-yellow-500"><AlertTriangle className="w-3 h-3" /><span>{risk}</span></div>}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Right Panel Sub-components
// ---------------------------------------------------------------------------

function StatMiniCard({ icon, label, value, valueColor }: {
  icon: React.ReactNode; label: string; value: string; valueColor?: string;
}) {
  return (
    <div className="bg-[#161b22] rounded-lg border border-gray-700/40 p-3">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">{label}</span>
      </div>
      <div className="text-lg font-bold" style={{ color: valueColor || '#e5e7eb' }}>{value}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function AccountsView() {
  const { session } = useSession();
  const customerId = getCustomerIdentifier(session);
  const [searchParams, setSearchParams] = useSearchParams();
  const arcFilter = searchParams.get('arc') || '';

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [pillarMap, setPillarMap] = useState<Record<string, PillarScores>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<SortField>('health_score');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [sortOpen, setSortOpen] = useState(false);

  // ---- Data fetching -------------------------------------------------------

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        const res = await apiCall('/api/accounts', {
          headers: { 'X-Customer-ID': customerId },
        });
        if (!res.ok) throw new Error(`Accounts API returned ${res.status}`);
        const data = await res.json();

        const acctList: Account[] = (data.accounts ?? data ?? []).map((a: any) => ({
          account_id: a.account_id ?? a.id,
          account_name: a.account_name ?? a.name ?? `Account ${a.account_id ?? a.id}`,
          health_score: a.health_score ?? 50,
          arr: a.arr ?? a.revenue ?? 0,
          status: classify(a.health_score ?? 50),
          signal_count: a.signal_count ?? a.signals ?? undefined,
          days_since_intervention: a.days_since_intervention ?? undefined,
        }));

        if (cancelled) return;
        setAccounts(acctList);

        // Fetch pillar scores for each account in parallel
        // Uses /api/dc2s/scores/account/<id>/latest which returns
        // health_score.contributing_pillars with P1-P5 values
        const pillarEntries = await Promise.allSettled(
          acctList.map(async (acct) => {
            const pRes = await apiCall(
              `/api/dc2s/scores/account/${acct.account_id}/latest`,
              { headers: { 'X-Customer-ID': customerId } },
            );
            if (!pRes.ok) return null;
            const pData = await pRes.json();
            // contributing_pillars lives inside the health_score object
            const cp = pData.health_score?.contributing_pillars
                    ?? pData.contributing_pillars
                    ?? pData.pillar_scores
                    ?? {};
            const scores: PillarScores = {
              P1: cp.P1 ?? cp.p1 ?? 0,
              P2: cp.P2 ?? cp.p2 ?? 0,
              P3: cp.P3 ?? cp.p3 ?? 0,
              P4: cp.P4 ?? cp.p4 ?? 0,
              P5: cp.P5 ?? cp.p5 ?? 0,
              P6: cp.P6 ?? cp.p6 ?? 0, // present only for datacenter_v1; unused by 5-pillar verticals
            };
            return [String(acct.account_id), scores] as const;
          }),
        );

        if (cancelled) return;

        const pMap: Record<string, PillarScores> = {};
        for (const entry of pillarEntries) {
          if (entry.status === 'fulfilled' && entry.value) {
            pMap[entry.value[0]] = entry.value[1];
          }
        }
        setPillarMap(pMap);
      } catch (err: any) {
        if (!cancelled) setError(err.message ?? 'Failed to load accounts');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => { cancelled = true; };
  }, [customerId]);

  // ---- Derived data --------------------------------------------------------

  const { healthy_min, at_risk_min } = thresholdValues();

  const { criticalAccounts, atRiskAccounts, healthyAccounts } = useMemo(() => {
    const critical: Account[] = [];
    const atRisk: Account[] = [];
    const healthy: Account[] = [];
    for (const a of accounts) {
      const s = classify(a.health_score);
      if (s === 'critical') critical.push(a);
      else if (s === 'at_risk') atRisk.push(a);
      else healthy.push(a);
    }
    // Sort worst-first within each group
    critical.sort((a, b) => a.health_score - b.health_score);
    atRisk.sort((a, b) => a.health_score - b.health_score);
    healthy.sort((a, b) => b.health_score - a.health_score);
    return { criticalAccounts: critical, atRiskAccounts: atRisk, healthyAccounts: healthy };
  }, [accounts]);

  const totalArr = useMemo(() => accounts.reduce((s, a) => s + a.arr, 0), [accounts]);

  const avgHealthScore = useMemo(() => {
    if (accounts.length === 0) return 0;
    return Math.round(accounts.reduce((s, a) => s + a.health_score, 0) / accounts.length);
  }, [accounts]);

  const revenueAtRisk = useMemo(
    () => accounts.filter((a) => a.health_score < healthy_min).reduce((s, a) => s + a.arr, 0),
    [accounts, healthy_min],
  );

  const revenueDonut = useMemo(() => {
    const buckets = { healthy: 0, at_risk: 0, critical: 0 };
    for (const a of accounts) {
      buckets[classify(a.health_score)] += a.arr;
    }
    return [
      { name: 'Healthy', value: buckets.healthy, color: STATUS_COLORS.healthy },
      { name: 'At Risk', value: buckets.at_risk, color: STATUS_COLORS.at_risk },
      { name: 'Critical', value: buckets.critical, color: STATUS_COLORS.critical },
    ].filter((d) => d.value > 0);
  }, [accounts]);

  // Health count distribution for donut (right panel)
  const healthCountDonut = useMemo(() => {
    return [
      { name: 'Healthy', value: healthyAccounts.length, color: STATUS_COLORS.healthy },
      { name: 'At Risk', value: atRiskAccounts.length, color: STATUS_COLORS.at_risk },
      { name: 'Critical', value: criticalAccounts.length, color: STATUS_COLORS.critical },
    ].filter((d) => d.value > 0);
  }, [healthyAccounts, atRiskAccounts, criticalAccounts]);

  // Revenue by status for stacked bar (right panel)
  const revenueByStatus = useMemo(() => {
    const buckets = { healthy: 0, at_risk: 0, critical: 0 };
    for (const a of accounts) {
      buckets[classify(a.health_score)] += a.arr;
    }
    const total = buckets.healthy + buckets.at_risk + buckets.critical;
    return {
      buckets,
      total,
      pctHealthy: total > 0 ? (buckets.healthy / total) * 100 : 0,
      pctAtRisk: total > 0 ? (buckets.at_risk / total) * 100 : 0,
      pctCritical: total > 0 ? (buckets.critical / total) * 100 : 0,
    };
  }, [accounts]);

  // Portfolio pillar averages (right panel)
  const pillarAverages = useMemo(() => {
    const sums: Record<PillarKey, number> = { P1: 0, P2: 0, P3: 0, P4: 0, P5: 0, P6: 0 };
    const counts: Record<PillarKey, number> = { P1: 0, P2: 0, P3: 0, P4: 0, P5: 0, P6: 0 };
    for (const acct of accounts) {
      const ps = pillarMap[String(acct.account_id)];
      if (!ps) continue;
      for (const k of PILLAR_KEYS) {
        sums[k] += ps[k];
        counts[k]++;
      }
    }
    return PILLAR_KEYS.map((k) => ({
      key: k,
      name: PILLAR_SHORT[k],
      fullName: PILLAR_NAMES[k],
      avg: counts[k] > 0 ? Math.round(sums[k] / counts[k]) : 0,
    }));
  }, [accounts, pillarMap]);

  // Best and worst accounts
  const { bestAccount, worstAccount } = useMemo(() => {
    if (accounts.length === 0) return { bestAccount: null, worstAccount: null };
    const sorted = [...accounts].sort((a, b) => a.health_score - b.health_score);
    return { bestAccount: sorted[sorted.length - 1], worstAccount: sorted[0] };
  }, [accounts]);

  // Sorted accounts for heatmap (worst first)
  const heatmapAccounts = useMemo(
    () => [...accounts].sort((a, b) => a.health_score - b.health_score),
    [accounts],
  );

  // Filtered + sorted for grid
  const filteredSorted = useMemo(() => {
    let list = accounts;
    if (searchTerm) {
      const lower = searchTerm.toLowerCase();
      list = list.filter((a) => a.account_name.toLowerCase().includes(lower));
    }
    list = [...list].sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'health_score': cmp = a.health_score - b.health_score; break;
        case 'arr': cmp = a.arr - b.arr; break;
        case 'account_name': cmp = a.account_name.localeCompare(b.account_name); break;
        case 'status':
          cmp = statusOrder(classify(a.health_score)) - statusOrder(classify(b.health_score)); break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return list;
  }, [accounts, searchTerm, sortField, sortDir]);

  // ---- Sort helpers --------------------------------------------------------

  const sortOptions: { field: SortField; label: string }[] = [
    { field: 'health_score', label: 'Health Score' },
    { field: 'arr', label: 'Revenue' },
    { field: 'account_name', label: 'Name' },
    { field: 'status', label: 'Status' },
  ];

  function handleSortSelect(field: SortField) {
    if (field === sortField) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir(field === 'account_name' ? 'asc' : 'desc');
    }
    setSortOpen(false);
  }

  function navigateToAccount(id: number | string) {
    window.location.hash = `#/account/${id}`;
  }

  // ---- Render: Error -------------------------------------------------------

  if (error) {
    return (
      <div className="min-h-screen bg-[#0f1419] flex items-center justify-center p-8">
        <div className="bg-[#1a1f2e] border border-red-500/30 rounded-xl p-8 max-w-md text-center">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <h2 className="text-white text-lg font-semibold mb-2">Failed to Load Accounts</h2>
          <p className="text-gray-400 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  // ---- Render: Loading skeleton --------------------------------------------

  if (loading) {
    return (
      <div className="flex h-full">
        <div className="flex-1 overflow-y-auto">
          <div className="p-6 max-w-[1200px] space-y-6">
            <SkeletonBlock rows={['h-6 w-1/3', 'h-4 w-2/3']} />
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => <SkeletonBlock key={i} rows={['h-4 w-1/3', 'h-8 w-1/2', 'h-3 w-2/3']} />)}
            </div>
            <SkeletonBlock rows={['h-4 w-1/3', 'h-32 w-full']} />
          </div>
        </div>
        <div className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 space-y-4">
          {[1, 2, 3, 4].map((i) => <SkeletonBlock key={i} rows={['h-3 w-1/2', 'h-6 w-3/4']} />)}
        </div>
      </div>
    );
  }

  // ---- Render: Main --------------------------------------------------------

  const totalAccounts = accounts.length;

  return (
    <div className="flex h-full">

      {/* ================================================================== */}
      {/* MAIN CONTENT (left, scrollable)                                    */}
      {/* ================================================================== */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-[1200px] space-y-6">

          {/* --- SECTION 1: MISSION BANNER --- */}
          <div className="relative rounded-xl overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-[#1a1f2e] via-[#1e2538] to-[#1a1f2e]" />
            <div className="absolute top-0 left-0 right-0 h-1 flex">
              {totalAccounts > 0 && (<>
                <div className="h-full" style={{ width: `${(healthyAccounts.length / totalAccounts) * 100}%`, backgroundColor: STATUS_COLORS.healthy }} />
                <div className="h-full" style={{ width: `${(atRiskAccounts.length / totalAccounts) * 100}%`, backgroundColor: STATUS_COLORS.at_risk }} />
                <div className="h-full" style={{ width: `${(criticalAccounts.length / totalAccounts) * 100}%`, backgroundColor: STATUS_COLORS.critical }} />
              </>)}
            </div>
            {/* Arc filter banner (when navigated from story arc click) */}
            {arcFilter && (
              <div className="flex items-center gap-2 px-4 py-2 mb-3 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span className="text-xs text-cyan-400 font-medium">Filtered by arc: {arcFilter.replace(/_/g, ' ')}</span>
                <button
                  onClick={() => setSearchParams({ view: 'accounts' })}
                  className="ml-auto text-[10px] text-gray-400 hover:text-white"
                >
                  Clear filter
                </button>
              </div>
            )}
            <div className="relative px-8 py-7 border border-gray-700/50 rounded-xl">
              <div className="flex items-center gap-3 mb-2">
                <Shield className="w-6 h-6 text-blue-400" />
                <h1 className="text-xl font-bold text-white">
                  Portfolio Health
                  <span className="text-gray-400 font-normal ml-2 text-base">{totalAccounts} accounts, {fmtCurrency(totalArr)} ARR</span>
                </h1>
              </div>
              <p className="text-sm text-gray-400 ml-9">
                <span className="text-green-400 font-medium">{healthyAccounts.length} Healthy</span>{' \u00B7 '}
                <span className="text-yellow-500 font-medium">{atRiskAccounts.length} At Risk</span>{' \u00B7 '}
                <span className="text-red-400 font-medium">{criticalAccounts.length} Critical</span>
                {revenueAtRisk > 0 && <>{' | '}<span className="text-red-400 font-semibold">{fmtCurrency(revenueAtRisk)}</span>
                  <span className="text-gray-500"> revenue needs attention</span></>}
              </p>
            </div>
          </div>

          {/* --- SECTION 2: WHAT NEEDS ATTENTION --- */}
          <div>
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-500" />
              What Needs Attention
            </h2>

            {/* Critical Accounts */}
            <CollapsibleSection
              title="Critical Accounts"
              count={criticalAccounts.length}
              color={STATUS_COLORS.critical}
              defaultOpen
            >
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {criticalAccounts.map((acct) => (
                  <ActionCard
                    key={String(acct.account_id)}
                    account={acct}
                    pillars={pillarMap[String(acct.account_id)]}
                    accentColor={STATUS_COLORS.critical}
                    onClick={() => navigateToAccount(acct.account_id)}
                  />
                ))}
              </div>
            </CollapsibleSection>

            {/* At-Risk Accounts */}
            <CollapsibleSection
              title="At-Risk Accounts"
              count={atRiskAccounts.length}
              color={STATUS_COLORS.at_risk}
              defaultOpen
            >
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {atRiskAccounts.map((acct) => (
                  <ActionCard
                    key={String(acct.account_id)}
                    account={acct}
                    pillars={pillarMap[String(acct.account_id)]}
                    accentColor={STATUS_COLORS.at_risk}
                    onClick={() => navigateToAccount(acct.account_id)}
                  />
                ))}
              </div>
            </CollapsibleSection>

            {criticalAccounts.length === 0 && atRiskAccounts.length === 0 && (
              <div className="bg-[#1a1f2e] rounded-xl border border-green-500/20 p-6 text-center">
                <Shield className="w-8 h-8 text-green-400 mx-auto mb-2" />
                <p className="text-green-400 font-medium text-sm">All accounts are healthy</p>
                <p className="text-gray-500 text-xs mt-1">No immediate actions required</p>
              </div>
            )}
          </div>

          {/* --- SECTION 3: PILLAR PERFORMANCE HEATMAP --- */}
          <div>
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2">
              <LayoutGrid className="w-4 h-4 text-purple-400" />
              Pillar Performance Heatmap
            </h2>

            <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700/50">
                      <th className="text-left text-xs text-gray-400 font-medium px-4 py-3 min-w-[180px]">Account</th>
                      <th className="text-center text-xs text-gray-400 font-medium px-2 py-3 w-16">Health</th>
                      {PILLAR_KEYS.map((k) => (
                        <th key={k} className="text-center text-xs text-gray-400 font-medium px-2 py-3 w-24">
                          <div>{k}</div>
                          <div className="text-[10px] text-gray-500 font-normal">{PILLAR_SHORT[k]}</div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {heatmapAccounts.map((acct, idx) => {
                      const pScores = pillarMap[String(acct.account_id)];
                      const rowBg = idx % 2 === 0 ? 'bg-[#1a1f2e]' : 'bg-[#181d28]';
                      return (
                        <tr key={String(acct.account_id)} onClick={() => navigateToAccount(acct.account_id)}
                          className={`border-b border-gray-800/50 cursor-pointer hover:bg-gray-700/20 ${rowBg}`}>
                          <td className="px-4 py-2.5">
                            <div className="text-xs text-white font-medium truncate max-w-[180px]">{acct.account_name}</div>
                            <div className="text-[10px] text-gray-500">{fmtCurrency(acct.arr)}</div>
                          </td>
                          <td className="px-2 py-2.5 text-center">
                            <span className="text-xs font-bold" style={{ color: classifyColor(acct.health_score) }}>{acct.health_score}</span>
                          </td>
                          {PILLAR_KEYS.map((k) => {
                            const rawVal = pScores?.[k] ?? 0;
                            const val = Math.round(rawVal * 10) / 10;
                            const cc = classifyColor(val);
                            const op = classify(val) === 'critical' ? '30' : classify(val) === 'at_risk' ? '20' : '15';
                            return (
                              <td key={k} className="px-2 py-2.5 text-center" style={{ backgroundColor: `${cc}${op}` }}>
                                <span className="text-xs font-semibold" style={{ color: cc }}>{pScores ? val.toFixed(1) : '--'}</span>
                              </td>
                            );
                          })}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {accounts.length === 0 && <div className="text-center text-gray-500 py-8 text-sm">No accounts to display</div>}
            </div>
          </div>

          {/* --- SECTION 4: ALL ACCOUNTS GRID --- */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                All Accounts
              </h2>
              <span className="text-xs text-gray-500">
                {filteredSorted.length} of {totalAccounts} accounts
              </span>
            </div>

            {/* Grid */}
            {filteredSorted.length === 0 ? (
              <div className="text-center text-gray-500 py-12">
                No accounts match your search.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {filteredSorted.map((acct) => (
                  <AccountGridCard
                    key={String(acct.account_id)}
                    account={acct}
                    pillars={pillarMap[String(acct.account_id)]}
                    onClick={() => navigateToAccount(acct.account_id)}
                  />
                ))}
              </div>
            )}
          </div>

        </div>
      </div>

      {/* ================================================================== */}
      {/* RIGHT CONTEXT PANEL (sticky, scrollable)                           */}
      {/* ================================================================== */}
      <div className="w-80 flex-shrink-0 bg-[#0d1117] border-l border-gray-700/50 py-6 px-4 overflow-y-auto flex flex-col gap-5">

        {/* --- Portfolio Stats (4 mini cards) --- */}
        <div>
          <h3 className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold mb-3">Portfolio Stats</h3>
          <div className="grid grid-cols-2 gap-2">
            <StatMiniCard
              icon={<DollarSign className="w-3.5 h-3.5 text-green-400" />}
              label="Total ARR"
              value={fmtCurrency(totalArr)}
              valueColor="#16a34a"
            />
            <StatMiniCard
              icon={<Activity className="w-3.5 h-3.5 text-blue-400" />}
              label="Avg Health"
              value={String(avgHealthScore)}
              valueColor={classifyColor(avgHealthScore)}
            />
            <StatMiniCard
              icon={<AlertTriangle className="w-3.5 h-3.5 text-red-400" />}
              label="Rev at Risk"
              value={fmtCurrency(revenueAtRisk)}
              valueColor={revenueAtRisk > 0 ? '#dc2626' : '#16a34a'}
            />
            <StatMiniCard
              icon={<Users className="w-3.5 h-3.5 text-gray-400" />}
              label="Accounts"
              value={String(totalAccounts)}
            />
          </div>
          {/* Best / Worst account */}
          {bestAccount && worstAccount && (
            <div className="mt-2 space-y-1.5">
              <div className="flex items-center justify-between bg-[#161b22] rounded-lg border border-gray-700/40 px-3 py-2">
                <div className="flex items-center gap-1.5">
                  <TrendingUp className="w-3 h-3 text-green-400" />
                  <span className="text-[10px] text-gray-500 uppercase">Best</span>
                </div>
                <div className="text-right">
                  <span className="text-xs text-white font-medium truncate max-w-[120px] inline-block">{bestAccount.account_name}</span>
                  <span className="text-xs font-bold ml-2" style={{ color: classifyColor(bestAccount.health_score) }}>{bestAccount.health_score}</span>
                </div>
              </div>
              <div className="flex items-center justify-between bg-[#161b22] rounded-lg border border-gray-700/40 px-3 py-2">
                <div className="flex items-center gap-1.5">
                  <TrendingDown className="w-3 h-3 text-red-400" />
                  <span className="text-[10px] text-gray-500 uppercase">Worst</span>
                </div>
                <div className="text-right">
                  <span className="text-xs text-white font-medium truncate max-w-[120px] inline-block">{worstAccount.account_name}</span>
                  <span className="text-xs font-bold ml-2" style={{ color: classifyColor(worstAccount.health_score) }}>{worstAccount.health_score}</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* --- Health Distribution (mini donut) --- */}
        <div>
          <h3 className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold mb-3">Health Distribution</h3>
          <div className="bg-[#161b22] rounded-lg border border-gray-700/40 p-3">
            {healthCountDonut.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={130}>
                  <PieChart>
                    <Pie
                      data={healthCountDonut}
                      cx="50%"
                      cy="50%"
                      innerRadius={35}
                      outerRadius={55}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {healthCountDonut.map((entry, idx) => (
                        <Cell key={idx} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1a1f2e', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }}
                      itemStyle={{ color: '#d1d5db' }}
                      formatter={(value: number, name: string) => [`${value} accounts`, name]}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex flex-col gap-1 mt-1">
                  {healthCountDonut.map((d) => (
                    <div key={d.name} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
                        <span className="text-gray-400">{d.name}</span>
                      </div>
                      <span className="text-white font-medium">{d.value}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-center text-gray-500 text-xs py-4">No data</div>
            )}
          </div>
        </div>

        {/* --- Revenue by Status (stacked bar) --- */}
        <div>
          <h3 className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold mb-3">Revenue by Status</h3>
          <div className="bg-[#161b22] rounded-lg border border-gray-700/40 p-3">
            {revenueByStatus.total > 0 ? (
              <>
                {/* Stacked horizontal bar */}
                <div className="flex h-5 rounded overflow-hidden mb-3">
                  {revenueByStatus.pctHealthy > 0 && (
                    <div
                      className="h-full"
                      style={{ width: `${revenueByStatus.pctHealthy}%`, backgroundColor: STATUS_COLORS.healthy }}
                      title={`Healthy: ${fmtCurrency(revenueByStatus.buckets.healthy)}`}
                    />
                  )}
                  {revenueByStatus.pctAtRisk > 0 && (
                    <div
                      className="h-full"
                      style={{ width: `${revenueByStatus.pctAtRisk}%`, backgroundColor: STATUS_COLORS.at_risk }}
                      title={`At Risk: ${fmtCurrency(revenueByStatus.buckets.at_risk)}`}
                    />
                  )}
                  {revenueByStatus.pctCritical > 0 && (
                    <div
                      className="h-full"
                      style={{ width: `${revenueByStatus.pctCritical}%`, backgroundColor: STATUS_COLORS.critical }}
                      title={`Critical: ${fmtCurrency(revenueByStatus.buckets.critical)}`}
                    />
                  )}
                </div>
                {/* Legend */}
                <div className="flex flex-col gap-1">
                  {[
                    { label: 'Healthy', value: revenueByStatus.buckets.healthy, color: STATUS_COLORS.healthy },
                    { label: 'At Risk', value: revenueByStatus.buckets.at_risk, color: STATUS_COLORS.at_risk },
                    { label: 'Critical', value: revenueByStatus.buckets.critical, color: STATUS_COLORS.critical },
                  ].filter((d) => d.value > 0).map((d) => (
                    <div key={d.label} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color }} />
                        <span className="text-gray-400">{d.label}</span>
                      </div>
                      <span className="text-white font-medium">{fmtCurrency(d.value)}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-center text-gray-500 text-xs py-4">No revenue data</div>
            )}
          </div>
        </div>

        {/* --- Pillar Averages (P1-P5 horizontal bars) --- */}
        <div>
          <h3 className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold mb-3">Pillar Averages</h3>
          <div className="bg-[#161b22] rounded-lg border border-gray-700/40 p-3 space-y-2.5">
            {pillarAverages.map((p) => {
              const barCol = classifyColor(p.avg);
              return (
                <div key={p.key} title={p.fullName}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-gray-400">{p.key} {p.name}</span>
                    <span className="text-xs font-semibold" style={{ color: barCol }}>{p.avg}</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-1.5">
                    <div
                      className="h-1.5 rounded-full transition-all"
                      style={{ width: `${Math.min(p.avg, 100)}%`, backgroundColor: barCol }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* --- Search & Filter (compact controls) --- */}
        <div>
          <h3 className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold mb-3">Search & Filter</h3>
          <div className="space-y-2">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
              <input
                type="text"
                placeholder="Search accounts..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 bg-[#161b22] border border-gray-700/40 rounded-lg
                           text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50"
              />
            </div>

            {/* Sort dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setSortOpen(!sortOpen)}
                className="flex items-center justify-between w-full px-3 py-1.5 bg-[#161b22] border border-gray-700/40
                           rounded-lg text-xs text-gray-300 hover:border-blue-500/50"
              >
                <span>Sort: {sortOptions.find((o) => o.field === sortField)?.label}</span>
                <span className="flex items-center gap-1">
                  <span className="text-[10px]">{sortDir === 'asc' ? '\u25B2' : '\u25BC'}</span>
                  <ChevronDown className="w-3 h-3" />
                </span>
              </button>
              {sortOpen && (
                <div className="absolute left-0 right-0 mt-1 bg-[#161b22] border border-gray-700/40
                                rounded-lg shadow-xl z-10">
                  {sortOptions.map((opt) => (
                    <button
                      key={opt.field}
                      type="button"
                      onClick={() => handleSortSelect(opt.field)}
                      className={`block w-full text-left px-3 py-1.5 text-xs hover:bg-gray-700/30 ${
                        sortField === opt.field ? 'text-blue-400' : 'text-gray-300'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="text-[10px] text-gray-600 text-center pt-1">
              {filteredSorted.length} of {totalAccounts} shown
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
