/**
 * Journey Visualizer Component (TypeScript)
 * ==========================================
 * 
 * Professional journey visualization for Wizard A generated data
 * Fully typed for TypeScript
 */

import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  BarChart, Bar, ComposedChart, Area, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import {
  Search, TrendingUp, Users, Activity, Award, Eye
} from 'lucide-react';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

interface Journey {
  account_id: string;
  account_name: string;
  pattern_type: string;
  starting_health: number;
  ending_health: number;
  lowest_health: number;
  highest_health: number;
  total_weeks: number;
  total_events?: number;
  events: JourneyEvent[];
  summary: {
    total_events: number;
    total_csm_investment?: number;
    financial_impact?: string;
  };
}

interface JourneyEvent {
  week_number: number;
  health_score_after: number;
  phase: string;
  sentiment_value: number;
}

interface KPI {
  account_id: string;
  week_number: number;
  kpi_name: string;
  value: number;
  percentile?: number;
}

interface Milestone {
  account_id: string;
  milestone_type: string;
  week_number: number;
  description: string;
}

interface WizardRun {
  run_id: string;
  created_at: number;
  accounts_generated: number;
  metadata?: any;
}

interface PatternDistribution {
  pattern: string;
  count: number;
  percentage: string;
}

interface HealthTrendData {
  week: number;
  health: number;
  phase: string;
  sentiment: number;
}

// ============================================================================
// CONSTANTS
// ============================================================================

