/**
 * Qualitative Signals View - Database Integration
 * ================================================
 * 
 * Fetches signals from /api/journey/:accountId/signals
 * instead of using hardcoded data.
 * 
 * Replace the existing QualitativeSignalsView in JourneyDashboardV3.tsx
 * with this version.
 */

import React, { useState, useEffect } from 'react';
import {
  Mail, Calendar, Ticket, Phone, FileText, Filter,
  TrendingUp, TrendingDown, Minus, AlertTriangle,
  ChevronDown, ChevronUp, ExternalLink, RefreshCw
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { apiCall } from '../../utils/api';

// ============================================================================
// TYPES
// ============================================================================

interface QualitativeSignal {
  signal_id: number;
  account_id: string;
  signal_type: 'email' | 'meeting' | 'support_ticket' | 'call' | 'csm_note';
  date: string;
  week_number: number;
  subject: string;
  summary: string;
  from_contact: string;
  from_role: string;
  to_contact: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  sentiment_score: number;
  priority: 'critical' | 'high' | 'medium' | 'low';
  health_impact: number;
  source: string;
  tags: string[];
  created_at: string;
}

interface SignalCounts {
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  critical: number;
  by_type: {
    email: number;
    meeting: number;
    support_ticket: number;
    call: number;
  };
}

interface QualitativeSignalsViewProps {
  accountId: string;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

const getSignalIcon = (type: string) => {
  switch (type) {
    case 'email': return <Mail className="w-4 h-4" />;
    case 'meeting': return <Calendar className="w-4 h-4" />;
    case 'support_ticket': return <Ticket className="w-4 h-4" />;
    case 'call': return <Phone className="w-4 h-4" />;
    default: return <FileText className="w-4 h-4" />;
  }
};

const getSentimentColor = (sentiment: string) => {
  switch (sentiment) {
    case 'positive': return 'text-green-600 bg-green-50 border-green-200';
    case 'negative': return 'text-red-600 bg-red-50 border-red-200';
    default: return 'text-gray-600 bg-gray-50 border-gray-200';
  }
};

const getSentimentBadgeColor = (sentiment: string) => {
  switch (sentiment) {
    case 'positive': return 'bg-green-100 text-green-800';
    case 'negative': return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-800';
  }
};

const getPriorityColor = (priority: string) => {
  switch (priority) {
    case 'critical': return 'bg-red-600 text-white';
    case 'high': return 'bg-orange-500 text-white';
    case 'medium': return 'bg-yellow-500 text-white';
    default: return 'bg-gray-400 text-white';
  }
};

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric',
    year: 'numeric'
  });
};

const formatRelativeDate = (dateStr: string) => {
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return formatDate(dateStr);
};

// ============================================================================
// SIGNAL CARD COMPONENT
// ============================================================================

