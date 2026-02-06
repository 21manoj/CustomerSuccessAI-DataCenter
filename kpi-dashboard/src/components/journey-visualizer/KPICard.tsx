/**
 * KPI Card Component
 * ===================
 * 
 * Displays individual KPI with:
 * - Raw value prominently (8,500 hours)
 * - Normalized score secondarily (85/100)
 * - Industry context (critical/at-risk/healthy ranges)
 * - Visual status indicator
 * - Enhanced tooltip
 * 
 * Supports both V1 (normalized only) and V2 (raw + normalized)
 */

import React, { useState } from 'react';

interface RawKPI {
  value: number;
  unit: string;
}

interface KPICardProps {
  name: string;
  rawValue?: RawKPI;
  normalizedValue: number;
  showIndustryContext?: boolean;
  isV2?: boolean;
}

interface KPIRange {
  critical: string;
  at_risk: string;
  healthy: string;
  recommendation?: string;
}

const KPICard: React.FC<KPICardProps> = ({
  name,
  rawValue,
  normalizedValue,
  showIndustryContext = true,
  isV2 = false
}) => {
  const [showTooltip, setShowTooltip] = useState(false);
  
  // Get KPI ranges and metadata
  const ranges = getKPIRanges(name);
  const status = getKPIStatus(normalizedValue);
  const statusColor = getStatusColor(status);
  const formattedName = formatKPIName(name);
  
  return (
    <div className="bg-white rounded-lg border border-gray-200 hover:shadow-lg transition-shadow">
      {/* Card Content */}
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <h4 className="font-medium text-gray-700 text-sm flex-1">
            {formattedName}
          </h4>
          
          {/* Status Badge */}
          <div className={`px-2 py-0.5 rounded text-xs font-medium ${statusColor}`}>
            {status}
          </div>
        </div>
        
        {/* Value Display */}
        <div className="mb-3">
          {rawValue ? (
            // V2: Show raw value prominently
            <>
              <div className="text-3xl font-bold text-blue-600 mb-1">
                {formatNumber(rawValue.value)} {rawValue.unit}
              </div>
              <div className="text-sm text-gray-500">
                Score: {normalizedValue.toFixed(1)}/100
              </div>
            </>
          ) : (
            // V1: Show normalized only
            <div className="text-3xl font-bold text-gray-600">
              {normalizedValue.toFixed(1)}/100
            </div>
          )}
        </div>
        
        {/* Industry Context */}
        {showIndustryContext && ranges && (
          <div className="space-y-2">
            {/* Visual Bar */}
            <div className="relative h-2 bg-gradient-to-r from-red-200 via-yellow-200 to-green-200 rounded-full overflow-hidden">
              {/* Current Position Marker */}
              <div 
                className="absolute top-0 h-full w-1 bg-black"
                style={{ left: `${normalizedValue}%` }}
              >
                <div className="absolute -top-6 -left-4 text-xs font-bold text-black">
                  ▼
                </div>
              </div>
            </div>
            
            {/* Range Labels */}
            <div className="flex justify-between text-xs text-gray-500">
              <span title="Critical">🔴 {ranges.critical}</span>
              <span title="At-Risk">🟡 {ranges.at_risk}</span>
              <span title="Healthy">🟢 {ranges.healthy}</span>
            </div>
          </div>
        )}
        
        {/* Recommendation (for at-risk/critical) */}
        {normalizedValue < 60 && ranges?.recommendation && (
          <div className="mt-3 p-2 bg-yellow-50 border-l-4 border-yellow-500 text-xs">
            <div className="font-medium text-yellow-800">💡 Recommendation:</div>
            <div className="text-yellow-700 mt-1">{ranges.recommendation}</div>
          </div>
        )}
      </div>
      
      {/* Enhanced Tooltip (on hover) */}
      <div className="relative">
        <button
          className="w-full px-4 py-2 text-xs text-gray-500 hover:bg-gray-50 border-t border-gray-200"
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
        >
          More Info
        </button>
        
        {showTooltip && (
          <div className="absolute bottom-full left-0 right-0 mb-2 p-4 bg-gray-900 text-white rounded-lg shadow-xl z-10 text-sm">
            {/* Raw Value */}
            {rawValue && (
              <div className="mb-2">
                <div className="font-bold text-lg">
                  {formatNumber(rawValue.value)} {rawValue.unit}
                </div>
                <div className="text-gray-300 text-xs">Raw Measurement</div>
              </div>
            )}
            
            {/* Normalized Score */}
            <div className="mb-2">
              <div className="text-gray-300">
                Normalized: {normalizedValue.toFixed(1)}/100
              </div>
            </div>
            
            {/* Industry Ranges */}
            {ranges && (
              <div className="border-t border-gray-700 pt-2 text-xs">
                <div className="text-gray-400 mb-1">Industry Ranges:</div>
                <div className="text-red-400">Critical: {ranges.critical}</div>
                <div className="text-yellow-400">At-Risk: {ranges.at_risk}</div>
                <div className="text-green-400">Healthy: {ranges.healthy}</div>
              </div>
            )}
            
            {/* Status */}
            <div className="border-t border-gray-700 pt-2 mt-2">
              <div className={`font-medium ${
                status === 'Healthy' ? 'text-green-400' :
                status === 'At-Risk' ? 'text-yellow-400' :
                'text-red-400'
              }`}>
                Status: {status}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function formatKPIName(name: string): string {
  return name
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatNumber(value: number): string {
  if (value >= 1000) {
    return value.toLocaleString();
  }
  return value.toFixed(1);
}

function getKPIStatus(normalizedValue: number): string {
  if (normalizedValue >= 70) return 'Healthy';
  if (normalizedValue >= 50) return 'At-Risk';
  return 'Critical';
}

function getStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    'Healthy': 'bg-green-100 text-green-800',
    'At-Risk': 'bg-yellow-100 text-yellow-800',
    'Critical': 'bg-red-100 text-red-800',
  };
  
  return colorMap[status] || 'bg-gray-100 text-gray-800';
}

function getKPIRanges(kpiName: string): KPIRange | null {
  // In production, load from API or config
  // For now, hardcoded ranges for common KPIs
  
  const ranges: Record<string, KPIRange> = {
    'mtbf': {
      critical: '<5,000h',
      at_risk: '5,000-10,000h',
      healthy: '>10,000h',
      recommendation: 'Review RMA patterns and thermal management. Target 10,000+ hours MTBF.'
    },
    'critical_incident_rate': {
      critical: '>2 P1/month',
      at_risk: '1-2 P1/month',
      healthy: '<1 P1/month',
      recommendation: 'Implement proactive monitoring and faster incident response.'
    },
    'gpu_utilization_rate': {
      critical: '<50%',
      at_risk: '50-70%',
      healthy: '>70%',
      recommendation: 'Optimize workload scheduling and identify idle capacity.'
    },
    'unplanned_downtime': {
      critical: '<99.5%',
      at_risk: '99.5-99.9%',
      healthy: '>99.9%',
      recommendation: 'Implement redundancy and improve failover procedures.'
    },
    'expansion_probability_90d': {
      critical: '<40%',
      at_risk: '40-60%',
      healthy: '>60%',
      recommendation: 'Increase executive engagement and showcase success metrics.'
    },
    'partner_engagement_score': {
      critical: '<1 meeting/mo',
      at_risk: '1-2 meetings/mo',
      healthy: '>2 meetings/mo',
      recommendation: 'Schedule regular partner check-ins and co-sell opportunities.'
    },
  };
  
  return ranges[kpiName] || null;
}

export default KPICard;
