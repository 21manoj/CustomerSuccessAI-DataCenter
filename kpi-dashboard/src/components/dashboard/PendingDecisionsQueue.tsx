/**
 * PendingDecisionsQueue — right-sidebar widget for CRO + CFO dashboards.
 *
 * Read-only v1. Surfaces 5 items awaiting executive decision, drawn from
 * in-flight playbooks, untreated at-risk accounts, and open expansion
 * signals. Persona prop drives sort order and headline framing.
 *
 * Data source: GET /api/executive/pending-decisions?persona=cro|cfo
 */
import React, { useEffect, useState } from 'react';
import { AlertTriangle, DollarSign, TrendingUp, Clock, ChevronRight } from 'lucide-react';
import { apiCall, getCustomerIdentifier } from '../../utils/api';
import { useSession } from '../../contexts/SessionContext';

type Persona = 'cro' | 'cfo';
type Urgency = 'high' | 'medium' | 'low';
type Kind =
  | 'playbook_in_flight'
  | 'at_risk_no_playbook'
  | 'expansion_open'
  | 'flagged_decision';

interface DecisionItem {
  decision_id: string;
  kind: Kind;
  account_id: number;
  account_name: string;
  headline: string;
  rationale: string;
  dollar_amount: number;
  revenue_at_stake: number;
  urgency: Urgency;
  occurred_at: string;
  source: { type: string; id: string | number };
}

interface ApiResponse {
  persona: Persona;
  customer_id: number;
  items: DecisionItem[];
  generated_at: string;
}

interface Props {
  persona: Persona;
}

function formatCompactUSD(value: number): string {
  if (!value || value === 0) return '$0';
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `$${(value / 1_000).toFixed(0)}K`;
  return `$${value.toFixed(0)}`;
}

const URGENCY_STYLES: Record<Urgency, { dot: string; text: string; bg: string }> = {
  high: { dot: 'bg-red-400', text: 'text-red-300', bg: 'bg-red-500/10 border-red-500/20' },
  medium: { dot: 'bg-amber-400', text: 'text-amber-300', bg: 'bg-amber-500/10 border-amber-500/20' },
  low: { dot: 'bg-gray-400', text: 'text-gray-400', bg: 'bg-gray-500/10 border-gray-500/20' },
};

const KIND_ICON: Record<Kind, React.ReactNode> = {
  playbook_in_flight: <Clock className="w-3 h-3" />,
  at_risk_no_playbook: <AlertTriangle className="w-3 h-3" />,
  expansion_open: <TrendingUp className="w-3 h-3" />,
  flagged_decision: <ChevronRight className="w-3 h-3" />,
};

const PendingDecisionsQueue: React.FC<Props> = ({ persona }) => {
  const { session } = useSession();
  const [items, setItems] = useState<DecisionItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const customerId = getCustomerIdentifier(session);
        const resp = await apiCall(
          `/api/executive/pending-decisions?persona=${persona}&limit=5`,
          { headers: { 'X-Customer-ID': customerId } },
        );
        if (!resp.ok) {
          throw new Error(`API ${resp.status}`);
        }
        const json: ApiResponse = await resp.json();
        if (!cancelled) {
          setItems(json.items || []);
        }
      } catch (e: any) {
        if (!cancelled) setError(e.message || 'Failed to load');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchData();
    return () => { cancelled = true; };
  }, [persona, session]);

  // Persona-aware $ display: CFO highlights spend (dollar_amount), CRO highlights ARR exposure.
  const formatPrimaryAmount = (it: DecisionItem): string => {
    if (persona === 'cfo' && it.dollar_amount > 0) return formatCompactUSD(it.dollar_amount);
    return formatCompactUSD(it.revenue_at_stake);
  };

  const primaryLabel = persona === 'cfo' ? 'spend / exposure' : 'revenue at stake';

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-gray-700/50 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[10px] font-semibold tracking-[0.15em] text-gray-500 uppercase">
          Pending Decisions
        </h3>
        <span className="text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400">
          {persona.toUpperCase()}
        </span>
      </div>

      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-3 bg-gray-700 rounded w-3/4 mb-1.5" />
              <div className="h-2 bg-gray-700/60 rounded w-full" />
            </div>
          ))}
        </div>
      )}

      {!loading && error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
          <p className="text-[11px] text-red-300">Could not load — {error}</p>
        </div>
      )}

      {!loading && !error && items && items.length === 0 && (
        <p className="text-xs text-gray-500 text-center py-4">
          No pending decisions. Queue is clear.
        </p>
      )}

      {!loading && !error && items && items.length > 0 && (
        <ul className="space-y-2">
          {items.map((it) => {
            const u = URGENCY_STYLES[it.urgency];
            return (
              <li
                key={it.decision_id}
                className={`rounded-lg border ${u.bg} px-3 py-2`}
              >
                <div className="flex items-start gap-2">
                  <span className={`inline-flex items-center justify-center w-5 h-5 rounded-full ${u.dot}/30 ${u.text} flex-shrink-0 mt-0.5`}>
                    {KIND_ICON[it.kind]}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-gray-200 truncate" title={it.headline}>
                      {it.headline}
                    </p>
                    <p className="text-[10px] text-gray-500 mt-0.5 leading-snug line-clamp-2">
                      {it.rationale}
                    </p>
                    <div className="flex items-center justify-between mt-1.5">
                      <span className={`text-[10px] font-semibold ${u.text}`}>
                        {formatPrimaryAmount(it)}
                      </span>
                      <span className={`text-[9px] uppercase tracking-wider ${u.text}`}>
                        {it.urgency}
                      </span>
                    </div>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {!loading && !error && items && items.length > 0 && (
        <p className="text-[9px] text-gray-600 text-center mt-3 italic">
          Sorted by {primaryLabel} &middot; read-only v1
        </p>
      )}
    </div>
  );
};

export default PendingDecisionsQueue;
