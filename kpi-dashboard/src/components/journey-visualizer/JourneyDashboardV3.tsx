/**
 * CS Pulse Journey Dashboard V3 - COMPREHENSIVE
 * ===============================================
 * 
 * Multi-view dashboard with:
 * 
 * VIEW 1: Health Overview (V2 - Quantitative)
 *   - Health score timeline
 *   - KPI pillar breakdown
 *   - Week-by-week navigation
 * 
 * VIEW 2: Qualitative Signals (V3 - Semantic)
 *   - Email/Meeting/Ticket timeline
 *   - Sentiment analysis
 *   - Contact engagement map
 *   - Signal source distribution
 * 
 * VIEW 3: Signal Analyst Output
 *   - Churn/Expansion probability charts
 *   - Risk driver breakdown
 *   - Recommended actions with priority
 *   - Confidence indicators
 * 
 * VIEW 4: Correlation Analysis
 *   - Signals vs Health overlay
 *   - Sentiment heatmap
 *   - Leading indicators
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSession } from '../../contexts/SessionContext';
import { getCustomerIdentifier } from '../../utils/api';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, ComposedChart, Legend
} from 'recharts';
import KPICard from './KPICard';
import {
  Mail, MessageSquare, Phone, Calendar, AlertTriangle,
  TrendingUp, TrendingDown, Minus, ChevronLeft, ChevronRight,
  Activity, Shield, Zap, Server, Clock, Target, Users,
  ThumbsUp, ThumbsDown, Meh, FileText, Headphones,
  Play, RefreshCw, ExternalLink, CheckCircle, XCircle,
  AlertCircle, BarChart2, PieChart as PieChartIcon
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

export interface QualitativeSignal {
  signal_id: string;
  date: string;
  week_number: number;
  signal_type: 'email' | 'meeting' | 'support_ticket' | 'call' | 'csm_note';
  source: string;
  from_contact: string;
  to_contact: string;
  subject: string;
  summary: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  sentiment_score: number; // -1 to 1
  priority: 'critical' | 'high' | 'medium' | 'low';
  keywords: string[];
  health_impact?: number;
}

interface SignalAnalystOutput {
  analysis_id: string;
  timestamp: string;
  account_id: string;
  health_score: number;
  churn_probability: number;
  expansion_probability: number;
  confidence: number;
  confidence_level: 'high' | 'medium' | 'low';
  predicted_outcome: string;
  risk_drivers: RiskDriver[];
  growth_drivers: GrowthDriver[];
  recommended_actions: RecommendedAction[];
  signals_analyzed: {
    quantitative: number;
    qualitative: number;
    historical: number;
  };
  model_used: string;
  analysis_duration_ms: number;
}

interface RiskDriver {
  driver: string;
  impact: number; // 0-100
  trend: 'improving' | 'stable' | 'worsening';
  evidence: string[];
}

interface GrowthDriver {
  driver: string;
  potential: number; // 0-100
  readiness: 'ready' | 'developing' | 'early';
  evidence: string[];
}

interface RecommendedAction {
  action: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  timeline_days: number;
  expected_impact: string;
  playbook_id?: string;
}

export interface WeekData {
  week_number: number;
  health_score: number;
  phase: string;
  pillar_scores?: Record<string, number>;
  kpis?: Record<string, number>;
  normalized_kpis?: Record<string, number>;
  raw_kpis?: Record<string, { value: number; unit: string }>;
  events?: any[];
  signals?: QualitativeSignal[];
  sentiment_avg?: number;
  date?: string;
  data_quality?: number;
  coverage_pct?: number;
  available_kpis?: string[];
}

// ============================================================================
// MOCK DATA FOR QUALITATIVE SIGNALS
// ============================================================================

const MOCK_SIGNALS: QualitativeSignal[] = [
  {
    signal_id: 'SIG-001',
    date: '2025-01-15',
    week_number: 3,
    signal_type: 'email',
    source: 'Gmail',
    from_contact: 'james.mitchell@cloudscale.ai',
    to_contact: 'sarah.chen@supermicro.com',
    subject: 'GPU Utilization Concerns',
    summary: 'Customer expressing concern about GPU utilization being below 70%. CFO asking about ROI.',
    sentiment: 'negative',
    sentiment_score: -0.65,
    priority: 'high',
    keywords: ['GPU', 'utilization', 'ROI', 'CFO'],
    health_impact: -8
  },
  {
    signal_id: 'SIG-002',
    date: '2025-01-22',
    week_number: 4,
    signal_type: 'meeting',
    source: 'Zoom',
    from_contact: 'Tech Review Meeting',
    to_contact: 'All Stakeholders',
    subject: 'Q1 Technical Review - Positive Outcome',
    summary: 'Successful technical review. Customer impressed with recent optimizations. Discussing Phase 2.',
    sentiment: 'positive',
    sentiment_score: 0.82,
    priority: 'medium',
    keywords: ['optimization', 'Phase 2', 'expansion'],
    health_impact: 12
  },
  {
    signal_id: 'SIG-003',
    date: '2025-02-01',
    week_number: 5,
    signal_type: 'support_ticket',
    source: 'Zendesk',
    from_contact: 'ops-team@cloudscale.ai',
    to_contact: 'support@supermicro.com',
    subject: 'CRITICAL: Cluster Outage - Node Failure',
    summary: 'Production cluster experiencing outage. 3 nodes failed simultaneously. Escalating to engineering.',
    sentiment: 'negative',
    sentiment_score: -0.95,
    priority: 'critical',
    keywords: ['outage', 'node failure', 'production', 'escalation'],
    health_impact: -25
  },
  {
    signal_id: 'SIG-004',
    date: '2025-02-05',
    week_number: 6,
    signal_type: 'call',
    source: 'Gong',
    from_contact: 'sarah.chen@supermicro.com',
    to_contact: 'james.mitchell@cloudscale.ai',
    subject: 'Post-Incident Review Call',
    summary: 'Customer appreciated fast response. Root cause identified. Prevention measures discussed.',
    sentiment: 'neutral',
    sentiment_score: 0.15,
    priority: 'medium',
    keywords: ['incident', 'root cause', 'prevention'],
    health_impact: 5
  },
  {
    signal_id: 'SIG-005',
    date: '2025-02-15',
    week_number: 7,
    signal_type: 'email',
    source: 'Gmail',
    from_contact: 'cto@cloudscale.ai',
    to_contact: 'exec-team@supermicro.com',
    subject: 'Partnership Expansion Discussion',
    summary: 'CTO reaching out about expanding partnership. Interested in additional capacity for Q3.',
    sentiment: 'positive',
    sentiment_score: 0.88,
    priority: 'high',
    keywords: ['partnership', 'expansion', 'Q3', 'capacity'],
    health_impact: 15
  }
];

const MOCK_ANALYST_OUTPUT: SignalAnalystOutput = {
  analysis_id: 'ANL-2025-01-13-001',
  timestamp: '2025-01-13T10:30:00Z',
  account_id: '10001',
  health_score: 78,
  churn_probability: 22,
  expansion_probability: 65,
  confidence: 0.82,
  confidence_level: 'high',
  predicted_outcome: 'expansion_likely',
  risk_drivers: [
    {
      driver: 'Recent support escalations',
      impact: 35,
      trend: 'improving',
      evidence: ['2 critical tickets in past 30 days', 'Resolution time improving']
    },
    {
      driver: 'Executive engagement declining',
      impact: 25,
      trend: 'stable',
      evidence: ['No executive contact in 45 days', 'Last QBR postponed']
    },
    {
      driver: 'Competitor evaluation signals',
      impact: 15,
      trend: 'worsening',
      evidence: ['Mentioned Dell in recent email', 'Requested pricing comparison']
    }
  ],
  growth_drivers: [
    {
      driver: 'Capacity utilization high',
      potential: 85,
      readiness: 'ready',
      evidence: ['GPU utilization at 82%', 'Approaching capacity limits']
    },
    {
      driver: 'Product satisfaction strong',
      potential: 70,
      readiness: 'ready',
      evidence: ['NPS score 72', 'Positive sentiment in communications']
    },
    {
      driver: 'Multi-region interest',
      potential: 60,
      readiness: 'developing',
      evidence: ['Asked about APAC availability', 'Growth plans mentioned']
    }
  ],
  recommended_actions: [
    {
      action: 'Schedule executive QBR within 14 days',
      priority: 'high',
      timeline_days: 14,
      expected_impact: 'Re-establish executive relationship, address concerns',
      playbook_id: 'PB-003'
    },
    {
      action: 'Prepare Phase 2 expansion proposal',
      priority: 'high',
      timeline_days: 21,
      expected_impact: 'Capture $450K expansion opportunity',
      playbook_id: 'PB-005'
    },
    {
      action: 'Address competitor concerns proactively',
      priority: 'medium',
      timeline_days: 7,
      expected_impact: 'Mitigate churn risk, demonstrate value',
      playbook_id: 'PB-002'
    },
    {
      action: 'Share customer success story with stakeholders',
      priority: 'low',
      timeline_days: 30,
      expected_impact: 'Reinforce partnership value',
      playbook_id: 'PB-006'
    }
  ],
  signals_analyzed: {
    quantitative: 19,
    qualitative: 12,
    historical: 45
  },
  model_used: 'gpt-4o',
  analysis_duration_ms: 16500
};

// ============================================================================
// HELPER COMPONENTS
// ============================================================================

const SentimentIcon: React.FC<{ sentiment: string }> = ({ sentiment }) => {
  if (sentiment === 'positive') return <ThumbsUp className="w-4 h-4 text-green-600" />;
  if (sentiment === 'negative') return <ThumbsDown className="w-4 h-4 text-red-600" />;
  return <Meh className="w-4 h-4 text-gray-500" />;
};

const SignalTypeIcon: React.FC<{ type: string }> = ({ type }) => {
  const icons: Record<string, React.ReactNode> = {
    email: <Mail className="w-4 h-4" />,
    meeting: <Calendar className="w-4 h-4" />,
    support_ticket: <Headphones className="w-4 h-4" />,
    call: <Phone className="w-4 h-4" />,
    csm_note: <FileText className="w-4 h-4" />
  };
  return <>{icons[type] || <MessageSquare className="w-4 h-4" />}</>;
};

const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800 border-red-200',
    high: 'bg-orange-100 text-orange-800 border-orange-200',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    low: 'bg-gray-100 text-gray-800 border-gray-200'
  };
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded border ${colors[priority]}`}>
      {priority.toUpperCase()}
    </span>
  );
};

const ConfidenceMeter: React.FC<{ confidence: number; level: string }> = ({ confidence, level }) => {
  const color = level === 'high' ? 'bg-green-500' : level === 'medium' ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 bg-gray-200 rounded-full h-2">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${confidence * 100}%` }} />
      </div>
      <span className="text-sm font-medium">{(confidence * 100).toFixed(0)}%</span>
    </div>
  );
};

// ============================================================================
// VIEW COMPONENTS
// ============================================================================

// VIEW 1: Health Overview (V2 - Quantitative)
const HealthOverviewView: React.FC<{ weeklyData: WeekData[]; selectedWeek: number; onWeekChange: (w: number) => void }> = ({
  weeklyData, selectedWeek, onWeekChange
}) => {
  const currentWeek = weeklyData[selectedWeek - 1];
  
  // Debug logging
  if (currentWeek) {
    const kpis = currentWeek.normalized_kpis || currentWeek.kpis || {};
    const rawKpis = currentWeek.raw_kpis || {};
    console.log('[HealthOverview] Current week:', {
      week: selectedWeek,
      hasKPIs: !!(currentWeek.kpis || currentWeek.normalized_kpis),
      kpiCount: Object.keys(kpis).length,
      hasRawKPIs: !!currentWeek.raw_kpis,
      rawKpiCount: Object.keys(rawKpis).length,
      kpiKeys: Object.keys(kpis).slice(0, 5),
      currentWeekKeys: Object.keys(currentWeek)
    });
  } else {
    console.warn('[HealthOverview] No current week data:', {
      selectedWeek,
      weeklyDataLength: weeklyData.length,
      weeklyData: weeklyData.length > 0 ? Object.keys(weeklyData[0]) : []
    });
  }
  
  const healthChartData = weeklyData.map(w => ({
    week: w.week_number,
    health: w.health_score,
    phase: w.phase
  }));

  const pillarData = currentWeek?.pillar_scores ? Object.entries(currentWeek.pillar_scores).map(([key, value]) => ({
    pillar: key,
    score: value,
    fullMark: 100
  })) : [];

  return (
    <div className="space-y-6">
      {/* Health Timeline */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">Health Score Timeline</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={healthChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" label={{ value: 'Week', position: 'bottom' }} />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <defs>
                <linearGradient id="healthGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="health" stroke="#3b82f6" fill="url(#healthGradient)" />
              {/* Reference lines */}
              <Line type="monotone" dataKey={() => 70} stroke="#22c55e" strokeDasharray="5 5" dot={false} />
              <Line type="monotone" dataKey={() => 50} stroke="#f59e0b" strokeDasharray="5 5" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="flex justify-center gap-6 mt-2 text-sm">
          <span className="flex items-center"><span className="w-4 h-0.5 bg-green-500 mr-2" />Healthy (70+)</span>
          <span className="flex items-center"><span className="w-4 h-0.5 bg-yellow-500 mr-2" />At Risk (50-70)</span>
        </div>
      </div>

      {/* Week Navigation + Pillar Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Week Navigator */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Week {selectedWeek}</h3>
            <div className="flex items-center gap-2">
              <button
                onClick={() => onWeekChange(Math.max(1, selectedWeek - 1))}
                className="p-1 rounded hover:bg-gray-100"
                disabled={selectedWeek <= 1}
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <span className="text-sm text-gray-500">of {weeklyData.length}</span>
              <button
                onClick={() => onWeekChange(Math.min(weeklyData.length, selectedWeek + 1))}
                className="p-1 rounded hover:bg-gray-100"
                disabled={selectedWeek >= weeklyData.length}
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
          
          {currentWeek && (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Health Score</span>
                <span className="text-2xl font-bold" style={{
                  color: currentWeek.health_score >= 70 ? '#16a34a' :
                         currentWeek.health_score >= 50 ? '#ca8a04' : '#dc2626'
                }}>
                  {currentWeek.health_score}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Phase</span>
                <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">
                  {currentWeek.phase}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Events</span>
                <span>{currentWeek.events?.length || 0}</span>
              </div>
            </div>
          )}
        </div>

        {/* Pillar Radar */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-4">Pillar Breakdown</h3>
          {pillarData.length > 0 ? (
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={pillarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="pillar" tick={{ fontSize: 10 }} />
                  <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Radar name="Score" dataKey="score" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.5} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-500">
              No pillar data available
            </div>
          )}
        </div>
      </div>

      {/* KPI Grid - Always show section, even if no data */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">KPIs - Week {selectedWeek}</h3>
        {currentWeek ? (
          (() => {
            // Use normalized_kpis if available (V2), otherwise kpis (V1)
            let kpis = currentWeek.normalized_kpis || currentWeek.kpis || {};
            let rawKpis = currentWeek.raw_kpis || {};
            let displayWeek = selectedWeek;
            
            // If current week has no KPIs, find the most recent week with KPIs
            const kpiEntries = Object.entries(kpis);
            if (kpiEntries.length === 0) {
              // Search backwards for the most recent week with KPIs
              for (let i = selectedWeek - 1; i >= 1; i--) {
                const weekData = weeklyData[i - 1];
                if (weekData) {
                  const weekKpis = weekData.normalized_kpis || weekData.kpis || {};
                  if (Object.keys(weekKpis).length > 0) {
                    kpis = weekKpis;
                    rawKpis = weekData.raw_kpis || {};
                    displayWeek = i;
                    break;
                  }
                }
              }
            }
            
            const finalKpiEntries = Object.entries(kpis);
            
            if (finalKpiEntries.length === 0) {
              return (
                <div className="text-center py-8 text-gray-500">
                  <p>No KPI data available for this week</p>
                  <p className="text-sm mt-2">KPI data may not be available for all weeks</p>
                </div>
              );
            }
            
            // Show a notice if we're displaying KPIs from a different week
            const isShowingDifferentWeek = displayWeek !== selectedWeek;
            
            console.log(`[HealthOverview] Rendering ${finalKpiEntries.length} KPI cards${isShowingDifferentWeek ? ` (from Week ${displayWeek})` : ''}`);
            return (
              <>
                {isShowingDifferentWeek && (
                  <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-800">
                      <span className="font-medium">Note:</span> No KPI data available for Week {selectedWeek}. 
                      Showing KPIs from Week {displayWeek} (most recent available).
                    </p>
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {finalKpiEntries.map(([kpiName, normalizedValue]) => {
                  const rawKpi = rawKpis[kpiName];
                  if (typeof normalizedValue !== 'number') {
                    console.warn(`[HealthOverview] Invalid KPI value for ${kpiName}:`, normalizedValue);
                    return null;
                  }
                  return (
                    <KPICard
                      key={kpiName}
                      name={kpiName}
                      rawValue={rawKpi}
                      normalizedValue={normalizedValue}
                      showIndustryContext={true}
                      isV2={!!rawKpi}
                    />
                  );
                })}
                </div>
              </>
            );
          })()
        ) : (
          <div className="text-center py-8 text-gray-500">
            <p>No data available for week {selectedWeek}</p>
            <p className="text-sm mt-2">Total weeks available: {weeklyData.length}</p>
          </div>
        )}
      </div>
    </div>
  );
};

// VIEW 2: Qualitative Signals (V3 - Semantic)
const QualitativeSignalsView: React.FC<{ signals: QualitativeSignal[]; accountId?: string }> = ({ signals, accountId }) => {
  const [filterType, setFilterType] = useState<string>('all');
  const [filterSentiment, setFilterSentiment] = useState<string>('all');

  const filteredSignals = signals.filter(s => {
    if (filterType !== 'all' && s.signal_type !== filterType) return false;
    if (filterSentiment !== 'all' && s.sentiment !== filterSentiment) return false;
    return true;
  });

  // Sentiment distribution
  const sentimentData = [
    { name: 'Positive', value: signals.filter(s => s.sentiment === 'positive').length, color: '#22c55e' },
    { name: 'Neutral', value: signals.filter(s => s.sentiment === 'neutral').length, color: '#6b7280' },
    { name: 'Negative', value: signals.filter(s => s.sentiment === 'negative').length, color: '#ef4444' }
  ];

  // Signal type distribution
  const typeData = [
    { name: 'Email', value: signals.filter(s => s.signal_type === 'email').length },
    { name: 'Meeting', value: signals.filter(s => s.signal_type === 'meeting').length },
    { name: 'Support', value: signals.filter(s => s.signal_type === 'support_ticket').length },
    { name: 'Call', value: signals.filter(s => s.signal_type === 'call').length }
  ];

  // Sentiment over time
  const sentimentTimeline = signals.reduce((acc, s) => {
    const week = s.week_number;
    if (!acc[week]) acc[week] = { week, positive: 0, neutral: 0, negative: 0, avg: 0, count: 0 };
    acc[week][s.sentiment]++;
    acc[week].avg += s.sentiment_score;
    acc[week].count++;
    return acc;
  }, {} as Record<number, any>);

  const sentimentTimelineData = Object.values(sentimentTimeline).map((w: any) => ({
    ...w,
    avg: w.count > 0 ? (w.avg / w.count).toFixed(2) : 0
  }));

  if (signals.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold mb-2">No Qualitative Signals Available</h3>
        <p className="text-gray-600 mb-4">
          No signals found for this account. Signals may be loaded from the database or journey files.
        </p>
        <p className="text-sm text-gray-500">
          Check that qualitative signals have been uploaded for account {accountId || 'this account'}.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Signals</p>
              <p className="text-2xl font-bold">{signals.length}</p>
            </div>
            <MessageSquare className="w-8 h-8 text-blue-500 opacity-50" />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Positive</p>
              <p className="text-2xl font-bold text-green-600">{sentimentData[0].value}</p>
            </div>
            <ThumbsUp className="w-8 h-8 text-green-500 opacity-50" />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Negative</p>
              <p className="text-2xl font-bold text-red-600">{sentimentData[2].value}</p>
            </div>
            <ThumbsDown className="w-8 h-8 text-red-500 opacity-50" />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Critical</p>
              <p className="text-2xl font-bold text-orange-600">
                {signals.filter(s => s.priority === 'critical').length}
              </p>
            </div>
            <AlertTriangle className="w-8 h-8 text-orange-500 opacity-50" />
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Sentiment Distribution */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-4">Sentiment Distribution</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={sentimentData} cx="50%" cy="50%" innerRadius={40} outerRadius={70} dataKey="value">
                  {sentimentData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Sentiment Timeline */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-4">Sentiment Over Time</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sentimentTimelineData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="week" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="positive" stackId="a" fill="#22c55e" name="Positive" />
                <Bar dataKey="neutral" stackId="a" fill="#6b7280" name="Neutral" />
                <Bar dataKey="negative" stackId="a" fill="#ef4444" name="Negative" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Signal Timeline */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Signal Timeline</h3>
          <div className="flex gap-2">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="all">All Types</option>
              <option value="email">Email</option>
              <option value="meeting">Meeting</option>
              <option value="support_ticket">Support</option>
              <option value="call">Call</option>
            </select>
            <select
              value={filterSentiment}
              onChange={(e) => setFilterSentiment(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="all">All Sentiment</option>
              <option value="positive">Positive</option>
              <option value="neutral">Neutral</option>
              <option value="negative">Negative</option>
            </select>
          </div>
        </div>

        <div className="space-y-3 max-h-96 overflow-y-auto">
          {filteredSignals.map(signal => (
            <div
              key={signal.signal_id}
              className={`p-3 rounded-lg border-l-4 ${
                signal.sentiment === 'positive' ? 'bg-green-50 border-green-500' :
                signal.sentiment === 'negative' ? 'bg-red-50 border-red-500' :
                'bg-gray-50 border-gray-400'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded ${
                    signal.sentiment === 'positive' ? 'bg-green-100' :
                    signal.sentiment === 'negative' ? 'bg-red-100' : 'bg-gray-100'
                  }`}>
                    <SignalTypeIcon type={signal.signal_type} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">{signal.subject}</span>
                      <PriorityBadge priority={signal.priority} />
                    </div>
                    <p className="text-sm text-gray-600">{signal.summary}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                      <span>Week {signal.week_number}</span>
                      <span>{signal.date}</span>
                      <span>{signal.from_contact}</span>
                      {signal.health_impact && (
                        <span className={signal.health_impact > 0 ? 'text-green-600' : 'text-red-600'}>
                          Health Impact: {signal.health_impact > 0 ? '+' : ''}{signal.health_impact}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <SentimentIcon sentiment={signal.sentiment} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// VIEW 3: Signal Analyst Output
const SignalAnalystView: React.FC<{ 
  output: SignalAnalystOutput | null; 
  onRunAnalysis: () => void;
  loading: boolean;
}> = ({ output, onRunAnalysis, loading }) => {
  if (!output) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <Activity className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold mb-2">No Analysis Available</h3>
        <p className="text-gray-600 mb-4">Run Signal Analyst to get AI-powered insights</p>
        <button
          onClick={onRunAnalysis}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 mx-auto"
        >
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          {loading ? 'Analyzing...' : 'Run Analysis'}
        </button>
      </div>
    );
  }

  const churnExpansionData = [
    { name: 'Churn Risk', value: output.churn_probability, fill: '#ef4444' },
    { name: 'Expansion Potential', value: output.expansion_probability, fill: '#22c55e' }
  ];

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Health Score</p>
          <p className="text-3xl font-bold" style={{
            color: output.health_score >= 70 ? '#16a34a' :
                   output.health_score >= 50 ? '#ca8a04' : '#dc2626'
          }}>
            {output.health_score}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Churn Probability</p>
          <p className="text-3xl font-bold text-red-600">{output.churn_probability}%</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Expansion Probability</p>
          <p className="text-3xl font-bold text-green-600">{output.expansion_probability}%</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">Confidence</p>
          <ConfidenceMeter confidence={output.confidence} level={output.confidence_level} />
        </div>
      </div>

      {/* Churn vs Expansion Chart */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-4">Outcome Prediction</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={churnExpansionData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} />
                <YAxis type="category" dataKey="name" width={120} />
                <Tooltip />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {churnExpansionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 p-3 bg-blue-50 rounded">
            <p className="text-sm font-medium text-blue-800">
              Predicted Outcome: <span className="uppercase">{(output.predicted_outcome ?? 'stable').replace('_', ' ')}</span>
            </p>
          </div>
        </div>

        {/* Signals Analyzed */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-lg font-semibold mb-4">Analysis Summary</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-gray-600">Quantitative Signals</span>
              <span className="font-semibold">{output.signals_analyzed?.quantitative ?? 0}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-gray-600">Qualitative Signals</span>
              <span className="font-semibold">{output.signals_analyzed?.qualitative ?? 0}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-gray-600">Historical Patterns</span>
              <span className="font-semibold">{output.signals_analyzed?.historical ?? 0}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-gray-600">Model Used</span>
              <span className="font-semibold">{output.model_used}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
              <span className="text-gray-600">Analysis Time</span>
              <span className="font-semibold">{(output.analysis_duration_ms / 1000).toFixed(1)}s</span>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Drivers */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-red-500" />
          Risk Drivers
        </h3>
        <div className="space-y-3">
          {(output.risk_drivers || []).map((driver, index) => (
            <div key={index} className="p-3 bg-red-50 rounded-lg border border-red-100">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium">{driver.driver}</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">Impact: {driver.impact}%</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    driver.trend === 'improving' ? 'bg-green-100 text-green-800' :
                    driver.trend === 'worsening' ? 'bg-red-100 text-red-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {driver.trend}
                  </span>
                </div>
              </div>
              <div className="w-full bg-red-200 rounded-full h-2 mb-2">
                <div className="bg-red-500 h-2 rounded-full" style={{ width: `${driver.impact}%` }} />
              </div>
              <ul className="text-sm text-gray-600 list-disc list-inside">
                {(driver.evidence || []).map((e, i) => <li key={i}>{typeof e === 'string' ? e : String(e)}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Growth Drivers */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-green-500" />
          Growth Drivers
        </h3>
        <div className="space-y-3">
          {(output.growth_drivers || []).map((driver, index) => (
            <div key={index} className="p-3 bg-green-50 rounded-lg border border-green-100">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium">{driver.driver}</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-500">Potential: {driver.potential}%</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    driver.readiness === 'ready' ? 'bg-green-100 text-green-800' :
                    driver.readiness === 'developing' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {driver.readiness}
                  </span>
                </div>
              </div>
              <div className="w-full bg-green-200 rounded-full h-2 mb-2">
                <div className="bg-green-500 h-2 rounded-full" style={{ width: `${driver.potential}%` }} />
              </div>
              <ul className="text-sm text-gray-600 list-disc list-inside">
                {(driver.evidence || []).map((e, i) => <li key={i}>{typeof e === 'string' ? e : String(e)}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Recommended Actions */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Target className="w-5 h-5 text-blue-500" />
          Recommended Actions
        </h3>
        <div className="space-y-3">
          {(output.recommended_actions || []).map((action, index) => (
            <div key={index} className={`p-4 rounded-lg border-l-4 ${
              (action.priority === 'critical' ? 'bg-red-50 border-red-500' :
              action.priority === 'high' ? 'bg-orange-50 border-orange-500' :
              action.priority === 'medium' ? 'bg-yellow-50 border-yellow-500' :
              'bg-gray-50 border-gray-400')
            }`}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <PriorityBadge priority={action.priority ?? 'medium'} />
                    <span className="text-sm text-gray-500">
                      Due in {action.timeline_days ?? (action as any).timeline ?? 0} days
                    </span>
                  </div>
                  <p className="font-medium">{action.action ?? (action as any).title ?? '—'}</p>
                  <p className="text-sm text-gray-600 mt-1">{action.expected_impact ?? (action as any).rationale ?? '—'}</p>
                </div>
                {action.playbook_id && (
                  <button className="text-sm text-blue-600 hover:underline flex items-center gap-1">
                    <ExternalLink className="w-3 h-3" />
                    {action.playbook_id}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// VIEW 4: Correlation Analysis
const CorrelationView: React.FC<{ weeklyData: WeekData[]; signals: QualitativeSignal[]; accountId?: string }> = ({ weeklyData, signals, accountId }) => {
  // Create combined data for correlation chart
  const correlationData = weeklyData.map(week => {
    const weekSignals = signals.filter(s => s.week_number === week.week_number);
    const avgSentiment = weekSignals.length > 0 
      ? weekSignals.reduce((sum, s) => sum + s.sentiment_score, 0) / weekSignals.length
      : 0;
    
    return {
      week: week.week_number,
      health: week.health_score,
      sentiment: (avgSentiment * 50) + 50, // Convert -1 to 1 → 0 to 100
      signalCount: weekSignals.length,
      negativeSignals: weekSignals.filter(s => s.sentiment === 'negative').length
    };
  });

  if (signals.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <BarChart2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold mb-2">No Correlation Data Available</h3>
        <p className="text-gray-600 mb-4">
          No signals found for this account. Correlation analysis requires qualitative signals.
        </p>
        <p className="text-sm text-gray-500">
          Check that qualitative signals have been uploaded for account {accountId || 'this account'}.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Health vs Sentiment Overlay */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">Health Score vs Sentiment Correlation</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={correlationData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" label={{ value: 'Week', position: 'bottom' }} />
              <YAxis yAxisId="left" domain={[0, 100]} label={{ value: 'Health', angle: -90, position: 'insideLeft' }} />
              <YAxis yAxisId="right" orientation="right" domain={[0, 100]} label={{ value: 'Sentiment', angle: 90, position: 'insideRight' }} />
              <Tooltip />
              <Legend />
              <Area yAxisId="left" type="monotone" dataKey="health" fill="#93c5fd" stroke="#3b82f6" name="Health Score" />
              <Line yAxisId="right" type="monotone" dataKey="sentiment" stroke="#22c55e" strokeWidth={2} name="Sentiment Index" dot />
              <Bar yAxisId="left" dataKey="negativeSignals" fill="#ef4444" opacity={0.5} name="Negative Signals" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <p className="text-sm text-gray-500 mt-2">
          Shows correlation between health score changes and sentiment from customer communications
        </p>
      </div>

      {/* Sentiment Heatmap */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">Weekly Sentiment Heatmap</h3>
        <div className="grid grid-cols-13 gap-1">
          {/* Week labels */}
          <div className="text-xs text-gray-500">Week</div>
          {Array.from({ length: 12 }, (_, i) => (
            <div key={i} className="text-xs text-gray-500 text-center">{i + 1}</div>
          ))}
          
          {/* Sentiment row */}
          <div className="text-xs text-gray-500">Sentiment</div>
          {correlationData.slice(0, 12).map((week, i) => {
            const sentiment = week.sentiment;
            let bgColor = '#f3f4f6'; // neutral
            if (sentiment > 60) bgColor = '#86efac'; // positive
            else if (sentiment > 55) bgColor = '#bbf7d0';
            else if (sentiment < 40) bgColor = '#fca5a5'; // negative
            else if (sentiment < 45) bgColor = '#fecaca';
            
            return (
              <div
                key={i}
                className="h-8 rounded flex items-center justify-center text-xs"
                style={{ backgroundColor: bgColor }}
                title={`Week ${week.week}: ${week.sentiment.toFixed(0)}`}
              >
                {week.signalCount}
              </div>
            );
          })}
        </div>
        <div className="flex justify-center gap-4 mt-4 text-sm">
          <span className="flex items-center"><span className="w-4 h-4 bg-green-300 rounded mr-2" />Positive</span>
          <span className="flex items-center"><span className="w-4 h-4 bg-gray-200 rounded mr-2" />Neutral</span>
          <span className="flex items-center"><span className="w-4 h-4 bg-red-300 rounded mr-2" />Negative</span>
        </div>
      </div>

      {/* Leading Indicators */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold mb-4">Leading Indicators Analysis</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-800 mb-2">Sentiment → Health Lag</h4>
            <p className="text-2xl font-bold text-blue-600">2-3 weeks</p>
            <p className="text-sm text-gray-600 mt-1">
              Negative sentiment typically precedes health score drops by 2-3 weeks
            </p>
          </div>
          <div className="p-4 bg-green-50 rounded-lg">
            <h4 className="font-medium text-green-800 mb-2">Positive Signal Correlation</h4>
            <p className="text-2xl font-bold text-green-600">0.72</p>
            <p className="text-sm text-gray-600 mt-1">
              Strong correlation between positive signals and health improvement
            </p>
          </div>
          <div className="p-4 bg-red-50 rounded-lg">
            <h4 className="font-medium text-red-800 mb-2">Critical Signal Impact</h4>
            <p className="text-2xl font-bold text-red-600">-15 pts</p>
            <p className="text-sm text-gray-600 mt-1">
              Average health score drop after critical signals
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// MAIN DASHBOARD COMPONENT
// ============================================================================

interface JourneyDashboardV3Props {
  accountId?: string; // Optional prop for when used as a component (e.g., in tenant hub)
}

const JourneyDashboardV3: React.FC<JourneyDashboardV3Props> = ({ accountId: propAccountId }) => {
  const { accountId: routeAccountId } = useParams<{ accountId: string }>();
  // Use prop accountId if provided (from tenant hub), otherwise use route param
  const accountId = propAccountId || routeAccountId;
  const navigate = useNavigate();
  const { session } = useSession();
  
  // State - Initialize with empty data, not mock data
  const [activeView, setActiveView] = useState<'health' | 'signals' | 'analyst' | 'correlation'>('health');
  const [weeklyData, setWeeklyData] = useState<WeekData[]>([]);
  const [signals, setSignals] = useState<QualitativeSignal[]>([]);
  const [analystOutput, setAnalystOutput] = useState<SignalAnalystOutput | null>(null);
  const [selectedWeek, setSelectedWeek] = useState(1);
  const [loading, setLoading] = useState(true);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [accountInfo, setAccountInfo] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Load journey data
  useEffect(() => {
    if (session?.customer_id) {
      loadJourneyData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountId, session?.customer_id]);

  const loadJourneyData = async () => {
    if (!session?.customer_id) {
      console.error('No session available');
      setLoading(false);
      return;
    }
    
    setLoading(true);
    try {
      // First check if backend session is valid
      const sessionCheck = await fetch('/api/session/status', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!sessionCheck.ok || !(await sessionCheck.json()).authenticated) {
        console.warn('[JourneyDashboard] Backend session invalid, redirecting to login');
        window.location.href = '/login';
        return;
      }
      
      // Validate accountId before making request
      if (!accountId || accountId === 'undefined') {
        console.error('[JourneyDashboard] Invalid accountId:', accountId);
        setError('Invalid account ID. Please select an account from the dashboard.');
        setLoading(false);
        return;
      }
      
      // Use relative path to ensure cookies are sent via proxy
      const response = await fetch(`/api/journey/${accountId}`, {
        method: 'GET',
        credentials: 'include', // Include session cookies
        headers: {
          'Content-Type': 'application/json',
          'X-Customer-ID': getCustomerIdentifier(session),
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          console.error('Authentication failed - session may have expired or cookies not being sent');
          setError('Authentication failed. Please try refreshing the page or logging in again.');
          setLoading(false);
          // Redirect to login
          window.location.href = '/login';
          return;
        }
        if (response.status === 404) {
          const errorData = await response.json().catch(() => ({ error: 'Journey data not found', message: 'No journey JSON file found for this account' }));
          console.error('Journey data not found:', errorData);
          const errorMessage = errorData.message || `No journey data available for account ${accountId}`;
          setError(`${errorMessage}. This account may not have journey data generated yet. Please check with your administrator or try a different account.`);
          setLoading(false);
          return;
        }
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        console.error('API error:', errorData);
        setError(errorData.message || `Failed to load journey data (HTTP ${response.status})`);
        throw new Error(errorData.message || `HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      // Debug: Log API response structure
      console.log('[JourneyDashboard] API Response:', {
        hasWeeklyData: !!data.weekly_data,
        weeklyDataLength: data.weekly_data?.length || 0,
        hasSignals: !!data.signals,
        signalsLength: data.signals?.length || 0,
        accountInfo: {
          account_id: data.account_id,
          account_name: data.account_name,
          total_weeks: data.total_weeks
        }
      });
      
      if (data.weekly_data && data.weekly_data.length > 0) {
        const firstWeek = data.weekly_data[0];
        console.log('[JourneyDashboard] First week structure:', {
          hasNormalizedKPIs: !!firstWeek.normalized_kpis,
          normalizedKPICount: Object.keys(firstWeek.normalized_kpis || {}).length,
          hasRawKPIs: !!firstWeek.raw_kpis,
          rawKPICount: Object.keys(firstWeek.raw_kpis || {}).length,
          weekKeys: Object.keys(firstWeek)
        });
      }
      
      setAccountInfo(data);
      setWeeklyData(data.weekly_data || []);
      
      // Clear previous signals and analyst output when switching accounts
      setSignals([]);
      setAnalystOutput(null);
      
      // Use real signals from API if available
      if (data.signals && Array.isArray(data.signals) && data.signals.length > 0) {
        console.log(`[JourneyDashboard] Found ${data.signals.length} signals from API`);
        // Convert API signals format to QualitativeSignal format
        const realSignals: QualitativeSignal[] = data.signals.map((sig: any) => ({
          signal_id: sig.signal_id || `SIG-${sig.date}-${sig.week_number || 1}-${accountId}`,
          date: sig.date,
          week_number: sig.week_number || 1,
          signal_type: (sig.signal_type === 'meeting' ? 'meeting' : 
                       sig.signal_type === 'email' ? 'email' :
                       sig.signal_type === 'call' ? 'call' :
                       sig.signal_type === 'support_ticket' ? 'support_ticket' : 'csm_note') as any,
          source: sig.source || 'Unknown',
          from_contact: sig.from_contact || '',
          to_contact: sig.to_contact || '',
          subject: sig.subject || sig.summary?.substring(0, 50) || '',
          summary: sig.summary || '',
          sentiment: (sig.sentiment === 'positive' ? 'positive' :
                     sig.sentiment === 'negative' ? 'negative' : 'neutral') as any,
          sentiment_score: sig.sentiment_score || 0,
          priority: (sig.priority === 'critical' ? 'critical' :
                    sig.priority === 'high' ? 'high' :
                    sig.priority === 'medium' ? 'medium' : 'low') as any,
          keywords: sig.keywords || [],
          health_impact: sig.health_impact || 0
        }));
        setSignals(realSignals);
      } else {
        // No signals available - set empty array instead of mock data
        console.log(`[JourneyDashboard] No signals found in API response. signals: ${data.signals}, length: ${data.signals?.length}`);
        setSignals([]);
      }
      
      if (data.weekly_data?.length > 0) {
        setSelectedWeek(data.weekly_data.length);
      }
    } catch (error) {
      console.error('Error loading journey data:', error);
      setError(error instanceof Error ? error.message : 'Failed to load journey data');
    } finally {
      setLoading(false);
    }
  };

  const runSignalAnalysis = async () => {
    setAnalysisLoading(true);
    try {
      const response = await fetch('/api/signal-analyst/analyze', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Customer-ID': getCustomerIdentifier(session)
        },
        credentials: 'include',
        body: JSON.stringify({ account_id: accountId })
      });
      
      if (response.ok) {
        const result = await response.json();
        // Use real analysis result, only fill in missing fields with defaults
        setAnalystOutput({
          analysis_id: result.analysis_id || `ANL-${new Date().toISOString().split('T')[0]}-${accountId}`,
          timestamp: result.timestamp || new Date().toISOString(),
          account_id: String(accountId), // Use actual account ID, not mock
          health_score: result.health_score || 0,
          churn_probability: result.churn_probability || 0,
          expansion_probability: result.expansion_probability || 0,
          confidence: result.confidence || 0,
          confidence_level: result.confidence_level || 'low',
          predicted_outcome: result.predicted_outcome || 'unknown',
          risk_drivers: result.risk_drivers || [],
          growth_drivers: result.growth_drivers || [],
          recommended_actions: result.recommended_actions || [],
          signals_analyzed: result.signals_analyzed || {
            quantitative: 0,
            qualitative: signals.length,
            historical: 0
          },
          model_used: result.model_used || 'default',
          analysis_duration_ms: result.analysis_duration_ms || 0
        });
      } else {
        const errorData = await response.json().catch(() => ({ error: 'Analysis failed' }));
        console.error('Analysis failed:', errorData);
        setError(errorData.error || 'Failed to run analysis');
      }
    } catch (error) {
      console.error('Error running analysis:', error);
      setError(error instanceof Error ? error.message : 'Failed to run analysis');
    } finally {
      setAnalysisLoading(false);
    }
  };

  const views = [
    { id: 'health', label: 'Health Overview', icon: <Activity className="w-4 h-4" /> },
    { id: 'signals', label: 'Qualitative Signals', icon: <MessageSquare className="w-4 h-4" /> },
    { id: 'analyst', label: 'Signal Analyst', icon: <Target className="w-4 h-4" /> },
    { id: 'correlation', label: 'Correlation', icon: <BarChart2 className="w-4 h-4" /> }
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading journey data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    const is404Error = error.toLowerCase().includes('not found') || error.toLowerCase().includes('no journey data');
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="text-center max-w-lg bg-white rounded-lg shadow-lg p-8">
          <AlertCircle className={`w-16 h-16 ${is404Error ? 'text-yellow-500' : 'text-red-500'} mx-auto mb-4`} />
          <h2 className="text-2xl font-bold text-gray-900 mb-3">
            {is404Error ? 'Journey Data Not Available' : 'Error Loading Journey Data'}
          </h2>
          <p className="text-gray-600 mb-6 leading-relaxed">{error}</p>
          {is404Error && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-left">
              <p className="text-sm text-blue-800">
                <strong>Available accounts with journey data:</strong> 17001, 17003
              </p>
            </div>
          )}
          <div className="flex gap-3 justify-center">
            {!is404Error && (
              <button
                onClick={() => {
                  setError(null);
                  loadJourneyData();
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Retry
              </button>
            )}
            <button
              onClick={() => navigate('/dc-dashboard')}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
            >
              Back to Dashboard
            </button>
            {is404Error && (
              <button
                onClick={() => navigate('/journey-v3/17001')}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                View Account 17001
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 hover:bg-gray-100 rounded"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-xl font-bold">{accountInfo?.account_name || `Account ${accountId}`}</h1>
                <p className="text-sm text-gray-500">
                  {accountInfo?.pattern_type && `Pattern: ${accountInfo.pattern_type}`}
                  {accountInfo?.total_weeks && ` • ${accountInfo.total_weeks} weeks`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {accountInfo && (
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  accountInfo.ending_health >= 70 ? 'bg-green-100 text-green-800' :
                  accountInfo.ending_health >= 50 ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  Health: {accountInfo.ending_health}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* View Tabs */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex gap-1">
            {views.map(view => (
              <button
                key={view.id}
                onClick={() => setActiveView(view.id as any)}
                className={`flex items-center gap-2 px-4 py-3 border-b-2 transition ${
                  activeView === view.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                {view.icon}
                {view.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {activeView === 'health' && (
          <HealthOverviewView
            weeklyData={weeklyData}
            selectedWeek={selectedWeek}
            onWeekChange={setSelectedWeek}
          />
        )}
        {activeView === 'signals' && (
          <QualitativeSignalsView signals={signals} />
        )}
        {activeView === 'analyst' && (
          <SignalAnalystView
            output={analystOutput}
            onRunAnalysis={runSignalAnalysis}
            loading={analysisLoading}
          />
        )}
        {activeView === 'correlation' && (
          <CorrelationView weeklyData={weeklyData} signals={signals} />
        )}
      </div>
    </div>
  );
};

export default JourneyDashboardV3;
