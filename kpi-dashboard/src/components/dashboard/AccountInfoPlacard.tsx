/**
 * Account Info Placard
 * ====================
 * 
 * Summary card showing account information at the top of Journey Dashboard
 * 
 * Displays:
 * - Account name, industry, segment
 * - ARR, renewal date, contract info
 * - Health score with trend
 * - CSM info, Champion info
 * - Quick stats: Churn risk, Expansion, NPS, Open tickets
 */

import React from 'react';
import {
  Building2, DollarSign, Calendar, User, Users, Phone, Mail,
  TrendingUp, TrendingDown, Minus, AlertTriangle, Target,
  MessageSquare, Ticket, Star, Clock, ExternalLink
} from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

interface AccountInfo {
  account_id: string;
  account_name: string;
  industry: string;
  segment: string;
  tier: string;
  
  // Financial
  arr: number;
  contract_value?: number;
  contract_start?: string;
  renewal_date?: string;
  days_to_renewal?: number;
  contract_months?: number;
  
  // Health
  health_score: number;
  health_status: 'Healthy' | 'At Risk' | 'Critical';
  health_trend: number;
  pattern_type?: string;
  
  // Predictions
  churn_probability: number;
  expansion_probability: number;
  
  // Team
  csm_name?: string;
  csm_email?: string;
  csm_phone?: string;
  days_since_contact?: number;
  
  // Champion
  champion_name?: string;
  champion_title?: string;
  champion_email?: string;
  champion_sentiment?: 'positive' | 'neutral' | 'negative';
  
  // Metrics
  nps_score?: number;
  nps_trend?: number;
  open_tickets?: number;
  csat_score?: number;
  
  // Product
  products?: string[];
  gpu_count?: number;
  deployment_type?: string;
}