const SignalCard: React.FC<{ signal: QualitativeSignal }> = ({ signal }) => {
  const [expanded, setExpanded] = useState(false);
  
  return (
    <div className={`border rounded-lg overflow-hidden ${getSentimentColor(signal.sentiment)}`}>
      <div 
        className="p-4 cursor-pointer hover:bg-opacity-80"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className={`p-2 rounded-lg ${
              signal.sentiment === 'positive' ? 'bg-green-100' :
              signal.sentiment === 'negative' ? 'bg-red-100' : 'bg-gray-100'
            }`}>
              {getSignalIcon(signal.signal_type)}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getPriorityColor(signal.priority)}`}>
                  {signal.priority}
                </span>
                <span className={`px-2 py-0.5 rounded text-xs ${getSentimentBadgeColor(signal.sentiment)}`}>
                  {signal.sentiment}
                </span>
                <span className="text-xs text-gray-500">
                  {signal.signal_type.replace('_', ' ')}
                </span>
              </div>
              <h4 className="font-medium text-gray-900">{signal.subject}</h4>
              <p className="text-sm text-gray-600 mt-1">
                {signal.from_contact}
                {signal.from_role && <span className="text-gray-400"> • {signal.from_role}</span>}
              </p>
            </div>
          </div>
          <div className="flex flex-col items-end gap-2">
            <span className="text-xs text-gray-500">{formatRelativeDate(signal.date)}</span>
            {signal.health_impact !== 0 && (
              <span className={`text-sm font-medium ${
                signal.health_impact > 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {signal.health_impact > 0 ? '+' : ''}{signal.health_impact} pts
              </span>
            )}
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </div>
      </div>
      
      {expanded && (
        <div className="px-4 pb-4 border-t bg-white bg-opacity-50">
          <div className="pt-3">
            <p className="text-sm text-gray-700">{signal.summary}</p>
            <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
              <span>Source: {signal.source}</span>
              <span>Week {signal.week_number}</span>
              {signal.sentiment_score !== undefined && (
                <span>Sentiment score: {(signal.sentiment_score * 100).toFixed(0)}%</span>
              )}
            </div>
            {signal.tags && signal.tags.length > 0 && (
              <div className="flex gap-1 mt-2">
                {signal.tags.map((tag, i) => (
                  <span key={i} className="px-2 py-0.5 bg-gray-200 rounded text-xs">
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const QualitativeSignalsView: React.FC<QualitativeSignalsViewProps> = ({ accountId }) => {
  const [signals, setSignals] = useState<QualitativeSignal[]>([]);
  const [counts, setCounts] = useState<SignalCounts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [sentimentFilter, setSentimentFilter] = useState<string>('all');
  const [showFilters, setShowFilters] = useState(false);

  // Fetch signals from API
  useEffect(() => {
    const fetchSignals = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const params = new URLSearchParams();
        if (typeFilter !== 'all') params.append('type', typeFilter);
        if (sentimentFilter !== 'all') params.append('sentiment', sentimentFilter);
        params.append('limit', '50');
        
        const response = await apiCall(`/api/journey/${accountId}/signals?${params}`);
        
        if (!response.ok) {
          throw new Error('Failed to fetch signals');
        }
        
        const data = await response.json();
        setSignals(data.signals || []);
        setCounts(data.counts || null);
      } catch (err) {
        console.error('Error fetching signals:', err);
        setError('Failed to load signals. Using sample data.');
        
        // Fallback to sample data
        setSignals([
          {
            signal_id: 1,
            account_id: accountId,
            signal_type: 'email',
            date: new Date().toISOString(),
            week_number: 45,
            subject: 'Q4 Planning Discussion',
            summary: 'Customer expressed interest in expanding GPU cluster for new AI initiatives.',
            from_contact: 'Jane Doe',
            from_role: 'VP Engineering',
            to_contact: 'CSM',
            sentiment: 'positive',
            sentiment_score: 0.8,
            priority: 'high',
            health_impact: 5,
            source: 'gmail',
            tags: ['expansion', 'q4'],
            created_at: new Date().toISOString()
          }
        ]);
        setCounts({
          total: 1,
          positive: 1,
          negative: 0,
          neutral: 0,
          critical: 0,
          by_type: { email: 1, meeting: 0, support_ticket: 0, call: 0 }
        });
      } finally {
        setLoading(false);
      }
    };

    fetchSignals();
  }, [accountId, typeFilter, sentimentFilter]);

  // Sentiment chart data
  const sentimentChartData = counts ? [
    { name: 'Positive', value: counts.positive, color: '#22c55e' },
    { name: 'Neutral', value: counts.neutral, color: '#9ca3af' },
    { name: 'Negative', value: counts.negative, color: '#ef4444' }
  ].filter(d => d.value > 0) : [];

  // Type chart data
  const typeChartData = counts ? [
    { name: 'Email', value: counts.by_type.email, color: '#3b82f6' },
    { name: 'Meeting', value: counts.by_type.meeting, color: '#8b5cf6' },
    { name: 'Ticket', value: counts.by_type.support_ticket, color: '#f59e0b' },
    { name: 'Call', value: counts.by_type.call, color: '#10b981' }
  ].filter(d => d.value > 0) : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
        <span className="ml-2 text-gray-600">Loading signals...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Error Banner */}
      {error && (
        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800 text-sm">
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Total Signals</span>
            <FileText className="w-5 h-5 text-gray-400" />
          </div>
          <p className="text-2xl font-bold mt-1">{counts?.total || 0}</p>
        </div>
        
        <div className="bg-green-50 rounded-lg border border-green-200 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-green-600">Positive</span>
            <TrendingUp className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-2xl font-bold text-green-700 mt-1">{counts?.positive || 0}</p>
        </div>
        
        <div className="bg-red-50 rounded-lg border border-red-200 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-red-600">Negative</span>
            <TrendingDown className="w-5 h-5 text-red-500" />
          </div>
          <p className="text-2xl font-bold text-red-700 mt-1">{counts?.negative || 0}</p>
        </div>
        
        <div className="bg-orange-50 rounded-lg border border-orange-200 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-orange-600">Critical</span>
            <AlertTriangle className="w-5 h-5 text-orange-500" />
          </div>
          <p className="text-2xl font-bold text-orange-700 mt-1">{counts?.critical || 0}</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-2 gap-4">
        {/* Sentiment Distribution */}
        <div className="bg-white rounded-lg border p-4">
          <h4 className="font-medium mb-4">Sentiment Distribution</h4>
          {sentimentChartData.length > 0 ? (
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sentimentChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {sentimentChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-500">
              No data available
            </div>
          )}
        </div>

        {/* Signal Types */}
        <div className="bg-white rounded-lg border p-4">
          <h4 className="font-medium mb-4">Signal Types</h4>
          {typeChartData.length > 0 ? (
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={typeChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {typeChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-500">
              No data available
            </div>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-medium">Signal Timeline</h4>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"
          >
            <Filter className="w-4 h-4" />
            Filters
            {showFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

        {showFilters && (
          <div className="flex gap-4 mb-4 p-3 bg-gray-50 rounded-lg">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Type</label>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="px-3 py-1.5 border rounded text-sm"
              >
                <option value="all">All Types</option>
                <option value="email">Email</option>
                <option value="meeting">Meeting</option>
                <option value="support_ticket">Support Ticket</option>
                <option value="call">Call</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Sentiment</label>
              <select
                value={sentimentFilter}
                onChange={(e) => setSentimentFilter(e.target.value)}
                className="px-3 py-1.5 border rounded text-sm"
              >
                <option value="all">All Sentiments</option>
                <option value="positive">Positive</option>
                <option value="neutral">Neutral</option>
                <option value="negative">Negative</option>
              </select>
            </div>
          </div>
        )}

        {/* Signal List */}
        <div className="space-y-3">
          {signals.length > 0 ? (
            signals.map((signal) => (
              <SignalCard key={signal.signal_id} signal={signal} />
            ))
          ) : (
            <div className="text-center py-8 text-gray-500">
              <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No signals found</p>
              <p className="text-sm">Signals will appear here when data is imported</p>
            </div>
          )}
        </div>

        {/* Load More */}
        {signals.length >= 50 && (
          <div className="text-center mt-4">
            <button className="text-sm text-blue-600 hover:underline">
              Load more signals...
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default QualitativeSignalsView;