const PATTERN_COLORS: Record<string, string> = {
  crisis: '#ef4444',
  churn: '#f97316',
  stable: '#3b82f6',
  expansion: '#10b981'
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const JourneyVisualizer: React.FC = () => {
  // Get accountId from URL if present
  const { accountId } = useParams<{ accountId?: string }>();
  
  // State
  const [runs, setRuns] = useState<WizardRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [journeys, setJourneys] = useState<Journey[]>([]);
  const [kpis, setKpis] = useState<KPI[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<Journey | null>(null);
  const [view, setView] = useState<string>('overview');
  const [filterPattern, setFilterPattern] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  // Load wizard runs on mount
  useEffect(() => {
    loadWizardRuns();
  }, []);

  // Load data when run selected
  useEffect(() => {
    if (selectedRun) {
      loadRunData(selectedRun);
    }
  }, [selectedRun]);

  // Auto-select account if accountId is in URL
  useEffect(() => {
    if (accountId && journeys.length > 0) {
      const account = journeys.find(j => j.account_id === accountId || j.account_id === `account-${accountId}`);
      if (account) {
        setSelectedAccount(account);
        setView('detail');
      }
    }
  }, [accountId, journeys]);

  // ============================================================================
  // DATA LOADING
  // ============================================================================

  const loadWizardRuns = async () => {
    try {
      const response = await fetch('/api/wizard/runs');
      const data = await response.json();
      setRuns(data.runs || []);
      if (data.runs && data.runs.length > 0) {
        setSelectedRun(data.runs[0].run_id);
      }
    } catch (error) {
      console.error('Failed to load wizard runs:', error);
    }
  };

  const loadRunData = async (runId: string) => {
    setLoading(true);
    try {
      // Load journey data
      const journeyResponse = await fetch(`/api/wizard/journey/${runId}`);
      const journeyData = await journeyResponse.json();
      setJourneys(journeyData.journeys || []);

      // Load KPI data
      const kpiResponse = await fetch(`/api/wizard/kpis/${runId}`);
      const kpiData = await kpiResponse.json();
      setKpis(kpiData.kpis || []);

      // Load milestone data
      const milestoneResponse = await fetch(`/api/wizard/milestones/${runId}`);
      const milestoneData = await milestoneResponse.json();
      setMilestones(milestoneData.milestones || []);

      setLoading(false);
    } catch (error) {
      console.error('Failed to load run data:', error);
      setLoading(false);
    }
  };

  // ============================================================================
  // DATA PROCESSING
  // ============================================================================

  const getFilteredJourneys = (): Journey[] => {
    let filtered = journeys;

    if (filterPattern !== 'all') {
      filtered = filtered.filter(j => j.pattern_type === filterPattern);
    }

    if (searchTerm) {
      filtered = filtered.filter(j =>
        j.account_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        j.account_id.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    return filtered;
  };

  const getPatternDistribution = (): PatternDistribution[] => {
    const distribution: Record<string, number> = {};
    journeys.forEach(j => {
      distribution[j.pattern_type] = (distribution[j.pattern_type] || 0) + 1;
    });
    return Object.entries(distribution).map(([pattern, count]) => ({
      pattern,
      count,
      percentage: ((count / journeys.length) * 100).toFixed(1)
    }));
  };

  const getHealthTrendData = (journey: Journey): HealthTrendData[] => {
    if (!journey || !journey.events) return [];
    
    return journey.events.map(event => ({
      week: event.week_number,
      health: event.health_score_after,
      phase: event.phase,
      sentiment: event.sentiment_value
    }));
  };

  // ============================================================================
  // RENDER FUNCTIONS
  // ============================================================================

  const renderRunSelector = () => (
    <div className="bg-white rounded-lg shadow p-4 mb-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Wizard Run</h3>
          <p className="text-sm text-gray-500">Select a data generation run to visualize</p>
        </div>
        <select
          value={selectedRun || ''}
          onChange={(e) => setSelectedRun(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        >
          {runs.map(run => (
            <option key={run.run_id} value={run.run_id}>
              {run.run_id} ({run.accounts_generated || 'N/A'} accounts)
            </option>
          ))}
        </select>
      </div>
    </div>
  );

  const renderSummaryCards = () => {
    const totalEvents = journeys.reduce((sum, j) => sum + (j.total_events || 0), 0);
    const avgHealth = journeys.reduce((sum, j) => sum + j.ending_health, 0) / journeys.length;
    const totalMilestones = milestones.length;

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Accounts</p>
              <p className="text-3xl font-bold text-gray-900">{journeys.length}</p>
            </div>
            <Users className="w-10 h-10 text-blue-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Events</p>
              <p className="text-3xl font-bold text-gray-900">{totalEvents}</p>
            </div>
            <Activity className="w-10 h-10 text-purple-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Avg Health</p>
              <p className="text-3xl font-bold text-gray-900">{avgHealth.toFixed(1)}</p>
            </div>
            <TrendingUp className="w-10 h-10 text-green-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Milestones</p>
              <p className="text-3xl font-bold text-gray-900">{totalMilestones}</p>
            </div>
            <Award className="w-10 h-10 text-yellow-500" />
          </div>
        </div>
      </div>
    );
  };

  const renderPatternDistribution = () => {
    const distribution = getPatternDistribution();

    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Pattern Distribution</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={distribution}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="pattern" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" radius={[8, 8, 0, 0]}>
              {distribution.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={PATTERN_COLORS[entry.pattern] || '#999'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          {distribution.map(d => (
            <div key={d.pattern} className="text-center">
              <div
                className="w-4 h-4 rounded-full mx-auto mb-2"
                style={{ backgroundColor: PATTERN_COLORS[d.pattern] || '#999' }}
              />
              <p className="text-sm font-medium text-gray-900 capitalize">{d.pattern}</p>
              <p className="text-xs text-gray-500">{d.count} accounts ({d.percentage}%)</p>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderJourneyTimeline = (journey: Journey) => {
    const trendData = getHealthTrendData(journey);

    return (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{journey.account_name}</h3>
            <p className="text-sm text-gray-500">
              {journey.account_id} • {journey.pattern_type} pattern
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className="px-3 py-1 rounded-full text-sm font-medium"
              style={{
                backgroundColor: (PATTERN_COLORS[journey.pattern_type] || '#999') + '20',
                color: PATTERN_COLORS[journey.pattern_type] || '#999'
              }}
            >
              {journey.pattern_type}
            </span>
          </div>
        </div>

        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="week" label={{ value: 'Week', position: 'insideBottom', offset: -5 }} />
            <YAxis label={{ value: 'Health Score', angle: -90, position: 'insideLeft' }} />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload as HealthTrendData;
                  return (
                    <div className="bg-white p-3 shadow-lg rounded-lg border">
                      <p className="font-medium">Week {data.week}</p>
                      <p className="text-sm">Health: {data.health.toFixed(1)}</p>
                      <p className="text-sm capitalize">Phase: {data.phase}</p>
                      <p className="text-sm">Sentiment: {data.sentiment.toFixed(2)}</p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Area
              type="monotone"
              dataKey="health"
              fill={(PATTERN_COLORS[journey.pattern_type] || '#999') + '20'}
              stroke="none"
            />
            <Line
              type="monotone"
              dataKey="health"
              stroke={PATTERN_COLORS[journey.pattern_type] || '#999'}
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </ComposedChart>
        </ResponsiveContainer>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <div>
            <p className="text-sm text-gray-500">Starting Health</p>
            <p className="text-xl font-semibold text-gray-900">{journey.starting_health.toFixed(1)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Ending Health</p>
            <p className="text-xl font-semibold text-gray-900">{journey.ending_health.toFixed(1)}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Total Events</p>
            <p className="text-xl font-semibold text-gray-900">{journey.total_events || 0}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Duration</p>
            <p className="text-xl font-semibold text-gray-900">{journey.total_weeks} weeks</p>
          </div>
        </div>
      </div>
    );
  };

  const renderAccountList = () => {
    const filteredJourneys = getFilteredJourneys();

    return (
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search accounts..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <select
              value={filterPattern}
              onChange={(e) => setFilterPattern(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Patterns</option>
              <option value="crisis">Crisis Recovery</option>
              <option value="churn">Ignored Churn</option>
              <option value="stable">Stable</option>
              <option value="expansion">Proactive Growth</option>
            </select>
          </div>
        </div>

        <div className="divide-y divide-gray-200">
          {filteredJourneys.map(journey => (
            <div
              key={journey.account_id}
              className="p-4 hover:bg-gray-50 cursor-pointer transition-colors"
              onClick={() => {
                setSelectedAccount(journey);
                setView('account');
              }}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h4 className="font-medium text-gray-900">{journey.account_name}</h4>
                    <span
                      className="px-2 py-1 rounded text-xs font-medium"
                      style={{
                        backgroundColor: (PATTERN_COLORS[journey.pattern_type] || '#999') + '20',
                        color: PATTERN_COLORS[journey.pattern_type] || '#999'
                      }}
                    >
                      {journey.pattern_type}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500">{journey.account_id}</p>
                </div>
                <div className="flex items-center gap-6 text-sm">
                  <div className="text-center">
                    <p className="text-gray-500">Health</p>
                    <p className="font-semibold text-gray-900">
                      {journey.starting_health.toFixed(0)} → {journey.ending_health.toFixed(0)}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-gray-500">Events</p>
                    <p className="font-semibold text-gray-900">{journey.total_events || 0}</p>
                  </div>
                  <Eye className="w-5 h-5 text-gray-400" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // ============================================================================
  // MAIN RENDER
  // ============================================================================

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading journey data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Journey Visualizer</h1>
          <p className="text-gray-600">Synthetic customer journeys generated by Wizard A</p>
        </div>

        {/* Run Selector */}
        {renderRunSelector()}

        {/* View Tabs */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setView('overview')}
              className={`px-6 py-3 font-medium ${
                view === 'overview'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setView('accounts')}
              className={`px-6 py-3 font-medium ${
                view === 'accounts'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              All Accounts
            </button>
            {selectedAccount && (
              <button
                onClick={() => setView('account')}
                className={`px-6 py-3 font-medium ${
                  view === 'account'
                    ? 'border-b-2 border-blue-500 text-blue-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {selectedAccount.account_name}
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        {view === 'overview' && (
          <>
            {renderSummaryCards()}
            {renderPatternDistribution()}
            <div className="space-y-6">
              {journeys.slice(0, 5).map(journey => renderJourneyTimeline(journey))}
            </div>
          </>
        )}

        {view === 'accounts' && renderAccountList()}

        {view === 'account' && selectedAccount && (
          <>
            <button
              onClick={() => {
                setView('accounts');
                setSelectedAccount(null);
              }}
              className="mb-4 text-blue-600 hover:text-blue-700 font-medium"
            >
              ← Back to all accounts
            </button>
            {renderJourneyTimeline(selectedAccount)}
          </>
        )}
      </div>
    </div>
  );
};

export default JourneyVisualizer;