interface AccountInfoPlacardProps {
  accountInfo: AccountInfo | null;
  loading?: boolean;
  onEdit?: () => void;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

const formatCurrency = (value: number): string => {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  } else if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value.toFixed(0)}`;
};

const formatDate = (dateStr: string | undefined): string => {
  if (!dateStr) return 'N/A';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

const getHealthColor = (score: number): string => {
  if (score >= 70) return 'text-green-600';
  if (score >= 50) return 'text-yellow-600';
  return 'text-red-600';
};

const getHealthBgColor = (score: number): string => {
  if (score >= 70) return 'bg-green-100 border-green-300';
  if (score >= 50) return 'bg-yellow-100 border-yellow-300';
  return 'bg-red-100 border-red-300';
};

const getTrendIcon = (trend: number) => {
  if (trend > 0) return <TrendingUp className="w-4 h-4 text-green-500" />;
  if (trend < 0) return <TrendingDown className="w-4 h-4 text-red-500" />;
  return <Minus className="w-4 h-4 text-gray-400" />;
};

const getSentimentColor = (sentiment: string | undefined): string => {
  switch (sentiment) {
    case 'positive': return 'text-green-600';
    case 'negative': return 'text-red-600';
    default: return 'text-gray-600';
  }
};

// ============================================================================
// STAT CARD COMPONENT
// ============================================================================

const StatCard: React.FC<{
  label: string;
  value: string | number;
  subtext?: string;
  trend?: number;
  color?: 'green' | 'yellow' | 'red' | 'blue' | 'gray';
}> = ({ label, value, subtext, trend, color = 'gray' }) => {
  const colorClasses = {
    green: 'bg-green-50 border-green-200',
    yellow: 'bg-yellow-50 border-yellow-200',
    red: 'bg-red-50 border-red-200',
    blue: 'bg-blue-50 border-blue-200',
    gray: 'bg-gray-50 border-gray-200'
  };

  return (
    <div className={`p-3 rounded-lg border ${colorClasses[color]}`}>
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-xl font-bold">{value}</span>
        {trend !== undefined && getTrendIcon(trend)}
      </div>
      {subtext && <p className="text-xs text-gray-500 mt-0.5">{subtext}</p>}
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const AccountInfoPlacard: React.FC<AccountInfoPlacardProps> = ({
  accountInfo,
  loading = false,
  onEdit
}) => {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6 animate-pulse">
        <div className="flex items-start gap-6">
          <div className="w-16 h-16 bg-gray-200 rounded-lg" />
          <div className="flex-1 space-y-3">
            <div className="h-6 bg-gray-200 rounded w-1/3" />
            <div className="h-4 bg-gray-200 rounded w-1/2" />
          </div>
          <div className="w-24 h-24 bg-gray-200 rounded-lg" />
        </div>
      </div>
    );
  }

  if (!accountInfo) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6 text-center text-gray-500">
        No account information available
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-50 to-slate-100 px-6 py-4 border-b">
        <div className="flex items-start justify-between">
          {/* Left: Logo + Name + Industry */}
          <div className="flex items-start gap-4">
            {/* Logo placeholder */}
            <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center text-white font-bold text-xl shadow-sm">
              {accountInfo.account_name.charAt(0)}
            </div>
            
            <div>
              <h2 className="text-xl font-bold text-gray-900">{accountInfo.account_name}</h2>
              <div className="flex items-center gap-2 mt-1 text-sm text-gray-600">
                <Building2 className="w-4 h-4" />
                <span>{accountInfo.industry}</span>
                <span className="text-gray-300">•</span>
                <span>{accountInfo.segment}</span>
                <span className="text-gray-300">•</span>
                <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                  {accountInfo.tier}
                </span>
              </div>
              
              {/* ARR and Renewal */}
              <div className="flex items-center gap-4 mt-2 text-sm">
                <div className="flex items-center gap-1">
                  <DollarSign className="w-4 h-4 text-gray-400" />
                  <span className="font-semibold">{formatCurrency(accountInfo.arr)}</span>
                  <span className="text-gray-500">ARR</span>
                </div>
                <div className="flex items-center gap-1">
                  <Calendar className="w-4 h-4 text-gray-400" />
                  <span>Renewal: {formatDate(accountInfo.renewal_date)}</span>
                  {accountInfo.days_to_renewal && (
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      accountInfo.days_to_renewal <= 30 ? 'bg-red-100 text-red-700' :
                      accountInfo.days_to_renewal <= 90 ? 'bg-yellow-100 text-yellow-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {accountInfo.days_to_renewal}d
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
          
          {/* Right: Health Score */}
          <div className={`px-5 py-3 rounded-lg border-2 text-center ${getHealthBgColor(accountInfo.health_score)}`}>
            <p className="text-xs text-gray-600 uppercase tracking-wide">Health</p>
            <p className={`text-3xl font-bold ${getHealthColor(accountInfo.health_score)}`}>
              {accountInfo.health_score}
            </p>
            <div className="flex items-center justify-center gap-1 mt-1">
              {getTrendIcon(accountInfo.health_trend)}
              <span className={`text-sm ${
                accountInfo.health_trend > 0 ? 'text-green-600' :
                accountInfo.health_trend < 0 ? 'text-red-600' : 'text-gray-500'
              }`}>
                {accountInfo.health_trend > 0 ? '+' : ''}{accountInfo.health_trend}
              </span>
            </div>
            <p className={`text-xs font-medium mt-1 ${getHealthColor(accountInfo.health_score)}`}>
              {accountInfo.health_status}
            </p>
          </div>
        </div>
      </div>
      
      {/* Body */}
      <div className="p-6">
        {/* Team & Champion Row */}
        <div className="flex items-start gap-8 mb-6">
          {/* CSM Info */}
          <div className="flex-1">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
              <User className="w-4 h-4" />
              <span className="font-medium">Customer Success Manager</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-indigo-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">{accountInfo.csm_name || 'Unassigned'}</p>
                {accountInfo.csm_email && (
                  <a href={`mailto:${accountInfo.csm_email}`} className="text-sm text-blue-600 hover:underline">
                    {accountInfo.csm_email}
                  </a>
                )}
                {accountInfo.days_since_contact !== undefined && (
                  <p className="text-xs text-gray-500 mt-0.5 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Last contact: {accountInfo.days_since_contact === 0 ? 'Today' : 
                      accountInfo.days_since_contact === 1 ? 'Yesterday' :
                      `${accountInfo.days_since_contact} days ago`}
                  </p>
                )}
              </div>
            </div>
          </div>
          
          {/* Champion Info */}
          <div className="flex-1">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
              <Star className="w-4 h-4" />
              <span className="font-medium">Champion</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center">
                <Star className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="font-medium text-gray-900">{accountInfo.champion_name || 'Not identified'}</p>
                {accountInfo.champion_title && (
                  <p className="text-sm text-gray-600">{accountInfo.champion_title}</p>
                )}
                {accountInfo.champion_sentiment && (
                  <p className={`text-xs mt-0.5 flex items-center gap-1 ${getSentimentColor(accountInfo.champion_sentiment)}`}>
                    <MessageSquare className="w-3 h-3" />
                    Sentiment: {accountInfo.champion_sentiment}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
        
        {/* Divider */}
        <div className="border-t my-4" />
        
        {/* Quick Stats */}
        <div className="grid grid-cols-4 gap-4">
          <StatCard
            label="Churn Risk"
            value={`${accountInfo.churn_probability}%`}
            subtext={accountInfo.churn_probability > 50 ? 'High Risk' : accountInfo.churn_probability > 30 ? 'Moderate' : 'Low'}
            color={accountInfo.churn_probability > 50 ? 'red' : accountInfo.churn_probability > 30 ? 'yellow' : 'green'}
          />
          
          <StatCard
            label="Expansion"
            value={`${accountInfo.expansion_probability}%`}
            subtext={accountInfo.expansion_probability > 60 ? 'High Potential' : accountInfo.expansion_probability > 40 ? 'Moderate' : 'Low'}
            color={accountInfo.expansion_probability > 60 ? 'green' : accountInfo.expansion_probability > 40 ? 'blue' : 'gray'}
          />
          
          <StatCard
            label="NPS Score"
            value={accountInfo.nps_score ?? 'N/A'}
            trend={accountInfo.nps_trend}
            subtext={accountInfo.nps_score ? (accountInfo.nps_score >= 50 ? 'Promoter' : accountInfo.nps_score >= 0 ? 'Passive' : 'Detractor') : undefined}
            color={accountInfo.nps_score ? (accountInfo.nps_score >= 50 ? 'green' : accountInfo.nps_score >= 0 ? 'yellow' : 'red') : 'gray'}
          />
          
          <StatCard
            label="Open Tickets"
            value={accountInfo.open_tickets ?? 0}
            subtext={accountInfo.open_tickets === 0 ? 'All clear' : accountInfo.open_tickets === 1 ? '1 pending' : `${accountInfo.open_tickets} pending`}
            color={!accountInfo.open_tickets || accountInfo.open_tickets === 0 ? 'green' : accountInfo.open_tickets <= 2 ? 'yellow' : 'red'}
          />
        </div>
        
        {/* Products/Deployment (optional) */}
        {(accountInfo.products?.length || accountInfo.gpu_count) && (
          <>
            <div className="border-t my-4" />
            <div className="flex items-center gap-4 text-sm text-gray-600">
              {accountInfo.products?.length && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">Products:</span>
                  {accountInfo.products.map((p, i) => (
                    <span key={i} className="px-2 py-0.5 bg-gray-100 rounded text-xs">{p}</span>
                  ))}
                </div>
              )}
              {accountInfo.gpu_count && (
                <div className="flex items-center gap-1">
                  <span className="text-gray-400">GPUs:</span>
                  <span className="font-medium">{accountInfo.gpu_count}</span>
                </div>
              )}
              {accountInfo.deployment_type && (
                <div className="flex items-center gap-1">
                  <span className="text-gray-400">Deployment:</span>
                  <span>{accountInfo.deployment_type}</span>
                </div>
              )}
            </div>
          </>
        )}
      </div>
      
      {/* Edit Button (if handler provided) */}
      {onEdit && (
        <div className="px-6 py-3 bg-gray-50 border-t flex justify-end">
          <button
            onClick={onEdit}
            className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
          >
            <ExternalLink className="w-4 h-4" />
            Edit Account
          </button>
        </div>
      )}
    </div>
  );
};

export default AccountInfoPlacard;
